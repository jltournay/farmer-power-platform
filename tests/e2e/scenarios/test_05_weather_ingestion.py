"""E2E Test: Weather Data Ingestion with Real AI Extraction.

Story 0.75.18: Validates weather data ingestion via scheduled pull with real AI Model
extraction using the weather-extractor agent and Claude 3 Haiku.

This test validates the complete async event-driven flow:
1. Collection Model triggers weather pull job
2. Open-Meteo API returns real weather data
3. Collection Model publishes AgentRequestEvent to AI Model
4. AI Model executes weather-extractor workflow
5. AI Model publishes AgentCompletedEvent back
6. Collection Model updates document with extracted fields
7. Document is queryable via MCPs

Acceptance Criteria:
1. AC1: Weather Extractor Agent Configuration - agent_configs.json seeded (verified in setup)
2. AC2: Weather Pull Job Trigger - Pull job fetches real data from Open-Meteo API
3. AC3: Weather Document Creation - Weather document created with region_id linkage
4. AC4: Plantation MCP Query - get_region_weather returns weather observations
5. AC5: Collection MCP Query - get_documents returns weather document

Prerequisites:
    docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
    Wait for all services to be healthy before running tests.

Environment Variables:
    - OPENROUTER_API_KEY: Required for LLM calls (for real AI extraction)

    For local testing, set in your environment BEFORE running docker-compose:
        export OPENROUTER_API_KEY=your-key-here
        docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build

    For CI: Environment variables are passed via env: block in e2e-tests.yaml workflow.

Source Config Required:
    - e2e-weather-api: mode=scheduled_pull, ai_agent_id=weather-extractor
    - iteration: source_mcp=plantation-mcp, source_tool=list_regions
    - storage.index_collection: weather_documents

Seed Data Required:
    - source_configs.json: e2e-weather-api with ai_agent_id=weather-extractor
    - regions.json: Regions with weather_config.api_location
    - agent_configs.json: weather-extractor:1.0.0
    - prompts.json: weather-extractor:1.0.0
"""

import asyncio
import os
import time

import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# TEST CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SOURCE_ID = "e2e-weather-api"


@pytest.fixture
def openrouter_is_configured():
    """Check if OPENROUTER is configured (returns bool, does NOT skip).

    Story 0.75.18: Docker-compose reads OPENROUTER_API_KEY from shell environment.
    For local testing with openrouter, run: source .env && docker compose ...
    For CI, GitHub Actions sets env vars from secrets.

    This fixture checks ONLY the shell environment to match Docker's behavior.
    """
    return bool(os.environ.get("OPENROUTER_API_KEY"))


# ═══════════════════════════════════════════════════════════════════════════════
# POLLING HELPERS - Replace fragile asyncio.sleep with robust polling
# ═══════════════════════════════════════════════════════════════════════════════


async def wait_for_weather_documents(
    mongodb_direct,
    source_id: str,
    expected_min_count: int = 1,
    timeout: float = 90.0,  # Increased for async AI processing
    poll_interval: float = 1.0,
) -> int:
    """Wait for weather document count to reach expected minimum.

    Args:
        mongodb_direct: MongoDB direct client fixture
        source_id: Source ID to filter documents
        expected_min_count: Minimum document count to wait for
        timeout: Maximum time to wait in seconds (90s for AI processing)
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
        f"within {timeout}s (last count: {last_count}). "
        f"Check AI Model logs for extraction errors."
    )


async def wait_for_extraction_complete(
    mongodb_direct,
    source_id: str,
    timeout: float = 90.0,
    poll_interval: float = 1.0,
) -> dict:
    """Wait for at least one weather document to have extraction complete.

    Args:
        mongodb_direct: MongoDB direct client fixture
        source_id: Source ID to filter documents
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Returns:
        First document with completed extraction

    Raises:
        TimeoutError: If no document completes extraction within timeout
    """
    start = time.time()
    last_status = "unknown"
    while time.time() - start < timeout:
        documents = await mongodb_direct.find_documents(
            collection="weather_documents",
            query={"ingestion.source_id": source_id},
        )
        for doc in documents:
            extraction = doc.get("extraction", {})
            status = extraction.get("status", "unknown")
            if status == "complete":
                return doc
            last_status = status
        await asyncio.sleep(poll_interval)

    raise TimeoutError(
        f"No weather document for {source_id} reached 'complete' extraction status "
        f"within {timeout}s (last status: {last_status}). "
        f"If status is 'pending', check that OPENROUTER_API_KEY is set. "
        f"See tests/e2e/scenarios/test_05_weather_ingestion.py docstring for details."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AC1: WEATHER EXTRACTOR AGENT CONFIGURATION (Verified in Seed Data)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestWeatherExtractorConfiguration:
    """Test Weather Extractor agent configuration is seeded (AC1)."""

    @pytest.mark.asyncio
    async def test_weather_extractor_agent_config_exists(
        self,
        mongodb_direct,
        seed_data,
    ):
        """Given seed data is loaded, When I query AI Model database,
        Then weather-extractor agent config exists.
        """
        agent_config = await mongodb_direct.get_agent_config("weather-extractor")

        assert agent_config is not None, "weather-extractor agent config not found in ai_model_e2e database"
        assert agent_config["agent_id"] == "weather-extractor"
        assert agent_config["type"] == "extractor"
        assert agent_config["status"] == "active"

    @pytest.mark.asyncio
    async def test_weather_extractor_prompt_exists(
        self,
        mongodb_direct,
        seed_data,
    ):
        """Given seed data is loaded, When I query AI Model database,
        Then weather-extractor prompt exists.
        """
        prompt = await mongodb_direct.get_prompt("weather-extractor")

        assert prompt is not None, "weather-extractor prompt not found in ai_model_e2e database"
        assert prompt["prompt_id"] == "weather-extractor"
        assert prompt["agent_id"] == "weather-extractor"
        assert prompt["status"] == "active"


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
        openrouter_is_configured,
    ):
        """Given weather data is fetched and processed by AI extraction,
        When I query MongoDB, Then weather documents exist with region_id linkage.
        """
        assert openrouter_is_configured, (
            "OPENROUTER_API_KEY must be set for AI extraction tests. "
            "Set it in your shell: export OPENROUTER_API_KEY=your-key"
        )
        # Trigger pull job first
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async AI processing using polling (90s for AI extraction)
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=90.0)

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
        # Fields extracted by weather-extractor agent via LLM
        assert len(extracted) > 0, "No extracted fields in weather document"

    @pytest.mark.asyncio
    async def test_weather_document_has_weather_attributes(
        self,
        collection_api,
        mongodb_direct,
        seed_data,
        openrouter_is_configured,
    ):
        """Given weather documents exist, When I check extracted fields,
        Then weather attributes from Open-Meteo are present.
        """
        assert openrouter_is_configured, (
            "OPENROUTER_API_KEY must be set for AI extraction tests. "
            "Set it in your shell: export OPENROUTER_API_KEY=your-key"
        )
        # Trigger pull job
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for extraction to complete (not just document creation)
        # This will timeout with a helpful message if OPENROUTER_API_KEY is not set
        doc = await wait_for_extraction_complete(mongodb_direct, SOURCE_ID, timeout=90.0)

        # Check for weather-specific fields in extracted data
        extracted = doc.get("extracted_fields", {})

        # Weather extractor should return these fields based on Open-Meteo data
        weather_fields = ["observation_date", "temperature_c", "precipitation_mm", "humidity_percent"]
        found_fields = [f for f in weather_fields if f in extracted]

        assert len(found_fields) > 0, (
            f"No weather fields found. Expected some of {weather_fields}, got {list(extracted.keys())}. "
            f"Extraction status: {doc.get('extraction', {}).get('status', 'unknown')}"
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
        openrouter_is_configured,
    ):
        """Given weather documents exist for a region, When I call get_region_weather,
        Then weather observations are returned.
        """
        assert openrouter_is_configured, (
            "OPENROUTER_API_KEY must be set for AI extraction tests. "
            "Set it in your shell: export OPENROUTER_API_KEY=your-key"
        )
        # First ensure weather data exists
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async AI processing using polling
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=90.0)

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
        mongodb_direct,
        seed_data,
        openrouter_is_configured,
    ):
        """Given weather document is stored, When I query via Collection MCP,
        Then the weather document is returned with attributes.
        """
        assert openrouter_is_configured, (
            "OPENROUTER_API_KEY must be set for AI extraction tests. "
            "Set it in your shell: export OPENROUTER_API_KEY=your-key"
        )
        # Trigger pull job to create weather documents
        result = await collection_api.trigger_pull_job(SOURCE_ID)
        assert result["success"] is True, f"Pull job failed: {result.get('error')}"

        # Wait for async AI processing using polling
        await wait_for_weather_documents(mongodb_direct, SOURCE_ID, expected_min_count=1, timeout=90.0)

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
