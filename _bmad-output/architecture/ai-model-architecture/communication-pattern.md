# Communication Pattern

The AI Model uses **event-driven async communication** via DAPR:

```
Domain Models                          AI Model
┌─────────────────┐                   ┌─────────────────────────────┐
│                 │   publish event   │                             │
│  Collection     │──────────────────▶│   1. Receive event (ref)    │
│  Knowledge      │   { doc_id }      │   2. Fetch data via MCP     │
│  Action Plan    │                   │   3. Run agent workflow     │
│  Plantation     │◀──────────────────│   4. Publish result event   │
│  Market         │   result event    │                             │
│                 │   { result }      │                             │
└─────────────────┘                   └─────────────────────────────┘
     No AI logic                           All AI logic here
     No RAG access
```

**Event Flow Example - Quality Document Processing:**

```
1. Collection Model receives QC payload via API
2. Collection stores raw document → doc_id = "doc-123"
3. Collection publishes via DAPR Pub/Sub:
   topic: "collection.document.received"
   payload: { doc_id: "doc-123", source: "qc-analyzer", event_type: "END_BAG" }

4. AI Model subscribes, receives event
5. AI Model calls Collection MCP: get_document("doc-123")
6. AI Model runs extraction agent workflow
7. AI Model publishes via DAPR Pub/Sub:
   topic: "ai.extraction.complete"
   payload: {
     doc_id: "doc-123",
     success: true,
     result: {
       farmer_id: "WM-4521",
       grade: "B",
       quality_score: 78,
       validation_warnings: []
     }
   }

8. Collection Model subscribes, receives result
9. Collection updates document with extracted fields
```
