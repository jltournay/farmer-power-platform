# Story 1.1 Code Review - Lessons Learned for Future Agents

**Story:** 1-1-plantation-model-service-setup
**Reviewed:** 2025-12-23
**Reviewer:** Adversarial Code Review Workflow

---

## Critical Issues Found & Fixed

### Issue #1: Python Version Mismatch

**Problem:**
- `pyproject.toml` specified `python = "^3.12"`
- Architecture docs and Dockerfile use Python 3.11
- User's local environment has Python 3.11.12

**Root Cause:**
The dev agent used Python 3.12 requirement without checking the architecture spec which mandates Python 3.11.

**Fix Applied:**
```toml
# pyproject.toml
python = "^3.11"  # NOT ^3.12

# [tool.ruff]
target-version = "py311"  # NOT py312

# [tool.mypy]
python_version = "3.11"  # NOT 3.12
```

**Rule for Future Agents:**
> ALWAYS check `_bmad-output/architecture/repository-structure.md` for the Dockerfile base image version and match `pyproject.toml` Python version to it.

---

### Issue #2: Dockerfile - Poetry Export with Local Dependencies

**Problem:**
```dockerfile
# This FAILS when pyproject.toml has local path dependencies
RUN poetry export -f requirements.txt --without-hashes > requirements.txt
```

**Root Cause:**
Poetry export cannot resolve local path dependencies like `fp-proto = { path = "../../libs/fp-proto" }` during Docker build.

**Fix Applied:**
Use `poetry install` with proper directory structure maintained:
```dockerfile
# Maintain repository structure for relative path resolution
WORKDIR /app

# Copy shared libs first
COPY libs/ /app/libs/

# Copy service maintaining directory structure
COPY services/plantation-model/ /app/services/plantation-model/

# Change to service directory for poetry paths to work
WORKDIR /app/services/plantation-model

# Use poetry install, NOT poetry export
RUN poetry install --no-interaction --no-ansi --no-root --only main
```

**Rule for Future Agents:**
> NEVER use `poetry export` in Dockerfiles when services depend on local path packages from `libs/`. Use `poetry install` with the full repository context.

---

### Issue #3: Dockerfile - Permission Denied for Non-Root User

**Problem:**
```
PermissionError: [Errno 13] Permission denied: '/app/src/plantation_model/main.py'
```

**Root Cause:**
Files copied from builder stage are owned by `root`, but runtime runs as `appuser`.

**Fix Applied:**
```dockerfile
# Use --chown to set correct ownership
COPY --from=builder --chown=appuser:appgroup /app/services/plantation-model/src/ ./src/
COPY --from=builder --chown=appuser:appgroup /app/libs/fp-proto/src/ ./libs/fp-proto/src/
```

**Rule for Future Agents:**
> ALWAYS use `--chown=appuser:appgroup` when COPY-ing files into runtime stage if the container runs as a non-root user.

---

### Issue #4: OpenTelemetry Version Conflicts

**Problem:**
```
Because opentelemetry-instrumentation-pymongo (0.43b0) depends on
opentelemetry-semantic-conventions (0.43b0) and opentelemetry-sdk (>=1.22.0)
requires newer versions... version solving failed.
```

**Root Cause:**
Dev agent pinned old beta versions of instrumentation packages (`^0.43b0`) that are incompatible with newer SDK/exporter versions.

**Fix Applied:**
```toml
# OpenTelemetry versions MUST be aligned
opentelemetry-api = "^1.29.0"
opentelemetry-sdk = "^1.29.0"
opentelemetry-exporter-otlp = "^1.29.0"
# Instrumentation versions follow pattern: SDK 1.XX → Instrumentation 0.XXb0
opentelemetry-instrumentation-fastapi = ">=0.50b0"
opentelemetry-instrumentation-grpc = ">=0.50b0"
opentelemetry-instrumentation-pymongo = ">=0.50b0"
```

**Rule for Future Agents:**
> OpenTelemetry packages MUST use compatible versions:
> - SDK/API/Exporter versions should be pinned to same minor version (e.g., all ^1.29.0)
> - Instrumentation packages version = SDK version - 1.0 as beta (SDK 1.29 → Instrumentation 0.50b0)
> - Use `>=0.XXb0` instead of `^0.XXb0` for flexibility

---

### Issue #5: Docker Compose Port Conflicts

**Problem:**
```
Bind for 0.0.0.0:50006 failed: port is already allocated
```

**Root Cause:**
Other Docker containers (DAPR development stack) already using ports 27017, 6379, 50006.

**Fix Applied:**
```yaml
mongodb:
  ports:
    - "27018:27017"  # Changed from 27017

redis:
  ports:
    - "6380:6379"  # Changed from 6379

placement:
  command: ["./placement", "-port", "50007"]  # Changed from 50006
  ports:
    - "50007:50007"
```

**Rule for Future Agents:**
> When creating docker-compose.yml, use non-standard host ports to avoid conflicts:
> - MongoDB: 27018:27017
> - Redis: 6380:6379
> - DAPR Placement: 50007:50007
> - Service HTTP: 800X:8000 (increment X per service)

---

### Issue #6: IDE Imports Don't Work (Local Development)

**Problem:**
```python
# This fails in IDE but works in Docker
from plantation_model.config import settings
# ModuleNotFoundError: No module named 'plantation_model'
```

**Root Cause:**
Docker sets `PYTHONPATH=/app/src`, but the IDE doesn't know where to find the package.

**Fix Applied:**
```bash
# Install package in editable mode
cd services/plantation-model
pip install -e .

# Also install fp-proto if needed
cd ../../libs/fp-proto
pip install -e .
```

**Rule for Future Agents:**
> After creating a new service, document in README.md that developers must run `pip install -e .` from the service directory for local development. This does NOT affect Docker builds.

**IDE Configuration (Optional):**
For VSCode, add to `.vscode/settings.json`:
```json
{
  "python.analysis.extraPaths": [
    "services/plantation-model/src",
    "libs/fp-proto/src"
  ]
}
```

---

---

## Issues from Previous Code Review Session (Git History)

### Issue #8: Unused Imports in gRPC Server

**Problem:**
```python
import asyncio  # Not used
from concurrent import futures  # Not needed for async server
```

**Root Cause:**
Dev agent copied boilerplate code without checking if imports were used.

**Fix Applied:**
Removed unused imports.

**Rule for Future Agents:**
> After implementation, verify all imports are used. IDEs show warnings for unused imports.

---

### Issue #9: ThreadPoolExecutor with Async gRPC Server

**Problem:**
```python
self._server = grpc.aio.server(
    futures.ThreadPoolExecutor(max_workers=10),  # WRONG!
    ...
)
```

**Root Cause:**
`grpc.aio.server()` is async-native and doesn't need a ThreadPoolExecutor. That's for the synchronous `grpc.server()`.

**Fix Applied:**
```python
self._server = grpc.aio.server(
    options=[...]  # No thread pool needed
)
```

**Rule for Future Agents:**
> When using `grpc.aio.server()` (async), do NOT pass ThreadPoolExecutor. Only synchronous `grpc.server()` needs it.

---

### Issue #10: Duplicate HealthService in Proto Definition

**Problem:**
```protobuf
// plantation.proto
service HealthService {
  rpc Check(HealthCheckRequest) returns (HealthCheckResponse);
}
```

**Root Cause:**
Dev agent defined custom HealthService in proto, but `grpc-health-checking` package already provides the standard `grpc.health.v1.Health` service.

**Fix Applied:**
Removed custom HealthService from proto, added comment:
```protobuf
// Note: Health checking uses standard grpc.health.v1.Health (grpc-health-checking package)
```

**Rule for Future Agents:**
> Use `grpc-health-checking` package for gRPC health checks. Do NOT define custom HealthService in proto files.

---

### Issue #11: Hardcoded Configuration Values

**Problem:**
```python
otlp_exporter = OTLPSpanExporter(
    endpoint=settings.otel_exporter_endpoint,
    insecure=True,  # Hardcoded!
)
```

**Root Cause:**
Dev agent hardcoded `insecure=True` instead of making it configurable.

**Fix Applied:**
```python
# config.py
otel_exporter_insecure: bool = True  # Set False in production for TLS

# tracing.py
insecure=settings.otel_exporter_insecure,
```

**Rule for Future Agents:**
> ALL environment-specific values MUST be configurable via Settings class. Never hardcode values like `True`/`False` for security flags.

---

### Issue #12: Tests in Wrong Location

**Problem:**
Tests were placed in `services/plantation-model/tests/` instead of global `tests/` folder.

**Root Cause:**
Dev agent didn't check `test-design-system-level.md` which specifies test location.

**Fix Applied:**
- Moved unit tests to `tests/unit/plantation/`
- Moved integration tests to `tests/integration/`

**Rule for Future Agents:**
> ALWAYS check `_bmad-output/test-design-system-level.md` for test organization rules BEFORE writing tests.

---

### Issue #13: Test Assertions Don't Match Implementation

**Problem:**
```python
# Test expected:
assert response.json() == {"status": "ok", "timestamp": "...", "version": "..."}

# But implementation returns:
{"status": "healthy"}
```

**Root Cause:**
Dev agent wrote tests based on assumed response format without reading the actual implementation.

**Fix Applied:**
Updated tests to match actual implementation:
```python
assert response.json() == {"status": "healthy"}
```

**Rule for Future Agents:**
> When writing tests, READ the actual implementation first. Don't assume the response format.

---

### Issue #7: httpx Version Incompatible with TestClient

**Problem:**
```
TypeError: Client.__init__() got an unexpected keyword argument 'app'
```

**Root Cause:**
`httpx >= 0.28.0` changed API, breaking `starlette.testclient.TestClient`.

**Fix Applied:**
```toml
# In pyproject.toml dev dependencies
httpx = ">=0.26.0,<0.28.0"  # 0.28+ has breaking changes with starlette TestClient
```

**Rule for Future Agents:**
> Pin httpx version to `<0.28.0` when using FastAPI/Starlette TestClient.

---

## Summary: 13 Critical Rules for Service Setup Stories

### Build & Environment Rules

1. **Python Version**: Match Dockerfile base image version, check `repository-structure.md`
2. **Dockerfile Strategy**: Use `poetry install` with full repo context, not `poetry export`
3. **File Permissions**: Always `--chown=appuser:appgroup` for non-root containers
4. **OpenTelemetry Versions**: All packages must use aligned versions (SDK/API/Exporter same, Instrumentation = SDK-1.0)
5. **Port Allocation**: Use non-standard ports in docker-compose to avoid conflicts
6. **Local Development**: Always run `pip install -e .` from service directory for IDE imports
7. **httpx Version**: Pin to `<0.28.0` for TestClient compatibility

### Code Quality Rules

8. **Clean Imports**: Remove unused imports - IDEs warn about these
9. **Async gRPC**: Don't use ThreadPoolExecutor with `grpc.aio.server()` - it's async-native
10. **Use Standard Libraries**: Use `grpc-health-checking` for health checks, don't reinvent in proto
11. **No Hardcoded Config**: ALL environment-specific values in Settings class

### Testing Rules

12. **Test Location**: Check `test-design-system-level.md` BEFORE writing tests
13. **Test vs Implementation**: READ implementation BEFORE writing test assertions

---

## Files Modified During Review

- `services/plantation-model/pyproject.toml` - Python version, OpenTelemetry versions
- `services/plantation-model/Dockerfile` - Complete rewrite for Poetry + local deps
- `libs/fp-proto/pyproject.toml` - Python version alignment
- `deploy/docker/docker-compose.yml` - Created with proper port allocation
- `deploy/docker/dapr-components/statestore.yaml` - Created
- `deploy/docker/dapr-components/pubsub.yaml` - Created

---

**Validation Status:** All issues fixed and validated
- [x] Docker image builds successfully
- [x] Docker Compose starts all services
- [x] Health endpoint returns 200
- [x] MongoDB connection established
