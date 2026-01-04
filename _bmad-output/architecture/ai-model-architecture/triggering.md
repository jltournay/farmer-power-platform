# Triggering

**Key Decision:** Triggering is the responsibility of domain models, NOT the AI Model.

Domain models configure triggers that specify when to invoke AI workflows:

```yaml
# In Knowledge Model configuration
triggers:
  - name: poor-quality-analysis
    type: event
    event: "collection.poor_quality_detected"
    workflow: "diagnose-quality-issue"

  - name: daily-weather-analysis
    type: schedule
    cron: "0 6 * * *"
    workflow: "analyze-weather-impact"
    params: { region: "all" }

  - name: weekly-trend-analysis
    type: schedule
    cron: "0 0 * * 0"
    workflow: "analyze-trends"
    params: { scope: "all_farmers" }
```

**Trigger Schema:**

```yaml
trigger:
  name: string              # Unique identifier
  type: event | schedule    # Trigger mechanism

  # If type: event
  event: string             # Event topic to subscribe to

  # If type: schedule
  cron: string              # Cron expression

  workflow: string          # AI Model workflow to invoke
  params: object            # Optional parameters to pass
  enabled: boolean          # Can disable without removing
```

**Infrastructure:**

| Trigger Type | DAPR Component | Agnostic Of |
|--------------|----------------|-------------|
| Event | DAPR Pub/Sub | Message broker (Azure SB, Kafka, Redis...) |
| Schedule | DAPR Jobs | Scheduler backend |
