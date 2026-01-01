"""Unit tests for Factory domain model."""

import pytest
from plantation_model.domain.models import (
    ContactInfo,
    Factory,
    FactoryCreate,
    FactoryUpdate,
    GeoLocation,
    PaymentPolicy,
    PaymentPolicyType,
    QualityThresholds,
)
from pydantic import ValidationError


class TestFactory:
    """Tests for Factory model validation."""

    def test_factory_creation_valid(self) -> None:
        """Test creating a valid factory."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Nyeri Tea Factory",
            code="NTF",
            region_id="nyeri-highland",
            location=GeoLocation(
                latitude=-0.4232,
                longitude=36.9587,
                altitude_meters=1950.0,
            ),
            contact=ContactInfo(
                phone="+254712345678",
                email="factory@ntf.co.ke",
                address="P.O. Box 123, Nyeri",
            ),
            processing_capacity_kg=50000,
        )

        assert factory.id == "KEN-FAC-001"
        assert factory.name == "Nyeri Tea Factory"
        assert factory.code == "NTF"
        assert factory.region_id == "nyeri-highland"
        assert factory.location.latitude == -0.4232
        assert factory.location.longitude == 36.9587
        assert factory.location.altitude_meters == 1950.0
        assert factory.is_active is True
        assert factory.processing_capacity_kg == 50000

    def test_factory_name_validation(self) -> None:
        """Test factory name validation."""
        with pytest.raises(ValidationError):
            Factory(
                id="KEN-FAC-001",
                name="",  # Empty name should fail
                code="NTF",
                region_id="nyeri-highland",
                location=GeoLocation(latitude=0, longitude=0),
            )

    def test_factory_code_validation(self) -> None:
        """Test factory code validation."""
        with pytest.raises(ValidationError):
            Factory(
                id="KEN-FAC-001",
                name="Test Factory",
                code="",  # Empty code should fail
                region_id="nyeri-highland",
                location=GeoLocation(latitude=0, longitude=0),
            )

    def test_factory_processing_capacity_validation(self) -> None:
        """Test processing capacity must be non-negative."""
        with pytest.raises(ValidationError):
            Factory(
                id="KEN-FAC-001",
                name="Test Factory",
                code="TF",
                region_id="test",
                location=GeoLocation(latitude=0, longitude=0),
                processing_capacity_kg=-100,  # Negative should fail
            )

    def test_factory_default_values(self) -> None:
        """Test factory default values."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=0, longitude=0),
        )

        assert factory.is_active is True
        assert factory.processing_capacity_kg == 0
        assert factory.contact.phone == ""
        assert factory.contact.email == ""
        assert factory.contact.address == ""

    def test_factory_model_dump(self) -> None:
        """Test factory serialization with model_dump (Pydantic 2.0)."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=-1.0, longitude=37.0, altitude_meters=1500.0),
        )

        data = factory.model_dump()

        assert data["id"] == "KEN-FAC-001"
        assert data["name"] == "Test Factory"
        assert data["location"]["latitude"] == -1.0
        assert data["location"]["longitude"] == 37.0
        assert data["location"]["altitude_meters"] == 1500.0


class TestFactoryCreate:
    """Tests for FactoryCreate model."""

    def test_factory_create_valid(self) -> None:
        """Test valid factory creation request."""
        create_req = FactoryCreate(
            name="New Factory",
            code="NF",
            region_id="test-region",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
        )

        assert create_req.name == "New Factory"
        assert create_req.code == "NF"
        assert create_req.processing_capacity_kg == 0

    def test_factory_create_with_contact(self) -> None:
        """Test factory creation with contact info."""
        create_req = FactoryCreate(
            name="New Factory",
            code="NF",
            region_id="test-region",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
            contact=ContactInfo(
                phone="+254700000000",
                email="test@factory.co.ke",
            ),
        )

        assert create_req.contact.phone == "+254700000000"


class TestFactoryUpdate:
    """Tests for FactoryUpdate model."""

    def test_factory_update_partial(self) -> None:
        """Test partial factory update."""
        update = FactoryUpdate(name="Updated Name")

        assert update.name == "Updated Name"
        assert update.code is None
        assert update.is_active is None

    def test_factory_update_all_fields(self) -> None:
        """Test updating all fields."""
        update = FactoryUpdate(
            name="Updated Name",
            code="UF",
            processing_capacity_kg=100000,
            is_active=False,
        )

        assert update.name == "Updated Name"
        assert update.code == "UF"
        assert update.processing_capacity_kg == 100000
        assert update.is_active is False


class TestQualityThresholds:
    """Tests for QualityThresholds value object (Story 1.7)."""

    def test_quality_thresholds_defaults(self) -> None:
        """Test default threshold values."""
        thresholds = QualityThresholds()

        assert thresholds.tier_1 == 85.0
        assert thresholds.tier_2 == 70.0
        assert thresholds.tier_3 == 50.0

    def test_quality_thresholds_custom_valid(self) -> None:
        """Test custom threshold values."""
        thresholds = QualityThresholds(tier_1=90.0, tier_2=75.0, tier_3=55.0)

        assert thresholds.tier_1 == 90.0
        assert thresholds.tier_2 == 75.0
        assert thresholds.tier_3 == 55.0

    def test_quality_thresholds_tier2_must_be_less_than_tier1(self) -> None:
        """Test tier_2 must be less than tier_1."""
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholds(tier_1=80.0, tier_2=85.0, tier_3=50.0)

        assert "tier_2" in str(exc_info.value)

    def test_quality_thresholds_tier3_must_be_less_than_tier2(self) -> None:
        """Test tier_3 must be less than tier_2."""
        with pytest.raises(ValidationError) as exc_info:
            QualityThresholds(tier_1=85.0, tier_2=70.0, tier_3=75.0)

        assert "tier_3" in str(exc_info.value)

    def test_quality_thresholds_equal_values_rejected(self) -> None:
        """Test equal tier values are rejected."""
        with pytest.raises(ValidationError):
            QualityThresholds(tier_1=70.0, tier_2=70.0, tier_3=50.0)

    def test_quality_thresholds_range_validation(self) -> None:
        """Test threshold values must be 0-100."""
        with pytest.raises(ValidationError):
            QualityThresholds(tier_1=150.0)  # > 100

        with pytest.raises(ValidationError):
            QualityThresholds(tier_1=-10.0)  # < 0

    def test_factory_with_custom_thresholds(self) -> None:
        """Test factory with custom quality thresholds."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=0, longitude=0),
            quality_thresholds=QualityThresholds(
                tier_1=90.0,
                tier_2=75.0,
                tier_3=60.0,
            ),
        )

        assert factory.quality_thresholds.tier_1 == 90.0
        assert factory.quality_thresholds.tier_2 == 75.0
        assert factory.quality_thresholds.tier_3 == 60.0

    def test_factory_default_thresholds(self) -> None:
        """Test factory uses default thresholds if not specified."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=0, longitude=0),
        )

        assert factory.quality_thresholds.tier_1 == 85.0
        assert factory.quality_thresholds.tier_2 == 70.0
        assert factory.quality_thresholds.tier_3 == 50.0

    def test_factory_create_with_thresholds(self) -> None:
        """Test FactoryCreate with quality thresholds."""
        create_req = FactoryCreate(
            name="New Factory",
            code="NF",
            region_id="test-region",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
            quality_thresholds=QualityThresholds(tier_1=88.0, tier_2=72.0, tier_3=55.0),
        )

        assert create_req.quality_thresholds is not None
        assert create_req.quality_thresholds.tier_1 == 88.0

    def test_factory_update_with_thresholds(self) -> None:
        """Test FactoryUpdate with quality thresholds."""
        update = FactoryUpdate(
            quality_thresholds=QualityThresholds(tier_1=92.0, tier_2=78.0, tier_3=58.0),
        )

        assert update.quality_thresholds is not None
        assert update.quality_thresholds.tier_1 == 92.0


class TestPaymentPolicy:
    """Tests for PaymentPolicy value object (Story 1.9)."""

    def test_payment_policy_defaults(self) -> None:
        """Test default payment policy values."""
        policy = PaymentPolicy()

        assert policy.policy_type == PaymentPolicyType.FEEDBACK_ONLY
        assert policy.tier_1_adjustment == 0.0
        assert policy.tier_2_adjustment == 0.0
        assert policy.tier_3_adjustment == 0.0
        assert policy.below_tier_3_adjustment == 0.0

    def test_payment_policy_custom_valid(self) -> None:
        """Test custom payment policy values."""
        policy = PaymentPolicy(
            policy_type=PaymentPolicyType.SPLIT_PAYMENT,
            tier_1_adjustment=0.15,
            tier_2_adjustment=0.0,
            tier_3_adjustment=-0.05,
            below_tier_3_adjustment=-0.10,
        )

        assert policy.policy_type == PaymentPolicyType.SPLIT_PAYMENT
        assert policy.tier_1_adjustment == 0.15
        assert policy.tier_2_adjustment == 0.0
        assert policy.tier_3_adjustment == -0.05
        assert policy.below_tier_3_adjustment == -0.10

    def test_payment_policy_all_policy_types(self) -> None:
        """Test all payment policy types are valid."""
        for policy_type in PaymentPolicyType:
            policy = PaymentPolicy(policy_type=policy_type)
            assert policy.policy_type == policy_type

    def test_payment_policy_adjustment_upper_bound(self) -> None:
        """Test adjustment values cannot exceed 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentPolicy(tier_1_adjustment=1.5)

        assert "tier_1_adjustment" in str(exc_info.value)

    def test_payment_policy_adjustment_lower_bound(self) -> None:
        """Test adjustment values cannot be less than -1.0."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentPolicy(tier_3_adjustment=-1.5)

        assert "tier_3_adjustment" in str(exc_info.value)

    def test_payment_policy_all_adjustments_boundary_valid(self) -> None:
        """Test boundary values are accepted."""
        policy = PaymentPolicy(
            tier_1_adjustment=1.0,
            tier_2_adjustment=-1.0,
            tier_3_adjustment=0.0,
            below_tier_3_adjustment=-0.5,
        )

        assert policy.tier_1_adjustment == 1.0
        assert policy.tier_2_adjustment == -1.0

    def test_payment_policy_model_dump(self) -> None:
        """Test payment policy serialization with model_dump (Pydantic 2.0)."""
        policy = PaymentPolicy(
            policy_type=PaymentPolicyType.WEEKLY_BONUS,
            tier_1_adjustment=0.20,
        )

        data = policy.model_dump()

        assert data["policy_type"] == "weekly_bonus"
        assert data["tier_1_adjustment"] == 0.20

    def test_payment_policy_enum_values(self) -> None:
        """Test PaymentPolicyType enum string values."""
        assert PaymentPolicyType.SPLIT_PAYMENT.value == "split_payment"
        assert PaymentPolicyType.WEEKLY_BONUS.value == "weekly_bonus"
        assert PaymentPolicyType.DELAYED_PAYMENT.value == "delayed_payment"
        assert PaymentPolicyType.FEEDBACK_ONLY.value == "feedback_only"


class TestFactoryWithPaymentPolicy:
    """Tests for Factory with PaymentPolicy (Story 1.9)."""

    def test_factory_default_payment_policy(self) -> None:
        """Test factory uses default payment policy if not specified."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=0, longitude=0),
        )

        assert factory.payment_policy.policy_type == PaymentPolicyType.FEEDBACK_ONLY
        assert factory.payment_policy.tier_1_adjustment == 0.0
        assert factory.payment_policy.tier_2_adjustment == 0.0
        assert factory.payment_policy.tier_3_adjustment == 0.0
        assert factory.payment_policy.below_tier_3_adjustment == 0.0

    def test_factory_with_custom_payment_policy(self) -> None:
        """Test factory with custom payment policy."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=0, longitude=0),
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
        assert factory.payment_policy.below_tier_3_adjustment == -0.10

    def test_factory_create_with_payment_policy(self) -> None:
        """Test FactoryCreate with payment policy."""
        create_req = FactoryCreate(
            name="New Factory",
            code="NF",
            region_id="test-region",
            location=GeoLocation(latitude=-0.5, longitude=36.5),
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType.WEEKLY_BONUS,
                tier_1_adjustment=0.10,
            ),
        )

        assert create_req.payment_policy is not None
        assert create_req.payment_policy.policy_type == PaymentPolicyType.WEEKLY_BONUS

    def test_factory_update_with_payment_policy(self) -> None:
        """Test FactoryUpdate with payment policy."""
        update = FactoryUpdate(
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType.DELAYED_PAYMENT,
                tier_1_adjustment=0.20,
            ),
        )

        assert update.payment_policy is not None
        assert update.payment_policy.policy_type == PaymentPolicyType.DELAYED_PAYMENT

    def test_factory_model_dump_includes_payment_policy(self) -> None:
        """Test factory serialization includes payment policy."""
        factory = Factory(
            id="KEN-FAC-001",
            name="Test Factory",
            code="TF",
            region_id="test",
            location=GeoLocation(latitude=0, longitude=0),
            payment_policy=PaymentPolicy(
                policy_type=PaymentPolicyType.SPLIT_PAYMENT,
                tier_1_adjustment=0.15,
            ),
        )

        data = factory.model_dump()

        assert "payment_policy" in data
        assert data["payment_policy"]["policy_type"] == "split_payment"
        assert data["payment_policy"]["tier_1_adjustment"] == 0.15
