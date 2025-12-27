"""Unit tests for ZipExtractionProcessor (Story 2.5).

Tests cover:
- Manifest validation and parsing
- File extraction and storage
- Document creation with config-driven fields
- Atomic batch storage
- Error handling (corrupt ZIP, missing manifest, etc.)
- Event emission
"""

import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from collection_model.domain.ingestion_job import IngestionJob
from collection_model.domain.manifest import ManifestFile, ZipManifest
from collection_model.infrastructure.blob_storage import BlobReference
from collection_model.processors.registry import ProcessorRegistry
from collection_model.processors.zip_extraction import ZipExtractionProcessor


def create_test_zip(
    manifest: dict[str, Any],
    files: dict[str, bytes] | None = None,
) -> bytes:
    """Create a test ZIP file with manifest and optional files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write manifest
        zf.writestr("manifest.json", json.dumps(manifest))

        # Write additional files
        if files:
            for path, content in files.items():
                zf.writestr(path, content)

    return buffer.getvalue()


def create_sample_manifest(
    source_id: str = "qc-analyzer-exceptions",
    documents: list[dict[str, Any]] | None = None,
    linkage: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a sample manifest.json structure."""
    return {
        "manifest_version": "1.0",
        "source_id": source_id,
        "created_at": datetime.now(UTC).isoformat(),
        "linkage": linkage or {"plantation_id": "WM-4521", "batch_id": "batch-001"},
        "documents": documents
        or [
            {
                "document_id": "leaf_001",
                "files": [
                    {"path": "images/leaf_001.jpg", "role": "image", "mime_type": "image/jpeg"},
                    {"path": "metadata/leaf_001.json", "role": "metadata", "mime_type": "application/json"},
                ],
                "attributes": {"leaf_type": "two_leaves_bud", "quality_grade": "secondary"},
            }
        ],
        "payload": payload or {"grading_model_id": "tbk_kenya_tea_v1"},
    }


class TestZipManifestModel:
    """Tests for ZipManifest Pydantic model."""

    def test_valid_manifest(self) -> None:
        """Test parsing a valid manifest."""
        manifest_data = create_sample_manifest()
        manifest = ZipManifest.model_validate(manifest_data)

        assert manifest.source_id == "qc-analyzer-exceptions"
        assert manifest.manifest_version == "1.0"
        assert len(manifest.documents) == 1
        assert manifest.documents[0].document_id == "leaf_001"
        assert len(manifest.documents[0].files) == 2
        assert manifest.linkage["plantation_id"] == "WM-4521"
        assert manifest.payload["grading_model_id"] == "tbk_kenya_tea_v1"

    def test_manifest_empty_documents(self) -> None:
        """Test that manifest can have empty documents list."""
        manifest_data = {
            "manifest_version": "1.0",
            "source_id": "test",
            "created_at": datetime.now(UTC).isoformat(),
            "linkage": {},
            "documents": [],
            "payload": {},
        }
        manifest = ZipManifest.model_validate(manifest_data)
        assert len(manifest.documents) == 0

    def test_manifest_with_multiple_documents(self) -> None:
        """Test manifest with multiple documents."""
        documents = [
            {
                "document_id": "leaf_001",
                "files": [{"path": "images/leaf_001.jpg", "role": "image"}],
            },
            {
                "document_id": "leaf_002",
                "files": [{"path": "images/leaf_002.jpg", "role": "image"}],
            },
        ]
        manifest_data = create_sample_manifest(documents=documents)
        manifest = ZipManifest.model_validate(manifest_data)

        assert len(manifest.documents) == 2
        assert manifest.documents[0].document_id == "leaf_001"
        assert manifest.documents[1].document_id == "leaf_002"


class TestManifestFile:
    """Tests for ManifestFile model."""

    def test_file_with_all_fields(self) -> None:
        """Test file entry with all fields."""
        file = ManifestFile(
            path="images/leaf_001.jpg",
            role="image",
            mime_type="image/jpeg",
            size_bytes=12345,
        )
        assert file.path == "images/leaf_001.jpg"
        assert file.role == "image"
        assert file.mime_type == "image/jpeg"
        assert file.size_bytes == 12345

    def test_file_with_minimal_fields(self) -> None:
        """Test file entry with only required fields."""
        file = ManifestFile(path="data.json", role="metadata")
        assert file.path == "data.json"
        assert file.role == "metadata"
        assert file.mime_type is None
        assert file.size_bytes is None


class TestZipExtractionProcessor:
    """Tests for ZipExtractionProcessor."""

    @pytest.fixture
    def mock_blob_client(self) -> MagicMock:
        """Create mock blob client."""
        client = MagicMock()
        blob_ref = BlobReference(
            container="exception-images",
            blob_path="WM-4521/batch-001/leaf_001/leaf_001.jpg",
            content_type="image/jpeg",
            size_bytes=1000,
        )
        client.download_blob = AsyncMock()
        client.upload_blob = AsyncMock(return_value=blob_ref)
        return client

    @pytest.fixture
    def mock_raw_store(self) -> MagicMock:
        """Create mock raw document store."""
        store = MagicMock()
        mock_raw_doc = MagicMock()
        mock_raw_doc.blob_container = "exception-images-raw"
        mock_raw_doc.blob_path = "qc-analyzer-exceptions/ing-123/abc123"
        mock_raw_doc.content_hash = "abc123"
        mock_raw_doc.size_bytes = 50000
        mock_raw_doc.stored_at = datetime.now(UTC)
        store.store_raw_document = AsyncMock(return_value=mock_raw_doc)
        return store

    @pytest.fixture
    def mock_doc_repo(self) -> MagicMock:
        """Create mock document repository."""
        repo = MagicMock()
        repo.ensure_indexes = AsyncMock()
        repo.save = AsyncMock(return_value="doc-123")
        return repo

    @pytest.fixture
    def mock_event_publisher(self) -> MagicMock:
        """Create mock event publisher."""
        publisher = MagicMock()
        publisher.publish = AsyncMock(return_value=True)
        return publisher

    @pytest.fixture
    def sample_job(self) -> IngestionJob:
        """Create sample ingestion job."""
        return IngestionJob(
            ingestion_id="ing-123",
            blob_path="exceptions/WM-4521/batch-001.zip",
            blob_etag='"etag-123"',
            container="qc-analyzer-landing",
            source_id="qc-analyzer-exceptions",
            content_length=50000,
            status="queued",
            metadata={"plantation_id": "WM-4521", "batch_id": "batch-001"},
        )

    @pytest.fixture
    def sample_source_config(self) -> dict[str, Any]:
        """Create sample source configuration."""
        return {
            "source_id": "qc-analyzer-exceptions",
            "config": {
                "ingestion": {
                    "mode": "blob_trigger",
                    "processor_type": "zip-extraction",
                    "zip_config": {
                        "manifest_file": "manifest.json",
                    },
                },
                "transformation": {
                    "ai_agent_id": "qc-exception-extraction-agent",
                    "extract_fields": ["plantation_id", "batch_id"],
                    "link_field": "plantation_id",
                },
                "storage": {
                    "raw_container": "exception-images-raw",
                    "file_container": "exception-images",
                    "file_path_pattern": "{plantation_id}/{batch_id}/{doc_id}/{filename}",
                    "index_collection": "documents",
                },
                "events": {
                    "on_success": {
                        "topic": "collection.exception_images.received",
                        "payload_fields": ["plantation_id", "batch_id", "document_count"],
                    },
                },
            },
        }

    @pytest.mark.asyncio
    async def test_process_success(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test successful ZIP processing."""
        # Create test ZIP with manifest and files
        manifest = create_sample_manifest()
        files = {
            "images/leaf_001.jpg": b"fake image data",
            "metadata/leaf_001.json": b'{"quality": "good"}',
        }
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),  # Not used for ZIP
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is True
        assert result.error_message is None
        assert result.extracted_data["document_count"] == 1

        # Verify steps were called
        mock_blob_client.download_blob.assert_called_once()
        mock_raw_store.store_raw_document.assert_called_once()
        mock_doc_repo.save.assert_called_once()
        mock_event_publisher.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_corrupt_zip(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test handling of corrupt ZIP file."""
        mock_blob_client.download_blob = AsyncMock(return_value=b"not a valid zip")

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is False
        assert result.error_type == "zip_extraction"
        assert "Invalid ZIP" in result.error_message or "ZIP" in result.error_message

    @pytest.mark.asyncio
    async def test_process_missing_manifest(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test handling of ZIP without manifest.json."""
        # Create ZIP without manifest
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("images/leaf_001.jpg", b"image data")
        zip_content = buffer.getvalue()
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is False
        assert result.error_type == "zip_extraction"
        assert "manifest" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_process_invalid_manifest_json(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test handling of invalid JSON in manifest."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("manifest.json", "not valid json {")
        zip_content = buffer.getvalue()
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is False
        assert result.error_type == "zip_extraction"
        assert "JSON" in result.error_message or "manifest" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_process_missing_file_container_config(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
    ) -> None:
        """Test that missing file_container in config raises ConfigurationError."""
        bad_config = {
            "source_id": "test",
            "config": {
                "ingestion": {"zip_config": {"manifest_file": "manifest.json"}},
                "transformation": {"link_field": "id"},
                "storage": {
                    "raw_container": "raw",
                    "index_collection": "documents",
                    # Missing file_container!
                },
            },
        }

        manifest = create_sample_manifest()
        files = {"images/leaf_001.jpg": b"image data"}
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, bad_config)

        assert result.success is False
        assert result.error_type == "config"
        assert "file_container" in result.error_message

    @pytest.mark.asyncio
    async def test_process_multiple_documents(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test processing ZIP with multiple documents."""
        documents = [
            {
                "document_id": "leaf_001",
                "files": [{"path": "images/leaf_001.jpg", "role": "image"}],
                "attributes": {"quality": "good"},
            },
            {
                "document_id": "leaf_002",
                "files": [{"path": "images/leaf_002.jpg", "role": "image"}],
                "attributes": {"quality": "fair"},
            },
            {
                "document_id": "leaf_003",
                "files": [{"path": "images/leaf_003.jpg", "role": "image"}],
                "attributes": {"quality": "poor"},
            },
        ]
        manifest = create_sample_manifest(documents=documents)
        files = {
            "images/leaf_001.jpg": b"image1",
            "images/leaf_002.jpg": b"image2",
            "images/leaf_003.jpg": b"image3",
        }
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is True
        assert result.extracted_data["document_count"] == 3
        assert len(result.extracted_data["document_ids"]) == 3

        # Verify save was called 3 times (once per document)
        assert mock_doc_repo.save.call_count == 3

    @pytest.mark.asyncio
    async def test_process_file_not_in_zip(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test handling of file referenced in manifest but not in ZIP."""
        manifest = create_sample_manifest()  # References images/leaf_001.jpg
        # Don't include the referenced file
        zip_content = create_test_zip(manifest, files={})
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        assert result.success is False
        assert result.error_type == "zip_extraction"
        assert "not found" in result.error_message.lower()

    def test_supports_content_type(self) -> None:
        """Test content type support."""
        processor = ZipExtractionProcessor()

        assert processor.supports_content_type("application/zip") is True
        assert processor.supports_content_type("application/x-zip-compressed") is True
        assert processor.supports_content_type("application/x-zip") is True
        assert processor.supports_content_type("application/json") is False
        assert processor.supports_content_type("image/jpeg") is False

    def test_build_blob_path(self) -> None:
        """Test blob path building from pattern."""
        processor = ZipExtractionProcessor()

        manifest = ZipManifest.model_validate(create_sample_manifest())
        doc_entry = manifest.documents[0]
        file_entry = doc_entry.files[0]
        job = IngestionJob(
            ingestion_id="ing-123",
            blob_path="test.zip",
            blob_etag='"etag"',
            container="test",
            source_id="test",
            content_length=100,
        )
        source_config = {
            "config": {"transformation": {"link_field": "plantation_id"}},
        }

        path = processor._build_blob_path(
            pattern="{plantation_id}/{batch_id}/{doc_id}/{filename}",
            manifest=manifest,
            doc_entry=doc_entry,
            file_entry=file_entry,
            job=job,
            source_config=source_config,
        )

        assert path == "WM-4521/batch-001/leaf_001/leaf_001.jpg"

    def test_guess_mime_type(self) -> None:
        """Test MIME type guessing from filename."""
        processor = ZipExtractionProcessor()

        assert processor._guess_mime_type("image.jpg") == "image/jpeg"
        assert processor._guess_mime_type("image.jpeg") == "image/jpeg"
        assert processor._guess_mime_type("image.png") == "image/png"
        assert processor._guess_mime_type("data.json") == "application/json"
        assert processor._guess_mime_type("data.xml") == "application/xml"
        assert processor._guess_mime_type("unknown.xyz") == "application/octet-stream"
        assert processor._guess_mime_type("noextension") == "application/octet-stream"


class TestZipExtractionProcessorDeduplication:
    """Tests for ZIP processor duplicate detection (Story 2.6)."""

    @pytest.fixture
    def mock_blob_client(self) -> MagicMock:
        """Create mock blob client."""
        client = MagicMock()
        blob_ref = BlobReference(
            container="exception-images",
            blob_path="WM-4521/batch-001/leaf_001/leaf_001.jpg",
            content_type="image/jpeg",
            size_bytes=1000,
        )
        client.download_blob = AsyncMock()
        client.upload_blob = AsyncMock(return_value=blob_ref)
        return client

    @pytest.fixture
    def mock_raw_store(self) -> MagicMock:
        """Create mock raw document store."""
        store = MagicMock()
        mock_raw_doc = MagicMock()
        mock_raw_doc.blob_container = "exception-images-raw"
        mock_raw_doc.blob_path = "qc-analyzer-exceptions/ing-123/abc123"
        mock_raw_doc.content_hash = "abc123"
        mock_raw_doc.size_bytes = 50000
        mock_raw_doc.stored_at = datetime.now(UTC)
        store.store_raw_document = AsyncMock(return_value=mock_raw_doc)
        return store

    @pytest.fixture
    def mock_doc_repo(self) -> MagicMock:
        """Create mock document repository."""
        repo = MagicMock()
        repo.ensure_indexes = AsyncMock()
        repo.save = AsyncMock(return_value="doc-123")
        return repo

    @pytest.fixture
    def mock_event_publisher(self) -> MagicMock:
        """Create mock event publisher."""
        publisher = MagicMock()
        publisher.publish = AsyncMock(return_value=True)
        return publisher

    @pytest.fixture
    def sample_job(self) -> IngestionJob:
        """Create sample ingestion job."""
        return IngestionJob(
            ingestion_id="ing-123",
            blob_path="exceptions/WM-4521/batch-001.zip",
            blob_etag='"etag-123"',
            container="qc-analyzer-landing",
            source_id="qc-analyzer-exceptions",
            content_length=50000,
            status="queued",
            metadata={"plantation_id": "WM-4521", "batch_id": "batch-001"},
        )

    @pytest.fixture
    def sample_source_config(self) -> dict[str, Any]:
        """Create sample source configuration."""
        return {
            "source_id": "qc-analyzer-exceptions",
            "config": {
                "ingestion": {
                    "mode": "blob_trigger",
                    "processor_type": "zip-extraction",
                    "zip_config": {"manifest_file": "manifest.json"},
                },
                "transformation": {
                    "ai_agent_id": "qc-exception-extraction-agent",
                    "link_field": "plantation_id",
                },
                "storage": {
                    "raw_container": "exception-images-raw",
                    "file_container": "exception-images",
                    "file_path_pattern": "{plantation_id}/{batch_id}/{doc_id}/{filename}",
                    "index_collection": "documents",
                },
                "events": {
                    "on_success": {
                        "topic": "collection.exception_images.received",
                        "payload_fields": ["plantation_id", "batch_id"],
                    },
                },
            },
        }

    @pytest.mark.asyncio
    async def test_duplicate_zip_returns_is_duplicate_true(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate ZIP returns ProcessorResult with is_duplicate=True."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        # Create test ZIP
        manifest = create_sample_manifest()
        files = {"images/leaf_001.jpg": b"fake image data"}
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        # Make raw_store raise DuplicateDocumentError
        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123def456"))

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        result = await processor.process(sample_job, sample_source_config)

        # Verify duplicate handling
        assert result.success is True, "Duplicate should be a success case"
        assert result.is_duplicate is True, "is_duplicate should be True"
        assert result.error_message is None
        assert result.document_id is None

    @pytest.mark.asyncio
    async def test_duplicate_zip_does_not_emit_event(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate ZIP does not emit domain event."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        manifest = create_sample_manifest()
        files = {"images/leaf_001.jpg": b"fake image data"}
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)
        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        await processor.process(sample_job, sample_source_config)

        # Event should NOT be emitted for duplicates
        mock_event_publisher.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_zip_does_not_store_documents(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate ZIP does not store documents to index collection."""
        from collection_model.domain.exceptions import DuplicateDocumentError

        manifest = create_sample_manifest()
        files = {"images/leaf_001.jpg": b"fake image data"}
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)
        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        await processor.process(sample_job, sample_source_config)

        # Document repository save should NOT be called for duplicates
        mock_doc_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_zip_calls_storage_metrics(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that duplicate ZIP increments StorageMetrics.record_duplicate()."""
        from unittest.mock import patch

        from collection_model.domain.exceptions import DuplicateDocumentError

        manifest = create_sample_manifest()
        files = {"images/leaf_001.jpg": b"fake image data"}
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)
        mock_raw_store.store_raw_document = AsyncMock(side_effect=DuplicateDocumentError("abc123"))

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        with patch("collection_model.processors.zip_extraction.StorageMetrics") as mock_metrics:
            await processor.process(sample_job, sample_source_config)

            # Verify record_duplicate was called with correct source_id
            mock_metrics.record_duplicate.assert_called_once_with("qc-analyzer-exceptions")
            mock_metrics.record_stored.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_zip_calls_storage_metrics_stored(
        self,
        mock_blob_client: MagicMock,
        mock_raw_store: MagicMock,
        mock_doc_repo: MagicMock,
        mock_event_publisher: MagicMock,
        sample_job: IngestionJob,
        sample_source_config: dict[str, Any],
    ) -> None:
        """Test that successful ZIP processing calls StorageMetrics.record_stored()."""
        from unittest.mock import patch

        manifest = create_sample_manifest()
        files = {
            "images/leaf_001.jpg": b"fake image data",
            "metadata/leaf_001.json": b'{"quality": "good"}',
        }
        zip_content = create_test_zip(manifest, files)
        mock_blob_client.download_blob = AsyncMock(return_value=zip_content)

        processor = ZipExtractionProcessor()
        processor.set_dependencies(
            blob_client=mock_blob_client,
            raw_document_store=mock_raw_store,
            ai_model_client=MagicMock(),
            document_repository=mock_doc_repo,
            event_publisher=mock_event_publisher,
        )

        with patch("collection_model.processors.zip_extraction.StorageMetrics") as mock_metrics:
            result = await processor.process(sample_job, sample_source_config)

            assert result.success is True
            # Verify record_stored was called with correct args
            mock_metrics.record_stored.assert_called_once_with("qc-analyzer-exceptions", len(zip_content))
            mock_metrics.record_duplicate.assert_not_called()


class TestZipExtractionProcessorRegistration:
    """Test that ZipExtractionProcessor is properly registered."""

    def test_zip_extraction_registered(self) -> None:
        """Test that zip-extraction processor is registered on import."""
        # Re-register since other tests may clear the registry
        from collection_model.processors.zip_extraction import ZipExtractionProcessor

        ProcessorRegistry.register("zip-extraction", ZipExtractionProcessor)

        assert ProcessorRegistry.is_registered("zip-extraction")

        processor = ProcessorRegistry.get_processor("zip-extraction")
        assert isinstance(processor, ZipExtractionProcessor)


class TestDocumentIndexCreation:
    """Tests for DocumentIndex creation from manifest."""

    @pytest.fixture
    def processor(self) -> ZipExtractionProcessor:
        return ZipExtractionProcessor()

    def test_document_id_format(self, processor: ZipExtractionProcessor) -> None:
        """Test that document_id follows the pattern {source_id}/{link_value}/{manifest_doc_id}."""
        from collection_model.domain.document_index import RawDocumentRef

        manifest = ZipManifest.model_validate(create_sample_manifest())
        doc_entry = manifest.documents[0]
        raw_zip_ref = RawDocumentRef(
            blob_container="raw",
            blob_path="test.zip",
            content_hash="abc",
            size_bytes=100,
            stored_at=datetime.now(UTC),
        )
        job = IngestionJob(
            ingestion_id="ing-123",
            blob_path="test.zip",
            blob_etag='"etag"',
            container="test",
            source_id="qc-analyzer-exceptions",
            content_length=100,
        )
        source_config = {
            "config": {"transformation": {"link_field": "plantation_id"}},
        }

        doc = processor._create_document_index(
            doc_entry=doc_entry,
            manifest=manifest,
            file_refs={},
            raw_zip_ref=raw_zip_ref,
            job=job,
            source_config=source_config,
        )

        # Document ID should be: qc-analyzer-exceptions/WM-4521/leaf_001
        assert doc.document_id == "qc-analyzer-exceptions/WM-4521/leaf_001"

    def test_linkage_fields_copied_as_is(self, processor: ZipExtractionProcessor) -> None:
        """Test that linkage fields are copied AS-IS from manifest."""
        from collection_model.domain.document_index import RawDocumentRef

        linkage = {
            "plantation_id": "WM-4521",
            "batch_id": "batch-001",
            "custom_field": "custom_value",
        }
        manifest = ZipManifest.model_validate(create_sample_manifest(linkage=linkage))
        doc_entry = manifest.documents[0]
        raw_zip_ref = RawDocumentRef(
            blob_container="raw",
            blob_path="test.zip",
            content_hash="abc",
            size_bytes=100,
            stored_at=datetime.now(UTC),
        )
        job = IngestionJob(
            ingestion_id="ing-123",
            blob_path="test.zip",
            blob_etag='"etag"',
            container="test",
            source_id="test",
            content_length=100,
        )
        source_config = {"config": {"transformation": {"link_field": "plantation_id"}}}

        doc = processor._create_document_index(
            doc_entry=doc_entry,
            manifest=manifest,
            file_refs={},
            raw_zip_ref=raw_zip_ref,
            job=job,
            source_config=source_config,
        )

        assert doc.linkage_fields == linkage
        assert doc.linkage_fields["plantation_id"] == "WM-4521"
        assert doc.linkage_fields["custom_field"] == "custom_value"

    def test_payload_merged_into_extracted_fields(self, processor: ZipExtractionProcessor) -> None:
        """Test that manifest.payload is merged into extracted_fields."""
        from collection_model.domain.document_index import RawDocumentRef

        payload = {
            "grading_model_id": "tbk_kenya_tea_v1",
            "grading_model_version": "1.0.0",
        }
        manifest = ZipManifest.model_validate(create_sample_manifest(payload=payload))
        doc_entry = manifest.documents[0]
        raw_zip_ref = RawDocumentRef(
            blob_container="raw",
            blob_path="test.zip",
            content_hash="abc",
            size_bytes=100,
            stored_at=datetime.now(UTC),
        )
        job = IngestionJob(
            ingestion_id="ing-123",
            blob_path="test.zip",
            blob_etag='"etag"',
            container="test",
            source_id="test",
            content_length=100,
        )
        source_config = {"config": {"transformation": {"link_field": "plantation_id"}}}

        doc = processor._create_document_index(
            doc_entry=doc_entry,
            manifest=manifest,
            file_refs={},
            raw_zip_ref=raw_zip_ref,
            job=job,
            source_config=source_config,
        )

        # Payload should be merged
        assert doc.extracted_fields["grading_model_id"] == "tbk_kenya_tea_v1"
        assert doc.extracted_fields["grading_model_version"] == "1.0.0"

        # Document attributes should also be present
        assert doc.extracted_fields["leaf_type"] == "two_leaves_bud"
        assert doc.extracted_fields["quality_grade"] == "secondary"

    def test_file_refs_stored_by_role(self, processor: ZipExtractionProcessor) -> None:
        """Test that file references are stored organized by role."""
        from collection_model.domain.document_index import RawDocumentRef

        manifest = ZipManifest.model_validate(create_sample_manifest())
        doc_entry = manifest.documents[0]
        raw_zip_ref = RawDocumentRef(
            blob_container="raw",
            blob_path="test.zip",
            content_hash="abc",
            size_bytes=100,
            stored_at=datetime.now(UTC),
        )
        job = IngestionJob(
            ingestion_id="ing-123",
            blob_path="test.zip",
            blob_etag='"etag"',
            container="test",
            source_id="test",
            content_length=100,
        )
        source_config = {"config": {"transformation": {"link_field": "plantation_id"}}}

        # Create file refs by role
        image_ref = BlobReference(
            container="images",
            blob_path="leaf_001.jpg",
            content_type="image/jpeg",
            size_bytes=1000,
        )
        metadata_ref = BlobReference(
            container="images",
            blob_path="leaf_001.json",
            content_type="application/json",
            size_bytes=100,
        )
        file_refs = {
            "image": [image_ref],
            "metadata": [metadata_ref],
        }

        doc = processor._create_document_index(
            doc_entry=doc_entry,
            manifest=manifest,
            file_refs=file_refs,
            raw_zip_ref=raw_zip_ref,
            job=job,
            source_config=source_config,
        )

        # Verify file_refs are stored in extracted_fields
        assert "file_refs" in doc.extracted_fields
        assert "image" in doc.extracted_fields["file_refs"]
        assert "metadata" in doc.extracted_fields["file_refs"]
        assert len(doc.extracted_fields["file_refs"]["image"]) == 1
        assert len(doc.extracted_fields["file_refs"]["metadata"]) == 1
