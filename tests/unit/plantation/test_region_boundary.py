"""Unit tests for RegionBoundary and related value objects (Story 1.10).

Tests for Coordinate, PolygonRing, and RegionBoundary classes that support
polygon-based region definition for accurate farmer-to-region assignment.
"""

import pytest
from fp_common.models.value_objects import (
    GPS,
    AltitudeBand,
    AltitudeBandLabel,
    Coordinate,
    Geography,
    PolygonRing,
    RegionBoundary,
)
from pydantic import ValidationError

# ============================================================================
# Coordinate Value Object Tests
# ============================================================================


class TestCoordinate:
    """Tests for Coordinate value object."""

    def test_coordinate_valid(self) -> None:
        """Test creating a valid coordinate."""
        coord = Coordinate(longitude=36.9553, latitude=-0.4197)
        assert coord.longitude == 36.9553
        assert coord.latitude == -0.4197

    def test_coordinate_valid_extremes(self) -> None:
        """Test valid extreme coordinate values."""
        # Valid at boundaries
        coord1 = Coordinate(longitude=-180, latitude=-90)
        assert coord1.longitude == -180
        assert coord1.latitude == -90

        coord2 = Coordinate(longitude=180, latitude=90)
        assert coord2.longitude == 180
        assert coord2.latitude == 90

    def test_coordinate_longitude_too_low(self) -> None:
        """Test longitude below -180 fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Coordinate(longitude=-181, latitude=0)
        assert "longitude" in str(exc_info.value).lower()

    def test_coordinate_longitude_too_high(self) -> None:
        """Test longitude above 180 fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Coordinate(longitude=181, latitude=0)
        assert "longitude" in str(exc_info.value).lower()

    def test_coordinate_latitude_too_low(self) -> None:
        """Test latitude below -90 fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Coordinate(longitude=0, latitude=-91)
        assert "latitude" in str(exc_info.value).lower()

    def test_coordinate_latitude_too_high(self) -> None:
        """Test latitude above 90 fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            Coordinate(longitude=0, latitude=91)
        assert "latitude" in str(exc_info.value).lower()

    def test_coordinate_origin(self) -> None:
        """Test coordinate at origin (0, 0)."""
        coord = Coordinate(longitude=0, latitude=0)
        assert coord.longitude == 0
        assert coord.latitude == 0


# ============================================================================
# PolygonRing Value Object Tests
# ============================================================================


def create_valid_ring(num_points: int = 4) -> list[Coordinate]:
    """Create a list of coordinates forming a valid closed ring (triangle)."""
    # Simple triangle in Kenya tea region
    points = [
        Coordinate(longitude=36.9, latitude=-0.4),  # Point 1
        Coordinate(longitude=37.0, latitude=-0.4),  # Point 2
        Coordinate(longitude=36.95, latitude=-0.3),  # Point 3
        Coordinate(longitude=36.9, latitude=-0.4),  # Closing point (same as first)
    ]
    return points[:num_points] if num_points < 4 else points


class TestPolygonRing:
    """Tests for PolygonRing value object."""

    def test_polygon_ring_valid_triangle(self) -> None:
        """Test creating a valid polygon ring (triangle with closing point)."""
        ring = PolygonRing(points=create_valid_ring())
        assert len(ring.points) == 4
        assert ring.points[0].longitude == ring.points[-1].longitude
        assert ring.points[0].latitude == ring.points[-1].latitude

    def test_polygon_ring_valid_complex(self) -> None:
        """Test creating a valid polygon ring with more points."""
        points = [
            Coordinate(longitude=36.9, latitude=-0.4),
            Coordinate(longitude=37.0, latitude=-0.4),
            Coordinate(longitude=37.1, latitude=-0.3),
            Coordinate(longitude=37.0, latitude=-0.2),
            Coordinate(longitude=36.9, latitude=-0.3),
            Coordinate(longitude=36.9, latitude=-0.4),  # Closing point
        ]
        ring = PolygonRing(points=points)
        assert len(ring.points) == 6

    def test_polygon_ring_too_few_points(self) -> None:
        """Test polygon ring with fewer than 4 points fails."""
        with pytest.raises(ValidationError) as exc_info:
            PolygonRing(
                points=[
                    Coordinate(longitude=36.9, latitude=-0.4),
                    Coordinate(longitude=37.0, latitude=-0.4),
                    Coordinate(longitude=36.9, latitude=-0.4),  # Only 3 points
                ]
            )
        # Should fail min_length validation
        assert "points" in str(exc_info.value).lower() or "length" in str(exc_info.value).lower()

    def test_polygon_ring_unclosed_fails(self) -> None:
        """Test polygon ring that is not closed fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            PolygonRing(
                points=[
                    Coordinate(longitude=36.9, latitude=-0.4),
                    Coordinate(longitude=37.0, latitude=-0.4),
                    Coordinate(longitude=36.95, latitude=-0.3),
                    Coordinate(longitude=36.95, latitude=-0.35),  # Different from first point
                ]
            )
        assert "closed" in str(exc_info.value).lower()

    def test_polygon_ring_unclosed_different_longitude(self) -> None:
        """Test ring with same latitude but different longitude fails."""
        with pytest.raises(ValidationError) as exc_info:
            PolygonRing(
                points=[
                    Coordinate(longitude=36.9, latitude=-0.4),
                    Coordinate(longitude=37.0, latitude=-0.4),
                    Coordinate(longitude=36.95, latitude=-0.3),
                    Coordinate(longitude=36.91, latitude=-0.4),  # Same lat, different lng
                ]
            )
        assert "closed" in str(exc_info.value).lower()

    def test_polygon_ring_unclosed_different_latitude(self) -> None:
        """Test ring with same longitude but different latitude fails."""
        with pytest.raises(ValidationError) as exc_info:
            PolygonRing(
                points=[
                    Coordinate(longitude=36.9, latitude=-0.4),
                    Coordinate(longitude=37.0, latitude=-0.4),
                    Coordinate(longitude=36.95, latitude=-0.3),
                    Coordinate(longitude=36.9, latitude=-0.41),  # Same lng, different lat
                ]
            )
        assert "closed" in str(exc_info.value).lower()

    def test_polygon_ring_empty_fails(self) -> None:
        """Test polygon ring with empty points list fails."""
        with pytest.raises(ValidationError):
            PolygonRing(points=[])


# ============================================================================
# RegionBoundary Value Object Tests
# ============================================================================


def create_valid_boundary() -> RegionBoundary:
    """Create a valid RegionBoundary for testing."""
    return RegionBoundary(
        type="Polygon",
        rings=[PolygonRing(points=create_valid_ring())],
    )


class TestRegionBoundary:
    """Tests for RegionBoundary value object."""

    def test_region_boundary_valid(self) -> None:
        """Test creating a valid region boundary."""
        boundary = create_valid_boundary()
        assert boundary.type == "Polygon"
        assert len(boundary.rings) == 1

    def test_region_boundary_type_default(self) -> None:
        """Test region boundary type defaults to 'Polygon'."""
        boundary = RegionBoundary(rings=[PolygonRing(points=create_valid_ring())])
        assert boundary.type == "Polygon"

    def test_region_boundary_invalid_type(self) -> None:
        """Test region boundary with invalid type fails."""
        with pytest.raises(ValidationError) as exc_info:
            RegionBoundary(
                type="MultiPolygon",  # Only "Polygon" is allowed
                rings=[PolygonRing(points=create_valid_ring())],
            )
        assert "type" in str(exc_info.value).lower() or "input" in str(exc_info.value).lower()

    def test_region_boundary_no_rings_fails(self) -> None:
        """Test region boundary with no rings fails."""
        with pytest.raises(ValidationError):
            RegionBoundary(type="Polygon", rings=[])

    def test_region_boundary_exterior_property(self) -> None:
        """Test exterior property returns first ring."""
        boundary = create_valid_boundary()
        exterior = boundary.exterior
        assert exterior == boundary.rings[0]

    def test_region_boundary_holes_property_empty(self) -> None:
        """Test holes property returns empty list for simple polygon."""
        boundary = create_valid_boundary()
        assert boundary.holes == []

    def test_region_boundary_with_hole(self) -> None:
        """Test region boundary with interior ring (hole)."""
        # Exterior ring (larger triangle)
        exterior_points = [
            Coordinate(longitude=36.8, latitude=-0.5),
            Coordinate(longitude=37.2, latitude=-0.5),
            Coordinate(longitude=37.0, latitude=-0.2),
            Coordinate(longitude=36.8, latitude=-0.5),
        ]
        # Interior ring (hole - smaller triangle inside)
        hole_points = [
            Coordinate(longitude=36.95, latitude=-0.45),
            Coordinate(longitude=37.05, latitude=-0.45),
            Coordinate(longitude=37.0, latitude=-0.35),
            Coordinate(longitude=36.95, latitude=-0.45),
        ]

        boundary = RegionBoundary(
            rings=[
                PolygonRing(points=exterior_points),
                PolygonRing(points=hole_points),
            ]
        )

        assert len(boundary.rings) == 2
        assert len(boundary.holes) == 1
        assert boundary.exterior == boundary.rings[0]
        assert boundary.holes[0] == boundary.rings[1]

    def test_region_boundary_serialization(self) -> None:
        """Test region boundary serialization with model_dump."""
        boundary = create_valid_boundary()
        data = boundary.model_dump()

        assert data["type"] == "Polygon"
        assert len(data["rings"]) == 1
        assert len(data["rings"][0]["points"]) == 4
        assert data["rings"][0]["points"][0]["longitude"] == 36.9
        assert data["rings"][0]["points"][0]["latitude"] == -0.4


# ============================================================================
# Geography Extension Tests (Story 1.10)
# ============================================================================


class TestGeographyWithBoundary:
    """Tests for extended Geography with polygon boundary support."""

    def test_geography_without_boundary(self) -> None:
        """Test Geography works without boundary (backward compatibility)."""
        geo = Geography(
            center_gps=GPS(lat=-0.4197, lng=36.9553),
            radius_km=25,
            altitude_band=AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=AltitudeBandLabel.HIGHLAND,
            ),
        )
        assert geo.boundary is None
        assert geo.area_km2 is None
        assert geo.perimeter_km is None

    def test_geography_with_boundary(self) -> None:
        """Test Geography with boundary."""
        boundary = create_valid_boundary()
        geo = Geography(
            center_gps=GPS(lat=-0.4197, lng=36.9553),
            radius_km=25,
            altitude_band=AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=AltitudeBandLabel.HIGHLAND,
            ),
            boundary=boundary,
        )
        assert geo.boundary is not None
        assert geo.boundary.type == "Polygon"

    def test_geography_with_computed_values(self) -> None:
        """Test Geography with area and perimeter values."""
        boundary = create_valid_boundary()
        geo = Geography(
            center_gps=GPS(lat=-0.4197, lng=36.9553),
            radius_km=25,
            altitude_band=AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=AltitudeBandLabel.HIGHLAND,
            ),
            boundary=boundary,
            area_km2=150.5,
            perimeter_km=50.2,
        )
        assert geo.area_km2 == 150.5
        assert geo.perimeter_km == 50.2

    def test_geography_area_negative_fails(self) -> None:
        """Test area_km2 must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            Geography(
                center_gps=GPS(lat=-0.4197, lng=36.9553),
                radius_km=25,
                altitude_band=AltitudeBand(
                    min_meters=1800,
                    max_meters=2200,
                    label=AltitudeBandLabel.HIGHLAND,
                ),
                area_km2=-10.0,
            )
        assert "area_km2" in str(exc_info.value).lower()

    def test_geography_perimeter_negative_fails(self) -> None:
        """Test perimeter_km must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            Geography(
                center_gps=GPS(lat=-0.4197, lng=36.9553),
                radius_km=25,
                altitude_band=AltitudeBand(
                    min_meters=1800,
                    max_meters=2200,
                    label=AltitudeBandLabel.HIGHLAND,
                ),
                perimeter_km=-5.0,
            )
        assert "perimeter_km" in str(exc_info.value).lower()

    def test_geography_with_boundary_serialization(self) -> None:
        """Test Geography serialization with boundary."""
        boundary = create_valid_boundary()
        geo = Geography(
            center_gps=GPS(lat=-0.4197, lng=36.9553),
            radius_km=25,
            altitude_band=AltitudeBand(
                min_meters=1800,
                max_meters=2200,
                label=AltitudeBandLabel.HIGHLAND,
            ),
            boundary=boundary,
            area_km2=150.5,
            perimeter_km=50.2,
        )
        data = geo.model_dump()

        assert data["center_gps"]["lat"] == -0.4197
        assert data["boundary"]["type"] == "Polygon"
        assert data["area_km2"] == 150.5
        assert data["perimeter_km"] == 50.2
