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
  - `/claude-agent-kit:sisyphus`
  - `/claude-agent-kit:hephaestus`
  - `/claude-agent-kit:prometheus`
  - `/claude-agent-kit:atlas`

## Evidence
- Write logs under `.agent-kit/evidence/<area>/<scenario>.log`.
- Include command output snippets and pass/fail result per scenario.

## Constraints
- Never spawn `claude` via Bash.
- Prefer deterministic checks and file evidence over human inspection.
