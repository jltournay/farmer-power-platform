# Epic 1 Retrospective: Farmer Registration & Data Foundation

**Date:** 2025-12-29
**Epic:** 1 - Farmer Registration & Data Foundation
**Status:** Complete (9/9 stories done)
**Facilitator:** Bob (Scrum Master)

---

## Epic Summary

| Story | Description | Status | Tests | GitHub Issue |
|-------|-------------|--------|-------|--------------|
| 1-1 | Plantation Model Service Setup | Done | ~20 | - |
| 1-2 | Factory and Collection Point Management | Done | 106 | - |
| 1-3 | Farmer Registration | Done | 215 | - |
| 1-4 | Farmer Performance History Structure | Done | 90 | - |
| 1-5 | Farmer Communication Preferences | Done | 16 | #12 |
| 1-6 | Plantation Model MCP Server | Done | 12 | #13 |
| 1-7 | Quality Grading Event Subscription | Done | 38 | #24 |
| 1-8 | Region Entity & Weather Configuration | Done | 130 | #25 |
| 1-9 | Factory Payment Policy Configuration | Done | 24 | #26 |

**Deliverables:**
- Complete Plantation Model service with 6 domain entities
- 10+ MCP tools for AI agent integration
- Event subscription for quality grading from Collection Model
- ~450 tests (unit + integration + MCP)
- gRPC API with proper error handling
- MongoDB repositories with async Motor client
- Dapr Pub/Sub integration for domain events

---

## What Went Well

### 1. Domain-Driven Design Maturity
- Clear entity separation: Factory, CollectionPoint, Farmer, GradingModel, FarmerPerformance, Region
- Value objects encapsulate complexity: GeoLocation, ContactInfo, OperatingHours, PaymentPolicy, QualityThresholds, FlushCalendar
- Model-driven grading: Grade labels from GradingModel, never hardcoded

### 2. Test Coverage Excellence
- Started at ~20 tests (Story 1.1) and grew to ~450 tests total
- Integration tests validate full CRUD flows via gRPC
- MCP server tests validate tool responses with JSON schemas
- Code review process consistently caught missing tests (Story 1.4, 1.7)

### 3. MCP Server Foundation (Story 1.6)
- First MCP server in platform established reusable patterns
- 10+ tools implemented: get_farmer, get_farmer_summary, get_collection_points, get_farmers_by_collection_point, get_factory, get_region, list_regions, get_current_flush, get_region_weather
- Tool handler pattern with DAPR service invocation validated
- Kubernetes deployment with HPA (min 2, max 10 replicas)

### 4. Event-Driven Architecture (Story 1.7)
- `collection.quality_result.received` event subscription implemented
- Two domain events emitted: `plantation.quality.graded`, `plantation.performance_updated`
- Atomic MongoDB updates using `$inc` for counters
- QualityThresholds value object enables factory-specific quality tiers

### 5. Design Review Process (Story 1.5)
- Party Mode discussion identified semantic confusion in `pref_channel`
- Split into `notification_channel` (PUSH) vs `interaction_pref` (CONSUME)
- Low-literacy farmer scenario properly modeled (SMS + voice)
- Demonstrates value of collaborative design review

### 6. Region Entity Complexity Handled (Story 1.8)
- Geography, FlushCalendar, WeatherConfig, Agronomic value objects
- FlushCalculator handles year-spanning dormant periods (Dec-Feb)
- 130 tests ensure correctness across edge cases
- Weather data integration with Open-Meteo API prepared

---

## Challenges Encountered

### 1. Code Review Catches Missing Tests
- **Story 1.4:** Tasks 8.5-8.8 marked [x] but test files did not exist
- **Resolution:** Code review process is critical - added `test_grpc_grading_model.py` and `test_grpc_farmer_summary.py`
- **Learning:** Tasks marked complete must have corresponding test evidence

### 2. Region Assignment Bug (Story 1.3)
- **Issue:** Missing `elif` condition for Kericho county caused unconditional overwrite
- **Impact:** All region assignments for Nyeri coordinates broken
- **Root Cause:** Insufficient boundary testing for coordinate-based logic
- **Fix:** Added proper conditional bounds for each county

### 3. Default Value Duplication (Story 1.2)
- **Issue:** Hardcoded defaults like `"06:00-10:00"` in service layer duplicated domain model defaults
- **Resolution:** Use domain model defaults via `OperatingHours().weekdays`
- **Learning:** DRY principle - single source of truth for defaults

### 4. Operating Hours Validation Gap (Story 1.2)
- **Issue:** No validation on time range format allowed `"hello-world"`
- **Resolution:** Added field_validator with regex pattern
- **Learning:** String fields need format validation

### 5. Proto Field Numbering (Story 1.5, 1.9)
- **Issue:** Multiple stories adding fields to same proto message
- **Resolution:** Careful coordination of field numbers (16-18 for preferences)
- **Learning:** Track proto field assignments across stories

### 6. FlushCalculator Edge Case (Story 1.8)
- **Issue:** Dormant period spanning year boundary (Dec 1 - Feb 28) not handled
- **Resolution:** `_is_in_dormant_period()` helper with year-spanning logic
- **Learning:** Calendar-based logic needs explicit boundary testing

---

## Key Insights

### Architecture Patterns Validated

1. **Value Object Pattern** - Encapsulating complex nested data (GPS, ContactInfo, PaymentPolicy) improves maintainability
2. **gRPC Error Handling** - Consistent use of NOT_FOUND, ALREADY_EXISTS, INVALID_ARGUMENT with descriptive messages
3. **MCP Tool Pattern** - Tool handlers dictionary with DAPR service invocation enables clean AI agent integration
4. **Event Subscription Pattern** - DAPR Pub/Sub with Pydantic event models ensures type safety

### Testing Patterns Established

1. **Mock MongoDB** - Use `MockMongoClient` from root `conftest.py`, never override in local conftest
2. **gRPC Testing** - Use `AsyncMock` for context.abort, validate status codes and messages
3. **MCP Testing** - Validate tool responses against JSON schemas
4. **Integration Testing** - Full CRUD flows via gRPC client with real MongoDB (docker-compose)

### Process Improvements

1. **Code Review** - Adversarial review catches bugs and missing tests before merge
2. **Party Mode** - Cross-agent discussion improves design quality (Story 1.5 preference split)
3. **Story File Documentation** - Dev Agent Record with file list enables easy handoff

---

## Learnings Carry-Forward from Epic 0

| Epic 0 Learning | Applied in Epic 1 |
|-----------------|-------------------|
| Centralize configuration | All ruff settings in root pyproject.toml |
| Document dependencies explicitly | CI PYTHONPATH updated for plantation-model |
| Version consistency | Python 3.11 maintained across all stories |
| Test infrastructure changes locally | Integration tests run locally before push |

---

## Action Items

### Resolved from Previous Retrospective

| Action | Status |
|--------|--------|
| Implement deferred MongoDB integration tests | Done (via Story 0-2) |
| Add test count verification to code review | Done |
| Document gRPC testing patterns | Done (in fp-testing) |

### New Process Improvements

| Action | Owner | Status |
|--------|-------|--------|
| Code review MUST verify test file existence for marked tasks | Dev/SM | Implemented |
| Add boundary tests for coordinate/calendar logic | Dev | Implemented |
| Track proto field assignments in story files | SM | Implemented |

### Technical Patterns Documented

| Pattern | Location |
|---------|----------|
| Value object encapsulation | Story 1.2, 1.8, 1.9 |
| MCP server implementation | Story 1.6 |
| Event subscription | Story 1.7 |
| gRPC error handling | Story 1.2, 1.3 |

### Team Agreements

- All gRPC methods must validate inputs and return descriptive error messages
- Domain model defaults are the single source of truth (DRY)
- MCP tools must include grading_model reference for label display
- Event payloads include sufficient context for downstream processing

---

## Epic 1 Metrics

| Metric | Value |
|--------|-------|
| Stories Completed | 9/9 (100%) |
| Total Tests | ~450 |
| Domain Entities | 6 |
| MCP Tools | 10+ |
| Value Objects | 10+ |
| Domain Events | 3 (farmer.registered, quality.graded, performance_updated) |
| Code Review Issues Found | 20+ |
| Code Review Issues Fixed | 20+ |
| Design Revisions | 1 (Story 1.5) |

---

## Next Epic Preparation

**Epic 0.5: Frontend & Identity Infrastructure** is the next priority (P1).

**Dependencies Satisfied:**
- Plantation Model MCP Server ready for BFF consumption
- gRPC API stable for frontend integration
- Domain events ready for Notification Model

**Key Considerations for Epic 0.5:**
- Shared component library (@fp/ui-components) needs TBK color palette
- Azure AD B2C configuration for authentication
- BFF service will consume Plantation Model via DAPR
- Factory Portal scaffold will use MCP tools indirectly

**Stories in Epic 0.5:**
1. 0.5.1: Shared Component Library Setup
2. 0.5.2: Azure AD B2C Configuration
3. 0.5.3: Shared Auth Library
4. 0.5.4: Factory Portal Scaffold
5. 0.5.5: BFF Authentication Middleware
6. 0.5.6: BFF Service Setup

**No blockers identified.**

---

## Participants

- Bob (Scrum Master) - Facilitator
- Alice (Product Owner) - Business perspective
- Charlie (Senior Dev) - Technical lead
- Dana (QA Engineer) - Quality perspective
- Elena (Junior Dev) - Fresh perspective
- Jeanlouistournay (Project Lead) - Overall direction

---

*Generated with BMAD Retrospective Workflow*
*Updated: 2025-12-29 (Final - All 9 stories complete)*
