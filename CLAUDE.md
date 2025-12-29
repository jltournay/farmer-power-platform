# Farmer Power Platform - AI Agent Instructions

## Before You Code

**READ THIS FIRST:** `_bmad-output/project-context.md`

This file contains 176 critical rules covering:
- Repository structure and naming conventions
- Technology stack requirements (Python 3.12, Pydantic 2.0, DAPR)
- Domain model boundaries and responsibilities
- Testing patterns and golden sample requirements
- UI/UX design tokens and accessibility rules

## Project Structure

```
farmer-power-platform/
├── services/           # Microservices (8 domain models + BFF)
├── mcp-servers/        # MCP Server implementations
├── proto/              # Protocol Buffer definitions
├── libs/               # Shared libraries (fp-common, fp-proto, fp-testing)
├── deploy/             # Kubernetes & Docker configs
├── tests/              # Cross-service tests
└── scripts/            # Build & deployment scripts
```

**Full structure details:** `_bmad-output/architecture/repository-structure.md`

## Critical Rules Summary

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Service folder | kebab-case | `collection-model/` |
| Python package | snake_case | `collection_model/` |
| Proto package | snake_case | `farmer_power.collection.v1` |

### Where to Put Code

| Need | Location |
|------|----------|
| New domain model service | `services/{model-name}/` |
| New MCP server | `mcp-servers/{model-name}-mcp/` |
| Shared utility | `libs/fp-common/fp_common/` |
| Proto definition | `proto/{domain}/v1/{domain}.proto` |
| Unit test | `tests/unit/{model_name}/` |
| Golden sample | `tests/golden/{agent-name}/samples.json` |

### Must-Follow Rules

1. **ALL I/O operations MUST be async** - database, HTTP, MCP calls
2. **ALL inter-service communication via DAPR** - no direct HTTP between services
3. **ALL LLM calls via OpenRouter** - no direct provider calls
4. **ALL prompts stored in MongoDB** - no hardcoded prompts
5. **MCP servers are STATELESS** - no in-memory caching
6. **Use Pydantic 2.0 syntax** - `model_dump()` not `dict()`

### Testing Requirements

- Golden samples required for all AI agents (see `tests/golden/`)
- Mock ALL external APIs (LLM, Starfish, Weather, Africa's Talking)
- Use fixtures from `tests/conftest.py` - **DO NOT override** `mock_mongodb_client` in local conftest.py
- **E2E Tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` before writing E2E tests
  - Proto = source of truth, production code implements it, seed data/tests verify it
  - NEVER modify production code to make tests pass
  - NEVER modify production code to accept incorrect seed data
  - **If you modify production code:** Document each change with file, what, why, evidence, and type
  - Run `python tests/e2e/infrastructure/validate_seed_data.py` before starting Docker

### CI Validation (MANDATORY before marking story done)

1. **Run locally before push:**
   ```bash
   ruff check . && ruff format --check .
   ```

2. **Verify CI passes after push:**
   ```bash
   gh run list --limit 1  # Check status
   gh run view <run_id> --log-failed  # If failed, check logs
   ```

3. **Story is NOT done until CI passes** - Definition of Done includes green CI

### New Service Checklist

When adding a new service (e.g., `services/new-model/`), you MUST:

1. **Update CI PYTHONPATH** in `.github/workflows/ci.yaml`:
   ```yaml
   PYTHONPATH="${PYTHONPATH}:...:services/new-model/src"
   ```
   Update BOTH `unit-tests` and `integration-tests` jobs

2. **DO NOT create conflicting fixtures** in `tests/unit/new_model/conftest.py`
   - Use fixtures from root `tests/conftest.py` (MockMongoClient, mock_llm_client, etc.)
   - Only add service-specific fixtures that don't override parent fixtures

### Git Commit Rules

- **ALWAYS include GitHub issue reference** when working on a story (e.g., `Relates to #16` or `Fixes #16`)
- Check `sprint-status.yaml` for the `github_issue` comment on the story being worked on
- Commit message format:
  ```
  Short summary (50 chars max)

  Relates to #<issue_number>

  ## What changed
  - Bullet points of changes

  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
  ```

## Reference Documents

| Topic | Document |
|-------|----------|
| Full rules & patterns | `_bmad-output/project-context.md` |
| Repository structure | `_bmad-output/architecture/repository-structure.md` |
| Architecture decisions | `_bmad-output/architecture/index.md` |
| Test strategy | `_bmad-output/test-design-system-level.md` |
| **E2E testing mental model** | `tests/e2e/E2E-TESTING-MENTAL-MODEL.md` |
| UX specifications | `_bmad-output/ux-design-specification/index.md` |
| Epics & stories | `_bmad-output/epics.md` |

---

**When in doubt:** Check `_bmad-output/project-context.md` first.
