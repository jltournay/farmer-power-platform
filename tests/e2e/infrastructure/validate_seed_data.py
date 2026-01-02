#!/usr/bin/env python3
"""Validate E2E seed data against Pydantic domain models.

Run this BEFORE starting the Docker stack to catch schema errors early.

Usage:
    python tests/e2e/infrastructure/validate_seed_data.py

Exit codes:
    0 - All seed data is valid
    1 - Validation errors found

This script validates:
    - factories.json against Factory model
    - farmers.json against Farmer model
    - collection_points.json against CollectionPoint model
    - regions.json against Region model
    - grading_models.json against GradingModel model
    - farmer_performance.json against FarmerPerformance model
    - weather_observations.json against RegionalWeather model
    - source_configs.json (basic structure check)
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add service paths to allow importing domain models
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "services" / "plantation-model" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "services" / "collection-model" / "src"))

SEED_DIR = Path(__file__).parent / "seed"


class ValidationError:
    """Represents a single validation error."""

    def __init__(self, file: str, index: int, record_id: str, error: str) -> None:
        self.file = file
        self.index = index
        self.record_id = record_id
        self.error = error

    def __str__(self) -> str:
        return f"  [{self.index}] {self.record_id}: {self.error}"


class SeedValidator:
    """Validates seed data files against domain models."""

    def __init__(self) -> None:
        self.errors: list[ValidationError] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Validate all seed files.

        Returns:
            True if all valid, False if any errors.
        """
        print("=" * 60)
        print("E2E SEED DATA VALIDATION")
        print("=" * 60)
        print()

        # Check seed directory exists
        if not SEED_DIR.exists():
            print(f"ERROR: Seed directory not found: {SEED_DIR}")
            return False

        # Validate each seed file
        self._validate_factories()
        self._validate_farmers()
        self._validate_collection_points()
        self._validate_regions()
        self._validate_grading_models()
        self._validate_farmer_performance()
        self._validate_weather_observations()
        self._validate_source_configs()

        # Print summary
        print()
        print("=" * 60)
        if self.errors:
            print(f"VALIDATION FAILED: {len(self.errors)} error(s) found")
            print("=" * 60)
            print()
            print("Fix these errors before starting the E2E infrastructure:")
            print()
            for error in self.errors:
                print(error)
            print()
            return False
        else:
            print("VALIDATION PASSED: All seed data is valid")
            print("=" * 60)
            if self.warnings:
                print()
                print("Warnings (non-blocking):")
                for warning in self.warnings:
                    print(f"  - {warning}")
            return True

    def _load_json(self, filename: str) -> list[dict[str, Any]] | None:
        """Load a JSON seed file."""
        filepath = SEED_DIR / filename
        if not filepath.exists():
            self.warnings.append(f"{filename} not found (optional)")
            return None
        try:
            with filepath.open() as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(ValidationError(filename, 0, "N/A", f"Invalid JSON: {e}"))
            return None

    def _validate_factories(self) -> None:
        """Validate factories.json against Factory model."""
        print("Validating factories.json...", end=" ")
        data = self._load_json("factories.json")
        if data is None:
            print("SKIP")
            return

        try:
            from plantation_model.domain.models import Factory

            for i, record in enumerate(data):
                record_id = record.get("id", f"index-{i}")
                try:
                    Factory.model_validate(record)
                except Exception as e:
                    self.errors.append(ValidationError("factories.json", i, record_id, str(e)))

            if not any(e.file == "factories.json" for e in self.errors):
                print(f"OK ({len(data)} records)")
            else:
                print("ERRORS")
        except ImportError as e:
            print(f"SKIP (model not available: {e})")

    def _validate_farmers(self) -> None:
        """Validate farmers.json against Farmer model."""
        print("Validating farmers.json...", end=" ")
        data = self._load_json("farmers.json")
        if data is None:
            print("SKIP")
            return

        try:
            from plantation_model.domain.models import Farmer

            for i, record in enumerate(data):
                record_id = record.get("id", f"index-{i}")
                try:
                    Farmer.model_validate(record)
                except Exception as e:
                    self.errors.append(ValidationError("farmers.json", i, record_id, str(e)))

            if not any(e.file == "farmers.json" for e in self.errors):
                print(f"OK ({len(data)} records)")
            else:
                print("ERRORS")
        except ImportError as e:
            print(f"SKIP (model not available: {e})")

    def _validate_collection_points(self) -> None:
        """Validate collection_points.json against CollectionPoint model."""
        print("Validating collection_points.json...", end=" ")
        data = self._load_json("collection_points.json")
        if data is None:
            print("SKIP")
            return

        try:
            from plantation_model.domain.models import CollectionPoint

            for i, record in enumerate(data):
                record_id = record.get("id", f"index-{i}")
                try:
                    CollectionPoint.model_validate(record)
                except Exception as e:
                    self.errors.append(ValidationError("collection_points.json", i, record_id, str(e)))

            if not any(e.file == "collection_points.json" for e in self.errors):
                print(f"OK ({len(data)} records)")
            else:
                print("ERRORS")
        except ImportError as e:
            print(f"SKIP (model not available: {e})")

    def _validate_regions(self) -> None:
        """Validate regions.json against Region model."""
        print("Validating regions.json...", end=" ")
        data = self._load_json("regions.json")
        if data is None:
            print("SKIP")
            return

        try:
            from plantation_model.domain.models import Region

            for i, record in enumerate(data):
                record_id = record.get("region_id", f"index-{i}")
                try:
                    Region.model_validate(record)
                except Exception as e:
                    self.errors.append(ValidationError("regions.json", i, record_id, str(e)))

            if not any(e.file == "regions.json" for e in self.errors):
                print(f"OK ({len(data)} records)")
            else:
                print("ERRORS")
        except ImportError as e:
            print(f"SKIP (model not available: {e})")

    def _validate_grading_models(self) -> None:
        """Validate grading_models.json (MongoDB seed structure)."""
        print("Validating grading_models.json...", end=" ")
        data = self._load_json("grading_models.json")
        if data is None:
            print("SKIP")
            return

        # MongoDB seed structure uses model_id, model_version, etc.
        required_fields = ["model_id", "model_version", "grading_type", "attributes", "grade_rules"]
        for i, record in enumerate(data):
            record_id = record.get("model_id", f"index-{i}")
            missing = [f for f in required_fields if f not in record]
            if missing:
                self.errors.append(
                    ValidationError(
                        "grading_models.json",
                        i,
                        record_id,
                        f"Missing required fields: {missing}",
                    )
                )
            # Validate grading_type is valid
            if record.get("grading_type") not in ["binary", "ternary"]:
                self.errors.append(
                    ValidationError(
                        "grading_models.json",
                        i,
                        record_id,
                        f"Invalid grading_type: {record.get('grading_type')} (must be 'binary' or 'ternary')",
                    )
                )

        if not any(e.file == "grading_models.json" for e in self.errors):
            print(f"OK ({len(data)} records)")
        else:
            print("ERRORS")

    def _validate_farmer_performance(self) -> None:
        """Validate farmer_performance.json against FarmerPerformance model."""
        print("Validating farmer_performance.json...", end=" ")
        data = self._load_json("farmer_performance.json")
        if data is None:
            print("SKIP")
            return

        try:
            from plantation_model.domain.models import (
                FarmerPerformance,
            )

            for i, record in enumerate(data):
                record_id = record.get("farmer_id", f"index-{i}")
                try:
                    FarmerPerformance.model_validate(record)
                except Exception as e:
                    self.errors.append(ValidationError("farmer_performance.json", i, record_id, str(e)))

            if not any(e.file == "farmer_performance.json" for e in self.errors):
                print(f"OK ({len(data)} records)")
            else:
                print("ERRORS")
        except ImportError as e:
            print(f"SKIP (model not available: {e})")

    def _validate_weather_observations(self) -> None:
        """Validate weather_observations.json (MongoDB seed structure)."""
        print("Validating weather_observations.json...", end=" ")
        data = self._load_json("weather_observations.json")
        if data is None:
            print("SKIP")
            return

        # MongoDB seed structure: { region_id, observations: [...], updated_at }
        required_fields = ["region_id", "observations"]
        observation_fields = ["date", "temperature", "precipitation_mm", "humidity_percent"]

        for i, record in enumerate(data):
            record_id = record.get("region_id", f"index-{i}")
            missing = [f for f in required_fields if f not in record]
            if missing:
                self.errors.append(
                    ValidationError(
                        "weather_observations.json",
                        i,
                        record_id,
                        f"Missing required fields: {missing}",
                    )
                )
            # Validate observations array
            observations = record.get("observations", [])
            if not observations:
                self.errors.append(
                    ValidationError(
                        "weather_observations.json",
                        i,
                        record_id,
                        "observations array is empty",
                    )
                )
            else:
                for j, obs in enumerate(observations):
                    obs_missing = [f for f in observation_fields if f not in obs]
                    if obs_missing:
                        self.errors.append(
                            ValidationError(
                                "weather_observations.json",
                                i,
                                f"{record_id}[{j}]",
                                f"Observation missing fields: {obs_missing}",
                            )
                        )

        if not any(e.file == "weather_observations.json" for e in self.errors):
            print(f"OK ({len(data)} records)")
        else:
            print("ERRORS")

    def _validate_source_configs(self) -> None:
        """Validate source_configs.json against SourceConfig Pydantic model."""
        print("Validating source_configs.json...", end=" ")
        data = self._load_json("source_configs.json")
        if data is None:
            print("SKIP")
            return

        try:
            from fp_common.models.source_config import SourceConfig

            for i, record in enumerate(data):
                record_id = record.get("source_id", f"index-{i}")
                try:
                    SourceConfig.model_validate(record)
                except Exception as e:
                    self.errors.append(ValidationError("source_configs.json", i, record_id, str(e)))

            if not any(e.file == "source_configs.json" for e in self.errors):
                print(f"OK ({len(data)} records)")
            else:
                print("ERRORS")
        except ImportError as e:
            print(f"SKIP (model not available: {e})")


def main() -> int:
    """Run seed data validation."""
    validator = SeedValidator()
    is_valid = validator.validate_all()
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
