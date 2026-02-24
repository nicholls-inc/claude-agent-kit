# Claude Agent Kit

A multi-agent orchestration plugin for Claude Code. Provides persona-based workflows, planning and execution pipelines, specialist subagents, and continuation control using hooks, skills, subagents, and repo-local state files.

It's essentially a port of [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) for Claude Code.

## Features

- Ultrawork trigger via `ulw`/`ultrawork` keyword and `/claude-agent-kit:ulw` skill.
- Plan to execution flow via `/claude-agent-kit:plan` and `/claude-agent-kit:start-work` using `.agent-kit/boulder.json`.
- Bounded continuation enforcement in Stop hook with max blocks, cooldown, and escape hatch.
- Session resume injection from active boulder state on `SessionStart`.
- Leaf specialists: explore, librarian, oracle, metis, momus.
- Main-session persona controls: `/claude-agent-kit:sisyphus`, `/claude-agent-kit:hephaestus`, `/claude-agent-kit:prometheus`, `/claude-agent-kit:atlas`.

## Limitations

- Hidden model override is not supported.
- Native custom tools are not supported; use built-in tools and MCP wrappers.
- Nested subagent orchestration is not supported.
- Full tool output rewriting is not supported.

## Security and Permissions

Recommended posture (documentation only):
- allow: Read, Grep, Glob
- ask: Bash, Edit, Write, WebFetch, MCP
- deny destructive bash patterns: `rm -rf`, `mkfs`, `dd if=`

The plugin does not ship a `settings.json` and does not auto-change user permissions.

## Compatibility

- Target runtime: Claude Code plugin hooks with `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`.
- Dependencies: `bash` required, `jq` optional (preferred for strict JSON handling).
- Hook stdin fields can vary by Claude Code version; scripts use fallback extraction and fail-open behavior.

## Selftest Pass Criteria

Selftest passes when:
- evidence logs are written under `.agent-kit/evidence/<area>/...` for each scenario
- plugin validation commands report no errors in a real plugin runtime
- destructive Bash guard scenario is blocked

## Smoke Run

1. Enable plugin in Claude Code.
2. Run `/plugin validate` and `/plugin errors`.
3. Run `/claude-agent-kit:selftest` and collect evidence under `.agent-kit/evidence/final/`.
4. Confirm escape hatch works with `/claude-agent-kit:stop-continuation`.
