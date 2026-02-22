# Selftest Harness (Agent-Executable)

## Goal

Validate Tier A (and key Tier B) behaviors inside a single Claude Code session.

Hard guardrail:
- Do not invoke `claude` via Bash or hooks.

## Evidence Convention

Write evidence under:
- `.sisyphus/evidence/cc-omo-parity/<area>/<scenario>.log`

## Scenario: Plugin Loads

Scenario: Plugin Loads

Steps:
1. Run `/plugin validate`.
2. Run `/plugin errors`.

Expected:
- validate passes; no errors.

## Scenario: Keyword Ultrawork Injection

Scenario: Keyword Ultrawork Injection

Steps:
1. Send: `ulw write a 2-line hello world script`.
2. Confirm ultrawork instruction injection (via behavior or `/debug`).

Expected:
- injection occurs.

## Scenario: Escape Hatch

Scenario: Escape Hatch

Steps:
1. Start a continuation state (active boulder or ralph-loop).
2. Run `/omo:stop-continuation`.

Expected:
- Stop is no longer blocked.

## Scenario: Plan Creation

Scenario: Plan Creation

Steps:
1. Run `/omo:plan "Create a tiny plan"`.
2. Verify `.sisyphus/plans/` contains a new file.
3. Verify `.sisyphus/boulder.json` exists and points to it.

Expected:
- plan + boulder created.

## Scenario: Start Work Resume

Scenario: Start Work Resume

Steps:
1. With an active `.sisyphus/boulder.json`, run `/omo:start-work`.
2. Confirm it reads boulder and begins at `currentTask`.

Expected:
- execution resumes from boulder.

## Scenario: Ralph Loop Start/Cancel

Scenario: Ralph Loop Start/Cancel

Steps:
1. Run `/omo:ralph-loop "Do a trivial non-destructive task"`.
2. Confirm `.sisyphus/ralph-loop.local.md` exists.
3. Run `/omo:cancel-ralph`.

Expected:
- state created; then cancelled.

## Scenario: PreToolUse Guard (Destructive Bash)

Scenario: PreToolUse Guard (Destructive Bash)

Steps:
1. Attempt: `rm -rf /tmp/should-not-run`.
2. Confirm PreToolUse hook denies.

Expected:
- tool call blocked.
