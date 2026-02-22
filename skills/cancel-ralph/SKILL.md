---
name: cancel-ralph
description: Cancel the currently active Ralph Loop.
---

# Cancel Ralph

Deactivate the loop state so Stop hook no longer enforces Ralph continuation.

## Execute
1. If `.sisyphus/ralph-loop.local.md` exists, set `status: cancelled`.
2. Keep previous loop metadata for auditability.
3. Print a short confirmation that Ralph continuation is disabled.

## Constraints
- Never require manual edits.
- Keep this inline (non-fork skill).
