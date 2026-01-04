# Agent Type Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Number of types** | 5 (Extractor, Explorer, Generator, Conversational, Tiered-Vision) | Covers fundamental AI patterns including dialogue and cost-optimized image analysis |
| **Type location** | In code | Workflow logic requires conditionals, loops, error handling |
| **Instance location** | YAML → MongoDB → Pydantic | Git source, MongoDB runtime, type-safe loading |
| **Model selection** | Explicit per agent | No indirection; agent config shows exact model used |
| **Inheritance** | Flat (Type → Instance only) | Avoids complexity; use parameters for variations |
| **Prompts** | Separate .md files | Better diffs, easier review, can be long |
