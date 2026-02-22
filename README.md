# OMO Claude Code Plugin

`omo` recreates OMO Tier A workflows in Claude Code using hooks, skills, subagents, and repo-local state files.

## Tier A (implemented)

- Ultrawork trigger via `ulw`/`ultrawork` keyword and `/omo:ulw` skill.
- Plan to execution flow via `/omo:plan` and `/omo:start-work` using `.agent-kit/boulder.json`.
- Bounded continuation enforcement in Stop hook with max blocks, cooldown, and escape hatch.
- Session resume injection from active boulder state on `SessionStart`.
- Leaf specialists: explore, librarian, oracle, metis, momus.
- Main-session persona controls: `/omo:sisyphus`, `/omo:hephaestus`, `/omo:prometheus`, `/omo:atlas`.

## Tier B (deferred or partial)

- Additional keyword modes beyond ultrawork (search/analyze).
- Rich output truncation and notification patterns.
- Full automated selftest execution inside a live Claude Code plugin runtime (this repo ships the procedure and evidence conventions).

## Tier C (explicit non-parity)

- Hidden model override is not supported.
- Native custom tools are not supported; use built-in tools and MCP wrappers.
- Nested subagent orchestration is not supported.
- Full tool output rewriting parity is not supported.

## Security and Permissions

Recommended posture (documentation only):
- allow: Read, Grep, Glob
- ask: Bash, Edit, Write, WebFetch, MCP
- deny destructive bash patterns: `rm -rf`, `mkfs`, `dd if=`

The plugin does not ship `omo/settings.json` and does not auto-change user permissions.

## Compatibility

- Target runtime: Claude Code plugin hooks with `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`.
- Dependencies: `bash` required, `jq` optional (preferred for strict JSON handling).
- Hook stdin fields can vary by Claude Code version; scripts use fallback extraction and fail-open behavior.

## Selftest Pass Criteria

Selftest passes when:
- evidence logs are written under `.agent-kit/evidence/cc-omo-parity/<area>/...` for each scenario
- plugin validation commands report no errors in a real plugin runtime
- destructive Bash guard scenario is blocked

## Smoke Run

1. Enable plugin in Claude Code.
2. Run `/plugin validate` and `/plugin errors`.
3. Run `/omo:selftest` and collect evidence under `.agent-kit/evidence/cc-omo-parity/final/`.
4. Confirm escape hatch works with `/omo:stop-continuation`.
