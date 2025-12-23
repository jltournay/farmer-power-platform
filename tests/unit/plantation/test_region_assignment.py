"""Unit tests for region auto-assignment logic."""

from plantation_model.infrastructure.google_elevation import assign_region_from_altitude


class TestRegionAssignment:
    """Tests for assign_region_from_altitude function."""

    # =========================================================================
    # Altitude Band Tests
    # =========================================================================

    def test_highland_altitude_band(self) -> None:
        """Test regions with altitude >= 1800m are classified as highland."""
        # Nyeri coordinates with highland altitude
        region = assign_region_from_altitude(-0.4197, 36.9553, 1950.0)
        assert region.endswith("-highland")

        region = assign_region_from_altitude(-0.4197, 36.9553, 1800.0)
        assert region.endswith("-highland")

        region = assign_region_from_altitude(-0.4197, 36.9553, 2500.0)
        assert region.endswith("-highland")

    def test_midland_altitude_band(self) -> None:
        """Test regions with altitude 1400-1800m are classified as midland."""
        region = assign_region_from_altitude(-0.4197, 36.9553, 1600.0)
        assert region.endswith("-midland")

        region = assign_region_from_altitude(-0.4197, 36.9553, 1400.0)
        assert region.endswith("-midland")

        region = assign_region_from_altitude(-0.4197, 36.9553, 1799.0)
        assert region.endswith("-midland")

    def test_lowland_altitude_band(self) -> None:
        """Test regions with altitude < 1400m are classified as lowland."""
        region = assign_region_from_altitude(-0.4197, 36.9553, 1000.0)
        assert region.endswith("-lowland")

        region = assign_region_from_altitude(-0.4197, 36.9553, 1399.0)
        assert region.endswith("-lowland")

        region = assign_region_from_altitude(-0.4197, 36.9553, 500.0)
        assert region.endswith("-lowland")

    # =========================================================================
    # County Assignment Tests (Kenya tea regions)
    # =========================================================================

    def test_nyeri_county_coordinates(self) -> None:
        """Test coordinates in Nyeri County bounds."""
        # Coordinates within Nyeri bounds: lat -0.6 to 0.0, long 36.5 to 37.5
        region = assign_region_from_altitude(-0.4197, 36.9553, 1950.0)
        assert region.startswith("nyeri-")
        assert region == "nyeri-highland"

    def test_kericho_county_coordinates(self) -> None:
        """Test coordinates in Kericho County bounds."""
        # Coordinates within Kericho bounds: lat -0.8 to 0.0, long 35.0 to 36.0
        region = assign_region_from_altitude(-0.5, 35.5, 1950.0)
        assert region.startswith("kericho-")
        assert region == "kericho-highland"

    def test_nandi_county_coordinates(self) -> None:
        """Test coordinates in Nandi County bounds."""
        # Coordinates within Nandi bounds: lat 0.0 to 0.5, long 34.5 to 35.5
        region = assign_region_from_altitude(0.2, 35.0, 1600.0)
        assert region.startswith("nandi-")
        assert region == "nandi-midland"

    def test_bomet_county_coordinates(self) -> None:
        """Test coordinates in Bomet County bounds."""
        # Coordinates within Bomet bounds: lat -1.0 to -0.3, long 35.0 to 35.8
        # Using lat -0.9 to be outside Kericho (which is -0.8 to 0.0)
        region = assign_region_from_altitude(-0.9, 35.4, 1500.0)
        assert region.startswith("bomet-")
        assert region == "bomet-midland"

    def test_kisii_county_coordinates(self) -> None:
        """Test coordinates in Kisii County bounds."""
        # Coordinates within Kisii bounds: lat -1.0 to -0.4, long 34.5 to 35.0
        region = assign_region_from_altitude(-0.7, 34.8, 1200.0)
        assert region.startswith("kisii-")
        assert region == "kisii-lowland"

    def test_unknown_coordinates_default_to_nyeri(self) -> None:
        """Test coordinates outside known regions default to nyeri."""
        # Coordinates outside all defined tea regions
        region = assign_region_from_altitude(5.0, 40.0, 1950.0)
        assert region.startswith("nyeri-")

        # Another unknown location
        region = assign_region_from_altitude(-5.0, 30.0, 1600.0)
        assert region.startswith("nyeri-")

    # =========================================================================
    # Region ID Format Tests
    # =========================================================================

    def test_region_id_format(self) -> None:
        """Test region ID follows format: {county}-{altitude_band}."""
        region = assign_region_from_altitude(-0.4197, 36.9553, 1950.0)

        # Should contain exactly one hyphen separating county and band
        parts = region.split("-")
        assert len(parts) == 2
        assert parts[0] in ["nyeri", "kericho", "nandi", "bomet", "kisii"]
        assert parts[1] in ["highland", "midland", "lowland"]

    def test_altitude_boundary_highland_midland(self) -> None:
        """Test boundary between highland and midland at 1800m."""
        # At exactly 1800m should be highland
        region = assign_region_from_altitude(-0.4197, 36.9553, 1800.0)
        assert region.endswith("-highland")

        # Just below should be midland
        region = assign_region_from_altitude(-0.4197, 36.9553, 1799.9)
        assert region.endswith("-midland")

    def test_altitude_boundary_midland_lowland(self) -> None:
        """Test boundary between midland and lowland at 1400m."""
        # At exactly 1400m should be midland
        region = assign_region_from_altitude(-0.4197, 36.9553, 1400.0)
        assert region.endswith("-midland")

        # Just below should be lowland
        region = assign_region_from_altitude(-0.4197, 36.9553, 1399.9)
        assert region.endswith("-lowland")
