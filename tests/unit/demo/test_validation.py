"""Unit tests for Pydantic validation module.

Tests for:
- AC #1: Seed JSON files validated through Pydantic models with detailed errors
- AC #2: Unknown fields rejected (not silently ignored)
- AC #3: Missing required fields produce clear error with context
- AC #5: Models imported directly from service packages (no duplication)
- AC #6: Path-agnostic design - works with any source directory
"""

import json
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

from scripts.demo.validation import (
    ValidationError,
    ValidationResult,
    validate_json_file,
    validate_with_pydantic,
)


# Test model with extra="forbid" to reject unknown fields
class TestModel(BaseModel):
    """Test model for validation tests."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique ID")
    name: str = Field(min_length=1, max_length=100, description="Name")
    count: int = Field(ge=0, description="Count")
    is_active: bool = Field(default=True, description="Active flag")


T = TypeVar("T", bound=BaseModel)


class TestValidateWithPydantic:
    """Tests for validate_with_pydantic function."""

    def test_valid_records_pass_validation(self) -> None:
        """AC #1: Valid JSON passes Pydantic validation."""
        records = [
            {"id": "test-001", "name": "Test One", "count": 5, "is_active": True},
            {"id": "test-002", "name": "Test Two", "count": 10},  # default is_active
        ]

        validated, errors = validate_with_pydantic(
            records=records,
            model=TestModel,
            filename="test_data.json",
        )

        assert len(validated) == 2
        assert len(errors) == 0
        assert isinstance(validated[0], TestModel)
        assert validated[0].id == "test-001"
        assert validated[1].is_active is True  # default value

    def test_invalid_type_rejected_with_error(self) -> None:
        """AC #3: Invalid field type is rejected with clear error."""
        records = [
            {"id": "test-001", "name": "Test", "count": "not_a_number"},
        ]

        validated, errors = validate_with_pydantic(
            records=records,
            model=TestModel,
            filename="test_data.json",
        )

        assert len(validated) == 0
        assert len(errors) == 1
        error = errors[0]
        assert error.filename == "test_data.json"
        assert error.record_index == 0
        assert "count" in error.field_path
        assert "int" in error.message.lower() or "number" in error.message.lower()

    def test_missing_required_field_produces_error_with_context(self) -> None:
        """AC #3: Missing required field produces error with record index and filename."""
        records = [
            {"id": "test-001", "count": 5},  # missing required 'name'
        ]

        validated, errors = validate_with_pydantic(
            records=records,
            model=TestModel,
            filename="missing_fields.json",
        )

        assert len(validated) == 0
        assert len(errors) == 1
        error = errors[0]
        assert error.filename == "missing_fields.json"
        assert error.record_index == 0
        assert "name" in error.field_path
        assert "required" in error.message.lower() or "missing" in error.message.lower()

    def test_extra_field_rejected_not_ignored(self) -> None:
        """AC #2: Unknown/extra field is rejected (not silently ignored)."""
        records = [
            {
                "id": "test-001",
                "name": "Test",
                "count": 5,
                "unknown_field": "should fail",
            },
        ]

        validated, errors = validate_with_pydantic(
            records=records,
            model=TestModel,
            filename="extra_fields.json",
        )

        assert len(validated) == 0
        assert len(errors) == 1
        error = errors[0]
        assert error.filename == "extra_fields.json"
        assert error.record_index == 0
        assert "unknown_field" in error.field_path or "unknown_field" in error.message
        # Pydantic error for extra fields
        assert "extra" in error.message.lower() or "not permitted" in error.message.lower()

    def test_collects_all_errors_not_stop_at_first(self) -> None:
        """AC #1: Validation collects ALL errors (doesn't stop at first)."""
        records = [
            {"id": "test-001", "name": "Test", "count": "invalid"},  # error 1
            {"id": "test-002", "count": 5},  # error 2: missing name
            {"id": "test-003", "name": "Valid", "count": 10},  # valid
            {"name": "NoId", "count": 5},  # error 3: missing id
        ]

        validated, errors = validate_with_pydantic(
            records=records,
            model=TestModel,
            filename="multiple_errors.json",
        )

        # 1 valid record
        assert len(validated) == 1
        assert validated[0].id == "test-003"

        # 3 errors from 3 different records
        assert len(errors) == 3
        error_indices = {e.record_index for e in errors}
        assert error_indices == {0, 1, 3}

    def test_error_includes_record_index(self) -> None:
        """AC #1: Validation errors include record index."""
        records = [
            {"id": "test-001", "name": "Valid", "count": 5},
            {"id": "test-002", "name": "Valid", "count": 10},
            {"id": "test-003", "name": "", "count": 15},  # error: min_length=1
        ]

        validated, errors = validate_with_pydantic(
            records=records,
            model=TestModel,
            filename="test.json",
        )

        assert len(errors) == 1
        assert errors[0].record_index == 2


class TestValidateJsonFile:
    """Tests for validate_json_file function."""

    def test_loads_and_validates_json_file(self) -> None:
        """AC #1: JSON file is loaded and validated through Pydantic model."""
        records = [
            {"id": "file-001", "name": "From File", "count": 42},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            f.flush()
            file_path = Path(f.name)

        try:
            result = validate_json_file(
                file_path=file_path,
                model=TestModel,
            )

            assert isinstance(result, ValidationResult)
            assert len(result.validated) == 1
            assert result.validated[0].name == "From File"
            assert len(result.errors) == 0
        finally:
            file_path.unlink()

    def test_path_agnostic_design(self) -> None:
        """AC #6: Validation works regardless of path (path-agnostic)."""
        records = [{"id": "test", "name": "Test", "count": 1}]

        # Test with different directory structures
        for subdir in ["seed", "demo/generated", "custom/nested/path"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                nested_path = Path(tmpdir) / subdir
                nested_path.mkdir(parents=True)
                file_path = nested_path / "data.json"
                file_path.write_text(json.dumps(records))

                result = validate_json_file(file_path=file_path, model=TestModel)
                assert len(result.validated) == 1
                assert len(result.errors) == 0


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_error_contains_all_context(self) -> None:
        """AC #1: Error includes filename, record index, field name, error message."""
        error = ValidationError(
            filename="test.json",
            record_index=5,
            field_path="name",
            message="Field required",
        )

        assert error.filename == "test.json"
        assert error.record_index == 5
        assert error.field_path == "name"
        assert error.message == "Field required"

    def test_error_str_representation(self) -> None:
        """Error has useful string representation."""
        error = ValidationError(
            filename="farmers.json",
            record_index=10,
            field_path="region_id",
            message="Field required",
        )

        error_str = str(error)
        assert "farmers.json" in error_str
        assert "10" in error_str
        assert "region_id" in error_str
        assert "Field required" in error_str
