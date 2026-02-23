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

## Agent model assignments

| Agent | Claude Code model |
|---|---|
| Sisyphus | `opus` |
| Hephaestus | `opus` (or `sonnet` when cost-sensitive) |
| Oracle | `opus` |
| Librarian | `sonnet` |
| Explore | `haiku` |
| Metis | `opus` |
| Momus | `opus` |
| Atlas | `sonnet` |
| Prometheus | `opus` / `opusplan` |

Notes:
- Claude Code built-in `Explore` agent already uses `haiku`.
- The plugin's `explore` agent is kept as `haiku` for consistency, but you may prefer the built-in Explore in some cases.
