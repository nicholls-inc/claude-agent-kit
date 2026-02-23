# Claude Code CLI Plugin Architecture (OMO Parity)

## Overview

We implement OMO parity in Claude Code (CC) CLI by expressing OMO’s system as:
- A **plugin** that ships **skills**, **subagents**, **hooks**, and optionally **MCP servers**.
- A **main-thread coordinator** implemented primarily as **skills** (because CC subagents cannot spawn subagents).
- A set of **leaf subagents** that do isolated work (Explore/Librarian/Oracle-like roles).
- A small set of **state files** in the repository to preserve continuity across session restarts.

This architecture intentionally does NOT attempt to:
- Replace CC’s default agent globally.
- Perform hidden model overrides.
- Spawn additional Claude Code processes.

## Plugin Name and Namespacing

Assume plugin name: `omo`.

All user-invocable commands will be namespaced (e.g., `/omo:start-work`). This is a known Tier C parity gap.

## Plugin Layout

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
│   ├── selftest/
│   │   └── SKILL.md
│   └── handoff/
│       └── SKILL.md
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── hook-router.sh
│   ├── detect-ulw.sh
│   ├── state-read.sh
│   ├── state-write.sh
│   └── sanitize-hook-input.sh
├── .mcp.json            # optional
├── .lsp.json            # optional
└── settings.json        # optional (agent settings only)
```

## State and Persistence

OMO parity requires session continuity independent of chat memory.

Repository state (project scope):
- `.agent-kit/plans/*.md` (plan files; checklist-driven)
- `.agent-kit/boulder.json` (active plan pointer + progress metadata)
- `.agent-kit/notepads/<plan>/...` (learnings/decisions/issues/verification)
- `.agent-kit/ralph-loop.local.md` (loop state; gitignored)
- `.agent-kit/cc-omo/runtime.local.json` (continuation circuit breakers; gitignored)

In CC, we also optionally use:
- `.claude/agent-memory/<agent>/` (if we enable subagent memory)

Design choice: **state-of-truth is repo files**, not CC internal task UI, to preserve portability.

## Orchestration Pattern

### Main-thread coordination

The coordinator is implemented as **skills** that run in the main thread (not `context: fork`) so they can use:
- `Task(...)` to spawn leaf subagents
- edit/write tools when permitted

Leaf subagents:
- `omo-explore`: Read/Grep/Glob/Bash only
- `omo-librarian`: WebFetch + MCP (foreground only), plus read-only repo tools
- `omo-oracle`: Read-only review/advice
- `omo-metis`: plan gap analysis
- `omo-momus`: plan review loop

### Background tasks

Use CC background subagents for:
- internal code search (Explore)
- long-running test commands via Bash (if allowed)

Do not rely on MCP tools in background subagents.

## Hooks Strategy

### Why a hook router

CC runs matching hooks in parallel and deduplicates identical handlers.
Any ordering-sensitive automation is centralized into a single command hook entrypoint:
- `scripts/hook-router.sh`

The router:
- parses hook stdin JSON
- dispatches to specific sub-scripts in a deterministic order
- prints either valid JSON or nothing

### Hook usage principles

- `UserPromptSubmit`: keyword detection (ulw) and non-destructive context injection
- `PreToolUse`: enforce safety policies (Read-before-Edit, block risky Bash)
- `PostToolUseFailure`: recommend/trigger recovery routines
- `Stop`: continuation enforcement (boulder + ralph-loop), with circuit breakers

## Circuit Breakers (Non-negotiable)

Stop-hook continuation is powerful and dangerous.

We include:
- max continuation iterations per session
- cooldown timers
- a state flag respected by all continuation hooks (`stop-continuation`)
- always-available manual escape hatch: `/omo:stop-continuation`

## Verification Harness

We design an agent-executable selftest workflow that runs inside a single CC session (no `claude` spawning).
See `design/selftest.md`.
