---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
workflowType: 'product-brief'
lastStep: 4
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

## Scope Boundaries

**IMPORTANT:** This document covers the **Farmer Power Cloud Platform** - the cloud-based backend system. It does NOT cover the edge devices (QC Analyzers, tagging devices) which are a separate project.

### In Scope (This Project)

| Component | Description |
|-----------|-------------|
| **Cloud Platform** | Backend services, APIs, data processing |
| **6 Models** | Collection, Knowledge, Action, Plantation, Market Analysis, AI |
| **Data Storage** | MongoDB, Azure Blob, Pinecone |
| **Farmer Messaging** | SMS/WhatsApp/Voice IVR delivery to farmers |
| **Web Dashboards** | Factory manager, owner, and regulator interfaces |
| **API Gateway** | Receives data FROM QC Analyzers |
| **AI Action Plans** | Generates personalized farmer recommendations |
| **Analytics & Reporting** | Quality trends, ROI reports, regulatory data |

### Out of Scope (QC Analyzer Project)

The following are part of the **Farmer Power QC Analyzer** project ([github.com/farmerpower-ai/farmer-power-qc-analyzer](https://github.com/farmerpower-ai/farmer-power-qc-analyzer)):

| Component | Description |
|-----------|-------------|
| **QC Analyzer Device** | Hardware for factory grading (conveyor, cameras, sorting) |
| **Tagging Device** | Collection point device for farmer ID tagging |
| **Edge AI** | On-device grading models (IMX500, Hailo) |
| **Device UX** | Grace's operator interface, Peter's tagging interface |
| **Hardware Operations** | Conveyor belt, leaf dispersion, physical sorting |

### Context References

This document references the QC Analyzer project to explain:
- How quality data arrives at the Cloud Platform (via API)
- The end-to-end farmer journey (for context)
- Integration points between edge and cloud

Sections marked with **[CONTEXT - QC Analyzer Project]** describe the edge system for understanding data flow, but are not implementation scope for this project.

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

**Delivery Channels:** Guidance is delivered via SMS in local languages (Swahili, Kikuyu, Luo) to accommodate farmers with basic feature phones. For detailed explanations, farmers can call the **Voice IVR system** to hear action plans spoken in their local language via Text-to-Speech - addressing low-literacy farmers without smartphones. Visual evidence (photos of leaf quality issues) can be accessed via factory kiosks or WhatsApp for farmers with smartphones.

---

## Key Differentiators

The platform's defensibility comes not from doing six things, but from owning the **quality data layer** that makes everything else possible:

1. **Real-time AI Quality Assessment**: Objective measurement at the point of intake, not subjective post-processing evaluation. This generates the proprietary quality dataset.

2. **Closed-Loop Farmer Feedback**: Actionable improvement guidance delivered in local languages. Factory incentives align with farmer adoption - higher incoming quality means less processing waste.

3. **Market Intelligence Integration**: Buyer preference profiles that connect production quality to market demand. This data layer becomes more valuable over time as historical patterns accumulate.

**The Moat:** Competitors can build better grading hardware or better market analytics, but they can't replicate 24 months of quality-outcome correlation data for 800,000 farms. This dataset - linking specific farming practices to specific quality outcomes to specific price improvements - is the true moat. The flywheel is how we build that dataset; the dataset is what competitors cannot copy.

**Focused Execution:** Phase 1 focuses exclusively on grading accuracy and farmer feedback. Market intelligence and regulatory dashboards are Phase 2 additions only after the core loop is proven. We win by doing one thing exceptionally well first.

---

## Target Users

### Primary Users

**1. Farmer - "Wanjiku" (P1)**
- **Population:** 800,000 smallholder tea farmers in Kenya
- **Profile:** 45yo woman, 0.4 hectare plot, tea is 70% of household income, feature phone, literate in Swahili
- **Current pain:** Binary accept/reject with no explanation, no feedback, no way to improve
- **Journey:** Pluck (5:30 AM) → Deliver to collection point (11:00 AM) → Receive receipt → Wait → Receive SMS with grade + tip (3:00 PM) → Learn → Improve next harvest
- **Key need:** Understand WHY they got their grade and HOW to improve
- **Success metric:** Grade improvement over time, price per kg increase
- **Communication:** SMS in local languages (Swahili, Kikuyu, Luo), photos viewable at factory kiosk or via WhatsApp
**2. Collection Clerk - "Peter" [CONTEXT - QC Analyzer Project]**
- **Note:** Peter uses the **QC Analyzer tagging device**, not this Cloud Platform. Listed here to explain how data originates.
- **Population:** ~500 clerks across 100+ collection points
- **Profile:** 28yo, secondary school graduate, handles 200-400 farmers/day during peak season
- **Role in data flow:** Tags bags with Farmer ID → Data arrives at Cloud Platform via API
- **Cloud Platform interaction:** None direct - his device sends data to our API

**3. Factory QC Operator - "Grace" [CONTEXT - QC Analyzer Project]**
- **Note:** Grace uses the **QC Analyzer hardware**, not this Cloud Platform. Listed here to explain how grading data originates.
- **Population:** 1-2 operators per factory (100-200 total)
- **Profile:** 32yo, diploma in food science, operates the QC Analyzer device
- **Role in data flow:** Scans bags, AI grades on device → Grading results sent to Cloud Platform via API
- **Cloud Platform interaction:** None direct - QC Analyzer sends grading data to our API

### Secondary Users

**4. Factory Quality Manager - "Joseph"**
- Reviews dashboards, identifies problem farmers and collection points
- Takes action: contacts repeat offenders, schedules extension officer visits
- Key need: Actionable insights with farmer contact info, not just charts

**5. Factory Owner**
- Makes subscription/purchase decisions
- Reviews ROI: quality improvement %, waste reduction, premium grade increase
- Key need: Clear business case, monthly cost vs. savings

**6. Regulator (Tea Board of Kenya)**
- Views national quality trends, regional comparisons
- Supports national branding with quality data
- Key need: Aggregated, anonymized industry-level analytics

### Operational Flow (Corrected)

**Current State (Broken):**
```
Collection Point: Farmer → Clerk visual check → Accept/Reject → Weigh → SAME PRICE for all
Factory: Bags arrive anonymous → Grace samples 4% → Bad bags found but can't trace → Factory absorbs loss
```

**Future State (With Farmer Power):**
```
Collection Point: Farmer → Clerk visual check → Accept → Weigh → TAG WITH FARMER ID → Receipt
Factory: Bags arrive tagged → Grace scans 100% → AI grades each → Linked to farmer → SMS sent
```

### Farmer Traceability System

**Registration (One-time):**
- Farmer provides: Name, phone, National ID, collection point
- System generates: Farmer ID (e.g., WM-4521)
- Farmer receives: ID card + welcome SMS

**Tagging (Each delivery):**
- Peter enters Farmer ID → Device prints receipt+tag (perforated)
- Top half: Farmer keeps (receipt)
- Bottom half: Attached to bag (QR tag with string loop)
- Tag survives transport, scannable at factory

**Scanning (At factory) [CONTEXT - QC Analyzer Project]:**

*The factory scanning process is handled by the QC Analyzer hardware. This section describes how data flows to the Cloud Platform.*

**QC Analyzer Process (Out of Scope):**
- Operator scans bag QR code → AI grades on device → Physical sorting by grade

**Data Sent to Cloud Platform (In Scope):**

The QC Analyzer's `farmer_ai_platform_collection` component sends three event types via HTTP API:

| Event Type | When Sent | Data Content | Cloud Platform Action                           |
|------------|-----------|--------------|-------------------------------------------------|
| `END_BAG` | Bag grading complete | Final grade, complete leaf distribution, farmer ID, bag ID, factory ID | Store record, trigger SMS, update farmer history |
| `POOR_QUALITY_DETECTED` | Quality below threshold | Specific quality issues, sample images, farmer context | Generate Analyse and AI action plan             |

**QR Code Data Structure:**
- Farmer's national ID
- Factory national ID
- Collection date and time
- Unique bag ID (system-generated)

**Connectivity:**
- **Batch Upload** supported: QC Analyzers can operate offline and sync when connected
- Events are batched for efficient transmission
- Queue-based processing with retry logic for unreliable network conditions

The Cloud Platform does NOT control the QC Analyzer - it receives data via the Collection Model and generates action plans, SMS messages, and analytics.

### User Journey: One Bag's Complete Path

| Time | Wanjiku (Farmer) | Peter (Clerk) | Grace (QC Operator) | System |
|------|------------------|---------------|---------------------|--------|
| 5:30 AM | Plucks tea | | | |
| 10:30 AM | Walks to collection | | | |
| 11:00 AM | Waits in queue | Processing farmers | | |
| 11:45 AM | Delivers bag | Inspects, weighs, tags | | Tag created |
| 11:46 AM | Gets receipt, goes home | Loads truck | | |
| 2:00 PM | | | Scans bag WM-4521 | Bag scanned |
| 2:01 PM | | | Samples, AI grades: B (78) | Grade stored |
| 3:00 PM | **Receives SMS** | | | **SMS sent** |
| 4:30 PM | Reads tip, plans improvement | | Reviews dashboard | Reports generated |
| Next day | Applies tip: dark green only | | | |
| Next week | **Grade A!** Feedback loop closes | | | Improvement tracked |

### User Acceptance Criteria

**Wanjiku (Farmer) - Cloud Platform User:**
- [ ] Receives SMS within 3 hours of delivery
- [ ] SMS in Swahili, under 160 characters
- [ ] Shows: Grade, score, ONE specific tip
- [ ] Tip actionable within 24-48 hours
- [ ] Price impact shown in KES
- [ ] Can call Voice IVR for detailed explanation in local language
- [ ] Voice message plays full action plan via TTS (2-3 minutes max)
- [ ] Voice supports Swahili, Kikuyu, Luo language selection

**Joseph (Factory Quality Manager) - Cloud Platform User:**
- [ ] Dashboard loads in <3 seconds
- [ ] Can filter farmers by grade, collection point, trend
- [ ] One-click contact for problem farmers
- [ ] Daily reports auto-generated by 6 AM
- [ ] Clear "action needed" vs. "watch" vs. "wins" categorization

**API (Data Ingestion from QC Analyzer):**
- [ ] Accepts `END_BAG` events to store records, trigger SMS, update farmer history
- [ ] Accepts `POOR_QUALITY_DETECTED` events to generate AI action plans
- [ ] Batch upload supported for intermittent connectivity (queue-based retry)
- [ ] Processes `END_BAG` → SMS in <3 hours; `POOR_QUALITY_DETECTED` → Analysis 
- [ ] Validates incoming data schema (reject malformed)
- [ ] Returns confirmation with event ID and processing status

*Note: Peter (Collection Clerk) and Grace (Factory QC Operator) use the QC Analyzer hardware, not this Cloud Platform. Their acceptance criteria are defined in the [QC Analyzer project](https://github.com/farmerpower-ai/farmer-power-qc-analyzer).*

### UX Design Principles

**Core Philosophy:** Technology should be invisible. Users focus on tea, not software.

#### SMS Experience Design (Wanjiku)

The SMS is the ONLY touchpoint for 800,000 farmers. These 160 characters must be perfect.

**Message Structure:**
```
LINE 1: Identity + Result (emotional connection)
LINE 2: The WHY (understanding)
LINE 3: The HOW (actionable next step)
```

**Visual Grade System (Stars, not Letters):**
- Grade A = ⭐⭐⭐⭐⭐ (5 stars) - Universal understanding
- Grade B = ⭐⭐⭐⭐ (4 stars) - Shows "close to top"
- Grade C = ⭐⭐⭐ (3 stars)
- Grade D = ⭐⭐ (2 stars)

**Personalization Requirements:**
- Use farmer's NAME ("Mama Wanjiku" not "WM-4521")
- Reference improvement trajectory ("Up from 3 stars last week!")
- Celebrate wins ("⭐⭐⭐⭐⭐ First time! Well done!")
- Swahili phrasing should feel like a friend, not a system

**Example SMS:**
```
Mama Wanjiku, chai yako: ⭐⭐⭐⭐ (78)
Majani ya manjano yamepunguza daraja
Kesho: chuma KIJANI tu = ⭐⭐⭐⭐⭐!
```

#### Collection Point Device UX (Peter) [CONTEXT - QC Analyzer Project]

*This section describes the tagging device UX for context. Implementation is part of the [QC Analyzer project](https://github.com/farmerpower-ai/farmer-power-qc-analyzer).*

**Design Constraints:** 300 farmers waiting, one-handed operation, outdoor conditions.

**Key Principles:** Fast tagging (<10 sec), farmer lookup, offline-capable, high contrast display.

#### QC Analyzer Interface UX (Grace) [CONTEXT - QC Analyzer Project]

*This section describes the QC Analyzer operator interface for context. Implementation is part of the [QC Analyzer project](https://github.com/farmerpower-ai/farmer-power-qc-analyzer).*

**Design Constraint:** One bag every 11.5 seconds. Interface supports rhythm through sound-based feedback.

**Key Principles:** Sound-driven workflow, single-button operation, progress display.

#### Dashboard UX (Joseph)

**Philosophy:** Action-oriented, not data-oriented. Joseph wants "What should I do?" not charts.

**Homepage Structure:**
- 🔴 **ACTION NEEDED** - Problems requiring immediate attention
- 🟡 **WATCH** - Trends that may become problems
- 🟢 **WINS** - Celebrate improvements (send congratulations)

**Contextual Intelligence:**
- Show relative performance: "12% below factory average"
- Peer comparison: "Improving faster than 80% of peers"
- One-click farmer contact (WhatsApp/SMS/Schedule visit)

#### Accessibility & Edge Cases

**Wanjiku (Low-tech, Low-literacy):**
- SMS works on ANY phone (no app required)
- **Voice IVR** for detailed explanations - farmer calls in to hear action plan in local language via TTS
- Audio messages via WhatsApp for low-literacy farmers with smartphones
- Factory kiosk displays photos for visual learners

**Peter (Outdoor, High-pressure):**
- Manual backup: Pre-printed tags if printer fails
- Handwritten ID option - manual entry at factory still works
- Never block queue for tech issues

**Grace (Noisy Factory):**
- Redundant feedback: Visual + Audio + Haptic
- Large display readable at arm's length
- Auto-recovery from errors without data loss

#### Design Principles Summary

| Principle | Application |
|-----------|-------------|
| **Invisible Technology** | System works in background; users focus on tea |
| **Progressive Disclosure** | Simple by default, details on demand |
| **Celebrate Progress** | Every improvement acknowledged |
| **Fail Gracefully** | Offline works, errors don't block, manual fallback exists |
| **Cultural Fit** | Local language that feels human, stars not letters, names not IDs |
| **Speed Over Features** | Peter and Grace need FAST, not feature-rich |
| **Action Over Data** | Joseph sees "do this" not "here's a chart" |

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

### AI Accuracy Validation

**Ground Truth Methodology:**
- Expert panel consensus: 3 independent graders, 2/3 agreement required, 4th arbitrator for disputes
- Golden dataset: 5,000+ validated samples, stratified by season/region/factory/grade, version-controlled
- Human baseline: Measure inter-rater reliability (Fleiss' Kappa) to establish accuracy ceiling - AI cannot exceed human agreement

**Accuracy Metrics:**

| Metric | Target | Description |
|--------|--------|-------------|
| Overall Agreement | ≥97% | AI matches expert panel consensus |
| Within-1-Grade | ≥99% | AI within one tier of consensus |
| Critical Misgrade | <0.1% | Premium↔Reject confusion |
| Inter-rater Reliability | Kappa ≥0.85 | AI consistency vs expert panel |

**Continuous Validation:**
- 1% production sampling for expert review (random selection)
- Weekly accuracy dashboards by region/factory/grade tier
- Drift detection: Alert if accuracy drops below 95%
- Monthly full golden dataset evaluation
- Quarterly golden dataset refresh with discovered edge cases

**Calibration Loop:**
- Misgraded samples analyzed and categorized (lighting, leaf variety, edge case)
- Failure patterns feed back to training/prompt improvement
- Model updates follow staged rollout (staging → pilot → regional → full)
- Full audit trail links accuracy metrics to model versions

**Expert Review Process:**
- Blind review: Experts grade without seeing AI prediction
- 48-hour SLA for expert review completion
- Disagreement reasons captured for failure taxonomy
- Expert calibration sessions quarterly to maintain consistency

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

### API Architecture

**Design Standards:**
- All APIs follow [Google API Design Guide](https://cloud.google.com/apis/design) for consistency, naming conventions, and error handling
- Resource-oriented design with standard methods (List, Get, Create, Update, Delete)
- Consistent error responses with standard error codes

**Inter-Model Communication (gRPC):**
- All model-to-model communication uses gRPC with Protobuf schemas
- DAPR service invocation abstracts gRPC transport
- Schemas versioned and stored in central schema registry
- Backward compatibility enforced via Protobuf evolution rules

**External APIs (Backend-for-Frontend):**
- REST APIs for Factory UI and Regulator UI (Google API Guide compliant)
- WebSocket for real-time dashboard updates
- FastAPI as the BFF framework

**AI Agent Data Access (MCP Servers):**
- AI agents access platform data via tools, not direct database queries
- Each logical data domain exposed through dedicated MCP (Model Context Protocol) server:
  - **MCP-CollectedDocuments:** Quality results, images, weather data
  - **MCP-Analysis:** Knowledge model outputs, disease detection results
  - **MCP-ActionPlan:** Generated action plans, farmer feedback
  - **MCP-PlantationModel:** Farm, factory, grading model, buyer profiles
- Benefits:
  - Domain-aligned: Agents query by business concept, not storage structure
  - Testability: Mock MCP layer for agent unit tests
  - Security: MCP servers enforce access control per domain
  - Observability: All data access logged and traced

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

### Disaster Recovery

**Infrastructure Resilience (Azure-Managed):**
- AKS deployed across 3 availability zones
- Leader election between API server nodes for control plane HA
- Azure handles zone failover, node replacement, and control plane recovery
- Platform team responsibility: Stateless pods + externalized state (MongoDB, Blob)

**Data Layer Resilience:**
- MongoDB Atlas: Multi-AZ replica set (managed by MongoDB Atlas or Azure Cosmos DB for MongoDB)
- Azure Blob Storage: Zone-redundant storage (ZRS) by default
- Pinecone: Managed service with built-in redundancy

**Platform Team Responsibility:**
- Ensure pods are stateless and can restart on any node
- Ensure no single-AZ affinity in deployments
- Monitor Azure Service Health for regional incidents
- Backup strategy for MongoDB (point-in-time recovery) - operational, not DR

### Cost Architecture

**LLM Strategy: OpenRouter.ai**
- Multi-model approach: Select optimal model per agent based on task complexity
- Unified API: Single integration, access to all major providers
- No vendor lock-in: Switch models via configuration without code changes
- Cost monitoring: OpenRouter dashboard + custom per-agent tracking

**Model Selection by Agent:**

| Agent | Primary Model | Fallback | Selection Criteria |
|-------|---------------|----------|-------------------|
| Data Validation | Mistral 7B | Llama 3 8B | Speed, cost, structured output |
| Quality Analysis | Claude 3 Haiku | GPT-4o-mini | Vision + cost balance |
| Disease Detection | Claude 3.5 Sonnet | GPT-4o | Best vision accuracy |
| Action Plans | Claude 3 Haiku | Mistral 7B | Reasoning + localization |
| Complex Advice | Claude 3.5 Sonnet | GPT-4o | Deep agricultural knowledge |
| Knowledge Queries | Mistral 7B | Llama 3 8B | Simple retrieval, low cost |
| Market Analysis | GPT-4o | Claude 3.5 Sonnet | Analytical capability |

**Monthly Cost Target (Kenya Phase 1):** $20,000-25,000/month

**Cost Breakdown (Optimized):**

| Category | Monthly Cost |
|----------|--------------|
| Compute (AKS) | $1,500 |
| Storage (MongoDB, Blob, Pinecone) | $610 |
| LLM APIs (OpenRouter, optimized) | $10,000 |
| Messaging (WhatsApp + SMS fallback) | $8,000 |
| Voice IVR (TTS + IVR minutes) | $4,000 |
| Other (API Gateway, Weather) | $650 |
| **Total** | **~$25,000/month** |

**Unit Economics Targets:**
- Per factory: < $250/month
- Per farmer: < $0.50/year
- Per quality event: < $0.0001

**Cost Optimization Levers:**
- Semantic caching for repeated knowledge queries (30% reduction)
- Batch processing for non-urgent analysis (20% reduction)
- Model downgrade for simple tasks (automatic via OpenRouter routing)
- WhatsApp-first messaging strategy (70% reduction vs SMS)

**Cost Observability:**
- Query OpenRouter Cost API after each LLM generation to capture actual cost
- Store generation cost with each analysis record (farm_id, factory_id, agent, model, tokens, cost)
- Cost attribution: Every LLM call tagged with farmer_id and factory_id for full traceability
- Cost Dashboard with ventilation by:
  - Factory (monthly cost per factory, cost trends)
  - Farmer (cost per farmer, high-cost outliers)
  - Agent type (which agents consume most budget)
  - Model (cost distribution across models)
- Alerts: Per-factory cost exceeds threshold, unexpected cost spikes
- Weekly cost reports for operations team

### Testing Strategy

**Testing Pyramid:**
- **Unit Tests (70%):** Fast, isolated tests for business logic, handlers, validators. Target: <5 seconds for full suite.
- **Contract Tests (10%):** Schema validation for gRPC, REST, events, MCP tools. Run on every PR.
- **Integration Tests (15%):** Model-to-database, model-to-model via Testcontainers and mocks. Target: <2 minutes.
- **E2E Tests (5%):** Critical user journeys in staging environment. Run before deployment.

**AI Agent Testing (Technical):**
- Prompt unit tests: Validate template construction and variable injection
- Response parsing tests: Ensure agent can handle all expected output formats
- Mock MCP servers: Isolate agent logic from database dependencies
- Golden tests: Recorded prompt/response pairs for regression detection

**AI Agent Testing (Functional - Prompt Tuning):**
- **Evaluation Dataset:** Curated farm scenarios with agronomist-validated expected recommendations
- **Functional Assertions:** Must-include and must-not-include checks for domain correctness
- **LLM-as-Judge:** Automated evaluation of correctness, relevance, actionability, safety, completeness
- **Regression Suite:** Known-good outputs that must not degrade on prompt changes
- **Human Review:** Quarterly agronomist review of sampled action plans
- **A/B Comparison:** Side-by-side evaluation when testing new prompt versions

**Prompt Change Workflow:**
1. Developer modifies prompt
2. Unit tests validate technical correctness (parsing, structure)
3. Functional evaluation suite validates domain correctness (>80% pass required)
4. If <80% pass → Agronomist review before proceeding
5. Deploy to staging → Pilot factory validation → Production rollout

**MCP Server Testing (Technical + Functional):**

*Technical Tests:*
- Unit tests for each tool implementation
- Schema validation for inputs and outputs
- Error handling for invalid inputs, missing data, timeouts
- Integration tests with actual database (Testcontainers)

*LLM Comprehension Tests:*
- **Tool Selection:** Given a task description, does the LLM pick the correct tool?
- **Tool Avoidance:** Does the LLM avoid using tools when they don't apply?
- **Response Interpretation:** Can the LLM correctly summarize tool output?
- **Edge Case Handling:** Does the LLM handle empty results without hallucinating?
- **Tool Chain Reasoning:** For multi-step tasks, does the LLM call tools in logical order?

*Tool Description Quality:*
- Every MCP tool description reviewed for LLM clarity
- Must specify: purpose, when to use, when NOT to use, response format
- Complex tools include usage examples in description
- Descriptions version-controlled and tested like prompts

**Test Infrastructure:**
- Testcontainers for MongoDB, Azurite for Blob Storage
- VCR.py cassettes for recorded OpenRouter responses (deterministic AI tests)
- Factory Boy for realistic test data generation
- GitHub Actions CI with parallelized test execution
- Evaluation dataset maintained by agronomist team (version controlled)

**Coverage Targets:**
- Unit tests: >80% line coverage
- Critical paths: 100% coverage (quality intake, action plan generation)
- Integration tests: All model-to-model interactions covered
- Functional eval: >90% pass rate on evaluation dataset before production
- MCP comprehension: 100% tool selection accuracy on test scenarios

**Test Environments:**
- **Local:** Full platform via Docker Compose + Testcontainers
- **CI:** Isolated per-PR with ephemeral databases
- **Staging:** Deployed environment for E2E and performance tests
- **Pilot Factory:** Production-like environment with real (anonymized) data

### Local Development Experience

**One-Command Startup:**
- `docker-compose up` launches entire platform: 6 models + 4 MCP servers + databases
- Full local stack running in under 2 minutes
- Predictable ports for each service (model-collection:8001, model-knowledge:8002, etc.)

**Development Stack:**
```
docker-compose.yaml
├── mongodb (single instance, all collections)
├── redis (DAPR state/pub-sub simulation)
├── azurite (Azure Blob Storage emulator)
├── model-collection, model-knowledge, model-action
├── model-plantation, model-market-analysis, model-ai
├── mcp-collected-documents, mcp-analysis
├── mcp-action-plan, mcp-plantation-model
└── (optional) local vector DB for Pinecone mock
```

**DAPR Bypass Mode:**
- Direct service-to-service HTTP/gRPC calls locally
- DAPR abstraction enabled in deployed environments only
- Environment variable: `DAPR_ENABLED=false` for local development

**Hot Reload:**
- Volume-mounted source code directories
- uvicorn with `--reload` for automatic restart on code changes
- Rapid iteration without container rebuilds

**Mock LLM Mode:**
- Environment flag: `LLM_MOCK_MODE=true`
- Cached/deterministic LLM responses for fast local testing
- No API costs during development iteration
- Responses keyed by prompt hash for reproducibility

**Seed Data Scripts:**
- `make seed-db` populates MongoDB with representative test data
- Anonymized patterns from production scenarios
- Realistic farm, factory, and quality event data

**Makefile Interface:**
```makefile
up:           docker-compose up -d
down:         docker-compose down
logs:         docker-compose logs -f
seed:         python scripts/seed_local_db.py
test:         pytest tests/
test-mcp:     pytest tests/mcp/ --functional
shell-model:  docker-compose exec model-$(MODEL) /bin/bash
```

**Local Observability:**
- Jaeger for distributed tracing
- Simple dashboard showing model-to-model calls
- Debug inter-model communication without guesswork

**30-Minute Onboarding Target:**
- Prerequisites: Docker, Python 3.11+, Make
- First-time setup: `make setup && make up && make seed`
- Verify: `make test` passes
- New developer productive in 30 minutes, not 3 hours

### Performance Baselines

**API Response Time Targets:**

| Category | p50 | p95 | p99 |
|----------|-----|-----|-----|
| Read (single) | 50ms | 150ms | 300ms |
| Read (list) | 100ms | 300ms | 500ms |
| Write | 100ms | 200ms | 400ms |
| Quality lookup | 50ms | 100ms | 200ms |

**AI Operation Targets:**

| Operation | p50 | p95 | Timeout |
|-----------|-----|-----|---------|
| Quality analysis | 3s | 6s | 30s |
| Action plan | 2s | 5s | 30s |
| Knowledge query | 1s | 3s | 15s |
| Disease detection | 4s | 8s | 30s |

**System Throughput (Kenya Scale):**
- Quality events: 10,000/hour (peak: 20,000)
- API requests: 100/second (peak: 200)
- Concurrent users: 500 (peak: 1,000)
- LLM calls: 200/minute (peak: 400)

**Event Processing SLAs:**
- Quality Event → Action Plan: < 60 seconds (p95)
- Quality Event → Farmer SMS: < 5 minutes
- Dashboard staleness: < 30 seconds
- Daily reports: Complete by 6 AM local

**Performance Testing Cadence:**
- Load testing: Weekly in staging
- Stress testing: Before major releases (2x peak)
- Soak testing: Monthly (24-hour runs)
- Chaos testing: Quarterly (failure injection)

**Resource Efficiency Targets:**
- CPU utilization: < 60% average (alert > 80%)
- Memory utilization: < 70% (alert > 85%)
- Error rate: < 0.1% (alert > 1%)

### Payment Model Flexibility

**Platform Philosophy:** Farmer Power provides quality DATA. Each factory chooses their POLICY.

The platform is payment-model agnostic. Each factory configures their preferred approach based on their relationship with farmers and readiness for change.

**Supported Payment Policies:**

| Policy | Description | Best For |
|--------|-------------|----------|
| **A: Split Payment** | 70% at collection, 30% based on grade | Factories wanting immediate quality incentive |
| **B: Weekly Bonus** | Full payment at collection + weekly quality bonus | Factories easing into quality pricing |
| **C: Delayed Payment** | Payment after factory grading (1-2 days) | Factories with established farmer trust |
| **D: Feedback Only** | Same flat payment, feedback for improvement | Pilot phase, building trust |
| **E: Reputation Score** | Flat payment + farmer reputation tracking | Long-term behavior change, gamification |

**Factory Configuration:**
- Select payment policy from admin dashboard
- Customize grade-to-price multipliers (Grade A = +20%, Grade D = -15%)
- Set bonus rules (threshold, amount, frequency)
- Preview SMS templates before activation
- Change policy with farmer notification period

**Key Principle:** Every farmer receives the same quality feedback (grade, photo, tip). Payment mechanics vary by factory preference.

**Recommended Onboarding Path:**
1. **Month 1-2:** Option D (Feedback Only) - build trust, no payment changes
2. **Month 3-4:** Option E (Reputation) - add gamification, recognition
3. **Month 5-6:** Option B (Weekly Bonus) - introduce low-risk incentives
4. **Month 7+:** Option A or C - full quality-based pricing (factory decides)

### Scalability Path
Architecture supports Kenya's scale (100 factories, 800K farms, 20M daily events) on day one. Horizontal scaling via Kubernetes (AKS) and MongoDB sharding provides clear path to 10x growth without architectural changes.

---

## Success Metrics

### North Star Metric

**Quality Improvement Rate:** Percentage increase in Grade A+B tea intake across all factories
- This single metric captures: farmer behavior change, system effectiveness, factory ROI
- Target: **+20% Grade A+B intake within 12 months** of deployment

### User Success Metrics

**Wanjiku (Farmer) Success:**

| Metric | Measurement | Target | Timeframe |
|--------|-------------|--------|-----------|
| Grade Improvement | Average grade score change per farmer | +15 points (e.g., 65→80) | 6 months |
| Income Increase | Price per kg received vs. baseline | +15% | 12 months |
| Tip Action Rate | % of farmers who improve after receiving tip | >40% | Per delivery |
| Feedback Loop Closure | % of farmers who reach Grade A at least once | >25% | 12 months |
| SMS Engagement | % of farmers who read SMS (via delivery confirmation) | >80% | Ongoing |

**Peter (Collection Clerk) Success:**

| Metric | Measurement | Target | Timeframe |
|--------|-------------|--------|-----------|
| Processing Speed | Time per bag (including tagging) | <60 seconds | Ongoing |
| Tagging Compliance | % of bags correctly tagged | >99% | Ongoing |
| Dispute Reduction | Arguments at collection point | -100% (zero disputes) | 3 months |
| System Adoption | % of clerks using system daily | 100% | 1 month post-training |

**Grace (Factory QC Operator) Success:**

| Metric | Measurement | Target | Timeframe |
|--------|-------------|--------|-----------|
| Throughput | Bags processed per hour | 250+ bags/hour | Ongoing |
| Coverage | % of bags graded (vs. 4% sampling) | 100% | Day 1 |
| Processing Time | Time per bag (scan → grade) | <15 seconds | Ongoing |
| System Uptime | % of operating hours without issues | >99% | Ongoing |
| Exception Rate | % of bags flagged for review | <5% | Ongoing |

### Business Objectives

**Factory ROI (Primary Business Metric):**

| Metric | Measurement | Target | Timeframe |
|--------|-------------|--------|-----------|
| Quality Waste Reduction | $ saved from reduced bad tea processing | >$20,000/month | 6 months |
| Premium Grade Increase | % of output graded premium | +25% | 12 months |
| Dispute Resolution Cost | Hours/month spent on farmer disputes | -80% | 3 months |
| Payback Period | Time to recover subscription cost | <3 months | - |

**Platform Growth (Company Objectives):**

| Metric | Measurement | Target | Timeframe |
|--------|-------------|--------|-----------|
| Factory Adoption | # of factories using platform | 10 factories (pilot) | 6 months |
| | | 50 factories | 18 months |
| | | 100 factories (Kenya) | 36 months |
| Farmer Coverage | # of farmers receiving feedback | 80,000 (pilot) | 6 months |
| | | 400,000 | 18 months |
| | | 800,000 (Kenya) | 36 months |
| Net Revenue Retention | % of factories renewing | >90% | Annual |
| Monthly Recurring Revenue | Subscription revenue | $25,000 (pilot) | 6 months |
| | | $250,000 | 18 months |

### Key Performance Indicators (KPIs)

**Leading Indicators (Predict Success):**
- Farmer SMS engagement rate (>80%)
- Tip action rate (>40%)
- Collection point tagging compliance (>99%)
- QC Analyzer uptime (>99%)

**Lagging Indicators (Prove Success):**
- Grade distribution shift (more A+B, fewer C+D)
- Farmer income increase (+15%)
- Factory waste reduction ($20K+/month)
- Factory renewal rate (>90%)

**System Health Indicators:**
- AI grading accuracy (≥97% vs. expert panel)
- SMS delivery rate (>98%)
- Processing latency (Quality Event → SMS <3 hours)
- System availability (>99.5%)

### Measurement Strategy

**Data Sources:**
- Grade distributions from QC Analyzer (automatic)
- SMS delivery/read receipts from messaging provider
- Factory financial reports (monthly review)
- Farmer surveys (quarterly sampling)
- Expert panel validation (monthly sampling)

**Reporting Cadence:**

| Report | Audience | Frequency |
|--------|----------|-----------|
| Operational Dashboard | Grace, Joseph | Real-time |
| Factory Quality Report | Factory Owner | Weekly |
| Farmer Progress Report | Extension Officers | Monthly |
| Platform Health | Platform Team | Daily |
| Business Review | Leadership | Monthly |
| ROI Report | Factory Owner, Sales | Quarterly |

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
| **Party Mode (Technical Team)** | Deployment architecture, AI governance, AI accuracy validation, inter-model communication, data consistency, security, DR, cost architecture, API design, testing strategy, local dev experience, performance baselines |
| **Party Mode (User Personas)** | Farmer (Wanjiku), Collection Clerk (Peter), Factory QC Operator (Grace), corrected operational flow, tagging system, payment flexibility, complete user journeys |
| **UX Designer Review (Sally)** | SMS experience design with stars, personalization, cultural fit; collection device UX; QC Analyzer sound design and rhythm; action-oriented dashboard; accessibility and edge cases |

---

*Document generated through BMAD Product Brief Workflow*
*Last updated: 2025-12-16*