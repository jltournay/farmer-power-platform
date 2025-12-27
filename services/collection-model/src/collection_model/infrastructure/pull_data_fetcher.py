"""HTTP Pull Data Fetcher for scheduled pull sources (Story 2.7).

This module provides the PullDataFetcher class for fetching data from
external HTTP APIs. It handles URL construction, authentication via
DAPR Secret Store, and retry logic for transient failures.
"""

import re
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class PullDataFetcher:
    """HTTP data fetcher for scheduled pull sources.

    Fetches JSON data from external APIs with support for:
    - URL parameter substitution (including iteration item values)
    - Authentication via DAPR Secret Store (API key, bearer token)
    - Retry logic for transient failures

    Attributes:
        dapr_secret_client: Client for retrieving secrets from DAPR.
        max_retries: Maximum number of retry attempts.
        retry_wait_seconds: Base wait time between retries.
    """

    def __init__(
        self,
        dapr_secret_client: Any,
        max_retries: int = 3,
        retry_wait_seconds: float = 1.0,
    ) -> None:
        """Initialize the Pull Data Fetcher.

        Args:
            dapr_secret_client: Client for DAPR Secret Store API.
            max_retries: Maximum number of retry attempts (default: 3).
            retry_wait_seconds: Base wait time between retries (default: 1.0).
        """
        self._secret_client = dapr_secret_client
        self._max_retries = max_retries
        self._retry_wait_seconds = retry_wait_seconds

    async def fetch(
        self,
        pull_config: dict[str, Any],
        iteration_item: dict[str, Any] | None = None,
    ) -> bytes:
        """Fetch data from an external API.

        Builds the URL with parameter substitution, adds authentication
        headers, and performs the HTTP GET request with retry logic.

        Args:
            pull_config: Pull configuration containing base_url, auth_type,
                        auth_config, and parameters.
            iteration_item: Optional item from iteration for parameter
                           substitution (e.g., region data with coordinates).

        Returns:
            Raw response content as bytes (typically JSON).

        Raises:
            httpx.HTTPStatusError: On HTTP error responses.
            httpx.TimeoutException: On request timeout.
            httpx.ConnectError: On connection failure after retries.
        """
        base_url = pull_config.get("base_url", "")
        parameters = pull_config.get("parameters", {})

        url = self._build_url(
            base_url=base_url,
            parameters=parameters,
            iteration_item=iteration_item,
        )

        headers = await self._get_auth_header(pull_config)

        logger.debug(
            "Fetching data from external API",
            url=url,
            has_auth=bool(headers),
            has_iteration_item=iteration_item is not None,
        )

        return await self._fetch_with_retry(url=url, headers=headers)

    async def _fetch_with_retry(
        self,
        url: str,
        headers: dict[str, str],
    ) -> bytes:
        """Perform HTTP GET with retry logic.

        Uses tenacity for exponential backoff on transient errors.

        Args:
            url: Full URL to fetch.
            headers: HTTP headers including authentication.

        Returns:
            Raw response content as bytes.
        """

        # Create a retrying wrapper dynamically based on instance config
        @retry(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential(
                multiplier=self._retry_wait_seconds,
                min=self._retry_wait_seconds,
                max=30,
            ),
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            reraise=True,
        )
        async def _do_fetch() -> bytes:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.content

        return await _do_fetch()

    def _build_url(
        self,
        base_url: str,
        parameters: dict[str, str],
        iteration_item: dict[str, Any] | None = None,
    ) -> str:
        """Build full URL with parameter substitution.

        Supports {item.field} syntax for substituting values from
        iteration items. Nested access is supported: {item.location.lat}.

        Args:
            base_url: Base URL without query parameters.
            parameters: Query parameters (may contain {item.field} templates).
            iteration_item: Optional item for template substitution.

        Returns:
            Full URL with query string.
        """
        if not parameters:
            return base_url

        # Substitute iteration item values in parameters
        resolved_params = {}
        for key, value in parameters.items():
            resolved_params[key] = self._substitute_item_value(
                value=value,
                iteration_item=iteration_item,
            )

        query_string = urlencode(resolved_params)
        return f"{base_url}?{query_string}"

    def _substitute_item_value(
        self,
        value: str,
        iteration_item: dict[str, Any] | None,
    ) -> str:
        """Substitute {item.field} templates with actual values.

        Args:
            value: String value potentially containing {item.field} templates.
            iteration_item: Item containing values to substitute.

        Returns:
            Value with templates replaced by actual values.
        """
        if not iteration_item or "{item." not in value:
            return value

        # Pattern to match {item.field} or {item.nested.field}
        pattern = r"\{item\.([a-zA-Z0-9_.]+)\}"

        def replace_match(match: re.Match[str]) -> str:
            path = match.group(1)
            return str(self._get_nested_value(iteration_item, path))

        return re.sub(pattern, replace_match, value)

    def _get_nested_value(
        self,
        data: dict[str, Any],
        path: str,
    ) -> Any:
        """Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to extract value from.
            path: Dot-separated path (e.g., "location.latitude").

        Returns:
            Value at path, or empty string if not found.
        """
        current = data
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return ""
        return current

    async def _get_auth_header(
        self,
        pull_config: dict[str, Any],
    ) -> dict[str, str]:
        """Generate authentication headers from pull config.

        Retrieves secrets from DAPR Secret Store based on auth_type.

        Args:
            pull_config: Configuration containing auth_type and auth_config.

        Returns:
            Dictionary of HTTP headers for authentication.
            Empty dict for auth_type "none".
        """
        auth_type = pull_config.get("auth_type", "none")

        if auth_type == "none":
            return {}

        auth_config = pull_config.get("auth_config", {})
        secret_name = auth_config.get("secret_name", "")
        secret_store = auth_config.get("secret_store", "")

        if not secret_name or not secret_store:
            logger.warning(
                "Missing secret configuration for auth",
                auth_type=auth_type,
            )
            return {}

        # Retrieve secret from DAPR
        secret_data = await self._secret_client.get_secret(
            store_name=secret_store,
            key=secret_name,
        )

        if auth_type == "api_key":
            header_name = auth_config.get("header_name", "X-API-Key")
            api_key = secret_data.get("api_key", "")
            if api_key:
                return {header_name: api_key}

        elif auth_type == "bearer":
            token = secret_data.get("token", "")
            if token:
                return {"Authorization": f"Bearer {token}"}

        logger.warning(
            "Failed to retrieve secret for auth",
            auth_type=auth_type,
            secret_name=secret_name,
        )
        return {}
