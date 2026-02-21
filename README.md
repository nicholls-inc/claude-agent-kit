# claude-agent-kit

Claude Code plugin that ports the oh-my-opencode agent roster (as close to 1:1 as practical) using Anthropic models (Haiku/Sonnet/Opus).

## Try locally

From this repository root:

```bash
claude --plugin-dir ./claude-agent-kit --debug
```

Then in Claude Code:
- `/help` to see skills
- `/agents` to see agents
- `/mcp` to see MCP servers (and authenticate if needed)

## What you get

Agents (under `/agents`):
- `claude-agent-kit:sisyphus`
- `claude-agent-kit:hephaestus`
- `claude-agent-kit:oracle` (read-only)
- `claude-agent-kit:librarian` (read-only)
- `claude-agent-kit:explore` (read-only)
- `claude-agent-kit:multimodal-looker` (read-only)
- `claude-agent-kit:metis` (read-only)
- `claude-agent-kit:momus` (read-only)
- `claude-agent-kit:atlas`
- `claude-agent-kit:prometheus` (read-only)
- `claude-agent-kit:sisyphus-junior`
- `claude-agent-kit:boulder` (bounded finisher; plugin-specific)

Skills (under `/claude-agent-kit:*`):
- Workflows: `/claude-agent-kit:explore`, `/claude-agent-kit:plan`, `/claude-agent-kit:implement`, `/claude-agent-kit:review`, `/claude-agent-kit:boulder`
- Agent entrypoints: `/claude-agent-kit:sisyphus`, `/claude-agent-kit:hephaestus`, `/claude-agent-kit:oracle`, `/claude-agent-kit:librarian`, `/claude-agent-kit:explore-agent`, `/claude-agent-kit:multimodal-looker`, `/claude-agent-kit:metis`, `/claude-agent-kit:momus`, `/claude-agent-kit:atlas`, `/claude-agent-kit:prometheus`, `/claude-agent-kit:sisyphus-junior`
- Management: `/claude-agent-kit:configure`, `/claude-agent-kit:team-templates`

Docs:
- `docs/routing.md`
- `docs/agent-mapping.md`

## Boulder safe gate (lint/test/build)

`/claude-agent-kit:boulder ...` runs in a forked `boulder` subagent context.

When `boulder` tries to stop, a plugin `SubagentStop` hook runs:
- `scripts/safe-gate.sh`

If the gate fails, the hook exits 2, and Claude Code prevents the `boulder` subagent from stopping.

### Customizing the gate

Option A: environment variable (semicolon-separated):

```bash
export CLAUDE_AGENT_KIT_SAFE_GATE_COMMANDS='bun run lint; bun test; bun run build'
```

Option B: project config file (in repo root): `claude-agent-kit.safe-gate.json`

```json
{
  "commands": ["bun run lint", "bun test", "bun run build"]
}
```

If neither is provided, the gate attempts to use `package.json` scripts `lint`, `test`, and `build`.

## MCP servers

This plugin includes `.mcp.json` with a GitHub MCP server definition. You may need to authenticate in Claude Code:
- `/mcp` -> authenticate

If you do not want plugin MCP servers running, disable them via your Claude Code settings or remove `.mcp.json`.

## Namespacing

Plugin skills are namespaced. A skill named `review` will show up as:

- `/claude-agent-kit:review`

Agents are namespaced in the `/agents` UI as:

- `claude-agent-kit:<agent-name>`

## Troubleshooting

- Plugin loads but no skills/agents: ensure `agents/` and `skills/` are at plugin root, not under `.claude-plugin/`.
- Hooks not firing: ensure `scripts/safe-gate.sh` is executable.
- MCP server not connected: open `/mcp`, check plugin servers, and authenticate if required.
- Stale plugin changes: bump version in `.claude-plugin/plugin.json` if you distribute via a marketplace (Claude Code caches installed plugins).
