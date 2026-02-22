# CC Plugin Spec: `omo`

## Purpose

Concrete file-by-file spec for the Claude Code plugin that implements the Tier A workflows.

## Plugin Tree

```
omo/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── omo-explore.md
│   ├── omo-librarian.md
│   ├── omo-oracle.md
│   ├── omo-metis.md
│   └── omo-momus.md
├── skills/
│   ├── ulw/
│   │   └── SKILL.md
│   ├── plan/
│   │   └── SKILL.md
│   ├── start-work/
│   │   └── SKILL.md
│   ├── ralph-loop/
│   │   └── SKILL.md
│   ├── cancel-ralph/
│   │   └── SKILL.md
│   ├── stop-continuation/
│   │   └── SKILL.md
│   ├── handoff/
│   │   └── SKILL.md
│   └── selftest/
│       └── SKILL.md
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── hook-router.sh
│   ├── detect-ulw.sh
│   ├── state-read.sh
│   ├── state-write.sh
│   └── sanitize-hook-input.sh
└── .mcp.json  # optional
```

## Manifest: `.claude-plugin/plugin.json`

```json
{
  "name": "omo",
  "version": "0.1.0",
  "description": "OMO-style orchestration workflows for Claude Code CLI",
  "hooks": "./hooks/hooks.json"
}
```

## Hooks: `hooks/hooks.json`

Required hook events:
- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `Stop`

All events route to `${CLAUDE_PLUGIN_ROOT}/scripts/hook-router.sh`.

## Scripts (contracts)

- `scripts/hook-router.sh`: the only hook entrypoint; reads stdin JSON and emits either injected context text (SessionStart/UserPromptSubmit) or decision JSON (PreToolUse/Stop).
- `scripts/detect-ulw.sh`: keyword detection helper.
- `scripts/state-read.sh` / `scripts/state-write.sh`: atomic reads/writes for `.sisyphus/boulder.json` and `.sisyphus/cc-omo/runtime.local.json`.
- `scripts/sanitize-hook-input.sh`: defensive filtering of hook input fields.

## Skills (contracts)

- `/omo:ulw`: sets ultrawork enabled flag in runtime state.
- `/omo:plan`: writes plan + initializes boulder.
- `/omo:start-work`: executes boulder tasks until done.
- `/omo:ralph-loop`: initializes loop state.
- `/omo:cancel-ralph`: cancels loop state.
- `/omo:stop-continuation`: disables Stop-hook enforcement.
- `/omo:handoff`: writes a continuation summary file.
- `/omo:selftest`: runs through `design/selftest.md` scenarios without spawning `claude`.

## Agents (contracts)

Agents are leaf workers only (no nested orchestration).

- `agents/omo-explore.md`: codebase discovery; read-only tools.
- `agents/omo-librarian.md`: docs/OSS research; read-only repo tools plus WebFetch/MCP.
- `agents/omo-oracle.md`: read-only reviewer.
- `agents/omo-metis.md`: plan gap analysis.
- `agents/omo-momus.md`: plan reviewer (OKAY/REJECT).
