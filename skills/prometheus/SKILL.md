---
name: prometheus
description: Switch main-session persona to prometheus (planning discipline).
---

# Switch Persona: Prometheus

Set runtime `activePersona` to `prometheus` in `.agent-kit/cc-omo/runtime.local.json` using inline execution.

## Execute
1. Ensure runtime file exists (create with `version=1` if needed).
2. Set `sessions.<session_or_global>.activePersona="prometheus"`.
3. Preserve all existing ulw/boulder/ralph related fields.
4. Confirm planner-only discipline: markdown planning artifacts under `.agent-kit/` unless user explicitly requests execution.

## Constraints
- Do not use `context: fork`.
- Keep planning markdown-focused.
