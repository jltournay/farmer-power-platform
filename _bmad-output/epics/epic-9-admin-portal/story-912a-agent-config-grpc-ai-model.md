# Story 9.12a: AgentConfigService gRPC in AI Model

**Status:** draft
**Story Points:** 5
**Priority:** P2
**Dependencies:** None
**Blocked by:** -
**Reference:** ADR-019 (Decision 3)

## User Story

**As a** platform administrator,
**I want** read-only gRPC endpoints for AI agent and prompt configurations in the AI Model service,
**So that** the Admin UI can display agent configs and their linked prompts without direct MongoDB access.

## Acceptance Criteria

- [ ] `AgentConfigService` added to `proto/ai_model/v1/ai_model.proto`
- [ ] `ListAgentConfigs` RPC returns paginated summaries with filters (agent_type, status)
- [ ] `GetAgentConfig` RPC returns full agent config with linked prompts in one call
- [ ] `ListPromptsByAgent` RPC returns prompts for a specific agent
- [ ] Read-only: No create/update/delete methods exposed
- [ ] Unit tests with golden samples
- [ ] gRPC service registered in AI Model server startup

## Technical Notes

- Proto definitions specified in ADR-019 Decision 3
- Uses existing `agent_configs` and `prompts` MongoDB collections
- `GetAgentConfig` denormalizes prompts into the response (single call efficiency)
- Prompt linked via `agent_id` foreign key relationship
- Version history accessible via optional version parameter
- Full config returned as JSON string to avoid proto duplication
