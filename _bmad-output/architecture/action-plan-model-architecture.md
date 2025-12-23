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
| Notification trigger (emit event) | N/A (notification is infrastructure, not AI) |

> **Message Delivery:** For SMS, Voice IVR, WhatsApp, and delivery assurance, see [`notification-model-architecture.md`](./notification-model-architecture.md).

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

## Message Delivery

**Architecture Decision:** Message delivery is NOT part of Action Plan Model - it's handled by the **Notification Model**.

```
Action Plan Model                      Notification Model
┌─────────────────┐                   ┌─────────────────────────────┐
│ Generates plans │───publish event──▶│ SMS, Voice IVR, WhatsApp    │
│ Stores in DB    │                   │ Delivery assurance, retry   │
│                 │                   │ Group messaging, broadcasts │
└─────────────────┘                   └─────────────────────────────┘
```

**Separation of Concerns:**
- Action Plan Model: **Content generation** (what to say)
- Notification Model: **Message delivery** (how to reach the farmer)

For details on SMS optimization, Voice IVR, delivery assurance, and group messaging, see [`notification-model-architecture.md`](./notification-model-architecture.md).

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
