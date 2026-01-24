# Epic 9: Use Cases

<!-- These define the functional user journeys that stories must collectively deliver -->
<!-- E2E tests will verify these flows end-to-end across service boundaries -->

## UC9.0: Publish Knowledge Document (Retrospective - Stories 9.9a, 9.9b)

**Actor:** Platform Administrator
**Preconditions:** Admin is authenticated with platform_admin role
**Stories:** 9.9a, 9.9b (completed - use case added retroactively as reference)

**Main Flow:**

1. Admin uploads a document file → System extracts content and stores in blob storage
2. Admin reviews extracted content and chunks → System displays document content with chunk boundaries
3. Admin triggers preparation for AI retrieval → System vectorizes chunks and stores embeddings
4. Admin tests AI retrieval with sample questions → System returns relevant content matches with confidence scores
5. Admin approves and activates the document → System makes document available for production AI queries (ONLY if step 3 completed successfully)

**Postcondition:** Document content is searchable by AI agents in production with relevant matches returned for domain-specific queries

**Critical Invariant:** Activation (step 5) MUST be rejected by the system if vectorization (step 3) has not completed. This is a system-enforced guard, not a manual checkbox.

---

## UC9.1: View Source Configurations

**Actor:** Platform Administrator
**Preconditions:** Admin is authenticated with platform_admin role
**Stories:** 9.11a, 9.11b, 9.11c

**Main Flow:**

1. Admin navigates to Source Configurations page → System displays a paginated list of source configurations with key fields (source_id, display_name, ingestion_mode, enabled status)
2. Admin filters by ingestion mode or enabled status → System updates the list showing only matching configurations
3. Admin clicks a source configuration row → System opens a detail panel showing structured sections (Summary, Ingestion, Validation, Transformation, Storage, Events)
4. Admin views the raw JSON section → System displays the full configuration as formatted JSON

**Postcondition:** Admin has inspected the source configuration data without requiring CLI access or direct MongoDB queries

---

## UC9.2: View AI Agent and Prompt Configurations

**Actor:** Platform Administrator
**Preconditions:** Admin is authenticated with platform_admin role
**Stories:** 9.12a, 9.12b, 9.12c

**Main Flow:**

1. Admin navigates to AI Agents page → System displays a paginated list of agent configurations (agent_id, type, version, status, model, prompt_count)
2. Admin filters by agent type or status → System updates the list showing only matching agents
3. Admin clicks an agent row → System navigates to agent detail page showing sections (Summary, LLM Configuration, RAG Configuration, Input/Output Contracts)
4. Admin views linked prompts table → System displays all prompts linked to this agent with version history
5. Admin clicks a prompt row → System expands inline showing prompt content (System Prompt, Template, Output Schema, Few-Shot Examples)

**Postcondition:** Admin has inspected agent configurations and their linked prompt content without requiring CLI access

---

## UC9.3: Monitor Platform Costs

**Actor:** Platform Administrator
**Preconditions:** Admin is authenticated with platform_admin role, platform cost service is operational (Epic 13)
**Stories:** 9.10a, 9.10b

**Main Flow:**

1. Admin navigates to Platform Costs page → System displays total cost overview with today's live cost, budget utilization, daily trend chart (stacked by type), and cost breakdown by type (LLM, Documents, Embeddings)
2. Admin selects a date range → System updates all cost figures and charts for the selected period
3. Admin clicks a cost type tab (LLM, Documents, Embeddings) → System shows detailed breakdown for that type (LLM: by agent type + by model with token counts; Documents: pages processed, avg cost/page; Embeddings: by knowledge domain)
4. Admin configures budget thresholds → System saves daily and monthly threshold values (alert delivery handled by AlertManager via OTEL metrics)
5. Admin exports cost data → System generates CSV for the selected period and cost type

**Postcondition:** Admin has reviewed platform spending across LLM, Document, and Embedding costs, identified cost drivers, and configured budget thresholds

---
