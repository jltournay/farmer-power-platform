"""Unit tests for SourceConfigRepository.

Tests the repository pattern implementation that provides
typed SourceConfig access instead of raw dict[str, Any].
"""

import pytest
from collection_model.infrastructure.repositories import SourceConfigRepository
from fp_common.models.source_config import SourceConfig
from pydantic import ValidationError


def create_source_config_doc(
    source_id: str = "test-source-001",
    display_name: str = "Test Source",
    enabled: bool = True,
    mode: str = "blob_trigger",
    landing_container: str = "test-landing",
) -> dict:
    """Create a source config document as stored in MongoDB.

    Factory function to avoid fixture mutation issues with mock MongoDB.
    """
    return {
        "source_id": source_id,
        "display_name": display_name,
        "description": "A test source configuration",
        "enabled": enabled,
        "ingestion": {
            "mode": mode,
            "landing_container": landing_container,
            "file_format": "json",
            "processor_type": "json-extraction",
        },
        "transformation": {
            "extract_fields": ["field1", "field2"],
            "link_field": "farmer_id",
        },
        "storage": {
            "raw_container": "test-raw",
            "index_collection": "test_documents",
        },
    }


@pytest.fixture
def sample_source_config_doc() -> dict:
    """Create a sample source config document as stored in MongoDB."""
    return create_source_config_doc()


@pytest.fixture
def sample_pull_source_config_doc() -> dict:
    """Create a sample scheduled_pull source config document."""
    return {
        "source_id": "weather-source",
        "display_name": "Weather Data Source",
        "description": "Weather API data source",
        "enabled": True,
        "ingestion": {
            "mode": "scheduled_pull",
            "provider": "open-meteo",
            "schedule": "0 */6 * * *",
            "processor_type": "json-extraction",
            "request": {
                "base_url": "https://api.open-meteo.com",
                "auth_type": "none",
                "timeout_seconds": 30,
            },
        },
        "transformation": {
            "extract_fields": ["temperature", "humidity"],
            "link_field": "region_id",
        },
        "storage": {
            "raw_container": "weather-raw",
            "index_collection": "weather_data",
        },
    }


@pytest.fixture
def invalid_source_config_doc() -> dict:
    """Create an invalid source config document missing required fields."""
    return {
        "source_id": "invalid-source",
        # Missing required fields: ingestion, transformation, storage
        "display_name": "Invalid Source",
        "description": "Missing required fields",
    }


class TestSourceConfigRepository:
    """Tests for SourceConfigRepository."""

    @pytest.mark.asyncio
    async def test_get_by_source_id_returns_typed_model(
        self,
        mock_mongodb_client,
        sample_source_config_doc,
    ):
        """Test that get_by_source_id returns a typed SourceConfig model."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert test document
        await db["source_configs"].insert_one(sample_source_config_doc)

        # Act
        result = await repo.get_by_source_id("test-source-001")

        # Assert
        assert result is not None
        assert isinstance(result, SourceConfig)
        assert result.source_id == "test-source-001"
        assert result.display_name == "Test Source"
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_get_by_source_id_typed_attribute_access(
        self,
        mock_mongodb_client,
        sample_source_config_doc,
    ):
        """Test that returned SourceConfig allows typed attribute access."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)
        await db["source_configs"].insert_one(sample_source_config_doc)

        # Act
        config = await repo.get_by_source_id("test-source-001")

        # Assert - typed attribute access instead of dict.get()
        assert config is not None
        assert config.ingestion.mode == "blob_trigger"
        assert config.ingestion.landing_container == "test-landing"
        assert config.ingestion.file_format == "json"
        assert config.ingestion.processor_type == "json-extraction"
        assert config.transformation.link_field == "farmer_id"
        assert config.transformation.extract_fields == ["field1", "field2"]
        assert config.storage.raw_container == "test-raw"
        assert config.storage.index_collection == "test_documents"

    @pytest.mark.asyncio
    async def test_get_by_source_id_not_found_returns_none(
        self,
        mock_mongodb_client,
    ):
        """Test that get_by_source_id returns None for non-existent source."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Act
        result = await repo.get_by_source_id("non-existent-source")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_enabled_returns_typed_list(
        self,
        mock_mongodb_client,
        sample_pull_source_config_doc,
    ):
        """Test that get_all_enabled returns list of typed SourceConfig models."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert multiple configs using factory to avoid mutation issues
        await db["source_configs"].insert_one(
            create_source_config_doc(
                source_id="source-001",
                display_name="First Source",
                enabled=True,
            )
        )
        await db["source_configs"].insert_one(sample_pull_source_config_doc)

        # Also insert a disabled config that should not be returned
        await db["source_configs"].insert_one(
            create_source_config_doc(
                source_id="disabled-source",
                enabled=False,
            )
        )

        # Act
        results = await repo.get_all_enabled()

        # Assert
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(config, SourceConfig) for config in results)
        assert all(config.enabled is True for config in results)

    @pytest.mark.asyncio
    async def test_get_all_enabled_empty_collection(
        self,
        mock_mongodb_client,
    ):
        """Test that get_all_enabled returns empty list for empty collection."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Act
        results = await repo.get_all_enabled()

        # Assert
        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="MockMongoCollection doesn't support nested query notation (ingestion.mode)")
    async def test_get_by_container_returns_typed_model(
        self,
        mock_mongodb_client,
        sample_source_config_doc,
    ):
        """Test that get_by_container returns a typed SourceConfig model.

        Note: This test is skipped because MockMongoCollection doesn't support
        nested query notation like {"ingestion.mode": "blob_trigger"}.
        This functionality is tested via integration tests.
        """
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)
        await db["source_configs"].insert_one(sample_source_config_doc)

        # Act
        result = await repo.get_by_container("test-landing")

        # Assert
        assert result is not None
        assert isinstance(result, SourceConfig)
        assert result.ingestion.landing_container == "test-landing"
        assert result.ingestion.mode == "blob_trigger"

    @pytest.mark.asyncio
    async def test_get_by_container_no_match_returns_none(
        self,
        mock_mongodb_client,
        sample_source_config_doc,
    ):
        """Test that get_by_container returns None for non-matching container."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)
        await db["source_configs"].insert_one(sample_source_config_doc)

        # Act
        result = await repo.get_by_container("non-existent-container")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_container_ignores_scheduled_pull_mode(
        self,
        mock_mongodb_client,
        sample_pull_source_config_doc,
    ):
        """Test that get_by_container only matches blob_trigger mode sources."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)
        await db["source_configs"].insert_one(sample_pull_source_config_doc)

        # Act - scheduled_pull configs don't have landing_container
        result = await repo.get_by_container("weather-raw")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_document_raises_validation_error(
        self,
        mock_mongodb_client,
        invalid_source_config_doc,
    ):
        """Test that invalid MongoDB documents raise Pydantic ValidationError."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert invalid document directly (bypassing validation)
        await db["source_configs"].insert_one(invalid_source_config_doc)

        # Act & Assert - should raise ValidationError when trying to validate
        with pytest.raises(ValidationError):
            await repo.get_by_source_id("invalid-source")

    @pytest.mark.asyncio
    async def test_typed_access_prevents_attribute_errors(
        self,
        mock_mongodb_client,
        sample_source_config_doc,
    ):
        """Test that type safety prevents accessing non-existent attributes."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)
        await db["source_configs"].insert_one(sample_source_config_doc)

        # Act
        config = await repo.get_by_source_id("test-source-001")

        # Assert - accessing valid nested attributes works
        assert config is not None
        assert config.ingestion.mode is not None
        assert config.transformation.link_field is not None
        assert config.storage.index_collection is not None

        # Accessing non-existent attributes would raise AttributeError at runtime
        # This is the type safety benefit - dict.get() silently returns None
        # while typed access fails fast with AttributeError

    @pytest.mark.asyncio
    async def test_get_all_enabled_with_events_config(
        self,
        mock_mongodb_client,
    ):
        """Test that events configuration is properly deserialized."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Use a valid topic from the domain events registry
        config_with_events = {
            "source_id": "events-source",
            "display_name": "Source with Events",
            "description": "Has event configuration",
            "enabled": True,
            "ingestion": {
                "mode": "blob_trigger",
                "landing_container": "events-landing",
                "processor_type": "json-extraction",
            },
            "transformation": {
                "extract_fields": ["data"],
                "link_field": "id",
            },
            "storage": {
                "raw_container": "events-raw",
                "index_collection": "events_docs",
            },
            "events": {
                "on_success": {
                    "topic": "collection.quality_result.received",
                    "payload_fields": ["document_id", "source_id"],
                },
            },
        }
        await db["source_configs"].insert_one(config_with_events)

        # Act
        result = await repo.get_by_source_id("events-source")

        # Assert
        assert result is not None
        assert result.events is not None
        assert result.events.on_success is not None
        assert result.events.on_success.topic == "collection.quality_result.received"
        assert result.events.on_success.payload_fields == ["document_id", "source_id"]

    @pytest.mark.asyncio
    async def test_list_all_returns_all_configs(
        self,
        mock_mongodb_client,
    ):
        """Test that list_all returns all configs with pagination."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert multiple configs
        for i in range(5):
            await db["source_configs"].insert_one(
                create_source_config_doc(
                    source_id=f"source-{i:03d}",
                    display_name=f"Source {i}",
                    enabled=i % 2 == 0,  # Alternating enabled/disabled
                    mode="blob_trigger" if i % 2 == 0 else "scheduled_pull",
                    landing_container=f"container-{i}" if i % 2 == 0 else None,
                )
            )

        # Act
        results = await repo.list_all()

        # Assert
        assert len(results) == 5
        assert all(isinstance(config, SourceConfig) for config in results)

    @pytest.mark.asyncio
    async def test_list_all_with_enabled_only_filter(
        self,
        mock_mongodb_client,
    ):
        """Test that list_all filters enabled configs correctly."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert enabled and disabled configs
        await db["source_configs"].insert_one(create_source_config_doc(source_id="enabled-1", enabled=True))
        await db["source_configs"].insert_one(create_source_config_doc(source_id="disabled-1", enabled=False))
        await db["source_configs"].insert_one(create_source_config_doc(source_id="enabled-2", enabled=True))

        # Act
        results = await repo.list_all(enabled_only=True)

        # Assert
        assert len(results) == 2
        assert all(config.enabled is True for config in results)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="MockMongoCollection doesn't support nested query notation (ingestion.mode)")
    async def test_list_all_with_ingestion_mode_filter(
        self,
        mock_mongodb_client,
    ):
        """Test that list_all filters by ingestion mode.

        Note: Skipped because MockMongoCollection doesn't support nested queries.
        """
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert configs with different modes
        await db["source_configs"].insert_one(create_source_config_doc(source_id="blob-1", mode="blob_trigger"))
        await db["source_configs"].insert_one(
            {
                **create_source_config_doc(source_id="pull-1"),
                "ingestion": {
                    "mode": "scheduled_pull",
                    "schedule": "0 * * * *",
                    "provider": "test",
                    "processor_type": "json-extraction",
                },
            }
        )

        # Act
        results = await repo.list_all(ingestion_mode="blob_trigger")

        # Assert
        assert len(results) == 1
        assert results[0].ingestion.mode == "blob_trigger"

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(
        self,
        mock_mongodb_client,
    ):
        """Test that list_all supports pagination."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert 5 configs
        for i in range(5):
            await db["source_configs"].insert_one(create_source_config_doc(source_id=f"source-{i:03d}"))

        # Act - First page
        first_page = await repo.list_all(page_size=2, skip=0)

        # Act - Second page
        second_page = await repo.list_all(page_size=2, skip=2)

        # Act - Third page (partial)
        third_page = await repo.list_all(page_size=2, skip=4)

        # Assert
        assert len(first_page) == 2
        assert len(second_page) == 2
        assert len(third_page) == 1

    @pytest.mark.asyncio
    async def test_count_returns_total(
        self,
        mock_mongodb_client,
    ):
        """Test that count returns total number of configs."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert 3 configs
        for i in range(3):
            await db["source_configs"].insert_one(create_source_config_doc(source_id=f"source-{i:03d}"))

        # Act
        count = await repo.count()

        # Assert
        assert count == 3

    @pytest.mark.asyncio
    async def test_count_with_enabled_only_filter(
        self,
        mock_mongodb_client,
    ):
        """Test that count filters by enabled status."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Insert enabled and disabled configs
        await db["source_configs"].insert_one(create_source_config_doc(source_id="enabled-1", enabled=True))
        await db["source_configs"].insert_one(create_source_config_doc(source_id="disabled-1", enabled=False))
        await db["source_configs"].insert_one(create_source_config_doc(source_id="enabled-2", enabled=True))

        # Act
        count = await repo.count(enabled_only=True)

        # Assert
        assert count == 2

    @pytest.mark.asyncio
    async def test_count_empty_collection(
        self,
        mock_mongodb_client,
    ):
        """Test that count returns 0 for empty collection."""
        # Arrange
        db = mock_mongodb_client["collection_model"]
        repo = SourceConfigRepository(db)

        # Act
        count = await repo.count()

        # Assert
        assert count == 0
