# Agent Mapping

This document maps each agent in the plugin to its role, model, and namespace.

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
| Explore | code search | haiku | `claude-agent-kit:explore` |
| Librarian | external research | sonnet | `claude-agent-kit:librarian` |
| Oracle | advisor | opus | `claude-agent-kit:oracle` |
| Metis | pre-planning | opus | `claude-agent-kit:metis` |
| Momus | plan review | opus | `claude-agent-kit:momus` |

### Agents not yet ported

| Agent | Category | Original cost | Notes |
|---|---|---|---|
| Multimodal-Looker | vision/PDF | cheap | Pending multimodal support |

## Tool surface translation

| Reference | Claude Code equivalent |
|---|---|
| `Task(<agent-name>)` | Fork a specialist subagent via `context: fork` skills |
| Task/todo enforcement | Claude Code tasks (agent teams) or explicit checklists; optional hooks for gates |
| External tools | Replace with Claude Code tools: `Read`, `Edit`, `Write`, `Bash`, `Glob`, `Grep`, plus MCP tools |

## Prompt suitability notes

Common changes required when porting prompts:
- Use Claude Code tool names in all agent prompts.
- Replace background-task manager language with Claude Code subagent behavior (foreground/background limitations).
