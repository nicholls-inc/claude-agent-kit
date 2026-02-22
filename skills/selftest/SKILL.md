---
name: selftest
description: Validate Tier A behaviors inside a single Claude Code session.
---

# Selftest

Run the documented parity harness and write evidence files.

## Scenarios (must be executed)
- Plugin Loads
- Keyword Ultrawork Injection
- Escape Hatch
- Plan Creation
- Start Work Resume
- Ralph Loop Start/Cancel
- PreToolUse Guard (Destructive Bash)
- Persona switching checks:
  - `/omo:sisyphus`
  - `/omo:hephaestus`
  - `/omo:prometheus`
  - `/omo:atlas`

## Evidence
- Write logs under `.sisyphus/evidence/cc-omo-parity/<area>/<scenario>.log`.
- Include command output snippets and pass/fail result per scenario.

## Constraints
- Never spawn `claude` via Bash.
- Prefer deterministic checks and file evidence over human inspection.
