# Story 9.10b: Platform Cost Dashboard UI

As a **Platform Administrator**,
I want a **cost dashboard to monitor platform spending across LLM, Documents, and Embeddings**,
So that **I can track total costs, understand cost drivers by type, and configure budget thresholds**.

## Acceptance Criteria

**AC 9.10b.1: Total Cost Overview Tab**

**Given** I navigate to `/costs`
**When** the page loads
**Then** I see the Total Overview tab active with:
- KPI cards: Total Cost (period), Today Live (real-time), Budget Status (utilization %)
- Daily cost trend stacked chart (LLM, Document, Embedding layers)
- Cost by type table: type, cost, requests, quantity, % of total
- Data availability boundary notice (TTL)
- Date range selector (Last 7 days, Last 30 days, This month, Last month, Custom)

**AC 9.10b.2: LLM Cost Detail Tab**

**Given** I click the "LLM" tab
**When** the tab loads
**Then** I see:
- KPI cards: LLM Total, Requests, Avg Cost/Request (calculated)
- Daily LLM cost trend chart
- Cost by Agent Type breakdown (chart + table with tokens_in, tokens_out)
- Cost by Model breakdown (chart + table with tokens_in, tokens_out)

**AC 9.10b.3: Documents Cost Detail Tab**

**Given** I click the "Documents" tab
**When** the tab loads
**Then** I see:
- KPI cards: Document Total, Pages Processed, Avg Cost/Page
- Daily document cost trend chart
- Summary metrics table (total cost, documents processed, total pages, avg cost/page, period)

**AC 9.10b.4: Embeddings Cost Detail Tab**

**Given** I click the "Embeddings" tab
**When** the tab loads
**Then** I see:
- KPI cards: Embedding Total, Texts Embedded, Total Tokens
- Daily embedding cost trend chart
- Cost by Knowledge Domain table (domain, texts, tokens, cost, percentage)

**AC 9.10b.5: Date Range Selection**

**Given** I am on any tab
**When** I change the date range
**Then** all data on the current tab refreshes with the new range
**And** preset ranges available: Last 7 days, Last 30 days, This month, Last month, Custom
**And** Custom range shows date pickers for start/end (ISO YYYY-MM-DD)

**AC 9.10b.6: CSV Export**

**Given** I am on any tab
**When** I click "Export"
**Then** I can download a CSV file of the current tab's data
**And** the CSV includes all visible table data for the selected date range

**AC 9.10b.7: Budget Configuration Modal**

**Given** I click the "Budget" button
**When** the modal opens
**Then** I see:
- Current daily budget: threshold, today's spend, remaining, utilization progress bar
- Current monthly budget: threshold, this month's spend, remaining, utilization progress bar
- Today's breakdown by type
- Editable threshold fields (daily, monthly)
- Save button to persist threshold changes

## Wireframe: Total Cost Overview

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|  ===============                                                                 |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  TOTAL COST       |  |  TODAY (LIVE)     |  |  BUDGET STATUS    |            |
|  |  $1,892.30        |  |  $66.40           |  |  Monthly: 47%     |            |
|  |  Last 30 days     |  |  Updated 14:32    |  |  $1,892 / $4,000  |            |
|  |  3,386 requests   |  |  LLM: $45.20     |  |  Daily: 44%       |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  +----------------------------------------------------------------------+       |
|  |  DAILY COST TREND (Stacked by Type)                                   |       |
|  |  $150 -+-------------------------------------------------------------+       |
|  |        |  LLM [solid]  Document [dots]  Embedding [hash]              |       |
|  |        |     ####        ####                                         |       |
|  |  $100 -+---####..------####..--------------------------------------   |       |
|  |        |  ####..##    ####..##                                        |       |
|  |   $50 -+-####..##----####..##--------------------------------------   |       |
|  |        |                                                              |       |
|  |    $0 -+--------------------------------------------------------------+       |
|  |        1   5   10   15   20   25   30                                 |       |
|  |  (i) Data available from: 2025-11-01 (TTL boundary)                   |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|  COST BY TYPE                                                                    |
|  +----------------------------------------------------------------------+       |
|  |  Type             | Cost (period) | Requests | Quantity  | % Total   |       |
|  |  -----------------+---------------+----------+-----------+-----------+       |
|  |  LLM (OpenRouter) | $1,195.50     | 2,340    | --        | 63%       |       |
|  |  Documents (Azure)| $412.30       | 156      | 1,240 pg  | 22%       |       |
|  |  Embeddings (Pine)| $284.50       | 890      | 45,200 tk | 15%       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

## Wireframe: LLM Cost Detail (Tab View)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|                    =====                                                         |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  LLM TOTAL        |  |  REQUESTS         |  |  AVG COST/REQ     |            |
|  |  $1,195.50        |  |  2,340             |  |  $0.51            |            |
|  |  63% of total     |  |  Last 30 days     |  |  (calculated)     |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  +----------------------------------------------------------------------+       |
|  |  DAILY LLM COST TREND                                                 |       |
|  |  $50 -+-----------------------------------------------------------    |       |
|  |       |     /--\                                                      |       |
|  |  $25 -+----/    \--------/\--------------------------------------     |       |
|  |       |   /      \------/  \                                          |       |
|  |   $0 -+-----------------------------------------------------------    |       |
|  |       1   5   10   15   20   25   30                                  |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|  +---------------------------------+  +-------------------------------------+   |
|  |  COST BY AGENT TYPE             |  |  COST BY MODEL                       |   |
|  |                                  |  |                                      |   |
|  |  Agent Type    | Cost   | %      |  |  Model             | Cost   | %     |   |
|  |  --------------+--------+----    |  |  ------------------+--------+----   |   |
|  |  explorer      | $538   | 45%    |  |  claude-3-haiku    | $717   | 60%   |   |
|  |  generator     | $358   | 30%    |  |  gpt-4o-mini       | $299   | 25%   |   |
|  |  extractor     | $180   | 15%    |  |  gpt-4o            | $180   | 15%   |   |
|  |  other         | $120   | 10%    |  |                                      |   |
|  |                                  |  |                                      |   |
|  |  Reqs: 1,053  Tok-in: 2.1M     |  |  Reqs: 2,340  Tok-in: 4.8M          |   |
|  |                Tok-out: 890K    |  |                Tok-out: 1.9M         |   |
|  +---------------------------------+  +-------------------------------------+   |
|                                                                                  |
|  DETAILED AGENT TYPE BREAKDOWN                                                   |
|  +----------------------------------------------------------------------+       |
|  |  Agent Type  | Requests | Tokens In  | Tokens Out | Cost    | %      |       |
|  |  ------------+----------+------------+------------+---------+--------+       |
|  |  explorer    | 1,053    | 2,106,000  | 890,000    | $538.00 | 45%    |       |
|  |  generator   | 745      | 1,490,000  | 620,000    | $358.00 | 30%    |       |
|  |  extractor   | 342      | 684,000    | 285,000    | $180.00 | 15%    |       |
|  |  other       | 200      | 520,000    | 105,000    | $120.00 | 10%    |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

## Wireframe: Documents Cost Detail (Tab View)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|                            ===========                                           |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  DOCUMENT TOTAL   |  |  PAGES PROCESSED  |  |  AVG COST/PAGE    |            |
|  |  $412.30          |  |  1,240            |  |  $0.33            |            |
|  |  22% of total     |  |  156 documents    |  |  Azure Doc Intel  |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  +----------------------------------------------------------------------+       |
|  |  DAILY DOCUMENT COST TREND                                            |       |
|  |  $25 -+-----------------------------------------------------------    |       |
|  |       |        /\              /\                                     |       |
|  |  $15 -+--------\/              \/-------------------------------      |       |
|  |       |                                                               |       |
|  |   $0 -+-----------------------------------------------------------    |       |
|  |       1   5   10   15   20   25   30                                  |       |
|  +----------------------------------------------------------------------+       |
|  Note: Spikes correlate with knowledge base upload batches                       |
|                                                                                  |
|  SUMMARY METRICS                                                                 |
|  +----------------------------------------------------------------------+       |
|  |  Metric              | Value                                         |       |
|  |  --------------------+-----------------------------------------------+       |
|  |  Total Cost          | $412.30                                       |       |
|  |  Documents Processed | 156                                           |       |
|  |  Total Pages         | 1,240                                         |       |
|  |  Avg Cost per Page   | $0.33                                         |       |
|  |  Period              | 2025-12-25 to 2026-01-24                       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

## Wireframe: Embeddings Cost Detail (Tab View)

```
+---------------------------------------------------------------------------------+
|  PLATFORM COSTS                                          [Export v] [Budget]     |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  [Total Overview]  [LLM]  [Documents]  [Embeddings]                             |
|                                        ============                              |
|                                                                                  |
|  DATE RANGE: [Last 30 days v]  [Custom: _____ to _____]                         |
|                                                                                  |
|  +-------------------+  +-------------------+  +-------------------+            |
|  |  EMBEDDING TOTAL  |  |  TEXTS EMBEDDED   |  |  TOTAL TOKENS     |            |
|  |  $284.50          |  |  4,520            |  |  3.2M             |            |
|  |  15% of total     |  |  Last 30 days     |  |  Pinecone         |            |
|  +-------------------+  +-------------------+  +-------------------+            |
|                                                                                  |
|  +----------------------------------------------------------------------+       |
|  |  DAILY EMBEDDING COST TREND                                           |       |
|  |  $20 -+-----------------------------------------------------------    |       |
|  |       |  /\         /\                   /\                           |       |
|  |  $10 -+--\/         \/                   \/----                       |       |
|  |       |                                                               |       |
|  |   $0 -+-----------------------------------------------------------    |       |
|  |       1   5   10   15   20   25   30                                  |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|  COST BY KNOWLEDGE DOMAIN                                                        |
|  +----------------------------------------------------------------------+       |
|  |  Domain              | Texts  | Tokens    | Cost    | % of Embedding |       |
|  |  --------------------+--------+-----------+---------+----------------+       |
|  |  tea-quality         | 1,890  | 1,340,000 | $119.00 | 42%            |       |
|  |  farming-practices   | 1,245  | 890,000   | $82.50  | 29%            |       |
|  |  pest-management     | 780    | 560,000   | $46.80  | 16%            |       |
|  |  weather-advisory    | 605    | 430,000   | $36.20  | 13%            |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

## Wireframe: Budget Configuration Modal

```
+---------------------------------------------------------------------------------+
|  BUDGET CONFIGURATION                                                      [X]  |
+---------------------------------------------------------------------------------+
|                                                                                  |
|  CURRENT STATUS                                                                  |
|  +----------------------------------------------------------------------+       |
|  |                                                                       |       |
|  |  DAILY BUDGET                          MONTHLY BUDGET                 |       |
|  |  +----------------------------+       +----------------------------+  |       |
|  |  |  Threshold: $150.00        |       |  Threshold: $4,000.00      |  |       |
|  |  |  Today:     $66.40 (44%)   |       |  This month: $1,892 (47%) |  |       |
|  |  |  Remaining: $83.60         |       |  Remaining:  $2,108        |  |       |
|  |  |                            |       |                             |  |       |
|  |  |  [########..........] 44%  |       |  [#########........] 47%   |  |       |
|  |  +----------------------------+       +----------------------------+  |       |
|  |                                                                       |       |
|  |  TODAY'S BREAKDOWN (by_type map):                                     |       |
|  |  LLM: $45.20 | Document: $12.80 | Embedding: $8.40                   |       |
|  |                                                                       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|  CONFIGURE THRESHOLDS                                                            |
|  +----------------------------------------------------------------------+       |
|  |                                                                       |       |
|  |  Daily Threshold:    [$150.00     ]   (alert triggers when exceeded)  |       |
|  |  Monthly Threshold:  [$4,000.00   ]   (alert triggers when exceeded) |       |
|  |                                                                       |       |
|  |  (i) Alerts delivered by AlertManager via OTEL metrics.               |       |
|  |      Dashboard shows status only.                                     |       |
|  |                                                                       |       |
|  +----------------------------------------------------------------------+       |
|                                                                                  |
|                                                    {Cancel}  {Save Thresholds}  |
|                                                                                  |
+---------------------------------------------------------------------------------+
```

## Technical Notes

- Consumes BFF REST API endpoints from Story 9.10a (`/api/v1/admin/costs/*`)
- `GetCurrentDayCost` polled every 60 seconds for live today card
- Charts rendered using shared chart components from Story 9.1b
- Budget alerts handled by AlertManager via OTEL metrics — dashboard shows status only
- `data_available_from` displayed as info notice on trend charts
- Export CSV generated client-side from API response data

## BFF Endpoint to UI Mapping

| BFF Endpoint | UI Section |
|---|---|
| `GET /costs/summary` | Overview: total KPI card, type breakdown table |
| `GET /costs/trend/daily` | All tabs: daily trend charts (stacked on overview) |
| `GET /costs/today` | Overview: today live KPI card |
| `GET /costs/llm/by-agent-type` | LLM tab: agent type breakdown |
| `GET /costs/llm/by-model` | LLM tab: model breakdown |
| `GET /costs/documents` | Documents tab: summary metrics |
| `GET /costs/embeddings/by-domain` | Embeddings tab: domain breakdown |
| `GET /costs/budget` | Overview: budget KPI card + Budget modal: status |
| `PUT /costs/budget` | Budget modal: save thresholds |

## Dependencies

- Story 9.10a: Platform Cost BFF REST API
- Story 9.1a: Platform Admin Application Scaffold
- Story 9.1b: Shared Admin UI Components (chart components)

## Story Points: 3

## Human Validation Gate

**MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
| --------------- | ----------- |
| **Screen Review with Test Data** | Human must validate UI screens with realistic test data loaded |
| **Checklist** | Cost overview, LLM detail (agent type + model), Documents detail, Embeddings detail (by domain), budget config modal |
| **Approval** | Story cannot be marked "done" until human signs off |

---
