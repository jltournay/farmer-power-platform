"""Azure Blob Storage client for async blob operations.

This module provides the BlobStorageClient class for downloading and uploading
blobs using the Azure SDK's async client.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient
from collection_model.config import settings
from collection_model.domain.exceptions import BlobNotFoundError, StorageError
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class BlobReference(BaseModel):
    """Reference to a blob in Azure Blob Storage.

    Attributes:
        container: The container name.
        blob_path: The blob path within the container.
        content_type: MIME type of the blob content.
        size_bytes: Size of the blob in bytes.
        etag: ETag for versioning.
        stored_at: When the blob was stored.
    """

    container: str
    blob_path: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    etag: str | None = None
    stored_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BlobStorageClient:
    """Async client for Azure Blob Storage operations.

    Uses the Azure SDK's async BlobServiceClient for non-blocking I/O.
    Supports streaming downloads for large files.
    """

    def __init__(self, connection_string: str | None = None) -> None:
        """Initialize the blob storage client.

        Args:
            connection_string: Azure Storage connection string.
                If not provided, uses settings.azure_storage_connection_string.
        """
        self._connection_string = connection_string or settings.azure_storage_connection_string
        self._client: BlobServiceClient | None = None

    async def _get_client(self) -> BlobServiceClient:
        """Get or create the blob service client."""
        if self._client is None:
            self._client = BlobServiceClient.from_connection_string(self._connection_string)
        return self._client

    async def download_blob(self, container: str, blob_path: str) -> bytes:
        """Download a blob's content as bytes.

        Uses async streaming for efficient memory usage with large files.

        Args:
            container: The container name.
            blob_path: The blob path within the container.

        Returns:
            The blob content as bytes.

        Raises:
            BlobNotFoundError: If the blob does not exist.
            StorageError: If download fails for other reasons.
        """
        try:
            client = await self._get_client()
            blob_client = client.get_blob_client(container=container, blob=blob_path)

            # Check if blob exists
            if not await blob_client.exists():
                raise BlobNotFoundError(f"Blob not found: {container}/{blob_path}")

            # Download using async stream
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
            raise StorageError(f"Failed to download blob: {e}") from e

    async def upload_blob(
        self,
        container: str,
        blob_path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> BlobReference:
        """Upload content to a blob.

        Args:
            container: The container name.
            blob_path: The blob path within the container.
            content: The content to upload.
            content_type: MIME type of the content.
            metadata: Optional metadata to attach to the blob.

        Returns:
            BlobReference with details of the uploaded blob.

        Raises:
            StorageError: If upload fails.
        """
        try:
            client = await self._get_client()
            blob_client = client.get_blob_client(container=container, blob=blob_path)

            # Upload with overwrite
            result = await blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
                metadata=metadata or {},
            )

            logger.debug(
                "Blob uploaded successfully",
                container=container,
                blob_path=blob_path,
                size_bytes=len(content),
                etag=result.get("etag"),
            )

            return BlobReference(
                container=container,
                blob_path=blob_path,
                content_type=content_type,
                size_bytes=len(content),
                etag=result.get("etag"),
                stored_at=datetime.now(UTC),
            )

        except Exception as e:
            logger.exception(
                "Failed to upload blob",
                container=container,
                blob_path=blob_path,
                error=str(e),
            )
            raise StorageError(f"Failed to upload blob: {e}") from e

    async def get_blob_properties(self, container: str, blob_path: str) -> dict[str, Any]:
        """Get properties of a blob.

        Args:
            container: The container name.
            blob_path: The blob path within the container.

        Returns:
            Dict of blob properties.

        Raises:
            BlobNotFoundError: If the blob does not exist.
            StorageError: If fetching properties fails.
        """
        try:
            client = await self._get_client()
            blob_client = client.get_blob_client(container=container, blob=blob_path)

            if not await blob_client.exists():
                raise BlobNotFoundError(f"Blob not found: {container}/{blob_path}")

            props = await blob_client.get_blob_properties()
            return {
                "name": props.name,
                "container": container,
                "size": props.size,
                "content_type": props.content_settings.content_type,
                "etag": props.etag,
                "last_modified": props.last_modified,
                "metadata": props.metadata,
            }

        except BlobNotFoundError:
            raise
        except Exception as e:
            logger.exception(
                "Failed to get blob properties",
                container=container,
                blob_path=blob_path,
                error=str(e),
            )
            raise StorageError(f"Failed to get blob properties: {e}") from e

    async def close(self) -> None:
        """Close the blob service client."""
        if self._client:
            await self._client.close()
            self._client = None
