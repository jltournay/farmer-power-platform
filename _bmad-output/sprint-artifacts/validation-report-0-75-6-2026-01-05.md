# Validation Report

**Document:** `_bmad-output/sprint-artifacts/0-75-6-cli-manage-prompt-type-configuration.md`
**Checklist:** `_bmad/bmm/workflows/4-implementation/create-story/checklist.md`
**Date:** 2026-01-05

## Summary

- **Overall:** 16/19 items passed (84%)
- **Critical Issues:** 3

## Section Results

### Acceptance Criteria Coverage
Pass Rate: 19/19 (100%)

✓ All 19 acceptance criteria are clearly defined with IDs (AC1-AC19)
✓ Each AC maps to specific tasks
✓ Testable and measurable criteria

### Tasks Completeness
Pass Rate: 14/18 tasks fully specified (78%)

✓ **Task 1-12:** Well-defined with clear subtasks
✓ **Task 13-15:** Test tasks clearly specified
✓ **Task 16-18:** CI tasks correctly defined

⚠ **PARTIAL - Task 3: MongoDB Client**
Evidence: Line 53-58 mentions "reuse PromptRepository pattern" but doesn't specify that the CLI should NOT import from ai_model service directly (dependency direction issue).
Impact: Developer might create wrong dependency direction.

✗ **FAIL - Missing: Agent existence check method**
Evidence: Lines 71-72 say "Query `agent_configs` collection to verify agent_id exists" but don't specify WHICH method to use.
Impact: The `agent_id` in prompts collection is like "diagnose-quality-issue", but AgentConfigRepository's `get_by_id` expects document ID format "agent_id:version". Need to use `get_active(agent_id)` instead.

### Architecture Guidance
Pass Rate: 8/9 (89%)

✓ CLI Standards table present (lines 315-324)
✓ Prompt-Agent validation rules documented (lines 326-348)
✓ File structure after story defined (lines 361-378)
✓ Dependencies table with versions (lines 381-389)
✓ Anti-patterns to avoid table (lines 461-471)
✓ What's NOT in scope table (lines 473-480)

⚠ **PARTIAL - Branch naming inconsistency**
Evidence: Line 182 says `story/0-75-6-...` but the feature branch created was `feature/0-75-6-...`
Impact: Developer may use inconsistent naming.

### Disaster Prevention
Pass Rate: 4/5 (80%)

✓ "CRITICAL: Reuse Existing Prompt Model" section (lines 275-290)
✓ Anti-patterns table prevents common mistakes
✓ References section with source documents

✗ **FAIL - Missing: Sample YAML fixture content**
Evidence: Task 4 (line 63) mentions validating YAML but no sample YAML provided in story.
Impact: Developer must guess YAML format; may create incorrect test fixtures.

### LLM Optimization
Pass Rate: 3/4 (75%)

✓ Clear section headings and structure
✓ Actionable task lists with checkboxes
✓ Code examples for key patterns

⚠ **PARTIAL - Verbose in places**
Evidence: Some guidance is repeated (e.g., validation rules appear in both AC and Dev Notes)
Impact: Token waste when dev agent processes story.

---

## Critical Issues (Must Fix)

### 1. ✗ Agent Validation Query Method Ambiguous

**Current:** Lines 71-72 say "Query `agent_configs` collection to verify agent_id exists"

**Problem:** Ambiguous. The prompt's `agent_id` field (e.g., "diagnose-quality-issue") doesn't match the document `_id` format (e.g., "diagnose-quality-issue:1.0.0").

**Correct approach:**
```python
# Use get_active() which queries by agent_id field, not document _id
agent = await agent_config_repo.get_active(prompt.agent_id)
```

**Recommendation:** Add explicit guidance on using `get_active(agent_id)` method.

---

### 2. ✗ Missing Sample YAML Fixture

**Current:** Story mentions YAML validation but provides no example YAML file.

**Problem:** Developer must infer YAML structure from Pydantic model.

**Recommendation:** Add sample YAML to Dev Notes:
```yaml
# Sample: tests/fixtures/prompt_config/valid-prompt.yaml
prompt_id: disease-diagnosis
agent_id: diagnose-quality-issue
version: "1.0.0"
status: draft

content:
  system_prompt: |
    You are an expert tea disease diagnostician...
  template: |
    Analyze the following quality event: {{event_data}}
  output_schema:
    type: object
    properties:
      condition: { type: string }
      confidence: { type: number }

metadata:
  author: test-user
  changelog: Initial version
```

---

### 3. ⚠ Branch Naming Inconsistency

**Current:** Line 182 uses `story/0-75-6-...` but actual branch is `feature/0-75-6-...`

**Recommendation:** Standardize to `story/` prefix to match the documentation OR update documentation to match `feature/` convention.

---

## Enhancement Opportunities (Should Add)

### 1. Add pyproject.toml Template

Based on `scripts/source-config/pyproject.toml` pattern, add explicit example:

```toml
[project]
name = "fp-prompt-config"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "motor>=3.3.0",
]

[project.scripts]
fp-prompt-config = "fp_prompt_config.cli:app"
```

### 2. Add --dry-run Flag

The `fp-source-config` CLI has `--dry-run` for deploy command. Consider adding for consistency.

### 3. Clarify MongoDB Transaction Pattern

Task 9 (Promote) mentions "Transaction" but motor requires explicit session handling:

```python
async with await client.start_session() as session:
    async with session.start_transaction():
        await archive_current_active(session)
        await promote_staged(session)
```

### 4. Add conftest.py Fixture Pattern

No existing `tests/unit/scripts/` conftest.py exists. Add guidance:

```python
# tests/unit/scripts/prompt_config/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_prompt_client():
    """Mock PromptClient for CLI tests."""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    return client
```

---

## LLM Optimizations (Nice to Have)

### 1. Consolidate Repeated Validation Rules

Lines 326-348 repeat information from AC10-11. Consider cross-referencing instead.

### 2. Inline File Paths in Tasks

Instead of separate "File Structure" section, put file paths directly in tasks for faster developer reference.

---

## Recommendations Summary

| Priority | Item | Action |
|----------|------|--------|
| **Must Fix** | Agent validation method | Specify `get_active(agent_id)` not `get_by_id()` |
| **Must Fix** | Sample YAML fixture | Add complete example YAML |
| **Must Fix** | Branch naming | Standardize to `story/` or update to `feature/` |
| **Should Add** | pyproject.toml template | Copy from source-config pattern |
| **Should Add** | --dry-run flag | Consistency with source-config CLI |
| **Should Add** | Transaction pattern | Motor session example for promote/rollback |
| **Consider** | Consolidate repeated info | Reduce token usage |

---

## Conclusion

The story is **well-structured** with comprehensive acceptance criteria and task breakdown. The three critical issues identified are fixable with targeted edits. After applying the "Must Fix" items, the story will provide unambiguous guidance for the developer agent.
