"""Region assignment service for GPS-based farmer-to-region matching.

Story 1.10: GPS-Based Region Assignment with Polygon Boundaries
Replaces hardcoded bounding box logic with polygon-based point-in-polygon tests.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from fp_common.models.value_objects import (
        Coordinate,
        RegionBoundary,
    )
    from plantation_model.domain.models import Region

logger = structlog.get_logger("plantation_model.domain.services.region_assignment")


class RegionAssignmentService:
    """Assigns farms to regions based on GPS coordinates and altitude.

    This service implements the region assignment logic defined in ADR-017:
    1. For regions WITH polygon boundaries: point-in-polygon test + altitude band match
    2. For regions WITHOUT boundaries: altitude band match + nearest center (Haversine)

    The service is stateless and operates on a list of regions passed to it.
    """

    # Earth's radius in kilometers (for Haversine calculations)
    EARTH_RADIUS_KM = 6371.0

    def assign_region(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        regions: list[Region],
    ) -> str | None:
        """Assign a farm location to a region.

        Algorithm:
        1. Filter regions to only active ones
        2. Check each region with a polygon boundary for point-in-polygon match
        3. Verify altitude falls within region's altitude band
        4. If no polygon match, fall back to nearest region center by Haversine distance
        5. Return region_id of best match, or None if no match found

        Args:
            latitude: Farm latitude in decimal degrees (-90 to 90).
            longitude: Farm longitude in decimal degrees (-180 to 180).
            altitude: Farm altitude in meters.
            regions: List of Region objects to search.

        Returns:
            region_id of the matched region, or None if no match found.
        """
        if not regions:
            logger.warning("No regions provided for assignment")
            return None

        # Filter to active regions only
        active_regions = [r for r in regions if r.is_active]
        if not active_regions:
            logger.warning("No active regions found")
            return None

        # Step 1: Try polygon-based matching for regions with boundaries
        for region in active_regions:
            if (
                region.geography.boundary is not None
                and self._point_in_polygon(latitude, longitude, region.geography.boundary)
                and self._altitude_matches_band(altitude, region)
            ):
                logger.info(
                    "Assigned region by polygon match",
                    region_id=region.region_id,
                    latitude=latitude,
                    longitude=longitude,
                    altitude=altitude,
                )
                return region.region_id

        # Step 2: Fall back to altitude band + nearest center
        candidates = [r for r in active_regions if self._altitude_matches_band(altitude, r)]

        if not candidates:
            logger.warning(
                "No region found matching altitude band",
                altitude=altitude,
                latitude=latitude,
                longitude=longitude,
            )
            # Fall back to nearest region by center regardless of altitude
            candidates = active_regions

        # Find nearest by Haversine distance
        nearest_region = min(
            candidates,
            key=lambda r: self._haversine_distance(
                latitude,
                longitude,
                r.geography.center_gps.lat,
                r.geography.center_gps.lng,
            ),
        )

        logger.info(
            "Assigned region by nearest center (Haversine fallback)",
            region_id=nearest_region.region_id,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
        )
        return nearest_region.region_id

    def _point_in_polygon(
        self,
        latitude: float,
        longitude: float,
        boundary: RegionBoundary,
    ) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm.

        Args:
            latitude: Point latitude.
            longitude: Point longitude.
            boundary: RegionBoundary containing the polygon rings.

        Returns:
            True if point is inside the polygon (exterior minus holes).
        """
        # Check if point is inside exterior ring
        if not self._point_in_ring(latitude, longitude, boundary.exterior.points):
            return False

        # Check if point is inside any hole (interior ring)
        return all(not self._point_in_ring(latitude, longitude, hole.points) for hole in boundary.holes)

    def _point_in_ring(
        self,
        latitude: float,
        longitude: float,
        points: list[Coordinate],
    ) -> bool:
        """Ray casting algorithm to determine if point is inside a ring.

        Casts a horizontal ray from the point and counts crossings with the polygon edges.
        Odd number of crossings = inside, even = outside.

        Args:
            latitude: Point latitude (y-coordinate in GeoJSON terms).
            longitude: Point longitude (x-coordinate in GeoJSON terms).
            points: List of Coordinate objects forming the ring.

        Returns:
            True if point is inside the ring.
        """
        n = len(points)
        if n < 4:  # Need at least 3 vertices + closing point
            return False

        inside = False

        # Note: GeoJSON coordinates are [longitude, latitude] but we use
        # latitude as y and longitude as x for the algorithm
        j = n - 1
        for i in range(n):
            xi, yi = points[i].longitude, points[i].latitude
            xj, yj = points[j].longitude, points[j].latitude

            # Check if the ray crosses this edge
            if ((yi > latitude) != (yj > latitude)) and (longitude < (xj - xi) * (latitude - yi) / (yj - yi) + xi):
                inside = not inside

            j = i

        return inside

    def _altitude_matches_band(self, altitude: float, region: Region) -> bool:
        """Check if altitude falls within region's altitude band.

        Args:
            altitude: Altitude in meters.
            region: Region to check.

        Returns:
            True if altitude is within the region's altitude band.
        """
        band = region.geography.altitude_band
        return band.min_meters <= altitude <= band.max_meters

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Calculate great-circle distance between two points.

        Uses the Haversine formula for distance on a sphere.

        Args:
            lat1: First point latitude.
            lon1: First point longitude.
            lat2: Second point latitude.
            lon2: Second point longitude.

        Returns:
            Distance in kilometers.
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return self.EARTH_RADIUS_KM * c
