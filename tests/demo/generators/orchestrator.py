"""Data generation orchestrator for profile-based demo data creation.

This module orchestrates the complete data generation process:
1. Loads reference data from E2E seed files
2. Generates new data based on profile configuration
3. Assigns scenarios to farmers
4. Generates quality documents based on scenarios
5. Outputs JSON files in E2E seed format

Story 0.8.4: Profile-Based Data Generation
AC #1: Profile-based generation (minimal, demo, demo-large)
AC #2: Output follows E2E seed file structure
AC #3: Deterministic with --seed flag
AC #5: Scenario-based quality patterns
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Set up paths at module load time
_project_root = Path(__file__).parent.parent.parent.parent
_fp_common_path = _project_root / "libs" / "fp-common"
if str(_fp_common_path) not in sys.path:
    sys.path.insert(0, str(_fp_common_path))

_demo_scripts_path = _project_root / "scripts" / "demo"
if str(_demo_scripts_path) not in sys.path:
    sys.path.insert(0, str(_demo_scripts_path))

from fk_registry import FKRegistry  # noqa: E402

from .base import BaseModelFactory, FKRegistryMixin  # noqa: E402
from .plantation import (  # noqa: E402
    CollectionPointFactory,
    FactoryEntityFactory,
    FarmerFactory,
    FarmerPerformanceFactory,
)
from .profile_loader import Profile, parse_range  # noqa: E402
from .quality import DocumentFactory  # noqa: E402
from .random_utils import set_global_seed  # noqa: E402
from .scenarios import FarmerScenario, ScenarioAssigner  # noqa: E402
from .weather import RegionalWeatherFactory  # noqa: E402


@dataclass
class GeneratedData:
    """Container for all generated data.

    Attributes:
        factories: List of Factory dicts.
        collection_points: List of CollectionPoint dicts.
        farmers: List of Farmer dicts with scenario assignments.
        farmer_performance: List of FarmerPerformance dicts.
        weather_observations: List of RegionalWeather dicts.
        documents: List of Document dicts.
    """

    factories: list[dict[str, Any]] = field(default_factory=list)
    collection_points: list[dict[str, Any]] = field(default_factory=list)
    farmers: list[dict[str, Any]] = field(default_factory=list)
    farmer_performance: list[dict[str, Any]] = field(default_factory=list)
    weather_observations: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    profile_name: str = ""
    seed: int | None = None
    generated_at: str = ""


class DataOrchestrator:
    """Orchestrates profile-based demo data generation.

    Handles the complete generation pipeline:
    1. Loading reference data (regions, grading_models from E2E seed)
    2. Generating factories and collection points
    3. Generating farmers with scenario assignments
    4. Generating quality documents following scenario patterns
    5. Generating weather data

    Example:
        orchestrator = DataOrchestrator(seed=12345)
        profile = ProfileLoader().load("demo")

        data = orchestrator.generate(profile)

        # Write to files
        orchestrator.write_to_files(data, output_dir="tests/demo/generated/demo")

        # Or load directly to MongoDB
        await orchestrator.load_to_mongodb(data, mongodb_uri)
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize orchestrator with optional seed.

        Args:
            seed: Random seed for deterministic generation.
        """
        self._seed = seed
        self._fk_registry = FKRegistry()

        # Initialize global seed for all random operations
        if seed is not None:
            set_global_seed(seed)
            BaseModelFactory.set_seed(seed)  # Set polyfactory seed

        # Set FK registry for all factories
        FKRegistryMixin.set_fk_registry(self._fk_registry)

        # Reset factory counters
        FactoryEntityFactory.reset_counter()
        CollectionPointFactory.reset_counter()
        FarmerFactory.reset_counter()
        FarmerPerformanceFactory.reset_counter()
        RegionalWeatherFactory.reset_counter()
        DocumentFactory.reset_counter()

        # E2E seed path
        self._e2e_seed_path = _project_root / "tests" / "e2e" / "infrastructure" / "seed"

    def generate(self, profile: Profile) -> GeneratedData:
        """Generate all data based on profile configuration.

        Args:
            profile: Loaded profile configuration.

        Returns:
            GeneratedData container with all generated entities.
        """
        data = GeneratedData(
            profile_name=profile.name,
            seed=self._seed,
            generated_at=datetime.now().isoformat(),
        )

        # Step 1: Load reference data from E2E seed
        self._load_reference_data()

        # Step 2: Generate factories
        factory_count = profile.get_factory_count()
        factories = FactoryEntityFactory.build_batch_and_register(factory_count)
        data.factories = [f.model_dump(mode="json") for f in factories]

        # Step 3: Generate collection points
        cp_count = profile.get_collection_point_count()
        collection_points = CollectionPointFactory.build_batch_and_register(cp_count)
        data.collection_points = [cp.model_dump(mode="json") for cp in collection_points]

        # Step 4: Generate farmers with scenario assignments
        farmers, farmer_scenarios = self._generate_farmers_with_scenarios(profile)
        data.farmers = [f.model_dump(mode="json") for f in farmers]

        # Step 5: Generate farmer performance
        performances = []
        for farmer in farmers:
            perf = FarmerPerformanceFactory.build(farmer_id=farmer.id)
            performances.append(perf)
        data.farmer_performance = [p.model_dump(mode="json") for p in performances]

        # Step 6: Generate weather observations
        region_ids = list(self._fk_registry.get_valid_ids("regions"))
        weather_obs = []
        for region_id in region_ids:
            weather = RegionalWeatherFactory.build(region_id=region_id)
            weather_obs.append(weather)
        data.weather_observations = [w.model_dump(mode="json") for w in weather_obs]

        # Step 7: Generate quality documents based on scenarios
        documents = self._generate_documents_with_scenarios(
            farmers=farmers,
            farmer_scenarios=farmer_scenarios,
            profile=profile,
        )
        data.documents = [d.model_dump(mode="json") for d in documents]

        return data

    def _load_reference_data(self) -> None:
        """Load reference data from E2E seed files into FK registry."""
        # Load regions
        regions_path = self._e2e_seed_path / "regions.json"
        if regions_path.exists():
            with regions_path.open() as f:
                regions = json.load(f)
            region_ids = [r["region_id"] for r in regions]
            self._fk_registry.register("regions", region_ids)

        # Load grading models
        grading_path = self._e2e_seed_path / "grading_models.json"
        if grading_path.exists():
            with grading_path.open() as f:
                grading_models = json.load(f)
            model_ids = [g["model_id"] for g in grading_models]
            self._fk_registry.register("grading_models", model_ids)

        # Load source configs
        source_path = self._e2e_seed_path / "source_configs.json"
        if source_path.exists():
            with source_path.open() as f:
                source_configs = json.load(f)
            source_ids = [s["source_id"] for s in source_configs]
            self._fk_registry.register("source_configs", source_ids)

    def _generate_farmers_with_scenarios(self, profile: Profile) -> tuple[list, dict[str, FarmerScenario]]:
        """Generate farmers and assign scenarios.

        Args:
            profile: Profile configuration.

        Returns:
            Tuple of (farmers list, farmer_id -> scenario mapping).
        """
        farmer_count = profile.get_farmer_count()
        scenario_counts = profile.get_scenario_counts()
        id_prefix = profile.get_farmer_id_prefix()

        # Set up scenario assigner
        assigner = ScenarioAssigner(scenario_counts)

        # Set custom ID prefix for this profile
        FarmerFactory._id_prefix = id_prefix
        FarmerFactory.reset_counter()

        farmers = []
        farmer_scenarios: dict[str, FarmerScenario] = {}

        for _ in range(farmer_count):
            farmer = FarmerFactory.build()
            farmers.append(farmer)

            # Check if this farmer gets a predefined scenario
            scenario = assigner.get_next_scenario()
            if scenario:
                farmer_scenarios[farmer.id] = scenario

            # Register farmer ID
            self._fk_registry.register("farmers", [farmer.id])

        return farmers, farmer_scenarios

    def _generate_documents_with_scenarios(
        self,
        farmers: list,
        farmer_scenarios: dict[str, FarmerScenario],
        profile: Profile,
    ) -> list:
        """Generate quality documents following farmer scenarios.

        Farmers with assigned scenarios get documents following their
        quality pattern. Other farmers get random quality documents.

        Args:
            farmers: List of Farmer instances.
            farmer_scenarios: Mapping of farmer_id to scenario.
            profile: Profile configuration.

        Returns:
            List of Document instances.
        """
        documents = []
        historical_days = profile.get_historical_days()

        # Get per-farmer document count
        doc_config = profile.generated_data.quality_documents
        min_docs, max_docs = parse_range(doc_config.per_farmer)

        for farmer in farmers:
            # Get a random factory for this farmer's documents
            factory_ids = list(self._fk_registry.get_valid_ids("factories"))
            factory_id = random.choice(factory_ids)

            if farmer.id in farmer_scenarios:
                # Generate documents following scenario pattern
                scenario = farmer_scenarios[farmer.id]
                farmer_docs = DocumentFactory.generate_for_scenario(
                    farmer_id=farmer.id,
                    factory_id=factory_id,
                    scenario=scenario,
                    days_span=historical_days,
                )
                documents.extend(farmer_docs)
            else:
                # Generate random quality documents
                doc_count = random.randint(min_docs, max_docs)
                farmer_docs = DocumentFactory.generate_random_for_farmer(
                    farmer_id=farmer.id,
                    factory_id=factory_id,
                    count=doc_count,
                    days_span=historical_days,
                )
                documents.extend(farmer_docs)

        return documents

    def write_to_files(
        self,
        data: GeneratedData,
        output_dir: str | Path,
    ) -> dict[str, int]:
        """Write generated data to JSON files in E2E seed format.

        Creates files in the same structure as tests/e2e/infrastructure/seed/

        Args:
            data: Generated data container.
            output_dir: Output directory path.

        Returns:
            Dict mapping filename to record count.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_counts: dict[str, int] = {}

        # Write each entity type
        files_to_write = [
            ("factories.json", data.factories),
            ("collection_points.json", data.collection_points),
            ("farmers.json", data.farmers),
            ("farmer_performance.json", data.farmer_performance),
            ("weather_observations.json", data.weather_observations),
            ("documents.json", data.documents),
        ]

        for filename, records in files_to_write:
            if records:
                filepath = output_path / filename
                with filepath.open("w") as f:
                    json.dump(records, f, indent=2, default=str)
                file_counts[filename] = len(records)

        # Write metadata file
        metadata = {
            "profile": data.profile_name,
            "seed": data.seed,
            "generated_at": data.generated_at,
            "counts": file_counts,
        }
        metadata_path = output_path / "_metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)

        return file_counts

    def get_fk_registry(self) -> FKRegistry:
        """Get the FK registry instance."""
        return self._fk_registry
