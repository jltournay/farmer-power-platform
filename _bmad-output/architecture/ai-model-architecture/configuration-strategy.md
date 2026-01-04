# Configuration Strategy

**Hybrid approach - Git for technical config, Admin UI for business data:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONFIGURATION STRATEGY                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GIT (YAML files) - Infrastructure & Technical Config                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • Agent instance definitions                                    │   │
│  │  • Trigger configurations (event mappings, cron schedules)       │   │
│  │  • LLM routing (model per task type)                             │   │
│  │  • DAPR component configs                                        │   │
│  │  • Prompt templates (separate .md files)                         │   │
│  │                                                                  │   │
│  │  Changed by: Developers, Architects                              │   │
│  │  Process: PR → Review → Merge → Deploy                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ADMIN UI + MongoDB - Business & Operational Config                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • RAG knowledge documents (upload interface)                    │   │
│  │  • Farmer/Factory data (Plantation Model)                        │   │
│  │  • Buyer profiles                                                │   │
│  │                                                                  │   │
│  │  Changed by: Operations, Agronomists, Factory managers          │   │
│  │  Process: Login → Edit → Save → Immediate effect                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```
