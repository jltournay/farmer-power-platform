# Engagement Model Architecture

## Overview

The Engagement Model is the **farmer motivation and progress tracking engine** that maintains engagement state, calculates streaks/milestones, and provides personalization context for communications. It implements Duolingo-style encouragement patterns adapted for agricultural context.

**Core Responsibility:** Track farmer progress over time, calculate engagement metrics (streaks, levels, milestones), and provide motivation context for personalized messaging.

**Does NOT:** Diagnose problems (that's Knowledge Model), prescribe actions (that's Action Plan Model), or send messages (that's Notification Model).

## Document Boundaries

| This Document Owns | Other Documents Own |
|-------------------|---------------------|
| Streak calculation and persistence | Message content generation (Action Plan Model) |
| Level/tier progression logic | Message delivery (Notification Model) |
| Milestone detection and tracking | Quality diagnosis (Knowledge Model) |
| Engagement state machine | Quality grading logic (Collection Model) |
| MCP tools for engagement queries | Farmer profile data (Plantation Model) |
| Celebration trigger events | — |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENGAGEMENT MODEL                                     │
│                    (9th Domain Model - Farmer Motivation Engine)            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EVENT CONSUMERS (triggers engagement updates)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  plantation.performance_updated → Update streak, check milestones       ││
│  │    (emitted by Plantation Model in Story 1.7 with summary + trends)     ││
│  │  knowledge.diagnosis_created → Track issue awareness                     ││
│  │  notification.tip_acknowledged → Reward engagement                       ││
│  └──────────────────────────────────────┬──────────────────────────────────┘│
│                                         │                                    │
│                                         ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    ENGAGEMENT SERVICE                                  │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │               STREAK CALCULATOR                                  │  │  │
│  │  │                                                                  │  │  │
│  │  │  • Consecutive weeks in WIN/WATCH category                      │  │  │
│  │  │  • Grade improvement streak (consecutive better grades)         │  │  │
│  │  │  • Activity streak (consecutive weeks with deliveries)          │  │  │
│  │  │  • Streak freeze logic (allow 1 missed week per month)          │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │               LEVEL PROGRESSION                                  │  │  │
│  │  │                                                                  │  │  │
│  │  │  Level 1: Newcomer (0-4 weeks)                                  │  │  │
│  │  │  Level 2: Learner (5-12 weeks, 1 milestone)                     │  │  │
│  │  │  Level 3: Practitioner (13-26 weeks, 3 milestones)              │  │  │
│  │  │  Level 4: Expert (27-52 weeks, 5 milestones)                    │  │  │
│  │  │  Level 5: Master (52+ weeks, 10 milestones)                     │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │               MILESTONE DETECTOR                                 │  │  │
│  │  │                                                                  │  │  │
│  │  │  • First Grade A batch                                          │  │  │
│  │  │  • 4 weeks consecutive WIN category                             │  │  │
│  │  │  • Quality score improved by 20%                                │  │  │
│  │  │  • First month without rejection                                │  │  │
│  │  │  • 10 tips acknowledged                                         │  │  │
│  │  │  • Season best quality achieved                                 │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │               MOTIVATION STATE MACHINE                           │  │  │
│  │  │                                                                  │  │  │
│  │  │  States: THRIVING → STEADY → AT_RISK → DECLINING → RECOVERING   │  │  │
│  │  │                                                                  │  │  │
│  │  │  Transitions based on streak + recent quality + trend           │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                         │                                    │
│                                         ▼                                    │
│  EVENT PRODUCERS (engagement state changes)                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  engagement.streak_updated → Streak count changed                       ││
│  │  engagement.milestone_achieved → New milestone unlocked                 ││
│  │  engagement.level_up → Farmer advanced to new level                     ││
│  │  engagement.state_changed → Motivation state transition                 ││
│  │  engagement.celebration_triggered → Time for encouraging message        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  PERSISTENCE: MongoDB (engagement_state collection)                          │
│  CONSUMERS: Action Plan Model (via MCP), Admin Dashboard (via Query API)    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Engagement Categories (based on Primary %)

The TBK Kenya grading model is **binary** (Primary/Secondary leaves). The platform computes **Primary %** (percentage of primary-grade leaves per batch), then maps this to engagement categories:

| Category | Primary % Threshold | Engagement Meaning | Message Tone |
|----------|---------------------|-------------------|--------------|
| **WIN** | ≥85% | Excellent - celebrate! | "Amazing work!" |
| **WATCH** | 70-84% | Good - encourage growth | "You're doing great, here's how to reach WIN" |
| **WORK** | 50-69% | Needs improvement | "Let's work on this together" |
| **WARN** | <50% | Critical - supportive intervention | "Don't give up, we're here to help" |

**Note:** These thresholds are factory-configurable. The defaults above are based on UX research and TBK industry standards.

### How Primary % is Calculated

From the QC Analyzer grading output:
```
Primary % = (primary_count / total_leaves) × 100

Example: 61 primary leaves out of 102 total = 59.8% → WORK category
```

The QC Analyzer classifies each leaf as Primary or Secondary based on the TBK grading rules (leaf type, coarse subtype, banji hardness).

### TBK Grading → Engagement Category Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TBK GRADING TO ENGAGEMENT FLOW                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  QC ANALYZER (per leaf classification)                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  leaf_type: bud, one_leaf_bud, two_leaves_bud, ... → Primary            ││
│  │  leaf_type: three_plus_leaves_bud, coarse_leaf → Secondary              ││
│  │  leaf_type: banji → Check banji_hardness: soft=Primary, hard=Secondary  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                         │                                    │
│                                         ▼                                    │
│  BATCH AGGREGATION (per tea bag)                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  total: 102 leaves                                                       ││
│  │  primary: 61 leaves                                                      ││
│  │  secondary: 41 leaves                                                    ││
│  │  Primary % = 61/102 = 59.8%                                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                         │                                    │
│                                         ▼                                    │
│  ENGAGEMENT CATEGORY (configurable thresholds)                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  ≥85% Primary → WIN   (green)                                           ││
│  │  70-84%       → WATCH (yellow)                                          ││
│  │  50-69%       → WORK  (orange)                                          ││
│  │  <50%         → WARN  (red)                                             ││
│  │                                                                          ││
│  │  59.8% → WORK category                                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Factory-Configurable Thresholds:** Factories can adjust category thresholds based on their quality standards via the **Quality Categories & Pricing** screen in the Factory Admin UI. See [UX Specification](../ux-design-specification/admin-interface-core-experience.md#quality-categories--pricing-configuration) for the configuration interface.

| Factory Type | WIN | WATCH | WORK | Use Case |
|--------------|-----|-------|------|----------|
| Premium Export | ≥90% | ≥80% | ≥60% | High standards for export market |
| Standard (Default) | ≥85% | ≥70% | ≥50% | TBK industry standard |
| Developing Region | ≥75% | ≥60% | ≥40% | Encouraging new farmers |

### Streak Types

| Streak Type | Definition | Business Value |
|-------------|------------|----------------|
| **WIN Streak** | Consecutive weeks in WIN category | Highest tier achievement |
| **Quality Streak** | Consecutive weeks in WIN or WATCH | Consistent good performer |
| **Improvement Streak** | Consecutive weeks with better grade than previous | Building momentum |
| **Activity Streak** | Consecutive weeks with at least 1 delivery | Consistent engagement |
| **Tip Response Streak** | Consecutive tips acknowledged/actioned | Active learner |

### Streak Freeze (Compassion Logic)

Rural farmers face unpredictable challenges (weather, illness, transport). The system allows:

- **1 streak freeze per month** - missed week doesn't break streak
- **Automatic application** - no action needed from farmer
- **Notification** - "Your streak is protected this week. Keep going!"
- **Weather-triggered extension** - severe weather events grant extra freeze

```yaml
streak_freeze:
  monthly_allowance: 1
  auto_apply: true
  weather_extension:
    enabled: true
    triggers:
      - event_type: severe_weather
        extra_freezes: 1
        duration_days: 7
```

## Data Model

### Engagement State (MongoDB)

```json
{
  "_id": "engagement-farmer-WM-4521",
  "farmer_id": "WM-4521",
  "factory_id": "FAC-001",

  "current_level": {
    "level": 3,
    "name": "Practitioner",
    "since": "2025-10-01T00:00:00Z",
    "progress_to_next": 0.65
  },

  "streaks": {
    "win_streak": {
      "current": 4,
      "best": 7,
      "last_updated": "2025-12-23T00:00:00Z"
    },
    "quality_streak": {
      "current": 8,
      "best": 12,
      "last_updated": "2025-12-23T00:00:00Z"
    },
    "improvement_streak": {
      "current": 2,
      "best": 5,
      "last_updated": "2025-12-23T00:00:00Z"
    },
    "activity_streak": {
      "current": 15,
      "best": 15,
      "last_updated": "2025-12-23T00:00:00Z"
    },
    "tip_response_streak": {
      "current": 3,
      "best": 6,
      "last_updated": "2025-12-20T00:00:00Z"
    }
  },

  "streak_freezes": {
    "used_this_month": 0,
    "monthly_allowance": 1,
    "weather_bonus": 0,
    "last_used": null
  },

  "milestones": {
    "achieved": [
      {
        "id": "first_grade_a",
        "name": "First Grade A!",
        "achieved_at": "2025-09-15T00:00:00Z",
        "celebration_sent": true
      },
      {
        "id": "4_week_win_streak",
        "name": "4 Week Champion",
        "achieved_at": "2025-12-23T00:00:00Z",
        "celebration_sent": false
      }
    ],
    "in_progress": [
      {
        "id": "8_week_win_streak",
        "name": "8 Week Legend",
        "progress": 0.5,
        "target": 8,
        "current": 4
      }
    ],
    "total_count": 5
  },

  "motivation_state": {
    "current": "THRIVING",
    "previous": "STEADY",
    "changed_at": "2025-12-16T00:00:00Z",
    "consecutive_weeks_in_state": 3
  },

  "quality_trend": {
    "last_4_weeks": ["WIN", "WIN", "WIN", "WIN"],
    "trend_direction": "stable_high",
    "average_score": 0.92
  },

  "engagement_score": {
    "current": 87,
    "previous_week": 82,
    "trend": "improving"
  },

  "created_at": "2025-06-01T00:00:00Z",
  "updated_at": "2025-12-23T00:00:00Z"
}
```

### Milestone Definitions

```yaml
# engagement-service/config/milestones.yaml
milestones:
  # Quality achievements
  first_grade_a:
    name: "First Grade A!"
    description: "Your first batch graded at top quality"
    icon: "star"
    trigger:
      event: collection.quality_graded
      condition: grade_category == "WIN" AND is_first_ever == true
    celebration_priority: high

  4_week_win_streak:
    name: "4 Week Champion"
    description: "Four consecutive weeks in WIN category"
    icon: "trophy"
    trigger:
      event: engagement.streak_updated
      condition: win_streak.current >= 4 AND not already_achieved
    celebration_priority: high

  8_week_win_streak:
    name: "8 Week Legend"
    description: "Eight consecutive weeks of excellence"
    icon: "crown"
    trigger:
      event: engagement.streak_updated
      condition: win_streak.current >= 8 AND not already_achieved
    celebration_priority: critical

  quality_improvement_20:
    name: "Quality Champion"
    description: "Improved quality score by 20% over baseline"
    icon: "chart_up"
    trigger:
      event: collection.quality_graded
      condition: improvement_vs_baseline >= 0.20
    celebration_priority: high

  first_month_no_rejection:
    name: "Perfect Month"
    description: "Full month without any rejected batches"
    icon: "check_circle"
    trigger:
      event: internal.month_end_check
      condition: rejections_this_month == 0 AND deliveries_this_month >= 4
    celebration_priority: medium

  # Engagement achievements
  10_tips_acknowledged:
    name: "Active Learner"
    description: "Acknowledged 10 tips with action"
    icon: "book"
    trigger:
      event: notification.tip_acknowledged
      condition: total_tips_acknowledged >= 10
    celebration_priority: medium

  season_best:
    name: "Season Best!"
    description: "Your best quality score this season"
    icon: "sparkle"
    trigger:
      event: collection.quality_graded
      condition: quality_score > season_best_score
    celebration_priority: medium

  recovery_hero:
    name: "Recovery Hero"
    description: "Bounced back from WARN to WIN in 4 weeks"
    icon: "rocket"
    trigger:
      event: engagement.state_changed
      condition: previous_state == "DECLINING" AND current_state == "THRIVING"
    celebration_priority: critical
```

## Motivation State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MOTIVATION STATE MACHINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ┌────────────┐                                            │
│                    │  THRIVING  │◄─────────────────────────────────┐        │
│                    │            │  (3+ weeks WIN, improving trend) │        │
│                    └─────┬──────┘                                   │        │
│                          │                                          │        │
│        (1 week WATCH     │         (2+ weeks WIN streak             │        │
│         or score drop)   │          after any state)                │        │
│                          ▼                                          │        │
│                    ┌────────────┐                                   │        │
│                    │   STEADY   │───────────────────────────────────┘        │
│                    │            │  (Consistent WATCH/WIN mix)                │
│                    └─────┬──────┘                                            │
│                          │                                                   │
│        (1 week WORK      │         (2+ weeks WATCH/WIN)                     │
│         category)        │                   │                               │
│                          ▼                   │                               │
│                    ┌────────────┐            │                               │
│              ┌────►│  AT_RISK   │────────────┘                               │
│              │     │            │  (1-2 weeks in WORK)                       │
│              │     └─────┬──────┘                                            │
│              │           │                                                   │
│              │  (1 week  │  (2+ weeks WORK or                               │
│              │  WATCH+)  │   any WARN)                                       │
│              │           ▼                                                   │
│              │     ┌────────────┐                                            │
│              │     │ DECLINING  │                                            │
│              │     │            │  (Multiple WORK or WARN weeks)             │
│              │     └─────┬──────┘                                            │
│              │           │                                                   │
│              │           │  (Any improvement)                                │
│              │           ▼                                                   │
│              │     ┌────────────┐                                            │
│              └─────│ RECOVERING │                                            │
│                    │            │  (Showing improvement from decline)        │
│                    └────────────┘                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### State Definitions

| State | Criteria | Message Strategy |
|-------|----------|------------------|
| **THRIVING** | 3+ weeks WIN, quality_streak >= 4 | Celebrate, share advanced tips |
| **STEADY** | Mix of WIN/WATCH, no recent decline | Encourage consistency, gentle challenges |
| **AT_RISK** | 1-2 weeks in WORK category | Extra support, simplified tips, check-in |
| **DECLINING** | 2+ weeks WORK or any WARN | Intensive intervention, human escalation |
| **RECOVERING** | Improvement after decline | Heavy encouragement, celebrate small wins |

## Event Integration

### Events Consumed

| Event | Source | Engagement Action |
|-------|--------|-------------------|
| `plantation.performance_updated` | Plantation Model | Update streaks, check milestones, recalculate state (uses full performance history including improvement_trend, grade distributions) |
| `knowledge.diagnosis_created` | Knowledge Model | Track awareness (farmer informed of issues) |
| `notification.tip_acknowledged` | Notification Model | Update tip response streak, engagement score |
| `notification.message_delivered` | Notification Model | Track reachability for engagement health |

**Why Plantation, not Collection?**

The Engagement Model subscribes to `plantation.performance_updated` rather than raw `collection.quality_graded` because:

1. **Historical context required** - Streaks and milestones need the computed `improvement_trend`, not just a single grade event
2. **No duplicate computation** - Plantation already computes performance summaries; Engagement shouldn't recalculate
3. **Clean data flow** - Collection → Plantation (performance) → Engagement (motivation)
4. **Performance summary payload** includes:
   - `primary_percentage` - raw metric for category computation
   - `improvement_trend` for state machine transitions
   - `today.deliveries` for activity streak

**Vocabulary Ownership:**

| Model | Owns | Does NOT own |
|-------|------|--------------|
| **Plantation** | Quality thresholds (tier_1, tier_2, tier_3), Primary % | Category labels |
| **Engagement** | Category vocabulary (WIN/WATCH/WORK/WARN), Streaks | Raw performance data |

**Category Computation Flow:**

```
plantation.performance_updated
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ENGAGEMENT MODEL                                           │
│                                                             │
│  1. Receive event with primary_percentage (e.g., 85.2%)    │
│  2. Fetch factory thresholds via Plantation MCP:            │
│     {tier_1: 85, tier_2: 70, tier_3: 50}                   │
│  3. Map to engagement category:                             │
│     85.2% >= tier_1(85%) → "WIN"                           │
│  4. Update streaks using WIN category                       │
└─────────────────────────────────────────────────────────────┘
```

**Implementation Note:** The `plantation.performance_updated` event is implemented in **Story 1.7** (Quality Grading Event Subscription). When Plantation Model processes `collection.quality_result.received`, it:
1. Updates `FarmerPerformance.today`
2. Emits `plantation.quality.graded` (per-delivery data for Knowledge/Notification)
3. Computes `primary_percentage` and `improvement_trend`
4. Emits `plantation.performance_updated` (raw data - NO category, Engagement computes)

### Events Produced

| Event | Trigger | Consumers |
|-------|---------|-----------|
| `engagement.streak_updated` | Any streak change | Action Plan (messaging), Admin Dashboard |
| `engagement.milestone_achieved` | New milestone unlocked | Action Plan (celebration message), Admin |
| `engagement.level_up` | Level progression | Action Plan (special message), Admin |
| `engagement.state_changed` | Motivation state transition | Action Plan (adjust messaging), Admin |
| `engagement.celebration_triggered` | Time for positive message | Notification Model (immediate send) |
| `engagement.at_risk_detected` | Farmer entering AT_RISK or DECLINING | Action Plan (intervention), Admin alert |

## MCP Server Tools

The Engagement Model exposes an MCP server for Action Plan Model to query farmer engagement context.

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| `get_farmer_engagement` | Get complete engagement state | `farmer_id` | Full engagement document |
| `get_engagement_summary` | Compact summary for messaging | `farmer_id` | Streaks, state, recent milestones |
| `get_pending_celebrations` | Milestones needing celebration | `farmer_id?`, `limit?` | List of achievements to celebrate |
| `check_milestone_progress` | Progress toward next milestones | `farmer_id` | In-progress milestones with % |
| `get_farmers_by_state` | Find farmers in specific state | `state`, `factory_id?` | List of farmer_ids |
| `get_at_risk_farmers` | Farmers needing intervention | `factory_id?` | Farmers in AT_RISK or DECLINING |

### Example MCP Query (Action Plan consuming)

```python
# Action Plan Model querying engagement context before generating weekly plan
engagement = await engagement_mcp.get_engagement_summary(farmer_id="WM-4521")

# Response:
{
    "farmer_id": "WM-4521",
    "motivation_state": "THRIVING",
    "win_streak": 4,
    "quality_streak": 8,
    "current_level": "Practitioner",
    "pending_celebrations": [
        {"id": "4_week_win_streak", "name": "4 Week Champion"}
    ],
    "next_milestone": {"id": "8_week_win_streak", "progress": 0.5},
    "engagement_score": 87,
    "message_tone": "celebratory"
}
```

## Category Mapping Service

**Engagement Model owns the WIN/WATCH/WORK/WARN vocabulary.** This service maps raw `primary_percentage` to engagement categories.

```python
# engagement_model/domain/services/category_service.py

from dataclasses import dataclass


@dataclass
class QualityThresholds:
    """Factory quality thresholds (fetched from Plantation MCP).

    Neutral naming - Plantation doesn't know about engagement vocabulary.
    """
    tier_1: float  # Highest quality tier (e.g., 85%)
    tier_2: float  # Good quality tier (e.g., 70%)
    tier_3: float  # Acceptable quality tier (e.g., 50%)


class CategoryService:
    """Maps raw Primary % to engagement categories.

    WIN/WATCH/WORK/WARN are ENGAGEMENT vocabulary, not Plantation vocabulary.
    """

    def __init__(self, plantation_mcp_client):
        self._plantation_mcp = plantation_mcp_client
        self._threshold_cache: dict[str, QualityThresholds] = {}

    async def get_factory_thresholds(self, factory_id: str) -> QualityThresholds:
        """Fetch factory thresholds from Plantation MCP (with caching)."""
        if factory_id not in self._threshold_cache:
            factory = await self._plantation_mcp.get_factory(factory_id)
            self._threshold_cache[factory_id] = QualityThresholds(
                tier_1=factory.get("quality_thresholds", {}).get("tier_1", 85.0),
                tier_2=factory.get("quality_thresholds", {}).get("tier_2", 70.0),
                tier_3=factory.get("quality_thresholds", {}).get("tier_3", 50.0),
            )
        return self._threshold_cache[factory_id]

    def map_to_category(
        self,
        primary_percentage: float,
        thresholds: QualityThresholds,
    ) -> str:
        """Map Primary % to engagement category.

        Categories (Engagement vocabulary):
        - WIN: Excellent, celebrate!
        - WATCH: Good, encourage growth
        - WORK: Needs improvement
        - WARN: Critical, supportive intervention
        """
        if primary_percentage >= thresholds.tier_1:
            return "WIN"
        elif primary_percentage >= thresholds.tier_2:
            return "WATCH"
        elif primary_percentage >= thresholds.tier_3:
            return "WORK"
        else:
            return "WARN"

    async def get_category_for_event(
        self,
        factory_id: str,
        primary_percentage: float,
    ) -> str:
        """Convenience method for event processing."""
        thresholds = await self.get_factory_thresholds(factory_id)
        return self.map_to_category(primary_percentage, thresholds)
```

**Usage in event handler:**

```python
# When processing plantation.performance_updated event
async def handle_performance_updated(event: dict) -> None:
    factory_id = event["factory_id"]
    primary_pct = event["primary_percentage"]

    # Engagement Model computes category (owns the vocabulary)
    category = await category_service.get_category_for_event(factory_id, primary_pct)

    # Use category for streak updates
    await update_streak(farmer_id, category)  # e.g., "WIN" → increment win_streak
```

## Message Personalization Context

The Engagement Model provides context that Action Plan uses to personalize messaging:

### Tone Selection

| Motivation State | Streak Status | Recommended Tone |
|------------------|---------------|------------------|
| THRIVING | Any | Celebratory, share advanced tips |
| STEADY | Improving | Encouraging, acknowledge progress |
| STEADY | Stable | Friendly, maintain momentum |
| AT_RISK | Any | Supportive, simplified guidance |
| DECLINING | Any | Compassionate, offer help |
| RECOVERING | Any | Highly encouraging, celebrate small wins |

### Celebration Message Templates

```yaml
# engagement-service/config/celebrations.yaml
celebration_templates:
  milestone_achieved:
    swahili: |
      {FARMER_NAME}, HONGERA! 🎉
      {MILESTONE_NAME}!
      Umefanya vizuri sana. Endelea hivyo!
    english: |
      {FARMER_NAME}, CONGRATULATIONS! 🎉
      {MILESTONE_NAME}!
      You're doing amazing. Keep it up!

  streak_milestone:
    swahili: |
      {FARMER_NAME}! Wiki {STREAK_COUNT} mfululizo katika WIN!
      Wewe ni bingwa! 🏆
    english: |
      {FARMER_NAME}! {STREAK_COUNT} weeks in a row in WIN!
      You're a champion! 🏆

  level_up:
    swahili: |
      {FARMER_NAME}, umepanda daraja!
      Sasa wewe ni {LEVEL_NAME}! ⬆️
      Milestones {MILESTONE_COUNT} - vizuri sana!
    english: |
      {FARMER_NAME}, you leveled up!
      You're now a {LEVEL_NAME}! ⬆️
      {MILESTONE_COUNT} milestones - amazing!

  recovery_celebration:
    swahili: |
      {FARMER_NAME}, UMEFANYA!
      Kutoka WORK hadi WIN - wewe ni shujaa! 🚀
      Juhudi yako inalipa.
    english: |
      {FARMER_NAME}, YOU DID IT!
      From WORK to WIN - you're a hero! 🚀
      Your hard work is paying off.
```

## Engagement Score Calculation

A composite score (0-100) reflecting overall farmer engagement health:

```python
def calculate_engagement_score(state: EngagementState) -> int:
    """
    Composite engagement score for dashboards and prioritization.

    Components:
    - Quality component (40%): Based on recent Primary % category
    - Streak component (30%): Longest active streak normalized
    - Activity component (15%): Delivery consistency
    - Responsiveness (15%): Tip acknowledgment rate

    Categories based on Primary % thresholds:
    - WIN: ≥85% Primary
    - WATCH: 70-84% Primary
    - WORK: 50-69% Primary
    - WARN: <50% Primary
    """
    quality_score = {
        "WIN": 100,    # ≥85% Primary
        "WATCH": 75,   # 70-84% Primary
        "WORK": 40,    # 50-69% Primary
        "WARN": 10     # <50% Primary
    }[state.recent_category]

    streak_score = min(100, state.best_active_streak * 10)
    activity_score = min(100, state.activity_streak * 7)
    response_score = state.tip_acknowledgment_rate * 100

    return int(
        quality_score * 0.40 +
        streak_score * 0.30 +
        activity_score * 0.15 +
        response_score * 0.15
    )
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Core Role** | Track progress & motivate | Clean separation from diagnosis/prescription |
| **Streak Unit** | Weekly (not daily) | Matches tea collection cycle |
| **Streak Freeze** | 1 per month + weather bonus | Compassion for rural challenges |
| **Levels** | 5 tiers (Newcomer → Master) | Long-term progression (1+ year journey) |
| **Leaderboards** | NOT included | Farmers aren't competing; avoid demotivation |
| **Points System** | NOT included | Real quality metrics > gamified points |
| **State Machine** | 5 states with transitions | Enables nuanced messaging |
| **MCP Server** | Yes | Action Plan needs engagement context |
| **Celebration Timing** | Immediate on milestone | Positive reinforcement timing matters |

## Anti-Patterns Avoided

| Anti-Pattern | Why Avoided | Our Approach |
|--------------|-------------|--------------|
| **Excessive gamification** | Farming is livelihood, not game | Celebrate progress, not points |
| **Punitive messaging** | Demotivates struggling farmers | Always encouraging, never blaming |
| **Complex point systems** | Confusing, doesn't match reality | Use real quality metrics |
| **Leaderboards** | Creates competition anxiety | Focus on personal progress |
| **Daily streaks** | Doesn't match weekly collection | Weekly-based engagement |
| **Lost streak = restart** | Too harsh for rural context | Freeze system with compassion |

## Testing Strategy

| Test Type | Focus |
|-----------|-------|
| **Streak Calculation** | Correct counting, freeze application |
| **Milestone Detection** | All trigger conditions work correctly |
| **State Machine** | Transitions happen at right thresholds |
| **Event Handling** | All consumed events update state correctly |
| **MCP Tools** | Correct data returned for all queries |
| **Edge Cases** | First delivery, streak breaks, level boundaries |
| **Celebration Timing** | Immediate emission on milestone |

## Integration with Other Models

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENGAGEMENT MODEL INTEGRATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DATA FLOW: Collection → Plantation → Engagement                             │
│  ════════════════════════════════════════════════                            │
│                                                                              │
│  COLLECTION MODEL                                                            │
│  └──► collection.quality_graded ──► Plantation (NOT directly to Engagement) │
│                                                                              │
│  PLANTATION MODEL                                                            │
│  └──► plantation.performance_updated ──► Engagement: Update streaks/state   │
│       (includes: improvement_trend, grade_distribution_30d, today counters) │
│                                                                              │
│  KNOWLEDGE MODEL                                                             │
│  └──► knowledge.diagnosis_created ──► Engagement: Track awareness           │
│                                                                              │
│  NOTIFICATION MODEL                                                          │
│  └──► notification.tip_acknowledged ──► Engagement: Response tracking       │
│  ◄──── engagement.celebration_triggered ──► Notification: Send celebration  │
│                                                                              │
│  ACTION PLAN MODEL                                                           │
│  └──► MCP: get_engagement_summary() ──► Personalize weekly plan             │
│  └──► MCP: get_pending_celebrations() ──► Include milestone messages        │
│                                                                              │
│  ADMIN DASHBOARD                                                             │
│  └──► Query API: get_at_risk_farmers() ──► Intervention prioritization      │
│  └──► Query API: get_factory_engagement() ──► Factory-level metrics         │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Future Considerations

### Phase 2 Enhancements (Post-MVP)

- **Cooperative group engagement** - Track group-level progress, group milestones
- **Seasonal challenges** - Factory-wide goals during peak seasons
- **Mentor matching** - Connect struggling farmers with local experts
- **Family notifications** - Share achievements with farmer's family (opt-in)
- **Voice celebrations** - IVR milestone announcements in local language

### Metrics to Track

| Metric | Purpose | Target |
|--------|---------|--------|
| Milestone achievement rate | Engagement effectiveness | >60% farmers achieve 1+ milestone/quarter |
| Streak maintenance rate | System stickiness | >40% maintain 4+ week streaks |
| Recovery rate | Intervention effectiveness | >50% of DECLINING farmers reach RECOVERING |
| Celebration delivery rate | Message system health | >95% delivered within 1 hour |

---

*Document created collaboratively by the BMAD team in Party Mode session, 2025-12-28*
