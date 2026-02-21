---
name: configure
description: Configure recommended settings for model routing, agent teams, and MCP visibility. Manual invocation only.
disable-model-invocation: true
allowed-tools: Read, Edit, Write, Bash
---

Configure Claude Code for this plugin.

Recommended defaults (user chooses):
- Default model: Sonnet (`/model sonnet`)
- Available models allowlist: `haiku`, `sonnet`, `opus`
- (Optional) enable agent teams: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

If editing settings files, prefer `.claude/settings.local.json` (project-local) and do not modify global user settings unless explicitly requested.

Also:
- Show how to verify plugin MCP servers with `/mcp`.
