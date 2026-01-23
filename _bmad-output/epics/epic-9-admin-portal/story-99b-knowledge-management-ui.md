# Story 9.9b: Knowledge Management UI

As a **Platform Administrator or Agronomist**,
I want to **upload and manage expert knowledge documents through a web interface**,
So that **AI recommendations are powered by verified expert content**.

**Key Insight:** Agronomists shouldn't need to understand PDF extraction methods. The system auto-detects whether a PDF is digital (text-based) or scanned (needs OCR) and handles extraction automatically.

## Acceptance Criteria

**AC 9.9b.1: Knowledge Document Library**

**Given** I navigate to `/knowledge`
**When** the page loads
**Then** I see a library of all knowledge documents
**And** I can filter by domain (Plant Diseases, Tea Cultivation, Weather, Quality Standards, Regional)
**And** I can filter by status (Draft, Staged, Active, Archived)
**And** search is available across document titles and content
**And** documents show title, version, domain, author, status, and last updated date
**And** pagination is available for large document lists

**AC 9.9b.2: Document Upload - Step 1 (File & Metadata)**

**Given** I click "+ Upload Document"
**When** the upload wizard opens
**Then** I can drag & drop or browse for a file (PDF, DOCX, MD, TXT, max 50MB)
**And** I can alternatively write content directly in a rich text editor
**And** I enter metadata: title, domain (select), author, source, region (optional)
**And** I can proceed to Step 2 after file and required metadata are provided

**AC 9.9b.3: Document Upload - Step 2 (Processing & Preview)**

**Given** I uploaded a file and provided metadata
**When** the system processes the document
**Then** I see extraction progress with a real-time progress bar (via SSE EventSource)
**And** I see what extraction method was auto-detected (text vs OCR vs Vision)
**And** when complete, I see the extracted content in a preview panel
**And** I see the confidence score of the extraction
**And** I can edit the extracted content before saving

**AC 9.9b.4: Low Confidence Handling**

**Given** extraction confidence is low (<80%)
**When** the extraction completes
**Then** system shows a quality warning with specific issues (e.g., handwritten notes, low-res images)
**And** offers options: try Vision AI, edit manually, upload clearer scan
**And** I can continue anyway if content is acceptable

**AC 9.9b.5: Document Upload - Step 3 (Save)**

**Given** I have reviewed the extracted content
**When** I proceed to the save step
**Then** I see a summary of the document (title, domain, author, pages, word count, extraction method, confidence)
**And** I choose save status: Draft, Staged (recommended), or Active (requires admin)
**And** the document is saved with the chosen status

**AC 9.9b.6: Document Review & Activation**

**Given** I open a staged document for review
**When** the review screen loads
**Then** I see document info (domain, author, version, created date)
**And** I see a content preview panel
**And** I can "Test with AI" — ask questions and verify retrieval works correctly
**And** I must check approval boxes before activating:
  - "I have reviewed the content for accuracy"
  - "I have tested AI retrieval with sample questions"
  - "I approve this document for production use"
**And** activation moves the document to production namespace

**AC 9.9b.7: Version Management**

**Given** I need to update an active document
**When** I edit and save
**Then** a new version is created (old version archived)
**And** a change summary is required
**And** version history shows all versions with dates, authors, and change summaries
**And** I can view any previous version
**And** I can rollback to a previous version (creates new draft from that version)

## Wireframe: Knowledge Document Library

```
+-----------------------------------------------------------------------------+
|  KNOWLEDGE MANAGEMENT                                  [+ Upload Document]   |
+-----------------------------------------------------------------------------+
|                                                                              |
|  FILTER BY DOMAIN        SEARCH                                              |
|  +------------------+   +------------------------------------------------+  |
|  | [x] All Domains  |   |  Search documents...                           |  |
|  | [ ] Plant Disease|   +------------------------------------------------+  |
|  | [ ] Tea Cultiv.  |                                                        |
|  | [ ] Weather      |   DOCUMENTS                                            |
|  | [ ] Quality Std  |   +------------------------------------------------+  |
|  | [ ] Regional     |   |  Blister Blight Treatment Guide         v2.1   |  |
|  +------------------+   |    Plant Diseases - Dr. Njeri Kamau - Active    |  |
|                         |    Updated: 2025-12-15                 [View]   |  |
|  FILTER BY STATUS       +------------------------------------------------+  |
|  +------------------+   |  Optimal Plucking Techniques            v1.0   |  |
|  | Active       (24)|   |    Tea Cultivation - J. Odhiambo - Staged      |  |
|  | Staged        (3)|   |    Ready for review since: 2025-12-20          |  |
|  | Draft         (5)|   |                             [Review] [Edit]    |  |
|  | Archived      (8)|   +------------------------------------------------+  |
|  +------------------+   |  Weather Pattern Recognition            v3.0   |  |
|                         |    Weather Patterns - TBK - Active              |  |
|                         |    Updated: 2025-11-28                 [View]   |  |
|                         +------------------------------------------------+  |
|                                                                              |
|  Showing 32 documents - Page 1 of 4         [Previous] [Next]               |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Wireframe: Document Upload - Step 1 (File & Metadata)

```
+-----------------------------------------------------------------------------+
|  UPLOAD NEW DOCUMENT                                       Step 1 of 3       |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |                                                                        |  |
|  |                   Drag & drop your file here                           |  |
|  |                        or click to browse                              |  |
|  |                                                                        |  |
|  |                  Supported: PDF, DOCX, MD, TXT                         |  |
|  |                  Max size: 50MB                                         |  |
|  |                                                                        |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  ------------------------------ OR ---------------------------------         |
|                                                                              |
|  [Write content directly] (opens rich text editor)                           |
|                                                                              |
|  -------------------------------------------------------------------         |
|                                                                              |
|  DOCUMENT DETAILS                                                            |
|  +-----------------------------------------------------------------------+  |
|  |  Title:     [                                                      ]  |  |
|  |  Domain:    [Select domain v]                                         |  |
|  |  Author:    [                                                      ]  |  |
|  |  Source:    [e.g., TBK Research Paper, Field Study, etc.           ]  |  |
|  |  Region:    [Select region (optional) v]                              |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  [Cancel]                                                    [Continue]      |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Wireframe: Document Upload - Step 2 (Processing)

```
+-----------------------------------------------------------------------------+
|  PROCESSING DOCUMENT                                       Step 2 of 3       |
+-----------------------------------------------------------------------------+
|                                                                              |
|  blister-blight-treatment-guide.pdf                                          |
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  |                                                                        |  |
|  |  Analyzing document...                                                 |  |
|  |  [====================............................................] 45% |  |
|  |                                                                        |  |
|  |  [ok] Detected: Scanned PDF with embedded images                       |  |
|  |  [ok] Using: Azure Document Intelligence (OCR)                         |  |
|  |  [...] Extracting text from 12 pages...                                |  |
|  |                                                                        |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  This may take 1-2 minutes for large documents                               |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Wireframe: Document Upload - Step 2b (Content Preview)

```
+-----------------------------------------------------------------------------+
|  REVIEW EXTRACTED CONTENT                                  Step 2 of 3       |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Blister Blight Treatment Guide                                              |
|  +-----------------------------------------------------------------------+  |
|  | Extraction: Completed - Confidence: 94% - Pages: 12                   |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  EXTRACTED CONTENT                                              [Edit]       |
|  +-----------------------------------------------------------------------+  |
|  |                                                                        |  |
|  |  # Blister Blight (Exobasidium vexans)                                |  |
|  |                                                                        |  |
|  |  ## Identification                                                     |  |
|  |  Blister blight appears as small, circular, translucent spots on      |  |
|  |  young leaves...                                                       |  |
|  |                                                                        |  |
|  |  ## Environmental Conditions                                           |  |
|  |  - High humidity (>85%)                                                |  |
|  |  - Temperature: 18-22C                                                 |  |
|  |  - Rainfall during plucking season                                     |  |
|  |                                                                        |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  Please verify the extracted content is accurate.                            |
|                                                                              |
|  [Back]     [Re-extract with different method]              [Continue]       |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Wireframe: Low Confidence Warning

```
+-----------------------------------------------------------------------------+
|  EXTRACTION QUALITY WARNING                                                  |
+-----------------------------------------------------------------------------+
|                                                                              |
|  The automatic extraction achieved 62% confidence.                           |
|  Some content may be missing or incorrectly extracted.                        |
|                                                                              |
|  POSSIBLE ISSUES DETECTED:                                                   |
|  - Handwritten notes on pages 3, 7                                           |
|  - Low resolution images/diagrams on pages 5-6                               |
|  - Complex table on page 8                                                   |
|                                                                              |
|  RECOMMENDED ACTIONS:                                                        |
|  +-------------------------------------------------------------------+      |
|  |  [Try Vision AI extraction]                                        |      |
|  |     Best for: diagrams, handwritten notes, complex layouts         |      |
|  |                                                                    |      |
|  |  [Edit extracted content manually]                                 |      |
|  |     Fix specific sections that weren't captured correctly          |      |
|  |                                                                    |      |
|  |  [Upload clearer scan]                                             |      |
|  |     If original document quality is poor                           |      |
|  +-------------------------------------------------------------------+      |
|                                                                              |
|  [Back]                                              [Continue anyway]       |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Wireframe: Document Review & Activation

```
+-----------------------------------------------------------------------------+
|  REVIEW DOCUMENT                                             [Activate v]    |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Blister Blight Treatment Guide                          Status: Staged      |
|  -------------------------------------------------------------------         |
|                                                                              |
|  DOCUMENT INFO              |  TEST WITH AI                                  |
|  +-----------------------+  |  +------------------------------------------+  |
|  | Domain: Plant Disease |  |  | Ask a test question:                     |  |
|  | Author: Dr. N. Kamau  |  |  |                                          |  |
|  | Version: 1.0          |  |  | [What causes blister blight?          ]  |  |
|  | Created: 2025-12-22   |  |  |                                          |  |
|  |                       |  |  | [Test]                                   |  |
|  | Previous versions: 0  |  |  |                                          |  |
|  +-----------------------+  |  | AI Response:                             |  |
|                             |  | "Blister blight is caused by the         |  |
|  CONTENT PREVIEW            |  |  fungus Exobasidium vexans..."            |  |
|  +-----------------------+  |  |                                          |  |
|  | # Blister Blight      |  |  | [ok] Document content retrieved          |  |
|  |                       |  |  |      successfully                        |  |
|  | ## Identification     |  |  +------------------------------------------+  |
|  | Blister blight...     |  |                                                |
|  |                       |  |                                                |
|  | [View full content]   |  |                                                |
|  +-----------------------+  |                                                |
|                             |                                                |
|  -------------------------------------------------------------------         |
|                                                                              |
|  APPROVAL                                                                    |
|  +-----------------------------------------------------------------------+  |
|  |  [ ] I have reviewed the content for accuracy                         |  |
|  |  [ ] I have tested AI retrieval with sample questions                  |  |
|  |  [ ] I approve this document for production use                        |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  [Back to Library]    [Edit]    [Reject]    [Activate for Production]        |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Wireframe: Version History

```
+-----------------------------------------------------------------------------+
|  VERSION HISTORY: Blister Blight Treatment Guide                             |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +-----------------------------------------------------------------------+  |
|  | v2.1 (Active)                                     2025-12-15 10:30    |  |
|  | Updated treatment recommendations per 2025 TBK guidelines             |  |
|  | Author: Dr. Njeri Kamau                                               |  |
|  |                                                   [View] [Rollback]   |  |
|  +-----------------------------------------------------------------------+  |
|  | v2.0 (Archived)                                   2025-09-01 14:22    |  |
|  | Added regional variations section                                     |  |
|  | Author: J. Odhiambo                                                   |  |
|  |                                                   [View] [Compare]    |  |
|  +-----------------------------------------------------------------------+  |
|  | v1.0 (Archived)                                   2025-06-15 09:45    |  |
|  | Initial version                                                       |  |
|  | Author: Dr. Njeri Kamau                                               |  |
|  |                                                   [View] [Compare]    |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
+-----------------------------------------------------------------------------+
```

## Document Lifecycle States

| State | Icon | Description | Who Can Access |
|-------|------|-------------|----------------|
| **Draft** | Draft | Work in progress, not indexed | Author only |
| **Staged** | Staged | Ready for review, test namespace | Reviewers + Admins |
| **Active** | Active | Live in production, used by AI | All AI agents |
| **Archived** | Archived | Deprecated, kept for history | Admins only |

## Technical Notes

- Location: `web/platform-admin/src/pages/knowledge/`
- Consumes BFF REST API from Story 9.9a
- Real-time extraction progress via browser `EventSource` API connecting to SSE endpoint
- File upload via multipart form submission
- Markdown preview for extracted content display
- "Test with AI" uses the `/api/v1/admin/knowledge/query` endpoint

## Dependencies

- Story 9.1: Platform Admin Application Scaffold
- Story 9.9a: Knowledge Management BFF REST API

## Story Points: 5

## Human Validation Gate

**MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
| --------------- | ----------- |
| **Screen Review with Test Data** | Human must validate UI screens with realistic test data loaded |
| **Checklist** | Document library, upload wizard (3 steps), extraction progress bar, content preview, low confidence warning, AI test queries, review & activation flow, version history |
| **Approval** | Story cannot be marked "done" until human signs off |

---
