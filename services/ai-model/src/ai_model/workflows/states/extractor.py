"""Extractor workflow state definition.

The Extractor workflow performs structured data extraction from unstructured input.
It uses a linear graph: fetch_data → extract → validate → normalize → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import datetime
from typing import Any, TypedDict


class ExtractorState(TypedDict, total=False):
    """State for Extractor workflow.

    This state flows through the linear extraction pipeline:
    1. fetch_data: Load input data
    2. extract: LLM extracts structured fields
    3. validate: Check extracted data against schema
    4. normalize: Apply normalization rules
    5. output: Package final result

    Attributes:
        # Input
        input_data: Raw input data to extract from.
        agent_id: ID of the extractor agent.
        agent_config: Agent configuration loaded from cache.
        prompt_template: Prompt template loaded from cache.
        correlation_id: Request correlation ID for tracing.

        # Intermediate
        raw_extraction: Raw extraction output from LLM.
        validated_data: Extraction after schema validation.
        validation_errors: List of validation errors (if any).

        # Output
        output: Final extracted and normalized data.
        success: Whether extraction succeeded.
        error_message: Error message if failed.

        # Metadata
        model_used: Actual LLM model that processed the request.
        tokens_used: Total tokens consumed.
        execution_time_ms: Total execution time in milliseconds.
        started_at: Workflow start timestamp.
        completed_at: Workflow completion timestamp.
    """

    # Input
    input_data: dict[str, Any]
    agent_id: str
    agent_config: dict[str, Any]
    prompt_template: str
    correlation_id: str

    # Intermediate
    raw_extraction: dict[str, Any]
    validated_data: dict[str, Any]
    validation_errors: list[str]

    # Output
    output: dict[str, Any]
    success: bool
    error_message: str | None

    # Metadata
    model_used: str
    tokens_used: int
    execution_time_ms: int
    started_at: datetime
    completed_at: datetime
