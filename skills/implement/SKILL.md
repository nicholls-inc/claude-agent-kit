---
name: implement
description: Implement a change with verification (tests/build). Manual invocation only.
disable-model-invocation: true
model: sonnet
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

Implement: $ARGUMENTS

Rules:
- Prefer minimal diffs.
- Match existing code conventions.
- Run relevant verification commands (at least one). If unclear, run the project's standard test command.
- Do not commit unless explicitly requested.

Finish with:
- Files changed
- Commands run + result
