"""QC Analyzer quality result models.

Typed Pydantic models for the QC Analyzer output — the grading result
produced per tea bag. Schema defined in:
  _bmad-output/analysis/tbk-kenya-tea-grading-model-specification.md (line 397)

The Collection Model ingests this JSON blob and stores it in
Document.extracted_fields. These models allow typed validation
at service boundaries instead of raw dict access.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class AttributeClassResult(BaseModel):
    """Result for a single class within an attribute (e.g., 'bud' within 'leaf_type').

    Attributes:
        count: Number of leaves classified into this class.
        avg_confidence: Average model confidence for this classification.
    """

    count: int = Field(ge=0, description="Number of leaves in this class")
    avg_confidence: float = Field(ge=0.0, le=1.0, description="Average model confidence")


class GradeCount(BaseModel):
    """Counts of grades (primary/secondary) for a single attribute."""
    grade: str = Field(description="Grade label (e.g., 'primary', 'secondary')")
    count: int = Field(ge=0, description="Number of leaves with this grade")

class QcAnalyzerResult(BaseModel):
    """QC Analyzer grading result for a single tea bag.

    This is the JSON output produced by the QC Analyzer after classifying
    all leaves in a bag. It contains the full attribute distribution
    (leaf_type, coarse_subtype, banji_hardness) and the final grade counts
    (primary/secondary).

    Attributes:
        market_name: Market identifier (e.g., 'Kenya').
        crop_name: Crop type (e.g., 'tea').
        grading_model_version: Version of the grading model used.
        grading_model_id: Identifier of the grading model used.
        timestamp: When the grading was performed.
        bag_id: Unique identifier for the tea bag.
        factory_id: Factory where the bag was processed.
        farmer_id: Farmer who produced the bag.
        total: Total number of leaves classified.
        attribute_distribution: Per-attribute class distributions with counts and confidence.
        primary: Number of leaves graded as primary quality.
        secondary: Number of leaves graded as secondary quality.
    """

    market_name: str = Field(description="Market identifier (e.g., 'Kenya')")
    crop_name: str = Field(description="Crop type (e.g., 'tea')")
    grading_model_version: str = Field(description="Version of the grading model used")
    grading_model_id: str = Field(description="Grading model identifier (e.g., 'tbk_kenya_tea_v1')")
    timestamp: datetime = Field(description="When the grading was performed")
    bag_id: str = Field(description="Unique identifier for the tea bag")
    factory_id: str = Field(description="Factory where the bag was processed")
    farmer_id: str = Field(description="Farmer who produced the bag")
    total: int = Field(ge=0, description="Total number of leaves classified")
    attribute_distribution: dict[str, dict[str, AttributeClassResult]] = Field(
        default_factory=dict,
        description="Per-attribute class distributions (e.g., leaf_type -> bud -> {count, avg_confidence})",
    )
    grade_counts: dict[str, GradeCount] = Field(
        default_factory=dict,
        description="Grade counts (e.g., primary -> {count})",
    )
