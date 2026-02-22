---
name: start-work
description: Resume and execute tasks from an active implementation plan.
---

# Start Work

Resume from active boulder state and execute tasks in order.

## Execute
1. Read `.sisyphus/boulder.json`.
2. If missing/inactive/done, return deterministic guidance: run `/omo:plan <goal>`.
3. If active:
   - open `planPath`
   - locate `currentTask`
   - execute the next task slice
   - update the plan checklist and `currentTask`
   - set `updatedAt=<now>`
4. Done condition:
   - when all checklist tasks are complete, write `status="done"` and `active=false` in boulder.
5. Keep orchestration main-thread only; delegate leaf work to leaf subagents only.

## Constraints
- Do not use nested orchestration.
- Keep this inline (non-fork skill).
