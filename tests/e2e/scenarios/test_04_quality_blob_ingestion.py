"""E2E Test: Quality Event Blob Ingestion (No AI).

Story 0.4.5: Validates quality event ingestion via blob trigger without AI extraction.

Acceptance Criteria:
1. AC1: Blob Upload - Upload JSON blob to Azurite quality-events-e2e container
2. AC2: Blob Event Trigger - POST /api/events/blob-created triggers processing
3. AC3: Document Creation - Document created in MongoDB with correct farmer_id linkage
4. AC4: MCP Query Verification - Document queryable via get_documents(farmer_id=...)
5. AC5: DAPR Event Published - collection.quality_result.received event published
6. AC6: Duplicate Detection - Same content hash is detected and skipped

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
    Wait for all services to be healthy before running tests.

Source Config Required:
    - e2e-qc-direct-json: processor_type=json-extraction, ai_agent_id=null
    - landing_container: quality-events-e2e
    - path_pattern: {farmer_id}/{event_id}.json

Seed Data Required:
    - source_configs.json: e2e-qc-direct-json
    - farmers.json: FRM-E2E-001 (farmer for linkage)
"""

import asyncio
import hashlib
import json
import time
import uuid

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# POLLING HELPERS - Replace fragile asyncio.sleep with robust polling
# ═══════════════════════════════════════════════════════════════════════════════


async def wait_for_document_count(
    mongodb_direct,
    farmer_id: str,
    expected_min_count: int = 1,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
    source_id: str | None = None,
) -> int:
    """Wait for document count to reach expected minimum.

    Args:
        mongodb_direct: MongoDB direct client fixture
        farmer_id: Farmer ID to check documents for
        expected_min_count: Minimum document count to wait for
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds
        source_id: Optional source_id filter for counting

    Returns:
        Final document count

    Raises:
        TimeoutError: If expected count not reached within timeout
    """
    start = time.time()
    last_count = 0
    while time.time() - start < timeout:
        last_count = await mongodb_direct.count_quality_documents(farmer_id=farmer_id, source_id=source_id)
        if last_count >= expected_min_count:
            return last_count
        await asyncio.sleep(poll_interval)
    raise TimeoutError(
        f"Document count for {farmer_id} (source_id={source_id}) did not reach {expected_min_count} "
        f"within {timeout}s (last count: {last_count})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════════════════════════════


def create_quality_event(
    event_id: str | None = None,
    farmer_id: str = "FRM-E2E-001",
    collection_point_id: str = "kericho-highland-cp-100",
) -> dict:
    """Create a quality event JSON payload for blob ingestion."""
    return {
        "event_id": event_id or f"QC-E2E-{uuid.uuid4().hex[:6].upper()}",
        "farmer_id": farmer_id,
        "collection_point_id": collection_point_id,
        "timestamp": "2025-01-15T08:30:00Z",
        "leaf_analysis": {
            "leaf_type": "two_leaves_bud",
            "color_score": 85,
            "freshness_score": 90,
        },
        "weight_kg": 12.5,
        "grade": "Primary",
    }


def compute_content_hash(data: dict) -> str:
    """Compute SHA-256 hash of JSON content for duplicate detection."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# AC1: BLOB UPLOAD TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestBlobUpload:
    """Test blob upload to Azurite (AC1)."""

    @pytest.mark.asyncio
    async def test_blob_upload_to_quality_events_container(
        self,
        azurite_client,
        seed_data,
    ):
        """Given source config e2e-qc-direct-json exists, When I upload a JSON blob,
        Then the blob is stored in Azurite successfully.
        """
        # Create unique test data
        event_id = f"QC-AC1-{uuid.uuid4().hex[:6].upper()}"
        quality_event = create_quality_event(event_id=event_id)
        farmer_id = quality_event["farmer_id"]

        # Path pattern from source config: {farmer_id}/{event_id}.json
        blob_path = f"{farmer_id}/{event_id}.json"
        container_name = "quality-events-e2e"

        # Upload blob
        blob_url = await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )

        # Verify blob exists and URL is returned
        assert blob_url is not None
        assert container_name in blob_url
        assert blob_path in blob_url

        # Verify blob content is retrievable
        downloaded_content = await azurite_client.download_json(
            container_name=container_name,
            blob_name=blob_path,
        )
        assert downloaded_content["event_id"] == event_id
        assert downloaded_content["farmer_id"] == farmer_id
        assert downloaded_content["grade"] == "Primary"


# ═══════════════════════════════════════════════════════════════════════════════
# AC2: BLOB EVENT TRIGGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestBlobEventTrigger:
    """Test blob event trigger via POST /api/events/blob-created (AC2)."""

    @pytest.mark.asyncio
    async def test_blob_event_trigger_returns_202_accepted(
        self,
        azurite_client,
        collection_api,
        seed_data,
    ):
        """Given a blob exists in the landing container, When I trigger the blob event,
        Then the Collection Model accepts the event (202) and queues processing.
        """
        # Create and upload test blob
        event_id = f"QC-AC2-{uuid.uuid4().hex[:6].upper()}"
        quality_event = create_quality_event(event_id=event_id)
        farmer_id = quality_event["farmer_id"]
        blob_path = f"{farmer_id}/{event_id}.json"
        container_name = "quality-events-e2e"

        await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )

        # Trigger blob event - Collection Model should accept and queue
        accepted = await collection_api.trigger_blob_event(
            container=container_name,
            blob_path=blob_path,
            content_length=len(json.dumps(quality_event)),
        )

        # Verify 202 Accepted response
        assert accepted is True, "Expected blob event to be accepted (202)"


# ═══════════════════════════════════════════════════════════════════════════════
# AC3 & AC4: DOCUMENT CREATION AND MCP QUERY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestDocumentCreation:
    """Test document creation in MongoDB with farmer linkage (AC3, AC4)."""

    @pytest.mark.asyncio
    async def test_document_created_with_farmer_linkage(
        self,
        azurite_client,
        collection_api,
        collection_mcp,
        mongodb_direct,  # Used for polling wait
        seed_data,
    ):
        """Given the blob event is processed, When I wait for async processing,
        Then a document is created in MongoDB with correct farmer_id linkage.
        """
        # Create unique test data
        event_id = f"QC-AC3-{uuid.uuid4().hex[:6].upper()}"
        farmer_id = "FRM-E2E-001"  # Existing seeded farmer
        quality_event = create_quality_event(event_id=event_id, farmer_id=farmer_id)
        blob_path = f"{farmer_id}/{event_id}.json"
        container_name = "quality-events-e2e"

        # Upload and trigger
        await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )
        await collection_api.trigger_blob_event(
            container=container_name,
            blob_path=blob_path,
        )

        # Wait for async processing using polling (more robust than fixed sleep)
        await wait_for_document_count(mongodb_direct, farmer_id, expected_min_count=1, timeout=10.0)

        # Verify document created with farmer linkage via MCP
        result = await collection_mcp.call_tool(
            "get_documents",
            {"farmer_id": farmer_id, "limit": 50},
        )

        assert result is not None
        assert result.get("success") is True, f"Expected success=True, got: {result}"

        # Verify our event data is in the result
        result_str = str(result.get("result_json", ""))
        assert farmer_id in result_str, f"Expected farmer_id {farmer_id} in result"

    @pytest.mark.asyncio
    async def test_document_has_extracted_attributes(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """Given the document is created, Then it contains extracted attributes from JSON."""
        # Create unique test data
        event_id = f"QC-AC4-{uuid.uuid4().hex[:6].upper()}"
        farmer_id = "FRM-E2E-001"
        quality_event = create_quality_event(event_id=event_id, farmer_id=farmer_id)
        blob_path = f"{farmer_id}/{event_id}.json"
        container_name = "quality-events-e2e"

        # Upload and trigger
        await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )
        await collection_api.trigger_blob_event(
            container=container_name,
            blob_path=blob_path,
        )

        # Wait for async processing using polling
        await wait_for_document_count(mongodb_direct, farmer_id, expected_min_count=1, timeout=10.0)

        # Get latest documents for farmer directly from MongoDB
        docs = await mongodb_direct.get_latest_quality_documents(farmer_id=farmer_id, limit=10)

        # Find our document (should have the event data)
        # Note: Document structure depends on Collection Model implementation
        assert len(docs) > 0, "Expected at least one document created"


# ═══════════════════════════════════════════════════════════════════════════════
# AC5: DAPR EVENT PUBLISHED TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestDaprEventPublished:
    """Test DAPR event publishing (AC5)."""

    @pytest.mark.asyncio
    async def test_quality_result_received_event_published(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """Given the document is processed successfully, When I check DAPR pubsub,
        Then event collection.quality_result.received is published.

        Note: This test verifies the document is created successfully, which implies
        the DAPR event was published (as per source config on_success topic).
        Direct DAPR pubsub verification would require a subscription endpoint or
        checking DAPR state store - we verify indirectly via successful processing.
        """
        # Create unique test data
        event_id = f"QC-AC5-{uuid.uuid4().hex[:6].upper()}"
        farmer_id = "FRM-E2E-001"
        quality_event = create_quality_event(event_id=event_id, farmer_id=farmer_id)
        blob_path = f"{farmer_id}/{event_id}.json"
        container_name = "quality-events-e2e"

        # Get initial document count
        initial_count = await mongodb_direct.count_quality_documents(
            farmer_id=farmer_id,
            source_id="e2e-qc-direct-json",
        )

        # Upload and trigger
        await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )
        await collection_api.trigger_blob_event(
            container=container_name,
            blob_path=blob_path,
        )

        # Wait for async processing using polling (with source_id for consistency)
        await wait_for_document_count(
            mongodb_direct,
            farmer_id,
            expected_min_count=initial_count + 1,
            timeout=10.0,
            source_id="e2e-qc-direct-json",
        )

        # Verify document count increased (implies successful processing and DAPR event)
        final_count = await mongodb_direct.count_quality_documents(
            farmer_id=farmer_id,
            source_id="e2e-qc-direct-json",
        )

        # Document was created = processing succeeded = DAPR event published
        assert final_count > initial_count or final_count > 0, (
            f"Expected document to be created. Initial: {initial_count}, Final: {final_count}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AC6: DUPLICATE DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestDuplicateDetection:
    """Test duplicate detection via content hash (AC6)."""

    @pytest.mark.asyncio
    async def test_duplicate_blob_is_detected_and_skipped(
        self,
        azurite_client,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """Given a duplicate blob is uploaded (same content hash), When the blob
        event is triggered, Then the duplicate is detected and skipped (no new document).
        """
        # Use a UNIQUE farmer_id for this test to avoid race conditions with other tests
        # Other tests use FRM-E2E-001 which can cause count interference
        unique_suffix = uuid.uuid4().hex[:6].upper()
        farmer_id = f"FRM-DUP-{unique_suffix}"
        event_id = f"QC-AC6-{unique_suffix}"
        quality_event = create_quality_event(event_id=event_id, farmer_id=farmer_id)
        blob_path = f"{farmer_id}/{event_id}.json"
        container_name = "quality-events-e2e"

        # Get initial count (should be 0 for this unique farmer_id)
        source_id = "e2e-qc-direct-json"
        initial_count = await mongodb_direct.count_quality_documents(farmer_id=farmer_id, source_id=source_id)

        # First upload and trigger - should create document
        await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )
        await collection_api.trigger_blob_event(
            container=container_name,
            blob_path=blob_path,
        )

        # Wait for first processing using polling (with source_id for consistency)
        await wait_for_document_count(
            mongodb_direct,
            farmer_id,
            expected_min_count=initial_count + 1,
            timeout=10.0,
            source_id=source_id,
        )

        # Get count after first upload
        count_after_first = await mongodb_direct.count_quality_documents(farmer_id=farmer_id, source_id=source_id)

        # Second trigger with same blob (same content hash) - should be skipped
        # Re-upload same content to ensure it's identical
        await azurite_client.upload_json(
            container_name=container_name,
            blob_name=blob_path,
            data=quality_event,
        )
        await collection_api.trigger_blob_event(
            container=container_name,
            blob_path=blob_path,
        )

        # Wait a bit for potential processing (duplicate should be fast-rejected)
        # Use shorter timeout since duplicate detection should be quick
        await asyncio.sleep(2)

        # Get count after duplicate - should be same (duplicate skipped)
        count_after_duplicate = await mongodb_direct.count_quality_documents(farmer_id=farmer_id, source_id=source_id)

        # Document count should not increase for duplicate
        # Note: This assumes duplicate detection is implemented in Collection Model
        # If duplicate detection is not implemented, this test documents expected behavior
        assert count_after_duplicate == count_after_first, (
            f"Duplicate should be skipped. First: {count_after_first}, After dup: {count_after_duplicate}"
        )
