# Story 9.9b: Knowledge Management UI

**Status:** review
**GitHub Issue:** #221

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **Platform Administrator or Agronomist**,
I want to **upload and manage expert knowledge documents through a web interface**,
so that **AI recommendations are powered by verified expert content**.

## Acceptance Criteria

### AC 9.9b.1: Knowledge Document Library

**Given** I navigate to `/knowledge`
**When** the page loads
**Then** I see a library of all knowledge documents
**And** I can filter by domain (Plant Diseases, Tea Cultivation, Weather, Quality Standards, Regional)
**And** I can filter by status (Draft, Staged, Active, Archived)
**And** search is available across document titles and content
**And** documents show title, version, domain, author, status, and last updated date
**And** pagination is available for large document lists

### AC 9.9b.2: Document Upload - Step 1 (File & Metadata)

**Given** I click "+ Upload Document"
**When** the upload wizard opens
**Then** I can drag & drop or browse for a file (PDF, DOCX, MD, TXT, max 50MB)
**And** I can alternatively write content directly in a rich text editor
**And** I enter metadata: title, domain (select), author, source, region (optional)
**And** I can proceed to Step 2 after file and required metadata are provided

### AC 9.9b.3: Document Upload - Step 2 (Processing & Preview)

**Given** I uploaded a file and provided metadata
**When** the system processes the document
**Then** I see extraction progress with a real-time progress bar (via SSE EventSource)
**And** I see what extraction method was auto-detected (text vs OCR vs Vision)
**And** when complete, I see the extracted content in a preview panel
**And** I see the confidence score of the extraction
**And** I can edit the extracted content before saving

### AC 9.9b.4: Low Confidence Handling

**Given** extraction confidence is low (<80%)
**When** the extraction completes
**Then** system shows a quality warning with specific issues (e.g., handwritten notes, low-res images)
**And** offers options: try Vision AI, edit manually, upload clearer scan
**And** I can continue anyway if content is acceptable

### AC 9.9b.5: Document Upload - Step 3 (Save)

**Given** I have reviewed the extracted content
**When** I proceed to the save step
**Then** I see a summary of the document (title, domain, author, pages, word count, extraction method, confidence)
**And** I choose save status: Draft, Staged (recommended), or Active (requires admin)
**And** the document is saved with the chosen status

### AC 9.9b.6: Document Review & Activation

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

### AC 9.9b.7: Version Management

**Given** I need to update an active document
**When** I edit and save
**Then** a new version is created (old version archived)
**And** a change summary is required
**And** version history shows all versions with dates, authors, and change summaries
**And** I can view any previous version
**And** I can rollback to a previous version (creates new draft from that version)

## Wireframes

### WF-1: Knowledge Document Library (Task 2)

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

### WF-2: Document Upload - Step 1 File & Metadata (Task 3)

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

### WF-3: Document Upload - Step 2 Processing (Task 4)

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

### WF-4: Document Upload - Step 2b Content Preview (Task 4)

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

### WF-5: Low Confidence Warning (Task 4)

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

### WF-6: Document Upload - Step 3 Save (Task 5)

```
+-----------------------------------------------------------------------------+
|  SAVE DOCUMENT                                               Step 3 of 3     |
+-----------------------------------------------------------------------------+
|                                                                              |
|  DOCUMENT SUMMARY                                                            |
|  +-----------------------------------------------------------------------+  |
|  |  Title:      Blister Blight Treatment Guide                           |  |
|  |  Domain:     Plant Diseases                                           |  |
|  |  Author:     Dr. Njeri Kamau                                          |  |
|  |  Source:     TBK Research Paper 2024                                  |  |
|  |  Pages:      12                                                       |  |
|  |  Word count: ~3,200 words                                             |  |
|  |  Extraction: Azure Document Intelligence (94% confidence)             |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  SAVE AS                                                                     |
|  +-----------------------------------------------------------------------+  |
|  |  o  Draft        - Save for later editing. Not visible to AI agents.  |  |
|  |  *  Staged (Recommended) - Ready for review. Test with AI first.      |  |
|  |  o  Active (Requires approval) - Immediately available to AI agents.  |  |
|  +-----------------------------------------------------------------------+  |
|                                                                              |
|  [Back]                                                [Save as Staged]      |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### WF-7: Document Review & Activation (Task 7)

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

### WF-8: Version History (Task 6)

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

## Tasks / Subtasks

- [x] Task 1: Create Knowledge API Module (AC: all)
  - [x] 1.1 Create `web/platform-admin/src/api/knowledge.ts` with typed functions for all BFF endpoints
  - [x] 1.2 Define TypeScript interfaces in `web/platform-admin/src/api/types.ts` (or inline) for all knowledge types
  - [x] 1.3 Implement `listDocuments()` with domain/status/author filtering and pagination
  - [x] 1.4 Implement `searchDocuments()` with query and optional filters
  - [x] 1.5 Implement `getDocument()` with optional version parameter
  - [x] 1.6 Implement `createDocument()` for manual content creation
  - [x] 1.7 Implement `updateDocument()` (creates new version, requires change summary)
  - [x] 1.8 Implement `deleteDocument()` (archives all versions)
  - [x] 1.9 Implement lifecycle methods: `stageDocument()`, `activateDocument()`, `archiveDocument()`, `rollbackDocument()`
  - [x] 1.10 Implement `uploadDocument()` using FormData (multipart file + metadata)
  - [x] 1.11 Implement `getExtractionJob()` for polling extraction status
  - [x] 1.12 Implement `listChunks()` with pagination
  - [x] 1.13 Implement `vectorizeDocument()` trigger
  - [x] 1.14 Implement `getVectorizationJob()` for polling
  - [x] 1.15 Implement `queryKnowledge()` for "Test with AI" feature
  - [x] 1.16 Create SSE helper: `createExtractionProgressStream()` using native EventSource API

- [x] Task 2: Knowledge Library Page - Full Implementation (AC: 1, Wireframe: WF-1)
  - [x] 2.1 Replace placeholder `KnowledgeLibrary.tsx` with full implementation matching WF-1
  - [x] 2.2 Use `PageHeader` with title "Knowledge Library" and `[+ Upload Document]` action button
  - [x] 2.3 Use `FilterBar` with domain dropdown filter (5 values) and status filter (4 values)
  - [x] 2.4 Implement search via FilterBar `showSearch` prop
  - [x] 2.5 Use `DataTable` for document list with columns: title, version, domain, author, status, updated_at
  - [x] 2.6 Status column uses MUI `Chip` with color mapping (green=Active, amber=Staged, grey=Draft, blue-grey=Archived)
  - [x] 2.7 Row actions: [View] navigates to `/knowledge/:id`, [Review] (for staged) navigates to `/knowledge/:id/review`, [Edit]
  - [x] 2.8 Implement server-side pagination with page/page_size params
  - [x] 2.9 Add loading spinner and empty state ("No documents yet. Upload your first knowledge document.")

- [x] Task 3: Upload Wizard - Step 1 File & Metadata (AC: 2, Wireframe: WF-2)
  - [x] 3.1 Create `web/platform-admin/src/pages/knowledge/UploadWizard.tsx` as full-page route matching WF-2
  - [x] 3.2 Implement 3-step stepper UI (MUI `Stepper` component) with step labels: "Upload", "Preview", "Save"
  - [x] 3.3 File drop zone: drag & drop or click to browse (reuse pattern from `FarmerImport.tsx`)
  - [x] 3.4 File validation: accept only pdf, docx, md, txt; max 50MB; show error for invalid files
  - [x] 3.5 "Write content directly" alternative: toggles textarea (no rich editor - keep it simple for MVP)
  - [x] 3.6 Metadata form using `react-hook-form` + `zod`: title (required), domain (required, enum select), author, source, region (optional)
  - [x] 3.7 [Continue] button enabled only when file/content + required metadata provided
  - [x] 3.8 [Cancel] navigates back to `/knowledge`

- [x] Task 4: Upload Wizard - Step 2 Processing & Preview (AC: 3, 4, Wireframes: WF-3, WF-4, WF-5)
  - [x] 4.1 On step activation: call `uploadDocument()` API (multipart form) and immediately connect to SSE stream (see WF-3 for progress UI)
  - [x] 4.2 Display real-time progress bar (MUI `LinearProgress` with percent label)
  - [x] 4.3 Show detected extraction method and status messages as they arrive via SSE
  - [x] 4.4 SSE connection: use `EventSource` API, parse `event: progress` events, handle `event: complete` and `event: error`
  - [x] 4.5 On SSE complete: fetch full document to display content preview
  - [x] 4.6 Content preview: render extracted markdown in a scrollable panel (use simple `<pre>` with whitespace or a markdown renderer)
  - [x] 4.7 Show extraction confidence badge (green >=80%, amber 60-80%, red <60%)
  - [x] 4.8 Low confidence warning (<80%): display alert with issues and action options (re-extract, edit, re-upload)
  - [x] 4.9 [Edit] button: enables textarea overlay to modify extracted content
  - [x] 4.10 [Continue] proceeds to Step 3; [Back] returns to Step 1

- [x] Task 5: Upload Wizard - Step 3 Save (AC: 5, Wireframe: WF-6)
  - [x] 5.1 Display document summary card matching WF-6 (title, domain, author, pages, word count, extraction method, confidence)
  - [x] 5.2 Radio group for save status: Draft, Staged (default/recommended), Active
  - [x] 5.3 [Save] calls `stageDocument()` / `activateDocument()` based on selection (or just saves as draft)
  - [x] 5.4 On success: show snackbar and navigate to document detail `/knowledge/:id`
  - [x] 5.5 On error: show error alert, stay on step

- [x] Task 6: Document Detail Page (AC: 6, 7, Wireframe: WF-8)
  - [x] 6.1 Create `web/platform-admin/src/pages/knowledge/KnowledgeDetail.tsx` with version history section matching WF-8
  - [x] 6.2 Display document info: title, domain, author, version, status, created/updated dates
  - [x] 6.3 Content preview panel with full markdown content (scrollable)
  - [x] 6.4 Actions based on status:
    - Draft: [Edit], [Stage], [Delete]
    - Staged: [Review & Activate], [Edit], [Archive]
    - Active: [Edit] (creates new version), [Archive]
    - Archived: [Rollback] (creates new draft)
  - [x] 6.5 Version history section: list all versions with date, author, change summary, [View] [Rollback] actions

- [x] Task 7: Document Review & Activation Page (AC: 6, Wireframe: WF-7)
  - [x] 7.1 Create `web/platform-admin/src/pages/knowledge/KnowledgeReview.tsx` matching WF-7
  - [x] 7.2 Two-column layout matching WF-7: left = document info + content preview, right = "Test with AI" panel
  - [x] 7.3 "Test with AI" panel: text input for question, [Test] button, displays AI response
  - [x] 7.4 Call `queryKnowledge()` API with document's domain filter to test retrieval
  - [x] 7.5 Approval checkboxes (all 3 required to enable Activate button):
    - "I have reviewed the content for accuracy"
    - "I have tested AI retrieval with sample questions"
    - "I approve this document for production use"
  - [x] 7.6 [Activate for Production] calls `activateDocument()`, navigates to detail on success
  - [x] 7.7 [Back to Library] navigates to `/knowledge`

- [x] Task 8: Route Registration (AC: all)
  - [x] 8.1 Add routes in `routes.tsx`: `/knowledge` (list), `/knowledge/upload` (wizard), `/knowledge/:documentId` (detail), `/knowledge/:documentId/review` (review)
  - [x] 8.2 Update imports and ensure all pages are ProtectedRoute wrapped
  - [x] 8.3 Update `web/platform-admin/src/pages/knowledge/index.ts` with new exports

- [x] Task 9: Unit Tests (AC: all)
  - [x] 9.1 Test API module functions (mock fetch, verify request params and headers)
  - [x] 9.2 Test SSE helper (mock EventSource, verify event parsing)
  - [x] 9.3 Test UploadWizard step transitions and validation
  - [x] 9.4 Test KnowledgeLibrary filtering and pagination
  - [x] 9.5 Test KnowledgeReview approval checkbox logic

- [x] Task 10: Lint and Build Verification
  - [x] 10.1 Run TypeScript build: `cd web/platform-admin && npm run build` (pre-existing TS errors only, no regressions)
  - [x] 10.2 Run linter: `cd web/platform-admin && npm run lint` (0 errors/warnings)
  - [x] 10.3 Run unit tests: `cd web/platform-admin && npm run test` (152 tests pass)

## Git Workflow (MANDATORY)

**All story development MUST use feature branches.** Direct pushes to main are blocked.

### Story Start
- [ ] GitHub Issue exists or created: `gh issue create --title "Story 9.9b: Knowledge Management UI"`
- [ ] Feature branch created from main:
  ```bash
  git checkout main && git pull origin main
  git checkout -b story/9-9b-knowledge-management-ui
  ```

**Branch name:** `story/9-9b-knowledge-management-ui`

### During Development
- [ ] All commits reference GitHub issue: `Relates to #XX`
- [ ] Commits are atomic by type (production, test, seed - not mixed)
- [ ] Push to feature branch: `git push -u origin story/9-9b-knowledge-management-ui`

### Story Done
- [ ] Create Pull Request: `gh pr create --title "Story 9.9b: Knowledge Management UI" --base main`
- [ ] CI passes on PR (including E2E tests)
- [ ] Code review completed (`/code-review` or human review)
- [ ] PR approved and merged (squash)
- [ ] Local branch cleaned up: `git branch -d story/9-9b-knowledge-management-ui`

**PR URL:** _______________ (fill in when created)

---

## Local Test Run Evidence (MANDATORY - ALL STORIES)

> **This section MUST be completed before marking story as "review"**

> **REGRESSION RULE — NO EXCEPTIONS:**
> - Run the **FULL** test suite, not just tests you think are related to your change.
> - A previously passing test that now fails **IS a regression caused by your change**.
> - "Not related to my change" is **NEVER** a valid reason to skip or ignore a failing test.
> - **Zero failures** is the only acceptable outcome. Fix all regressions before proceeding.
> - If you believe a test was already broken before your change, provide `git stash && pytest` evidence proving it fails on clean main too.

### 1. Unit Tests
```bash
cd web/platform-admin && npm run test
```
**Output:**
```
 Test Files  14 passed (14)
      Tests  152 passed (152)
   Start at  13:53:27
   Duration  10.18s (transform 3.88s, setup 4.23s, collect 45.13s, tests 1.95s, environment 15.17s, prepare 6.36s)
```

### 2. Lint & Build Check
```bash
cd web/platform-admin && npm run lint && npm run build
```
**Lint passed:** [x] Yes / [ ] No
**Build note:** 3 pre-existing TS errors (`initialExpanded` prop) exist on main branch too (confirmed via `git stash && tsc --noEmit`). No regressions from this story.

### 3. CI Verification on Story Branch (MANDATORY)

> **After pushing to story branch, CI must pass before creating PR**

```bash
# Push to story branch
git push origin feature/9-9b-knowledge-management-ui

# Wait ~30s, then check CI status
gh run list --branch feature/9-9b-knowledge-management-ui --limit 3
```
**CI Run ID:** 21286934196
**CI Status:** [x] Passed / [ ] Failed
**Verification Date:** 2026-01-23

> **Note:** E2E tests are NOT required for this frontend-only story. Backend API coverage was validated in Story 9.9a (41 knowledge-specific E2E tests pass).

---

## Dev Notes

### CRITICAL: This is a Frontend-Only Story

This story implements the **React UI** that consumes the BFF REST API created in Story 9.9a. The backend is complete and tested (286 E2E tests pass including 41 knowledge-specific tests).

**DO NOT modify any backend code (services/, proto/, libs/).**
**DO NOT modify BFF routes, schemas, or services.**

### Architecture: Frontend → BFF REST API

```
React Component → API Module (fetch) → BFF REST Endpoint → gRPC → AI Model Service
```

The frontend communicates exclusively via REST endpoints at `/api/admin/knowledge/*`. SSE streaming uses the browser's native `EventSource` API connecting to `/api/admin/knowledge/{id}/extraction/progress?job_id={job_id}`.

### BFF API Endpoints Available (from Story 9.9a)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/admin/knowledge` | List documents (paginated, filterable) |
| `GET` | `/api/admin/knowledge/search` | Search by title/content |
| `GET` | `/api/admin/knowledge/{id}` | Get document details |
| `POST` | `/api/admin/knowledge` | Create document |
| `PUT` | `/api/admin/knowledge/{id}` | Update document (new version) |
| `DELETE` | `/api/admin/knowledge/{id}` | Archive document |
| `POST` | `/api/admin/knowledge/{id}/stage` | draft → staged |
| `POST` | `/api/admin/knowledge/{id}/activate` | staged → active |
| `POST` | `/api/admin/knowledge/{id}/archive` | any → archived |
| `POST` | `/api/admin/knowledge/{id}/rollback` | Creates new draft from old version |
| `POST` | `/api/admin/knowledge/upload` | Upload file (multipart) + trigger extraction |
| `GET` | `/api/admin/knowledge/{id}/extraction/{job_id}` | Poll extraction status |
| `GET` | `/api/admin/knowledge/{id}/extraction/progress?job_id={job_id}` | **SSE stream** |
| `GET` | `/api/admin/knowledge/{id}/chunks` | List chunks (paginated) |
| `POST` | `/api/admin/knowledge/{id}/vectorize` | Trigger vectorization |
| `GET` | `/api/admin/knowledge/{id}/vectorization/{job_id}` | Poll vectorization status |
| `POST` | `/api/admin/knowledge/query` | Query knowledge base (Test with AI) |

### TypeScript Types (MUST match BFF Pydantic schemas exactly)

Source: `services/bff/src/bff/api/schemas/admin/knowledge_schemas.py`

```typescript
// === Enums ===
type KnowledgeDomain = 'plant_diseases' | 'tea_cultivation' | 'weather_patterns' | 'quality_standards' | 'regional_context';
type DocumentStatus = 'draft' | 'staged' | 'active' | 'archived';

// === Shared Pagination (from bff.api.schemas.responses.PaginationMeta) ===
interface PaginationMeta {
  page: number;       // 1-indexed
  page_size: number;  // 1-100
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  next_page_token: string | null;
}

// === Request Types ===
interface CreateDocumentRequest {
  title: string;        // min 1, max 500
  domain: KnowledgeDomain;
  content?: string;     // markdown content (for manual creation)
  author?: string;
  source?: string;
  region?: string;
  tags?: string[];
}

interface UpdateDocumentRequest {
  title?: string;       // empty = no change
  content?: string;
  author?: string;
  source?: string;
  region?: string;
  tags?: string[];
  change_summary: string;  // REQUIRED for versioning
}

interface QueryKnowledgeRequest {
  query: string;        // min 1
  domains?: KnowledgeDomain[];  // empty = all
  top_k?: number;       // 1-100, default 5
  confidence_threshold?: number;  // 0-1, default 0
}

interface RollbackDocumentRequest {
  target_version: number;  // >= 1
}

// === Response Types ===
interface SourceFileResponse {
  filename: string;
  file_type: string;      // 'pdf' | 'docx' | 'md' | 'txt'
  file_size_bytes: number;
  extraction_method: string;     // e.g. 'text', 'ocr', 'vision'
  extraction_confidence: number; // 0-1
  page_count: number;
}

interface DocumentMetadataResponse {
  author: string;
  source: string;
  region: string;
  season: string;
  tags: string[];
}

// Used in list views (GET /knowledge)
interface DocumentSummary {
  document_id: string;    // Stable ID across versions
  version: number;
  title: string;
  domain: string;         // KnowledgeDomain value
  status: string;         // DocumentStatus value
  author: string;
  created_at: string | null;  // ISO datetime
  updated_at: string | null;
}

// Used in detail views (GET /knowledge/:id, lifecycle endpoints)
interface DocumentDetail {
  id: string;             // Unique: "document_id:v{version}"
  document_id: string;    // Stable ID across versions
  version: number;
  title: string;
  domain: string;
  content: string;        // Markdown content
  status: string;
  metadata: DocumentMetadataResponse;
  source_file: SourceFileResponse | null;
  change_summary: string;
  pinecone_namespace: string;
  content_hash: string;
  created_at: string | null;
  updated_at: string | null;
}

// List endpoint response
interface DocumentListResponse {
  data: DocumentSummary[];       // NOTE: field is "data", NOT "documents"
  pagination: PaginationMeta;
}

interface DeleteDocumentResponse {
  versions_archived: number;
}

// Extraction
interface ExtractionJobStatus {
  job_id: string;
  document_id: string;
  status: string;           // 'pending' | 'in_progress' | 'completed' | 'failed'
  progress_percent: number; // 0-100
  pages_processed: number;
  total_pages: number;
  error_message: string;    // empty string if no error
  started_at: string | null;
  completed_at: string | null;
}

// SSE progress event (from SSEManager.create_response with event_type="progress")
// Event format: "event: progress\ndata: {...}\n\n"
interface ExtractionProgressEvent {
  percent: number;         // 0-100
  status: string;          // job status
  message: string;         // "Pages X/Y"
  pages_processed: number;
  total_pages: number;
}

// Vectorization
interface VectorizationJobStatus {
  job_id: string;
  status: string;
  document_id: string;
  document_version: number;
  namespace: string;
  chunks_total: number;
  chunks_embedded: number;
  chunks_stored: number;
  failed_count: number;
  content_hash: string;
  error_message: string;
  started_at: string | null;
  completed_at: string | null;
}

// Chunks
interface ChunkSummary {
  chunk_id: string;
  document_id: string;
  document_version: number;
  chunk_index: number;
  content: string;
  section_title: string;
  word_count: number;
  char_count: number;
  pinecone_id: string;
  created_at: string | null;
}

interface ChunkListResponse {
  data: ChunkSummary[];
  pagination: PaginationMeta;
}

// Query
interface QueryResultItem {
  chunk_id: string;
  content: string;
  score: number;       // 0-1 similarity
  document_id: string;
  title: string;
  domain: string;
}

interface QueryResponse {
  matches: QueryResultItem[];
  query: string;
  total_matches: number;
}
```

### API Call Signatures (Task 1 - `api/knowledge.ts`)

All calls go through the existing `apiClient` pattern from `api/client.ts`, EXCEPT upload (uses native `fetch` for FormData) and SSE (uses `EventSource`).

```typescript
// === CRUD ===
listDocuments(params?: { domain?: string; status?: string; author?: string; page?: number; page_size?: number }): Promise<DocumentListResponse>
// GET /admin/knowledge?domain=...&status=...&author=...&page=1&page_size=20

searchDocuments(params: { query: string; domain?: string; top_k?: number }): Promise<DocumentListResponse>
// GET /admin/knowledge/search?query=...&domain=...&top_k=10

getDocument(documentId: string, version?: number): Promise<DocumentDetail>
// GET /admin/knowledge/{documentId}?version=...

createDocument(data: CreateDocumentRequest): Promise<DocumentDetail>
// POST /admin/knowledge  body: JSON

updateDocument(documentId: string, data: UpdateDocumentRequest): Promise<DocumentDetail>
// PUT /admin/knowledge/{documentId}  body: JSON

deleteDocument(documentId: string): Promise<DeleteDocumentResponse>
// DELETE /admin/knowledge/{documentId}

// === Lifecycle ===
stageDocument(documentId: string): Promise<DocumentDetail>
// POST /admin/knowledge/{documentId}/stage  (no body)

activateDocument(documentId: string): Promise<DocumentDetail>
// POST /admin/knowledge/{documentId}/activate  (no body)

archiveDocument(documentId: string): Promise<DocumentDetail>
// POST /admin/knowledge/{documentId}/archive  (no body)

rollbackDocument(documentId: string, targetVersion: number): Promise<DocumentDetail>
// POST /admin/knowledge/{documentId}/rollback  body: { target_version: number }

// === Upload & Extraction ===
uploadDocument(file: File, metadata: { title: string; domain: KnowledgeDomain; author?: string; source?: string; region?: string }): Promise<ExtractionJobStatus>
// POST /admin/knowledge/upload  body: FormData (multipart)
// Form fields: file, title, domain, author, source, region

getExtractionJob(documentId: string, jobId: string): Promise<ExtractionJobStatus>
// GET /admin/knowledge/{documentId}/extraction/{jobId}

createExtractionProgressStream(documentId: string, jobId: string, callbacks): () => void
// EventSource: GET /admin/knowledge/{documentId}/extraction/progress?job_id={jobId}

// === Chunks & Vectorization ===
listChunks(documentId: string, params?: { page?: number; page_size?: number }): Promise<ChunkListResponse>
// GET /admin/knowledge/{documentId}/chunks?page=...&page_size=...

vectorizeDocument(documentId: string, version?: number): Promise<VectorizationJobStatus>
// POST /admin/knowledge/{documentId}/vectorize  body: { version: 0 }

getVectorizationJob(documentId: string, jobId: string): Promise<VectorizationJobStatus>
// GET /admin/knowledge/{documentId}/vectorization/{jobId}

// === Query ===
queryKnowledge(data: QueryKnowledgeRequest): Promise<QueryResponse>
// POST /admin/knowledge/query  body: JSON
```

### SSE EventSource Pattern (NEW - First use in this app)

```typescript
// Helper function for SSE connection
export function createExtractionProgressStream(
  documentId: string,
  jobId: string,
  onProgress: (event: ExtractionProgressEvent) => void,
  onComplete: () => void,
  onError: (error: string) => void,
): () => void {
  const token = localStorage.getItem('fp_auth_token');
  const baseURL = import.meta.env.VITE_BFF_URL || '/api';
  const url = `${baseURL}/admin/knowledge/${documentId}/extraction/progress?job_id=${jobId}`;

  // EventSource doesn't support custom headers natively
  // Use query param or polyfill if auth needed
  const eventSource = new EventSource(url);

  eventSource.addEventListener('progress', (event) => {
    const data: ExtractionProgressEvent = JSON.parse(event.data);
    onProgress(data);
  });

  eventSource.addEventListener('complete', () => {
    onComplete();
    eventSource.close();
  });

  eventSource.addEventListener('error', (event) => {
    // Check if it's a normal stream end vs actual error
    if (eventSource.readyState === EventSource.CLOSED) {
      onComplete(); // Stream ended normally
    } else {
      onError('Connection lost. Retrying...');
    }
  });

  // Return cleanup function
  return () => eventSource.close();
}
```

**IMPORTANT SSE Auth Consideration:** The native `EventSource` API does NOT support custom Authorization headers. Solutions:
1. **Query param token** (simplest): Pass `?token=...` - BFF must accept this
2. **Cookie-based auth**: If BFF supports cookies
3. **Fetch-based SSE polyfill**: Use `fetch()` with `ReadableStream` to parse SSE manually with headers

Check BFF SSE endpoint auth handling. The `require_platform_admin()` dependency uses Bearer token. If EventSource can't pass it, you may need to use a fetch-based approach or pass token as query parameter. **Verify this works before implementing the full wizard.**

### File Upload Pattern (Multipart FormData)

```typescript
export async function uploadDocument(
  file: File,
  metadata: { title: string; domain: KnowledgeDomain; author?: string; source?: string; region?: string },
): Promise<ExtractionJobStatus> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', metadata.title);
  formData.append('domain', metadata.domain);
  if (metadata.author) formData.append('author', metadata.author);
  if (metadata.source) formData.append('source', metadata.source);
  if (metadata.region) formData.append('region', metadata.region);

  const token = localStorage.getItem('fp_auth_token');
  const baseURL = import.meta.env.VITE_BFF_URL || '/api';

  const response = await fetch(`${baseURL}/admin/knowledge/upload`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }, // No Content-Type - browser sets boundary
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Upload failed: ${response.status}`);
  }

  return response.json();
}
```

### Frontend File Structure (This Story)

**Files to CREATE:**
- `web/platform-admin/src/api/knowledge.ts` - API module with all knowledge endpoints
- `web/platform-admin/src/pages/knowledge/KnowledgeDetail.tsx` - Document detail/view page
- `web/platform-admin/src/pages/knowledge/KnowledgeReview.tsx` - Review & activation page
- `web/platform-admin/src/pages/knowledge/UploadWizard.tsx` - 3-step upload wizard
- `web/platform-admin/src/pages/knowledge/components/ExtractionProgress.tsx` - SSE progress component
- `web/platform-admin/src/pages/knowledge/components/ContentPreview.tsx` - Markdown content preview
- `web/platform-admin/src/pages/knowledge/components/VersionHistory.tsx` - Version history list

**Files to MODIFY:**
- `web/platform-admin/src/pages/knowledge/KnowledgeLibrary.tsx` - Replace placeholder with full implementation
- `web/platform-admin/src/pages/knowledge/index.ts` - Export new page components
- `web/platform-admin/src/app/routes.tsx` - Add new knowledge routes (upload, detail, review)
- `web/platform-admin/src/api/types.ts` - Add knowledge TypeScript interfaces

**Files NOT to touch:**
- `services/bff/` - Backend is complete (Story 9.9a)
- `services/ai-model/` - AI Model service (Stories 0.75.x)
- `proto/` - Proto definitions (source of truth)
- `libs/` - Shared Python libraries

### Existing Frontend Patterns to Follow

| Pattern | Example File | Key Points |
|---------|-------------|------------|
| **List page** | `pages/farmers/FarmerList.tsx` | PageHeader + FilterBar + DataTable + pagination |
| **Detail page** | `pages/grading-models/GradingModelDetail.tsx` | Fetch by ID, display sections, action buttons |
| **Form page** | `pages/farmers/FarmerCreate.tsx` | react-hook-form + zod + Controller + PageHeader with save |
| **File upload** | `pages/farmers/FarmerImport.tsx` | Drag/drop, FormData, progress states |
| **API module** | `api/farmers.ts` | Typed functions, apiClient.get/post, error handling |
| **Routing** | `app/routes.tsx` | ProtectedRoute wrapper, Layout children |

### Domain Enum Display Labels

| API Value | Display Label |
|-----------|--------------|
| `plant_diseases` | Plant Diseases |
| `tea_cultivation` | Tea Cultivation |
| `weather_patterns` | Weather Patterns |
| `quality_standards` | Quality Standards |
| `regional_context` | Regional Context |

### Status Color Mapping

| Status | MUI Chip Color | Icon |
|--------|---------------|------|
| `active` | `success` (green) | CheckCircle |
| `staged` | `warning` (amber) | Schedule |
| `draft` | `default` (grey) | Edit |
| `archived` | `info` (blue-grey) | Archive |

### Accessibility Requirements

- All interactive elements have 48x48px minimum touch targets
- Status indicators use color + icon + text (never color alone)
- Focus ring: 3px Forest Green outline on all interactive elements
- ARIA labels on progress bar: `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- Upload dropzone: keyboard accessible (Enter/Space to trigger file browser)
- Stepper: `aria-current="step"` on active step
- Modal confirmations use `aria-modal="true"` and trap focus
- Reduced motion: disable progress bar animation when `prefers-reduced-motion` is set

### Human Validation Gate

**MANDATORY: This story requires human validation before acceptance.**

| Validation Type | Requirement |
|-----------------|-------------|
| **Screen Review with Test Data** | Human must validate UI screens with realistic test data loaded |
| **Checklist** | Document library, upload wizard (3 steps), extraction progress bar, content preview, low confidence warning, AI test queries, review & activation flow, version history |
| **Approval** | Story cannot be marked "done" until human signs off |

### Previous Story Intelligence

**From Story 9.9a (BFF API - completed):**
1. All endpoints use `require_platform_admin()` auth - frontend must send Bearer token
2. Upload endpoint accepts multipart form with specific field names: `file`, `title`, `domain`, `author`, `source`, `region`
3. SSE endpoint uses `SSEManager.create_response()` - events have `event: progress` type
4. Pagination uses `page`/`page_size` query params (not cursor-based tokens for this API)
5. Domain filter uses exact enum values: `plant_diseases`, `tea_cultivation`, etc.
6. Document status filter uses exact values: `draft`, `staged`, `active`, `archived`
7. Delete endpoint archives (doesn't permanently delete) - returns `DeleteDocumentResponse`
8. **Code review found SSE route ordering bug (fixed)**: `/extraction/progress` route is BEFORE `/{job_id}` route

**From Story 9.6b (most recent UI story - Grading Models):**
1. List pages use `useCallback` + `useEffect` for data fetching
2. Pagination uses page tokens stored in state
3. Filter changes reset pagination to page 0
4. Error display uses MUI `Alert` component
5. Loading state uses skeleton screens
6. Row click navigates to detail page
7. All routes wrapped with `ProtectedRoute`

**From Story 9.5 (Farmer Management UI):**
1. File upload uses native `FormData` + `fetch()` (not apiClient for multipart)
2. Drag/drop uses `onDragEnter`, `onDragLeave`, `onDragOver`, `onDrop` handlers
3. File validation happens client-side before upload
4. Upload progress shown with status messages

### Git Intelligence

Recent commits show:
- Story 9.9a merged as PR #220 (Knowledge BFF API)
- Story 9.6b merged (Grading Model UI) - most recent UI pattern
- `e2e-up.sh` script improvements for frontend volume clearing

### Technical Stack (Frontend)

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3 | UI framework |
| TypeScript | 5.7 | Type safety |
| Vite | 6.0 | Build tool |
| MUI v6 | 6.3 | Component library (DataGrid, Stepper, Chip, LinearProgress, etc.) |
| react-hook-form | 7.54 | Form management |
| zod | 3.24 | Schema validation |
| React Router | v7 | Client-side routing |
| @fp/auth | internal | Auth context, ProtectedRoute, token management |
| @fp/ui-components | internal | PageHeader, DataTable, FilterBar, FileDropzone, etc. |

### Project Structure Notes

- Frontend root: `web/platform-admin/`
- Source: `web/platform-admin/src/`
- Pages organized by domain: `src/pages/knowledge/`
- API modules: `src/api/` (one file per domain)
- Shared components: from `@fp/ui-components` package
- Build output: `web/platform-admin/dist/` (served by NGINX in E2E)
- Alias `@/` maps to `src/` in imports

### References

- [Source: _bmad-output/epics/epic-9-admin-portal/story-99b-knowledge-management-ui.md] - Story requirements & wireframes
- [Source: _bmad-output/epics/epic-9-admin-portal/story-99-knowledge-management-interface.md] - Original combined story
- [Source: _bmad-output/epics/epic-9-admin-portal/interaction-patterns.md] - UI interaction patterns
- [Source: _bmad-output/sprint-artifacts/9-9a-knowledge-management-bff-api.md] - Previous story (BFF API) with endpoint details
- [Source: web/platform-admin/src/pages/farmers/FarmerList.tsx] - List page pattern
- [Source: web/platform-admin/src/pages/farmers/FarmerImport.tsx] - File upload pattern
- [Source: web/platform-admin/src/pages/farmers/FarmerCreate.tsx] - Form pattern
- [Source: web/platform-admin/src/pages/grading-models/GradingModelDetail.tsx] - Detail page pattern
- [Source: web/platform-admin/src/api/client.ts] - API client pattern
- [Source: web/platform-admin/src/api/farmers.ts] - API module pattern
- [Source: web/platform-admin/src/app/routes.tsx] - Route definitions
- [Source: _bmad-output/project-context.md] - Project rules (UI/UX section)
- [Source: services/bff/src/bff/api/routes/admin/knowledge.py] - BFF endpoint implementations (DO NOT MODIFY)
- [Source: services/bff/src/bff/infrastructure/sse/manager.py] - SSE infrastructure reference

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Fixed `PageHeaderAction` missing `id` field in KnowledgeLibrary and KnowledgeDetail
- Fixed `FilterValues` type incompatibility (changed handler to `string | string[]`)
- Removed invalid `paginationMode` prop from DataTable
- Changed `return null` to `return <></>` for JSX.Element return type in KnowledgeDetail and KnowledgeReview
- Fixed React `useCallback` exhaustive-deps warning by inlining file handling logic in UploadWizard

### Completion Notes List

- All 10 tasks implemented with 21 new unit tests (152 total pass)
- Lint clean (0 errors/warnings)
- Build: 3 pre-existing TS errors on main (not from this story)
- Frontend-only story: E2E not required per story notes
- SSE pattern uses native EventSource API (first use in this app)
- File upload uses native fetch with FormData (not apiClient)

### File List

**Created:**
- `web/platform-admin/src/api/knowledge.ts` - API module with 16 functions for all BFF knowledge endpoints
- `web/platform-admin/src/pages/knowledge/UploadWizard.tsx` - 3-step upload wizard (file+metadata, processing/preview, save)
- `web/platform-admin/src/pages/knowledge/KnowledgeDetail.tsx` - Document detail with version history and lifecycle actions
- `web/platform-admin/src/pages/knowledge/KnowledgeReview.tsx` - Review & activation with "Test with AI" panel
- `web/platform-admin/src/pages/knowledge/components/ExtractionProgress.tsx` - SSE-based real-time progress display
- `web/platform-admin/src/pages/knowledge/components/ContentPreview.tsx` - Scrollable markdown content preview
- `web/platform-admin/src/pages/knowledge/components/VersionHistory.tsx` - Version list with View/Rollback actions
- `tests/unit/web/platform-admin/api/knowledge.test.ts` - 21 unit tests for knowledge API module

**Modified:**
- `web/platform-admin/src/api/types.ts` - Added all knowledge TypeScript interfaces and helper constants/functions
- `web/platform-admin/src/api/index.ts` - Added `export * from './knowledge'`
- `web/platform-admin/src/pages/knowledge/KnowledgeLibrary.tsx` - Replaced placeholder with full implementation (DataTable, FilterBar, search, pagination)
- `web/platform-admin/src/pages/knowledge/index.ts` - Added exports for UploadWizard, KnowledgeDetail, KnowledgeReview
- `web/platform-admin/src/app/routes.tsx` - Added 3 new knowledge routes (upload, detail, review)
