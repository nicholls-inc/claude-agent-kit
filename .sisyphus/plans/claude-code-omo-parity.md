# Claude Code Plugin With OMO Parity (CLI-Only)

## TL;DR

> Build a Claude Code CLI plugin that reproduces oh-my-opencode’s orchestration system (agents + workflows + hooks + skills) using only Claude Code-native extension points: plugins, subagents, skills/commands, hooks, and plugin-bundled MCP servers + scripts.

**Deliverables**:
- A Claude Code plugin directory implementing OMO-equivalent workflows (Ultrawork, Plan→Start-Work, Ralph Loop, rules injection, etc.)
- A complete inventory + mapping document: OMO feature → CC mechanism → workaround/gap
- A documented plugin architecture + plugin spec (file-by-file design)

**Estimated effort**: XL
**Parallel execution**: YES (5 waves)
**Critical path**: CC plugin primitives confirmed → OMO inventory → mapping matrix → plugin architecture → implementation + verification

---

## Context

### Original Request
Design a Claude Code (CC) plugin that recreates all oh-my-opencode (OMO) features using only native CC capabilities.

### Constraints (hard)
- No modifications to Claude Code source code.
- No external automation that programmatically controls Claude Code.
- Do NOT use or research Claude Code Agent Teams.
- Allowed: CC plugins/hooks/skills/subagents/worktrees + plugin-bundled scripts + plugin-bundled MCP servers.
- Disallowed: any custom code that launches additional Claude Code instances (no programmatic `claude ...` spawning).

### Key Evidence Anchors (what to read/follow)
- OMO feature docs: `docs/features.md`, `docs/guide/overview.md`
- OMO orchestration: `docs/orchestration-guide.md`, `docs/guide/understanding-orchestration-system.md`
- OMO runtime wiring: `src/create-tools.ts`, `src/tools/index.ts`, `src/hooks/index.ts`, `src/create-hooks.ts`, `src/plugin/chat-message.ts`
- Claude Code docs: `https://code.claude.com/docs/en/plugins-reference`, `https://code.claude.com/docs/en/hooks`, `https://code.claude.com/docs/en/sub-agents`, `https://code.claude.com/docs/en/skills`, `https://code.claude.com/docs/en/mcp`, `https://code.claude.com/docs/en/settings`, `https://code.claude.com/docs/en/permissions`, `https://code.claude.com/docs/en/cli-reference`

### Metis Guardrails To Apply (already decided)
- Define an explicit parity contract (tiered) to prevent infinite scope.
- Accept that CC cannot add first-class built-in tools; implement “tool parity” via MCP + skills/hooks.
- Design around CC limitations:
  - Background subagents cannot use MCP.
  - Subagents cannot spawn subagents.
  - Hook ordering can be nondeterministic; ordering-sensitive logic must be centralized.
- Ultrawork “hidden model override” is not portable; model choices must be explicit/visible.
- Stop/continuation automation needs circuit breakers and an escape hatch.

---

## Work Objectives

### Core Objective
Recreate OMO’s user-facing workflows and automation (agents, hooks, skills/commands, persistence) inside Claude Code CLI as a plugin, without relying on OpenCode internals.

### Definition of Done
- A Claude Code plugin can be loaded via `claude --plugin-dir <dir>` and exposes:
  - Equivalent workflows: Ultrawork (“ulw”), Plan→Start Work, Ralph Loop
  - Equivalent automation: keyword detection, continuation enforcement, rules injection, notifications, output control
- A mapping matrix explicitly covers every OMO feature area (features/workflows/agents/tools/hooks) with: CC equivalent + workaround + gap justification.

### Must NOT Do (guardrails)
- Do not use Agent Teams.
- Do not create any solution that relies on launching additional Claude Code processes.
- Do not depend on OpenCode-specific storage hacks (e.g., OMO deferred DB mutation for model override).

---

## Verification Strategy

> Verification must be agent-executable. No “manual try it.”

- **Plugin load**: within a CC session, `/plugin validate` passes and `/plugin errors` is empty; use `/debug` to confirm load ordering when needed.
- **Hook firing**: within a CC session, `/debug` confirms expected hook events fire on sample actions.
- **Skill/command discoverability**: `/` command list includes plugin commands; `/agents` lists plugin subagents.
- **MCP tool availability**: `/mcp` shows plugin MCP servers; MCP tools callable in foreground session.
- **Golden-path workflows**: run scripted scenarios (Bash scripts invoked by hooks or a “selftest” skill) that execute each workflow end-to-end and record evidence logs.

Evidence convention: `.sisyphus/evidence/cc-omo-parity/<area>/<scenario>.{log,md,json,png}`

---

## Execution Strategy (Parallel Waves)

Wave 1 (Foundations: constraints + CC primitives + repo inventory scaffolding)
Wave 2 (Complete OMO inventory: features/workflows/agents/tools/hooks)
Wave 3 (Complete CC capability inventory + parity mapping matrix)
Wave 4 (Plugin architecture/design + “parity contract” + safety model)
Wave 5 (Implementation plan + verification harness design)

---

## TODOs

- [ ] 1. Define the parity contract (tiers + non-goals)

  **What to do**:
  - Write `design/parity-contract.md` with 3 tiers:
    - Tier A (Must match): core workflows + behaviors that define “OMO-ness”
    - Tier B (Should match): nice-to-have automation
    - Tier C (Won’t match): explicit gaps with justification
  - Include a glossary mapping terms: OMO agent/workflow/hook/tool → CC plugin equivalents.

  **References**:
  - `docs/features.md` - OMO feature surface area
  - `docs/orchestration-guide.md` - OMO user workflows (ulw vs @plan + /start-work)
  - `docs/guide/overview.md` - what users expect from OMO

  **Acceptance Criteria**:
  - [ ] `design/parity-contract.md` exists and includes Tier A/B/C lists (≥10 items total)
  - [ ] Tier C includes the “no hidden model override” gap explicitly

  **QA Scenarios**:
  - Scenario: Contract is actionable
    Tool: Bash
    Steps:
      1. `test -f design/parity-contract.md`
      2. `rg -n "Tier A|Tier B|Tier C" design/parity-contract.md`
    Expected Result: file exists; all 3 tiers are present
    Evidence: `.sisyphus/evidence/cc-omo-parity/contract/tiers.log`

  **Recommended Agent Profile**:
  - Category: `writing` (requires careful, unambiguous spec writing)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1 (with Tasks 2-4)

- [ ] 2. Inventory Claude Code CLI plugin primitives + hard limits

  **What to do**:
  - Write `design/claude-code-capabilities.md` summarizing the CC mechanisms we can use:
    - Plugins: manifest, caching behavior, namespacing
    - Hooks: available events, handler types, ordering/dedupe caveats
    - Subagents: tool/model restrictions, “no nested subagent spawn”, background limitations
    - Skills/commands: invocation, fork context, arguments
    - MCP: plugin-bundled servers, tool search, scopes
    - Permissions/sandboxing: how to enforce guardrails
  - Add a “Do/Don’t” section directly reflecting the constraints (no Agent Teams, no spawning CC processes).

  **External References**:
  - `https://code.claude.com/docs/en/plugins-reference`
  - `https://code.claude.com/docs/en/hooks`
  - `https://code.claude.com/docs/en/sub-agents`
  - `https://code.claude.com/docs/en/mcp`
  - `https://code.claude.com/docs/en/permissions`
  - `https://code.claude.com/docs/en/cli-reference`

  **Acceptance Criteria**:
  - [ ] `design/claude-code-capabilities.md` exists
  - [ ] Document explicitly states: background subagents cannot use MCP; subagents cannot spawn subagents

  **QA Scenarios**:
  - Scenario: Key constraints recorded
    Tool: Bash
    Steps:
      1. `test -f design/claude-code-capabilities.md`
      2. `rg -n "cannot use MCP" design/claude-code-capabilities.md`
      3. `rg -n "cannot spawn" design/claude-code-capabilities.md`
    Expected Result: both constraints are present as explicit statements
    Evidence: `.sisyphus/evidence/cc-omo-parity/cc-docs/key-constraints.log`

  **Recommended Agent Profile**:
  - Category: `writing` (docs synthesis + constraint capture)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1 (with Tasks 1, 3, 4)

- [ ] 3. Create the Phase-1 OMO inventory document skeleton

  **What to do**:
  - Create `design/omo-inventory.md` with headings for:
    - Features (inventory)
    - Workflows (Sisyphus, Hephaestus, Prometheus, Atlas)
    - Agents (role/process/prompt generation/delegation/tool gates)
    - Tools (purpose, integration points)
    - Hooks (event triggers, scope, automation)
    - Persistence/state (boulder/notepads/tasks)
  - Add “source of truth” links to OMO files for each section.

  **References**:
  - `docs/features.md`
  - `src/agents/`
  - `src/tools/`
  - `src/hooks/`
  - `src/plugin/chat-message.ts`

  **Acceptance Criteria**:
  - [ ] `design/omo-inventory.md` exists with all 6 headings listed above

  **QA Scenarios**:
  - Scenario: Inventory skeleton present
    Tool: Bash
    Steps:
      1. `test -f design/omo-inventory.md`
      2. `rg -n "^## (Features|Workflows|Agents|Tools|Hooks|Persistence)" design/omo-inventory.md`
    Expected Result: all expected headings appear
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/inventory-skeleton.log`

  **Recommended Agent Profile**:
  - Category: `writing`
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1 (with Tasks 1, 2, 4)

- [ ] 4. Create the Phase-3 mapping matrix skeleton (OMO → CC)

  **What to do**:
  - Create `design/omo-to-cc-mapping.md` with a table schema:
    - OMO capability (feature/workflow/tool/hook)
    - Where in OMO (file paths)
    - CC equivalent mechanism (hook/skill/subagent/MCP/settings)
    - Workaround (if any)
    - Parity tier (A/B/C)
    - Verification approach
  - Add a “Hard gaps” section for known non-portable OMO behavior.

  **References**:
  - `design/parity-contract.md`
  - `design/claude-code-capabilities.md`

  **Acceptance Criteria**:
  - [ ] `design/omo-to-cc-mapping.md` exists and includes the table schema + Hard gaps section

  **QA Scenarios**:
  - Scenario: Mapping template ready
    Tool: Bash
    Steps:
      1. `test -f design/omo-to-cc-mapping.md`
      2. `rg -n "Hard gaps" design/omo-to-cc-mapping.md`
    Expected Result: template file exists and includes Hard gaps
    Evidence: `.sisyphus/evidence/cc-omo-parity/mapping/template.log`

  **Recommended Agent Profile**:
  - Category: `writing`
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 1 (with Tasks 1-3)

- [ ] 5. OMO feature inventory (complete, with pointers)

  **What to do**:
  - Fill `design/omo-inventory.md` “Features” section with a complete list derived from `docs/features.md`.
  - For each feature, add:
    - Where it’s implemented in code (directory/file pointers)
    - User-facing trigger (slash command, keyword, hook)

  **References**:
  - `docs/features.md` - enumerates agents/skills/commands/hooks/tools
  - `src/create-tools.ts`, `src/create-hooks.ts` - wiring entry points

  **Acceptance Criteria**:
  - [ ] `design/omo-inventory.md` lists at least: Agents, Skills, Commands, Hooks, Tools, Persistence/state

  **QA Scenarios**:
  - Scenario: Feature list is not superficial
    Tool: Bash
    Steps:
      1. `rg -n "## Features" -n design/omo-inventory.md`
      2. `rg -n "Agents|Skills|Commands|Hooks|Tools" design/omo-inventory.md`
    Expected Result: all categories appear as subsections under Features
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/features-inventory.log`

  **Recommended Agent Profile**:
  - Category: `writing` (structured inventory writing)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Tasks 6-10)

- [ ] 6. OMO workflow deep dive: Ultrawork + Plan→Start-Work + Ralph Loop

  **What to do**:
  - In `design/omo-inventory.md` “Workflows” section, document:
    - Ultrawork (keyword detection + behavior changes)
    - Prometheus planning flow (draft → plan → optional Momus)
    - `/start-work` execution flow (boulder.json resume/init)
    - Ralph loop continuation behavior
  - For each, include:
    - Trigger conditions
    - State/persistence artifacts
    - Key hooks/tools involved

  **References**:
  - `docs/orchestration-guide.md`
  - `src/plugin/chat-message.ts` (keyword detector, ralph-loop, ultrawork apply)
  - `docs/guide/understanding-orchestration-system.md`

  **Acceptance Criteria**:
  - [ ] Workflow descriptions include explicit triggers and state files

  **QA Scenarios**:
  - Scenario: Workflow section has concrete anchors
    Tool: Bash
    Steps:
      1. `rg -n "Ultrawork|start-work|Ralph" design/omo-inventory.md`
      2. `rg -n "boulder\.json|\.sisyphus/plans" design/omo-inventory.md`
    Expected Result: workflow names and persistence artifacts are referenced
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/workflows.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (cross-cutting reasoning + precise extraction)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Tasks 5, 7-10)

- [ ] 7. OMO agents inventory (role/process/prompt generation/tool gates)

  **What to do**:
  - In `design/omo-inventory.md` “Agents” section, create a table for each agent:
    - Purpose/role
    - Process/workflow (steps)
    - How its prompt is generated (static vs dynamic builder)
    - Delegation rules
    - Tool allow/deny
  - Cover at minimum: Sisyphus, Hephaestus, Prometheus, Atlas, Oracle, Librarian, Explore, Metis, Momus.

  **References**:
  - `src/agents/sisyphus.ts`, `src/agents/hephaestus.ts`
  - `src/agents/atlas/agent.ts`
  - `src/agents/oracle.ts`, `src/agents/librarian.ts`, `src/agents/explore.ts`
  - `src/agents/prometheus/*`, `src/agents/metis.ts`, `src/agents/momus.ts`

  **Acceptance Criteria**:
  - [ ] Each agent entry includes at least one file pointer and one explicit restriction/permission note

  **QA Scenarios**:
  - Scenario: Agent table complete
    Tool: Bash
    Steps:
      1. `rg -n "Sisyphus|Hephaestus|Prometheus|Atlas|Oracle|Librarian|Explore|Metis|Momus" design/omo-inventory.md`
    Expected Result: all required agent names appear
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/agents.log`

  **Recommended Agent Profile**:
  - Category: `writing` (table synthesis)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Tasks 5, 6, 8-10)

- [ ] 8. OMO tools inventory (purpose + integration points)

  **What to do**:
  - In `design/omo-inventory.md` “Tools” section, list each tool in `src/tools/index.ts` and where it’s registered/used.
  - Call out which are OpenCode-only vs can be replicated via CC built-ins or MCP.

  **References**:
  - `src/tools/index.ts`
  - `src/plugin/tool-registry.ts`
  - `docs/features.md` (tool catalog section)

  **Acceptance Criteria**:
  - [ ] Tool list includes: delegation tools, search tools, LSP tools, background tools, session tools, interactive terminal

  **QA Scenarios**:
  - Scenario: Tool catalog coverage
    Tool: Bash
    Steps:
      1. `rg -n "task\b|call_omo_agent|background_output|lsp_|ast_grep|glob\b|grep\b" design/omo-inventory.md`
    Expected Result: major tool families are present
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/tools.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (requires accurate technical classification)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Tasks 5-7, 9-10)

- [ ] 9. OMO hooks inventory (trigger → scope → automation)

  **What to do**:
  - In `design/omo-inventory.md` “Hooks” section, enumerate hooks exported by `src/hooks/index.ts`.
  - For each hook, document:
    - Trigger event(s)
    - Agent-specific vs global
    - Behavior (what it injects/blocks/rewrites)
    - Dependencies (state files, config keys)
  - Highlight hooks that rely on OpenCode APIs (non-portable).

  **References**:
  - `src/hooks/index.ts`
  - `src/create-hooks.ts` (tiering: core/continuation/skill)
  - `src/plugin/chat-message.ts` (hook invocation wiring)

  **Acceptance Criteria**:
  - [ ] Hook inventory includes at least: keyword-detector, start-work, ralph-loop, rules-injector, tool-output-truncator, session-recovery, comment-checker

  **QA Scenarios**:
  - Scenario: Hook list includes the orchestration-critical hooks
    Tool: Bash
    Steps:
      1. `rg -n "keyword-detector|start-work|ralph-loop|rules-injector" design/omo-inventory.md`
    Expected Result: the critical hooks are explicitly described
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/hooks-critical.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (hook/event reasoning + portability tagging)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Tasks 5-8, 10)

- [ ] 10. OMO persistence/state inventory (boulder, plans, drafts, notepads)

  **What to do**:
  - In `design/omo-inventory.md` “Persistence” section, document all state artifacts:
    - `.sisyphus/plans/*.md`, `.sisyphus/drafts/*.md`
    - `.sisyphus/boulder.json`
    - `.sisyphus/notepads/<plan>/...`
    - tasks storage if used
  - Explain how these artifacts drive continuity.

  **References**:
  - `docs/orchestration-guide.md` (boulder flow)
  - `docs/task-system.md`
  - Search repo for `.sisyphus/` references

  **Acceptance Criteria**:
  - [ ] Persistence section lists the file paths and the workflow that reads/writes each

  **QA Scenarios**:
  - Scenario: Continuity artifacts documented
    Tool: Bash
    Steps:
      1. `rg -n "boulder\.json|notepads|drafts|plans" design/omo-inventory.md`
    Expected Result: all continuity artifacts appear in the Persistence section
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/persistence.log`

  **Recommended Agent Profile**:
  - Category: `writing` (state artifact documentation)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 2 (with Tasks 5-9)

- [ ] 11. Map CC hook events to OMO hooks (feasibility grid)

  **What to do**:
  - In `design/omo-to-cc-mapping.md`, add a “Hook Feasibility Grid” mapping OMO hook behaviors onto CC hook events:
    - `UserPromptSubmit` for keyword detection
    - `PreToolUse` for validation/guardrails
    - `PostToolUse` / `PostToolUseFailure` for notifications/recovery
    - `Stop` for continuation enforcement
  - Call out ordering/dedup risks and the “hook router” pattern.

  **External References**:
  - `https://code.claude.com/docs/en/hooks`

  **Acceptance Criteria**:
  - [ ] Grid includes at least 10 OMO hooks and their target CC events

  **QA Scenarios**:
  - Scenario: Hook grid exists
    Tool: Bash
    Steps:
      1. `rg -n "Hook Feasibility Grid" design/omo-to-cc-mapping.md`
    Expected Result: section exists
    Evidence: `.sisyphus/evidence/cc-omo-parity/mapping/hook-grid.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (tradeoff analysis + feasibility)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 3 (with Tasks 12, 13, 21)
  - Blocked By: Tasks 2, 9

- [ ] 12. Map OMO “agents + categories” to CC subagents + skills

  **What to do**:
  - In `design/omo-to-cc-mapping.md`, define the CC equivalent roster:
    - Coordinator (main thread) behavior
    - Leaf subagents (Explore/Librarian/Oracle analogs)
    - “Categories” implemented as either subagents or skills that route to a subagent
  - Ensure design respects CC constraints (no nested subagent spawning; no MCP in background).

  **References**:
  - `docs/guide/understanding-orchestration-system.md` (agent layering + category system)
  - `https://code.claude.com/docs/en/sub-agents`
  - `https://code.claude.com/docs/en/skills`

  **Acceptance Criteria**:
  - [ ] Mapping explicitly states how “visual-engineering / ultrabrain / quick” concepts translate in CC

  **QA Scenarios**:
  - Scenario: Category mapping recorded
    Tool: Bash
    Steps:
      1. `rg -n "visual-engineering|ultrabrain|quick" design/omo-to-cc-mapping.md`
    Expected Result: those category concepts appear with CC equivalents
    Evidence: `.sisyphus/evidence/cc-omo-parity/mapping/categories.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 3 (with Tasks 11, 13, 21)
  - Blocked By: Tasks 2, 7

- [ ] 13. Complete the feature-by-feature mapping matrix (exhaustive)

  **What to do**:
  - Populate `design/omo-to-cc-mapping.md` so every item in `docs/features.md` is mapped.
  - For each mapping row, include: parity tier (A/B/C) + verification approach.
  - Maintain an explicit “Hard gaps” list (Tier C) with justification.

  **References**:
  - `docs/features.md`
  - `design/parity-contract.md`
  - `design/claude-code-capabilities.md`

  **Acceptance Criteria**:
  - [ ] All sections in `docs/features.md` have corresponding entries in the mapping matrix

  **QA Scenarios**:
  - Scenario: Mapping is exhaustive vs OMO feature list
    Tool: Bash
    Steps:
      1. `test -f design/omo-to-cc-mapping.md`
      2. `rg -n "Agents:|Skills:|Commands:|Hooks:" docs/features.md`
      3. `rg -n "Agents|Skills|Commands|Hooks" design/omo-to-cc-mapping.md`
    Expected Result: mapping doc clearly mirrors the OMO feature areas
    Evidence: `.sisyphus/evidence/cc-omo-parity/mapping/exhaustive.log`

  **Recommended Agent Profile**:
  - Category: `writing` (careful tabular mapping)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 3 (with Tasks 11, 12, 21)
  - Blocked By: Tasks 5, 8, 9

- [ ] 14. Design the CC plugin architecture (modules + data flow)

  **What to do**:
  - Write `design/cc-plugin-architecture.md` describing:
    - Plugin directory layout (`.claude-plugin/plugin.json`, `agents/`, `skills/`, `hooks/`, `.mcp.json`, `scripts/`)
    - “Coordinator in main thread” pattern (no nested subagent spawning)
    - Hook router approach (single hook entrypoint to enforce ordering)
    - State/persistence locations (repo vs user scope)
    - Namespacing and command UX plan

  **External References**:
  - `https://code.claude.com/docs/en/plugins-reference`
  - `https://code.claude.com/docs/en/hooks`

  **Acceptance Criteria**:
  - [ ] Architecture doc includes a data-flow diagram (ASCII or Mermaid)
  - [ ] Explicitly states: no Agent Teams; no spawning CC processes

  **QA Scenarios**:
  - Scenario: Architecture doc exists and includes routing/state
    Tool: Bash
    Steps:
      1. `test -f design/cc-plugin-architecture.md`
      2. `rg -n "hook router|state|persistence|namespac" design/cc-plugin-architecture.md`
    Expected Result: routing/state/namespacing decisions are present
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/architecture.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (architecture synthesis)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 4 (with Tasks 15-19)
  - Blocked By: Tasks 11-13

- [ ] 15. Design workflow: Ultrawork (keyword → orchestration)

  **What to do**:
  - Write `design/workflows/ultrawork.md` specifying how CC implements:
    - Keyword detection (`ulw` / `ultrawork`) via `UserPromptSubmit`
    - Explicit model selection (no hidden override)
    - Background research strategy that avoids MCP in background
    - Circuit breakers (max continuation iterations)

  **References**:
  - `docs/orchestration-guide.md` (OMO ultrawork semantics)
  - `design/claude-code-capabilities.md`

  **Acceptance Criteria**:
  - [ ] Ultrawork design includes: trigger, steps, state, stop conditions

  **QA Scenarios**:
  - Scenario: Ultrawork design is concrete
    Tool: Bash
    Steps:
      1. `test -f design/workflows/ultrawork.md`
      2. `rg -n "Trigger|Steps|State|Stop" design/workflows/ultrawork.md`
    Expected Result: all 4 elements exist
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/ultrawork.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 4 (with Tasks 14, 16-19)
  - Blocked By: Tasks 6, 11, 18

- [ ] 16. Design workflow: Prometheus planning + /start-work execution (no Agent Teams)

  **What to do**:
  - Write `design/workflows/plan-and-start-work.md` specifying:
    - How “plan mode” is entered (CC plan permission mode + planning subagent)
    - Plan output format + storage location
    - `/start-work` skill behavior (init vs resume)
    - Resume state file format (OMO-like boulder), and how CC hooks read it

  **References**:
  - `docs/orchestration-guide.md` (OMO boulder init/resume)
  - `https://code.claude.com/docs/en/common-workflows` (plan mode)
  - `https://code.claude.com/docs/en/settings` (plansDirectory)

  **Acceptance Criteria**:
  - [ ] Design includes explicit state machine for init/resume

  **QA Scenarios**:
  - Scenario: Plan/start-work doc has init+resume
    Tool: Bash
    Steps:
      1. `test -f design/workflows/plan-and-start-work.md`
      2. `rg -n "init|resume|boulder" design/workflows/plan-and-start-work.md`
    Expected Result: init/resume are described with state
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/plan-start-work.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 4 (with Tasks 14, 15, 17-19)
  - Blocked By: Tasks 6, 10, 12

- [ ] 17. Design workflow: Ralph Loop continuation + escape hatch

  **What to do**:
  - Write `design/workflows/ralph-loop.md` specifying:
    - How loop is started (skill/command)
    - How completion is detected
    - Stop-hook continuation logic with circuit breaker
    - A user-invocable “stop all continuation” command

  **References**:
  - `docs/features.md` (ralph-loop)
  - `docs/orchestration-guide.md`
  - `https://code.claude.com/docs/en/hooks` (Stop hook)

  **Acceptance Criteria**:
  - [ ] Design includes maximum iterations + manual cancel behavior

  **QA Scenarios**:
  - Scenario: Loop safety documented
    Tool: Bash
    Steps:
      1. `test -f design/workflows/ralph-loop.md`
      2. `rg -n "max iterations|cancel|escape" design/workflows/ralph-loop.md`
    Expected Result: safety/escape hatch documented
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/ralph-loop.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high`
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 4 (with Tasks 14-16, 18-19)
  - Blocked By: Tasks 6, 9

- [ ] 18. Design safety/permissions/sandboxing posture (prompt-injection aware)

  **What to do**:
  - Write `design/security-and-permissions.md` covering:
    - Permission rules strategy (`allow/ask/deny`) for Bash/Edit/WebFetch/MCP/Task
    - Hook validation strategy (treat hook stdin JSON as untrusted)
    - Bash sandboxing requirements (domains/filesystem)
    - How to prevent “hook script becomes an exploit vector”
  - Include a recommended `.claude/settings.json` snippet (documented; not auto-installed).

  **External References**:
  - `https://code.claude.com/docs/en/permissions`
  - `https://code.claude.com/docs/en/sandboxing`

  **Acceptance Criteria**:
  - [ ] Document contains a minimal recommended denylist for secrets and risky network tools

  **QA Scenarios**:
  - Scenario: Security doc exists
    Tool: Bash
    Steps:
      1. `test -f design/security-and-permissions.md`
      2. `rg -n "deny|sandbox|prompt injection" design/security-and-permissions.md`
    Expected Result: core security topics present
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/security.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (security policy + safe defaults)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 4 (with Tasks 14-17, 19)

- [ ] 19. Design the “selftest” verification harness (agent-executable)

  **What to do**:
  - Write `design/selftest.md` specifying a repeatable verification script/skill that:
    - Validates plugin loads in CC CLI
    - Exercises each workflow (ulw, plan/start-work, ralph-loop) on a tiny fixture project
    - Captures evidence logs
  - Guardrail: selftest must NOT invoke `claude` via Bash/hooks (no programmatic CC spawning). It must run inside a single CC session via skills/hooks and ordinary tools.
  - Define a minimal fixture repo structure (small TS project) used only for testing.

  **References**:
  - `https://code.claude.com/docs/en/cli-reference` (debug flags)
  - `https://code.claude.com/docs/en/plugins-reference` (plugin load)

  **Acceptance Criteria**:
  - [ ] Selftest design includes at least 6 scenarios with commands and expected outputs

  **QA Scenarios**:
  - Scenario: Selftest has scenario count
    Tool: Bash
    Steps:
      1. `test -f design/selftest.md`
      2. `python - <<'PY'
import re
txt=open('design/selftest.md','r',encoding='utf-8').read()
print(len(re.findall(r'^Scenario:', txt, flags=re.M)))
PY`
    Expected Result: count >= 6
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/selftest-scenarios.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (requires operational CLI detail)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 4 (with Tasks 14-18)

- [ ] 20. Produce the concrete CC plugin design spec (what files we will ship)

  **What to do**:
  - Write `design/plugin-spec.md` listing the exact plugin tree to implement, including:
    - `.claude-plugin/plugin.json`
    - `agents/*.md` (OMO-equivalent subagents)
    - `skills/*/SKILL.md` and `commands/*.md` (OMO-equivalent slash workflows)
    - `hooks/hooks.json`
    - `.mcp.json` (only if needed for tool parity)
    - `scripts/*` (hook router + utilities)
  - For each file, include purpose + acceptance criteria + owner (hook/skill/agent).

  **References**:
  - `design/cc-plugin-architecture.md`
  - `design/omo-to-cc-mapping.md`
  - `https://code.claude.com/docs/en/plugins-reference`

  **Acceptance Criteria**:
  - [ ] Spec includes all plugin components required by Tier A parity features

  **QA Scenarios**:
  - Scenario: Plugin spec enumerates required roots
    Tool: Bash
    Steps:
      1. `test -f design/plugin-spec.md`
      2. `rg -n "plugin\.json|hooks\.json|agents/|skills/" design/plugin-spec.md`
    Expected Result: all key components referenced
    Evidence: `.sisyphus/evidence/cc-omo-parity/design/plugin-spec.log`

  **Recommended Agent Profile**:
  - Category: `writing` (spec enumeration)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: NO (depends on Tasks 14-19 completing)
  - Parallel Group: Wave 5 (sequential start)
  - Blocked By: Tasks 14-19

- [ ] 21. Explicitly document non-portable OMO features + CC workarounds

  **What to do**:
  - Add a dedicated “Hard gaps + workarounds” section to `design/omo-to-cc-mapping.md` covering at least:
    - Hidden model override via OpenCode DB mutation (`src/plugin/ultrawork-model-override.ts`)
    - First-class custom tools vs CC MCP-only tool extension
    - OMO hashline edit tool (stale-line safety) and CC alternatives
    - OMO tmux multi-pane background visualization and CC alternatives
    - OMO session manager tooling vs CC session management primitives
  - For each gap, include: why it’s not possible, the closest CC-native approximation, and parity tier.

  **References**:
  - `src/plugin/ultrawork-model-override.ts`
  - `docs/features.md`
  - `https://code.claude.com/docs/en/plugins-reference`
  - `https://code.claude.com/docs/en/hooks`
  - `https://code.claude.com/docs/en/mcp`

  **Acceptance Criteria**:
  - [ ] Hard gaps section includes >=5 items and assigns Tier C where appropriate

  **QA Scenarios**:
  - Scenario: Hard gaps enumerated
    Tool: Bash
    Steps:
      1. `rg -n "Hard gaps" design/omo-to-cc-mapping.md`
      2. `python - <<'PY'
import re
txt=open('design/omo-to-cc-mapping.md','r',encoding='utf-8').read()
sec=re.split(r'Hard gaps', txt, maxsplit=1)
print('has_section', len(sec)>1)
print('tier_c', len(re.findall(r'Tier C', txt)))
PY`
    Expected Result: section exists; Tier C appears at least once
    Evidence: `.sisyphus/evidence/cc-omo-parity/mapping/hard-gaps.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (technical feasibility + explicit gaps)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 3 (with Tasks 11-13)
  - Blocked By: Tasks 8, 9

- [ ] 22. Research “base OpenCode CLI” dependencies (what OMO relied on)

  **What to do**:
  - Create `design/opencode-dependency-audit.md` that answers:
    - Which OMO features require OpenCode plugin APIs (custom tool registry, message transforms, TUI toast, session storage)
    - Which are portable to CC plugin mechanisms
  - Use a “feature → dependency” table; each row cites an OMO file.

  **References**:
  - `src/index.ts` (plugin initialization)
  - `src/plugin/*` (hook handlers, tool/agent wiring)
  - `src/plugin-handlers/*` (config pipeline)

  **Acceptance Criteria**:
  - [ ] Audit lists at least 10 dependency rows with file pointers

  **QA Scenarios**:
  - Scenario: Dependency audit exists and has rows
    Tool: Bash
    Steps:
      1. `test -f design/opencode-dependency-audit.md`
      2. `python - <<'PY'
import re
txt=open('design/opencode-dependency-audit.md','r',encoding='utf-8').read()
print('rows', len(re.findall(r'^\|', txt, flags=re.M)))
PY`
    Expected Result: table present (row count > 20 including header/separator)
    Evidence: `.sisyphus/evidence/cc-omo-parity/omo/opencode-audit.log`

  **Recommended Agent Profile**:
  - Category: `unspecified-high` (dependency analysis)
  - Skills: none

  **Parallelization**:
  - Can Run In Parallel: YES
  - Parallel Group: Wave 5 (can run alongside Task 20 once architecture is stable)
  - Blocked By: Tasks 8-10

---

## Final Verification Wave

- Validate mapping coverage: every OMO feature area present; all gaps justified.
- Validate CC feasibility: every plugin mechanism referenced exists in docs and matches constraints.
- Validate the design is implementable without Agent Teams or spawning Claude instances.

---

## Commit Strategy

- No git commits are required for research/design output; if implementation is started, commit in small vertical slices: `docs(mapping)`, `plugin(hooks)`, `plugin(agents)`, `plugin(mcp)`, `plugin(selftest)`.

---

## Success Criteria

- A single CC plugin design exists that can plausibly reproduce OMO workflows within CC’s extension points.
- Explicit, exhaustive parity mapping exists, including known hard gaps.
- Step-by-step implementation plan is ready for an execution agent.
