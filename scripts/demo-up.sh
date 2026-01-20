#!/usr/bin/env bash
#
# Shell wrapper for load-demo-data.py with proper PYTHONPATH setup.
#
# Story 0.8.2: Seed Data Loader Script
# Task 6: Create shell wrapper script
#
# Usage:
#   bash scripts/demo-up.sh --source e2e
#   bash scripts/demo-up.sh --source e2e --dry-run
#   bash scripts/demo-up.sh --source custom --path ./my-data/
#
set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env file if exists
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Setup PYTHONPATH to include all required packages
export PYTHONPATH="${PYTHONPATH:-}:${PROJECT_ROOT}"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/libs/fp-common"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/libs/fp-proto/src"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/services/ai-model/src"
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}/tests/e2e"

# Run the loader script with all passed arguments
python "${PROJECT_ROOT}/scripts/demo/load_demo_data.py" "$@"
