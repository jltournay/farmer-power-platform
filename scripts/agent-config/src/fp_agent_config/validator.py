"""Agent configuration YAML validation.

This module validates agent config YAML files against the AgentConfig Pydantic
discriminated union schema. It validates:
1. YAML syntax
2. Required fields per agent type
3. Version format (semver)
4. Type-specific field requirements
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from fp_agent_config.models import (
    AgentConfig,
    AgentConfigStatus,
    AgentType,
    agent_config_adapter,
)

# Semantic versioning pattern (e.g., 1.0.0, 2.1.0, 10.20.30)
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

# Required fields per agent type (beyond base fields)
TYPE_SPECIFIC_FIELDS: dict[str, list[str]] = {
    "extractor": ["extraction_schema"],
    "explorer": ["rag"],
    "generator": ["rag", "output_format"],
    "conversational": ["rag", "state", "intent_model", "response_model"],
    "tiered-vision": ["tiered_llm", "routing", "rag"],
}

# Base required fields for all agent types
BASE_REQUIRED_FIELDS = [
    "agent_id",
    "type",
    "version",
    "description",
    "input",
    "output",
    "metadata",
]


@dataclass
class ValidationResult:
    """Result of validating an agent config YAML file."""

    file_path: Path
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    config: AgentConfig | None = None


def _validate_config_data(data: dict[str, Any], result: ValidationResult) -> None:
    """Shared validation logic for agent config data.

    Validates the data dictionary and populates the result with errors or config.
    This is the core validation logic used by both YAML file and dict validation.

    Args:
        data: Dictionary with agent config data.
        result: ValidationResult to populate with errors or config.
    """
    # Validate required base fields
    for field_name in BASE_REQUIRED_FIELDS:
        if field_name not in data:
            # llm is special - not required for tiered-vision
            if field_name == "llm" and data.get("type") == "tiered-vision":
                continue
            result.errors.append(f"Missing required field: {field_name}")

    if result.errors:
        return

    # Validate version format (semver)
    version = data.get("version", "")
    if not isinstance(version, str):
        version = str(version)
    if not SEMVER_PATTERN.match(version):
        result.errors.append(
            f"Invalid version format: '{version}' (expected X.Y.Z semver format)"
        )

    # Validate type is a valid AgentType
    agent_type = data.get("type", "")
    valid_types = [t.value for t in AgentType]
    if agent_type not in valid_types:
        valid_list = ", ".join(valid_types)
        result.errors.append(
            f"Invalid type: '{agent_type}' (expected one of: {valid_list})"
        )
        return

    # Validate status if present
    if "status" in data:
        status_value = data["status"]
        valid_statuses = [s.value for s in AgentConfigStatus]
        if status_value not in valid_statuses:
            valid_list = ", ".join(valid_statuses)
            result.errors.append(
                f"Invalid status: '{status_value}' (expected one of: {valid_list})"
            )

    # Validate type-specific required fields
    type_fields = TYPE_SPECIFIC_FIELDS.get(agent_type, [])
    for field_name in type_fields:
        if field_name not in data:
            # llm is not required for tiered-vision
            if field_name == "llm":
                continue
            result.errors.append(
                f"Missing required field for {agent_type}: {field_name}"
            )

    if result.errors:
        return

    # Build the AgentConfig using discriminated union
    try:
        # Generate id from agent_id and version
        agent_id = data["agent_id"]
        version_str = str(data["version"])
        data_copy = dict(data)
        data_copy["id"] = f"{agent_id}:{version_str}"
        data_copy["version"] = version_str

        # Set default status if not provided
        if "status" not in data_copy:
            data_copy["status"] = AgentConfigStatus.DRAFT.value

        # Set default mcp_sources if not provided
        if "mcp_sources" not in data_copy:
            data_copy["mcp_sources"] = []

        # Set default error_handling if not provided
        if "error_handling" not in data_copy:
            data_copy["error_handling"] = {}

        # Validate with Pydantic discriminated union
        config = agent_config_adapter.validate_python(data_copy)
        result.config = config
        result.is_valid = True

    except ValidationError as e:
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            result.errors.append(f"{loc}: {msg}")


def validate_agent_config_yaml(file_path: Path) -> ValidationResult:
    """Validate an agent configuration YAML file against the schema.

    Performs the following validations:
    1. File exists and is readable
    2. Valid YAML syntax
    3. Required fields present (agent_id, type, version, description, etc.)
    4. Version format is valid semver (X.Y.Z)
    5. Type is a valid AgentType
    6. Status (if present) is a valid AgentConfigStatus
    7. Type-specific required fields are present
    8. Full Pydantic discriminated union validation

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

    # Use shared validation logic
    _validate_config_data(data, result)
    return result


def validate_agent_config_dict(data: dict[str, Any]) -> ValidationResult:
    """Validate an agent configuration dictionary against the schema.

    Same as validate_agent_config_yaml but for in-memory dict data.

    Args:
        data: Dictionary with agent config data.

    Returns:
        ValidationResult with is_valid=True if valid, errors list if not.
    """
    result = ValidationResult(file_path=Path("<dict>"), is_valid=False)

    if not isinstance(data, dict):
        result.errors.append("Data must be a dictionary")
        return result

    # Use shared validation logic
    _validate_config_data(data, result)
    return result
