# Claude Code Plugin: Agents + Model Routing

## TL;DR
Build a configurable Claude Code plugin that recreates (as close to 1:1 as practical) the agents and prompts from this repository inside Anthropic official Claude Code. Provide pinned-model agents and skill-based slash commands for each agent/workflow, and enforce a "Safe" completion gate for a Boulder/Sisyphus-like one-shot workflow.

**Primary deliverable**: a plugin directory (installable via `claude --plugin-dir`) containing `skills/`, `agents/`, `hooks/`, scripts, and docs.

**Estimated effort**: Medium
**Parallel execution**: YES (4 waves)
**Critical path**: Plugin scaffold -> Agent/skill roster -> Boulder gate hooks/scripts -> Local verification + docs

---

## Context

### Original Request
Recreate an "agent system" in Anthropic official Claude Code without multi-provider support, but with efficient usage via model switching based on task. Provide both manual access (slash commands) and automatic delegation (subagents), and experiment with agent teams.

Additionally: repurpose the agents and prompts in this repository for Claude Code - inventory all agents, categorize them, document their purpose/function, analyze each agent prompt for suitability in Claude Code, and identify required prompt changes.

### Key Constraints
- Target platform is Anthropic official Claude Code.
- Models to use: Haiku, Sonnet, Opus, and `opusplan` (where supported).
- Distribution: one configurable Claude Code plugin; users can enable/disable features.
- Include a Sisyphus-like "Boulder" one-shot agent that loops until done; default completion gate is **Safe** (lint + unit tests + build).
- Plugin-shipped `settings.json` currently supports only the `agent` key; other toggles should be implemented via user/project `.claude/settings*.json` and permissions guidance.
- No multi-provider LLM routing; however, MCP servers may be used to approximate missing tools (docs/search/github/etc.) where needed.

### Sources
- Plugins: `https://code.claude.com/docs/en/plugins.md`
- Plugins reference: `https://code.claude.com/docs/en/plugins-reference.md`
- Skills: `https://code.claude.com/docs/en/skills.md`
- Subagents: `https://code.claude.com/docs/en/sub-agents.md`
- Model config: `https://code.claude.com/docs/en/model-config.md`
- Agent teams: `https://code.claude.com/docs/en/agent-teams.md`
- Hooks: `https://code.claude.com/docs/en/hooks.md`
- Costs: `https://code.claude.com/docs/en/costs.md`

### Note On Metis
Metis consultation was attempted but unavailable in this environment; this plan includes a built-in gap/edge-case checklist and explicit guardrails instead.

---

## Work Objectives

### Core Objective
Provide a Claude Code plugin that makes "right-model-for-the-job" usage easy and repeatable via:
1) pinned-model agents (subagents),
2) pinned-model slash commands (skills),
3) optional agent team templates,
4) a safe, self-verifying Boulder one-shot flow for simple tasks.

### Concrete Deliverables
- Plugin directory (example name: `claude-agent-kit/`) with:
  - `.claude-plugin/plugin.json`
  - `skills/` for manual commands (namespaced `/claude-agent-kit:<skill>`)
  - `agents/` recreating the repo's agent roster (visible in `/agents`)
  - `hooks/` + `scripts/` for quality gates and cost controls
  - `.mcp.json` (optional but planned) for tool parity where Claude Code supports it
  - `README.md` describing install + usage + configuration
- A mapping doc that shows, for each oh-my-opencode agent, the Claude Code equivalent: model, tools, prompt differences, and known limitations.
- Minimal configuration story for enabling/disabling features.
- Team templates to spawn common teammate sets (experimental agent teams).

### Definition Of Done
- Loading the plugin via `claude --plugin-dir ./claude-agent-kit` shows:
  - skills available under `/claude-agent-kit:*`
  - agents available in `/agents`
- Each v1 skill works end-to-end in a fresh session (see QA scenarios per task).
- Boulder agent completes a small change and only stops after **Safe** checks pass.

### Must NOT Have (Guardrails)
- No multi-provider routing/gateways.
- No hidden side effects: skills that write files or change git state must be `disable-model-invocation: true`.
- No "infinite loop" Boulder behavior: must have a max-iterations / max-turns stop condition and a clear failure report.
- Avoid bloating always-on context (keep CLAUDE.md minimal; use on-demand skills).

---

## Verification Strategy

### Automated Tests
- Prefer "tests-after" rather than TDD for this plugin, since it is primarily configuration + prompts.
- Verification is primarily **agent-executed QA scenarios** (CLI-driven) and smoke tests.

### QA Policy (Agent-Executable)
Every task includes QA scenarios. Evidence is saved to:
- `.sisyphus/evidence/task-<N>-<slug>.txt` (terminal output)
- `.sisyphus/evidence/task-<N>-<slug>.png` (if screenshots are used)

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Scaffold + inventory + mapping)
- Tasks 1-4

Wave 2 (Core workflows + agent prompt adaptations)
- Tasks 5-7

Wave 3 (Boulder safe gate + automation + teams + configuration)
- Tasks 8-12, 16

Wave 4 (Docs + troubleshooting + release readiness)
- Tasks 13-15

---

## TODOs

- [ ] 1. Create plugin scaffold + manifest

  **What to do**:
  - Create a new plugin directory (default name: `claude-agent-kit/`).
  - Add `.claude-plugin/plugin.json` with name/description/version.
  - Add stub directories: `agents/`, `skills/`, `hooks/`, `scripts/`.
  - Add a minimal `README.md` describing `claude --plugin-dir` usage.

  **Must NOT do**:
  - Don’t place `agents/`, `skills/`, `hooks/` inside `.claude-plugin/` (manifest-only dir).

  **Recommended Agent Profile**:
  - Category: `quick`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 2-4)

  **References**:
  - `https://code.claude.com/docs/en/plugins.md` (plugin structure + `--plugin-dir`)
  - `https://code.claude.com/docs/en/plugins-reference.md` (manifest schema + directory layout)

  **Acceptance Criteria**:
  - `claude --plugin-dir ./claude-agent-kit` starts without plugin load errors.

  **QA Scenarios**:
  ```
  Scenario: Plugin loads via --plugin-dir
    Tool: Bash
    Steps:
      1. Run: claude --plugin-dir ./claude-agent-kit --debug
      2. Confirm debug output shows plugin discovered + no manifest errors
    Evidence: .sisyphus/evidence/task-1-plugin-load.txt
  ```

- [ ] 2. Define routing policy + model mapping

  **What to do**:
  - Write a short routing policy doc (in the plugin README or a `docs/` file within the plugin) that states:
    - Haiku: read-only exploration + high-volume ops
    - Sonnet: implementation + refactors
    - Opus: architecture + tricky reasoning + deep review
    - `opusplan`: use for plan-mode-to-exec workflows when supported
  - Define which components pin models (subagents vs skills) and when to `inherit`.
  - Add a "model substitution" table mapping the repo's original models to Anthropic-only equivalents (e.g., Hephaestus GPT-Codex -> Opus or Sonnet with higher effort).
  - Add cost guardrails: "default to Sonnet in main session; delegate exploration to Haiku agents".

  **Must NOT do**:
  - Don’t introduce any non-Anthropic provider routing.

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 1, 3, 4)

  **References**:
  - `https://code.claude.com/docs/en/model-config.md` (aliases, `opusplan`, `/model`, env vars)
  - `https://code.claude.com/docs/en/costs.md` (cost guidance; teams and token usage)
  - `https://code.claude.com/docs/en/sub-agents.md` (subagent models; Explore=Haiku)

  **Acceptance Criteria**:
  - Policy includes a table mapping each v1 command/agent to a model and rationale.

  **QA Scenarios**:
  ```
  Scenario: Policy is actionable
    Tool: Read
    Steps:
      1. Open policy doc
      2. Verify each v1 agent/skill has a model assignment and usage guidance
    Evidence: .sisyphus/evidence/task-2-policy-review.txt
  ```

- [ ] 3. Inventory + recreate repo agents as Claude Code subagents (close to 1:1)

  **What to do**:
  - Use `src/agents/AGENTS.md` to enumerate the full agent roster (11 agents) and tool restrictions.
  - For each agent, locate its source prompt and extract/translate the intent into a Claude Code agent markdown definition under `claude-agent-kit/agents/`.
  - Target roster to recreate:
    - Sisyphus (orchestrator)
    - Hephaestus (autonomous deep worker)
    - Oracle (read-only advisor)
    - Librarian (external docs/code search)
    - Explore (read-only codebase search)
    - Multimodal-Looker (read-only media interpretation)
    - Metis (pre-planning consultant)
    - Momus (plan reviewer)
    - Atlas (todo/task orchestration)
    - Prometheus (planner)
    - Sisyphus-Junior (focused executor)
  - Translate tool references to Claude Code equivalents:
    - remove OpenCode-only tools (e.g. `call_omo_agent`, `todowrite`) and replace with Claude Code primitives (skills, subagents, hooks, or explicit instructions)
    - map tool restrictions to Claude Code `tools:` and `disallowedTools:` fields
  - Ensure each agent has:
    - clear `description:` to encourage correct delegation
    - explicit `tools:` allowlist / `disallowedTools:` denylist
    - sensible `maxTurns` defaults (especially autonomous agents)
    - consistent output format for summaries

  **Must NOT do**:
  - Don’t let read-only agents have `Edit`/`Write`.
  - Don’t allow Boulder to run without iteration/time limits.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 1, 2, 4)

  **References**:
  - `src/agents/AGENTS.md` (authoritative roster + restrictions)
  - `src/agents/sisyphus.ts` (Sisyphus prompt intent)
  - `src/agents/hephaestus.ts` (Hephaestus prompt intent)
  - `src/agents/oracle.ts` (Oracle prompt)
  - `src/agents/librarian.ts` (Librarian prompt)
  - `src/agents/explore.ts` (Explore prompt)
  - `src/agents/multimodal-looker.ts` (Multimodal-Looker prompt)
  - `src/agents/metis.ts` (Metis prompt)
  - `src/agents/momus.ts` (Momus prompt)
  - `src/agents/atlas/agent.ts` (Atlas prompt intent)
  - `src/agents/prometheus/system-prompt.ts` (Prometheus prompt assembly)
  - `src/agents/sisyphus-junior/agent.ts` (Sisyphus-Junior)
  - `https://code.claude.com/docs/en/sub-agents.md` (Claude Code agent frontmatter fields)

  **Acceptance Criteria**:
  - All recreated agents appear in Claude Code `/agents` UI when loading plugin via `--plugin-dir`.
  - Each agent has an explicit model assignment and tool policy appropriate to its role.

  **QA Scenarios**:
  ```
  Scenario: Agents are discoverable
    Tool: Bash
    Steps:
      1. Run: claude --plugin-dir ./claude-agent-kit
      2. In session, open /agents and confirm all recreated agents appear
    Evidence: .sisyphus/evidence/task-3-agents-listed.txt
  ```

- [ ] 4. Create skill (slash command) roster skeletons

  **What to do**:
  - Create skill directories under `claude-agent-kit/skills/`:
    - Workflow skills: `explore/`, `plan/`, `implement/`, `review/`, `boulder/`
    - Agent-entrypoint skills (manual access to each recreated agent):
      - `sisyphus/`, `hephaestus/`, `oracle/`, `librarian/`, `explore-agent/`, `multimodal-looker/`, `metis/`, `momus/`, `atlas/`, `prometheus/`, `sisyphus-junior/`
    - Management: `configure/`, `team-templates/`
  - For each `SKILL.md`:
    - include a precise `description:`
    - set `disable-model-invocation: true` for any skill with side effects
    - set `model:` per routing policy
    - decide `context:` (`inline` vs `fork`) and `agent:` when forking

  **Must NOT do**:
  - Don’t let Claude auto-invoke side-effecting skills.

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 1-3)

  **References**:
  - `https://code.claude.com/docs/en/skills.md` (frontmatter: `model`, `context: fork`, `agent`, `disable-model-invocation`)
  - `https://code.claude.com/docs/en/plugins.md` (plugin skill namespacing)

  **Acceptance Criteria**:
  - Skills show in `/help` under `/claude-agent-kit:*` after plugin load.
  - There is at least one manual entrypoint skill per recreated agent.

  **QA Scenarios**:
  ```
  Scenario: Skills are discoverable
    Tool: Bash
    Steps:
      1. Run: claude --plugin-dir ./claude-agent-kit
      2. Type: /help
      3. Confirm skills listed under claude-agent-kit namespace
    Evidence: .sisyphus/evidence/task-4-skills-listed.txt
  ```

- [ ] 5. Implement Explore workflow (manual command + delegation-friendly)

  **What to do**:
  - Fill in `skills/explore/SKILL.md` to:
    - run in forked context using Explore agent when appropriate
    - require output as: "Files to read next", "Key findings", "Open questions"
    - explicitly avoid code edits
  - Ensure model selection aligns (Haiku via Explore agent).

  **Recommended Agent Profile**:
  - Category: `quick`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 6-7)
  - Blocked by: Task 4

  **References**:
  - `https://code.claude.com/docs/en/sub-agents.md` (built-in Explore: Haiku, read-only)
  - `https://code.claude.com/docs/en/skills.md` (context fork + agent field)

  **Acceptance Criteria**:
  - Running `/claude-agent-kit:explore <topic>` produces a concise summary and a short file list.

  **QA Scenarios**:
  ```
  Scenario: Explore produces concise, non-edit output
    Tool: Bash
    Steps:
      1. Start: claude --plugin-dir ./claude-agent-kit
      2. Run: /claude-agent-kit:explore "summarize this repo structure"
      3. Verify output includes the required sections and contains no edit instructions
    Evidence: .sisyphus/evidence/task-5-explore-output.txt
  ```

- [ ] 6. Implement Plan workflow (Opus / opusplan)

  **What to do**:
  - Implement `skills/plan/SKILL.md` to produce:
    - explicit scope (IN/OUT)
    - numbered steps
    - verification commands
    - risk checklist
  - Use `opusplan` for this skill if supported in skill frontmatter; otherwise pin to Opus and instruct `/model opusplan` for interactive plan mode.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 5, 7)
  - Blocked by: Task 4

  **References**:
  - `https://code.claude.com/docs/en/model-config.md` (`opusplan` behavior)
  - `https://code.claude.com/docs/en/common-workflows.md` (plan mode usage; if needed)

  **Acceptance Criteria**:
  - `/claude-agent-kit:plan <task>` returns a plan with explicit verification steps.

  **QA Scenarios**:
  ```
  Scenario: Plan output is structured
    Tool: Bash
    Steps:
      1. Start: claude --plugin-dir ./claude-agent-kit
      2. Run: /claude-agent-kit:plan "refactor a module safely"
      3. Verify includes IN/OUT and verification commands
    Evidence: .sisyphus/evidence/task-6-plan-output.txt
  ```

- [ ] 7. Implement Implement + Review workflows

  **What to do**:
  - Implement `skills/implement/SKILL.md` to:
    - default to Sonnet
    - require incremental changes + local verification
    - prefer using repo test scripts when available
  - Implement `skills/review/SKILL.md` to:
    - pin to Opus
    - run `git diff` first
    - return prioritized findings + suggested patches

  **Must NOT do**:
  - Review skill must not mutate files.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 5-6)
  - Blocked by: Task 4

  **References**:
  - `https://code.claude.com/docs/en/skills.md` (frontmatter: model + allowed-tools)
  - `https://code.claude.com/docs/en/sub-agents.md` (tool allowlists)

  **Acceptance Criteria**:
  - `/claude-agent-kit:implement ...` results in edits and runs at least one verification command.
  - `/claude-agent-kit:review` produces a prioritized list without editing.

  **QA Scenarios**:
  ```
  Scenario: Review is read-only
    Tool: Bash
    Steps:
      1. Start: claude --plugin-dir ./claude-agent-kit
      2. Run: /claude-agent-kit:review
      3. Confirm no files changed (git status clean)
    Evidence: .sisyphus/evidence/task-7-review-readonly.txt
  ```

- [ ] 8. Design Boulder workflow (one-shot "push the boulder") + limits

  **What to do**:
  - Implement `skills/boulder/SKILL.md` to run a full loop:
    1) restate goal + acceptance criteria
    2) plan briefly
    3) implement incrementally
    4) verify with **Safe gate**
    5) if fail: diagnose + fix + repeat
  - Add hard limits:
    - max iterations (e.g., 5)
    - max turns (agent `maxTurns`)
    - stop with a "failure report" if still failing after limits.

  **Must NOT do**:
  - Don’t allow Boulder to run indefinitely.

  **Recommended Agent Profile**:
  - Category: `deep`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 9-10)
  - Blocked by: Tasks 3-4

  **References**:
  - `https://code.claude.com/docs/en/sub-agents.md` (maxTurns, tool restrictions)
  - `https://code.claude.com/docs/en/skills.md` (context fork + model pinning)
  - `https://code.claude.com/docs/en/hooks.md` (Stop/SubagentStop blocking behavior)

  **Acceptance Criteria**:
  - Boulder skill explicitly defines iteration limits and a failure-report format.

  **QA Scenarios**:
  ```
  Scenario: Boulder has bounded retries
    Tool: Bash
    Steps:
      1. Start: claude --plugin-dir ./claude-agent-kit
      2. Run: /claude-agent-kit:boulder "do something impossible"
      3. Verify it terminates with a bounded failure report, not an endless loop
    Evidence: .sisyphus/evidence/task-8-boulder-bounded.txt
  ```

- [ ] 9. Implement "Safe gate" command resolution strategy (lint + tests + build)

  **What to do**:
  - Add a script in `scripts/` that determines how to run the repo’s checks:
    - prefer package scripts (e.g., `npm|pnpm|yarn|bun` scripts)
    - fall back to common defaults when scripts missing
    - allow a user override via environment variable or a small config file inside the plugin
  - Define how the gate behaves when commands are unavailable:
    - fail closed (recommended for "Safe") with actionable guidance.

  **Must NOT do**:
  - Don’t silently skip verification steps.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 8, 10)

  **References**:
  - `https://code.claude.com/docs/en/hooks.md` (command hooks, JSON stdin)
  - `https://code.claude.com/docs/en/costs.md` (delegate verbose operations; keep context small)

  **Acceptance Criteria**:
  - Script prints a clear, ordered list of commands it will run and exits non-zero on failure.

  **QA Scenarios**:
  ```
  Scenario: Safe gate fails closed when commands missing
    Tool: Bash
    Steps:
      1. Run safe-gate script in a minimal repo fixture with no package scripts
      2. Verify it exits non-zero and explains how to configure overrides
    Evidence: .sisyphus/evidence/task-9-safe-gate-missing.txt
  ```

- [ ] 10. Enforce Boulder "Safe" completion via hooks (Stop/SubagentStop)

  **What to do**:
  - Add plugin hook configuration (`hooks/hooks.json`) to support Boulder safe gating.
  - Choose the mechanism:
    - For the Boulder agent: a `Stop`/`SubagentStop` hook that runs the safe-gate script and exits 2 to block stopping on failure.
  - Ensure hook output is actionable (points to failing command and next step).

  **Must NOT do**:
  - Don’t block Stop globally for all sessions; scope to Boulder where possible (via agent-scoped hooks or matcher strategy).

  **Recommended Agent Profile**:
  - Category: `unspecified-high`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 8-9)
  - Blocked by: Task 9

  **References**:
  - `https://code.claude.com/docs/en/hooks.md` (Stop/SubagentStop; exit code 2 behavior)
  - `https://code.claude.com/docs/en/plugins-reference.md` (plugin hooks location + `${CLAUDE_PLUGIN_ROOT}`)

  **Acceptance Criteria**:
  - If lint/tests/build fail, Boulder cannot stop and returns the failing output summary.

  **QA Scenarios**:
  ```
  Scenario: Stop is blocked on failing checks
    Tool: Bash
    Preconditions: Introduce an intentional failing test
    Steps:
      1. Start: claude --plugin-dir ./claude-agent-kit
      2. Run: /claude-agent-kit:boulder "make a small change"
      3. Verify it runs safe-gate, detects failure, and continues instead of stopping
    Evidence: .sisyphus/evidence/task-10-stop-blocked.txt
  ```

- [ ] 11. Add agent team templates (experimental)

  **What to do**:
  - Provide a skill `skills/team-templates/SKILL.md` that contains copy-pasteable prompts to spawn teams, e.g.:
    - Security + Performance + Test Coverage review team
    - Competing-hypotheses debugging team
    - New-feature split (frontend/backend/tests) team
  - Include enablement instructions: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES (with Tasks 8-10)

  **References**:
  - `https://code.claude.com/docs/en/agent-teams.md` (enablement + prompts + limitations)
  - `https://code.claude.com/docs/en/costs.md` (agent team token costs)

  **Acceptance Criteria**:
  - Templates explicitly recommend Sonnet for teammates unless a strong reason exists.

  **QA Scenarios**:
  ```
  Scenario: Team template is runnable
    Tool: Bash
    Steps:
      1. Enable agent teams via env/settings
      2. Run template prompt in Claude Code
      3. Confirm team spawns and task list appears
    Evidence: .sisyphus/evidence/task-11-team-spawn.txt
  ```

- [ ] 12. Provide a user-facing configuration story (enable/disable features)

  **What to do**:
  - Add `skills/configure/SKILL.md` to guide users through:
    - selecting default model (`/model sonnet`)
    - setting `availableModels` allowlist (optional)
    - enabling agent teams (optional)
    - disabling auto-invocation for side-effecting skills (already default)
    - enabling/disabling plugin MCP servers (if installed) and checking token overhead
    - optionally denying certain tools for safety
  - If feasible, have the configure skill write/update `.claude/settings.local.json` (user-controlled) rather than requiring manual edits.

  **Must NOT do**:
  - Don’t change global user settings without explicit user invocation.

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES (with Task 11)

  **References**:
  - `https://code.claude.com/docs/en/settings.md` (settings files + scopes)
  - `https://code.claude.com/docs/en/permissions.md` (deny rules for Skill/Task)
  - `https://code.claude.com/docs/en/mcp.md` (MCP configuration and scope)

  **Acceptance Criteria**:
  - Users can disable agent teams and still use all non-team skills.

  **QA Scenarios**:
  ```
  Scenario: Configure writes local settings
    Tool: Bash
    Steps:
      1. Run: /claude-agent-kit:configure
      2. Verify .claude/settings.local.json updated as described
    Evidence: .sisyphus/evidence/task-12-configure-settings.txt
  ```

- [ ] 13. Write usage docs + examples (day-to-day workflows)

  **What to do**:
  - Expand plugin `README.md` with:
    - install/test: `claude --plugin-dir`
    - model switching guidance (`/model`, `opusplan`)
    - examples for each skill:
      - explore a module
      - plan a refactor
      - implement a change
      - run review
      - run boulder
    - agent teams: how to enable and when to avoid (cost)

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES (with Task 14)

  **References**:
  - `https://code.claude.com/docs/en/plugins.md` (testing via `--plugin-dir`)
  - `https://code.claude.com/docs/en/model-config.md` (`/model`, `opusplan`)
  - `https://code.claude.com/docs/en/costs.md` (cost do/don’t)

  **Acceptance Criteria**:
  - README has one copy-paste example per skill and a "when to use which model" section.

  **QA Scenarios**:
  ```
  Scenario: Docs are complete enough for a new user
    Tool: Read
    Steps:
      1. Open README
      2. Confirm each skill has an example invocation and expected output shape
    Evidence: .sisyphus/evidence/task-13-docs-check.txt
  ```

- [ ] 14. Add troubleshooting + compatibility checks

  **What to do**:
  - Document:
    - minimum Claude Code version
    - how to use `--debug` and plugin validation tooling
    - common failure modes: wrong directory structure, hooks not executable, agent teams disabled
    - plugin caching constraints (don’t reference outside plugin root)

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES (with Task 13)

  **References**:
  - `https://code.claude.com/docs/en/plugins-reference.md` (debugging checklist; caching)
  - `https://code.claude.com/docs/en/hooks.md` (hook troubleshooting + exit codes)
  - `https://code.claude.com/docs/en/agent-teams.md` (limitations)

  **Acceptance Criteria**:
  - Troubleshooting section includes at least: plugin not loading, hooks not firing, team not spawning.

  **QA Scenarios**:
  ```
  Scenario: Troubleshooting covers common errors
    Tool: Read
    Steps:
      1. Open troubleshooting section
      2. Confirm it contains fixes for the 3 most common issues
    Evidence: .sisyphus/evidence/task-14-troubleshooting.txt
  ```

- [ ] 15. Release readiness: versioning + optional marketplace packaging

  **What to do**:
  - Add a `CHANGELOG.md` and define semantic versioning rules.
  - Decide whether to ship as:
    - local plugin directory only, or
    - a repository that can be used in a marketplace later.
  - Add guidance on bumping `plugin.json` version to avoid cache-stale updates.

  **Recommended Agent Profile**:
  - Category: `writing`

  **Parallelization**:
  - Can run in parallel: YES

  **References**:
  - `https://code.claude.com/docs/en/plugins-reference.md` (version management + caching behavior)

  **Acceptance Criteria**:
  - Version bump guidance is present and consistent with Claude Code caching behavior.

  **QA Scenarios**:
  ```
  Scenario: Versioning guidance exists
    Tool: Read
    Steps:
      1. Open CHANGELOG and manifest
      2. Confirm versions are consistent and bump guidance is present
    Evidence: .sisyphus/evidence/task-15-versioning.txt
  ```

- [ ] 16. Bundle MCP servers to approximate oh-my-opencode tool surface

  **What to do**:
  - Add a plugin `.mcp.json` that provides the missing "research/search" capabilities expected by the ported agents (as close as feasible), for example:
    - docs lookup (Context7-like)
    - web search
    - GitHub code search helpers
  - Ensure MCP server configs use `${CLAUDE_PLUGIN_ROOT}` and do not reference paths outside the plugin (plugin cache constraints).
  - Document how users authenticate/configure any MCPs that require keys.
  - Add permission guidance so MCP tools do not auto-run unexpectedly.

  **Must NOT do**:
  - Don’t introduce non-Anthropic LLM providers for chat/model routing.

  **Recommended Agent Profile**:
  - Category: `unspecified-high`

  **Parallelization**:
  - Can run in parallel: YES

  **References**:
  - `https://code.claude.com/docs/en/mcp.md` (MCP config)
  - `https://code.claude.com/docs/en/plugins-reference.md` (plugin MCP servers)

  **Acceptance Criteria**:
  - MCP tools appear in `/mcp` and are usable from within a plugin-enabled session.

  **QA Scenarios**:
  ```
  Scenario: MCP servers load with plugin
    Tool: Bash
    Steps:
      1. Start: claude --plugin-dir ./claude-agent-kit --debug
      2. Run: /mcp
      3. Confirm plugin MCP servers are connected and tools are listed
    Evidence: .sisyphus/evidence/task-16-mcp-loaded.txt
  ```

---

## Final Verification Wave
- Run a clean smoke test: install via `--plugin-dir`, list skills/agents, execute one workflow per skill.
- Validate the Boulder gate: deliberately introduce a failing test to confirm the gate blocks stopping.

## Commit Strategy
- Prefer small, reviewable commits by component type: `plugin scaffold`, `agents`, `skills`, `hooks/scripts`, `docs`.

## Success Criteria
- Plugin installs/loads cleanly; skills + agents are discoverable.
- Model usage matches intent (Haiku for exploration, Sonnet for implementation, Opus for deep planning/review) as observed in `/status` or model picker.
- Boulder completes simple tasks and refuses to stop if lint/tests/build fail.
