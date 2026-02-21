# Model routing policy

This plugin is designed to use the right Anthropic model for the job.

## Default stance

- Keep the main session on `sonnet` for most work.
- Delegate high-volume discovery/search to `haiku`.
- Use `opus` (or `opusplan`) for deep planning, architecture, and high-risk reviews.

## Model mapping

| Model | Use for | Avoid for |
|---|---|---|
| `haiku` | codebase exploration, file discovery, lightweight summarization, running noisy checks in a forked context | architecture decisions, tricky debugging |
| `sonnet` | implementation, refactors, writing tests, day-to-day work | extremely ambiguous/high-stakes decisions |
| `opus` | architecture, hard debugging, deep review, pre-planning critique | high-volume grep-style scanning |
| `opusplan` | planning workflows (plan mode -> execution) | long implementation runs |

## Special workflow agent

- `boulder` uses `sonnet` by default to control cost while still being capable. If it struggles on a domain-level design decision, it should consult `oracle` (opus) rather than switching itself.

## Substituting original oh-my-opencode models

oh-my-opencode uses multiple providers/models. In Claude Code we map these roles onto Anthropic-only models:

| Original agent | Original model (repo) | Claude Code model |
|---|---|---|
| Sisyphus | `claude-opus-4-6` | `opus` |
| Hephaestus | `gpt-5.3-codex` | `opus` (or `sonnet` when cost-sensitive) |
| Oracle | `gpt-5.2` | `opus` |
| Librarian | `glm-4.7` | `sonnet` |
| Explore | `grok-code-fast-1` | `haiku` |
| Multimodal-Looker | `gemini-3-flash` | `sonnet` |
| Metis | `claude-opus-4-6` | `opus` |
| Momus | `gpt-5.2` | `opus` |
| Atlas | `claude-sonnet-4-6` | `sonnet` |
| Prometheus | `claude-opus-4-6` | `opus` / `opusplan` |
| Sisyphus-Junior | `claude-sonnet-4-6` | `sonnet` |

Notes:
- Claude Code built-in `Explore` agent already uses `haiku`.
- The plugin's `explore` agent is kept as `haiku` to preserve the repo's intent, but you may prefer the built-in Explore in some cases.
