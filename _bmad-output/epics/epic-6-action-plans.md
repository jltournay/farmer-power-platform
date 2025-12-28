# Epic 6: Weekly Action Plans

**Priority:** P4

**Dependencies:** Epic 0.75 (AI Model Foundation), Epic 5 (Knowledge Model)

**FRs covered:** FR29, FR30, FR31, FR32, FR33

## Overview

The Action Plan Model generates personalized weekly improvement recommendations for farmers based on quality diagnoses from the Knowledge Model. Action plans are tailored to farm scale, translated to the farmer's preferred language, and delivered in dual formats (detailed report + SMS summary).

This epic defines the **business logic** for action plan generation: what triggers generation, what recommendations must contain, how farm scale affects advice, and how plans are delivered.

> **Implementation Note:** All AI agent implementations (LLM orchestration, RAG queries, prompt engineering) are defined in Epic 0.75 (AI Model Foundation). This epic focuses on WHAT to generate and WHEN, not HOW agents work internally.

## Document Boundaries

| This Epic Owns | Epic 0.75 (AI Model) Owns |
|----------------|---------------------------|
| Generation schedule and triggers | Agent implementations (Plan Generator, Translator) |
| Recommendation content requirements | LLM selection and model routing |
| Farm-scale-aware business rules | RAG configuration and knowledge domains |
| Output formats (report + SMS) | Prompt engineering and A/B testing |
| Delivery integration (Notification Model) | Few-shot examples and templates |
| MCP tools exposed to Voice Advisor | Translation quality validation |

## Scope

- Action Plan Model service setup with scheduled generation
- Weekly action plan generation workflow
- Farm-scale-aware recommendation rules
- Dual-format output requirements (detailed report + SMS)
- Multilingual output requirements
- Action Plan MCP Server for Voice Advisor access

**NOT in scope:** Agent implementations, LLM configuration, RAG infrastructure, prompt management — these belong in Epic 0.75.

---

## Stories

### Story 6.1: Action Plan Model Service Setup

As a **platform operator**,
I want the Action Plan Model service deployed with scheduled generation capability,
So that farmers receive weekly personalized improvement recommendations.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Action Plan Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** MongoDB connection is established for Action Plan DB
**And** OpenTelemetry traces are emitted for all operations

**Given** the service is running
**When** the Monday 6 AM scheduled job is configured
**Then** Dapr Jobs component triggers action plan generation weekly
**And** the schedule is per-factory timezone (Africa/Nairobi)

**Given** the service needs to generate action plans
**When** the generation workflow starts
**Then** the AI Model service is invoked via Dapr with agent_id: `action-plan-generator-v1`
**And** MCP tools provide farmer context (Knowledge, Plantation, Collection)

**Given** the AI Model service is unavailable during generation
**When** the scheduled job runs
**Then** failed farmers are queued for retry (1 hour later)
**And** successful generations proceed
**And** partial success is logged with failure count

**Technical Notes:**
- Python FastAPI service
- Dapr service invocation to AI Model for agent execution
- Schedule: Monday 06:00 Africa/Nairobi
- Action Plan DB: `action_plan_model.plans` collection
- Environment: farmer-power-{env} namespace

> **Implementation:** Agent execution delegated to AI Model service (Epic 0.75).

---

### Story 6.2: Weekly Action Plan Generation

As a **farmer**,
I want to receive a weekly action plan based on my recent quality data,
So that I know what specific steps to take to improve my tea quality.

**Acceptance Criteria:**

**Given** the Monday 6 AM generation job runs
**When** farmers with deliveries in the past 7 days are identified
**Then** action plan generation is triggered for each farmer
**And** farmers are processed in batches (100 per batch)
**And** rate limiting is applied (10/second)

**Given** a farmer has diagnoses from Knowledge Model
**When** the action plan is generated
**Then** diagnoses are retrieved via `get_farmer_analyses(farmer_id, past_7_days)`
**And** diagnoses are prioritized by severity
**And** the top 3 issues are selected for recommendations

**Given** diagnoses are retrieved
**When** recommendations are generated
**Then** each recommendation includes:
```json
{
  "issue": "What's wrong (from diagnosis)",
  "action": "What to do (specific, actionable)",
  "why": "Expected impact if action is taken",
  "priority": 1-3,
  "diagnosis_ref": "diagnosis_id"
}
```

**Given** a farmer has no quality issues (all Grade 1)
**When** the action plan is generated
**Then** a celebration plan is created with:
  - Congratulations message
  - Optional tip for maintaining quality
  - Encouragement to help neighbors

**Given** action plan generation completes
**When** the plan is stored
**Then** it includes: farmer_id, week_number, diagnoses_referenced, recommendations[], generated_at
**And** an `action_plan.generated` event is published for Notification Model
**And** the plan is marked as `pending_delivery`

**Business Rules:**
- Max 3 recommendations per plan
- Recommendations must be specific, not generic advice
- Each recommendation must reference a specific diagnosis
- Generation timeout: 30 seconds per farmer

> **Implementation:** Action plan generator agent configuration in Epic 0.75.

---

### Story 6.3: Farm-Scale-Aware Recommendations

As a **farmer with a specific farm size**,
I want recommendations tailored to my scale of operation,
So that advice is practical for my situation.

**Acceptance Criteria:**

**Given** a farmer's farm_scale is "smallholder" (<1 hectare)
**When** recommendations are generated
**Then** advice focuses on:
  - Manual techniques
  - Low-cost solutions
  - Family labor optimization
**And** language is simple and jargon-free
**And** equipment recommendations avoid expensive purchases

**Given** a farmer's farm_scale is "medium" (1-5 hectares)
**When** recommendations are generated
**Then** advice includes:
  - Basic tool investments
  - Hired labor coordination
  - Batch processing techniques
**And** cost-benefit context is provided for larger investments

**Given** a farmer's farm_scale is "estate" (>5 hectares)
**When** recommendations are generated
**Then** advice includes:
  - Workforce management
  - Equipment investments
  - Process optimization
**And** ROI context is included for capital investments

**Given** yield_vs_regional_avg is below average
**When** recommendations are generated
**Then** the plan includes specific catch-up strategies
**And** comparison to successful peers at similar scale is referenced

**Farm Scale Context Requirements:**

| Scale | Labor Focus | Investment Focus | Language Level |
|-------|-------------|------------------|----------------|
| Smallholder | Family | Low-cost | Simple |
| Medium | Hired + Family | Moderate | Standard |
| Estate | Workforce | Capital | Technical |

> **Implementation:** Farm scale context passed to agent. Scale-specific guidance configured in Epic 0.75 agent definition.

---

### Story 6.4: Dual-Format Output (Report + SMS)

As a **farmer**,
I want to receive both a detailed report and a short SMS summary,
So that I can get quick tips via SMS and refer to details later.

**Acceptance Criteria:**

**Given** an action plan is generated
**When** the detailed report is created
**Then** it includes:
```
Header: farmer_name, week, overall_grade
Issues Section: list of top 3 diagnoses with severity
Recommendations Section: numbered action steps
Encouragement: closing positive message
```
**And** the report is 300-500 words
**And** the report is stored in Action Plan DB

**Given** an action plan is generated
**When** the SMS summary is created
**Then** it includes:
  - Grade indicator (stars or simple text)
  - ONE priority action (most important)
  - Encouragement phrase
**And** the SMS is under 160 GSM-7 characters
**And** the SMS ends with "Call *384# for full plan"

**Given** the SMS summary is created
**When** passed to Notification Model
**Then** the `action_plan.generated` event includes:
  - farmer_id
  - sms_content
  - detailed_report_id
**And** the Notification Model handles delivery

**Given** a farmer requests their plan via Voice IVR
**When** the detailed report is retrieved
**Then** a TTS-optimized version is available
**And** the TTS version includes pauses and emphasis markers
**And** TTS version is limited to 2-3 minutes of audio

**Output Format Requirements:**

| Format | Length | Content | Delivery |
|--------|--------|---------|----------|
| Detailed Report | 300-500 words | Full recommendations | Stored in DB |
| SMS Summary | ≤160 chars | 1 priority action | Via Notification Model |
| TTS Script | 2-3 min audio | Spoken version | Via Voice IVR |

> **Implementation:** Multi-format output handled by agent. Format constraints configured in Epic 0.75.

---

### Story 6.5: Multilingual Output

As a **farmer**,
I want my action plan in my preferred language,
So that I fully understand the recommendations.

**Acceptance Criteria:**

**Given** a farmer's pref_lang is "sw" (Swahili)
**When** the action plan is generated
**Then** both detailed report and SMS are in Swahili
**And** agricultural terms use locally understood vocabulary

**Given** a farmer's pref_lang is "ki" (Kikuyu)
**When** the action plan is generated
**Then** the content is in Kikuyu
**And** cultural context is preserved

**Given** a farmer's pref_lang is "luo" (Luo)
**When** the action plan is generated
**Then** the content is in Luo
**And** regional farming terminology is used

**Given** translation quality is validated
**When** the output is checked
**Then** basic coherence validation passes
**And** if quality check fails, the plan is flagged for human review
**And** English fallback is delivered if translation is poor

**Supported Languages:**

| Code | Language | Region |
|------|----------|--------|
| en | English | Default |
| sw | Swahili | Kenya-wide |
| ki | Kikuyu | Central Kenya |
| luo | Luo | Western Kenya |

**Quality Assurance:**
- Translation quality check runs on each output
- Fallback flag: `use_english_fallback`
- Failed translations logged as `translation.quality_issue` event

> **Implementation:** Multilingual generation configured in agent. Language-specific examples in Epic 0.75 prompt management.

---

### Story 6.6: Action Plan MCP Server

As an **AI agent (Voice Advisor)**,
I want to access action plans via MCP tools,
So that conversational AI can reference farmer's current recommendations.

**Acceptance Criteria:**

**Given** the Action Plan MCP Server is deployed
**When** an AI agent calls `get_current_action_plan(farmer_id)`
**Then** the most recent action plan is returned
**And** includes: week_number, recommendations[], status (pending/delivered/acknowledged)

**Given** a farmer_id exists
**When** an AI agent calls `get_action_plan_history(farmer_id, weeks=4)`
**Then** action plans from the past 4 weeks are returned
**And** results show progression and recurring themes

**Given** a specific recommendation needs context
**When** an AI agent calls `get_recommendation_details(plan_id, rec_index)`
**Then** the full diagnosis chain is returned
**And** includes: original quality event, diagnosis, recommendation reasoning

**Given** no action plan exists for current week
**When** `get_current_action_plan` is called
**Then** the response indicates: `no_plan_this_week`
**And** the previous week's plan is optionally returned

**Given** the MCP Server receives a request
**When** processing completes
**Then** OpenTelemetry traces are emitted
**And** tool usage is logged for cost attribution

**MCP Tools Summary:**

| Tool | Purpose | Primary Consumer |
|------|---------|------------------|
| `get_current_action_plan` | Most recent plan | Voice Advisor |
| `get_action_plan_history` | Past weeks' plans | Voice Advisor |
| `get_recommendation_details` | Full context for one recommendation | Voice Advisor |

**Technical Notes:**
- MCP Server deployed as separate Kubernetes deployment
- HPA enabled: min 2, max 10 replicas
- Read-only access to Action Plan DB
- gRPC interface following MCP protocol

---

## Dependencies

| This Epic Depends On | Reason |
|---------------------|--------|
| Epic 0.75 (AI Model Foundation) | Agent framework, LLM gateway |
| Epic 5 (Knowledge Model) | Diagnoses via MCP |
| Epic 1 (Plantation Model) | Farmer context via MCP |
| Epic 2 (Collection Model) | Quality events via MCP |

| Epics That Depend On This | Reason |
|--------------------------|--------|
| Epic 8 (Voice Advisor) | Consumes action plans via MCP |

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2025-12-28_
