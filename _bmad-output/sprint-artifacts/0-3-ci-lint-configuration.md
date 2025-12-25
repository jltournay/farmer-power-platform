# Story 0.3: CI Lint Configuration Unification

**Status:** ready-for-dev

---

## Story

As a **developer**,
I want unified linting configuration across all pyproject.toml files,
So that CI lint checks pass consistently and code quality is enforced automatically.

---

## Context

**From Story 0-2 Implementation:**
- CI lint job was disabled because of conflicting ruff configurations
- Multiple pyproject.toml files have different settings
- Service-specific configs use deprecated `[tool.ruff]` `select` instead of `[tool.ruff.lint]` `select`
- Different line-length settings (100 vs 120) across projects
- Missing per-file-ignores for gRPC method naming (N802) and generated proto files

**Problem:**
- 57+ lint errors when running `ruff check .`
- CI cannot enforce code quality without unified configuration
- Developers may introduce inconsistent code style

---

## Acceptance Criteria

1. **Given** multiple pyproject.toml files exist
   **When** ruff runs from project root
   **Then** a unified configuration is applied from root pyproject.toml

2. **Given** generated proto files exist in `libs/fp-proto/`
   **When** ruff runs
   **Then** they are excluded from linting (F403, ERA001, ARG002)

3. **Given** gRPC service files use PascalCase method names
   **When** ruff runs
   **Then** N802 is ignored for these files

4. **Given** the lint job is enabled in CI
   **When** a PR is opened
   **Then** ruff check passes without errors

5. **Given** the lint job completes
   **When** all checks pass
   **Then** the CI pipeline succeeds

---

## Tasks / Subtasks

- [ ] **Task 1: Audit pyproject.toml files** (AC: #1)
  - [ ] 1.1 List all pyproject.toml files with ruff settings
  - [ ] 1.2 Document current settings and conflicts
  - [ ] 1.3 Identify which settings should be centralized

- [ ] **Task 2: Consolidate ruff configuration** (AC: #1, #2, #3)
  - [ ] 2.1 Remove `[tool.ruff]` and `[tool.ruff.lint]` from service pyproject.toml files
  - [ ] 2.2 Update root pyproject.toml with comprehensive configuration
  - [ ] 2.3 Add `extend` or `extend-exclude` patterns if needed
  - [ ] 2.4 Standardize line-length to 120 across all projects

- [ ] **Task 3: Configure exclusions** (AC: #2, #3)
  - [ ] 3.1 Exclude generated proto files (`*_pb2.py`, `*_pb2_grpc.py`)
  - [ ] 3.2 Add per-file-ignores for proto `__init__.py` files (F403, F401)
  - [ ] 3.3 Add N802 ignore for gRPC service files (PascalCase methods)
  - [ ] 3.4 Configure test file ignores (ARG, RUF059, ERA001)

- [ ] **Task 4: Fix remaining lint errors** (AC: #4)
  - [ ] 4.1 Run `ruff check .` and capture errors
  - [ ] 4.2 Fix auto-fixable errors with `ruff check . --fix`
  - [ ] 4.3 Manually fix remaining errors
  - [ ] 4.4 Run `ruff format --check .` and fix formatting

- [ ] **Task 5: Re-enable CI lint job** (AC: #4, #5)
  - [ ] 5.1 Uncomment lint job in `.github/workflows/ci.yaml`
  - [ ] 5.2 Add lint to `needs` array in `all-tests-pass` job
  - [ ] 5.3 Verify lint job uses correct Python version

- [ ] **Task 6: Verify CI passes** (AC: #5)
  - [ ] 6.1 Push changes and verify CI pipeline
  - [ ] 6.2 Fix any remaining issues
  - [ ] 6.3 Update story status to done

---

## Dev Notes

### Current Lint Errors (57+)

```
- N802: gRPC method names (GetFactory, ListFarmers, etc.) - should ignore
- E501: Line too long - conflicting line-length settings
- F403: Star imports in proto __init__.py - should ignore
- ERA001: Commented code in proto files - should ignore
- RUF059: Unused unpacked variables in tests - should ignore
- B017: Blind exception in tests - should ignore or fix
- TC001: Type-checking imports - should fix
- F841: Unused variables - should fix
```

### Configuration Strategy

**Option 1 (Recommended): Root-only configuration**
- Remove all ruff settings from service pyproject.toml files
- Configure everything in root pyproject.toml
- Ruff will automatically use root config for all subdirectories

**Option 2: Extend pattern**
- Keep minimal settings in service files
- Use `extend = "../../pyproject.toml"` to inherit from root
- Override only what's necessary

### Files to Modify

```
pyproject.toml                              # Root - comprehensive config
services/plantation-model/pyproject.toml    # Remove ruff section
mcp-servers/plantation-mcp/pyproject.toml   # Remove ruff section
libs/fp-common/pyproject.toml               # Check for ruff section
libs/fp-proto/pyproject.toml                # Check for ruff section
libs/fp-testing/pyproject.toml              # Check for ruff section
.github/workflows/ci.yaml                   # Re-enable lint job
```

### Recommended Root Configuration

```toml
[tool.ruff]
target-version = "py312"
line-length = 120
fix = true

exclude = [
    "libs/fp-proto/src/fp_proto/**/*_pb2.py",
    "libs/fp-proto/src/fp_proto/**/*_pb2_grpc.py",
]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM", "TCH", "PTH", "ERA", "RUF"]
ignore = [
    "E501",   # Line too long (handled by formatter)
    "B008",   # Function calls in defaults
    "B904",   # Raise without from
    "ARG001", # Unused function argument
    "N802",   # gRPC method names are PascalCase
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["ARG", "S101", "RUF059", "ERA001", "B017"]
"libs/fp-proto/src/fp_proto/**/__init__.py" = ["F403", "F401"]
```

---

## Technical Decisions

1. **Root-only config** - Simpler to maintain than extending
2. **Line-length 120** - Matches existing root config
3. **Exclude proto files** - Generated code shouldn't be linted
4. **Per-file-ignores for tests** - Test patterns differ from prod code

---

## Out of Scope

- Adding pre-commit hooks (separate story if needed)
- Adding mypy to CI (already complex enough)
- Formatting changes beyond what ruff --fix does

---

## References

- Root pyproject.toml: `pyproject.toml`
- CI workflow: `.github/workflows/ci.yaml`
- Story 0-2: `_bmad-output/sprint-artifacts/0-2-mongodb-integration-testing.md`
- GitHub Issue: #15
