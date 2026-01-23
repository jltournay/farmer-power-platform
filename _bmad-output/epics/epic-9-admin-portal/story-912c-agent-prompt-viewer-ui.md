# Story 9.12c: AI Agent & Prompt Viewer UI

**Status:** draft
**Story Points:** 5
**Priority:** P2
**Dependencies:** Story 9.12b
**Blocked by:** 9.12b
**Reference:** ADR-019 (Decision 5, Screens 2 & 2b)

## User Story

**As a** platform administrator,
**I want** a read-only AI Agent and Prompt viewer in the Admin Portal,
**So that** I can inspect agent configurations, their linked prompts, and prompt content without CLI access.

## Acceptance Criteria

- [ ] AI Agent list page at `/admin/ai-agents` with DataTable
- [ ] Columns: agent_id, type, version, status, model, prompt_count
- [ ] Filters: agent_type dropdown, status dropdown
- [ ] Pagination support
- [ ] Click row navigates to full-page Agent Detail view (`/admin/ai-agents/{agent_id}`)
- [ ] Detail page sections: Summary, LLM Configuration, RAG Configuration, Input Contract, Output Contract
- [ ] Linked Prompts table with version history
- [ ] Click prompt row expands prompt detail inline
- [ ] Prompt detail shows: System Prompt, Template, Output Schema, Few-Shot Examples, A/B Test Config
- [ ] Collapsible sections for long content (prompts, schemas)
- [ ] Collapsible raw JSON section for power users
- [ ] Read-only indicator with CLI references (agent-config, prompt-config)
- [ ] Back navigation to agent list

## Wireframe: AI Agent List

See ADR-019 Decision 5, Screen 2.

## Wireframe: AI Agent Detail

See ADR-019 Decision 5, Screen 2b.

## Technical Notes

- Full-page detail view (not slide-out) due to content density
- Follows existing Admin Portal component patterns
- Navigation item added to Admin sidebar under "Configuration" section
- Prompt detail uses expandable row pattern within the Linked Prompts table
