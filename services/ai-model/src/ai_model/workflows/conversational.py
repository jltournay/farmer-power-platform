"""Conversational workflow implementation.

LangGraph workflow for multi-turn dialogue with context management:
load_history → classify_intent → (conditional) → retrieve_knowledge → respond → update_history

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import structlog
from ai_model.workflows.base import WorkflowBuilder, create_node_wrapper
from ai_model.workflows.states.conversational import ConversationalState, MessageTurn
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = structlog.get_logger(__name__)

# Default session configuration
DEFAULT_MAX_TURNS = 5
DEFAULT_SESSION_TTL_MINUTES = 30
DEFAULT_CONTEXT_WINDOW = 3


class ConversationalWorkflow(WorkflowBuilder[ConversationalState]):
    """Conversational workflow for multi-turn dialogue.

    This workflow implements a dialogue pipeline with:
    1. load_history: Load conversation history from checkpoint
    2. classify_intent: Fast model classifies user intent
    3. (conditional): Route based on intent
    4. retrieve_knowledge: Fetch RAG knowledge if needed
    5. respond: Generate response with full context
    6. update_history: Persist updated conversation state

    Features:
    - Two-model approach: fast intent + capable response
    - Sliding window context management
    - Session TTL and max turns limits
    - RAG-enhanced responses for knowledge queries
    """

    workflow_name = "conversational"
    workflow_version = "1.0.0"

    def __init__(
        self,
        llm_gateway: Any,  # LLMGateway
        ranking_service: Any | None = None,  # RankingService
        checkpointer: Any | None = None,
    ) -> None:
        """Initialize the conversational workflow.

        Args:
            llm_gateway: LLM gateway for making LLM calls.
            ranking_service: Optional ranking service for RAG.
            checkpointer: Checkpointer for conversation persistence.
        """
        super().__init__(checkpointer=checkpointer)
        self._llm_gateway = llm_gateway
        self._ranking_service = ranking_service

    def _get_state_schema(self) -> type[ConversationalState]:
        """Return the ConversationalState schema."""
        return ConversationalState

    def _build_graph(self, builder: StateGraph[ConversationalState]) -> StateGraph[ConversationalState]:
        """Build the conversational workflow graph.

        Graph structure:
        START → load_history → classify_intent → (router) → respond → update_history → END
                                                    ↓
                                        with_rag or without_rag
        """
        # Add nodes
        builder.add_node("load_history", self._load_history_node)
        builder.add_node("classify_intent", self._classify_intent_node)
        builder.add_node("retrieve_knowledge", self._retrieve_knowledge_node)
        builder.add_node("respond", self._respond_node)
        builder.add_node("update_history", self._update_history_node)

        # Add edges
        builder.add_edge(START, "load_history")
        builder.add_edge("load_history", "classify_intent")

        # Conditional routing after intent classification
        builder.add_conditional_edges(
            "classify_intent",
            self._route_after_intent,
            {
                "with_rag": "retrieve_knowledge",
                "without_rag": "respond",
                "end_session": "update_history",
            },
        )

        builder.add_edge("retrieve_knowledge", "respond")
        builder.add_edge("respond", "update_history")
        builder.add_edge("update_history", END)

        return builder

    def _route_after_intent(
        self,
        state: ConversationalState,
    ) -> Literal["with_rag", "without_rag", "end_session"]:
        """Determine routing based on intent classification.

        Args:
            state: Current workflow state.

        Returns:
            Route name: 'with_rag', 'without_rag', or 'end_session'.
        """
        intent = state.get("intent", "unknown")

        # End session intents
        if intent in ("goodbye", "end", "exit", "quit"):
            return "end_session"

        # Knowledge-requiring intents
        if state.get("requires_knowledge", False):
            return "with_rag"

        return "without_rag"

    @create_node_wrapper("load_history", "conversational")
    async def _load_history_node(self, state: ConversationalState) -> dict[str, Any]:
        """Load conversation history and initialize session.

        Args:
            state: Current workflow state.

        Returns:
            State update with session configuration.
        """
        agent_config = state["agent_config"]
        state_config = agent_config.state

        # Get session configuration
        max_turns = state_config.max_turns if state_config else DEFAULT_MAX_TURNS
        session_ttl_minutes = state_config.session_ttl_minutes if state_config else DEFAULT_SESSION_TTL_MINUTES
        context_window = state_config.context_window if state_config else DEFAULT_CONTEXT_WINDOW

        # Initialize or load history
        history = state.get("conversation_history", [])
        turn_count = len(history)

        # Check session limits
        if turn_count >= max_turns:
            logger.info(
                "Session max turns reached",
                session_id=state.get("session_id"),
                turn_count=turn_count,
                max_turns=max_turns,
            )
            return {
                "should_end_session": True,
                "error_message": f"Maximum turns ({max_turns}) reached",
            }

        now = datetime.now(UTC)
        session_started = state.get("session_started_at") or now
        session_expires = session_started + timedelta(minutes=session_ttl_minutes)

        # Check session expiry
        if now > session_expires:
            logger.info(
                "Session expired",
                session_id=state.get("session_id"),
                session_expires=session_expires.isoformat(),
            )
            return {
                "should_end_session": True,
                "error_message": "Session has expired",
            }

        logger.debug(
            "Session loaded",
            session_id=state.get("session_id"),
            turn_count=turn_count,
            context_window=context_window,
        )

        return {
            "turn_count": turn_count,
            "max_turns": max_turns,
            "context_window": context_window,
            "session_started_at": session_started,
            "session_expires_at": session_expires,
        }

    @create_node_wrapper("classify_intent", "conversational")
    async def _classify_intent_node(self, state: ConversationalState) -> dict[str, Any]:
        """Classify user intent using fast model.

        Args:
            state: Current workflow state.

        Returns:
            State update with intent classification.
        """
        user_message = state.get("user_message", "")
        agent_config = state["agent_config"]

        # Check for session end
        if state.get("should_end_session"):
            return {}

        # Get intent model (fast model like Haiku)
        intent_model = agent_config.intent_model or "anthropic/claude-3-haiku"

        system_prompt = self._build_intent_system_prompt()
        user_prompt = f"User message: {user_message}"

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            result = await self._llm_gateway.complete(
                messages=messages,
                model=intent_model,
                agent_id=state.get("agent_id", ""),
                agent_type="conversational",
                request_id=state.get("correlation_id"),
                temperature=0.0,  # Deterministic classification
                max_tokens=200,
            )

            # Parse intent response
            intent_result = self._parse_intent_response(result.get("content", ""))

            requires_knowledge = intent_result.get("intent") in (
                "question",
                "how_to",
                "information",
                "advice",
                "problem",
            )

            logger.debug(
                "Intent classified",
                session_id=state.get("session_id"),
                intent=intent_result.get("intent"),
                confidence=intent_result.get("confidence"),
                requires_knowledge=requires_knowledge,
            )

            return {
                "intent": intent_result.get("intent", "unknown"),
                "intent_confidence": intent_result.get("confidence", 0.5),
                "entities": intent_result.get("entities", {}),
                "requires_knowledge": requires_knowledge,
                "intent_model": intent_model,
            }

        except Exception as e:
            logger.warning(
                "Intent classification failed",
                session_id=state.get("session_id"),
                error=str(e),
            )
            return {
                "intent": "unknown",
                "intent_confidence": 0.0,
                "requires_knowledge": True,  # Default to RAG on failure
            }

    @create_node_wrapper("retrieve_knowledge", "conversational")
    async def _retrieve_knowledge_node(self, state: ConversationalState) -> dict[str, Any]:
        """Retrieve relevant knowledge from RAG.

        Args:
            state: Current workflow state.

        Returns:
            State update with RAG context.
        """
        user_message = state.get("user_message", "")
        agent_config = state["agent_config"]
        entities = state.get("entities", {})

        rag_config = agent_config.rag

        if not rag_config.enabled or not self._ranking_service:
            return {"rag_context": []}

        try:
            # Build query - combine user message with extracted entities
            query_parts = [user_message]
            for entity_value in entities.values():
                if isinstance(entity_value, str):
                    query_parts.append(entity_value)

            query = " ".join(query_parts)
            domains = rag_config.knowledge_domains

            ranking_result = await self._ranking_service.rank(
                query=query,
                domains=domains,
                config=None,
            )

            rag_context = [
                {
                    "content": m.content,
                    "title": m.title,
                    "domain": m.domain,
                    "score": m.rerank_score,
                }
                for m in ranking_result.matches
            ]

            logger.debug(
                "Knowledge retrieved for conversation",
                session_id=state.get("session_id"),
                matches=len(rag_context),
            )

            return {
                "rag_context": rag_context,
                "rag_query": query,
            }

        except Exception as e:
            logger.warning(
                "RAG retrieval failed",
                session_id=state.get("session_id"),
                error=str(e),
            )
            return {
                "rag_context": [],
                "rag_error": str(e),
            }

    @create_node_wrapper("respond", "conversational")
    async def _respond_node(self, state: ConversationalState) -> dict[str, Any]:
        """Generate response using capable model.

        Args:
            state: Current workflow state.

        Returns:
            State update with response.
        """
        user_message = state.get("user_message", "")
        agent_config = state["agent_config"]
        conversation_history = state.get("conversation_history", [])
        context_window = state.get("context_window", DEFAULT_CONTEXT_WINDOW)
        rag_context = state.get("rag_context", [])
        intent = state.get("intent", "unknown")

        # Get response model (capable model like Sonnet)
        response_model = agent_config.response_model or "anthropic/claude-3-5-sonnet"
        llm_config = agent_config.llm

        # Build conversation context (sliding window)
        recent_history = conversation_history[-context_window:] if conversation_history else []

        system_prompt = self._build_response_system_prompt(rag_context)
        user_prompt = self._build_response_user_prompt(
            user_message,
            recent_history,
            intent,
            rag_context,
        )

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            result = await self._llm_gateway.complete(
                messages=messages,
                model=response_model,
                agent_id=state.get("agent_id", ""),
                agent_type="conversational",
                request_id=state.get("correlation_id"),
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
            )

            response_text = result.get("content", "")
            tokens_used = result.get("tokens_in", 0) + result.get("tokens_out", 0)

            logger.debug(
                "Response generated",
                session_id=state.get("session_id"),
                response_length=len(response_text),
                tokens_used=tokens_used,
            )

            return {
                "response_text": response_text,
                "response_model": response_model,
                "tokens_used": tokens_used,
                "response_metadata": {
                    "intent": intent,
                    "rag_sources": len(rag_context),
                    "history_turns": len(recent_history),
                },
            }

        except Exception as e:
            logger.error(
                "Response generation failed",
                session_id=state.get("session_id"),
                error=str(e),
            )
            return {
                "response_text": "I apologize, but I encountered an error processing your request. Please try again.",
                "generation_error": str(e),
            }

    @create_node_wrapper("update_history", "conversational")
    async def _update_history_node(self, state: ConversationalState) -> dict[str, Any]:
        """Update conversation history and package output.

        Args:
            state: Current workflow state.

        Returns:
            Final state update.
        """
        user_message = state.get("user_message", "")
        response_text = state.get("response_text", "")
        conversation_history = list(state.get("conversation_history", []))
        should_end_session = state.get("should_end_session", False)

        now = datetime.now(UTC)

        # Add user message to history
        if user_message:
            conversation_history.append(
                MessageTurn(
                    role="user",
                    content=user_message,
                    timestamp=now,
                )
            )

        # Add assistant response to history
        if response_text and not should_end_session:
            conversation_history.append(
                MessageTurn(
                    role="assistant",
                    content=response_text,
                    timestamp=now,
                )
            )

        # Build output
        output: dict[str, Any] = {
            "response": response_text,
            "session_id": state.get("session_id"),
            "turn_count": len(conversation_history) // 2,  # User + assistant = 1 turn
            "session_ended": should_end_session,
        }

        # Determine success
        success = bool(response_text) or should_end_session
        error_message = state.get("error_message") or state.get("generation_error")

        logger.info(
            "Conversational workflow completed",
            session_id=state.get("session_id"),
            turn_count=output["turn_count"],
            session_ended=should_end_session,
            success=success,
        )

        return {
            "conversation_history": conversation_history,
            "output": output,
            "success": success,
            "error_message": error_message,
            "should_end_session": should_end_session,
        }

    # Helper methods

    def _build_intent_system_prompt(self) -> str:
        """Build system prompt for intent classification."""
        return """You are an intent classifier. Classify the user's message into one of these intents:

- greeting: Hello, hi, good morning, etc.
- goodbye: Bye, see you, end conversation
- question: Asking for information or explanation
- how_to: Asking how to do something
- advice: Seeking recommendations
- problem: Reporting an issue or problem
- confirmation: Yes, no, ok, agreeing/disagreeing
- feedback: Providing feedback or opinion
- smalltalk: General conversation, weather, etc.
- unknown: Cannot determine intent

Respond with JSON:
{
    "intent": "intent_name",
    "confidence": 0.0-1.0,
    "entities": {"key": "value"}  // extracted entities if any
}"""

    def _parse_intent_response(self, content: str) -> dict[str, Any]:
        """Parse intent classification response."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            return {"intent": "unknown", "confidence": 0.5, "entities": {}}

    def _build_response_system_prompt(
        self,
        rag_context: list[dict[str, Any]],
    ) -> str:
        """Build system prompt for response generation."""
        base_prompt = """You are a helpful agricultural assistant for farmers. Respond naturally and helpfully.

Guidelines:
1. Be friendly and conversational
2. Provide practical, actionable advice
3. Acknowledge when you don't know something
4. Keep responses concise but complete
5. Use simple language appropriate for farmers"""

        if rag_context:
            knowledge = "\n".join(
                f"- {r.get('title', 'Info')}: {r.get('content', '')[:200]}..." for r in rag_context[:3]
            )
            base_prompt += f"\n\nRelevant knowledge to reference:\n{knowledge}"

        return base_prompt

    def _build_response_user_prompt(
        self,
        user_message: str,
        recent_history: list[MessageTurn],
        intent: str,
        rag_context: list[dict[str, Any]],
    ) -> str:
        """Build user prompt for response generation."""
        parts = []

        # Add conversation history
        if recent_history:
            history_text = "\n".join(
                f"{turn.get('role', 'unknown').title()}: {turn.get('content', '')}" for turn in recent_history
            )
            parts.append(f"Previous conversation:\n{history_text}")

        # Add current message
        parts.append(f"User: {user_message}")

        # Add intent hint
        parts.append(f"\n(Detected intent: {intent})")

        return "\n\n".join(parts)
