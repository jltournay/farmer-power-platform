"""Generator workflow implementation.

LangGraph workflow for RAG-enhanced content generation:
fetch_context → retrieve_knowledge → generate → format → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from typing import Any, Literal

import structlog
from ai_model.workflows.base import WorkflowBuilder, create_node_wrapper
from ai_model.workflows.states.generator import GeneratorState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = structlog.get_logger(__name__)


class GeneratorWorkflow(WorkflowBuilder[GeneratorState]):
    """Generator workflow for content generation.

    This workflow implements a RAG-enhanced generation pipeline:
    1. fetch_context: Load entity context via MCP
    2. retrieve_knowledge: Fetch relevant RAG knowledge
    3. generate: LLM generates content with context
    4. format: Transform to target format (json/markdown/text)
    5. output: Package final result

    Supports multiple output formats and uses RAG for
    grounding generated content in factual knowledge.
    """

    workflow_name = "generator"
    workflow_version = "1.0.0"

    def __init__(
        self,
        llm_gateway: Any,  # LLMGateway
        ranking_service: Any | None = None,  # RankingService
        mcp_integration: Any | None = None,  # MCPIntegration
        checkpointer: Any | None = None,
    ) -> None:
        """Initialize the generator workflow.

        Args:
            llm_gateway: LLM gateway for making LLM calls.
            ranking_service: Optional ranking service for RAG.
            mcp_integration: Optional MCP integration for context.
            checkpointer: Optional checkpointer for state persistence.
        """
        super().__init__(checkpointer=checkpointer)
        self._llm_gateway = llm_gateway
        self._ranking_service = ranking_service
        self._mcp_integration = mcp_integration

    def _get_state_schema(self) -> type[GeneratorState]:
        """Return the GeneratorState schema."""
        return GeneratorState

    def _build_graph(self, builder: StateGraph[GeneratorState]) -> StateGraph[GeneratorState]:
        """Build the generator workflow graph.

        Graph structure:
        START → fetch_context → retrieve_knowledge → generate → format → output → END
        """
        # Add nodes
        builder.add_node("fetch_context", self._fetch_context_node)
        builder.add_node("retrieve_knowledge", self._retrieve_knowledge_node)
        builder.add_node("generate", self._generate_node)
        builder.add_node("format", self._format_node)
        builder.add_node("output", self._output_node)

        # Add edges (linear flow)
        builder.add_edge(START, "fetch_context")
        builder.add_edge("fetch_context", "retrieve_knowledge")
        builder.add_edge("retrieve_knowledge", "generate")
        builder.add_edge("generate", "format")
        builder.add_edge("format", "output")
        builder.add_edge("output", END)

        return builder

    @create_node_wrapper("fetch_context", "generator")
    async def _fetch_context_node(self, state: GeneratorState) -> dict[str, Any]:
        """Fetch entity context via MCP.

        Args:
            state: Current workflow state.

        Returns:
            State update with MCP context.
        """
        agent_config = state.get("agent_config", {})
        input_data = state.get("input_data", {})

        result: dict[str, Any] = {}

        # Fetch MCP context if integration available
        if self._mcp_integration:
            try:
                mcp_sources = agent_config.get("mcp_sources", [])
                mcp_context = await self._fetch_mcp_context(mcp_sources, input_data)
                result["mcp_context"] = mcp_context
            except Exception as e:
                logger.warning(
                    "MCP context fetch failed",
                    agent_id=state.get("agent_id"),
                    error=str(e),
                )
                result["mcp_error"] = str(e)

        return result

    @create_node_wrapper("retrieve_knowledge", "generator")
    async def _retrieve_knowledge_node(self, state: GeneratorState) -> dict[str, Any]:
        """Retrieve relevant knowledge from RAG.

        Args:
            state: Current workflow state.

        Returns:
            State update with RAG context.
        """
        agent_config = state.get("agent_config", {})
        input_data = state.get("input_data", {})

        rag_config = agent_config.get("rag", {})

        if not rag_config.get("enabled", True) or not self._ranking_service:
            return {"rag_context": [], "rag_query": ""}

        try:
            # Build query from input or template
            query_template = rag_config.get("query_template")
            if query_template:
                query = self._render_template(query_template, input_data)
            else:
                query = self._build_generation_query(input_data)

            domains = rag_config.get("knowledge_domains", [])

            ranking_result = await self._ranking_service.rank(
                query=query,
                domains=domains,
                config=None,  # Use defaults
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
                "Knowledge retrieved",
                agent_id=state.get("agent_id"),
                matches=len(rag_context),
                query_length=len(query),
            )

            return {
                "rag_context": rag_context,
                "rag_query": query,
                "rag_domains": domains,
            }

        except Exception as e:
            logger.warning(
                "RAG retrieval failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "rag_context": [],
                "rag_error": str(e),
                "rag_query": "",
            }

    @create_node_wrapper("generate", "generator")
    async def _generate_node(self, state: GeneratorState) -> dict[str, Any]:
        """Generate content using LLM with context.

        Args:
            state: Current workflow state.

        Returns:
            State update with raw generation.
        """
        agent_config = state.get("agent_config", {})
        input_data = state.get("input_data", {})
        mcp_context = state.get("mcp_context", {})
        rag_context = state.get("rag_context", [])
        prompt_template = state.get("prompt_template", "")
        output_format: Literal["json", "markdown", "text"] = state.get("output_format", "markdown")
        llm_config = agent_config.get("llm", {})

        # Build generation prompt
        system_prompt = self._build_generation_system_prompt(output_format)
        user_prompt = self._build_generation_user_prompt(
            prompt_template,
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
                model=llm_config.get("model", "anthropic/claude-3-5-sonnet"),
                agent_id=state.get("agent_id", ""),
                agent_type="generator",
                request_id=state.get("correlation_id"),
                temperature=llm_config.get("temperature", 0.5),
                max_tokens=llm_config.get("max_tokens", 3000),
            )

            tokens_used = result.get("tokens_in", 0) + result.get("tokens_out", 0)

            logger.debug(
                "Content generated",
                agent_id=state.get("agent_id"),
                content_length=len(result.get("content", "")),
                tokens_used=tokens_used,
            )

            return {
                "raw_generation": result.get("content", ""),
                "model_used": result.get("model", ""),
                "tokens_used": tokens_used,
            }

        except Exception as e:
            logger.error(
                "Generation failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "raw_generation": "",
                "generation_error": str(e),
            }

    @create_node_wrapper("format", "generator")
    async def _format_node(self, state: GeneratorState) -> dict[str, Any]:
        """Format generated content to target format.

        Args:
            state: Current workflow state.

        Returns:
            State update with formatted output.
        """
        raw_generation = state.get("raw_generation", "")
        output_format: Literal["json", "markdown", "text"] = state.get("output_format", "markdown")

        # Check for generation errors
        if state.get("generation_error"):
            return {}

        try:
            if output_format == "json":
                formatted = self._format_as_json(raw_generation)
            elif output_format == "markdown":
                formatted = self._format_as_markdown(raw_generation)
            else:
                formatted = raw_generation.strip()

            return {"formatted_output": formatted}

        except Exception as e:
            logger.warning(
                "Formatting failed",
                agent_id=state.get("agent_id"),
                format=output_format,
                error=str(e),
            )
            return {
                "formatted_output": raw_generation,
                "format_error": str(e),
            }

    @create_node_wrapper("output", "generator")
    async def _output_node(self, state: GeneratorState) -> dict[str, Any]:
        """Package final generation result.

        Args:
            state: Current workflow state.

        Returns:
            Final state update.
        """
        formatted_output = state.get("formatted_output", "")
        output_format = state.get("output_format", "markdown")
        generation_error = state.get("generation_error")

        if generation_error:
            return {
                "output": {},
                "success": False,
                "error_message": generation_error,
            }

        output: dict[str, Any] = {
            "content": formatted_output,
            "format": output_format,
            "metadata": {
                "rag_sources_used": len(state.get("rag_context", [])),
                "rag_query": state.get("rag_query", ""),
            },
        }

        logger.info(
            "Generator workflow completed",
            agent_id=state.get("agent_id"),
            format=output_format,
            content_length=(
                len(formatted_output) if isinstance(formatted_output, str) else len(json.dumps(formatted_output))
            ),
        )

        return {
            "output": output,
            "success": True,
        }

    # Helper methods

    async def _fetch_mcp_context(
        self,
        mcp_sources: list[dict[str, Any]],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Fetch context from MCP servers.

        Story 0.75.16b: Implemented actual MCP tool calls.

        Args:
            mcp_sources: List of MCP source configurations from agent config.
            input_data: Input data to pass to MCP tools.

        Returns:
            Dictionary with context from each MCP tool call.
        """
        if not self._mcp_integration or not mcp_sources:
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
                # Get the tool from the integration
                tool = self._mcp_integration.get_tool(server, tool_name)

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

    def _render_template(
        self,
        template: str,
        data: dict[str, Any],
    ) -> str:
        """Render template with data substitution."""
        result = template
        for key, value in data.items():
            placeholder = "{{" + key + "}}"
            result = result.replace(placeholder, str(value))
        return result

    def _build_generation_query(self, input_data: dict[str, Any]) -> str:
        """Build generation query from input data."""
        # Extract text content for RAG query
        text_fields = ["topic", "subject", "description", "request", "prompt"]
        parts = []

        for field in text_fields:
            if input_data.get(field):
                parts.append(str(input_data[field]))

        return " ".join(parts) if parts else json.dumps(input_data)

    def _build_generation_system_prompt(
        self,
        output_format: Literal["json", "markdown", "text"],
    ) -> str:
        """Build system prompt for generation."""
        format_instructions = {
            "json": "Respond with valid JSON only. Structure the content appropriately.",
            "markdown": "Respond with well-formatted Markdown. Use headers, lists, and emphasis appropriately.",
            "text": "Respond with plain text. Keep formatting minimal.",
        }

        return f"""You are a content generation assistant. Generate helpful, accurate content based on the provided context and knowledge.

Output format: {output_format}
{format_instructions.get(output_format, "")}

Guidelines:
1. Use provided knowledge to ground your response in facts
2. Be clear, concise, and actionable
3. Tailor content to the specific context provided
4. If knowledge is insufficient, acknowledge limitations"""

    def _build_generation_user_prompt(
        self,
        prompt_template: str,
        input_data: dict[str, Any],
        mcp_context: dict[str, Any],
        rag_context: list[dict[str, Any]],
    ) -> str:
        """Build user prompt for generation."""
        parts = []

        # Add knowledge context first
        if rag_context:
            knowledge = "\n\n".join(
                f"**{r.get('title', 'Knowledge')}**\n{r.get('content', '')}" for r in rag_context[:5]
            )
            parts.append(f"## Relevant Knowledge\n\n{knowledge}")

        # Add entity context
        if mcp_context:
            parts.append(f"## Entity Context\n\n{json.dumps(mcp_context, indent=2)}")

        # Add request/prompt
        if prompt_template:
            user_request = self._render_template(prompt_template, input_data)
            parts.append(f"## Request\n\n{user_request}")
        else:
            parts.append(f"## Request\n\nGenerate content based on:\n{json.dumps(input_data, indent=2)}")

        return "\n\n---\n\n".join(parts)

    def _format_as_json(self, content: str) -> dict[str, Any]:
        """Parse and validate JSON output."""
        content = content.strip()

        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        return json.loads(content)

    def _format_as_markdown(self, content: str) -> str:
        """Clean and format markdown output."""
        content = content.strip()

        # Remove markdown code block wrappers if present
        if content.startswith("```markdown"):
            content = content[11:]
        if content.startswith("```md"):
            content = content[5:]
        if content.endswith("```"):
            content = content[:-3]

        return content.strip()
