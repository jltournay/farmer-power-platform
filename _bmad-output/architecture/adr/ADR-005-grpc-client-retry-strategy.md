# ADR-005: gRPC Client Retry and Reconnection Strategy

**Status:** Accepted
**Date:** 2025-12-31
**Deciders:** Winston (Architect), Murat (TEA), Amelia (Dev), Jeanlouistournay
**Related Stories:** Epic 0-4 (Grading Validation)
**Validated By:** PoC at `tests/e2e/poc-dapr-patterns/` (resilience test passing)

## Context

During E2E testing of Epic 0-4, we discovered that some gRPC clients lack retry logic. When a gRPC connection is lost (server restart, network blip, transient failure), the client becomes **permanently broken** until the pod is restarted.

**Critical finding:** DAPR resiliency middleware only works for HTTP connections, NOT gRPC. All gRPC clients must implement their own retry logic.

**Current state:**

| Client | Retry Logic | Channel Pattern | Status |
|--------|-------------|-----------------|--------|
| PlantationClient | ✅ Tenacity (3 attempts, exponential 1-10s) | Singleton | GOOD |
| AiModelClient | ❌ NONE | Per-request | CRITICAL |
| IterationResolver | ❌ NONE | Per-request | CRITICAL |

## Decision

**ALL gRPC clients MUST implement retry logic with singleton channel pattern.**

This is a **UNIVERSAL RULE** that applies to:
- All existing gRPC clients
- All future gRPC clients (including BFF → Plantation Model, BFF → Collection Model, etc.)
- Any service-to-service gRPC communication

Clients without retry are unacceptable in production - a lost connection should auto-recover, not require pod restart.

**This rule MUST be enforced in code review.** Any PR introducing a new gRPC client without retry logic should be rejected.

## Alternatives Considered

| Option | Description | Verdict |
|--------|-------------|---------|
| DAPR resiliency | Use DAPR middleware for retry | Rejected: Only works for HTTP |
| Per-request channels | Create new channel each call | Rejected: No reconnection |
| **Tenacity + Singleton** | Client-side retry + reusable channel | **Selected** |

## Required Pattern

All gRPC clients must follow the PlantationClient pattern:

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import grpc.aio

class GrpcServiceClient:
    """Required pattern for all gRPC clients."""

    def __init__(self, channel: grpc.aio.Channel | None = None) -> None:
        self._channel = channel
        self._stub: SomeServiceStub | None = None

    async def _get_stub(self) -> SomeServiceStub:
        """Lazy singleton channel - created once, reused."""
        if self._stub is None:
            if self._channel is None:
                self._channel = grpc.aio.insecure_channel(
                    target,
                    options=[
                        ("grpc.keepalive_time_ms", 30000),
                        ("grpc.keepalive_timeout_ms", 10000),
                    ]
                )
            self._stub = SomeServiceStub(self._channel)
        return self._stub

    @retry(
        retry=retry_if_exception_type(grpc.aio.AioRpcError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def some_rpc_method(self, ...) -> ...:
        """ALL RPC methods MUST have retry decorator."""
        stub = await self._get_stub()
        try:
            response = await stub.SomeRpc(request, metadata=self._get_metadata())
            return response
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundError(...) from e
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                raise ServiceUnavailableError(...) from e
            raise

    async def close(self) -> None:
        """Clean up resources."""
        if self._channel:
            await self._channel.close()
            self._channel = None
```

## Consequences

### Positive

- **Auto-recovery** from transient failures without pod restart
- **Consistent behavior** across all gRPC clients
- **Observable failures** via retry logs

### Negative

- **Additional dependency** on Tenacity library
- **Latency increase** during retry cycles

## Anti-Patterns (FORBIDDEN)

```python
# ❌ FORBIDDEN: Per-request channel creation
async with grpc.aio.insecure_channel(target) as channel:
    stub = SomeStub(channel)
    response = await stub.SomeRpc(request)

# ❌ FORBIDDEN: No retry decorator on RPC methods
async def some_rpc_method(self):
    response = await stub.SomeRpc(request)  # Will fail permanently on error
```

## Implementation Plan

### Phase 1: Fix Critical Clients

| Client | File | Changes Required |
|--------|------|------------------|
| **AiModelClient** | `services/collection-model/.../ai_model_client.py` | Singleton + Tenacity retry |
| **IterationResolver** | `services/collection-model/.../iteration_resolver.py` | Singleton + Tenacity retry |

### Phase 2: Create Base Class in fp-common (Future)

Create `libs/fp-common/fp_common/grpc/base_client.py` with:
- `BaseGrpcClient` class with retry decorator
- `grpc_retry` decorator for easy application
- Standard keepalive configuration
- DAPR metadata helper

## Revisit Triggers

Re-evaluate this decision if:

1. **DAPR adds gRPC resiliency** - May be able to use middleware instead
2. **Performance impact significant** - May need circuit breaker pattern
3. **Different retry strategies needed** - May need per-client configuration

## PoC Validation

The retry and reconnection pattern was validated in a standalone PoC: `tests/e2e/poc-dapr-patterns/`

| Test | Status | What It Validates |
|------|--------|-------------------|
| gRPC Client Resilience (ADR-005) | ✅ Pass | Auto-reconnection after server restart |

**Test scenario:**
1. Service A calls Service B via DAPR gRPC proxy → succeeds
2. Service B + DAPR sidecar are restarted (simulates pod restart)
3. Service A calls Service B again → succeeds (auto-reconnected)

**Key findings from PoC:**
- With proper gRPC keepalive settings, connections recover quickly
- Tenacity retry decorator provides robust error handling
- Reset channel/stub on error forces reconnection on next attempt
- DAPR mesh recovers automatically when both service and sidecar restart together

Run the resilience test:
```bash
cd tests/e2e/poc-dapr-patterns
docker compose up --build -d
sleep 20
python run_tests.py --test resilience
docker compose down -v
```

## References

- Epic 0-4: Grading Validation
- Reference: PlantationClient in `plantation-mcp` (correct pattern)
- Related: ADR-004 (Type Safety), ADR-010 (DAPR Patterns), ADR-011 (Service Architecture)
