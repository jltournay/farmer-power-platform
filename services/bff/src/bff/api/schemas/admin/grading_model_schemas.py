"""Grading Model admin API schemas (Story 9.6a).

Provides request/response schemas for grading model management:
- GradingModelSummary: List view with basic info
- GradingModelDetail: Full detail with attributes and rules
- GradingModelListResponse: Paginated list response
- AssignGradingModelRequest: Assign model to factory
"""

from datetime import datetime

from bff.api.schemas.responses import PaginationMeta
from pydantic import BaseModel, Field


class GradingAttributeResponse(BaseModel):
    """Grading attribute definition for API responses."""

    num_classes: int = Field(description="Number of classes for this attribute")
    classes: list[str] = Field(description="Class names (e.g., ['Fine', 'Coarse'])")


class ConditionalRejectResponse(BaseModel):
    """Conditional reject rule for API responses."""

    if_attribute: str = Field(description="Attribute to check condition on")
    if_value: str = Field(description="Value that triggers the rule")
    then_attribute: str = Field(description="Attribute to apply rejection to")
    reject_values: list[str] = Field(description="Values to reject when condition met")


class GradeRulesResponse(BaseModel):
    """Grade rules for API responses."""

    reject_conditions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Attribute values that cause automatic rejection",
    )
    conditional_reject: list[ConditionalRejectResponse] = Field(
        default_factory=list,
        description="Conditional rejection rules",
    )


class FactoryReference(BaseModel):
    """Factory reference for grading model assignment."""

    factory_id: str = Field(description="Factory ID")
    name: str | None = Field(default=None, description="Factory name (resolved)")


class GradingModelSummary(BaseModel):
    """Grading model summary for admin list views."""

    model_id: str = Field(description="Grading model ID (e.g., 'tbk_kenya_tea_v1')")
    model_version: str = Field(description="Model version (e.g., '2024.1')")
    crops_name: str = Field(description="Crop name (e.g., 'Tea')")
    market_name: str = Field(description="Market name (e.g., 'Kenya_TBK')")
    grading_type: str = Field(description="Grading type: 'binary', 'ternary', or 'multi_level'")
    attribute_count: int = Field(description="Number of grading attributes")
    factory_count: int = Field(description="Number of factories using this model")


class GradingModelDetail(BaseModel):
    """Full grading model detail for admin single-entity views."""

    model_id: str = Field(description="Grading model ID")
    model_version: str = Field(description="Model version")
    regulatory_authority: str | None = Field(default=None, description="Regulatory authority (e.g., 'KTDA')")
    crops_name: str = Field(description="Crop name")
    market_name: str = Field(description="Market name")
    grading_type: str = Field(description="Grading type")
    attributes: dict[str, GradingAttributeResponse] = Field(
        description="Grading attributes (e.g., {'leaf_appearance': {...}})",
    )
    grade_rules: GradeRulesResponse = Field(description="Grade determination rules")
    grade_labels: dict[str, str] = Field(
        description="Display labels for grades (e.g., {'primary': 'Grade A'})",
    )
    active_at_factories: list[FactoryReference] = Field(
        default_factory=list,
        description="Factories using this grading model",
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class GradingModelListResponse(BaseModel):
    """Paginated grading model list response."""

    data: list[GradingModelSummary] = Field(description="List of grading model summaries")
    pagination: PaginationMeta = Field(description="Pagination metadata")


class AssignGradingModelRequest(BaseModel):
    """Request to assign grading model to factory."""

    factory_id: str = Field(description="Factory ID to assign the model to")
