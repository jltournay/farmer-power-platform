# Story 2-13: Thumbnail Generation for AI Tiered Vision Processing

**Epic:** Epic 2 - Quality Data Ingestion
**Status:** Blocked
**Blocked By:** Story 0.75.17 (Extractor Agent Implementation)
**Blocks:** Story 0.75.18 (E2E Weather Observation Extraction Flow)
**GitHub Issue:** #88
**Story Points:** 3

---

## User Story

As a **platform operator**,
I want Collection Model to generate thumbnails at image ingestion time,
So that AI Model's Tiered Vision processing can reduce LLM costs by 57%.

---

## Context

The AI Model architecture includes a **Tiered Vision Processing** optimization:

- **Tier 1 (Haiku):** Quick screening using 256x256 thumbnail → $0.001/image
- **Tier 2 (Sonnet):** Deep analysis using full resolution → $0.012/image (only 35% of images)

For this to work efficiently, **Collection Model must generate thumbnails at ingestion time**, not AI Model on-demand.

**Architecture Reference:** `_bmad-output/architecture/ai-model-architecture.md` § *Tiered Vision Processing*

```
QC Analyzer ──► Collection Model ──► Blob Storage
                      │                  │
                      │ Generate         ├── /documents/{doc_id}/original.jpg
                      │ thumbnail        └── /documents/{doc_id}/thumbnail.jpg
                      │
                      └──► MongoDB: { doc_id, original_url, thumbnail_url }
```

---

## Acceptance Criteria

### AC-1: Image Processing Capability
- [ ] `Pillow` added to Collection Model dependencies
- [ ] `ThumbnailGenerator` service class created
- [ ] Thumbnail size: 256x256 pixels, JPEG format, quality 60%
- [ ] Aspect ratio maintained with center-crop or pad to square

### AC-2: Processing Flow Integration
- [ ] After storing original image, thumbnail generated automatically
- [ ] Thumbnail stored to blob: `/documents/{doc_id}/thumbnail.jpg`
- [ ] Document record updated with `thumbnail_url`

### AC-3: Document Schema Updated
- [ ] `DocumentRecord` model includes `thumbnail_url: str | None`
- [ ] `DocumentRecord` model includes `thumbnail_generated: bool`
- [ ] Proto definitions updated if needed

### AC-4: MCP Tool Added
- [ ] `get_document_thumbnail(doc_id)` tool returns thumbnail bytes
- [ ] Tool documented in MCP server tool list

### AC-5: Event Payload Updated
- [ ] `collection.document.received` event includes `has_thumbnail: bool`
- [ ] `collection.document.received` event includes `thumbnail_url: str | None`

### AC-6: Error Handling
- [ ] If thumbnail generation fails, log warning but don't fail ingestion
- [ ] `thumbnail_generated: false` set on failure
- [ ] Error details logged for debugging

### AC-7: Testing
- [ ] Unit tests for `ThumbnailGenerator` service
- [ ] Unit tests for various image formats (JPEG, PNG)
- [ ] Integration test: ingest image → verify thumbnail exists in blob

---

## Technical Notes

### Thumbnail Specification

| Property | Value |
|----------|-------|
| Size | 256x256 pixels |
| Format | JPEG |
| Quality | 60% |
| Aspect Ratio | Maintain original, center-crop or pad to square |

### Files to Create/Modify

**New Files:**
- `services/collection-model/src/collection_model/domain/thumbnail_generator.py`

**Modified Files:**
- `services/collection-model/pyproject.toml` - Add Pillow dependency
- `services/collection-model/src/collection_model/domain/models.py` - Add thumbnail fields
- `services/collection-model/src/collection_model/infrastructure/blob_storage.py` - Store thumbnail
- `mcp-servers/collection-mcp/src/collection_mcp/tools.py` - Add get_document_thumbnail tool

---

## Dependencies

| Depends On | Reason |
|------------|--------|
| Story 0.75.17 | Extractor agent defines tiered vision interface expectations |
| Story 2-5 | QC Analyzer image ingestion (already complete) |

| Blocks | Reason |
|--------|--------|
| Story 0.75.18 | E2E validation needs thumbnails for full tiered vision flow |
| Story 0.75.22 | Tiered-Vision agent requires thumbnails |

---

## Out of Scope

- Tiered Vision agent implementation (Story 0.75.22)
- E2E testing (Story 0.75.18)
- AI Model changes

---

_Created: 2026-01-05_
_Last Updated: 2026-01-05_
