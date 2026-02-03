# Farmer Power Platform

[![CI](https://github.com/jltournay/farmer-power-platform/actions/workflows/ci.yaml/badge.svg)](https://github.com/jltournay/farmer-power-platform/actions/workflows/ci.yaml)
![Backend Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/jltournay/9b8394c5dcef6340897ac07f62df408d/raw/coverage.json)
![Frontend Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/jltournay/9b8394c5dcef6340897ac07f62df408d/raw/frontend-coverage.json)

**AI-powered crop quality intelligence platform for African agriculture**

The Farmer Power Platform is a cloud-based system that collects and analyzes crop quality data, generates actionable insights, and delivers personalized recommendations to farmers. Built for the Kenyan tea industry with scalability to coffee, grapes, and other crops.

---

## Overview

FarmerPower.ai transforms how agricultural processors manage quality, accountability, and market intelligence. The platform connects real-time quality grading at factory intake with data-driven insights delivered directly to farmers via SMS and Voice IVR.

**Key Capabilities:**

- Real-time quality data ingestion from IoT analyzers
- AI-powered root cause analysis (disease, weather, technique)
- Personalized action plans for quality improvement
- Multi-language delivery (SMS, Voice IVR) for low-literacy farmers
- Market intelligence and buyer preference matching

> **Note:** This repository contains only the cloud platform component. For the complete solution, see also:
> - [Farmer Power QC Analyzer](https://github.com/farmerpower-ai/farmer-power-qc-analyzer) - Industrial IoT quality assessment hardware
> - [Farmer Power Training](https://github.com/farmerpower-ai/farmer-power-training) - Computer vision model training

---

## Architecture

The platform is built on nine interconnected domain models, each deployed as an independent microservice communicating via DAPR.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SYSTEMS                                   │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │ QC Analyzer  │  │ Weather API │  │ Starfish Network│  │ Africa's Talking │   │
│  └──────┬───────┘  └──────┬──────┘  └────────┬────────┘  └────────▲─────────┘   │
└─────────┼─────────────────┼──────────────────┼─────────────────────┼────────────┘
          │                 │                  │                     │
          ▼                 ▼                  │                     │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FARMER POWER PLATFORM                                 │
│                                                                                 │
│  ┌───────────────────┐      ┌───────────────────┐      ┌──────────────────┐    │
│  │  Collection Model │─────▶│     AI Model      │◀────▶│ Plantation Model │    │
│  │  (Data Ingestion) │      │ (LLM Orchestration)│      │  (Digital Twin)  │    │
│  └───────────────────┘      └─────────┬─────────┘      └──────────────────┘    │
│                                       │                         ▲              │
│                          ┌────────────┼────────────┐            │              │
│                          ▼            ▼            ▼            │              │
│  ┌───────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │  Knowledge Model  │  │ Action Plan Model│  │   Market Analysis Model    │───┘
│  │    (Diagnosis)    │  │(Recommendations) │  │   (Buyer Intelligence)     │    │
│  └─────────┬─────────┘  └────────┬────────┘  └─────────────────────────────┘   │
│            │                     │                                              │
│            └──────────┬──────────┘                                              │
│                       ▼                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                        Notification Model                                  │ │
│  │                     (SMS / Voice IVR Delivery)                            │──┘
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                       ▲                                                         │
│                       │                                                         │
│  ┌────────────────────┴──────────────────┐    ┌────────────────────────────┐   │
│  │     Conversational AI Model           │    │    Platform Cost Model     │   │
│  │    (Two-way Farmer Dialogue)          │    │   (Usage & Billing)        │   │
│  └───────────────────────────────────────┘    └────────────────────────────┘   │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                              BFF API                                       │ │
│  │                        (REST / WebSocket)                                  │ │
│  └─────────────────────────────────┬─────────────────────────────────────────┘ │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Factory Dashboard│      │   Admin Portal   │      │Regulatory Dashboard│
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

### Domain Models

| Model | Responsibility |
|-------|----------------|
| **Collection Model** | Ingests quality data, weather, and IoT sensor readings. Validates and stores documents with metadata linking to farms and factories. |
| **Plantation Model** | Digital twin of farms and factories. Tracks farmer history, performance metrics, grading configurations, and regional data. |
| **Knowledge Model** | Diagnoses quality issues using AI analysis. Identifies root causes: disease, weather correlation, harvesting technique, or handling problems. |
| **Action Plan Model** | Generates personalized recommendations based on diagnosis and farm history. Outputs in triple format: detailed report, SMS summary, voice script. |
| **AI Model** | Orchestrates LLM-powered agents via LangGraph. Provides extraction, triage, analysis, and generation capabilities to other models. |
| **Market Analysis Model** | Analyzes buyer behavior and auction data to create Market Preference Profiles and enable intelligent lot allocation. |
| **Notification Model** | Delivers messages via SMS and Voice IVR through Africa's Talking. Supports Swahili, Kikuyu, and Luo languages. |
| **Conversational AI Model** | Handles two-way dialogue with farmers via voice chatbot |
| **Platform Cost Model** | Tracks usage, costs, and billing across the platform. Monitors LLM token consumption, API calls, and resource utilization. |

---

## Repository Structure

```
farmer-power-platform/
├── services/                    # Microservices I
│   ├── collection-model/        # Data ingestion service
│   ├── plantation-model/        # Farm/factory digital twin
│   ├── knowledge-model/         # AI diagnosis engine
│   ├── action-plan-model/       # Recommendation generator
│   ├── ai-model/                # LLM agent orchestration
│   ├── market-analysis-model/   # Market intelligence
│   ├── notification-model/      # SMS/Voice delivery
│   ├── conversational-ai/       # Two-way dialogue handling
│   ├── platform-cost/           # Cost tracking and billing
│   └── bff/                     # Backend for Frontend (REST/WebSocket)
│
├── mcp-servers/                 # Model Context Protocol servers
│   ├── collection-mcp/          # Collection data access
│   └── plantation-mcp/          # Plantation data access
│
├── proto/                       # Protocol Buffer definitions
│   ├── collection/v1/           # Collection service contracts
│   ├── plantation/v1/           # Plantation service contracts
│   ├── common/v1/               # Shared message types
│   └── ...
│
├── libs/                        # Shared Python libraries
│   ├── fp-common/               # Config, tracing, DAPR utilities
│   ├── fp-proto/                # Generated protobuf stubs
│   ├── fp-testing/              # Test fixtures and utilities
│   ├── ui-components/           # React component library
│   └── auth/                    # Authentication utilities
│
├── web/                         # Frontend applications
│   ├── factory-portal/          # Factory manager dashboard (React)
│   └── platform-admin/          # Platform administration portal (React)
│
├── deploy/                      # Deployment configurations
│   ├── kubernetes/              # K8s manifests (Kustomize)
│   └── docker/                  # Docker Compose for local dev
│
├── tests/                       # Cross-service tests
│   ├── unit/                    # Unit tests by model
│   ├── integration/             # Cross-model integration tests
│   ├── e2e/                     # End-to-end scenarios
│   ├── golden/                  # AI agent accuracy tests
│   └── contracts/               # DAPR event schema validation
│
├── scripts/                     # Build, deploy, and utility scripts
│   ├── e2e-up.sh                # Start/stop E2E Docker infrastructure
│   ├── e2e-test.sh              # Run E2E test suite
│   ├── e2e-preflight.sh         # Validate E2E environment before tests
│   ├── e2e-diagnose.sh          # Debug failing E2E infrastructure
│   ├── demo-up.sh               # Start demo environment
│   ├── proto-gen.sh             # Generate Python stubs from proto files
│   ├── demo/                    # Demo data generation scripts
│   ├── agent-config/            # AI agent configuration loaders
│   ├── prompt-config/           # LLM prompt configuration scripts
│   ├── knowledge-config/        # Knowledge base setup scripts
│   ├── source-config/           # Data source configuration scripts
│   └── hooks/                   # Git hooks
│
├── config/                      # Environment configurations
└── docs/                        # Additional documentation
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.12 |
| **Validation** | Pydantic 2.0 |
| **API** | FastAPI (REST), gRPC (inter-service) |
| **AI Framework** | LangChain, LangGraph |
| **LLM Gateway** | OpenRouter |
| **Service Mesh** | DAPR (pub/sub, service invocation, state, secrets) |
| **Database** | MongoDB Atlas |
| **Vector DB** | Pinecone |
| **Storage** | Azure Blob Storage |
| **Observability** | OpenTelemetry via DAPR, Grafana Cloud |
| **Container Orchestration** | Kubernetes (AKS) |
| **Frontend** | React, MUI v6, Emotion |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Node.js 18+ (for frontend)
- DAPR CLI

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/jltournay/farmer-power-platform.git
   cd farmer-power-platform
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

4. **Start local infrastructure**
   ```bash
   bash scripts/e2e-up.sh
   ```

5. **Run tests**
   ```bash
   pytest tests/unit -v
   ```

### Running Services

Individual services can be started for development:

```bash
# Start a specific service
cd services/collection-model
uvicorn collection_model.main:app --reload --port 8001
```

For full platform testing, use the E2E infrastructure:

```bash
bash scripts/e2e-up.sh --build
bash scripts/e2e-test.sh
```

---

## Documentation

| Topic | Location |
|-------|----------|
| Architecture Decisions | `_bmad-output/architecture/` |
| API Specifications | `proto/` (gRPC), `services/bff/` (REST) |
| UX Design System | `_bmad-output/ux-design-specification/` |
| Test Strategy | `_bmad-output/test-design-system-level.md` |
| Demo Data Setup | `docs/demo-data.md` |

---

## Contributing

1. Create a feature branch from `main`
2. Follow the coding standards in `CLAUDE.md`
3. Ensure all tests pass: `pytest tests/ -v`
4. Run linting: `ruff check . && ruff format --check .`
5. Submit a pull request

---

## License

Proprietary - FarmerPower.ai

---

## Contact

- **Website:** [farmerpower.ai](https://farmerpower.ai)
- **Issues:** [GitHub Issues](https://github.com/jltournay/farmer-power-platform/issues)
