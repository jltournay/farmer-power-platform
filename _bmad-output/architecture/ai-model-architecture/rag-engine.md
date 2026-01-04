# RAG Engine

The RAG (Retrieval-Augmented Generation) engine is internal to the AI Model.

> **Implementation details:** See `ai-model-developer-guide/10-rag-knowledge-management.md` for knowledge domain setup and query optimization.

| Aspect | Decision |
|--------|----------|
| **Vector DB** | Pinecone |
| **Access** | Internal only - domain models cannot query directly |
| **Curation (v1)** | Manual upload via Admin UI by agronomists |
| **Curation (future)** | Separate knowledge curation workflow |

**Knowledge Domains:**

| Domain | Content | Used By |
|--------|---------|---------|
| Plant Diseases | Symptoms, identification, treatments | diagnose-quality-issue |
| Tea Cultivation | Best practices, seasonal guidance | analyze-weather-impact, generate-action-plan |
| Weather Patterns | Regional climate, crop impact | analyze-weather-impact |
| Quality Standards | Grading criteria, buyer expectations | extract-and-validate, analyze-market |
| Regional Context | Local practices, cultural factors | generate-action-plan |
