# Story 1.9: Factory Payment Policy Configuration

**Status:** done
**GitHub Issue:** #26

---

## Story

As a **factory administrator**,
I want to configure payment policies for my factory,
So that farmers receive quality-based payment adjustments according to our chosen incentive model.

---

## Context: Completing Epic 1

This story adds the final piece to Epic 1: **PaymentPolicy** configuration for factories. This enables factories to define quality-based incentive models that external payroll systems can consume via API.

**Business Value:**
- Factories can configure payment incentive models without code changes
- External payroll systems integrate via standard API
- Supports multiple incentive strategies (split, bonus, delayed, feedback-only)

**Dependencies:**
- Story 1.2: Factory and Collection Point Management (Factory entity exists)

**Consumers:**
- Factory Admin UI (Epic 3, Story 3.8) - display and edit payment policies
- External payroll systems - retrieve policy via `get_factory` API/MCP

---

## Acceptance Criteria

1. **Given** the Plantation Model service is running
   **When** I create or update a factory
   **Then** the factory can include a `payment_policy` with:
     - `policy_type`: one of `"split_payment"`, `"weekly_bonus"`, `"delayed_payment"`, `"feedback_only"`
     - `tier_1_adjustment`: percentage adjustment for Premium tier (e.g., +0.15 for +15%)
     - `tier_2_adjustment`: percentage adjustment for Standard tier (typically 0.0 for base rate)
     - `tier_3_adjustment`: percentage adjustment for Acceptable tier (e.g., -0.05 for -5%)
     - `below_tier_3_adjustment`: percentage adjustment for Below Standard (e.g., -0.10 for -10%)

2. **Given** a factory has no `payment_policy` configured
   **When** the factory is queried
   **Then** default values are returned: `policy_type="feedback_only"`, all adjustments = 0.0

3. **Given** a factory has `payment_policy` configured
   **When** an AI agent calls `get_factory(factory_id)` via MCP
   **Then** the response includes the full `payment_policy` configuration

4. **Given** a factory exists
   **When** I update only the `payment_policy`
   **Then** the changes are persisted and returned in subsequent queries
   **And** `updated_at` timestamp is refreshed

5. **Given** invalid adjustment values are provided (e.g., > 1.0 or < -1.0)
   **When** I attempt to save the configuration
   **Then** validation fails with appropriate error message

---

## Tasks / Subtasks

- [x] **Task 1: Create PaymentPolicy value object** (AC: #1, #2, #5)
  - [x] 1.1 Create `PaymentPolicyType` enum: `split_payment`, `weekly_bonus`, `delayed_payment`, `feedback_only`
  - [x] 1.2 Create `PaymentPolicy` value object in `domain/models/value_objects.py`
  - [x] 1.3 Add `tier_1_adjustment`, `tier_2_adjustment`, `tier_3_adjustment`, `below_tier_3_adjustment` fields
  - [x] 1.4 Add field validators: all adjustments must be between -1.0 and 1.0
  - [x] 1.5 Set defaults: `policy_type=feedback_only`, all adjustments = 0.0
  - [x] 1.6 Unit tests for PaymentPolicy validation

- [x] **Task 2: Update Factory entity** (AC: #1, #2, #4)
  - [x] 2.1 Add `payment_policy: PaymentPolicy` field to `Factory` entity with default factory
  - [x] 2.2 Add `payment_policy` to `FactoryCreate` DTO (optional)
  - [x] 2.3 Add `payment_policy` to `FactoryUpdate` DTO (optional)
  - [x] 2.4 Update Factory model_config example to include payment_policy
  - [x] 2.5 Unit tests for Factory with payment_policy

- [x] **Task 3: Update Proto definitions** (AC: #1, #3)
  - [x] 3.1 Add `PaymentPolicyType` enum to `plantation.proto`
  - [x] 3.2 Add `PaymentPolicy` message with all fields
  - [x] 3.3 Add `payment_policy` field to `Factory` message
  - [x] 3.4 Add `payment_policy` to `CreateFactoryRequest` message
  - [x] 3.5 Add `payment_policy` to `UpdateFactoryRequest` message
  - [x] 3.6 Regenerate Python stubs via `scripts/proto-gen.sh`

- [x] **Task 4: Update gRPC handlers** (AC: #1, #3, #4)
  - [x] 4.1 Update `CreateFactory` handler to accept payment_policy
  - [x] 4.2 Update `UpdateFactory` handler to accept payment_policy
  - [x] 4.3 Ensure `GetFactory` returns payment_policy (already returns full Factory)
  - [x] 4.4 Verify `updated_at` is refreshed on payment_policy update
  - [x] 4.5 Integration test for factory with payment_policy (covered by existing gRPC tests)

- [x] **Task 5: Update MCP tool description** (AC: #3)
  - [x] 5.1 Update `get_factory` tool description to mention payment_policy
  - [x] 5.2 MCP tool implementation already returns full Factory (no handler changes needed)
  - [x] 5.3 Unit test verifying payment_policy in MCP response (covered by existing MCP tests)

---

## Dev Notes

### Service Location

All code modifications are in the existing Plantation Model service:

```
services/plantation-model/
├── src/plantation_model/
│   ├── domain/
│   │   └── models/
│   │       ├── value_objects.py        # MODIFY - add PaymentPolicyType, PaymentPolicy
│   │       └── factory.py              # MODIFY - add payment_policy field
│   └── api/
│       └── plantation_service.py       # MODIFY - payment_policy in handlers (already passing full objects)
```

### PaymentPolicy Value Object Design

```python
# In domain/models/value_objects.py

from enum import Enum

class PaymentPolicyType(str, Enum):
    """Payment incentive model types."""

    SPLIT_PAYMENT = "split_payment"      # Pay base rate + quality adjustment per delivery
    WEEKLY_BONUS = "weekly_bonus"        # Base rate per delivery, weekly quality bonus
    DELAYED_PAYMENT = "delayed_payment"  # Full payment after quality assessment
    FEEDBACK_ONLY = "feedback_only"      # No payment adjustment, quality info only (default)


class PaymentPolicy(BaseModel):
    """Factory-configurable payment policy for quality-based incentives.

    Adjustments are percentage modifiers applied to base rate:
    - tier_1_adjustment: +0.15 means +15% for Premium tier
    - tier_2_adjustment: 0.0 means base rate for Standard tier
    - tier_3_adjustment: -0.05 means -5% for Acceptable tier
    - below_tier_3_adjustment: -0.10 means -10% for Below Standard

    Payment calculation is EXTERNAL - factory payroll systems consume this via API.
    Farmer Power Platform does NOT perform actual payment processing.
    """

    policy_type: PaymentPolicyType = Field(
        default=PaymentPolicyType.FEEDBACK_ONLY,
        description="Payment incentive model type",
    )
    tier_1_adjustment: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Premium tier adjustment (-1.0 to 1.0)",
    )
    tier_2_adjustment: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Standard tier adjustment (-1.0 to 1.0)",
    )
    tier_3_adjustment: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Acceptable tier adjustment (-1.0 to 1.0)",
    )
    below_tier_3_adjustment: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Below Standard adjustment (-1.0 to 1.0)",
    )
```

### Proto Definition

```protobuf
// In proto/plantation/v1/plantation.proto

// Payment incentive model types
enum PaymentPolicyType {
  PAYMENT_POLICY_TYPE_UNSPECIFIED = 0;
  PAYMENT_POLICY_TYPE_SPLIT_PAYMENT = 1;    // Base + quality adjustment per delivery
  PAYMENT_POLICY_TYPE_WEEKLY_BONUS = 2;     // Base per delivery, weekly bonus
  PAYMENT_POLICY_TYPE_DELAYED_PAYMENT = 3;  // Full payment after quality assessment
  PAYMENT_POLICY_TYPE_FEEDBACK_ONLY = 4;    // No payment adjustment (default)
}

// Factory payment policy configuration (Story 1.9)
// Adjustments are percentage modifiers (-1.0 to +1.0) applied to base rate
// Payment calculation is EXTERNAL - consumed by factory payroll systems via API
message PaymentPolicy {
  PaymentPolicyType policy_type = 1;
  double tier_1_adjustment = 2;     // Premium tier adjustment
  double tier_2_adjustment = 3;     // Standard tier adjustment
  double tier_3_adjustment = 4;     // Acceptable tier adjustment
  double below_tier_3_adjustment = 5;  // Below Standard adjustment
}

// Update Factory message to include payment_policy
message Factory {
  // ... existing fields ...
  PaymentPolicy payment_policy = 12;  // Story 1.9: Payment incentive configuration
}
```

### Factory Entity Update

```python
# In domain/models/factory.py

from plantation_model.domain.models.value_objects import (
    ContactInfo, GeoLocation, QualityThresholds, PaymentPolicy
)

class Factory(BaseModel):
    # ... existing fields ...
    payment_policy: PaymentPolicy = Field(
        default_factory=PaymentPolicy,
        description="Payment incentive policy configuration",
    )
```

### MCP Tool Update

Update tool description in `mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py`:

```python
"get_factory": ToolDefinition(
    name="get_factory",
    description=(
        "Get factory details by ID. Returns name, code, region, location, "
        "processing capacity, quality thresholds (tier_1, tier_2, tier_3), "
        "and payment policy (policy_type, tier adjustments)."  # Updated
    ),
    # ... rest unchanged
),
```

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**
- `test_payment_policy.py` - PaymentPolicy validation (bounds, defaults, types)
- `test_factory.py` - Update existing tests to verify payment_policy field

**Integration Tests (`tests/integration/`):**
- `test_factory_repository_mongodb.py` - Factory CRUD with payment_policy

**MCP Tests (`tests/unit/plantation_mcp/`):**
- `test_mcp_service.py` - Verify get_factory returns payment_policy

### Critical Implementation Rules

**From project-context.md:**

1. **Pydantic 2.0 syntax** - Use `Field(ge=-1.0, le=1.0)` for bounds validation
2. **ALL I/O operations MUST be async** - Repository operations
3. **Use Enum for policy_type** - NOT string literals
4. **Default factory** - Use `default_factory=PaymentPolicy` not `default=PaymentPolicy()`
5. **No payment calculation** - Platform stores policy, external systems calculate payments

### Previous Story Patterns to Follow

**From Story 1.8 (Region Entity):**
- Value object organization in `value_objects.py` with clear enum
- Field validation using Pydantic `Field(ge=..., le=...)`
- Proto message organization with enum first, then message
- Unit test naming: `test_{value_object}.py`

**From Story 1.7 (Quality Grading):**
- QualityThresholds pattern - similar tiered structure
- Field validators using `@field_validator` for cross-field validation
- Integration with Factory entity

### Common Pitfalls to Avoid

1. **DO NOT** implement payment calculation logic - external systems do this
2. **DO NOT** use string literals for policy_type - use enum
3. **DO NOT** forget `default_factory=PaymentPolicy` - required for mutable defaults
4. **DO NOT** add fields to gRPC handlers that already pass full objects
5. **DO** regenerate proto stubs after updating .proto file

### File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `domain/models/value_objects.py` | ADD | PaymentPolicyType enum, PaymentPolicy class |
| `domain/models/factory.py` | MODIFY | Add payment_policy field to Factory, FactoryCreate, FactoryUpdate |
| `proto/plantation/v1/plantation.proto` | MODIFY | Add PaymentPolicyType enum, PaymentPolicy message, update Factory |
| `libs/fp-proto/src/fp_proto/plantation/v1/*.py` | REGENERATE | Proto stubs |
| `mcp-servers/plantation-mcp/.../definitions.py` | MODIFY | Update get_factory description |
| `tests/unit/plantation/test_payment_policy.py` | ADD | PaymentPolicy unit tests |
| `tests/unit/plantation/test_factory.py` | MODIFY | Add payment_policy test cases |

### References

- [Source: _bmad-output/epics/epic-1-plantation-model.md#Story 1.9] - Acceptance criteria
- [Source: _bmad-output/project-context.md#Pydantic 2.0 Patterns] - Pydantic syntax rules
- [Source: _bmad-output/project-context.md#Code Design Principles] - Value object design
- [Source: services/plantation-model/src/plantation_model/domain/models/value_objects.py] - Existing value objects pattern
- [Source: services/plantation-model/src/plantation_model/domain/models/factory.py] - Factory entity structure
- [Source: _bmad-output/sprint-artifacts/1-7-quality-grading-event-subscription.md] - QualityThresholds pattern
- [Source: proto/plantation/v1/plantation.proto] - Proto definitions

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Added `PaymentPolicyType` enum with 4 policy types: split_payment, weekly_bonus, delayed_payment, feedback_only
- Added `PaymentPolicy` value object with tier adjustments (-1.0 to 1.0 bounds validation)
- Updated Factory, FactoryCreate, FactoryUpdate models with payment_policy field
- Added PaymentPolicyType enum and PaymentPolicy message to plantation.proto
- Updated Factory, CreateFactoryRequest, UpdateFactoryRequest proto messages
- Regenerated Python proto stubs via proto-gen.sh
- Added _proto_to_payment_policy helper for gRPC proto-to-domain conversion
- Updated _factory_to_proto to include payment_policy in response
- Updated CreateFactory and UpdateFactory handlers to accept payment_policy
- Updated MCP get_factory tool description to mention payment_policy
- All 435 plantation unit tests passing
- All 16 gRPC factory tests passing (4 new payment_policy tests)
- All 24 MCP service tests passing (3 new get_factory/payment_policy tests)
- All 33 factory model tests passing (including 14 new PaymentPolicy tests)

### File List

**Modified:**
- services/plantation-model/src/plantation_model/domain/models/value_objects.py
- services/plantation-model/src/plantation_model/domain/models/factory.py
- services/plantation-model/src/plantation_model/api/plantation_service.py
- proto/plantation/v1/plantation.proto
- libs/fp-proto/src/fp_proto/plantation/v1/plantation_pb2.py
- libs/fp-proto/src/fp_proto/plantation/v1/plantation_pb2.pyi
- mcp-servers/plantation-mcp/src/plantation_mcp/tools/definitions.py
- tests/unit/plantation/test_factory_model.py
- tests/unit/plantation/test_grpc_factory.py
- mcp-servers/plantation-mcp/tests/unit/test_mcp_service.py

### Change Log

- 2025-12-29: Story 1.9 implementation complete - PaymentPolicy value object, Factory entity update, proto definitions, gRPC handlers, MCP tool description
- 2025-12-29: Code review fixes - Added 4 gRPC tests and 3 MCP tests for payment_policy, corrected file list
