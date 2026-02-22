# Plugin State Schema

This file defines the canonical state keys used by `scripts/*.sh` and `skills/*`.

## Versioning

- `version` is an integer.
- Unknown versions must fail open (allow Stop; do not block).

## `.agent-kit/boulder.json`

```json
{
  "version": 1,
  "active": true,
  "planPath": ".agent-kit/plans/<slug>.md",
  "status": "in_progress",
  "currentTask": { "number": 1, "label": "Task title" },
  "updatedAt": "2026-02-22T19:00:00Z"
}
```

Rules:
- `active=false` or `status=done` means continuation should not be enforced from boulder.
- Missing/corrupt boulder must fail open.

## `.agent-kit/state/runtime.local.json`

```json
{
  "version": 1,
  "sessions": {
    "global": {
      "activePersona": "sisyphus",
      "ulw": {
        "enabled": false,
        "stopBlocks": 0,
        "lastStopEpoch": 0,
        "lastStopAt": null,
        "updatedAt": null
      },
      "stopContinuation": {
        "disabled": false,
        "disabledReason": null,
        "disabledAt": null
      }
    }
  }
}
```

Session key strategy:
- Prefer `session_id` from hook input.
- Fallback key: `global`.

Persona values:
- `sisyphus` (default)
- `hephaestus`
- `prometheus`
- `atlas`

## `.agent-kit/ralph-loop.local.md`

```md
# ralph-loop

status: active
created_at: 2026-02-22T19:00:00Z
max_iterations: 8
iterations: 0

goal: |
  <user goal>

done_marker: "RALPH_DONE"
```

Rules:
- Stop hook treats `status: active` as continuation-active.
- If done marker is observed, mark inactive and allow Stop.
- If `iterations >= max_iterations`, mark inactive and allow Stop.
