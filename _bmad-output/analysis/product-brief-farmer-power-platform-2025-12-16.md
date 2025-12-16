---
stepsCompleted: [1, 2]
inputDocuments: []
workflowType: 'product-brief'
lastStep: 2
project_name: 'farmer-power-platform'
user_name: 'Jeanlouistournay'
date: '2025-12-16'
---

# Product Brief: farmer-power-platform

**Date:** 2025-12-16
**Author:** Jeanlouistournay

---

## Executive Summary

**The One-Sentence Value Proposition:** Farmer Power Platform turns quality data into money - higher prices for farmers, less waste for factories, better exports for Kenya.

The platform is a cloud-based quality intelligence system built on one fundamental insight: *you can't improve what you can't measure, and you won't improve what you're not paid for.* By connecting real-time quality measurement directly to pricing and actionable feedback, the platform creates a virtuous circle where better farming practices lead to measurably better outcomes for everyone in the value chain.

**Business Model:** Factories subscribe because higher-quality intake means less processing waste and premium-grade output. Farmers participate for free because higher-quality delivery means better prices. Regulatory authorities gain visibility into national quality trends. Each stakeholder wins through their own self-interest - not altruism.

**Why This Works:** The platform doesn't create new value from nothing - it unlocks value that's currently lost to information asymmetry. Factories already pay premium for premium tea, but farmers don't know what "premium" means in measurable terms. The platform makes implicit knowledge explicit, enabling farmers who CAN improve to actually do so. For farmers facing structural constraints (soil, water, inputs), the platform identifies these barriers and routes them to appropriate support services.

Initial deployment targets tea production in Kenya (100 factories, 800,000 farms), with phased expansion across Africa and into multi-crop applications.

---

## Core Vision

### Problem Statement

The tea supply chain has a broken feedback loop. Farmers deliver leaves → Factories grade subjectively → Farmers receive a price with no explanation → Farmers have no idea how to improve → Quality stagnates → Kenya's tea brand suffers globally.

The core problem isn't *measurement* - it's the disconnect between quality, price, and actionable guidance. Farmers don't know why they got the price they got, and even if they did, they wouldn't know what to change.

### Problem Impact

- **Farmers**: Receive feedback days or weeks after delivery, missing the window to adjust practices. Current grading lacks transparency - farmers don't understand *why* they received a particular grade, breeding distrust and resistance to change.
- **Factories**: Cannot optimize processing parameters for incoming batch quality, leading to waste and inconsistency. Quality managers spend hours daily resolving disputes with farmers over subjective grades.
- **Regulatory Authorities**: Lack data-driven insights into national quality trends and international market positioning. Cannot demonstrate measurable quality improvements to support national branding initiatives.
- **Markets**: "Blind" production disconnected from buyer preferences results in suboptimal pricing and unsold inventory

### Why Existing Solutions Fall Short

Traditional quality control relies on manual inspection, subjective grading, and delayed laboratory results. These approaches fail on three dimensions:
- **Speed**: Assessment happens post-processing, not at intake
- **Actionability**: Results are technical metrics, not farmer-friendly guidance
- **Market Intelligence**: No connection between production quality and buyer demand

Until recently, the technology to change this paradigm didn't exist. Advances in computer vision, edge AI, and cloud-scale analytics now make real-time, objective quality assessment economically viable.

### Proposed Solution

The Farmer Power Platform closes the loop with three connected capabilities:

1. **Transparent Grading**: AI-powered quality assessment at intake with photographic evidence. Farmers see exactly what affected their grade - not abstract scores, but pictures of woody stems, diseased leaves, or incorrect plucking.

2. **Price-Linked Feedback**: Every quality assessment translates directly to price impact. "Your batch graded 78/100. The moisture content cost you 3 KES/kg. Here's how to fix it."

3. **Contextual Guidance**: Instead of arbitrary weekly messages, farmers receive contextually-timed guidance aligned with the farming calendar. During plucking season: technique tips tied to their specific quality issues. Pre-fertilizer season: input recommendations based on soil and yield history. Each message addresses the farmer's most impactful improvement opportunity for their current farming phase.

The six technical models (Collection, Knowledge, Action, Plantation, Market Analysis, AI) power this experience invisibly. Users don't see models - they see prices, photos, and simple instructions.

**Delivery Channels:** Guidance is delivered via SMS in local languages (Swahili, Kikuyu, Luo) to accommodate farmers with basic feature phones. Visual evidence (photos of leaf quality issues) can be accessed via factory kiosks or WhatsApp for farmers with smartphones.

---

## Key Differentiators

The platform's defensibility comes not from doing six things, but from owning the **quality data layer** that makes everything else possible:

1. **Real-time AI Quality Assessment**: Objective measurement at the point of intake, not subjective post-processing evaluation. This generates the proprietary quality dataset.

2. **Closed-Loop Farmer Feedback**: Actionable improvement guidance delivered in local languages. Factory incentives align with farmer adoption - higher incoming quality means less processing waste.

3. **Market Intelligence Integration**: Buyer preference profiles that connect production quality to market demand. This data layer becomes more valuable over time as historical patterns accumulate.

**The Moat:** Competitors can build better grading hardware or better market analytics, but they can't replicate 24 months of quality-outcome correlation data for 800,000 farms. This dataset - linking specific farming practices to specific quality outcomes to specific price improvements - is the true moat. The flywheel is how we build that dataset; the dataset is what competitors cannot copy.

**Focused Execution:** Phase 1 focuses exclusively on grading accuracy and farmer feedback. Market intelligence and regulatory dashboards are Phase 2 additions only after the core loop is proven. We win by doing one thing exceptionally well first.

---

## Risk Mitigation

### Trust Safeguards
- AI accuracy target: 97%+ agreement with expert human graders (validated quarterly)
- Confidence scores displayed - only grades with <90% confidence trigger human review (expected: <5% of batches)
- Factory quality managers retain override authority; overrides tracked and fed back to improve models
- Dispute escalation is exception handling, not standard process - target <0.1% dispute rate
- Regional model validation before deployment ensures local accuracy before trust is tested

### Adoption Assurance
- Track implementation rates per farmer to measure advice effectiveness
- Tiered engagement: Active responders receive personalized coaching; non-responders receive simplified messages
- Minimum 15% price differential between grades to create meaningful incentive for improvement

### Operational Resilience
- Edge processing handled by Farmer Power QC Analyzer (separate product/team) - this platform receives data, not responsible for hardware
- Platform designed for intermittent connectivity: batch uploads accepted, not dependent on real-time streaming
- Graceful degradation: Factories can operate analyzers standalone for days; cloud sync catches up automatically
- Clear responsibility boundary: QC Analyzer team owns hardware reliability; Platform team owns data intelligence

### Regulatory Strategy
- Position as "grader decision support" not "grader replacement"
- Partner with Tea Board of Kenya on pilot certification program
- Publish transparency reports comparing AI accuracy to human grader baseline

### Competitive Defense
- Modular product tiers enabling entry at grading-only level
- 12+ months of quality history creates switching cost through data value
- Open API strategy to become the platform ecosystem others build upon

### Data Governance
Farmers own their individual farm data. Factories access aggregated insights for their supplier base. Regulatory authorities receive anonymized industry-level analytics. All data handling complies with Kenya's Data Protection Act 2019.

### Adoption Strategy
The platform is free for farmers because the factory is the paying customer AND the factory benefits directly when farmer quality improves. This creates aligned incentives:
- Factory success metric: Percentage of intake graded premium
- Farmer success metric: Price per kg received
- Platform success metric: Both improving quarter-over-quarter

Farmers are not data sources - they are the mechanism through which factory ROI is delivered. If farmers don't improve, factories don't renew. This makes farmer success a commercial imperative, not charity.

---

## Technical Architecture Principles

### Design Philosophy
Build a solid foundation that evolves gracefully. The architecture must support today's tea-in-Kenya use case while enabling tomorrow's multi-crop, multi-country expansion without rewrites. Every architectural decision prioritizes: (1) reliability under real-world conditions, (2) clear extension points for new capabilities, and (3) operational simplicity for a lean team.

### Evolutive by Design
- **Open-Closed Principle:** Core platform is closed for modification, open for extension. New crops, new grading models, new analysis types are added via configuration - not code changes.
- **Contract-First Integration:** All module interactions defined by versioned schemas. Internal boundaries are future external boundaries - extraction to microservices requires no code changes.
- **Technology Abstraction (DAPR):** Infrastructure concerns (messaging, state, secrets) abstracted via DAPR sidecars. Swap databases, message brokers, or cloud providers without application changes.

### Deployment Architecture
- Each of the six models deploys as an independent Kubernetes pod (or pod set)
- All models are stateless; state persisted in MongoDB + Azure Blob
- Multiple replicas per model for fault tolerance - failure of one instance doesn't interrupt service
- DAPR sidecars handle inter-model communication, service discovery, and observability
- Models scale independently based on load (Collection scales for harvest peaks; Market Analysis scales for batch processing)

### Solid Foundation
- **Fail-Safe Operations:** Edge devices operate independently during cloud outages. Batch uploads accepted for intermittent connectivity. Graceful degradation over catastrophic failure.
- **Observable by Default:** Full observability (logging, metrics, tracing) via OpenTelemetry from day one. LangChain/LangGraph traces integrated for AI debugging. Debug production issues without guesswork.

### AI Model Governance
New AI configurations (prompts, models, workflows) follow staged rollout:
1. **Staging:** Validation against synthetic data, accuracy > 95% on test corpus
2. **Pilot Factory:** Single factory (~3,000 farmers) with human review of action plans
3. **Regional Rollout:** 10 factories with monitoring, < 0.5% complaint threshold
4. **Full Deployment:** All factories with auto-rollback triggers

- No AI configuration reaches farmers without passing pilot factory validation
- Rollback capability: Revert to previous config version within 5 minutes
- Full audit trail links every AI output to its configuration version and inputs

### Edge/Cloud Responsibility Split
The cloud platform receives data from edge devices; it does not control them. Edge devices provide immediate grading; cloud provides enhanced grading with historical context. Both grades are stored, enabling continuous accuracy comparison. Clear team boundaries: QC Analyzer team owns hardware, Platform team owns intelligence.

### Two-Tier Data Architecture
- **Raw Documents (Azure Blob Storage):** Images, full analysis documents, action plans - immutable, append-only, cost-optimized for bulk storage with compliance retention
- **Index & Metadata (MongoDB):** Queryable references, relationships, scores, timestamps - optimized for fast lookups and aggregation pipelines
- **Knowledge Base (Pinecone):** Agronomic best practices and semantic search for AI context enrichment

### Inter-Model Communication

**Event-Driven (Async) - Default Pattern:**
- Collection Model publishes quality events to event bus
- Knowledge, Plantation, and Action Models subscribe to relevant topics
- DAPR Pub/Sub with at-least-once delivery and idempotency
- Dead-letter queues with alerting for failed message processing
- Processing SLA: Quality event to action plan < 60 seconds (p95)

**Request-Response (Sync) - Exception Pattern:**
- Used only when: (a) AI Model orchestration requires result to continue, or (b) user is actively waiting
- DAPR Service Invocation with 30-second timeout for AI, 5-second for data
- Circuit breakers prevent cascade failures (5 failures in 60s → open for 30s)
- Retry with exponential backoff (max 3 attempts)

**Message Design:**
- Events are self-contained: Include all required data, never assume read-after-write consistency
- Correlation IDs propagated across all interactions for end-to-end tracing
- Schema-validated payloads (Pydantic) at publish and consume

### Data Consistency Model

**Consistency Tiers:**

| Tier | Use Case | Write Concern | Read Concern | Read Preference |
|------|----------|---------------|--------------|-----------------|
| **Critical** | Quality events, action plan triggers | `w:majority, j:true` | `majority` | `primary` |
| **Operational** | Farm/factory record updates | `w:1` | `local` | `primaryPreferred` |
| **Analytical** | Dashboards, reports, market analysis | `w:1` | `local` | `secondaryPreferred` |

**Design Principles:**
- Every database operation explicitly declares its consistency tier - no implicit defaults
- Critical path (Quality Event → Action Plan) uses synchronous writes with majority acknowledgment
- UI displays "last updated" timestamps; users understand data freshness
- Idempotency keys on all write operations to handle duplicate delivery safely

**Acceptable Latencies:**
- Critical tier: +200ms write latency acceptable for durability guarantee
- Operational tier: Eventual consistency within 2 seconds
- Analytical tier: Up to 30 seconds staleness acceptable for dashboards

### Security Architecture

**Authentication & Authorization:**
- Edge devices: mTLS with X.509 certificates, device registry validation
- Users: OAuth2/OpenID Connect with 15-minute JWT access tokens
- RBAC roles: Admin, FactoryManager, FactoryViewer, Regulator
- Resource isolation: All queries scoped by factory_id/farm_id from JWT claims

**API Security:**
- Azure API Management (or Kong) as gateway
- Rate limiting: 100 req/min per user, 1000 req/min per factory
- WAF with OWASP Top 10 protection
- DDoS protection via Azure Front Door

**Data Protection:**
- Encryption at rest: AES-256 with customer-managed keys (Azure Key Vault)
- Encryption in transit: TLS 1.3 mandatory
- Field-level encryption for PII (farmer name, phone, GPS)
- Network isolation: Private endpoints for all Azure services

**Secrets Management:**
- DAPR Secret Store component abstracts secret access - application code never directly calls Azure Key Vault
- Azure Key Vault as the backing store for DAPR Secret Store
- Managed Identity for DAPR → Key Vault authentication (no stored credentials)
- Swap secret backends (Key Vault → HashiCorp Vault → AWS Secrets Manager) via DAPR config, no code changes
- Automated rotation: API keys quarterly, certificates annually

**Compliance (Kenya Data Protection Act 2019):**
- Data residency: Azure South Africa North region
- Farmer consent captured at registration
- Right to access/deletion workflows implemented
- Breach notification: 72-hour SLA with incident response plan

### Scalability Path
Architecture supports Kenya's scale (100 factories, 800K farms, 20M daily events) on day one. Horizontal scaling via Kubernetes (AKS) and MongoDB sharding provides clear path to 10x growth without architectural changes.

---

## Elicitation Methods Applied

This product brief was refined through the following advanced elicitation techniques:

| Method | Key Insights |
|--------|--------------|
| **Shark Tank Pitch** | Business model clarity, "integrated data flywheel" moat, aligned incentives |
| **User Persona Focus Group** | Delivery channels for basic phones, operational resilience, data governance |
| **First Principles Analysis** | Outcome-forward positioning ("turns data into money"), simplified to 3 user-facing capabilities |
| **Pre-mortem Analysis** | Comprehensive risk mitigation: trust, adoption, operations, regulatory, competitive |
| **Challenge from Critical Perspective** | Strengthened claims with specific metrics, phased execution strategy |
| **Architecture Decision Records** | Technical architecture principles: evolutive design, solid foundation, two-tier data |
| **Party Mode (Technical Team)** | Deployment architecture, AI governance, inter-model communication, data consistency, security |

---

*Document generated through BMAD Product Brief Workflow*
*Last updated: 2025-12-16*