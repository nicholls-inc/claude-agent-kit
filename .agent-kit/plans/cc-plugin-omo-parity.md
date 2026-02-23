# CC Plugin `omo` Parity (Tier A) — Implementation Plan

## TL;DR
> Build a Claude Code CLI plugin directory `omo/` inside this repo that recreates OMO Tier A workflows (ultrawork + plan→start-work + continuation + session continuity) using CC-native primitives (hooks, skills, subagents, repo state files), with a CC selftest harness.

**Deliverables**
- `omo/` plugin skeleton per `design/plugin-spec.md`
- Hook router + hardened shell scripts implementing: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop`
- Skills: `/omo:ulw`, `/omo:plan`, `/omo:start-work`, `/omo:ralph-loop`, `/omo:cancel-ralph`, `/omo:stop-continuation`, `/omo:handoff`, `/omo:selftest`
- Agent roster:
  - Main-session personas: `sisyphus`, `hephaestus`, `prometheus`, `atlas`
  - Leaf workers: `omo-explore`, `omo-librarian`, `omo-oracle`, `omo-metis`, `omo-momus`
- Non-fork skills to switch the main session persona: `/omo:sisyphus`, `/omo:hephaestus`, `/omo:prometheus`, `/omo:atlas`
- Repo state files: `.agent-kit/boulder.json`, `.agent-kit/plans/*.md`, `.agent-kit/cc-omo/runtime.local.json` (gitignored), `.agent-kit/ralph-loop.local.md` (gitignored), `.agent-kit/evidence/cc-omo-parity/**`
- Explicit Tier C gap doc section (no hidden model override, no native custom tools, no nested orchestration, limited tool output transforms)

**Estimated Effort**: Large
**Parallel Execution**: YES (4 waves + final verification)
**Critical Path**: plugin skeleton → state I/O → Stop/PreToolUse enforcement → skills wiring → selftest

---

## Context

### Source of Truth (Design)
- `design/plugin-spec.md`
- `design/parity-contract.md`
- `design/cc-plugin-architecture.md`
- `design/claude-code-capabilities.md`
- `design/omo-to-cc-mapping.md`
- `design/security-and-permissions.md`
- `design/selftest.md`
- `design/workflows/ultrawork.md`
- `design/workflows/plan-and-start-work.md`
- `design/workflows/ralph-loop.md`

### Key Constraints
- No Claude Code source modifications; no spawning additional `claude` processes (`design/parity-contract.md`).
- Subagents cannot spawn subagents; background subagents cannot use MCP (`design/claude-code-capabilities.md`).
- Ordering-sensitive hook logic must be centralized into one handler (`design/cc-plugin-architecture.md`).
- Treat hook stdin JSON as untrusted; stdout must be strictly plain text (context hooks) or strictly JSON (decision hooks) (`design/security-and-permissions.md`).

### Existing Implementation to Reuse as Pattern (this repo)
This repo already implements OMO workflows for OpenCode. We will use it as a reference for behaviors and state semantics:
- Keyword detector: `src/hooks/keyword-detector/`
- Plan/start-work orchestration: `src/hooks/start-work/`, `src/hooks/atlas/`, `src/features/boulder-state/`
- Ralph loop state: `src/hooks/ralph-loop/`
- Stop-continuation escape hatch: `src/hooks/stop-continuation-guard/`, `src/features/builtin-commands/templates/stop-continuation.ts`

---

## Work Objectives

### Core Objective
Implement a CC plugin (`omo/`) that achieves Tier A parity behaviors as defined in `design/parity-contract.md`, with durable repo state and bounded continuation.

### Definition of Done
- Tier A behaviors verifiably work via the selftest scenarios in `design/selftest.md`.
- Tier B items are explicitly deferred (or implemented if cheap) with a documented list.
- Tier C gaps are documented and justified.

### Must NOT Have (Guardrails)
- No attempts at hidden model override (explicit Tier C).
- No nested subagent spawning (CC limitation).
- No hook scripts that emit non-JSON to stdout for decision hooks.
- No reliance on MCP tools from background subagents.

---

## Verification Strategy

### Test Decision (this repo)
- **Infrastructure exists**: YES (Bun `bun:test`)
- **Automated tests for new work**: Tests-after (match repo conventions)
- **Commands**:
  - `bun test`
  - `bun run typecheck`
  - `bun run build`

### Agent-Executable QA Policy (for CC plugin)
Every task includes QA scenarios the executor can run in Claude Code CLI (and/or shell) with evidence written under:
- `.agent-kit/evidence/cc-omo-parity/<area>/<scenario>.log`

Notes:
- If the QA scenario uses `rg`, prefer Claude Code's built-in `Grep` tool when `rg` is not available on the host.
- Avoid using Python in QA steps; prefer `node -e` for JSON parsing when needed.

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Scaffolding + contracts)
- Task 1-6

Wave 2 (State + hook router + safety)
- Task 7-12

Wave 3 (Skills + orchestration behaviors)
- Task 13-18

Wave 4 (Selftest + docs + hardening)
- Task 19-28

---

## TODOs

 [x] 1. Create CC plugin directory skeleton (`omo/`)

  **What to do**:
  - Create the on-disk plugin tree described in `design/plugin-spec.md` and `design/cc-plugin-architecture.md`.
  - Add empty placeholder files for manifest, hooks, scripts, agents, skills (content added in later tasks).

  **Must NOT do**:
  - Do not change existing OpenCode plugin behavior under `src/`.

  **Recommended Agent Profile**:
  - **Category**: `quick` (mostly file scaffolding)
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 2-6)
  - **Blocks**: 7-24
  - **Blocked By**: None

  **References**:
  - `design/plugin-spec.md` - required tree + hook/script contracts
  - `design/cc-plugin-architecture.md` - canonical layout + state files

  **Acceptance Criteria**:
  - [ ] `omo/.claude-plugin/plugin.json` exists
  - [ ] `omo/hooks/hooks.json` exists
  - [ ] `omo/scripts/` directory exists
  - [ ] `omo/agents/` directory exists
  - [ ] `omo/skills/` directory exists

  **QA Scenarios**:
  ```
  Scenario: Plugin skeleton present
    Tool: Bash
    Steps:
      1. test -f omo/.claude-plugin/plugin.json
      2. test -f omo/hooks/hooks.json
      3. test -d omo/scripts && test -d omo/agents && test -d omo/skills
    Evidence: .agent-kit/evidence/cc-omo-parity/scaffold/plugin-skeleton.log

  Scenario: No src/ changes required
    Tool: Bash
    Steps:
      1. git diff --name-only | (grep -v '^src/' || true)
    Evidence: .agent-kit/evidence/cc-omo-parity/scaffold/no-src-changes.log
  ```

 [x] 2. Define leaf subagents (`omo/agents/omo-*.md`)

  **What to do**:
  - Add CC subagent definitions for: explore, librarian, oracle, metis, momus.
  - Encode constraints from `design/claude-code-capabilities.md`: leaf-only; no nested subagent spawning; background MCP restrictions noted for librarian.

  **Must NOT do**:
  - Do not add orchestrator logic into subagents; orchestration stays in main-thread skills.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 3-6)
  - **Blocks**: 13-21
  - **Blocked By**: 1

  **References**:
  - `design/cc-plugin-architecture.md` - leaf worker roster + tool restrictions
  - `design/claude-code-capabilities.md` - subagent limitations
  - `src/agents/explore.ts`, `src/agents/librarian.ts`, `src/agents/oracle.ts`, `src/agents/metis.ts`, `src/agents/momus.ts` - behavior/policy to mirror

  **Acceptance Criteria**:
  - [ ] `omo/agents/omo-explore.md` exists
  - [ ] `omo/agents/omo-librarian.md` exists
  - [ ] `omo/agents/omo-oracle.md` exists
  - [ ] `omo/agents/omo-metis.md` exists
  - [ ] `omo/agents/omo-momus.md` exists

  **QA Scenarios**:
  ```
  Scenario: Agent files present
    Tool: Bash
    Steps:
      1. test -f omo/agents/omo-explore.md
      2. test -f omo/agents/omo-librarian.md
      3. test -f omo/agents/omo-oracle.md
      4. test -f omo/agents/omo-metis.md
      5. test -f omo/agents/omo-momus.md
    Evidence: .agent-kit/evidence/cc-omo-parity/agents/agent-files.log

  Scenario: Leaf-only constraints mentioned
    Tool: Bash
    Steps:
      1. rg -n "cannot spawn" omo/agents/omo-*.md
    Evidence: .agent-kit/evidence/cc-omo-parity/agents/leaf-only.log
  ```

 [x] 3. Define Tier A skills (`omo/skills/*/SKILL.md`)

  **What to do**:
  - Create skill directories and SKILL.md for:
    - `ulw`, `plan`, `start-work`, `ralph-loop`, `cancel-ralph`, `stop-continuation`, `handoff`, `selftest`
  - Persona switcher skills are added separately in Task 27.
  - Ensure namespacing matches CC plugin (`/omo:<skill>`) and arguments are passed via `$ARGUMENTS`.
  - Decide which skills run inline vs `context: fork` (leaf work should use fork + agent; orchestration should remain main thread).

  **Must NOT do**:
  - Do not require user to install extra tooling beyond bash (+ optional jq fallback).

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1-2, 4-6)
  - **Blocks**: 14-21
  - **Blocked By**: 1

  **References**:
  - `design/plugin-spec.md` - required skills list
  - `design/workflows/ultrawork.md` - ulw semantics + circuit breakers
  - `design/workflows/plan-and-start-work.md` - plan/start-work artifacts + flow
  - `design/workflows/ralph-loop.md` - loop state + done marker

  **Acceptance Criteria**:
  - [ ] `omo/skills/ulw/SKILL.md` exists
  - [ ] `omo/skills/plan/SKILL.md` exists
  - [ ] `omo/skills/start-work/SKILL.md` exists
  - [ ] `omo/skills/ralph-loop/SKILL.md` exists
  - [ ] `omo/skills/cancel-ralph/SKILL.md` exists
  - [ ] `omo/skills/stop-continuation/SKILL.md` exists
  - [ ] `omo/skills/handoff/SKILL.md` exists
  - [ ] `omo/skills/selftest/SKILL.md` exists

  **QA Scenarios**:
  ```
  Scenario: Skill files present
    Tool: Bash
    Steps:
      1. for s in ulw plan start-work ralph-loop cancel-ralph stop-continuation handoff selftest; do test -f "omo/skills/$s/SKILL.md"; done
    Evidence: .agent-kit/evidence/cc-omo-parity/skills/skill-files.log

  Scenario: Skills reference $ARGUMENTS
    Tool: Bash
    Steps:
      1. rg -n "\$ARGUMENTS" omo/skills -S
    Evidence: .agent-kit/evidence/cc-omo-parity/skills/skill-arguments.log
  ```

 [x] 4. Wire CC hook events to a single router (`omo/hooks/hooks.json`)

  **What to do**:
  - Configure `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Stop` to call one entrypoint: `${CLAUDE_PLUGIN_ROOT}/scripts/hook-router.sh`.
  - Ensure `UserPromptSubmit`/`SessionStart` modes emit plain text only; `PreToolUse`/`Stop` emit JSON only.

  **Must NOT do**:
  - Do not register multiple scripts for ordering-sensitive behavior (CC runs hooks in parallel).

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1-3, 5-6)
  - **Blocks**: 9-12, 18
  - **Blocked By**: 1

  **References**:
  - `design/plugin-spec.md` - required events + router rule
  - `design/claude-code-capabilities.md` - hook parallelism/dedup caveat

  **Acceptance Criteria**:
  - [ ] `omo/hooks/hooks.json` references `${CLAUDE_PLUGIN_ROOT}/scripts/hook-router.sh` for all 4 events

  **QA Scenarios**:
  ```
  Scenario: hooks.json references router
    Tool: Bash
    Steps:
      1. rg -n "hook-router\.sh" omo/hooks/hooks.json
      2. rg -n "SessionStart|UserPromptSubmit|PreToolUse|Stop" omo/hooks/hooks.json
    Evidence: .agent-kit/evidence/cc-omo-parity/hooks/hooks-json.log

  Scenario: Plugin-root path used
    Tool: Bash
    Steps:
      1. rg -n "\$\{CLAUDE_PLUGIN_ROOT\}" omo/hooks/hooks.json
    Evidence: .agent-kit/evidence/cc-omo-parity/hooks/plugin-root-path.log
  ```

 [x] 5. Add hardened script scaffolding (`omo/scripts/*.sh`)

  **What to do**:
  - Create script files with shebang, `set -euo pipefail`, and a consistent stdout/stderr policy.
  - Scripts (initial): `hook-router.sh`, `detect-ulw.sh`, `sanitize-hook-input.sh`, `state-read.sh`, `state-write.sh`.
  - Add a `DEBUG` toggle that writes diagnostic info to files under `.agent-kit/evidence/cc-omo-parity/` (never to stdout).

  **Must NOT do**:
  - Never print debug logs to stdout in decision hooks.
  - Never `eval` any hook-derived input.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high` (shell safety + contracts)
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1-4, 6)
  - **Blocks**: 7-12
  - **Blocked By**: 1

  **References**:
  - `design/security-and-permissions.md` - hardening requirements
  - `design/plugin-spec.md` - script contracts

  **Acceptance Criteria**:
  - [ ] `omo/scripts/hook-router.sh` exists
  - [ ] `omo/scripts/detect-ulw.sh` exists
  - [ ] `omo/scripts/sanitize-hook-input.sh` exists
  - [ ] `omo/scripts/state-read.sh` exists
  - [ ] `omo/scripts/state-write.sh` exists
  - [ ] All scripts run `bash -n` successfully

  **QA Scenarios**:
  ```
  Scenario: Scripts exist and are syntax-valid
    Tool: Bash
    Steps:
      1. for f in omo/scripts/*.sh; do test -f "$f"; bash -n "$f"; done
    Evidence: .agent-kit/evidence/cc-omo-parity/scripts/bash-n.log

  Scenario: Stdout/stderr policy present
    Tool: Bash
    Steps:
      1. rg -n "set -euo pipefail" omo/scripts/*.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/scripts/hardening-flags.log
  ```

 [x] 6. Initialize repo state + ignore rules for local artifacts

  **What to do**:
  - Ensure `.agent-kit/` subdirs exist (plans/evidence/cc-omo) and add ignore rules for local state:
    - `.agent-kit/cc-omo/runtime.local.json`
    - `.agent-kit/ralph-loop.local.md`
  - Decide whether evidence logs are committed or ignored; default: ignore evidence logs (keep local).

  **Must NOT do**:
  - Do not overwrite existing `.agent-kit/` conventions already used by this repo.

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1-5)
  - **Blocks**: 7-24 (state files must be writable)
  - **Blocked By**: None

  **References**:
  - `design/cc-plugin-architecture.md` - state-of-truth file list
  - `design/selftest.md` - evidence path conventions
  - Existing repo patterns: `.agent-kit/plans/`, `.agent-kit/drafts/`

  **Acceptance Criteria**:
  - [ ] Ignore rules exist for `.agent-kit/cc-omo/runtime.local.json` and `.agent-kit/ralph-loop.local.md`
  - [ ] `.agent-kit/evidence/cc-omo-parity/` exists

  **QA Scenarios**:
  ```
  Scenario: Ignore rules present
    Tool: Bash
    Steps:
      1. rg -n "cc-omo/runtime\.local\.json" .gitignore .agent-kit/.gitignore || true
      2. rg -n "ralph-loop\.local\.md" .gitignore .agent-kit/.gitignore || true
    Evidence: .agent-kit/evidence/cc-omo-parity/state/ignore-rules.log

  Scenario: Evidence directory exists
    Tool: Bash
    Steps:
      1. test -d .agent-kit/evidence/cc-omo-parity
    Evidence: .agent-kit/evidence/cc-omo-parity/state/evidence-dir.log
  ```

- [x] 7. Implement robust state read/write helpers (atomic + fail-open)

  **What to do**:
  - Implement `state-read.sh` and `state-write.sh` to manage:
    - `.agent-kit/boulder.json`
    - `.agent-kit/cc-omo/runtime.local.json`
    - `.agent-kit/ralph-loop.local.md`
  - Use atomic write (`tmp` + `mv`) and best-effort locking (lockfile) to reduce hook races.
  - If parsing fails (corrupt JSON/YAML), treat as missing and allow Stop (fail-open).

  **Must NOT do**:
  - Never block Stop due to state parse errors.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 8-12)
  - **Blocks**: 9-21
  - **Blocked By**: 5-6

  **References**:
  - `design/security-and-permissions.md` - fail-open requirement
  - `design/workflows/ultrawork.md` - runtime.local.json schema + circuit breakers
  - Existing OMO state patterns: `src/features/boulder-state/storage.ts`, `src/hooks/ralph-loop/storage.ts`

  **Acceptance Criteria**:
  - [ ] State writes are atomic (no direct overwrite without temp file)
  - [ ] Parse failures do not exit non-zero in a way that prints to stdout

  **QA Scenarios**:
  ```
  Scenario: Atomic write uses temp+mv
    Tool: Bash
    Steps:
      1. rg -n "mv .*\.tmp" omo/scripts/state-write.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/state/atomic-write.log

  Scenario: Fail-open on corrupt state
    Tool: Bash
    Steps:
      1. printf '{not-json' > .agent-kit/cc-omo/runtime.local.json
      2. bash omo/scripts/state-read.sh .agent-kit/cc-omo/runtime.local.json || true
    Evidence: .agent-kit/evidence/cc-omo-parity/state/fail-open.log
  ```

- [x] 8. Sanitize hook stdin JSON before use

  **What to do**:
  - Implement `sanitize-hook-input.sh` to parse stdin, allowlist only needed fields, and drop any large/untrusted payloads.
  - Add a safe mechanism to extract required fields (tool name, command, arguments, event type) without shell interpolation.
  - Add a "hook input probe" mode (DEBUG only) that writes a redacted snapshot to `.agent-kit/evidence/cc-omo-parity/hook-input/`.

  **Must NOT do**:
  - Never store raw hook input containing secrets.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 7, 9-12)
  - **Blocks**: 9-12, 18
  - **Blocked By**: 5-6

  **References**:
  - `design/security-and-permissions.md` - treat stdin as untrusted; avoid eval
  - `design/claude-code-capabilities.md` - hook stdin injection rules

  **Acceptance Criteria**:
  - [ ] Sanitizer never prints untrusted content to stdout in decision mode
  - [ ] Redaction rules exist for obvious secret fields (tokens/keys)

  **QA Scenarios**:
  ```
  Scenario: Sanitizer uses jq with safe defaults OR explicit fallback
    Tool: Bash
    Steps:
      1. rg -n "jq -e" omo/scripts/sanitize-hook-input.sh || true
      2. rg -n "node -e" omo/scripts/sanitize-hook-input.sh || true
    Evidence: .agent-kit/evidence/cc-omo-parity/security/sanitizer-impl.log

  Scenario: Debug snapshots write to evidence (not stdout)
    Tool: Bash
    Steps:
      1. rg -n "cc-omo-parity/hook-input" omo/scripts/sanitize-hook-input.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/security/hook-probe-path.log
  ```

- [x] 9. Implement hook router dispatch (event → handler)

  **What to do**:
  - Implement `omo/scripts/hook-router.sh` to:
    - identify the hook event type
    - sanitize stdin (Task 8)
    - call the correct sub-handler in a deterministic order
  - Enforce stdout rules:
    - `SessionStart`/`UserPromptSubmit`: plain text only
    - `PreToolUse`/`Stop`: JSON only (or empty output)
  - On any internal error: log to stderr and fail-open.

  **Must NOT do**:
  - Never emit mixed stdout content.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 10-12)
  - **Blocks**: 10-12, 18
  - **Blocked By**: 4-5, 8

  **References**:
  - `design/plugin-spec.md` - router contract
  - `design/cc-plugin-architecture.md` - ordering-sensitive behavior rationale
  - `design/claude-code-capabilities.md` - stdout injection caveats

  **Acceptance Criteria**:
  - [ ] Router does not crash on empty/malformed stdin (fail-open)
  - [ ] Decision-mode outputs are valid JSON when present

  **QA Scenarios**:
  ```
  Scenario: Router fail-open on malformed stdin
    Tool: Bash
    Steps:
      1. printf '{bad' | bash omo/scripts/hook-router.sh >/tmp/router.out 2>/tmp/router.err || true
      2. test -s /tmp/router.err
    Evidence: .agent-kit/evidence/cc-omo-parity/router/fail-open.log

  Scenario: Router JSON-only in decision mode
    Tool: Bash
    Steps:
      1. printf '{}' | bash omo/scripts/hook-router.sh | (node -e 'JSON.parse(require("fs").readFileSync(0,"utf8"))') || true
    Evidence: .agent-kit/evidence/cc-omo-parity/router/json-only.log
  ```

- [x] 10. Implement `UserPromptSubmit` ultrawork keyword injection

  **What to do**:
  - Implement `detect-ulw.sh` with word-boundary detection for `ulw`/`ultrawork`.
  - In `UserPromptSubmit` handling, when keyword present:
    - print the ultrawork instruction block (plain text) described in `design/workflows/ultrawork.md`
    - optionally toggle `ulw.enabled=true` in runtime state (Task 15)
  - Explicitly defer other keyword modes (Tier B).

  **Must NOT do**:
  - Avoid false positives (e.g., "bulwark").

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9, 11-12)
  - **Blocks**: 18
  - **Blocked By**: 5, 9

  **References**:
  - `design/workflows/ultrawork.md` - trigger + injected instruction contract
  - Existing pattern: `src/hooks/keyword-detector/ultrawork/`

  **Acceptance Criteria**:
  - [ ] `ulw` is detected as standalone word and not as substring
  - [ ] Injected text is non-empty and contains an explicit verification-gates rule

  **QA Scenarios**:
  ```
  Scenario: Word-boundary detection
    Tool: Bash
    Steps:
      1. echo "bulwark" | bash omo/scripts/detect-ulw.sh && exit 1 || true
      2. echo "ulw do thing" | bash omo/scripts/detect-ulw.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/ulw/word-boundary.log

  Scenario: Injection block contains verification gates
    Tool: Bash
    Steps:
      1. rg -n "verification" omo/scripts/hook-router.sh omo/skills/ulw/SKILL.md || true
    Evidence: .agent-kit/evidence/cc-omo-parity/ulw/verification-gates-text.log
  ```

- [x] 11. Implement `SessionStart` resume context injection

  **What to do**:
  - On `SessionStart`, if `.agent-kit/boulder.json` indicates active work:
    - inject a small resume block (plan path + current task + escape hatch reminder)
    - do NOT inject the entire plan file (avoid context blowups)
  - If state is missing/corrupt: print nothing (fail-open).

  **Must NOT do**:
  - Never block session start; never print JSON here.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9-10, 12)
  - **Blocks**: 17-18, 21
  - **Blocked By**: 7, 9

  **References**:
  - `design/workflows/plan-and-start-work.md` - resume injection requirements
  - Existing pattern: `src/hooks/task-resume-info/`, `src/hooks/start-work/`

  **Acceptance Criteria**:
  - [ ] Injection includes `/omo:stop-continuation`
  - [ ] Injection is capped (e.g., <= 15 lines)

  **QA Scenarios**:
  ```
  Scenario: Resume block mentions escape hatch
    Tool: Bash
    Steps:
      1. rg -n "/omo:stop-continuation" omo/scripts/hook-router.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/resume/escape-hatch-mention.log

  Scenario: Resume block size is capped
    Tool: Bash
    Steps:
      1. rg -n "max.*lines|cap" omo/scripts/hook-router.sh || true
    Evidence: .agent-kit/evidence/cc-omo-parity/resume/cap.log
  ```

- [x] 12. Implement `PreToolUse` guardrails (destructive Bash + edit discipline)

  **What to do**:
  - Implement `PreToolUse` handling to block known-destructive Bash patterns (at least `rm -rf`, `mkfs`, `dd if=`) per `design/security-and-permissions.md`.
  - Confirm the exact CC decision JSON schema and match it (Metis flagged this as a validation item).
  - Optional (Tier B): enforce Read-before-Edit/Write pattern.

  **Must NOT do**:
  - Never hard-block tools on parse errors; fail open.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 9-11)
  - **Blocks**: 21
  - **Blocked By**: 9, 8

  **References**:
  - `design/security-and-permissions.md` - deny patterns + stdout rules
  - Existing pattern: `src/hooks/write-existing-file-guard/`, `src/hooks/prometheus-md-only/`

  **Acceptance Criteria**:
  - [ ] Attempting `rm -rf /tmp/should-not-run` is blocked by PreToolUse in CC (selftest scenario)

  **QA Scenarios**:
  ```
  Scenario: Pattern list includes rm -rf
    Tool: Bash
    Steps:
      1. rg -n "rm\\s\+\-rf|rm -rf" omo/scripts/hook-router.sh omo/scripts/* || true
    Evidence: .agent-kit/evidence/cc-omo-parity/pretool/patterns.log

  Scenario: Decision output is valid JSON
    Tool: Bash
    Steps:
      1. rg -n "decision" omo/scripts/hook-router.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/pretool/decision-fields.log
  ```

- [x] 13. Finalize state schemas + session identification strategy

  **What to do**:
  - Choose and document a single schema for `.agent-kit/boulder.json` and `.agent-kit/cc-omo/runtime.local.json`.
  - Decide how scripts key circuit breakers:
    - Prefer `session_id` from hook stdin if available.
    - If not available, fall back to a repo-local key (e.g., "global"), and keep circuit breakers still bounded.
  - Add schema versioning (integer) and a migration rule: unknown version → fail-open.

  **Must NOT do**:
  - Do not silently drift between schemas across scripts.

  **Recommended Agent Profile**:
  - **Category**: `deep` (contract decisions + edge cases)
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (central contract)
  - **Blocks**: 14-21
  - **Blocked By**: 7-11

  **References**:
  - `design/workflows/plan-and-start-work.md` - boulder recommended schema
  - `design/workflows/ultrawork.md` - runtime.local.json minimum schema
  - Existing OMO state: `src/features/boulder-state/types.ts`, `src/features/boulder-state/storage.ts`

  **Acceptance Criteria**:
  - [ ] One canonical schema is written in a doc file inside `omo/` (e.g., `omo/STATE.md`)
  - [ ] All scripts reference the same keys

  **QA Scenarios**:
  ```
  Scenario: State doc exists
    Tool: Bash
    Steps:
      1. test -f omo/STATE.md
    Evidence: .agent-kit/evidence/cc-omo-parity/state/state-doc.log

  Scenario: Scripts reference canonical keys
    Tool: Bash
    Steps:
      1. rg -n "planPath|currentTask|stopBlocks|max" omo/scripts -S || true
    Evidence: .agent-kit/evidence/cc-omo-parity/state/key-usage.log
  ```

- [x] 14. Implement `/omo:stop-continuation` escape hatch

  **What to do**:
  - Skill sets `stopContinuation.disabled=true` in `.agent-kit/cc-omo/runtime.local.json` (with reason + timestamp).
  - Ensure `Stop` hook and any continuation logic always checks this first.

  **Must NOT do**:
  - Never require manual file edits to escape continuation.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 15-17)
  - **Blocks**: 18-19
  - **Blocked By**: 13

  **References**:
  - `design/security-and-permissions.md` - escape hatch requirement
  - Existing pattern: `src/hooks/stop-continuation-guard/`

  **Acceptance Criteria**:
  - [ ] Running `/omo:stop-continuation` results in state indicating disabled

  **QA Scenarios**:
  ```
  Scenario: Escape hatch state toggle
    Tool: Bash
    Steps:
      1. rg -n "stopContinuation" omo/skills/stop-continuation/SKILL.md omo/scripts -S
    Evidence: .agent-kit/evidence/cc-omo-parity/escape-hatch/toggle.log

  Scenario: Stop hook checks disabled first
    Tool: Bash
    Steps:
      1. rg -n "stopContinuation\.disabled" omo/scripts/hook-router.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/escape-hatch/checked-first.log
  ```

- [x] 15. Implement `/omo:ulw` command toggle (runtime state)

  **What to do**:
  - Implement `/omo:ulw` to set `ulw.enabled=true` in runtime state (and optionally store a short reason).
  - Ensure keyword injection (Task 10) and command enablement share the same flag.

  **Must NOT do**:
  - Do not attempt any hidden model override.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14, 16-17)
  - **Blocks**: 18
  - **Blocked By**: 13

  **References**:
  - `design/workflows/ultrawork.md` - state schema + stopBlocks/cooldown
  - Existing OMO behavior: `src/hooks/keyword-detector/ultrawork/*`

  **Acceptance Criteria**:
  - [ ] `ulw.enabled` is persisted and readable by Stop hook

  **QA Scenarios**:
  ```
  Scenario: ULW state written
    Tool: Bash
    Steps:
      1. rg -n "ulw" omo/skills/ulw/SKILL.md omo/scripts -S
    Evidence: .agent-kit/evidence/cc-omo-parity/ulw/state-write.log

  Scenario: Stop hook consults ulw.enabled
    Tool: Bash
    Steps:
      1. rg -n "ulw\.enabled" omo/scripts/hook-router.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/ulw/stop-check.log
  ```

- [x] 16. Implement `/omo:plan` (write plan + init boulder)

  **What to do**:
  - Skill runs in plan discipline (`permissionMode: plan` if supported) and generates:
    - `.agent-kit/plans/<slug>.md` checklist plan
    - `.agent-kit/boulder.json` pointing to it (`active=true`, `status=in_progress`, `currentTask` set)
  - Ensure `.agent-kit/` is created if missing.

  **Must NOT do**:
  - Do not require existing `.agent-kit/` directories.

  **Recommended Agent Profile**:
  - **Category**: `deep` (plan artifact contract)
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14-15, 17)
  - **Blocks**: 17-18, 21
  - **Blocked By**: 13, 3, 6

  **References**:
  - `design/workflows/plan-and-start-work.md` - plan format + boulder init rules
  - Existing OMO plan conventions: `.agent-kit/plans/` and this repo's planner outputs

  **Acceptance Criteria**:
  - [ ] Selftest scenario "Plan Creation" passes (`design/selftest.md`)

  **QA Scenarios**:
  ```
  Scenario: Plan skill writes artifacts
    Tool: Bash
    Steps:
      1. rg -n "\.agent-kit/plans" omo/skills/plan/SKILL.md omo/scripts -S
      2. rg -n "boulder\.json" omo/skills/plan/SKILL.md omo/scripts -S
    Evidence: .agent-kit/evidence/cc-omo-parity/plan/artifact-paths.log

  Scenario: boulder schema fields present
    Tool: Bash
    Steps:
      1. rg -n "active|status|currentTask|planPath" omo/STATE.md
    Evidence: .agent-kit/evidence/cc-omo-parity/plan/schema.log
  ```

- [x] 17. Implement `/omo:start-work` (resume + task advancement protocol)

  **What to do**:
  - Skill reads `.agent-kit/boulder.json`; if missing/inactive, guide to `/omo:plan`.
  - If active, it must:
    - open the plan file
    - identify `currentTask`
    - instruct the coordinator to execute the next slice and then update:
      - plan checklist
      - boulder currentTask/updatedAt
  - Explicitly define the done condition and how status transitions to `done` + `active=false`.

  **Must NOT do**:
  - No nested orchestration; any leaf work uses Task to leaf subagents (not subagents spawning subagents).

  **Recommended Agent Profile**:
  - **Category**: `deep` (workflow correctness + continuation)
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 14-16)
  - **Blocks**: 18, 21
  - **Blocked By**: 13, 16

  **References**:
  - `design/workflows/plan-and-start-work.md` - start-work execution flow
  - Existing OMO reference: `src/hooks/start-work/start-work-hook.ts`, `src/hooks/atlas/`

  **Acceptance Criteria**:
  - [ ] Selftest scenario "Start Work Resume" passes (`design/selftest.md`)

  **QA Scenarios**:
  ```
  Scenario: start-work reads boulder and plan path
    Tool: Bash
    Steps:
      1. rg -n "boulder\.json" omo/skills/start-work/SKILL.md omo/scripts -S
      2. rg -n "planPath" omo/skills/start-work/SKILL.md omo/scripts -S
    Evidence: .agent-kit/evidence/cc-omo-parity/start-work/reads-state.log

  Scenario: done condition documented
    Tool: Bash
    Steps:
      1. rg -n "status=done|active=false|done" omo/STATE.md
    Evidence: .agent-kit/evidence/cc-omo-parity/start-work/done-condition.log
  ```

- [x] 18. Implement `Stop` hook continuation enforcement (bounded)

  **What to do**:
  - In `Stop`:
    - if escape hatch disabled → allow Stop
    - else if boulder active OR ralph loop active OR ulw enabled and incomplete → block Stop with JSON
  - Add circuit breakers:
    - max stop blocks per session/global
    - cooldown
    - auto-disable when limits reached
  - Fail-open on any state parse errors.

  **Must NOT do**:
  - Never create an infinite unescapable loop.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (integrates 10-17)
  - **Blocks**: 19-21
  - **Blocked By**: 13-17, 14

  **References**:
  - `design/workflows/ultrawork.md` - Stop hook JSON block format + circuit breakers
  - `design/workflows/plan-and-start-work.md` - boulder-based Stop blocking
  - `design/workflows/ralph-loop.md` - loop-based Stop blocking
  - Existing OMO reference: `src/hooks/todo-continuation-enforcer/`, `src/hooks/atlas/`, `src/hooks/ralph-loop/`

  **Acceptance Criteria**:
  - [ ] Selftest scenario "Escape Hatch" passes (`design/selftest.md`)
  - [ ] Stop blocks while active and stops blocking when done/disabled/max reached

  **QA Scenarios**:
  ```
  Scenario: Stop returns JSON block decision
    Tool: Bash
    Steps:
      1. rg -n '"decision"\s*:\s*"block"' omo/scripts/hook-router.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/stop/block-json.log

  Scenario: Circuit breakers present
    Tool: Bash
    Steps:
      1. rg -n "max.*stop|cooldown|stopBlocks" omo/scripts/hook-router.sh omo/scripts/state-*.sh
    Evidence: .agent-kit/evidence/cc-omo-parity/stop/circuit-breakers.log
  ```

- [x] 19. Implement Ralph loop (`/omo:ralph-loop` + `/omo:cancel-ralph`)

  **What to do**:
  - Implement skills to create/cancel `.agent-kit/ralph-loop.local.md` per `design/workflows/ralph-loop.md`.
  - Ensure Stop hook detects:
    - `status: active`
    - iteration count and max
    - done marker `RALPH_DONE` (validate CC provides assistant output content to Stop; if not, switch to a state-file done marker instead).

  **Must NOT do**:
  - Never require manual edits to end the loop; cancel + escape hatch must work.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 20-22)
  - **Blocks**: 21
  - **Blocked By**: 18, 13

  **References**:
  - `design/workflows/ralph-loop.md` - state format + done marker + Stop behavior
  - Existing OMO: `src/hooks/ralph-loop/`, `src/features/builtin-commands/templates/ralph-loop.ts`

  **Acceptance Criteria**:
  - [ ] Selftest scenario "Ralph Loop Start/Cancel" passes (`design/selftest.md`)

  **QA Scenarios**:
  ```
  Scenario: Loop state file path referenced
    Tool: Bash
    Steps:
      1. rg -n "ralph-loop\.local\.md" omo/skills/ralph-loop/SKILL.md omo/skills/cancel-ralph/SKILL.md omo/scripts -S
    Evidence: .agent-kit/evidence/cc-omo-parity/ralph/state-path.log

  Scenario: Done marker strategy documented
    Tool: Bash
    Steps:
      1. rg -n "RALPH_DONE" omo/STATE.md omo/scripts -S || true
    Evidence: .agent-kit/evidence/cc-omo-parity/ralph/done-marker.log
  ```

- [x] 20. Implement `/omo:handoff` continuation summary

  **What to do**:
  - Write a handoff markdown file that captures:
    - active plan path
    - currentTask
    - last known errors (if available)
    - how to resume (`/omo:start-work`) and how to escape
  - Choose a deterministic path, e.g. `.agent-kit/handoff/last.md` (overwrite) or timestamped.

  **Must NOT do**:
  - Do not include secrets from hook inputs or environment.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 19, 21-22)
  - **Blocks**: 21
  - **Blocked By**: 13, 16-18

  **References**:
  - `design/plugin-spec.md` - handoff skill contract
  - Existing OMO: `src/features/builtin-commands/templates/handoff.ts`

  **Acceptance Criteria**:
  - [ ] Running `/omo:handoff` creates/updates the handoff file under `.agent-kit/`

  **QA Scenarios**:
  ```
  Scenario: Handoff path referenced
    Tool: Bash
    Steps:
      1. rg -n "\.agent-kit/.*handoff" omo/skills/handoff/SKILL.md omo/scripts -S || true
    Evidence: .agent-kit/evidence/cc-omo-parity/handoff/path.log

  Scenario: Handoff includes escape hatch reminder
    Tool: Bash
    Steps:
      1. rg -n "/omo:stop-continuation" omo/skills/handoff/SKILL.md
    Evidence: .agent-kit/evidence/cc-omo-parity/handoff/escape-hatch.log
  ```

- [x] 21. Implement `/omo:selftest` (agent-executable parity harness)

  **What to do**:
  - Implement a selftest skill that executes the scenarios in `design/selftest.md` inside a single CC session.
  - Ensure evidence logs are written under `.agent-kit/evidence/cc-omo-parity/<area>/...`.
  - Ensure selftest never spawns `claude` via Bash.

  **Must NOT do**:
  - Do not require manual verification; the agent running CC should be able to complete the checklist.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (integration harness)
  - **Blocks**: 24, Final Verification
  - **Blocked By**: 1-20

  **References**:
  - `design/selftest.md` - scenario list + evidence conventions
  - `design/security-and-permissions.md` - "no claude spawning" guardrail

  **Acceptance Criteria**:
  - [ ] Selftest writes evidence logs for each scenario
  - [ ] Selftest includes destructive bash deny scenario

  **QA Scenarios**:
  ```
  Scenario: Selftest references all scenarios
    Tool: Bash
    Steps:
      1. rg -n "Plugin Loads|Keyword Ultrawork Injection|Escape Hatch|Plan Creation|Start Work Resume|Ralph Loop|PreToolUse" omo/skills/selftest/SKILL.md
    Evidence: .agent-kit/evidence/cc-omo-parity/selftest/scenario-refs.log

  Scenario: Selftest uses evidence path convention
    Tool: Bash
    Steps:
      1. rg -n "cc-omo-parity" omo/skills/selftest/SKILL.md omo/scripts -S
    Evidence: .agent-kit/evidence/cc-omo-parity/selftest/evidence-path.log
  ```

- [x] 22. Document Tier B deferrals + Tier C gaps (explicit non-parity)

  **What to do**:
  - Add a short doc inside the plugin (e.g., `omo/README.md`) that states:
    - Tier A implemented features
    - Tier B deferred list (keyword modes beyond ulw, output control, notifications, etc.)
    - Tier C gaps and why (hidden model override, native custom tools, nested orchestration, tool output transforms)

  **Must NOT do**:
  - Do not claim parity for Tier C gaps.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 19-20)
  - **Blocks**: 24
  - **Blocked By**: None

  **References**:
  - `design/parity-contract.md` - parity tiers + Tier C list
  - `design/omo-to-cc-mapping.md` - mapping-based caveats
  - `design/opencode-dependency-audit.md` - OpenCode-only items

  **Acceptance Criteria**:
  - [ ] `omo/README.md` includes a Tier C section

  **QA Scenarios**:
  ```
  Scenario: Tier C gaps mentioned
    Tool: Bash
    Steps:
      1. rg -n "Tier C" omo/README.md
      2. rg -n "hidden model override|native tools|nested" omo/README.md
    Evidence: .agent-kit/evidence/cc-omo-parity/docs/tier-c.log

  Scenario: Tier B deferrals listed
    Tool: Bash
    Steps:
      1. rg -n "Tier B" omo/README.md
    Evidence: .agent-kit/evidence/cc-omo-parity/docs/tier-b.log
  ```

- [x] 23. Permissions posture documentation (no default settings side effects)

  **What to do**:
  - Document a recommended permissions snippet (from `design/security-and-permissions.md`) as docs only.
  - Ensure plugin does not ship a `settings.json` that changes permissions automatically.

  **Must NOT do**:
  - Do not auto-enable dangerous permissions; do not require network.

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 22)
  - **Blocks**: 24
  - **Blocked By**: None

  **References**:
  - `design/security-and-permissions.md` - recommended posture and deny patterns

  **Acceptance Criteria**:
  - [ ] Docs include deny patterns for destructive bash
  - [ ] No mandatory permission changes required for basic Tier A flows

  **QA Scenarios**:
  ```
  Scenario: Deny patterns documented
    Tool: Bash
    Steps:
      1. rg -n "rm\\s\+\-rf|mkfs|dd\\s\+if=" omo/README.md || true
    Evidence: .agent-kit/evidence/cc-omo-parity/docs/deny-patterns.log

  Scenario: No settings.json shipped
    Tool: Bash
    Steps:
      1. test ! -f omo/settings.json || exit 1
    Evidence: .agent-kit/evidence/cc-omo-parity/docs/no-settings-json.log
  ```

- [x] 24. Compatibility validation + selftest pass criteria

  **What to do**:
  - Add a short compatibility note:
    - minimum CC version assumptions (events supported)
    - required dependencies (bash; jq optional)
  - Define "selftest passes" concretely:
    - evidence logs exist for each scenario
    - `/plugin validate` and `/plugin errors` show no errors
  - Add a final smoke-run instruction sequence for an agent to follow.

  **Must NOT do**:
  - Do not assume hook stdin provides fields without a probe or fallback.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Final Verification
  - **Blocked By**: 21-23

  **References**:
  - `design/claude-code-capabilities.md` - event list + behavior caveats
  - `design/selftest.md` - scenario expectations

  **Acceptance Criteria**:
  - [ ] Documented smoke-run produces evidence under `.agent-kit/evidence/cc-omo-parity/final/`

  **QA Scenarios**:
  ```
  Scenario: Pass criteria documented
    Tool: Bash
    Steps:
      1. rg -n "selftest passes" omo/README.md omo/skills/selftest/SKILL.md || true
    Evidence: .agent-kit/evidence/cc-omo-parity/final/pass-criteria.log

  Scenario: Compatibility notes included
    Tool: Bash
    Steps:
      1. rg -n "Claude Code" omo/README.md
      2. rg -n "jq|bash" omo/README.md
    Evidence: .agent-kit/evidence/cc-omo-parity/final/compatibility.log
  ```

- [x] 25. Add "active persona" state + prompt injection glue

  **What to do**:
  - Extend runtime state to track the selected main-session persona (one of: `sisyphus`, `hephaestus`, `prometheus`, `atlas`).
  - On `SessionStart` and `UserPromptSubmit`, inject the correct persona prompt block based on runtime state.
  - Default persona if unset: `sisyphus`.

  **Must NOT do**:
  - Do not fork into a subagent for persona switching; this must affect the main session.

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO (cross-cutting)
  - **Blocks**: 26-28
  - **Blocked By**: 13, 9-11

  **References**:
  - `design/claude-code-capabilities.md` - which events inject stdout into context
  - Existing OMO persona prompts: `src/agents/sisyphus.ts`, `src/agents/hephaestus.ts`, `src/agents/prometheus/*`, `src/agents/atlas/agent.ts`

  **Acceptance Criteria**:
  - [ ] Persona injection occurs on `SessionStart` and on subsequent prompts
  - [ ] Prometheus persona is planner-only and aligns with markdown-only planning constraints (best-effort via guidance + PreToolUse)

  **QA Scenarios**:
  ```
  Scenario: Persona keys documented
    Tool: Bash
    Steps:
      1. rg -n "sisyphus|hephaestus|prometheus|atlas" omo/STATE.md omo/README.md || true
    Evidence: .agent-kit/evidence/cc-omo-parity/persona/keys.log

  Scenario: Router injects persona block
    Tool: Bash
    Steps:
      1. rg -n "activePersona|persona" omo/scripts/hook-router.sh omo/scripts/state-read.sh omo/scripts/state-write.sh || true
    Evidence: .agent-kit/evidence/cc-omo-parity/persona/injection-glue.log
  ```

- [x] 26. Add main-session persona definitions (agents)

  **What to do**:
  - Add agent markdown definitions for the four main personas.
  - Encode tool allow/deny and permissionMode differences:
    - `prometheus`: plan discipline; md-only outputs by instruction; avoid implementing.
    - `atlas`: executor discipline; follows plan tasks; strong continuation.
    - `sisyphus`: orchestration + delegation.
    - `hephaestus`: deep autonomous worker (but no nested orchestration).

  **Must NOT do**:
  - Do not let Prometheus write non-markdown or outside `.agent-kit/` (enforce via instructions + PreToolUse where possible).

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 27)
  - **Blocks**: 28
  - **Blocked By**: 25

  **References**:
  - Existing agent intent and restrictions: `src/agents/AGENTS.md`, `src/agents/tool-restrictions.test.ts`
  - Prometheus constraints: `src/hooks/prometheus-md-only/`

  **Acceptance Criteria**:
  - [ ] Agent markdown files exist for all four personas

  **QA Scenarios**:
  ```
  Scenario: Persona agent files present
    Tool: Bash
    Steps:
      1. test -f omo/agents/sisyphus.md
      2. test -f omo/agents/hephaestus.md
      3. test -f omo/agents/prometheus.md
      4. test -f omo/agents/atlas.md
    Evidence: .agent-kit/evidence/cc-omo-parity/persona/agent-files.log

  Scenario: Prometheus mentions md-only constraint
    Tool: Bash
    Steps:
      1. rg -n "\.agent-kit/|markdown" omo/agents/prometheus.md
    Evidence: .agent-kit/evidence/cc-omo-parity/persona/prometheus-constraint.log
  ```

- [x] 27. Add non-fork skills to switch persona (`/omo:sisyphus`, etc.)

  **What to do**:
  - Implement four skills that:
    - run inline (no `context: fork`)
    - set runtime `activePersona`
    - print a short confirmation + how to revert
  - Ensure switching persona does not break existing `ulw` / boulder / ralph state.

  **Must NOT do**:
  - Do not rely on a CC internal `/agent` command existing.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 26)
  - **Blocks**: 28
  - **Blocked By**: 25

  **References**:
  - User requirement: main session must be able to operate under these personas
  - `design/claude-code-capabilities.md` - inline vs fork skills

  **Acceptance Criteria**:
  - [ ] Skills exist: `omo/skills/sisyphus/SKILL.md`, `omo/skills/hephaestus/SKILL.md`, `omo/skills/prometheus/SKILL.md`, `omo/skills/atlas/SKILL.md`

  **QA Scenarios**:
  ```
  Scenario: Persona skills exist
    Tool: Bash
    Steps:
      1. for s in sisyphus hephaestus prometheus atlas; do test -f "omo/skills/$s/SKILL.md"; done
    Evidence: .agent-kit/evidence/cc-omo-parity/persona/skill-files.log

  Scenario: Persona skills are non-fork
    Tool: Bash
    Steps:
      1. rg -n "context:\s*fork" omo/skills/sisyphus/SKILL.md omo/skills/hephaestus/SKILL.md omo/skills/prometheus/SKILL.md omo/skills/atlas/SKILL.md && exit 1 || true
    Evidence: .agent-kit/evidence/cc-omo-parity/persona/non-fork.log
  ```

- [x] 28. Extend selftest to validate persona switching

  **What to do**:
  - Add selftest steps:
    - switch to each persona via skill
    - confirm injected persona block changes on next prompt
    - confirm Prometheus persona stays planner-only
  - Capture evidence logs.

  **Must NOT do**:
  - Do not require human inspection; selftest must record evidence in logs.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: none

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Final Verification
  - **Blocked By**: 21, 25-27

  **References**:
  - `design/selftest.md` - harness conventions

  **Acceptance Criteria**:
  - [ ] Selftest includes persona switching steps and writes evidence

  **QA Scenarios**:
  ```
  Scenario: Selftest references persona switching
    Tool: Bash
    Steps:
      1. rg -n "omo:sisyphus|omo:hephaestus|omo:prometheus|omo:atlas" omo/skills/selftest/SKILL.md
    Evidence: .agent-kit/evidence/cc-omo-parity/selftest/persona-refs.log
  ```

---

## Final Verification Wave

- F1. Run CC selftest scenarios end-to-end (`design/selftest.md`) and archive evidence under `.agent-kit/evidence/cc-omo-parity/final/`.
- F2. Run repo checks: `bun test && bun run typecheck && bun run build`.

---

## Commit Strategy
- Prefer small commits per wave, each with passing `bun test` (or scoped test path) and a short message describing parity milestone.

---

## Success Criteria
- CC plugin directory `omo/` can be enabled and validated in Claude Code.
- Selftest scenarios in `design/selftest.md` all pass with evidence logs.
- Continuation is bounded and escapable (`/omo:stop-continuation`).
- Tier C gaps are explicit and no forbidden behaviors are attempted.
