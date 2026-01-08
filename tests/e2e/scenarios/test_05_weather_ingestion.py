"""E2E Test: Weather Data Ingestion with Mock AI.

Story 0.4.6: Validates weather data ingestion via scheduled pull with mock AI extraction.

SKIPPED (Story 0.75.13c): This test requires AI agent functionality (mock-weather-extractor)
that is not available in the real ai-model service. The real ai-model only provides
RAG document management and vectorization. AI agent tests will be re-enabled in
Story 0.75.18 (E2E: Weather Observation Extraction Flow) when the Extractor agent
is implemented.

Acceptance Criteria:
1. AC1: Mock AI Extractor Deployment - Mock AI server responds deterministically
2. AC2: Weather Pull Job Trigger - Pull job fetches real data from Open-Meteo API
3. AC3: Weather Document Creation - Weather document created with region_id linkage
4. AC4: Plantation MCP Query - get_region_weather returns weather observations
5. AC5: Collection MCP Query - get_documents returns weather document

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
    Wait for all services to be healthy before running tests.

Source Config Required:
    - e2e-weather-api: mode=scheduled_pull, ai_agent_id=mock-weather-extractor
    - iteration: source_mcp=plantation-mcp, source_tool=list_regions
    - storage.index_collection: weather_documents

Seed Data Required:
    - source_configs.json: e2e-weather-api
    - regions.json: Regions with weather_config.api_location
"""

import asyncio
import time

import grpc
import pytest

# Story 0.75.13c: Skip entire module - requires AI agent (mock-weather-extractor)
# not available in real ai-model service. Re-enable in Story 0.75.18.
pytestmark = pytest.mark.skip(reason="Requires AI agent functionality - Story 0.75.18 will re-enable")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SOURCE_ID = "e2e-weather-api"
MOCK_AI_MODEL_PORT = 8090  # External port mapped in docker-compose


# ═══════════════════════════════════════════════════════════════════════════════
# POLLING HELPERS - Replace fragile asyncio.sleep with robust polling
# ═══════════════════════════════════════════════════════════════════════════════


async def wait_for_weather_documents(
    mongodb_direct,
    source_id: str,
    expected_min_count: int = 1,
    timeout: float = 45.0,
    poll_interval: float = 0.5,
) -> int:
    """Wait for weather document count to reach expected minimum.

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
        documents = await mongodb_direct.find_documents(
            collection="weather_documents",
            query={"ingestion.source_id": source_id},
        )
        last_count = len(documents)
        if last_count >= expected_min_count:
            return last_count
        await asyncio.sleep(poll_interval)
    raise TimeoutError(
        f"Weather document count for {source_id} did not reach {expected_min_count} "
        f"within {timeout}s (last count: {last_count})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AC1: MOCK AI EXTRACTOR DEPLOYMENT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestMockAiExtractor:
    """Test Mock AI Extractor deployment (AC1)."""

    @pytest.mark.asyncio
    async def test_mock_ai_model_grpc_server_accessible(
        self,
        seed_data,
    ):
        """Given Mock AI Model is deployed, When I connect via gRPC,
        Then the server is accessible and ready.
        """
        # Connect to mock AI model on external port
        channel = grpc.insecure_channel(f"localhost:{MOCK_AI_MODEL_PORT}")

        # Wait for channel to be ready (with timeout)
        try:
            grpc.channel_ready_future(channel).result(timeout=10)
            connected = True
        except grpc.FutureTimeoutError:
            connected = False
        finally:
            channel.close()

        assert connected, f"Mock AI Model not accessible on port {MOCK_AI_MODEL_PORT}"

    @pytest.mark.asyncio
    async def test_mock_ai_model_health_check(
        self,
        seed_data,
    ):
        """Given Mock AI Model is deployed, When I call HealthCheck RPC,
        Then the server returns healthy status.
        """
        from fp_proto.ai_model.v1 import ai_model_pb2, ai_model_pb2_grpc

        channel = grpc.insecure_channel(f"localhost:{MOCK_AI_MODEL_PORT}")
        stub = ai_model_pb2_grpc.AiModelServiceStub(channel)

        try:
            request = ai_model_pb2.HealthCheckRequest()
            response = stub.HealthCheck(request, timeout=10)

            assert response.healthy is True
            assert response.version == "mock-1.0.0"
        finally:
            channel.close()


# ═══════════════════════════════════════════════════════════════════════════════
# AC2: WEATHER PULL JOB TRIGGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestWeatherPullJobTrigger:
    """Test weather pull job trigger (AC2)."""

    @pytest.mark.asyncio
    async def test_weather_pull_job_trigger_succeeds(
        self,
        collection_api,
        seed_data,
    ):
        """Given source config e2e-weather-api exists, When I trigger the pull job,
        Then real weather data is fetched from Open-Meteo API successfully.
        """
        # Trigger pull job for weather source
        result = await collection_api.trigger_pull_job(SOURCE_ID)

        # Pull job should succeed with at least some successful fetches
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"
        assert result["source_id"] == SOURCE_ID

        # Should have fetched data for at least one region
        fetched = result.get("fetched", 0)
        assert fetched > 0, "No weather data was fetched"


# ═══════════════════════════════════════════════════════════════════════════════
# AC3: WEATHER DOCUMENT CREATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestWeatherDocumentCreation:
    """Test weather document creation in MongoDB (AC3)."""

    @pytest.mark.asyncio
    async def test_weather_document_created_with_region_linkage(
        self,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """Given weather data is fetched and processed, When I query MongoDB,
        Then weather documents exist with region_id linkage.
        """
        # Trigger pull job first
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async processing using polling (more robust than fixed sleep)
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=45.0)

        # Query weather documents from MongoDB
        documents = await mongodb_direct.find_documents(
            collection="weather_documents",
            query={"ingestion.source_id": SOURCE_ID},
        )

        # Should have at least one weather document
        assert len(documents) > 0, "No weather documents found in MongoDB"

        # Verify first document has expected structure
        doc = documents[0]
        assert "linkage_fields" in doc
        assert "region_id" in doc["linkage_fields"], "Missing region_id in linkage"
        assert "extracted_fields" in doc

        # Verify extracted weather fields exist
        extracted = doc["extracted_fields"]
        # Fields may include: observation_date, temperature_c, precipitation_mm, etc.
        assert len(extracted) > 0, "No extracted fields in weather document"

    @pytest.mark.asyncio
    async def test_weather_document_has_weather_attributes(
        self,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """Given weather documents exist, When I check extracted fields,
        Then weather attributes from Open-Meteo are present.
        """
        # Trigger pull job
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async processing using polling
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=45.0)

        # Query weather documents
        documents = await mongodb_direct.find_documents(
            collection="weather_documents",
            query={"ingestion.source_id": SOURCE_ID},
        )

        assert len(documents) > 0, "No weather documents found"

        # Check for weather-specific fields in extracted data
        doc = documents[0]
        extracted = doc.get("extracted_fields", {})

        # Mock extractor should return these fields based on Open-Meteo data
        weather_fields = ["observation_date", "temperature_c", "precipitation_mm"]
        found_fields = [f for f in weather_fields if f in extracted]

        assert len(found_fields) > 0, (
            f"No weather fields found. Expected some of {weather_fields}, got {list(extracted.keys())}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AC4: PLANTATION MCP QUERY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestPlantationMCPWeatherQuery:
    """Test Plantation MCP weather query (AC4)."""

    @pytest.mark.asyncio
    async def test_get_region_weather_returns_observations(
        self,
        plantation_mcp,
        collection_api,
        mongodb_direct,
        seed_data,
    ):
        """Given weather documents exist for a region, When I call get_region_weather,
        Then weather observations are returned.
        """
        # First ensure weather data exists
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async processing using polling
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=45.0)

        # Get a region_id from the weather documents
        documents = await mongodb_direct.find_documents(
            collection="weather_documents",
            query={"ingestion.source_id": SOURCE_ID},
        )

        # This is a real test - must have documents from pull job
        assert len(documents) > 0, "No weather documents found - pull job must create documents for this test"

        region_id = documents[0].get("linkage_fields", {}).get("region_id")
        assert region_id is not None, "No region_id in weather document linkage - iteration must inject region_id"

        # Call Plantation MCP get_region_weather
        result = await plantation_mcp.call_tool(
            tool_name="get_region_weather",
            arguments={"region_id": region_id, "days": 7},
        )

        # Should return weather data
        assert result["success"] is True
        # Weather data structure depends on Plantation Model implementation


# ═══════════════════════════════════════════════════════════════════════════════
# AC5: COLLECTION MCP QUERY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestCollectionMCPWeatherQuery:
    """Test Collection MCP weather document query (AC5)."""

    @pytest.mark.asyncio
    async def test_get_documents_returns_weather_document(
        self,
        collection_mcp,
        collection_api,
        mongodb_direct,  # Added for polling
        seed_data,
    ):
        """Given weather document is stored, When I query via Collection MCP,
        Then the weather document is returned with attributes.
        """
        # Trigger pull job to create weather documents
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async processing using polling
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=45.0)

        # Query via Collection MCP get_documents
        result = await collection_mcp.call_tool(
            tool_name="get_documents",
            arguments={"source_id": SOURCE_ID, "limit": 10},
        )

        assert result["success"] is True, f"MCP call failed: {result.get('error_message')}"

        # Parse result
        import json

        result_data = json.loads(result.get("result_json", "{}"))
        documents = result_data.get("documents", [])

        assert len(documents) > 0, "No weather documents returned from Collection MCP"

        # Verify document has weather source_id
        doc = documents[0]
        assert doc.get("source_id") == SOURCE_ID or "weather" in str(doc).lower()
