# Story 9.12b: Agent Config gRPC Client + REST API in BFF

**Status:** draft
**Story Points:** 3
**Priority:** P2
**Dependencies:** Story 9.12a
**Blocked by:** 9.12a
**Reference:** ADR-019 (Decision 4)

## User Story

**As a** frontend developer,
**I want** REST API endpoints in the BFF that proxy AI agent and prompt data from AI Model,
**So that** the Admin UI can fetch agent configurations via standard REST calls.

## Acceptance Criteria

- [ ] `AgentConfigClient` gRPC client created in BFF (`infrastructure/clients/agent_config_client.py`)
- [ ] `GET /admin/ai-agents` endpoint returns paginated agent list with filters
- [ ] `GET /admin/ai-agents/{agent_id}` endpoint returns agent detail with linked prompts
- [ ] Optional `version` query param for specific version retrieval
- [ ] Follows ADR-012 BFF composition patterns
- [ ] Unit tests for client and routes
- [ ] Error handling for gRPC failures (unavailable, not found)

## Technical Notes

- BFF client and REST endpoints specified in ADR-019 Decision 4
- Follows existing BFF patterns (e.g., GradingModelClient)
- Query params: `page_size`, `page_token`, `agent_type`, `status`, `version`
- Agent detail response includes denormalized prompt list
