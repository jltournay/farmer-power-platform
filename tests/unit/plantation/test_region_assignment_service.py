"""Unit tests for RegionAssignmentService (Story 1.10).

Tests the GPS-based region assignment with polygon boundaries.
"""

from fp_common.models.value_objects import (
    GPS,
    Agronomic,
    AltitudeBand,
    AltitudeBandLabel,
    Coordinate,
    FlushCalendar,
    FlushPeriod,
    Geography,
    PolygonRing,
    RegionBoundary,
    WeatherConfig,
)
from plantation_model.domain.models import Region
from plantation_model.domain.services.region_assignment import RegionAssignmentService

# ============================================================================
# Test Fixtures
# ============================================================================


def create_flush_calendar() -> FlushCalendar:
    """Create a minimal FlushCalendar for tests."""
    return FlushCalendar(
        first_flush=FlushPeriod(start="03-15", end="05-15"),
        monsoon_flush=FlushPeriod(start="06-15", end="09-30"),
        autumn_flush=FlushPeriod(start="10-15", end="12-15"),
        dormant=FlushPeriod(start="12-16", end="03-14"),
    )


def create_simple_polygon(center_lat: float, center_lng: float, size: float = 0.5) -> RegionBoundary:
    """Create a simple square polygon around a center point.

    Args:
        center_lat: Center latitude.
        center_lng: Center longitude.
        size: Half-size of the square in degrees.

    Returns:
        RegionBoundary containing a square polygon.
    """
    points = [
        Coordinate(longitude=center_lng - size, latitude=center_lat - size),
        Coordinate(longitude=center_lng + size, latitude=center_lat - size),
        Coordinate(longitude=center_lng + size, latitude=center_lat + size),
        Coordinate(longitude=center_lng - size, latitude=center_lat + size),
        Coordinate(longitude=center_lng - size, latitude=center_lat - size),  # Close
    ]
    return RegionBoundary(rings=[PolygonRing(points=points)])


def create_region(
    region_id: str,
    center_lat: float,
    center_lng: float,
    min_alt: int,
    max_alt: int,
    band_label: AltitudeBandLabel,
    with_boundary: bool = False,
) -> Region:
    """Create a Region for testing.

    Args:
        region_id: Region identifier.
        center_lat: Center latitude.
        center_lng: Center longitude.
        min_alt: Minimum altitude in meters.
        max_alt: Maximum altitude in meters.
        band_label: Altitude band label.
        with_boundary: If True, create a polygon boundary.

    Returns:
        A Region object.
    """
    boundary = None
    if with_boundary:
        boundary = create_simple_polygon(center_lat, center_lng)

    return Region(
        region_id=region_id,
        name=region_id.replace("-", " ").title(),
        county=region_id.split("-")[0].title(),
        country="Kenya",
        geography=Geography(
            center_gps=GPS(lat=center_lat, lng=center_lng),
            radius_km=25,
            altitude_band=AltitudeBand(
                min_meters=min_alt,
                max_meters=max_alt,
                label=band_label,
            ),
            boundary=boundary,
        ),
        flush_calendar=create_flush_calendar(),
        agronomic=Agronomic(soil_type="volcanic"),
        weather_config=WeatherConfig(
            api_location=GPS(lat=center_lat, lng=center_lng),
            altitude_for_api=min_alt,
        ),
        is_active=True,
    )


# ============================================================================
# Point-in-Polygon Tests
# ============================================================================


class TestPointInPolygon:
    """Tests for point-in-polygon algorithm."""

    def test_point_inside_simple_polygon(self) -> None:
        """Test point clearly inside a simple polygon."""
        service = RegionAssignmentService()
        boundary = create_simple_polygon(center_lat=0.0, center_lng=0.0, size=1.0)

        # Point at center
        assert service._point_in_polygon(0.0, 0.0, boundary) is True
        # Point slightly off center
        assert service._point_in_polygon(0.5, 0.5, boundary) is True
        # Point near edge but inside
        assert service._point_in_polygon(0.9, 0.0, boundary) is True

    def test_point_outside_simple_polygon(self) -> None:
        """Test point clearly outside a simple polygon."""
        service = RegionAssignmentService()
        boundary = create_simple_polygon(center_lat=0.0, center_lng=0.0, size=1.0)

        # Point outside bounds
        assert service._point_in_polygon(2.0, 0.0, boundary) is False
        assert service._point_in_polygon(0.0, 2.0, boundary) is False
        assert service._point_in_polygon(-2.0, -2.0, boundary) is False

    def test_point_on_boundary(self) -> None:
        """Test point exactly on polygon edge.

        Note: Ray casting may return either True or False for points
        exactly on the boundary. This is expected behavior.
        """
        service = RegionAssignmentService()
        boundary = create_simple_polygon(center_lat=0.0, center_lng=0.0, size=1.0)

        # Point on edge - result depends on exact algorithm implementation
        # We just verify it doesn't crash
        result = service._point_in_polygon(0.0, 1.0, boundary)
        assert isinstance(result, bool)

    def test_polygon_with_hole(self) -> None:
        """Test polygon with interior hole."""
        service = RegionAssignmentService()

        # Outer square: -1 to 1
        outer_points = [
            Coordinate(longitude=-1, latitude=-1),
            Coordinate(longitude=1, latitude=-1),
            Coordinate(longitude=1, latitude=1),
            Coordinate(longitude=-1, latitude=1),
            Coordinate(longitude=-1, latitude=-1),
        ]
        # Inner hole: -0.5 to 0.5
        hole_points = [
            Coordinate(longitude=-0.5, latitude=-0.5),
            Coordinate(longitude=0.5, latitude=-0.5),
            Coordinate(longitude=0.5, latitude=0.5),
            Coordinate(longitude=-0.5, latitude=0.5),
            Coordinate(longitude=-0.5, latitude=-0.5),
        ]
        boundary = RegionBoundary(rings=[PolygonRing(points=outer_points), PolygonRing(points=hole_points)])

        # Point inside outer but also inside hole -> outside
        assert service._point_in_polygon(0.0, 0.0, boundary) is False
        # Point inside outer but outside hole -> inside
        assert service._point_in_polygon(0.75, 0.75, boundary) is True
        # Point outside outer -> outside
        assert service._point_in_polygon(2.0, 2.0, boundary) is False


# ============================================================================
# Altitude Band Tests
# ============================================================================


class TestAltitudeBandMatching:
    """Tests for altitude band matching."""

    def test_altitude_within_band(self) -> None:
        """Test altitude within region's altitude band."""
        service = RegionAssignmentService()
        region = create_region("nyeri-highland", -0.4, 37.0, 1800, 2200, AltitudeBandLabel.HIGHLAND)

        assert service._altitude_matches_band(1900, region) is True
        assert service._altitude_matches_band(1800, region) is True  # Lower bound
        assert service._altitude_matches_band(2200, region) is True  # Upper bound

    def test_altitude_outside_band(self) -> None:
        """Test altitude outside region's altitude band."""
        service = RegionAssignmentService()
        region = create_region("nyeri-highland", -0.4, 37.0, 1800, 2200, AltitudeBandLabel.HIGHLAND)

        assert service._altitude_matches_band(1799, region) is False  # Just below
        assert service._altitude_matches_band(2201, region) is False  # Just above
        assert service._altitude_matches_band(1000, region) is False  # Way below


# ============================================================================
# Haversine Distance Tests
# ============================================================================


class TestHaversineDistance:
    """Tests for Haversine distance calculation."""

    def test_same_point_zero_distance(self) -> None:
        """Test distance between same point is zero."""
        service = RegionAssignmentService()
        dist = service._haversine_distance(-0.4, 37.0, -0.4, 37.0)
        assert abs(dist) < 0.001

    def test_known_distance(self) -> None:
        """Test known distance calculation.

        Nairobi (-1.2921, 36.8219) to Mombasa (-4.0435, 39.6682)
        is approximately 440 km.
        """
        service = RegionAssignmentService()
        dist = service._haversine_distance(-1.2921, 36.8219, -4.0435, 39.6682)
        assert 430 < dist < 450  # Allow some tolerance

    def test_distance_is_positive(self) -> None:
        """Test distance is always non-negative."""
        service = RegionAssignmentService()
        dist = service._haversine_distance(10.0, 20.0, -30.0, -40.0)
        assert dist >= 0


# ============================================================================
# Region Assignment Integration Tests
# ============================================================================


class TestRegionAssignment:
    """Integration tests for the full region assignment flow."""

    def test_assign_by_polygon_match(self) -> None:
        """Test assignment by polygon boundary match."""
        service = RegionAssignmentService()

        # Create region with polygon centered at (0, 0)
        region = create_region(
            "test-highland",
            center_lat=0.0,
            center_lng=0.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=True,
        )

        # Point inside polygon with matching altitude
        result = service.assign_region(0.0, 0.0, 1900, [region])
        assert result == "test-highland"

    def test_assign_polygon_altitude_mismatch(self) -> None:
        """Test polygon match but altitude mismatch falls back to nearest."""
        service = RegionAssignmentService()

        # Highland region with polygon
        highland = create_region(
            "test-highland",
            center_lat=0.0,
            center_lng=0.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=True,
        )
        # Midland region nearby without polygon
        midland = create_region(
            "test-midland",
            center_lat=0.1,
            center_lng=0.1,
            min_alt=1400,
            max_alt=1800,
            band_label=AltitudeBandLabel.MIDLAND,
            with_boundary=False,
        )

        # Point inside highland polygon but midland altitude
        # Should fall back and match midland by altitude band + distance
        result = service.assign_region(0.0, 0.0, 1600, [highland, midland])
        assert result == "test-midland"

    def test_assign_by_nearest_center(self) -> None:
        """Test assignment by nearest center when no polygon matches."""
        service = RegionAssignmentService()

        # Two regions without polygons, same altitude band
        region1 = create_region(
            "near-highland",
            center_lat=0.0,
            center_lng=0.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=False,
        )
        region2 = create_region(
            "far-highland",
            center_lat=10.0,
            center_lng=10.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=False,
        )

        # Point closer to region1
        result = service.assign_region(0.5, 0.5, 1900, [region1, region2])
        assert result == "near-highland"

    def test_assign_no_regions(self) -> None:
        """Test assignment with empty region list."""
        service = RegionAssignmentService()
        result = service.assign_region(0.0, 0.0, 1900, [])
        assert result is None

    def test_assign_no_active_regions(self) -> None:
        """Test assignment when all regions are inactive."""
        service = RegionAssignmentService()

        region = create_region(
            "test-highland",
            center_lat=0.0,
            center_lng=0.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
        )
        region.is_active = False

        result = service.assign_region(0.0, 0.0, 1900, [region])
        assert result is None

    def test_assign_fallback_when_no_altitude_match(self) -> None:
        """Test fallback to nearest when no altitude band matches."""
        service = RegionAssignmentService()

        # Only highland region, but lowland altitude
        highland = create_region(
            "test-highland",
            center_lat=0.0,
            center_lng=0.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=False,
        )

        # Very low altitude - should still match nearest
        result = service.assign_region(0.0, 0.0, 500, [highland])
        assert result == "test-highland"

    def test_multiple_regions_polygon_priority(self) -> None:
        """Test that polygon match takes priority over center distance."""
        service = RegionAssignmentService()

        # Region with polygon, further center
        with_polygon = create_region(
            "polygon-highland",
            center_lat=1.0,
            center_lng=1.0,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=True,
        )
        # Region without polygon, closer center but no polygon
        without_polygon = create_region(
            "no-polygon-highland",
            center_lat=0.5,
            center_lng=0.5,
            min_alt=1800,
            max_alt=2200,
            band_label=AltitudeBandLabel.HIGHLAND,
            with_boundary=False,
        )

        # Point inside polygon region's polygon
        result = service.assign_region(1.0, 1.0, 1900, [without_polygon, with_polygon])
        assert result == "polygon-highland"
