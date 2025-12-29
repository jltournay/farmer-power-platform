"""E2E Test: Infrastructure Verification.

Verifies that all E2E infrastructure components are running and accessible:
1. HTTP endpoints (Plantation Model, Collection Model)
2. MCP gRPC endpoints (Plantation MCP, Collection MCP)
3. MongoDB connection
4. Redis/DAPR Pub/Sub connectivity
5. Azurite blob storage

This test should PASS before running any functional E2E tests.
Run this first to verify your Docker Compose stack is healthy.

Prerequisites:
    docker-compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d
"""

import contextlib

import pytest


@pytest.mark.e2e
class TestHTTPEndpoints:
    """Verify HTTP API endpoints are accessible."""

    @pytest.mark.asyncio
    async def test_plantation_model_health(self, plantation_api):
        """Verify Plantation Model HTTP endpoint is healthy."""
        health = await plantation_api.health()
        assert health is not None
        # Accept various health response formats
        assert health.get("status") == "healthy" or health.get("status") == "ok" or "healthy" in str(health).lower()

    @pytest.mark.asyncio
    async def test_plantation_model_ready(self, plantation_api):
        """Verify Plantation Model is ready to accept requests."""
        ready = await plantation_api.ready()
        assert ready is not None

    @pytest.mark.asyncio
    async def test_collection_model_health(self, collection_api):
        """Verify Collection Model HTTP endpoint is healthy."""
        health = await collection_api.health()
        assert health is not None
        assert health.get("status") == "healthy" or health.get("status") == "ok" or "healthy" in str(health).lower()

    @pytest.mark.asyncio
    async def test_collection_model_ready(self, collection_api):
        """Verify Collection Model is ready to accept requests."""
        ready = await collection_api.ready()
        assert ready is not None


@pytest.mark.e2e
class TestMCPEndpoints:
    """Verify MCP gRPC endpoints are accessible."""

    @pytest.mark.asyncio
    async def test_plantation_mcp_list_tools(self, plantation_mcp):
        """Verify Plantation MCP can list tools."""
        tools = await plantation_mcp.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Log available tools for debugging
        tool_names = [t.get("name") for t in tools]
        print(f"Plantation MCP tools: {tool_names}")

    @pytest.mark.asyncio
    async def test_collection_mcp_list_tools(self, collection_mcp):
        """Verify Collection MCP can list tools."""
        tools = await collection_mcp.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        # Log available tools for debugging
        tool_names = [t.get("name") for t in tools]
        print(f"Collection MCP tools: {tool_names}")


@pytest.mark.e2e
class TestMongoDB:
    """Verify MongoDB connectivity."""

    @pytest.mark.asyncio
    async def test_mongodb_connection(self, mongodb_direct):
        """Verify MongoDB is accessible."""
        databases = await mongodb_direct.list_databases()
        assert isinstance(databases, list)
        # Should have at least admin, config, local
        assert len(databases) >= 1
        print(f"MongoDB databases: {databases}")

    @pytest.mark.asyncio
    async def test_plantation_database_accessible(self, mongodb_direct):
        """Verify plantation_e2e database is accessible."""
        db = mongodb_direct.plantation_db
        collections = await db.list_collection_names()
        assert isinstance(collections, list)
        print(f"Plantation E2E collections: {collections}")

    @pytest.mark.asyncio
    async def test_collection_database_accessible(self, mongodb_direct):
        """Verify collection_e2e database is accessible."""
        db = mongodb_direct.collection_db
        collections = await db.list_collection_names()
        assert isinstance(collections, list)
        print(f"Collection E2E collections: {collections}")


@pytest.mark.e2e
class TestAzurite:
    """Verify Azurite blob storage connectivity."""

    @pytest.mark.asyncio
    async def test_azurite_connection(self, azurite_client):
        """Verify Azurite is accessible."""
        # List containers (may be empty initially)
        containers = await azurite_client.list_containers()
        assert isinstance(containers, list)
        print(f"Azurite containers: {containers}")

    @pytest.mark.asyncio
    async def test_azurite_create_container(self, azurite_client):
        """Verify can create a container in Azurite."""
        test_container = "e2e-infra-test"
        try:
            await azurite_client.create_container(test_container)
            containers = await azurite_client.list_containers()
            assert test_container in containers
        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                await azurite_client.delete_container(test_container)

    @pytest.mark.asyncio
    async def test_azurite_upload_download(self, azurite_client):
        """Verify can upload and download from Azurite."""
        test_container = "e2e-infra-test-blob"
        test_data = {"test": "data", "value": 123}

        try:
            # Upload
            blob_url = await azurite_client.upload_json(
                container_name=test_container,
                blob_name="test/infra-check.json",
                data=test_data,
            )
            assert blob_url is not None
            assert "devstoreaccount1" in blob_url

            # List to verify
            blobs = await azurite_client.list_blobs(test_container)
            assert len(blobs) >= 1
        finally:
            # Cleanup
            with contextlib.suppress(Exception):
                await azurite_client.delete_container(test_container)


@pytest.mark.e2e
class TestDAPRPubSub:
    """Verify DAPR Pub/Sub connectivity via service sidecars."""

    @pytest.mark.asyncio
    async def test_plantation_model_dapr_health(self, e2e_config):
        """Verify Plantation Model DAPR sidecar is running.

        DAPR sidecar health is accessible via the service's localhost:3500.
        Since we can't access localhost inside container, we verify indirectly
        by checking if the service health includes DAPR connectivity.
        """
        # If service is healthy, DAPR sidecar must be running
        # (service depends on DAPR for inter-service calls)
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                # Check if service is responding (implies DAPR is up)
                response = await client.get(f"{e2e_config['plantation_model_url']}/health")
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.fail("Plantation Model not accessible - DAPR may be down")

    @pytest.mark.asyncio
    async def test_collection_model_dapr_health(self, e2e_config):
        """Verify Collection Model DAPR sidecar is running."""
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{e2e_config['collection_model_url']}/health")
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.fail("Collection Model not accessible - DAPR may be down")


@pytest.mark.e2e
class TestSeedData:
    """Verify seed data is loaded correctly."""

    @pytest.mark.asyncio
    async def test_seed_data_fixture_works(self, seed_data):
        """Verify seed_data fixture loads data."""
        assert seed_data is not None
        assert isinstance(seed_data, dict)
        print(f"Seed data keys: {list(seed_data.keys())}")

    @pytest.mark.asyncio
    async def test_grading_models_seeded(self, seed_data, mongodb_direct):
        """Verify grading models are seeded."""
        grading_models = seed_data.get("grading_models", [])
        print(f"Seeded grading models: {len(grading_models)}")

        if grading_models:
            # Verify at least one exists in DB
            db_count = await mongodb_direct.plantation_db.grading_models.count_documents({})
            assert db_count >= len(grading_models)

    @pytest.mark.asyncio
    async def test_regions_seeded(self, seed_data, mongodb_direct):
        """Verify regions are seeded."""
        regions = seed_data.get("regions", [])
        print(f"Seeded regions: {len(regions)}")

        if regions:
            db_count = await mongodb_direct.plantation_db.regions.count_documents({})
            assert db_count >= len(regions)

    @pytest.mark.asyncio
    async def test_source_configs_seeded(self, seed_data, mongodb_direct):
        """Verify source configs are seeded (required for Collection Model)."""
        source_configs = seed_data.get("source_configs", [])
        print(f"Seeded source configs: {len(source_configs)}")

        if source_configs:
            db_count = await mongodb_direct.collection_db.source_configs.count_documents({})
            assert db_count >= len(source_configs)


@pytest.mark.e2e
class TestInfrastructureSummary:
    """Final summary test that checks all components."""

    @pytest.mark.asyncio
    async def test_full_infrastructure_check(
        self,
        plantation_api,
        collection_api,
        plantation_mcp,
        collection_mcp,
        mongodb_direct,
        azurite_client,
        seed_data,
    ):
        """Complete infrastructure verification.

        This single test verifies all components are working together.
        If this passes, the E2E infrastructure is ready for functional tests.
        """
        results = {}

        # 1. HTTP APIs
        try:
            await plantation_api.health()
            results["plantation_api"] = "OK"
        except Exception as e:
            results["plantation_api"] = f"FAILED: {e}"

        try:
            await collection_api.health()
            results["collection_api"] = "OK"
        except Exception as e:
            results["collection_api"] = f"FAILED: {e}"

        # 2. MCP Servers
        try:
            tools = await plantation_mcp.list_tools()
            results["plantation_mcp"] = f"OK ({len(tools)} tools)"
        except Exception as e:
            results["plantation_mcp"] = f"FAILED: {e}"

        try:
            tools = await collection_mcp.list_tools()
            results["collection_mcp"] = f"OK ({len(tools)} tools)"
        except Exception as e:
            results["collection_mcp"] = f"FAILED: {e}"

        # 3. MongoDB
        try:
            dbs = await mongodb_direct.list_databases()
            results["mongodb"] = f"OK ({len(dbs)} databases)"
        except Exception as e:
            results["mongodb"] = f"FAILED: {e}"

        # 4. Azurite
        try:
            containers = await azurite_client.list_containers()
            results["azurite"] = f"OK ({len(containers)} containers)"
        except Exception as e:
            results["azurite"] = f"FAILED: {e}"

        # 5. Seed Data
        results["seed_grading_models"] = len(seed_data.get("grading_models", []))
        results["seed_regions"] = len(seed_data.get("regions", []))
        results["seed_source_configs"] = len(seed_data.get("source_configs", []))

        # Print summary
        print("\n" + "=" * 60)
        print("E2E INFRASTRUCTURE STATUS")
        print("=" * 60)
        for component, status in results.items():
            print(f"  {component}: {status}")
        print("=" * 60)

        # Fail if any component failed
        failures = [k for k, v in results.items() if "FAILED" in str(v)]
        if failures:
            pytest.fail(f"Infrastructure components failed: {failures}")
