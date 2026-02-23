# OMO Inventory (oh-my-opencode)

## Purpose

This document is the Phase-1 inventory of oh-my-opencode (OMO): what it does, how it works, and where each capability lives in the repository.

Primary goal: give enough precision (file pointers + semantics) to map each capability to a Claude Code CLI plugin equivalent.

## Sources

- Feature surface: `docs/features.md`, `docs/guide/overview.md`
- Orchestration semantics: `docs/orchestration-guide.md`, `docs/guide/understanding-orchestration-system.md`
- Runtime wiring: `src/index.ts`, `src/create-tools.ts`, `src/create-hooks.ts`, `src/plugin/chat-message.ts`

Additional catalogs already maintained in-repo:
- Agents catalog: `src/agents/AGENTS.md`
- Tools catalog: `src/tools/AGENTS.md`
- Hooks catalog: `src/hooks/AGENTS.md`

## Features

### Agents

OMO provides 11 agents (see `docs/features.md` and `src/agents/AGENTS.md`).

Core agents (user-facing):
- Sisyphus (default orchestrator): `src/agents/sisyphus.ts`
- Hephaestus (autonomous deep worker): `src/agents/hephaestus.ts`
- Atlas (executor for planned work): `src/agents/atlas/agent.ts`

Planning layer:
- Prometheus (planner): `src/agents/prometheus/*`
- Metis (plan consultant): `src/agents/metis.ts`
- Momus (plan reviewer): `src/agents/momus.ts`

Specialized leaf workers:
- Oracle (architecture/debug review): `src/agents/oracle.ts`
- Librarian (docs/OSS research): `src/agents/librarian.ts`
- Explore (codebase search): `src/agents/explore.ts`
- Multimodal-Looker (image/pdf): `src/agents/multimodal-looker.ts`

Category executor:
- Sisyphus-Junior: spawned by the `task` tool categories (see `src/agents/AGENTS.md`).

Tool restrictions are centralized in agent factories (see `src/agents/*.ts`) and summarized in `src/agents/AGENTS.md`.

### Skills / Commands

Built-in skills (as SKILL.md + TypeScript wrappers):
- playwright: `src/features/builtin-skills/playwright/SKILL.md`, `src/features/builtin-skills/skills/playwright.ts`
- frontend-ui-ux: `src/features/builtin-skills/frontend-ui-ux/SKILL.md`, `src/features/builtin-skills/skills/frontend-ui-ux.ts`
- git-master: `src/features/builtin-skills/git-master/SKILL.md`, `src/features/builtin-skills/skills/git-master.ts`
- dev-browser / agent-browser: `src/features/builtin-skills/dev-browser/SKILL.md`, `src/features/builtin-skills/agent-browser/SKILL.md`

Built-in commands (templates): `src/features/builtin-commands/templates/*`
- init-deep: `src/features/builtin-commands/templates/init-deep.ts`
- start-work: `src/features/builtin-commands/templates/start-work.ts`
- ralph-loop / ulw-loop / cancel-ralph: `src/features/builtin-commands/templates/ralph-loop.ts`
- refactor: `src/features/builtin-commands/templates/refactor.ts`
- stop-continuation: `src/features/builtin-commands/templates/stop-continuation.ts`
- handoff: `src/features/builtin-commands/templates/handoff.ts`

Discovery/registration:
- Slash command discovery is wired via tool registry: `src/plugin/tool-registry.ts` uses `discoverCommandsSync(...)` and the `skill` tool.

### Tools

Tool inventory is enumerated in `src/tools/AGENTS.md` and assembled in `src/plugin/tool-registry.ts`.

Key integration points:
- Tool assembly + filtering: `src/plugin/tool-registry.ts`
- Hook tiering around tools: `src/plugin/hooks/create-tool-guard-hooks.ts`, `src/plugin/tool-execute-before.ts`, `src/plugin/tool-execute-after.ts`

Tool catalog (by family; authoritative definitions are in `src/tools/AGENTS.md`):

- Delegation:
  - `task` (delegation to categories and/or subagent types)
  - `call_omo_agent` (direct OMO agent invocation)
- Background control:
  - `background_output`, `background_cancel`
- Search/navigation:
  - `glob`, `grep`, `ast_grep_search`, `ast_grep_replace`
  - LSP: `lsp_goto_definition`, `lsp_find_references`, `lsp_symbols`, `lsp_diagnostics`, `lsp_prepare_rename`, `lsp_rename`
- Session history:
  - `session_list`, `session_read`, `session_search`, `session_info`
- Skill/command:
  - `skill`, `skill_mcp`, `slashcommand`
- Editing safety:
  - hashline edit tool replaces standard `edit` when enabled (see `src/plugin/tool-registry.ts`)
- Misc:
  - `interactive_bash` (tmux)
  - `look_at` (multimodal)

### Hooks / Automation

Hook inventory is enumerated in `src/hooks/AGENTS.md` and exported via `src/hooks/index.ts`.

Hook composition tiers:
- Core hooks: `src/plugin/hooks/create-core-hooks.ts`
- Continuation hooks: `src/plugin/hooks/create-continuation-hooks.ts`
- Skill hooks: `src/plugin/hooks/create-skill-hooks.ts`

Hook invocation wiring occurs in the OpenCode hook handlers, e.g. `src/plugin/chat-message.ts`.

Hook inventory (tiered) is captured in `src/hooks/AGENTS.md`. Key hooks that define OMO workflows:

- keyword-detector:
  - Implementation: `src/hooks/keyword-detector/hook.ts` and `src/hooks/keyword-detector/ultrawork/*`
  - Injects mode messages and sets message variant (e.g., `max`) on ultrawork.
- start-work:
  - Implementation: `src/hooks/start-work/start-work-hook.ts`
  - Creates/resumes `.agent-kit/boulder.json`, forces agent to Atlas.
- atlas (continuation hook):
  - Implementation: `src/hooks/atlas/*`
  - Orchestrates boulder sessions and injects continuation prompts on session idle.
- ralph-loop:
  - Implementation: `src/hooks/ralph-loop/*`
  - Loop state persisted to `.agent-kit/ralph-loop.local.md`.

### Persistence / State

Primary continuity/state artifacts:
- Plans: `.agent-kit/plans/*.md` (created by Prometheus, executed by Atlas)
- Drafts: `.agent-kit/drafts/*.md` (Prometheus working notes)
- Boulder state: `.agent-kit/boulder.json` (tracks active plan + progress)
  - Implementation: `src/features/boulder-state/*`
  - Used by `/start-work` hook: `src/hooks/start-work/start-work-hook.ts`
- Ralph loop state: `.agent-kit/ralph-loop.local.md` (gitignored)
  - Implementation: `src/hooks/ralph-loop/*`
- Notepads: `.agent-kit/notepads/<plan-name>/*` (wisdom accumulation)
  - See: `docs/guide/understanding-orchestration-system.md` and `src/hooks/sisyphus-junior-notepad/*`

## Workflows

This section describes the four primary user-facing workflows called out by OMO docs and code.

### Sisyphus (Default Orchestrator)

User surface:
- Default agent; also the orchestration "front door" for keyword modes.

Key behavior:
- Delegation-first instructions + tool selection + hard blocks are generated dynamically.
  - Prompt builder: `src/agents/dynamic-agent-prompt-builder.ts`
  - Sisyphus agent factory: `src/agents/sisyphus.ts`

Keyword influence:
- Keyword detection injects mode-specific messages into the user prompt.
  - Hook: `src/hooks/keyword-detector/hook.ts`
  - Ultrawork message routing: `src/hooks/keyword-detector/ultrawork/*`

Ultrawork modifier:
- YES (via keyword detector). Side effects include setting message variant to `max` and showing a toast.
  - See: `src/hooks/keyword-detector/hook.ts`
  - Potential hidden model override (OpenCode-specific): `src/plugin/ultrawork-model-override.ts`

### Hephaestus (Deep Worker)

User surface:
- A separate primary agent optimized for deep autonomous execution.

Key behavior:
- Strong "do not ask, just do" posture and persistence until completion.
- Uses the same dynamic prompt-builder sections for delegation and tool selection.
  - Implementation: `src/agents/hephaestus.ts`

Ultrawork modifier:
- YES, if the user includes `ulw`/`ultrawork` in the prompt.
  - Keyword detection is global except for planner agents and background task sessions (see `src/hooks/keyword-detector/hook.ts`).

### Prometheus (Planner)

User surface:
- Planner agent that performs interview-style clarification and produces plans.
- Invoked by switching the active agent to Prometheus.
  - Behavioral description: `docs/orchestration-guide.md`

Core constraints:
- Prometheus is planner-only (restricted writes). A dedicated hook enforces markdown-only / .agent-kit-only behavior.
  - Hook: `src/hooks/prometheus-md-only/*`
  - Ultrawork planner message: `src/hooks/keyword-detector/ultrawork/planner.ts`

Ultrawork modifier:
- NO (ultrawork is explicitly filtered out for planner agents).
  - Filter: `src/hooks/keyword-detector/hook.ts` (planner agent filter)

### Atlas (/start-work Executor)

User surface:
- `/start-work` triggers switching to Atlas and starting/resuming execution.
- The hook decides whether to resume from `.agent-kit/boulder.json` or create new state from the newest incomplete plan.
  - Hook: `src/hooks/start-work/start-work-hook.ts`
  - State: `src/features/boulder-state/*`

Continuation/orchestration:
- Atlas orchestration for boulder sessions is enforced by a continuation-tier hook that monitors session idle events and injects continuation prompts.
  - Hook: `src/hooks/atlas/*`
  - Hook assembly: `src/plugin/hooks/create-continuation-hooks.ts` (atlasHook)

Ultrawork modifier:
- Not a first-class mode for Atlas.
  - `/start-work` strips `ultrawork|ulw` keywords from an explicitly requested plan name (so plan matching works).
  - See: `extractUserRequestPlanName()` in `src/hooks/start-work/start-work-hook.ts`

## Agents

Agent inventory is summarized in `src/agents/AGENTS.md` (models, modes, restrictions). This section adds workflow/prompt-generation notes.

| Agent | Purpose/Role | Process / Workflow | Prompt Generation | Delegation | Tool allow/deny (high-level) |
| --- | --- | --- | --- | --- | --- |
| Sisyphus | Default orchestrator | Intent gate -> explore -> delegate -> verify | Dynamic sections assembled by `src/agents/dynamic-agent-prompt-builder.ts` and used by `src/agents/sisyphus.ts` | Yes (heavy `task` usage) | Full toolset; denies `call_omo_agent` (see `src/agents/sisyphus.ts`) |
| Hephaestus | Deep autonomous executor | EXPLORE -> PLAN -> EXECUTE -> VERIFY; completion guarantee | Dynamic sections via `src/agents/dynamic-agent-prompt-builder.ts` in `src/agents/hephaestus.ts` | Yes (heavy explore/librarian, plus category routing) | Full toolset (model requirement: GPT codex) |
| Prometheus | Planner/interviewer | Interview mode -> draft -> plan generation; consult Metis/Momus | Dedicated planner prompt modules in `src/agents/prometheus/*` | Delegates to Explore/Librarian for research | Write/Edit restricted by hook `src/hooks/prometheus-md-only/*` |
| Atlas | Plan executor / conductor | Executes `.agent-kit/plans/*` via `/start-work`; resume via boulder | Atlas prompt sections in `src/agents/atlas/*` and orchestration enforced by `src/hooks/atlas/*` | Delegation is primarily enforced via orchestration hooks and task tooling | Denies `task` + `call_omo_agent` (see `src/agents/AGENTS.md`) |
| Oracle | Read-only architectural advisor | Consultation only, returns guidance | Static agent definition in `src/agents/oracle.ts` | No (read-only) | Denies write/edit/task/call_omo_agent |
| Librarian | External docs/OSS researcher | Evidence-based research, citations | Static agent definition in `src/agents/librarian.ts` | No (read-only) | Denies write/edit/task/call_omo_agent |
| Explore | Codebase search/grep | Fast internal repo discovery | Static agent definition in `src/agents/explore.ts` | No (read-only) | Denies write/edit/task/call_omo_agent |
| Multimodal-Looker | Visual/PDF analysis | Extract info from images/PDFs | Static agent definition in `src/agents/multimodal-looker.ts` | No | Allowlist-only tools (see `src/agents/AGENTS.md`) |
| Metis | Plan consultant | Identify hidden intent, missing ACs | Static agent definition in `src/agents/metis.ts` | No | Read-only (by policy) |
| Momus | Plan reviewer | Validate plan; OKAY/REJECT loop | Static agent definition in `src/agents/momus.ts` | No | Denies write/edit/task |
| Sisyphus-Junior | Category executor | Executes delegated tasks with strict verify | Built from categories + skills in task tool | No nested delegation | N/A (depends on category profile) |

Notes:
- Tool gates are enforced in both agent config and via tool-guard hooks (e.g. `write-existing-file-guard`, `prometheus-md-only`).

## Tools

Canonical tool inventory (name -> purpose -> parameters) is in `src/tools/AGENTS.md`.

Integration points:
- Tool registration and conditional enabling: `src/plugin/tool-registry.ts`
- Background manager + tmux visualizer: `src/features/background-agent/*`, `src/features/tmux-subagent/*`

Workflow associations (high-level):
- Sisyphus/Hephaestus: heavy use of `task`, `grep`, `glob`, `lsp_diagnostics`, and (optionally) background task tools.
- Prometheus: uses exploration subagents and is constrained to writing `.agent-kit/**/*.md`.
- Atlas execution: mediated by `/start-work` and boulder state; delegates work via task system and continuation hooks.

## Hooks

Canonical hook catalog is in `src/hooks/AGENTS.md`.

Hooks that matter most for parity (examples):
- keyword-detector: injects ultrawork/search/analyze mode prompts (`src/hooks/keyword-detector/*`).
- auto-slash-command: replaces messages with command templates (`src/hooks/auto-slash-command/*`).
- start-work: selects/resumes plan via boulder state (`src/hooks/start-work/*`).
- todo-continuation-enforcer: boulder continuation for incomplete todos (`src/hooks/todo-continuation-enforcer/*`).
- atlas: boulder session orchestrator (`src/hooks/atlas/*`).
- ralph-loop: iterative loop continuation (`src/hooks/ralph-loop/*`).
- rules-injector + directory injectors: context/rules injection (`src/hooks/rules-injector/*`, `src/hooks/directory-agents-injector/*`, `src/hooks/directory-readme-injector/*`).

Portability note (for CC mapping):
- OMO relies on OpenCode hook event names (`chat.message`, `tool.execute.before/after`, `messages.transform`, `session.idle`). CC has similar but not identical events and different context injection semantics.

## Persistence

List all artifacts used for continuity:
- `.agent-kit/drafts/`
- `.agent-kit/plans/`
- `.agent-kit/boulder.json`
- `.agent-kit/notepads/`
- task storage (if enabled)


See "Persistence / State" section above plus:
- Atlas hook state: in-memory per-session state inside `src/hooks/atlas/atlas-hook.ts`
- Todo continuation enforcer: `src/hooks/todo-continuation-enforcer/*`

Core persistence modules:
- Boulder state storage: `src/features/boulder-state/storage.ts`
- Ralph loop state storage: `src/hooks/ralph-loop/storage.ts`
