# Epic 8: Voice Quality Advisor (Conversational AI)

**Priority:** P5

**Dependencies:** Epic 0.75 (AI Model Foundation), Epic 5 (Knowledge Model), Epic 6 (Action Plans)

**FRs covered:** FR50, FR51, FR52, FR53, FR54, FR55, FR56, FR57

## Overview

Farmers can have interactive voice conversations with an AI quality advisor to ask questions about their tea quality and get personalized advice. This provides a natural, conversational interface for farmers who need detailed guidance beyond SMS summaries.

This epic defines the **business logic** for voice conversations: what triggers calls, how conversations flow, what responses must contain, and how fallbacks work.

> **Implementation Note:** All AI agent implementations (LLM orchestration, STT/TTS integration, conversation state management) are defined in Epic 0.75 (AI Model Foundation). This epic focuses on WHAT conversations achieve and HOW they flow, not HOW the conversational agent works internally.

## Document Boundaries

| This Epic Owns | Epic 0.75 (AI Model) Owns |
|----------------|---------------------------|
| Call handling and telephony integration | Conversational agent implementation |
| Dialogue flow and turn limits | LLM selection and streaming |
| Intent categories and responses | STT/TTS provider configuration |
| Personalization requirements | Conversation state checkpointing |
| Fallback triggers and behavior | Intent classification prompts |
| MCP data requirements | Response generation prompts |

## Scope

- Conversational AI service setup with telephony
- Speech-to-text requirements for Swahili
- Intent classification categories
- Personalized response requirements
- Guided dialogue flow with turn management
- SMS fallback handling

**NOT in scope:** Conversational agent implementation, LLM configuration, STT/TTS provider setup, streaming architecture — these belong in Epic 0.75.

---

## Stories

### Story 8.1: Conversational AI Service Setup

As a **platform operator**,
I want the Conversational AI service deployed with telephony integration,
So that farmers can have interactive voice conversations about quality improvement.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Conversational AI service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** Africa's Talking Voice API is configured for inbound calls
**And** OpenTelemetry traces are emitted for all calls

**Given** the service is running
**When** a call is received on the Voice Advisor number (*384#)
**Then** the call is routed to the AI Model service with agent_id: `voice-advisor-v1`
**And** a new conversation session is created
**And** the session tracks: call_id, farmer_id, turn_count, start_time

**Given** the AI Model service is unavailable
**When** a call is received
**Then** a pre-recorded message plays: "Our advisor is temporarily unavailable"
**And** SMS fallback is triggered (Story 8.7)
**And** the call ends gracefully

**Technical Notes:**
- Python FastAPI service
- Africa's Talking for telephony (Kenya)
- Dapr service invocation to AI Model for agent execution
- Session state: Redis with TTL
- Environment: farmer-power-{env} namespace

> **Implementation:** Voice advisor agent configuration in Epic 0.75.

---

### Story 8.2: Speech-to-Text Requirements

As a **farmer speaking Swahili**,
I want my speech accurately transcribed,
So that the AI understands my questions.

**Acceptance Criteria:**

**Given** a farmer speaks during the call
**When** audio is captured
**Then** transcription begins immediately (streaming mode)
**And** interim results are available for responsive interaction

**Given** the farmer speaks Swahili
**When** transcription is performed
**Then** accuracy target is >85% for common tea/farming vocabulary
**And** agricultural terms are recognized correctly
**And** common code-switching (Swahili/English mix) is handled

**Given** background noise is present
**When** audio is captured
**Then** noise reduction is applied
**And** voice activity detection filters silence
**And** only speech segments are transcribed

**Given** transcription confidence is low (<0.6)
**When** the result is returned
**Then** a clarification prompt is triggered: "I didn't quite catch that. Could you repeat?"
**And** the low confidence is logged for quality monitoring

**Given** STT fails completely
**When** the service is unavailable
**Then** fallback to DTMF-based interaction is offered
**And** SMS fallback is triggered (Story 8.7)

**Transcription Requirements:**

| Requirement | Target |
|-------------|--------|
| Language | Swahili (sw-KE) |
| Accuracy | >85% for farming vocabulary |
| Latency | <500ms for interim results |
| Noise handling | Background noise tolerance |

> **Implementation:** STT provider configuration in Epic 0.75 agent definition.

---

### Story 8.3: Intent Classification

As a **Conversational AI system**,
I want farmer intents classified from their speech,
So that appropriate responses can be generated.

**Acceptance Criteria:**

**Given** a farmer's speech is transcribed
**When** intent classification runs
**Then** the intent is classified into one of the defined categories

**Intent Categories:**

| Intent | Example Utterances | Response Type |
|--------|-------------------|---------------|
| quality_question | "Why was my tea graded poorly?" | Fetch diagnoses, explain |
| action_plan_query | "What should I do to improve?" | Fetch current action plan |
| delivery_status | "When was my last delivery?" | Fetch recent documents |
| general_help | "How can you help me?" | Explain capabilities |
| clarification | "I don't understand" | Rephrase previous response |
| goodbye | "Asante", "Goodbye" | End conversation gracefully |
| out_of_scope | Non-quality topics | Politely redirect |

**Given** intent classification confidence is low (<0.5)
**When** the classifier is uncertain
**Then** a disambiguation question is asked
**And** options are provided: "Are you asking about your recent delivery or your weekly plan?"

**Given** the farmer says goodbye or thanks
**When** classification runs
**Then** the conversation wrapping procedure is triggered
**And** a summary of key points is optionally provided

> **Implementation:** Intent classification handled by conversational agent. Intent prompts in Epic 0.75.

---

### Story 8.4: Personalized Response Requirements

As a **farmer**,
I want personalized answers based on my quality data,
So that advice is relevant to my specific situation.

**Acceptance Criteria:**

**Given** a farmer asks a quality question
**When** response generation begins
**Then** the following context is gathered via MCP:
  - Farmer profile and trend (`plantation-mcp.get_farmer_summary`)
  - Recent deliveries (`collection-mcp.get_recent_quality_events`)
  - Diagnoses (`knowledge-mcp.get_farmer_analyses`)
  - Current action plan (`action-plan-mcp.get_current_action_plan`)

**Given** context is gathered
**When** the response is generated
**Then** the response references the farmer's actual data by name
**And** specific issues are mentioned (not generic advice)
**And** actionable guidance is provided

**Response Personalization Requirements:**

| Data Point | How Used |
|------------|----------|
| farmer_name | Addressed by name |
| last_delivery_grade | Referenced in context |
| primary_percentage | Specific numbers cited |
| trend_direction | Acknowledged (improving/declining) |
| current_recommendations | Referenced from action plan |

**Given** the farmer is performing well
**When** they ask a question
**Then** the AI acknowledges success: "You're doing great!"
**And** tips for maintaining quality are offered

**Given** the response is generated
**When** it is finalized
**Then** the response is appropriate for spoken delivery (short sentences)
**And** the response is in the farmer's preferred language
**And** response length is limited to ~30 seconds of audio

> **Implementation:** Response generation handled by conversational agent with MCP tools.

---

### Story 8.5: Guided Dialogue Flow

As a **Conversational AI system**,
I want to guide conversations efficiently,
So that farmers get answers within the time limit.

**Acceptance Criteria:**

**Given** a conversation starts
**When** the greeting plays
**Then** the AI introduces itself in the farmer's language
**And** the conversation turn counter starts at 1

**Given** the conversation proceeds
**When** each turn completes
**Then** the turn counter increments
**And** the turn is logged with: intent, response_length, duration

**Given** the conversation reaches turn 3
**When** the farmer continues
**Then** the AI gently guides toward closure: "Is there anything else quick I can help with?"

**Given** the conversation reaches turn 5 (max)
**When** the turn completes
**Then** the AI wraps up: "I hope that helped. Call back anytime. Goodbye!"
**And** the call ends gracefully

**Given** the conversation exceeds 3 minutes
**When** the time limit approaches
**Then** a gentle warning plays: "We're almost out of time. Let me summarize..."
**And** a brief summary of key points is provided
**And** the call wraps up

**Dialogue Flow Constraints:**

| Constraint | Value |
|------------|-------|
| Max turns | 5 |
| Max duration | 3 minutes |
| Response length | ~30 seconds audio |
| Greeting | Personalized, in farmer's language |

**Given** the farmer goes off-topic
**When** out-of-scope intent is detected
**Then** the AI politely redirects: "I'm here to help with tea quality. Is there something about your tea I can help with?"
**And** if farmer insists, escalation to human is offered

> **Implementation:** Turn management and streaming configured in conversational agent.

---

### Story 8.6: Streaming Response Delivery

As a **farmer**,
I want to hear responses without long delays,
So that the conversation feels natural.

**Acceptance Criteria:**

**Given** the AI generates a response
**When** response generation begins
**Then** audio playback begins as soon as the first sentence is ready
**And** subsequent sentences stream while earlier ones play

**Given** streaming is active
**When** the farmer hears the response
**Then** the perceived latency is <2 seconds from end of farmer speech
**And** audio plays smoothly without stuttering

**Given** the farmer interrupts during playback
**When** speech is detected mid-response (barge-in)
**Then** playback stops immediately
**And** the new farmer speech is transcribed
**And** the AI adapts to the interruption

**Given** network latency is high
**When** streaming cannot achieve <2s latency
**Then** a filler phrase plays: "Let me think about that..."
**And** the response begins as soon as available

**Latency Requirements:**

| Metric | Target |
|--------|--------|
| End-to-end latency | <2 seconds |
| First audio chunk | <1 second |
| Barge-in detection | <200ms |

> **Implementation:** Streaming and barge-in configured in conversational agent (Epic 0.75).

---

### Story 8.7: SMS Fallback Handling

As a **farmer whose speech wasn't understood**,
I want to receive an SMS with the information,
So that I still get help even if voice interaction fails.

**Acceptance Criteria:**

**Given** the AI cannot understand after 2 clarification attempts
**When** the third attempt fails
**Then** the AI offers SMS fallback: "I'm having trouble understanding. Would you like me to send an SMS?"

**Given** the farmer accepts SMS fallback (says yes or presses 1)
**When** fallback is triggered
**Then** the Notification Model is invoked via Dapr
**And** an SMS is sent with: recent grade, primary %, key action
**And** the call ends gracefully

**Given** the farmer declines SMS fallback
**When** they indicate no
**Then** the AI offers one more try: "Let's try once more. Please speak slowly."
**And** if still unsuccessful, escalation to human is offered

**Given** STT service is completely unavailable
**When** the call starts
**Then** the AI announces: "Our voice system is temporarily unavailable."
**And** SMS fallback is immediately offered
**And** the call is kept short (<30 seconds)

**Given** SMS fallback is triggered
**When** the SMS is sent
**Then** the SMS includes: farmer_name, last_grade, last_primary_%, ONE tip
**And** the SMS ends with: "Call back later for more help."
**And** the SMS uses the farmer's pref_lang
**And** SMS is ≤160 characters

**Fallback Triggers:**

| Trigger | Action |
|---------|--------|
| 3 failed transcriptions | Offer SMS fallback |
| STT unavailable | Immediate SMS fallback |
| LLM unavailable | Pre-recorded message + SMS |
| TTS unavailable | SMS-only response |

> **Implementation:** Fallback logic in conversational agent. SMS via Notification Model.

---

## Dependencies

| This Epic Depends On | Reason |
|---------------------|--------|
| Epic 0.75 (AI Model Foundation) | Conversational agent framework, STT/TTS |
| Epic 5 (Knowledge Model) | Diagnoses via MCP |
| Epic 6 (Action Plans) | Action plans via MCP |
| Epic 1 (Plantation Model) | Farmer context via MCP |
| Epic 2 (Collection Model) | Quality events via MCP |
| Epic 7 (Notification Model) | SMS fallback delivery |

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2025-12-28_
