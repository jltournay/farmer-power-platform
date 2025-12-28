# Epic 7: Voice IVR Experience

Farmers can call a shortcode to hear their action plans read aloud via text-to-speech. This provides an accessible interface for farmers who prefer voice interaction or have difficulty reading.

**Related Requirements:** FR5-FR7

**Scope:**
- Voice IVR service with telephony integration
- Caller ID-based farmer identification
- Multi-language support (Swahili, Kikuyu, Luo, English)
- Action plan TTS playback
- Navigation and help options

---

## Story 7.1: Voice IVR Service Setup

As a **platform operator**,
I want the Voice IVR service deployed with telephony integration,
So that farmers can call and hear their action plans.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running
**When** the Voice IVR service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** Africa's Talking Voice API is configured
**And** shortcode (*384#) is registered and active
**And** OpenTelemetry traces are emitted for all calls

**Given** the service is running
**When** a call is received on the shortcode
**Then** the incoming call webhook is triggered
**And** call session is created with unique call_id
**And** call start time is logged

**Given** Voice IVR needs TTS capability
**When** the service initializes
**Then** Google Cloud TTS is configured
**And** voice models for Swahili, English are loaded
**And** fallback to Africa's Talking TTS is available

**Given** a call is in progress
**When** the call ends (hangup, timeout, error)
**Then** call duration is logged
**And** call outcome is recorded (completed, abandoned, error)
**And** metrics are collected for reporting

**Technical Notes:**
- Python FastAPI with async support
- Africa's Talking Voice API for telephony
- Google Cloud TTS: Swahili (sw-KE), Kikuyu (Wavenet), English (en-KE)
- Shortcode: *384# (USSD-style for Kenya)
- Environment: farmer-power-{env} namespace

---

## Story 7.2: Caller ID Farmer Identification

As a **farmer**,
I want to be automatically identified when I call,
So that I can hear my personalized action plan without entering my ID.

**Acceptance Criteria:**

**Given** a farmer calls the Voice IVR shortcode
**When** the call is received
**Then** the caller's phone number is extracted
**And** Plantation Model is queried: `get_farmer_by_phone(phone)`

**Given** the phone number matches a registered farmer
**When** lookup succeeds
**Then** the farmer's name, pref_lang, and farmer_id are retrieved
**And** a greeting plays: "Jambo {farmer_name}, karibu!"
**And** the call proceeds to language selection

**Given** the phone number is not registered
**When** lookup fails
**Then** a prompt plays: "We don't recognize this number. Please enter your farmer ID."
**And** DTMF input is collected (farmer_id digits)
**And** the entered ID is validated against Plantation Model

**Given** the farmer enters an invalid farmer_id
**When** validation fails
**Then** an error message plays: "That ID was not found. Please try again."
**And** the farmer can retry up to 3 times
**And** after 3 failures, the call offers "Press 0 for help"

**Given** a farmer is identified (by phone or ID)
**When** identification completes
**Then** the farmer_id is stored in call session
**And** all subsequent actions use this farmer context

**Technical Notes:**
- Caller ID: E.164 format (+254...)
- DTMF timeout: 10 seconds
- Farmer ID format: WM-XXXX (4 digits)
- Session storage: Redis with call_id key

---

## Story 7.3: Language Selection Menu

As a **farmer**,
I want to choose my language when calling,
So that I hear the action plan in a language I understand.

**Acceptance Criteria:**

**Given** a farmer is identified
**When** language selection begins
**Then** a menu plays: "For Swahili, press 1. For Kikuyu, press 2. For Luo, press 3. For English, press 4."
**And** each option is read in the respective language

**Given** the farmer's pref_lang is already set
**When** the menu plays
**Then** the farmer's preferred language is suggested: "Press 1 for Swahili (your usual language)"
**And** the preferred option is listed first

**Given** a farmer selects a language option
**When** DTMF input is received
**Then** the selected language is stored in call session
**And** all subsequent audio is in the selected language
**And** "Asante" (or equivalent) confirmation plays

**Given** no input is received within 10 seconds
**When** the timeout occurs
**Then** the menu replays once
**And** if still no input after second play, default to pref_lang
**And** proceed with action plan playback

**Given** an invalid key is pressed
**When** input is received
**Then** "Sorry, that option is not available. Let's try again." plays
**And** the menu replays

**Technical Notes:**
- Languages: sw (Swahili), ki (Kikuyu), luo (Luo), en (English)
- DTMF: 1=sw, 2=ki, 3=luo, 4=en, 0=help
- TTS voices: Google Cloud Wavenet where available
- Kikuyu/Luo: may use pre-recorded audio (TTS limited)

---

## Story 7.4: Action Plan TTS Playback

As a **farmer**,
I want to hear my weekly action plan read aloud,
So that I understand my recommendations without needing to read.

**Acceptance Criteria:**

**Given** language selection is complete
**When** action plan playback begins
**Then** the Action Plan Model MCP is queried: `get_current_action_plan(farmer_id)`
**And** the TTS script version of the plan is retrieved

**Given** an action plan exists
**When** TTS playback starts
**Then** the plan is read with natural pacing: intro, issue 1, recommendation 1, pause, issue 2, etc.
**And** SSML tags control pauses, emphasis, and speed
**And** total duration is 2-3 minutes maximum

**Given** the action plan has multiple recommendations
**When** reading each section
**Then** there is a 1-second pause between sections
**And** "First..." "Second..." "Finally..." transitional phrases are used
**And** the farmer can interrupt at any time (see Story 7.5)

**Given** no action plan exists for this week
**When** the query returns empty
**Then** a friendly message plays: "You have no new recommendations this week. Your last delivery was excellent!"
**And** the option to hear previous week's plan is offered

**Given** playback completes
**When** the plan has been fully read
**Then** "That's your plan for this week. Press 1 to replay, 9 to end call."
**And** the menu allows farmer to choose next action

**Technical Notes:**
- TTS: Google Cloud TTS with SSML
- Max duration: 180 seconds (3 min)
- Speech rate: 0.9x for clarity
- Pauses: <break time="1s"/> between sections

---

## Story 7.5: Navigation and Help Options

As a **farmer**,
I want to control playback and get help during the call,
So that I can replay sections I missed or exit when done.

**Acceptance Criteria:**

**Given** the action plan is playing
**When** the farmer presses 1 during playback
**Then** playback restarts from the beginning
**And** "Repeating from the start..." plays first

**Given** the action plan is playing
**When** the farmer presses 5 during playback
**Then** playback pauses
**And** "Paused. Press 5 to continue." plays
**And** call remains open for up to 30 seconds

**Given** the farmer presses 0 at any time
**When** the input is received
**Then** help menu plays: "For main menu, press star. To replay, press 1. To end call, press 9."
**And** help is in the farmer's selected language

**Given** the farmer presses 9 at any time
**When** the input is received
**Then** "Thank you for calling. Goodbye!" plays
**And** the call is ended gracefully
**And** call duration and outcome are logged

**Given** the farmer is silent for 60 seconds
**When** inactivity timeout occurs
**Then** "Are you still there? Press any key to continue." plays
**And** if no response in 15 seconds, call ends
**And** outcome is logged as "abandoned"

**Given** the call exceeds 5 minutes
**When** the time limit is reached
**Then** "Your call is about to end. Thank you for calling." plays
**And** the call ends after the message

**Technical Notes:**
- DTMF barge-in: enabled during playback
- Key mappings: 1=replay, 5=pause, 0=help, 9=end, *=main menu
- Inactivity timeout: 60 seconds
- Max call duration: 5 minutes
- Graceful hangup with goodbye message
