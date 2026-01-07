"""RAG Document YAML validation.

This module validates document YAML files against the RagDocumentInput model schema.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from fp_knowledge.models import KnowledgeDomain, RagDocumentInput

# Valid file extensions for document upload
VALID_FILE_TYPES = {".pdf", ".md", ".markdown", ".txt", ".docx"}


@dataclass
class ValidationResult:
    """Result of validating a document YAML file."""

    file_path: Path
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    document: RagDocumentInput | None = None


def validate_document_yaml(file_path: Path) -> ValidationResult:
    """Validate a document YAML file against the schema.

    Performs the following validations:
    1. File exists and is readable
    2. Valid YAML syntax
    3. Required fields present (document_id, title, domain)
    4. Either content or file is provided (not both, not neither)
    5. Domain is a valid KnowledgeDomain value
    6. File type is valid if file path provided
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
    required_fields = ["document_id", "title", "domain"]
    for field_name in required_fields:
        if field_name not in data:
            result.errors.append(f"Missing required field: {field_name}")

    if result.errors:
        return result

    # Validate domain enum
    domain = data.get("domain", "")
    valid_domains = [d.value for d in KnowledgeDomain]
    if domain not in valid_domains:
        valid_list = ", ".join(valid_domains)
        result.errors.append(
            f"Invalid domain: '{domain}' (expected one of: {valid_list})"
        )

    # Validate content/file mutual exclusivity
    has_content = bool(data.get("content"))
    has_file = bool(data.get("file"))

    if not has_content and not has_file:
        result.errors.append(
            "Either 'content' or 'file' must be provided (found neither)"
        )
    elif has_content and has_file:
        result.errors.append("Cannot specify both 'content' and 'file' (choose one)")

    # Validate file type if file path provided
    if has_file:
        file_ref = data.get("file", "")
        file_ext = Path(file_ref).suffix.lower()
        if file_ext not in VALID_FILE_TYPES:
            valid_types = ", ".join(VALID_FILE_TYPES)
            result.errors.append(
                f"Invalid file type: '{file_ext}' (expected one of: {valid_types})"
            )
        # Check if referenced file exists (relative to YAML file)
        ref_path = file_path.parent / file_ref
        if not ref_path.exists():
            result.warnings.append(
                f"Referenced file not found: {file_ref} (resolved to {ref_path})"
            )

    if result.errors:
        return result

    # Build the RagDocumentInput model
    try:
        # Set default metadata if not provided
        if "metadata" not in data:
            data["metadata"] = {"author": "unknown"}

        # Validate with Pydantic
        document = RagDocumentInput.model_validate(data)
        result.document = document
        result.is_valid = True

    except ValidationError as e:
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            result.errors.append(f"{loc}: {msg}")

    return result


def validate_document_dict(data: dict) -> ValidationResult:
    """Validate a document dictionary against the schema.

    Same as validate_document_yaml but for in-memory dict data.

    Args:
        data: Dictionary with document data.

    Returns:
        ValidationResult with is_valid=True if valid, errors list if not.
    """
    result = ValidationResult(file_path=Path("<dict>"), is_valid=False)

    if not isinstance(data, dict):
        result.errors.append("Data must be a dictionary")
        return result

    # Validate required top-level fields
    required_fields = ["document_id", "title", "domain"]
    for field_name in required_fields:
        if field_name not in data:
            result.errors.append(f"Missing required field: {field_name}")

    if result.errors:
        return result

    # Validate domain enum
    domain = data.get("domain", "")
    valid_domains = [d.value for d in KnowledgeDomain]
    if domain not in valid_domains:
        valid_list = ", ".join(valid_domains)
        result.errors.append(
            f"Invalid domain: '{domain}' (expected one of: {valid_list})"
        )

    # Validate content/file mutual exclusivity
    has_content = bool(data.get("content"))
    has_file = bool(data.get("file"))

    if not has_content and not has_file:
        result.errors.append(
            "Either 'content' or 'file' must be provided (found neither)"
        )
    elif has_content and has_file:
        result.errors.append("Cannot specify both 'content' and 'file' (choose one)")

    if result.errors:
        return result

    # Build the RagDocumentInput model
    try:
        # Set default metadata if not provided
        data_copy = dict(data)
        if "metadata" not in data_copy:
            data_copy["metadata"] = {"author": "unknown"}

        # Validate with Pydantic
        document = RagDocumentInput.model_validate(data_copy)
        result.document = document
        result.is_valid = True

    except ValidationError as e:
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            result.errors.append(f"{loc}: {msg}")

    return result
