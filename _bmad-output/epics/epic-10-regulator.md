# Epic 10: Regulator Dashboard

Tea Board of Kenya officials can view national-level quality intelligence. This dashboard is completely isolated from factory data for security.

**Related ADRs:** ADR-002 (Frontend Architecture), ADR-003 (Identity & Access Management)

**Scope:**
- Regulator web application (completely separate from factory systems)
- National quality overview with regional breakdown
- Leaf type distribution analysis
- Export readiness indicators
- No individual farmer PII visible

---

## Story 10.1: Regulator Application Scaffold

As a **platform developer**,
I want the Regulator Dashboard React application scaffolded,
So that TBK officials have a secure, isolated portal.

**Acceptance Criteria:**

**Given** the web folder structure exists
**When** I create `web/regulator/`
**Then** Vite + React + TypeScript project is initialized
**And** `@fp/ui-components` and `@fp/auth` are configured as dependencies
**And** Separate authentication configuration (B2B federation ready)

**Given** the application is deployed
**When** TBK officials access the portal
**Then** It's hosted on separate subdomain: `regulator.farmerpower.co.ke`
**And** No shared runtime state with factory applications
**And** All data is pre-aggregated (no individual farmer data)

**Given** authentication is configured
**When** regulator users sign in
**Then** They use TBK Azure AD tenant (B2B federation)
**And** No access to factory-level or farmer-level data
**And** Only `regulator` role has access

**Technical Notes:**
- Location: `web/regulator/`
- Separate B2C application registration
- B2B federation with TBK Azure AD (future)
- Reference: ADR-002, ADR-003 for isolation requirements

**Dependencies:**
- Story 0.5.1: Shared Component Library
- Story 0.5.3: Shared Auth Library

**Story Points:** 3

---

## Story 10.2: National Quality Overview

As a **Tea Board of Kenya official**,
I want to see national-level quality metrics,
So that I can monitor tea quality across all participating factories.

**Acceptance Criteria:**

**Given** I am logged in as regulator
**When** I view the National Overview page
**Then** I see: total participating factories, total farmers, total volume (kg)
**And** National average quality grade is shown
**And** Trend shows quality over time (weekly/monthly)

**Given** I want to understand quality distribution
**When** I view the quality breakdown
**Then** Chart shows: % Primary, % Secondary by region
**And** Comparison to previous period (week/month/quarter)
**And** Target thresholds are marked on chart

**Given** I need to identify problem areas
**When** quality falls below threshold
**Then** Regions are highlighted with warning indicator
**And** I can click to see regional details
**And** No individual factory or farmer names are shown

**Technical Notes:**
- API: Aggregated data only (no factory_id in response)
- Pre-computed aggregations (not real-time queries)
- Data anonymized at API layer

**Dependencies:**
- Story 10.1: Regulator Application Scaffold

**Story Points:** 5

---

## Story 10.3: Regional Quality Comparison

As a **Tea Board of Kenya official**,
I want to compare quality metrics across regions,
So that I can target interventions and policy.

**Acceptance Criteria:**

**Given** I navigate to Regional Comparison
**When** the page loads
**Then** Map of Kenya shows regions color-coded by quality
**And** Table shows: region name, avg grade, volume, trend
**And** Sorting and filtering by metric is available

**Given** I select a region
**When** I view region details
**Then** I see: factory count (anonymized), farmer count, quality trend
**And** Seasonal pattern analysis is shown
**And** Weather impact correlation (if significant)

**Given** I want to export data
**When** I click "Export Report"
**Then** PDF/Excel report is generated with selected metrics
**And** Report is branded with TBK logo
**And** Data export is logged for audit

**Technical Notes:**
- Map: Choropleth with Kenya county boundaries
- Export: Server-side PDF generation
- No factory identifiers in export

**Dependencies:**
- Story 10.1: Regulator Application Scaffold
- Story 10.2: National Quality Overview

**Story Points:** 5

---

## Story 10.4: Leaf Type Distribution & Export Readiness

As a **Tea Board of Kenya official**,
I want to analyze leaf type distribution and export readiness,
So that I can assess Kenya's tea export potential.

**Acceptance Criteria:**

**Given** I navigate to Leaf Type Distribution
**When** the page loads
**Then** I see: national breakdown by leaf_type (Purple Leaf, Fine, Coarse, etc.)
**And** Trend over time shows seasonal patterns
**And** Comparison to TBK quality targets

**Given** I view Export Readiness
**When** I analyze the data
**Then** I see: % meeting export grade thresholds
**And** Projection based on current trends
**And** Regional breakdown of export-ready volume

**Given** I need policy insights
**When** I view recommendations panel
**Then** AI-generated insights highlight:
  - Regions with improvement potential
  - Seasonal factors affecting quality
  - Suggested intervention focus areas
**And** Insights are based on aggregated data only

**Technical Notes:**
- Leaf type categories per TBK specification
- Export thresholds: configurable in admin
- AI insights: pre-generated daily (not real-time LLM calls)

**Dependencies:**
- Story 10.1: Regulator Application Scaffold
- Story 10.2: National Quality Overview

**Story Points:** 5
