"""Demo data validation and generation module.

This package provides:
- Pydantic-based validation for seed data files
- FK registry for referential integrity checks
- Model registry mapping file patterns to Pydantic models

Story 0.8.1: Pydantic Validation Infrastructure
"""

from scripts.demo.fk_registry import (
    FKRegistry,
    FKValidationError,
    validate_foreign_keys,
)
from scripts.demo.model_registry import (
    ModelRegistry,
    get_model_for_file,
    get_seed_model_registry,
)
from scripts.demo.validation import (
    ValidationError,
    ValidationResult,
    validate_json_file,
    validate_with_pydantic,
)

__all__ = [
    "FKRegistry",
    "FKValidationError",
    "ModelRegistry",
    "ValidationError",
    "ValidationResult",
    "get_model_for_file",
    "get_seed_model_registry",
    "validate_foreign_keys",
    "validate_json_file",
    "validate_with_pydantic",
]
