"""Grading Model domain models.

GradingModel defines the grading configuration for a specific crop/market.
Grading models are stored in the Plantation Model and referenced by
FarmerPerformance records for interpreting grade distributions.

Key concepts:
- GradingType: Binary (Accept/Reject), Ternary (Premium/Standard/Reject),
  or Multi-Level (A/B/C/D)
- Attributes: What the CV model outputs (e.g., leaf_type, banji_hardness)
- GradeRules: Rules for determining final grade from attribute values
- GradeLabels: Factory-specific display labels (internal → display)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GradingType(str, Enum):
    """Type of grading system.

    - BINARY: Accept/Reject or Primary/Secondary (TBK Kenya Tea)
    - TERNARY: Premium/Standard/Reject (some coffee markets)
    - MULTI_LEVEL: A/B/C/D or custom levels (specialty markets)
    """

    BINARY = "binary"
    TERNARY = "ternary"
    MULTI_LEVEL = "multi_level"


class GradingAttribute(BaseModel):
    """Definition of a single attribute in the grading model.

    Each attribute represents one output from the CV/grading system.
    Example: leaf_type with 7 classes (bud, one_leaf_bud, etc.)
    """

    num_classes: int = Field(ge=2, description="Number of classes for this attribute")
    classes: list[str] = Field(min_length=2, description="Class labels in order")


class ConditionalReject(BaseModel):
    """Conditional rejection rule.

    Example: If leaf_type is "banji" AND banji_hardness is "hard",
    then reject the sample.
    """

    if_attribute: str = Field(description="Attribute to check first")
    if_value: str = Field(description="Value that triggers the condition")
    then_attribute: str = Field(description="Second attribute to check")
    reject_values: list[str] = Field(
        description="Values in then_attribute that cause rejection"
    )


class GradeRules(BaseModel):
    """Rules for determining final grade from attributes.

    Contains both unconditional reject conditions and conditional reject rules.
    """

    reject_conditions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Attribute values that always result in rejection",
    )
    conditional_reject: list[ConditionalReject] = Field(
        default_factory=list,
        description="Conditional rejection rules",
    )


class GradingModel(BaseModel):
    """Complete grading model definition stored in Plantation Model.

    A grading model defines:
    - What attributes the CV system outputs
    - How to determine the final grade from those attributes
    - Factory-specific display labels for grades

    Key relationships:
    - Active at specific factories via active_at_factory list
    - Referenced by FarmerPerformance for interpreting distributions
    """

    # Identity
    model_id: str = Field(description="Unique identifier for this grading model")
    model_version: str = Field(description="Semantic version (e.g., 1.0.0)")
    regulatory_authority: Optional[str] = Field(
        default=None,
        description="Regulatory body that defines this grading standard",
    )
    crops_name: str = Field(description="Crop type (e.g., Tea, Coffee)")
    market_name: str = Field(description="Market identifier (e.g., Kenya_TBK)")
    grading_type: GradingType = Field(description="Type of grading system")

    # Attribute structure
    attributes: dict[str, GradingAttribute] = Field(
        description="Attribute definitions keyed by attribute name"
    )

    # Grade calculation rules
    grade_rules: GradeRules = Field(default_factory=GradeRules)

    # Display labels
    grade_labels: dict[str, str] = Field(
        description="Internal grade → display label mapping"
    )

    # Deployment
    active_at_factory: list[str] = Field(
        default_factory=list,
        description="Factory IDs where this model is active",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )

    def get_all_attribute_classes(self) -> dict[str, list[str]]:
        """Return all classes for all attributes.

        Returns:
            Dictionary mapping attribute names to their class lists.
        """
        return {name: attr.classes for name, attr in self.attributes.items()}

    def get_grade_display_label(self, internal_grade: str) -> str:
        """Convert internal grade to display label.

        Args:
            internal_grade: Internal grade key (e.g., "ACCEPT", "REJECT").

        Returns:
            Display label if found, otherwise returns the internal grade itself.
        """
        return self.grade_labels.get(internal_grade, internal_grade)

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_id": "tbk_kenya_tea_v1",
                "model_version": "1.0.0",
                "regulatory_authority": "Tea Board of Kenya (TBK)",
                "crops_name": "Tea",
                "market_name": "Kenya_TBK",
                "grading_type": "binary",
                "attributes": {
                    "leaf_type": {
                        "num_classes": 7,
                        "classes": [
                            "bud",
                            "one_leaf_bud",
                            "two_leaves_bud",
                            "three_plus_leaves_bud",
                            "single_soft_leaf",
                            "coarse_leaf",
                            "banji",
                        ],
                    },
                },
                "grade_rules": {
                    "reject_conditions": {
                        "leaf_type": ["three_plus_leaves_bud", "coarse_leaf"],
                    },
                    "conditional_reject": [
                        {
                            "if_attribute": "leaf_type",
                            "if_value": "banji",
                            "then_attribute": "banji_hardness",
                            "reject_values": ["hard"],
                        },
                    ],
                },
                "grade_labels": {"ACCEPT": "Primary", "REJECT": "Secondary"},
                "active_at_factory": ["factory-001"],
            },
        },
    }
