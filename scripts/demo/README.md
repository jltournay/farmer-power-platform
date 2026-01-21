# Demo Data Scripts

Quick reference for demo data tooling. See [`docs/demo-data.md`](../../docs/demo-data.md) for full documentation.

## Quick Start (End-to-End)

```bash
# 1. Start infrastructure (MongoDB + services)
bash scripts/e2e-up.sh

# 2. Load seed data (--clear wipes existing data first)
python scripts/demo/load_demo_data.py --source e2e --clear

# 3. (Optional) Generate demo data
python scripts/demo/generate_demo_data.py --profile demo --seed 12345 --load

# 4. When done
bash scripts/e2e-up.sh --down
```

## Individual Commands

```bash
# Load E2E seed data (requires MongoDB)
python scripts/demo/load_demo_data.py --source e2e

# Generate and load demo data (50 farmers)
python scripts/demo/generate_demo_data.py --profile demo --load

# Validate only (no MongoDB needed)
python scripts/demo/load_demo_data.py --source e2e --dry-run
```

## Environment Setup

```bash
# Required PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:.:libs/fp-common:libs/fp-proto/src"

# MongoDB connection (for loading)
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
```

## Command Reference

### Loader (`load_demo_data.py`)

| Command | Purpose |
|---------|---------|
| `--source e2e` | Load E2E seed data |
| `--source e2e --dry-run` | Validate E2E seed without loading |
| `--source custom --path X` | Load from custom directory |
| `--source custom --path X --dry-run` | Validate custom data only |
| `--clear` | Clear databases before loading |
| `--mongodb-uri URI` | Custom MongoDB connection |

### Generator (`generate_demo_data.py`)

| Command | Purpose |
|---------|---------|
| `--profile minimal` | Generate minimal dataset (3 farmers) |
| `--profile demo` | Generate demo dataset (50 farmers) |
| `--profile demo-large` | Generate large dataset (250 farmers) |
| `--seed 12345` | Deterministic generation |
| `--load` | Generate and load to MongoDB |
| `--list-profiles` | Show available profiles |
| `--output DIR` | Custom output directory |

## Available Profiles

| Profile | Farmers | Factories | Documents | Description |
|---------|---------|-----------|-----------|-------------|
| `minimal` | 3 | 1 | 15 | Quick testing |
| `demo` | 50 | 3 | 500 | UI development |
| `demo-large` | 250 | 10 | 3000 | Performance testing |

## Files

| File | Purpose |
|------|---------|
| `load_demo_data.py` | Seed data loader CLI |
| `generate_demo_data.py` | Data generator CLI |
| `loader.py` | Database loading logic |
| `validation.py` | Pydantic validation |
| `fk_registry.py` | FK tracking |
| `model_registry.py` | Model-to-file mapping |

## Related

- Full documentation: [`docs/demo-data.md`](../../docs/demo-data.md)
- Profile definitions: [`tests/demo/profiles/`](../../tests/demo/profiles/)
- E2E seed data: [`tests/e2e/infrastructure/seed/`](../../tests/e2e/infrastructure/seed/)
- Generator factories: [`tests/demo/generators/`](../../tests/demo/generators/)
