# Epic 3: Factory Manager Dashboard

**Priority:** P6 (LAST frontend epic)

**Dependencies:** Epic 0.5 (Frontend Infrastructure), Epic 1 (Plantation Model), Epic 2 (Collection Model), Epic 4 (SMS Feedback), Epic 5 (Quality Diagnosis AI), Epic 6 (Weekly Action Plans)

**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR14

## Overview

This epic focuses on building the Factory Manager Dashboard - a comprehensive web interface for factory quality managers to monitor farmer quality metrics, categorize farmers by status, contact farmers directly, and generate daily reports. The dashboard serves as the primary tool for factory personnel to oversee quality across their farmer base and take action on quality issues.

**Note:** This is the MOST COMPLEX frontend application and should be built LAST. It requires data from all major backend services (Plantation, Collection, Knowledge, Action Plan, Notification) to display meaningful content. Build simpler UIs first (Epic 11 Kiosk → Epic 9 Admin → Epic 10 Regulator) to validate React patterns before tackling this epic.

## Scope

- Farmer quality overview grid with virtualized rendering
- Automatic farmer categorization (Action Needed/Watch/Wins)
- Dashboard filtering capabilities
- One-click farmer contact functionality
- Daily report auto-generation
- Performance optimization for large datasets
- Factory Owner ROI dashboard
- Factory Admin settings UI
- Command Center screen implementation
- Farmer detail screen
- SMS preview and compose functionality

**Note:** BFF Service Setup moved to Epic 0.5 (Story 0.5.6) as shared infrastructure for all frontends.

---

## Stories

### Story 3.1: Farmer Quality Overview Grid

As a **Factory Quality Manager**,
I want to see a grid of all farmers with their quality metrics,
So that I can quickly assess the quality situation across my factory.

**Acceptance Criteria:**

**Given** I am logged into the Factory Manager dashboard
**When** I view the Farmer Overview page
**Then** I see a grid of FarmerCards with: farmer_name, farmer_id, primary_percentage, trend_indicator, last_delivery_date, grade_badge
**And** the grid loads in < 3 seconds
**And** farmers are sorted by primary_percentage ascending (worst first) by default

**Given** the farmer grid is displayed
**When** a farmer has TBK grading data
**Then** the FarmerCard shows: primary_percentage (large), leaf_type_distribution (LeafTypeTag components), overall_grade (StatusBadge)

**Given** the farmer grid is displayed
**When** a farmer's trend is "improving"
**Then** a green TrendIndicator (up arrow) is shown
**When** a farmer's trend is "stable"
**Then** a gray TrendIndicator (right arrow) is shown
**When** a farmer's trend is "declining"
**Then** a red TrendIndicator (down arrow) is shown

**Given** the grid shows 500+ farmers
**When** I scroll through the list
**Then** virtualized rendering ensures smooth scrolling
**And** only visible cards are rendered in the DOM
**And** memory usage remains stable

**Given** I click on a FarmerCard
**When** the detail panel opens
**Then** I see: full farmer details, 30-day quality history chart, recent deliveries list, communication history

**Technical Notes:**
- React with Material UI v6
- React-virtualized for large lists
- FarmerCard, StatusBadge, TrendIndicator, LeafTypeTag custom components
- API endpoint: GET /api/farmers?factory_id={id}&page={n}&size={s}

---

### Story 3.2: Farmer Categorization (Action Needed/Watch/Wins)

As a **Factory Quality Manager**,
I want farmers automatically categorized by status,
So that I can prioritize my attention on those needing help.

**Acceptance Criteria:**

**Given** a farmer has primary_percentage < 60% in last 7 days
**When** the dashboard loads
**Then** the farmer is categorized as "Action Needed" (red badge)
**And** appears at the top of the priority list

**Given** a farmer has primary_percentage 60-75% OR declining trend
**When** the dashboard loads
**Then** the farmer is categorized as "Watch" (amber badge)
**And** appears in the middle priority section

**Given** a farmer has primary_percentage > 75% AND stable/improving trend
**When** the dashboard loads
**Then** the farmer is categorized as "Wins" (green badge)
**And** appears in the success section

**Given** the dashboard shows categorized farmers
**When** I view the "Command Center" layout
**Then** I see three columns: Action Needed (left), Watch (center), Wins (right)
**And** each column shows count badge (e.g., "23 farmers")
**And** I can collapse/expand each column

**Given** a farmer's category changes
**When** new quality data arrives (via WebSocket)
**Then** the farmer moves to the new category with animation
**And** the category counts update in real-time

**Given** no farmers are in a category
**When** I view that category column
**Then** an empty state message is shown (e.g., "No farmers need immediate action - great work!")

**Technical Notes:**
- Categorization logic runs in BFF (not frontend)
- WebSocket for real-time updates (optional enhancement)
- Category thresholds configurable per factory

---

### Story 3.3: Dashboard Filtering

As a **Factory Quality Manager**,
I want to filter farmers by various criteria,
So that I can focus on specific segments of my farmer base.

**Acceptance Criteria:**

**Given** I am on the Farmer Overview page
**When** I select a grade filter (Grade 1, Grade 2, Grade 3)
**Then** only farmers with that grade are displayed
**And** the filter chip is shown in the active filters bar

**Given** I am on the Farmer Overview page
**When** I select a collection point filter
**Then** only farmers from that collection point are displayed
**And** the collection point dropdown shows all CPs for my factory

**Given** I am on the Farmer Overview page
**When** I select a trend filter (Improving, Stable, Declining)
**Then** only farmers with that trend are displayed

**Given** I am on the Farmer Overview page
**When** I select a date range filter
**Then** metrics are recalculated for that date range
**And** "Last 7 days", "Last 30 days", "Custom range" options are available

**Given** multiple filters are applied
**When** I view the results
**Then** filters are combined with AND logic
**And** the result count updates dynamically
**And** I can clear individual filters or "Clear all"

**Given** filters are applied
**When** I refresh the page
**Then** filters are persisted in URL query parameters
**And** the same view is restored on refresh

**Technical Notes:**
- Filters stored in URL: ?grade=2&cp=KEN-cp-001&trend=declining
- BFF endpoint: GET /api/farmers?factory_id=...&grade=...&cp=...&trend=...
- Material UI FilterChip components

---

### Story 3.4: One-Click Farmer Contact

As a **Factory Quality Manager**,
I want to quickly contact problem farmers,
So that I can follow up on quality issues without leaving the dashboard.

**Acceptance Criteria:**

**Given** I am viewing a FarmerCard or farmer detail panel
**When** I click the "Contact" button
**Then** a contact options menu appears: SMS, WhatsApp, Call

**Given** I select "SMS" contact option
**When** I click it
**Then** the SMSPreview component opens
**And** it shows a pre-filled message template based on farmer's quality issues
**And** I can edit the message before sending
**And** the send button triggers the Notification Model API

**Given** I select "WhatsApp" contact option
**When** I click it
**Then** a WhatsApp deep link opens with pre-filled message
**And** the farmer's phone number is auto-populated
**And** the message template includes farmer name and recent quality issue

**Given** I select "Call" contact option
**When** I click it
**Then** the farmer's phone number is copied to clipboard
**And** a toast notification confirms "Phone number copied"
**And** (optional) a tel: link opens the phone dialer

**Given** I send an SMS from the dashboard
**When** the message is sent successfully
**Then** a success toast appears: "SMS sent to {farmer_name}"
**And** the contact is logged in the farmer's communication history
**And** I can view the sent message in the detail panel

**Given** I send an SMS and it fails
**When** the error occurs
**Then** an error toast appears with reason
**And** I have option to retry
**And** the failed attempt is logged

**Technical Notes:**
- SMS via Notification Model gRPC API
- WhatsApp: wa.me/{phone}?text={encoded_message}
- SMSPreview component from UX spec
- Contact logging via Collection Model event

---

### Story 3.5: Daily Report Auto-Generation

As a **Factory Quality Manager**,
I want daily summary reports generated automatically,
So that I have a quality overview waiting for me each morning.

**Acceptance Criteria:**

**Given** it is 6:00 AM in the factory's timezone
**When** the scheduled report job runs
**Then** a daily summary report is generated for each factory
**And** the report includes: date, factory_name, total_farmers, total_deliveries, avg_primary_percentage, category_counts (Action/Watch/Wins)

**Given** a daily report is generated
**When** the report is created
**Then** it includes: top 10 problem farmers (by declining primary_percentage), top 5 improving farmers (success stories), collection point comparison

**Given** a daily report is generated
**When** I view the Reports section in the dashboard
**Then** the report is available as a card with: date, summary stats, "View Full Report" button, "Download PDF" button

**Given** I click "Download PDF"
**When** the PDF is generated
**Then** the PDF is formatted with factory branding
**And** it includes all report sections with charts
**And** file name format: {factory_id}_daily_report_{date}.pdf

**Given** the report generation fails
**When** the scheduled job encounters an error
**Then** the error is logged with full context
**And** an alert is sent to platform operators
**And** the previous day's report remains available

**Given** no quality data was received yesterday
**When** the report is generated
**Then** the report shows "No deliveries recorded" with appropriate messaging
**And** trend comparisons show week-over-week instead

**Technical Notes:**
- Dapr Jobs component for 6 AM scheduling (per-factory timezone)
- PDF generation via WeasyPrint or similar
- Reports stored in Azure Blob Storage
- Report retention: 90 days

---

### Story 3.6: Dashboard Performance Optimization

As a **Factory Quality Manager**,
I want the dashboard to load quickly even with large datasets,
So that I can efficiently review quality data without waiting.

**Acceptance Criteria:**

**Given** the dashboard has 5000+ farmers in the system
**When** I load the Farmer Overview page
**Then** the initial load completes in < 3 seconds
**And** the first 50 farmer cards are rendered
**And** remaining data loads progressively as I scroll

**Given** the BFF receives a dashboard request
**When** processing the request
**Then** read replica MongoDB connections are used
**And** commonly accessed data is cached (5-minute TTL)
**And** complex aggregations run on pre-computed materialized views

**Given** I apply filters on the dashboard
**When** the filtered results are requested
**Then** the response time is < 1 second
**And** the UI shows a loading skeleton during fetch

**Given** the dashboard is idle for 5+ minutes
**When** new quality data arrives
**Then** a subtle notification appears: "New data available - Click to refresh"
**And** data is not auto-refreshed (to avoid jarring changes during viewing)

**Given** the dashboard is under heavy load (1000 concurrent users)
**When** requests are processed
**Then** response times remain < 5 seconds (p95)
**And** HPA scales BFF pods appropriately
**And** no requests are dropped

**Given** a downstream service is unavailable
**When** the dashboard loads
**Then** available data is still displayed
**And** unavailable sections show "Data temporarily unavailable"
**And** the page does not crash

**Technical Notes:**
- Redis cache for hot data (farmer summaries, category counts)
- Materialized views for aggregations (updated every 5 min)
- Pagination: cursor-based for large result sets
- Error boundaries in React for graceful degradation

---

### Story 3.7: Factory Owner ROI Dashboard

As a **Factory Owner**,
I want to see ROI metrics and value validation for my subscription,
So that I can justify the platform investment to stakeholders.

**Acceptance Criteria:**

**Given** I am logged in as Factory Owner
**When** I navigate to the ROI Summary page
**Then** I see key metrics: quality improvement %, reject reduction, farmer retention
**And** Cost savings are calculated in KES
**And** Trend comparison shows month-over-month improvement
**And** Page loads in < 3 seconds

**Given** I am viewing ROI metrics
**When** I click on a metric card
**Then** I drill down to detailed breakdown (by collection point, by farmer segment)
**And** Charts show historical trend (3, 6, 12 month views)
**And** Export to PDF is available

**Given** I want regional context
**When** I view the Regional Benchmark page
**Then** My factory's metrics are compared to anonymous regional averages
**And** Ranking percentile is shown (e.g., "Top 20% in region")
**And** No competitor factory names are revealed

**Technical Notes:**
- Location: `web/factory-portal/src/pages/owner/`
- Components: ROISummary, ROIDrillDown, RegionalBenchmark
- Reference: ADR-002 for factory-portal structure

**Dependencies:**
- Story 0.5.4: Factory Portal Scaffold
- Story 0.5.6: BFF Service Setup

**Story Points:** 5

---

### Story 3.8: Factory Admin Settings UI

As a **Factory Administrator**,
I want to configure payment policies, grade multipliers, and SMS templates,
So that I can customize the platform for my factory's specific needs.

**Acceptance Criteria:**

**Given** I am logged in as Factory Admin
**When** I navigate to Settings -> Payment Policy
**Then** I can configure price per kg by grade (Premium, Standard, Reject)
**And** I can set minimum/maximum thresholds
**And** Changes require confirmation before saving

**Given** I am on the Grade Multipliers page
**When** I configure multipliers
**Then** I can set adjustment factors for leaf type distribution
**And** Preview shows sample calculation with current settings
**And** Historical multiplier changes are logged

**Given** I am on the SMS Templates page
**When** I manage templates
**Then** I can view and edit message templates per language (EN, SW)
**And** Character count is shown with GSM-7 compatibility check
**And** Preview shows how message appears on feature phone
**And** Templates use placeholders: {farmer_name}, {grade}, {tip}

**Given** I want to understand financial impact
**When** I use the Impact Calculator
**Then** I can simulate policy changes with current data
**And** Before/after comparison shows projected farmer payouts
**And** Calculation is explained transparently

**Technical Notes:**
- Location: `web/factory-portal/src/pages/admin/`
- Components: PaymentPolicy, GradeMultipliers, SMSTemplates, ImpactCalculator
- Reference: ADR-002 for factory-portal structure

**Dependencies:**
- Story 0.5.4: Factory Portal Scaffold
- Story 0.5.6: BFF Service Setup

**Story Points:** 5

---

### Story 3.9: Command Center Screen Implementation

As a **Factory Quality Manager (Joseph)**,
I want the Command Center screen to show today's quality overview,
So that I can identify farmers needing intervention at a glance.

**Acceptance Criteria:**

**Given** I am logged in as Factory Manager
**When** I open the Command Center
**Then** I see today's summary: total deliveries, average grade, top issues
**And** Three sections show: "Action Needed" (red), "Watch" (amber), "Wins" (green)
**And** Farmer cards show: name, ID, grade trend, last tip sent
**And** Sorting defaults to most urgent first (lowest grade, declining trend)

**Given** I am viewing the Command Center
**When** I click on a farmer card
**Then** I navigate to Farmer Detail page
**And** Full history and action options are available

**Given** I want to take quick action
**When** I use the action strip on a farmer card
**Then** I can trigger SMS, schedule call, or mark for follow-up
**And** Action confirmation appears inline
**And** Action is logged for audit

**Given** I need temporal context
**When** I click "View Patterns"
**Then** Temporal Patterns modal shows weekly/seasonal trends
**And** Weather correlation is highlighted if significant
**And** Recommended intervention timing is suggested

**Technical Notes:**
- Location: `web/factory-portal/src/pages/manager/CommandCenter/`
- Components: FarmerCard, ActionStrip, TrendChart
- Design: "Command Center" pattern from UX spec
- Reference: `_bmad-output/ux-design-specification/`

**Dependencies:**
- Story 0.5.4: Factory Portal Scaffold
- Story 3.1: Farmer Quality Overview Grid
- Story 3.2: Farmer Categorization

**Story Points:** 5

---

### Story 3.10: Farmer Detail Screen

As a **Factory Quality Manager**,
I want to view detailed farmer information and history,
So that I can make informed intervention decisions.

**Acceptance Criteria:**

**Given** I am on the Farmer Detail page
**When** the page loads
**Then** I see farmer profile: name, ID, farm size, collection point
**And** Contact info is shown with one-click actions (SMS, WhatsApp)
**And** Performance summary shows: avg grade, trend, total deliveries

**Given** I am viewing farmer details
**When** I look at the history section
**Then** I see a timeline of quality events (last 30 days)
**And** Each event shows: date, grade, primary %, issues detected
**And** Events can be filtered by date range

**Given** I need AI insights
**When** I view the Insights panel
**Then** I see AI-generated summary: likely cause, recommended action
**And** Weather impact correlation is shown if relevant
**And** Comparison to similar farmers in collection point

**Given** I want to send a message
**When** I click "Compose SMS"
**Then** SMSPreview component opens with farmer context pre-filled
**And** Template selection with personalization
**And** Estimated cost shown before send

**Technical Notes:**
- Location: `web/factory-portal/src/pages/manager/FarmerDetail/`
- Components: FarmerProfile, EventTimeline, InsightsPanel, SMSPreview
- API: GET /api/farmers/{id} with history

**Dependencies:**
- Story 0.5.4: Factory Portal Scaffold
- Story 0.5.6: BFF Service Setup

**Story Points:** 5

---

### Story 3.11: SMS Preview and Compose

As a **Factory Quality Manager**,
I want to preview and compose SMS messages to farmers,
So that I can communicate effectively with proper personalization.

**Acceptance Criteria:**

**Given** I open the SMS Compose dialog
**When** I select a template
**Then** Template is populated with farmer context (name, grade, tip)
**And** Preview shows exactly how message appears on phone
**And** Character count shows: current/160 or current/320

**Given** I am composing a message
**When** I exceed 160 characters
**Then** Warning shows: "Message will be split (2 SMS, higher cost)"
**And** Character count turns amber
**And** Non-GSM-7 characters are highlighted for replacement

**Given** the message is ready
**When** I click "Send"
**Then** Confirmation dialog shows: recipient, message, estimated cost
**And** After confirmation, message is queued for delivery
**And** Success notification shows: "SMS queued - delivery in ~30 seconds"

**Given** I want to send to multiple farmers
**When** I select multiple farmers from Command Center
**Then** Bulk SMS option appears in action bar
**And** Same template is applied to all with individual personalization
**And** Total cost estimate shown before confirmation

**Technical Notes:**
- Component: `@fp/ui-components/SMSPreview`
- GSM-7 validation in component
- API: POST /api/sms/send (single), POST /api/sms/bulk (multiple)
- Integration with Story 4.1: Notification Model

**Dependencies:**
- Story 0.5.1: Shared Component Library
- Story 0.5.6: BFF Service Setup

**Story Points:** 3
