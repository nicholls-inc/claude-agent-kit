---
name: atlas
description: Switch main-session persona to atlas (plan execution coordinator mode).
---

# Switch Persona: Atlas

Set runtime `activePersona` to `atlas` in `.agent-kit/cc-omo/runtime.local.json` using inline execution.

## Execute
1. Ensure runtime file exists (create with `version=1` if needed).
2. Set `sessions.<session_or_global>.activePersona="atlas"`.
3. Preserve all existing ulw/boulder/ralph related fields.
4. Confirm persona switch and remind user to continue via `/omo:start-work` for active plans.

## Constraints
- Do not use `context: fork`.
