# Appendix: Quick Reference

## Agent Type Selection

```
Need to extract data from documents?     → Extractor (LangChain)
Need to analyze/diagnose/find patterns?  → Explorer (LangGraph)
Need to generate content/reports?        → Generator (LangGraph)
Need multi-turn dialogue with users?     → Conversational (LangGraph)
```

## Common Patterns

```python
# Pattern: Confidence-based retry
if result.confidence < threshold and attempts < max_attempts:
    return "retry"

# Pattern: Multi-output generation
outputs = {
    "detailed": generate_detailed(context),
    "simplified": simplify(generate_detailed(context))
}

# Pattern: RAG context injection
rag_context = rag_engine.query(query_template.format(**inputs))
prompt = template.format(rag_context=rag_context, **inputs)
```

## Checklist Before PR

- [ ] Agent config YAML is valid and complete
- [ ] Prompts follow structure standards
- [ ] Golden sample tests pass
- [ ] No PII in prompts or logs
- [ ] Error handling covers all failure modes
- [ ] Tracing spans added for key operations
- [ ] Cost impact estimated

---
