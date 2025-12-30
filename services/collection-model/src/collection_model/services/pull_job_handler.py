"""Pull Job Handler for scheduled pull ingestion (Story 2.7).

This module provides the PullJobHandler class which orchestrates
data fetching from external APIs when DAPR Jobs trigger callbacks.
Supports both single-fetch and multi-fetch with iteration.
"""

import asyncio
from typing import Any

import structlog
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.infrastructure.iteration_resolver import IterationResolver
from collection_model.infrastructure.pull_data_fetcher import PullDataFetcher
from collection_model.infrastructure.storage_metrics import StorageMetrics
from collection_model.processors.base import ContentProcessor

logger = structlog.get_logger(__name__)


class PullJobHandler:
    """Handles scheduled pull job execution.

    Orchestrates the pull ingestion flow:
    1. Load source config
    2. Resolve iteration items (if iteration block present)
    3. Fetch data from external API (single or parallel)
    4. Create IngestionJobs with inline content
    5. Process through the existing pipeline

    Attributes:
        source_config_service: Service for loading source configs.
        pull_data_fetcher: HTTP client for external APIs.
        iteration_resolver: MCP tool client for iteration resolution.
        processor: Content processor (JsonExtractionProcessor).
        ingestion_queue: Queue for tracking job status.
    """

    def __init__(
        self,
        source_config_service: Any,
        pull_data_fetcher: PullDataFetcher,
        iteration_resolver: IterationResolver,
        processor: ContentProcessor | None = None,
        ingestion_queue: Any | None = None,
    ) -> None:
        """Initialize the Pull Job Handler.

        Args:
            source_config_service: Service for loading source configs.
            pull_data_fetcher: HTTP client for external APIs.
            iteration_resolver: MCP tool client for iteration resolution.
            processor: Content processor for extracted data (optional, can be set via worker).
            ingestion_queue: Optional queue for tracking job status.
        """
        self._source_config = source_config_service
        self._fetcher = pull_data_fetcher
        self._resolver = iteration_resolver
        self._processor = processor
        self._queue = ingestion_queue
        self._worker: Any = None

    def set_worker(self, worker: Any) -> None:
        """Set the content processor worker for processor access.

        The worker provides access to configured processors with
        infrastructure dependencies (blob client, AI client, etc).

        Args:
            worker: ContentProcessorWorker instance.
        """
        self._worker = worker

    async def _get_processor(self, source_config: dict[str, Any]) -> ContentProcessor:
        """Get processor for the source config.

        Uses the worker to get a processor with dependencies set,
        or falls back to the directly injected processor.

        Args:
            source_config: Source configuration.

        Returns:
            Configured processor instance.
        """
        if self._worker:
            # Get processor from worker (has infrastructure dependencies)
            return await self._worker._get_processor(source_config)
        if self._processor:
            return self._processor
        raise RuntimeError("No processor available - set worker or processor")

    async def handle_job_trigger(self, source_id: str) -> dict[str, Any]:
        """Handle a DAPR Job trigger callback.

        Main entry point when a scheduled job fires. Loads the source
        config, resolves iteration (if any), fetches data, and processes
        through the ingestion pipeline.

        Args:
            source_id: Source identifier from the job callback.

        Returns:
            Summary dict with success status and counts:
            - success: Overall success (True if at least one fetch succeeded)
            - source_id: Source identifier
            - fetched: Number of successful fetches
            - failed: Number of failed fetches
            - duplicates: Number of duplicate documents detected
            - error: Error message if complete failure
        """
        logger.info("Pull job triggered", source_id=source_id)

        # Load source config
        source_config = await self._source_config.get_config(source_id)
        if not source_config:
            error_msg = f"Source config not found: {source_id}"
            logger.error(error_msg)
            return {
                "success": False,
                "source_id": source_id,
                "error": error_msg,
                "fetched": 0,
                "failed": 0,
                "duplicates": 0,
            }

        ingestion = source_config.get("ingestion", {})
        request_config = ingestion.get("request", {})
        iteration_config = ingestion.get("iteration")

        # Build pull config for fetcher
        pull_config = {
            "base_url": request_config.get("base_url", ""),
            "auth_type": request_config.get("auth_type", "none"),
            "auth_config": request_config.get("auth_config", {}),
            "parameters": request_config.get("parameters", {}),
        }

        if iteration_config:
            # Multi-fetch with iteration
            return await self._handle_iteration_fetch(
                source_id=source_id,
                source_config=source_config,
                pull_config=pull_config,
                iteration_config=iteration_config,
            )
        else:
            # Single fetch
            return await self._handle_single_fetch(
                source_id=source_id,
                source_config=source_config,
                pull_config=pull_config,
            )

    async def _handle_single_fetch(
        self,
        source_id: str,
        source_config: dict[str, Any],
        pull_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle single fetch (no iteration).

        Args:
            source_id: Source identifier.
            source_config: Full source configuration.
            pull_config: Pull configuration for fetcher.

        Returns:
            Summary dict with results.
        """
        try:
            content = await self._fetcher.fetch(
                pull_config=pull_config,
                iteration_item=None,
            )

            # Create job with inline content
            job = IngestionJob(
                source_id=source_id,
                content=content,
            )

            # Get processor and process through pipeline
            processor = await self._get_processor(source_config)
            result = await processor.process(job, source_config)

            is_duplicate = getattr(result, "is_duplicate", False)

            logger.info(
                "Single fetch completed",
                source_id=source_id,
                success=result.success,
                is_duplicate=is_duplicate,
            )

            # Record metrics (AC9)
            StorageMetrics.record_pull_fetch_success(source_id)

            return {
                "success": True,
                "source_id": source_id,
                "fetched": 1,
                "failed": 0,
                "duplicates": 1 if is_duplicate else 0,
            }

        except Exception as e:
            logger.exception(
                "Single fetch failed",
                source_id=source_id,
                error=str(e),
            )
            # Record failure metrics (AC9)
            StorageMetrics.record_pull_fetch_failed(source_id)

            return {
                "success": False,
                "source_id": source_id,
                "error": str(e),
                "fetched": 0,
                "failed": 1,
                "duplicates": 0,
            }

    async def _handle_iteration_fetch(
        self,
        source_id: str,
        source_config: dict[str, Any],
        pull_config: dict[str, Any],
        iteration_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle multi-fetch with iteration.

        Resolves iteration items via MCP tool, then fetches data
        for each item in parallel (respecting concurrency limit).

        Args:
            source_id: Source identifier.
            source_config: Full source configuration.
            pull_config: Pull configuration for fetcher.
            iteration_config: Iteration configuration with MCP tool details.

        Returns:
            Summary dict with aggregated results.
        """
        # Resolve iteration items
        try:
            items = await self._resolver.resolve(iteration_config)
        except Exception as e:
            logger.error(
                "Iteration resolution failed",
                source_id=source_id,
                error=str(e),
            )
            return {
                "success": False,
                "source_id": source_id,
                "error": f"Iteration resolution failed: {e}",
                "fetched": 0,
                "failed": 0,
                "duplicates": 0,
            }

        if not items:
            logger.warning(
                "No iteration items returned",
                source_id=source_id,
            )
            return {
                "success": True,
                "source_id": source_id,
                "fetched": 0,
                "failed": 0,
                "duplicates": 0,
            }

        concurrency = iteration_config.get("concurrency", 5)
        inject_linkage = iteration_config.get("inject_linkage", [])

        logger.info(
            "Starting iteration fetch",
            source_id=source_id,
            item_count=len(items),
            concurrency=concurrency,
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_item(item: dict[str, Any]) -> dict[str, Any]:
            """Fetch single item with semaphore."""
            async with semaphore:
                return await self._fetch_and_process_item(
                    source_id=source_id,
                    source_config=source_config,
                    pull_config=pull_config,
                    item=item,
                    inject_linkage=inject_linkage,
                )

        # Execute fetches in parallel
        results = await asyncio.gather(
            *[fetch_item(item) for item in items],
            return_exceptions=True,
        )

        # Aggregate results
        fetched = 0
        failed = 0
        duplicates = 0

        for r in results:
            if isinstance(r, Exception):
                failed += 1
            elif r.get("success"):
                fetched += 1
                if r.get("is_duplicate"):
                    duplicates += 1
            else:
                failed += 1

        success = fetched > 0

        logger.info(
            "Iteration fetch completed",
            source_id=source_id,
            fetched=fetched,
            failed=failed,
            duplicates=duplicates,
        )

        return {
            "success": success,
            "source_id": source_id,
            "fetched": fetched,
            "failed": failed,
            "duplicates": duplicates,
        }

    async def _fetch_and_process_item(
        self,
        source_id: str,
        source_config: dict[str, Any],
        pull_config: dict[str, Any],
        item: dict[str, Any],
        inject_linkage: list[str],
    ) -> dict[str, Any]:
        """Fetch and process a single iteration item.

        Args:
            source_id: Source identifier.
            source_config: Full source configuration.
            pull_config: Pull configuration for fetcher.
            item: Iteration item for URL substitution.
            inject_linkage: Fields to extract for linkage.

        Returns:
            Result dict with success status.
        """
        try:
            # Fetch with iteration item for URL substitution
            content = await self._fetcher.fetch(
                pull_config=pull_config,
                iteration_item=item,
            )

            # Extract linkage fields
            linkage = self._resolver.extract_linkage(item, inject_linkage)

            # Create job with inline content and linkage
            job = IngestionJob(
                source_id=source_id,
                content=content,
                linkage=linkage if linkage else None,
            )

            # Get processor and process through pipeline
            processor = await self._get_processor(source_config)
            result = await processor.process(job, source_config)

            is_duplicate = getattr(result, "is_duplicate", False)

            # Record metrics (AC9)
            StorageMetrics.record_pull_fetch_success(source_id)

            return {
                "success": result.success,
                "is_duplicate": is_duplicate,
            }

        except Exception as e:
            logger.warning(
                "Item fetch/process failed",
                source_id=source_id,
                item=item,
                error=str(e),
            )
            # Record failure metrics (AC9)
            StorageMetrics.record_pull_fetch_failed(source_id)

            return {
                "success": False,
                "error": str(e),
            }
