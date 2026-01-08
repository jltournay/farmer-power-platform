"""Tiered-Vision workflow implementation.

LangGraph workflow for cost-optimized image analysis:
preprocess → screen → (conditional) → diagnose → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from typing import Any, Literal

import structlog
from ai_model.workflows.base import WorkflowBuilder, create_node_wrapper
from ai_model.workflows.states.tiered_vision import (
    DiagnoseResult,
    ScreenResult,
    TieredVisionState,
)
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = structlog.get_logger(__name__)

# Default routing thresholds
DEFAULT_SCREEN_THRESHOLD = 0.7
DEFAULT_HEALTHY_SKIP_THRESHOLD = 0.85
DEFAULT_OBVIOUS_SKIP_THRESHOLD = 0.75

# Default thumbnail dimensions
DEFAULT_THUMBNAIL_WIDTH = 512
DEFAULT_THUMBNAIL_HEIGHT = 512


class TieredVisionWorkflow(WorkflowBuilder[TieredVisionState]):
    """Tiered-Vision workflow for cost-optimized image analysis.

    This workflow implements a two-tier processing pipeline:
    1. preprocess: Resize image to thumbnail for Tier 1
    2. screen: Fast Haiku classification on thumbnail
    3. (conditional): Evaluate routing thresholds
    4. diagnose: Deep Sonnet analysis on full image (if triggered)
    5. output: Package final result

    Cost Optimization:
    - Tier 1 (Screen): Fast, cheap model on thumbnail
      - Classifies: healthy, obvious_issue, uncertain
    - Tier 2 (Diagnose): Capable, expensive model on full image
      - Only triggered when needed based on thresholds

    Routing Logic:
    - If healthy + confidence >= healthy_skip_threshold → Skip Tier 2
    - If obvious_issue + confidence >= obvious_skip_threshold → Skip Tier 2
    - If confidence < screen_threshold OR uncertain → Run Tier 2
    """

    workflow_name = "tiered_vision"
    workflow_version = "1.0.0"

    def __init__(
        self,
        llm_gateway: Any,  # LLMGateway
        ranking_service: Any | None = None,  # RankingService
        checkpointer: Any | None = None,
    ) -> None:
        """Initialize the tiered-vision workflow.

        Args:
            llm_gateway: LLM gateway for making LLM calls.
            ranking_service: Optional ranking service for RAG in Tier 2.
            checkpointer: Optional checkpointer for state persistence.
        """
        super().__init__(checkpointer=checkpointer)
        self._llm_gateway = llm_gateway
        self._ranking_service = ranking_service

    def _get_state_schema(self) -> type[TieredVisionState]:
        """Return the TieredVisionState schema."""
        return TieredVisionState

    def _build_graph(self, builder: StateGraph[TieredVisionState]) -> StateGraph[TieredVisionState]:
        """Build the tiered-vision workflow graph.

        Graph structure:
        START → preprocess → screen → (router) → output → END
                                         ↓
                                  diagnose (if needed)
        """
        # Add nodes
        builder.add_node("preprocess", self._preprocess_node)
        builder.add_node("screen", self._screen_node)
        builder.add_node("diagnose", self._diagnose_node)
        builder.add_node("output", self._output_node)

        # Add edges
        builder.add_edge(START, "preprocess")
        builder.add_edge("preprocess", "screen")

        # Conditional routing after screen
        builder.add_conditional_edges(
            "screen",
            self._route_after_screen,
            {
                "diagnose": "diagnose",
                "skip": "output",
                "error": "output",
            },
        )

        builder.add_edge("diagnose", "output")
        builder.add_edge("output", END)

        return builder

    def _route_after_screen(
        self,
        state: TieredVisionState,
    ) -> Literal["diagnose", "skip", "error"]:
        """Determine routing based on screen results.

        Args:
            state: Current workflow state.

        Returns:
            Route name: 'diagnose', 'skip', or 'error'.
        """
        # Check for errors
        if state.get("screen_error") or state.get("preprocessing_error"):
            return "error"

        # Check proceed_to_tier2 flag set in screen node
        if state.get("proceed_to_tier2", False):
            return "diagnose"

        return "skip"

    @create_node_wrapper("preprocess", "tiered_vision")
    async def _preprocess_node(self, state: TieredVisionState) -> dict[str, Any]:
        """Preprocess image for Tier 1 screening.

        Args:
            state: Current workflow state.

        Returns:
            State update with thumbnail data.
        """
        image_data = state.get("image_data", "")
        image_url = state.get("image_url")

        if not image_data and not image_url:
            return {
                "preprocessing_error": "No image data or URL provided",
            }

        try:
            # For now, pass through the image data
            # In production, this would resize to thumbnail
            # using PIL or similar library

            # Simulate thumbnail creation
            thumbnail_data = image_data  # In production: resize to 512x512

            logger.debug(
                "Image preprocessed",
                agent_id=state.get("agent_id"),
                has_thumbnail=bool(thumbnail_data),
            )

            return {
                "thumbnail_data": thumbnail_data,
                "original_dimensions": (0, 0),  # Would be extracted from image
                "thumbnail_dimensions": (DEFAULT_THUMBNAIL_WIDTH, DEFAULT_THUMBNAIL_HEIGHT),
            }

        except Exception as e:
            logger.error(
                "Preprocessing failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "preprocessing_error": str(e),
            }

    @create_node_wrapper("screen", "tiered_vision")
    async def _screen_node(self, state: TieredVisionState) -> dict[str, Any]:
        """Tier 1: Fast screening classification.

        Args:
            state: Current workflow state.

        Returns:
            State update with screening results.
        """
        thumbnail_data = state.get("thumbnail_data", "")
        image_mime_type = state.get("image_mime_type", "image/jpeg")
        agent_config = state.get("agent_config", {})

        # Check for preprocessing errors
        if state.get("preprocessing_error"):
            return {}

        # Get screen model and routing config
        tiered_llm = agent_config.get("tiered_llm", {})
        screen_config = tiered_llm.get("screen", {})
        routing_config = agent_config.get("routing", {})

        screen_model = screen_config.get("model", "anthropic/claude-3-haiku")
        screen_threshold = routing_config.get("screen_threshold", DEFAULT_SCREEN_THRESHOLD)
        healthy_skip = routing_config.get("healthy_skip_threshold", DEFAULT_HEALTHY_SKIP_THRESHOLD)
        obvious_skip = routing_config.get("obvious_skip_threshold", DEFAULT_OBVIOUS_SKIP_THRESHOLD)

        system_prompt = self._build_screen_system_prompt()

        try:
            # Build vision message with image
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "Analyze this image and classify it."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime_type};base64,{thumbnail_data}",
                            },
                        },
                    ]
                ),
            ]

            result = await self._llm_gateway.complete(
                messages=messages,
                model=screen_model,
                agent_id=state.get("agent_id", ""),
                agent_type="tiered-vision",
                request_id=state.get("correlation_id"),
                temperature=0.1,
                max_tokens=200,
            )

            # Parse screen response
            screen_result = self._parse_screen_response(result.get("content", ""))

            classification = screen_result.get("classification", "uncertain")
            confidence = screen_result.get("confidence", 0.5)

            # Determine if we should proceed to Tier 2
            proceed_to_tier2 = True
            skip_reason: str | None = None

            if classification == "healthy" and confidence >= healthy_skip:
                proceed_to_tier2 = False
                skip_reason = f"Healthy with high confidence ({confidence:.2f} >= {healthy_skip})"
            elif classification == "obvious_issue" and confidence >= obvious_skip:
                proceed_to_tier2 = False
                skip_reason = f"Obvious issue with high confidence ({confidence:.2f} >= {obvious_skip})"
            elif classification != "uncertain" and confidence >= screen_threshold:
                proceed_to_tier2 = False
                skip_reason = f"Clear classification above threshold ({confidence:.2f} >= {screen_threshold})"

            tier1_tokens = result.get("tokens_in", 0) + result.get("tokens_out", 0)

            logger.info(
                "Tier 1 screening completed",
                agent_id=state.get("agent_id"),
                classification=classification,
                confidence=confidence,
                proceed_to_tier2=proceed_to_tier2,
                skip_reason=skip_reason,
            )

            return {
                "screen_result": ScreenResult(
                    classification=classification,  # type: ignore[typeddict-item]
                    confidence=confidence,
                    preliminary_findings=screen_result.get("findings", []),
                    skip_reason=skip_reason,
                ),
                "proceed_to_tier2": proceed_to_tier2,
                "tier2_skip_reason": skip_reason,
                "tier1_executed": True,
                "tier1_model": screen_model,
                "tier1_tokens": tier1_tokens,
            }

        except Exception as e:
            logger.error(
                "Tier 1 screening failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "screen_error": str(e),
                "tier1_executed": True,
            }

    @create_node_wrapper("diagnose", "tiered_vision")
    async def _diagnose_node(self, state: TieredVisionState) -> dict[str, Any]:
        """Tier 2: Deep diagnosis on full image.

        Args:
            state: Current workflow state.

        Returns:
            State update with diagnosis results.
        """
        image_data = state.get("image_data", "")
        image_mime_type = state.get("image_mime_type", "image/jpeg")
        agent_config = state.get("agent_config", {})
        screen_result = state.get("screen_result")

        # Get diagnose model
        tiered_llm = agent_config.get("tiered_llm", {})
        diagnose_config = tiered_llm.get("diagnose", {})

        diagnose_model = diagnose_config.get("model", "anthropic/claude-3-5-sonnet")

        # Fetch RAG context if available
        rag_context: list[dict[str, Any]] = []
        if self._ranking_service:
            try:
                rag_config = agent_config.get("rag", {})
                if rag_config.get("enabled", True):
                    # Build query from preliminary findings
                    preliminary = screen_result.get("preliminary_findings", []) if screen_result else []
                    query = " ".join(preliminary) if preliminary else "plant health diagnosis"
                    domains = rag_config.get("knowledge_domains", [])

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
                        }
                        for m in ranking_result.matches
                    ]
            except Exception as e:
                logger.warning(
                    "RAG retrieval failed for diagnosis",
                    agent_id=state.get("agent_id"),
                    error=str(e),
                )

        system_prompt = self._build_diagnose_system_prompt(rag_context)

        try:
            # Build context message
            context_parts = []
            if screen_result:
                context_parts.append(
                    f"Tier 1 screening: {screen_result.get('classification', 'unknown')} "
                    f"(confidence: {screen_result.get('confidence', 0):.2f})"
                )
                if screen_result.get("preliminary_findings"):
                    context_parts.append(f"Preliminary findings: {', '.join(screen_result['preliminary_findings'])}")

            context_text = "\n".join(context_parts) if context_parts else "No prior screening data."

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=[
                        {"type": "text", "text": f"Prior context:\n{context_text}\n\nProvide detailed diagnosis:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime_type};base64,{image_data}",
                            },
                        },
                    ]
                ),
            ]

            result = await self._llm_gateway.complete(
                messages=messages,
                model=diagnose_model,
                agent_id=state.get("agent_id", ""),
                agent_type="tiered-vision",
                request_id=state.get("correlation_id"),
                temperature=diagnose_config.get("temperature", 0.3),
                max_tokens=diagnose_config.get("max_tokens", 2000),
            )

            # Parse diagnose response
            diagnose_result = self._parse_diagnose_response(result.get("content", ""))

            tier2_tokens = result.get("tokens_in", 0) + result.get("tokens_out", 0)

            logger.info(
                "Tier 2 diagnosis completed",
                agent_id=state.get("agent_id"),
                primary_issue=diagnose_result.get("primary_issue", "unknown"),
                confidence=diagnose_result.get("confidence", 0),
                severity=diagnose_result.get("severity", "unknown"),
            )

            return {
                "diagnose_result": DiagnoseResult(
                    primary_issue=diagnose_result.get("primary_issue", "unknown"),
                    confidence=diagnose_result.get("confidence", 0.5),
                    detailed_findings=diagnose_result.get("findings", []),
                    recommendations=diagnose_result.get("recommendations", []),
                    severity=diagnose_result.get("severity", "medium"),  # type: ignore[typeddict-item]
                ),
                "rag_context": rag_context,
                "tier2_executed": True,
                "tier2_model": diagnose_model,
                "tier2_tokens": tier2_tokens,
            }

        except Exception as e:
            logger.error(
                "Tier 2 diagnosis failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "diagnose_error": str(e),
                "tier2_executed": True,
            }

    @create_node_wrapper("output", "tiered_vision")
    async def _output_node(self, state: TieredVisionState) -> dict[str, Any]:
        """Package final vision analysis result.

        Args:
            state: Current workflow state.

        Returns:
            Final state update.
        """
        screen_result = state.get("screen_result")
        diagnose_result = state.get("diagnose_result")
        screen_error = state.get("screen_error")
        diagnose_error = state.get("diagnose_error")
        preprocessing_error = state.get("preprocessing_error")

        # Determine final classification and confidence
        if diagnose_result:
            # Tier 2 was executed - use its results
            final_classification = diagnose_result.get("primary_issue", "unknown")
            final_confidence = diagnose_result.get("confidence", 0.5)
        elif screen_result:
            # Only Tier 1 was executed
            final_classification = screen_result.get("classification", "unknown")
            final_confidence = screen_result.get("confidence", 0.5)
        else:
            final_classification = "error"
            final_confidence = 0.0

        # Build output
        output: dict[str, Any] = {
            "classification": final_classification,
            "confidence": final_confidence,
            "tier1": {
                "executed": state.get("tier1_executed", False),
                "result": screen_result,
            },
            "tier2": {
                "executed": state.get("tier2_executed", False),
                "result": diagnose_result,
                "skip_reason": state.get("tier2_skip_reason"),
            },
        }

        if diagnose_result:
            output["severity"] = diagnose_result.get("severity")
            output["recommendations"] = diagnose_result.get("recommendations", [])
            output["detailed_findings"] = diagnose_result.get("detailed_findings", [])
        elif screen_result:
            output["preliminary_findings"] = screen_result.get("preliminary_findings", [])

        # Calculate total cost
        tier1_tokens = state.get("tier1_tokens", 0)
        tier2_tokens = state.get("tier2_tokens", 0)

        # Determine success
        error_message = preprocessing_error or screen_error or diagnose_error
        success = final_classification != "error" and not error_message

        logger.info(
            "Tiered-vision workflow completed",
            agent_id=state.get("agent_id"),
            final_classification=final_classification,
            final_confidence=final_confidence,
            tier1_executed=state.get("tier1_executed", False),
            tier2_executed=state.get("tier2_executed", False),
            total_tokens=tier1_tokens + tier2_tokens,
            success=success,
        )

        return {
            "output": output,
            "final_classification": final_classification,
            "final_confidence": final_confidence,
            "success": success,
            "error_message": error_message,
        }

    # Helper methods

    def _build_screen_system_prompt(self) -> str:
        """Build system prompt for Tier 1 screening."""
        return """You are a fast image screening system. Quickly classify the image into one of these categories:

- healthy: Plant appears healthy with no visible issues
- obvious_issue: Clear disease, pest, or damage visible
- uncertain: Unable to determine, needs deeper analysis

Respond with JSON only:
{
    "classification": "healthy|obvious_issue|uncertain",
    "confidence": 0.0-1.0,
    "findings": ["brief", "observations"]
}

Be conservative - if unsure, classify as uncertain."""

    def _build_diagnose_system_prompt(
        self,
        rag_context: list[dict[str, Any]],
    ) -> str:
        """Build system prompt for Tier 2 diagnosis."""
        base_prompt = """You are an expert plant pathologist. Provide detailed diagnosis of plant health issues.

Analyze the image carefully and provide:
1. Primary issue identification
2. Confidence level (0-1)
3. Detailed findings
4. Actionable recommendations
5. Severity assessment (low/medium/high/critical)

Respond with JSON:
{
    "primary_issue": "specific issue name",
    "confidence": 0.0-1.0,
    "findings": ["detailed", "observations"],
    "recommendations": ["specific", "actions"],
    "severity": "low|medium|high|critical"
}"""

        if rag_context:
            knowledge = "\n".join(
                f"- {r.get('title', 'Info')}: {r.get('content', '')[:200]}..." for r in rag_context[:3]
            )
            base_prompt += f"\n\nRelevant knowledge:\n{knowledge}"

        return base_prompt

    def _parse_screen_response(self, content: str) -> dict[str, Any]:
        """Parse Tier 1 screen response."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse screen response")
            return {
                "classification": "uncertain",
                "confidence": 0.5,
                "findings": [],
            }

    def _parse_diagnose_response(self, content: str) -> dict[str, Any]:
        """Parse Tier 2 diagnose response."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse diagnose response")
            return {
                "primary_issue": "unknown",
                "confidence": 0.5,
                "findings": [],
                "recommendations": [],
                "severity": "medium",
            }
