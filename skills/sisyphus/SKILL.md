---
name: sisyphus
description: Switch main-session persona to sisyphus (orchestrator mode).
---

# Switch Persona: Sisyphus

Set runtime `activePersona` to `sisyphus` in `.agent-kit/cc-omo/runtime.local.json` using inline execution.

## Execute
1. Ensure runtime file exists (create with `version=1` if needed).
2. Set `sessions.<session_or_global>.activePersona="sisyphus"`.
3. Preserve all existing ulw/boulder/ralph related fields.
4. Confirm persona switch and mention you can switch again with `/omo:hephaestus`, `/omo:prometheus`, or `/omo:atlas`.

## Constraints
- Do not use `context: fork`.
