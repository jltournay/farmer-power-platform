"""Extractor workflow implementation.

Linear LangGraph workflow for structured data extraction:
fetch_data → extract → validate → normalize → output

Story 0.75.16: LangGraph SDK Integration & Base Workflows
"""

import json
from typing import Any

import structlog
from ai_model.workflows.base import WorkflowBuilder, create_node_wrapper
from ai_model.workflows.states.extractor import ExtractorState
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

logger = structlog.get_logger(__name__)


class ExtractorWorkflow(WorkflowBuilder[ExtractorState]):
    """Extractor workflow for structured data extraction.

    This workflow implements a linear extraction pipeline:
    1. fetch_data: Load and prepare input data
    2. extract: Use LLM to extract structured fields
    3. validate: Validate extracted data against schema
    4. normalize: Apply normalization rules
    5. output: Package final result

    The workflow uses a single LLM call for efficient extraction.
    No RAG is needed as extraction works directly on input data.
    """

    workflow_name = "extractor"
    workflow_version = "1.0.0"

    def __init__(
        self,
        llm_gateway: Any,  # LLMGateway
        checkpointer: Any | None = None,
    ) -> None:
        """Initialize the extractor workflow.

        Args:
            llm_gateway: LLM gateway for making LLM calls.
            checkpointer: Optional checkpointer for state persistence.
        """
        super().__init__(checkpointer=checkpointer)
        self._llm_gateway = llm_gateway

    def _get_state_schema(self) -> type[ExtractorState]:
        """Return the ExtractorState schema."""
        return ExtractorState

    def _build_graph(self, builder: StateGraph[ExtractorState]) -> StateGraph[ExtractorState]:
        """Build the extractor workflow graph.

        Graph structure:
        START → fetch_data → extract → validate → normalize → output → END
        """
        # Add nodes
        builder.add_node("fetch_data", self._fetch_data_node)
        builder.add_node("extract", self._extract_node)
        builder.add_node("validate", self._validate_node)
        builder.add_node("normalize", self._normalize_node)
        builder.add_node("output", self._output_node)

        # Add edges (linear flow)
        builder.add_edge(START, "fetch_data")
        builder.add_edge("fetch_data", "extract")
        builder.add_edge("extract", "validate")
        builder.add_edge("validate", "normalize")
        builder.add_edge("normalize", "output")
        builder.add_edge("output", END)

        return builder

    @create_node_wrapper("fetch_data", "extractor")
    async def _fetch_data_node(self, state: ExtractorState) -> dict[str, Any]:
        """Fetch and prepare input data for extraction.

        Args:
            state: Current workflow state.

        Returns:
            State update with prepared input data.
        """
        input_data = state.get("input_data", {})

        logger.debug(
            "Fetching data for extraction",
            agent_id=state.get("agent_id"),
            input_keys=list(input_data.keys()) if isinstance(input_data, dict) else None,
        )

        # Input is already provided - just validate it exists
        if not input_data:
            return {
                "error_message": "No input data provided for extraction",
                "success": False,
            }

        return {}

    @create_node_wrapper("extract", "extractor")
    async def _extract_node(self, state: ExtractorState) -> dict[str, Any]:
        """Extract structured data using LLM.

        Args:
            state: Current workflow state.

        Returns:
            State update with raw extraction result.
        """
        agent_config = state["agent_config"]
        input_data = state.get("input_data", {})
        prompt_template = state.get("prompt_template", "")

        # Get extraction schema and LLM config from typed config
        extraction_schema = agent_config.extraction_schema
        llm_config = agent_config.llm

        # Build extraction prompt
        system_prompt = self._build_system_prompt(extraction_schema)
        user_prompt = self._build_user_prompt(prompt_template, input_data)

        logger.debug(
            "Extracting data with LLM",
            agent_id=state.get("agent_id"),
            model=llm_config.model,
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
                agent_type="extractor",
                request_id=state.get("correlation_id"),
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
            )

            # Parse JSON from response
            content = result.get("content", "")
            raw_extraction = self._parse_json_response(content)

            return {
                "raw_extraction": raw_extraction,
                "model_used": result.get("model", ""),
                "tokens_used": result.get("tokens_in", 0) + result.get("tokens_out", 0),
            }

        except Exception as e:
            logger.error(
                "LLM extraction failed",
                agent_id=state.get("agent_id"),
                error=str(e),
            )
            return {
                "raw_extraction": {},
                "error_message": f"Extraction failed: {e}",
                "success": False,
            }

    @create_node_wrapper("validate", "extractor")
    async def _validate_node(self, state: ExtractorState) -> dict[str, Any]:
        """Validate extracted data against schema.

        Args:
            state: Current workflow state.

        Returns:
            State update with validation results.
        """
        raw_extraction = state.get("raw_extraction", {})
        agent_config = state["agent_config"]
        extraction_schema = agent_config.extraction_schema

        # Check for prior errors
        if state.get("error_message"):
            return {}

        validation_errors: list[str] = []

        # Validate required fields
        required_fields = extraction_schema.get("required_fields", [])
        for field in required_fields:
            if field not in raw_extraction or raw_extraction[field] is None:
                validation_errors.append(f"Missing required field: {field}")

        # Validate field types if specified
        field_types = extraction_schema.get("field_types", {})
        for field, expected_type in field_types.items():
            if field in raw_extraction:
                value = raw_extraction[field]
                if not self._validate_type(value, expected_type):
                    validation_errors.append(f"Invalid type for {field}: expected {expected_type}")

        logger.debug(
            "Validation completed",
            agent_id=state.get("agent_id"),
            errors_count=len(validation_errors),
        )

        if validation_errors:
            return {
                "validation_errors": validation_errors,
                "validated_data": raw_extraction,  # Pass through for potential partial success
            }

        return {
            "validation_errors": [],
            "validated_data": raw_extraction,
        }

    @create_node_wrapper("normalize", "extractor")
    async def _normalize_node(self, state: ExtractorState) -> dict[str, Any]:
        """Apply normalization rules to extracted data.

        Args:
            state: Current workflow state.

        Returns:
            State update with normalized data.
        """
        validated_data = state.get("validated_data", {})
        agent_config = state["agent_config"]
        normalization_rules = agent_config.normalization_rules or []

        # Check for prior errors
        if state.get("error_message"):
            return {}

        normalized_data = validated_data.copy()

        for rule in normalization_rules or []:
            field = rule.get("field")
            transform = rule.get("transform")

            if field and field in normalized_data and transform:
                normalized_data[field] = self._apply_transform(
                    normalized_data[field],
                    transform,
                )

        logger.debug(
            "Normalization completed",
            agent_id=state.get("agent_id"),
            rules_applied=len(normalization_rules or []),
        )

        return {"output": normalized_data}

    @create_node_wrapper("output", "extractor")
    async def _output_node(self, state: ExtractorState) -> dict[str, Any]:
        """Package final extraction result.

        Args:
            state: Current workflow state.

        Returns:
            Final state update.
        """
        validation_errors = state.get("validation_errors", [])
        error_message = state.get("error_message")

        # Determine success
        if error_message:
            success = False
        elif validation_errors:
            success = False
            error_message = "; ".join(validation_errors)
        else:
            success = True

        logger.info(
            "Extractor workflow completed",
            agent_id=state.get("agent_id"),
            success=success,
            validation_errors=len(validation_errors),
        )

        return {
            "success": success,
            "error_message": error_message,
        }

    def _build_system_prompt(self, extraction_schema: dict[str, Any]) -> str:
        """Build system prompt for extraction.

        Args:
            extraction_schema: Schema defining fields to extract.

        Returns:
            System prompt string.
        """
        fields = extraction_schema.get("required_fields", [])
        optional_fields = extraction_schema.get("optional_fields", [])

        prompt = """You are a data extraction assistant. Extract structured data from the input.

Your response MUST be valid JSON with the following fields:

Required fields:
"""
        for field in fields:
            prompt += f"- {field}\n"

        if optional_fields:
            prompt += "\nOptional fields:\n"
            for field in optional_fields:
                prompt += f"- {field}\n"

        prompt += """
Rules:
1. Return ONLY valid JSON, no additional text
2. If a required field cannot be found, set it to null
3. Use exact field names as specified
4. Preserve data types (numbers as numbers, strings as strings)
"""
        return prompt

    def _build_user_prompt(
        self,
        prompt_template: str,
        input_data: dict[str, Any],
    ) -> str:
        """Build user prompt from template and input data.

        Args:
            prompt_template: Template string with {{placeholders}}.
            input_data: Data to fill placeholders.

        Returns:
            Rendered user prompt.
        """
        if prompt_template:
            # Simple template substitution
            result = prompt_template
            for key, value in input_data.items():
                placeholder = "{{" + key + "}}"
                result = result.replace(placeholder, str(value))
            return result

        # Default: dump input data as JSON
        return f"Extract data from the following input:\n\n{json.dumps(input_data, indent=2)}"

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response.

        Args:
            content: LLM response content.

        Returns:
            Parsed JSON dictionary.
        """
        # Try to extract JSON from response
        content = content.strip()

        # Handle markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse JSON from LLM response",
                error=str(e),
                content_preview=content[:200],
            )
            return {}

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value against expected type.

        Args:
            value: Value to validate.
            expected_type: Expected type name.

        Returns:
            True if valid, False otherwise.

        Note:
            None values are allowed for all types. This allows optional fields
            to return null when the value is missing/unknown, which is valid
            JSON representation for "no value".
        """
        # None is valid for all types (represents missing/unknown value)
        if value is None:
            return True

        type_map = {
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "list": list,
            "array": list,
            "dict": dict,
            "object": dict,
        }

        expected = type_map.get(expected_type.lower())
        if expected is None:
            return True  # Unknown type, skip validation

        return isinstance(value, expected)

    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply normalization transform to value.

        Args:
            value: Value to transform.
            transform: Transform name.

        Returns:
            Transformed value.
        """
        if not isinstance(value, str):
            return value

        transforms = {
            "uppercase": lambda v: v.upper(),
            "lowercase": lambda v: v.lower(),
            "strip": lambda v: v.strip(),
            "title": lambda v: v.title(),
        }

        transform_fn = transforms.get(transform.lower())
        if transform_fn:
            return transform_fn(value)

        return value
