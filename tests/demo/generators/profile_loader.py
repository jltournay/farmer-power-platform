"""Profile loader for YAML-based data generation profiles.

This module loads and validates YAML profile configurations that define
how much and what kind of demo data to generate.

Story 0.8.4: Profile-Based Data Generation
AC #1: Profiles defined in YAML (minimal, demo, demo-large)
AC #2: Profile loading with schema validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DistributionConfig:
    """Configuration for distribution of values.

    Attributes:
        by_region: How to distribute across regions (proportional, first, random).
        farm_scale: Percentage distribution of farm scales.
        notification_channel: Percentage distribution of notification channels.
        pref_lang: Percentage distribution of preferred languages.
    """

    by_region: str = "proportional"
    farm_scale: dict[str, int] = field(default_factory=lambda: {"smallholder": 60, "medium": 35, "estate": 5})
    notification_channel: dict[str, int] = field(default_factory=lambda: {"sms": 70, "whatsapp": 30})
    pref_lang: dict[str, int] = field(default_factory=lambda: {"sw": 50, "en": 30, "ki": 15, "luo": 5})


@dataclass
class FarmerConfig:
    """Configuration for farmer generation.

    Attributes:
        count: Number of farmers to generate.
        id_prefix: Prefix for farmer IDs.
        distribution: Distribution configuration.
        scenarios: Dict mapping scenario name to count.
    """

    count: int
    id_prefix: str = "FRM-GEN-"
    distribution: DistributionConfig = field(default_factory=DistributionConfig)
    scenarios: dict[str, int] = field(default_factory=dict)


@dataclass
class DocumentConfig:
    """Configuration for quality document generation.

    Attributes:
        count: Total number of documents to generate.
        per_farmer: Documents per farmer (int or "5-15" range).
        date_range: Date range for documents.
    """

    count: int
    per_farmer: str | int = "5-15"
    date_range: str = "last_90_days"


@dataclass
class GeneratedDataConfig:
    """Configuration for all generated data types.

    Attributes:
        factories: Factory generation config.
        collection_points: Collection point config.
        farmers: Farmer generation config.
        farmer_performance: Performance data config.
        weather_observations: Weather data config.
        quality_documents: Document generation config.
        cost_events: Cost event generation config (Story 0.8.6).
    """

    factories: dict[str, Any] = field(default_factory=dict)
    collection_points: dict[str, Any] = field(default_factory=dict)
    farmers: FarmerConfig = field(default_factory=lambda: FarmerConfig(count=10))
    farmer_performance: dict[str, Any] = field(default_factory=dict)
    weather_observations: dict[str, Any] = field(default_factory=dict)
    quality_documents: DocumentConfig = field(default_factory=lambda: DocumentConfig(count=100))
    cost_events: dict[str, Any] = field(default_factory=dict)


@dataclass
class Profile:
    """Complete profile configuration.

    Attributes:
        name: Profile name (minimal, demo, demo-large).
        description: Human-readable description.
        reference_data: Reference data configuration.
        generated_data: Generated data configuration.
    """

    name: str
    description: str
    reference_data: dict[str, Any]
    generated_data: GeneratedDataConfig

    def get_farmer_count(self) -> int:
        """Get the total number of farmers to generate."""
        return self.generated_data.farmers.count

    def get_factory_count(self) -> int:
        """Get the total number of factories to generate."""
        return self.generated_data.factories.get("count", 1)

    def get_collection_point_count(self) -> int:
        """Get the total number of collection points to generate."""
        return self.generated_data.collection_points.get("count", 2)

    def get_document_count(self) -> int:
        """Get the total number of documents to generate."""
        return self.generated_data.quality_documents.count

    def get_scenario_counts(self) -> dict[str, int]:
        """Get scenario assignment counts."""
        return self.generated_data.farmers.scenarios

    def get_farmer_id_prefix(self) -> str:
        """Get the ID prefix for generated farmers."""
        return self.generated_data.farmers.id_prefix

    def get_historical_days(self) -> int:
        """Get the number of historical days for data generation."""
        perf_config = self.generated_data.farmer_performance
        return perf_config.get("historical_days", 90)


class ProfileLoader:
    """Loads and validates YAML profile configurations.

    Example:
        loader = ProfileLoader(profiles_dir="tests/demo/profiles")
        profile = loader.load("demo")

        print(f"Generating {profile.get_farmer_count()} farmers")
        print(f"Scenarios: {profile.get_scenario_counts()}")
    """

    def __init__(self, profiles_dir: str | Path | None = None) -> None:
        """Initialize the profile loader.

        Args:
            profiles_dir: Path to profiles directory.
                Defaults to tests/demo/profiles.
        """
        if profiles_dir is None:
            # Default to tests/demo/profiles relative to this file
            self._profiles_dir = Path(__file__).parent.parent / "profiles"
        else:
            self._profiles_dir = Path(profiles_dir)

    def list_profiles(self) -> list[str]:
        """List available profile names.

        Returns:
            List of profile names (without .yaml extension).
        """
        if not self._profiles_dir.exists():
            return []

        return [p.stem for p in self._profiles_dir.glob("*.yaml") if not p.name.startswith("_")]

    def load(self, profile_name: str) -> Profile:
        """Load a profile by name.

        Args:
            profile_name: Name of the profile (without .yaml extension).

        Returns:
            Profile instance with parsed configuration.

        Raises:
            FileNotFoundError: If profile file doesn't exist.
            ValueError: If profile is invalid.
        """
        profile_path = self._profiles_dir / f"{profile_name}.yaml"

        if not profile_path.exists():
            available = self.list_profiles()
            raise FileNotFoundError(f"Profile not found: {profile_name}. Available profiles: {available}")

        with profile_path.open() as f:
            data = yaml.safe_load(f)

        return self._parse_profile(data, profile_name)

    def _parse_profile(self, data: dict[str, Any], profile_name: str) -> Profile:
        """Parse raw YAML data into Profile instance.

        Args:
            data: Raw YAML data dictionary.
            profile_name: Name of the profile being parsed.

        Returns:
            Parsed Profile instance.

        Raises:
            ValueError: If required fields are missing.
        """
        # Validate required fields
        if "generated_data" not in data:
            raise ValueError(f"Profile {profile_name} missing 'generated_data' section")

        gen_data = data["generated_data"]

        # Parse farmer config
        farmer_data = gen_data.get("farmers", {})
        farmer_dist_data = farmer_data.get("distribution", {})

        distribution = DistributionConfig(
            by_region=farmer_dist_data.get("by_region", "proportional"),
            farm_scale=farmer_dist_data.get("farm_scale", {"smallholder": 60, "medium": 35, "estate": 5}),
            notification_channel=farmer_dist_data.get("notification_channel", {"sms": 70, "whatsapp": 30}),
            pref_lang=farmer_dist_data.get("pref_lang", {"sw": 50, "en": 30, "ki": 15, "luo": 5}),
        )

        farmer_config = FarmerConfig(
            count=farmer_data.get("count", 10),
            id_prefix=farmer_data.get("id_prefix", "FRM-GEN-"),
            distribution=distribution,
            scenarios=farmer_data.get("scenarios", {}),
        )

        # Parse document config
        doc_data = gen_data.get("quality_documents", {})
        doc_dist = doc_data.get("distribution", {})

        document_config = DocumentConfig(
            count=doc_data.get("count", 100),
            per_farmer=doc_dist.get("per_farmer", "5-15"),
            date_range=doc_dist.get("date_range", "last_90_days"),
        )

        generated_data_config = GeneratedDataConfig(
            factories=gen_data.get("factories", {"count": 1}),
            collection_points=gen_data.get("collection_points", {"count": 2}),
            farmers=farmer_config,
            farmer_performance=gen_data.get("farmer_performance", {}),
            weather_observations=gen_data.get("weather_observations", {}),
            quality_documents=document_config,
            cost_events=gen_data.get("cost_events", {}),
        )

        return Profile(
            name=data.get("profile", profile_name),
            description=data.get("description", ""),
            reference_data=data.get("reference_data", {}),
            generated_data=generated_data_config,
        )

    def get_profiles_dir(self) -> Path:
        """Get the profiles directory path."""
        return self._profiles_dir


def parse_range(range_str: str | int) -> tuple[int, int]:
    """Parse a range string like "5-15" into (min, max) tuple.

    Args:
        range_str: Range string "min-max" or single int.

    Returns:
        Tuple of (min, max) integers.
    """
    if isinstance(range_str, int):
        return (range_str, range_str)

    if "-" in str(range_str):
        parts = str(range_str).split("-")
        return (int(parts[0]), int(parts[1]))

    return (int(range_str), int(range_str))
