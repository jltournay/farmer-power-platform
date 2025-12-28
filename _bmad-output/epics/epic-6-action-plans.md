# Epic 6: Weekly Action Plans

## Overview

This epic implements the Action Plan Model service that generates personalized weekly improvement recommendations for farmers based on quality diagnoses from the Knowledge Model. Action plans are tailored to farm scale, translated to the farmer's preferred language, and delivered in dual formats (detailed report + SMS summary).

## Scope

- Action Plan Model service setup with scheduled generation
- Weekly action plan generation with LLM-powered recommendations
- Farm-scale-aware recommendations for smallholder, medium, and estate farms
- Dual-format output (detailed report and SMS summary)
- Multilingual translation (English, Swahili, Kikuyu, Luo)
- Action Plan MCP Server for cross-service access

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
**And** MCP client connections to Knowledge, Plantation, Collection Models are configured
**And** OpenTelemetry traces are emitted for all operations

**Given** the service is running
**When** the Monday 6 AM scheduled job is configured
**Then** Dapr Jobs component triggers action plan generation weekly
**And** the schedule is per-factory timezone (Africa/Nairobi)

**Given** the service needs to generate action plans
**When** MCP tools are invoked
**Then** `get_farmer_analyses`, `get_farmer_summary`, `get_recent_quality_events` are available
**And** all tool calls are traced and logged

**Given** the LLM API is unavailable during generation
**When** the scheduled job runs
**Then** failed farmers are queued for retry (1 hour later)
**And** successful generations proceed
**And** partial success is logged with failure count

**Technical Notes:**
- Python with LangChain/LangGraph
- Claude Sonnet for action plan generation
- Schedule: Monday 06:00 Africa/Nairobi
- Environment: farmer-power-{env} namespace

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
**And** rate limiting is applied to LLM calls (10/second)

**Given** a farmer has diagnoses from Knowledge Model
**When** the action plan is generated
**Then** the AI queries `get_farmer_analyses(farmer_id, past_7_days)`
**And** diagnoses are prioritized by severity
**And** the top 3 issues are selected for recommendations

**Given** diagnoses are retrieved
**When** recommendations are generated
**Then** each recommendation includes: issue (what's wrong), action (what to do), why (expected impact)
**And** actions are specific and actionable (not generic advice)
**And** actions reference the specific diagnosis details

**Given** a farmer has no quality issues (all Grade 1)
**When** the action plan is generated
**Then** a celebration message is created: "Great work this week! Keep up the excellent quality."
**And** optional tip for maintaining quality is included
**And** encouragement to help neighbors is suggested

**Given** action plan generation completes
**When** the plan is stored
**Then** it includes: farmer_id, week_number, diagnoses_referenced, recommendations[], generated_at
**And** an "action_plan.generated" event is published for Notification Model
**And** the plan is marked as "pending_delivery"

**Technical Notes:**
- LLM: Claude Sonnet
- Max 3 recommendations per plan
- RAG enrichment from Knowledge Base (cultivation tips)
- Generation timeout: 30 seconds per farmer

---

### Story 6.3: Farm-Scale-Aware Recommendations

As a **farmer with a specific farm size**,
I want recommendations tailored to my scale of operation,
So that advice is practical for my situation.

**Acceptance Criteria:**

**Given** a farmer's farm_scale is "smallholder" (<1 hectare)
**When** recommendations are generated
**Then** advice focuses on: manual techniques, low-cost solutions, family labor optimization
**And** language is simple and jargon-free
**And** equipment recommendations avoid expensive purchases

**Given** a farmer's farm_scale is "medium" (1-5 hectares)
**When** recommendations are generated
**Then** advice includes: basic tool investments, hired labor coordination, batch processing techniques
**And** cost-benefit analysis is provided for larger investments

**Given** a farmer's farm_scale is "estate" (>5 hectares)
**When** recommendations are generated
**Then** advice includes: workforce management, equipment investments, process optimization
**And** recommendations may reference management practices
**And** ROI calculations are included for capital investments

**Given** farm_scale context is passed to LLM
**When** the prompt is constructed
**Then** few-shot examples appropriate for that scale are included
**And** the system prompt emphasizes scale-appropriate advice

**Given** yield_vs_regional_avg is below average
**When** recommendations are generated
**Then** the plan includes specific catch-up strategies
**And** comparison to successful peers at similar scale is referenced

**Technical Notes:**
- farm_scale from Plantation Model
- Few-shot examples per scale category
- yield_vs_regional_avg from Plantation Model summary
- Prompt template versioned for A/B testing

---

### Story 6.4: Dual-Format Output (Report + SMS)

As a **farmer**,
I want to receive both a detailed report and a short SMS summary,
So that I can get quick tips via SMS and refer to details later.

**Acceptance Criteria:**

**Given** an action plan is generated
**When** the detailed report is created
**Then** it includes: header (farmer name, week), issues section (list of diagnoses), recommendations section (numbered steps), next steps
**And** the report is stored in Action Plan DB
**And** the report is 300-500 words

**Given** an action plan is generated
**When** the SMS summary is created
**Then** it condenses the plan to: grade stars, ONE priority action, encouragement phrase
**And** the SMS is under 160 GSM-7 characters
**And** the SMS ends with "Call *384# for full plan"

**Given** the SMS summary is created
**When** passed to Notification Model
**Then** the `action_plan.generated` event includes: farmer_id, sms_content, detailed_report_id
**And** the Notification Model handles delivery

**Given** a farmer calls Voice IVR for details
**When** they request their action plan
**Then** the full detailed report is converted to TTS script
**And** the TTS script is structured for audio delivery (pauses, emphasis)

**Given** the detailed report is too long for TTS (>3 min)
**When** the TTS script is generated
**Then** the script is summarized to fit 2-3 minute audio
**And** the full report remains available in the system

**Technical Notes:**
- LLM generates both formats in single call
- SMS format strict: 160 char limit enforced
- TTS script: SSML-compatible formatting
- Storage: action_plans collection with reports and sms_summaries

---

### Story 6.5: Multilingual Translation

As a **farmer**,
I want my action plan in my preferred language,
So that I fully understand the recommendations.

**Acceptance Criteria:**

**Given** a farmer's pref_lang is "sw" (Swahili)
**When** the action plan is generated
**Then** both detailed report and SMS are in Swahili
**And** agricultural terms use locally understood vocabulary
**And** the language is natural, not machine-translated sounding

**Given** a farmer's pref_lang is "ki" (Kikuyu)
**When** the action plan is generated
**Then** the content is translated to Kikuyu
**And** cultural context is preserved (e.g., local farming practices)

**Given** a farmer's pref_lang is "luo" (Luo)
**When** the action plan is generated
**Then** the content is translated to Luo
**And** regional farming terminology is used

**Given** translation is needed
**When** the LLM generates the action plan
**Then** the prompt includes language instruction
**And** few-shot examples in the target language guide output
**And** fallback to English is available if translation quality is poor

**Given** a translation quality check fails
**When** the output is validated
**Then** the plan is flagged for human review
**And** English version is delivered as fallback
**And** a "translation.quality_issue" event is logged

**Technical Notes:**
- LLM generates in target language directly (not post-translation)
- Few-shot examples in Swahili, Kikuyu, Luo pre-validated by native speakers
- Quality check: basic grammar/coherence validation
- Fallback flag: use_english_fallback

---

### Story 6.6: Action Plan MCP Server

As an **AI agent (Conversational AI)**,
I want to access action plans via MCP tools,
So that Voice Quality Advisor can reference farmer's current recommendations.

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
**And** includes: original quality event, diagnosis, RAG context used, recommendation reasoning

**Given** the Conversational AI needs to explain a recommendation
**When** it queries the action plan
**Then** sufficient context is available for natural explanation
**And** the farmer's history informs the response

**Given** no action plan exists for current week
**When** `get_current_action_plan` is called
**Then** the response indicates: "no_plan_this_week"
**And** the previous week's plan is optionally returned

**Given** the MCP Server receives a request
**When** processing completes
**Then** OpenTelemetry traces are emitted
**And** tool usage is logged for cost attribution

**Technical Notes:**
- MCP Server deployed as separate Kubernetes deployment
- HPA enabled: min 2, max 10 replicas
- Read-only access to Action Plan DB
- gRPC interface following MCP protocol
