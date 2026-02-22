---
description: |
  Weekly maintenance of CLAUDE.md. Reviews merged pull requests and changed
  source files since the last run, then opens a pull request that keeps
  CLAUDE.md accurate and current.

on:
  schedule: weekly
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read

network: defaults

tools:
  github:
    toolsets: [repos, pull_requests]

safe-outputs:
  create-pull-request:
    max: 1

engine: claude
---

# Maintain CLAUDE.md

Keep the repository's `CLAUDE.md` file accurate and current by reviewing recent changes.

## Context

`CLAUDE.md` provides guidance to Claude Code when working in this repository. It documents:
- How to run the plugin locally
- Architecture of agents, skills, hooks, and the safe gate
- Model routing policy
- How to add new agents and skills
- Key conventions

When the codebase changes (new agents, renamed skills, updated hooks, changed conventions), `CLAUDE.md` must be updated to match.

## Process

1. **Gather recent changes**: Use the GitHub MCP tools to list pull requests merged into `main` since the last run of this workflow (approximately the last 7 days). Also review any direct pushes to `main` in that period.

2. **Read the current CLAUDE.md**: Read the full contents of `CLAUDE.md` from the repository.

3. **Read affected source files**: For each merged PR or commit, identify which files changed. Read the current versions of any changed files that are relevant to what CLAUDE.md documents:
   - `agents/*.md` (agent definitions)
   - `skills/*/SKILL.md` (skill definitions)
   - `hooks/hooks.json` (hook configuration)
   - `scripts/safe-gate.sh` (safe gate logic)
   - `docs/routing.md` (model routing policy)
   - `docs/agent-mapping.md` (agent inventory)
   - `README.md` (project overview)

4. **Determine if CLAUDE.md needs updates**: Compare the current CLAUDE.md against the source files. Look for:
   - New or removed agents/skills not reflected in CLAUDE.md
   - Changed model assignments or routing policy
   - Modified hook configurations or safe gate behavior
   - Updated conventions or architectural changes
   - Stale instructions that no longer match reality

5. **If no updates needed**: Call the `noop` tool with a message summarizing what was reviewed and confirming CLAUDE.md is current.

6. **If updates needed**:
   - Edit `CLAUDE.md` with the minimum changes required to make it accurate
   - Preserve the existing style and structure
   - Do not add fluff, generic advice, or documentation beyond what is already in scope
   - Do not remove information that is still accurate
   - Create a pull request with the changes using the `create-pull-request` safe output tool

## Pull request format

- **Branch name**: `maintain-claude-md/weekly-<date>` (use the current date in YYYY-MM-DD format)
- **Title**: Brief description of what changed, e.g. "Update CLAUDE.md: add new atlas agent, fix model routing"
- **Body**: List each change made and which source file motivated it

## Important

- Only update CLAUDE.md based on actual source file changes. Do not invent or speculate.
- Keep changes minimal and precise.
- If CLAUDE.md references a file that no longer exists, remove that reference.
- If a new agent or skill was added but is not mentioned, add it in the appropriate section following the existing format.
