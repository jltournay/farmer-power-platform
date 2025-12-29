"""Cleanup utilities for E2E tests."""

from typing import Any

from tests.e2e.helpers.azure_blob import AzuriteClient
from tests.e2e.helpers.mongodb_direct import MongoDBDirectClient


async def cleanup_all_data(
    mongodb_client: MongoDBDirectClient | None = None,
    azurite_client: AzuriteClient | None = None,
) -> dict[str, Any]:
    """
    Clean up all E2E test data.

    This should be called after the E2E test session completes
    to ensure a clean slate for the next run.

    Returns a summary of what was cleaned up.
    """
    summary = {
        "databases_dropped": [],
        "containers_deleted": [],
        "errors": [],
    }

    # Cleanup MongoDB
    if mongodb_client:
        try:
            await mongodb_client.drop_all_e2e_databases()
            summary["databases_dropped"].extend(["plantation_e2e", "collection_e2e"])
        except Exception as e:
            summary["errors"].append(f"MongoDB cleanup error: {e}")

    # Cleanup Azurite
    if azurite_client:
        containers_to_clean = [
            "quality-events-e2e",
            "weather-data-e2e",
            "test-data-e2e",
        ]
        for container in containers_to_clean:
            try:
                await azurite_client.delete_container(container)
                summary["containers_deleted"].append(container)
            except Exception as e:
                summary["errors"].append(f"Azurite cleanup error ({container}): {e}")

    return summary


async def cleanup_with_new_clients(
    mongodb_uri: str = "mongodb://localhost:27017",
    azurite_connection_string: str | None = None,
) -> dict[str, Any]:
    """
    Convenience function to cleanup with freshly created clients.

    Use this when you don't have existing client instances.
    """
    from tests.e2e.helpers.azure_blob import AZURITE_CONNECTION_STRING

    summary = {"databases_dropped": [], "containers_deleted": [], "errors": []}

    # Cleanup MongoDB
    async with MongoDBDirectClient(mongodb_uri) as mongo:
        try:
            await mongo.drop_all_e2e_databases()
            summary["databases_dropped"].extend(["plantation_e2e", "collection_e2e"])
        except Exception as e:
            summary["errors"].append(f"MongoDB cleanup error: {e}")

    # Cleanup Azurite
    conn_str = azurite_connection_string or AZURITE_CONNECTION_STRING
    async with AzuriteClient(conn_str) as azurite:
        containers_to_clean = [
            "quality-events-e2e",
            "weather-data-e2e",
            "test-data-e2e",
        ]
        for container in containers_to_clean:
            try:
                await azurite.delete_container(container)
                summary["containers_deleted"].append(container)
            except Exception as e:
                summary["errors"].append(f"Azurite cleanup error ({container}): {e}")

    return summary
