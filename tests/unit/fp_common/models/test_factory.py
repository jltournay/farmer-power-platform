"""Unit tests for Factory model in fp_common."""

import pytest
from fp_common.models import Factory, FactoryCreate, FactoryUpdate
from fp_common.models.value_objects import (
    ContactInfo,
    GeoLocation,
    PaymentPolicy,
    PaymentPolicyType,
    QualityThresholds,
)
from pydantic import ValidationError


class TestFactoryModel:
    """Tests for Factory model."""

    @pytest.fixture
    def valid_factory_data(self):
        """Valid factory data for testing."""
        return {
            "id": "KEN-FAC-001",
            "name": "Nyeri Tea Factory",
            "code": "NTF",
            "region_id": "nyeri-highland",
            "location": GeoLocation(latitude=-0.4232, longitude=36.9587, altitude_meters=1950.0),
        }

    def test_factory_creation_with_required_fields(self, valid_factory_data):
        """Factory model accepts valid required fields."""
        factory = Factory(**valid_factory_data)
        assert factory.id == "KEN-FAC-001"
        assert factory.name == "Nyeri Tea Factory"
        assert factory.code == "NTF"
        assert factory.region_id == "nyeri-highland"

    def test_factory_default_values(self, valid_factory_data):
        """Factory model has correct default values."""
        factory = Factory(**valid_factory_data)
        assert factory.is_active is True
        assert factory.processing_capacity_kg == 0
        assert factory.quality_thresholds.tier_1 == 85.0
        assert factory.quality_thresholds.tier_2 == 70.0
        assert factory.quality_thresholds.tier_3 == 50.0
        assert factory.payment_policy.policy_type == PaymentPolicyType.FEEDBACK_ONLY

    def test_factory_with_quality_thresholds(self, valid_factory_data):
        """Factory model accepts custom quality thresholds."""
        factory = Factory(
            **valid_factory_data,
            quality_thresholds=QualityThresholds(tier_1=90.0, tier_2=75.0, tier_3=55.0),
        )
        assert factory.quality_thresholds.tier_1 == 90.0
        assert factory.quality_thresholds.tier_2 == 75.0
        assert factory.quality_thresholds.tier_3 == 55.0

    def test_factory_with_payment_policy(self, valid_factory_data):
        """Factory model accepts payment policy."""
        factory = Factory(
            **valid_factory_data,
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType.SPLIT_PAYMENT,
                tier_1_adjustment=0.15,
                tier_2_adjustment=0.0,
                tier_3_adjustment=-0.05,
                below_tier_3_adjustment=-0.10,
            ),
        )
        assert factory.payment_policy.policy_type == PaymentPolicyType.SPLIT_PAYMENT
        assert factory.payment_policy.tier_1_adjustment == 0.15

    def test_factory_with_contact_info(self, valid_factory_data):
        """Factory model accepts contact info."""
        factory = Factory(
            **valid_factory_data,
            contact=ContactInfo(
                phone="+254712345678",
                email="factory@ntf.co.ke",
                address="P.O. Box 123, Nyeri",
            ),
        )
        assert factory.contact.phone == "+254712345678"
        assert factory.contact.email == "factory@ntf.co.ke"

    def test_factory_validation_rejects_empty_name(self, valid_factory_data):
        """Factory model rejects empty name."""
        valid_factory_data["name"] = ""
        with pytest.raises(ValidationError) as exc_info:
            Factory(**valid_factory_data)
        assert "name" in str(exc_info.value)

    def test_factory_validation_rejects_empty_code(self, valid_factory_data):
        """Factory model rejects empty code."""
        valid_factory_data["code"] = ""
        with pytest.raises(ValidationError) as exc_info:
            Factory(**valid_factory_data)
        assert "code" in str(exc_info.value)

    def test_factory_validation_rejects_negative_capacity(self, valid_factory_data):
        """Factory model rejects negative processing capacity."""
        valid_factory_data["processing_capacity_kg"] = -100
        with pytest.raises(ValidationError) as exc_info:
            Factory(**valid_factory_data)
        assert "processing_capacity_kg" in str(exc_info.value)

    def test_factory_model_dump_produces_dict(self, valid_factory_data):
        """model_dump() produces a dictionary."""
        factory = Factory(**valid_factory_data)
        data = factory.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "KEN-FAC-001"
        assert data["name"] == "Nyeri Tea Factory"


class TestQualityThresholds:
    """Tests for QualityThresholds value object."""

    def test_quality_thresholds_defaults(self):
        """QualityThresholds has correct defaults."""
        thresholds = QualityThresholds()
        assert thresholds.tier_1 == 85.0
        assert thresholds.tier_2 == 70.0
        assert thresholds.tier_3 == 50.0

    def test_quality_thresholds_custom_values(self):
        """QualityThresholds accepts custom values."""
        thresholds = QualityThresholds(tier_1=90.0, tier_2=75.0, tier_3=60.0)
        assert thresholds.tier_1 == 90.0
        assert thresholds.tier_2 == 75.0
        assert thresholds.tier_3 == 60.0

    def test_quality_thresholds_tier_2_must_be_less_than_tier_1(self):
        """tier_2 must be less than tier_1."""
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholds(tier_1=80.0, tier_2=85.0, tier_3=50.0)
        assert "tier_2" in str(exc_info.value)

    def test_quality_thresholds_tier_3_must_be_less_than_tier_2(self):
        """tier_3 must be less than tier_2."""
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholds(tier_1=85.0, tier_2=70.0, tier_3=75.0)
        assert "tier_3" in str(exc_info.value)


class TestPaymentPolicy:
    """Tests for PaymentPolicy value object."""

    def test_payment_policy_defaults(self):
        """PaymentPolicy has correct defaults."""
        policy = PaymentPolicy()
        assert policy.policy_type == PaymentPolicyType.FEEDBACK_ONLY
        assert policy.tier_1_adjustment == 0.0
        assert policy.tier_2_adjustment == 0.0
        assert policy.tier_3_adjustment == 0.0
        assert policy.below_tier_3_adjustment == 0.0

    def test_payment_policy_split_payment(self):
        """PaymentPolicy accepts split payment configuration."""
        policy = PaymentPolicy(
            policy_type=PaymentPolicyType.SPLIT_PAYMENT,
            tier_1_adjustment=0.15,
            tier_2_adjustment=0.05,
            tier_3_adjustment=-0.05,
            below_tier_3_adjustment=-0.15,
        )
        assert policy.policy_type == PaymentPolicyType.SPLIT_PAYMENT
        assert policy.tier_1_adjustment == 0.15
        assert policy.below_tier_3_adjustment == -0.15

    def test_payment_policy_adjustment_bounds(self):
        """PaymentPolicy adjustments must be within -1.0 to 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentPolicy(tier_1_adjustment=1.5)
        assert "tier_1_adjustment" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            PaymentPolicy(tier_3_adjustment=-1.5)
        assert "tier_3_adjustment" in str(exc_info.value)


class TestFactoryCreate:
    """Tests for FactoryCreate model."""

    def test_factory_create_valid(self):
        """FactoryCreate accepts valid data."""
        create_data = FactoryCreate(
            name="New Factory",
            code="NF",
            region_id="nyeri-highland",
            location=GeoLocation(latitude=-0.4232, longitude=36.9587, altitude_meters=1950.0),
        )
        assert create_data.name == "New Factory"
        assert create_data.code == "NF"

    def test_factory_create_with_optional_fields(self):
        """FactoryCreate accepts optional fields."""
        create_data = FactoryCreate(
            name="New Factory",
            code="NF",
            region_id="nyeri-highland",
            location=GeoLocation(latitude=-0.4232, longitude=36.9587, altitude_meters=1950.0),
            processing_capacity_kg=50000,
            quality_thresholds=QualityThresholds(tier_1=90.0, tier_2=75.0, tier_3=55.0),
        )
        assert create_data.processing_capacity_kg == 50000
        assert create_data.quality_thresholds.tier_1 == 90.0


class TestFactoryUpdate:
    """Tests for FactoryUpdate model."""

    def test_factory_update_all_optional(self):
        """FactoryUpdate fields are all optional."""
        update = FactoryUpdate()
        assert update.name is None
        assert update.code is None
        assert update.location is None
        assert update.contact is None
        assert update.processing_capacity_kg is None

    def test_factory_update_partial(self):
        """FactoryUpdate accepts partial updates."""
        update = FactoryUpdate(name="Updated Factory", is_active=False)
        assert update.name == "Updated Factory"
        assert update.is_active is False
        assert update.code is None

    def test_factory_update_quality_thresholds(self):
        """FactoryUpdate accepts quality threshold updates."""
        update = FactoryUpdate(quality_thresholds=QualityThresholds(tier_1=88.0, tier_2=72.0, tier_3=52.0))
        assert update.quality_thresholds.tier_1 == 88.0
