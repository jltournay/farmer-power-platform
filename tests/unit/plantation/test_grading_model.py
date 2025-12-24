"""Unit tests for GradingModel domain model."""

import pytest
from pydantic import ValidationError

from plantation_model.domain.models.grading_model import (
    ConditionalReject,
    GradeRules,
    GradingAttribute,
    GradingModel,
    GradingType,
)


class TestGradingType:
    """Tests for GradingType enum."""

    def test_grading_type_enum_values(self) -> None:
        """Test GradingType enum string values."""
        assert GradingType.BINARY.value == "binary"
        assert GradingType.TERNARY.value == "ternary"
        assert GradingType.MULTI_LEVEL.value == "multi_level"


class TestGradingAttribute:
    """Tests for GradingAttribute model."""

    def test_grading_attribute_valid(self) -> None:
        """Test creating a valid grading attribute."""
        attr = GradingAttribute(
            num_classes=3,
            classes=["class_a", "class_b", "class_c"],
        )
        assert attr.num_classes == 3
        assert len(attr.classes) == 3
        assert attr.classes[0] == "class_a"

    def test_grading_attribute_minimum_classes(self) -> None:
        """Test grading attribute needs at least 2 classes."""
        attr = GradingAttribute(num_classes=2, classes=["yes", "no"])
        assert attr.num_classes == 2
        assert len(attr.classes) == 2

    def test_grading_attribute_classes_too_few(self) -> None:
        """Test grading attribute fails with less than 2 classes."""
        with pytest.raises(ValidationError):
            GradingAttribute(num_classes=1, classes=["only_one"])

    def test_grading_attribute_num_classes_too_small(self) -> None:
        """Test num_classes must be at least 2."""
        with pytest.raises(ValidationError):
            GradingAttribute(num_classes=1, classes=["a", "b"])


class TestConditionalReject:
    """Tests for ConditionalReject model."""

    def test_conditional_reject_valid(self) -> None:
        """Test creating a valid conditional reject rule."""
        rule = ConditionalReject(
            if_attribute="leaf_type",
            if_value="banji",
            then_attribute="banji_hardness",
            reject_values=["hard"],
        )
        assert rule.if_attribute == "leaf_type"
        assert rule.if_value == "banji"
        assert rule.then_attribute == "banji_hardness"
        assert "hard" in rule.reject_values


class TestGradeRules:
    """Tests for GradeRules model."""

    def test_grade_rules_empty(self) -> None:
        """Test creating grade rules with defaults."""
        rules = GradeRules()
        assert rules.reject_conditions == {}
        assert rules.conditional_reject == []

    def test_grade_rules_with_reject_conditions(self) -> None:
        """Test grade rules with reject conditions."""
        rules = GradeRules(
            reject_conditions={
                "leaf_type": ["three_plus_leaves_bud", "coarse_leaf"],
            }
        )
        assert "leaf_type" in rules.reject_conditions
        assert "coarse_leaf" in rules.reject_conditions["leaf_type"]

    def test_grade_rules_with_conditional_reject(self) -> None:
        """Test grade rules with conditional rejection."""
        conditional = ConditionalReject(
            if_attribute="leaf_type",
            if_value="banji",
            then_attribute="banji_hardness",
            reject_values=["hard"],
        )
        rules = GradeRules(conditional_reject=[conditional])
        assert len(rules.conditional_reject) == 1
        assert rules.conditional_reject[0].if_attribute == "leaf_type"


class TestGradingModel:
    """Tests for GradingModel model."""

    def test_grading_model_valid_binary(self) -> None:
        """Test creating a valid binary grading model."""
        model = GradingModel(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            regulatory_authority="Tea Board of Kenya (TBK)",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=GradingType.BINARY,
            attributes={
                "leaf_type": GradingAttribute(
                    num_classes=7,
                    classes=[
                        "bud",
                        "one_leaf_bud",
                        "two_leaves_bud",
                        "three_plus_leaves_bud",
                        "single_soft_leaf",
                        "coarse_leaf",
                        "banji",
                    ],
                ),
            },
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        )

        assert model.model_id == "tbk_kenya_tea_v1"
        assert model.model_version == "1.0.0"
        assert model.grading_type == GradingType.BINARY
        assert "leaf_type" in model.attributes
        assert model.grade_labels["ACCEPT"] == "Primary"

    def test_grading_model_with_rules(self) -> None:
        """Test grading model with grade rules."""
        model = GradingModel(
            model_id="tbk_kenya_tea_v1",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Kenya_TBK",
            grading_type=GradingType.BINARY,
            attributes={
                "leaf_type": GradingAttribute(
                    num_classes=3,
                    classes=["good", "medium", "bad"],
                ),
            },
            grade_rules=GradeRules(
                reject_conditions={"leaf_type": ["bad"]},
            ),
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        )

        assert "leaf_type" in model.grade_rules.reject_conditions
        assert "bad" in model.grade_rules.reject_conditions["leaf_type"]

    def test_grading_model_with_factory_assignments(self) -> None:
        """Test grading model active at specific factories."""
        model = GradingModel(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=GradingType.BINARY,
            attributes={
                "quality": GradingAttribute(
                    num_classes=2,
                    classes=["good", "bad"],
                ),
            },
            grade_labels={"ACCEPT": "Good", "REJECT": "Bad"},
            active_at_factory=["factory-001", "factory-002"],
        )

        assert "factory-001" in model.active_at_factory
        assert "factory-002" in model.active_at_factory

    def test_grading_model_get_all_attribute_classes(self) -> None:
        """Test getting all attribute classes."""
        model = GradingModel(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=GradingType.BINARY,
            attributes={
                "leaf_type": GradingAttribute(
                    num_classes=3,
                    classes=["a", "b", "c"],
                ),
                "hardness": GradingAttribute(
                    num_classes=2,
                    classes=["soft", "hard"],
                ),
            },
            grade_labels={"ACCEPT": "Good", "REJECT": "Bad"},
        )

        all_classes = model.get_all_attribute_classes()
        assert "leaf_type" in all_classes
        assert "hardness" in all_classes
        assert all_classes["leaf_type"] == ["a", "b", "c"]
        assert all_classes["hardness"] == ["soft", "hard"]

    def test_grading_model_get_grade_display_label(self) -> None:
        """Test getting grade display label."""
        model = GradingModel(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=GradingType.BINARY,
            attributes={
                "quality": GradingAttribute(
                    num_classes=2,
                    classes=["good", "bad"],
                ),
            },
            grade_labels={"ACCEPT": "Primary", "REJECT": "Secondary"},
        )

        assert model.get_grade_display_label("ACCEPT") == "Primary"
        assert model.get_grade_display_label("REJECT") == "Secondary"
        # Unknown label returns itself
        assert model.get_grade_display_label("UNKNOWN") == "UNKNOWN"

    def test_grading_model_ternary_type(self) -> None:
        """Test creating a ternary grading model."""
        model = GradingModel(
            model_id="coffee_ternary",
            model_version="1.0.0",
            crops_name="Coffee",
            market_name="Ethiopia",
            grading_type=GradingType.TERNARY,
            attributes={
                "bean_quality": GradingAttribute(
                    num_classes=3,
                    classes=["premium", "standard", "reject"],
                ),
            },
            grade_labels={
                "PREMIUM": "Grade A",
                "STANDARD": "Grade B",
                "REJECT": "Grade C",
            },
        )

        assert model.grading_type == GradingType.TERNARY

    def test_grading_model_multi_level_type(self) -> None:
        """Test creating a multi-level grading model."""
        model = GradingModel(
            model_id="multi_level_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Custom",
            grading_type=GradingType.MULTI_LEVEL,
            attributes={
                "overall": GradingAttribute(
                    num_classes=4,
                    classes=["excellent", "good", "fair", "poor"],
                ),
            },
            grade_labels={"A": "Excellent", "B": "Good", "C": "Fair", "D": "Poor"},
        )

        assert model.grading_type == GradingType.MULTI_LEVEL

    def test_grading_model_model_dump(self) -> None:
        """Test grading model serialization with model_dump (Pydantic 2.0)."""
        model = GradingModel(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=GradingType.BINARY,
            attributes={
                "quality": GradingAttribute(
                    num_classes=2,
                    classes=["good", "bad"],
                ),
            },
            grade_labels={"ACCEPT": "Good", "REJECT": "Bad"},
        )

        data = model.model_dump()

        assert data["model_id"] == "test_model"
        assert data["grading_type"] == "binary"
        assert "quality" in data["attributes"]
        assert data["attributes"]["quality"]["num_classes"] == 2

    def test_grading_model_optional_regulatory_authority(self) -> None:
        """Test regulatory authority is optional."""
        model = GradingModel(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=GradingType.BINARY,
            attributes={
                "quality": GradingAttribute(
                    num_classes=2,
                    classes=["good", "bad"],
                ),
            },
            grade_labels={"ACCEPT": "Good", "REJECT": "Bad"},
        )

        assert model.regulatory_authority is None

    def test_grading_model_default_timestamps(self) -> None:
        """Test grading model has default timestamps."""
        model = GradingModel(
            model_id="test_model",
            model_version="1.0.0",
            crops_name="Tea",
            market_name="Test",
            grading_type=GradingType.BINARY,
            attributes={
                "quality": GradingAttribute(
                    num_classes=2,
                    classes=["good", "bad"],
                ),
            },
            grade_labels={"ACCEPT": "Good", "REJECT": "Bad"},
        )

        assert model.created_at is not None
        assert model.updated_at is not None