# MCP Servers

Model Context Protocol (MCP) server implementations for inter-model data access.

## Available MCP Servers

| Server | Domain Model | Purpose |
|--------|--------------|---------|
| `collection-mcp/` | Collection Model | Query quality events, documents |
| `plantation-mcp/` | Plantation Model | Query farmers, factories, regions, weather |
| `knowledge-mcp/` | Knowledge Model | Query diagnoses, analysis results |
| `action-plan-mcp/` | Action Plan Model | Query action plans, recommendations |

## Design Rules

1. **MCP servers are STATELESS** - no in-memory caching
2. **Tools return data, NOT make decisions** - business logic stays in domain models
3. **Read-only access** - mutations go through domain model APIs
4. **Use Pydantic models** for tool input/output schemas

## Tool Naming Conventions

- Read operations: `get_*`, `search_*`, `list_*`
- Examples: `get_farmer_by_id`, `search_quality_events`, `list_regions`

## Server Structure

```
mcp-servers/{model-name}-mcp/
├── src/{model_name}_mcp/
│   ├── __init__.py
│   ├── server.py           # MCP server setup
│   ├── tools/              # Tool implementations
│   └── schemas/            # Pydantic models
├── tests/
├── Dockerfile
└── pyproject.toml
```

See `_bmad-output/project-context.md` for MCP usage rules.
