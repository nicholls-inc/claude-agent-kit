# Workflow: Ralph Loop (Stop-hook Continuation)

## Intent

Provide a robust, bounded continuation loop that keeps working across responses until a stop condition is met.

In CC this is implemented as:
- a command (`/omo:ralph-loop`) that initializes loop state
- a `Stop` hook that blocks stopping while the loop is active

## User-Facing Commands

- `/omo:ralph-loop <goal...>`: start loop
- `/omo:cancel-ralph`: cancel loop
- `/omo:stop-continuation`: global escape hatch

## State

Gitignored repo-local file:
- `.agent-kit/ralph-loop.local.md`

Example format:

```md
# ralph-loop

status: active
created_at: 2026-02-22T17:30:00Z
max_iterations: 8
iterations: 0

goal: |
  Fix failing tests in the repo.

done_marker: "RALPH_DONE"
```

## Start Behavior (`/omo:ralph-loop`)

1. Write `.agent-kit/ralph-loop.local.md` with `status: active` and the `goal`.
2. Instruct the coordinator to emit `RALPH_DONE` when finished.

## Stop-hook Behavior

On `Stop`:
- If stop-continuation is disabled -> allow Stop.
- If loop state missing/not active -> allow Stop.
- If the assistant message contains `RALPH_DONE` -> mark loop inactive and allow Stop.
- If iterations >= max -> mark loop inactive and allow Stop.
- Otherwise -> increment iteration count and block Stop:

```json
{ "decision": "block", "reason": "Ralph loop active: continuing" }
```

Safety:
- Fail open on parse errors.
- Always honor `/omo:stop-continuation`.

## Cancel Behavior (`/omo:cancel-ralph`)

Set `status: cancelled` (or delete the file). Stop hook treats it as inactive.

## Verification Scenarios

1. Start loop creates state.
2. Stop blocks while active.
3. Cancel allows Stop.
4. Done marker ends loop.
