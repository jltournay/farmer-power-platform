"""Integration tests for CLI → Collection Model schema alignment (Story 2-11).

These tests verify that configs deployed via fp-source-config CLI can be
read by Collection Model's SourceConfigService using typed SourceConfig
Pydantic models.

Requires:
    - MongoDB running on localhost:27018
    - docker-compose -f tests/docker-compose.test.yaml up -d
"""

import sys
from pathlib import Path

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "source-config" / "src"))
sys.path.insert(0, str(Path(__file__).parents[2] / "services" / "collection-model" / "src"))
sys.path.insert(0, str(Path(__file__).parents[2] / "libs" / "fp-common"))

from collection_model.services.source_config_service import SourceConfigService
from fp_common.models.source_config import SourceConfig
from fp_source_config.deployer import SourceConfigDeployer

# Sample config matching E2E seed data format (flat schema)
SAMPLE_BLOB_TRIGGER_CONFIG = {
    "source_id": "integration-test-qc-json",
    "display_name": "Integration Test QC JSON",
    "description": "Integration test for CLI → Collection Model schema alignment",
    "enabled": True,
    "ingestion": {
        "mode": "blob_trigger",
        "processor_type": "json-extraction",
        "landing_container": "quality-events-integration",
        "path_pattern": {
            "pattern": "{farmer_id}/{event_id}.json",
            "extract_fields": ["farmer_id", "event_id"],
        },
    },
    "transformation": {
        "ai_agent_id": None,
        "link_field": "farmer_id",
        "extract_fields": ["farmer_id", "collection_point_id", "weight_kg", "grade"],
    },
    "storage": {
        "index_collection": "quality_documents",
        "raw_container": "raw-documents-integration",
    },
    "events": {
        "on_success": {
            "topic": "collection.quality_result.received",
        },
    },
}


SAMPLE_SCHEDULED_PULL_CONFIG = {
    "source_id": "integration-test-weather-api",
    "display_name": "Integration Test Weather API",
    "description": "Integration test for scheduled pull schema alignment",
    "enabled": True,
    "ingestion": {
        "mode": "scheduled_pull",
        "processor_type": "json-extraction",
        "request": {
            "base_url": "https://api.open-meteo.com/v1/forecast",
            "auth_type": "none",
            "parameters": {
                "latitude": "{item.weather_config.api_location.lat}",
                "longitude": "{item.weather_config.api_location.lng}",
            },
        },
        "iteration": {
            "foreach": "region",
            "source_mcp": "plantation-mcp",
            "source_tool": "list_regions",
            "concurrency": 3,
        },
    },
    "transformation": {
        "ai_agent_id": "mock-weather-extractor",
        "link_field": "region_id",
        "extract_fields": ["region_id", "temperature_c", "precipitation_mm"],
    },
    "storage": {
        "index_collection": "weather_documents",
        "raw_container": "raw-documents-integration",
    },
    "events": {
        "on_success": {
            "topic": "collection.weather.updated",
        },
    },
}


@pytest.mark.integration
@pytest.mark.mongodb
@pytest.mark.asyncio
class TestCLICollectionIntegration:
    """Integration tests for CLI → Collection Model schema compatibility (AC4)."""

    async def test_cli_deploy_collection_model_read_blob_trigger(
        self,
        test_db: AsyncIOMotorDatabase,
    ) -> None:
        """AC4: CLI deploy blob_trigger config → Collection Model reads with typed access."""
        # Step 1: Validate config with SourceConfig Pydantic model
        source_config = SourceConfig.model_validate(SAMPLE_BLOB_TRIGGER_CONFIG)
        assert source_config.source_id == "integration-test-qc-json"

        # Step 2: Deploy using CLI deployer
        deployer = SourceConfigDeployer("dev")
        deployer._db = test_db
        actions = await deployer.deploy([source_config])
        assert len(actions) == 1
        assert actions[0].action == "created"

        # Step 3: Read using Collection Model's SourceConfigService
        service = SourceConfigService(test_db)
        service.invalidate_cache()  # Ensure fresh read

        # Get all configs (simulates Collection Model startup)
        all_configs = await service.get_all_configs()
        assert len(all_configs) == 1

        # Step 4: Verify typed access works (the key requirement)
        config = all_configs[0]
        assert isinstance(config, SourceConfig), "Must return typed SourceConfig"
        assert config.source_id == "integration-test-qc-json"
        assert config.ingestion.mode == "blob_trigger"
        assert config.ingestion.processor_type == "json-extraction"
        assert config.ingestion.landing_container == "quality-events-integration"
        assert config.storage.index_collection == "quality_documents"
        assert config.transformation.link_field == "farmer_id"

    async def test_cli_deploy_collection_model_read_scheduled_pull(
        self,
        test_db: AsyncIOMotorDatabase,
    ) -> None:
        """AC4: CLI deploy scheduled_pull config → Collection Model reads with typed access."""
        # Step 1: Validate and deploy
        source_config = SourceConfig.model_validate(SAMPLE_SCHEDULED_PULL_CONFIG)
        deployer = SourceConfigDeployer("dev")
        deployer._db = test_db
        await deployer.deploy([source_config])

        # Step 2: Read using Collection Model
        service = SourceConfigService(test_db)
        service.invalidate_cache()

        config = await service.get_config("integration-test-weather-api")
        assert config is not None
        assert isinstance(config, SourceConfig)

        # Step 3: Verify typed access on nested structures
        assert config.ingestion.mode == "scheduled_pull"
        assert config.ingestion.request is not None
        assert config.ingestion.request.base_url == "https://api.open-meteo.com/v1/forecast"
        assert config.ingestion.iteration is not None
        assert config.ingestion.iteration.foreach == "region"
        assert config.ingestion.iteration.source_mcp == "plantation-mcp"

    async def test_cli_deploy_collection_model_container_lookup(
        self,
        test_db: AsyncIOMotorDatabase,
    ) -> None:
        """AC4: Collection Model's get_config_by_container works with CLI-deployed configs."""
        # Deploy config
        source_config = SourceConfig.model_validate(SAMPLE_BLOB_TRIGGER_CONFIG)
        deployer = SourceConfigDeployer("dev")
        deployer._db = test_db
        await deployer.deploy([source_config])

        # Use Collection Model's container lookup
        service = SourceConfigService(test_db)
        service.invalidate_cache()

        config = await service.get_config_by_container("quality-events-integration")
        assert config is not None
        assert config.source_id == "integration-test-qc-json"
        assert config.ingestion.landing_container == "quality-events-integration"

    async def test_cli_deploy_update_collection_model_read(
        self,
        test_db: AsyncIOMotorDatabase,
    ) -> None:
        """AC4: Updated CLI config is readable by Collection Model."""
        # Deploy initial version
        source_config = SourceConfig.model_validate(SAMPLE_BLOB_TRIGGER_CONFIG)
        deployer = SourceConfigDeployer("dev")
        deployer._db = test_db
        await deployer.deploy([source_config])

        # Update config
        updated_data = SAMPLE_BLOB_TRIGGER_CONFIG.copy()
        updated_data["storage"] = {
            "index_collection": "quality_documents_updated",
            "raw_container": "raw-documents-updated",
        }
        updated_config = SourceConfig.model_validate(updated_data)
        actions = await deployer.deploy([updated_config])
        assert actions[0].action == "updated"

        # Collection Model reads updated config
        service = SourceConfigService(test_db)
        service.invalidate_cache()

        config = await service.get_config("integration-test-qc-json")
        assert config is not None
        assert config.storage.index_collection == "quality_documents_updated"
        assert config.storage.raw_container == "raw-documents-updated"

    async def test_multiple_configs_round_trip(
        self,
        test_db: AsyncIOMotorDatabase,
    ) -> None:
        """AC4: Multiple configs deploy and read successfully."""
        # Deploy both configs
        configs = [
            SourceConfig.model_validate(SAMPLE_BLOB_TRIGGER_CONFIG),
            SourceConfig.model_validate(SAMPLE_SCHEDULED_PULL_CONFIG),
        ]
        deployer = SourceConfigDeployer("dev")
        deployer._db = test_db
        actions = await deployer.deploy(configs)
        assert len(actions) == 2
        assert all(a.action == "created" for a in actions)

        # Collection Model reads all configs
        service = SourceConfigService(test_db)
        service.invalidate_cache()

        all_configs = await service.get_all_configs()
        assert len(all_configs) == 2

        source_ids = {c.source_id for c in all_configs}
        assert "integration-test-qc-json" in source_ids
        assert "integration-test-weather-api" in source_ids

        # All configs are properly typed
        for config in all_configs:
            assert isinstance(config, SourceConfig)
            assert config.ingestion.mode in ("blob_trigger", "scheduled_pull")
