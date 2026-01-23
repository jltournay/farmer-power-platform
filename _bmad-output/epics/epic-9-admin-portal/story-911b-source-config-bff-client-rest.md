# Story 9.11b: Source Config gRPC Client + REST API in BFF

**Status:** draft
**Story Points:** 3
**Priority:** P2
**Dependencies:** Story 9.11a
**Blocked by:** 9.11a
**Reference:** ADR-019 (Decision 4)

## User Story

**As a** frontend developer,
**I want** REST API endpoints in the BFF that proxy source config data from Collection Model,
**So that** the Admin UI can fetch source configurations via standard REST calls.

## Acceptance Criteria

- [ ] `SourceConfigClient` gRPC client created in BFF (`infrastructure/clients/source_config_client.py`)
- [ ] `GET /admin/source-configs` endpoint returns paginated list with filters
- [ ] `GET /admin/source-configs/{source_id}` endpoint returns full config detail
- [ ] Follows ADR-012 BFF composition patterns
- [ ] Unit tests for client and routes
- [ ] Error handling for gRPC failures (unavailable, not found)

## Technical Notes

- BFF client and REST endpoints specified in ADR-019 Decision 4
- Follows existing BFF patterns (e.g., GradingModelClient)
- Query params: `page_size`, `page_token`, `enabled_only`, `ingestion_mode`
