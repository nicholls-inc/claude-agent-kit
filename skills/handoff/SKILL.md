---
name: handoff
description: Create a detailed context summary for continuing work in a new session.
---

# Handoff

Write a deterministic handoff file for continuation.

## Execute
1. Create `.agent-kit/handoff/` if missing.
2. Write `.agent-kit/handoff/last.md` containing:
   - active plan path
   - current task
   - unresolved errors (if known)
   - resume command: `/claude-agent-kit:start-work`
   - escape hatch: `/claude-agent-kit:stop-continuation`
3. Avoid secrets or raw hook payloads.
4. Print the handoff path and concise summary.

## Constraints
- Keep this inline (non-fork skill).
