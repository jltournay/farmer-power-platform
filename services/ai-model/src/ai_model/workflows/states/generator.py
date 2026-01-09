"""Generator workflow state definition.

The Generator workflow creates content (plans, reports, messages) using
RAG-enhanced LLM generation with support for multiple output formats.

Graph: fetch_context → retrieve_knowledge → generate → format → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import datetime
from typing import Any, Literal, TypedDict

from ai_model.domain.agent_config import GeneratorConfig


class GeneratorState(TypedDict, total=False):
    """State for Generator workflow.

    This state flows through the content generation pipeline:
    1. fetch_context: Load entity context via MCP
    2. retrieve_knowledge: Fetch RAG knowledge chunks
    3. generate: LLM generates content with context + knowledge
    4. format: Transform output to target format
    5. output: Package final result

    Attributes:
        # Input
        input_data: Request data including entity reference.
        agent_id: ID of the generator agent.
        agent_config: Agent configuration loaded from cache.
        prompt_template: Prompt template loaded from cache.
        correlation_id: Request correlation ID for tracing.
        output_format: Target output format (json, markdown, text).

        # Context (from MCP)
        mcp_context: Data fetched from MCP servers.
        mcp_error: Error message if MCP fetch failed.

        # RAG
        rag_query: Query constructed for RAG retrieval.
        rag_context: Retrieved knowledge chunks.
        rag_error: Error message if RAG retrieval failed.
        rag_domains: Knowledge domains queried.

        # Generation
        raw_generation: Raw LLM output.
        generation_error: Error message if generation failed.

        # Formatting
        formatted_output: Output after format transformation.
        format_error: Error message if formatting failed.

        # Output
        output: Final formatted content.
        success: Whether generation succeeded.
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
    agent_config: GeneratorConfig
    prompt_template: str
    correlation_id: str
    output_format: Literal["json", "markdown", "text"]

    # Context (from MCP)
    mcp_context: dict[str, Any] | None
    mcp_error: str | None

    # RAG
    rag_query: str
    rag_context: list[dict[str, Any]]
    rag_error: str | None
    rag_domains: list[str]

    # Generation
    raw_generation: str
    generation_error: str | None

    # Formatting
    formatted_output: str | dict[str, Any]
    format_error: str | None

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
