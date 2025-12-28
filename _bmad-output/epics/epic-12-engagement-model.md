# Epic 12: Farmer Engagement & Motivation

Track farmer progress over time with streaks, milestones, and levels. Enable Duolingo-style encouragement patterns that motivate farmers to consistently improve quality.

**Dependencies:** Epic 0 (Infrastructure), Epic 0.75 (AI Model Foundation), Epic 1 (Plantation Model)

**FRs covered:** Derived from UX requirements for farmer motivation (see engagement-model-architecture.md)

**Scope:**
- Engagement state tracking (streaks, levels, milestones)
- Motivation state machine (THRIVING → STEADY → AT_RISK → DECLINING → RECOVERING)
- Celebration trigger events for positive reinforcement
- MCP Server for Action Plan Model to query engagement context
- Category mapping service (Primary % → WIN/WATCH/WORK/WARN)

---

## Stories

### Story 12.1: Engagement Model Service Setup

**Story File:** Not yet created | Status: Backlog

As a **platform operator**,
I want the Engagement Model service deployed with Dapr sidecar and MongoDB connection,
So that farmer engagement state can be tracked and accessed by other services.

**Acceptance Criteria:**

**Given** the Kubernetes cluster is running with Dapr installed
**When** the Engagement Model service is deployed
**Then** the service starts successfully with health check endpoint returning 200
**And** the Dapr sidecar is injected and connected
**And** MongoDB connection is established (engagement_state collection)
**And** gRPC server is listening on port 50051
**And** OpenTelemetry traces are emitted for all operations

**Technical Notes:**
- Python FastAPI + grpcio
- Dapr state store component for MongoDB
- Health endpoint: `/health` and `/ready`
- Environment: farmer-power-{env} namespace
- DAPR pub/sub subscription for plantation.performance_updated

---

### Story 12.2: Streak Calculator

**Story File:** Not yet created | Status: Backlog

As a **farmer**,
I want my consecutive weeks of good quality tracked as streaks,
So that I can see my progress and feel motivated to maintain quality.

**Acceptance Criteria:**

**Given** a `plantation.performance_updated` event is received
**When** the farmer's Primary % maps to WIN category
**Then** `win_streak.current` is incremented by 1
**And** `quality_streak.current` is incremented by 1
**And** `activity_streak.current` is incremented by 1
**And** if new streak > best, `win_streak.best` is updated

**Given** a farmer has a WIN streak of 4
**When** the next week is WATCH category
**Then** `win_streak.current` resets to 0
**And** `quality_streak.current` is incremented (WATCH counts)
**And** `activity_streak.current` is incremented

**Given** a farmer has `streak_freezes.used_this_month < monthly_allowance`
**When** no delivery is recorded for a week
**Then** a streak freeze is automatically applied
**And** all streaks are preserved (not reset)
**And** `streak_freezes.used_this_month` is incremented
**And** farmer receives notification: "Your streak is protected this week"

**Given** it is the first of a new month
**When** the streak calculator initializes
**Then** `streak_freezes.used_this_month` resets to 0

**Streak Types:**
| Streak | Increment Condition |
|--------|---------------------|
| win_streak | Week in WIN category |
| quality_streak | Week in WIN or WATCH category |
| improvement_streak | Better grade than previous week |
| activity_streak | At least 1 delivery this week |
| tip_response_streak | Acknowledged tip with action |

---

### Story 12.3: Level Progression System

**Story File:** Not yet created | Status: Backlog

As a **farmer**,
I want to advance through levels as I maintain quality over time,
So that I feel a sense of long-term progress and achievement.

**Acceptance Criteria:**

**Given** a farmer is at Level 1 (Newcomer)
**When** they have 5+ weeks in the system AND 1+ milestone achieved
**Then** they are promoted to Level 2 (Learner)
**And** an `engagement.level_up` event is emitted
**And** `current_level.progress_to_next` resets to 0

**Given** a farmer is at any level
**When** their engagement state is queried
**Then** `current_level.progress_to_next` shows percentage toward next level
**And** progress is based on weeks active + milestones achieved

**Level Definitions:**
| Level | Name | Requirements |
|-------|------|--------------|
| 1 | Newcomer | 0-4 weeks |
| 2 | Learner | 5-12 weeks, 1 milestone |
| 3 | Practitioner | 13-26 weeks, 3 milestones |
| 4 | Expert | 27-52 weeks, 5 milestones |
| 5 | Master | 52+ weeks, 10 milestones |

---

### Story 12.4: Milestone Detection & Tracking

**Story File:** Not yet created | Status: Backlog

As a **farmer**,
I want to unlock achievements when I reach important quality goals,
So that I feel recognized and motivated to continue improving.

**Acceptance Criteria:**

**Given** a farmer achieves their first WIN category batch
**When** the milestone detector runs
**Then** `milestones.achieved` includes `{id: "first_grade_a", achieved_at: now}`
**And** an `engagement.milestone_achieved` event is emitted
**And** an `engagement.celebration_triggered` event is emitted

**Given** a farmer has a `win_streak.current` of 4 and no prior "4_week_win_streak" milestone
**When** the streak is updated
**Then** the "4 Week Champion" milestone is achieved
**And** `milestones.in_progress` shows next milestone (8 Week Legend at 50%)

**Given** a farmer has a milestone in progress
**When** their engagement state is queried
**Then** the response includes current progress (e.g., "4/8 weeks toward 8 Week Legend")

**Milestones Implemented:**
| ID | Name | Trigger Condition |
|----|------|-------------------|
| first_grade_a | First Grade A! | First-ever WIN category |
| 4_week_win_streak | 4 Week Champion | win_streak >= 4 |
| 8_week_win_streak | 8 Week Legend | win_streak >= 8 |
| quality_improvement_20 | Quality Champion | 20% improvement vs baseline |
| first_month_no_rejection | Perfect Month | 0 rejections in a full month |
| 10_tips_acknowledged | Active Learner | 10 tips acknowledged |
| season_best | Season Best! | Best quality score this season |
| recovery_hero | Recovery Hero | DECLINING → THRIVING in 4 weeks |

---

### Story 12.5: Motivation State Machine

**Story File:** Not yet created | Status: Backlog

As an **action plan generator**,
I want to know a farmer's motivation state,
So that I can adjust messaging tone appropriately.

**Acceptance Criteria:**

**Given** a farmer has 3+ consecutive weeks in WIN category
**When** the state machine evaluates
**Then** `motivation_state.current` is set to "THRIVING"
**And** an `engagement.state_changed` event is emitted if state changed

**Given** a farmer in THRIVING state has 1 week in WATCH
**When** the state machine evaluates
**Then** `motivation_state.current` transitions to "STEADY"

**Given** a farmer has 2+ consecutive weeks in WORK category
**When** the state machine evaluates
**Then** `motivation_state.current` transitions to "DECLINING"
**And** an `engagement.at_risk_detected` event is emitted

**Given** a farmer in DECLINING shows improvement (any better category)
**When** the state machine evaluates
**Then** `motivation_state.current` transitions to "RECOVERING"

**State Transitions:**
```
THRIVING → STEADY (1 week drop to WATCH)
STEADY → AT_RISK (1 week WORK)
AT_RISK → DECLINING (2+ weeks WORK or any WARN)
DECLINING → RECOVERING (any improvement)
RECOVERING → STEADY (2+ weeks WATCH+)
STEADY → THRIVING (3+ weeks WIN)
```

---

### Story 12.6: Category Mapping Service

**Story File:** Not yet created | Status: Backlog

As the **engagement model**,
I want to map raw Primary % to engagement categories using factory thresholds,
So that WIN/WATCH/WORK/WARN vocabulary is owned by Engagement Model, not Plantation.

**Acceptance Criteria:**

**Given** a `plantation.performance_updated` event is received with `primary_percentage: 85.2`
**When** the category service fetches factory thresholds from Plantation MCP
**Then** thresholds are: `{tier_1: 85, tier_2: 70, tier_3: 50}`
**And** category is computed as: 85.2% >= 85% → "WIN"

**Given** factory thresholds are fetched
**When** subsequent events for the same factory arrive
**Then** thresholds are served from cache (no MCP call)
**And** cache expires after 1 hour

**Given** a factory has custom thresholds `{tier_1: 90, tier_2: 80, tier_3: 60}`
**When** a farmer has Primary % of 85%
**Then** category is "WATCH" (not WIN, because tier_1 is 90%)

**Category Mapping:**
| Primary % | Default Threshold | Category |
|-----------|-------------------|----------|
| ≥85% | tier_1 | WIN |
| ≥70% | tier_2 | WATCH |
| ≥50% | tier_3 | WORK |
| <50% | below tier_3 | WARN |

---

### Story 12.7: Engagement Model MCP Server

**Story File:** Not yet created | Status: Backlog

As an **Action Plan Model**,
I want to query farmer engagement context via MCP,
So that I can personalize weekly action plans with appropriate tone and celebrations.

**Acceptance Criteria:**

**Given** the Engagement MCP Server is deployed
**When** Action Plan calls `get_farmer_engagement(farmer_id)`
**Then** the full engagement document is returned (streaks, level, milestones, state)

**Given** a farmer has pending celebrations
**When** Action Plan calls `get_engagement_summary(farmer_id)`
**Then** the response includes: motivation_state, win_streak, pending_celebrations[], next_milestone, message_tone

**Given** a factory manager needs intervention priorities
**When** Admin Dashboard calls `get_at_risk_farmers(factory_id)`
**Then** all farmers in AT_RISK or DECLINING state are returned

**MCP Tools:**
| Tool | Parameters | Returns |
|------|------------|---------|
| `get_farmer_engagement` | farmer_id | Full engagement document |
| `get_engagement_summary` | farmer_id | Compact summary for messaging |
| `get_pending_celebrations` | farmer_id?, limit? | Milestones needing celebration |
| `check_milestone_progress` | farmer_id | In-progress milestones with % |
| `get_farmers_by_state` | state, factory_id? | List of farmer_ids |
| `get_at_risk_farmers` | factory_id? | Farmers in AT_RISK or DECLINING |

**Technical Notes:**
- MCP Server deployed as separate Kubernetes deployment (`mcp-servers/engagement-mcp/`)
- Uses DAPR service invocation to call Engagement Model service
- JSON Schema validation for all tool inputs

---

### Story 12.8: Celebration Event Emission

**Story File:** Not yet created | Status: Backlog

As a **farmer**,
I want to receive immediate celebration messages when I achieve milestones,
So that positive reinforcement happens at the right moment.

**Acceptance Criteria:**

**Given** a milestone is achieved
**When** the milestone detector completes
**Then** an `engagement.celebration_triggered` event is emitted immediately
**And** the event includes: farmer_id, milestone_id, milestone_name, celebration_priority

**Given** a celebration event is emitted with priority "critical"
**When** Notification Model receives the event
**Then** a celebration message is sent within 5 minutes
**And** the message uses the farmer's preferred language and channel

**Given** a farmer achieves multiple milestones in one event
**When** celebrations are triggered
**Then** each milestone gets its own celebration event
**And** events are ordered by celebration_priority (critical > high > medium)

**Celebration Templates:**
| Milestone | Priority | Message Key |
|-----------|----------|-------------|
| first_grade_a | high | milestone_achieved |
| 4_week_win_streak | high | streak_milestone |
| 8_week_win_streak | critical | streak_milestone |
| recovery_hero | critical | recovery_celebration |
| level_up | medium | level_up |

---

## Dependencies

| This Epic Depends On | Reason |
|---------------------|--------|
| Epic 0 | Infrastructure foundation |
| Epic 0.75 (Story 0.75.6) | MCP client patterns |
| Epic 1 | Plantation MCP for farmer context and factory thresholds |
| Story 1.7 | Emits `plantation.performance_updated` event |

| Epics That Depend On This | Reason |
|--------------------------|--------|
| Epic 6 (Action Plans) | Uses Engagement MCP for message personalization |
| Epic 3 (Dashboard) | Shows engagement metrics and at-risk farmers |

---

## Retrospective

**Story File:** Not yet created | Status: Backlog

---

_Last Updated: 2025-12-28_
