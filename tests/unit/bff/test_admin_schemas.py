"""Tests for Admin API schemas.

Tests validation rules for admin CRUD schemas.
"""

import pytest
from bff.api.schemas.admin.factory_schemas import QualityThresholdsAPI
from bff.api.schemas.admin.farmer_schemas import (
    AdminFarmerCreateRequest,
    AdminFarmerUpdateRequest,
)
from pydantic import ValidationError


class TestQualityThresholdsAPI:
    """Tests for quality threshold validation."""

    def test_valid_thresholds(self):
        """Test valid threshold values."""
        thresholds = QualityThresholdsAPI(tier_1=85.0, tier_2=70.0, tier_3=50.0)
        assert thresholds.tier_1 == 85.0
        assert thresholds.tier_2 == 70.0
        assert thresholds.tier_3 == 50.0

    def test_tier_2_must_be_less_than_tier_1(self):
        """Test tier_2 >= tier_1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholdsAPI(tier_1=85.0, tier_2=85.0, tier_3=50.0)
        assert "tier_2" in str(exc_info.value)

    def test_tier_3_must_be_less_than_tier_2(self):
        """Test tier_3 >= tier_2 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholdsAPI(tier_1=85.0, tier_2=70.0, tier_3=70.0)
        assert "tier_3" in str(exc_info.value)

    def test_default_values(self):
        """Test default threshold values."""
        thresholds = QualityThresholdsAPI()
        assert thresholds.tier_1 == 85.0
        assert thresholds.tier_2 == 70.0
        assert thresholds.tier_3 == 50.0


class TestAdminFarmerCreateRequest:
    """Tests for farmer creation validation."""

    def test_valid_create_request(self):
        """Test valid farmer creation request."""
        request = AdminFarmerCreateRequest(
            first_name="Wanjiku",
            last_name="Muthoni",
            phone="+254712345678",
            national_id="12345678",
            collection_point_id="nyeri-highland-cp-001",
            farm_size_hectares=1.5,
            latitude=-0.4197,
            longitude=36.9553,
        )
        assert request.first_name == "Wanjiku"
        assert request.phone == "+254712345678"

    def test_phone_must_start_with_plus(self):
        """Test phone number must be E.164 format."""
        with pytest.raises(ValidationError) as exc_info:
            AdminFarmerCreateRequest(
                first_name="Wanjiku",
                last_name="Muthoni",
                phone="254712345678",  # Missing +
                national_id="12345678",
                collection_point_id="nyeri-highland-cp-001",
                farm_size_hectares=1.5,
                latitude=-0.4197,
                longitude=36.9553,
            )
        assert "E.164" in str(exc_info.value)

    def test_farm_size_min_value(self):
        """Test farm size minimum constraint."""
        with pytest.raises(ValidationError):
            AdminFarmerCreateRequest(
                first_name="Wanjiku",
                last_name="Muthoni",
                phone="+254712345678",
                national_id="12345678",
                collection_point_id="nyeri-highland-cp-001",
                farm_size_hectares=0.001,  # Too small
                latitude=-0.4197,
                longitude=36.9553,
            )


class TestAdminFarmerUpdateRequest:
    """Tests for farmer update validation."""

    def test_all_fields_optional(self):
        """Test all fields are optional for update."""
        request = AdminFarmerUpdateRequest()
        assert request.first_name is None
        assert request.phone is None
        assert request.is_active is None

    def test_phone_validation_when_provided(self):
        """Test phone validation only applies when provided."""
        # Valid phone
        request = AdminFarmerUpdateRequest(phone="+254712345678")
        assert request.phone == "+254712345678"

        # Invalid phone
        with pytest.raises(ValidationError):
            AdminFarmerUpdateRequest(phone="invalid")
