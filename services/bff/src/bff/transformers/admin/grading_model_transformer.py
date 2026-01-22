"""Grading Model transformer for admin API (Story 9.6a).

Transforms GradingModel domain models to admin API schemas.
Note: Receives Pydantic models from PlantationClient (NOT proto).
"""

from bff.api.schemas.admin.grading_model_schemas import (
    ConditionalRejectResponse,
    FactoryReference,
    GradeRulesResponse,
    GradingAttributeResponse,
    GradingModelDetail,
    GradingModelSummary,
)
from fp_common.models import GradingModel, GradingType


def grading_type_to_string(grading_type: GradingType) -> str:
    """Convert GradingType enum to string for API responses.

    Args:
        grading_type: The GradingType enum value.

    Returns:
        String representation: "binary", "ternary", or "multi_level".
    """
    return grading_type.value


class GradingModelTransformer:
    """Transforms GradingModel domain models to admin API schemas."""

    @staticmethod
    def to_summary(model: GradingModel) -> GradingModelSummary:
        """Transform GradingModel to summary schema for list views.

        Args:
            model: GradingModel Pydantic domain model.

        Returns:
            GradingModelSummary for API response.
        """
        return GradingModelSummary(
            model_id=model.model_id,
            model_version=model.model_version,
            crops_name=model.crops_name,
            market_name=model.market_name,
            grading_type=grading_type_to_string(model.grading_type),
            attribute_count=len(model.attributes),
            factory_count=len(model.active_at_factory),
        )

    @staticmethod
    def to_detail(
        model: GradingModel,
        factory_names: dict[str, str] | None = None,
    ) -> GradingModelDetail:
        """Transform GradingModel to detail schema for single-entity views.

        Args:
            model: GradingModel Pydantic domain model.
            factory_names: Optional dict mapping factory_id -> factory_name
                          for resolving factory references.

        Returns:
            GradingModelDetail for API response.
        """
        factory_names = factory_names or {}

        # Transform attributes
        attributes_response: dict[str, GradingAttributeResponse] = {}
        for attr_name, attr in model.attributes.items():
            attributes_response[attr_name] = GradingAttributeResponse(
                num_classes=attr.num_classes,
                classes=attr.classes,
            )

        # Transform grade rules
        conditional_reject_list = [
            ConditionalRejectResponse(
                if_attribute=cr.if_attribute,
                if_value=cr.if_value,
                then_attribute=cr.then_attribute,
                reject_values=cr.reject_values,
            )
            for cr in model.grade_rules.conditional_reject
        ]

        grade_rules_response = GradeRulesResponse(
            reject_conditions=model.grade_rules.reject_conditions,
            conditional_reject=conditional_reject_list,
        )

        # Transform factory references
        active_at_factories = [
            FactoryReference(
                factory_id=factory_id,
                name=factory_names.get(factory_id),
            )
            for factory_id in model.active_at_factory
        ]

        return GradingModelDetail(
            model_id=model.model_id,
            model_version=model.model_version,
            regulatory_authority=model.regulatory_authority,
            crops_name=model.crops_name,
            market_name=model.market_name,
            grading_type=grading_type_to_string(model.grading_type),
            attributes=attributes_response,
            grade_rules=grade_rules_response,
            grade_labels=model.grade_labels,
            active_at_factories=active_at_factories,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
