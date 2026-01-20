"""Pydantic validation module for seed data files.

This module provides validation functions that:
- Load JSON files and validate through Pydantic models
- Reject unknown fields (extra="forbid" enforcement)
- Produce clear error messages with context (filename, record index, field path)
- Support path-agnostic design (any source directory)

Story 0.8.1: Pydantic Validation Infrastructure
AC #1: Seed JSON files validated through Pydantic models with detailed errors
AC #2: Unknown fields rejected (not silently ignored)
AC #3: Missing required fields produce clear error with record index and filename
AC #6: Path-agnostic design - accepts any source directory path
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

if TYPE_CHECKING:
    from pathlib import Path

T = TypeVar("T", bound=BaseModel)


@dataclass
class ValidationError:
    """Detailed validation error with context.

    Attributes:
        filename: Name of the file containing the error.
        record_index: 0-based index of the record in the array.
        field_path: Dot-separated path to the field (e.g., "contact.phone").
        message: Human-readable error message.
    """

    filename: str
    record_index: int
    field_path: str
    message: str

    def __str__(self) -> str:
        """Return formatted error string with all context."""
        return f"{self.filename}[{self.record_index}].{self.field_path}: {self.message}"


@dataclass
class ValidationResult(Generic[T]):
    """Result of validating a JSON file.

    Attributes:
        validated: List of successfully validated Pydantic model instances.
        errors: List of validation errors for records that failed.
        filename: Name of the source file.
    """

    validated: list[T]
    errors: list[ValidationError]
    filename: str

    @property
    def is_valid(self) -> bool:
        """Return True if no validation errors."""
        return len(self.errors) == 0


def validate_with_pydantic(  # noqa: UP047
    records: list[dict[str, Any]],
    model: type[T],
    filename: str,
) -> tuple[list[T], list[ValidationError]]:
    """Validate a list of records through a Pydantic model.

    This function validates each record independently, collecting all errors
    rather than stopping at the first failure. This enables users to fix
    all issues in one pass.

    The model MUST use `extra="forbid"` via ConfigDict to reject unknown fields
    (AC #2). If the model doesn't have this setting, unknown fields will be
    silently ignored by Pydantic.

    Args:
        records: List of dictionaries to validate.
        model: Pydantic model class to validate against. Should have
            ConfigDict(extra="forbid") to reject unknown fields.
        filename: Source filename for error reporting context.

    Returns:
        Tuple of (validated_records, validation_errors).
        validated_records: List of successfully validated model instances.
        validation_errors: List of ValidationError for failed records.
    """
    validated: list[T] = []
    errors: list[ValidationError] = []

    for index, record in enumerate(records):
        try:
            instance = model.model_validate(record)
            validated.append(instance)
        except PydanticValidationError as e:
            # Extract all errors from Pydantic's error list
            for error in e.errors():
                field_path = _format_field_path(error.get("loc", ()))
                message = _format_error_message(error)

                errors.append(
                    ValidationError(
                        filename=filename,
                        record_index=index,
                        field_path=field_path,
                        message=message,
                    )
                )

    return validated, errors


def validate_json_file(  # noqa: UP047
    file_path: Path,
    model: type[T],
) -> ValidationResult[T]:
    """Load and validate a JSON file through a Pydantic model.

    Path-agnostic design (AC #6) - works with any file path.

    Args:
        file_path: Path to the JSON file to validate.
        model: Pydantic model class to validate against.

    Returns:
        ValidationResult containing validated records and any errors.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    with file_path.open(encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        # Single object should be wrapped in list
        records = [records]

    filename = file_path.name
    validated, errors = validate_with_pydantic(records, model, filename)

    return ValidationResult(
        validated=validated,
        errors=errors,
        filename=filename,
    )


def _format_field_path(loc: tuple[str | int, ...]) -> str:
    """Format Pydantic location tuple as dot-separated path.

    Examples:
        ("name",) -> "name"
        ("contact", "phone") -> "contact.phone"
        ("items", 0, "name") -> "items[0].name"
    """
    if not loc:
        return "root"

    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        else:
            if parts and not parts[-1].endswith("]"):
                parts.append(".")
            parts.append(str(item))

    return "".join(parts)


def _format_error_message(error: dict[str, Any]) -> str:
    """Format Pydantic error dict into human-readable message.

    Args:
        error: Pydantic error dict with 'type' and 'msg' keys.

    Returns:
        Human-readable error message.
    """
    error_type = error.get("type", "unknown")
    message = error.get("msg", "Validation failed")

    # Enhance common error messages with more context
    if error_type == "missing":
        return "Field required"
    elif error_type == "extra_forbidden":
        return f"Extra field not permitted: {message}"
    elif "int_parsing" in error_type:
        return "Value must be an integer"

    return message
