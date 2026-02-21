# Agent mapping: oh-my-opencode -> Claude Code

This document maps each agent defined in `src/agents/` in this repository to its Claude Code plugin equivalent.

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

Source of truth: `src/agents/AGENTS.md`

| Agent | Category | Intended cost | Claude Code equivalent |
|---|---|---|---|
| Sisyphus | orchestrator | expensive | `claude-agent-kit:sisyphus` |
| Hephaestus | executor/autonomous | expensive | `claude-agent-kit:hephaestus` |
| Oracle | advisor | expensive | `claude-agent-kit:oracle` |
| Librarian | external research | cheap | `claude-agent-kit:librarian` |
| Explore | code search | free | `claude-agent-kit:explore` |
| Multimodal-Looker | vision/PDF | cheap | `claude-agent-kit:multimodal-looker` |
| Metis | pre-planning | expensive | `claude-agent-kit:metis` |
| Momus | plan review | expensive | `claude-agent-kit:momus` |
| Atlas | task/todo orchestration | expensive | `claude-agent-kit:atlas` |
| Prometheus | planning | expensive | `claude-agent-kit:prometheus` |
| Sisyphus-Junior | focused executor | medium | `claude-agent-kit:sisyphus-junior` |

Additional (not in the original 11-agent roster):

| Agent | Category | Intended cost | Claude Code equivalent |
|---|---|---|---|
| Boulder | bounded finisher | medium | `claude-agent-kit:boulder` |

## Tool surface translation

| oh-my-opencode reference | Claude Code equivalent |
|---|---|
| `call_omo_agent(subagent_type="explore"|"librarian"|...)` | `Task(<agent-name>)` (only available when running a main-thread agent) or `context: fork` skills |
| `todowrite` / task/todo enforcement | Claude Code tasks (agent teams) or explicit checklists; optional hooks for gates |
| OpenCode-specific tools | Replace with Claude Code tools: `Read`, `Edit`, `Write`, `Bash`, `Glob`, `Grep`, plus MCP tools |

## Prompt suitability notes

Common changes required when porting prompts:
- Remove references to OpenCode-only tools and replace with Claude Code tool names.
- Remove OpenCode-specific file editing constraints (e.g., apply_patch semantics) and keep the behavioral intent.
- Replace background-task manager language with Claude Code subagent behavior (foreground/background limitations).
