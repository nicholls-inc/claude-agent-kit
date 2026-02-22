---
name: hephaestus
description: Switch main-session persona to hephaestus (deep autonomous execution mode).
---

# Switch Persona: Hephaestus

Set runtime `activePersona` to `hephaestus` in `.sisyphus/cc-omo/runtime.local.json` using inline execution.

## Execute
1. Ensure runtime file exists (create with `version=1` if needed).
2. Set `sessions.<session_or_global>.activePersona="hephaestus"`.
3. Preserve all existing ulw/boulder/ralph related fields.
4. Confirm persona switch and mention revert options.

## Constraints
- Do not use `context: fork`.
