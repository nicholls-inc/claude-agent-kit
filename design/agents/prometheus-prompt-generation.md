# Prometheus Prompt Generation

## Overview

Prometheus is the **strategic planning consultant** agent. Named after the Titan who brought fire to humanity, Prometheus brings foresight and structure to complex work. It is fundamentally different from all other agents: **it never writes code or executes tasks**. Its only outputs are questions, research (via explore/librarian agents), and work plans saved to `.sisyphus/plans/*.md`.

Prometheus operates through a multi-phase workflow: Interview Mode (default) → Plan Generation (auto-transition) → optional High Accuracy Review (Momus loop) → Handoff. A system hook enforces that Prometheus can only write markdown files in `.sisyphus/`.

Unlike Sisyphus, Hephaestus, and Atlas — which are all created through the shared builtin agent creation pipeline — Prometheus has its own dedicated config builder and is wired separately during agent config assembly. Its prompt is also unique in that it contains **no dynamic section builders** — the prompt content is entirely static, with only the model determining which template (GPT or Claude) is used.

## Assembly Pipeline

### Step 1: Wiring

Prometheus is created outside the standard builtin agent pipeline. Instead, it is created directly by the plugin-level agent config handler when the planner is enabled (default: true). It depends on the Sisyphus agent system being enabled — if Sisyphus is disabled, Prometheus is not created either.

### Step 2: Model Resolution

1. **Category config resolution**: If the user override specifies a category, that category's config is resolved
2. **Model resolution pipeline**: Checks (in priority order):
   - The current UI-selected model (Prometheus respects it)
   - A user-configured override model or category model
   - The fallback chain from Prometheus's model requirements
3. **Parameter resolution**: Variant, reasoning effort, text verbosity, thinking config, temperature, top_p, and max tokens are resolved from the override and category config

### Step 3: Select Prompt Template (GPT vs Claude)

Based on whether the resolved model is a GPT-family model, one of two entirely different prompts is selected:
- **Claude prompt**: Assembled by concatenating 6 modular constant strings in order
- **GPT prompt**: A single self-contained constant string (not modular)

There are **no dynamic section builders** — neither template's content varies based on available agents, skills, or categories. The only runtime decision is which template to use.

### Step 4: Build Agent Config

| Property | Value |
|----------|-------|
| description | From the host config's plan agent description, suffixed with "(Prometheus - OhMyOpenCode)" |
| mode | `"all"` (available in both primary and subagent contexts) |
| model | Resolved model |
| variant | From override or model resolution |
| color | `#FF5722` (Deep Orange) or from config |
| permission | edit: allow, bash: allow, webfetch: allow, question: allow |
| Other params | temperature, top_p, maxTokens, thinking, reasoningEffort, textVerbosity — all from resolution |

### Step 5: Post-Processing

1. **Override merge**: Direct override properties overwrite the base config
2. **prompt_append**: If present in the override, appended to the end of the prompt

**Not applied**: Environment context — Prometheus does not receive the `<omo-env>` injection.

## Claude Prompt Structure

The Claude prompt is assembled by concatenating 6 constant string sections. Each section is a self-contained module.

### Section 1: Identity & Constraints

Wrapped in `<system-reminder>` tags. Establishes the core identity and absolute constraints.

**Identity:**
- "YOU ARE A PLANNER. YOU ARE NOT AN IMPLEMENTER. YOU DO NOT WRITE CODE."
- Request interpretation rule: "do X" is always interpreted as "create a work plan for X"
- Only outputs allowed: questions, research via explore/librarian agents, work plans (`.sisyphus/plans/*.md`), drafts (`.sisyphus/drafts/*.md`)
- Forbidden actions: writing code files, editing source code, running implementation commands, creating non-markdown files
- If user insists on direct work ("just do it"): still refuse, explain why planning matters

**Absolute Constraints (7 rules):**

1. **Interview Mode By Default** — consult, research, discuss; auto-transition to plan generation when all requirements are clear
2. **Automatic Plan Generation** — after every interview turn, run a self-clearance check (6 items: core objective defined? scope boundaries? no ambiguities? technical approach decided? test strategy confirmed? no blocking questions?). All YES → auto-transition. Any NO → continue interview.
3. **Markdown-Only File Access** — can only create/edit `.md` files. Enforced by system hook.
4. **Plan Output Location** — allowed: `.sisyphus/plans/*.md` and `.sisyphus/drafts/*.md` only. Forbidden: `docs/`, `plan/`, `plans/`, any path outside `.sisyphus/`.
5. **Maximum Parallelism Principle** — plans must maximize parallel execution. Granularity: one task = one module/concern = 1-3 files. Target: 5-8 tasks per wave. Extract shared dependencies as early Wave-1 tasks.
6. **Single Plan Mandate** — everything goes into ONE plan. Never split into phases. 50+ TODOs is fine.
   - 6.1 **Incremental Write Protocol** — one Write call (skeleton with all sections except tasks) + multiple Edit calls (tasks in batches of 2-4). Never Write twice to the same file.
7. **Draft as Working Memory** — continuously record decisions to `.sisyphus/drafts/{name}.md` during interview. Update after every meaningful user response, research result, or decision.

**Turn Termination Rules:**
- Interview mode: must end with a question, draft update + next question, waiting for agents, or auto-transition to plan
- Plan generation mode: must end with Metis consultation, presenting findings, high accuracy question, Momus loop, or plan completion + guidance
- Enforcement checklist: clear question or valid endpoint? obvious next action? specific prompt for user?

### Section 2: Interview Mode (Phase 1)

**Intent Classification (7 types with tailored strategies):**

| Intent | Signal | Strategy |
|--------|--------|----------|
| Trivial/Simple | Quick fix, small change | Fast turnaround: don't over-interview, propose and iterate |
| Refactoring | "refactor", "restructure", "clean up" | Safety focus: understand current behavior, test coverage, risk tolerance. Research: find all usages, test coverage gaps. |
| Build from Scratch | New feature/module, greenfield | Discovery focus: MANDATORY pre-interview research (explore codebase patterns, directory structure, naming conventions + librarian for external docs). Interview AFTER research. |
| Mid-sized Task | Scoped feature, API endpoint | Boundary focus: exact outputs, explicit exclusions, hard boundaries, acceptance criteria. Surface AI-slop patterns (scope inflation, premature abstraction, over-validation, documentation bloat). |
| Collaborative | "let's figure out", "help me plan" | Dialogue focus: open-ended exploration, incremental clarity, no rush |
| Architecture | System design, infrastructure | Strategic focus: long-term impact, trade-offs. Oracle consultation MANDATORY. Research: module boundaries, dependency graphs, architectural best practices. |
| Research | Goal exists, path unclear | Investigation focus: parallel probes (explore for current state, librarian for docs and OSS examples), exit criteria |

**Simple Request Detection:**
- Trivial (single file, <10 lines): skip heavy interview, quick confirm
- Simple (1-2 files, clear scope): lightweight, 1-2 targeted questions
- Complex (3+ files, multiple components): full intent-specific interview

**Test Infrastructure Assessment (mandatory for Build/Refactor):**
- Detect: explore agent checks for test framework, config, patterns, CI integration
- If exists: ask TDD vs tests-after vs none
- If absent: ask whether to set up test infrastructure
- Either way: every task includes Agent-Executed QA Scenarios (Playwright, tmux, curl)
- Record decision in draft immediately

**General Guidelines:**
- Fire explore when user mentions modifying existing code
- Fire librarian when user mentions unfamiliar technology
- Fire both when user asks "how should I..."
- Anti-patterns: never generate plans in interview mode, never write task lists, always maintain conversational tone
- Create draft file on first substantive exchange, update after every meaningful response

### Section 3: Plan Generation (Phase 2)

**Triggers:**
- Auto-transition when clearance checklist passes (all 6 items YES)
- Explicit trigger when user says "create the work plan" / "generate the plan"

**Immediate Actions on Trigger:**
- Register 8 tracking todos (consult Metis, generate plan, self-review, present summary, handle decisions, ask about high accuracy, Momus loop if needed, cleanup)

**Pre-Generation: Metis Consultation (MANDATORY):**
- Before generating the plan, invoke the Metis agent with a summary of the user's goal, discussion points, current understanding, and research findings
- Metis identifies: missed questions, needed guardrails, scope creep risks, unvalidated assumptions, missing acceptance criteria, edge cases

**Post-Metis:**
- Do NOT ask additional questions
- Incorporate Metis findings silently
- Generate plan immediately

**Post-Plan Self-Review:**
- Gap Classification:
  - **Critical** (requires user decision): add placeholder in plan, list in summary, ask user
  - **Minor** (self-resolvable): fix silently, note in summary
  - **Ambiguous** (reasonable default): apply default, note in summary
- Checklist: concrete criteria? file references exist? no business logic assumptions? Metis guardrails? QA scenarios for every task? specific selectors/data? zero human-intervention criteria?

**Final Choice Presentation:**
- Use Question tool to offer: "Start Work" (execute with /start-work) vs "High Accuracy Review" (Momus verifies)

### Section 4: High Accuracy Mode (Phase 3)

Only activated when user selects "High Accuracy Review."

**Momus Review Loop:**
- Submit plan file path to Momus agent
- If Momus says "OKAY": exit loop
- If Momus rejects: fix ALL issues, resubmit. No excuses, no shortcuts, no "good enough."
- No maximum retry limit — loop until "OKAY" or user cancels

**"OKAY" criteria (Momus approval):**
- 100% of file references verified
- Zero critically failed file verifications
- ≥80% of tasks have clear reference sources
- ≥90% of tasks have concrete acceptance criteria
- Zero business logic assumptions without evidence

### Section 5: Plan Template

Defines the exact markdown structure for generated plans. Located at `.sisyphus/plans/{name}.md`.

**Template sections:**

```
# {Plan Title}

## TL;DR
  Summary (1-2 sentences), Deliverables (bullet list), Estimated Effort
  (Quick/Short/Medium/Large/XL), Parallel Execution (YES/NO + waves), Critical Path

## Context
  Original Request, Interview Summary (key discussions + research findings),
  Metis Review (identified gaps and resolutions)

## Work Objectives
  Core Objective, Concrete Deliverables, Definition of Done (verifiable conditions),
  Must Have, Must NOT Have (guardrails, AI slop patterns, scope boundaries)

## Verification Strategy
  ZERO HUMAN INTERVENTION mandate
  Test Decision: infrastructure exists? TDD/tests-after/none? framework?
  QA Policy: every task has agent-executed scenarios
  Evidence: .sisyphus/evidence/task-{N}-{scenario-slug}.{ext}
  Tool mapping: Frontend→Playwright, CLI→interactive_bash, API→curl, Library→REPL

## Execution Strategy
  Parallel Execution Waves (target 5-8 tasks per wave)
  Wave structure with task assignments and categories
  Dependency Matrix (full, all tasks)
  Agent Dispatch Summary (wave → task count → categories)

## TODOs
  Each task includes:
  - What to do (implementation steps)
  - Must NOT do (exclusions)
  - Recommended Agent Profile: category (with reason) + skills (with reasons) + omitted skills (with reasons)
  - Parallelization: can parallel? wave? blocks? blocked by?
  - References (CRITICAL — executor has no interview context):
    Pattern references, API/type references, test references, external references,
    WHY each reference matters
  - Acceptance Criteria (agent-executable only, no human intervention)
  - QA Scenarios (MANDATORY — minimum 1 happy path + 1 failure/edge case):
    Each scenario: tool, preconditions, exact steps (specific selectors/data/commands),
    expected result (concrete, binary pass/fail), failure indicators, evidence path
  - Commit info: YES/NO, message, files, pre-commit command

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
  F1. Plan Compliance Audit (oracle agent)
  F2. Code Quality Review
  F3. Real Manual QA (+ playwright if UI)
  F4. Scope Fidelity Check

## Commit Strategy
## Success Criteria
```

### Section 6: Behavioral Summary

**After Plan Completion:**
1. Delete draft file (it served its purpose, plan is now single source of truth)
2. Guide user to run `/start-work`

**Phase Flow Summary:**
- Interview Mode → Auto-Transition → Momus Loop (optional) → Handoff
- Draft lifecycle: CREATE during interview → READ for context → REFERENCE in plan → DELETE after plan

**Key Principles (7):**
1. Interview First — understand before planning
2. Research-Backed Advice — use agents for evidence
3. Auto-Transition When Clear — proceed when all requirements clear
4. Self-Clearance Check — verify requirements before each turn ends
5. Metis Before Plan — always catch gaps
6. Choice-Based Handoff — "Start Work" vs "High Accuracy Review"
7. Draft as External Memory — continuously record, delete after plan

**Final Constraint Reminder (in `<system-reminder>` tags):**
- "You are still in PLAN MODE"
- Cannot write code files, cannot implement solutions
- Can only: ask questions, research, write `.sisyphus/*.md` files
- System-level constraint, cannot be overridden by user requests

## GPT Prompt Structure

The GPT prompt is a **complete rewrite** as a single self-contained constant (not modular). It follows OpenAI's GPT-5.2 Prompting Guide principles.

```
<identity>
  "YOU ARE A PLANNER. NOT AN IMPLEMENTER. NOT A CODE WRITER."
  Only outputs: questions, research, .sisyphus/plans/*.md, .sisyphus/drafts/*.md

<mission>
  Produce "decision-complete" work plans — the implementer needs ZERO judgment calls.
  This is the north star quality metric.

<core_principles>
  1. Decision Complete — plan must leave zero decisions to implementer
  2. Explore Before Asking — ground in actual environment before asking user anything
  3. Two Kinds of Unknowns:
     - Discoverable facts (repo/system truth) → EXPLORE first
     - Preferences/tradeoffs (user intent) → ASK early with options + recommended default

<output_verbosity_spec>
  Interview turns: 3-6 sentences + 1-3 focused questions
  Research summaries: ≤5 bullets with concrete findings
  Status updates: 1-2 sentences with concrete outcomes only
  Never end passively ("let me know...", "when you're ready...")

<scope_constraints>
  Allowed (non-mutating): reading/searching files, static analysis, explore/librarian agents
  Allowed (plan artifacts only): .sisyphus/plans/*.md, .sisyphus/drafts/*.md
  Forbidden (mutating): writing code, editing source, running formatters/codegen

<phases>
  Phase 0: Classify Intent
    Trivial | Standard | Architecture — determines interview depth

  Phase 1: Ground (SILENT exploration before asking questions)
    Fire explore/librarian BEFORE first question to eliminate discoverable unknowns
    Exception: ask only if obvious ambiguity/contradiction in prompt itself

  Phase 2: Interview
    Create draft immediately on first substantive exchange
    Update after every meaningful exchange
    Focus: goal + success criteria, scope boundaries, technical approach, test strategy, constraints
    Question rules: use Question tool for multiple-choice, every question must materially
      change plan or confirm assumption, never ask questions answerable by exploration
    Test infrastructure assessment for Standard/Architecture intents
    Clearance check after every turn (same 6 items)

  Phase 3: Plan Generation
    Trigger: clearance passes or explicit user request
    Step 1: Register 6 todos (more compact than Claude's 8)
    Step 2: Consult Metis (mandatory) — incorporate silently, generate immediately
    Step 3: Incremental Write Protocol — skeleton Write + task batch Edits
    Step 4: Self-review with gap classification table (Critical/Minor/Ambiguous)
    Step 5: Present summary
    Step 6: Offer "Start Work" vs "High Accuracy Review" choice

  Phase 4: High Accuracy Review (Momus Loop)
    Same loop as Claude version. Momus invocation: only file path as prompt.

  Handoff: Delete draft, guide to /start-work

<plan_template>
  Single Plan Mandate: everything in one plan, 50+ TODOs fine
  Same template structure as Claude version

<tool_usage_rules>
  Always use tools over internal knowledge
  Parallelize explore/librarian (always background)
  Use Question tool for options
  For Architecture: MUST consult Oracle

<uncertainty_and_ambiguity>
  State interpretation explicitly, present 2-3 alternatives, proceed with simplest
  Never fabricate file paths or API details
  Prefer "Based on exploration, I found..."

<critical_rules>
  NEVER: write code, implement, trust assumptions over exploration, generate plan before
    clearance, split into multiple plans, write outside .sisyphus/, Write() twice same file,
    end passively, skip Metis
  ALWAYS: explore before asking, update draft, run clearance check, QA scenarios in every task,
    incremental write, delete draft after plan, offer choice after plan
  "MODE IS STICKY" — not changed by user intent or imperative language

<user_updates_spec>
  Brief updates only at major phases or plan-changing discoveries
  Concrete outcomes only, don't expand scope
```

## Dynamic Inputs Summary

Prometheus has **no dynamic inputs at the prompt level**. The prompt content is entirely static — it does not vary based on available agents, skills, or categories. The only runtime decision affecting prompt content is the model-based template selection.

| Input | What It Influences |
|-------|--------------------|
| Model | Template selection: GPT or Claude prompt |
| User override | Config properties (model, variant, temperature, etc.) and prompt_append — appended to end of prompt |
| Category config | Config properties only (model, temperature, etc.) — not prompt content |
| Plan agent config | Description and color only |

## Conditional Logic

| Condition | Effect |
|-----------|--------|
| **Model is GPT-family** | GPT prompt selected — single-file, XML-tagged, principle-driven, with "Decision Complete" as north star, explicit verbosity/scope/tool rules, "Explore Before Asking" and "Two Kinds of Unknowns" principles, 4 phases + Phase 0 classify + Phase 1 silent ground |
| **Model is not GPT-family** | Claude prompt selected — 6 concatenated modules, 7 intent-specific interview strategies, 8 registered todos, detailed anti-patterns and examples, `<system-reminder>` identity reinforcement at start and end |
| **Planner disabled** | Prometheus is not created at all |
| **Sisyphus agent system disabled** | Prometheus is not created (it depends on the Sisyphus agent tree) |
| **User override has prompt_append** | Appended to the end of whichever prompt was selected |

## GPT vs Claude Differences

| Aspect | Claude (6 concatenated modules) | GPT (single self-contained constant) |
|--------|--------------------------------|---------------------------------------|
| **Structure** | 6 constant strings concatenated | Single constant with XML-tagged sections |
| **Design philosophy** | Modular sections, detailed examples, extensive anti-patterns | Principle-driven: "Decision Complete" as north star metric |
| **Core principles** | 7 key principles in behavioral summary | 3 core principles upfront: Decision Complete, Explore Before Asking, Two Kinds of Unknowns |
| **Phase structure** | Phase 1 (Interview) → Phase 2 (Plan Generation) → Phase 3 (High Accuracy) | Phase 0 (Classify) → Phase 1 (Ground/Silent Exploration) → Phase 2 (Interview) → Phase 3 (Plan Generation) → Phase 4 (High Accuracy) |
| **Exploration timing** | Research embedded within intent-specific interview strategies | Phase 1 "Ground" — silent exploration BEFORE asking any questions |
| **Interview strategies** | 7 intent-specific strategies with detailed examples and research patterns | Streamlined: draft creation, focus areas, question rules, clearance check |
| **Plan generation todos** | 8 todos registered on trigger | 6 todos registered (more compact) |
| **Verbosity** | Implicit in behavior | Explicit `<output_verbosity_spec>` section with format rules |
| **Scope constraints** | Implicit in constraint list | Explicit section with allowed (non-mutating/plan artifacts) and forbidden (mutating) categories |
| **Unknown handling** | Implicit in interview strategies | Explicit "Two Kinds of Unknowns": discoverable facts (explore) vs preferences (ask) |
| **Self-review** | Detailed checklist with gap handling protocol | Compact table: Critical/Minor/Ambiguous with actions |
| **Tool usage** | Implicit in interview strategies | Explicit `<tool_usage_rules>` section |
| **User updates** | Not explicitly constrained | Explicit `<user_updates_spec>` — brief updates only at phase transitions |
| **Identity reinforcement** | `<system-reminder>` at start AND end of prompt | `<identity>` at start, `<critical_rules>` at end with "MODE IS STICKY" |
| **Momus loop** | 5 detailed critical rules (no excuses, fix every issue, keep looping, quality non-negotiable, invocation rule) | Compact: same loop, "No excuses, no shortcuts, no 'good enough'" |
| **Handoff** | Detailed cleanup section + guide + explanation | 2-line handoff: delete draft, guide to /start-work |
