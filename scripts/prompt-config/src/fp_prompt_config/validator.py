"""Prompt YAML validation.

This module validates prompt YAML files against the Prompt Pydantic model schema.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from fp_prompt_config.models import Prompt, PromptStatus

# Semantic versioning pattern (e.g., 1.0.0, 2.1.0, 10.20.30)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass
class ValidationResult:
    """Result of validating a prompt YAML file."""

    file_path: Path
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    prompt: Prompt | None = None


def validate_prompt_yaml(file_path: Path) -> ValidationResult:
    """Validate a prompt YAML file against the schema.

    Performs the following validations:
    1. File exists and is readable
    2. Valid YAML syntax
    3. Required fields present (prompt_id, agent_id, version, content)
    4. Content has required fields (system_prompt, template)
    5. Version format is valid semver (X.Y.Z)
    6. Status is a valid PromptStatus value
    7. Full Pydantic model validation

    Args:
        file_path: Path to the YAML file to validate.

    Returns:
        ValidationResult with is_valid=True if valid, errors list if not.
    """
    result = ValidationResult(file_path=file_path, is_valid=False)

    # Check file exists
    if not file_path.exists():
        result.errors.append(f"File not found: {file_path}")
        return result

    # Read and parse YAML
    try:
        yaml_content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        result.errors.append(f"Cannot read file: {e}")
        return result

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        result.errors.append(f"Invalid YAML syntax: {e}")
        return result

    if not isinstance(data, dict):
        result.errors.append("YAML file must contain a mapping (dictionary)")
        return result

    # Validate required top-level fields
    required_fields = ["prompt_id", "agent_id", "version", "content"]
    for field_name in required_fields:
        if field_name not in data:
            result.errors.append(f"Missing required field: {field_name}")

    if result.errors:
        return result

    # Validate version format (semver)
    version = data.get("version", "")
    if not isinstance(version, str):
        version = str(version)
    if not SEMVER_PATTERN.match(version):
        result.errors.append(
            f"Invalid version format: '{version}' (expected X.Y.Z semver format)"
        )

    # Validate content has required fields
    content = data.get("content", {})
    if not isinstance(content, dict):
        result.errors.append("content must be a mapping (dictionary)")
    else:
        content_required = ["system_prompt", "template"]
        for field_name in content_required:
            if field_name not in content:
                result.errors.append(f"Missing required field: content.{field_name}")

    # Validate status if present
    if "status" in data:
        status_value = data["status"]
        valid_statuses = [s.value for s in PromptStatus]
        if status_value not in valid_statuses:
            valid_list = ", ".join(valid_statuses)
            msg = f"Invalid status: '{status_value}' (expected one of: {valid_list})"
            result.errors.append(msg)

    if result.errors:
        return result

    # Build the Prompt model
    try:
        # Generate id from prompt_id and version
        prompt_id = data["prompt_id"]
        version_str = str(data["version"])
        data["id"] = f"{prompt_id}:{version_str}"

        # Ensure version is string
        data["version"] = version_str

        # Set default status if not provided
        if "status" not in data:
            data["status"] = PromptStatus.DRAFT.value

        # Set default metadata if not provided
        if "metadata" not in data:
            data["metadata"] = {"author": "unknown"}

        # Set default ab_test if not provided
        if "ab_test" not in data:
            data["ab_test"] = {}

        # Validate with Pydantic
        prompt = Prompt.model_validate(data)
        result.prompt = prompt
        result.is_valid = True

    except ValidationError as e:
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            result.errors.append(f"{loc}: {msg}")

    return result


def validate_prompt_dict(data: dict[str, Any]) -> ValidationResult:
    """Validate a prompt dictionary against the schema.

    Same as validate_prompt_yaml but for in-memory dict data.

    Args:
        data: Dictionary with prompt data.

    Returns:
        ValidationResult with is_valid=True if valid, errors list if not.
    """
    result = ValidationResult(file_path=Path("<dict>"), is_valid=False)

    if not isinstance(data, dict):
        result.errors.append("Data must be a dictionary")
        return result

    # Validate required top-level fields
    required_fields = ["prompt_id", "agent_id", "version", "content"]
    for field_name in required_fields:
        if field_name not in data:
            result.errors.append(f"Missing required field: {field_name}")

    if result.errors:
        return result

    # Validate version format (semver)
    version = data.get("version", "")
    if not isinstance(version, str):
        version = str(version)
    if not SEMVER_PATTERN.match(version):
        result.errors.append(
            f"Invalid version format: '{version}' (expected X.Y.Z semver format)"
        )

    # Validate content has required fields
    content = data.get("content", {})
    if not isinstance(content, dict):
        result.errors.append("content must be a mapping (dictionary)")
    else:
        content_required = ["system_prompt", "template"]
        for field_name in content_required:
            if field_name not in content:
                result.errors.append(f"Missing required field: content.{field_name}")

    if result.errors:
        return result

    # Build the Prompt model
    try:
        # Generate id from prompt_id and version
        prompt_id = data["prompt_id"]
        version_str = str(data["version"])
        data_copy = dict(data)
        data_copy["id"] = f"{prompt_id}:{version_str}"
        data_copy["version"] = version_str

        # Set default status if not provided
        if "status" not in data_copy:
            data_copy["status"] = PromptStatus.DRAFT.value

        # Set default metadata if not provided
        if "metadata" not in data_copy:
            data_copy["metadata"] = {"author": "unknown"}

        # Set default ab_test if not provided
        if "ab_test" not in data_copy:
            data_copy["ab_test"] = {}

        # Validate with Pydantic
        prompt = Prompt.model_validate(data_copy)
        result.prompt = prompt
        result.is_valid = True

    except ValidationError as e:
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            result.errors.append(f"{loc}: {msg}")

    return result
