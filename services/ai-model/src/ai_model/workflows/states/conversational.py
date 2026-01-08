"""Conversational workflow state definition.

The Conversational workflow handles multi-turn dialogue with context management.
It uses a two-model approach: fast model for intent, capable model for response.

Graph: load_history → classify_intent → (conditional) → retrieve_knowledge → respond → update_history

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

from datetime import datetime
from typing import Any, Literal, TypedDict


class MessageTurn(TypedDict):
    """Single turn in conversation history."""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime


class ConversationalState(TypedDict, total=False):
    """State for Conversational workflow.

    This state flows through the dialogue pipeline:
    1. load_history: Load conversation history from checkpoint
    2. classify_intent: Fast model classifies user intent
    3. (conditional): Route based on intent
    4. retrieve_knowledge: Fetch RAG knowledge if needed
    5. respond: Generate response with full context
    6. update_history: Persist updated conversation state

    Multi-turn Context:
    - Maintains sliding window of recent turns
    - Session TTL enforced via MongoDB TTL index
    - Checkpointing enables crash recovery

    Attributes:
        # Input
        user_message: Current user message.
        session_id: Conversation session identifier.
        agent_id: ID of the conversational agent.
        agent_config: Agent configuration loaded from cache.
        correlation_id: Request correlation ID for tracing.

        # Session State
        conversation_history: Previous turns (loaded from checkpoint).
        turn_count: Current turn number.
        max_turns: Maximum turns allowed in session.
        context_window: Number of recent turns to include in prompt.
        session_started_at: Session start timestamp.
        session_expires_at: Session expiry timestamp.

        # Intent Classification
        intent: Classified intent category.
        intent_confidence: Confidence score for classification.
        entities: Extracted entities from user message.
        requires_knowledge: Whether RAG retrieval is needed.

        # RAG
        rag_query: Query constructed for RAG retrieval.
        rag_context: Retrieved knowledge chunks.
        rag_error: Error message if RAG retrieval failed.

        # Response Generation
        response_text: Generated response text.
        response_metadata: Additional response info (sources, etc.).
        generation_error: Error message if generation failed.

        # Output
        output: Final response package.
        success: Whether response generation succeeded.
        error_message: Error message if failed.
        should_end_session: Whether session should be terminated.

        # Metadata
        intent_model: Model used for intent classification.
        response_model: Model used for response generation.
        tokens_used: Total tokens consumed (both models).
        execution_time_ms: Total execution time in milliseconds.
        started_at: Request start timestamp.
        completed_at: Request completion timestamp.
    """

    # Input
    user_message: str
    session_id: str
    agent_id: str
    agent_config: dict[str, Any]
    correlation_id: str

    # Session State
    conversation_history: list[MessageTurn]
    turn_count: int
    max_turns: int
    context_window: int
    session_started_at: datetime
    session_expires_at: datetime

    # Intent Classification
    intent: str
    intent_confidence: float
    entities: dict[str, Any]
    requires_knowledge: bool

    # RAG
    rag_query: str
    rag_context: list[dict[str, Any]]
    rag_error: str | None

    # Response Generation
    response_text: str
    response_metadata: dict[str, Any]
    generation_error: str | None

    # Output
    output: dict[str, Any]
    success: bool
    error_message: str | None
    should_end_session: bool

    # Metadata
    intent_model: str
    response_model: str
    tokens_used: int
    execution_time_ms: int
    started_at: datetime
    completed_at: datetime
