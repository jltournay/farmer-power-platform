"""Azure Blob Storage client for downloading blobs.

Story 2.13: Thumbnail Generation for AI Tiered Vision Processing
"""

import structlog
from azure.storage.blob.aio import BlobServiceClient

logger = structlog.get_logger(__name__)


class BlobNotFoundError(Exception):
    """Raised when a blob is not found."""

    def __init__(self, container: str, blob_path: str) -> None:
        self.container = container
        self.blob_path = blob_path
        super().__init__(f"Blob not found: {container}/{blob_path}")


class BlobStorageClient:
    """Async client for Azure Blob Storage operations."""

    def __init__(self, connection_string: str) -> None:
        """Initialize the blob storage client.

        Args:
            connection_string: Azure Storage connection string.
        """
        self._connection_string = connection_string
        self._client: BlobServiceClient | None = None

    async def _get_client(self) -> BlobServiceClient:
        """Get or create the blob service client."""
        if self._client is None:
            self._client = BlobServiceClient.from_connection_string(self._connection_string)
        return self._client

    async def download_blob(self, container: str, blob_path: str) -> bytes:
        """Download a blob's content as bytes.

        Args:
            container: The container name.
            blob_path: The blob path within the container.

        Returns:
            The blob content as bytes.

        Raises:
            BlobNotFoundError: If the blob does not exist.
        """
        try:
            client = await self._get_client()
            blob_client = client.get_blob_client(container=container, blob=blob_path)

            if not await blob_client.exists():
                raise BlobNotFoundError(container, blob_path)

            stream = await blob_client.download_blob()
            content = await stream.readall()

            logger.debug(
                "Blob downloaded successfully",
                container=container,
                blob_path=blob_path,
                size_bytes=len(content),
            )
            return content

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.exception(
                "Failed to download blob",
                container=container,
                blob_path=blob_path,
                error=str(e),
            )
            raise

    async def close(self) -> None:
        """Close the blob service client."""
        if self._client:
            await self._client.close()
            self._client = None
