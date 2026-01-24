"""Azure Blob Storage client for RAG document file access.

This module provides async blob storage operations for downloading
source files (PDFs, Markdown, etc.) for content extraction.

Story 0.75.10b: Basic PDF/Markdown Extraction
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import structlog
from ai_model.config import settings
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = structlog.get_logger(__name__)

# Thread pool for running sync Azure SDK operations
_executor = ThreadPoolExecutor(max_workers=4)


class BlobStorageError(Exception):
    """Base exception for blob storage operations."""

    pass


class BlobNotFoundError(BlobStorageError):
    """Raised when a blob does not exist."""

    pass


class BlobStorageClient:
    """Async client for Azure Blob Storage operations.

    Provides async wrappers around the synchronous Azure Storage SDK.
    Uses a thread pool executor to avoid blocking the event loop.

    Usage:
        client = BlobStorageClient()
        content = await client.download_to_bytes("rag-documents/guide.pdf")
    """

    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str | None = None,
    ) -> None:
        """Initialize the blob storage client.

        Args:
            connection_string: Azure Storage connection string.
                              Defaults to settings.azure_storage_connection_string.
            container_name: Container name for RAG documents.
                           Defaults to settings.azure_storage_container.
        """
        self._connection_string = connection_string or settings.azure_storage_connection_string
        self._container_name = container_name or settings.azure_storage_container
        self._blob_service_client: BlobServiceClient | None = None

    def _get_blob_service_client(self) -> BlobServiceClient:
        """Get or create the blob service client (lazy initialization).

        Returns:
            BlobServiceClient instance.

        Raises:
            BlobStorageError: If connection string is not configured.
        """
        if self._blob_service_client is None:
            if not self._connection_string:
                raise BlobStorageError(
                    "Azure Storage connection string not configured. "
                    "Set AI_MODEL_AZURE_STORAGE_CONNECTION_STRING environment variable."
                )
            self._blob_service_client = BlobServiceClient.from_connection_string(self._connection_string)
        return self._blob_service_client

    async def upload_bytes(self, blob_path: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to blob storage.

        Args:
            blob_path: Path for the blob within the container.
            content: The bytes to upload.
            content_type: MIME type of the content.

        Returns:
            The blob_path that was used.

        Raises:
            BlobStorageError: If upload fails.
        """
        loop = asyncio.get_event_loop()

        def _sync_upload() -> str:
            """Synchronous upload operation run in thread pool."""
            try:
                service_client = self._get_blob_service_client()
                container_client = service_client.get_container_client(self._container_name)

                # Ensure container exists (idempotent)
                try:
                    container_client.create_container()
                except Exception:
                    pass  # Already exists

                blob_client = container_client.get_blob_client(blob_path)

                blob_client.upload_blob(
                    content,
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type),
                )

                logger.info(
                    "Blob uploaded",
                    blob_path=blob_path,
                    container=self._container_name,
                    size_bytes=len(content),
                )

                return blob_path

            except Exception as e:
                raise BlobStorageError(f"Failed to upload blob: {e}") from e

        return await loop.run_in_executor(_executor, _sync_upload)

    async def download_to_bytes(self, blob_path: str) -> bytes:
        """Download a blob's content as bytes.

        Args:
            blob_path: Path to the blob within the container
                      (e.g., "rag-documents/guide.pdf" or just "guide.pdf").

        Returns:
            The blob content as bytes.

        Raises:
            BlobNotFoundError: If the blob does not exist.
            BlobStorageError: If download fails for other reasons.
        """
        loop = asyncio.get_event_loop()

        def _sync_download() -> bytes:
            """Synchronous download operation run in thread pool."""
            try:
                service_client = self._get_blob_service_client()
                container_client = service_client.get_container_client(self._container_name)
                blob_client = container_client.get_blob_client(blob_path)

                downloader = blob_client.download_blob()
                content = downloader.readall()

                logger.debug(
                    "Blob downloaded",
                    blob_path=blob_path,
                    container=self._container_name,
                    size_bytes=len(content),
                )

                return content

            except ResourceNotFoundError as e:
                raise BlobNotFoundError(f"Blob not found: {blob_path}") from e
            except Exception as e:
                raise BlobStorageError(f"Failed to download blob: {e}") from e

        return await loop.run_in_executor(_executor, _sync_download)

    async def blob_exists(self, blob_path: str) -> bool:
        """Check if a blob exists.

        Args:
            blob_path: Path to the blob within the container.

        Returns:
            True if the blob exists, False otherwise.
        """
        loop = asyncio.get_event_loop()

        def _sync_exists() -> bool:
            """Synchronous exists check run in thread pool."""
            try:
                service_client = self._get_blob_service_client()
                container_client = service_client.get_container_client(self._container_name)
                blob_client = container_client.get_blob_client(blob_path)
                return blob_client.exists()
            except Exception as e:
                logger.warning("Failed to check blob existence", blob_path=blob_path, error=str(e))
                return False

        return await loop.run_in_executor(_executor, _sync_exists)

    async def get_blob_properties(self, blob_path: str) -> dict:
        """Get blob properties (size, content type, etc.).

        Args:
            blob_path: Path to the blob within the container.

        Returns:
            Dictionary with blob properties.

        Raises:
            BlobNotFoundError: If the blob does not exist.
            BlobStorageError: If operation fails.
        """
        loop = asyncio.get_event_loop()

        def _sync_properties() -> dict:
            """Synchronous properties fetch run in thread pool."""
            try:
                service_client = self._get_blob_service_client()
                container_client = service_client.get_container_client(self._container_name)
                blob_client = container_client.get_blob_client(blob_path)

                props = blob_client.get_blob_properties()

                return {
                    "name": props.name,
                    "size": props.size,
                    "content_type": props.content_settings.content_type,
                    "created_on": props.creation_time,
                    "last_modified": props.last_modified,
                    "etag": props.etag,
                }
            except ResourceNotFoundError as e:
                raise BlobNotFoundError(f"Blob not found: {blob_path}") from e
            except Exception as e:
                raise BlobStorageError(f"Failed to get blob properties: {e}") from e

        return await loop.run_in_executor(_executor, _sync_properties)
