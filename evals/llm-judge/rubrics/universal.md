# Universal Evaluation Dimensions

Applied to every persona trace evaluation alongside persona-specific dimensions.

## Tool Usage Discipline (1-5)

- 1: Wrong tools for the task (e.g., Bash for file search instead of Glob), redundant calls, repeated identical queries
- 2: Multiple tool misuses or significant waste (>3 unnecessary calls)
- 3: Mostly correct tool selection but some unnecessary calls or suboptimal choices
- 4: Good tool selection with minor inefficiencies
- 5: Every tool call is appropriate for its purpose, no wasteful invocations

## Failure Handling (1-5)

- 1: Silent failure — returned incorrect results with high confidence, or gave up without explanation
- 2: Acknowledged failure but took no recovery action
- 3: Acknowledged failure but recovery was incomplete or superficial
- 4: Good failure handling — diagnosed the issue and attempted recovery
- 5: Graceful failure — diagnosed the issue, attempted targeted recovery, escalated to user if unrecoverable
