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


def assign_region_from_altitude(
    latitude: float, longitude: float, altitude: float
) -> str:
    """Assign a farm to a region based on location and altitude.

    Regions are defined by {county}-{altitude_band}:
    - highland: >= 1800m (cooler, more rainfall, later flushes, frost risk)
    - midland: 1400m - 1800m (moderate conditions)
    - lowland: < 1400m (warmer, earlier flushes)

    For MVP, we use a simplified county assignment based on Kenya tea regions.
    A full implementation would use reverse geocoding to get the actual county.

    Args:
        latitude: Farm latitude in decimal degrees.
        longitude: Farm longitude in decimal degrees.
        altitude: Altitude in meters.

    Returns:
        Region ID in format: {county}-{altitude_band} (e.g., "nyeri-highland")
    """
    # Determine altitude band
    if altitude >= 1800:
        band = "highland"
    elif altitude >= 1400:
        band = "midland"
    else:
        band = "lowland"

    # MVP: Simplified county assignment for Kenya tea regions
    # Using rough bounding boxes for major tea-producing counties
    # A production implementation would use reverse geocoding

    # Nyeri County approximate bounds
    if -0.6 <= latitude <= 0.0 and 36.5 <= longitude <= 37.5:
        county = "nyeri"
    # Kericho County approximate bounds
    elif -0.8 <= latitude <= 0.0 and 35.0 <= longitude <= 36.0:
        county = "kericho"
    # Nandi County approximate bounds
    elif 0.0 <= latitude <= 0.5 and 34.5 <= longitude <= 35.5:
        county = "nandi"
    # Bomet County approximate bounds
    elif -1.0 <= latitude <= -0.3 and 35.0 <= longitude <= 35.8:
        county = "bomet"
    # Kisii County approximate bounds
    elif -1.0 <= latitude <= -0.4 and 34.5 <= longitude <= 35.0:
        county = "kisii"
    else:
        # Default to nyeri for coordinates outside known regions
        county = "nyeri"
        logger.warning(
            "Could not determine county for coordinates (%.4f, %.4f), "
            "defaulting to 'nyeri'",
            latitude,
            longitude,
        )

    region_id = f"{county}-{band}"
    logger.debug(
        "Assigned region '%s' for coordinates (%.4f, %.4f) at altitude %.0fm",
        region_id,
        latitude,
        longitude,
        altitude,
    )
    return region_id
