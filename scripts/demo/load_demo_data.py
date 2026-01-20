#!/usr/bin/env python3
"""Seed data loader script with full Pydantic and FK validation.

This script loads E2E seed data (or custom data) into MongoDB with:
- Phase 1: Pydantic model validation (reject unknown fields, enforce types)
- Phase 2: Foreign key validation (check all FKs exist before loading)
- Phase 3: Database load in dependency order (upsert pattern)
- Phase 4: Post-load verification (confirm record counts)

Story 0.8.2: Seed Data Loader Script
AC #1: All phases run in order with validation
AC #2: Stop before database write if validation fails
AC #3: Show files processed, records loaded, total time
AC #4: Upsert pattern used (no duplicates on re-runs)
AC #5: Custom source path supported
AC #6: Dry-run mode validates without loading

Usage:
    # Load E2E seed data (default)
    python scripts/demo/load-demo-data.py --source e2e

    # Load from custom directory
    python scripts/demo/load-demo-data.py --source custom --path ./my-data/

    # Dry-run validation only (no database writes)
    python scripts/demo/load-demo-data.py --source e2e --dry-run

    # Clear databases before loading
    python scripts/demo/load-demo-data.py --source e2e --clear

    # Custom MongoDB URI
    python scripts/demo/load-demo-data.py --source e2e --mongodb-uri mongodb://user:pass@host:27017
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure imports work from project root
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Add libs to path
_libs_path = _project_root / "libs" / "fp-common"
if str(_libs_path) not in sys.path:
    sys.path.insert(0, str(_libs_path))

# Add services/ai-model for prompt/agent_config models
_ai_model_path = _project_root / "services" / "ai-model" / "src"
if str(_ai_model_path) not in sys.path:
    sys.path.insert(0, str(_ai_model_path))

# Add tests/e2e for MongoDBDirectClient
_e2e_path = _project_root / "tests" / "e2e"
if str(_e2e_path) not in sys.path:
    sys.path.insert(0, str(_e2e_path))


# Default E2E seed data location
DEFAULT_E2E_SEED_PATH = _project_root / "tests" / "e2e" / "infrastructure" / "seed"


def print_header(title: str) -> None:
    """Print a formatted phase header."""
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_status(label: str, status: str, detail: str = "") -> None:
    """Print a status line."""
    if detail:
        print(f"  {status:4}  {label} ({detail})")
    else:
        print(f"  {status:4}  {label}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Load seed data into MongoDB with full validation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--source",
        choices=["e2e", "custom"],
        default="e2e",
        help="Source of seed data (e2e = tests/e2e/infrastructure/seed/, custom = specify --path)",
    )

    parser.add_argument(
        "--path",
        type=Path,
        help="Path to custom seed data directory (required if --source custom)",
    )

    parser.add_argument(
        "--mongodb-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI (default: mongodb://localhost:27017)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run validation only, skip database load",
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all E2E databases before loading",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Path:
    """Validate arguments and return seed path.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Path to seed data directory.

    Raises:
        SystemExit: If arguments are invalid.
    """
    if args.source == "custom":
        if not args.path:
            print("ERROR: --path required when --source custom")
            sys.exit(1)
        if not args.path.exists():
            print(f"ERROR: Path does not exist: {args.path}")
            sys.exit(1)
        if not args.path.is_dir():
            print(f"ERROR: Path is not a directory: {args.path}")
            sys.exit(1)
        return args.path
    else:
        if not DEFAULT_E2E_SEED_PATH.exists():
            print(f"ERROR: E2E seed path does not exist: {DEFAULT_E2E_SEED_PATH}")
            sys.exit(1)
        return DEFAULT_E2E_SEED_PATH


def run_phase1_pydantic_validation(
    seed_path: Path,
) -> tuple[dict[str, list[Any]], list[Any], dict[str, int]]:
    """Run Phase 1: Pydantic validation on all seed files.

    Args:
        seed_path: Path to seed data directory.

    Returns:
        Tuple of (validated_data, all_errors, record_counts).
        validated_data: Dict mapping filename to list of validated model instances.
        all_errors: List of all validation errors found.
        record_counts: Dict mapping filename to record count.
    """
    # Import validation modules
    from scripts.demo.model_registry import get_model_for_file
    from scripts.demo.validation import ValidationError, validate_json_file

    print_header("PHASE 1: PYDANTIC VALIDATION")

    validated_data: dict[str, list[Any]] = {}
    all_errors: list[ValidationError] = []
    record_counts: dict[str, int] = {}

    # Import SEED_ORDER to process files in correct order
    from scripts.demo.loader import SEED_ORDER

    for filename, _, _, _ in SEED_ORDER:
        file_path = seed_path / filename

        if not file_path.exists():
            print_status(filename, "SKIP", "file not found")
            continue

        model = get_model_for_file(filename)
        if model is None:
            print_status(filename, "SKIP", "no model registered")
            continue

        try:
            result = validate_json_file(file_path, model)
            record_counts[filename] = len(result.validated) + len(result.errors)

            if result.is_valid:
                print_status(filename, "OK", f"{len(result.validated)} records")
                validated_data[filename] = result.validated
            else:
                print_status(filename, "FAIL", f"{len(result.errors)} errors")
                all_errors.extend(result.errors)

        except json.JSONDecodeError as e:
            print_status(filename, "FAIL", f"Invalid JSON: {e}")
            all_errors.append(
                ValidationError(
                    filename=filename,
                    record_index=0,
                    field_path="root",
                    message=f"Invalid JSON: {e}",
                )
            )

    return validated_data, all_errors, record_counts


def run_phase2_fk_validation(
    validated_data: dict[str, list[Any]],
) -> list[Any]:
    """Run Phase 2: Foreign key validation.

    Args:
        validated_data: Dict mapping filename to list of validated model instances.

    Returns:
        List of FK validation errors.
    """
    from scripts.demo.fk_registry import FKRegistry, FKValidationError, validate_foreign_keys
    from scripts.demo.loader import convert_pydantic_to_dicts

    print_header("PHASE 2: FOREIGN KEY VALIDATION")

    registry = FKRegistry()
    all_fk_errors: list[FKValidationError] = []

    # Register IDs from validated data in dependency order
    # Level 0 - Independent entities
    if "grading_models.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["grading_models.json"])
        ids = [d.get("model_id") for d in dicts if d.get("model_id")]
        registry.register("grading_models", ids)

    if "regions.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["regions.json"])
        ids = [d.get("region_id") for d in dicts if d.get("region_id")]
        registry.register("regions", ids)

    if "agent_configs.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["agent_configs.json"])
        ids = [d.get("id") for d in dicts if d.get("id")]
        registry.register("agent_configs", ids)

    if "prompts.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["prompts.json"])
        ids = [d.get("id") for d in dicts if d.get("id")]
        registry.register("prompts", ids)

    # Level 1 - Depends on Level 0
    if "source_configs.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["source_configs.json"])
        ids = [d.get("source_id") for d in dicts if d.get("source_id")]
        registry.register("source_configs", ids)

        # Validate optional FK: transformation.ai_agent_id -> agent_configs
        # Note: This is optional per ADR-020, so we skip FK validation for it

    if "factories.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["factories.json"])
        ids = [d.get("id") for d in dicts if d.get("id")]
        registry.register("factories", ids)

        # Validate FK: region_id -> regions (REQUIRED)
        errors = validate_foreign_keys(
            records=dicts,
            source_entity="factories",
            fk_mappings={"region_id": "regions"},
            registry=registry,
        )
        all_fk_errors.extend(errors)

    # Level 2 - Depends on Level 1 + Level 0
    if "collection_points.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["collection_points.json"])
        ids = [d.get("id") for d in dicts if d.get("id")]
        registry.register("collection_points", ids)

        # Validate FKs: factory_id -> factories, region_id -> regions (REQUIRED)
        errors = validate_foreign_keys(
            records=dicts,
            source_entity="collection_points",
            fk_mappings={
                "factory_id": "factories",
                "region_id": "regions",
            },
            registry=registry,
        )
        all_fk_errors.extend(errors)

    # Level 3 - Depends on Level 0 (regions)
    if "farmers.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["farmers.json"])
        ids = [d.get("id") for d in dicts if d.get("id")]
        registry.register("farmers", ids)

        # Validate FK: region_id -> regions (REQUIRED)
        errors = validate_foreign_keys(
            records=dicts,
            source_entity="farmers",
            fk_mappings={"region_id": "regions"},
            registry=registry,
        )
        all_fk_errors.extend(errors)

    # Level 4 - Depends on Level 3
    if "farmer_performance.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["farmer_performance.json"])

        # Validate FK: farmer_id -> farmers (REQUIRED)
        errors = validate_foreign_keys(
            records=dicts,
            source_entity="farmer_performance",
            fk_mappings={"farmer_id": "farmers"},
            registry=registry,
        )
        all_fk_errors.extend(errors)

    if "weather_observations.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["weather_observations.json"])

        # Validate FK: region_id -> regions (REQUIRED)
        errors = validate_foreign_keys(
            records=dicts,
            source_entity="weather_observations",
            fk_mappings={"region_id": "regions"},
            registry=registry,
        )
        all_fk_errors.extend(errors)

    # Level 5 - Depends on Levels 1 and 3
    if "documents.json" in validated_data:
        dicts = convert_pydantic_to_dicts(validated_data["documents.json"])

        # Extract source_id from nested ingestion field
        for d in dicts:
            if "ingestion" in d and "source_id" in d["ingestion"]:
                d["_source_id"] = d["ingestion"]["source_id"]

        # Validate FK: ingestion.source_id -> source_configs (REQUIRED)
        errors = validate_foreign_keys(
            records=dicts,
            source_entity="documents",
            fk_mappings={"_source_id": "source_configs"},
            registry=registry,
        )
        all_fk_errors.extend(errors)

        # Note: linkage_fields.farmer_id is optional per ADR-020

    # Print summary
    if all_fk_errors:
        print(f"  Found {len(all_fk_errors)} FK validation errors")
    else:
        print("  All foreign key relationships valid")

    return all_fk_errors


async def run_phase3_database_load(
    validated_data: dict[str, list[Any]],
    mongodb_uri: str,
    clear_databases: bool = False,
) -> list[Any]:
    """Run Phase 3: Database load in dependency order.

    Args:
        validated_data: Dict mapping filename to list of validated model instances.
        mongodb_uri: MongoDB connection URI.
        clear_databases: If True, clear databases before loading.

    Returns:
        List of LoadResult for each file loaded.
    """
    from scripts.demo.loader import SeedDataLoader, convert_pydantic_to_dicts

    print_header("PHASE 3: DATABASE LOAD")

    # Convert Pydantic models to dicts
    data_dicts: dict[str, list[dict[str, Any]]] = {}
    for filename, models in validated_data.items():
        data_dicts[filename] = convert_pydantic_to_dicts(models)

    async with SeedDataLoader(mongodb_uri) as loader:
        if clear_databases:
            print("  Clearing E2E databases...")
            await loader.clear_all_databases()

        results = await loader.load_all(data_dicts)

        for result in results:
            print(f"  Loaded {result.collection}: {result.records_loaded} records")

    return results


async def run_phase4_verification(
    record_counts: dict[str, int],
    mongodb_uri: str,
) -> list[Any]:
    """Run Phase 4: Post-load verification.

    Args:
        record_counts: Dict mapping filename to expected record count.
        mongodb_uri: MongoDB connection URI.

    Returns:
        List of VerificationResult.
    """
    from scripts.demo.loader import SeedDataLoader

    print_header("PHASE 4: VERIFICATION")

    async with SeedDataLoader(mongodb_uri) as loader:
        results = await loader.verify_counts(record_counts)

        for result in results:
            if result.is_valid:
                print(f"  OK   {result.database}.{result.collection}: {result.actual} records")
            else:
                print(f"  FAIL {result.database}.{result.collection}: expected {result.expected}, got {result.actual}")

    return results


def print_validation_errors(pydantic_errors: list[Any], fk_errors: list[Any]) -> None:
    """Print all validation errors in a formatted way.

    Args:
        pydantic_errors: List of Pydantic validation errors.
        fk_errors: List of FK validation errors.
    """
    if pydantic_errors:
        print()
        print("=" * 60)
        print("PYDANTIC VALIDATION ERRORS")
        print("=" * 60)
        for error in pydantic_errors:
            print(f"  {error}")

    if fk_errors:
        print()
        print("=" * 60)
        print("FOREIGN KEY VALIDATION ERRORS")
        print("=" * 60)
        for error in fk_errors:
            print(f"  {error}")


async def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    start_time = time.time()

    args = parse_args()
    seed_path = validate_args(args)

    print(f"Loading seed data from: {seed_path}")
    print(f"MongoDB URI: {args.mongodb_uri}")
    if args.dry_run:
        print("Mode: DRY-RUN (validation only, no database writes)")

    # Phase 1: Pydantic validation
    validated_data, pydantic_errors, record_counts = run_phase1_pydantic_validation(seed_path)

    # Phase 2: FK validation
    fk_errors = run_phase2_fk_validation(validated_data)

    # Check for validation failures
    if pydantic_errors or fk_errors:
        print_validation_errors(pydantic_errors, fk_errors)
        print()
        print("=" * 60)
        print("VALIDATION FAILED - No data loaded")
        print("=" * 60)
        print("Fix validation errors and re-run.")
        return 1

    # Dry-run stops here
    if args.dry_run:
        print()
        print("=" * 60)
        print("DRY-RUN VALIDATION SUCCESSFUL")
        print("=" * 60)
        total_records = sum(record_counts.values())
        print(f"  Files validated: {len(record_counts)}")
        print(f"  Total records: {total_records}")
        print()
        print("Would load the following to MongoDB:")
        for filename, count in record_counts.items():
            print(f"  - {filename}: {count} records")
        return 0

    # Phase 3: Database load
    await run_phase3_database_load(
        validated_data,
        args.mongodb_uri,
        clear_databases=args.clear,
    )

    # Phase 4: Verification
    verification_results = await run_phase4_verification(record_counts, args.mongodb_uri)

    # Check verification results
    failed_verifications = [r for r in verification_results if not r.is_valid]
    if failed_verifications:
        print()
        print("=" * 60)
        print("VERIFICATION FAILED - Record counts don't match")
        print("=" * 60)
        return 1

    # Success
    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"SUCCESS: All seed data loaded in {elapsed:.2f}s")
    print("=" * 60)
    total_records = sum(record_counts.values())
    print(f"  Files processed: {len(record_counts)}")
    print(f"  Total records: {total_records}")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
