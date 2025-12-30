"""Content processor worker for background job processing.

This module provides the ContentProcessorWorker class which polls the
ingestion queue and processes jobs using the appropriate processor
based on source configuration.
"""

import asyncio
from typing import Any

import structlog
from collection_model.config import settings
from collection_model.domain.exceptions import ConfigurationError
from collection_model.infrastructure.ai_model_client import AiModelClient
from collection_model.infrastructure.blob_storage import BlobStorageClient
from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher
from collection_model.infrastructure.document_repository import DocumentRepository
from collection_model.infrastructure.ingestion_queue import IngestionQueue
from collection_model.infrastructure.metrics import ProcessingMetrics
from collection_model.infrastructure.raw_document_store import RawDocumentStore
from collection_model.processors import ProcessorNotFoundError, ProcessorRegistry
from collection_model.services.source_config_service import SourceConfigService
from fp_common.models.source_config import SourceConfig
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger(__name__)


class ContentProcessorWorker:
    """Background worker that processes queued ingestion jobs.

    Polls the ingestion_queue collection for pending jobs and processes
    them using the appropriate processor based on source configuration.
    """

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        ingestion_queue: IngestionQueue,
        source_config_service: SourceConfigService,
        processing_metrics: ProcessingMetrics | None = None,
        poll_interval: float | None = None,
        batch_size: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            db: MongoDB database instance.
            ingestion_queue: Ingestion queue for job management.
            source_config_service: Service for source config lookups.
            processing_metrics: Metrics for recording processing stats (optional).
            poll_interval: Seconds between queue polls (defaults to settings).
            batch_size: Max jobs to process per poll (defaults to settings).
            max_retries: Max retry attempts before permanent failure.
        """
        self.db = db
        self.queue = ingestion_queue
        self.config_service = source_config_service
        self._metrics = processing_metrics
        self.poll_interval = poll_interval or settings.worker_poll_interval
        self.batch_size = batch_size or settings.worker_batch_size
        self.max_retries = max_retries or settings.worker_max_retries
        self._running = False

        # Infrastructure clients (initialized on start)
        self._blob_client: BlobStorageClient | None = None
        self._raw_store: RawDocumentStore | None = None
        self._ai_client: AiModelClient | None = None
        self._doc_repo: DocumentRepository | None = None
        self._event_publisher: DaprEventPublisher | None = None

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info(
            "Content processor worker started",
            poll_interval=self.poll_interval,
            batch_size=self.batch_size,
            max_retries=self.max_retries,
        )

        # Initialize infrastructure clients
        await self._init_infrastructure()

        while self._running:
            try:
                await self._process_pending_jobs()
            except Exception as e:
                logger.exception("Worker loop error", error=str(e))

            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        logger.info("Content processor worker stopping")

        # Cleanup
        if self._blob_client:
            await self._blob_client.close()

        logger.info("Content processor worker stopped")

    async def _init_infrastructure(self) -> None:
        """Initialize infrastructure clients."""
        self._blob_client = BlobStorageClient()
        self._raw_store = RawDocumentStore(self.db, self._blob_client)
        self._ai_client = AiModelClient()
        self._doc_repo = DocumentRepository(self.db)
        self._event_publisher = DaprEventPublisher()

        # Ensure raw document indexes
        await self._raw_store.ensure_indexes()

        logger.info("Infrastructure clients initialized")

    async def _process_pending_jobs(self) -> None:
        """Process all pending jobs in the queue."""
        jobs = await self.queue.get_pending_jobs(limit=self.batch_size)

        if not jobs:
            return

        logger.debug("Processing pending jobs", count=len(jobs))

        for job in jobs:
            await self._process_job(job)

    async def _process_job(self, job: Any) -> None:
        """Process a single ingestion job."""
        import time

        start_time = time.time()

        logger.info(
            "Processing job",
            ingestion_id=job.ingestion_id,
            source_id=job.source_id,
            blob_path=job.blob_path,
        )

        try:
            # Update status to processing
            await self.queue.update_job_status(job.ingestion_id, "processing")

            # Get source config
            source_config = await self._get_source_config(job.source_id)

            # Get processor based on ingestion.processor_type - PURE CONFIG-DRIVEN
            processor = await self._get_processor(source_config)

            # Update status to extracting
            await self.queue.update_job_status(job.ingestion_id, "extracting")

            # Process the job
            result = await processor.process(job, source_config)

            # Record duration
            duration = time.time() - start_time
            self._record_metrics(job.source_id, result.success, duration, result.error_type)

            if result.success:
                await self.queue.update_job_status(
                    job.ingestion_id,
                    "completed",
                    document_id=result.document_id,
                )
                logger.info(
                    "Job completed successfully",
                    ingestion_id=job.ingestion_id,
                    document_id=result.document_id,
                    duration_seconds=duration,
                )
            else:
                await self._handle_failure(
                    job,
                    result.error_message or "Unknown error",
                    result.error_type or "unknown",
                )

        except ProcessorNotFoundError as e:
            # Configuration error - do not retry
            await self.queue.update_job_status(
                job.ingestion_id,
                "failed",
                error_message=str(e),
                error_type="config",
                no_retry=True,
            )
            self._record_metrics(job.source_id, False, time.time() - start_time, "config")
            logger.error("Processor not found", error=str(e), source_id=job.source_id)

        except ConfigurationError as e:
            # Configuration error - do not retry
            await self.queue.update_job_status(
                job.ingestion_id,
                "failed",
                error_message=str(e),
                error_type="config",
                no_retry=True,
            )
            self._record_metrics(job.source_id, False, time.time() - start_time, "config")
            logger.error("Configuration error", error=str(e), source_id=job.source_id)

        except Exception as e:
            await self._handle_failure(job, str(e), "unknown")
            self._record_metrics(job.source_id, False, time.time() - start_time, "unknown")

    async def _get_source_config(self, source_id: str) -> SourceConfig:
        """Get source config by source_id."""
        configs = await self.config_service.get_all_configs()
        for config in configs:
            if config.source_id == source_id:
                return config

        raise ConfigurationError(f"Source config not found: {source_id}")

    async def _get_processor(self, source_config: SourceConfig) -> Any:
        """Get the appropriate processor for the source config."""
        processor_type = source_config.ingestion.processor_type

        if not processor_type:
            raise ConfigurationError(f"No ingestion.processor_type in source config: {source_config.source_id}")

        processor = ProcessorRegistry.get_processor(processor_type)

        # Set dependencies on all processors via ABC method (no isinstance checks)
        processor.set_dependencies(
            blob_client=self._blob_client,
            raw_document_store=self._raw_store,
            ai_model_client=self._ai_client,
            document_repository=self._doc_repo,
            event_publisher=self._event_publisher,
        )

        return processor

    async def _handle_failure(
        self,
        job: Any,
        error_message: str,
        error_type: str,
    ) -> None:
        """Handle job failure with retry logic."""
        retry_count = await self.queue.increment_retry_count(job.ingestion_id)

        if retry_count >= self.max_retries:
            await self.queue.update_job_status(
                job.ingestion_id,
                "failed",
                error_message=error_message,
                error_type=error_type,
            )
            logger.error(
                "Job failed after max retries",
                ingestion_id=job.ingestion_id,
                retry_count=retry_count,
                error=error_message,
                error_type=error_type,
            )
        else:
            await self.queue.update_job_status(
                job.ingestion_id,
                "queued",  # Re-queue for retry
                error_message=error_message,
                error_type=error_type,
            )
            logger.warning(
                "Job failed, will retry",
                ingestion_id=job.ingestion_id,
                retry_count=retry_count,
                error=error_message,
                error_type=error_type,
            )

    def _record_metrics(
        self,
        source_id: str,
        success: bool,
        duration: float,
        error_type: str | None = None,
    ) -> None:
        """Record processing metrics."""
        if not self._metrics:
            return

        if success:
            self._metrics.record_success(source_id, duration)
        else:
            self._metrics.record_error(source_id, duration, error_type or "unknown")
