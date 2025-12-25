"""
Golden Sample Testing Framework

This module provides utilities for golden sample testing of AI agents.
Golden samples are expert-validated input/output pairs used to verify
that AI agents produce accurate and consistent results.

Usage:
    # Run all golden sample tests
    pytest tests/golden/ -m golden

    # Run golden samples for specific agent
    pytest tests/golden/qc_event_extractor/ -m golden

    # Generate new golden samples (record mode)
    python -m tests.golden.framework record qc_event_extractor

Architecture Reference:
    - _bmad-output/test-design-system-level.md
    - _bmad-output/architecture/ai-model-architecture.md
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
# TYPES AND MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentType(str, Enum):
    """Types of AI agents that can be tested with golden samples."""

    EXTRACTOR = "extractor"
    EXPLORER = "explorer"
    GENERATOR = "generator"
    TRIAGE = "triage"


class ValidationResult(str, Enum):
    """Result of golden sample validation."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    VARIANCE = "variance"  # Passed with acceptable variance


@dataclass
class FieldValidation:
    """Validation result for a single field."""

    field_name: str
    expected: Any
    actual: Any
    result: ValidationResult
    variance: float | None = None
    message: str | None = None


@dataclass
class GoldenSampleResult:
    """Result of running a single golden sample test."""

    sample_id: str
    passed: bool
    field_validations: list[FieldValidation] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class GoldenSampleMetadata(BaseModel):
    """Metadata for a golden sample."""

    sample_id: str = Field(description="Unique identifier for the sample")
    agent_name: str = Field(description="Name of the agent being tested")
    agent_type: AgentType = Field(description="Type of agent")
    description: str = Field(default="", description="Human-readable description")
    source: str = Field(default="manual", description="How the sample was created")
    validated_by: str = Field(default="", description="Who validated this sample")
    validated_at: str | None = Field(default=None, description="When validation occurred")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    priority: str = Field(default="P1", description="Test priority (P0-P3)")


class GoldenSampleSchema(BaseModel):
    """Schema for a golden sample stored in JSON."""

    input: dict[str, Any] = Field(description="Input data for the agent")
    expected_output: dict[str, Any] = Field(description="Expected agent output")
    acceptable_variance: dict[str, float] = Field(
        default_factory=dict,
        description="Acceptable variance per field (for numeric fields)",
    )
    metadata: GoldenSampleMetadata = Field(description="Sample metadata")


class GoldenSampleCollection(BaseModel):
    """Collection of golden samples for an agent."""

    agent_name: str
    agent_type: AgentType
    version: str = "1.0.0"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    samples: list[GoldenSampleSchema] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class GoldenSampleValidator:
    """
    Validates actual agent output against expected golden sample output.

    Supports:
    - Exact match validation
    - Variance-based validation for numeric fields
    - Nested object validation
    - Array validation with order sensitivity options
    """

    def __init__(
        self,
        strict_mode: bool = False,
        ignore_extra_fields: bool = True,
    ) -> None:
        """
        Initialize validator.

        Args:
            strict_mode: If True, fail on any extra fields in actual output
            ignore_extra_fields: If True, ignore fields in actual not in expected
        """
        self.strict_mode = strict_mode
        self.ignore_extra_fields = ignore_extra_fields

    def validate(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any],
        acceptable_variance: dict[str, float] | None = None,
        path: str = "",
    ) -> list[FieldValidation]:
        """
        Validate actual output against expected.

        Args:
            expected: Expected output from golden sample
            actual: Actual output from agent
            acceptable_variance: Allowed variance per field
            path: Current path in nested structure (for error messages)

        Returns:
            List of field validations
        """
        results: list[FieldValidation] = []
        variance = acceptable_variance or {}

        # Check for extra fields if in strict mode
        if self.strict_mode and not self.ignore_extra_fields:
            for key in actual:
                if key not in expected:
                    results.append(
                        FieldValidation(
                            field_name=f"{path}.{key}" if path else key,
                            expected=None,
                            actual=actual[key],
                            result=ValidationResult.FAIL,
                            message=f"Unexpected field: {key}",
                        )
                    )

        # Validate expected fields
        for key, expected_value in expected.items():
            field_path = f"{path}.{key}" if path else key

            if key not in actual:
                results.append(
                    FieldValidation(
                        field_name=field_path,
                        expected=expected_value,
                        actual=None,
                        result=ValidationResult.FAIL,
                        message=f"Missing field: {key}",
                    )
                )
                continue

            actual_value = actual[key]

            # Handle nested dictionaries
            if isinstance(expected_value, dict) and isinstance(actual_value, dict):
                nested_variance = {k.replace(f"{key}.", ""): v for k, v in variance.items() if k.startswith(f"{key}.")}
                results.extend(self.validate(expected_value, actual_value, nested_variance, field_path))
                continue

            # Handle lists
            if isinstance(expected_value, list) and isinstance(actual_value, list):
                results.append(self._validate_list(field_path, expected_value, actual_value))
                continue

            # Handle numeric values with variance
            if key in variance and isinstance(expected_value, (int, float)):
                result = self._validate_with_variance(field_path, expected_value, actual_value, variance[key])
                results.append(result)
                continue

            # Exact match
            if expected_value == actual_value:
                results.append(
                    FieldValidation(
                        field_name=field_path,
                        expected=expected_value,
                        actual=actual_value,
                        result=ValidationResult.PASS,
                    )
                )
            else:
                results.append(
                    FieldValidation(
                        field_name=field_path,
                        expected=expected_value,
                        actual=actual_value,
                        result=ValidationResult.FAIL,
                        message="Value mismatch",
                    )
                )

        return results

    def _validate_with_variance(
        self,
        field_path: str,
        expected: float,
        actual: Any,
        allowed_variance: float,
    ) -> FieldValidation:
        """Validate numeric field with allowed variance."""
        if not isinstance(actual, (int, float)):
            return FieldValidation(
                field_name=field_path,
                expected=expected,
                actual=actual,
                result=ValidationResult.FAIL,
                message=f"Expected numeric value, got {type(actual).__name__}",
            )

        diff = abs(expected - actual)
        if diff <= allowed_variance:
            return FieldValidation(
                field_name=field_path,
                expected=expected,
                actual=actual,
                result=ValidationResult.VARIANCE if diff > 0 else ValidationResult.PASS,
                variance=diff,
                message=f"Within variance (diff={diff:.4f}, allowed={allowed_variance})",
            )
        else:
            return FieldValidation(
                field_name=field_path,
                expected=expected,
                actual=actual,
                result=ValidationResult.FAIL,
                variance=diff,
                message=f"Exceeds variance (diff={diff:.4f}, allowed={allowed_variance})",
            )

    def _validate_list(
        self,
        field_path: str,
        expected: list[Any],
        actual: list[Any],
    ) -> FieldValidation:
        """Validate list fields."""
        if len(expected) != len(actual):
            return FieldValidation(
                field_name=field_path,
                expected=expected,
                actual=actual,
                result=ValidationResult.FAIL,
                message=f"Length mismatch: expected {len(expected)}, got {len(actual)}",
            )

        # Check if all expected items exist in actual (order-independent)
        expected_set = {str(e) for e in expected}
        actual_set = {str(a) for a in actual}

        if expected_set == actual_set:
            return FieldValidation(
                field_name=field_path,
                expected=expected,
                actual=actual,
                result=ValidationResult.PASS,
            )
        else:
            missing = expected_set - actual_set
            extra = actual_set - expected_set
            return FieldValidation(
                field_name=field_path,
                expected=expected,
                actual=actual,
                result=ValidationResult.FAIL,
                message=f"List content mismatch. Missing: {missing}, Extra: {extra}",
            )


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN SAMPLE RUNNER
# ═══════════════════════════════════════════════════════════════════════════════


class GoldenSampleRunner:
    """
    Runs golden sample tests for AI agents.

    This runner:
    1. Loads golden samples from JSON files
    2. Executes the agent function with sample inputs
    3. Validates outputs against expected results
    4. Reports results with detailed diagnostics
    """

    def __init__(
        self,
        base_path: Path = Path("tests/golden"),
        validator: GoldenSampleValidator | None = None,
    ) -> None:
        self.base_path = base_path
        self.validator = validator or GoldenSampleValidator()
        self._results: list[GoldenSampleResult] = []

    def load_collection(self, agent_name: str) -> GoldenSampleCollection:
        """Load golden sample collection for an agent."""
        samples_file = self.base_path / agent_name / "samples.json"

        if not samples_file.exists():
            # Return empty collection if no samples exist
            return GoldenSampleCollection(
                agent_name=agent_name,
                agent_type=AgentType.EXTRACTOR,
            )

        data = json.loads(samples_file.read_text())
        return GoldenSampleCollection(**data)

    async def run_sample(
        self,
        sample: GoldenSampleSchema,
        agent_fn: Callable[..., Any],
    ) -> GoldenSampleResult:
        """
        Run a single golden sample test.

        Args:
            sample: The golden sample to test
            agent_fn: Async function that takes input and returns output

        Returns:
            GoldenSampleResult with validation details
        """
        import time

        start_time = time.perf_counter()

        try:
            # Execute agent function
            actual_output = await agent_fn(sample.input)

            # Validate output
            validations = self.validator.validate(
                expected=sample.expected_output,
                actual=actual_output,
                acceptable_variance=sample.acceptable_variance,
            )

            # Determine overall pass/fail
            passed = all(v.result in (ValidationResult.PASS, ValidationResult.VARIANCE) for v in validations)

            execution_time = (time.perf_counter() - start_time) * 1000

            return GoldenSampleResult(
                sample_id=sample.metadata.sample_id,
                passed=passed,
                field_validations=validations,
                execution_time_ms=execution_time,
                metadata=sample.metadata.model_dump(),
            )

        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            return GoldenSampleResult(
                sample_id=sample.metadata.sample_id,
                passed=False,
                execution_time_ms=execution_time,
                error=str(e),
                metadata=sample.metadata.model_dump(),
            )

    async def run_collection(
        self,
        agent_name: str,
        agent_fn: Callable[..., Any],
        filter_tags: list[str] | None = None,
        filter_priority: str | None = None,
    ) -> list[GoldenSampleResult]:
        """
        Run all golden samples for an agent.

        Args:
            agent_name: Name of the agent to test
            agent_fn: Async function that takes input and returns output
            filter_tags: Only run samples with these tags
            filter_priority: Only run samples with this priority

        Returns:
            List of results for all samples
        """
        collection = self.load_collection(agent_name)
        results: list[GoldenSampleResult] = []

        for sample in collection.samples:
            # Apply filters
            if filter_tags and not any(t in sample.metadata.tags for t in filter_tags):
                continue
            if filter_priority and sample.metadata.priority != filter_priority:
                continue

            result = await self.run_sample(sample, agent_fn)
            results.append(result)
            self._results.append(result)

        return results

    def generate_report(self, results: list[GoldenSampleResult]) -> str:
        """Generate a human-readable report of test results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        lines = [
            "=" * 60,
            "GOLDEN SAMPLE TEST REPORT",
            "=" * 60,
            f"Total: {total} | Passed: {passed} | Failed: {failed}",
            f"Pass Rate: {(passed / total * 100):.1f}%" if total > 0 else "No samples",
            "-" * 60,
        ]

        for result in results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"[{status}] {result.sample_id} ({result.execution_time_ms:.1f}ms)")

            if not result.passed:
                if result.error:
                    lines.append(f"  ERROR: {result.error}")
                for validation in result.field_validations:
                    if validation.result == ValidationResult.FAIL:
                        lines.append(f"  - {validation.field_name}: {validation.message}")
                        lines.append(f"    Expected: {validation.expected}")
                        lines.append(f"    Actual:   {validation.actual}")

        lines.append("=" * 60)
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE CREATION UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════


def generate_sample_id(input_data: dict[str, Any]) -> str:
    """Generate a deterministic sample ID from input data."""
    serialized = json.dumps(input_data, sort_keys=True)
    hash_value = hashlib.sha256(serialized.encode()).hexdigest()[:12]
    return f"GS-{hash_value}"


def create_golden_sample(
    agent_name: str,
    agent_type: AgentType,
    input_data: dict[str, Any],
    expected_output: dict[str, Any],
    description: str = "",
    validated_by: str = "",
    tags: list[str] | None = None,
    acceptable_variance: dict[str, float] | None = None,
) -> GoldenSampleSchema:
    """
    Create a new golden sample.

    Args:
        agent_name: Name of the agent
        agent_type: Type of agent (extractor, explorer, generator, triage)
        input_data: Input data for the agent
        expected_output: Expected output from the agent
        description: Human-readable description
        validated_by: Who validated this sample (e.g., "Agronomist John")
        tags: Tags for filtering (e.g., ["disease", "critical"])
        acceptable_variance: Allowed variance for numeric fields

    Returns:
        GoldenSampleSchema ready to be saved
    """
    sample_id = generate_sample_id(input_data)

    return GoldenSampleSchema(
        input=input_data,
        expected_output=expected_output,
        acceptable_variance=acceptable_variance or {},
        metadata=GoldenSampleMetadata(
            sample_id=sample_id,
            agent_name=agent_name,
            agent_type=agent_type,
            description=description,
            source="manual",
            validated_by=validated_by,
            validated_at=datetime.now(UTC).isoformat(),
            tags=tags or [],
            priority="P1",
        ),
    )


def save_golden_sample(
    sample: GoldenSampleSchema,
    base_path: Path = Path("tests/golden"),
) -> Path:
    """
    Save a golden sample to disk.

    Args:
        sample: The golden sample to save
        base_path: Base path for golden samples

    Returns:
        Path to the samples.json file
    """
    agent_dir = base_path / sample.metadata.agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    samples_file = agent_dir / "samples.json"

    # Load existing collection or create new
    if samples_file.exists():
        data = json.loads(samples_file.read_text())
        collection = GoldenSampleCollection(**data)
    else:
        collection = GoldenSampleCollection(
            agent_name=sample.metadata.agent_name,
            agent_type=sample.metadata.agent_type,
        )

    # Check for duplicate sample ID
    existing_ids = {s.metadata.sample_id for s in collection.samples}
    if sample.metadata.sample_id in existing_ids:
        # Update existing sample
        collection.samples = [
            s if s.metadata.sample_id != sample.metadata.sample_id else sample for s in collection.samples
        ]
    else:
        # Add new sample
        collection.samples.append(sample)

    # Save to disk
    samples_file.write_text(json.dumps(collection.model_dump(), indent=2, default=str))

    return samples_file


# ═══════════════════════════════════════════════════════════════════════════════
# PYTEST INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════


def pytest_golden_samples(agent_name: str):
    """
    Pytest parametrize decorator for golden sample tests.

    Usage:
        @pytest_golden_samples("qc_event_extractor")
        async def test_extraction(sample, mock_llm_client):
            result = await extract_qc_event(sample.input)
            passed, errors = sample.validate_output(result)
            assert passed, f"Golden sample failed: {errors}"
    """
    import pytest

    runner = GoldenSampleRunner()
    collection = runner.load_collection(agent_name)

    samples = [(s.metadata.sample_id, s) for s in collection.samples]

    return pytest.mark.parametrize(
        "sample_id,sample",
        samples,
        ids=[s[0] for s in samples],
    )
