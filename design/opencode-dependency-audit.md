# OpenCode Dependency Audit (OMO -> Base CLI)

## Purpose

OMO is an OpenCode plugin. This document identifies which OMO capabilities fundamentally depend on OpenCode plugin APIs, and which can be re-expressed using Claude Code CLI plugin primitives.

Primary downstream use: populate the "OpenCode-only" column in `design/omo-to-cc-mapping.md`.

## External Sources (OpenCode)

- OpenCode repo: `https://github.com/anomalyco/opencode`
- OpenCode plugin SDK: `https://github.com/anomalyco/opencode/tree/main/packages/plugin`

## High-Level Dependency Areas

| Capability Area | Why OMO needs OpenCode | OMO evidence | Portability to CC |
| --- | --- | --- | --- |
| Plugin entrypoint | OpenCode `Plugin` factory receives `ctx` (client, directory, etc.) | `src/index.ts` | CC plugin has different manifest + loading; must re-implement initialization via plugin components |
| Custom tool registry | OMO registers 26 tools via OpenCode plugin tool API | `src/plugin/tool-registry.ts`, `src/tools/*` | CC cannot add native tools; must use MCP + skills/hooks |
| Message transforms | OMO relies on `experimental.chat.messages.transform` for injection/validation | `src/plugin/messages-transform.ts`, `src/plugin/chat-message.ts` | CC has hooks, but not identical transform semantics; must use `UserPromptSubmit` / `SessionStart` + PreToolUse |
| Model override plumbing | OMO overrides variant/model per message/agent | `src/plugin/ultrawork-model-override.ts` | CC model selection is explicit; hidden override is non-portable |
| TUI feedback | OMO uses `ctx.client.tui.showToast` for feedback | `src/plugin/chat-message.ts` | CC has notifications/hook system; no toast API parity (approx via systemMessage or logs) |
| Session manager tooling | OMO adds session list/read/search/info tools | `src/tools/session-manager/*` | CC has transcripts + resume; session tool parity likely via skills reading transcript files |

## Non-Portable "Hard" Items

1. **Hidden ultrawork model override**
   - OMO uses a deferred SQLite DB mutation strategy to change the model used for the API call while leaving the UI model indicator unchanged.
   - Evidence: `src/plugin/ultrawork-model-override.ts` (deferred DB path) and `src/plugin/ultrawork-db-model-override.ts`.
   - CC: non-portable; must make model selection explicit.

2. **First-class tool additions**
   - OMO can add tools directly to the tool palette.
   - Evidence: `src/plugin/tool-registry.ts`.
   - CC: must use MCP for new tools.

3. **Transform-tier hooks**
   - OMO has a first-class message transform pipeline.
   - Evidence: `src/plugin/messages-transform.ts` and `create-transform-hooks.ts` (see `src/plugin/AGENTS.md`).
   - CC: must approximate with `UserPromptSubmit` and `PreToolUse` hooks, and with skills.

## Likely Portable (Re-expressible) Items

| OMO capability | OMO evidence | Why portable | CC equivalent |
| --- | --- | --- | --- |
| State artifacts (plans/boulder/notepads) | `src/features/boulder-state/*` | Filesystem-based state | Repo files + CC hooks/skills |
| Orchestration semantics (plan->execute) | `docs/orchestration-guide.md` | Behavioral contract | Skills + subagents + hooks |
| Delegation patterns | `docs/guide/understanding-orchestration-system.md` | Prompt-level procedure | CC subagents + skills fork |
| Tmux integration idea | `docs/configurations.md` | OS-level integration | CC plugin scripts (optional) |

## Notes

- CC hooks provide stronger/cleaner blocking semantics than OpenCode in some areas (exit 2, structured PreToolUse decisions), but CC lacks a general-purpose message transform pipeline.
- OMO's task system is modeled after Claude Code's Task tool signatures but implemented independently in OpenCode; CC already has Task semantics.
