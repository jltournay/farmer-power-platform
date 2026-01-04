# Architecture Decision Records

This folder contains Architecture Decision Records (ADRs) documenting significant technical decisions made for the Farmer Power Platform.

## ADR Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-001](./ADR-001-weather-api-selection.md) | Weather API Selection (Open-Meteo) | Accepted | 2025-12-26 |
| [ADR-002](./ADR-002-frontend-architecture.md) | Frontend Architecture (4-App Hybrid) | Accepted | 2025-12-26 |
| [ADR-003](./ADR-003-identity-access-management.md) | Identity & Access Management (Azure AD B2C) | Accepted | 2025-12-26 |
| [ADR-004](./ADR-004-type-safety-shared-pydantic-models.md) | Type Safety - Shared Pydantic Models in MCP | Accepted | 2025-12-31 |
| [ADR-005](./ADR-005-grpc-client-retry-strategy.md) | gRPC Client Retry and Reconnection Strategy | Accepted | 2025-12-31 |
| [ADR-006](./ADR-006-event-delivery-dead-letter-queue.md) | Event Delivery Guarantees and Dead Letter Queue | Accepted | 2025-12-31 |
| [ADR-007](./ADR-007-source-config-cache-change-streams.md) | Source Config Cache with MongoDB Change Streams | Accepted | 2025-12-31 |
| [ADR-008](./ADR-008-invalid-linkage-field-handling.md) | Invalid Linkage Field Handling with Metrics | Accepted | 2025-12-31 |
| [ADR-009](./ADR-009-logging-standards-runtime-configuration.md) | Logging Standards and Runtime Configuration | Accepted | 2025-12-31 |
| [ADR-010](./ADR-010-dapr-patterns-configuration.md) | DAPR Patterns and Configuration Standards | Accepted | 2025-12-31 |
| [ADR-011](./ADR-011-grpc-fastapi-dapr-architecture.md) | gRPC/FastAPI/DAPR Service Architecture | Accepted | 2025-12-31 |
| [ADR-012](./ADR-012-bff-service-composition-api-design.md) | BFF Service Composition and API Design Patterns | Accepted | 2026-01-03 |
| [ADR-013](./ADR-013-ai-model-configuration-cache.md) | AI Model Configuration Cache with Change Streams | Accepted | 2026-01-04 |

## ADR Template

New ADRs should follow this structure:

1. **Status**: Proposed, Accepted, Deprecated, Superseded
2. **Context**: Why is this decision needed?
3. **Decision**: What was decided?
4. **Alternatives Considered**: What other options were evaluated?
5. **Consequences**: What are the positive and negative outcomes?
6. **Mitigations**: How are risks addressed?
7. **Revisit Triggers**: When should this decision be re-evaluated?

## Naming Convention

`ADR-XXX-short-description.md` where XXX is a zero-padded sequential number.
