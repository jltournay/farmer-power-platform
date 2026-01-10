"""Golden sample tests for Disease Diagnosis Explorer agent.

Story 0.75.19: Explorer Agent Implementation - Sample Config & Golden Tests

This module tests the Disease Diagnosis Explorer workflow using golden samples.
Each sample is a validated input/output pair that represents expected behavior.

Golden samples cover:
- Fungal diseases (blister blight, grey blight)
- Nutrient deficiencies (nitrogen, phosphorus)
- Pest infestations (red spider mite)
- Weather damage (frost)
- Technique issues (over-pruning)
- Edge cases (healthy plant, low confidence, contradictory symptoms)

Run with:
    pytest tests/golden/disease_diagnosis/ -v -m golden
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from ai_model.workflows.explorer import ExplorerWorkflow
from ai_model.workflows.states.explorer import ExplorerState

from tests.golden.framework import (
    GoldenSampleCollection,
    GoldenSampleRunner,
    GoldenSampleValidator,
    ValidationResult,
)

if TYPE_CHECKING:
    from ai_model.domain.agent_config import ExplorerConfig

# Mark all tests in this module as golden sample tests
pytestmark = pytest.mark.golden


class TestDiseaseDiagnosisGoldenSamples:
    """Golden sample tests for Disease Diagnosis Explorer.

    These tests verify that the ExplorerWorkflow produces outputs matching
    golden samples when given the same inputs.

    Tests use mocked LLM to return expected outputs (deterministic testing).
    """

    @pytest.fixture
    def golden_collection(self) -> GoldenSampleCollection:
        """Load golden sample collection."""
        samples_path = Path(__file__).parent / "samples.json"
        data = json.loads(samples_path.read_text())
        return GoldenSampleCollection(**data)

    def test_sample_count_matches_expected(
        self,
        golden_collection: GoldenSampleCollection,
    ) -> None:
        """Validate sample count matches parametrized test range.

        If this test fails, update the range(N) in test_golden_sample_diagnosis
        to match the actual sample count.
        """
        expected_count = 10  # Must match range() in test_golden_sample_diagnosis
        actual_count = len(golden_collection.samples)
        assert actual_count == expected_count, (
            f"Sample count mismatch: expected {expected_count}, got {actual_count}. "
            f"Update range({expected_count}) in test_golden_sample_diagnosis to range({actual_count})"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sample_index",
        list(range(10)),  # Must match expected_count in test_sample_count_matches_expected
        ids=lambda i: f"GS-diag-{i + 1:03d}",
    )
    async def test_golden_sample_diagnosis(
        self,
        sample_index: int,
        golden_collection: GoldenSampleCollection,
        disease_diagnosis_config: ExplorerConfig,
        disease_diagnosis_prompt: str,
        mock_llm_gateway_factory,
        mock_ranking_service,
        mock_mcp_integration,
    ) -> None:
        """Test diagnosis against each golden sample.

        Args:
            sample_index: Index of the sample in the collection.
            golden_collection: The golden sample collection.
            disease_diagnosis_config: Agent configuration.
            disease_diagnosis_prompt: Prompt template.
            mock_llm_gateway_factory: Factory to create mock LLM gateway.
            mock_ranking_service: Mock RAG ranking service.
            mock_mcp_integration: Mock MCP integration.
        """
        sample = golden_collection.samples[sample_index]
        expected_output = sample.expected_output

        # Create mock LLM gateway that returns the expected output
        mock_gateway = mock_llm_gateway_factory(expected_output)

        # Create workflow with mocked dependencies
        workflow = ExplorerWorkflow(
            llm_gateway=mock_gateway,
            ranking_service=mock_ranking_service,
            mcp_integration=mock_mcp_integration,
        )

        # Build initial state from sample input
        initial_state: ExplorerState = {
            "input_data": sample.input,
            "agent_id": "disease-diagnosis",
            "agent_config": disease_diagnosis_config,
            "prompt_template": disease_diagnosis_prompt,
            "correlation_id": f"test-{sample.metadata.sample_id}",
        }

        # Execute workflow
        result = await workflow.execute(initial_state)

        # Validate output
        validator = GoldenSampleValidator(strict_mode=False, ignore_extra_fields=True)
        validations = validator.validate(
            expected=expected_output,
            actual=result.get("output", {}),
            acceptable_variance=sample.acceptable_variance,
        )

        # Check all validations passed
        failed_validations = [v for v in validations if v.result == ValidationResult.FAIL]

        assert result["success"], f"Workflow failed: {result.get('error_message')}"
        assert not failed_validations, f"Golden sample {sample.metadata.sample_id} failed:\n" + "\n".join(
            f"  - {v.field_name}: expected {v.expected}, got {v.actual} ({v.message})" for v in failed_validations
        )

    @pytest.mark.asyncio
    async def test_all_priority_p0_samples(
        self,
        golden_collection: GoldenSampleCollection,
        disease_diagnosis_config: ExplorerConfig,
        disease_diagnosis_prompt: str,
        mock_llm_gateway_factory,
        mock_ranking_service,
        mock_mcp_integration,
    ) -> None:
        """Test all P0 (critical) golden samples.

        P0 samples represent core functionality that must always work.
        """
        p0_samples = [s for s in golden_collection.samples if s.metadata.priority == "P0"]

        assert len(p0_samples) >= 5, "Expected at least 5 P0 golden samples"

        for sample in p0_samples:
            mock_gateway = mock_llm_gateway_factory(sample.expected_output)
            workflow = ExplorerWorkflow(
                llm_gateway=mock_gateway,
                ranking_service=mock_ranking_service,
                mcp_integration=mock_mcp_integration,
            )

            initial_state: ExplorerState = {
                "input_data": sample.input,
                "agent_id": "disease-diagnosis",
                "agent_config": disease_diagnosis_config,
                "prompt_template": disease_diagnosis_prompt,
                "correlation_id": f"test-p0-{sample.metadata.sample_id}",
            }

            result = await workflow.execute(initial_state)
            assert result["success"], f"P0 sample {sample.metadata.sample_id} failed: {result.get('error_message')}"

    @pytest.mark.asyncio
    async def test_edge_case_samples(
        self,
        golden_collection: GoldenSampleCollection,
        disease_diagnosis_config: ExplorerConfig,
        disease_diagnosis_prompt: str,
        mock_llm_gateway_factory,
        mock_ranking_service,
        mock_mcp_integration,
    ) -> None:
        """Test edge case golden samples.

        Edge cases include:
        - Healthy plant with no issues
        - Low confidence / undetermined diagnosis
        - Contradictory symptoms
        - Unusual regional patterns
        """
        edge_case_samples = [s for s in golden_collection.samples if "edge-case" in s.metadata.tags]

        assert len(edge_case_samples) >= 2, "Expected at least 2 edge case golden samples"

        for sample in edge_case_samples:
            mock_gateway = mock_llm_gateway_factory(sample.expected_output)
            workflow = ExplorerWorkflow(
                llm_gateway=mock_gateway,
                ranking_service=mock_ranking_service,
                mcp_integration=mock_mcp_integration,
            )

            initial_state: ExplorerState = {
                "input_data": sample.input,
                "agent_id": "disease-diagnosis",
                "agent_config": disease_diagnosis_config,
                "prompt_template": disease_diagnosis_prompt,
                "correlation_id": f"test-edge-{sample.metadata.sample_id}",
            }

            result = await workflow.execute(initial_state)
            assert result["success"], f"Edge case {sample.metadata.sample_id} failed: {result.get('error_message')}"


class TestDiseaseDiagnosisGoldenRunner:
    """Test using the GoldenSampleRunner for batch execution."""

    @pytest.fixture
    def runner(self) -> GoldenSampleRunner:
        """Create golden sample runner."""
        base_path = Path(__file__).parent.parent
        return GoldenSampleRunner(base_path=base_path)

    @pytest.mark.asyncio
    async def test_run_collection_with_runner(
        self,
        runner: GoldenSampleRunner,
        disease_diagnosis_config: ExplorerConfig,
        disease_diagnosis_prompt: str,
        mock_llm_gateway_factory,
    ) -> None:
        """Run all samples using GoldenSampleRunner.

        This test validates the runner framework by returning expected outputs
        for each sample, simulating a perfectly working diagnosis.
        """
        # Load samples to create a lookup for expected outputs
        samples_path = Path(__file__).parent / "samples.json"
        samples_data = json.loads(samples_path.read_text())
        expected_outputs = {s["metadata"]["sample_id"]: s["expected_output"] for s in samples_data["samples"]}

        async def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            """Agent function that returns expected output for each sample.

            This simulates a working diagnosis to validate the runner framework.
            """
            # Find matching sample by input signature
            for sample in samples_data["samples"]:
                if sample["input"] == input_data:
                    return sample["expected_output"]
            # Fallback - return empty (will fail validation)
            return {}

        results = await runner.run_collection(
            agent_name="disease_diagnosis",
            agent_fn=agent_fn,
        )

        # Verify we got results for all samples
        assert len(results) == 10, f"Expected 10 sample results, got {len(results)}"

        # Generate report
        report = runner.generate_report(results)
        assert "GOLDEN SAMPLE TEST REPORT" in report

        # With expected outputs returned, all should pass
        passed_count = sum(1 for r in results if r.passed)
        assert passed_count >= 8, f"Expected at least 8 passed, got {passed_count}"

    @pytest.mark.asyncio
    async def test_run_collection_filtered_by_priority(
        self,
        runner: GoldenSampleRunner,
    ) -> None:
        """Test filtering samples by priority."""

        async def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {}

        results = await runner.run_collection(
            agent_name="disease_diagnosis",
            agent_fn=agent_fn,
            filter_priority="P0",
        )

        # Should have fewer than total samples
        assert len(results) > 0, "Expected some P0 samples"
        assert len(results) < 10, "Expected P0 filter to reduce sample count"

    @pytest.mark.asyncio
    async def test_run_collection_filtered_by_tags(
        self,
        runner: GoldenSampleRunner,
    ) -> None:
        """Test filtering samples by tags."""

        async def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {}

        results = await runner.run_collection(
            agent_name="disease_diagnosis",
            agent_fn=agent_fn,
            filter_tags=["fungal"],
        )

        # Should have samples with fungal tag
        assert len(results) > 0, "Expected some fungal samples"


class TestDiseaseDiagnosisFixtures:
    """Tests for fixture behavior and edge cases."""

    def test_prompt_fixture_loads_from_file(self, disease_diagnosis_prompt: str) -> None:
        """Verify prompt fixture loads content from config file."""
        # Should contain the template from disease-diagnosis.json
        assert "Analyze" in disease_diagnosis_prompt or "diagnose" in disease_diagnosis_prompt.lower()
        assert "{{" in disease_diagnosis_prompt  # Has template variables

    def test_config_fixture_has_rag_enabled(self, disease_diagnosis_config: ExplorerConfig) -> None:
        """Verify config fixture has RAG enabled (required for Explorer)."""
        assert disease_diagnosis_config.rag.enabled is True
        assert len(disease_diagnosis_config.rag.knowledge_domains) >= 2
        assert "tea-disease" in disease_diagnosis_config.rag.knowledge_domains

    def test_config_fixture_has_mcp_sources(self, disease_diagnosis_config: ExplorerConfig) -> None:
        """Verify config fixture has MCP sources configured."""
        assert len(disease_diagnosis_config.mcp_sources) >= 2
        server_names = [s.server for s in disease_diagnosis_config.mcp_sources]
        assert "plantation-mcp" in server_names
        assert "collection-mcp" in server_names


class TestDiseaseDiagnosisValidation:
    """Tests for diagnosis validation behavior."""

    @pytest.fixture
    def validator(self) -> GoldenSampleValidator:
        """Create validator instance."""
        return GoldenSampleValidator(strict_mode=False, ignore_extra_fields=True)

    def test_validate_diagnosis_exact_match(self, validator: GoldenSampleValidator) -> None:
        """Test exact match validation for diagnosis."""
        expected = {
            "diagnosis": {
                "condition": "tea_blister_blight",
                "confidence": 0.88,
                "severity": "moderate",
            }
        }
        actual = {
            "diagnosis": {
                "condition": "tea_blister_blight",
                "confidence": 0.88,
                "severity": "moderate",
            }
        }

        validations = validator.validate(expected, actual)
        assert all(v.result == ValidationResult.PASS for v in validations)

    def test_validate_confidence_with_variance(self, validator: GoldenSampleValidator) -> None:
        """Test validation with acceptable confidence variance."""
        expected = {
            "diagnosis": {
                "condition": "tea_blister_blight",
                "confidence": 0.88,
            }
        }
        actual = {
            "diagnosis": {
                "condition": "tea_blister_blight",
                "confidence": 0.85,  # Within 0.1 variance
            }
        }
        variance = {"diagnosis.confidence": 0.1}

        validations = validator.validate(expected, actual, variance)
        # Should pass or pass with variance
        assert all(v.result in (ValidationResult.PASS, ValidationResult.VARIANCE) for v in validations)

    def test_validate_recommendations_order_independent(self, validator: GoldenSampleValidator) -> None:
        """Test recommendation array validation is order-independent."""
        expected = {"recommendations": ["Apply fungicide", "Improve drainage", "Monitor plants"]}
        actual = {"recommendations": ["Monitor plants", "Apply fungicide", "Improve drainage"]}

        validations = validator.validate(expected, actual)
        assert all(v.result == ValidationResult.PASS for v in validations)

    def test_validate_condition_mismatch(self, validator: GoldenSampleValidator) -> None:
        """Test condition mismatch validation fails."""
        expected = {
            "diagnosis": {
                "condition": "tea_blister_blight",
            }
        }
        actual = {
            "diagnosis": {
                "condition": "nutrient_deficiency_nitrogen",
            }
        }

        validations = validator.validate(expected, actual)
        failed = [v for v in validations if v.result == ValidationResult.FAIL]
        assert len(failed) >= 1
        assert any("condition" in v.field_name for v in failed)

    def test_validate_missing_recommendations(self, validator: GoldenSampleValidator) -> None:
        """Test missing recommendations field fails validation."""
        expected = {
            "diagnosis": {"condition": "healthy"},
            "recommendations": ["Continue current practices"],
        }
        actual = {
            "diagnosis": {"condition": "healthy"},
            # Missing recommendations
        }

        validations = validator.validate(expected, actual)
        failed = [v for v in validations if v.result == ValidationResult.FAIL]
        assert len(failed) >= 1
        assert any("recommendations" in v.field_name for v in failed)
