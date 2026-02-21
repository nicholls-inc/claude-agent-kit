---
name: boulder
description: One-shot loop: plan -> implement -> verify (Safe gate: lint + tests + build) until done or bounded failure.
disable-model-invocation: true
context: fork
agent: boulder
model: sonnet
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

Push the boulder for: $ARGUMENTS

Loop until success or hard limits:
- Max iterations: 5
- Max turns: (agent maxTurns)

Required loop:
1) Restate goal + acceptance criteria
2) Make a short plan
3) Implement incrementally
4) Verify using the Safe gate (lint + unit tests + build)
5) If failing: diagnose, fix, repeat

If you hit limits, stop with a failure report:
- What is still failing
- What you tried
- Most likely root cause
- Exact next steps for a human
