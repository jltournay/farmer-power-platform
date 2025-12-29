"""Azure Blob Storage (Azurite) client for E2E testing."""

import contextlib
import json
from typing import Any

from azure.storage.blob.aio import BlobServiceClient, ContainerClient

# Default Azurite connection string
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://localhost:10000/devstoreaccount1"
)


class AzuriteClient:
    """Client for interacting with Azurite (Azure Blob emulator)."""

    def __init__(self, connection_string: str = AZURITE_CONNECTION_STRING):
        self.connection_string = connection_string
        self._client: BlobServiceClient | None = None

    async def __aenter__(self) -> "AzuriteClient":
        self._client = BlobServiceClient.from_connection_string(self.connection_string)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.close()

    @property
    def client(self) -> BlobServiceClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    async def create_container(self, container_name: str) -> ContainerClient:
        """Create a container if it doesn't exist."""
        container = self.client.get_container_client(container_name)
        with contextlib.suppress(Exception):
            await container.create_container()
        return container

    async def delete_container(self, container_name: str) -> None:
        """Delete a container and all its blobs."""
        container = self.client.get_container_client(container_name)
        with contextlib.suppress(Exception):
            await container.delete_container()

    async def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes | str,
        content_type: str = "application/json",
    ) -> str:
        """Upload a blob and return its URL."""
        container = await self.create_container(container_name)
        blob = container.get_blob_client(blob_name)

        if isinstance(data, str):
            data = data.encode("utf-8")

        await blob.upload_blob(data, overwrite=True, content_type=content_type)
        return blob.url

    async def upload_json(
        self,
        container_name: str,
        blob_name: str,
        data: dict[str, Any],
    ) -> str:
        """Upload JSON data as a blob."""
        json_data = json.dumps(data, indent=2)
        return await self.upload_blob(
            container_name,
            blob_name,
            json_data,
            content_type="application/json",
        )

    async def download_blob(
        self,
        container_name: str,
        blob_name: str,
    ) -> bytes:
        """Download a blob's content."""
        container = self.client.get_container_client(container_name)
        blob = container.get_blob_client(blob_name)
        download = await blob.download_blob()
        return await download.readall()

    async def download_json(
        self,
        container_name: str,
        blob_name: str,
    ) -> dict[str, Any]:
        """Download and parse JSON blob."""
        data = await self.download_blob(container_name, blob_name)
        return json.loads(data.decode("utf-8"))

    async def list_blobs(self, container_name: str) -> list[str]:
        """List all blobs in a container."""
        container = self.client.get_container_client(container_name)
        blobs = []
        async for blob in container.list_blobs():
            blobs.append(blob.name)
        return blobs

    async def delete_blob(self, container_name: str, blob_name: str) -> None:
        """Delete a specific blob."""
        container = self.client.get_container_client(container_name)
        blob = container.get_blob_client(blob_name)
        with contextlib.suppress(Exception):
            await blob.delete_blob()

    async def upload_quality_event(
        self,
        farmer_id: str,
        factory_id: str,
        event_data: dict[str, Any],
        container_name: str = "quality-events-e2e",
        batch_id: str | None = None,
    ) -> tuple[str, str]:
        """Upload a quality event blob matching source_config path pattern.

        The source_config uses path pattern: results/{factory_id}/{farmer_id}/{batch_id}.json
        This must match for the Collection Model to correctly extract metadata.

        Args:
            farmer_id: Farmer identifier
            factory_id: Factory identifier
            event_data: Quality event data to upload
            container_name: Container name (must match source_config landing_container)
            batch_id: Optional batch ID (generates UUID if not provided)

        Returns:
            Tuple of (blob_url, blob_path) for triggering ingestion
        """
        import uuid
        from datetime import UTC, datetime

        if batch_id is None:
            batch_id = str(uuid.uuid4())

        # Path pattern from source_config: results/{factory_id}/{farmer_id}/{batch_id}.json
        blob_path = f"results/{factory_id}/{farmer_id}/{batch_id}.json"

        full_data = {
            "farmer_id": farmer_id,
            "factory_id": factory_id,
            "batch_id": batch_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **event_data,
        }

        blob_url = await self.upload_json(container_name, blob_path, full_data)
        return blob_url, blob_path

    async def list_containers(self) -> list[str]:
        """List all containers in the storage account."""
        containers = []
        async for container in self.client.list_containers():
            containers.append(container.name)
        return containers

    async def delete_all_e2e_containers(self) -> list[str]:
        """Delete all E2E test containers."""
        deleted = []
        e2e_containers = [
            "quality-events-e2e",
            "manual-uploads-e2e",
            "raw-documents-e2e",
        ]
        for container in e2e_containers:
            try:
                await self.delete_container(container)
                deleted.append(container)
            except Exception:
                pass
        return deleted
