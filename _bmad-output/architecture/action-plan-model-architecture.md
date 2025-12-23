# Action Plan Model Architecture

## Overview

The Action Plan Model is the **prescription engine** that transforms diagnoses from the Knowledge Model into actionable recommendations for farmers. It generates dual-format outputs: detailed reports for experts and simplified communications for farmers.

**Core Responsibility:** PRESCRIBE actions (what should the farmer do?)

**Does NOT:** Diagnose problems, collect data, or deliver messages (SMS delivery is infrastructure).

## Document Boundaries

> **This document defines WHAT to generate and WHEN.** For HOW generator agents are implemented (LLM config, prompts, workflows), see [`ai-model-architecture.md`](./ai-model-architecture.md).

| This Document Owns | AI Model Architecture Owns |
|-------------------|---------------------------|
| Output requirements (dual-format: report + farmer message) | Generator Agent implementation |
| Schedule (weekly) and trigger conditions | LLM selection and prompting |
| Translation and simplification requirements | Prompt engineering for translation |
| Farm-scale-aware recommendation guidelines | Scale-specific prompt templates |
| Notification infrastructure (SMS, Voice, channels) | N/A (notification is infrastructure, not AI) |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       ACTION PLAN MODEL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUTS (via MCP):                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ Knowledge MCP   │    │ Plantation MCP  │    │ Collection MCP  │     │
│  │ (analyses)      │    │ (farmer context)│    │ (raw data)      │     │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘     │
│           │                      │                      │               │
│           └──────────────────────┼──────────────────────┘               │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SELECTOR AGENT                              │   │
│  │  • Runs weekly (scheduled)                                       │   │
│  │  • Queries: "What analyses were created for farmer X this week?" │   │
│  │  • Routes to Action Plan Generator with combined context         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                 ACTION PLAN GENERATOR AGENT                      │   │
│  │                                                                   │   │
│  │  INPUT: Combined analyses + farmer context                        │   │
│  │                                                                   │   │
│  │  OUTPUT:                                                          │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐              │   │
│  │  │  DETAILED REPORT     │  │  FARMER MESSAGE      │              │   │
│  │  │  (Markdown)          │  │  (Simplified)        │              │   │
│  │  │                      │  │                      │              │   │
│  │  │  • Full analysis     │  │  • Local language    │              │   │
│  │  │  • Expert details    │  │  • Simple actions    │              │   │
│  │  │  • Confidence scores │  │  • SMS-ready format  │              │   │
│  │  │  • Source references │  │  • Cultural context  │              │   │
│  │  └──────────────────────┘  └──────────────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                  │                                       │
│                                  ▼                                       │
│              ┌─────────────────────────────────────┐                    │
│              │         ACTION PLAN DB              │                    │
│              │         (MongoDB)                   │                    │
│              │                                     │                    │
│              │  Both formats stored per plan       │                    │
│              └─────────────────────────────────────┘                    │
│                                  │                                       │
│                                  ▼                                       │
│              ┌─────────────────────────────────────┐                    │
│              │      INFRASTRUCTURE LAYER           │                    │
│              │      (Message Delivery - External)  │                    │
│              │                                     │                    │
│              │  SMS Gateway, Push Notifications    │                    │
│              └─────────────────────────────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Two-Agent Pattern

### Selector Agent
- **Trigger:** Weekly scheduled (e.g., every Monday at 6 AM)
- **Responsibility:** For each active farmer, query Knowledge MCP for analyses created in past 7 days
- **Logic:**
  - Has analyses → Route to Action Plan Generator with combined context
  - No analyses → Can trigger informational message (no action plan created)

### Action Plan Generator Agent
- **Input:** All analyses for one farmer (combined) + farmer context from Plantation MCP
- **Output:** Dual-format action plan stored in MongoDB
- **Behavior:** Combines multiple diagnoses into a coherent, prioritized action plan

## Dual-Format Output

Both formats are generated in the same workflow and stored together:

```json
{
    "_id": "action-plan-uuid",
    "farmer_id": "WM-4521",
    "week": "2025-W51",
    "created_at": "2025-12-16T06:00:00Z",
    "source_analyses": ["analysis-123", "analysis-456", "analysis-789"],

    "detailed_report": {
        "format": "markdown",
        "content": "# Weekly Action Plan for WM-4521\n\n## Summary\nBased on 3 analyses this week...\n\n## Priority Actions\n1. **Fungal Treatment Required** (High Priority)\n   - Diagnosis: Cercospora leaf spot detected\n   - Confidence: 87%\n   - Action: Apply copper-based fungicide within 3 days...\n\n## Full Analysis Details\n...",
        "priority_actions": 2,
        "analyses_summarized": 3
    },

    "farmer_message": {
        "language": "sw",
        "content": "Habari! Wiki hii tuligundua ugonjwa wa majani. Tafadhali...",
        "sms_segments": 2,
        "character_count": 280,
        "delivery_status": "pending"
    }
}
```

## Farmer Communication Preferences

The Action Plan Generator queries Plantation MCP for farmer profile including:
- **pref_channel:** SMS, Voice, WhatsApp - determines output format
- **pref_lang:** Swahili, Kikuyu, English, etc. - determines translation target
- **literacy_lvl:** Low, Medium, High - determines simplification level

## Farm-Scale-Aware Recommendations

The Action Plan Generator receives `farm_size_hectares` and `farm_scale` from Plantation MCP and tailors recommendations accordingly.

### Farm Scale Context

| Scale | Hectares | Recommendation Focus |
|-------|----------|---------------------|
| **Smallholder** | < 1 ha | Manual techniques, low-cost inputs, family labor optimization |
| **Medium** | 1-5 ha | Balance of technique + modest equipment ROI, seasonal labor planning |
| **Estate** | > 5 ha | Equipment investment, batch processing, labor management, efficiency at scale |

### Scale-Specific Recommendation Principles

The same treatment recommendation adapts based on farm scale:

| Aspect | Smallholder (<1 ha) | Medium (1-5 ha) | Estate (>5 ha) |
|--------|---------------------|-----------------|----------------|
| **Equipment** | Knapsack sprayer | Motorized sprayer | Tractor-mounted |
| **Labor** | Family members | 1-2 day laborers | Team leads per section |
| **Cost focus** | Low-cost alternatives | Bulk cooperative purchase | Supplier contracts |
| **Timing** | Single session | 2-day application window | Block-by-block schedule |
| **Documentation** | Verbal reminder | Basic tracking | Compliance documentation |

> **Implementation:** Scale-specific prompt templates are defined in [`ai-model-architecture.md`](./ai-model-architecture.md).

### Yield Performance Context

The Action Plan Generator also receives normalized yield metrics to provide context-aware feedback:

```yaml
# farmer_context from Plantation MCP
farmer_context:
  farmer_id: "WM-4521"
  farm_size_hectares: 1.5
  farm_scale: "medium"

  performance:
    yield_kg_per_hectare_30d: 120
    yield_vs_regional_avg: 0.85      # 85% of regional average
    yield_percentile: 42             # 42nd percentile among medium farms
    improvement_trend: "improving"
```

This enables recommendations like:
- "Your yield is 15% below regional average - focusing on plucking technique could help"
- "You're in the top 25% of medium farms in your region - maintain current practices"
- "Yield improving steadily - your recent changes are working"

### Action Plan Output with Scale Context

```json
{
    "farmer_id": "WM-4521",
    "farm_scale": "medium",
    "farm_size_hectares": 1.5,

    "detailed_report": {
        "content": "# Weekly Action Plan for WM-4521\n\n## Farm Context\nMedium-scale farm (1.5 ha), yield at 85% of regional average.\n\n## Priority Actions\n1. **Fungal Treatment** (scaled for 1.5 ha)...",
        "scale_specific_notes": "Recommendations optimized for medium-scale operation"
    },

    "farmer_message": {
        "content": "Habari! Shamba lako la hekta 1.5 linahitaji...",
        "includes_yield_context": true
    }
}
```

## Translation and Simplification

The Action Plan Generator Agent handles (based on farmer preferences):
- **Language Translation:** From English analysis to farmer's `pref_lang`
- **Simplification:** Adjusted to farmer's `literacy_lvl` (low = very simple, high = more detail)
- **Prioritization:** Multiple issues → Ordered by urgency/impact
- **Cultural Context:** Region-appropriate recommendations
- **Format Adaptation:** Based on `pref_channel` (SMS length, voice script, WhatsApp rich text)

## Empty State Handling

When Selector Agent finds no analyses for a farmer:
- **No action plan created** (nothing to prescribe)
- **Optional:** Trigger informational message ("No issues detected this week, keep up the good work!")
- **Tracking:** Record that farmer was checked but had no analyses

## No MCP Server

**Decision:** Action Plan Model does NOT expose an MCP Server.

**Rationale:**
- This is the **final output** of the analysis pipeline
- Consumers are the messaging infrastructure and dashboard UI
- No downstream AI agents need to query action plans
- Direct database access or REST API is sufficient

## Message Delivery Separation

**Architecture Decision:** Message delivery is NOT part of Action Plan Model - it's handled by a **Unified Notification Infrastructure Component**.

```
Action Plan Model                 NOTIFICATION INFRASTRUCTURE
┌─────────────────┐               ┌─────────────────────────────────────────┐
│ Generates plans │──────────────▶│           Notification Service          │
│ Stores in DB    │   publish     │                                         │
│                 │   event       │  ┌─────────────────────────────────┐    │
└─────────────────┘               │  │   Unified Channel Abstraction   │    │
                                  │  │                                 │    │
                                  │  │  notify(farmer_id, message)     │    │
                                  │  │  → Reads pref_channel from      │    │
                                  │  │    Plantation Model             │    │
                                  │  │  → Routes to appropriate        │    │
                                  │  │    channel adapter              │    │
                                  │  └─────────────────────────────────┘    │
                                  │                  │                      │
                                  │    ┌─────────────┼─────────────┐        │
                                  │    ▼             ▼             ▼        │
                                  │  ┌─────┐     ┌─────┐     ┌─────┐       │
                                  │  │ SMS │     │Whats│     │Tele │       │
                                  │  │     │     │App  │     │gram │       │
                                  │  └─────┘     └─────┘     └─────┘       │
                                  │    ▼             ▼             ▼        │
                                  │  ┌─────┐     ┌─────┐     ┌─────┐       │
                                  │  │Email│     │Mobile│    │Future│      │
                                  │  │     │     │ App  │    │Channel│     │
                                  │  └─────┘     └─────┘     └─────┘       │
                                  └─────────────────────────────────────────┘
```

## Unified Notification Infrastructure

**Purpose:** Generic infrastructure component providing unified abstraction for farmer communication across all channels.

**Supported Channels:**

| Channel    | Adapter                       | Use Case                   |
|------------|-------------------------------|----------------------------|
| SMS        | Twilio, Africa's Talking      | Basic phones, brief alerts |
| Voice IVR  | Africa's Talking, Twilio      | Detailed explanations for low-literacy farmers |
| WhatsApp   | WhatsApp Business API         | Rich media, farmers with smartphones |
| Telegram   | Telegram Bot API              | Tech-savvy farmers         |
| Email      | SendGrid / SMTP               | Factory managers, reports  |
| Mobile App | Push Notifications (FCM/APNs) | App users                  |

**Unified Interface:**
```typescript
interface NotificationService {
  // Simple: auto-routes based on farmer preference
  notify(farmerId: string, message: NotificationPayload): Promise<DeliveryResult>;

  // Explicit: override channel if needed
  notifyVia(farmerId: string, channel: Channel, message: NotificationPayload): Promise<DeliveryResult>;

  // Bulk: weekly action plan distribution
  notifyBatch(notifications: BatchNotification[]): Promise<BatchResult>;
}

interface NotificationPayload {
  content: string;           // Pre-formatted for channel (from Action Plan)
  priority: 'low' | 'normal' | 'high';
  metadata: {
    source: 'action_plan' | 'alert' | 'info';
    actionPlanId?: string;
    farmerId: string;
  };
}
```

**Channel Selection Logic:**
1. Query Plantation MCP for farmer's `pref_channel`
2. Check channel availability (e.g., WhatsApp requires opt-in)
3. Fallback chain: preferred → SMS → store for later

**Benefits:**
- Action Plan Model focuses on content generation only
- Single abstraction for all notification consumers
- Easy to add new channels without changing producers
- Centralized delivery tracking, retry logic, rate limiting
- Channel-specific formatting handled by adapters

## SMS Cost Optimization Strategy

At scale (800,000 farmers), SMS costs are a critical concern. The platform uses a **tiered SMS strategy** to optimize costs while maintaining effective communication.

### SMS Character Economics

| Character Set | Chars/Segment | Use Case |
|---------------|---------------|----------|
| **GSM-7** (ASCII + basic Latin) | 160 | English, transliterated Swahili |
| **Unicode** (full character set) | 70 | Native scripts, special characters |

**Cost Impact:** A 480-character message costs $0.15 (3 segments GSM-7) vs $0.35 (7 segments Unicode).

### Tiered Message Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SMS TIER STRATEGY                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIER 1: CRITICAL ALERTS (max 160 chars, 1 segment)                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Trigger: Urgent issues (disease outbreak, Grade D)              │   │
│  │  Format: GSM-7 (English + transliterated Swahili keywords)       │   │
│  │  Cost: $0.05/message                                             │   │
│  │                                                                  │   │
│  │  Example:                                                        │   │
│  │  "URGENT: Fungal disease found. Spray copper NOW.                │   │
│  │   Ugonjwa wa kuvu. Reply HELP for details."                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 2: WEEKLY SUMMARY (max 320 chars, 2 segments)                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Trigger: Monday weekly action plan                              │   │
│  │  Format: GSM-7 (transliterated Swahili)                          │   │
│  │  Cost: $0.10/message                                             │   │
│  │                                                                  │   │
│  │  Example:                                                        │   │
│  │  "Habari John! Wiki hii: 1) Nyunyiza dawa ndani ya siku 2        │   │
│  │   2) Vuna baada ya saa 3 asubuhi. Grade B - vizuri!"             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 3: RICH CONTENT (WhatsApp/App - unlimited)                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Trigger: Detailed recommendations, images                       │   │
│  │  Format: Full Unicode, rich media                                │   │
│  │  Cost: ~$0.02/message (WhatsApp Business API)                    │   │
│  │                                                                  │   │
│  │  For farmers with WhatsApp opt-in - full detailed plans          │   │
│  │  with native language and treatment images                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Transliteration Strategy

Most Swahili text is GSM-7 compatible. Transliteration converts the few Unicode characters to ASCII equivalents:

| Native | Transliterated | Meaning | GSM-7 Safe |
|--------|----------------|---------|------------|
| Shamba | Shamba | Farm | ✅ Already safe |
| Ugonjwa | Ugonjwa | Disease | ✅ Already safe |
| Majani ya chai | Majani ya chai | Tea leaves | ✅ Already safe |
| — (em dash) | - | Separator | ✅ Converted |

**Result:** 95%+ of Swahili messages fit in GSM-7 encoding.

### Cost Projection (800,000 farmers)

| Strategy | Avg Segments | Cost/Farmer | Weekly Cost | Annual Cost |
|----------|--------------|-------------|-------------|-------------|
| **Naive (480 Unicode)** | 7 | $0.35 | $280,000 | $14.5M |
| **Tiered SMS** | 2 | $0.10 | $80,000 | $4.2M |
| **+WhatsApp shift (50%)** | 1.5 | $0.06 | $48,000 | $2.5M |

**Projected savings: ~$10-12M annually at scale.**

### Message Generation Configuration

```yaml
# action-plan-model/config/message-tiers.yaml
message_tiers:
  critical_alert:
    max_chars: 160
    encoding: gsm7
    segments: 1
    triggers:
      - severity: critical
      - grade_category: rejection       # Semantic: lowest tier per Grading Model
      - quality_score_below: 0.3        # Alternative: normalized threshold
      - condition_type: disease_outbreak

  weekly_summary:
    max_chars: 320
    encoding: gsm7
    segments: 2
    triggers:
      - schedule: weekly
      - type: action_plan

  rich_content:
    max_chars: null              # Unlimited
    encoding: unicode
    channels: [whatsapp, app]
    triggers:
      - pref_channel: whatsapp
      - include_images: true

transliteration:
  enabled: true
  fallback_encoding: gsm7
  character_map:
    "—": "-"
    "'": "'"
    "…": "..."
```

## Voice IVR System

The Voice IVR (Interactive Voice Response) system enables farmers with basic phones and limited literacy to receive detailed action plan explanations via spoken audio in their local language.

### Voice IVR Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOICE IVR SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SMS HANDOFF                              INBOUND IVR                        │
│  ┌─────────────────────┐                 ┌─────────────────────┐            │
│  │ "Piga *384# kwa     │                 │ Farmer dials        │            │
│  │  maelezo zaidi"     │ ───────────────▶│ *384# or shortcode  │            │
│  └─────────────────────┘                 └──────────┬──────────┘            │
│                                                     │                        │
│                                                     ▼                        │
│                                          ┌─────────────────────┐            │
│                                          │ IVR GATEWAY         │            │
│                                          │ (Africa's Talking)  │            │
│                                          └──────────┬──────────┘            │
│                                                     │                        │
│                                                     ▼                        │
│                                          ┌─────────────────────┐            │
│                                          │ VOICE IVR SERVER    │            │
│                                          │ (Notification Svc)  │            │
│                                          └──────────┬──────────┘            │
│                                                     │                        │
│                           ┌─────────────────────────┼─────────────────────┐  │
│                           ▼                         ▼                     ▼  │
│                  ┌──────────────┐       ┌──────────────────┐   ┌──────────┐ │
│                  │ CALLER ID    │       │ LANGUAGE         │   │ FARMER   │ │
│                  │ LOOKUP       │       │ SELECTION        │   │ CONTEXT  │ │
│                  │ (farmer_id)  │       │ (IVR menu)       │   │ FETCH    │ │
│                  └──────┬───────┘       └────────┬─────────┘   └────┬─────┘ │
│                         │                        │                   │       │
│                         └────────────────────────┼───────────────────┘       │
│                                                  ▼                           │
│                                       ┌─────────────────────┐               │
│                                       │ TTS ENGINE          │               │
│                                       │ (Google Cloud TTS / │               │
│                                       │  Amazon Polly)      │               │
│                                       └──────────┬──────────┘               │
│                                                  │                           │
│                                                  ▼                           │
│                                       ┌─────────────────────┐               │
│                                       │ AUDIO STREAM        │               │
│                                       │ Action plan spoken  │               │
│                                       │ in local language   │               │
│                                       │ (2-3 min max)       │               │
│                                       └─────────────────────┘               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Voice IVR Call Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IVR CALL FLOW                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. GREETING (5 sec)                                                         │
│     "Habari! Karibu Farmer Power. Press 1 for Swahili, 2 for Kikuyu..."     │
│                                                                              │
│  2. LANGUAGE SELECTION                                                       │
│     ┌──────┐  ┌──────┐  ┌──────┐                                            │
│     │ 1    │  │ 2    │  │ 3    │                                            │
│     │ SW   │  │ KI   │  │ LUO  │                                            │
│     └──┬───┘  └──┬───┘  └──┬───┘                                            │
│        └─────────┴─────────┘                                                 │
│                  │                                                           │
│                  ▼                                                           │
│  3. FARMER IDENTIFICATION (auto via caller ID)                               │
│     "Jambo Mama Wanjiku, tunakuwa na mpango wako..."                        │
│                                                                              │
│  4. ACTION PLAN PLAYBACK (2-3 min)                                          │
│     TTS reads full action plan in selected language                         │
│                                                                              │
│  5. OPTIONS MENU                                                             │
│     ┌──────┐  ┌──────┐  ┌──────┐                                            │
│     │ 1    │  │ 2    │  │ 9    │                                            │
│     │REPLAY│  │ HELP │  │ END  │                                            │
│     └──────┘  └──────┘  └──────┘                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### TTS Engine Configuration

```yaml
# notification-service/config/voice-ivr.yaml
voice_ivr:
  enabled: true

  # IVR Provider (handles call routing, DTMF, etc.)
  ivr_provider:
    primary: africa_talking
    fallback: twilio
    shortcode: "*384#"

  # TTS Provider (text-to-speech conversion)
  tts_provider:
    primary: google_cloud_tts
    fallback: amazon_polly

  # Supported languages with voice configurations
  languages:
    swahili:
      code: "sw-KE"
      voice_name: "sw-KE-Standard-A"  # Female voice
      display_name: "Kiswahili"
      dtmf_key: "1"
    kikuyu:
      code: "ki-KE"
      voice_name: "ki-KE-Standard-A"  # Custom trained
      display_name: "Gĩkũyũ"
      dtmf_key: "2"
    luo:
      code: "luo-KE"
      voice_name: "luo-KE-Standard-A"  # Custom trained
      display_name: "Dholuo"
      dtmf_key: "3"

  # Audio settings
  audio:
    speaking_rate: 0.9          # Slightly slower for clarity
    pitch: 0.0                  # Natural pitch
    volume_gain_db: 0.0
    audio_encoding: "MP3"       # Compressed for streaming
    sample_rate_hz: 8000        # Phone quality

  # Call limits
  limits:
    max_duration_seconds: 300   # 5 min max call
    max_tts_chars: 2000         # ~3 min of speech
    max_replays: 3              # Prevent abuse

  # Farmer identification
  caller_id_lookup:
    enabled: true
    cache_ttl_seconds: 3600
    fallback_prompt: "Please enter your farmer ID followed by hash"
```

### SMS → Voice Handoff

The SMS notification includes a Voice IVR prompt for farmers who want detailed explanations:

```yaml
# notification-service/templates/sms-with-voice.yaml
sms_templates:
  action_plan_with_voice:
    swahili: |
      {farmer_name}, chai yako: {quality_score} stars.
      {short_action}.
      Piga *384# kwa maelezo zaidi.
    kikuyu: |
      {farmer_name}, mũtĩ waku: {quality_score} stars.
      {short_action}.
      Ĩta *384# nĩ ũhoro mũingĩ.
    luo: |
      {farmer_name}, yathi mari: {quality_score} stars.
      {short_action}.
      Goch *384# mondo iyud weche momedore.
```

### Action Plan to Voice Script Conversion

The AI Model generates voice-optimized scripts alongside standard action plans:

```python
# ai-model/agents/action_generator.py
class ActionPlanOutput(BaseModel):
    # Standard outputs
    action_plan_markdown: str
    sms_summary: str  # Max 300 chars

    # Voice IVR outputs (NEW)
    voice_script: VoiceScript

class VoiceScript(BaseModel):
    """Voice-optimized action plan for TTS playback."""

    greeting: str              # "Habari Mama Wanjiku..."
    quality_summary: str       # "Chai yako imepata nyota 4..."
    main_actions: list[str]    # Spoken action items (3-5 max)
    closing: str               # "Ukihitaji msaada, wasiliana na..."

    # TTS hints
    pause_after_greeting_ms: int = 500
    pause_between_actions_ms: int = 800

    # Estimated duration
    estimated_duration_seconds: int

    # Language
    language_code: str  # "sw-KE", "ki-KE", "luo-KE"
```

### Voice IVR Cost Model

| Component | Provider | Unit Cost | Monthly Estimate |
|-----------|----------|-----------|------------------|
| TTS API | Google Cloud TTS | $16 per 1M chars | $500-1,000 |
| Voice Minutes | Africa's Talking | $0.02/min (Kenya) | $2,000-3,000 |
| Shortcode Rental | Africa's Talking | $50/month | $50 |
| **Total Voice IVR** | | | **~$3,000-4,000/month** |

*Assumptions: 800K farmers, 20% use Voice IVR monthly, 2.5 min avg call*

## Two-Way Communication

The platform supports **inbound messages** from farmers, enabling them to ask questions, report actions taken, and provide feedback.

### Inbound Message Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TWO-WAY COMMUNICATION                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  OUTBOUND (existing)                    INBOUND (new)                   │
│  ┌─────────────────────┐               ┌─────────────────────┐         │
│  │ Action Plan         │               │ SMS Gateway         │         │
│  │ → Notification      │               │ (Africa's Talking   │         │
│  │ → Farmer            │               │  webhook)           │         │
│  └─────────────────────┘               └──────────┬──────────┘         │
│                                                   │                    │
│                                                   ▼                    │
│                                        ┌─────────────────────┐         │
│                                        │ INBOUND HANDLER     │         │
│                                        │ (Notification Svc)  │         │
│                                        └──────────┬──────────┘         │
│                                                   │                    │
│                                                   ▼                    │
│                                        ┌─────────────────────┐         │
│                                        │ KEYWORD DETECTION   │         │
│                                        │ (fast, no LLM)      │         │
│                                        └──────────┬──────────┘         │
│                           ┌───────────────────────┼───────────────────┐│
│                           ▼                       ▼                   ▼│
│                   ┌─────────────┐       ┌─────────────┐     ┌─────────┐│
│                   │ "HELP"      │       │ "DONE"      │     │ Free    ││
│                   │ "MSAADA"    │       │ "NIMEFANYA" │     │ Text    ││
│                   └──────┬──────┘       └──────┬──────┘     └────┬────┘│
│                          │                     │                 │     │
│                          ▼                     ▼                 ▼     │
│              ┌───────────────────┐ ┌─────────────────┐ ┌─────────────┐│
│              │ Send last action  │ │ Log completion  │ │ AI Triage   ││
│              │ plan details      │ │ Update farmer   │ │ (Haiku)     ││
│              │ (WhatsApp rich)   │ │ performance     │ │             ││
│              └───────────────────┘ └─────────────────┘ └──────┬──────┘│
│                                                               │       │
│                                             ┌─────────────────┴─────┐ │
│                                             │   Route by intent:    │ │
│                                             │   • Question → FAQ    │ │
│                                             │   • Problem → Ticket  │ │
│                                             │   • Feedback → Log    │ │
│                                             └───────────────────────┘ │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Keyword Commands (No LLM)

| Keyword | Language | Action | Response |
|---------|----------|--------|----------|
| `HELP` / `MSAADA` | EN/SW | Resend details | Full WhatsApp message with last action plan |
| `DONE` / `NIMEFANYA` | EN/SW | Mark complete | "Asante! Tumepokea. Reply HELP if problem persists" |
| `STOP` / `ACHA` | EN/SW | Opt out | Unsubscribe from messages |
| `STATUS` / `HALI` | EN/SW | Check status | Current grade trend, pending actions |

### Free Text AI Triage

For messages that don't match keywords, use Haiku for fast intent classification:

```yaml
# notification-service/config/inbound-triage.yaml
inbound_triage:
  keyword_detection:
    enabled: true
    keywords:
      help: ["HELP", "MSAADA", "SAIDIA", "?"]
      done: ["DONE", "NIMEFANYA", "TAYARI", "OK"]
      stop: ["STOP", "ACHA", "SIMAMA"]
      status: ["STATUS", "HALI", "JINSI"]

  free_text:
    enabled: true
    model: "anthropic/claude-3-haiku"
    max_tokens: 100
    temperature: 0.1

    intents:
      - name: clarification_question
        examples: ["what is fungicide?", "dawa hii ni gani?"]
        action: faq_lookup_or_escalate

      - name: problem_report
        examples: ["I did it but still sick", "bado majani yanaugua"]
        action: create_support_ticket

      - name: feedback
        examples: ["it worked!", "vizuri sana"]
        action: log_feedback

      - name: unrelated
        examples: ["hello", "how are you"]
        action: send_menu
```

### Intent Routing

| Intent | Action | Cost |
|--------|--------|------|
| **clarification_question** | Search FAQ, if no match → create support ticket | $0.001 |
| **problem_report** | Create support ticket, notify agronomist | $0.001 |
| **feedback** | Log to farmer record, update outcome tracking | $0.001 |
| **unrelated** | Send menu: "Reply HELP, DONE, or STATUS" | $0.001 |

### Cost Projection

| Message Type | Est. Volume/Week | Cost |
|--------------|------------------|------|
| Keywords (no LLM) | ~50,000 | $0 |
| Free text triage (Haiku) | ~5,000 | ~$5 |
| **Total inbound** | 55,000 | **~$5/week** |

### Inbound Webhook Configuration

```yaml
# notification-service/config/inbound-webhooks.yaml
inbound_webhooks:
  africas_talking:
    endpoint: /api/v1/inbound/sms/at
    auth: hmac_signature
    fields:
      from: "from"
      text: "text"
      date: "date"

  twilio:
    endpoint: /api/v1/inbound/sms/twilio
    auth: signature_validation
    fields:
      from: "From"
      text: "Body"
      date: "DateSent"

  whatsapp:
    endpoint: /api/v1/inbound/whatsapp
    auth: webhook_verification
    supports_media: true
```

## Message Delivery Assurance Strategy

Rural Kenya has significant network gaps (~15% of farmers experience regular connectivity issues). This strategy ensures critical information reaches farmers even in challenging environments.

### Delivery Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE DELIVERY FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Message Generated] ──► [Send Attempt #1]                      │
│                              │                                  │
│                    ┌────────┴────────┐                          │
│                    ▼                 ▼                          │
│              [Delivered]      [Failed/Pending]                  │
│                    │                 │                          │
│                    ▼                 ▼                          │
│              [Log Success]    [Queue for Retry]                 │
│                                      │                          │
│                         ┌────────────┴────────────┐             │
│                         ▼                         ▼             │
│                   [Standard]              [Critical]            │
│                   Retry: 4h, 8h, 24h      Retry: 1h, 2h, 4h,    │
│                   Max: 3 attempts         8h, 24h, 48h          │
│                                           Max: 6 attempts       │
│                                                                 │
│  [All Retries Exhausted] ──► [Escalation Path]                  │
│                              - Flag farmer as "unreachable"     │
│                              - Alert cooperative lead farmer    │
│                              - Queue for next collection visit  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Delivery Configuration

```yaml
# notification-service/config/message-delivery.yaml
message_delivery:
  standard_messages:
    initial_timeout: 60s
    retry_intervals: [4h, 8h, 24h]
    max_attempts: 3
    on_exhausted: log_and_continue

  critical_alerts:
    initial_timeout: 30s
    retry_intervals: [1h, 2h, 4h, 8h, 24h, 48h]
    max_attempts: 6
    on_exhausted: escalate
    parallel_channels: true  # Try SMS + WhatsApp simultaneously

  escalation:
    notify_cooperative_lead: true
    flag_for_field_visit: true
    aggregate_missed_critical: true

delivery_tracking:
  store_delivery_receipts: true
  track_read_receipts: false  # Not reliable for SMS

  statuses:
    - sent
    - delivered
    - failed
    - pending_retry
    - escalated
```

### Multi-Channel Fallback (Critical Alerts Only)

| Attempt | Channel | Timing | Rationale |
|---------|---------|--------|-----------|
| 1 | Primary (SMS or WhatsApp) | Immediate | User preference |
| 2 | Alternate channel | +1 hour | Different network path |
| 3 | Both channels | +4 hours | Maximize reach |
| 4+ | SMS only | +8h, +24h, +48h | SMS more reliable in poor coverage |

### Catch-Up Message for Recovered Farmers

When a farmer becomes reachable again after missing messages:

```yaml
# notification-service/config/catchup-messages.yaml
catchup_message:
  enabled: true
  trigger: first_successful_delivery_after_failure

  template_sw: |
    {FARMER_NAME}, umekosa ujumbe {MISSED_COUNT}.
    MUHIMU ZAIDI: {PRIORITY_SUMMARY}
    Jibu HALI kupata muhtasari kamili.

  template_en: |
    {FARMER_NAME}, you missed {MISSED_COUNT} messages.
    MOST IMPORTANT: {PRIORITY_SUMMARY}
    Reply STATUS for full summary.

  priority_extraction:
    include_critical_alerts: true
    include_action_items: true
    max_items: 3
    max_age_days: 14
```

### Lead Farmer Escalation

For truly unreachable farmers, escalate to cooperative leadership:

```yaml
# notification-service/config/escalation.yaml
lead_farmer_escalation:
  trigger_after_days: 3
  trigger_on_critical: immediate

  message_template_sw: |
    KIONGOZI: Mkulima {FARMER_NAME} hajafikika siku {DAYS}.
    Taarifa muhimu: {ALERT_SUMMARY}
    Tafadhali wasiliana naye.

  tracking:
    log_escalation: true
    request_confirmation: true
    auto_resolve_on_contact: true
```

### Delivery Assurance Cost Impact

| Scenario | Additional Cost | Frequency | Monthly Impact |
|----------|-----------------|-----------|----------------|
| Standard retry (3x) | +2 SMS avg | 5% of messages | ~$4,000 |
| Critical retry (6x) | +5 SMS avg | 0.5% of messages | ~$1,500 |
| Lead farmer escalation | +1 SMS | 0.1% of farmers | ~$200 |
| **Total overhead** | | | **~$5,700/month** |

This represents ~4% overhead on base SMS cost - acceptable for reliability assurance.

## Group Messaging Architecture

The platform supports tiered group messaging to optimize communication costs and leverage cooperative structures common in rural Kenya.

### Messaging Tiers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GROUP MESSAGING TIERS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIER 1: INDIVIDUAL (existing)                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  One farmer → One message                                        │   │
│  │  Personalized action plans, diagnoses                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 2: COOPERATIVE GROUP                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Lead Farmer receives aggregated group message                   │   │
│  │  "5 farmers in your group have fungal issues this week"          │   │
│  │  Includes: member names, summary, shared recommendations         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 3: REGIONAL BROADCAST                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  All farmers in a region receive same alert                      │   │
│  │  Weather warnings, disease outbreak notices                      │   │
│  │  Triggered by: Weather Analyzer, Knowledge Model patterns        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  TIER 4: FACTORY-WIDE ANNOUNCEMENT                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  All farmers delivering to a factory                             │   │
│  │  Policy changes, pricing updates, collection schedule            │   │
│  │  Triggered by: Admin UI (factory manager)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Group Entity (Plantation Model)

```yaml
# Plantation Model: farmer_groups collection
farmer_group:
  group_id: string               # "coop-nyeri-001"
  name: string                   # "Nyeri Highland Cooperative"
  type: enum                     # "cooperative" | "collection_point" | "custom"

  lead_farmer:
    farmer_id: string
    name: string
    phone: string

  members:
    - farmer_id: string
      name: string
      role: enum                 # "member" | "deputy_lead"

  region_id: string
  factory_id: string

  messaging_preferences:
    lead_receives_group_summary: true
    members_receive_individual: true
    broadcast_channel: whatsapp    # WhatsApp groups work better
```

### Broadcast Configuration

```yaml
# notification-service/config/broadcast.yaml
broadcasts:
  regional_alert:
    trigger_sources:
      - event: "knowledge.outbreak_detected"
      - event: "weather.severe_warning"
    audience: region_id
    template_sw: |
      TAHADHARI {REGION_NAME}:
      {ALERT_MESSAGE}
      Ushauri: {RECOMMENDATION}
    channels: [sms, whatsapp]
    throttle:
      max_per_day: 3              # Prevent alert fatigue
      cooldown_minutes: 60

  factory_announcement:
    trigger_sources:
      - manual: admin_ui
    audience: factory_id
    approval_required: true       # Factory manager must approve
    template_sw: |
      TAARIFA: {FACTORY_NAME}
      {ANNOUNCEMENT_BODY}
    channels: [sms]

  cooperative_summary:
    trigger_sources:
      - schedule: "0 7 * * 1"     # Weekly Monday 7 AM
    audience: group_id
    recipient: lead_farmer_only
    template_sw: |
      KIONGOZI - Wiki hii:
      Wakulima {AFFECTED_COUNT} wana matatizo
      Masuala makuu: {TOP_ISSUES}
      Jibu DETAILS kupata orodha kamili.
```

### Lead Farmer Cascade

When a lead farmer receives a group summary, they can request details and confirm relay:

```yaml
# notification-service/config/lead-farmer-cascade.yaml
lead_farmer_cascade:
  summary_message:
    template_sw: |
      {LEAD_NAME}, wiki hii wakulima {COUNT} wana matatizo:
      {BRIEF_LIST}
      Jibu DETAILS kupata orodha kamili.

  details_response:
    trigger: keyword "DETAILS"
    template_sw: |
      ORODHA KAMILI:
      {FULL_LIST_WITH_PHONES_AND_ACTIONS}

  action_tracking:
    lead_confirms_relay: true     # "NIMEWAAMBIA" → log confirmation
    track_member_outcomes: true   # Monitor if issues improve
    confirmation_template_sw: |
      Asante! Tumepokea. Tutafuatilia maendeleo.
```

### Cost Optimization via Grouping

| Scenario | Without Groups | With Groups | Savings |
|----------|----------------|-------------|---------|
| Regional weather alert (10,000 farmers) | 10,000 SMS | 10,000 SMS | 0% (critical info) |
| Cooperative summary (20 farmers/group, 1,000 groups) | 20,000 SMS | 1,000 SMS | **95%** |
| Factory announcement (50,000 farmers) | 50,000 SMS | 50,000 SMS | 0% (critical info) |

**Key insight:** Lead farmer summaries reduce weekly message volume by 95% for non-critical updates while maintaining information flow through cooperative structures.

### Implementation Priority

| Feature | Priority | Rationale |
|---------|----------|-----------|
| Regional broadcasts | MVP | Weather/disease alerts critical for crop protection |
| Lead farmer summaries | MVP | Cost savings, leverages existing cooperative structure |
| Factory announcements | Post-MVP | Less frequent, requires admin UI |
| WhatsApp groups integration | Future | Requires WhatsApp Business API group features |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | PRESCRIBE only | Clean separation from diagnosis |
| **Agent Architecture** | Two-agent (Selector + Generator) | Separation of routing and content generation |
| **Schedule** | Weekly | Matches farmer planning cycles |
| **Output Format** | Dual (detailed + simplified) | Serves both experts and farmers |
| **Translation** | In-agent workflow | LLM naturally handles translation |
| **Multiple Analyses** | Combined into one plan | One coherent weekly recommendation |
| **MCP Server** | No | Final output, no AI agent consumers |
| **Message Delivery** | Infrastructure layer | Separation of concerns |

## Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Selector Agent** | Correct weekly aggregation, no duplicates |
| **Plan Generation** | Quality of recommendations, prioritization |
| **Translation Accuracy** | Language correctness, cultural appropriateness |
| **Simplification** | Readability for farmers, SMS length compliance |
| **Empty State** | Correct handling of no-analysis weeks |
| **Multi-Analysis** | Coherent combination of diverse diagnoses |

---
