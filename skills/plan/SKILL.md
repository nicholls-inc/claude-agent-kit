---
name: plan
description: Create a durable, reviewable implementation plan for a complex task.
---

# Plan

Generate a checklist plan and initialize boulder state.

## Execute
1. Create `.agent-kit/plans/` if missing.
2. Generate slug from `$ARGUMENTS` and current date.
3. Write `.agent-kit/plans/<slug>.md` with sections:
   - Context
   - Tasks (`- [ ] 1. ...`)
   - Verification
4. Write `.agent-kit/boulder.json`:
   - `version=1`
   - `active=true`
   - `status="in_progress"`
   - `planPath=".agent-kit/plans/<slug>.md"`
   - `currentTask` set to first unchecked task
   - `updatedAt=<now>`
5. Print: plan path, current task, and reminder to run `/claude-agent-kit:start-work`.

## Constraints
- Planning output should be markdown-first.
- Keep this inline (non-fork skill).
