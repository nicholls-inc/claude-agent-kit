---
name: review
description: Read-only code review of current changes (git diff) with prioritized feedback. Manual invocation only.
disable-model-invocation: true
model: opus
allowed-tools: Read, Grep, Glob, Bash
---

Review the current working tree changes.

Steps:
1) Run `git status` and `git diff`.
2) Focus on changed files.

Return feedback by priority:
- Critical (must fix)
- Warnings (should fix)
- Suggestions (nice to have)

Do not edit files.
