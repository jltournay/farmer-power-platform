# Voice IVR Experience Design

## Strategic Rationale

**The Accessibility Gap:**

SMS delivers quality scores and brief recommendations, but farmers with limited literacy or basic phones cannot access detailed explanations of how to improve. Voice IVR bridges this gap.

| Channel | Content Depth | Best For |
|---------|---------------|----------|
| **SMS** | 160 chars, brief summary | Quick notification, score delivery |
| **Voice IVR** | 2-3 minutes spoken | Detailed explanations, step-by-step guidance |
| **WhatsApp** | Rich media, unlimited | Farmers with smartphones |

**Target Users:**
- Farmers with basic feature phones (no smartphone required)
- Low-literacy farmers who prefer spoken instructions
- Farmers who want detailed action plan explanations beyond SMS summary

## SMS → Voice Handoff Design (TBK Format)

Every SMS includes a voice IVR prompt for farmers who want more detail:

```
┌─────────────────────────────────────┐
│  📱 SMS Message (TBK Format)        │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  │  Mama Wanjiku, chai yako:   │    │
│  │  ✅ 82% daraja la kwanza!   │    │
│  │  Tatizo: majani 3+          │    │
│  │  Piga *384# kwa maelezo     │    │
│  │                             │    │
│  └─────────────────────────────┘    │
│                                     │
│  Translation:                       │
│  "Mama Wanjiku, your tea:           │
│   ✅ 82% first grade!               │
│   Issue: 3+ leaves plucking         │
│   Call *384# for more details."    │
│                                     │
│  Characters: 112/160 ✓             │
└─────────────────────────────────────┘
```

**Key Design Principles:**
1. **SMS is complete on its own** - Farmer gets Primary %, top leaf type issue
2. **Voice is optional enrichment** - "Piga *384#" is an invitation, not required
3. **One shortcode to remember** - Same number (*384#) for all farmers

---

## IVR Call Flow Design

**Complete Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOICE IVR CALL FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STEP 1: FARMER DIALS *384#                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  System looks up farmer by caller ID                                   │  │
│  │  → Found: Proceed to Step 2                                           │  │
│  │  → Not Found: "Please enter your farmer ID followed by #"             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 2: GREETING (5 seconds)                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Habari! Karibu Farmer Power."                                     │  │
│  │     "Hello! Welcome to Farmer Power."                                 │  │
│  │                                                                        │  │
│  │  🔊 "Bonyeza 1 kwa Kiswahili"                                          │  │
│  │     "Press 1 for Swahili"                                             │  │
│  │  🔊 "Bonyeza 2 kwa Gĩkũyũ"                                              │  │
│  │     "Press 2 for Kikuyu"                                              │  │
│  │  🔊 "Bonyeza 3 kwa Dholuo"                                              │  │
│  │     "Press 3 for Luo"                                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 3: LANGUAGE SELECTION (User presses 1, 2, or 3)                        │
│  ┌──────┐  ┌──────┐  ┌──────┐                                               │
│  │  1   │  │  2   │  │  3   │                                               │
│  │ SW   │  │ KI   │  │ LUO  │                                               │
│  └──┬───┘  └──┬───┘  └──┬───┘                                               │
│     └─────────┴─────────┘                                                    │
│               │                                                              │
│               ▼                                                              │
│  STEP 4: PERSONALIZED GREETING (5 seconds)                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 [Swahili] "Jambo Mama Wanjiku!"                                    │  │
│  │     "Hello Mama Wanjiku!"                                             │  │
│  │                                                                        │  │
│  │  🔊 "Tuna mpango wako wa wiki hii."                                    │  │
│  │     "We have your action plan for this week."                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 5: QUALITY SUMMARY (15 seconds)                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Chai yako wiki hii imepata nyota nne kati ya tano."               │  │
│  │     "Your tea this week received 4 out of 5 stars."                   │  │
│  │                                                                        │  │
│  │  🔊 "Hii ni vizuri! Umepanda kutoka nyota tatu wiki iliyopita."        │  │
│  │     "This is good! You went up from 3 stars last week."               │  │
│  │                                                                        │  │
│  │  🔊 "Tatizo kuu: Unyevu mwingi katika majani yako."                   │  │
│  │     "Main issue: Too much moisture in your leaves."                   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 6: ACTION PLAN (60-90 seconds)                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Hivi ndivyo unavyoweza kuboresha:"                                │  │
│  │     "Here is how you can improve:"                                    │  │
│  │                                                                        │  │
│  │  🔊 "[Pause 0.5s] Moja: Anika majani kwa masaa mawili zaidi           │  │
│  │      kabla ya kupeleka kiwandani."                                    │  │
│  │     "One: Dry your leaves for two more hours before taking            │  │
│  │      them to the factory."                                            │  │
│  │                                                                        │  │
│  │  🔊 "[Pause 0.8s] Mbili: Usivune asubuhi na mapema sana               │  │
│  │      wakati bado kuna umande."                                        │  │
│  │     "Two: Don't harvest too early in the morning when there           │  │
│  │      is still dew."                                                   │  │
│  │                                                                        │  │
│  │  🔊 "[Pause 0.8s] Tatu: Tumia kapu lenye mashimo madogo               │  │
│  │      ili hewa iweze kupita."                                          │  │
│  │     "Three: Use a basket with small holes so air can pass             │  │
│  │      through."                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 7: CLOSING (10 seconds)                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Ukifuata ushauri huu, chai yako itapata nyota tano!"              │  │
│  │     "If you follow this advice, your tea will get 5 stars!"           │  │
│  │                                                                        │  │
│  │  🔊 "Ukihitaji msaada, wasiliana na afisa wa kilimo wako."            │  │
│  │     "If you need help, contact your extension officer."              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  STEP 8: OPTIONS MENU (Repeats until hangup)                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  🔊 "Bonyeza 1 kusikiliza tena. Bonyeza 2 kwa msaada.                  │  │
│  │      Bonyeza 9 kumaliza."                                             │  │
│  │     "Press 1 to listen again. Press 2 for help. Press 9 to end."     │  │
│  │                                                                        │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐                                         │  │
│  │  │  1   │  │  2   │  │  9   │                                         │  │
│  │  │REPLAY│  │ HELP │  │ END  │                                         │  │
│  │  └──────┘  └──────┘  └──────┘                                         │  │
│  │     │          │          │                                            │  │
│  │     ▼          ▼          ▼                                            │  │
│  │  Go to      Transfer    "Asante!                                      │  │
│  │  Step 4     to human    Kwaheri."                                     │  │
│  │             (if avail)  (Goodbye)                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Voice UX Design Principles

| Principle | Implementation                                                                    |
|-----------|-----------------------------------------------------------------------------------|
| **Speak Slowly** | TTS rate set to 0.9x (slightly slower than normal)                                |
| **Use Pauses** | 0.5s pause after greeting, 0.8s between action items                              |
| **Repeat Key Info** | Star rating and main issue mentioned twice                                        |
| **Simple Language** | 6th-grade reading level equivalent                                                |
| **Action-Oriented** | Each step starts with a verb: "Anika..." (Dry...), "Usivune..." (Don't harvest...) |
| **Encouraging Tone** | Celebrate progress: "Umepanda!" (You went up!)                                    |
| **Limited Length** | Max 3 action items per call (cognitive load)                                      |

---

## Multi-Language Voice Templates (TBK Format)

**Quality Summary Template (Primary %):**

| Language | Template |
|----------|----------|
| **Swahili** | "Chai yako wiki hii imepata asilimia {PRIMARY_PCT} ya daraja la kwanza. {TREND_MESSAGE}. Tatizo kuu: {LEAF_TYPE_ISSUE}." |
| **Kikuyu** | "Mũtĩ waku wa wiki ĩno nĩũtũĩkĩire asilimia {PRIMARY_PCT} ya kĩrĩtĩ kĩa mbere. {TREND_MESSAGE}. Thĩna mũnene: {LEAF_TYPE_ISSUE}." |
| **Luo** | "Yathi mari mar jumani oyudo asilimia {PRIMARY_PCT} mar rang'iny mokwongo. {TREND_MESSAGE}. Chandruok maduong: {LEAF_TYPE_ISSUE}." |

**Example Voice Script (TBK Format):**
```
🔊 "Chai yako wiki hii imepata asilimia 82 ya daraja la kwanza."
   "Your tea this week got 82% first grade."

🔊 "Pongezi! Umepanda kutoka asilimia 74 wiki iliyopita!"
   "Congrats! You went up from 74% last week!"

🔊 "Tatizo kuu: Majani mengi na majani matatu au zaidi."
   "Main issue: Too many leaves with 3 or more leaves."

🔊 "Jinsi ya kuboresha: Chuma majani mawili tu na bud."
   "How to improve: Pluck only 2 leaves and a bud."
```

**Trend Messages:**

| Trend | Swahili | English |
|-------|---------|---------|
| **Up** | "Pongezi! Umepanda kutoka asilimia {PREV} wiki iliyopita!" | "Congrats! You went up from {PREV}% last week!" |
| **Same** | "Hii ni sawa na wiki iliyopita." | "This is the same as last week." |
| **Down** | "Hii imeshuka kutoka asilimia {PREV} wiki iliyopita. Usijali, tunaweza kuboresha!" | "This went down from {PREV}% last week. Don't worry, we can improve!" |

**Leaf Type Issue Messages (Swahili):**

| Leaf Type | Swahili Issue | Swahili Action |
|-----------|---------------|----------------|
| `three_plus_leaves_bud` | "Majani mengi (3+)" | "Chuma majani 2 tu na bud" |
| `coarse_leaf` | "Majani magumu" | "Chuma majani laini, machanga" |
| `hard_banji` | "Banji ngumu" | "Pogoa misitu yako kwa afya bora" |

---

## Voice Accessibility Features

| Feature | Design Decision |
|---------|-----------------|
| **No Smartphone Required** | Works on any phone that can dial *384# |
| **Language Selection First** | Farmer chooses their preferred language immediately |
| **Replay Option** | Press 1 to hear the entire message again (max 3 replays) |
| **Human Fallback** | Press 2 connects to extension officer (during working hours) |
| **Caller ID Lookup** | Automatic farmer identification - no need to enter ID |
| **Call Duration** | Max 5 minutes (cost control + attention span) |
| **Phone Quality Audio** | 8kHz sample rate optimized for phone speakers |

---

## Voice IVR Success Metrics

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| **Call Completion Rate** | >80% | Farmers listen to full message |
| **Replay Rate** | 20-40% | Some replay is healthy (absorbing info), too much = confusing |
| **Help Request Rate** | <10% | Most farmers understand without needing human support |
| **Caller ID Match Rate** | >95% | Seamless identification reduces friction |
| **Average Call Duration** | 2-3 min | Sweet spot for comprehension without fatigue |

---

## Dashboard Integration (Joseph's View)

Factory managers see Voice IVR engagement in farmer profiles:

```
┌─────────────────────────────────────────────────────────────────┐
│  FARMER DETAIL: Wanjiku Muthoni (WM-4521)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  COMMUNICATION HISTORY                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Dec 18, 10:32 AM  📱 SMS sent (⭐⭐⭐⭐, moisture issue)      │ │
│  │  Dec 18, 10:45 AM  📞 Voice IVR called (2:34 duration)      │ │
│  │                        ↳ Language: Swahili                  │ │
│  │                        ↳ Replayed: Yes (1x)                 │ │
│  │                        ↳ Help requested: No                 │ │
│  │  Dec 11, 09:15 AM  📱 SMS sent (⭐⭐⭐, leaf age issue)        │ │
│  │  Dec 11, 09:22 AM  📞 Voice IVR called (1:58 duration)      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ENGAGEMENT INSIGHTS                                             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  📊 This farmer regularly uses Voice IVR (4/4 weeks)        │ │
│  │  💡 Prefers Swahili, listens to full messages               │ │
│  │  ✓  Good engagement = likely following recommendations      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Voice UX Validation Plan

| Test | Method | Success Criteria |
|------|--------|------------------|
| **Comprehension** | Play voice message to 10 farmers, ask what actions they should take | 8/10 correctly identify main actions |
| **Language Quality** | Native speaker review of TTS output | "Natural-sounding, not robotic" |
| **Call Flow** | User testing with feature phones | Complete call without confusion |
| **Accessibility** | Test with farmers who can't read SMS | Can take action based on voice alone |

---
