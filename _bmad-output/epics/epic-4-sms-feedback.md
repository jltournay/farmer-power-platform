# Epic 4: Farmer SMS Feedback

## Overview

This epic implements the SMS communication system for farmers, enabling automated quality feedback notifications, cost-optimized messaging, delivery assurance with retry logic, lead farmer escalation for unreachable farmers, inbound keyword handling for farmer responses, and group/regional messaging capabilities.

## Scope

- Notification Model service setup with SMS gateway integration
- SMS message generation with multilingual support
- SMS cost optimization to meet per-farmer cost targets
- SMS delivery assurance with retry logic
- Lead farmer escalation for unreachable farmers
- Inbound keyword handling for farmer responses
- Group and regional messaging for factory managers

---

## Stories

### Story 4.1: Notification Model Service Setup

As a **platform operator**,
I want the Notification Model service deployed with SMS gateway integration,
So that farmers can receive SMS notifications about their quality results.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Notification Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** MongoDB connection is established for delivery tracking
**And** gRPC server is listening on port 50053
**And** OpenTelemetry traces are emitted for all operations

**Given** the service is running
**When** the Africa's Talking SMS gateway is configured
**Then** API credentials are loaded from Azure Key Vault
**And** the gateway connection is verified via test message
**And** shortcode is configured (e.g., 22384)

**Given** the service is running
**When** subscribed to Dapr pub/sub topics
**Then** "plantation.farmer.registered" events trigger welcome SMS (Story 4.8)
**And** "collection.end_bag.received" events trigger SMS generation
**And** "action_plan.generated" events trigger weekly SMS delivery

**Given** the service receives a send request
**When** processing begins
**Then** farmer preferences are fetched from Plantation Model
**And** message is translated to farmer's pref_lang
**And** delivery attempt is logged with timestamp

**Technical Notes:**
- Python FastAPI + grpcio
- Africa's Talking SDK for Kenya SMS
- Azure Key Vault for API credentials
- Environment: farmer-power-{env} namespace

---

### Story 4.2: SMS Message Generation

As a **farmer**,
I want to receive SMS feedback in my local language with my quality results,
So that I understand how my tea performed and what to improve.

**Acceptance Criteria:**

**Given** a quality event is processed for a farmer
**When** SMS generation is triggered (within 3 hours)
**Then** an SMS is generated with: farmer_name, grade (star rating), primary_percentage, ONE actionable tip

**Given** the farmer's pref_lang is "sw" (Swahili)
**When** the SMS is generated
**Then** the message is in Swahili
**And** the message uses culturally appropriate phrasing

**Given** the farmer's pref_lang is "ki" (Kikuyu) or "luo" (Luo)
**When** the SMS is generated
**Then** the message is in the respective language
**And** translation quality is verified against approved templates

**Given** the SMS must show price impact
**When** the grade affects payment
**Then** the message includes: "This grade means KES {amount} per kg" or similar
**And** the amount is calculated based on factory price tiers

**Given** the farmer has an improving trajectory (last 3 deliveries trending up)
**When** the SMS is generated
**Then** a personalized encouragement is included: "{name}, you're improving!"

**Given** the SMS content exceeds 160 characters
**When** using GSM-7 encoding
**Then** the message is trimmed to fit single SMS (160 chars)
**And** the actionable tip is prioritized over additional context

**Given** the SMS contains non-GSM-7 characters
**When** encoding is checked
**Then** the message falls back to UCS-2 encoding (70 chars)
**And** content is further condensed to fit

**Technical Notes:**
- Message templates stored in MongoDB (versioned)
- Translation via pre-approved templates (not real-time LLM)
- GSM-7 character validation before send
- Star rating: Grade 1 = 3 stars, Grade 2 = 2 stars, Grade 3 = 1 star

---

### Story 4.3: SMS Cost Optimization

As a **platform operator**,
I want SMS costs minimized while maintaining message effectiveness,
So that per-farmer costs stay under $0.50/year target.

**Acceptance Criteria:**

**Given** an SMS is being composed
**When** the message fits in 160 GSM-7 characters
**Then** it is sent as a single SMS (1 segment)
**And** the cost is 1 SMS credit

**Given** an SMS is being composed
**When** the message requires 161-320 GSM-7 characters
**Then** a warning is logged for review
**And** the system attempts to condense the message
**And** if condensing fails, it sends as 2-segment SMS

**Given** the farmer has no quality issues (Grade 1)
**When** deciding whether to send SMS
**Then** the SMS is sent with celebration message (shorter)
**And** premium farmers may opt out of "good news" SMS

**Given** a batch of SMS needs to be sent (e.g., 1000 farmers)
**When** the batch is processed
**Then** messages are queued and rate-limited (10 SMS/second)
**And** gateway rate limits are respected
**And** total batch cost is logged for monitoring

**Given** SMS cost metrics are collected
**When** viewing the admin dashboard
**Then** cost per factory, cost per farmer, SMS segment distribution are visible
**And** alerts trigger if cost exceeds $0.50/farmer/year

**Technical Notes:**
- Africa's Talking pricing: ~KES 0.8/SMS (~$0.006)
- Target: <100 SMS/farmer/year = $0.60/year
- Batch processing via Azure Service Bus
- Cost tracking in MongoDB: sms_costs collection

---

### Story 4.4: SMS Delivery Assurance

As a **platform operator**,
I want SMS delivery tracked with retry logic,
So that critical messages reach farmers reliably.

**Acceptance Criteria:**

**Given** an SMS is sent to a farmer
**When** the gateway returns delivery status
**Then** the status is stored: sent, delivered, failed, pending
**And** the delivery_report webhook updates the status

**Given** an SMS fails to deliver (network error)
**When** retry logic is triggered
**Then** the message is retried up to 3 times for standard messages
**And** retry intervals: 5 min, 30 min, 2 hours
**And** each retry attempt is logged

**Given** an SMS is marked as "critical" (e.g., Grade 3 urgent issue)
**When** delivery fails
**Then** the message is retried up to 6 times
**And** retry intervals: 5 min, 15 min, 1 hour, 4 hours, 12 hours, 24 hours

**Given** all retry attempts fail
**When** the message is exhausted
**Then** the status is set to "undeliverable"
**And** lead farmer escalation is triggered (see Story 4.5)
**And** an alert is logged for factory manager visibility

**Given** the farmer's phone is turned off
**When** the gateway reports "phone unreachable"
**Then** the system waits and retries during typical active hours (6 AM - 8 PM local)

**Given** delivery tracking data exists
**When** querying farmer SMS history
**Then** all attempts, statuses, and timestamps are returned
**And** delivery rate metrics are aggregated for reporting

**Technical Notes:**
- Africa's Talking delivery reports via webhook
- Retry queue: Azure Service Bus with delay scheduling
- Delivery status: sent -> pending -> delivered | failed | undeliverable
- Critical flag set by Grade 3 or declining streak

---

### Story 4.5: Lead Farmer Escalation

As a **factory quality manager**,
I want unreachable farmers escalated to lead farmers,
So that critical quality messages still reach the farmer through community networks.

**Acceptance Criteria:**

**Given** a farmer cannot be reached after all retry attempts
**When** escalation is triggered
**Then** the system identifies the farmer's lead farmer (from Plantation Model)
**And** an SMS is sent to the lead farmer

**Given** a lead farmer receives an escalation SMS
**When** the message is composed
**Then** it includes: target farmer name, collection point, brief issue summary, request to relay message
**And** the message respects the lead farmer's language preference

**Given** a lead farmer is assigned to multiple farmers
**When** multiple escalations occur within 1 hour
**Then** messages are aggregated: "3 farmers in your group need attention: {names}"
**And** a single SMS is sent with combined information

**Given** the lead farmer is also unreachable
**When** all escalation attempts fail
**Then** the issue is flagged for factory manager review
**And** appears in the dashboard "Unreachable Farmers" section

**Given** the target farmer is eventually reached (phone back on)
**When** they receive the original message
**Then** the escalation is marked as resolved
**And** the lead farmer receives optional confirmation: "{farmer_name} received their message"

**Technical Notes:**
- Lead farmer relationship in Plantation Model
- Aggregation window: 1 hour
- Lead farmer SMS priority: standard (3 retries)
- Dashboard flag in Collection Model events

---

### Story 4.6: Inbound Keyword Handling

As a **farmer**,
I want to reply to SMS with keywords to get help or update my status,
So that I can interact with the system even without data/internet.

**Acceptance Criteria:**

**Given** a farmer replies with "HELP" (or "MSAADA" in Swahili)
**When** the message is received
**Then** an auto-reply is sent: brief help menu with available keywords
**And** the message is in the farmer's preferred language

**Given** a farmer replies with "DONE" (or "IMEFANYIKA")
**When** the message is received
**Then** the current week's action plan is marked as acknowledged
**And** a confirmation reply is sent: "Great! We'll check your next delivery."

**Given** a farmer replies with "STOP" (or "SIMAMA")
**When** the message is received
**Then** the farmer is opted out of non-critical SMS
**And** only Grade 3 critical alerts are still sent
**And** a confirmation reply is sent with opt-back-in instructions

**Given** a farmer replies with "STATUS" (or "HALI")
**When** the message is received
**Then** a reply is sent with: current grade, last delivery date, trend
**And** the message fits in a single SMS

**Given** a farmer replies with an unrecognized keyword
**When** the message is received
**Then** an auto-reply is sent: "We didn't understand. Reply HELP for options."
**And** the unknown message is logged for review (potential new keyword discovery)

**Given** inbound messages are received
**When** processing
**Then** farmer is identified by phone number (lookup in Plantation Model)
**And** message is logged with timestamp and response

**Technical Notes:**
- Africa's Talking inbound webhook
- Keyword matching: case-insensitive, language-aware aliases
- Farmer lookup: phone -> farmer_id
- Logging: inbound_messages collection

---

### Story 4.7: Group and Regional Messaging

As a **factory quality manager**,
I want to send SMS to groups of farmers or entire regions,
So that I can communicate important announcements efficiently.

**Acceptance Criteria:**

**Given** I am a factory manager in the dashboard
**When** I compose a regional broadcast message
**Then** I can select: all farmers, specific collection points, specific grades, or custom filter
**And** the recipient count is shown before sending

**Given** I compose a broadcast message
**When** I enter the message text
**Then** the SMSPreview component shows character count and segment count
**And** translations are previewed for each language (Swahili, Kikuyu, Luo, English)

**Given** I send a broadcast to 1000+ farmers
**When** the send is triggered
**Then** messages are queued in batches (100 per batch)
**And** progress is shown: "Sending... 450/1000"
**And** rate limiting is enforced (10 SMS/second)

**Given** a broadcast is sent
**When** delivery completes
**Then** a summary report is generated: sent count, delivered count, failed count, cost
**And** the report is available in the Reports section

**Given** a broadcast message is scheduled (not immediate)
**When** the scheduled time arrives
**Then** the broadcast is sent automatically
**And** the factory manager receives confirmation notification

**Given** a broadcast is in progress
**When** the factory manager clicks "Cancel"
**Then** remaining unsent messages are cancelled
**And** already-sent messages remain (cannot be recalled)
**And** a partial delivery report is generated

**Technical Notes:**
- Broadcast queue: Azure Service Bus with priority
- Scheduling: Dapr Jobs component
- Rate limit: configurable per factory
- Cost estimate shown before send: "~KES {amount}"

---

### Story 4.8: Welcome SMS on Farmer Registration

As a **newly registered farmer**,
I want to receive a welcome SMS immediately after registration,
So that I know my registration was successful and understand what to expect.

**Acceptance Criteria:**

**Given** a farmer is registered in Plantation Model
**When** the "plantation.farmer.registered" event is published
**Then** the Notification Model receives the event via DAPR subscription
**And** a welcome SMS is triggered within 30 seconds

**Given** the welcome SMS is being composed
**When** the farmer's preferences are fetched
**Then** the message is translated to the farmer's pref_lang
**And** the message includes: farmer_name, factory_name, collection_point_name

**Given** the welcome SMS content
**When** composed in any language
**Then** it includes:
  - Greeting with farmer's name
  - Confirmation of registration
  - Brief explanation of the service (quality feedback, weekly tips)
  - Voice IVR number for assistance

**Given** the welcome SMS
**When** sent successfully
**Then** the delivery is logged with farmer_id and timestamp
**And** the event is marked as processed (idempotency)

**Given** the "plantation.farmer.registered" event is received again (duplicate)
**When** the farmer already received a welcome SMS
**Then** no duplicate SMS is sent
**And** the duplicate event is logged but ignored

**Technical Notes:**
- Subscribe to topic: "farmer-events" (event_type: "plantation.farmer.registered")
- Idempotency key: farmer_id + event_type
- Template: welcome_sms_{lang}.txt (Swahili, Kikuyu, Luo, English)
- Single SMS (160 chars max) - condensed message
