---
name: plan
description: Create a durable, reviewable implementation plan for a complex task.
---

# Plan

Generate a checklist plan and initialize boulder state.

## Execute
1. Create `.sisyphus/plans/` if missing.
2. Generate slug from `$ARGUMENTS` and current date.
3. Write `.sisyphus/plans/<slug>.md` with sections:
   - Context
   - Tasks (`- [ ] 1. ...`)
   - Verification
4. Write `.sisyphus/boulder.json`:
   - `version=1`
   - `active=true`
   - `status="in_progress"`
   - `planPath=".sisyphus/plans/<slug>.md"`
   - `currentTask` set to first unchecked task
   - `updatedAt=<now>`
5. Print: plan path, current task, and reminder to run `/omo:start-work`.

## Constraints
- Planning output should be markdown-first.
- Keep this inline (non-fork skill).
