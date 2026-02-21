---
name: explore
description: Fast, read-only repo exploration. Use for "where is X?", "what does Y do?", and finding related files without making changes.
context: fork
agent: Explore
model: haiku
allowed-tools: Read, Grep, Glob, Bash
---

Explore the codebase for: $ARGUMENTS

Return:
1) Files to read next (short list)
2) Key findings (bullet points)
3) Open questions / unknowns (if any)

Constraints:
- Read-only. Do not propose edits.
