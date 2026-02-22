---
name: stop-continuation
description: Global escape hatch to stop all automated continuation mechanisms.
---

# Stop Continuation

Set global/session continuation disable flags and deactivate active loop states.

## Execute
1. Update `.sisyphus/cc-omo/runtime.local.json`:
   - `version=1`
   - `sessions.<session_or_global>.stopContinuation.disabled=true`
   - `sessions.<session_or_global>.stopContinuation.disabledReason="manual escape hatch"`
   - `sessions.<session_or_global>.stopContinuation.disabledAt=<now>`
   - `sessions.<session_or_global>.ulw.enabled=false`
2. If `.sisyphus/ralph-loop.local.md` exists, set `status: cancelled`.
3. If `.sisyphus/boulder.json` exists, set `active=false`, `status="done"`, `updatedAt=<now>`.
4. Return a short confirmation that Stop will no longer be blocked.

## Constraints
- Never require manual file edits.
- Keep this inline (non-fork skill).
