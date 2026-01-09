"""Explorer workflow implementation.

LangGraph workflow with saga pattern for multi-analyzer diagnosis:
fetch_context → triage → (conditional) → analyze → aggregate → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import asyncio
import json
from typing import Any, Literal

import structlog
from ai_model.workflows.base import WorkflowBuilder, create_node_wrapper
from ai_model.workflows.states.explorer import AnalyzerResult, ExplorerState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = structlog.get_logger(__name__)

# Default timeout for parallel analyzer branches (seconds)
DEFAULT_BRANCH_TIMEOUT = 30

# Triage confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.7


class ExplorerWorkflow(WorkflowBuilder[ExplorerState]):
    """Explorer workflow implementing saga pattern for diagnosis.

    This workflow implements a multi-step diagnostic pipeline:
    1. fetch_context: Load context via MCP + RAG
    2. triage: Initial classification with confidence
    3. (conditional routing): Single vs parallel analyzers
    4. analyze: Execute selected analyzer(s)
    5. aggregate: Combine findings from all analyzers
    6. output: Package final diagnosis

    Saga Pattern:
    - If triage confidence >= 0.7: route to single best analyzer
    - If triage confidence < 0.7: parallel execution with timeout
    - Partial failures are handled gracefully
    """

    workflow_name = "explorer"
    workflow_version = "1.0.0"

    def __init__(
        self,
        llm_gateway: Any,  # LLMGateway
        ranking_service: Any | None = None,  # RankingService
        mcp_integration: Any | None = None,  # MCPIntegration
        tool_provider: Any | None = None,  # AgentToolProvider (Story 0.75.16b)
        checkpointer: Any | None = None,
        branch_timeout_seconds: int = DEFAULT_BRANCH_TIMEOUT,
    ) -> None:
        """Initialize the explorer workflow.

        Args:
            llm_gateway: LLM gateway for making LLM calls.
            ranking_service: Optional ranking service for RAG.
            mcp_integration: Optional MCP integration for context.
            tool_provider: Optional AgentToolProvider for MCP tool resolution (Story 0.75.16b).
            checkpointer: Optional checkpointer for state persistence.
            branch_timeout_seconds: Timeout for parallel analyzer branches.
        """
        super().__init__(checkpointer=checkpointer)
        self._llm_gateway = llm_gateway
        self._ranking_service = ranking_service
        self._mcp_integration = mcp_integration
        self._tool_provider = tool_provider
        self._branch_timeout_seconds = branch_timeout_seconds

    def _get_state_schema(self) -> type[ExplorerState]:
        """Return the ExplorerState schema."""
        return ExplorerState

    def _build_graph(self, builder: StateGraph[ExplorerState]) -> StateGraph[ExplorerState]:
        """Build the explorer workflow graph with conditional routing.

        Graph structure:
        START → fetch_context → triage → (router) → analyze → aggregate → output → END
                                            ↓
                               single_analyze or parallel_analyze
        """
        # Add nodes
        builder.add_node("fetch_context", self._fetch_context_node)
        builder.add_node("triage", self._triage_node)
        builder.add_node("single_analyze", self._single_analyze_node)
        builder.add_node("parallel_analyze", self._parallel_analyze_node)
        builder.add_node("aggregate", self._aggregate_node)
        builder.add_node("output", self._output_node)

        # Add edges
        builder.add_edge(START, "fetch_context")
        builder.add_edge("fetch_context", "triage")

        # Conditional routing after triage
        builder.add_conditional_edges(
            "triage",
            self._route_after_triage,
            {
                "single": "single_analyze",
                "parallel": "parallel_analyze",
                "error": "output",
            },
        )

        builder.add_edge("single_analyze", "aggregate")
        builder.add_edge("parallel_analyze", "aggregate")
        builder.add_edge("aggregate", "output")
        builder.add_edge("output", END)

        return builder

    def _route_after_triage(self, state: ExplorerState) -> Literal["single", "parallel", "error"]:
        """Determine routing based on triage results.

        Args:
            state: Current workflow state.

        Returns:
            Route name: 'single', 'parallel', or 'error'.
        """
        # Check for prior errors
        if state.get("error_message"):
            return "error"

        route_type = state.get("route_type", "parallel")
        return route_type  # type: ignore[return-value]

    @create_node_wrapper("fetch_context", "explorer")
    async def _fetch_context_node(self, state: ExplorerState) -> dict[str, Any]:
        """Fetch context from MCP and RAG.

        Args:
            state: Current workflow state.

        Returns:
            State update with MCP and RAG context.
        """
        agent_config = state["agent_config"]
        input_data = state.get("input_data", {})

        result: dict[str, Any] = {
            "branch_timeout_seconds": self._branch_timeout_seconds,
        }

        # Fetch MCP context if integration available
        if self._mcp_integration:
            try:
                mcp_sources = agent_config.mcp_sources
                mcp_context = await self._fetch_mcp_context(mcp_sources, input_data)
                result["mcp_context"] = mcp_context
            except Exception as e:
                logger.warning(
                    "MCP context fetch failed",
                    agent_id=state.get("agent_id"),
                    error=str(e),
                )
                result["mcp_error"] = str(e)

        # Fetch RAG context if ranking service available
        if self._ranking_service:
            try:
                rag_config = agent_config.rag
                if rag_config.enabled:
                    # Build query from input data
                    query = self._build_analysis_query(input_data)
                    domains = rag_config.knowledge_domains

                    ranking_result = await self._ranking_service.rank(
                        query=query,
                        domains=domains,
                        config=None,  # Use defaults
                    )

                    result["rag_context"] = [
                        {
                            "content": m.content,
                            "title": m.title,
                            "domain": m.domain,
                            "score": m.rerank_score,
                        }
                        for m in ranking_result.matches
                    ]
                    result["analysis_query"] = query
                    result["rag_domain"] = ",".join(domains) if domains else "all"
            except Exception as e:
                logger.warning(
                    "RAG context fetch failed",
                    agent_id=state.get("agent_id"),
                    error=str(e),
                )
                result["rag_error"] = str(e)
                result["rag_context"] = []

        return result

    @create_node_wrapper("triage", "explorer")
    async def _triage_node(self, state: ExplorerState) -> dict[str, Any]:
        """Perform initial triage to classify and route.

        Args:
            state: Current workflow state.

        Returns:
            State update with triage results and routing decision.
        """
        agent_config = state["agent_config"]
        input_data = state.get("input_data", {})
        mcp_context = state.get("mcp_context", {})
        rag_context = state.get("rag_context", [])
        llm_config = agent_config.llm

        # Build triage prompt
        system_prompt = self._build_triage_system_prompt()
        user_prompt = self._build_triage_user_prompt(input_data, mcp_context, rag_context)

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            result = await self._llm_gateway.complete(
                messages=messages,
                model=llm_config.model,
                agent_id=state.get("agent_id", ""),
                agent_type="explorer",
                request_id=state.get("correlation_id"),
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=500,
            )

            # Parse triage response
            triage_result = self._parse_triage_response(result.get("content", ""))

            category = triage_result.get("category", "unknown")
            confidence = triage_result.get("confidence", 0.5)
            secondary = triage_result.get("secondary_categories", [])

            # Determine routing
            if confidence >= HIGH_CONFIDENCE_THRESHOLD:
                route_type: Literal["single", "parallel"] = "single"
                selected_analyzers = [category]
            else:
                route_type = "parallel"
                # Select primary + secondary categories for parallel analysis
                selected_analyzers = [category, *secondary[:2]]  # Max 3 analyzers

            tokens_used = state.get("tokens_used", 0) + result.get("tokens_in", 0) + result.get("tokens_out", 0)

            logger.info(
                "Triage completed",
                agent_id=state.get("agent_id"),
                category=category,
                confidence=confidence,
                route_type=route_type,
                selected_analyzers=selected_analyzers,
            )

            return {
                "triage_category": category,
                "triage_confidence": confidence,
                "triage_secondary_categories": secondary,
                "route_type": route_type,
                "selected_analyzers": selected_analyzers,
                "model_used": result.get("model", ""),
                "tokens_used": tokens_used,
            }

        except Exception as e:
            logger.error(
                "Triage failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "error_message": f"Triage failed: {e}",
                "success": False,
            }

    @create_node_wrapper("single_analyze", "explorer")
    async def _single_analyze_node(self, state: ExplorerState) -> dict[str, Any]:
        """Execute single analyzer for high-confidence triage.

        Args:
            state: Current workflow state.

        Returns:
            State update with analyzer results.
        """
        selected_analyzers = state.get("selected_analyzers", [])

        if not selected_analyzers:
            return {"analyzer_results": [], "failed_branches": []}

        analyzer_id = selected_analyzers[0]
        result = await self._run_analyzer(state, analyzer_id)

        if result.get("success", False):
            return {"analyzer_results": [result]}
        else:
            return {"analyzer_results": [], "failed_branches": [analyzer_id]}

    @create_node_wrapper("parallel_analyze", "explorer")
    async def _parallel_analyze_node(self, state: ExplorerState) -> dict[str, Any]:
        """Execute multiple analyzers in parallel with timeout.

        Args:
            state: Current workflow state.

        Returns:
            State update with all analyzer results.
        """
        selected_analyzers = state.get("selected_analyzers", [])
        timeout = state.get("branch_timeout_seconds", DEFAULT_BRANCH_TIMEOUT)

        if not selected_analyzers:
            return {"analyzer_results": [], "failed_branches": []}

        # Run analyzers in parallel with timeout
        tasks = [self._run_analyzer(state, analyzer_id) for analyzer_id in selected_analyzers]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout,
            )
        except TimeoutError:
            logger.warning(
                "Parallel analyze timed out",
                agent_id=state.get("agent_id"),
                timeout=timeout,
            )
            results = []

        # Process results
        analyzer_results: list[AnalyzerResult] = []
        failed_branches: list[str] = []

        for idx, result in enumerate(results):
            analyzer_id = selected_analyzers[idx] if idx < len(selected_analyzers) else "unknown"

            if isinstance(result, Exception):
                logger.warning(
                    "Analyzer failed",
                    analyzer_id=analyzer_id,
                    error=str(result),
                )
                failed_branches.append(analyzer_id)
            elif isinstance(result, dict) and result.get("success", False):
                analyzer_results.append(result)  # type: ignore[arg-type]
            else:
                failed_branches.append(analyzer_id)

        logger.info(
            "Parallel analysis completed",
            agent_id=state.get("agent_id"),
            successful=len(analyzer_results),
            failed=len(failed_branches),
        )

        return {
            "analyzer_results": analyzer_results,
            "failed_branches": failed_branches,
        }

    async def _run_analyzer(
        self,
        state: ExplorerState,
        analyzer_id: str,
    ) -> AnalyzerResult:
        """Run a single analyzer.

        Args:
            state: Current workflow state.
            analyzer_id: ID of the analyzer to run.

        Returns:
            AnalyzerResult with findings.
        """
        agent_config = state["agent_config"]
        input_data = state.get("input_data", {})
        mcp_context = state.get("mcp_context", {})
        rag_context = state.get("rag_context", [])
        llm_config = agent_config.llm

        system_prompt = self._build_analyzer_system_prompt(analyzer_id)
        user_prompt = self._build_analyzer_user_prompt(
            analyzer_id,
            input_data,
            mcp_context,
            rag_context,
        )

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            result = await self._llm_gateway.complete(
                messages=messages,
                model=llm_config.model,
                agent_id=state.get("agent_id", ""),
                agent_type="explorer",
                request_id=state.get("correlation_id"),
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
            )

            # Parse analyzer response
            analysis = self._parse_analyzer_response(result.get("content", ""))

            return AnalyzerResult(
                analyzer_id=analyzer_id,
                category=analyzer_id,
                confidence=analysis.get("confidence", 0.5),
                findings=analysis.get("findings", []),
                recommendations=analysis.get("recommendations", []),
                success=True,
                error=None,
            )

        except Exception as e:
            logger.error(
                "Analyzer execution failed",
                analyzer_id=analyzer_id,
                error=str(e),
            )
            return AnalyzerResult(
                analyzer_id=analyzer_id,
                category=analyzer_id,
                confidence=0.0,
                findings=[],
                recommendations=[],
                success=False,
                error=str(e),
            )

    @create_node_wrapper("aggregate", "explorer")
    async def _aggregate_node(self, state: ExplorerState) -> dict[str, Any]:
        """Aggregate results from all analyzers.

        Args:
            state: Current workflow state.

        Returns:
            State update with aggregated diagnosis.
        """
        analyzer_results = state.get("analyzer_results", [])

        if not analyzer_results:
            return {
                "primary_diagnosis": None,
                "secondary_diagnoses": [],
            }

        # Sort by confidence
        sorted_results = sorted(
            analyzer_results,
            key=lambda r: r.get("confidence", 0),
            reverse=True,
        )

        primary = sorted_results[0] if sorted_results else None
        secondary = [r for r in sorted_results[1:] if r.get("confidence", 0) >= 0.5]

        logger.info(
            "Aggregation completed",
            agent_id=state.get("agent_id"),
            primary_category=primary.get("category") if primary else None,
            secondary_count=len(secondary),
        )

        return {
            "primary_diagnosis": primary,
            "secondary_diagnoses": secondary,
        }

    @create_node_wrapper("output", "explorer")
    async def _output_node(self, state: ExplorerState) -> dict[str, Any]:
        """Package final diagnosis result.

        Args:
            state: Current workflow state.

        Returns:
            Final state update.
        """
        primary = state.get("primary_diagnosis")
        secondary = state.get("secondary_diagnoses", [])
        failed_branches = state.get("failed_branches", [])
        error_message = state.get("error_message")

        if error_message:
            return {"success": False}

        # Build output
        output: dict[str, Any] = {
            "diagnosis": {
                "primary": primary,
                "secondary": secondary,
            },
            "metadata": {
                "triage_category": state.get("triage_category"),
                "triage_confidence": state.get("triage_confidence"),
                "analyzers_executed": len(state.get("analyzer_results", [])),
                "failed_analyzers": failed_branches,
            },
        }

        success = primary is not None and primary.get("success", False)

        logger.info(
            "Explorer workflow completed",
            agent_id=state.get("agent_id"),
            success=success,
            primary_category=primary.get("category") if primary else None,
        )

        return {
            "output": output,
            "success": success,
        }

    # Helper methods

    async def _fetch_mcp_context(
        self,
        mcp_sources: list[dict[str, Any]],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Fetch context from MCP servers.

        Story 0.75.16b: Implemented actual MCP tool calls via AgentToolProvider.

        Args:
            mcp_sources: List of MCP source configurations from agent config.
            input_data: Input data to pass to MCP tools.

        Returns:
            Dictionary with context from each MCP tool call.
        """
        # Prefer tool_provider (Story 0.75.16b), fallback to mcp_integration
        tool_source = self._tool_provider or self._mcp_integration
        if not tool_source or not mcp_sources:
            return {}

        context: dict[str, Any] = {}

        for source in mcp_sources:
            server = source.get("server", "")
            tool_name = source.get("tool", "")
            arg_mapping = source.get("arg_mapping", {})

            if not server or not tool_name:
                logger.warning("Invalid MCP source config", source=source)
                continue

            try:
                # Get the tool from tool_provider or mcp_integration
                tool = tool_source.get_tool(server, tool_name)

                # Build tool arguments from input data using arg_mapping
                tool_args = {}
                for arg_name, input_key in arg_mapping.items():
                    if input_key in input_data:
                        tool_args[arg_name] = input_data[input_key]

                # Invoke the tool
                result = await tool.ainvoke(tool_args)

                # Store result under server.tool key
                key = f"{server}.{tool_name}"
                context[key] = result

                logger.debug(
                    "MCP tool call succeeded",
                    server=server,
                    tool=tool_name,
                    result_type=type(result).__name__,
                )

            except ValueError as e:
                # Server not registered or tool not found
                logger.warning(
                    "MCP tool not available",
                    server=server,
                    tool=tool_name,
                    error=str(e),
                )
            except Exception as e:
                # Tool invocation failed
                logger.warning(
                    "MCP tool call failed",
                    server=server,
                    tool=tool_name,
                    error=str(e),
                )

        return context

    def _build_analysis_query(self, input_data: dict[str, Any]) -> str:
        """Build analysis query from input data."""
        # Extract text content for RAG query
        text_fields = ["description", "symptoms", "observations", "notes"]
        parts = []

        for field in text_fields:
            if input_data.get(field):
                parts.append(str(input_data[field]))

        return " ".join(parts) if parts else json.dumps(input_data)

    def _build_triage_system_prompt(self) -> str:
        """Build system prompt for triage."""
        return """You are a diagnostic triage system. Analyze the input and classify it into one of these categories:
- disease: Plant disease or pest issue
- weather: Weather-related damage or stress
- technique: Farming technique issue
- nutrition: Nutrient deficiency or excess
- unknown: Cannot determine

Respond with JSON:
{
    "category": "primary category",
    "confidence": 0.0-1.0,
    "secondary_categories": ["list", "of", "alternatives"]
}"""

    def _build_triage_user_prompt(
        self,
        input_data: dict[str, Any],
        mcp_context: dict[str, Any],
        rag_context: list[dict[str, Any]],
    ) -> str:
        """Build user prompt for triage."""
        parts = [f"Input data:\n{json.dumps(input_data, indent=2)}"]

        if mcp_context:
            parts.append(f"\nContext:\n{json.dumps(mcp_context, indent=2)}")

        if rag_context:
            knowledge = "\n".join(
                f"- {r.get('title', 'Unknown')}: {r.get('content', '')[:200]}..." for r in rag_context[:3]
            )
            parts.append(f"\nRelevant knowledge:\n{knowledge}")

        return "\n".join(parts)

    def _parse_triage_response(self, content: str) -> dict[str, Any]:
        """Parse triage response from LLM."""
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse triage response")
            return {"category": "unknown", "confidence": 0.5, "secondary_categories": []}

    def _build_analyzer_system_prompt(self, analyzer_id: str) -> str:
        """Build system prompt for specific analyzer."""
        prompts = {
            "disease": "You are a plant disease specialist. Analyze symptoms and diagnose potential diseases.",
            "weather": "You are a weather impact analyst. Assess weather-related damage to crops.",
            "technique": "You are a farming technique advisor. Identify technique-related issues.",
            "nutrition": "You are a plant nutrition expert. Diagnose nutrient deficiencies or excesses.",
            "unknown": "You are a general agricultural analyst. Provide broad analysis.",
        }

        base_prompt = prompts.get(analyzer_id, prompts["unknown"])
        return f"""{base_prompt}

Respond with JSON:
{{
    "confidence": 0.0-1.0,
    "findings": ["list", "of", "specific", "findings"],
    "recommendations": ["list", "of", "actionable", "recommendations"]
}}"""

    def _build_analyzer_user_prompt(
        self,
        analyzer_id: str,
        input_data: dict[str, Any],
        mcp_context: dict[str, Any],
        rag_context: list[dict[str, Any]],
    ) -> str:
        """Build user prompt for specific analyzer."""
        parts = [
            f"Analyze from {analyzer_id} perspective:",
            f"\nInput:\n{json.dumps(input_data, indent=2)}",
        ]

        if mcp_context:
            parts.append(f"\nContext:\n{json.dumps(mcp_context, indent=2)}")

        if rag_context:
            knowledge = "\n".join(
                f"- {r.get('title', 'Unknown')}: {r.get('content', '')[:300]}..." for r in rag_context[:5]
            )
            parts.append(f"\nRelevant knowledge:\n{knowledge}")

        return "\n".join(parts)

    def _parse_analyzer_response(self, content: str) -> dict[str, Any]:
        """Parse analyzer response from LLM."""
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse analyzer response")
            return {"confidence": 0.5, "findings": [], "recommendations": []}
