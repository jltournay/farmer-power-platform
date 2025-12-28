# Epics & Stories - Redirect Notice

**This file has been replaced by a sharded structure for better maintainability.**

## New Location

All epics and stories are now located in the `epics/` directory:

- **[epics/index.md](epics/index.md)** - Overview, requirements inventory, and epic summaries
- **[epics/epic-0-infrastructure.md](epics/epic-0-infrastructure.md)** - Platform Infrastructure Foundation
- **[epics/epic-0-5-frontend.md](epics/epic-0-5-frontend.md)** - Frontend & Identity Infrastructure
- **[epics/epic-1-plantation-model.md](epics/epic-1-plantation-model.md)** - Farmer Registration & Data Foundation
- **[epics/epic-2-collection-model.md](epics/epic-2-collection-model.md)** - Quality Data Ingestion
- **[epics/epic-3-dashboard.md](epics/epic-3-dashboard.md)** - Factory Manager Dashboard
- **[epics/epic-4-sms-feedback.md](epics/epic-4-sms-feedback.md)** - Farmer SMS Feedback
- **[epics/epic-5-diagnosis-ai.md](epics/epic-5-diagnosis-ai.md)** - Quality Diagnosis AI
- **[epics/epic-6-action-plans.md](epics/epic-6-action-plans.md)** - Weekly Action Plans
- **[epics/epic-7-voice-ivr.md](epics/epic-7-voice-ivr.md)** - Voice IVR Experience
- **[epics/epic-8-voice-advisor.md](epics/epic-8-voice-advisor.md)** - Voice Quality Advisor (Conversational AI)
- **[epics/epic-9-admin-portal.md](epics/epic-9-admin-portal.md)** - Platform Admin Portal
- **[epics/epic-10-regulator.md](epics/epic-10-regulator.md)** - Regulator Dashboard
- **[epics/epic-11-registration-kiosk.md](epics/epic-11-registration-kiosk.md)** - Registration Kiosk PWA

## Why Sharded?

The original `epics.md` was 4,500+ lines and 168KB - too large to maintain effectively. Each epic is now in its own file, making it easier to:

1. Edit individual epics without merge conflicts
2. Review changes in PRs (smaller diffs)
3. Navigate to specific stories quickly
4. Keep each file under 500 lines

## Sprint Status

For current implementation status, see: **[sprint-artifacts/sprint-status.yaml](sprint-artifacts/sprint-status.yaml)**

---

*Sharded on 2025-12-28*
