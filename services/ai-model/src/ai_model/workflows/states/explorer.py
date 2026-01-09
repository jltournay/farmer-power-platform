"""Explorer workflow state definition.

The Explorer workflow implements the saga pattern for multi-analyzer diagnosis.
It uses conditional routing based on triage confidence.

Graph: fetch_context → triage → (conditional) → analyze → aggregate → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import datetime
from typing import Any, Literal, TypedDict

from ai_model.domain.agent_config import ExplorerConfig


class AnalyzerResult(TypedDict):
    """Result from a single analyzer branch."""

    analyzer_id: str
    category: str  # disease, weather, technique, etc.
    confidence: float
    findings: list[str]
    recommendations: list[str]
    success: bool
    error: str | None


class ExplorerState(TypedDict, total=False):
    """State for Explorer workflow (saga pattern).

    This state flows through the diagnostic pipeline:
    1. fetch_context: Load farmer/event context via MCP
    2. triage: Initial classification to determine routing
    3. (conditional): Route to single or parallel analyzers
    4. analyze: Execute selected analyzer(s)
    5. aggregate: Combine findings from all analyzers
    6. output: Package final diagnosis

    Saga Pattern:
    - If triage confidence >= 0.7: single analyzer path
    - If triage confidence < 0.7: parallel analyzers with timeout
    - Partial failures handled gracefully

    Attributes:
        # Input
        input_data: Event data to analyze.
        agent_id: ID of the explorer agent.
        agent_config: Agent configuration loaded from cache.
        prompt_template: Prompt template loaded from cache.
        correlation_id: Request correlation ID for tracing.

        # Context (from MCP)
        mcp_context: Data fetched from MCP servers.
        mcp_error: Error message if MCP fetch failed.
        rag_context: Retrieved knowledge chunks.
        rag_error: Error message if RAG retrieval failed.
        analysis_query: Query for RAG retrieval.
        rag_domain: Domain for RAG filtering.

        # Triage
        triage_category: Primary category from triage (disease, weather, etc.).
        triage_confidence: Confidence score from triage.
        triage_secondary_categories: Additional possible categories.
        route_type: Routing decision (single, parallel).

        # Analysis (saga)
        selected_analyzers: List of analyzer IDs to execute.
        analyzer_results: Results from completed analyzers.
        branch_timeout_seconds: Timeout for parallel branches.
        failed_branches: List of analyzer IDs that failed/timed out.

        # Aggregation
        primary_diagnosis: Highest confidence result.
        secondary_diagnoses: Results with confidence >= 0.5.

        # Output
        output: Final aggregated diagnosis.
        success: Whether analysis succeeded.
        error_message: Error message if failed.

        # Metadata
        model_used: Actual LLM model that processed the request.
        tokens_used: Total tokens consumed across all LLM calls.
        execution_time_ms: Total execution time in milliseconds.
        started_at: Workflow start timestamp.
        completed_at: Workflow completion timestamp.
    """

    # Input
    input_data: dict[str, Any]
    agent_id: str
    agent_config: ExplorerConfig
    prompt_template: str
    correlation_id: str

    # Context (from MCP)
    mcp_context: dict[str, Any] | None
    mcp_error: str | None
    rag_context: list[dict[str, Any]]
    rag_error: str | None
    analysis_query: str
    rag_domain: str

    # Triage
    triage_category: str
    triage_confidence: float
    triage_secondary_categories: list[str]
    route_type: Literal["single", "parallel"]

    # Analysis (saga pattern fields)
    selected_analyzers: list[str]
    analyzer_results: list[AnalyzerResult]
    branch_timeout_seconds: int
    failed_branches: list[str]

    # Aggregation
    primary_diagnosis: AnalyzerResult | None
    secondary_diagnoses: list[AnalyzerResult]

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
