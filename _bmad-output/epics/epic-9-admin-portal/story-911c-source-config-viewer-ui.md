# Story 9.11c: Source Configuration Viewer UI

**Status:** draft
**Story Points:** 3
**Priority:** P2
**Dependencies:** Story 9.11b
**Blocked by:** 9.11b
**Reference:** ADR-019 (Decision 5, Screen 1)

## User Story

**As a** platform administrator,
**I want** a read-only Source Configuration viewer in the Admin Portal,
**So that** I can inspect active source configs without CLI access or direct MongoDB queries.

## Acceptance Criteria

- [ ] Source Config list page at `/admin/source-configs` with DataTable
- [ ] Columns: source_id, display_name, ingestion_mode, enabled status, linked agent
- [ ] Filters: enabled_only toggle, ingestion_mode dropdown
- [ ] Pagination support
- [ ] Click row opens slide-out detail panel
- [ ] Detail panel shows structured sections: Summary, Ingestion, Validation, Transformation, Storage, Events
- [ ] Conditional display based on ingestion mode (blob_trigger vs scheduled_pull)
- [ ] Collapsible raw JSON section for power users
- [ ] Read-only indicator with CLI reference
- [ ] Link to AI Agent detail when agent is configured

## Wireframe: Source Config List

See ADR-019 Decision 5, Screen 1.

## Wireframe: Source Config Detail

See ADR-019 Decision 5, Screen 1 (Detail Panel).

## Technical Notes

- Follows existing Admin Portal component patterns (DataTable, FilterBar, etc.)
- Slide-out detail panel pattern (not full page navigation)
- Navigation item added to Admin sidebar under "Configuration" section
