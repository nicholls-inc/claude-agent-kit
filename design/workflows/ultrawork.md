# Workflow: Ultrawork (CC Plugin)

## Intent

Recreate OMO's "ultrawork" mode in Claude Code (CC) CLI:
- A small trigger that flips the session into a disciplined "continue until done" execution mode.
- Parallel leaf-worker research to keep the coordinator context lean.
- Verification gates (tests/build/lsp) before declaring done.

Hard constraints (from CC):
- No hidden model override.
- Subagents cannot spawn subagents.
- Background subagents cannot use MCP tools.

## Trigger

Ultrawork is enabled by either:

1. **Keyword**: prompt contains `ulw` or `ultrawork` as a standalone word.
2. **Command**: user runs `/omo:ulw`.

## Hook Participation

### `UserPromptSubmit` (keyword detector)

Command hook runs for every prompt. If keyword is detected:
- Print an ultrawork instruction block to stdout (this becomes injected context).

Output rule:
- For `UserPromptSubmit`, stdout should be **plain text**, not JSON (stdout is injected as context).

### `Stop` (continuation enforcer)

When ultrawork is active and work is incomplete, return JSON to block stopping:

```json
{
  "decision": "block",
  "reason": "Ultrawork active: continuing until verification gates pass or stop requested"
}
```

CC parses this JSON (exit 0) and continues the conversation.

## Coordinator Loop (forced by ultrawork instruction)

When ultrawork is active, the coordinator follows this loop:

1. **Exploration burst (parallel)**
   - Spawn 2-5 leaf workers using `Task` for: codebase discovery and pattern-finding.
   - If external docs/OSS examples are needed, run librarian in the foreground (background subagents cannot use MCP).

2. **Plan an execution slice**
   - Pick 1-3 atomic changes with explicit verification.

3. **Execute + persist**
   - Make changes.
   - Update state/checklists if part of an active plan.

4. **Verify**
   - Run the checks specified by the task (tests/build/typecheck).
   - Fix failures and re-run until passing or documented as pre-existing.

5. **Exit condition**
   - Only allow Stop when work is complete and verification gates pass (or are explicitly recorded).

## State

Ultrawork needs minimal durable state for circuit breakers.

Recommended gitignored repo-local state file:
- `.sisyphus/cc-omo/runtime.local.json`

Minimum schema (keyed by `session_id`):

```json
{
  "sessions": {
    "abc123": {
      "ulw": {
        "enabled": true,
        "stopBlocks": 3,
        "lastStopAt": "2026-02-22T17:20:01Z"
      },
      "stopContinuation": {
        "disabled": false,
        "disabledReason": null
      }
    }
  }
}
```

## Circuit Breakers (required)

- **Max Stop blocks per session** (default 8).
- **Cooldown** between Stop blocks (default 3s).
- **Escape hatch**: `/omo:stop-continuation` sets `stopContinuation.disabled=true`.
- **Fail-open**: if state is unreadable, Stop hook must allow stopping.

## Verification Scenarios

1. Keyword injection: prompt includes `ulw`; injected instruction appears.
2. Stop continuation: Stop blocks while incomplete (bounded by max).
3. Escape hatch: `/omo:stop-continuation` disables Stop blocking.
