---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - '_bmad-output/analysis/product-brief-farmer-power-platform-2025-12-16.md'
  - '_bmad-output/project-context.md'
workflowType: 'product-brief'
lastStep: 5
project_name: 'voice-quality-advisor'
user_name: 'Jeanlouistournay'
date: '2025-12-20'
parent_project: 'farmer-power-platform'
feature_type: 'extension'
---

# Product Brief: Conversational AI Model (Voice Quality Advisor MVP)

**Date:** 2025-12-20
**Author:** Jeanlouistournay

---

## Executive Summary

**The One-Sentence Value Proposition:** The Conversational AI Model transforms quality data into personalized, interactive guidance - enabling farmers to ask "How do I improve?" via voice, and factory managers to query data via chat, all grounded in platform data and extensible to any channel.

The Conversational AI Model is a new domain model extending the Farmer Power Platform. While the existing Voice IVR delivers pre-generated action plans one-way, users cannot ask questions or engage in dialogue. This creates a gap: users receive feedback but cannot explore it, ask follow-ups, or get guidance tailored to their constraints.

**MVP Focus:** Farmer Voice Quality Advisor - a Swahili-first voice chatbot where farmers call to discuss quality improvement. The AI listens, understands intent, retrieves personalized context (quality history, weather, past successes), and responds with tailored guidance through 3-5 turn guided dialogue.

**Extensible by Design:** Built on the Open-Closed Principle, the architecture supports future channels (WhatsApp, Web Chat, SMS) and user types (factory managers, regulators) without modifying core logic. New capabilities are added through plugin adapters, not code changes.

**Key Constraint:** All conversations are grounded in Farmer Power Platform data - quality intake, knowledge base, action plans, and plantation model history. No speculation, only data-backed guidance.

---

## Core Vision

### Problem Statement

Users who receive quality data still don't understand HOW to act on it:
- Farmers receive grades but can't ask: *"Why did this happen to MY crop?"*
- Factory managers see dashboards but can't ask: *"Which farmers need intervention?"*
- The current Voice IVR plays fixed scripts - it cannot listen, understand, or adapt.

Users with questions have no conversational channel to ask them.

### Problem Impact

- **Knowledge Gap:** Users receive data without understanding, leading to repeated mistakes
- **Frustration:** "The system tells me what's wrong but won't help me fix it"
- **Missed Improvement:** Users who WANT to improve lack interactive guidance
- **Wasted Potential:** Rich historical data exists but isn't accessible conversationally

### Why Existing Solutions Fall Short

| Current Capability | Limitation |
|--------------------|------------|
| SMS feedback | Too brief, no follow-up possible |
| Voice IVR | One-way playback, cannot answer questions |
| Factory dashboards | Visual only, no conversational query |
| Extension officers | Scarce, expensive, not always available |

No existing channel allows users to ASK and RECEIVE personalized, data-driven guidance through natural conversation.

### Proposed Solution

A **Conversational AI Model** with pluggable channel adapters, starting with farmer voice:

**MVP: Farmer Voice Quality Advisor**

1. Farmer calls the Voice Advisor number
2. System identifies farmer (caller ID or spoken ID)
3. Farmer speaks their question in Swahili
4. AI retrieves context: latest quality result, farm history, weather, past action plans
5. AI responds in farmer's preferred language (Swahili/Kikuyu/Luo via TTS)
6. Guided dialogue: AI asks clarifying questions (3-5 turns max)
7. Farmer receives actionable, personalized recommendation
8. If AI cannot understand -> SMS fallback with details
9. Max 3 minutes per session (cost control)

**Example Conversation:**
> **Wanjiku:** "Chai yangu ilipata daraja la chini. Nifanye nini?"
> *(My tea got a low grade. What should I do?)*
>
> **AI:** "Wanjiku, mfuko wako wa jana ulikuwa na unyevu wa 18%, lakini lengo ni 14%. Mvua ilinyesha siku tatu zilizopita. Je, ulianika majani kwa siku ngapi?"
> *(Your bag yesterday had 18% moisture, target is 14%. It rained 3 days ago. How many days did you dry?)*
>
> **Wanjiku:** "Siku mbili tu."
> *(Only two days.)*
>
> **AI:** "Mwezi Machi ulipopata Daraja A, ulianika siku nne baada ya mvua. Jaribu kuongeza siku mbili zaidi."
> *(In March when you got Grade A, you dried four days after rain. Try adding two more days.)*

---

## Technical Architecture: Open-Closed Design

### Core Principle

**Open for Extension, Closed for Modification.** The core conversation engine is stable and never modified. New capabilities are added through plugin registration.

### Layered Architecture

```
+-------------------------------------------------------------------+
|                     CHANNEL LAYER (Open)                          |
|  +---------------+ +---------------+ +---------------+            |
|  | Voice         | | WhatsApp      | | Web Chat      |  + more   |
|  | Adapter       | | Adapter       | | Adapter       |            |
|  | (MVP)         | | (Future)      | | (Future)      |            |
|  +-------+-------+ +-------+-------+ +-------+-------+            |
|          +-----------------+------------------+                   |
|                            v                                      |
+-------------------------------------------------------------------+
|                    PERSONA LAYER (Open)                           |
|  - farmer_swahili: warm, simple, 6th-grade, encouraging          |
|  - farmer_kikuyu: same warmth, Kikuyu vocabulary                 |
|  - factory_manager_en: professional, data-rich, concise          |
+-------------------------------------------------------------------+
|               CONVERSATION ENGINE (Closed)                        |
|  - LangGraph orchestration with MongoDB checkpointing            |
|  - Intent classification (Haiku - fast)                          |
|  - Response generation (Sonnet - quality)                        |
|  - Turn management and state persistence                         |
+-------------------------------------------------------------------+
|                 INTENT HANDLERS (Open)                            |
|  - QualityImprovementHandler (MVP)                               |
|  - GradeExplanationHandler (MVP)                                 |
|  - WeatherCorrelationHandler (Future)                            |
+-------------------------------------------------------------------+
|                   DATA LAYER - MCP (Existing)                     |
|  MCP-Quality | MCP-Knowledge | MCP-Action | MCP-Plantation       |
+-------------------------------------------------------------------+
```

### Latency Optimization: Streaming Response

To achieve natural conversation (<2s perceived latency), responses are streamed in phases:

```
PHASE 1 (immediate, <0.5s):
+-- Acknowledgment: "Sawa Wanjiku, nimeelewa swali lako."

PHASE 2 (while LLM processing, ~1-2s):
+-- Context filler: "Ninaangalia mfuko wako wa jana..."

PHASE 3 (LLM result arrives):
+-- Actual advice: "Unyevu ulikuwa 18%. Anika siku 4 baada ya mvua."
```

Farmer hears continuous speech while computation happens in background.

### Extension Path

| Phase | Scope | What's Added |
|-------|-------|--------------|
| **MVP** | Farmer Voice (Swahili) | VoiceAdapter, farmer_swahili persona |
| **V1.1** | Farmer WhatsApp | WhatsAppAdapter (text + images) |
| **V2** | Factory Web Chat | WebChatAdapter, factory_manager_en persona |
| **V3** | Proactive outreach | OutboundVoiceAdapter, decline-triggered calls |

---

## Key Differentiators

| Differentiator | Why It Matters |
|----------------|----------------|
| **Two-way dialogue** | Users speak, AI listens and responds - not just playback |
| **Personalized to THEIR data** | "Last time YOU got Grade A, you did X" |
| **Swahili natural speech** | No menus, no buttons - just talk |
| **Guided, not open-ended** | AI leads to actionable answers in 3-5 turns |
| **Grounded in platform data** | No hallucination - only data-backed recommendations |
| **Open-Closed architecture** | New channels/personas added without modifying core |
| **Accessible** | Works on any phone, no smartphone needed, no literacy required |

---

## Party Mode Insights Applied

| Contributor | Key Insight Incorporated |
|-------------|-------------------------|
| **Winston (Architect)** | Generic model name, layered architecture, streaming response for latency, Open-Closed principle |
| **Sally (UX Designer)** | Persona per user type, filler audio for natural feel, turn-based dialogue for MVP simplicity |
| **John (PM)** | Evolutionary architecture (MVP -> extend), target declining-quality farmers first |
| **Murat (Test Architect)** | Contract testing for adapters, mock channels for fast unit tests, pilot with 50 farmers for audio corpus |
| **Amelia (Developer)** | Plugin registry pattern, self-registering adapters, clear directory structure |

---

## Target Users

### Primary User: "Wanjiku the Improver"

**Profile Summary**

| Attribute | Detail |
|-----------|--------|
| **Archetype** | Farmer who wants to improve and asks questions |
| **Name** | Wanjiku Mwangi |
| **Age** | 42 years old |
| **Location** | 0.4 hectare tea plot, Nyeri County, Kenya |
| **Phone** | Basic feature phone (no smartphone) |
| **Language** | Swahili (primary), limited English |
| **Tech Comfort** | Uses M-Pesa daily, familiar with IVR systems |
| **Income Dependency** | Tea is 70% of household income |
| **Current Performance** | Typically Grade B/C (65-78), aspires to Grade A |

**Behavioral Segmentation**

Not all farmers will use the Voice Advisor. The primary user is distinguished by motivation:

| Farmer Type | Behavior After SMS | Voice Advisor User? |
|-------------|-------------------|---------------------|
| **Self-Sufficient** | Reads action plan, understands, implements alone | No |
| **Implementation Seeker** | Wants more detail on HOW to implement | **Yes - Primary** |
| **Constraint-Limited** | "I can't do that because..." - needs alternatives | **Yes - Primary** |
| **Passive Accepter** | Glances at SMS, continues as usual | No |

**Her Story**

Wanjiku receives an SMS: "⭐⭐⭐ (68) - Unyevu mwingi. Anika siku zaidi baada ya mvua."
*(3 stars, score 68 - High moisture. Dry more days after rain.)*

She thinks: *"I dried for 2 days - how long IS enough? And what if it rains again tomorrow?"*

She sees the call prompt and dials immediately. She wants the AI to explain:
- **Why** exactly her moisture was high (understanding the cause)
- **How many days** to dry given the recent weather (specific, contextual action)
- **What she did last time** when she got a better grade (learning from her own success)

**Key Needs**

| Need | What She's Asking | Voice Advisor Response |
|------|-------------------|----------------------|
| **Understanding** | "Why did this happen?" | "Mvua ilinyesha siku 3 zilizopita, unyevu ulikuwa 18%..." |
| **Specific Action** | "What exactly should I do?" | "Anika siku 4 baada ya mvua, sio siku 2..." |
| **Personalization** | "What worked for ME before?" | "Mwezi Machi ulipofanya hivyo, ulipata Daraja A..." |
| **Constraint Handling** | "But I don't have X..." | "Ukikosa racks, tumia turubai safi juani..." |

**Device & Channel Constraints**

| Constraint | Implication |
|------------|-------------|
| Basic phone only | Voice is the ONLY interactive channel (no apps, no web) |
| No data plan | Cannot use WhatsApp or internet-based chat |
| Familiar with IVR | Comfortable with phone menus, voice prompts |
| Swahili preferred | Must support Swahili speech recognition and TTS |

**Success Moment**

Wanjiku hangs up thinking: *"Siku nne baada ya mvua - kama nilivyofanya Machi. Ninaweza kufanya hivyo."*
*(Four days after rain - like I did in March. I can do that.)*

Next delivery: Grade A. The feedback loop closes.

---

### User Journey: SMS to Voice to Action

```
+-------------------------------------------------------------------+
| TRIGGER: SMS Arrives                                              |
| "⭐⭐⭐ (68) Unyevu mwingi. Piga *123# kwa ushauri."              |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
| DECISION POINT: Does farmer want more help?                       |
|                                                                   |
|   Self-sufficient --> Implements action plan alone                |
|   Needs help --> Calls *123#                                      |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
| VOICE CONVERSATION (3 min max)                                    |
|                                                                   |
| 1. System identifies farmer (caller ID)                           |
| 2. Farmer speaks question in Swahili                              |
| 3. AI retrieves context (grade, history, weather)                 |
| 4. AI responds with personalized guidance                         |
| 5. Guided dialogue: 3-5 turns of Q&A                              |
| 6. Farmer receives actionable recommendation                      |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
| OUTCOME: Farmer Hangs Up With Clarity                             |
|                                                                   |
| - Understands WHY the issue occurred                              |
| - Knows EXACTLY what to do differently                            |
| - Confident it's achievable with their resources                  |
+-----------------------------+-------------------------------------+
                              |
                              v
+-------------------------------------------------------------------+
| NEXT DELIVERY: Quality Improves                                   |
|                                                                   |
| Feedback loop closes. Farmer sees result of advice.               |
+-------------------------------------------------------------------+
```

---

### User Acceptance Criteria

**Wanjiku (Farmer) - Voice Quality Advisor:**

- [ ] Can call from any basic phone (no app required)
- [ ] Identified by caller ID or spoken farmer ID
- [ ] Speaks questions in natural Swahili
- [ ] Receives response in Swahili (or Kikuyu/Luo via TTS)
- [ ] Conversation feels natural (<2s response delay)
- [ ] Gets personalized advice based on HER quality history
- [ ] AI references her past successes ("In March you...")
- [ ] Conversation stays focused (3-5 turns, 3 min max)
- [ ] If AI doesn't understand -> SMS fallback sent
- [ ] Hangs up with clear, actionable next step

---

### Non-Users (Out of Scope for MVP)

| User Type | Why Not MVP | Future Consideration |
|-----------|-------------|---------------------|
| Farmers without phones | Cannot access voice channel | Community listening groups? |
| Non-Swahili speakers | STT limited to Swahili MVP | Add Kikuyu/Luo STT in V2 |
| Factory managers | Different needs, different channel | Web chat in V2 |
| Extension officers | Advisory role, not direct user | Mobile chat in V3 |
| Regulators | Analytics, not conversation | Dashboard queries in V3 |

---

## Success Metrics

### North Star Metric

**Grade Improvement Rate for Voice Advisor Users**

> "Did farmers who called the Voice Advisor improve their quality compared to those who didn't?"

| Metric | Definition | Target | Timeframe |
|--------|------------|--------|-----------|
| **Grade Improvement Rate** | % of Voice Advisor callers whose grade improves on next delivery | >40% | Per delivery |
| **Caller vs Non-Caller Delta** | Grade improvement difference: callers vs farmers who only received SMS | +15 percentage points | 3 months |

This is the ultimate proof that conversational, personalized guidance creates real behavior change.

---

### User Success Metrics

**Wanjiku's Success = She improves her quality**

| Metric | What It Measures | Target | Measurement |
|--------|------------------|--------|-------------|
| **Call Completion Rate** | % of calls reaching natural conclusion (not mid-call hang-up) | >80% | System logs |
| **Actionable Outcome** | % of calls where farmer receives specific action to take | >95% | Conversation analysis |
| **Comprehension Confirmation** | % of calls where farmer verbally confirms understanding | >70% | Transcript analysis |
| **Repeat Usage** | % of farmers who call again within 30 days | >25% | Caller tracking |
| **Grade Improvement (Individual)** | % of callers whose next delivery grade improves | >40% | Quality data correlation |

**Leading Indicators (Predict Success):**
- High call completion -> Farmer engaged with advice
- Actionable outcome delivered -> Farmer knows what to do
- Comprehension confirmed -> Farmer understood the advice

**Lagging Indicator (Proves Success):**
- Grade improvement -> Farmer actually implemented and succeeded

---

### Business Objectives

**Voice Advisor Business Case**

| Objective | Metric | Target | Timeframe |
|-----------|--------|--------|-----------|
| **Adoption** | % of SMS recipients who call Voice Advisor | 10-20% | Ongoing |
| **Engagement Depth** | Average conversation turns per call | 3-4 turns | Ongoing |
| **Cost Efficiency** | Cost per call (telephony + STT + LLM + TTS) | <$0.30 | Ongoing |
| **Scalability Proof** | Successful calls per day at pilot scale | 100+ calls/day | Pilot |
| **Extension Officer Comparison** | Cost per farmer interaction vs human visit | <10% of officer cost | 6 months |

**Value Proposition Validation:**
- Voice Advisor call: ~$0.30, instant, scalable
- Extension officer visit: ~$5-10, requires scheduling, limited reach
- **Target:** 20x more cost-effective than human advisory

---

### Key Performance Indicators (KPIs)

**Operational KPIs (System Health)**

| KPI | Target | Alert Threshold |
|-----|--------|-----------------|
| **STT Accuracy (Swahili)** | >85% word accuracy | <75% |
| **Response Latency (perceived)** | <2 seconds | >3 seconds |
| **Call Setup Success** | >98% | <95% |
| **SMS Fallback Rate** | <15% | >25% |
| **Average Call Duration** | 1.5-2.5 minutes | >3.5 minutes |
| **System Uptime** | >99.5% | <99% |

**Conversation Quality KPIs**

| KPI | Target | Measurement Method |
|-----|--------|-------------------|
| **Intent Recognition Accuracy** | >90% | Sampled transcript review |
| **Personalization Rate** | >80% of responses reference farmer's history | Transcript analysis |
| **Advice Correctness** | >95% agronomically sound | Agronomist spot-check |
| **Conversation Coherence** | <5% off-topic or confused exchanges | Transcript review |

---

### Pilot Success Criteria

**50-Farmer Pilot Validation**

| Criteria | Threshold for Success | Measurement |
|----------|----------------------|-------------|
| **Adoption** | >10 farmers call (20%) | Call logs |
| **Completion** | >8 of 10 complete conversation (80%) | Call logs |
| **Grade Improvement** | >4 of 10 callers improve next delivery (40%) | Quality data |
| **No Critical Failures** | 0 calls with harmful/incorrect advice | Agronomist review |
| **Cost Validation** | Average cost <$0.35/call | Cost tracking |

**Pilot -> Scale Decision:**
- If pilot meets all 5 criteria -> Proceed to 500-farmer rollout
- If 3-4 criteria met -> Iterate and re-pilot
- If <3 criteria met -> Reassess approach

---

### Measurement Strategy

**Data Sources**

| Data | Source | Frequency |
|------|--------|-----------|
| Call logs (duration, completion, fallback) | Telephony provider (Africa's Talking) | Real-time |
| Transcripts | STT output stored in MongoDB | Per call |
| Grade data | QC Analyzer via Collection Model | Per delivery |
| Farmer history | Plantation Model | On-demand |
| Cost data | OpenRouter + Telephony billing | Daily |

**Reporting Cadence**

| Report | Audience | Frequency |
|--------|----------|-----------|
| Operational Dashboard | Platform Team | Real-time |
| Pilot Progress Report | Leadership | Weekly |
| Grade Improvement Analysis | Product Team | Bi-weekly |
| Cost Analysis | Finance | Monthly |
| Agronomist Quality Review | Quality Team | Weekly (pilot), Monthly (scale) |

---

### Success Metrics Summary

| Category | Key Metric | Target |
|----------|------------|--------|
| **North Star** | Grade Improvement Rate (callers) | >40% |
| **User Success** | Call Completion Rate | >80% |
| **Business** | Cost per Call | <$0.30 |
| **Operations** | Response Latency | <2s |
| **Pilot Gate** | All 5 criteria met | Yes/No |

---

## MVP Scope

### Core Features (Must Have)

**Voice Channel Infrastructure**

| Feature | Description | Technical Component |
|---------|-------------|---------------------|
| **Inbound Voice Call** | Farmer calls dedicated number | Africa's Talking telephony |
| **Caller Identification** | Identify farmer via caller ID or spoken ID | Caller ID lookup + voice input |
| **Session Management** | 3 min max, cost control | LangGraph state + timer |

**Speech Processing**

| Feature | Description | Technical Component |
|---------|-------------|---------------------|
| **Swahili STT** | Transcribe farmer speech | Google Cloud Speech / Whisper |
| **Multi-language TTS** | Respond in Swahili, Kikuyu, or Luo | Google Cloud TTS |
| **Streaming Response** | 3-phase output for natural feel | Async audio queue |

**Conversation Engine**

| Feature | Description | Technical Component |
|---------|-------------|---------------------|
| **Intent Classification** | Understand quality-related questions | Haiku (fast) |
| **Response Generation** | Personalized, data-grounded advice | Sonnet (quality) |
| **Guided Dialogue** | 3-5 turns with clarifying questions | LangGraph orchestration |
| **Turn Management** | No barge-in, turn-based | Audio state machine |

**Data Integration (via MCP)**

| Feature | Description | Source Model |
|---------|-------------|--------------|
| **Quality Context** | Latest grade, defects, scores | Collection Model |
| **Farmer History** | Past deliveries, trends | Plantation Model |
| **Agronomic Knowledge** | Best practices, recommendations | Knowledge Model |
| **Action Plans** | Previously generated advice | Action Model |
| **Weather Data** | Recent conditions | Weather API via AI Model |

**Fallback & Logging**

| Feature | Description | Purpose |
|---------|-------------|---------|
| **SMS Fallback** | Send SMS if AI can't understand | Ensure farmer gets help |
| **Conversation Logging** | Store transcripts in MongoDB | Analysis, testing, improvement |
| **Cost Tracking** | Log STT + LLM + TTS + telephony costs | Business validation |

---

### Out of Scope (Deferred)

| Feature | Rationale | Target Phase |
|---------|-----------|--------------|
| **WhatsApp Text Adapter** | Different channel, plugin architecture allows later | V1.1 |
| **Web Chat Adapter** | For factory managers, different persona | V2 |
| **Kikuyu/Luo STT** | STT accuracy lower, Swahili-first | V2 |
| **Smart Barge-in** | Adds complexity, turn-based is simpler for MVP | V2 |
| **Proactive Outbound Calls** | Requires trigger logic, inbound-first | V3 |
| **Factory Manager Persona** | Different user type, web channel | V2 |
| **Pricing/Payment Queries** | Out of quality focus, different data | V2 |
| **Multi-factory Deployment** | Single factory pilot first | V2 |
| **Offline/USSD Fallback** | Voice works for target users | V3 |

---

### MVP Success Criteria (Go/No-Go Gate)

**Pilot: 50 Farmers, 1 Factory, 4 Weeks**

| Criteria | Threshold | Measurement |
|----------|-----------|-------------|
| **Adoption** | >20% of SMS recipients call | Call logs |
| **Completion** | >80% calls reach natural end | Call logs |
| **Understanding** | >85% STT accuracy on pilot corpus | Transcript review |
| **Quality Advice** | 0 harmful/incorrect recommendations | Agronomist review |
| **Grade Improvement** | >40% of callers improve next delivery | Quality data |
| **Cost** | <$0.35 per call average | Cost tracking |

**Decision Matrix:**

| Outcome | Action |
|---------|--------|
| All 6 criteria met | Scale to 500 farmers |
| 4-5 criteria met | Iterate, re-pilot |
| <4 criteria met | Reassess approach |

---

### Future Vision (Post-MVP Roadmap)

**V1.1 - Expand Farmer Channels**
- WhatsApp text adapter for farmers with smartphones
- Kikuyu/Luo STT as accuracy improves
- Weather forecast proactive alerts

**V2 - Factory Users & Intelligence**
- Web chat for factory managers
- Natural language queries on farmer data
- Aggregated quality insights

**V3 - Proactive & Predictive**
- Outbound calls when quality declines
- Predictive advice before harvest
- Community listening groups for phone-less farmers

**Long-term Platform Value**
- Conversational AI Model becomes the standard interaction layer
- All user types can "ask" the platform in natural language
- Voice, text, and chat unified through single engine

---

### Technical Boundaries

**What Conversational AI Model Owns:**
- Channel adapters (Voice first, others later)
- Conversation orchestration (LangGraph)
- Persona management
- Intent classification and response generation
- Session state and logging

**What Conversational AI Model Uses (Not Owns):**
- Telephony infrastructure (Notification Model)
- MCP servers (AI Model)
- Quality data (Collection Model)
- Farmer profiles (Plantation Model)
- Knowledge base (Knowledge Model)
- Action plans (Action Model)

This boundary ensures no duplication with existing models.

---

## Document Status

**Product Brief Complete**

| Step | Status |
|------|--------|
| 1. Initialization | Done |
| 2. Vision & Problem | Done |
| 3. Target Users | Done |
| 4. Success Metrics | Done |
| 5. MVP Scope | Done |

**Next Steps:**
1. Update `architecture.md` to add Conversational AI Model (8th model)
2. Create PRD if detailed requirements needed
3. Create Epics & Stories for implementation

**References:**
- Parent Platform Brief: `product-brief-farmer-power-platform-2025-12-16.md`
- Platform Architecture: `architecture.md`
- Project Context: `project-context.md`