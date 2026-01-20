"""Unit tests for Kenya-specific data providers.

Story 0.8.3: Polyfactory Generator Framework
Tests AC #3: Kenya-specific data - Swahili names, +254 phone prefix, Kenya GPS bounds
"""

import sys
from pathlib import Path

# Add tests/demo to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tests" / "demo"))

from generators.kenya_providers import KenyaProvider


class TestKenyaProviderNames:
    """Tests for Kenya name generation."""

    def test_first_name_returns_string(self) -> None:
        """First name should return a non-empty string."""
        name = KenyaProvider.first_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_first_name_is_in_list(self) -> None:
        """First name should be from the predefined list."""
        for _ in range(20):
            name = KenyaProvider.first_name()
            assert name in KenyaProvider.FIRST_NAMES

    def test_last_name_returns_string(self) -> None:
        """Last name should return a non-empty string."""
        name = KenyaProvider.last_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_last_name_is_in_list(self) -> None:
        """Last name should be from the predefined list."""
        for _ in range(20):
            name = KenyaProvider.last_name()
            assert name in KenyaProvider.LAST_NAMES


class TestKenyaProviderPhone:
    """Tests for Kenya phone number generation."""

    def test_phone_number_format(self) -> None:
        """Phone number should follow +254 7XX XXX XXX format."""
        for _ in range(20):
            phone = KenyaProvider.phone_number()
            # Should start with +254
            assert phone.startswith("+254"), f"Phone {phone} should start with +254"
            # Should be 13 characters total (+254 + 9 digits)
            assert len(phone) == 13, f"Phone {phone} should be 13 chars"
            # After +254, should be numeric
            digits = phone[4:]
            assert digits.isdigit(), f"Digits {digits} should be numeric"

    def test_phone_operator_prefix(self) -> None:
        """Phone should use valid Kenya operator prefix."""
        valid_prefixes = ["70", "71", "72", "79", "74", "75", "78", "77"]
        for _ in range(20):
            phone = KenyaProvider.phone_number()
            prefix = phone[4:6]  # Characters after +254
            assert prefix in valid_prefixes, f"Prefix {prefix} should be valid"


class TestKenyaProviderCoordinates:
    """Tests for Kenya GPS coordinate generation."""

    def test_kenya_coordinates_returns_tuple(self) -> None:
        """Coordinates should return (lat, lng, alt) tuple."""
        coords = KenyaProvider.kenya_coordinates()
        assert isinstance(coords, tuple)
        assert len(coords) == 3

    def test_kenya_coordinates_within_bounds(self) -> None:
        """Coordinates should be within Kenya bounds."""
        for _ in range(20):
            lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=False)

            assert KenyaProvider.LATITUDE_MIN <= lat <= KenyaProvider.LATITUDE_MAX, f"Latitude {lat} out of bounds"
            assert KenyaProvider.LONGITUDE_MIN <= lng <= KenyaProvider.LONGITUDE_MAX, f"Longitude {lng} out of bounds"
            assert 0 <= alt <= 2500, f"Altitude {alt} out of bounds"

    def test_tea_region_coordinates(self) -> None:
        """Tea region coordinates should be in highland areas."""
        for _ in range(20):
            lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=True)

            # Should be within one of the tea regions
            in_region = False
            for region in KenyaProvider.TEA_REGIONS:
                if region["lat_min"] <= lat <= region["lat_max"] and region["lng_min"] <= lng <= region["lng_max"]:
                    in_region = True
                    break

            assert in_region, f"Coordinates ({lat}, {lng}) not in any tea region"

    def test_altitude_band_coordinates(self) -> None:
        """Coordinates for altitude band should have correct altitude."""
        for band_name, (alt_min, alt_max) in KenyaProvider.ALTITUDE_BANDS.items():
            lat, lng, alt = KenyaProvider.kenya_coordinates_for_altitude_band(band_name)
            assert alt_min <= alt <= alt_max, f"Altitude {alt} not in {band_name} band ({alt_min}-{alt_max})"


class TestKenyaProviderIdentifiers:
    """Tests for Kenya ID generation."""

    def test_national_id_format(self) -> None:
        """National ID should be 8 digits."""
        for _ in range(20):
            nid = KenyaProvider.national_id()
            assert len(nid) == 8, f"National ID {nid} should be 8 digits"
            assert nid.isdigit(), f"National ID {nid} should be numeric"

    def test_grower_number_format(self) -> None:
        """Grower number should follow GN-XXXXX format."""
        for _ in range(20):
            gn = KenyaProvider.grower_number()
            assert gn.startswith("GN-"), f"Grower number {gn} should start with GN-"
            digits = gn[3:]
            assert len(digits) == 5, f"Grower number {gn} should have 5 digits"
            assert digits.isdigit(), f"Grower number digits {digits} should be numeric"

    def test_tea_region_county(self) -> None:
        """Tea region county should be a valid tea county."""
        valid_counties = [r["county"] for r in KenyaProvider.TEA_REGIONS]
        for _ in range(20):
            county = KenyaProvider.tea_region_county()
            assert county in valid_counties, f"County {county} not a tea county"
