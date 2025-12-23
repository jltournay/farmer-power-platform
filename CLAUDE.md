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
- Use fixtures from `tests/conftest.py`

## Reference Documents

| Topic | Document |
|-------|----------|
| Full rules & patterns | `_bmad-output/project-context.md` |
| Repository structure | `_bmad-output/architecture/repository-structure.md` |
| Architecture decisions | `_bmad-output/architecture/index.md` |
| Test strategy | `_bmad-output/test-design-system-level.md` |
| UX specifications | `_bmad-output/ux-design-specification/index.md` |
| Epics & stories | `_bmad-output/epics.md` |

---

**When in doubt:** Check `_bmad-output/project-context.md` first.
