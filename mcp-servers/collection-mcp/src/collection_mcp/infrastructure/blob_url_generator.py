"""Azure Blob Storage URL generator with SAS tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import structlog
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

logger = structlog.get_logger(__name__)


class BlobUrlGeneratorError(Exception):
    """Raised when blob URL generation fails."""

    pass


class BlobUrlGenerator:
    """Generate SAS URLs for Azure Blob Storage access."""

    def __init__(
        self,
        account_name: str,
        account_key: str,
        validity_hours: int = 1,
    ) -> None:
        """Initialize the blob URL generator.

        Args:
            account_name: Azure Storage account name
            account_key: Azure Storage account key
            validity_hours: Default validity period for SAS tokens (hours)
        """
        self._account_name = account_name
        self._account_key = account_key
        self._validity_hours = validity_hours

    def _parse_blob_uri(self, blob_uri: str) -> tuple[str, str]:
        """Parse a blob URI to extract container and blob name.

        Supports formats:
        - https://account.blob.core.windows.net/container/path/to/blob
        - wasbs://container@account.blob.core.windows.net/path/to/blob

        Args:
            blob_uri: The blob URI to parse

        Returns:
            Tuple of (container_name, blob_name)

        Raises:
            BlobUrlGeneratorError: If the URI cannot be parsed
        """
        try:
            if blob_uri.startswith("wasbs://"):
                # wasbs://container@account.blob.core.windows.net/path/to/blob
                # Remove wasbs://
                remaining = blob_uri[8:]
                # Split by @ to get container and rest
                container, rest = remaining.split("@", 1)
                # Get the path after the host
                parsed = urlparse(f"https://{rest}")
                blob_name = parsed.path.lstrip("/")
                return container, blob_name

            elif blob_uri.startswith("https://"):
                # https://account.blob.core.windows.net/container/path/to/blob
                parsed = urlparse(blob_uri)
                path_parts = parsed.path.lstrip("/").split("/", 1)
                if len(path_parts) < 2:
                    raise BlobUrlGeneratorError(f"Invalid blob URI format, missing blob path: {blob_uri}")
                container = path_parts[0]
                blob_name = path_parts[1]
                return container, blob_name

            else:
                raise BlobUrlGeneratorError(f"Unsupported blob URI scheme: {blob_uri}")

        except Exception as e:
            if isinstance(e, BlobUrlGeneratorError):
                raise
            raise BlobUrlGeneratorError(f"Failed to parse blob URI '{blob_uri}': {e}") from e

    def generate_sas_url(
        self,
        blob_uri: str,
        validity_hours: int | None = None,
    ) -> str:
        """Generate a SAS URL for a blob.

        Args:
            blob_uri: The original blob URI
            validity_hours: Override the default validity period

        Returns:
            Full URL with SAS token for read access

        Raises:
            BlobUrlGeneratorError: If URL generation fails
        """
        if not self._account_name or not self._account_key:
            logger.warning(
                "Blob URL generator not configured, returning original URI",
                blob_uri=blob_uri,
            )
            return blob_uri

        validity = validity_hours or self._validity_hours

        try:
            container_name, blob_name = self._parse_blob_uri(blob_uri)

            # Generate SAS token with read permission
            sas_token = generate_blob_sas(
                account_name=self._account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=self._account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(UTC) + timedelta(hours=validity),
            )

            # Build the full URL with SAS token
            sas_url = f"https://{self._account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"

            logger.debug(
                "Generated SAS URL",
                container=container_name,
                blob=blob_name,
                validity_hours=validity,
            )

            return sas_url

        except BlobUrlGeneratorError:
            raise
        except Exception as e:
            raise BlobUrlGeneratorError(f"Failed to generate SAS URL for '{blob_uri}': {e}") from e

    def enrich_files_with_sas(
        self,
        files: list[dict[str, Any]],
        validity_hours: int | None = None,
    ) -> list[dict[str, Any]]:
        """Add SAS URLs to a list of file dictionaries.

        Args:
            files: List of file dictionaries with 'blob_uri' field
            validity_hours: Override the default validity period

        Returns:
            List of file dictionaries with 'sas_url' field added
        """
        enriched_files = []

        for file in files:
            enriched_file = dict(file)

            blob_uri = file.get("blob_uri")
            if blob_uri:
                try:
                    enriched_file["sas_url"] = self.generate_sas_url(
                        blob_uri=blob_uri,
                        validity_hours=validity_hours,
                    )
                except BlobUrlGeneratorError as e:
                    logger.warning(
                        "Failed to generate SAS URL for file",
                        blob_uri=blob_uri,
                        error=str(e),
                    )
                    # Keep original blob_uri, don't add sas_url
                    enriched_file["sas_url"] = None

            enriched_files.append(enriched_file)

        logger.info(
            "Enriched files with SAS URLs",
            file_count=len(files),
            enriched_count=sum(1 for f in enriched_files if f.get("sas_url")),
        )

        return enriched_files
