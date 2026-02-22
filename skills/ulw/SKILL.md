---
name: ulw
description: Enable ultrawork mode - a disciplined "continue until done" execution mode with parallel research and verification gates.
---

# Ultrawork (ulw)

Enable ultrawork in runtime state and proceed with strict execution discipline.

## Execute
1. Ensure `.sisyphus/cc-omo/` exists.
2. Read `.sisyphus/cc-omo/runtime.local.json` (or `{}` if missing).
3. Set:
   - `version=1`
   - `sessions.<session_or_global>.ulw.enabled=true`
   - `sessions.<session_or_global>.ulw.updatedAt=<now>`
   - `sessions.<session_or_global>.ulw.reason="$ARGUMENTS"` when non-empty
4. Preserve existing `stopBlocks` and `stopContinuation` fields.
5. Confirm with a short response that ultrawork is enabled and remind user about `/omo:stop-continuation`.

## Constraints
- Never attempt hidden model override.
- Keep this inline (non-fork skill).
- Use `.sisyphus/cc-omo/runtime.local.json` as state of truth.
