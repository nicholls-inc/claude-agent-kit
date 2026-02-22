---
name: ralph-loop
description: Start a self-referential development loop that runs until task completion.
---

# Ralph Loop

Create loop state and activate Stop-hook continuation for the loop.

## Execute
1. Write `.agent-kit/ralph-loop.local.md`:
   - `status: active`
   - `created_at: <now>`
   - `max_iterations: 8`
   - `iterations: 0`
   - `goal: |\n  $ARGUMENTS`
   - `done_marker: "RALPH_DONE"`
2. Confirm the done marker string (`RALPH_DONE`) to use on completion.
3. Remind user that `/omo:cancel-ralph` and `/omo:stop-continuation` are escape hatches.

## Constraints
- Never require manual file editing to stop the loop.
- Keep this inline (non-fork skill).
