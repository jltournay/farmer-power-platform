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

### Workflow Execution Rules (CRITICAL)

> **⛔ NEVER create your own todo list when executing a BMAD workflow.**

When running any BMAD workflow (dev-story, code-review, create-story, etc.):

1. **ALWAYS load and follow `instructions.xml`** - Execute steps in EXACT order
2. **NEVER skip workflow steps** - Even if you think they're not needed
3. **NEVER substitute your own task list** - The workflow steps ARE the task list
4. **NEVER make "judgment calls" to defer steps** - If a step says MANDATORY, do it

**Why this matters:** The workflow steps exist to prevent errors. When you create your own todo list, you bypass critical gates (like E2E testing and Code Review) that the workflow enforces.

**Correct behavior:**
```
Workflow says: Step 7 → Step 7b (Local E2E) → Step 8 → Step 9 → Step 9b (Quality CI) → Step 9c (E2E CI) → Step 9d (GitHub) → Step 9e (Code Review) → Step 10
You execute:    Step 7 → Step 7b (Local E2E) → Step 8 → Step 9 → Step 9b (Quality CI) → Step 9c (E2E CI) → Step 9d (GitHub) → Step 9e (Code Review) → Step 10
```

**Incorrect behavior:**
```
Workflow says: Step 7 → Step 7b (Local E2E) → ... → Step 9c (E2E CI) → ... → Step 9e (Code Review) → Step 10
You create:    Own todo: Unit tests → Lint → Push → Done  ← WRONG! (skipped Local E2E, E2E CI, and Code Review)
```

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

### E2E Testing Gate (MANDATORY - NO EXCEPTIONS)

> **⛔ CRITICAL: This gate CANNOT be skipped, deferred, or worked around.**

**TWO E2E VALIDATION STEPS ARE REQUIRED:**

| Step   | What      | When                                                                                         | Command                                               |
|--------|-----------|----------------------------------------------------------------------------------------------|-------------------------------------------------------|
| **7b** | Local E2E | Before marking tasks complete                                                                | `docker compose ... up -d --build`                    |
| **9c** | CI E2E    | After push in the story branch, run the e2e workflow in the story branch, before code review | `gh workflow run e2e-tests.yaml --ref <story branch>` |

#### Step 7b: Local E2E (MANDATORY)

**BEFORE marking ANY story complete or pushing final commits:**

1. **Rebuild and start E2E infrastructure (--build is MANDATORY):**
   ```bash
   docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml up -d --build
   ```
   > ⚠️ **WARNING:** You MUST use `--build` to rebuild Docker images. Without it, you test stale code and get false positives that fail in CI.

2. **VERIFY Docker images were actually rebuilt (NOT cached):**
   - Check the build output for `COPY services/` lines
   - If you see `CACHED` next to COPY commands for services you modified, the rebuild FAILED
   - You MUST see actual build steps (not CACHED) for modified service directories
   - If images are cached, run: `docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml build --no-cache`

3. **Run E2E test suite:**
   ```bash
   PYTHONPATH="${PYTHONPATH}:.:libs/fp-proto/src" pytest tests/e2e/scenarios/ -v
   ```

4. **Capture output in story file** - Paste actual test results, not placeholders

5. **Tear down infrastructure:**
   ```bash
   docker compose -f tests/e2e/infrastructure/docker-compose.e2e.yaml down -v
   ```

#### Step 9c: E2E CI (MANDATORY - SEPARATE FROM LOCAL)

**AFTER pushing to story branch, BEFORE code review:**

1. **Trigger E2E CI workflow (it does NOT auto-run):**
   ```bash
   gh workflow run e2e.yaml --ref <story-branch>
   ```

2. **Wait for workflow to start and get run ID:**
   ```bash
   sleep 10
   gh run list --workflow=e2e.yaml --branch <story-branch> --limit 1
   ```

3. **Monitor until completion:**
   ```bash
   gh run watch <run-id>
   ```

4. **Verify PASSED status and record run ID in story file**

> ⚠️ **WARNING:** Local E2E passing does NOT mean CI E2E will pass. CI rebuilds images from scratch and may catch Dockerfile issues, environment problems, or cache inconsistencies that local misses.

**⛔ BLOCKED ACTIONS without BOTH E2E gates:**
- Do NOT mark story status as 'review' or 'done'
- Do NOT proceed to code review
- Do NOT declare story complete
- Do NOT write "(to be verified later)" - this is NOT acceptable

**If either E2E gate fails:** HALT immediately and fix before proceeding.

This corresponds to **Steps 7b and 9c** in the dev-story workflow - both are NON-NEGOTIABLE.

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

### Code Review Gate (MANDATORY - NO EXCEPTIONS)

> **⛔ CRITICAL: This gate CANNOT be skipped, deferred, or worked around.**

**AFTER dev-story workflow completes (status = "review"):**

1. **Run code review workflow:**
   ```bash
   # In Claude Code, run:
   /code-review
   ```

2. **Address ALL review findings:**
   - High severity: MUST be fixed before proceeding
   - Medium severity: MUST be fixed or explicitly justified
   - Low severity: Should be fixed or documented for future

3. **Capture review evidence in story file:**
   - Review outcome (Approve/Changes Requested/Blocked)
   - Action items with checkboxes
   - Resolution notes for each finding

**⛔ BLOCKED ACTIONS without Code Review:**
- Do NOT mark story status as 'done'
- Do NOT merge to main branch
- Do NOT close the GitHub issue
- Do NOT declare story complete

**If code review requests changes:** Address findings, then re-run code-review until approved.

This corresponds to **Step 9e** in the dev-story workflow - it is NON-NEGOTIABLE.

**Best Practice:** Run code-review using a **different LLM** than the one that implemented the story for unbiased review.

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
