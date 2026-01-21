"""Plantation model factories for generating valid domain entities.

This module provides Polyfactory factories for:
- Region
- Factory (FactoryEntityFactory to avoid naming conflict)
- CollectionPoint
- Farmer
- FarmerPerformance

Story 0.8.3: Polyfactory Generator Framework
AC #1: Factories exist for each Plantation model
AC #2: FK fields reference FK registry
AC #3: Kenya-specific data (names, phones, coordinates)
AC #4: Generated Farmer passes Pydantic validation
"""

from __future__ import annotations

import datetime as dt
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar


# Set up paths at module load time
def _setup_paths() -> None:
    """Set up required paths for imports."""
    project_root = Path(__file__).parent.parent.parent.parent
    paths_to_add = [
        project_root / "libs" / "fp-common",  # fp_common is directly under fp-common/
        project_root / "scripts" / "demo",
    ]
    for p in paths_to_add:
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


_setup_paths()

from fp_common.models.collection_point import CollectionPoint  # noqa: E402
from fp_common.models.factory import Factory  # noqa: E402
from fp_common.models.farmer import (  # noqa: E402
    Farmer,
    FarmScale,
    InteractionPreference,
    NotificationChannel,
    PreferredLanguage,
)
from fp_common.models.farmer_performance import (  # noqa: E402
    FarmerPerformance,
)
from fp_common.models.region import Region  # noqa: E402
from fp_common.models.value_objects import (  # noqa: E402
    AltitudeBandLabel,
    PaymentPolicyType,
)

from .base import BaseModelFactory  # noqa: E402
from .kenya_providers import KenyaProvider  # noqa: E402


class RegionFactory(BaseModelFactory[Region]):
    """Factory for generating valid Region instances.

    Regions are independent entities (no FK dependencies).
    Region IDs follow format: {county}-{altitude_band} (e.g., nyeri-highland).
    """

    __model__ = Region
    _entity_type: ClassVar[str] = "regions"
    _id_counter: ClassVar[int] = 0

    # Predefined counties for variety
    COUNTIES: ClassVar[list[str]] = ["nyeri", "kericho", "nandi", "bomet", "muranga", "kiambu", "embu", "meru"]

    @classmethod
    def region_id(cls) -> str:
        """Generate region_id in format {county}-{altitude_band}."""
        county = random.choice(cls.COUNTIES)
        band = random.choice(["highland", "midland", "lowland"])
        return f"{county}-{band}"

    @classmethod
    def name(cls) -> str:
        """Generate human-readable region name."""
        county = random.choice(cls.COUNTIES).title()
        band = random.choice(["Highland", "Midland", "Lowland"])
        return f"{county} {band}"

    @classmethod
    def county(cls) -> str:
        """Generate county name."""
        return random.choice(cls.COUNTIES).title()

    @classmethod
    def country(cls) -> str:
        """Always Kenya."""
        return "Kenya"

    @classmethod
    def geography(cls) -> dict:
        """Generate valid Geography with altitude band."""
        lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=True)

        # Determine altitude band from altitude (per project-context.md)
        # Low: <800m, Medium: 800-1200m, High: >1200m
        if alt >= 1200:
            band_label = AltitudeBandLabel.HIGHLAND
            alt_min, alt_max = 1200, 2500
        elif alt >= 800:
            band_label = AltitudeBandLabel.MIDLAND
            alt_min, alt_max = 800, 1200
        else:
            band_label = AltitudeBandLabel.LOWLAND
            alt_min, alt_max = 0, 800

        return {
            "center_gps": {"lat": lat, "lng": lng},
            "radius_km": random.uniform(10, 30),
            "altitude_band": {
                "min_meters": alt_min,
                "max_meters": alt_max,
                "label": band_label.value,
            },
        }

    @classmethod
    def flush_calendar(cls) -> dict:
        """Generate standard tea flush calendar."""
        return {
            "first_flush": {
                "start": "03-15",
                "end": "05-15",
                "characteristics": "Highest quality, delicate flavor",
            },
            "monsoon_flush": {
                "start": "06-15",
                "end": "09-30",
                "characteristics": "High volume, robust flavor",
            },
            "autumn_flush": {
                "start": "10-15",
                "end": "12-15",
                "characteristics": "Balanced quality",
            },
            "dormant": {
                "start": "12-16",
                "end": "03-14",
                "characteristics": "Minimal growth",
            },
        }

    @classmethod
    def agronomic(cls) -> dict:
        """Generate agronomic factors."""
        soil_types = ["volcanic_red", "volcanic_brown", "laterite", "alluvial"]
        diseases = ["blister_blight", "grey_blight", "red_rust", "black_rot"]

        return {
            "soil_type": random.choice(soil_types),
            "typical_diseases": random.sample(diseases, k=random.randint(2, 4)),
            "harvest_peak_hours": "06:00-10:00",
            "frost_risk": random.choice([True, False]),
        }

    @classmethod
    def weather_config(cls) -> dict:
        """Generate weather API configuration."""
        lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=True)
        return {
            "api_location": {"lat": lat, "lng": lng},
            "altitude_for_api": int(alt),
            "collection_time": "06:00",
        }

    @classmethod
    def is_active(cls) -> bool:
        """Generate active status (mostly active)."""
        return random.random() > 0.1  # 90% active


class FactoryEntityFactory(BaseModelFactory[Factory]):
    """Factory for generating valid Factory (tea processing facility) instances.

    Named FactoryEntityFactory to avoid conflict with polyfactory.Factory.
    FK Dependencies: region_id -> regions
    """

    __model__ = Factory
    _id_prefix: ClassVar[str] = "KEN-FAC-"
    _entity_type: ClassVar[str] = "factories"
    _id_counter: ClassVar[int] = 0

    @classmethod
    def id(cls) -> str:
        """Generate factory ID."""
        return cls._next_id()

    @classmethod
    def name(cls) -> str:
        """Generate factory name."""
        county = KenyaProvider.tea_region_county().title()
        suffixes = ["Tea Factory", "Processing Plant", "Tea Works", "Tea Estate"]
        return f"{county} {random.choice(suffixes)}"

    @classmethod
    def code(cls) -> str:
        """Generate short factory code."""
        letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
        return letters

    @classmethod
    def region_id(cls) -> str:
        """Get region_id from FK registry."""
        return cls.get_random_fk("regions")

    @classmethod
    def location(cls) -> dict:
        """Generate valid GeoLocation."""
        lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=True)
        return {
            "latitude": lat,
            "longitude": lng,
            "altitude_meters": alt,
        }

    @classmethod
    def contact(cls) -> dict:
        """Generate contact information."""
        return {
            "phone": KenyaProvider.phone_number(),
            "email": f"factory{random.randint(1, 999)}@teafactory.co.ke",
            "address": f"P.O. Box {random.randint(100, 9999)}, Kenya",
        }

    @classmethod
    def processing_capacity_kg(cls) -> int:
        """Generate daily processing capacity."""
        return random.randint(10000, 100000)

    @classmethod
    def quality_thresholds(cls) -> dict:
        """Generate quality tier thresholds."""
        return {
            "tier_1": 85.0,
            "tier_2": 70.0,
            "tier_3": 50.0,
        }

    @classmethod
    def payment_policy(cls) -> dict:
        """Generate payment policy."""
        policy_types = [e.value for e in PaymentPolicyType]
        return {
            "policy_type": random.choice(policy_types),
            "tier_1_adjustment": round(random.uniform(0.0, 0.15), 2),
            "tier_2_adjustment": 0.0,
            "tier_3_adjustment": round(random.uniform(-0.05, 0.0), 2),
            "below_tier_3_adjustment": round(random.uniform(-0.10, -0.05), 2),
        }

    @classmethod
    def is_active(cls) -> bool:
        """Generate active status (mostly active)."""
        return random.random() > 0.1


class CollectionPointFactory(BaseModelFactory[CollectionPoint]):
    """Factory for generating valid CollectionPoint instances.

    FK Dependencies:
    - factory_id -> factories
    - region_id -> regions
    """

    __model__ = CollectionPoint
    _id_prefix: ClassVar[str] = "CP-"
    _entity_type: ClassVar[str] = "collection_points"
    _id_counter: ClassVar[int] = 0

    @classmethod
    def id(cls) -> str:
        """Generate collection point ID."""
        return cls._next_id()

    @classmethod
    def name(cls) -> str:
        """Generate collection point name."""
        prefixes = ["Central", "Northern", "Southern", "Eastern", "Western", "Main", "Upper", "Lower"]
        suffixes = ["Collection Point", "Tea Buying Center", "Collection Center", "Weighing Station"]
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"

    @classmethod
    def factory_id(cls) -> str:
        """Get factory_id from FK registry."""
        return cls.get_random_fk("factories")

    @classmethod
    def region_id(cls) -> str:
        """Get region_id from FK registry."""
        return cls.get_random_fk("regions")

    @classmethod
    def location(cls) -> dict:
        """Generate valid GeoLocation."""
        lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=True)
        return {
            "latitude": lat,
            "longitude": lng,
            "altitude_meters": alt,
        }

    @classmethod
    def clerk_id(cls) -> str | None:
        """Generate clerk ID (optional)."""
        if random.random() > 0.3:  # 70% have clerk
            return f"CLK-{random.randint(1, 999):03d}"
        return None

    @classmethod
    def clerk_phone(cls) -> str | None:
        """Generate clerk phone (optional)."""
        if random.random() > 0.3:
            return KenyaProvider.phone_number()
        return None

    @classmethod
    def operating_hours(cls) -> dict:
        """Generate operating hours."""
        return {
            "weekdays": "06:00-10:00",
            "weekends": "07:00-09:00",
        }

    @classmethod
    def collection_days(cls) -> list[str]:
        """Generate collection days."""
        all_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        # Most collect 3-5 days per week
        num_days = random.randint(3, 5)
        return sorted(random.sample(all_days[:6], num_days))  # Exclude Sunday usually

    @classmethod
    def capacity(cls) -> dict:
        """Generate capacity information."""
        storage_types = ["covered_shed", "open_air", "refrigerated"]
        return {
            "max_daily_kg": random.randint(1000, 10000),
            "storage_type": random.choice(storage_types),
            "has_weighing_scale": True,
            "has_qc_device": random.choice([True, False]),
        }

    @classmethod
    def status(cls) -> str:
        """Generate status."""
        statuses = ["active", "inactive", "seasonal"]
        weights = [85, 10, 5]
        return random.choices(statuses, weights=weights)[0]

    @classmethod
    def farmer_ids(cls) -> list[str]:
        """Generate empty farmer_ids list (populated separately)."""
        # Start with empty list - farmers assigned separately
        return []


class FarmerFactory(BaseModelFactory[Farmer]):
    """Factory for generating valid Farmer instances with Kenya-specific data.

    FK Dependencies: region_id -> regions
    AC #3: Kenya-specific names, phones, coordinates
    AC #4: Generated Farmer passes Pydantic validation
    """

    __model__ = Farmer
    _id_prefix: ClassVar[str] = "WM-"
    _entity_type: ClassVar[str] = "farmers"
    _id_counter: ClassVar[int] = 0

    @classmethod
    def id(cls) -> str:
        """Generate farmer ID."""
        return cls._next_id()

    @classmethod
    def grower_number(cls) -> str | None:
        """Generate grower number (optional)."""
        if random.random() > 0.3:  # 70% have grower number
            return KenyaProvider.grower_number()
        return None

    @classmethod
    def first_name(cls) -> str:
        """Generate Kenyan first name."""
        return KenyaProvider.first_name()

    @classmethod
    def last_name(cls) -> str:
        """Generate Kenyan last name."""
        return KenyaProvider.last_name()

    @classmethod
    def region_id(cls) -> str:
        """Get region_id from FK registry."""
        return cls.get_random_fk("regions")

    @classmethod
    def farm_location(cls) -> dict:
        """Generate Kenya tea region coordinates."""
        lat, lng, alt = KenyaProvider.kenya_coordinates(tea_region=True)
        return {
            "latitude": lat,
            "longitude": lng,
            "altitude_meters": alt,
        }

    @classmethod
    def contact(cls) -> dict:
        """Generate contact with Kenya phone number."""
        return {
            "phone": KenyaProvider.phone_number(),
            "email": "",
            "address": "",
        }

    @classmethod
    def farm_size_hectares(cls) -> float:
        """Generate realistic farm size.

        Distribution: 60% smallholder (<1ha), 35% medium (1-5ha), 5% estate (>5ha)
        """
        roll = random.random()
        if roll < 0.60:
            # Smallholder: 0.1 - 1.0 hectares
            return round(random.uniform(0.1, 0.99), 2)
        elif roll < 0.95:
            # Medium: 1.0 - 5.0 hectares
            return round(random.uniform(1.0, 5.0), 2)
        else:
            # Estate: 5.0 - 50.0 hectares
            return round(random.uniform(5.0, 50.0), 2)

    @classmethod
    def farm_scale(cls) -> FarmScale:
        """Generate farm scale based on typical distribution."""
        return random.choices(
            [FarmScale.SMALLHOLDER, FarmScale.MEDIUM, FarmScale.ESTATE],
            weights=[60, 35, 5],
        )[0]

    @classmethod
    def national_id(cls) -> str:
        """Generate Kenya national ID."""
        return KenyaProvider.national_id()

    @classmethod
    def registration_date(cls) -> datetime:
        """Generate registration date within last 2 years."""
        days_ago = random.randint(0, 730)
        return datetime.now(UTC) - dt.timedelta(days=days_ago)

    @classmethod
    def is_active(cls) -> bool:
        """Generate active status (mostly active)."""
        return random.random() > 0.05  # 95% active

    @classmethod
    def notification_channel(cls) -> NotificationChannel:
        """Generate notification channel preference."""
        return random.choices(
            [NotificationChannel.SMS, NotificationChannel.WHATSAPP],
            weights=[70, 30],
        )[0]

    @classmethod
    def interaction_pref(cls) -> InteractionPreference:
        """Generate interaction preference."""
        return random.choices(
            [InteractionPreference.TEXT, InteractionPreference.VOICE],
            weights=[80, 20],
        )[0]

    @classmethod
    def pref_lang(cls) -> PreferredLanguage:
        """Generate language preference."""
        return random.choices(
            [
                PreferredLanguage.SWAHILI,
                PreferredLanguage.KIKUYU,
                PreferredLanguage.LUO,
                PreferredLanguage.ENGLISH,
            ],
            weights=[60, 20, 10, 10],
        )[0]


class FarmerPerformanceFactory(BaseModelFactory[FarmerPerformance]):
    """Factory for generating valid FarmerPerformance instances.

    FK Dependencies: farmer_id -> farmers
    """

    __model__ = FarmerPerformance
    _entity_type: ClassVar[str] = "farmer_performance"
    _id_counter: ClassVar[int] = 0

    # Default grading model (can be overridden)
    DEFAULT_GRADING_MODEL_ID: ClassVar[str] = "tbk_kenya_tea_v1"
    DEFAULT_GRADING_MODEL_VERSION: ClassVar[str] = "1.0.0"

    @classmethod
    def farmer_id(cls) -> str:
        """Get farmer_id from FK registry."""
        return cls.get_random_fk("farmers")

    @classmethod
    def grading_model_id(cls) -> str:
        """Generate grading model ID."""
        return cls.DEFAULT_GRADING_MODEL_ID

    @classmethod
    def grading_model_version(cls) -> str:
        """Generate grading model version."""
        return cls.DEFAULT_GRADING_MODEL_VERSION

    @classmethod
    def farm_size_hectares(cls) -> float:
        """Generate farm size."""
        return round(random.uniform(0.1, 10.0), 2)

    @classmethod
    def farm_scale(cls) -> FarmScale:
        """Generate farm scale."""
        return random.choices(
            [FarmScale.SMALLHOLDER, FarmScale.MEDIUM, FarmScale.ESTATE],
            weights=[60, 35, 5],
        )[0]

    @classmethod
    def historical(cls) -> dict:
        """Generate historical metrics."""
        # Generate realistic grade distributions
        primary_30d = random.randint(50, 150)
        secondary_30d = random.randint(10, 50)
        total_30d = primary_30d + secondary_30d

        primary_pct_30d = round((primary_30d / total_30d) * 100, 1) if total_30d > 0 else 0.0

        return {
            "grade_distribution_30d": {"Primary": primary_30d, "Secondary": secondary_30d},
            "grade_distribution_90d": {"Primary": primary_30d * 3, "Secondary": secondary_30d * 3},
            "grade_distribution_year": {"Primary": primary_30d * 12, "Secondary": secondary_30d * 12},
            "attribute_distributions_30d": {
                "leaf_type": {
                    "bud": random.randint(5, 20),
                    "one_leaf_bud": random.randint(20, 50),
                    "two_leaves_bud": random.randint(30, 60),
                    "coarse_leaf": random.randint(5, 20),
                },
            },
            "attribute_distributions_90d": {},
            "attribute_distributions_year": {},
            "primary_percentage_30d": primary_pct_30d,
            "primary_percentage_90d": round(min(100, max(0, primary_pct_30d + random.uniform(-5, 5))), 1),
            "primary_percentage_year": round(min(100, max(0, primary_pct_30d + random.uniform(-10, 10))), 1),
            "total_kg_30d": round(random.uniform(50, 500), 1),
            "total_kg_90d": round(random.uniform(150, 1500), 1),
            "total_kg_year": round(random.uniform(600, 6000), 1),
            "yield_kg_per_hectare_30d": round(random.uniform(100, 500), 1),
            "yield_kg_per_hectare_90d": round(random.uniform(300, 1500), 1),
            "yield_kg_per_hectare_year": round(random.uniform(1200, 6000), 1),
            "improvement_trend": random.choice(["improving", "stable", "declining"]),
            "computed_at": datetime.now(UTC).isoformat(),
        }

    @classmethod
    def today(cls) -> dict:
        """Generate today's metrics."""
        deliveries = random.randint(0, 3)
        return {
            "deliveries": deliveries,
            "total_kg": round(random.uniform(0, 50) if deliveries > 0 else 0, 1),
            "grade_counts": {"Primary": deliveries} if deliveries > 0 else {},
            "attribute_counts": {},
            "last_delivery": datetime.now(UTC).isoformat() if deliveries > 0 else None,
            "metrics_date": dt.date.today().isoformat(),
        }
