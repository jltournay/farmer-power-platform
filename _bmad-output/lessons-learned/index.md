# Lessons Learned Index

This folder contains lessons learned from code reviews, implementation issues, and best practices discovered during development. **Review these before implementing similar features.**

---

## Documents

| Story | Topic | Key Lessons |
|-------|-------|-------------|
| [Story 1.2](./story-1-2-code-review-findings.md) | Factory & CollectionPoint gRPC | Referential integrity, input validation, gRPC mock patterns, CRUD completeness |

---

## Quick Reference: Common Mistakes to Avoid

### gRPC Services

1. **Always implement full CRUD** - Don't forget Delete operations
2. **Enforce referential integrity** - Check for child entities before deleting parents
3. **Validate enum-like fields** - Use `INVALID_ARGUMENT` with clear error messages
4. **Mock context.abort correctly** - Use `side_effect=grpc.RpcError()`

### Testing

1. **Test ALL layers** - Domain models, repositories, AND gRPC service
2. **Verify test counts** - Run pytest before documenting counts
3. **Include test files in File List** - They're part of the deliverable

### Documentation

1. **Update File List immediately** - When creating new files
2. **Use git status** - At end of story to verify all files documented
3. **Cross-reference proto with implementation** - Ensure completeness

---

## gRPC Status Codes

| Scenario | Status Code |
|----------|-------------|
| Entity not found | `NOT_FOUND` |
| Duplicate unique field | `ALREADY_EXISTS` |
| Invalid field value | `INVALID_ARGUMENT` |
| Referential integrity violation | `FAILED_PRECONDITION` |
| Missing required field | `INVALID_ARGUMENT` |

---

## Adding New Lessons

When you discover issues during code review or implementation:

1. Create a new file: `story-X-Y-{topic}.md`
2. Document: Problem, Root Cause, Fix Applied, Prevention
3. Update this index with a link and key lessons summary
