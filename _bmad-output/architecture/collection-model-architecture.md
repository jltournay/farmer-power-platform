# Collection Model Architecture

## Overview

The Collection Model is the **data gateway** for the Farmer Power Cloud Platform. It collects data from external sources using two ingestion modes and processes all data through a unified pipeline before making it available to downstream consumers.

**Core Responsibility:** Collect, validate, transform, link, store, and serve documents.

**Does NOT:** Generate action plans, make business decisions, or verify farmer existence.

## Ingestion Modes

The platform supports two ingestion patterns, designed for the realities of factory and field environments where network connectivity is unreliable:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION MODES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BLOB_TRIGGER (File-Based Push)                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  ┌──────────────┐    batch & upload    ┌──────────────────────────┐   │ │
│  │  │ QC Analyzer  │ ──────────────────▶  │ Azure Blob Storage       │   │ │
│  │  │ Mobile App   │    (when connected)  │ (landing containers)     │   │ │
│  │  └──────────────┘                      └────────────┬─────────────┘   │ │
│  │                                                     │                  │ │
│  │                                          Event Grid │                  │ │
│  │                                                     ▼                  │ │
│  │                                        ┌──────────────────────────┐   │ │
│  │                                        │ Collection Model         │   │ │
│  │                                        │ (processes uploaded files)│   │ │
│  │                                        └──────────────────────────┘   │ │
│  │                                                                        │ │
│  │  Characteristics:                                                      │ │
│  │  • Source batches data locally, uploads when connectivity available   │ │
│  │  • Resilient to network interruptions                                 │ │
│  │  • Near real-time via Azure Event Grid triggers                       │ │
│  │  • Supports ZIP archives with manifests and images                    │ │
│  │                                                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  SCHEDULED_PULL (API Polling)                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  ┌──────────────────────┐    scheduled     ┌──────────────────────┐   │ │
│  │  │ Collection Model     │ ────────────────▶│ Weather API          │   │ │
│  │  │ (DAPR Job trigger)   │    API request   │ Market Prices API    │   │ │
│  │  │                      │◀──────────────── │                      │   │ │
│  │  └──────────────────────┘    response      └──────────────────────┘   │ │
│  │                                                                        │ │
│  │  Characteristics:                                                      │ │
│  │  • Platform initiates data request on schedule                        │ │
│  │  • DAPR Jobs handle scheduling (cron expressions)                     │ │
│  │  • Can iterate over entities (e.g., pull weather per region)          │ │
│  │  • Built-in retry with exponential backoff                            │ │
│  │                                                                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why BLOB_TRIGGER Instead of Webhooks

Factory and field environments have **unreliable network connectivity**. HTTP webhooks require:
- Stable connection during request/response
- Immediate acknowledgment
- Retry logic on the source side

**BLOB_TRIGGER** is more resilient:
- Sources batch data locally
- Upload when connectivity is available
- Azure handles durability and delivery guarantees
- Collection Model processes asynchronously

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COLLECTION MODEL ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BLOB_TRIGGER SOURCES                      SCHEDULED_PULL SOURCES           │
│  ┌─────────────────────┐                  ┌─────────────────────┐          │
│  │ QC Analyzer (ZIP)   │──┐            ┌──│ Weather API         │          │
│  │ Mobile App (JSON)   │──┼─▶ Blob ──▶ │  │ Market Prices       │          │
│  └─────────────────────┘  │  Storage   │  └─────────────────────┘          │
│                           │            │            ▲                       │
│            Event Grid ◀───┘            │            │ DAPR Jobs             │
│                   │                    │            │ (scheduled)           │
│                   ▼                    │            │                       │
│  ┌─────────────────────────────────────┴────────────┴─────────────────────┐│
│  │                        UNIFIED INGESTION PIPELINE                       ││
│  │                                                                         ││
│  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐    ││
│  │  │  Extract   │   │  Schema    │   │    LLM     │   │   Store    │    ││
│  │  │  Payload   │──▶│  Validate  │──▶│  Extract   │──▶│  Document  │    ││
│  │  │            │   │            │   │ + Validate │   │            │    ││
│  │  └────────────┘   └────────────┘   └────────────┘   └────────────┘    ││
│  │       │                                                    │           ││
│  │  (ZIP: unzip,                                         (Blob + Mongo)   ││
│  │   extract manifest,                                        │           ││
│  │   store images)                                            ▼           ││
│  │                                                    ┌────────────┐      ││
│  │                                                    │   Emit     │      ││
│  │                                                    │   Event    │      ││
│  │                                                    └────────────┘      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                         │                                   │
│              ┌──────────────────────────┼──────────────────────────┐       │
│              ▼                          ▼                          ▼       │
│        ┌──────────┐              ┌──────────┐              ┌──────────┐   │
│        │  Query   │              │  Search  │              │   MCP    │   │
│        │   API    │              │   API    │              │  Server  │   │
│        └──────────┘              └──────────┘              └──────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Phase 1 Data Sources

### Source Registry

| Source | Ingestion Mode | Format | Trigger | Status |
|--------|----------------|--------|---------|--------|
| **QC Analyzer - Result** | BLOB_TRIGGER | JSON (bag summary) | Event Grid | Phase 1 |
| **QC Analyzer - Exceptions** | BLOB_TRIGGER | ZIP (secondary images) | Event Grid | Phase 1 |
| **Mobile App** | BLOB_TRIGGER | JSON (single file) | Event Grid | Phase 1 |
| **Weather API** | SCHEDULED_PULL | API response | DAPR Job (daily 6 AM) | Phase 1 |
| **Market Prices** | SCHEDULED_PULL | API response | DAPR Job (weekly Monday) | Phase 1 |
| **Factory POS** | BLOB_TRIGGER | TBD | Event Grid | **Deferred** |

> **Note:** Factory POS is deferred because each factory has different systems. A standardized export format will be defined in a future phase.

### QC Analyzer Sources

The QC Analyzer is a Starfish machine at factories that grades tea leaf quality using computer vision. It produces **two separate data streams**:

| Stream | Content | Format | Purpose |
|--------|---------|--------|---------|
| **Bag Quality Result** | Aggregated grading summary | JSON | Business metrics, farmer quality tracking |
| **Secondary Leaf Images** | All secondary-grade leaf images | ZIP (images + manifest) | Knowledge Model analysis to understand quality issues |

> **Field Mapping:** `plantation_id` is equivalent to `farmer_id` in the platform.

---

#### Stream 1: Bag Quality Result (JSON)

Complete grading summary for each bag - no images, lightweight upload.

**Upload Path:** `results/{plantation_id}/{crop}/{market}/{batch_id}.json`

**JSON Schema:**
```json
{
  "plantation_id": "WM-4521",
  "source_id": "qc_analyzer_result",
  "batch_id": "batch-2025-12-26-001",

  "factory_id": "KEN-FAC-001",
  "collection_point_id": "nyeri-cp-001",

  "grading_model_id": "tbk_kenya_tea_v1",
  "grading_model_version": "1.0.0",

  "batch_timestamp": "2025-12-26T08:32:15Z",
  "crop_name": "tea",
  "market_name": "mombasa",

  "bag_summary": {
    "total_leaves": 150,
    "primary_count": 120,
    "secondary_count": 30,
    "primary_percentage": 80.0,
    "secondary_percentage": 20.0,
    "leaf_type_distribution": {
      "bud": 15,
      "one_leaf_bud": 45,
      "two_leaves_bud": 50,
      "three_plus_leaves_bud": 10,
      "single_soft_leaf": 10,
      "coarse_leaf": 15,
      "banji": 5
    },
    "coarse_subtype_distribution": {
      "double_luck": 3,
      "maintenance_leaf": 7,
      "hard_leaf": 5
    },
    "banji_distribution": {
      "soft": 3,
      "hard": 2
    }
  }
}
```

**Source Configuration:**
```yaml
source_id: qc-analyzer-result
display_name: QC Analyzer - Bag Result
description: Aggregated quality grading results from Starfish QC machines

ingestion:
  mode: blob_trigger
  landing_container: qc-analyzer-landing
  path_pattern:
    pattern: "results/{plantation_id}/{crop}/{market}/{batch_id}.json"
    extract_fields: [plantation_id, crop, market, batch_id]
  file_pattern: "*.json"
  file_format: json
  trigger_mechanism: event_grid
  processed_file_config:
    action: archive
    archive_container: qc-archive
    archive_ttl_days: 365

validation:
  schema_name: qc-bag-result.json
  strict: true

transformation:
  agent: qc-result-extraction-agent
  extract_fields:
    - plantation_id
    - factory_id
    - collection_point_id
    - grading_model_id
    - grading_model_version
    - batch_timestamp
    - bag_summary
  link_field: plantation_id
  field_mappings:
    plantation_id: farmer_id

storage:
  raw_container: quality-results-raw
  index_collection: quality_results_index
  ttl_days: 730
```

---

#### Stream 2: Secondary Leaf Images (ZIP)

Images of all secondary-grade leaves with their classification metadata. The Knowledge Model uses these images to understand quality issues and diagnose why a farmer's tea is failing quality standards.

**Upload Path:** `exceptions/{plantation_id}/{crop}/{market}/{batch_id}.zip`

**ZIP Structure:**
```
{batch_id}.zip
├── manifest.json         # Metadata linking to batch result
└── images/
    ├── img_00001.jpg     # Secondary-grade leaf images only
    ├── img_00002.jpg
    └── ...
```

**manifest.json Schema:**
```json
{
  "plantation_id": "WM-4521",
  "source_id": "qc_analyzer_exceptions",
  "batch_id": "batch-2025-12-26-001",
  "batch_result_ref": "results/WM-4521/tea/mombasa/batch-2025-12-26-001.json",

  "factory_id": "KEN-FAC-001",
  "grading_model_id": "tbk_kenya_tea_v1",
  "grading_model_version": "1.0.0",

  "batch_timestamp": "2025-12-26T08:32:15Z",
  "exception_count": 30,

  "exception_images": [
    {
      "file_uri": "images/img_00001.jpg",
      "mime_type": "image/jpeg",
      "classification": {
        "quality_grade": "secondary",
        "confidence": 0.91,
        "leaf_type": "coarse_leaf",
        "coarse_subtype": "hard_leaf",
        "banji_hardness": null
      }
    },
    {
      "file_uri": "images/img_00002.jpg",
      "mime_type": "image/jpeg",
      "classification": {
        "quality_grade": "secondary",
        "confidence": 0.87,
        "leaf_type": "three_plus_leaves_bud",
        "coarse_subtype": null,
        "banji_hardness": null
      }
    }
  ]
}
```

**Source Configuration:**
```yaml
source_id: qc-analyzer-exceptions
display_name: QC Analyzer - Secondary Leaf Images
description: Images of secondary-grade leaves for audit and retraining

ingestion:
  mode: blob_trigger
  landing_container: qc-analyzer-landing
  path_pattern:
    pattern: "exceptions/{plantation_id}/{crop}/{market}/{batch_id}.zip"
    extract_fields: [plantation_id, crop, market, batch_id]
  file_pattern: "*.zip"
  file_format: zip
  zip_config:
    manifest_file: manifest.json
    images_folder: images
    extract_images: true
    image_storage_container: qc-exception-images
  trigger_mechanism: event_grid
  processed_file_config:
    action: archive
    archive_container: qc-archive
    archive_ttl_days: 730

validation:
  schema_name: qc-exceptions-manifest.json
  strict: true

transformation:
  agent: qc-exceptions-extraction-agent
  extract_fields:
    - plantation_id
    - factory_id
    - batch_id
    - batch_result_ref
    - exception_count
    - exception_images
  link_field: plantation_id
  field_mappings:
    plantation_id: farmer_id

storage:
  raw_container: quality-exceptions-raw
  index_collection: quality_exceptions_index
  ttl_days: 730
```

### Mobile App Source

The Mobile App is used by field officers to register new farmers. Each registration creates a single JSON file.

**Upload Path:** `registrations/{factory_id}/{date}/{registration_id}.json`

**JSON Schema:**
```json
{
  "registration_id": "REG-2025-001234",
  "farmer_name": "John Kamau",
  "phone_number": "+254712345678",
  "national_id": "12345678",
  "factory_id": "KEN-FAC-001",
  "collection_point_id": "nyeri-cp-001",
  "location_gps": {
    "latitude": -0.4167,
    "longitude": 36.9500
  },
  "registered_by": "FO-001",
  "registered_at": "2025-12-26T10:00:00Z"
}
```

**Source Configuration:**
```yaml
source_id: mobile-app
display_name: Mobile App
description: Farmer registration from field officers

ingestion:
  mode: blob_trigger
  landing_container: mobile-app-landing
  path_prefix: registrations/
  path_pattern:
    pattern: "registrations/{factory_id}/{date}/{registration_id}.json"
    extract_fields: [factory_id, date, registration_id]
  file_pattern: "*.json"
  file_format: json
  trigger_mechanism: event_grid
  processed_file_config:
    action: move
    processed_folder: processed

validation:
  schema_name: farmer-registration.json
  strict: true

transformation:
  agent: registration-extraction-agent
  extract_fields:
    - farmer_name
    - phone_number
    - national_id
    - factory_id
    - collection_point_id
    - location_gps
    - registered_by
    - registered_at
  link_field: phone_number

storage:
  raw_container: registrations-raw
  index_collection: farmer_registrations_index
  ttl_days: null
```

### Weather API Source

Daily weather data pulled from Open-Meteo for each region.

**Source Configuration:**
```yaml
source_id: weather-api
display_name: Weather API
description: Daily weather data per region from Open-Meteo

ingestion:
  mode: scheduled_pull
  provider: open-meteo
  schedule: "0 6 * * *"
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

### Market Prices Source

Weekly tea auction prices from Mombasa.

**Source Configuration:**
```yaml
source_id: market-prices
display_name: Market Prices
description: Weekly tea auction prices from Mombasa

ingestion:
  mode: scheduled_pull
  provider: mombasa-auction
  schedule: "0 8 * * 1"
  request:
    base_url: https://market-api.example.com/v1/prices
    auth_type: api_key
    auth_secret_key: market-api-key
    parameters:
      commodity: "tea"
      market: "mombasa_auction"
      date_range: "last_7_days"
    timeout_seconds: 30
  retry:
    max_attempts: 3
    backoff: exponential

transformation:
  agent: market-extraction-agent
  extract_fields:
    - commodity
    - market
    - price_date
    - price_per_kg
    - volume_traded
    - grade_breakdown

storage:
  raw_container: market-data-raw
  index_collection: market_prices_index
  ttl_days: 365
```

## Source Configuration Management

Source configurations use a **hybrid model**: YAML files in Git for version control, deployed to MongoDB for runtime access.

### Repository Structure

```
farmer-power-platform/
├── config/
│   └── source-configs/
│       ├── qc-analyzer-result.yaml
│       ├── qc-analyzer-exceptions.yaml
│       ├── mobile-app.yaml
│       ├── weather-api.yaml
│       └── market-prices.yaml
├── scripts/
│   └── source-config/
│       ├── __init__.py
│       ├── cli.py              # CLI entry point
│       ├── deployer.py         # Deployment logic
│       ├── validator.py        # Schema validation
│       └── models.py           # Pydantic models
└── .github/
    └── workflows/
        └── deploy-source-configs.yaml
```

### CLI Tool: `fp-source-config`

```bash
# Validate all source configs (no deployment)
fp-source-config validate

# Validate specific config
fp-source-config validate --file config/source-configs/qc-analyzer-result.yaml

# Deploy to environment
fp-source-config deploy --env dev
fp-source-config deploy --env staging
fp-source-config deploy --env prod

# Deploy specific config only
fp-source-config deploy --env dev --file qc-analyzer-result.yaml

# List deployed configs in environment
fp-source-config list --env dev

# Compare local vs deployed (diff)
fp-source-config diff --env dev

# Dry-run deployment (show what would change)
fp-source-config deploy --env dev --dry-run
```

### CLI Implementation (Typer)

The CLI is built with **Typer** for modern, type-hint based command-line interfaces.

**Installation:**
```bash
# Install as editable package
pip install -e "./scripts/source-config"

# Or with uv (recommended)
uv pip install -e "./scripts/source-config"
```

**Package Structure:**
```
scripts/source-config/
├── pyproject.toml
├── src/
│   └── fp_source_config/
│       ├── __init__.py
│       ├── cli.py           # Typer CLI entry point
│       ├── deployer.py      # Deployment logic
│       ├── validator.py     # Pydantic validation
│       ├── models.py        # Source config Pydantic models
│       └── settings.py      # Environment settings
└── tests/
    └── test_validator.py
```

**pyproject.toml:**
```toml
[project]
name = "fp-source-config"
version = "0.1.0"
description = "Farmer Power Source Configuration CLI"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.12.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "motor>=3.3.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]

[project.scripts]
fp-source-config = "fp_source_config.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**CLI Implementation:**
```python
# scripts/source-config/src/fp_source_config/cli.py
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from .deployer import SourceConfigDeployer
from .validator import validate_source_configs

app = typer.Typer(
    name="fp-source-config",
    help="Farmer Power Source Configuration CLI",
    no_args_is_help=True,
)
console = Console()


class Environment(str, Enum):
    dev = "dev"
    staging = "staging"
    prod = "prod"


CONFIGS_PATH = Path("config/source-configs")


@app.command()
def validate(
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Specific file to validate"),
    ] = None,
):
    """Validate source configuration YAML files."""
    if file:
        files = [CONFIGS_PATH / file] if not file.is_absolute() else [file]
    else:
        files = list(CONFIGS_PATH.glob("*.yaml"))

    if not files:
        console.print("[yellow]No config files found[/yellow]")
        raise typer.Exit(1)

    errors = validate_source_configs(files)

    if errors:
        for error in errors:
            console.print(f"[red]✗[/red] {error.file}: {error.message}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Validated {len(files)} source config(s)")


@app.command()
def deploy(
    env: Annotated[Environment, typer.Option("--env", "-e", help="Target environment")],
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Specific file to deploy"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show changes without deploying"),
    ] = False,
):
    """Deploy source configurations to MongoDB."""
    if file:
        files = [CONFIGS_PATH / file] if not file.is_absolute() else [file]
    else:
        files = list(CONFIGS_PATH.glob("*.yaml"))

    # Validate first
    errors = validate_source_configs(files)
    if errors:
        for error in errors:
            console.print(f"[red]✗[/red] {error.file}: {error.message}")
        raise typer.Exit(1)

    # Deploy
    deployer = SourceConfigDeployer(environment=env.value)
    results = deployer.deploy(files, dry_run=dry_run)

    for result in results:
        if result.action == "create":
            icon = "[green]➕[/green]"
            status = "would create" if dry_run else "created"
        elif result.action == "update":
            icon = "[blue]🔄[/blue]"
            status = "would update" if dry_run else "updated"
        else:
            icon = "[dim]✓[/dim]"
            status = "unchanged"

        console.print(f"{icon} {result.source_id}: {status}")

    if not dry_run:
        console.print(f"\n[green]✓[/green] Deployed {len(results)} config(s) to {env.value}")


@app.command()
def list(
    env: Annotated[Environment, typer.Option("--env", "-e", help="Target environment")],
):
    """List deployed source configurations."""
    deployer = SourceConfigDeployer(environment=env.value)
    configs = deployer.list_configs()

    table = Table(title=f"Source Configs ({env.value})")
    table.add_column("Source ID", style="cyan")
    table.add_column("Display Name")
    table.add_column("Version", justify="right")
    table.add_column("Deployed At")
    table.add_column("Enabled", justify="center")

    for config in configs:
        table.add_row(
            config.source_id,
            config.display_name,
            str(config.version),
            config.deployed_at.strftime("%Y-%m-%d %H:%M"),
            "✓" if config.enabled else "✗",
        )

    console.print(table)


@app.command()
def diff(
    env: Annotated[Environment, typer.Option("--env", "-e", help="Target environment")],
    source: Annotated[
        Optional[str],
        typer.Option("--source", "-s", help="Specific source to diff"),
    ] = None,
):
    """Compare local configs vs deployed configs."""
    deployer = SourceConfigDeployer(environment=env.value)
    diffs = deployer.diff(source_id=source)

    if not diffs:
        console.print("[green]✓[/green] All configs in sync")
        return

    for d in diffs:
        console.print(f"\n[bold]{d.source_id}[/bold]")
        for change in d.changes:
            console.print(f"  {change.path}: [red]{change.old}[/red] → [green]{change.new}[/green]")


@app.command()
def history(
    env: Annotated[Environment, typer.Option("--env", "-e", help="Target environment")],
    source: Annotated[str, typer.Option("--source", "-s", help="Source ID")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Number of versions")] = 10,
):
    """View deployment history for a source."""
    deployer = SourceConfigDeployer(environment=env.value)
    versions = deployer.get_history(source_id=source, limit=limit)

    table = Table(title=f"History: {source} ({env.value})")
    table.add_column("Version", justify="right")
    table.add_column("Deployed At")
    table.add_column("Deployed By")
    table.add_column("Git SHA")

    for v in versions:
        table.add_row(
            str(v.version),
            v.deployed_at.strftime("%Y-%m-%d %H:%M"),
            v.deployed_by,
            v.git_sha[:8] if v.git_sha else "-",
        )

    console.print(table)


@app.command()
def rollback(
    env: Annotated[Environment, typer.Option("--env", "-e", help="Target environment")],
    source: Annotated[str, typer.Option("--source", "-s", help="Source ID")],
    version: Annotated[int, typer.Option("--version", "-v", help="Version to rollback to")],
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation"),
    ] = False,
):
    """Rollback a source config to a previous version."""
    if env == Environment.prod and not confirm:
        typer.confirm(
            f"Rollback {source} to version {version} in PRODUCTION?",
            abort=True,
        )

    deployer = SourceConfigDeployer(environment=env.value)
    result = deployer.rollback(source_id=source, version=version)

    if result.success:
        console.print(f"[green]✓[/green] Rolled back {source} to version {version}")
    else:
        console.print(f"[red]✗[/red] Rollback failed: {result.error}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
```

### Environment Configuration

```python
# scripts/source-config/deployer.py
from pydantic_settings import BaseSettings

class DeployerSettings(BaseSettings):
    """Environment-specific MongoDB connection."""

    model_config = {"env_prefix": "FP_"}

    # Loaded from environment or .env file
    mongodb_uri: str
    mongodb_database: str = "farmer_power"

    @classmethod
    def for_environment(cls, env: str) -> "DeployerSettings":
        """Load settings for specific environment."""
        env_file = Path(f".env.{env}")
        return cls(_env_file=env_file if env_file.exists() else None)

# Environment files
# .env.dev:      FP_MONGODB_URI=mongodb://localhost:27017
# .env.staging:  FP_MONGODB_URI=mongodb+srv://staging.xxx.mongodb.net
# .env.prod:     FP_MONGODB_URI=mongodb+srv://prod.xxx.mongodb.net
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy-source-configs.yaml
name: Deploy Source Configs

on:
  push:
    branches: [main, staging]
    paths:
      - 'config/source-configs/**'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options: [dev, staging, prod]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e "./scripts/source-config[dev]"

      - name: Validate configs
        run: fp-source-config validate

  deploy:
    needs: validate
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || (github.ref == 'refs/heads/main' && 'prod') || 'staging' }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -e "./scripts/source-config"

      - name: Deploy to ${{ env.DEPLOY_ENV }}
        env:
          FP_MONGODB_URI: ${{ secrets.MONGODB_URI }}
          DEPLOY_ENV: ${{ github.event.inputs.environment || (github.ref == 'refs/heads/main' && 'prod') || 'staging' }}
        run: |
          fp-source-config deploy --env $DEPLOY_ENV
```

### Deployment Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SOURCE CONFIG DEPLOYMENT FLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Developer Workflow                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  1. Edit YAML ──▶ 2. Local validate ──▶ 3. Open PR ──▶ 4. Merge     │  │
│  │                                                                       │  │
│  │  $ vim config/source-configs/qc-analyzer-result.yaml                 │  │
│  │  $ fp-source-config validate                                         │  │
│  │  $ git commit -m "Update QC analyzer polling interval"               │  │
│  │  $ gh pr create                                                       │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                         │                                   │
│                                         ▼                                   │
│  CI/CD Pipeline (GitHub Actions)                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  On PR:                                                               │  │
│  │  ┌─────────────┐                                                     │  │
│  │  │  Validate   │ ── fail ──▶ Block merge                             │  │
│  │  │  YAML +     │                                                     │  │
│  │  │  Pydantic   │ ── pass ──▶ Allow merge                             │  │
│  │  └─────────────┘                                                     │  │
│  │                                                                       │  │
│  │  On Merge to main:                                                    │  │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                │  │
│  │  │  Validate   │──▶│   Deploy    │──▶│   Verify    │                │  │
│  │  │             │   │  to prod    │   │  (list)     │                │  │
│  │  └─────────────┘   └─────────────┘   └─────────────┘                │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                         │                                   │
│                                         ▼                                   │
│  MongoDB (per environment)                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  source_configs collection                                           │  │
│  │  ┌───────────────────────────────────────────────────────────────┐  │  │
│  │  │ {                                                              │  │  │
│  │  │   "_id": "qc-analyzer-result",                                │  │  │
│  │  │   "source_id": "qc-analyzer-result",                          │  │  │
│  │  │   "display_name": "QC Analyzer - Bag Result",                 │  │  │
│  │  │   "config": { ... full config ... },                          │  │  │
│  │  │   "version": 3,                                               │  │  │
│  │  │   "deployed_at": "2025-12-26T10:00:00Z",                      │  │  │
│  │  │   "deployed_by": "github-actions",                            │  │  │
│  │  │   "git_sha": "abc123"                                         │  │  │
│  │  │ }                                                              │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                         │                                   │
│  Application Runtime                    │                                   │
│  ┌──────────────────────────────────────┼───────────────────────────────┐  │
│  │                                      ▼                                │  │
│  │                         ┌─────────────────────┐                      │  │
│  │                         │ SourceConfigService │                      │  │
│  │                         │                     │                      │  │
│  │                         │ • 5-min TTL cache   │                      │  │
│  │                         │ • Async operations  │                      │  │
│  │                         │ • Type-safe queries │                      │  │
│  │                         └─────────────────────┘                      │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### MongoDB Document Schema

```python
# Stored in source_configs collection
{
    "_id": "qc-analyzer-result",           # Same as source_id
    "source_id": "qc-analyzer-result",
    "display_name": "QC Analyzer - Bag Result",
    "enabled": True,
    "config": {
        "ingestion": { ... },
        "validation": { ... },
        "transformation": { ... },
        "storage": { ... }
    },

    # Deployment metadata
    "version": 3,                           # Incremented on each deploy
    "deployed_at": "2025-12-26T10:00:00Z",
    "deployed_by": "github-actions",        # Or "jltournay" for manual
    "git_sha": "abc123def456",              # Commit that deployed this
    "git_file": "config/source-configs/qc-analyzer-result.yaml",

    # Change tracking
    "previous_version": { ... },            # Snapshot for rollback
    "created_at": "2025-12-01T08:00:00Z"
}
```

### Rollback Support

```bash
# View deployment history
fp-source-config history --env prod --source qc-analyzer-result

# Rollback to previous version
fp-source-config rollback --env prod --source qc-analyzer-result --version 2

# Rollback all configs to specific git commit
fp-source-config rollback --env prod --git-sha abc123
```

### Rationale

| Decision | Choice | Why |
|----------|--------|-----|
| **Same repo** | `config/source-configs/` | Single source of truth, atomic commits with code |
| **CLI tool** | `fp-source-config` | Local validation, manual deploys, CI integration |
| **Environment targeting** | `--env dev/staging/prod` | Clear separation, different MongoDB per env |
| **Version tracking** | Increment + git_sha | Audit trail, easy rollback |
| **5-min cache TTL** | Runtime service | Hot-reload without restart |

## Ingestion Pipeline

All sources flow through a unified pipeline regardless of ingestion mode:

### Pipeline Steps

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INGESTION PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Step 1: EXTRACT PAYLOAD                                              │   │
│  │                                                                      │   │
│  │ • BLOB_TRIGGER: Download blob, unzip if needed, parse manifest      │   │
│  │ • SCHEDULED_PULL: Make HTTP request, receive response               │   │
│  │ • Extract metadata from path/headers                                │   │
│  │ • Store images separately if applicable                             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                         │                                   │
│                                         ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Step 2: SCHEMA VALIDATION                                            │   │
│  │                                                                      │   │
│  │ • JSON Schema validation against source-specific schema             │   │
│  │ • Fast, deterministic check                                         │   │
│  │ • Strict mode: reject on failure                                    │   │
│  │ • Lenient mode: warn and continue                                   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                         │                                   │
│                                         ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Step 3: LLM EXTRACTION + VALIDATION                                  │   │
│  │                                                                      │   │
│  │ • Extract configured fields from payload                            │   │
│  │ • Apply field mappings (e.g., plantation_id → farmer_id)           │   │
│  │ • Semantic validation (cross-field consistency)                     │   │
│  │ • Handle format variations without code changes                     │   │
│  │ • Output: extracted_fields, confidence, warnings                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                         │                                   │
│                                         ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Step 4: STORE DOCUMENT                                               │   │
│  │                                                                      │   │
│  │ • Raw payload → Azure Blob Storage (immutable)                      │   │
│  │ • Index document → MongoDB (queryable)                              │   │
│  │ • Extracted images → Separate blob container                        │   │
│  │ • Include: farmer linkage, timestamps, confidence, warnings         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                         │                                   │
│                                         ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Step 5: EMIT EVENT                                                   │   │
│  │                                                                      │   │
│  │ • Publish to DAPR Pub/Sub: collection-events topic                  │   │
│  │ • Generic: collection.document.stored                               │   │
│  │ • Source-specific: collection.quality_event.received, etc.          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### LLM Extraction Output

```python
ExtractionResult(
    extracted_fields: dict,        # Normalized field values
    validation_warnings: list,     # Semantic issues found (non-blocking)
    validation_passed: bool,       # Overall semantic assessment
    confidence: float,             # LLM confidence score (0.0-1.0)
    link_value: str | None         # Value of link_field for entity linkage
)
```

## Trigger Mechanisms

### Event Grid (BLOB_TRIGGER)

Azure Event Grid triggers pipeline execution when new files are uploaded:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVENT GRID TRIGGER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Azure Blob Storage                  Azure Event Grid                       │
│  ┌──────────────────┐               ┌──────────────────┐                   │
│  │ qc-analyzer-     │  BlobCreated  │ System Topic     │                   │
│  │   landing/       │ ─────────────▶│                  │                   │
│  │ mobile-app-      │               │ Subscription:    │                   │
│  │   landing/       │               │ collection-model │                   │
│  └──────────────────┘               └────────┬─────────┘                   │
│                                              │                              │
│                                              │ POST /api/v1/triggers/       │
│                                              │      event-grid              │
│                                              ▼                              │
│                                     ┌──────────────────┐                   │
│                                     │ EventGridTrigger │                   │
│                                     │                  │                   │
│                                     │ • Validate sub   │                   │
│                                     │ • Parse blob URL │                   │
│                                     │ • Route to source│                   │
│                                     │ • Process async  │                   │
│                                     └────────┬─────────┘                   │
│                                              │                              │
│                                              ▼                              │
│                                     ┌──────────────────┐                   │
│                                     │BlobTriggerHandler│                   │
│                                     │                  │                   │
│                                     │ • Download blob  │                   │
│                                     │ • Extract ZIP    │                   │
│                                     │ • Run pipeline   │                   │
│                                     │ • Move processed │                   │
│                                     └──────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### DAPR Jobs (SCHEDULED_PULL)

DAPR Jobs trigger scheduled API pulls:

```yaml
# deploy/kubernetes/base/dapr/jobs/weather-pull.yaml
apiVersion: dapr.io/v1alpha1
kind: Job
metadata:
  name: pull-weather-api
spec:
  schedule: "0 6 * * *"
  job:
    target:
      type: Service
      name: collection-model
      path: /api/v1/triggers/job/pull-weather-api
      method: POST
```

## Domain Events

Events emitted after successful ingestion:

| Event | Trigger | Payload |
|-------|---------|---------|
| `collection.document.stored` | Any document stored | document_id, source_id, link_value |
| `collection.quality_result.received` | QC Analyzer bag result | farmer_id, factory_id, batch_id, primary_percentage |
| `collection.quality_exceptions.received` | QC Analyzer exception images | farmer_id, factory_id, batch_id, exception_count |
| `collection.farmer_registration.received` | Mobile App registration | farmer_name, phone_number, factory_id |
| `collection.weather_data.updated` | Weather pull complete | region_id, date_range |
| `collection.market_prices.updated` | Market prices pull complete | market, price_per_kg |

## Trust Model

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Source Trust** | Trust provided IDs | Fast ingestion, no cross-model dependency |
| **Farmer Verification** | None on ingest | Plantation Model lookup is downstream concern |
| **Validation Failures** | Store with warnings | Best-effort semantic checking, not hard rejection |
| **Data Integrity** | Source responsible | Collection Model is intake, not police |
| **Field Mapping** | `plantation_id` = `farmer_id` | QC Analyzer uses plantation_id internally |

## MCP Server Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_farmer_documents` | All documents for a farmer | `farmer_id`, `date_range?`, `source_type?` |
| `get_quality_results` | QC Analyzer bag results | `farmer_id?`, `factory_id?`, `grade_filter?` |
| `get_quality_exceptions` | Secondary leaf images for batch | `batch_id`, `include_images?` |
| `get_farmer_quality_history` | Farmer quality trends | `farmer_id`, `days`, `factory_id?` |
| `get_factory_quality_summary` | Factory overview | `factory_id`, `date_range?` |
| `get_regional_weather` | Weather data for region | `region_id`, `days` (default 7) |
| `get_market_prices` | Market price data | `commodity?`, `market?`, `date_range?` |
| `search_documents` | Search by criteria | `query?`, `filters`, `source_types?` |
| `get_document_by_id` | Single document | `document_id`, `include_raw?` |
| `list_sources` | List data sources | `enabled_only?` |

### Tool Examples

```python
# Knowledge Model getting farmer quality history
history = await collection_mcp.call_tool(
    "get_farmer_quality_history",
    {"farmer_id": "WM-4521", "days": 30}
)
# Returns: trends, leaf_type_distribution, top_secondary_causes

# Action Plan Model getting recent quality results
results = await collection_mcp.call_tool(
    "get_quality_results",
    {
        "farmer_id": "WM-4521",
        "grade_filter": "low_quality",
        "date_range": {"start": "2025-12-01", "end": "2025-12-26"}
    }
)

# Knowledge Model: analyze secondary leaves to diagnose quality issues
exceptions = await collection_mcp.call_tool(
    "get_quality_exceptions",
    {"batch_id": "batch-2025-12-26-001", "include_images": True}
)
# Returns: images + classification metadata for secondary-grade leaves
# Knowledge Model analyzes: leaf types, coarse subtypes, patterns

# Knowledge Model correlating weather with quality
weather = await collection_mcp.call_tool(
    "get_regional_weather",
    {"region_id": "nandi-high", "days": 7}
)
```

## Data Flow Examples

### QC Analyzer Flow

The QC Analyzer produces two separate uploads per batch:

```
QC Analyzer at factory:
1. Grades tea leaves using computer vision (100 leaves per batch)
2. Separates results: primary-grade vs secondary-grade leaves
3. Creates Stream 1: bag_result.json (aggregated summary, no images)
4. Creates Stream 2: exceptions.zip (secondary-grade images + manifest)
5. Uploads when connectivity available

STREAM 1: Bag Quality Result (JSON)
───────────────────────────────────
Upload: qc-analyzer-landing/results/{plantation_id}/{crop}/{market}/{batch_id}.json

Azure Event Grid:
6. Detects BlobCreated event
7. POSTs to Collection Model /api/v1/triggers/event-grid

Collection Model:
8. Downloads JSON from blob storage
9. Validates against qc-bag-result.json schema
10. LLM extracts: farmer_id, factory_id, bag_summary, grading_model_id
11. LLM validates: primary_count + secondary_count = total_leaves
12. Stores: raw JSON → Blob, index → MongoDB quality_results_index
13. Archives processed file to qc-archive container
14. Emits: collection.quality_result.received

STREAM 2: Secondary Leaf Images (ZIP)
─────────────────────────────────────
Upload: qc-analyzer-landing/exceptions/{plantation_id}/{crop}/{market}/{batch_id}.zip

Azure Event Grid:
15. Detects BlobCreated event
16. POSTs to Collection Model /api/v1/triggers/event-grid

Collection Model:
17. Downloads ZIP from blob storage
18. Extracts manifest.json and images
19. Stores images to qc-exception-images container
20. Validates manifest against qc-exceptions-manifest.json schema
21. Links to batch result via batch_result_ref
22. Stores: raw ZIP → Blob, index → MongoDB quality_exceptions_index
23. Archives processed file
24. Emits: collection.quality_exceptions.received

Downstream (Knowledge Model):
25. Subscribes to collection.quality_result.received
26. Calls MCP: get_farmer_quality_history("WM-4521", 30)
27. Analyzes trends, identifies declining quality patterns
28. Calls MCP: get_quality_exceptions(batch_id) to retrieve secondary leaf images
29. Analyzes images to understand WHY quality is failing (coarse leaves, over-plucking, etc.)
30. Generates diagnosis and recommendations for farmer
```

### Farmer Registration Flow

```
Field Officer with Mobile App:
1. Registers new farmer (name, phone, GPS location)
2. App creates JSON file
3. Uploads to: mobile-app-landing/registrations/{factory_id}/{date}/{id}.json

Event Grid → Collection Model:
4. Validates against farmer-registration.json schema
5. LLM extracts: farmer_name, phone_number, location_gps
6. Stores: raw JSON → Blob, index → MongoDB farmer_registrations_index
7. Emits: collection.farmer_registration.received

Downstream (Plantation Model):
8. Subscribes to collection.farmer_registration.received
9. Creates farmer entity in plantation database
10. Assigns farmer_id
11. Emits: plantation.farmer.created

Downstream (Notification Model):
12. Subscribes to plantation.farmer.created
13. Sends welcome SMS to farmer
```

## TBK Grading Model Reference

The Tea Board of Kenya (TBK) model is a **binary classification** (Primary/Secondary) based on leaf type:

| Leaf Type | Grade | Description |
|-----------|-------|-------------|
| `bud` | Primary | Unopened leaf tip, highest quality |
| `one_leaf_bud` | Primary | One open leaf + bud (fine plucking) |
| `two_leaves_bud` | Primary | Two open leaves + bud (standard fine plucking) |
| `three_plus_leaves_bud` | Secondary | Coarse plucking |
| `single_soft_leaf` | Primary | Tender young leaf |
| `coarse_leaf` | Secondary | Mature, fibrous leaves |
| `banji` (soft) | Primary | Dormant but pliable shoot |
| `banji` (hard) | Secondary | Dormant and rigid shoot |

**Coarse Leaf Subtypes:**
- `double_luck` - Two leaves on same stem
- `maintenance_leaf` - Pruning remnant
- `hard_leaf` - Mature, fibrous

> **Full specification:** See [`tbk-kenya-tea-grading-model-specification.md`](../analysis/tbk-kenya-tea-grading-model-specification.md)

## Document Storage Models

Documents are stored in two locations:
- **Raw payload** → Azure Blob Storage (immutable archive)
- **Index document** → MongoDB (queryable metadata + extracted fields)

### Storage Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DOCUMENT STORAGE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Azure Blob Storage (Raw)              MongoDB (Index)                      │
│  ┌─────────────────────────┐          ┌─────────────────────────┐          │
│  │ quality-results-raw/    │          │ quality_results_index   │          │
│  │   {document_id}.json    │◀────────▶│   extracted fields      │          │
│  │                         │  ref     │   + raw_blob_uri        │          │
│  ├─────────────────────────┤          ├─────────────────────────┤          │
│  │ quality-exceptions-raw/ │          │ quality_exceptions_index│          │
│  │   {document_id}.zip     │◀────────▶│   + image_uris[]        │          │
│  ├─────────────────────────┤          ├─────────────────────────┤          │
│  │ qc-exception-images/    │          │                         │          │
│  │   {doc_id}/img_001.jpg  │◀─────────│   references            │          │
│  │   {doc_id}/img_002.jpg  │          │                         │          │
│  ├─────────────────────────┤          ├─────────────────────────┤          │
│  │ registrations-raw/      │          │ farmer_registrations    │          │
│  │   {document_id}.json    │◀────────▶│   _index                │          │
│  ├─────────────────────────┤          ├─────────────────────────┤          │
│  │ weather-data-raw/       │          │ weather_index           │          │
│  │   {document_id}.json    │◀────────▶│                         │          │
│  ├─────────────────────────┤          ├─────────────────────────┤          │
│  │ market-data-raw/        │          │ market_prices_index     │          │
│  │   {document_id}.json    │◀────────▶│                         │          │
│  └─────────────────────────┘          └─────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Base Document Models

```python
# services/collection-model/src/collection_model/domain/models.py
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    """Status of document ingestion."""
    SUCCESS = "success"
    PARTIAL = "partial"           # Stored but with validation warnings
    FAILED = "failed"             # Failed to process


class BlobReference(BaseModel):
    """Reference to a blob in Azure Blob Storage."""
    container: str
    blob_path: str
    content_type: str
    size_bytes: int
    etag: str
    uploaded_at: datetime
    original_filename: str | None = None

    # Content hash for deduplication
    content_hash: str = Field(
        description="SHA-256 hash of file content for deduplication"
    )

    @property
    def uri(self) -> str:
        return f"az://{self.container}/{self.blob_path}"


class DuplicateDetectionResult(BaseModel):
    """Result of duplicate detection check."""
    is_duplicate: bool
    existing_document_id: str | None = None
    existing_ingested_at: datetime | None = None
    hash_matched: str | None = None


class RawDocumentSet(BaseModel):
    """
    Set of raw documents that together form one logical document.

    Examples:
    - Single JSON: primary only
    - ZIP with images: primary (ZIP) + extracted (images)
    - Result + Images: primary (JSON result) + related (image ZIP)
    """
    primary: BlobReference = Field(
        description="Main raw document (JSON, ZIP, etc.)"
    )
    related: list[BlobReference] = Field(
        default_factory=list,
        description="Related raw documents (e.g., separate image upload)"
    )
    extracted: list[BlobReference] = Field(
        default_factory=list,
        description="Files extracted from primary (e.g., images from ZIP)"
    )

    @property
    def all_blobs(self) -> list[BlobReference]:
        """All blob references for this document set."""
        return [self.primary] + self.related + self.extracted


# Usage Examples:
#
# 1. Single JSON (Quality Result):
#    RawDocumentSet(
#        primary=BlobReference(container="quality-results-raw", blob_path="doc123.json", ...),
#        related=[],
#        extracted=[]
#    )
#
# 2. ZIP with extracted images (Quality Exceptions):
#    RawDocumentSet(
#        primary=BlobReference(container="quality-exceptions-raw", blob_path="batch123.zip", ...),
#        related=[],
#        extracted=[
#            BlobReference(container="qc-exception-images", blob_path="batch123/img_001.jpg", ...),
#            BlobReference(container="qc-exception-images", blob_path="batch123/img_002.jpg", ...),
#        ]
#    )
#
# 3. Separate JSON + Images (alternative pattern):
#    RawDocumentSet(
#        primary=BlobReference(container="quality-results-raw", blob_path="result123.json", ...),
#        related=[
#            BlobReference(container="quality-exceptions-raw", blob_path="images123.zip", ...),
#        ],
#        extracted=[
#            BlobReference(container="qc-exception-images", blob_path="batch123/img_001.jpg", ...),
#        ]
#    )


class ExtractionMetadata(BaseModel):
    """Metadata from LLM extraction step."""
    agent_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    validation_passed: bool
    validation_warnings: list[str] = Field(default_factory=list)
    extracted_at: datetime
    extraction_duration_ms: int


class IngestionMetadata(BaseModel):
    """Metadata about the ingestion process."""
    ingestion_id: str              # Unique ID for this ingestion run
    trace_id: str                  # Distributed tracing ID
    source_id: str                 # Source config that processed this
    source_version: int            # Version of source config used

    triggered_by: str              # "event_grid" | "dapr_job" | "manual"
    trigger_event_id: str | None   # Event Grid event ID if applicable

    started_at: datetime
    completed_at: datetime
    duration_ms: int

    status: IngestionStatus
    error_message: str | None = None


class BaseDocumentIndex(BaseModel):
    """
    Base model for all indexed documents.
    Stored in MongoDB, references raw payload in Blob Storage.
    """
    # Identity
    document_id: str = Field(description="Unique document identifier (UUID)")
    source_id: str = Field(description="Source config ID that produced this")

    # Linkage
    farmer_id: str | None = Field(
        default=None,
        description="Farmer ID this document relates to (after field mapping)"
    )
    link_field: str | None = Field(
        default=None,
        description="Name of the field used for linkage"
    )
    link_value: str | None = Field(
        default=None,
        description="Original value before mapping"
    )

    # Raw storage reference (supports multiple related documents)
    raw_documents: RawDocumentSet

    # Extraction metadata
    extraction: ExtractionMetadata

    # Ingestion metadata
    ingestion: IngestionMetadata

    # Timestamps
    source_timestamp: datetime = Field(
        description="Timestamp from source (e.g., batch_timestamp)"
    )
    ingested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When document was ingested into platform"
    )

    # TTL
    expires_at: datetime | None = Field(
        default=None,
        description="When document should be deleted (TTL)"
    )

    class Config:
        # MongoDB will use document_id as _id
        json_schema_extra = {
            "indexes": [
                {"keys": [("farmer_id", 1), ("source_id", 1), ("ingested_at", -1)]},
                {"keys": [("source_id", 1), ("ingested_at", -1)]},
                {"keys": [("expires_at", 1)], "expireAfterSeconds": 0},
                # Deduplication index: unique per source + content hash
                {"keys": [("source_id", 1), ("raw_documents.primary.content_hash", 1)], "unique": True},
            ]
        }
```

### Deduplication Strategy

The pipeline checks for duplicates **before processing** using the content hash:

```python
# services/collection-model/src/collection_model/infrastructure/dedup.py
import hashlib
from motor.motor_asyncio import AsyncIOMotorCollection


class DeduplicationService:
    """Prevent duplicate document ingestion using content hash."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    async def check_duplicate(
        self,
        source_id: str,
        content_hash: str,
    ) -> DuplicateDetectionResult:
        """Check if document with same hash already exists for this source."""
        existing = await self.collection.find_one(
            {
                "source_id": source_id,
                "raw_documents.primary.content_hash": content_hash,
            },
            {"document_id": 1, "ingested_at": 1},
        )

        if existing:
            return DuplicateDetectionResult(
                is_duplicate=True,
                existing_document_id=existing["document_id"],
                existing_ingested_at=existing["ingested_at"],
                hash_matched=content_hash,
            )

        return DuplicateDetectionResult(is_duplicate=False)


# Usage in pipeline:
async def process_blob(blob_content: bytes, source_id: str):
    content_hash = await dedup_service.compute_hash(blob_content)

    # Check for duplicate before processing
    result = await dedup_service.check_duplicate(source_id, content_hash)
    if result.is_duplicate:
        logger.info(
            f"Skipping duplicate: {result.existing_document_id} "
            f"(ingested at {result.existing_ingested_at})"
        )
        return None  # Skip processing

    # Continue with ingestion pipeline...
```

**Key Design Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Hash algorithm** | SHA-256 | Fast, collision-resistant, widely supported |
| **Scope** | Per source_id | Same file from different sources = different documents |
| **Check timing** | Before processing | Avoid wasted LLM calls and storage |
| **On duplicate** | Skip silently | Idempotent uploads (retry-safe) |
| **Index** | Unique compound | DB-level enforcement, fast lookups |

### Quality Result Index

```python
# services/collection-model/src/collection_model/domain/quality_result.py
from .models import BaseDocumentIndex


class LeafTypeDistribution(BaseModel):
    """Distribution of leaf types in a batch."""
    bud: int = 0
    one_leaf_bud: int = 0
    two_leaves_bud: int = 0
    three_plus_leaves_bud: int = 0
    single_soft_leaf: int = 0
    coarse_leaf: int = 0
    banji: int = 0


class CoarseSubtypeDistribution(BaseModel):
    """Distribution of coarse leaf subtypes."""
    double_luck: int = 0
    maintenance_leaf: int = 0
    hard_leaf: int = 0


class BanjiDistribution(BaseModel):
    """Distribution of banji hardness."""
    soft: int = 0
    hard: int = 0


class BagSummary(BaseModel):
    """Aggregated quality summary for a bag."""
    total_leaves: int
    primary_count: int
    secondary_count: int
    primary_percentage: float = Field(ge=0.0, le=100.0)
    secondary_percentage: float = Field(ge=0.0, le=100.0)

    leaf_type_distribution: LeafTypeDistribution
    coarse_subtype_distribution: CoarseSubtypeDistribution
    banji_distribution: BanjiDistribution


class QualityResultIndex(BaseDocumentIndex):
    """
    Index document for QC Analyzer bag quality results.
    Collection: quality_results_index
    """
    # Batch identification
    batch_id: str
    batch_timestamp: datetime

    # Factory context
    factory_id: str
    collection_point_id: str

    # Grading model
    grading_model_id: str
    grading_model_version: str

    # Product context
    crop_name: str
    market_name: str

    # Quality data (extracted)
    bag_summary: BagSummary

    # Computed fields for querying
    is_low_quality: bool = Field(
        description="True if secondary_percentage > 30%"
    )
    dominant_secondary_cause: str | None = Field(
        default=None,
        description="Most common secondary leaf type"
    )

    class Config:
        json_schema_extra = {
            "collection": "quality_results_index",
            "indexes": [
                {"keys": [("farmer_id", 1), ("batch_timestamp", -1)]},
                {"keys": [("factory_id", 1), ("batch_timestamp", -1)]},
                {"keys": [("batch_id", 1)], "unique": True},
                {"keys": [("is_low_quality", 1), ("batch_timestamp", -1)]},
            ]
        }
```

### Quality Exceptions Index

```python
# services/collection-model/src/collection_model/domain/quality_exceptions.py
from .models import BaseDocumentIndex, BlobReference


class LeafClassification(BaseModel):
    """Classification result for a single leaf image."""
    quality_grade: str              # "primary" | "secondary"
    confidence: float = Field(ge=0.0, le=1.0)
    leaf_type: str
    coarse_subtype: str | None = None
    banji_hardness: str | None = None


class ExceptionImage(BaseModel):
    """A secondary-grade leaf image with its classification."""
    image_ref: BlobReference        # Reference to extracted image
    classification: LeafClassification
    sequence_number: int            # Order in batch


class QualityExceptionsIndex(BaseDocumentIndex):
    """
    Index document for QC Analyzer secondary leaf images.
    Collection: quality_exceptions_index

    Used by Knowledge Model to understand WHY quality is failing.
    """
    # Batch identification
    batch_id: str
    batch_timestamp: datetime

    # Reference to corresponding quality result
    batch_result_document_id: str
    batch_result_ref: str           # Blob path to result JSON

    # Factory context
    factory_id: str
    grading_model_id: str
    grading_model_version: str

    # Exception summary
    exception_count: int
    exception_images: list[ExceptionImage]

    # Aggregated analysis (computed on ingestion)
    leaf_type_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Count per leaf_type in exceptions"
    )
    top_exception_causes: list[str] = Field(
        default_factory=list,
        description="Top 3 leaf types causing exceptions"
    )

    class Config:
        json_schema_extra = {
            "collection": "quality_exceptions_index",
            "indexes": [
                {"keys": [("farmer_id", 1), ("batch_timestamp", -1)]},
                {"keys": [("batch_id", 1)], "unique": True},
                {"keys": [("batch_result_document_id", 1)]},
            ]
        }
```

### Farmer Registration Index

```python
# services/collection-model/src/collection_model/domain/registration.py
from .models import BaseDocumentIndex


class GPSLocation(BaseModel):
    """GPS coordinates."""
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class FarmerRegistrationIndex(BaseDocumentIndex):
    """
    Index document for farmer registrations from Mobile App.
    Collection: farmer_registrations_index
    """
    # Registration identity
    registration_id: str

    # Farmer details (extracted)
    farmer_name: str
    phone_number: str               # Primary linkage field
    national_id: str | None = None

    # Location
    factory_id: str
    collection_point_id: str
    location_gps: GPSLocation | None = None

    # Registration context
    registered_by: str              # Field officer ID
    registered_at: datetime

    # Processing status
    farmer_created: bool = Field(
        default=False,
        description="True when Plantation Model created farmer entity"
    )
    assigned_farmer_id: str | None = Field(
        default=None,
        description="Farmer ID assigned by Plantation Model"
    )

    class Config:
        json_schema_extra = {
            "collection": "farmer_registrations_index",
            "indexes": [
                {"keys": [("phone_number", 1)], "unique": True},
                {"keys": [("registration_id", 1)], "unique": True},
                {"keys": [("factory_id", 1), ("registered_at", -1)]},
                {"keys": [("farmer_created", 1)]},
            ]
        }
```

### Weather Index

```python
# services/collection-model/src/collection_model/domain/weather.py
from .models import BaseDocumentIndex


class DailyWeather(BaseModel):
    """Weather data for a single day."""
    date: date
    temp_max_c: float
    temp_min_c: float
    precipitation_mm: float
    humidity_avg: float | None = None


class WeatherIndex(BaseDocumentIndex):
    """
    Index document for weather data from Weather API.
    Collection: weather_index
    """
    # Location
    region_id: str
    region_name: str

    # Data range
    data_date: date                 # Primary date for this record
    date_range_start: date
    date_range_end: date

    # Weather data (extracted)
    daily_data: list[DailyWeather]

    # Aggregates (computed)
    avg_temp_max: float
    avg_temp_min: float
    total_precipitation_mm: float

    class Config:
        json_schema_extra = {
            "collection": "weather_index",
            "indexes": [
                {"keys": [("region_id", 1), ("data_date", -1)]},
                {"keys": [("region_id", 1), ("date_range_start", 1), ("date_range_end", 1)]},
            ]
        }
```

### Market Prices Index

```python
# services/collection-model/src/collection_model/domain/market_prices.py
from .models import BaseDocumentIndex


class GradePrice(BaseModel):
    """Price for a specific grade."""
    grade: str
    price_per_kg: float
    volume_kg: float | None = None


class MarketPricesIndex(BaseDocumentIndex):
    """
    Index document for market price data.
    Collection: market_prices_index
    """
    # Market identification
    commodity: str                  # "tea"
    market: str                     # "mombasa_auction"

    # Price date
    price_date: date
    auction_number: str | None = None

    # Price data (extracted)
    average_price_per_kg: float
    volume_traded_kg: float | None = None
    grade_breakdown: list[GradePrice] = Field(default_factory=list)

    # Trend indicators (computed)
    price_change_percent: float | None = Field(
        default=None,
        description="Change from previous week"
    )

    class Config:
        json_schema_extra = {
            "collection": "market_prices_index",
            "indexes": [
                {"keys": [("commodity", 1), ("market", 1), ("price_date", -1)]},
                {"keys": [("price_date", -1)]},
            ]
        }
```

### MongoDB Collections Summary

| Collection | Purpose | Key Indexes |
|------------|---------|-------------|
| `source_configs` | Source configuration registry | `source_id` (unique) |
| `quality_results_index` | QC Analyzer bag results | `farmer_id + batch_timestamp`, `batch_id` (unique) |
| `quality_exceptions_index` | Secondary leaf images | `farmer_id + batch_timestamp`, `batch_result_document_id` |
| `farmer_registrations_index` | Mobile app registrations | `phone_number` (unique), `registration_id` (unique) |
| `weather_index` | Regional weather data | `region_id + data_date` |
| `market_prices_index` | Auction prices | `commodity + market + price_date` |

## Testing Strategy

| Test Type | Scope | Examples |
|-----------|-------|----------|
| **Schema Validation** | Unit | Valid/invalid JSON against schemas |
| **ZIP Processing** | Unit | Extract manifest, handle malformed ZIPs |
| **Extraction Accuracy** | Golden samples | Known payloads → expected extractions |
| **Semantic Validation** | Edge cases | Inconsistent grades, invalid distributions |
| **Trigger Integration** | Integration | Event Grid subscription, DAPR Job execution |
| **MCP Tools** | Functional | Tool queries, response interpretation |
| **End-to-End** | Integration | Upload ZIP → Event → Pipeline → Query via MCP |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Ingestion Modes** | BLOB_TRIGGER + SCHEDULED_PULL | Webhook unsuitable for unreliable networks |
| **QC Analyzer Streams** | Separate result (JSON) + exceptions (ZIP) | Lightweight results, images only for secondary leaves |
| **Exception Images** | All secondary-grade leaves | Knowledge Model needs images to diagnose quality issues |
| **Mobile App Format** | JSON per registration | Simple, immediate upload when connected |
| **Factory POS** | Deferred | Heterogeneous systems require standardization |
| **Source Config Storage** | Git → MongoDB | Version control + fast runtime lookup |
| **Trigger Mechanism** | Event Grid + DAPR Jobs | Cloud-native, reliable delivery |
| **Pipeline Unification** | Same steps all sources | Consistent validation, extraction, storage |
| **LLM Extraction** | All sources use LLM | Handles format variations, semantic validation |
| **Trust Model** | Trust source IDs | No cross-model verification on ingest |
| **Field Mapping** | plantation_id = farmer_id | Align with QC Analyzer terminology |

---

_Last Updated: 2025-12-26_
