# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin that ports the oh-my-opencode multi-agent roster to Anthropic-only models. It is a pure-markdown plugin — no build step, no dependencies, no compiled code. All agents, skills, hooks, and docs are plain `.md` or `.json` files.

## Running Locally

```bash
claude --plugin-dir ./claude-agent-kit --debug
```

## Architecture

### Agents (`agents/*.md`)

Each file is a self-contained agent definition with YAML frontmatter (`name`, `model`, `tools`, `permissionMode`, `maxTurns`) and a markdown system prompt body. Agents are namespaced as `claude-agent-kit:<agent-name>`.

Key roles:
- **sisyphus** (opus): Top-level orchestrator — plans, delegates to specialists, verifies.
- **hephaestus** (opus): Autonomous executor — "just get it done" with verification.
- **boulder** (sonnet): Bounded one-shot finisher — loops plan/implement/verify up to 5 iterations with a SubagentStop hook enforcing a Safe gate (lint+test+build).
- **oracle** (opus, read-only): Architecture advisor and self-review. Called when stuck or after significant changes.
- **explore** (haiku, read-only): Fast file discovery and codebase search.
- **librarian** (sonnet, read-only): External docs and real-world examples.

### Skills (`skills/*/SKILL.md`)

Each subdirectory contains a `SKILL.md` with YAML frontmatter (`name`, `model`, `context`, `agent`, `allowed-tools`, `disable-model-invocation`) and a prompt template. Skills are namespaced as `/claude-agent-kit:<skill-name>`.

Two categories:
- **Workflow skills** (`explore`, `plan`, `implement`, `review`, `boulder`): Composable steps — explore the codebase, plan a change, implement it, review it, or do all three in a bounded loop.
- **Agent entrypoint skills**: Thin wrappers that fork into a named agent (e.g., `skills/boulder/SKILL.md` has `context: fork` + `agent: boulder`).
- **Management skills** (`configure`, `team-templates`): Setup helpers, not auto-invoked (`disable-model-invocation: true`).

### Hooks (`hooks/hooks.json`)

Plugin hook definitions. Currently one hook:
- **SubagentStop** on `boulder`: runs `scripts/safe-gate.sh` before the boulder agent can stop. Exit code 2 blocks the stop, forcing boulder to fix failures.

### Safe Gate (`scripts/safe-gate.sh`)

The lint/test/build gate enforced on boulder. Command discovery priority:
1. `CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS` env var (semicolon-separated)
2. `claude-agent-kit.safe-gate.json` config file (`{ "commands": [...] }`)
3. Auto-detect from `package.json` scripts (`lint`, `test`, `build`) using the detected package manager

Requires at least 3 commands. Must be executable (`chmod +x`).

### Model Routing (`docs/routing.md`)

All models are Anthropic-only. The mapping:
- **haiku**: high-volume search/exploration (Explore agent)
- **sonnet**: implementation, day-to-day work, cost-sensitive execution (Boulder, Atlas, Sisyphus-Junior)
- **opus / opusplan**: architecture, deep review, planning (Sisyphus, Oracle, Metis, Momus, Prometheus)

## Adding a New Agent

1. Create `agents/<name>.md` with required frontmatter: `name`, `description`, `model`, `tools`, `maxTurns`.
2. Optionally create `skills/<name>/SKILL.md` as an entrypoint (use `context: fork` + `agent: <name>` to run in a forked subagent).
3. Add to `docs/agent-mapping.md` inventory table.
4. Follow the model routing policy in `docs/routing.md` for model selection.

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` with required frontmatter: `name`, `description`.
2. Use `$ARGUMENTS` in the prompt body for user input.
3. Set `disable-model-invocation: true` for skills that should only be manually invoked.

## Key Conventions

- Agent prompts should not reference OpenCode-specific tools — use Claude Code tool names (`Read`, `Edit`, `Write`, `Bash`, `Grep`, `Glob`, `Task`, `WebFetch`).
- Read-only agents use `disallowedTools: Edit, Write` and/or `permissionMode: plan`.
- The `context: fork` skill frontmatter key runs the skill in a forked subagent context rather than the main thread.
- Project-local settings go in `.claude/settings.local.json`, never global user settings.
