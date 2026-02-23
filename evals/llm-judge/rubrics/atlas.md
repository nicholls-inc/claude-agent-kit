# Atlas Persona Evaluation Rubric

Evaluate whether this session followed the Atlas execution coordinator contract.

Contract: "Resume from boulder state and execute current task slice. Advance plan
checkboxes and boulder progress after each completed slice. Enforce verification
before completion. Keep continuation bounded and escapable."

Score each dimension 1-5:

## Boulder State Adherence (1-5)

- 1: Ignored boulder state entirely, started fresh work unrelated to the plan
- 2: Read boulder but worked on a different task than currentTask
- 3: Read boulder but didn't fully align execution to current task
- 4: Correctly aligned to boulder state with minor deviations
- 5: Correctly resumed from boulder state, worked on the exact current task, detected state divergence when present

## Task Advancement (1-5)

- 1: Never updated plan checkboxes or boulder state
- 2: Updated one but not the other
- 3: Updated checkboxes but forgot to advance boulder.json
- 4: Updated both but with minor errors
- 5: Consistently updated both plan checkboxes and boulder.json after each task

## Verification Gate (1-5)

- 1: Marked tasks complete without any verification
- 2: Mentioned verification but didn't actually run it
- 3: Some verification but inconsistent across tasks
- 4: Mostly verified before marking complete
- 5: Every task verified with deterministic checks before being marked complete

## Bounded Execution (1-5)

- 1: Ran unbounded, needed manual stop, exceeded step/token budget
- 2: Overshot significantly, worked on multiple tasks when should have done one
- 3: Mostly bounded but overshot on some tasks
- 4: Good bounded execution with minor overruns
- 5: Executed exactly one task slice, advanced state, and stopped cleanly (or continued within bounds respecting step budget)

## Tool Usage Discipline (1-5)

See universal.md for full rubric.

## Failure Handling (1-5)

See universal.md for full rubric.
