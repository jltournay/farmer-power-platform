# Testing Strategy

> **Implementation details:** See `ai-model-developer-guide/5-testing-tuning.md` for golden sample creation, LLM mocking, and test fixtures.

| Test Type | Focus |
|-----------|-------|
| **Agent Type Workflows** | Step execution, error handling, retries |
| **Extraction Accuracy** | Golden samples → expected extractions |
| **Diagnosis Quality** | Expert-validated cases |
| **RAG Relevance** | Query → useful context retrieval |
| **Event Contracts** | Input/output schema compliance |
| **MCP Integration** | Correct data fetching |
| **LLM Gateway** | Routing, fallback, cost tracking |
| **End-to-End** | Full event flow through system |
