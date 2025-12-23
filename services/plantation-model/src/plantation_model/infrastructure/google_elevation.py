"""Google Elevation API client for fetching altitude data."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class GoogleElevationClient:
    """Fetches altitude from Google Elevation API.

    The altitude is auto-populated based on GPS coordinates when creating
    factories or collection points.
    """

    BASE_URL = "https://maps.googleapis.com/maps/api/elevation/json"

    def __init__(self, api_key: str) -> None:
        """Initialize the client.

        Args:
            api_key: Google Cloud API key with Elevation API enabled.
        """
        self._api_key = api_key

    async def get_altitude(
        self, latitude: float, longitude: float
    ) -> Optional[float]:
        """Fetch altitude in meters for given GPS coordinates.

        Args:
            latitude: Latitude in decimal degrees.
            longitude: Longitude in decimal degrees.

        Returns:
            Altitude in meters, or None if the API call fails.
        """
        if not self._api_key:
            logger.warning(
                "Google Elevation API key not configured, returning default altitude"
            )
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "locations": f"{latitude},{longitude}",
                        "key": self._api_key,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "OK" and data.get("results"):
                    elevation = data["results"][0].get("elevation")
                    logger.debug(
                        "Fetched altitude %.2f meters for coordinates (%.4f, %.4f)",
                        elevation,
                        latitude,
                        longitude,
                    )
                    return elevation

                logger.warning(
                    "Google Elevation API returned status: %s",
                    data.get("status", "UNKNOWN"),
                )
                return None

        except httpx.HTTPError as e:
            logger.error("Failed to fetch altitude from Google Elevation API: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error fetching altitude: %s", e)
            return None
