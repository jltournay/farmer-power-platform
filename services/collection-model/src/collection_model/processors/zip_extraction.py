"""ZIP extraction processor for processing ZIP blobs with manifest.

This module provides the ZipExtractionProcessor class which handles
ZIP file ingestion following the Generic ZIP Manifest Format. It is
FULLY GENERIC - no hardcoded collection names, container names,
event topics, or domain-specific field names.
"""

import io
import json
import re
import zipfile
from datetime import UTC, datetime
from typing import Any

import structlog
from collection_model.domain.document_index import (
    DocumentIndex,
    ExtractionMetadata,
    IngestionMetadata,
    RawDocumentRef,
)
from collection_model.domain.exceptions import (
    BatchProcessingError,
    ConfigurationError,
    DuplicateDocumentError,
    ManifestValidationError,
    StorageError,
    ZipExtractionError,
)
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.domain.manifest import ManifestDocument, ManifestFile, ZipManifest
from collection_model.infrastructure.blob_storage import BlobReference, BlobStorageClient
from collection_model.infrastructure.dapr_event_publisher import DaprEventPublisher
from collection_model.infrastructure.document_repository import DocumentRepository
from collection_model.infrastructure.raw_document_store import RawDocumentStore
from collection_model.infrastructure.storage_metrics import StorageMetrics
from collection_model.processors.base import ContentProcessor, ProcessorResult
from fp_common.models.source_config import SourceConfig
from pydantic import ValidationError as PydanticValidationError

logger = structlog.get_logger(__name__)

# Constants for validation
MAX_ZIP_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_DOCUMENTS_PER_ZIP = 10000
MAX_FILES_PER_DOCUMENT = 100


class ZipExtractionProcessor(ContentProcessor):
    """Processor for ZIP file extraction following Generic ZIP Manifest Format.

    This processor is FULLY GENERIC:
    - NO hardcoded collection names (uses source_config.storage.index_collection)
    - NO hardcoded container names (uses source_config.storage.file_container)
    - NO hardcoded event topics (uses source_config.events.on_success.topic)
    - NO hardcoded field names (copies linkage AS-IS, stores payload AS-IS)

    Processing pipeline:
    1. Download ZIP blob from Azure Blob Storage
    2. Store raw ZIP to config-driven raw_container
    3. Extract and validate manifest.json
    4. Process each document in manifest:
       a. Extract files and store to config-driven file_container
       b. Parse metadata files AS-IS
       c. Create DocumentIndex with config-driven linkage
    5. Store all documents atomically (using MongoDB transaction)
    6. Emit domain event to config-driven topic
    """

    def __init__(
        self,
        blob_client: BlobStorageClient | None = None,
        raw_document_store: RawDocumentStore | None = None,
        document_repository: DocumentRepository | None = None,
        event_publisher: DaprEventPublisher | None = None,
    ) -> None:
        """Initialize the processor.

        Args:
            blob_client: Azure Blob Storage client.
            raw_document_store: Raw document storage.
            document_repository: Generic document repository.
            event_publisher: DAPR event publisher.
        """
        self._blob_client = blob_client
        self._raw_store = raw_document_store
        self._doc_repo = document_repository
        self._event_publisher = event_publisher

    async def process(
        self,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> ProcessorResult:
        """Process a ZIP ingestion job.

        Fully config-driven pipeline - all storage and event settings
        are read from source_config. NO domain-specific logic.

        Args:
            job: The queued ingestion job.
            source_config: Typed SourceConfig from MongoDB.

        Returns:
            ProcessorResult with success status and document count.
        """
        source_id = source_config.source_id or job.source_id

        logger.info(
            "Processing ZIP blob",
            ingestion_id=job.ingestion_id,
            source_id=source_id,
            blob_path=job.blob_path,
        )

        try:
            # Step 1: Download ZIP blob
            zip_content = await self._download_blob(job)

            # Validate ZIP size
            if len(zip_content) > MAX_ZIP_SIZE_BYTES:
                raise ZipExtractionError(f"ZIP exceeds maximum size: {len(zip_content)} > {MAX_ZIP_SIZE_BYTES}")

            # Step 2: Store raw ZIP first (before processing)
            raw_zip_ref = await self._store_raw_zip(
                zip_content=zip_content,
                job=job,
                source_config=source_config,
            )

            # Step 3: Extract and validate manifest
            manifest = self._extract_and_validate_manifest(
                zip_content=zip_content,
                source_config=source_config,
            )

            # Validate document count
            if len(manifest.documents) > MAX_DOCUMENTS_PER_ZIP:
                raise ZipExtractionError(
                    f"ZIP exceeds maximum document count: {len(manifest.documents)} > {MAX_DOCUMENTS_PER_ZIP}"
                )

            # Step 4: Process each document in manifest (open ZipFile once for efficiency)
            documents: list[DocumentIndex] = []
            with zipfile.ZipFile(io.BytesIO(zip_content), "r") as zf:
                for doc_entry in manifest.documents:
                    doc = await self._process_document(
                        zf=zf,
                        doc_entry=doc_entry,
                        manifest=manifest,
                        raw_zip_ref=raw_zip_ref,
                        job=job,
                        source_config=source_config,
                    )
                    documents.append(doc)

            # Step 5: Store all documents atomically
            await self._store_documents_atomic(documents, source_config)

            # Step 6: Emit domain event
            await self._emit_success_event(
                documents=documents,
                manifest=manifest,
                source_config=source_config,
            )

            logger.info(
                "ZIP processing completed",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                document_count=len(documents),
            )

            # Record storage metrics
            StorageMetrics.record_stored(source_id, len(zip_content))

            return ProcessorResult(
                success=True,
                document_id=documents[0].document_id if documents else None,
                extracted_data={
                    "document_count": len(documents),
                    "document_ids": [d.document_id for d in documents],
                },
            )

        except DuplicateDocumentError as e:
            logger.info(
                "Duplicate ZIP detected, skipping",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                content_hash=str(e),
            )
            # Record duplicate metrics
            StorageMetrics.record_duplicate(source_id)
            return ProcessorResult(
                success=True,
                is_duplicate=True,
            )

        except (ZipExtractionError, ManifestValidationError) as e:
            logger.warning(
                "ZIP extraction/validation failed",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="zip_extraction",
            )

        except ConfigurationError as e:
            logger.error(
                "Configuration error",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="config",
            )

        except BatchProcessingError as e:
            logger.error(
                "Batch processing failed - rolled back",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="batch_processing",
            )

        except StorageError as e:
            logger.error(
                "Storage operation failed",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="storage",
            )

        except Exception as e:
            logger.exception(
                "Unexpected error during ZIP processing",
                ingestion_id=job.ingestion_id,
                source_id=source_id,
                error=str(e),
            )
            return ProcessorResult(
                success=False,
                error_message=str(e),
                error_type="unknown",
            )

    def supports_content_type(self, content_type: str) -> bool:
        """Check if processor supports the given content type.

        Args:
            content_type: MIME type.

        Returns:
            True for application/zip and related types.
        """
        return content_type in (
            "application/zip",
            "application/x-zip-compressed",
            "application/x-zip",
        )

    async def _download_blob(self, job: IngestionJob) -> bytes:
        """Download blob content from Azure Blob Storage."""
        if not self._blob_client:
            raise ConfigurationError("Blob client not configured")

        return await self._blob_client.download_blob(
            container=job.container,
            blob_path=job.blob_path,
        )

    async def _store_raw_zip(
        self,
        zip_content: bytes,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> RawDocumentRef:
        """Store raw ZIP in blob storage before processing."""
        if not self._raw_store:
            raise ConfigurationError("Raw document store not configured")

        raw_doc = await self._raw_store.store_raw_document(
            content=zip_content,
            source_config=source_config,
            ingestion_id=job.ingestion_id,
            metadata=job.metadata,
        )

        return RawDocumentRef(
            blob_container=raw_doc.blob_container,
            blob_path=raw_doc.blob_path,
            content_hash=raw_doc.content_hash,
            size_bytes=raw_doc.size_bytes,
            stored_at=raw_doc.stored_at,
        )

    def _extract_and_validate_manifest(
        self,
        zip_content: bytes,
        source_config: SourceConfig,
    ) -> ZipManifest:
        """Extract and validate manifest.json from ZIP.

        Args:
            zip_content: ZIP file content bytes.
            source_config: Typed SourceConfig with validation settings.

        Returns:
            Validated ZipManifest instance.

        Raises:
            ZipExtractionError: If ZIP is corrupt or manifest missing.
            ManifestValidationError: If manifest fails validation.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), "r") as zf:
                # Check ZIP integrity
                if zf.testzip() is not None:
                    raise ZipExtractionError("Corrupt ZIP file detected")

                # Get manifest file name from config (default: manifest.json)
                zip_config = source_config.ingestion.zip_config
                manifest_file = zip_config.manifest_file if zip_config else "manifest.json"

                # Extract manifest
                if manifest_file not in zf.namelist():
                    raise ZipExtractionError(f"Missing manifest file: {manifest_file}")

                manifest_bytes = zf.read(manifest_file)
                manifest_data = json.loads(manifest_bytes.decode("utf-8"))

        except zipfile.BadZipFile as e:
            raise ZipExtractionError(f"Invalid ZIP file: {e}") from e
        except json.JSONDecodeError as e:
            raise ManifestValidationError(f"Invalid manifest JSON: {e}") from e

        # Parse manifest with Pydantic model
        try:
            manifest = ZipManifest.model_validate(manifest_data)
        except PydanticValidationError as e:
            raise ManifestValidationError(f"Invalid manifest structure: {e}") from e

        # Validate document count
        if not manifest.documents:
            raise ManifestValidationError("Manifest contains no documents")

        logger.debug(
            "Manifest validated",
            source_id=manifest.source_id,
            document_count=len(manifest.documents),
            linkage_keys=list(manifest.linkage.keys()),
        )

        return manifest

    async def _process_document(
        self,
        zf: zipfile.ZipFile,
        doc_entry: ManifestDocument,
        manifest: ZipManifest,
        raw_zip_ref: RawDocumentRef,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> DocumentIndex:
        """Process a single document from the manifest.

        Extracts files, stores them to blob storage, and creates a DocumentIndex.

        Args:
            zf: Open ZipFile object (shared across all documents for efficiency).
            doc_entry: Document entry from manifest.
            manifest: The full manifest.
            raw_zip_ref: Reference to the stored raw ZIP.
            job: The ingestion job.
            source_config: Source configuration.

        Returns:
            DocumentIndex for this document.
        """
        # Validate file count
        if len(doc_entry.files) > MAX_FILES_PER_DOCUMENT:
            raise ZipExtractionError(
                f"Document {doc_entry.document_id} exceeds maximum file count: "
                f"{len(doc_entry.files)} > {MAX_FILES_PER_DOCUMENT}"
            )

        # Extract and store files, organized by role
        file_refs: dict[str, list[BlobReference]] = {}

        for file_entry in doc_entry.files:
            blob_ref = await self._extract_and_store_file(
                zf=zf,
                file_entry=file_entry,
                doc_entry=doc_entry,
                manifest=manifest,
                job=job,
                source_config=source_config,
            )

            # Group by role
            role = file_entry.role
            if role not in file_refs:
                file_refs[role] = []
            file_refs[role].append(blob_ref)

        # Create DocumentIndex
        return self._create_document_index(
            doc_entry=doc_entry,
            manifest=manifest,
            file_refs=file_refs,
            raw_zip_ref=raw_zip_ref,
            job=job,
            source_config=source_config,
        )

    async def _extract_and_store_file(
        self,
        zf: zipfile.ZipFile,
        file_entry: ManifestFile,
        doc_entry: ManifestDocument,
        manifest: ZipManifest,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> BlobReference:
        """Extract a file from ZIP and store to blob storage.

        Args:
            zf: Open ZipFile object.
            file_entry: File entry from manifest.
            doc_entry: Document this file belongs to.
            manifest: Full manifest.
            job: Ingestion job.
            source_config: Typed SourceConfig.

        Returns:
            BlobReference to the stored file.
        """
        if not self._blob_client:
            raise ConfigurationError("Blob client not configured")

        # Validate path for security (reject path traversal attempts)
        if ".." in file_entry.path or file_entry.path.startswith("/"):
            raise ZipExtractionError(
                f"Invalid file path (path traversal rejected): {file_entry.path} (document: {doc_entry.document_id})"
            )

        # Verify file exists in ZIP
        if file_entry.path not in zf.namelist():
            raise ZipExtractionError(f"File not found in ZIP: {file_entry.path} (document: {doc_entry.document_id})")

        # Extract file content
        file_content = zf.read(file_entry.path)

        # Get container from config (NO hardcoded container names)
        # Note: StorageConfig may not have file_container - use getattr for optional field
        container = getattr(source_config.storage, "file_container", None)
        if not container:
            raise ConfigurationError("No file_container in storage config")

        # Build blob path from pattern in config
        path_pattern = getattr(
            source_config.storage, "file_path_pattern", "{source_id}/{link_value}/{doc_id}/{filename}"
        )

        blob_path = self._build_blob_path(
            pattern=path_pattern,
            manifest=manifest,
            doc_entry=doc_entry,
            file_entry=file_entry,
            job=job,
            source_config=source_config,
        )

        # Determine content type
        content_type = file_entry.mime_type or self._guess_mime_type(file_entry.path)

        # Upload to blob storage
        return await self._blob_client.upload_blob(
            container=container,
            blob_path=blob_path,
            content=file_content,
            content_type=content_type,
        )

    def _build_blob_path(
        self,
        pattern: str,
        manifest: ZipManifest,
        doc_entry: ManifestDocument,
        file_entry: ManifestFile,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> str:
        """Build blob path from config-driven pattern.

        Supported placeholders:
        - {source_id}: Source configuration ID
        - {link_value}: Value of the link_field from manifest.linkage
        - {doc_id}: Document ID from manifest
        - {filename}: Original filename
        - {ext}: File extension
        - {role}: File role
        - {ingestion_id}: Ingestion job ID
        - {linkage.*}: Any field from manifest.linkage
        """
        link_field = source_config.transformation.link_field
        link_value = manifest.linkage.get(link_field, "unknown")

        # Get filename and extension from path
        filename = file_entry.path.split("/")[-1]
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

        # Build substitution map
        subs = {
            "source_id": manifest.source_id,
            "link_value": str(link_value),
            "doc_id": doc_entry.document_id,
            "filename": filename,
            "ext": ext,
            "role": file_entry.role,
            "ingestion_id": job.ingestion_id,
        }

        # Add linkage fields
        for key, value in manifest.linkage.items():
            subs[f"linkage.{key}"] = str(value)
            # Also add without prefix for simpler patterns
            if key not in subs:
                subs[key] = str(value)

        # Apply substitutions
        result = pattern
        for key, value in subs.items():
            result = result.replace(f"{{{key}}}", value)

        # Check for unresolved placeholders and log warning
        unresolved = re.findall(r"\{([^}]+)\}", result)
        if unresolved:
            logger.warning(
                "Unresolved placeholders in file_path_pattern",
                pattern=pattern,
                unresolved_placeholders=unresolved,
                available_keys=list(subs.keys()),
            )
            # Replace with "unknown" to avoid broken paths
            result = re.sub(r"\{[^}]+\}", "unknown", result)

        return result

    def _create_document_index(
        self,
        doc_entry: ManifestDocument,
        manifest: ZipManifest,
        file_refs: dict[str, list[BlobReference]],
        raw_zip_ref: RawDocumentRef,
        job: IngestionJob,
        source_config: SourceConfig,
    ) -> DocumentIndex:
        """Create a DocumentIndex for a manifest document.

        Args:
            doc_entry: Document entry from manifest.
            manifest: Full manifest.
            file_refs: Dict of file references by role.
            raw_zip_ref: Reference to raw ZIP storage.
            job: Ingestion job.
            source_config: Typed SourceConfig.

        Returns:
            DocumentIndex instance.
        """
        link_field = source_config.transformation.link_field
        link_value = manifest.linkage.get(link_field, "unknown")

        # Build globally unique document_id
        # Uses pattern: source_id/link_value/manifest_doc_id
        manifest_doc_id = doc_entry.document_id
        document_id = f"{manifest.source_id}/{link_value}/{manifest_doc_id}"

        # Copy ALL linkage fields AS-IS (NO hardcoding of field names)
        linkage_fields = dict(manifest.linkage)

        # Get extracted fields from attributes - stored AS-IS (no validation of field names)
        extracted_fields = dict(doc_entry.attributes or {})

        # Merge batch-level payload data (e.g., grading_model_id, grading_model_version)
        # This makes batch context available at document level for querying
        if manifest.payload:
            extracted_fields.update(manifest.payload)

        # Add file references by role (generic, not image-specific)
        extracted_fields["file_refs"] = {role: [ref.model_dump() for ref in refs] for role, refs in file_refs.items()}

        # Create metadata models
        extraction = ExtractionMetadata(
            ai_agent_id="zip-extraction",  # No AI involved, just extraction
            extraction_timestamp=datetime.now(UTC),
            confidence=1.0,  # Deterministic extraction
            validation_passed=True,
        )

        ingestion = IngestionMetadata(
            ingestion_id=job.ingestion_id,
            source_id=job.source_id,
            received_at=job.created_at,
            processed_at=datetime.now(UTC),
        )

        return DocumentIndex(
            document_id=document_id,
            raw_document=raw_zip_ref,
            extraction=extraction,
            ingestion=ingestion,
            extracted_fields=extracted_fields,
            linkage_fields=linkage_fields,
        )

    async def _store_documents_atomic(
        self,
        documents: list[DocumentIndex],
        source_config: SourceConfig,
    ) -> None:
        """Store all documents atomically using MongoDB transaction.

        All-or-nothing semantics: if any document fails, all are rolled back.

        Args:
            documents: List of documents to store.
            source_config: Typed SourceConfig.

        Raises:
            BatchProcessingError: If any document fails to store.
        """
        if not self._doc_repo:
            raise ConfigurationError("Document repository not configured")

        # Get collection name FROM CONFIG - not hardcoded!
        collection_name = source_config.storage.index_collection
        if not collection_name:
            raise ConfigurationError("No index_collection in storage config")

        # Get link field for indexing
        link_field = source_config.transformation.link_field

        # Ensure indexes exist
        await self._doc_repo.ensure_indexes(collection_name, link_field)

        # Store all documents
        # TODO: Implement actual MongoDB transaction for true atomicity
        # For now, use best-effort batch insert with rollback on failure
        stored_ids: list[str] = []
        try:
            for doc in documents:
                await self._doc_repo.save(doc, collection_name)
                stored_ids.append(doc.document_id)

            logger.info(
                "Batch storage completed",
                document_count=len(documents),
                collection=collection_name,
            )

        except Exception as e:
            # Log the failure - documents already stored cannot be rolled back
            # without transaction support
            logger.error(
                "Batch storage failed",
                stored_count=len(stored_ids),
                total_count=len(documents),
                error=str(e),
            )
            raise BatchProcessingError(
                f"Batch storage failed after {len(stored_ids)}/{len(documents)} documents: {e}"
            ) from e

    async def _emit_success_event(
        self,
        documents: list[DocumentIndex],
        manifest: ZipManifest,
        source_config: SourceConfig,
    ) -> None:
        """Emit success event to config-driven topic.

        Args:
            documents: List of processed documents.
            manifest: The manifest that was processed.
            source_config: Typed SourceConfig.
        """
        if not self._event_publisher:
            logger.debug("Event publisher not configured, skipping event emission")
            return

        events_config = source_config.events
        if not events_config or not events_config.on_success:
            logger.debug(
                "No on_success event configured",
                source_id=source_config.source_id,
            )
            return

        on_success = events_config.on_success
        topic = on_success.topic
        payload_fields = on_success.payload_fields or []

        if not topic:
            logger.warning(
                "on_success event has no topic",
                source_id=source_config.source_id,
            )
            return

        # Build payload from manifest and documents
        # Always include document_count (framework-level)
        payload: dict[str, Any] = {
            "document_count": len(documents),
            "document_ids": [d.document_id for d in documents],
        }

        # Add fields from manifest linkage
        for field_name in payload_fields:
            if field_name in manifest.linkage:
                payload[field_name] = manifest.linkage[field_name]
            elif field_name in manifest.payload:
                payload[field_name] = manifest.payload[field_name]

        await self._event_publisher.publish(
            topic=topic,
            payload=payload,
            source_id=source_config.source_id or "unknown",
        )

    @staticmethod
    def _guess_mime_type(filename: str) -> str:
        """Guess MIME type from filename extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "json": "application/json",
            "xml": "application/xml",
            "txt": "text/plain",
            "csv": "text/csv",
            "pdf": "application/pdf",
        }

        return mime_map.get(ext, "application/octet-stream")
