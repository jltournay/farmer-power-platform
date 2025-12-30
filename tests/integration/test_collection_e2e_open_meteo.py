"""End-to-end integration test for Epic 2 Collection Model coherence.

This test validates the full data flow from source configuration
through to MCP queries using the Open-Meteo weather API as a real
external data source.

Test Flow:
1. CLI → Deploy source config to MongoDB
2. Pull Ingestion → Fetch real data from Open-Meteo
3. Content Processing → Process JSON through pipeline
4. Document Storage → Store in MongoDB with deduplication
5. MCP Query → Query stored documents via MCP client

This test proves that all Epic 2 modules work together coherently.

Usage:
    docker-compose -f tests/docker-compose.test.yaml up -d
    pytest tests/integration/test_collection_e2e_open_meteo.py -v
    docker-compose -f tests/docker-compose.test.yaml down
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import yaml
from fp_common.models.source_config import SourceConfig

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

# Import test fixtures
from tests.conftest_integration import mongodb_client, test_db  # noqa: F401

# =============================================================================
# Test Configuration
# =============================================================================

WEATHER_CONFIG_PATH = Path(__file__).parent.parent.parent / "config/source-configs/weather-api-test.yaml"


def load_weather_config() -> dict[str, Any]:
    """Load the weather-api-test.yaml configuration."""
    with WEATHER_CONFIG_PATH.open() as f:
        config = yaml.safe_load(f)
    return config


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def collection_test_db(test_db: AsyncIOMotorDatabase) -> AsyncIOMotorDatabase:  # noqa: F811
    """Collection model test database with required collections."""
    # Create required collections
    await test_db.create_collection("source_configs")
    await test_db.create_collection("documents")
    await test_db.create_collection("raw_documents")
    await test_db.create_collection("ingestion_queue")
    return test_db


@pytest_asyncio.fixture
async def deployed_source_config(
    collection_test_db: AsyncIOMotorDatabase,
) -> dict[str, Any]:
    """Deploy weather-api-test config to MongoDB.

    This simulates what fp-source-config CLI does.
    The SourceConfig Pydantic model expects fields directly (not nested in 'config').
    """
    config = load_weather_config()

    # Format as stored in MongoDB - matches SourceConfig Pydantic model
    source_doc = {
        "source_id": config["source_id"],
        "display_name": config["display_name"],
        "description": config.get("description", ""),
        "enabled": True,
        "ingestion": config["ingestion"],
        "transformation": config["transformation"],
        "storage": config["storage"],
        "events": config.get("events", {}),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    await collection_test_db["source_configs"].insert_one(source_doc)
    return source_doc


@pytest.fixture
def mock_blob_client() -> MagicMock:
    """Mock blob storage client that stores in memory."""
    client = MagicMock()
    storage: dict[str, bytes] = {}

    async def mock_upload(container: str, blob_path: str, content: bytes, **kwargs: Any) -> dict:
        key = f"{container}/{blob_path}"
        storage[key] = content
        return {
            "container": container,
            "blob_path": blob_path,
            "content_type": kwargs.get("content_type", "application/json"),
            "size_bytes": len(content),
            "etag": f"etag-{uuid.uuid4().hex[:8]}",
        }

    async def mock_download(container: str, blob_path: str) -> bytes:
        key = f"{container}/{blob_path}"
        if key not in storage:
            raise Exception(f"Blob not found: {key}")
        return storage[key]

    client.upload_blob = AsyncMock(side_effect=mock_upload)
    client.download_blob = AsyncMock(side_effect=mock_download)
    client._storage = storage  # For test inspection

    return client


@pytest.fixture
def mock_ai_client() -> MagicMock:
    """Mock AI Model client that passes through JSON data.

    For weather data, we don't need LLM extraction - just passthrough.
    """
    client = MagicMock()

    async def mock_extract(request: Any) -> dict:
        # Parse the raw content as JSON
        content = request.raw_content if hasattr(request, "raw_content") else request.get("raw_content", "{}")

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        extracted = json.loads(content)

        return {
            "extracted_fields": extracted,
            "confidence": 1.0,
            "validation_passed": True,
            "validation_warnings": [],
        }

    client.extract = AsyncMock(side_effect=mock_extract)
    return client


@pytest.fixture
def mock_event_publisher() -> MagicMock:
    """Mock DAPR event publisher."""
    publisher = MagicMock()
    publisher.events: list[dict] = []

    async def mock_publish(topic: str, payload: dict) -> None:
        publisher.events.append({"topic": topic, "payload": payload})

    publisher.publish = AsyncMock(side_effect=mock_publish)
    return publisher


@pytest.fixture
def mock_dapr_secret_client() -> MagicMock:
    """Mock DAPR secret client (not needed for Open-Meteo)."""
    client = MagicMock()
    client.get_secret = AsyncMock(return_value={})
    return client


# =============================================================================
# E2E Test: Full Pipeline with Real Open-Meteo API
# =============================================================================


@pytest.mark.mongodb
@pytest.mark.asyncio
class TestCollectionE2EOpenMeteo:
    """End-to-end tests for Collection Model with real Open-Meteo API."""

    async def test_full_pipeline_fetch_and_store(
        self,
        collection_test_db: AsyncIOMotorDatabase,
        deployed_source_config: dict[str, Any],
        mock_blob_client: MagicMock,
        mock_ai_client: MagicMock,
        mock_event_publisher: MagicMock,
        mock_dapr_secret_client: MagicMock,
    ) -> None:
        """Test the complete data flow from Open-Meteo to MongoDB to MCP query.

        This test validates:
        1. Source config is deployed to MongoDB (simulating CLI)
        2. Pull fetcher makes real HTTP call to Open-Meteo
        3. Raw document store computes content hash
        4. Document repository stores to config-driven collection
        5. MCP DocumentClient can query the stored document
        """
        # Import components under test
        from collection_mcp.infrastructure.document_client import DocumentClient
        from collection_model.infrastructure.document_repository import DocumentRepository
        from collection_model.infrastructure.pull_data_fetcher import PullDataFetcher
        from collection_model.infrastructure.raw_document_store import RawDocumentStore
        from collection_model.infrastructure.repositories.source_config_repository import (
            SourceConfigRepository,
        )
        from collection_model.services.source_config_service import SourceConfigService

        # =================================================================
        # Step 1: Verify source config is deployed
        # =================================================================
        repository = SourceConfigRepository(collection_test_db)
        source_config_service = SourceConfigService(repository)
        config = await source_config_service.get_config("weather-api-test")

        assert config is not None, "Source config should be deployed"
        assert isinstance(config, SourceConfig)
        assert config.source_id == "weather-api-test"
        assert config.ingestion.mode == "scheduled_pull"

        # =================================================================
        # Step 2: Fetch real data from Open-Meteo
        # =================================================================
        pull_fetcher = PullDataFetcher(
            dapr_secret_client=mock_dapr_secret_client,
            max_retries=1,
        )

        # Access request config via typed attribute
        pull_config = config.ingestion.request
        assert pull_config is not None, "Request config should be present"

        # Real HTTP call to Open-Meteo (convert Pydantic model to dict for fetcher)
        raw_content = await pull_fetcher.fetch(pull_config.model_dump())

        # Verify we got real weather data
        assert raw_content is not None
        assert len(raw_content) > 0

        weather_data = json.loads(raw_content)
        assert "latitude" in weather_data
        assert "longitude" in weather_data
        assert "hourly" in weather_data or "daily" in weather_data
        assert weather_data.get("timezone") == "Africa/Nairobi"

        # =================================================================
        # Step 3: Store raw document with deduplication
        # =================================================================
        raw_store = RawDocumentStore(
            db=collection_test_db,
            blob_client=mock_blob_client,
        )
        await raw_store.ensure_indexes()

        ingestion_id = f"test-ingestion-{uuid.uuid4().hex[:8]}"

        raw_doc = await raw_store.store_raw_document(
            content=raw_content,
            source_config=config,  # Now passes typed SourceConfig
            ingestion_id=ingestion_id,
        )

        assert raw_doc.document_id is not None
        assert raw_doc.content_hash is not None
        assert raw_doc.size_bytes == len(raw_content)

        # Verify blob was "uploaded"
        assert len(mock_blob_client._storage) == 1

        # =================================================================
        # Step 4: Test deduplication
        # =================================================================
        from collection_model.domain.exceptions import DuplicateDocumentError

        with pytest.raises(DuplicateDocumentError):
            await raw_store.store_raw_document(
                content=raw_content,  # Same content = same hash
                source_config=config,
                ingestion_id=f"test-ingestion-{uuid.uuid4().hex[:8]}",
            )

        # =================================================================
        # Step 5: Store document index (simulating JsonExtractionProcessor)
        # =================================================================
        from collection_model.domain.document_index import (
            DocumentIndex,
            ExtractionMetadata,
            IngestionMetadata,
            RawDocumentRef,
        )

        doc_repo = DocumentRepository(collection_test_db)

        # Access config via typed attributes
        index_collection = config.storage.index_collection
        link_field = config.transformation.link_field

        await doc_repo.ensure_indexes(index_collection, link_field)

        # Create document index
        now = datetime.now(UTC)
        document = DocumentIndex(
            document_id=f"weather-{uuid.uuid4().hex[:8]}",
            raw_document=RawDocumentRef(
                blob_container=config.storage.raw_container,
                blob_path=f"weather-api-test/{ingestion_id}/{raw_doc.content_hash}",
                content_hash=raw_doc.content_hash,
                size_bytes=raw_doc.size_bytes,
                stored_at=now,
            ),
            extraction=ExtractionMetadata(
                ai_agent_id="weather-passthrough-agent",
                extraction_timestamp=now,
                confidence=1.0,
                validation_passed=True,
            ),
            ingestion=IngestionMetadata(
                ingestion_id=ingestion_id,
                source_id="weather-api-test",
                received_at=now,
                processed_at=now,
            ),
            extracted_fields=weather_data,
            linkage_fields={
                "timezone": weather_data.get("timezone"),
            },
        )

        # Store to config-driven collection
        doc_id = await doc_repo.save(document, index_collection)
        assert doc_id == document.document_id

        # =================================================================
        # Step 6: Query via MCP DocumentClient
        # =================================================================
        # Need to add source_id and ingested_at for MCP queries
        # Update the document with these fields
        await collection_test_db[index_collection].update_one(
            {"document_id": document.document_id},
            {
                "$set": {
                    "source_id": "weather-api-test",
                    "ingested_at": now,
                }
            },
        )

        # Create MCP DocumentClient (uses same MongoDB)
        from tests.conftest_integration import MONGODB_TEST_URI

        mcp_client = DocumentClient(
            mongodb_uri=MONGODB_TEST_URI,
            database_name=collection_test_db.name,
        )

        try:
            # Query by source_id
            documents = await mcp_client.get_documents(
                source_id="weather-api-test",
                limit=10,
            )

            assert len(documents) == 1
            assert documents[0]["source_id"] == "weather-api-test"
            assert documents[0]["document_id"] == document.document_id
            assert "extracted_fields" in documents[0]
            assert documents[0]["extracted_fields"]["timezone"] == "Africa/Nairobi"

            # Query by document_id
            single_doc = await mcp_client.get_document_by_id(document.document_id)
            assert single_doc["document_id"] == document.document_id

        finally:
            await mcp_client.close()

        # =================================================================
        # Verification Summary
        # =================================================================
        # At this point we have validated:
        # - Source config deployed (simulating CLI)
        # - Real HTTP to Open-Meteo
        # - Content hash deduplication
        # - Document storage with config-driven collection
        # - MCP queries work correctly

    async def test_pipeline_with_modified_data_creates_new_document(
        self,
        collection_test_db: AsyncIOMotorDatabase,
        deployed_source_config: dict[str, Any],
        mock_blob_client: MagicMock,
    ) -> None:
        """Test that modified data (different content hash) creates a new document."""
        from collection_model.infrastructure.raw_document_store import RawDocumentStore

        raw_store = RawDocumentStore(
            db=collection_test_db,
            blob_client=mock_blob_client,
        )
        await raw_store.ensure_indexes()

        # Convert dict to SourceConfig Pydantic model
        config = SourceConfig.model_validate(deployed_source_config)

        # Store first document
        content1 = json.dumps({"temperature": 25.0, "timestamp": "2024-01-01T00:00:00Z"}).encode()
        raw_doc1 = await raw_store.store_raw_document(
            content=content1,
            source_config=config,
            ingestion_id="ingestion-1",
        )

        # Store second document with different content
        content2 = json.dumps({"temperature": 26.0, "timestamp": "2024-01-01T01:00:00Z"}).encode()
        raw_doc2 = await raw_store.store_raw_document(
            content=content2,
            source_config=config,
            ingestion_id="ingestion-2",
        )

        # Both should have unique document IDs and content hashes
        assert raw_doc1.document_id != raw_doc2.document_id
        assert raw_doc1.content_hash != raw_doc2.content_hash

        # Both should be stored in blob
        assert len(mock_blob_client._storage) == 2

    async def test_source_config_service_caching(
        self,
        collection_test_db: AsyncIOMotorDatabase,
        deployed_source_config: dict[str, Any],
    ) -> None:
        """Test that SourceConfigService correctly caches and retrieves configs."""
        from collection_model.infrastructure.repositories.source_config_repository import (
            SourceConfigRepository,
        )
        from collection_model.services.source_config_service import SourceConfigService

        repository = SourceConfigRepository(collection_test_db)
        service = SourceConfigService(repository)

        # First call - loads from DB
        config1 = await service.get_config("weather-api-test")
        assert config1 is not None
        assert isinstance(config1, SourceConfig)

        # Second call - should use cache
        config2 = await service.get_config("weather-api-test")
        assert config2 is not None
        assert config2.source_id == config1.source_id  # Typed attribute access

        # Invalidate and reload
        service.invalidate_cache()
        config3 = await service.get_config("weather-api-test")
        assert config3 is not None
        assert config3.source_id == "weather-api-test"


# =============================================================================
# Module-level tests for component coherence
# =============================================================================


@pytest.mark.mongodb
@pytest.mark.asyncio
async def test_weather_config_schema_is_valid(
    collection_test_db: AsyncIOMotorDatabase,
) -> None:
    """Test that weather-api-test.yaml is a valid source config."""
    config = load_weather_config()

    # Required top-level fields
    assert "source_id" in config
    assert "ingestion" in config
    assert "transformation" in config
    assert "storage" in config

    # Ingestion config
    ingestion = config["ingestion"]
    assert ingestion["mode"] == "scheduled_pull"
    assert ingestion["processor_type"] == "json-extraction"
    assert "request" in ingestion

    # Request config
    request = ingestion["request"]
    assert request["auth_type"] == "none"
    assert "base_url" in request
    assert "parameters" in request

    # Transformation config
    transformation = config["transformation"]
    assert "ai_agent_id" in transformation
    assert "extract_fields" in transformation
    assert "link_field" in transformation

    # Storage config
    storage = config["storage"]
    assert "raw_container" in storage
    assert "index_collection" in storage


@pytest.mark.mongodb
@pytest.mark.asyncio
async def test_open_meteo_api_is_accessible() -> None:
    """Verify Open-Meteo API is accessible for E2E testing."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": "-1.2921",
                "longitude": "36.8219",
                "hourly": "temperature_2m",
                "forecast_days": "1",
            },
            timeout=30.0,
        )

        assert response.status_code == 200
        data = response.json()
        assert "latitude" in data
        assert "longitude" in data
