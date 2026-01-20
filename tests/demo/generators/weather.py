"""Weather model factories for generating valid RegionalWeather instances.

Story 0.8.3: Polyfactory Generator Framework
AC #1: Factory exists for RegionalWeather
AC #2: FK fields reference FK registry
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

from fp_common.models.regional_weather import RegionalWeather  # noqa: E402

from .base import BaseModelFactory  # noqa: E402


class RegionalWeatherFactory(BaseModelFactory[RegionalWeather]):
    """Factory for generating valid RegionalWeather instances.

    FK Dependencies: region_id -> regions
    """

    __model__ = RegionalWeather
    _entity_type: ClassVar[str] = "weather_observations"
    _id_counter: ClassVar[int] = 0

    # Kenya highland tea region typical weather ranges
    TEMP_MIN_RANGE: ClassVar[tuple[float, float]] = (10.0, 18.0)  # °C
    TEMP_MAX_RANGE: ClassVar[tuple[float, float]] = (20.0, 28.0)  # °C
    PRECIPITATION_RANGE: ClassVar[tuple[float, float]] = (0.0, 50.0)  # mm
    HUMIDITY_RANGE: ClassVar[tuple[float, float]] = (60.0, 95.0)  # %

    @classmethod
    def region_id(cls) -> str:
        """Get region_id from FK registry."""
        return cls.get_random_fk("regions")

    @classmethod
    def date(cls) -> dt.date:
        """Generate observation date (within last 30 days)."""
        days_ago = random.randint(0, 30)
        return dt.date.today() - dt.timedelta(days=days_ago)

    @classmethod
    def temp_min(cls) -> float:
        """Generate minimum temperature."""
        return round(random.uniform(*cls.TEMP_MIN_RANGE), 1)

    @classmethod
    def temp_max(cls) -> float:
        """Generate maximum temperature."""
        return round(random.uniform(*cls.TEMP_MAX_RANGE), 1)

    @classmethod
    def precipitation_mm(cls) -> float:
        """Generate precipitation amount.

        Distribution: 60% dry (0mm), 30% light (0.1-10mm), 10% heavy (10-50mm)
        """
        roll = random.random()
        if roll < 0.60:
            return 0.0
        elif roll < 0.90:
            return round(random.uniform(0.1, 10.0), 1)
        else:
            return round(random.uniform(10.0, 50.0), 1)

    @classmethod
    def humidity_avg(cls) -> float:
        """Generate average humidity."""
        return round(random.uniform(*cls.HUMIDITY_RANGE), 1)

    @classmethod
    def source(cls) -> str:
        """Generate weather data source."""
        return "open-meteo"

    @classmethod
    def build_for_region_and_dates(
        cls,
        region_id: str,
        start_date: dt.date,
        num_days: int = 7,
    ) -> list[RegionalWeather]:
        """Build weather observations for a specific region over multiple days.

        Args:
            region_id: Region to generate weather for.
            start_date: First date of observations.
            num_days: Number of consecutive days to generate.

        Returns:
            List of RegionalWeather instances.
        """
        observations = []
        for day_offset in range(num_days):
            observation_date = start_date + dt.timedelta(days=day_offset)

            # Generate realistic temperature pair (min < max)
            temp_min = round(random.uniform(*cls.TEMP_MIN_RANGE), 1)
            temp_max = round(random.uniform(max(temp_min + 5, cls.TEMP_MAX_RANGE[0]), cls.TEMP_MAX_RANGE[1]), 1)

            observation = RegionalWeather(
                region_id=region_id,
                date=observation_date,
                temp_min=temp_min,
                temp_max=temp_max,
                precipitation_mm=cls.precipitation_mm(),
                humidity_avg=cls.humidity_avg(),
                source=cls.source(),
                created_at=datetime.now(UTC),
            )
            observations.append(observation)

        return observations
