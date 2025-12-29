"""
E2E Test Configuration.

This conftest.py provides fixtures for E2E tests that run against
a fully deployed Docker Compose stack with real services.

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d

Usage:
    pytest tests/e2e/scenarios/ -v --tb=short
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from tests.e2e.helpers.mcp_clients import CollectionMCPClient, PlantationMCPClient

from tests.e2e.helpers.api_clients import CollectionClient, PlantationClient
from tests.e2e.helpers.azure_blob import AZURITE_CONNECTION_STRING, AzuriteClient
from tests.e2e.helpers.mcp_clients import PlantationServiceClient
from tests.e2e.helpers.mongodb_direct import MongoDBDirectClient

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

E2E_CONFIG = {
    "plantation_model_url": "http://localhost:8001",
    "plantation_model_grpc_host": "localhost",
    "plantation_model_grpc_port": 50051,
    "collection_model_url": "http://localhost:8002",
    "plantation_mcp_host": "localhost",
    "plantation_mcp_port": 50052,
    "collection_mcp_host": "localhost",
    "collection_mcp_port": 50053,
    "mongodb_uri": "mongodb://localhost:27017",
    "azurite_connection_string": AZURITE_CONNECTION_STRING,
    "health_check_timeout": 60,  # seconds
    "health_check_interval": 2,  # seconds
}


# ═══════════════════════════════════════════════════════════════════════════════
# PYTEST CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom pytest markers for E2E tests."""
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES - All function-scoped for clean event loop handling
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def e2e_config() -> dict[str, Any]:
    """Provide E2E configuration."""
    return E2E_CONFIG


@pytest_asyncio.fixture
async def wait_for_services(e2e_config: dict[str, Any]) -> None:
    """
    Wait for all services to be healthy before running tests.
    """
    services = [
        ("Plantation Model", f"{e2e_config['plantation_model_url']}/health"),
        ("Collection Model", f"{e2e_config['collection_model_url']}/health"),
    ]

    timeout = e2e_config["health_check_timeout"]
    interval = e2e_config["health_check_interval"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, health_url in services:
            start_time = asyncio.get_event_loop().time()
            while True:
                try:
                    response = await client.get(health_url)
                    if response.status_code == 200:
                        break
                except (httpx.ConnectError, httpx.TimeoutException):
                    pass

                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(
                        f"{service_name} did not become healthy within {timeout}s. "
                        f"Ensure Docker Compose is running: "
                        f"docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d"
                    )

                await asyncio.sleep(interval)


# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def mongodb_direct(
    e2e_config: dict[str, Any],
) -> AsyncGenerator[MongoDBDirectClient, None]:
    """Provide MongoDB direct client for verification."""
    async with MongoDBDirectClient(e2e_config["mongodb_uri"]) as client:
        yield client


@pytest_asyncio.fixture
async def azurite_client(
    e2e_config: dict[str, Any],
) -> AsyncGenerator[AzuriteClient, None]:
    """Provide Azurite client for blob operations."""
    async with AzuriteClient(e2e_config["azurite_connection_string"]) as client:
        yield client


@pytest_asyncio.fixture
async def plantation_api(
    e2e_config: dict[str, Any],
    wait_for_services: None,
) -> AsyncGenerator[PlantationClient, None]:
    """Provide Plantation Model API client."""
    async with PlantationClient(e2e_config["plantation_model_url"]) as client:
        yield client


@pytest_asyncio.fixture
async def collection_api(
    e2e_config: dict[str, Any],
    wait_for_services: None,
) -> AsyncGenerator[CollectionClient, None]:
    """Provide Collection Model API client."""
    async with CollectionClient(e2e_config["collection_model_url"]) as client:
        yield client


@pytest_asyncio.fixture
async def plantation_service(
    e2e_config: dict[str, Any],
    wait_for_services: None,
) -> AsyncGenerator[PlantationServiceClient, None]:
    """Provide Plantation Model gRPC client for write operations."""
    async with PlantationServiceClient(
        host=e2e_config["plantation_model_grpc_host"],
        port=e2e_config["plantation_model_grpc_port"],
    ) as client:
        yield client


# ═══════════════════════════════════════════════════════════════════════════════
# MCP CLIENT FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def plantation_mcp(
    e2e_config: dict[str, Any],
    wait_for_services: None,
) -> AsyncGenerator[PlantationMCPClient, None]:
    """Provide Plantation MCP client."""
    # Import here to avoid import errors if grpcio not installed
    from tests.e2e.helpers.mcp_clients import PlantationMCPClient

    async with PlantationMCPClient(
        host=e2e_config["plantation_mcp_host"],
        port=e2e_config["plantation_mcp_port"],
    ) as client:
        yield client


@pytest_asyncio.fixture
async def collection_mcp(
    e2e_config: dict[str, Any],
    wait_for_services: None,
) -> AsyncGenerator[CollectionMCPClient, None]:
    """Provide Collection MCP client."""
    from tests.e2e.helpers.mcp_clients import CollectionMCPClient

    async with CollectionMCPClient(
        host=e2e_config["collection_mcp_host"],
        port=e2e_config["collection_mcp_port"],
    ) as client:
        yield client


# ═══════════════════════════════════════════════════════════════════════════════
# SEED DATA FIXTURE
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def seed_data(
    wait_for_services: None,
    mongodb_direct: MongoDBDirectClient,
    azurite_client: AzuriteClient,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Seed initial data for E2E tests.

    This fixture loads seed data from JSON files and populates
    the databases before tests run.
    """
    seed_dir = Path(__file__).parent / "infrastructure" / "seed"

    seeded_data: dict[str, Any] = {
        "grading_models": [],
        "regions": [],
        "source_configs": [],
        "factories": [],
        "collection_points": [],
        "farmers": [],
        "farmer_performance": [],
        "weather_observations": [],
        "documents": [],
        "document_blobs": [],
    }

    # Load and seed grading models
    grading_models_file = seed_dir / "grading_models.json"
    if grading_models_file.exists():
        grading_models = json.loads(grading_models_file.read_text())
        await mongodb_direct.seed_grading_models(grading_models)
        seeded_data["grading_models"] = grading_models

    # Load and seed regions
    regions_file = seed_dir / "regions.json"
    if regions_file.exists():
        regions = json.loads(regions_file.read_text())
        await mongodb_direct.seed_regions(regions)
        seeded_data["regions"] = regions

    # Load and seed source configs (required for Collection Model ingestion)
    source_configs_file = seed_dir / "source_configs.json"
    if source_configs_file.exists():
        source_configs = json.loads(source_configs_file.read_text())
        await mongodb_direct.seed_source_configs(source_configs)
        seeded_data["source_configs"] = source_configs

    # Load and seed factories
    factories_file = seed_dir / "factories.json"
    if factories_file.exists():
        factories = json.loads(factories_file.read_text())
        await mongodb_direct.seed_factories(factories)
        seeded_data["factories"] = factories

    # Load and seed collection points
    collection_points_file = seed_dir / "collection_points.json"
    if collection_points_file.exists():
        collection_points = json.loads(collection_points_file.read_text())
        await mongodb_direct.seed_collection_points(collection_points)
        seeded_data["collection_points"] = collection_points

    # Load and seed farmers
    farmers_file = seed_dir / "farmers.json"
    if farmers_file.exists():
        farmers = json.loads(farmers_file.read_text())
        await mongodb_direct.seed_farmers(farmers)
        seeded_data["farmers"] = farmers

    # Load and seed farmer performance data
    farmer_performance_file = seed_dir / "farmer_performance.json"
    if farmer_performance_file.exists():
        farmer_performance = json.loads(farmer_performance_file.read_text())
        await mongodb_direct.seed_farmer_performance(farmer_performance)
        seeded_data["farmer_performance"] = farmer_performance

    # Load and seed weather observations
    weather_observations_file = seed_dir / "weather_observations.json"
    if weather_observations_file.exists():
        weather_observations = json.loads(weather_observations_file.read_text())
        await mongodb_direct.seed_weather_observations(weather_observations)
        seeded_data["weather_observations"] = weather_observations

    # Load and seed documents (for Collection MCP tests)
    documents_file = seed_dir / "documents.json"
    if documents_file.exists():
        documents = json.loads(documents_file.read_text())
        await mongodb_direct.seed_documents(documents)
        seeded_data["documents"] = documents

    # Load and seed document blobs to Azurite (for Collection MCP tests)
    document_blobs_file = seed_dir / "document_blobs.json"
    if document_blobs_file.exists():
        document_blobs = json.loads(document_blobs_file.read_text())
        for blob_spec in document_blobs:
            await azurite_client.upload_json(
                container_name=blob_spec["container"],
                blob_name=blob_spec["blob_path"],
                data=blob_spec["content"],
            )
        seeded_data["document_blobs"] = document_blobs

    yield seeded_data
