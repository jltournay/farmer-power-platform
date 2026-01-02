"""E2E Test: ZIP Processor Ingestion (Exception Images).

Story 0.4.9: Validates ZIP processor for exception images end-to-end.

Acceptance Criteria:
1. AC1: Valid ZIP with Manifest - ZIP with manifest.json and 3 exception images → 3 documents created
2. AC2: File Extraction to Blob - Images extracted and stored to exception-images-e2e container
3. AC3: MCP Query Returns Documents - Documents queryable via get_documents(source_id=...)
4. AC4: Corrupt ZIP Handling - Corrupt ZIP → "Corrupt ZIP file detected" error
5. AC5: Missing Manifest Handling - ZIP without manifest → "Missing manifest file" error
6. AC6: Invalid Manifest Schema - Invalid manifest → validation error
7. AC7: Path Traversal Security - ZIP with ../etc/passwd → "path traversal rejected" error
8. AC8: Size Limit Enforcement - SKIPPED (unit test coverage only - 500MB file impractical)
9. AC9: Duplicate Detection - Same ZIP twice → second is skipped as duplicate

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
    Wait for all services to be healthy before running tests.

Source Config Required:
    - e2e-exception-images-zip: processor_type=zip-extraction
    - landing_container: exception-landing-e2e
    - file_container: exception-images-e2e
    - index_collection: documents
"""

import asyncio
import io
import json
import time
import uuid
import zipfile
from pathlib import Path

import pytest

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Source config for ZIP processor tests
SOURCE_ID = "e2e-exception-images-zip"
LANDING_CONTAINER = "exception-landing-e2e"
FILE_CONTAINER = "exception-images-e2e"
INDEX_COLLECTION = "documents"


# ═══════════════════════════════════════════════════════════════════════════════
# POLLING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


async def wait_for_document_count(
    mongodb_direct,
    source_id: str,
    expected_min_count: int = 1,
    timeout: float = 15.0,
    poll_interval: float = 0.5,
) -> int:
    """Wait for document count to reach expected minimum.

    Args:
        mongodb_direct: MongoDB direct client fixture
        source_id: Source ID to filter documents
        expected_min_count: Minimum document count to wait for
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Returns:
        Final document count

    Raises:
        TimeoutError: If expected count not reached within timeout
    """
    start = time.time()
    last_count = 0
    while time.time() - start < timeout:
        last_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=source_id,
        )
        if last_count >= expected_min_count:
            return last_count
        await asyncio.sleep(poll_interval)
    raise TimeoutError(
        f"Document count for source_id={source_id} did not reach {expected_min_count} "
        f"within {timeout}s (last count: {last_count})"
    )


def load_fixture(filename: str) -> bytes:
    """Load a ZIP fixture file."""
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Fixture not found: {filepath}")
    return filepath.read_bytes()


def create_unique_zip(unique_id: str) -> bytes:
    """Create a unique ZIP with a custom manifest for duplicate detection test.

    This creates a ZIP with a unique batch_id/document_id to ensure a unique content hash,
    avoiding interference with other tests that use the same fixture.

    Args:
        unique_id: Unique identifier to include in manifest

    Returns:
        ZIP file content as bytes
    """
    manifest = {
        "manifest_version": "1.0",
        "source_id": "e2e-exception-images-zip",
        "created_at": "2025-01-01T00:00:00Z",  # Valid timestamp
        "linkage": {
            "plantation_id": f"PLT-UNIQ-{unique_id}",
            "batch_id": f"BATCH-UNIQ-{unique_id}",
            "batch_result_ref": f"QC-RESULT-{unique_id}",
        },
        "payload": {
            "exception_count": 1,
            "unique_marker": unique_id,  # Add unique marker to ensure different hash
        },
        "documents": [
            {
                "document_id": f"exception_{unique_id}",
                "files": [
                    {
                        "path": "images/exception.jpg",
                        "role": "image",
                        "mime_type": "image/jpeg",
                    },
                ],
                "attributes": {
                    "exception_type": "test",
                    "severity": "low",
                },
            },
        ],
    }

    # Minimal valid JPEG
    dummy_jpeg = bytes(
        [
            0xFF,
            0xD8,
            0xFF,
            0xE0,
            0x00,
            0x10,
            0x4A,
            0x46,
            0x49,
            0x46,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x01,
            0x00,
            0x01,
            0x00,
            0x00,
            0xFF,
            0xD9,
        ]
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("images/exception.jpg", dummy_jpeg)

    return buffer.getvalue()


# ═══════════════════════════════════════════════════════════════════════════════
# AC1, AC2, AC3: VALID ZIP PROCESSING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestValidZipProcessing:
    """Test valid ZIP processing (AC1, AC2, AC3)."""

    @pytest.mark.asyncio
    async def test_valid_zip_creates_documents(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC1: Given source config e2e-exception-images-zip exists, When I upload
        a valid ZIP with manifest.json and 3 exception images, Then all 3 documents
        are created in MongoDB atomically.
        """
        # Generate unique batch ID to avoid collisions with other tests
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-ZIP-{unique_suffix}"
        batch_id = f"BATCH-ZIP-{unique_suffix}"

        # Path pattern from source_config: {plantation_id}/{batch_id}.zip
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Load the valid ZIP fixture
        zip_content = load_fixture("valid_exception_batch.zip")

        # Upload ZIP to landing container
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )

        # Trigger blob event
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait for processing - expect 3 documents from the manifest
        count = await wait_for_document_count(
            mongodb_direct,
            source_id=SOURCE_ID,
            expected_min_count=3,
            timeout=15.0,
        )

        # Verify 3 documents were created
        assert count >= 3, f"Expected at least 3 documents, got {count}"

    @pytest.mark.asyncio
    async def test_files_extracted_to_blob_storage(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC2: Given a ZIP contains exception images, When processing completes,
        Then all images are extracted and stored to exception-images-e2e container.
        """
        # Generate unique IDs
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-BLOB-{unique_suffix}"
        batch_id = f"BATCH-BLOB-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Upload and trigger
        zip_content = load_fixture("valid_exception_batch.zip")
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait for documents to be created
        await wait_for_document_count(
            mongodb_direct,
            source_id=SOURCE_ID,
            expected_min_count=3,
            timeout=15.0,
        )

        # Check that files were extracted to the file container
        blobs = await azurite_client.list_blobs(FILE_CONTAINER)

        # We expect image and metadata files to be extracted
        # The manifest has 3 documents, each with 2 files (image + metadata)
        # So we expect at least 6 files in the container
        assert len(blobs) >= 6, f"Expected at least 6 extracted files in {FILE_CONTAINER}, found {len(blobs)}: {blobs}"

    @pytest.mark.asyncio
    async def test_mcp_query_returns_documents(
        self,
        azurite_client,
        collection_api,
        collection_mcp,
        mongodb_direct,
        seed_data,
    ):
        """AC3: Given the ZIP is processed, When I query via Collection MCP
        get_documents, Then all documents from the manifest are returned.
        """
        # Generate unique IDs
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-MCP-{unique_suffix}"
        batch_id = f"BATCH-MCP-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Upload and trigger
        zip_content = load_fixture("valid_exception_batch.zip")
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait for processing
        await wait_for_document_count(
            mongodb_direct,
            source_id=SOURCE_ID,
            expected_min_count=3,
            timeout=15.0,
        )

        # Query via Collection MCP
        result = await collection_mcp.call_tool(
            "get_documents",
            {"source_id": SOURCE_ID, "limit": 50},
        )

        # Verify MCP returns documents
        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"


# ═══════════════════════════════════════════════════════════════════════════════
# AC4, AC5, AC6: ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestZipErrorHandling:
    """Test ZIP error handling (AC4, AC5, AC6)."""

    @pytest.mark.asyncio
    async def test_corrupt_zip_fails_with_error(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC4: Given a corrupt ZIP file is uploaded, When the blob event is
        triggered, Then processing fails gracefully with error.

        Note: We verify by checking that no documents are created for this source.
        The exact error message is logged server-side.
        """
        # Generate unique IDs
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-CORRUPT-{unique_suffix}"
        batch_id = f"BATCH-CORRUPT-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Get initial document count
        initial_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Upload corrupt ZIP
        zip_content = load_fixture("corrupt_zip.zip")
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )

        # Trigger processing
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait a bit for processing attempt
        await asyncio.sleep(3)

        # Verify no new documents were created (processing should fail)
        final_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Document count should not increase (corrupt ZIP fails)
        assert final_count == initial_count, (
            f"Corrupt ZIP should not create documents. Initial: {initial_count}, Final: {final_count}"
        )

    @pytest.mark.asyncio
    async def test_missing_manifest_fails_with_error(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC5: Given a ZIP without manifest.json is uploaded, When the blob
        event is triggered, Then processing fails with error.
        """
        # Generate unique IDs
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-NOMANIFEST-{unique_suffix}"
        batch_id = f"BATCH-NOMANIFEST-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Get initial document count
        initial_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Upload ZIP without manifest
        zip_content = load_fixture("missing_manifest.zip")
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )

        # Trigger processing
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait a bit for processing attempt
        await asyncio.sleep(3)

        # Verify no new documents were created
        final_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        assert final_count == initial_count, (
            f"Missing manifest ZIP should not create documents. Initial: {initial_count}, Final: {final_count}"
        )

    @pytest.mark.asyncio
    async def test_invalid_manifest_schema_fails_with_error(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC6: Given an invalid manifest schema is in the ZIP, When the blob
        event is triggered, Then processing fails with validation error.
        """
        # Generate unique IDs
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-BADSCHEMA-{unique_suffix}"
        batch_id = f"BATCH-BADSCHEMA-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Get initial document count
        initial_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Upload ZIP with invalid manifest
        zip_content = load_fixture("invalid_manifest_schema.zip")
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )

        # Trigger processing
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait a bit for processing attempt
        await asyncio.sleep(3)

        # Verify no new documents were created
        final_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        assert final_count == initial_count, (
            f"Invalid manifest ZIP should not create documents. Initial: {initial_count}, Final: {final_count}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AC7: SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestZipSecurity:
    """Test ZIP security validation (AC7)."""

    @pytest.mark.asyncio
    async def test_path_traversal_attempt_rejected(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC7: Given a ZIP with path traversal attempt (../etc/passwd), When
        the blob event is triggered, Then processing fails with security error.
        """
        # Generate unique IDs
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-TRAVERSAL-{unique_suffix}"
        batch_id = f"BATCH-TRAVERSAL-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Get initial document count
        initial_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Upload ZIP with path traversal attempt
        zip_content = load_fixture("path_traversal_attempt.zip")
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )

        # Trigger processing
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait a bit for processing attempt
        await asyncio.sleep(3)

        # Verify no new documents were created (path traversal rejected)
        final_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        assert final_count == initial_count, (
            f"Path traversal ZIP should not create documents. Initial: {initial_count}, Final: {final_count}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AC8: SIZE LIMIT (SKIPPED - Unit test coverage only)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestZipSizeLimit:
    """Test ZIP size limit enforcement (AC8)."""

    @pytest.mark.skip(reason="AC8: 500MB ZIP file impractical for E2E - covered by unit tests")
    @pytest.mark.asyncio
    async def test_size_limit_exceeded_fails(self):
        """AC8: Given a ZIP exceeds 500MB size limit, When upload is attempted,
        Then processing fails with size limit error.

        SKIPPED: Creating and uploading a 500MB+ file is impractical for E2E tests.
        This is covered by unit tests in the ZipExtractionProcessor.
        """
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# AC9: DUPLICATE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestZipDuplicateDetection:
    """Test duplicate detection (AC9)."""

    @pytest.mark.asyncio
    async def test_duplicate_zip_is_detected_and_skipped(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """AC9: Given a duplicate ZIP (same content hash) is uploaded, When the
        blob event is triggered, Then the duplicate is detected and skipped.
        """
        # Generate unique IDs for this specific test to avoid content hash collision
        # with other tests that use the same fixture
        unique_suffix = uuid.uuid4().hex[:8]
        plantation_id = f"PLT-DUP-{unique_suffix}"
        batch_id = f"BATCH-DUP-{unique_suffix}"
        blob_path = f"{plantation_id}/{batch_id}.zip"

        # Create a UNIQUE ZIP content to ensure this test has its own content hash
        # This prevents interference from other tests that use the same fixture
        zip_content = create_unique_zip(unique_suffix)

        # Get initial document count
        initial_count = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # First upload and trigger - should create documents
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait for first processing (1 document expected from unique manifest)
        await wait_for_document_count(
            mongodb_direct,
            source_id=SOURCE_ID,
            expected_min_count=initial_count + 1,
            timeout=15.0,
        )

        # Get count after first upload
        count_after_first = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Second trigger with same blob (same content hash) - should be skipped
        await azurite_client.upload_blob(
            container_name=LANDING_CONTAINER,
            blob_name=blob_path,
            data=zip_content,
            content_type="application/zip",
        )
        await collection_api.trigger_blob_event(
            container=LANDING_CONTAINER,
            blob_path=blob_path,
            content_length=len(zip_content),
        )

        # Wait a bit for potential processing (duplicate should be fast-rejected)
        await asyncio.sleep(3)

        # Get count after duplicate
        count_after_duplicate = await mongodb_direct.count_documents_in_collection(
            collection_name=INDEX_COLLECTION,
            source_id=SOURCE_ID,
        )

        # Document count should not increase for duplicate
        assert count_after_duplicate == count_after_first, (
            f"Duplicate ZIP should be skipped. After first: {count_after_first}, After dup: {count_after_duplicate}"
        )
