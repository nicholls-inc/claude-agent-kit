# Workflow: Plan -> Start Work (CC Plugin)

## Intent

Recreate OMO's Prometheus (planning) + Atlas (/start-work execution) split:
- Planning produces a durable, reviewable artifact.
- Execution resumes from a durable state file across session restarts.

## User-Facing Commands

- `/omo:plan` (planner)
- `/omo:start-work` (executor)
- `/omo:handoff` (optional continuation summary)
- `/omo:stop-continuation` (escape hatch)

## Artifacts (repo state of truth)

- `.sisyphus/plans/<plan-slug>.md` (plan)
- `.sisyphus/boulder.json` (resume anchor)
- `.sisyphus/notepads/<plan-slug>/...` (optional evidence/notes)
- `.sisyphus/cc-omo/runtime.local.json` (gitignored: counters, circuit breakers)

## Plan Format

`/omo:plan` should generate a checklist-style plan.

```md
# <Plan Title>

## Context
- goal: ...
- constraints: ...

## Tasks
- [ ] 1. ...
- [ ] 2. ...

## Verification
- [ ] <command>
- [ ] <command>
```

## Boulder State File

`.sisyphus/boulder.json` points at the active plan and progress.

Recommended schema:

```json
{
  "version": 1,
  "active": true,
  "planPath": ".sisyphus/plans/2026-02-22-cc-omo-parity.md",
  "status": "in_progress",
  "currentTask": { "number": 1, "label": "Define plugin-spec.md" },
  "updatedAt": "2026-02-22T17:25:00Z"
}
```

Rules:
- If `active=false` or `status=done`, Stop hook must not enforce continuation.
- If the plan file is missing, executor must fail safe (disable `active`).

## Execution Flow

### `/omo:plan`

1. Run in planning discipline (`permissionMode: plan`).
2. Write `.sisyphus/plans/<slug>.md`.
3. Initialize `.sisyphus/boulder.json` to `active=true` and `status=in_progress`.

### `/omo:start-work`

1. Read `.sisyphus/boulder.json`.
2. If missing/inactive -> deterministic guidance (usually: run `/omo:plan`).
3. If active -> execute tasks in order, updating:
   - the plan checklist
   - `currentTask` in boulder
   - verification evidence under `.sisyphus/notepads/<plan>/...` (optional)
4. When finished -> set `status=done`, `active=false`.

### Resume Injection (`SessionStart`)

On session start/resume, if boulder is active, inject a short resume block:
- plan path
- current task
- reminder of `/omo:stop-continuation`

### Continuation Enforcement (`Stop`)

If boulder is active and stop-continuation is not disabled, Stop hook blocks stopping until executor updates boulder to done.
Circuit breakers apply.

## Verification Scenarios

1. Plan creation writes plan + boulder.
2. Session restart injects resume context.
3. Start-work resumes and advances state.
4. Stop hook blocks while active and stops blocking when done.
