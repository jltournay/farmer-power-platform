#!/usr/bin/env python3
"""Demo data generator script.

This script generates demo data based on profile configurations.
Output follows the same structure as E2E seed files.

Story 0.8.4: Profile-Based Data Generation

Usage:
    # Generate demo dataset (deterministic)
    python scripts/demo/generate_demo_data.py --profile demo --seed 12345

    # Generate minimal dataset for quick testing
    python scripts/demo/generate_demo_data.py --profile minimal

    # Generate and load to MongoDB
    python scripts/demo/generate_demo_data.py --profile demo --seed 12345 --load

    # List available profiles
    python scripts/demo/generate_demo_data.py --list-profiles

    # Custom output directory
    python scripts/demo/generate_demo_data.py --profile demo --output ./my-data
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Set up paths
_project_root = Path(__file__).parent.parent.parent
_fp_common_path = _project_root / "libs" / "fp-common"
if str(_fp_common_path) not in sys.path:
    sys.path.insert(0, str(_fp_common_path))

_tests_demo_path = _project_root / "tests" / "demo"
if str(_tests_demo_path) not in sys.path:
    sys.path.insert(0, str(_tests_demo_path))

from generators.orchestrator import DataOrchestrator, GeneratedData  # noqa: E402
from generators.profile_loader import ProfileLoader  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate demo data based on profile configurations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate demo dataset with deterministic seed
  %(prog)s --profile demo --seed 12345

  # Generate minimal dataset for quick testing
  %(prog)s --profile minimal

  # Generate and load to MongoDB
  %(prog)s --profile demo --seed 12345 --load

  # List available profiles
  %(prog)s --list-profiles
        """,
    )

    parser.add_argument(
        "--profile",
        type=str,
        default="demo",
        help="Profile name (minimal, demo, demo-large). Default: demo",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic generation.",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory. Default: tests/demo/generated/{profile}",
    )

    parser.add_argument(
        "--load",
        action="store_true",
        help="Load generated data to MongoDB after generation.",
    )

    parser.add_argument(
        "--mongodb-uri",
        type=str,
        default="mongodb://localhost:27017",
        help="MongoDB URI for --load. Default: mongodb://localhost:27017",
    )

    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available profiles and exit.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output.",
    )

    return parser.parse_args()


def list_profiles() -> None:
    """List available profiles."""
    loader = ProfileLoader()
    profiles = loader.list_profiles()

    print("Available profiles:")
    for name in profiles:
        try:
            profile = loader.load(name)
            print(f"  {name}: {profile.description}")
            print(f"    Farmers: {profile.get_farmer_count()}")
            print(f"    Factories: {profile.get_factory_count()}")
            print(f"    Documents: {profile.get_document_count()}")
        except Exception as e:
            print(f"  {name}: (error loading: {e})")


def generate_data(args: argparse.Namespace) -> GeneratedData:
    """Generate data based on args.

    Args:
        args: Parsed command line arguments.

    Returns:
        GeneratedData container.
    """
    loader = ProfileLoader()
    profile = loader.load(args.profile)

    if args.verbose:
        print(f"Loaded profile: {profile.name}")
        print(f"  Description: {profile.description}")
        print(f"  Farmers: {profile.get_farmer_count()}")
        print(f"  Factories: {profile.get_factory_count()}")
        print(f"  Documents: {profile.get_document_count()}")
        print(f"  Scenarios: {profile.get_scenario_counts()}")
        print()

    orchestrator = DataOrchestrator(seed=args.seed)

    if args.verbose:
        if args.seed:
            print(f"Using seed: {args.seed}")
        else:
            print("Using random seed (non-deterministic)")
        print()

    print(f"Generating data for profile: {profile.name}...")

    data = orchestrator.generate(profile)

    print("Generated:")
    print(f"  Factories: {len(data.factories)}")
    print(f"  Collection Points: {len(data.collection_points)}")
    print(f"  Farmers: {len(data.farmers)}")
    print(f"  Farmer Performance: {len(data.farmer_performance)}")
    print(f"  Weather Observations: {len(data.weather_observations)}")
    print(f"  Documents: {len(data.documents)}")

    return data


def write_data(
    data: GeneratedData,
    output_dir: str | Path,
    verbose: bool = False,
) -> dict[str, int]:
    """Write generated data to files.

    Args:
        data: Generated data.
        output_dir: Output directory.
        verbose: Show verbose output.

    Returns:
        Dict mapping filename to record count.
    """
    orchestrator = DataOrchestrator(seed=data.seed)
    file_counts = orchestrator.write_to_files(data, output_dir)

    print(f"\nWritten to: {output_dir}")
    for filename, count in file_counts.items():
        print(f"  {filename}: {count} records")

    return file_counts


async def load_to_mongodb(
    data: GeneratedData,
    mongodb_uri: str,
    verbose: bool = False,
) -> None:
    """Load generated data to MongoDB.

    Uses the loader from Story 0.8.2.

    Args:
        data: Generated data.
        mongodb_uri: MongoDB URI.
        verbose: Show verbose output.
    """
    # Import loader (Story 0.8.2)
    sys.path.insert(0, str(_project_root / "scripts" / "demo"))
    from loader import SeedDataLoader

    # Prepare data in format expected by loader
    validated_data = {
        "factories.json": data.factories,
        "collection_points.json": data.collection_points,
        "farmers.json": data.farmers,
        "farmer_performance.json": data.farmer_performance,
        "weather_observations.json": data.weather_observations,
        "documents.json": data.documents,
    }

    print(f"\nLoading to MongoDB: {mongodb_uri}")

    async with SeedDataLoader(mongodb_uri) as loader:
        results = await loader.load_all(validated_data)

        print("Loaded:")
        for result in results:
            print(f"  {result.collection} ({result.database}): {result.records_loaded}")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    if args.list_profiles:
        list_profiles()
        return 0

    # Determine output directory
    output_dir = Path(args.output) if args.output else _project_root / "tests" / "demo" / "generated" / args.profile

    # Generate data
    try:
        data = generate_data(args)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Generation error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    if args.dry_run:
        print("\nDry run - no files written.")
        return 0

    # Write to files
    write_data(data, output_dir, args.verbose)

    # Optionally load to MongoDB
    if args.load:
        try:
            asyncio.run(load_to_mongodb(data, args.mongodb_uri, args.verbose))
        except Exception as e:
            print(f"MongoDB load error: {e}")
            if args.verbose:
                import traceback

                traceback.print_exc()
            return 1

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
