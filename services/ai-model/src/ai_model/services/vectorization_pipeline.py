"""Vectorization pipeline for RAG document processing.

This module provides the VectorizationPipeline class that orchestrates the
full vectorization flow:
1. Read un-vectorized chunks from MongoDB
2. Generate embeddings via EmbeddingService
3. Store vectors in Pinecone via PineconeVectorStore
4. Update chunk and document records in MongoDB

The pipeline supports:
- Batch processing for memory efficiency
- Partial failure handling (continues with remaining chunks)
- Progress tracking and async job support
- Namespace-based version isolation

Story 0.75.13b: RAG Vectorization Pipeline (Orchestration)
"""

import hashlib
import uuid
from datetime import UTC, datetime

import structlog
from ai_model.config import Settings
from ai_model.domain.exceptions import (
    DocumentNotFoundError,
    InvalidDocumentStatusError,
)
from ai_model.domain.rag_document import RagChunk, RagDocument, RagDocumentStatus
from ai_model.domain.vector_store import VectorMetadata, VectorUpsertRequest
from ai_model.domain.vectorization import (
    FailedChunk,
    VectorizationJob,
    VectorizationJobStatus,
    VectorizationProgress,
    VectorizationResult,
)
from ai_model.infrastructure.pinecone_vector_store import PineconeVectorStore
from ai_model.infrastructure.repositories.rag_chunk_repository import RagChunkRepository
from ai_model.infrastructure.repositories.rag_document_repository import RagDocumentRepository
from ai_model.infrastructure.repositories.vectorization_job_repository import (
    VectorizationJobRepository,
)
from ai_model.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


__all__ = [
    "VectorizationPipeline",
]


class VectorizationPipeline:
    """Orchestrates the full vectorization flow for RAG documents.

    This pipeline coordinates:
    - Reading chunks from MongoDB (via RagChunkRepository)
    - Generating embeddings (via EmbeddingService)
    - Storing vectors in Pinecone (via PineconeVectorStore)
    - Updating chunk and document records after vectorization

    The pipeline processes chunks in configurable batches (default: 50)
    and handles partial failures gracefully, continuing with remaining
    chunks when some fail.
    """

    def __init__(
        self,
        chunk_repository: RagChunkRepository,
        document_repository: RagDocumentRepository,
        embedding_service: EmbeddingService,
        vector_store: PineconeVectorStore,
        settings: Settings,
        job_repository: VectorizationJobRepository | None = None,
    ) -> None:
        """Initialize the vectorization pipeline.

        Args:
            chunk_repository: Repository for reading/updating chunks.
            document_repository: Repository for reading/updating documents.
            embedding_service: Service for generating embeddings.
            vector_store: Store for persisting vectors to Pinecone.
            settings: Service configuration (batch size, etc.).
            job_repository: Optional repository for persisting job status.
                           If None, falls back to in-memory storage.
        """
        self._chunk_repo = chunk_repository
        self._document_repo = document_repository
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._settings = settings
        self._job_repository = job_repository

        # In-memory job tracking (fallback when job_repository is None)
        # Story 0.75.13d: When job_repository is provided, this is still used
        # as a local cache for backwards compatibility and performance.
        self._jobs: dict[str, VectorizationResult] = {}

        # Log warning if using in-memory mode
        if self._job_repository is None:
            logger.warning(
                "VectorizationPipeline initialized without job repository - "
                "using in-memory job tracking. Job status will be lost on pod restart. "
                "For production, provide a VectorizationJobRepository instance."
            )

    def _generate_namespace(self, document: RagDocument) -> str:
        """Generate Pinecone namespace based on document status.

        Namespace strategy per rag-knowledge-versioning.md:
        - Active: knowledge-v{version}
        - Staged: knowledge-v{version}-staged
        - Archived: knowledge-v{version}-archived
        - Draft: Not allowed (raises error)

        Args:
            document: The document to generate namespace for.

        Returns:
            Namespace string for Pinecone.

        Raises:
            InvalidDocumentStatusError: If document is in draft status.
        """
        version = document.version
        status = document.status

        if status == RagDocumentStatus.ACTIVE:
            return f"knowledge-v{version}"
        elif status == RagDocumentStatus.STAGED:
            return f"knowledge-v{version}-staged"
        elif status == RagDocumentStatus.ARCHIVED:
            return f"knowledge-v{version}-archived"
        else:
            # Draft documents shouldn't be vectorized
            raise InvalidDocumentStatusError(
                f"Cannot vectorize document with status '{status.value}'. "
                "Document must be 'staged', 'active', or 'archived'."
            )

    def _compute_content_hash(self, chunks: list[RagChunk]) -> str:
        """Compute SHA256 hash of all chunk contents.

        Used for change detection - if content_hash matches, document
        hasn't changed and re-vectorization can be skipped.

        Args:
            chunks: List of chunks to hash (sorted by chunk_index).

        Returns:
            Hash string in format 'sha256:{hex_digest}'.
        """
        # Sort by chunk_index to ensure consistent hashing
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)
        content = "".join(chunk.content for chunk in sorted_chunks)
        digest = hashlib.sha256(content.encode()).hexdigest()
        return f"sha256:{digest}"

    def _build_vector_metadata(
        self,
        chunk: RagChunk,
        document: RagDocument,
    ) -> VectorMetadata:
        """Build VectorMetadata from chunk and document.

        Maps fields from RagChunk and RagDocument to the VectorMetadata
        schema used by Pinecone for filtering.

        Args:
            chunk: The chunk being vectorized.
            document: The parent document.

        Returns:
            VectorMetadata populated with all relevant fields.
        """
        return VectorMetadata(
            document_id=document.document_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            domain=document.domain.value,
            title=document.title,
            region=document.metadata.region,
            season=document.metadata.season,
            tags=document.metadata.tags,
        )

    def _generate_vector_id(self, document_id: str, chunk_index: int) -> str:
        """Generate a unique vector ID for Pinecone.

        Format: {document_id}-{chunk_index}

        Args:
            document_id: The stable document ID.
            chunk_index: The chunk position in document.

        Returns:
            Vector ID string.
        """
        return f"{document_id}-{chunk_index}"

    async def vectorize_document(
        self,
        document_id: str,
        document_version: int,
        request_id: str | None = None,
    ) -> VectorizationResult:
        """Vectorize a document by processing all its chunks.

        This is the main entry point for vectorization. It:
        1. Loads the document and validates status
        2. Gets all un-vectorized chunks
        3. Processes chunks in batches (embed + store)
        4. Updates chunk records with Pinecone IDs
        5. Updates document with namespace, IDs, and content hash

        Args:
            document_id: The stable document ID (e.g., "disease-diagnosis-guide").
            document_version: The version number to vectorize.
            request_id: Optional correlation ID for tracing.

        Returns:
            VectorizationResult with status and progress metrics.

        Raises:
            DocumentNotFoundError: If document doesn't exist.
            InvalidDocumentStatusError: If document is in draft status.
        """
        job_id = request_id or str(uuid.uuid4())
        started_at = datetime.now(UTC)

        logger.info(
            "Starting document vectorization",
            job_id=job_id,
            document_id=document_id,
            document_version=document_version,
        )

        # 1. Load document and validate
        document = await self._document_repo.get_by_version(document_id, document_version)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' version {document_version} not found")

        # 2. Generate namespace (validates status)
        namespace = self._generate_namespace(document)

        # 3. Get un-vectorized chunks
        chunks = await self._chunk_repo.get_chunks_without_vectors(
            document_id=document_id,
            document_version=document_version,
        )

        # If no chunks to process, return completed immediately
        if not chunks:
            logger.info(
                "No un-vectorized chunks found",
                job_id=job_id,
                document_id=document_id,
            )
            return VectorizationResult(
                job_id=job_id,
                status=VectorizationJobStatus.COMPLETED,
                document_id=document_id,
                document_version=document_version,
                namespace=namespace,
                progress=VectorizationProgress(
                    chunks_total=0,
                    chunks_embedded=0,
                    chunks_stored=0,
                    failed_count=0,
                ),
                started_at=started_at,
                completed_at=datetime.now(UTC),
            )

        # 4. Process chunks in batches
        batch_size = self._settings.vectorization_batch_size
        batches = [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]

        progress = VectorizationProgress(
            chunks_total=len(chunks),
            chunks_embedded=0,
            chunks_stored=0,
            failed_count=0,
        )

        all_pinecone_ids: list[str] = []
        failed_chunks: list[FailedChunk] = []

        logger.info(
            "Processing chunks in batches",
            job_id=job_id,
            total_chunks=len(chunks),
            batch_count=len(batches),
            batch_size=batch_size,
        )

        for batch_idx, batch in enumerate(batches):
            try:
                batch_ids = await self._process_batch(
                    batch=batch,
                    document=document,
                    namespace=namespace,
                    job_id=job_id,
                    batch_idx=batch_idx,
                )
                all_pinecone_ids.extend(batch_ids)
                progress.chunks_embedded += len(batch)
                progress.chunks_stored += len(batch)

                logger.debug(
                    "Batch processed successfully",
                    job_id=job_id,
                    batch_idx=batch_idx,
                    batch_size=len(batch),
                )

            except Exception as e:
                # Log error but continue with next batch
                logger.error(
                    "Batch processing failed",
                    job_id=job_id,
                    batch_idx=batch_idx,
                    error=str(e),
                )
                # Track individual failures
                for chunk in batch:
                    failed_chunks.append(
                        FailedChunk(
                            chunk_id=chunk.chunk_id,
                            chunk_index=chunk.chunk_index,
                            error_message=str(e),
                        )
                    )
                progress.failed_count += len(batch)
                continue

        # 5. Compute content hash
        content_hash = self._compute_content_hash(chunks)

        # 6. Update document with vectorization results
        await self._update_document_after_vectorization(
            document=document,
            namespace=namespace,
            pinecone_ids=all_pinecone_ids,
            content_hash=content_hash,
        )

        # 7. Determine final status
        completed_at = datetime.now(UTC)
        if progress.failed_count == 0:
            status = VectorizationJobStatus.COMPLETED
        elif progress.chunks_stored > 0:
            status = VectorizationJobStatus.PARTIAL
        else:
            status = VectorizationJobStatus.FAILED

        result = VectorizationResult(
            job_id=job_id,
            status=status,
            document_id=document_id,
            document_version=document_version,
            namespace=namespace,
            progress=progress,
            content_hash=content_hash,
            pinecone_ids=all_pinecone_ids,
            failed_chunks=failed_chunks,
            started_at=started_at,
            completed_at=completed_at,
        )

        # Store for async retrieval (both in-memory cache and repository)
        self._jobs[job_id] = result

        # Persist to repository if available (Story 0.75.13d)
        if self._job_repository is not None:
            try:
                await self._job_repository.update(result)
            except Exception as e:
                # Log warning - in-memory cache still has the result, but
                # job status will be lost on pod restart
                logger.warning(
                    "Failed to persist job result to repository - "
                    "job status will be lost on pod restart",
                    job_id=job_id,
                    document_id=document_id,
                    status=status.value,
                    error=str(e),
                    exc_info=True,
                )

        logger.info(
            "Document vectorization completed",
            job_id=job_id,
            status=status.value,
            chunks_stored=progress.chunks_stored,
            failed_count=progress.failed_count,
            duration_seconds=result.duration_seconds,
        )

        return result

    async def _process_batch(
        self,
        batch: list[RagChunk],
        document: RagDocument,
        namespace: str,
        job_id: str,
        batch_idx: int,
    ) -> list[str]:
        """Process a single batch of chunks.

        Steps:
        1. Extract text content for embedding
        2. Generate embeddings via EmbeddingService
        3. Build VectorUpsertRequest objects
        4. Upsert to Pinecone
        5. Update chunk records with Pinecone IDs

        Args:
            batch: List of chunks to process.
            document: Parent document for metadata.
            namespace: Target Pinecone namespace.
            job_id: Correlation ID for logging.
            batch_idx: Batch index for logging.

        Returns:
            List of Pinecone vector IDs that were stored.

        Raises:
            Exception: If embedding or upsert fails.
        """
        # 1. Extract text content
        passages = [chunk.content for chunk in batch]

        # 2. Generate embeddings
        embeddings = await self._embedding_service.embed_passages(
            passages=passages,
            request_id=f"{job_id}-batch-{batch_idx}",
            knowledge_domain=document.domain.value,
        )

        # 3. Build upsert requests
        vectors: list[VectorUpsertRequest] = []
        for chunk, embedding in zip(batch, embeddings, strict=True):
            vector_id = self._generate_vector_id(document.document_id, chunk.chunk_index)
            metadata = self._build_vector_metadata(chunk, document)
            vectors.append(
                VectorUpsertRequest(
                    id=vector_id,
                    values=embedding,
                    metadata=metadata,
                )
            )

        # 4. Upsert to Pinecone
        await self._vector_store.upsert(vectors=vectors, namespace=namespace)

        # 5. Update chunk records with Pinecone IDs
        pinecone_ids: list[str] = []
        for chunk, vector in zip(batch, vectors, strict=True):
            await self._chunk_repo.update_pinecone_id(
                chunk_id=chunk.chunk_id,
                pinecone_id=vector.id,
            )
            pinecone_ids.append(vector.id)

        return pinecone_ids

    async def _update_document_after_vectorization(
        self,
        document: RagDocument,
        namespace: str,
        pinecone_ids: list[str],
        content_hash: str,
    ) -> None:
        """Update document record after successful vectorization.

        Updates:
        - pinecone_namespace: Target namespace for vectors
        - pinecone_ids: List of all vector IDs
        - content_hash: SHA256 hash for change detection
        - updated_at: Timestamp

        Args:
            document: The document to update.
            namespace: Pinecone namespace used.
            pinecone_ids: List of stored vector IDs.
            content_hash: Computed content hash.
        """
        # Build update with new fields
        updated_document = document.model_copy(
            update={
                "pinecone_namespace": namespace,
                "pinecone_ids": pinecone_ids,
                "content_hash": content_hash,
                "updated_at": datetime.now(UTC),
            }
        )

        await self._document_repo.replace(updated_document)

        logger.debug(
            "Document updated with vectorization results",
            document_id=document.document_id,
            namespace=namespace,
            vector_count=len(pinecone_ids),
        )

    async def get_job_status(self, job_id: str) -> VectorizationResult | None:
        """Get the status of a vectorization job.

        Used for async mode to poll job completion.
        Checks in-memory cache first, then repository if available.

        Story 0.75.13d: Now supports persistent job storage via repository.

        Args:
            job_id: The job ID to query.

        Returns:
            VectorizationResult if found, None otherwise.
        """
        # Check in-memory cache first (fast path)
        if job_id in self._jobs:
            return self._jobs[job_id]

        # Check repository if available (Story 0.75.13d)
        if self._job_repository is not None:
            try:
                result = await self._job_repository.get(job_id)
                if result is not None:
                    # Cache locally for future lookups
                    self._jobs[job_id] = result
                    return result
            except Exception as e:
                logger.error(
                    "Failed to get job from repository",
                    job_id=job_id,
                    error=str(e),
                )

        return None

    async def create_job(
        self,
        document_id: str,
        document_version: int,
    ) -> VectorizationJob:
        """Create a new vectorization job (for tracking purposes).

        Used for async mode to return a job_id immediately before
        processing starts. Job is stored in self._jobs so it can be
        polled via get_job_status() before completion.

        Story 0.75.13d: Now persists to repository if available.

        Args:
            document_id: Document to vectorize.
            document_version: Version to vectorize.

        Returns:
            VectorizationJob with pending status.
        """
        job_id = str(uuid.uuid4())

        # Story 0.75.13c: Store PENDING result immediately so async jobs can be polled
        # before vectorization completes
        pending_result = VectorizationResult(
            job_id=job_id,
            status=VectorizationJobStatus.PENDING,
            document_id=document_id,
            document_version=document_version,
            namespace="",  # Not known until vectorization starts
            chunks_total=0,
            chunks_stored=0,
        )

        # Store in-memory cache
        self._jobs[job_id] = pending_result

        # Persist to repository if available (Story 0.75.13d)
        if self._job_repository is not None:
            try:
                await self._job_repository.create(pending_result)
            except Exception as e:
                # Log warning - in-memory cache still has the job, but
                # job status will be lost on pod restart
                logger.warning(
                    "Failed to persist new job to repository - "
                    "job status will be lost on pod restart",
                    job_id=job_id,
                    document_id=document_id,
                    error=str(e),
                    exc_info=True,
                )

        return VectorizationJob(
            job_id=job_id,
            status=VectorizationJobStatus.PENDING,
            document_id=document_id,
            document_version=document_version,
        )
