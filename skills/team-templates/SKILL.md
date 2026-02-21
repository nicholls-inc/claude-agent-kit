---
name: team-templates
description: Copy-pasteable agent team templates (experimental). Manual invocation only.
disable-model-invocation: true
---

Agent teams are experimental and higher-cost (multiple independent Claude instances).

Enable:
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

Templates

1) Debugging with competing hypotheses

Prompt:
"""
Start an agent team with 3 teammates:
- Teammate A: forms hypothesis, finds repro and likely root cause
- Teammate B: searches codebase for related patterns and past fixes
- Teammate C: proposes minimal fix + verification plan

All teammates default to Sonnet unless they have a strong reason to use Opus.
Goal: $ARGUMENTS
"""

2) Review team (security + performance + testing)

Prompt:
"""
Start an agent team with 3 teammates:
- Security reviewer (read-only)
- Performance reviewer (read-only)
- Test/CI reviewer (read-only)

All teammates use Sonnet by default.
Review target: $ARGUMENTS
"""

3) Feature split (frontend + backend + tests)

Prompt:
"""
Start an agent team with 3 teammates:
- Frontend implementer
- Backend implementer
- Tests/verification owner

All teammates default to Sonnet.
Feature: $ARGUMENTS
"""
