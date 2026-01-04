# RAG Document Ingestion UX Specification

**Frontend Application:** Platform Admin Portal (Epic 9)
**Story:** 9.5 - Knowledge Management Interface
**Last Updated:** 2026-01-04

---

## Overview

The RAG Document Ingestion interface enables agronomists and domain experts to upload, manage, and activate expert knowledge documents that power AI recommendations. The system handles document extraction automatically, so users don't need technical expertise.

### Primary Users

| User | Role | Primary Tasks |
|------|------|---------------|
| **Agronomist** | Domain expert | Upload research papers, review content accuracy |
| **TBK Specialist** | Tea Board of Kenya | Upload official guidelines, quality standards |
| **Platform Admin** | Internal operations | Activate documents, manage lifecycle, troubleshoot |

### Key Design Principles

1. **Zero Technical Knowledge Required** - Users shouldn't need to understand OCR, embeddings, or vector databases
2. **Transparency Over Magic** - Show confidence scores, extraction methods, and progress
3. **Test Before Production** - Staged testing with AI before going live
4. **Full Audit Trail** - Version history and rollback capability

---

## Knowledge Domains

Documents are categorized into knowledge domains that map to AI agent expertise:

| Domain | Description | Example Documents |
|--------|-------------|-------------------|
| **Plant Diseases** | Disease identification, symptoms, treatments | Blister Blight Guide, Pest Management Manual |
| **Tea Cultivation** | Growing techniques, plucking methods, seasonal care | Optimal Plucking Techniques, Pruning Calendar |
| **Weather Patterns** | Weather impact on tea, seasonal advisories | Drought Response Guide, Frost Protection |
| **Quality Standards** | TBK grading criteria, export requirements | Kenya Tea Grading Standards, Premium Tea Specs |
| **Regional Context** | Region-specific growing conditions, local practices | Kericho Growing Guide, Nyeri Altitude Considerations |

---

## Screen Specifications

### Screen 1: Knowledge Document Library

**Purpose:** Browse, search, and manage all expert knowledge documents.

**Navigation:** Platform Admin Portal > Knowledge Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE MANAGEMENT                                    [+ Upload Document] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FILTER BY DOMAIN        SEARCH                                              │
│  ┌──────────────────┐   ┌────────────────────────────────────────────────┐  │
│  │ [x] All Domains  │   │  🔍 Search documents...                        │  │
│  │ [ ] Plant Disease│   └────────────────────────────────────────────────┘  │
│  │ [ ] Tea Cultiv.  │                                                       │
│  │ [ ] Weather      │   DOCUMENTS                                           │
│  │ [ ] Quality Std  │   ┌────────────────────────────────────────────────┐  │
│  │ [ ] Regional     │   │  📄 Blister Blight Treatment Guide    v2.1     │  │
│  └──────────────────┘   │     Plant Diseases • Dr. Njeri Kamau • Active  │  │
│                         │     Updated: 2025-12-15                        │  │
│  FILTER BY STATUS       │                                       [View →] │  │
│  ┌──────────────────┐   ├────────────────────────────────────────────────┤  │
│  │ 🟢 Active    (24)│   │  📄 Optimal Plucking Techniques      v1.0     │  │
│  │ 🟡 Staged     (3)│   │     Tea Cultivation • J. Odhiambo • Staged    │  │
│  │ 📝 Draft      (5)│   │     Ready for review since: 2025-12-20        │  │
│  │ 📦 Archived   (8)│   │                             [Review →] [Edit] │  │
│  └──────────────────┘   ├────────────────────────────────────────────────┤  │
│                         │  📄 Weather Pattern Recognition       v3.0     │  │
│                         │     Weather Patterns • TBK • Active            │  │
│                         │     Updated: 2025-11-28                        │  │
│                         │                                       [View →] │  │
│                         └────────────────────────────────────────────────┘  │
│                                                                              │
│  Showing 32 documents • Page 1 of 4              [← Previous] [Next →]      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Interactions:**

| Element | Action | Result |
|---------|--------|--------|
| Domain filter checkboxes | Click | Filter document list by selected domains |
| Status filter | Click | Filter by lifecycle status |
| Search input | Type | Real-time search across titles and content |
| Document card | Click | Navigate to document detail view |
| [View →] | Click | Open read-only document view |
| [Review →] | Click | Open review/activation screen (staged docs only) |
| [Edit] | Click | Open edit mode for draft/staged docs |
| [+ Upload Document] | Click | Start upload wizard |

---

### Screen 2: Document Upload - Step 1 (File & Metadata)

**Purpose:** Upload document file and enter metadata.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  UPLOAD NEW DOCUMENT                                         Step 1 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │                    📁 Drag & drop your file here                       │  │
│  │                         or click to browse                             │  │
│  │                                                                        │  │
│  │                   Supported: PDF, DOCX, MD, TXT                        │  │
│  │                   Max size: 50MB                                       │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ─────────────────────────── OR ───────────────────────────────────────     │
│                                                                              │
│  [📝 Write content directly] (opens rich text editor)                       │
│                                                                              │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DOCUMENT DETAILS                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Title:     [                                                      ]  │  │
│  │                                                                        │  │
│  │  Domain:    [Select domain ▼]                                         │  │
│  │             • Plant Diseases                                          │  │
│  │             • Tea Cultivation                                         │  │
│  │             • Weather Patterns                                        │  │
│  │             • Quality Standards                                       │  │
│  │             • Regional Context                                        │  │
│  │                                                                        │  │
│  │  Author:    [Your name                                             ]  │  │
│  │  Source:    [e.g., TBK Research Paper, Field Study, etc.           ]  │  │
│  │  Region:    [Select region (optional) ▼]                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  [Cancel]                                                    [Continue →]   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Validation Rules:**

| Field | Required | Validation |
|-------|----------|------------|
| File | Yes | PDF, DOCX, MD, TXT only; max 50MB |
| Title | Yes | 3-200 characters |
| Domain | Yes | Must select one |
| Author | Yes | 2-100 characters |
| Source | No | Max 200 characters |
| Region | No | Optional, for region-specific content |

---

### Screen 3: Document Processing - Step 2 (Extraction)

**Purpose:** Show extraction progress with automatic method detection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PROCESSING DOCUMENT                                         Step 2 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📄 blister-blight-treatment-guide.pdf                                      │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ⏳ Analyzing document...                                              │  │
│  │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%       │  │
│  │                                                                        │  │
│  │  ✅ Detected: Scanned PDF with embedded images                        │  │
│  │  ✅ Using: Azure Document Intelligence (OCR)                          │  │
│  │  ⏳ Extracting text from 12 pages...                                   │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ℹ️ This may take 1-2 minutes for large documents                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Extraction Methods (Auto-Detected):**

| Document Type | Detection | Extraction Method |
|---------------|-----------|-------------------|
| Digital PDF (text-based) | Embedded text layer | PyMuPDF (fast, free) |
| Scanned PDF | No text layer, image pages | Azure Document Intelligence (OCR) |
| PDF with diagrams | Complex layouts, charts | Vision LLM (for diagram interpretation) |
| Markdown (.md) | File extension | Direct parsing |
| Word (.docx) | File extension | python-docx |
| Plain text (.txt) | File extension | Direct read |

---

### Screen 4: Content Preview - Step 2b

**Purpose:** Review and optionally edit extracted content.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REVIEW EXTRACTED CONTENT                                    Step 2 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📄 Blister Blight Treatment Guide                                          │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Extraction: ✅ Completed • Confidence: 94% • Pages: 12                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  EXTRACTED CONTENT                                              [Edit ✏️]   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  # Blister Blight (Exobasidium vexans)                                │  │
│  │                                                                        │  │
│  │  ## Identification                                                     │  │
│  │  Blister blight appears as small, circular, translucent spots on      │  │
│  │  young leaves. As the disease progresses, blisters become convex      │  │
│  │  on the upper surface and concave on the lower surface...             │  │
│  │                                                                        │  │
│  │  ## Environmental Conditions                                          │  │
│  │  - High humidity (>85%)                                               │  │
│  │  - Temperature: 18-22°C                                               │  │
│  │  - Rainfall during plucking season                                    │  │
│  │                                                                        │  │
│  │  ## Treatment Recommendations                                         │  │
│  │  1. Remove and destroy infected shoots                                │  │
│  │  2. Apply copper-based fungicide...                                   │  │
│  │                                                                        │  │
│  │  [... scroll for more content ...]                                    │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ⚠️ Please verify the extracted content is accurate. You can edit          │
│     directly or re-upload if extraction quality is poor.                    │
│                                                                              │
│  [← Back]    [🔄 Re-extract with different method]         [Continue →]     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Confidence Score Interpretation:**

| Score | Indicator | Meaning |
|-------|-----------|---------|
| ≥90% | 🟢 High | Extraction reliable, minimal review needed |
| 70-89% | 🟡 Medium | Review recommended, some sections may need editing |
| <70% | 🔴 Low | Significant issues, consider re-extraction or manual entry |

---

### Screen 5: Extraction Quality Warning

**Purpose:** Handle low-confidence extractions with user guidance.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚠️ EXTRACTION QUALITY WARNING                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  The automatic extraction achieved 62% confidence.                          │
│  Some content may be missing or incorrectly extracted.                      │
│                                                                              │
│  POSSIBLE ISSUES DETECTED:                                                   │
│  • Handwritten notes on pages 3, 7                                          │
│  • Low resolution images/diagrams on pages 5-6                              │
│  • Complex table on page 8                                                  │
│                                                                              │
│  RECOMMENDED ACTIONS:                                                        │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  [🔍 Try Vision AI extraction]                                     │     │
│  │      Best for: diagrams, handwritten notes, complex layouts        │     │
│  │                                                                     │     │
│  │  [✏️ Edit extracted content manually]                              │     │
│  │      Fix specific sections that weren't captured correctly         │     │
│  │                                                                     │     │
│  │  [📄 Upload clearer scan]                                          │     │
│  │      If original document quality is poor                          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  [← Back]                                          [Continue anyway →]      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Screen 6: Save Document - Step 3

**Purpose:** Confirm metadata and select initial lifecycle status.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SAVE DOCUMENT                                               Step 3 of 3    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DOCUMENT SUMMARY                                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Title:      Blister Blight Treatment Guide                           │  │
│  │  Domain:     Plant Diseases                                           │  │
│  │  Author:     Dr. Njeri Kamau                                          │  │
│  │  Source:     TBK Research Paper 2024                                  │  │
│  │  Region:     All regions                                              │  │
│  │  Pages:      12                                                       │  │
│  │  Word count: ~3,200 words                                             │  │
│  │  Extraction: Azure Document Intelligence (94% confidence)             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  SAVE AS                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ○ 📝 Draft                                                           │  │
│  │       Save for later editing. Not visible to AI agents.               │  │
│  │                                                                        │  │
│  │  ● 🟡 Staged (Recommended)                                            │  │
│  │       Ready for review. Test with AI before going live.               │  │
│  │                                                                        │  │
│  │  ○ 🟢 Active (Requires approval)                                      │  │
│  │       Immediately available to AI agents.                             │  │
│  │       Note: Only Platform Admins can activate directly.               │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  [← Back]                                         [Save as Staged ✓]        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Screen 7: Document Review & Activation

**Purpose:** Review staged documents and promote to active status with AI testing.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  REVIEW DOCUMENT                                              [Activate ▼]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📄 Blister Blight Treatment Guide                           Status: Staged │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  DOCUMENT INFO               │  TEST WITH AI                                │
│  ┌─────────────────────────┐ │  ┌───────────────────────────────────────┐   │
│  │ Domain: Plant Diseases  │ │  │ Ask a test question:                  │   │
│  │ Author: Dr. Njeri Kamau │ │  │                                       │   │
│  │ Version: 1.0            │ │  │ [What causes blister blight?      ]   │   │
│  │ Created: 2025-12-22     │ │  │                                       │   │
│  │                         │ │  │ [Test →]                              │   │
│  │ Previous versions: None │ │  │                                       │   │
│  └─────────────────────────┘ │  │ AI Response:                          │   │
│                              │  │ "Blister blight is caused by the      │   │
│  CONTENT PREVIEW             │  │  fungus Exobasidium vexans. It        │   │
│  ┌─────────────────────────┐ │  │  thrives in humid conditions..."      │   │
│  │ # Blister Blight        │ │  │                                       │   │
│  │                         │ │  │ ✅ Document content retrieved         │   │
│  │ ## Identification       │ │  │    successfully                       │   │
│  │ Blister blight appears  │ │  └───────────────────────────────────────┘   │
│  │ as small, circular...   │ │                                              │
│  │                         │ │                                              │
│  │ [View full content →]   │ │                                              │
│  └─────────────────────────┘ │                                              │
│                              │                                              │
│  ───────────────────────────────────────────────────────────────────────    │
│                                                                              │
│  APPROVAL                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ☐ I have reviewed the content for accuracy                          │  │
│  │  ☐ I have tested AI retrieval with sample questions                  │  │
│  │  ☐ I approve this document for production use                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  [← Back to Library]    [Edit]    [Reject]    [🟢 Activate for Production]  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**"Test with AI" Feature:**
- Allows reviewer to ask questions that should be answerable from the document
- Verifies document is properly chunked and indexed in vector store
- Shows which chunks were retrieved (for debugging)
- Must pass at least one test before activation is allowed

---

### Screen 8: Version History

**Purpose:** View document version history with rollback capability.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VERSION HISTORY: Blister Blight Treatment Guide                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ v2.1 (Active)                                      2025-12-15 10:30    │ │
│  │ Updated treatment recommendations per 2025 TBK guidelines              │ │
│  │ Author: Dr. Njeri Kamau                                                │ │
│  │                                                    [View] [Rollback]   │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ v2.0 (Archived)                                    2025-09-01 14:22    │ │
│  │ Added regional variations section                                      │ │
│  │ Author: J. Odhiambo                                                    │ │
│  │                                                    [View] [Compare]    │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ v1.0 (Archived)                                    2025-06-15 09:45    │ │
│  │ Initial version                                                        │ │
│  │ Author: Dr. Njeri Kamau                                                │ │
│  │                                                    [View] [Compare]    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Version Operations:**

| Action | Description |
|--------|-------------|
| **View** | Open read-only view of that version |
| **Compare** | Side-by-side diff with current active version |
| **Rollback** | Reactivate a previous version (current becomes archived) |

---

## Document Lifecycle

### States

| State | Icon | Description | Vector Index | Who Can Access |
|-------|------|-------------|--------------|----------------|
| **Draft** | 📝 | Work in progress | Not indexed | Author only |
| **Staged** | 🟡 | Ready for review | Test namespace | Reviewers + Admins |
| **Active** | 🟢 | Live in production | Production namespace | All AI agents |
| **Archived** | 📦 | Deprecated, kept for history | Removed from index | Admins only |

### State Transitions

```
                    ┌──────────────┐
                    │    Draft     │
                    │     📝       │
                    └──────┬───────┘
                           │ Submit for Review
                           ▼
                    ┌──────────────┐
        ┌──────────▶│   Staged     │◀──────────┐
        │           │     🟡       │           │
        │           └──────┬───────┘           │
        │                  │ Approve           │ Reject
        │                  ▼                   │
        │           ┌──────────────┐           │
        │           │   Active     │───────────┘
        │           │     🟢       │
        │           └──────┬───────┘
        │                  │ New version uploaded
        │                  ▼
        │           ┌──────────────┐
        └───────────│  Archived    │
                    │     📦       │
                    └──────────────┘
```

---

## Technical Integration

### Backend APIs

| Screen | API Endpoint | Method |
|--------|--------------|--------|
| Document Library | `/api/admin/rag/documents` | GET |
| Upload | `/api/admin/rag/documents` | POST (multipart) |
| Extraction Status | `/api/admin/rag/documents/{id}/extraction-status` | GET |
| Update Content | `/api/admin/rag/documents/{id}` | PATCH |
| Activate | `/api/admin/rag/documents/{id}/activate` | POST |
| Test with AI | `/api/admin/rag/documents/{id}/test` | POST |
| Version History | `/api/admin/rag/documents/{id}/versions` | GET |
| Rollback | `/api/admin/rag/documents/{id}/rollback` | POST |

### gRPC Services

- **RagDocumentService** (Epic 0.75, Story 0.75.10): Document CRUD operations
- **CostService** (Epic 0.75, Story 0.75.5): Track extraction costs (Azure DI, Vision LLM)

---

## Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Keyboard navigation | All actions accessible via Tab/Enter |
| Screen reader | ARIA labels on all interactive elements |
| Color contrast | WCAG AA compliant (4.5:1 ratio) |
| Status indicators | Icons + text (not color alone) |
| Progress feedback | Live region announcements for extraction progress |

---

## Related Documents

- [UI Screens Inventory](./ui-screens-inventory.md) - Platform Admin UI section
- [Admin Interface Core Experience](./admin-interface-core-experience.md) - Knowledge Management UI
- [Epic 9: Platform Admin Portal](../epics/epic-9-admin-portal.md) - Story 9.5
- [Epic 0.75: AI Model Foundation](../epics/epic-0-75-ai-model.md) - RAG infrastructure stories

---

_Last Updated: 2026-01-04_
