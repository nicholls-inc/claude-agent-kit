# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What This Is

A Claude Code plugin that ports the oh-my-opencode (OMO) multi-agent roster to Anthropic-only models. Pure-markdown plugin — no build step, no dependencies, no compiled code. All agents, skills, hooks, and docs are plain `.md` or `.json` files.

## Running Locally

```bash
claude --plugin-dir ./claude-agent-kit --debug
```

## Testing

```bash
./tests/validate.sh
```

Validates: agent/skill frontmatter, `hooks.json` schema, shell script correctness, and bidirectional consistency between `agents/*.md` and `docs/agent-mapping.md`. Exits 0 on success, 1 on failure. Runs in CI via `.github/workflows/validate.yml`.

## Architecture

### Agents (`agents/*.md`)

Each file has YAML frontmatter (`name`, `description`, `model`, `tools`, `maxTurns`) and a markdown system prompt body. Namespaced as `claude-agent-kit:<agent-name>`.

Two categories:
- **Persona agents** (main-session injection via hooks): `sisyphus` (opus, orchestrator), `hephaestus` (opus, autonomous executor), `atlas` (sonnet, execution coordinator), `prometheus` (opus, planner).
- **Subagents** (forked specialists): `omo-explore` (haiku, code search), `omo-librarian` (sonnet, external research), `omo-oracle` (opus, architecture advisor), `omo-metis` (opus, pre-planning), `omo-momus` (opus, plan review).

### Skills (`skills/*/SKILL.md`)

Each has YAML frontmatter (`name`, `description`) and a prompt template. Namespaced as `/claude-agent-kit:<skill-name>`. Use `$ARGUMENTS` for user input.

Categories:
- **Persona switches** (`sisyphus`, `hephaestus`, `atlas`, `prometheus`): Set `activePersona` in runtime state.
- **Workflow** (`plan`, `start-work`): Create plans under `.sisyphus/plans/` and execute from boulder state.
- **Continuation control** (`ulw`, `ralph-loop`, `stop-continuation`, `cancel-ralph`): Manage autonomous execution loops.
- **Utilities** (`handoff`, `selftest`): Context transfer and self-testing.

### Hooks (`hooks/hooks.json`)

Four hooks, all dispatched through `scripts/hook-router.sh`:
- **SessionStart**: Injects active persona prompt + boulder resume context.
- **UserPromptSubmit**: Injects persona prompt + detects ultrawork (ULW) triggers.
- **PreToolUse**: Blocks destructive Bash commands; blocks code edits in `prometheus` persona.
- **Stop**: Blocks agent stop when boulder/ralph/ULW continuation is active (up to 8 blocks, then auto-disables).

### State Management (`.sisyphus/`)

Runtime state files (gitignored, not part of the plugin itself):
- `boulder.json`: Active plan tracking (`active`, `status`, `planPath`, `currentTask`).
- `plans/*.md`: Markdown checklists created by `/omo:plan`.
- `cc-omo/runtime.local.json`: Session state (`activePersona`, ULW flags, stop counters).
- `ralph-loop.local.md`: Iteration-bounded continuation loop state.

### Scripts (`scripts/`)

- `hook-router.sh`: Central hook dispatcher (fail-open on errors).
- `detect-ulw.sh`: Pattern-matches user prompts for ultrawork triggers.
- `sanitize-hook-input.sh`: Safe stdin JSON parsing for hooks.
- `state-read.sh` / `state-write.sh`: JSON file I/O helpers.

### Model Routing (`docs/routing.md`)

All Anthropic-only:
- **haiku**: high-volume search/exploration (omo-explore)
- **sonnet**: implementation, coordination (atlas, omo-librarian)
- **opus**: architecture, planning, deep review (sisyphus, hephaestus, prometheus, omo-oracle, omo-metis, omo-momus)

## Adding a New Agent

1. Create `agents/<name>.md` with required frontmatter: `name`, `description`, `model`, `tools`, `maxTurns`.
2. Add to `docs/agent-mapping.md` inventory table.
3. Follow model routing policy in `docs/routing.md`.
4. Optionally create a matching `skills/<name>/SKILL.md` entrypoint.

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` with required frontmatter: `name`, `description`.
2. Use `$ARGUMENTS` in the prompt body for user input.
3. Optional frontmatter keys: `model`, `context` (e.g. `fork` to run in a forked subagent), `agent` (paired with `context: fork`), `allowed-tools`, `disable-model-invocation` (set `true` for manual-only skills).

## Key Conventions

- Agent prompts must use Claude Code tool names (`Read`, `Edit`, `Write`, `Bash`, `Grep`, `Glob`, `Task`, `WebFetch`) — never OpenCode-specific tools.
- Read-only agents use `disallowedTools: Edit, Write` and/or `permissionMode: plan`.
- Project-local settings go in `.claude/settings.local.json`, never global user settings.
- All shell scripts must have `#!/usr/bin/env bash`, `set -euo pipefail`, and be executable (`chmod +x`).
- Hook router is fail-open: on any error, it logs to stderr and exits 0 (never blocks the user).
