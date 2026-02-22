# Agent mapping: oh-my-opencode -> Claude Code

This document maps each agent defined in the original oh-my-opencode roster to its Claude Code plugin equivalent.

## What is 1:1 here?

"1:1" means we preserve:
- role/purpose
- tool restrictions
- output structure
- cost intent (cheap vs expensive)

but we must adapt:
- OpenCode-only tools (e.g. `call_omo_agent`, `todowrite`)
- OpenCode-only lifecycle behaviors (some continuation/coordination hooks)

## Inventory

### Persona agents (main-session injection)

These agents define persona behavior injected into the main Claude Code session via hooks.

| Agent | Category | Model | Claude Code equivalent |
|---|---|---|---|
| Sisyphus | orchestrator | opus | `claude-agent-kit:sisyphus` |
| Hephaestus | executor/autonomous | opus | `claude-agent-kit:hephaestus` |
| Atlas | execution coordinator | sonnet | `claude-agent-kit:atlas` |
| Prometheus | planning | opus | `claude-agent-kit:prometheus` |

### Subagents (forked specialist workers)

These agents run as forked subagents via `Task()` or `context: fork` skills.

| Agent | Category | Model | Claude Code equivalent |
|---|---|---|---|
| Explore | code search | haiku | `claude-agent-kit:omo-explore` |
| Librarian | external research | sonnet | `claude-agent-kit:omo-librarian` |
| Oracle | advisor | opus | `claude-agent-kit:omo-oracle` |
| Metis | pre-planning | opus | `claude-agent-kit:omo-metis` |
| Momus | plan review | opus | `claude-agent-kit:omo-momus` |

### Agents not yet ported

These agents from the original roster do not have equivalents in this plugin yet.

| Agent | Category | Original cost | Notes |
|---|---|---|---|
| Multimodal-Looker | vision/PDF | cheap | Pending multimodal support |
| Sisyphus-Junior | focused executor | medium | Merged into sisyphus persona |
| Boulder | bounded finisher | medium | Replaced by hook-driven continuation |

## Tool surface translation

| oh-my-opencode reference | Claude Code equivalent |
|---|---|
| `call_omo_agent(subagent_type="explore"\|"librarian"\|...)` | `Task(<agent-name>)` (only available when running a main-thread agent) or `context: fork` skills |
| `todowrite` / task/todo enforcement | Claude Code tasks (agent teams) or explicit checklists; optional hooks for gates |
| OpenCode-specific tools | Replace with Claude Code tools: `Read`, `Edit`, `Write`, `Bash`, `Glob`, `Grep`, plus MCP tools |

## Prompt suitability notes

Common changes required when porting prompts:
- Remove references to OpenCode-only tools and replace with Claude Code tool names.
- Remove OpenCode-specific file editing constraints (e.g., apply_patch semantics) and keep the behavioral intent.
- Replace background-task manager language with Claude Code subagent behavior (foreground/background limitations).
