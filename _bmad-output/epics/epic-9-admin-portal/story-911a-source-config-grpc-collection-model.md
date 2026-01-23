# Story 9.11a: SourceConfigService gRPC in Collection Model

**Status:** draft
**Story Points:** 3
**Priority:** P2
**Dependencies:** None
**Blocked by:** -
**Reference:** ADR-019 (Decision 2)

## User Story

**As a** platform administrator,
**I want** read-only gRPC endpoints for source configurations in the Collection Model service,
**So that** the Admin UI can display source config data without direct MongoDB access.

## Acceptance Criteria

- [ ] `SourceConfigService` added to `proto/collection/v1/collection.proto`
- [ ] `ListSourceConfigs` RPC returns paginated summaries with filters (enabled_only, ingestion_mode)
- [ ] `GetSourceConfig` RPC returns full config detail as JSON string
- [ ] Read-only: No create/update/delete methods exposed
- [ ] Unit tests with golden samples
- [ ] gRPC service registered in Collection Model server startup

## Technical Notes

- Proto definitions specified in ADR-019 Decision 2
- Uses existing `source_configs` MongoDB collection
- Returns `config_json` as string to avoid duplicating complex Pydantic models in proto
- List returns `SourceConfigSummary` (key fields for table display)
- Get returns `SourceConfigResponse` (full config as JSON)
