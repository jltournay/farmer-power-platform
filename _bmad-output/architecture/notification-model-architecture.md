# Notification Model Architecture

## Overview

The Notification Model is the **unified messaging infrastructure** that handles all outbound communication to farmers across multiple channels. It provides channel abstraction, delivery assurance, and cost optimization for rural Kenya's challenging network environment.

**Core Responsibility:** Deliver messages to farmers via their preferred channel (SMS, Voice IVR, WhatsApp, etc.) with delivery assurance.

**Does NOT:** Generate message content (that's Action Plan Model), handle conversational dialogue (that's Conversational AI Model), or store farmer preferences (that's Plantation Model).

## Document Boundaries

| This Document Owns | Other Documents Own |
|-------------------|---------------------|
| Channel adapters (SMS, Voice, WhatsApp) | Message content generation (Action Plan Model) |
| Delivery assurance and retry logic | Two-way conversation (Conversational AI Model) |
| SMS cost optimization | Farmer channel preferences (Plantation Model) |
| Voice IVR playback (one-way) | Voice conversation (Conversational AI Model) |
| Group messaging and broadcasts | — |
| Inbound keyword handling | Free-text AI triage (AI Model) |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NOTIFICATION MODEL                                    │
│                    (7th Domain Model - Messaging Infrastructure)             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PRODUCERS (event-driven)                                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Action Plan     │  │ Knowledge Model │  │ Admin UI        │             │
│  │ Model           │  │ (alerts)        │  │ (broadcasts)    │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    NOTIFICATION SERVICE                                │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │               UNIFIED CHANNEL ABSTRACTION                        │  │ │
│  │  │                                                                  │  │ │
│  │  │  notify(farmer_id, message) → Routes by pref_channel            │  │ │
│  │  │  notifyVia(farmer_id, channel, message) → Explicit channel      │  │ │
│  │  │  notifyBatch(notifications[]) → Bulk delivery                   │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                │                                       │ │
│  │         ┌──────────────────────┼──────────────────────┐               │ │
│  │         ▼                      ▼                      ▼               │ │
│  │  ┌────────────┐         ┌────────────┐         ┌────────────┐        │ │
│  │  │ SMS        │         │ Voice IVR  │         │ WhatsApp   │        │ │
│  │  │ Adapter    │         │ Adapter    │         │ Adapter    │        │ │
│  │  │            │         │            │         │            │        │ │
│  │  │ Africa's   │         │ TTS Engine │         │ Business   │        │ │
│  │  │ Talking    │         │ + IVR      │         │ API        │        │ │
│  │  │ / Twilio   │         │ Gateway    │         │            │        │ │
│  │  └────────────┘         └────────────┘         └────────────┘        │ │
│  │         │                      │                      │               │ │
│  │         └──────────────────────┼──────────────────────┘               │ │
│  │                                ▼                                       │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │               DELIVERY ASSURANCE                                 │  │ │
│  │  │                                                                  │  │ │
│  │  │  • Retry logic (standard: 3x, critical: 6x)                     │  │ │
│  │  │  • Multi-channel fallback                                        │  │ │
│  │  │  • Lead farmer escalation                                        │  │ │
│  │  │  • Catch-up messages for recovered farmers                       │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  INBOUND HANDLING                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Webhooks (Africa's Talking, Twilio, WhatsApp)                        │ │
│  │  → Keyword detection (HELP, DONE, STOP) → Auto-response               │ │
│  │  → Free text → Route to AI Model for triage                           │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  PERSISTENCE: MongoDB (delivery logs, message queue)                         │
│  EXTERNAL: Africa's Talking, Twilio, WhatsApp Business API, Google TTS      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Supported Channels

| Channel    | Adapter                       | Use Case                   | Status |
|------------|-------------------------------|----------------------------|--------|
| SMS        | Africa's Talking, Twilio      | Basic phones, brief alerts | MVP |
| Voice IVR  | Africa's Talking + Google TTS | Detailed explanations for low-literacy farmers | MVP |
| WhatsApp   | WhatsApp Business API         | Rich media, smartphones    | MVP |
| Telegram   | Telegram Bot API              | Tech-savvy farmers         | Future |
| Email      | SendGrid / SMTP               | Factory managers, reports  | Future |
| Mobile App | Push Notifications (FCM/APNs) | App users                  | Future |

## Unified Interface

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

## Channel Selection Logic

1. Query Plantation MCP for farmer's `pref_channel`
2. Check channel availability (e.g., WhatsApp requires opt-in)
3. Fallback chain: preferred → SMS → store for later

---

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
| Shamba | Shamba | Farm | Already safe |
| Ugonjwa | Ugonjwa | Disease | Already safe |
| Majani ya chai | Majani ya chai | Tea leaves | Already safe |
| — (em dash) | - | Separator | Converted |

**Result:** 95%+ of Swahili messages fit in GSM-7 encoding.

### Cost Projection (800,000 farmers)

| Strategy | Avg Segments | Cost/Farmer | Weekly Cost | Annual Cost |
|----------|--------------|-------------|-------------|-------------|
| **Naive (480 Unicode)** | 7 | $0.35 | $280,000 | $14.5M |
| **Tiered SMS** | 2 | $0.10 | $80,000 | $4.2M |
| **+WhatsApp shift (50%)** | 1.5 | $0.06 | $48,000 | $2.5M |

**Projected savings: ~$10-12M annually at scale.**

### Message Tier Configuration

```yaml
# notification-service/config/message-tiers.yaml
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

---

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
      display_name: "Gikuyu"
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

### SMS to Voice Handoff

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
      {farmer_name}, muti waku: {quality_score} stars.
      {short_action}.
      Ita *384# ni uhoro muingi.
    luo: |
      {farmer_name}, yathi mari: {quality_score} stars.
      {short_action}.
      Goch *384# mondo iyud weche momedore.
```

### Voice Script Generation

The AI Model generates voice-optimized scripts alongside standard action plans:

```python
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

---

## Inbound Message Handling

The platform supports **inbound messages** from farmers, enabling them to ask questions, report actions taken, and provide feedback.

### Inbound Message Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INBOUND MESSAGE HANDLING                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SMS Gateway (Africa's Talking webhook)                                 │
│  WhatsApp (Business API webhook)                                        │
│                          │                                              │
│                          ▼                                              │
│               ┌─────────────────────┐                                   │
│               │ INBOUND HANDLER     │                                   │
│               │ (Notification Svc)  │                                   │
│               └──────────┬──────────┘                                   │
│                          │                                              │
│                          ▼                                              │
│               ┌─────────────────────┐                                   │
│               │ KEYWORD DETECTION   │                                   │
│               │ (fast, no LLM)      │                                   │
│               └──────────┬──────────┘                                   │
│          ┌───────────────┼───────────────────┐                          │
│          ▼               ▼                   ▼                          │
│   ┌─────────────┐ ┌─────────────┐     ┌─────────┐                      │
│   │ "HELP"      │ │ "DONE"      │     │ Free    │                      │
│   │ "MSAADA"    │ │ "NIMEFANYA" │     │ Text    │                      │
│   └──────┬──────┘ └──────┬──────┘     └────┬────┘                      │
│          │               │                 │                            │
│          ▼               ▼                 ▼                            │
│   ┌─────────────┐ ┌─────────────┐   ┌─────────────┐                    │
│   │ Send last   │ │ Log done    │   │ Route to    │                    │
│   │ action plan │ │ Update      │   │ AI Model    │                    │
│   │ details     │ │ farmer      │   │ for triage  │                    │
│   └─────────────┘ └─────────────┘   └─────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Keyword Commands (No LLM)

| Keyword | Language | Action | Response |
|---------|----------|--------|----------|
| `HELP` / `MSAADA` | EN/SW | Resend details | Full WhatsApp message with last action plan |
| `DONE` / `NIMEFANYA` | EN/SW | Mark complete | "Asante! Tumepokea. Reply HELP if problem persists" |
| `STOP` / `ACHA` | EN/SW | Opt out | Unsubscribe from messages |
| `STATUS` / `HALI` | EN/SW | Check status | Current grade trend, pending actions |

### Free Text AI Triage

For messages that don't match keywords, route to AI Model for intent classification:

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
    route_to: ai_model  # AI Model handles Haiku-based triage

    intents:
      - name: clarification_question
        action: faq_lookup_or_escalate

      - name: problem_report
        action: create_support_ticket

      - name: feedback
        action: log_feedback

      - name: unrelated
        action: send_menu
```

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

---

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

---

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

---

## No MCP Server

**Decision:** Notification Model does NOT expose an MCP Server.

**Rationale:**
- This is **infrastructure**, not a data model
- No AI agents need to query notification status
- Producers use events (Dapr pub/sub) to trigger notifications
- Direct service invocation for synchronous needs

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Deliver messages only | Clean separation from content generation |
| **Channel Abstraction** | Unified interface | Simplifies producers, enables channel additions |
| **Delivery Assurance** | Retry + escalation | Rural network reliability concerns |
| **SMS Optimization** | GSM-7 + tiered strategy | Cost critical at 800K farmers |
| **Voice IVR** | TTS playback (one-way) | Supports low-literacy farmers |
| **Inbound Handling** | Keywords + AI triage | Balances cost and intelligence |
| **Group Messaging** | Lead farmer cascade | Leverages cooperative structure |
| **MCP Server** | No | Infrastructure, not data model |

---

## Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Channel Adapters** | Each adapter correctly formats and sends |
| **Delivery Retry** | Retry intervals respected, max attempts enforced |
| **Fallback Chain** | Channel fallback triggers correctly |
| **Keyword Detection** | All keyword variants recognized |
| **GSM-7 Encoding** | Transliteration produces valid GSM-7 |
| **Voice IVR Flow** | DTMF navigation, TTS playback |
| **Broadcast Throttling** | Alert fatigue prevention works |
| **Load Testing** | 100K+ messages/hour throughput |

---
