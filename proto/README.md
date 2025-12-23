# Protocol Buffers

Shared Protocol Buffer definitions for gRPC services.

## Directory Structure

```
proto/
├── buf.yaml                 # Buf configuration
├── buf.gen.yaml             # Code generation config
├── collection/v1/           # Collection Model protos
├── plantation/v1/           # Plantation Model protos
├── knowledge/v1/            # Knowledge Model protos
├── action_plan/v1/          # Action Plan Model protos
├── notification/v1/         # Notification Model protos
├── mcp/v1/                  # MCP tool definitions
└── common/v1/               # Shared types (pagination, errors, health)
```

## Package Naming

- Format: `farmer_power.{domain}.v1`
- Example: `farmer_power.collection.v1`

## Code Generation

```bash
# Generate Python stubs
make proto

# Or manually
./scripts/proto-gen.sh
```

Generated stubs go to `libs/fp-proto/fp_proto/`.

## Versioning

- Use versioned directories (`v1/`, `v2/`)
- Never break existing APIs - add new versions
- Deprecate old versions with timeline

See `_bmad-output/architecture/repository-structure.md` for proto organization details.
