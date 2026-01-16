"""Weather observation admin API schemas.

Provides response schemas for regional weather data (AC 9.2.5):
- WeatherObservation: Single day's weather data with alerts
- RegionWeatherResponse: List of observations with metadata
"""

import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class WeatherAlertType(str, Enum):
    """Types of weather alerts based on AC 9.2.5 thresholds."""

    HEAVY_RAIN = "heavy_rain"  # >10mm precipitation
    FROST_RISK = "frost_risk"  # <2°C minimum temperature
    HIGH_HUMIDITY = "high_humidity"  # >90% humidity
    DROUGHT = "drought"  # 0mm for 5+ consecutive days


class WeatherAlert(BaseModel):
    """Weather alert with type and impact description."""

    alert_type: WeatherAlertType = Field(description="Alert type")
    icon: str = Field(description="Alert icon emoji")
    impact: str = Field(description="Impact description")


class WeatherObservation(BaseModel):
    """Single day's weather observation with computed alerts.

    Implements AC 9.2.5 alert thresholds:
    - Heavy rain: >10mm precipitation
    - Frost risk: <2°C minimum temperature
    - High humidity: >90% humidity
    """

    date: dt.date = Field(description="Date of observation")
    temp_min: float = Field(description="Minimum temperature (°C)")
    temp_max: float = Field(description="Maximum temperature (°C)")
    precipitation_mm: float = Field(description="Total precipitation (mm)")
    humidity_avg: float = Field(description="Average humidity (%)")
    source: str = Field(description="Data source (e.g., 'open-meteo')")

    @computed_field
    @property
    def alerts(self) -> list[WeatherAlert]:
        """Compute weather alerts based on AC 9.2.5 thresholds."""
        alerts = []

        # Heavy rain: >10mm
        if self.precipitation_mm > 10:
            alerts.append(
                WeatherAlert(
                    alert_type=WeatherAlertType.HEAVY_RAIN,
                    icon="⚠️",
                    impact="May impact leaf quality 3-5 days later",
                )
            )

        # Frost risk: <2°C
        if self.temp_min < 2:
            alerts.append(
                WeatherAlert(
                    alert_type=WeatherAlertType.FROST_RISK,
                    icon="❄️",
                    impact="Potential frost damage to leaves",
                )
            )

        # High humidity: >90%
        if self.humidity_avg > 90:
            alerts.append(
                WeatherAlert(
                    alert_type=WeatherAlertType.HIGH_HUMIDITY,
                    icon="💧",
                    impact="Increased fungal disease risk",
                )
            )

        return alerts


class RegionWeatherResponse(BaseModel):
    """Response for region weather observations endpoint.

    Implements AC 9.2.5: Last 7 days of weather observations with alerts.
    """

    region_id: str = Field(description="Region ID")
    observations: list[WeatherObservation] = Field(
        description="Weather observations (most recent first)"
    )
    last_updated: dt.datetime | None = Field(
        default=None, description="Timestamp of most recent observation"
    )

    @classmethod
    def from_domain_models(
        cls,
        region_id: str,
        observations: list,  # list[RegionalWeather] from fp_common
    ) -> "RegionWeatherResponse":
        """Create response from domain models."""
        weather_obs = [
            WeatherObservation(
                date=obs.date,
                temp_min=obs.temp_min,
                temp_max=obs.temp_max,
                precipitation_mm=obs.precipitation_mm,
                humidity_avg=obs.humidity_avg,
                source=obs.source,
            )
            for obs in observations
        ]

        # Sort by date descending (most recent first)
        weather_obs.sort(key=lambda x: x.date, reverse=True)

        last_updated = None
        if observations:
            # Get the most recent created_at timestamp
            last_updated = max(obs.created_at for obs in observations)

        return cls(
            region_id=region_id,
            observations=weather_obs,
            last_updated=last_updated,
        )
