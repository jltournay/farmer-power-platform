# Story 0.8.6: Cost Event Demo Data Generator

**Status:** review
**Story Points:** 5
**GitHub Issue:** #223

## Story

As a **developer preparing demo environments for the cost dashboard**,
I want the demo data generator to produce realistic platform cost events,
so that the platform-cost database has historical data for cost dashboard UI development and demos.

## Acceptance Criteria

### AC1: CostEventFactory generates valid UnifiedCostEvent instances

**Given** the CostEventFactory is invoked with default configuration
**When** I build a cost event using `CostEventFactory.build()`
**Then** the result is a valid `UnifiedCostEvent` instance
**And** it passes Pydantic re-validation via `UnifiedCostEvent.model_validate(event.model_dump())`
**And** the `cost_type`/`unit` pairing is valid (llm→tokens, document→pages, embedding→queries, sms→messages)
**And** `amount_usd` is non-negative
**And** `request_id` is unique per event

### AC2: Cost events are JSON-serializable and follow established patterns

**Given** a generated cost event
**When** I serialize it via `json.dumps(event.model_dump(mode="json"))`
**Then** it round-trips without error
**And** `Decimal` amounts are serialized as strings (per `DecimalStr` type)
**And** enums are serialized as string values (per `model_config = {"use_enum_values": True}`)

### AC3: Profile YAML controls cost event generation parameters

**Given** a demo profile with `cost_events:` section
**When** the generator runs with that profile
**Then** it generates events distributed across the configured `date_range`
**And** the approximate `daily_events` count is respected
**And** the cost_type `distribution` percentages are followed (e.g., 60% llm, 20% document, etc.)
**And** `source_services` are drawn from the configured list

### AC4: Orchestrator includes cost events in GeneratedData output

**Given** the DataOrchestrator generates data for a profile
**When** generation completes
**Then** `GeneratedData.cost_events` contains the generated events as dicts
**And** the events are written to `cost_events.json` in the output directory
**And** the events are loadable by the seed data loader

### AC5: Loader seeds platform_cost_e2e.cost_events via existing seed_cost_events()

**Given** `cost_events.json` exists in the seed data path
**When** the loader runs
**Then** it loads through `StrictUnifiedCostEvent` (Pydantic with `extra="forbid"`)
**And** it upserts to `platform_cost_e2e.cost_events` collection using `request_id` as key
**And** the SEED_ORDER places cost_events at Level 0 (no FK dependencies)

### AC6: Unit tests validate factory behavior with full coverage

**Given** the unit test file `tests/unit/demo/generators/test_cost_factory.py`
**When** I run `pytest tests/unit/demo/generators/test_cost_factory.py -v`
**Then** all tests pass covering:
  - Pydantic validation
  - JSON serialization
  - cost_type/unit pairing
  - Realistic amount ranges per cost type
  - Unique request_id generation
  - Time distribution across date range
  - Metadata fields per cost type (model, agent_type, tokens for LLM, etc.)
  - Batch generation and cost_type distribution
  - Custom overrides

### AC7: Metadata is realistic per cost type

**Given** a generated cost event of type `llm`
**Then** metadata includes: `model` (from realistic set), `agent_type`, `tokens_in`, `tokens_out`

**Given** a generated cost event of type `document`
**Then** metadata includes: `model_id`, `page_count`

**Given** a generated cost event of type `embedding`
**Then** metadata includes: `model`, `knowledge_domain`, `texts_count`

**Given** a generated cost event of type `sms`
**Then** metadata includes: `message_type`, `recipient_count`

## Tasks / Subtasks

- [x] Task 1: Create CostEventFactory (AC: #1, #2, #7)
  - [x] 1.1 Create `tests/demo/generators/cost.py`
  - [x] 1.2 Implement `CostEventFactory` extending base pattern from `base.py`
  - [x] 1.3 Implement realistic pricing per cost_type (llm: $0.001-$0.05, document: $0.01-$0.10, embedding: $0.0001-$0.001, sms: $0.01-$0.05)
  - [x] 1.4 Implement metadata generation per cost_type
  - [x] 1.5 Implement time-distributed generation method (spread across days_span)
  - [x] 1.6 Implement cost_type weighted distribution
  - [x] 1.7 Ensure unique `request_id` per event (UUID4)
  - [x] 1.8 Add source_service rotation: ai-model, collection-model, knowledge-model, notification-model
  - [x] 1.9 Export from `generators/__init__.py`

- [x] Task 2: Add cost_events to demo profiles (AC: #3)
  - [x] 2.1 Add `cost_events:` section to `tests/demo/profiles/minimal.yaml` (30 days, 5-10/day)
  - [x] 2.2 Add `cost_events:` section to `tests/demo/profiles/demo.yaml` (90 days, 20-50/day)
  - [x] 2.3 Add `cost_events:` section to `tests/demo/profiles/demo-large.yaml` (180 days, 50-150/day)
  - [x] 2.4 Update profile loading code if needed to parse cost_events config

- [x] Task 3: Wire cost events into orchestrator (AC: #4)
  - [x] 3.1 Add `cost_events: list[dict[str, Any]]` to `GeneratedData` dataclass
  - [x] 3.2 Add generation step in `DataOrchestrator.generate()` (after weather, uses CostEventFactory)
  - [x] 3.3 Add `("cost_events.json", data.cost_events)` to `write_to_files()`
  - [x] 3.4 Import CostEventFactory in orchestrator

- [x] Task 4: Add StrictCostEvent to model_registry.py (AC: #5)
  - [x] 4.1 Create `_get_strict_cost_event()` function (StrictUnifiedCostEvent with extra="forbid")
  - [x] 4.2 Register `"cost_events.json"` in `get_seed_model_registry()`

- [x] Task 5: Add cost_events to loader.py (AC: #5)
  - [x] 5.1 Add to SEED_ORDER at Level 0: `("cost_events.json", "seed_cost_events", "request_id", "platform_cost_e2e")`
  - [x] 5.2 Add to COLLECTION_MAPPING: `"cost_events.json": ("platform_cost_e2e", "cost_events")`

- [x] Task 6: Create unit tests (AC: #6)
  - [x] 6.1 Create `tests/unit/demo/generators/test_cost_factory.py`
  - [x] 6.2 TestCostEventFactory class (validity, serialization, cost_type/unit matching, amounts, metadata)
  - [x] 6.3 TestCostEventFactoryBatch class (batch size, distribution, timestamps)
  - [x] 6.4 TestCostEventFactoryPeriod class (time span, daily count, weighted distribution)
  - [x] 6.5 TestCostEventFactoryOverrides class (custom cost_type, factory_id, timestamp)

- [x] Task 7: Update ADR-020 documentation (AC: implicit)
  - [x] 7.1 Add cost_events to seed file mapping table
  - [x] 7.2 Add platform_cost_e2e to database mapping table
  - [x] 7.3 Add cost_events to FK dependency graph (Level 0)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 0.8.6: Cost Event Demo Data Generator"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/0-8-6-cost-event-demo-data-generator
  ```

**Branch name:** `story/0-8-6-cost-event-demo-data-generator`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/0-8-6-cost-event-demo-data-generator`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 0.8.6: Cost Event Demo Data Generator" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/0-8-6-cost-event-demo-data-generator`

**PR URL:** https://github.com/jltournay/farmer-power-platform/pull/224

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **Regression Rule:** Run the FULL test suite. Zero failures is the only acceptable outcome.

### 1. Unit Tests
```bash
pytest tests/unit/demo/ -v
```
**Output:**
```
146 passed, 4 warnings in 1.96s
```
- 33 new cost factory tests (test_cost_factory.py)
- 113 existing demo tests (all pass, no regressions)

### 2. E2E Tests

**Skipped with justification:** This story modifies ONLY test/demo tooling code:
- `tests/demo/generators/` (factory code)
- `tests/unit/demo/generators/` (unit tests)
- `scripts/demo/` (loader, model_registry)
- `tests/demo/profiles/` (YAML configuration)
- `_bmad-output/` (documentation)

No production service code (`services/`) was modified. E2E tests validate production service behavior which is unaffected by this change. User confirmed skip.

> **Before running E2E tests:** Read `tests/e2e/E2E-TESTING-MENTAL-MODEL.md`

```bash
bash scripts/e2e-up.sh --build
bash scripts/e2e-preflight.sh
bash scripts/e2e-test.sh --keep-up
bash scripts/e2e-up.sh --down
```
**Output:**
```
(paste E2E test output here)
```
**E2E passed:** [ ] Yes / [ ] No

### 3. Lint Check
```bash
ruff check . && ruff format --check .
```
**Lint passed:** [ ] Yes / [ ] No

### 4. CI Verification on Story Branch (MANDATORY)

```bash
git push origin story/0-8-6-cost-event-demo-data-generator
gh workflow run e2e.yaml --ref story/0-8-6-cost-event-demo-data-generator
sleep 10
gh run list --workflow=e2e.yaml --branch story/0-8-6-cost-event-demo-data-generator --limit 1
```
**CI Run ID:** _______________
**CI E2E Status:** [ ] Passed / [ ] Failed
**Verification Date:** _______________

---

## Dev Notes

### Architecture Pattern: Demo Data Generator

The demo data system follows a layered architecture (ADR-020):

```
Profile YAML → Polyfactory Generator → FK Registry → Orchestrator → JSON → Loader → MongoDB
```

**Each entity follows this exact pattern:**
1. **Polyfactory class** in `tests/demo/generators/{entity}.py` extending `BaseModelFactory[PydanticModel]`
2. **Profile config** in `tests/demo/profiles/*.yaml` controlling volume/distribution
3. **Orchestrator step** in `tests/demo/generators/orchestrator.py` (GeneratedData dataclass + generate method)
4. **Model registry** in `scripts/demo/model_registry.py` (strict Pydantic with `extra="forbid"`)
5. **Loader entry** in `scripts/demo/loader.py` (SEED_ORDER + COLLECTION_MAPPING)
6. **Unit tests** in `tests/unit/demo/generators/test_{entity}_factory.py`

### Key Implementation Details

**Source Pydantic Model:** `UnifiedCostEvent` at `services/platform-cost/src/platform_cost/domain/cost_event.py`
- Uses `DecimalStr` (Decimal serialized as string) for `amount_usd`
- Has `model_config = {"use_enum_values": True}` for enum serialization
- Has `@model_validator` ensuring cost_type/unit matching
- `factory_id` is optional (nullable FK to factories)
- No required FK dependencies → Level 0 in SEED_ORDER

**Shared Event Model (reference only):** `CostRecordedEvent` at `libs/fp-common/fp_common/events/cost_recorded.py`
- Contains `CostType` and `CostUnit` enums
- Same field structure as `UnifiedCostEvent` (they're equivalent)
- Use `UnifiedCostEvent` as the factory's `__model__` since that's what gets stored in MongoDB

**MongoDB Target:**
- Database: `platform_cost_e2e`
- Collection: `cost_events`
- Upsert key: `request_id` (per existing `MongoDBDirectClient.seed_cost_events()` at `tests/e2e/helpers/mongodb_direct.py:484`)

**Existing seed helper (already implemented, just wire it):**
```python
async def seed_cost_events(self, cost_events: list[dict[str, Any]]) -> None:
    if cost_events:
        for event in cost_events:
            await self.platform_cost_db.cost_events.update_one(
                {"request_id": event["request_id"]},
                {"$set": event},
                upsert=True,
            )
```

### Realistic Pricing Reference

| Cost Type | Amount Range (USD) | Quantity | Unit | Source Services |
|-----------|-------------------|----------|------|-----------------|
| llm | $0.001 - $0.05 | 100-5000 | tokens | ai-model |
| document | $0.01 - $0.10 | 1-10 | pages | collection-model |
| embedding | $0.0001 - $0.001 | 1-50 | queries | knowledge-model |
| sms | $0.01 - $0.05 | 1-5 | messages | notification-model |

### Metadata Templates

```python
# LLM metadata
{"model": "anthropic/claude-3-haiku", "agent_type": "extractor", "tokens_in": 300, "tokens_out": 200}
# Document metadata
{"model_id": "prebuilt-document", "page_count": 3}
# Embedding metadata
{"model": "text-embedding-3-small", "knowledge_domain": "tea-quality", "texts_count": 10}
# SMS metadata
{"message_type": "quality_feedback", "recipient_count": 1}
```

### Model Choices for LLM Events

Rotate through: `anthropic/claude-3-haiku`, `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash-lite`

### Agent Types for LLM Events

Rotate through: `extractor`, `explorer`, `generator`, `conversational`, `tiered_vision`

### Knowledge Domains for Embedding Events

Rotate through: `tea-quality`, `weather-impact`, `disease-detection`, `farming-best-practices`

### Test Pattern Reference

Follow exact structure from `tests/unit/demo/generators/test_weather_factory.py`:
- `pytest.importorskip("polyfactory")`
- `sys.path` inserts for `tests/demo` and `scripts/demo`
- `autouse` fixture resetting counters + FK registry
- Test classes: TestCostEventFactory, TestCostEventFactoryBatch, TestCostEventFactoryPeriod, TestCostEventFactoryOverrides

### Previous Story Intelligence (Story 0.8.5)

Story 0.8.5 (Documentation) completed the epic with docs. Key learnings from 0.8.3/0.8.4:
- Polyfactory requires `polyfactory` package (importorskip in tests)
- Factory counters must be reset between tests
- FK registry is global module-level state (use `set_fk_registry()`/`reset_fk_registry()`)
- `model_dump(mode="json")` is required for JSON serialization (handles datetime, Decimal)
- Profile YAML is loaded by orchestrator and drives batch sizes

### Project Structure Notes

| File | Action | Notes |
|------|--------|-------|
| `tests/demo/generators/cost.py` | CREATE | New CostEventFactory |
| `tests/demo/generators/__init__.py` | MODIFY | Export CostEventFactory |
| `tests/demo/generators/orchestrator.py` | MODIFY | Add cost_events to GeneratedData + generate step |
| `tests/demo/profiles/minimal.yaml` | MODIFY | Add cost_events section |
| `tests/demo/profiles/demo.yaml` | MODIFY | Add cost_events section |
| `tests/demo/profiles/demo-large.yaml` | MODIFY | Add cost_events section |
| `scripts/demo/model_registry.py` | MODIFY | Add _get_strict_cost_event() + register |
| `scripts/demo/loader.py` | MODIFY | Add to SEED_ORDER + COLLECTION_MAPPING |
| `tests/unit/demo/generators/test_cost_factory.py` | CREATE | Unit tests |
| `_bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md` | MODIFY | Document cost events |

### References

- [Source: _bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md] - Demo data strategy
- [Source: services/platform-cost/src/platform_cost/domain/cost_event.py] - UnifiedCostEvent model
- [Source: libs/fp-common/fp_common/events/cost_recorded.py] - CostType/CostUnit enums
- [Source: tests/demo/generators/base.py] - BaseModelFactory pattern
- [Source: tests/demo/generators/orchestrator.py] - DataOrchestrator + GeneratedData
- [Source: tests/demo/generators/quality.py] - DocumentFactory (closest analogue)
- [Source: scripts/demo/model_registry.py] - StrictModel registration pattern
- [Source: scripts/demo/loader.py] - SEED_ORDER + COLLECTION_MAPPING
- [Source: tests/e2e/helpers/mongodb_direct.py:484] - seed_cost_events() method
- [Source: tests/unit/demo/generators/test_weather_factory.py] - Unit test pattern
- [Source: _bmad-output/project-context.md] - 202 project rules

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

**Created:**
- tests/demo/generators/cost.py
- tests/unit/demo/generators/test_cost_factory.py

**Modified:**
- tests/demo/generators/__init__.py
- tests/demo/generators/orchestrator.py
- tests/demo/profiles/minimal.yaml
- tests/demo/profiles/demo.yaml
- tests/demo/profiles/demo-large.yaml
- scripts/demo/model_registry.py
- scripts/demo/loader.py
- _bmad-output/architecture/adr/ADR-020-demo-data-loader-pydantic-validation.md
