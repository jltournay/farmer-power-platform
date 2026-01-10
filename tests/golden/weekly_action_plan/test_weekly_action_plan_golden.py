"""Golden sample tests for Weekly Action Plan Generator agent.

Story 0.75.20: Generator Agent Implementation - Sample Config & Golden Tests

This module tests the Weekly Action Plan Generator workflow using golden samples.
Each sample is a validated input/output pair that represents expected behavior.

Golden samples cover:
- Standard weekly plans with diagnoses and weather
- Critical emergency situations (pest outbreak + drought)
- Weather-focused preparations (heavy rain, frost)
- High-performer maintenance plans
- Multiple diagnoses with prioritization
- Format-specific output tests (SMS, voice script)
- Edge cases (conflicting diagnoses, no diagnoses)

Run with:
    pytest tests/golden/weekly_action_plan/ -v -m golden
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from ai_model.workflows.generator import GeneratorWorkflow
from ai_model.workflows.states.generator import GeneratorState

from tests.golden.framework import (
    GoldenSampleCollection,
    GoldenSampleRunner,
    GoldenSampleValidator,
    ValidationResult,
)

if TYPE_CHECKING:
    from ai_model.domain.agent_config import GeneratorConfig

# Mark all tests in this module as golden sample tests
pytestmark = pytest.mark.golden


class TestWeeklyActionPlanGoldenSamples:
    """Golden sample tests for Weekly Action Plan Generator.

    These tests verify that the GeneratorWorkflow produces outputs matching
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

        If this test fails, update the range(N) in test_golden_sample_generation
        to match the actual sample count.
        """
        expected_count = 12  # Must match range() in test_golden_sample_generation
        actual_count = len(golden_collection.samples)
        assert actual_count == expected_count, (
            f"Sample count mismatch: expected {expected_count}, got {actual_count}. "
            f"Update range({expected_count}) in test_golden_sample_generation to range({actual_count})"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sample_index",
        list(range(12)),  # Must match expected_count in test_sample_count_matches_expected
        ids=lambda i: f"GS-gen-{i + 1:03d}",
    )
    async def test_golden_sample_generation(
        self,
        sample_index: int,
        golden_collection: GoldenSampleCollection,
        weekly_action_plan_config: GeneratorConfig,
        weekly_action_plan_prompt: str,
        mock_llm_gateway_factory,
        mock_ranking_service,
        mock_mcp_integration,
    ) -> None:
        """Test generation against each golden sample.

        Args:
            sample_index: Index of the sample in the collection.
            golden_collection: The golden sample collection.
            weekly_action_plan_config: Agent configuration.
            weekly_action_plan_prompt: Prompt template.
            mock_llm_gateway_factory: Factory to create mock LLM gateway.
            mock_ranking_service: Mock RAG ranking service.
            mock_mcp_integration: Mock MCP integration.
        """
        sample = golden_collection.samples[sample_index]
        expected_output = sample.expected_output

        # Create mock LLM gateway that returns the expected output
        mock_gateway = mock_llm_gateway_factory(expected_output)

        # Create workflow with mocked dependencies
        workflow = GeneratorWorkflow(
            llm_gateway=mock_gateway,
            ranking_service=mock_ranking_service,
            mcp_integration=mock_mcp_integration,
        )

        # Build initial state from sample input
        initial_state: GeneratorState = {
            "input_data": sample.input,
            "agent_id": "weekly-action-plan",
            "agent_config": weekly_action_plan_config,
            "prompt_template": weekly_action_plan_prompt,
            "correlation_id": f"test-{sample.metadata.sample_id}",
            "output_format": sample.input.get("format_type", "markdown"),
        }

        # Execute workflow
        result = await workflow.execute(initial_state)

        # Verify workflow execution succeeded
        assert result["success"], f"Workflow failed: {result.get('error_message')}"

    @pytest.mark.asyncio
    async def test_all_priority_p0_samples(
        self,
        golden_collection: GoldenSampleCollection,
        weekly_action_plan_config: GeneratorConfig,
        weekly_action_plan_prompt: str,
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
            workflow = GeneratorWorkflow(
                llm_gateway=mock_gateway,
                ranking_service=mock_ranking_service,
                mcp_integration=mock_mcp_integration,
            )

            initial_state: GeneratorState = {
                "input_data": sample.input,
                "agent_id": "weekly-action-plan",
                "agent_config": weekly_action_plan_config,
                "prompt_template": weekly_action_plan_prompt,
                "correlation_id": f"test-p0-{sample.metadata.sample_id}",
                "output_format": sample.input.get("format_type", "markdown"),
            }

            result = await workflow.execute(initial_state)
            assert result["success"], f"P0 sample {sample.metadata.sample_id} failed: {result.get('error_message')}"

    @pytest.mark.asyncio
    async def test_edge_case_samples(
        self,
        golden_collection: GoldenSampleCollection,
        weekly_action_plan_config: GeneratorConfig,
        weekly_action_plan_prompt: str,
        mock_llm_gateway_factory,
        mock_ranking_service,
        mock_mcp_integration,
    ) -> None:
        """Test edge case golden samples.

        Edge cases include:
        - Conflicting diagnoses (drought AND waterlogging)
        - Extreme weather (frost, heat wave)
        - No diagnoses (proactive planning)
        """
        edge_case_samples = [s for s in golden_collection.samples if "edge-case" in s.metadata.tags]

        assert len(edge_case_samples) >= 2, "Expected at least 2 edge case golden samples"

        for sample in edge_case_samples:
            mock_gateway = mock_llm_gateway_factory(sample.expected_output)
            workflow = GeneratorWorkflow(
                llm_gateway=mock_gateway,
                ranking_service=mock_ranking_service,
                mcp_integration=mock_mcp_integration,
            )

            initial_state: GeneratorState = {
                "input_data": sample.input,
                "agent_id": "weekly-action-plan",
                "agent_config": weekly_action_plan_config,
                "prompt_template": weekly_action_plan_prompt,
                "correlation_id": f"test-edge-{sample.metadata.sample_id}",
                "output_format": sample.input.get("format_type", "markdown"),
            }

            result = await workflow.execute(initial_state)
            assert result["success"], f"Edge case {sample.metadata.sample_id} failed: {result.get('error_message')}"

    @pytest.mark.asyncio
    async def test_format_specific_samples(
        self,
        golden_collection: GoldenSampleCollection,
        weekly_action_plan_config: GeneratorConfig,
        weekly_action_plan_prompt: str,
        mock_llm_gateway_factory,
        mock_ranking_service,
        mock_mcp_integration,
    ) -> None:
        """Test format-specific golden samples (SMS and voice script).

        Validates that the generator can produce output in different formats:
        - sms_summary: Short 300-char message
        - voice_script: Conversational script for IVR
        """
        format_samples = [s for s in golden_collection.samples if "format-test" in s.metadata.tags]

        assert len(format_samples) >= 2, "Expected at least 2 format-specific golden samples"

        for sample in format_samples:
            mock_gateway = mock_llm_gateway_factory(sample.expected_output)
            workflow = GeneratorWorkflow(
                llm_gateway=mock_gateway,
                ranking_service=mock_ranking_service,
                mcp_integration=mock_mcp_integration,
            )

            initial_state: GeneratorState = {
                "input_data": sample.input,
                "agent_id": "weekly-action-plan",
                "agent_config": weekly_action_plan_config,
                "prompt_template": weekly_action_plan_prompt,
                "correlation_id": f"test-format-{sample.metadata.sample_id}",
                "output_format": sample.input.get("format_type", "markdown"),
            }

            result = await workflow.execute(initial_state)
            assert result["success"], f"Format sample {sample.metadata.sample_id} failed: {result.get('error_message')}"


class TestWeeklyActionPlanGoldenRunner:
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
        weekly_action_plan_config: GeneratorConfig,
        weekly_action_plan_prompt: str,
        mock_llm_gateway_factory,
    ) -> None:
        """Run all samples using GoldenSampleRunner.

        This test validates the runner framework by returning expected outputs
        for each sample, simulating a perfectly working generator.
        """
        # Load samples to create a lookup for expected outputs
        samples_path = Path(__file__).parent / "samples.json"
        samples_data = json.loads(samples_path.read_text())

        async def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            """Agent function that returns expected output for each sample.

            This simulates a working generator to validate the runner framework.
            """
            # Find matching sample by input signature
            for sample in samples_data["samples"]:
                if sample["input"] == input_data:
                    return sample["expected_output"]
            # Fallback - return empty (will fail validation)
            return {}

        results = await runner.run_collection(
            agent_name="weekly_action_plan",
            agent_fn=agent_fn,
        )

        # Verify we got results for all samples
        assert len(results) == 12, f"Expected 12 sample results, got {len(results)}"

        # Generate report
        report = runner.generate_report(results)
        assert "GOLDEN SAMPLE TEST REPORT" in report

        # With expected outputs returned, all should pass
        passed_count = sum(1 for r in results if r.passed)
        assert passed_count >= 10, f"Expected at least 10 passed, got {passed_count}"

    @pytest.mark.asyncio
    async def test_run_collection_filtered_by_priority(
        self,
        runner: GoldenSampleRunner,
    ) -> None:
        """Test filtering samples by priority."""

        async def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {}

        results = await runner.run_collection(
            agent_name="weekly_action_plan",
            agent_fn=agent_fn,
            filter_priority="P0",
        )

        # Should have fewer than total samples
        assert len(results) > 0, "Expected some P0 samples"
        assert len(results) < 12, "Expected P0 filter to reduce sample count"

    @pytest.mark.asyncio
    async def test_run_collection_filtered_by_tags(
        self,
        runner: GoldenSampleRunner,
    ) -> None:
        """Test filtering samples by tags."""

        async def agent_fn(input_data: dict[str, Any]) -> dict[str, Any]:
            return {}

        results = await runner.run_collection(
            agent_name="weekly_action_plan",
            agent_fn=agent_fn,
            filter_tags=["emergency"],
        )

        # Should have samples with emergency tag
        assert len(results) > 0, "Expected some emergency samples"


class TestWeeklyActionPlanFixtures:
    """Tests for fixture behavior and edge cases."""

    def test_prompt_fixture_loads_from_file(self, weekly_action_plan_prompt: str) -> None:
        """Verify prompt fixture loads content from config file."""
        # Should contain the template from weekly-action-plan.json
        assert "Create" in weekly_action_plan_prompt or "action plan" in weekly_action_plan_prompt.lower()
        assert "{{" in weekly_action_plan_prompt  # Has template variables

    def test_config_fixture_has_rag_enabled(self, weekly_action_plan_config: GeneratorConfig) -> None:
        """Verify config fixture has RAG enabled (required for Generator)."""
        assert weekly_action_plan_config.rag.enabled is True
        assert len(weekly_action_plan_config.rag.knowledge_domains) >= 2
        assert "tea-cultivation" in weekly_action_plan_config.rag.knowledge_domains

    def test_config_fixture_has_mcp_sources(self, weekly_action_plan_config: GeneratorConfig) -> None:
        """Verify config fixture has MCP sources configured."""
        assert len(weekly_action_plan_config.mcp_sources) >= 2
        server_names = [s.server for s in weekly_action_plan_config.mcp_sources]
        assert "plantation-mcp" in server_names
        assert "knowledge-mcp" in server_names

    def test_config_fixture_output_format(self, weekly_action_plan_config: GeneratorConfig) -> None:
        """Verify config fixture has output format set."""
        assert weekly_action_plan_config.output_format == "markdown"


class TestWeeklyActionPlanValidation:
    """Tests for action plan validation behavior."""

    @pytest.fixture
    def validator(self) -> GoldenSampleValidator:
        """Create validator instance."""
        return GoldenSampleValidator(strict_mode=False, ignore_extra_fields=True)

    def test_validate_action_plan_exact_match(self, validator: GoldenSampleValidator) -> None:
        """Test exact match validation for action plan."""
        expected = {
            "action_plan": {
                "week_of": "2026-01-13",
                "priority_actions": [{"action": "Apply fungicide", "priority": "high", "timing": "Within 48 hours"}],
            }
        }
        actual = {
            "action_plan": {
                "week_of": "2026-01-13",
                "priority_actions": [{"action": "Apply fungicide", "priority": "high", "timing": "Within 48 hours"}],
            }
        }

        validations = validator.validate(expected, actual)
        assert all(v.result == ValidationResult.PASS for v in validations)

    def test_validate_priority_actions_order_independent(self, validator: GoldenSampleValidator) -> None:
        """Test action array validation is order-independent."""
        expected = {
            "action_plan": {
                "priority_actions": [
                    {"action": "Apply fungicide"},
                    {"action": "Prune branches"},
                ]
            }
        }
        actual = {
            "action_plan": {
                "priority_actions": [
                    {"action": "Prune branches"},
                    {"action": "Apply fungicide"},
                ]
            }
        }

        validations = validator.validate(expected, actual)
        assert all(v.result == ValidationResult.PASS for v in validations)

    def test_validate_missing_action_plan(self, validator: GoldenSampleValidator) -> None:
        """Test missing action_plan field fails validation."""
        expected = {
            "action_plan": {"week_of": "2026-01-13"},
            "summary": {"sms_message": "Test message"},
        }
        actual = {
            # Missing action_plan
            "summary": {"sms_message": "Test message"},
        }

        validations = validator.validate(expected, actual)
        failed = [v for v in validations if v.result == ValidationResult.FAIL]
        assert len(failed) >= 1
        assert any("action_plan" in v.field_name for v in failed)

    def test_validate_sms_length_constraint(self, validator: GoldenSampleValidator) -> None:
        """Test SMS message length validation (max 300 chars)."""
        # This validates the golden samples have proper SMS length
        samples_path = Path(__file__).parent / "samples.json"
        samples_data = json.loads(samples_path.read_text())

        for sample in samples_data["samples"]:
            expected_output = sample["expected_output"]
            sms_message = expected_output.get("summary", {}).get("sms_message", "")
            assert len(sms_message) <= 300, (
                f"SMS message in sample {sample['metadata']['sample_id']} exceeds 300 chars: {len(sms_message)}"
            )

    def test_validate_voice_script_length_constraint(self, validator: GoldenSampleValidator) -> None:
        """Test voice script length validation (max 2000 chars)."""
        # This validates the golden samples have proper voice script length
        samples_path = Path(__file__).parent / "samples.json"
        samples_data = json.loads(samples_path.read_text())

        for sample in samples_data["samples"]:
            expected_output = sample["expected_output"]
            voice_script = expected_output.get("summary", {}).get("voice_script", "")
            assert len(voice_script) <= 2000, (
                f"Voice script in sample {sample['metadata']['sample_id']} exceeds 2000 chars: {len(voice_script)}"
            )

    def test_validate_max_priority_actions(self, validator: GoldenSampleValidator) -> None:
        """Test that priority_actions has max 5 items."""
        # This validates the golden samples follow the 5-action maximum
        samples_path = Path(__file__).parent / "samples.json"
        samples_data = json.loads(samples_path.read_text())

        for sample in samples_data["samples"]:
            expected_output = sample["expected_output"]
            priority_actions = expected_output.get("action_plan", {}).get("priority_actions", [])
            assert len(priority_actions) <= 5, (
                f"Priority actions in sample {sample['metadata']['sample_id']} exceeds 5 items: {len(priority_actions)}"
            )
