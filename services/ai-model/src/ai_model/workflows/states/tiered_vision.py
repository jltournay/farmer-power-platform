"""Tiered-Vision workflow state definition.

The Tiered-Vision workflow implements cost-optimized image analysis:
- Tier 1 (Screen): Fast Haiku classification on thumbnail
- Tier 2 (Diagnose): Deep Sonnet analysis on full image (if needed)

Graph: preprocess → screen → (conditional) → diagnose → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import datetime
from typing import Any, Literal, TypedDict

from ai_model.domain.agent_config import TieredVisionConfig


class ScreenResult(TypedDict):
    """Tier 1 screening result."""

    classification: Literal["healthy", "obvious_issue", "uncertain"]
    confidence: float
    preliminary_findings: list[str]
    skip_reason: str | None  # Reason for skipping Tier 2


class DiagnoseResult(TypedDict):
    """Tier 2 diagnosis result."""

    primary_issue: str
    confidence: float
    detailed_findings: list[str]
    recommendations: list[str]
    severity: Literal["low", "medium", "high", "critical"]


class TieredVisionState(TypedDict, total=False):
    """State for Tiered-Vision workflow.

    This state flows through the cost-optimized vision pipeline:
    1. preprocess: Resize/thumbnail image for Tier 1
    2. screen: Fast Haiku classification
    3. (conditional): Evaluate routing thresholds
    4. diagnose: Deep Sonnet analysis (if triggered)
    5. output: Package final result

    Cost Optimization:
    - Tier 1 uses thumbnail + Haiku (cheap)
    - Tier 2 uses full image + Sonnet (expensive)
    - Routing thresholds minimize unnecessary Tier 2 calls

    Attributes:
        # Input
        image_data: Base64-encoded image data.
        image_url: URL to image (alternative to data).
        image_mime_type: MIME type of image.
        agent_id: ID of the tiered-vision agent.
        agent_config: Agent configuration loaded from cache.
        correlation_id: Request correlation ID for tracing.

        # Preprocessing
        thumbnail_data: Resized thumbnail for Tier 1.
        original_dimensions: Original image dimensions.
        thumbnail_dimensions: Thumbnail dimensions.
        preprocessing_error: Error message if preprocessing failed.

        # Tier 1 (Screen)
        screen_result: Screening result from Tier 1.
        screen_error: Error message if screening failed.
        proceed_to_tier2: Whether to execute Tier 2.
        tier2_skip_reason: Reason for skipping Tier 2 (if applicable).

        # Tier 2 (Diagnose)
        diagnose_result: Diagnosis result from Tier 2.
        diagnose_error: Error message if diagnosis failed.
        rag_context: Retrieved knowledge for Tier 2.
        rag_error: Error message if RAG retrieval failed.

        # Output
        output: Final combined result.
        final_classification: Final classification (screen or diagnose).
        final_confidence: Final confidence score.
        success: Whether analysis succeeded.
        error_message: Error message if failed.

        # Cost Tracking
        tier1_executed: Whether Tier 1 was executed.
        tier2_executed: Whether Tier 2 was executed.
        tier1_model: Model used for Tier 1.
        tier2_model: Model used for Tier 2.
        tier1_tokens: Tokens used in Tier 1.
        tier2_tokens: Tokens used in Tier 2.
        total_cost_usd: Estimated total cost.

        # Metadata
        execution_time_ms: Total execution time in milliseconds.
        started_at: Workflow start timestamp.
        completed_at: Workflow completion timestamp.
    """

    # Input
    image_data: str
    image_url: str | None
    image_mime_type: str
    agent_id: str
    agent_config: TieredVisionConfig
    correlation_id: str

    # Preprocessing
    thumbnail_data: str
    original_dimensions: tuple[int, int]
    thumbnail_dimensions: tuple[int, int]
    preprocessing_error: str | None

    # Tier 1 (Screen)
    screen_result: ScreenResult | None
    screen_error: str | None
    proceed_to_tier2: bool
    tier2_skip_reason: str | None

    # Tier 2 (Diagnose)
    diagnose_result: DiagnoseResult | None
    diagnose_error: str | None
    rag_context: list[dict[str, Any]]
    rag_error: str | None

    # Output
    output: dict[str, Any]
    final_classification: str
    final_confidence: float
    success: bool
    error_message: str | None

    # Cost Tracking
    tier1_executed: bool
    tier2_executed: bool
    tier1_model: str
    tier2_model: str | None
    tier1_tokens: int
    tier2_tokens: int
    total_cost_usd: float

    # Metadata
    execution_time_ms: int
    started_at: datetime
    completed_at: datetime
