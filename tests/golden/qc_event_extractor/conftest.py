"""Test fixtures for QC Event Extractor golden sample tests.

Story 0.75.17: Extractor Agent Implementation

This module provides fixtures for testing the QC Event Extractor with mocked LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from ai_model.domain.agent_config import (
    AgentConfigMetadata,
    ErrorHandlingConfig,
    ExtractorConfig,
    InputConfig,
    LLMConfig,
    OutputConfig,
)
from ai_model.workflows.extractor import ExtractorWorkflow

if TYPE_CHECKING:
    from tests.golden.framework import GoldenSampleCollection


@pytest.fixture
def qc_extractor_config() -> ExtractorConfig:
    """QC Event Extractor agent configuration."""
    return ExtractorConfig(
        id="qc-event-extractor:1.0.0",
        agent_id="qc-event-extractor",
        version="1.0.0",
        description="Extracts structured QC data from QC Analyzer END_BAG events",
        input=InputConfig(
            event="collection.document.received",
            schema={"type": "object", "required": ["raw_data"]},
        ),
        output=OutputConfig(
            event="ai.extraction.complete",
            schema={"type": "object"},
        ),
        llm=LLMConfig(
            model="anthropic/claude-3-haiku",
            temperature=0.1,
            max_tokens=500,
        ),
        extraction_schema={
            "required_fields": [
                "grade",
                "quality_score",
                "leaf_count",
                "moisture_percent",
                "extraction_confidence",
            ],
            "optional_fields": ["farmer_id", "defects", "validation_warnings"],
            "field_types": {
                "farmer_id": "string",
                "grade": "string",
                "quality_score": "number",
                "leaf_count": "integer",
                "moisture_percent": "number",
                "defects": "array",
                "validation_warnings": "array",
                "extraction_confidence": "number",
            },
        },
        normalization_rules=[
            {"field": "farmer_id", "transform": "uppercase"},
            {"field": "grade", "transform": "uppercase"},
        ],
        error_handling=ErrorHandlingConfig(),
        metadata=AgentConfigMetadata(author="test"),
    )


@pytest.fixture
def qc_extractor_prompt() -> str:
    """Load QC Event Extractor prompt template from config file."""
    prompt_file = Path(__file__).parent.parent.parent.parent / "config/prompts/qc-event-extractor.json"
    if prompt_file.exists():
        config = json.loads(prompt_file.read_text())
        return config["content"]["template"]
    return "Extract QC data from: {{raw_data}}"


def create_mock_llm_response(expected_output: dict[str, Any]) -> dict[str, Any]:
    """Create a mock LLM response for a given expected output.

    Args:
        expected_output: The expected output from the golden sample.

    Returns:
        Mock LLM response dict.
    """
    return {
        "content": json.dumps(expected_output),
        "model": "anthropic/claude-3-haiku",
        "tokens_in": 150,
        "tokens_out": 75,
    }


@pytest.fixture
def mock_llm_gateway_factory():
    """Factory fixture to create mock LLM gateway with specific response."""

    def _factory(expected_output: dict[str, Any]) -> MagicMock:
        gateway = MagicMock()
        gateway.complete = AsyncMock(return_value=create_mock_llm_response(expected_output))
        return gateway

    return _factory


@pytest.fixture
def mock_llm_gateway() -> MagicMock:
    """Default mock LLM gateway (returns empty response)."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value={
            "content": "{}",
            "model": "anthropic/claude-3-haiku",
            "tokens_in": 100,
            "tokens_out": 50,
        }
    )
    return gateway


@pytest.fixture
def extractor_workflow(mock_llm_gateway: MagicMock) -> ExtractorWorkflow:
    """Extractor workflow instance with mocked LLM."""
    return ExtractorWorkflow(llm_gateway=mock_llm_gateway)


@pytest.fixture
def golden_samples_path() -> Path:
    """Path to golden samples directory."""
    return Path(__file__).parent


@pytest.fixture
def load_golden_samples(golden_samples_path: Path) -> GoldenSampleCollection:
    """Load golden samples from JSON file."""
    from tests.golden.framework import GoldenSampleCollection

    samples_file = golden_samples_path / "samples.json"
    data = json.loads(samples_file.read_text())
    return GoldenSampleCollection(**data)
