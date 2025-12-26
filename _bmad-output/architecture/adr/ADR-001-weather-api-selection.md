# ADR-001: Weather API Selection

**Status:** Accepted
**Date:** 2025-12-26
**Deciders:** Mary (Business Analyst), Winston (Architect)
**Related Stories:** 2.7 (Weather API Pull Mode), 5.5 (Weather Impact Analyzer)

## Context

The Farmer Power Platform requires weather data to correlate environmental conditions with tea quality issues. The Knowledge Model's Weather Impact Analyzer needs to identify patterns such as:

- Heavy rain 3-5 days before poor quality delivery
- Frost damage (temperatures < 2°C)
- Drought stress (> 5 days without rain)
- High humidity (> 90%) driving fungal risk

Weather correlation uses a 3-7 day lag window, meaning we need historical weather data (14 days lookback) rather than real-time data.

### Requirements

| Requirement | Value |
|-------------|-------|
| **Coverage** | Kenyan tea regions (Nandi, Kericho, Kisii highlands) |
| **Historical depth** | 14 days minimum lookback |
| **Data points** | Temperature (min/max), precipitation, humidity |
| **Pull frequency** | Daily (6 AM EAT via DAPR Jobs) |
| **Scale** | ~20 distinct weather regions |
| **Cost sensitivity** | High (smallholder farmer context) |

## Decision

**Selected: Open-Meteo API (free tier)**

Open-Meteo provides global weather data with no API key required and no usage costs.

## Alternatives Considered

| API | Cost | Rate Limits | Historical Data | Auth Complexity | Verdict |
|-----|------|-------------|-----------------|-----------------|---------|
| **Open-Meteo** | Free | 10,000/day | 30+ days | None | **Selected** |
| OpenWeatherMap | Free tier: 1,000/day | Restrictive | 5 days (free) | API key required | Rejected: limited history |
| Tomorrow.io | Free: 500/day | Very restrictive | Limited (free) | API key + account | Rejected: rate limits |
| Visual Crossing | Free: 1,000/day | Moderate | 15 days | API key required | Rejected: key management overhead |

### Why Open-Meteo

1. **Zero cost** - No API fees, critical for cost-sensitive agricultural platform
2. **No authentication** - No API key management, rotation, or secret storage
3. **Sufficient rate limits** - 10,000 requests/day vs our ~20 requests/day (500x headroom)
4. **Adequate resolution** - 0.1° grid (~11km) sufficient for regional weather correlation
5. **Historical depth** - 30+ days exceeds our 14-day requirement
6. **Proven stability** - Community reports 99.5%+ uptime

### Why Not Paid Alternatives

A paid API with SLA guarantees (e.g., Tomorrow.io $100/month) was considered but rejected because:

- Weather data is **non-critical-path** - diagnosis continues without it
- Missing weather attribution degrades value by ~10-15%, not system failure
- Factory managers receive weekly action plans where weather is one factor among many
- Cost savings benefit smallholder farmers directly

## Consequences

### Positive

- **Zero ongoing API costs** for weather data
- **Simplified operations** - no API keys to manage or rotate
- **Sufficient scale headroom** - 500x current needs
- **Adequate data quality** for regional correlation use case

### Negative

- **No formal SLA** - Open-Meteo is a free service with no contractual uptime guarantee
- **No usage dashboard** - Cannot track our API consumption on their side
- **Schema changes possible** - Free API may change format without notice

### Mitigations

| Risk | Mitigation |
|------|------------|
| API unavailability | 7-day local cache of weather data |
| Transient failures | 3 retries with exponential backoff |
| Extended outage | Graceful degradation - analyzer returns `weather_data_unavailable` flag |
| Ops awareness | Alert if 3 consecutive daily pulls fail |
| Schema changes | LLM extraction agent handles format variations |

## Technical Implementation Notes

1. **Timezone handling**: Open-Meteo returns data in requested timezone (Africa/Nairobi)
2. **Coordinate source**: Plantation Model MCP `list_regions()` provides lat/long per region
3. **Rate limiting**: Handle HTTP 429 gracefully with backoff
4. **Metrics**: Implement internal tracking since no provider dashboard available
5. **Data format**: Daily JSON arrays processed by `weather-extraction-agent`

### Humidity Data Resolution

**Original Issue:** The collection model architecture extracted `humidity_avg` but the API request parameters did not include humidity.

**Resolution (2025-12-26):** Added `relative_humidity_2m_mean` to the daily parameters in `collection-model-architecture.md`. This parameter is available in the Open-Meteo forecast API.

**Updated API parameters:**
```
temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,relative_humidity_2m_mean
```

This enables Story 5.5 (Weather Impact Analyzer) to perform fungal risk detection based on humidity levels (>90% triggers fungal risk diagnosis).

Sources:
- [Open-Meteo API Documentation](https://open-meteo.com/en/docs)

### Source Configuration

The full source configuration (from `collection-model-architecture.md`):

```yaml
source_id: weather-api
display_name: Weather API
description: Daily weather data per region from Open-Meteo

ingestion:
  mode: scheduled_pull
  provider: open-meteo
  schedule: "0 6 * * *"  # Daily 6 AM EAT
  request:
    base_url: https://api.open-meteo.com/v1/forecast
    auth_type: none
    parameters:
      latitude: "{region.center_lat}"
      longitude: "{region.center_lng}"
      daily: "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,relative_humidity_2m_mean"
      past_days: "7"
      timezone: "Africa/Nairobi"
    timeout_seconds: 30
  iteration:
    foreach: regions
    source_mcp: plantation_mcp
    source_tool: list_regions
    concurrency: 5
  retry:
    max_attempts: 3
    backoff: exponential

transformation:
  agent: weather-extraction-agent
  extract_fields:
    - region_id
    - date
    - temp_max
    - temp_min
    - precipitation_mm
    - humidity_avg
  link_field: region_id

storage:
  raw_container: weather-data-raw
  index_collection: weather_index
  ttl_days: 365
```

### API Call Pattern

```python
# Example Open-Meteo call for a Kenyan tea region
import httpx

async def fetch_weather(latitude: float, longitude: float, past_days: int = 7):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,relative_humidity_2m_mean",
        "past_days": past_days,
        "timezone": "Africa/Nairobi"
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

## Revisit Triggers

Re-evaluate this decision if:

1. **Predictive features added** - If we need weather forecasts for proactive alerts ("expect quality issues next week"), forecast reliability becomes critical and may require paid SLA
2. **Per-farmer precision required** - If business needs change to farm-plot-level weather (currently ruled out as no added value)
3. **Open-Meteo reliability degrades** - If observed uptime drops below 95% over a 30-day period
4. **Scale exceeds 5,000 regions** - Unlikely but would approach rate limits

## References

- [Open-Meteo API Documentation](https://open-meteo.com/en/docs)
- Story 2.7: Weather API Pull Mode
- Story 5.5: Weather Impact Analyzer
- Collection Model Architecture: Weather API Source section
