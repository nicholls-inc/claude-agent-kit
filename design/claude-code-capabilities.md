# Claude Code CLI Capabilities For OMO Parity

## Scope

This document summarizes Claude Code CLI primitives relevant to recreating oh-my-opencode (OMO) via a Claude Code plugin.

Non-goals:
- Claude Code Agent Teams (explicitly excluded).

Primary source: `https://code.claude.com/docs/en/plugins-reference` and linked pages.

## Plugin System

Claude Code plugins are self-contained directories that can bundle:
- Subagents (`agents/*.md`)
- Skills (`skills/<name>/SKILL.md`) and legacy commands (`commands/*.md`)
- Hooks (`hooks/hooks.json` or inline in `.claude-plugin/plugin.json`)
- MCP servers (`.mcp.json` or inline in manifest)
- LSP server configs (`.lsp.json` or inline)
- Default settings (`settings.json`) (currently: agent settings only)

Important path rule:
- Plugin scripts must be referenced via `${CLAUDE_PLUGIN_ROOT}` because marketplace-installed plugins are copied to a cache (cannot traverse outside the plugin root).

## Hooks

Hooks are event handlers (shell command, prompt, or agent verifier) that run at lifecycle points.

Events we care about for OMO parity (core):
- `UserPromptSubmit`: runs when user submits prompt, before Claude processes it. Stdout is injected as context.
- `PreToolUse`: before a tool executes; can block or redirect tool calls via structured JSON output.
- `PostToolUse` / `PostToolUseFailure`: after tool success/failure; cannot undo the tool outcome.
- `Stop`: runs when Claude finishes responding; can block stopping (continuation).
- `SubagentStart` / `SubagentStop`: observe/control lifecycle.
- `SessionStart` / `SessionEnd`: setup/teardown; SessionStart stdout is injected as context.
- `PreCompact`: compaction hook.
- `ConfigChange`: reacts to config changes; can block the change.
- `WorktreeCreate` / `WorktreeRemove`: integrate with worktrees.

Ordering caveat:
- All matching hooks run in parallel, and identical handlers are deduplicated.
- Ordering-sensitive behavior should be centralized into one hook handler (a "hook router" script) that runs sub-steps sequentially.

Decision control caveat:
- Not all events support a structured "block" decision via JSON; some rely only on exit codes (notably `TaskCompleted`, `TeammateIdle`).

Stdout injection caveat:
- In general, stdout from command hooks is only visible in verbose mode, except for `UserPromptSubmit` and `SessionStart`, where stdout is injected into context.

## Subagents

Subagents are specialized agents defined as markdown files with YAML frontmatter.

Key constraints we must design around:
- Subagents cannot spawn other subagents (no nested orchestration).
- Background subagents run concurrently but:
  - They must have permissions pre-approved (they cannot ask clarifying questions interactively).
  - MCP tools are not available in background subagents.

Implications for OMO parity:
- Keep orchestration in the main thread (or a coordinator agent running as main).
- Use subagents as leaf workers for isolated exploration/research/review.
- Any MCP-backed tool parity should run in the foreground (or via main thread), not background subagents.

Useful knobs:
- Tool allowlist/denylist: `tools:` and `disallowedTools:`
- Permission mode: `permissionMode:` (e.g., `plan` for read-only)
- Hooks scoped to a subagent via frontmatter.
- Persistent memory directories via `memory: user|project|local`.
- Worktree isolation: `isolation: worktree` (auto-cleanup when no changes).

## Skills (Slash Commands)

Skills are directories containing `SKILL.md`. They create `/name` commands.

Key capabilities:
- Control invocation: `disable-model-invocation: true` prevents Claude from auto-invoking (manual-only).
- Tool scoping: `allowed-tools:` can grant tool access while skill active.
- Fork execution: `context: fork` runs the skill in a separate subagent context; `agent:` selects which subagent type.
- Scoped hooks via frontmatter `hooks:`.
- Argument interpolation via `$ARGUMENTS` and positional `$ARGUMENTS[N]`.

Key constraint:
- If a skill runs in fork context, it must contain an actionable task prompt. Pure reference skills should run inline.

## MCP (Tool Extension)

Claude Code cannot add new native tools directly.
MCP is the supported mechanism to add custom tool capabilities.

Plugins can bundle MCP servers via `.mcp.json` or inline in `plugin.json`.
- Plugin MCP servers start automatically when the plugin is enabled.
- Plugin MCP server changes generally require a Claude Code restart to apply.

Operational notes:
- MCP tools show as `mcp__<server>__<tool>` in tool events and permissions.
- Tool Search can dynamically load MCP tool defs when too many are present (env: `ENABLE_TOOL_SEARCH`).
- Large MCP outputs can trigger warnings; output limits are configurable (env: `MAX_MCP_OUTPUT_TOKENS`).

## Permissions + Sandboxing

Permissions:
- Configured via `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, and managed settings.
- Rules are evaluated in order: deny -> ask -> allow.
- Permission modes exist: `default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`.

Sandboxing:
- OS-level enforcement for Bash. Network allowlist via sandbox `network.allowedDomains` plus `WebFetch` permission rules.

Security implications for OMO parity:
- Hooks/scripts must treat stdin JSON as untrusted.
- PreToolUse is the right place to block or constrain destructive Bash patterns.

## Hard Limits / Non-Portable OMO Behaviors (early)

- No hidden model override: CC plugin cannot silently change model used while preserving the UI indicator.
- No nested orchestration: subagents cannot spawn subagents.
- Background + MCP incompatibility: MCP is not available to background subagents.
