---
description: 'Create a GitHub issue from a story file for code-to-story traceability'
---

IT IS CRITICAL THAT YOU FOLLOW THESE STEPS:

<steps CRITICAL="TRUE">
1. Always LOAD the FULL @_bmad/bmm/tasks/create-github-issue.xml
2. READ its entire contents - this contains the complete task instructions
3. Execute ALL steps in the task flow IN EXACT ORDER
4. Use GitHub MCP tools (mcp__github__*) for all GitHub operations
5. Update the story file with the new issue number when complete
</steps>

## Quick Usage

This task creates a GitHub issue from a BMAD story file and links them for traceability.

**What it does:**
- Discovers or uses provided story file
- Creates GitHub issue with story content
- Adds labels (story, epic-N)
- Updates story file with issue reference
- Updates sprint-status.yaml if present

**Commit format after issue is created:**
```
feat: Description of change

Relates to #<issue-number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
