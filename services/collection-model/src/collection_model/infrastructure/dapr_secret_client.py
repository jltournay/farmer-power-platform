"""DAPR Secret Store client for retrieving secrets (Story 2.7).

This module provides the DaprSecretClient class for retrieving secrets
from DAPR Secret Store via the DAPR HTTP API. Secrets are used for
API authentication in scheduled pull sources.

DAPR Secrets API:
- GET /v1.0/secrets/{store_name}/{key} - Get a secret
"""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class DaprSecretClient:
    """Client for DAPR Secrets HTTP API.

    Retrieves secrets from configured DAPR Secret Stores
    (e.g., Azure Key Vault, Kubernetes Secrets).

    Attributes:
        dapr_host: DAPR sidecar host (default: localhost).
        dapr_port: DAPR sidecar HTTP port (default: 3500).
    """

    def __init__(
        self,
        dapr_host: str = "localhost",
        dapr_port: int = 3500,
    ) -> None:
        """Initialize the DAPR Secret client.

        Args:
            dapr_host: DAPR sidecar host.
            dapr_port: DAPR sidecar HTTP port.
        """
        self._dapr_host = dapr_host
        self._dapr_port = dapr_port
        self._base_url = f"http://{dapr_host}:{dapr_port}"

    async def get_secret(
        self,
        store_name: str,
        key: str,
    ) -> dict[str, Any]:
        """Retrieve a secret from DAPR Secret Store.

        Args:
            store_name: Name of the secret store component.
            key: Secret key name.

        Returns:
            Dictionary with secret key-value pairs.
            Returns empty dict on error.
        """
        url = f"{self._base_url}/v1.0/secrets/{store_name}/{key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(
                "Failed to retrieve secret from DAPR",
                store_name=store_name,
                key=key,
                error=str(e),
            )
            return {}
