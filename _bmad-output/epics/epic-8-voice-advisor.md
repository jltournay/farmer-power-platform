# Epic 8: Voice Quality Advisor (Conversational AI)

**Priority:** P5

**Dependencies:** Epic 0.75 (AI Model Foundation), Epic 5 (Quality Diagnosis AI), Epic 6 (Weekly Action Plans)

**FRs covered:** FR50, FR51, FR52, FR53, FR54, FR55, FR56, FR57

Farmers can have interactive voice conversations with an AI quality advisor to ask questions about their tea quality and get personalized advice. This provides a more natural, conversational interface for farmers who need detailed guidance.

**Note:** This epic requires Epic 0.75 (AI Model Foundation) for LLM orchestration, Epic 5 for quality diagnoses, and Epic 6 for action plan context.

**Scope:**
- Conversational AI service with voice processing
- Swahili speech-to-text transcription
- Intent classification and entity extraction
- Personalized response generation using MCP tools
- Guided dialogue flow with turn management
- Streaming response delivery
- SMS fallback for failed voice interactions

---

## Story 8.1: Conversational AI Service Setup

As a **platform operator**,
I want the Conversational AI service deployed with voice processing capabilities,
So that farmers can have interactive voice conversations about quality improvement.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running
**When** the Conversational AI service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** Africa's Talking Voice API is configured for inbound calls
**And** speech-to-text (STT) provider is connected (Google Cloud Speech or Whisper)
**And** text-to-speech (TTS) provider is connected (Google Cloud TTS)
**And** OpenTelemetry traces are emitted for all calls

**Given** the service is running
**When** a call is received on the Voice Advisor number
**Then** the call is routed to the conversational AI handler
**And** a new conversation session is created
**And** the session tracks: call_id, farmer_id, turn_count, conversation_history

**Given** the service needs LLM capability
**When** the AI responds to farmer questions
**Then** Claude Sonnet is used for response generation
**And** MCP tools provide farmer context (Plantation, Collection, Knowledge, Action Plan)
**And** all LLM calls are traced via LangChain callbacks

**Given** external dependencies are unavailable
**When** STT, TTS, or LLM fails
**Then** graceful fallback is triggered (see Story 8.7)
**And** an alert is logged for monitoring

**Technical Notes:**
- Python FastAPI with async WebSocket support
- Africa's Talking for telephony
- Google Cloud Speech-to-Text v2 (Swahili model)
- Google Cloud TTS (Wavenet voices)
- Claude Sonnet for conversational AI
- Environment: farmer-power-{env} namespace

---

## Story 8.2: Swahili Speech-to-Text

As a **farmer speaking Swahili**,
I want my speech accurately transcribed,
So that the AI understands my questions.

**Acceptance Criteria:**

**Given** a farmer speaks during the call
**When** audio is captured
**Then** audio is streamed to the STT provider in real-time
**And** transcription begins immediately (streaming mode)
**And** interim results are available for responsive UI

**Given** the farmer speaks Swahili
**When** transcription is performed
**Then** the Swahili language model (sw-KE) is used
**And** accuracy target is >85% for common tea/farming vocabulary
**And** agricultural terms are recognized correctly

**Given** the farmer speaks with a regional accent
**When** transcription is performed
**Then** the model adapts to Kenyan Swahili pronunciation
**And** common code-switching (Swahili/English mix) is handled

**Given** background noise is present
**When** audio is captured
**Then** noise reduction is applied before STT
**And** voice activity detection filters silence
**And** only speech segments are transcribed

**Given** STT returns low confidence (<0.6)
**When** transcription completes
**Then** the system flags the utterance as unclear
**And** a clarification prompt is triggered: "I didn't quite catch that. Could you repeat?"

**Given** STT fails completely
**When** the service is unavailable
**Then** fallback to DTMF-based interaction is offered
**And** SMS fallback is triggered (see Story 8.7)

**Technical Notes:**
- Google Cloud Speech-to-Text v2 (streaming)
- Model: sw-KE (Swahili - Kenya)
- Sample rate: 8kHz (telephony)
- Enhanced model for improved accuracy
- Phrase hints: tea, quality, primary, secondary, grade

---

## Story 8.3: Intent Classification

As a **Conversational AI system**,
I want to classify farmer intents from their speech,
So that appropriate responses can be generated.

**Acceptance Criteria:**

**Given** a farmer's speech is transcribed
**When** intent classification runs
**Then** the intent is classified into categories: quality_question, action_plan_query, general_help, clarification, goodbye

**Given** the farmer asks "Why was my tea graded poorly?"
**When** classification runs
**Then** intent = "quality_question"
**And** entities extracted: time_reference="recent delivery"

**Given** the farmer asks "What should I do to improve?"
**When** classification runs
**Then** intent = "action_plan_query"
**And** the system fetches the farmer's current action plan

**Given** the farmer says "I don't understand"
**When** classification runs
**Then** intent = "clarification"
**And** the previous response is rephrased more simply

**Given** the farmer says "Goodbye" or "Asante"
**When** classification runs
**Then** intent = "goodbye"
**And** the call wrapping procedure is triggered

**Given** intent classification confidence is low (<0.5)
**When** the classifier is uncertain
**Then** a disambiguation question is asked: "Are you asking about your recent delivery or your weekly plan?"
**And** the response guides the farmer to clarify

**Technical Notes:**
- Intent classification: Claude Haiku (fast, cheap)
- Entity extraction: time_reference, topic, quantity
- Confidence threshold: 0.5 for disambiguation
- Intent history: tracked in conversation session

---

## Story 8.4: Personalized Response Generation

As a **farmer**,
I want personalized answers based on my quality data,
So that advice is relevant to my specific situation.

**Acceptance Criteria:**

**Given** a farmer asks a quality question
**When** response generation begins
**Then** MCP tools are invoked to gather context:
  - `get_farmer_summary(farmer_id)` for profile and trend
  - `get_recent_quality_events(farmer_id, days=7)` for recent deliveries
  - `get_farmer_analyses(farmer_id, past_7_days)` for diagnoses
  - `get_current_action_plan(farmer_id)` for recommendations

**Given** context is gathered
**When** the LLM generates a response
**Then** the response references the farmer's actual data: "{farmer_name}, your last delivery was 65% primary..."
**And** specific issues are mentioned by name
**And** actionable advice is provided

**Given** the farmer's trend is declining
**When** response is generated
**Then** the AI acknowledges the trend: "I notice your quality has been decreasing lately..."
**And** encouragement is included: "But here's what you can do..."

**Given** the farmer is performing well
**When** they ask a question
**Then** the AI acknowledges success: "You're doing great! Your 85% primary rate is above average."
**And** tips for maintaining quality are offered

**Given** the response is generated
**When** it is finalized
**Then** the response is appropriate for spoken delivery (short sentences, simple words)
**And** the response is in the farmer's selected language
**And** response length is limited to 30 seconds of TTS

**Technical Notes:**
- LLM: Claude Sonnet with MCP tools
- Max response tokens: 150 (for natural speech)
- Language: farmer's pref_lang or session language
- Conversation history: passed to LLM for context

---

## Story 8.5: Guided Dialogue Flow

As a **Conversational AI system**,
I want to guide conversations efficiently,
So that farmers get answers within the 3-minute limit.

**Acceptance Criteria:**

**Given** a conversation starts
**When** the greeting plays
**Then** the AI introduces itself: "I'm your Quality Advisor. How can I help you today?"
**And** the conversation turn counter starts at 1

**Given** the conversation proceeds
**When** each turn completes
**Then** the turn counter increments
**And** the turn is logged with: intent, response, duration

**Given** the conversation reaches turn 3
**When** the farmer continues
**Then** the AI gently guides toward closure: "Is there anything else quick I can help with?"
**And** turn 4 and 5 are available if needed

**Given** the conversation reaches turn 5
**When** the turn completes
**Then** the AI wraps up: "I hope that helped. Remember, you can call back anytime. Goodbye!"
**And** the call ends gracefully

**Given** the conversation exceeds 3 minutes
**When** the time limit approaches
**Then** a gentle warning plays: "We're almost out of time. Let me quickly summarize..."
**And** a brief summary of key points is provided
**And** the call wraps up

**Given** the farmer goes off-topic
**When** non-quality topics are detected
**Then** the AI politely redirects: "I'm here to help with tea quality. Is there something about your tea I can help with?"
**And** escalation to human is offered if farmer insists

**Technical Notes:**
- Max turns: 5
- Max duration: 3 minutes
- Turn tracking: conversation session state
- Off-topic detection: intent = "out_of_scope"

---

## Story 8.6: Streaming Response Delivery

As a **farmer**,
I want to hear responses without long delays,
So that the conversation feels natural.

**Acceptance Criteria:**

**Given** the AI generates a response
**When** response generation begins
**Then** streaming mode is used for LLM output
**And** TTS synthesis starts as soon as the first sentence is complete
**And** audio playback begins while subsequent sentences are generated

**Given** streaming is active
**When** the farmer hears the response
**Then** the perceived latency is <2 seconds from end of farmer speech
**And** audio plays smoothly without stuttering

**Given** a sentence is complete
**When** TTS synthesis runs
**Then** SSML formatting is applied for natural prosody
**And** appropriate pauses are inserted between sentences
**And** emphasis is added for key words

**Given** the farmer interrupts during playback
**When** speech is detected mid-response
**Then** playback stops immediately (barge-in)
**And** the new farmer speech is transcribed
**And** the AI adapts to the interruption

**Given** network latency is high
**When** streaming cannot achieve <2s
**Then** a filler phrase plays: "Let me think about that..."
**And** the response begins as soon as available
**And** total perceived latency remains acceptable

**Technical Notes:**
- LLM streaming: enabled for Claude Sonnet
- TTS chunking: per-sentence
- Barge-in: voice activity detection
- Latency budget: 2 seconds total
- Buffer: 1 sentence ahead for smooth playback

---

## Story 8.7: SMS Fallback Handling

As a **farmer whose speech wasn't understood**,
I want to receive an SMS with the information,
So that I still get help even if voice interaction fails.

**Acceptance Criteria:**

**Given** the AI cannot understand the farmer after 2 clarification attempts
**When** the third attempt fails
**Then** the AI offers SMS fallback: "I'm having trouble understanding. Would you like me to send you an SMS with your information?"

**Given** the farmer accepts SMS fallback (says yes or presses 1)
**When** fallback is triggered
**Then** the Notification Model is invoked
**And** an SMS is sent with: recent grade, primary %, and key action
**And** the call ends gracefully: "I've sent you an SMS. Goodbye!"

**Given** the farmer declines SMS fallback
**When** they indicate no (says no or presses 2)
**Then** the AI offers one more try: "Let's try once more. Please speak slowly."
**And** if still unsuccessful, escalation to human is offered

**Given** STT service is completely unavailable
**When** the call starts
**Then** the AI announces: "Our voice system is temporarily unavailable."
**And** SMS fallback is immediately offered
**And** the call is kept short (< 30 seconds)

**Given** LLM is unavailable
**When** response generation fails
**Then** a pre-recorded message plays: "I'm unable to answer right now. Let me send you an SMS."
**And** SMS fallback is triggered automatically
**And** the incident is logged for review

**Given** SMS fallback is triggered
**When** the SMS is sent
**Then** the SMS includes: farmer_name, last_grade, last_primary_%, ONE tip
**And** the SMS ends with: "Call back later for more help."
**And** the SMS uses the farmer's pref_lang

**Technical Notes:**
- SMS via Notification Model gRPC
- Fallback SMS template: pre-approved, 160 chars max
- Escalation: flag for human callback (if configured)
- Logging: failed_conversation events for analysis
