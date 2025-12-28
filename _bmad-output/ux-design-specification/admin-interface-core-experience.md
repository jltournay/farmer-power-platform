# Admin Interface Core Experience

## Factory Admin UI

**Core Purpose:** Enable factory administrators to configure quality-to-payment relationships and customize farmer communication without technical support.

**Primary Workflow:** Payment Policy Configuration
- Select policy type (Split Payment, Weekly Bonus, Delayed Payment, Feedback Only, Reputation)
- Configure quality tier thresholds (Premium/Standard/Acceptable/Below Standard based on Primary %)
- Configure price adjustments per tier
- Preview SMS templates for each tier
- Calculate projected monthly cost impact
- Activate with 7-day farmer notification period

**Key Screens:**

```
┌─────────────────────────────────────────────────────────────────┐
│  FACTORY ADMIN: Kericho Tea                      [Settings ⚙️]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PAYMENT POLICY                    SMS TEMPLATES                │
│  ┌─────────────────────┐          ┌─────────────────────────┐  │
│  │ Current: Weekly     │          │ Premium Message  [Edit] │  │
│  │ Bonus (Policy B)    │          │ Standard Message [Edit] │  │
│  │                     │          │ Acceptable Msg   [Edit] │  │
│  │ [Change Policy →]   │          │ Below Std Msg    [Edit] │  │
│  └─────────────────────┘          │ [Preview All →]         │  │
│                                   └─────────────────────────┘  │
│  QUALITY TIERS & PRICING                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  🟢 Premium        (≥85% Primary):  +15% bonus [Config →]│  │
│  │  🟡 Standard       (≥70% Primary):  Base rate  [Config →]│  │
│  │  🟠 Acceptable     (≥50% Primary):  -5%        [Config →]│  │
│  │  🔴 Below Standard (<50% Primary):  -10%       [Config →]│  │
│  │                                                          │  │
│  │  [💰 Calculate Impact] - Shows projected monthly cost    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ⚠️ Changes take effect after farmer notification period (7d)  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Quality Tiers & Pricing Configuration

**Purpose:** Allow factories to customize quality thresholds and associated payment adjustments based on their quality standards and farmer population.

**Default Thresholds (TBK Industry Standard):**

| Quality Tier | Default Threshold | Typical Use Case |
|--------------|-------------------|------------------|
| Premium | ≥85% Primary | Export-grade quality |
| Standard | ≥70% Primary | Good commercial quality |
| Acceptable | ≥50% Primary | Needs improvement support |
| Below Standard | <50% Primary | Critical intervention needed |

**Configuration Screen:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  QUALITY TIERS & PRICING                                     [Reset ↺]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Configure your quality thresholds and associated payment adjustments   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  QUALITY TIER      │  PRIMARY % THRESHOLD  │  PRICE ADJUSTMENT    │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │  🟢 Premium        │  [≥ 85 %        ▲▼]  │  [+15 %        ▲▼]   │  │
│  │  🟡 Standard       │  [≥ 70 %        ▲▼]  │  [Base rate      ]   │  │
│  │  🟠 Acceptable     │  [≥ 50 %        ▲▼]  │  [-5  %        ▲▼]   │  │
│  │  🔴 Below Standard │  [< 50 %          ]  │  [-10 %        ▲▼]   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ⚠️ "Below Standard" is always below Acceptable threshold (auto-calc)  │
│                                                                         │
│  PREVIEW: Based on last 30 days                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Current              │  With new thresholds                      │  │
│  │  Premium:   245       │  Premium:   [312] (+67 farmers) ▲         │  │
│  │  Standard:  380       │  Standard:  [340] (-40 farmers)           │  │
│  │  Acceptable:210       │  Acceptable:[198] (-12 farmers)           │  │
│  │  Below Std:  65       │  Below Std: [ 50] (-15 farmers) ▲         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  💰 Projected cost impact: +KES 45,000/month (more bonuses paid)        │
│                                                                         │
│  [Cancel]                            [Preview SMS] [Save & Notify ✓]    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Validation Rules:**

| Rule | Constraint | Error Message |
|------|------------|---------------|
| Premium > Standard > Acceptable | Thresholds must be descending | "Premium threshold must be higher than Standard" |
| Minimum gap | At least 10% between tiers | "Tiers need at least 10% gap" |
| Below Standard auto-calculated | Always < Acceptable threshold | (No user input - computed) |
| Range limits | 30% ≤ threshold ≤ 95% | "Threshold must be between 30% and 95%" |

**Use Cases for Custom Thresholds:**

| Factory Type | Premium | Standard | Acceptable | Rationale |
|--------------|---------|----------|------------|-----------|
| **Premium Export** | ≥90% | ≥80% | ≥60% | High standards for export market |
| **Standard (Default)** | ≥85% | ≥70% | ≥50% | TBK industry standard |
| **Developing Region** | ≥75% | ≥60% | ≥40% | Encouraging new farmers |
| **Training Mode** | ≥70% | ≥55% | ≥35% | Maximum encouragement during onboarding |

**Key Design Decisions:**

| Decision | Rationale |
|----------|-----------|
| Thresholds + pricing together | One place for quality economics |
| Live preview of farmer distribution | Understand impact before committing |
| Cost projection | Financial implications visible |
| WARN auto-calculated | Simplify config, prevent gaps |
| Reset to defaults | Safety net for experiments |
| 7-day notification period | Farmers informed before changes apply |

**Key Design Decisions:**
- All changes preview-able before activation
- Impact calculator shows cost/benefit projections
- SMS preview shows exact farmer experience
- Rollback available within notification period

---

## Platform Admin UI

**Core Purpose:** Onboard factories, manage users, and monitor platform health with enterprise-grade oversight.

**Primary Workflow:** Factory Onboarding (4 Steps)
1. Factory Details (name, region, address)
2. Admin User (email, phone, role assignment)
3. QC Integration (API key generation, connection test)
4. Go Live (test event verification, activation)

**Key Screens:**

```
┌─────────────────────────────────────────────────────────────────┐
│  PLATFORM ADMIN                              [+ Add Factory]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FACTORY STATUS                    SYSTEM HEALTH                │
│  ┌─────────────────────┐          ┌─────────────────────┐      │
│  │ 🟢 Active: 47       │          │ API: ✅ Healthy      │      │
│  │ 🟡 Onboarding: 3    │          │ QC Sync: ✅ Normal   │      │
│  │ 🔴 Issues: 2        │          │ SMS: ✅ 99.2% deliv  │      │
│  │                     │          │ Voice: ✅ Operational│      │
│  │ [View All →]        │          │ AI: ✅ <2s latency   │      │
│  └─────────────────────┘          └─────────────────────┘      │
│                                                                 │
│  RECENT ACTIVITY                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  🏭 Nyeri Tea Factory - Onboarding Step 3/4 (pending)    │  │
│  │  👤 Joseph K. added as FactoryManager at Kericho Tea     │  │
│  │  ⚠️ Kisii Factory - QC Analyzer offline 2hrs             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  QUICK ACTIONS                                                  │
│  [+ Add Factory] [+ Add User] [📊 Usage Report] [🔧 Config]    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Factory Onboarding Flow (4 Steps):**

```
Step 1: Factory Details     Step 2: Admin User        Step 3: QC Integration    Step 4: Go Live
┌─────────────────┐        ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ • Factory Name  │   →    │ • Admin Email   │   →   │ • API Key Gen   │   →   │ • Test Event    │
│ • Region        │        │ • Phone         │       │ • Connection    │       │ • Verify Data   │
│ • Address       │        │ • Role: Admin   │       │   Test          │       │ • Activate ✓    │
└─────────────────┘        └─────────────────┘       └─────────────────┘       └─────────────────┘
```

**Key Design Decisions:**
- Status dashboard shows all factories at a glance
- System health visible without drilling down
- One-click user role assignment
- QC Analyzer connection wizard with troubleshooting

---

## Farmer Registration UI

**Core Purpose:** Enable rapid farmer enrollment with immediate ID issuance at collection points or factory offices.

**Primary Workflow:** Farmer Enrollment (<2 minutes)
1. Phone number entry with instant duplicate detection
2. Basic details (name, National ID, preferred name, language)
3. Collection point assignment
4. ID card printing + automatic welcome SMS

**Key Screens:**

```
┌─────────────────────────────────────────────────────────────────┐
│  FARMER REGISTRATION                    Clerk: Peter Ochieng    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📱 PHONE NUMBER                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  +254 │ 712 345 678                      [Verify →]      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ✅ Phone verified - New farmer (not registered)               │
│                                                                 │
│  👤 FARMER DETAILS                                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Full Name:    [Wanjiku Muthoni                      ]   │  │
│  │  National ID:  [12345678                             ]   │  │
│  │  Preferred Name: [Mama Wanjiku    ] (for SMS)            │  │
│  │  Language:     [Swahili ▼]                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  📍 COLLECTION POINT                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  [Kericho Central ▼]                                     │  │
│  │  Distance: ~2km from farmer location                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         [📋 Register & Print ID Card]                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Registration Flow (Target: <2 minutes):**

```
Phone Entry → Duplicate Check → Details Form → Collection Point → Print ID → Welcome SMS
   (10s)          (instant)        (45s)           (15s)          (30s)       (auto)
```

**ID Card Output:**

```
┌─────────────────────────────────────────┐
│  FARMER POWER                           │
│  ═══════════════════════════════════════│
│                                         │
│  Wanjiku Muthoni                        │
│  ID: WM-4521                            │
│                                         │
│  Collection Point: Kericho Central      │
│  Phone: +254 712 345 678                │
│                                         │
│  [QR CODE]                              │
│                                         │
│  Registered: 2025-12-22                 │
└─────────────────────────────────────────┘
```

**Key Design Decisions:**
- Phone-first registration prevents duplicates
- Preferred name (e.g., "Mama Wanjiku") used in all SMS
- ID card printable immediately or collectible later
- Works offline with sync when connected

---

## Admin Experience Principles

| Principle | Application |
|-----------|-------------|
| **Minimal Steps** | Every workflow <4 steps, most <2 minutes |
| **Instant Validation** | Phone duplicates, API connections, email format - validate immediately |
| **Preview Before Commit** | SMS templates, price changes, policy updates - always preview impact |
| **Clear Status** | Traffic light system: 🟢 Active, 🟡 Pending, 🔴 Issue |
| **Undo Window** | Policy changes have 7-day notification period, can be reverted |
| **Role-Appropriate Views** | Factory Admin sees their factory only; Platform Admin sees all |

---
