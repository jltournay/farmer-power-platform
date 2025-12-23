# Conversational AI Model Architecture

## Overview

The Conversational AI Model is the **8th Domain Model** - the interactive dialogue layer for the Farmer Power Cloud Platform. Unlike the existing Voice IVR (one-way playback in Notification Model), this model enables two-way conversational interactions where users can ask questions and receive personalized, context-aware responses.

**Core Responsibility:** Manage conversational sessions across multiple channels (voice, text, chat), understand user intent, retrieve relevant context, and generate personalized responses.

**Does NOT:** Own telephony infrastructure (uses Notification Model), own data (uses MCP to fetch from other models), or make business decisions.

## Architecture Diagram

```
+-------------------------------------------------------------------------+
|                    CONVERSATIONAL AI MODEL                              |
|                        (8th Domain Model)                               |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                      CHANNEL LAYER (Open)                         |  |
|  |                                                                   |  |
|  |  +---------------+  +---------------+  +---------------+         |  |
|  |  | Voice         |  | WhatsApp      |  | Web Chat      |  +more  |  |
|  |  | Adapter       |  | Adapter       |  | Adapter       |         |  |
|  |  | (MVP)         |  | (Future)      |  | (Future)      |         |  |
|  |  |               |  |               |  |               |         |  |
|  |  | - STT input   |  | - Text input  |  | - Text input  |         |  |
|  |  | - TTS output  |  | - Rich cards  |  | - Markdown    |         |  |
|  |  | - 3min limit  |  | - Images OK   |  | - Charts OK   |         |  |
|  |  +-------+-------+  +-------+-------+  +-------+-------+         |  |
|  |          +------------------+------------------+                  |  |
|  |                             |                                     |  |
|  +-----------------------------v-------------------------------------+  |
|                                |                                        |
|  +-----------------------------v-------------------------------------+  |
|  |                      PERSONA LAYER (Open)                         |  |
|  |                                                                   |  |
|  |  farmer_swahili:     warm, simple, 6th-grade, encouraging        |  |
|  |  farmer_kikuyu:      same warmth, Kikuyu vocabulary              |  |
|  |  factory_manager_en: professional, data-rich, concise            |  |
|  +-------------------------------------------------------------------+  |
|                                |                                        |
|  +-----------------------------v-------------------------------------+  |
|  |                 CONVERSATION ENGINE (Closed)                      |  |
|  |                                                                   |  |
|  |  +-------------------+  +-------------------+  +----------------+ |  |
|  |  | Intent            |  | Response          |  | State          | |  |
|  |  | Classifier        |  | Generator         |  | Manager        | |  |
|  |  | (Haiku - fast)    |  | (Sonnet - quality)|  | (LangGraph)    | |  |
|  |  +-------------------+  +-------------------+  +----------------+ |  |
|  |                                                                   |  |
|  |  Orchestration: LangGraph with MongoDB checkpointing             |  |
|  |  Turn Management: 3-5 turns max, streaming response              |  |
|  +-------------------------------------------------------------------+  |
|                                |                                        |
|  +-----------------------------v-------------------------------------+  |
|  |                    INTENT HANDLERS (Open)                         |  |
|  |                                                                   |  |
|  |  QualityImprovementHandler:  "How do I improve my grade?"        |  |
|  |  GradeExplanationHandler:    "Why did I get this grade?"         |  |
|  |  WeatherCorrelationHandler:  "Was it because of the rain?"       |  |
|  |  (Future handlers registered via plugin pattern)                 |  |
|  +-------------------------------------------------------------------+  |
|                                |                                        |
|  +-----------------------------v-------------------------------------+  |
|  |                    MCP CLIENTS (Existing)                         |  |
|  |                                                                   |  |
|  |  +------------+ +------------+ +------------+ +------------+     |  |
|  |  | Collection | | Knowledge  | | Action     | | Plantation |     |  |
|  |  | MCP        | | MCP        | | MCP        | | MCP        |     |  |
|  |  +------------+ +------------+ +------------+ +------------+     |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  Persistence: MongoDB (conversation state, transcripts)                 |
|  External: Telephony via Notification Model, LLM via AI Model gateway   |
|                                                                         |
+-------------------------------------------------------------------------+
```

## Open-Closed Design Principle

The Conversational AI Model is built on the **Open-Closed Principle**: open for extension, closed for modification.

| Component | Type | Extension Method |
|-----------|------|------------------|
| **Channel Adapters** | Open | Implement `ChannelAdapter` interface |
| **Personas** | Open | Add YAML configuration file |
| **Intent Handlers** | Open | Implement `IntentHandler` interface |
| **Conversation Engine** | Closed | Never modified, stable core |

**Adding a New Channel (e.g., Telegram):**
1. Create `TelegramAdapter` implementing `ChannelAdapter`
2. Register in plugin registry
3. No changes to conversation engine

## Channel Adapter Interface

```python
class ChannelAdapter(ABC):
    """Base interface for all conversation channels."""

    @abstractmethod
    async def receive_input(self) -> ConversationInput:
        """Receive user input (speech, text, etc.)"""
        pass

    @abstractmethod
    async def send_output(self, response: ConversationOutput) -> None:
        """Send response (TTS, text, rich card, etc.)"""
        pass

    @abstractmethod
    def get_constraints(self) -> ChannelConstraints:
        """Return channel-specific limits (duration, length, etc.)"""
        pass

@dataclass
class ChannelConstraints:
    max_duration_seconds: int
    max_message_length: int
    supports_rich_content: bool
    supports_images: bool
```

## Voice Adapter (MVP)

The Voice Adapter handles farmer voice conversations via Africa's Talking telephony.

**Call Flow:**

```
Farmer Phone                   Conversational AI Model
     |                                   |
     |------ Call *123# -------------->  |
     |                                   |
     |  [Africa's Talking webhook]       |
     |                                   |
     |<----- "Karibu! Sema swali lako" --|  (Welcome! Say your question)
     |                                   |
     |------ Farmer speaks in Swahili -->|
     |                                   |
     |       [STT: Google Cloud Speech]  |
     |       [Intent: Haiku classifier]  |
     |       [Context: MCP fetch]        |
     |       [Response: Sonnet generate] |
     |       [TTS: Google Cloud TTS]     |
     |                                   |
     |<----- Streaming TTS response -----|
     |                                   |
     |------ Follow-up question -------->|
     |                                   |
     |       [Continue dialogue...]      |
     |                                   |
     |<----- Final advice + goodbye -----|
     |                                   |
     |------ Hang up ------------------->|
     |                                   |
     |       [Log conversation]          |
     |       [Link to farmer profile]    |
```

**Latency Optimization - 3-Phase Streaming:**

```
PHASE 1 (immediate, <0.5s):
  - Play acknowledgment: "Sawa Wanjiku, nimeelewa swali lako."
  - (Intent classification running in background)

PHASE 2 (while LLM processing, ~1-2s):
  - Play filler: "Ninaangalia mfuko wako wa jana..."
  - (MCP fetch + LLM response generation running)

PHASE 3 (LLM result arrives):
  - Play actual advice: "Unyevu ulikuwa 18%. Anika siku 4 baada ya mvua."
  - (Streaming TTS as response is generated)
```

**Turn-Based Dialogue (MVP):**

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Barge-in | Not supported | Simpler implementation, clearer turn boundaries |
| Turn signal | Audio cue "Sema sasa" | Clear indication farmer can speak |
| Max turns | 5 | Cost control, keeps conversations focused |
| Max duration | 3 minutes | Cost control, telephony budget |

## Integration with Existing Models

The Conversational AI Model does NOT duplicate functionality. It orchestrates existing capabilities:

```
+----------------------+     +-------------------------+
| Conversational AI    |     | AI Model                |
| Model                |     | (6th Domain)            |
+----------------------+     +-------------------------+
|                      |     |                         |
| - Session management |     | - LLM Gateway           |
| - Channel adapters   |---->| - Agent orchestration   |
| - Turn management    |     | - RAG Engine            |
| - Persona selection  |     |                         |
+----------------------+     +-------------------------+
         |
         | MCP calls
         v
+--------+---------+--------+---------+
|        |         |        |         |
v        v         v        v         v
Collection  Knowledge  Action   Plantation  Notification
Model       Model      Model    Model       Model
(quality)   (advice)   (plans)  (farmer)    (telephony)
```

**Data Flow for Voice Conversation:**

```
1. Farmer calls *123#
   └── Africa's Talking webhook → Notification Model → Conversational AI Model

2. Farmer identified (caller ID lookup)
   └── Conversational AI → Plantation MCP → Get farmer profile

3. Farmer speaks: "Kwa nini chai yangu ilipata daraja la chini?"
   └── Voice Adapter → Google STT → Swahili transcription

4. Intent classified
   └── Conversation Engine → Haiku → "grade_explanation" intent

5. Context fetched
   └── Parallel MCP calls:
       ├── Collection MCP → Latest quality result
       ├── Plantation MCP → Farmer history
       └── Knowledge MCP → Relevant best practices

6. Response generated
   └── Conversation Engine → Sonnet → Personalized explanation

7. Response delivered
   └── Response → Google TTS → Streaming audio → Farmer phone

8. Conversation logged
   └── MongoDB: session state, transcript, farmer_id linkage
```

## Persona Configuration

Personas define how the AI communicates with different user types:

```yaml
# personas/farmer_swahili.yaml
persona_id: farmer_swahili
name: "Mshauri wa Ubora" # Quality Advisor
description: "Warm, encouraging advisor for Swahili-speaking farmers"

language:
  input: sw  # Swahili STT
  output: sw # Swahili TTS

tone:
  warmth: high
  formality: low
  encouragement: high

vocabulary:
  reading_level: "grade_6"
  avoid:
    - technical_jargon
    - english_loanwords_when_swahili_exists
  prefer:
    - simple_sentences
    - concrete_examples
    - local_references

constraints:
  max_response_sentences: 4
  always_include_action: true
  reference_farmer_history: true

greeting: "Karibu {farmer_name}! Nimefurahi kusaidia leo."
goodbye: "Asante {farmer_name}! Tutaonana wakati wa mavuno yako."
not_understood: "Samahani, sikusikia vizuri. Sema tena tafadhali?"
```

## Conversation State Management

LangGraph manages conversation state with MongoDB checkpointing:

```python
@dataclass
class ConversationState:
    session_id: str
    farmer_id: str
    channel: str                    # "voice", "whatsapp", "webchat"
    persona: str                    # "farmer_swahili", etc.
    turn_count: int
    started_at: datetime
    last_activity: datetime

    # Context accumulated during conversation
    quality_context: Optional[QualityContext]
    farmer_profile: Optional[FarmerProfile]
    intent_history: List[str]

    # Conversation transcript
    messages: List[ConversationMessage]

    # Status
    status: ConversationStatus      # "active", "completed", "timeout", "fallback"
    fallback_reason: Optional[str]

class ConversationMessage:
    role: str                       # "farmer", "advisor"
    content: str                    # Transcription or response text
    timestamp: datetime
    audio_url: Optional[str]        # For voice, stored in blob
    confidence: Optional[float]     # STT confidence score
```

## SMS Fallback

When the AI cannot understand the farmer or conversation fails:

```python
async def handle_fallback(session: ConversationState, reason: str):
    """Send SMS with actionable info when voice fails."""

    # Get last action plan if available
    action_plan = await action_mcp.get_latest(session.farmer_id)

    sms_content = f"""
{session.farmer_profile.name}, samahani sikusikia vizuri.

Hii ni ushauri wako:
{action_plan.farmer_message if action_plan else "Tafadhali piga simu tena baadaye."}

Maswali? Piga {SUPPORT_NUMBER}
    """

    await notification_mcp.send_sms(
        farmer_id=session.farmer_id,
        content=sms_content,
        trigger="voice_fallback"
    )

    # Log fallback event
    session.status = ConversationStatus.FALLBACK
    session.fallback_reason = reason
    await save_session(session)
```

## Cost Model

| Component | Unit Cost | Per Call Estimate |
|-----------|-----------|-------------------|
| Africa's Talking Voice | $0.05/min | $0.125 (2.5 min avg) |
| Google Cloud STT | $0.006/15s | $0.024 (60s farmer speech) |
| Google Cloud TTS | $0.000016/char | $0.016 (1000 chars) |
| OpenRouter (Haiku) | $0.00025/1K tokens | $0.0025 (10 calls) |
| OpenRouter (Sonnet) | $0.003/1K tokens | $0.06 (3 responses) |
| MCP overhead | negligible | $0.00 |
| **Total per call** | | **~$0.23** |

**Monthly Projection (50K calls):**
- Voice calls: $11,500/month
- At 10% adoption of 500K farmers

## Logging and Analytics

All conversations are logged for improvement:

```python
# Stored per conversation
ConversationLog:
  session_id: str
  farmer_id: str
  factory_id: str
  start_time: datetime
  end_time: datetime
  duration_seconds: int
  turn_count: int
  channel: str
  persona: str

  # Quality metrics
  stt_accuracy: float           # Estimated from confidence scores
  intent_recognition: List[str] # Intents detected per turn
  personalization_used: bool    # Did we reference farmer history?

  # Outcome
  completion_status: str        # "completed", "abandoned", "fallback"
  fallback_reason: Optional[str]

  # Full transcript (for analysis)
  messages: List[ConversationMessage]

  # For grade improvement tracking
  pre_call_grade: Optional[str]
  post_call_grade: Optional[str]  # Filled after next delivery
```

## Testing Strategy

| Test Type | Approach | Coverage |
|-----------|----------|----------|
| **Unit Tests** | Mock channel adapters, test conversation engine logic | >90% |
| **Contract Tests** | Validate all adapters implement interface correctly | 100% |
| **Intent Tests** | Golden set of farmer utterances → expected intents | >90% |
| **Response Tests** | Sampled responses reviewed by agronomist | Weekly |
| **Integration Tests** | Full call flow with test telephony numbers | Per release |
| **Load Tests** | Concurrent call simulation | 100+ concurrent |

## MVP vs Future Capabilities

| Capability | MVP | V1.1 | V2 | V3 |
|------------|-----|------|----|----|
| Voice inbound (Swahili) | ✓ | ✓ | ✓ | ✓ |
| TTS (Swahili/Kikuyu/Luo) | ✓ | ✓ | ✓ | ✓ |
| Guided dialogue (3-5 turns) | ✓ | ✓ | ✓ | ✓ |
| SMS fallback | ✓ | ✓ | ✓ | ✓ |
| Conversation logging | ✓ | ✓ | ✓ | ✓ |
| WhatsApp text | | ✓ | ✓ | ✓ |
| Kikuyu/Luo STT | | | ✓ | ✓ |
| Web chat (factory) | | | ✓ | ✓ |
| Proactive outbound calls | | | | ✓ |
| Smart barge-in | | | | ✓ |

---

## Updated Model Overview

The Farmer Power Platform now has **8 Domain Models**:

| # | Model | Responsibility |
|---|-------|----------------|
| 1 | Collection Model | Data ingestion, document storage, retrieval |
| 2 | Knowledge Model | Analyses, diagnoses, best practices storage |
| 3 | Plantation Model | Farmer profiles, farm data, preferences |
| 4 | Action Plan Model | Weekly action plan generation and delivery |
| 5 | Market Analysis Model | Market intelligence, pricing, demand |
| 6 | AI Model | Centralized LLM orchestration, RAG, agents |
| 7 | Notification Model | SMS, WhatsApp, Voice IVR (one-way) |
| 8 | **Conversational AI Model** | Two-way dialogue across channels (NEW) |

**Model Interaction Diagram:**

```
                    External Users
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   +-----------+   +-----------+   +-----------+
   | Voice     |   | WhatsApp  |   | Web Chat  |
   | (Farmers) |   | (Farmers) |   | (Factory) |
   +-----------+   +-----------+   +-----------+
          │               │               │
          └───────────────┼───────────────┘
                          │
                          ▼
   +--------------------------------------------------+
   |          CONVERSATIONAL AI MODEL (8)             |
   |  Channel Adapters → Engine → Intent Handlers    |
   +--------------------------------------------------+
                          │
                          │ MCP + Events
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   +-----------+   +-----------+   +-----------+
   | AI Model  |   | Collection|   | Knowledge |
   |    (6)    |   |    (1)    |   |    (2)    |
   +-----------+   +-----------+   +-----------+
          │               │               │
          │               ▼               │
          │        +-----------+          │
          │        | Plantation|          │
          │        |    (3)    |          │
          │        +-----------+          │
          │               │               │
          ▼               ▼               ▼
   +-----------+   +-----------+   +-----------+
   | Action    |   |  Market   |   | Notific-  |
   | Plan (4)  |   |   (5)     |   | ation (7) |
   +-----------+   +-----------+   +-----------+
```