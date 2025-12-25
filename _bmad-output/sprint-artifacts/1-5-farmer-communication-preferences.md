# Story 1.5: Farmer Communication Preferences

**Status:** done
**GitHub Issue:** #12

---

## Story

As a **farmer**,
I want to set my preferred communication channel and language,
So that I receive feedback in a way I can understand.

---

## Acceptance Criteria

1. **Given** a farmer is registered
   **When** the farmer record is created
   **Then** default preferences are set: notification_channel = "sms", interaction_pref = "text", pref_lang = "sw" (Swahili)

2. **Given** a farmer exists
   **When** I update communication preferences via API
   **Then** notification_channel can be set to: "sms", "whatsapp" (how we PUSH notifications)
   **And** interaction_pref can be set to: "text", "voice" (how farmer CONSUMES information)
   **And** pref_lang can be set to: "sw" (Swahili), "ki" (Kikuyu), "luo" (Luo), "en" (English)
   **And** changes are persisted immediately

3. **Given** a farmer's preferences are updated
   **When** the Notification Model queries farmer preferences
   **Then** the current notification_channel, interaction_pref, and pref_lang are returned

4. **Given** an invalid preference value is provided
   **When** I attempt to update preferences
   **Then** the update fails with validation error listing valid options

---

## Tasks / Subtasks

- [x] **Task 1: Add Communication Preference Enums** (AC: #1, #2, #4)
  - [x] 1.1 Create `PreferredChannel` enum: "sms", "whatsapp", "voice"
  - [x] 1.2 Create `PreferredLanguage` enum: "sw", "ki", "luo", "en"
  - [x] 1.3 Add human-readable labels for each language (e.g., sw = "Swahili")

- [x] **Task 2: Update Farmer Domain Model** (AC: #1, #2)
  - [x] 2.1 Add `pref_channel: PreferredChannel` field with default "sms"
  - [x] 2.2 Add `pref_lang: PreferredLanguage` field with default "sw"
  - [x] 2.3 Update `FarmerUpdate` model to include optional preference fields
  - [x] 2.4 Update model_config example to include preferences

- [x] **Task 3: Update Proto Definitions** (AC: #1, #2, #3)
  - [x] 3.1 Add `PreferredChannel` enum to plantation.proto
  - [x] 3.2 Add `PreferredLanguage` enum to plantation.proto
  - [x] 3.3 Add `pref_channel` and `pref_lang` fields to `Farmer` message
  - [x] 3.4 Add `pref_channel` and `pref_lang` fields to `FarmerSummary` message
  - [x] 3.5 Add `UpdateCommunicationPreferencesRequest` message
  - [x] 3.6 Add `UpdateCommunicationPreferencesResponse` message
  - [x] 3.7 Add `UpdateCommunicationPreferences` RPC to PlantationService
  - [x] 3.8 Regenerate Python stubs via `./scripts/proto-gen.sh`

- [x] **Task 4: Implement UpdateCommunicationPreferences gRPC Method** (AC: #2, #3, #4)
  - [x] 4.1 Add `UpdateCommunicationPreferences` to PlantationServiceServicer
  - [x] 4.2 Validate farmer_id exists (return NOT_FOUND if not)
  - [x] 4.3 Validate pref_channel is one of: sms, whatsapp, voice
  - [x] 4.4 Validate pref_lang is one of: sw, ki, luo, en
  - [x] 4.5 Return INVALID_ARGUMENT with descriptive message for invalid values
  - [x] 4.6 Update farmer document with new preferences
  - [x] 4.7 Return updated Farmer in response

- [x] **Task 5: Update CreateFarmer to Set Defaults** (AC: #1)
  - [x] 5.1 Modify CreateFarmer in PlantationServiceServicer to set defaults
  - [x] 5.2 Set pref_channel = "sms" on new farmer creation
  - [x] 5.3 Set pref_lang = "sw" on new farmer creation
  - [x] 5.4 Allow optional override via CreateFarmerRequest (if proto supports it)

- [x] **Task 6: Update FarmerRepository** (AC: #2)
  - [x] 6.1 Update `update()` method to handle preference field updates
  - [x] 6.2 Add `update_preferences()` convenience method (optional)

- [x] **Task 7: Write Unit Tests** (AC: #1, #2, #3, #4)
  - [x] 7.1 Test PreferredChannel enum validation
  - [x] 7.2 Test PreferredLanguage enum validation
  - [x] 7.3 Test Farmer model with default preferences
  - [x] 7.4 Test CreateFarmer sets defaults (pref_channel=sms, pref_lang=sw)
  - [x] 7.5 Test UpdateCommunicationPreferences success case
  - [x] 7.6 Test UpdateCommunicationPreferences with invalid channel (INVALID_ARGUMENT)
  - [x] 7.7 Test UpdateCommunicationPreferences with invalid language (INVALID_ARGUMENT)
  - [x] 7.8 Test UpdateCommunicationPreferences farmer not found (NOT_FOUND)
  - [x] 7.9 Test GetFarmer returns preferences
  - [x] 7.10 Test GetFarmerSummary returns preferences

---

## Dev Notes

### Service Location

All code goes in the existing Plantation Model service:

```
services/plantation-model/
├── src/plantation_model/
│   ├── domain/
│   │   ├── models/
│   │   │   ├── farmer.py          # UPDATE - add preference fields + enums
│   │   │   └── ...
│   ├── infrastructure/
│   │   └── repositories/
│   │       ├── farmer_repository.py  # UPDATE - handle preference updates
│   │       └── ...
│   └── api/
│       └── plantation_service.py     # UPDATE - add UpdateCommunicationPreferences RPC
└── ...
```

### Communication Preference Enums

**Source:** [_bmad-output/epics.md - Story 1.5]

```python
# Add to domain/models/farmer.py

class PreferredChannel(str, Enum):
    """Preferred communication channel for farmer notifications.

    Channels:
    - SMS: Text messages via Africa's Talking (most common)
    - WHATSAPP: WhatsApp messages (requires WhatsApp registration)
    - VOICE: Voice IVR calls (for low-literacy farmers)
    """
    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"


class PreferredLanguage(str, Enum):
    """Preferred language for farmer communications.

    Languages supported in Kenya:
    - SW: Swahili (national language, default)
    - KI: Kikuyu (Central Kenya)
    - LUO: Luo (Western Kenya)
    - EN: English (formal communications)
    """
    SWAHILI = "sw"
    KIKUYU = "ki"
    LUO = "luo"
    ENGLISH = "en"

    @classmethod
    def get_display_name(cls, value: str) -> str:
        """Get human-readable language name."""
        names = {
            "sw": "Swahili",
            "ki": "Kikuyu",
            "luo": "Luo",
            "en": "English",
        }
        return names.get(value, value)
```

### Updated Farmer Model

```python
# domain/models/farmer.py - Add these fields to Farmer class

class Farmer(BaseModel):
    # ... existing fields ...

    # Communication preferences (Story 1.5)
    pref_channel: PreferredChannel = Field(
        default=PreferredChannel.SMS,
        description="Preferred communication channel"
    )
    pref_lang: PreferredLanguage = Field(
        default=PreferredLanguage.SWAHILI,
        description="Preferred language for communications"
    )
```

### Updated FarmerUpdate Model

```python
# domain/models/farmer.py - Add to FarmerUpdate class

class FarmerUpdate(BaseModel):
    # ... existing fields ...

    pref_channel: Optional[PreferredChannel] = None
    pref_lang: Optional[PreferredLanguage] = None
```

### Proto Updates Required

Update `proto/plantation/v1/plantation.proto`:

```protobuf
// ============================================================================
// Communication Preference Enums (Story 1.5)
// ============================================================================

enum PreferredChannel {
  PREFERRED_CHANNEL_UNSPECIFIED = 0;
  PREFERRED_CHANNEL_SMS = 1;
  PREFERRED_CHANNEL_WHATSAPP = 2;
  PREFERRED_CHANNEL_VOICE = 3;
}

enum PreferredLanguage {
  PREFERRED_LANGUAGE_UNSPECIFIED = 0;
  PREFERRED_LANGUAGE_SW = 1;   // Swahili
  PREFERRED_LANGUAGE_KI = 2;   // Kikuyu
  PREFERRED_LANGUAGE_LUO = 3;  // Luo
  PREFERRED_LANGUAGE_EN = 4;   // English
}

// Update Farmer message - add fields 16 and 17
message Farmer {
  // ... existing fields 1-15 ...
  PreferredChannel pref_channel = 16;
  PreferredLanguage pref_lang = 17;
}

// Update FarmerSummary message - add preference fields
message FarmerSummary {
  // ... existing fields ...
  PreferredChannel pref_channel = 15;
  PreferredLanguage pref_lang = 16;
}

// New messages for preference updates
message UpdateCommunicationPreferencesRequest {
  string farmer_id = 1;
  PreferredChannel pref_channel = 2;
  PreferredLanguage pref_lang = 3;
}

message UpdateCommunicationPreferencesResponse {
  Farmer farmer = 1;
}

// Add RPC to PlantationService
service PlantationService {
  // ... existing RPCs ...

  // Communication Preferences (Story 1.5)
  rpc UpdateCommunicationPreferences(UpdateCommunicationPreferencesRequest)
      returns (UpdateCommunicationPreferencesResponse);
}
```

### gRPC Implementation Pattern

```python
# api/plantation_service.py

async def UpdateCommunicationPreferences(
    self,
    request: plantation_pb2.UpdateCommunicationPreferencesRequest,
    context: grpc.aio.ServicerContext,
) -> plantation_pb2.UpdateCommunicationPreferencesResponse:
    """Update farmer communication preferences.

    Args:
        request: Contains farmer_id, pref_channel, pref_lang
        context: gRPC context

    Returns:
        Updated Farmer record

    Raises:
        NOT_FOUND: If farmer doesn't exist
        INVALID_ARGUMENT: If channel or language is invalid
    """
    # Validate farmer exists
    farmer = await self._farmer_repo.get_by_id(request.farmer_id)
    if not farmer:
        await context.abort(
            grpc.StatusCode.NOT_FOUND,
            f"Farmer not found: {request.farmer_id}"
        )

    # Validate channel
    valid_channels = {
        plantation_pb2.PREFERRED_CHANNEL_SMS,
        plantation_pb2.PREFERRED_CHANNEL_WHATSAPP,
        plantation_pb2.PREFERRED_CHANNEL_VOICE,
    }
    if request.pref_channel not in valid_channels:
        await context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            f"Invalid channel. Valid options: sms, whatsapp, voice"
        )

    # Validate language
    valid_langs = {
        plantation_pb2.PREFERRED_LANGUAGE_SW,
        plantation_pb2.PREFERRED_LANGUAGE_KI,
        plantation_pb2.PREFERRED_LANGUAGE_LUO,
        plantation_pb2.PREFERRED_LANGUAGE_EN,
    }
    if request.pref_lang not in valid_langs:
        await context.abort(
            grpc.StatusCode.INVALID_ARGUMENT,
            f"Invalid language. Valid options: sw (Swahili), ki (Kikuyu), luo (Luo), en (English)"
        )

    # Map proto enums to domain enums
    channel_map = {
        plantation_pb2.PREFERRED_CHANNEL_SMS: PreferredChannel.SMS,
        plantation_pb2.PREFERRED_CHANNEL_WHATSAPP: PreferredChannel.WHATSAPP,
        plantation_pb2.PREFERRED_CHANNEL_VOICE: PreferredChannel.VOICE,
    }
    lang_map = {
        plantation_pb2.PREFERRED_LANGUAGE_SW: PreferredLanguage.SWAHILI,
        plantation_pb2.PREFERRED_LANGUAGE_KI: PreferredLanguage.KIKUYU,
        plantation_pb2.PREFERRED_LANGUAGE_LUO: PreferredLanguage.LUO,
        plantation_pb2.PREFERRED_LANGUAGE_EN: PreferredLanguage.ENGLISH,
    }

    # Update farmer
    update_data = FarmerUpdate(
        pref_channel=channel_map[request.pref_channel],
        pref_lang=lang_map[request.pref_lang],
    )
    updated_farmer = await self._farmer_repo.update(request.farmer_id, update_data)

    return plantation_pb2.UpdateCommunicationPreferencesResponse(
        farmer=self._farmer_to_proto(updated_farmer)
    )
```

### Validation Error Messages

Provide descriptive error messages that list valid options (AC #4):

| Error Scenario | gRPC Code | Message |
|---------------|-----------|---------|
| Farmer not found | NOT_FOUND | "Farmer not found: {farmer_id}" |
| Invalid channel | INVALID_ARGUMENT | "Invalid channel. Valid options: sms, whatsapp, voice" |
| Invalid language | INVALID_ARGUMENT | "Invalid language. Valid options: sw (Swahili), ki (Kikuyu), luo (Luo), en (English)" |

### Testing Strategy

**Unit Tests (`tests/unit/plantation/`):**

| Test File | Tests |
|-----------|-------|
| `test_farmer_model.py` | Add tests for preference fields, defaults, validation |
| `test_grpc_farmer_preferences.py` (NEW) | UpdateCommunicationPreferences gRPC tests |

**Test Cases Required:**

```python
# test_grpc_farmer_preferences.py

class TestFarmerCommunicationPreferences:
    """Tests for farmer communication preferences (Story 1.5)."""

    @pytest.mark.asyncio
    async def test_create_farmer_sets_default_preferences(self, ...):
        """AC #1: New farmer gets pref_channel=sms, pref_lang=sw."""

    @pytest.mark.asyncio
    async def test_update_preferences_success(self, ...):
        """AC #2: Can update to whatsapp + en."""

    @pytest.mark.asyncio
    async def test_update_preferences_invalid_channel(self, ...):
        """AC #4: Invalid channel returns INVALID_ARGUMENT with valid options."""

    @pytest.mark.asyncio
    async def test_update_preferences_invalid_language(self, ...):
        """AC #4: Invalid language returns INVALID_ARGUMENT with valid options."""

    @pytest.mark.asyncio
    async def test_update_preferences_farmer_not_found(self, ...):
        """NOT_FOUND when farmer doesn't exist."""

    @pytest.mark.asyncio
    async def test_get_farmer_includes_preferences(self, ...):
        """AC #3: GetFarmer returns current preferences."""

    @pytest.mark.asyncio
    async def test_get_farmer_summary_includes_preferences(self, ...):
        """AC #3: GetFarmerSummary includes preferences for Notification Model."""
```

### Critical Implementation Rules

**From project-context.md:**

1. **ALL I/O operations MUST be async** - Repository and gRPC methods
2. **Use Pydantic 2.0 syntax** - `model_dump()`, `Field()`, `model_config`
3. **Type hints required** - ALL function signatures
4. **Absolute imports only** - No relative imports
5. **Descriptive error messages** - List valid options in INVALID_ARGUMENT errors

### What This Story Does NOT Include

| Excluded | Reason | Future Story |
|----------|--------|--------------|
| Notification delivery logic | Notification Model responsibility | Epic 4 |
| Language translation content | Handled by Action Plan Model | Epic 6 |
| Voice IVR implementation | Separate Notification Model feature | Epic 7 |
| WhatsApp integration | Notification Model responsibility | Epic 4 |

**This story focuses on:**
- Adding preference fields to Farmer model
- Storing and retrieving preferences via gRPC
- Validating preference values
- Setting sensible defaults on registration

### Project Structure Notes

- Domain models: `services/plantation-model/src/plantation_model/domain/models/`
- gRPC service: `services/plantation-model/src/plantation_model/api/plantation_service.py`
- Repository: `services/plantation-model/src/plantation_model/infrastructure/repositories/farmer_repository.py`
- Proto: `proto/plantation/v1/plantation.proto`
- Tests: `tests/unit/plantation/`

### References

- [Source: _bmad-output/epics.md - Story 1.5] - Story requirements
- [Source: _bmad-output/project-context.md] - Critical rules
- [Source: services/plantation-model/src/plantation_model/domain/models/farmer.py] - Existing Farmer model
- [Source: proto/plantation/v1/plantation.proto] - Existing proto definitions
- [Source: _bmad-output/sprint-artifacts/1-4-farmer-performance-history-structure.md] - Previous story patterns

### Previous Story Intelligence (Story 1-4)

**Learnings from Story 1-4 code review:**
- Tasks marked [x] must have corresponding test files that actually exist
- gRPC test patterns: use mock_context with AsyncMock for abort
- Test both success cases AND error cases (NOT_FOUND, INVALID_ARGUMENT)
- Fixture pattern: create mock repositories with spec=

**Files modified in Story 1-4 (patterns to follow):**
- Added domain models in `domain/models/` with Pydantic BaseModel
- Extended `plantation_service.py` with new gRPC methods
- Updated proto with new messages and RPCs
- Unit tests in `tests/unit/plantation/test_grpc_*.py`

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Design Revision: Split Notification Channel from Interaction Preference

**Party Mode Discussion:** After initial implementation, a design review with Architect (Winston) and UX Designer (Sally) identified a semantic confusion in the original model. The original `pref_channel` with "sms", "whatsapp", "voice" options conflated two distinct concepts:

1. **Notification Delivery Channel** - How we PUSH notifications TO the farmer
2. **Interaction Mode Preference** - How the farmer prefers to CONSUME detailed information

**Key Insight:** When a farmer selects "VOICE", they're not saying "send my action plan via voice" - that's technically impossible without an outbound call. They're saying "I prefer to interact with the system via voice (IVR/conversational AI) rather than reading SMS."

**Revised Model:**
```python
notification_channel: sms | whatsapp
  → How we PUSH notifications to the farmer
  → Used by: Epic 4 (SMS Feedback), Epic 6 (Action Plans)

interaction_pref: text | voice
  → How farmer prefers to CONSUME detailed information
  → Used by: Epic 7 (IVR), Epic 8 (Voice AI)
```

**User Scenarios:**
| Farmer Type | notification_channel | interaction_pref | Experience |
|-------------|---------------------|------------------|------------|
| Literate, smartphone | whatsapp | text | Full action plan via WhatsApp |
| Literate, basic phone | sms | text | SMS summary, reads details |
| Low-literacy | sms | voice | SMS trigger → calls IVR to listen |

### Completion Notes List

- **AC #1:** Default preferences: notification_channel=SMS, interaction_pref=TEXT, pref_lang=SWAHILI
- **AC #2:** UpdateCommunicationPreferences gRPC method with all combinations supported
- **AC #3:** GetFarmer and GetFarmerSummary return notification_channel, interaction_pref, and pref_lang
- **AC #4:** Invalid values return INVALID_ARGUMENT with descriptive error messages
- **Tests:** 16 unit tests covering all scenarios including low-literacy and smartphone farmer use cases, plus GetFarmerSummary preferences
- **Design Revision:** Split pref_channel into notification_channel + interaction_pref per party mode discussion

### File List

**Domain Models (Updated):**
- `services/plantation-model/src/plantation_model/domain/models/farmer.py`
  - Added `NotificationChannel` enum (sms, whatsapp) - for PUSH notifications
  - Added `InteractionPreference` enum (text, voice) - for information consumption mode
  - Added `PreferredLanguage` enum (sw, ki, luo, en)
  - Added `notification_channel`, `interaction_pref`, `pref_lang` fields to Farmer
  - Updated FarmerUpdate with optional preference fields

**Proto (Updated):**
- `proto/plantation/v1/plantation.proto`
  - Added `NotificationChannel` enum (SMS, WHATSAPP only)
  - Added `InteractionPreference` enum (TEXT, VOICE)
  - Added `PreferredLanguage` enum
  - Updated Farmer message with fields 16, 17, 18
  - Updated FarmerSummary with fields 15, 16, 17
  - Added UpdateCommunicationPreferencesRequest with 4 fields
  - Added UpdateCommunicationPreferences RPC

**Generated (Regenerated):**
- `libs/fp-proto/src/fp_proto/plantation/v1/plantation_pb2.py`
- `libs/fp-proto/src/fp_proto/plantation/v1/plantation_pb2.pyi`
- `libs/fp-proto/src/fp_proto/plantation/v1/plantation_pb2_grpc.py`

**API (Updated):**
- `services/plantation-model/src/plantation_model/api/plantation_service.py`
  - Added `_notification_channel_to_proto()` / `_notification_channel_from_proto()`
  - Added `_interaction_pref_to_proto()` / `_interaction_pref_from_proto()`
  - Updated `_farmer_to_proto()` and `_farmer_summary_to_proto()`
  - Implemented `UpdateCommunicationPreferences()` with 3-field validation

**Unit Tests (New/Updated):**
- `tests/unit/plantation/test_grpc_farmer_preferences.py` - 16 tests including:
  - Default preferences validation
  - Update preferences (various combinations)
  - Validation errors (invalid channel, interaction, language)
  - Low-literacy farmer scenario (sms + voice)
  - Smartphone farmer scenario (whatsapp + text)
  - GetFarmerSummary returns preferences (AC #3)
- `tests/unit/plantation/test_grpc_farmer_summary.py` - Updated to work with new preference proto fields
- `tests/unit/plantation/test_grpc_grading_model.py` - Updated to work with new preference proto fields
