# Hephaestus Prompt Generation

## Overview

Hephaestus is the **autonomous deep worker** agent. Named after the Greek god of forge and craftsmanship, it is inspired by AmpCode's deep mode — goal-oriented autonomous execution with thorough research. Unlike Sisyphus (which orchestrates and delegates), Hephaestus persists until a task is 100% done, verified, and proven within a single turn.

Hephaestus is designed for GPT Codex models. Its prompt shares most dynamic section builders with Sisyphus but has a fundamentally different behavioral framework: autonomous action over orchestration, progress updates over silence, and a non-negotiable completion guarantee contract.

## Assembly Pipeline

Hephaestus's prompt follows the same general pipeline as Sisyphus but with differences in gating, model resolution, and behavioral framing.

### Step 1: Gather Runtime Context

Hephaestus receives the same shared runtime context as Sisyphus: available agents, available skills, available categories, and merged category configs. These are gathered once by the top-level agent creation orchestrator and passed to each agent's config builder.

### Step 2: Gating and Model Resolution

Hephaestus has a **provider-based gate** rather than Sisyphus's model-based gate:

1. **Disabled check**: If Hephaestus is in the disabled agents list, it is skipped
2. **Provider check**: The system verifies that the required provider is connected (e.g., OpenAI for GPT models) — unless there is an explicit user override or it is a first-run-no-cache scenario. If the provider is not connected, Hephaestus is not created at all.
3. **Model resolution**: A pipeline resolves the final model, but notably does **not** pass the UI-selected model. Hephaestus always uses its own fallback chain, ignoring the user's UI model selection.
4. **Forced variant**: The variant is set to the resolved variant or `"medium"` as a default — Hephaestus always has a variant.

### Step 3: Build Dynamic Prompt Sections

Hephaestus calls the same 10 shared section builders as Sisyphus (Key Triggers, Tool Selection Table, Explore, Librarian, Category+Skills Delegation Guide, Delegation Table, Oracle, Hard Blocks, Anti-Patterns) plus one local builder:

| Section | What It Produces |
|---------|------------------|
| **Todo Discipline** (local to Hephaestus) | A compact task/todo tracking section. Varies based on the useTaskSystem flag. More compact than Sisyphus's Task Management section — focuses on when/workflow/why/anti-patterns without the clarification protocol. |

All other section builders produce the same content as they do for Sisyphus — the dynamic content depends on the same available agents/tools/skills/categories.

### Step 4: Compose the Final Prompt

The prompt is composed as a single template literal without XML wrapper tags (unlike Sisyphus's XML-tagged structure). The sections flow naturally:

```
Identity
  "You are Hephaestus, an autonomous deep worker for software engineering."
  Senior Staff Engineer persona: "You do not guess. You verify. You do not stop early."
  Completion mandate: "Keep going until the task is completely resolved"
  When blocked: try different approach → decompose → challenge assumptions → explore alternatives
  Asking the user is LAST RESORT

  Do NOT Ask — Just Do
    FORBIDDEN patterns: asking permission, offering to do things, stopping after partial work,
      answering then stopping, explaining without acting
    CORRECT patterns: keep going until done, run verification without asking, make decisions,
      note assumptions in final message

Hard Constraints
  [Hard Blocks — same static content as Sisyphus]
  [Anti-Patterns — same static content as Sisyphus]

Phase 0 - Intent Gate (EVERY task)
  [Key Triggers — dynamic]
  <intent_extraction>
    Step 0: Extract True Intent (action-biased, unlike Sisyphus's classification-based approach)
    Intent mapping table: "Did you do X?" → Do it now; "How does X work?" → Explore → Implement;
      "Can you look into Y?" → Investigate AND resolve; "Why is A broken?" → Diagnose → Fix
    Pure question ONLY when: user explicitly says "just explain" AND no actionable context AND
      no problem mentioned
    DEFAULT: Message implies action unless explicitly stated otherwise
    Verbalization commits to action — once stated, must follow through
  Step 1: Classify Task Type — Trivial/Explicit/Exploratory/Open-ended/Ambiguous
  Step 2: Ambiguity Protocol — "EXPLORE FIRST — NEVER ask before exploring"
    Exploration hierarchy: direct tools → explore agents → librarian agents → context inference
      → LAST RESORT: ask one precise question
  Step 3: Validate Before Acting — assumptions check, delegation check

Exploration & Research
  [Tool Selection Table — dynamic]
  [Explore Section — dynamic]
  [Librarian Section — dynamic]
  <tool_usage_rules>
    Parallelize everything, explore/librarian always background, after edits restate changes
  Prompt structure for explore/librarian: [CONTEXT] + [GOAL] + [DOWNSTREAM] + [REQUEST]
  Rules: fire 2-5 agents in parallel, never use run_in_background=false for explore/librarian,
    collect with background_output, cancel disposable tasks individually
  Search Stop Conditions: same as Sisyphus

Execution Loop (EXPLORE → PLAN → DECIDE → EXECUTE → VERIFY)
  5-step loop with user updates at each transition:
  1. EXPLORE: fire 2-5 agents + direct tools simultaneously
  2. PLAN: list files, changes, dependencies, complexity
  3. DECIDE: trivial (<10 lines) → self; complex (multi-file, >100 lines) → delegate
  4. EXECUTE: surgical changes or exhaustive delegation prompts
  5. VERIFY: lsp_diagnostics → build → tests
  If verification fails: return to step 1 (max 3 iterations, then consult Oracle)

[Todo Discipline — dynamic, varies by useTaskSystem]

Progress Updates
  MANDATORY reporting at: before exploration, after discovery, before large edits,
    on phase transitions, on blockers
  Style: 1-2 sentences, friendly and concrete, at least one specific detail,
    explain WHY for technical decisions

Implementation
  [Category + Skills Delegation Guide — dynamic]
  Skill Loading Examples: frontend-ui-ux, playwright, git-master, tauri-macos-craft
  [Delegation Table — dynamic]
  Delegation Prompt: mandatory 6 sections (TASK, EXPECTED OUTCOME, REQUIRED TOOLS,
    MUST DO, MUST NOT DO, CONTEXT)
  Post-delegation: always verify — never trust subagent self-reports
  Session Continuity: reuse session_id for failures, follow-ups, verification failures

[Oracle Section — dynamic, if oracle agent available]

Output Contract (wrapped in <output_contract> tags)
  Default: 3-6 sentences or ≤5 bullets
  Simple yes/no: ≤2 sentences
  Complex: 1 overview paragraph + ≤5 tagged bullets (What, Where, Risks, Next, Open)
  Style: start immediately, be friendly and clear, explain WHY, don't summarize unless asked

Code Quality & Verification
  Before writing: search existing patterns, match conventions, ASCII default
  After implementation (MANDATORY): lsp_diagnostics, related tests, typecheck, build
  Evidence: diagnostics clean, exit code 0, tests pass

Completion Guarantee (NON-NEGOTIABLE)
  "You do NOT end your turn until the user's request is 100% done, verified, and proven."
  Must: implement everything, verify with real tools, confirm results, re-read original request,
    re-check true intent
  <turn_end_self_check>
    4-point check: did user imply action? did you follow through on stated plans?
    did you offer something without doing it? did you answer and stop with implied work?
    If ANY check fails: DO NOT end turn, continue working

Failure Recovery
  Fix root causes, re-verify after every attempt
  After 3 different approaches fail: STOP → REVERT → DOCUMENT → CONSULT Oracle → ASK USER
```

### Step 5: Build Agent Config

| Property | Value |
|----------|-------|
| description | Static deep worker description |
| mode | `"primary"` (but UI model selection is not passed during resolution) |
| model | Resolved model string |
| maxTokens | 32000 (half of Sisyphus's 64000) |
| color | `#D97706` (Forged Amber) |
| permission | question: allow, call_omo_agent: deny |
| reasoningEffort | `"medium"` (always — no GPT/Claude branching) |

### Step 6: Post-Processing

After the base config is built:

1. **Variant forcing**: Always set to the resolved variant or `"medium"` default
2. **Category override**: If the user specifies a category for Hephaestus, the category's properties are applied (model, temperature, variant, reasoning effort, text verbosity, thinking, top_p, max tokens, plus the category's prompt_append)
3. **Environment context**: Unless disabled, an `<omo-env>` XML block is appended with date, time, timezone, locale
4. **User override**: Remaining override properties are deep-merged, and the override's prompt_append is appended

Note: Hephaestus applies category override and user override as separate steps, not as a combined operation like Sisyphus.

## Dynamic Inputs Summary

| Input | What It Influences |
|-------|--------------------|
| Available agents | Key triggers, tool selection, explore/librarian/oracle sections, delegation table — same as Sisyphus |
| Available tools | Tool selection table — same as Sisyphus |
| Available skills | Category+skills delegation guide — same as Sisyphus |
| Available categories | Category+skills delegation guide — same as Sisyphus |
| useTaskSystem flag | Todo discipline section — switches between task_create/task_update and todowrite terminology |
| Model string | Only affects the model field in the config. Does NOT change prompt content or config branching (always uses reasoningEffort: "medium"). |

## Conditional Logic

| Condition | Effect on Prompt |
|-----------|-----------------|
| **useTaskSystem is true** | Todo Discipline section uses task_create/task_update API language. |
| **useTaskSystem is false** | Todo Discipline section uses todowrite API language. |
| **Oracle agent available** | Oracle section included. Failure recovery references Oracle consultation. |
| **Oracle agent not available** | Oracle section omitted. Execution loop fallback ("consult Oracle") has no target. |
| **Explore/Librarian/other agents available or not** | Their respective sections are included or omitted — same behavior as Sisyphus. |
| **No categories and no skills** | Category+Skills Delegation Guide omitted. |
| **Environment injection disabled** | `<omo-env>` block not appended. |
| **Required provider not connected** | Hephaestus is not created at all. |
| **Agent is disabled** | Hephaestus is not created at all. |

## Key Differences from Sisyphus

| Aspect | Sisyphus | Hephaestus |
|--------|----------|------------|
| **Persona** | Orchestrator / Conductor | Autonomous Deep Worker |
| **maxTokens** | 64000 | 32000 |
| **Model config branching** | GPT: reasoningEffort "medium"; Claude: thinking enabled with 32000 budget | Always reasoningEffort "medium", regardless of model |
| **UI model selection** | Respected during resolution | Ignored — uses own fallback chain |
| **Availability gating** | Checks if any model in fallback chain is available | Checks if the required provider is connected |
| **Intent handling** | Classification-based: Trivial/Explicit/Exploratory/Open-ended/Ambiguous with equal weighting | Action-biased: "Default: message implies action unless explicitly stated otherwise" |
| **Asking behavior** | Can ask clarifying questions, has "Ambiguous" category that says "MUST ask" | "Do NOT Ask — Just Do" — asking is forbidden; LAST RESORT only after exhausting alternatives |
| **Completion model** | Phase 3 checklist (all todos done, diagnostics clean, build passes) | NON-NEGOTIABLE completion guarantee with 4-point turn-end self-check |
| **Progress updates** | "No Status Updates" — use todos for tracking | MANDATORY progress updates at meaningful milestones (before exploration, after discovery, etc.) |
| **Task management** | Detailed multi-section with clarification protocol template | Compact discipline section without clarification protocol |
| **Execution structure** | Phased (0→1→2A→2B→2C→3) with detailed sub-phases | 5-step loop (EXPLORE→PLAN→DECIDE→EXECUTE→VERIFY) with iteration |
| **Prompt structure** | XML-tagged sections (`<Role>`, `<Behavior_Instructions>`, etc.) | Flat template literal with markdown headings, no XML wrapper tags |
| **Default variant** | Only set if model resolution produces one | Always forced to resolved variant or "medium" |
