# Sisyphus Prompt Generation

## Overview

Sisyphus is the **primary orchestrator agent**. It acts as a senior engineer persona that parses implicit requirements, delegates specialized work to subagents, and coordinates parallel execution. It is the default agent users interact with — the conductor of all other agents.

Sisyphus's prompt is the largest and most dynamic in the system. It is assembled from 10+ shared section builders that inject content based on which agents, tools, skills, and categories are available at initialization time.

## Assembly Pipeline

Sisyphus's prompt is built through a multi-step pipeline that gathers runtime context, resolves the model, generates dynamic prompt sections, and applies post-processing.

### Step 1: Gather Runtime Context

Before Sisyphus's config is created, the system gathers several pieces of runtime context:

1. **Available models** are fetched from connected providers
2. **Category configs** are merged from built-in defaults and user configuration
3. **Available categories** are assembled as name+description pairs from the merged config
4. **Available skills** are assembled from built-in skills and user-discovered skills (filtered by disabled skills)
5. **Available agents** are collected by iterating over all other builtin agents (oracle, librarian, explore, multimodal-looker, metis, momus) — each agent that passes its own model/provider requirements contributes its name, description, and prompt metadata to this list
6. **Custom registered agents** are parsed from external agent summaries and appended to the available agents list

This gathered context is the foundation for all dynamic prompt content.

### Step 2: Gating and Model Resolution

Before the prompt is built, the system checks whether Sisyphus should be created at all:

1. **Disabled check**: If Sisyphus is in the disabled agents list, it is skipped entirely
2. **Model availability check**: The system verifies that at least one model from Sisyphus's fallback chain is available — unless there is an explicit user override or it is a first-run-no-cache scenario
3. **Model resolution**: A pipeline resolves the final model by checking (in priority order):
   - The user's UI-selected model (Sisyphus is a "primary" mode agent, so it respects UI selection)
   - A user-configured override model
   - The fallback chain from agent model requirements
   - The system default model
4. On first-run-no-cache with no explicit selection, the first model in the fallback chain is used directly

### Step 3: Build Dynamic Prompt Sections

The prompt is assembled by calling 10 shared section builders and 1 local builder. Each builder takes some subset of the runtime context (available agents, tools, skills, categories) and produces a string of prompt content. If the relevant data is absent or empty, the builder returns an empty string and that section is omitted from the final prompt.

#### Dynamic Section Builders

| Section | Inputs | What It Produces |
|---------|--------|------------------|
| **Key Triggers** | agents, skills | Bullet list of key trigger rules extracted from each agent's metadata (e.g., "External library mentioned -> fire librarian"). Agents without a key trigger are skipped. A hardcoded trigger for "look into + create PR" is always appended. |
| **Tool Selection Table** | agents, tools, skills | A cost-sorted table. Tools (grep, glob, lsp, ast, etc.) are listed as FREE. Agents are sorted by cost (FREE, CHEAP, EXPENSIVE) with their first-sentence description. Utility-category agents are excluded. Ends with a default-flow recommendation. |
| **Explore Section** | agents | Guidance for the explore agent: "Use Direct Tools when" (from the explore agent's `avoidWhen` metadata) and "Use Explore Agent when" (from `useWhen` metadata). Only appears if an explore agent exists. |
| **Librarian Section** | agents | Guidance for the librarian agent: distinguishes "Contextual Grep (Internal)" from "Reference Grep (External)". Lists trigger phrases from the librarian's `useWhen` metadata. Only appears if a librarian agent exists. |
| **Category + Skills Delegation Guide** | categories, skills | A comprehensive delegation guide. Lists all available categories with descriptions. Lists skills split into built-in and user-installed, with user-installed skills marked as priority. Includes a mandatory 2-step selection protocol (select category, then evaluate all skills) and a delegation pattern with code example. Only appears if categories or skills exist. |
| **Delegation Table** | agents | A domain-to-agent routing table. For each agent, lists every delegation trigger from its metadata (domain name + trigger description). |
| **Oracle Section** | agents | A detailed guide for Oracle consultation: when to consult (from `useWhen`), when not to (from `avoidWhen`), usage pattern (announce before invocation), and a strict background task policy (must collect results before final answer, never cancel Oracle). Only appears if an oracle agent exists. Wrapped in `<Oracle_Usage>` tags. |
| **Hard Blocks** | (none — static) | A fixed list of "NEVER violate" rules: no type error suppression, no commits without request, no speculation about unread code, no broken state, no cancelling Oracle, no delivering answers before collecting Oracle results. |
| **Anti-Patterns** | (none — static) | A fixed list of blocking anti-patterns: type safety violations, empty catch blocks, deleting failing tests, firing agents for trivial issues, shotgun debugging, bulk background cancellation, skipping Oracle results. |
| **Task Management** | useTaskSystem flag | A full task/todo management section. **Varies based on the useTaskSystem flag** — see Conditional Logic below. |

### Step 4: Compose the Final Prompt

The sections produced by the builders are composed into a single prompt string using a template literal. The prompt is structured with XML-style tags and follows this order:

```
<Role>
  Identity: "Sisyphus" - Powerful AI Agent with orchestration capabilities
  Persona: SF Bay Area engineer — work, delegate, verify, ship
  Core Competencies: parsing implicit requirements, adapting to codebase maturity,
    delegating to subagents, parallel execution, following user instructions
  Operating Mode: never works alone when specialists are available

<Behavior_Instructions>
  Phase 0 - Intent Gate (EVERY message):
    [Key Triggers section — dynamic]
    <intent_verbalization>
      Step 0: Verbalize Intent — a table mapping surface forms ("explain X", "implement X",
        "look into X", "what do you think about X?", "I'm seeing error X", "refactor")
        to true intents and routing decisions
    Step 1: Classify Request Type — Trivial / Explicit / Exploratory / Open-ended / Ambiguous
    Step 2: Check for Ambiguity — single interpretation vs multiple, effort difference threshold
    Step 3: Validate Before Acting — assumptions check, delegation check (3-step: specialized agent?
      category+skills? can I do it myself?)

  Phase 1 - Codebase Assessment (for open-ended tasks):
    Quick Assessment: check configs, sample files, note project age
    State Classification: Disciplined / Transitional / Legacy-Chaotic / Greenfield

  Phase 2A - Exploration & Research:
    [Tool Selection Table — dynamic]
    [Explore Section — dynamic]
    [Librarian Section — dynamic]
    Parallel Execution rules: parallelize everything, explore/librarian always background,
      fire 2-5 agents in parallel, detailed prompt structure template
      ([CONTEXT] + [GOAL] + [DOWNSTREAM] + [REQUEST])
    Background Result Collection: launch → continue → collect → cancel disposable individually
    Search Stop Conditions: enough context, same info repeating, 2 fruitless iterations

  Phase 2B - Implementation:
    Pre-Implementation: find skills, create todo list, mark in_progress/completed
    [Category + Skills Delegation Guide — dynamic]
    [Delegation Table — dynamic]
    Delegation Prompt Structure: mandatory 6 sections
      (TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, CONTEXT)
    Post-delegation verification checklist
    Session Continuity: reuse session_id for follow-ups, failures, verification failures
    Code Changes: match patterns, propose for chaotic codebases, never suppress types
    Verification: lsp_diagnostics on changed files, build commands, test runs
    Evidence Requirements: file edit → diagnostics clean, build → exit 0, tests → pass

  Phase 2C - Failure Recovery:
    Fix root causes, re-verify after every fix
    After 3 consecutive failures: STOP, REVERT, DOCUMENT, CONSULT Oracle, ASK USER

  Phase 3 - Completion:
    Checklist: all todos done, diagnostics clean, build passes, request addressed
    Before final answer: cancel disposable tasks individually, always wait for Oracle

[Oracle Section — dynamic, wrapped in <Oracle_Usage> tags]

[Task Management Section — dynamic, wrapped in <Task_Management> tags]

<Tone_and_Style>
  Be Concise: start immediately, no acknowledgments, no summaries unless asked
  No Flattery: never praise user input
  No Status Updates: no casual acknowledgments — use todos for tracking
  When User is Wrong: state concern and alternative concisely
  Match User's Style: terse if they're terse, detailed if they want detail

<Constraints>
  [Hard Blocks — static]
  [Anti-Patterns — static]
  Soft Guidelines: prefer existing libraries, prefer small changes, ask when uncertain
```

### Step 5: Build Agent Config

The prompt string is placed into an agent config with these properties:

| Property | Value |
|----------|-------|
| description | Static orchestrator description |
| mode | `"primary"` (respects user's UI model selection) |
| model | Resolved model string |
| maxTokens | 64000 |
| color | `#00CED1` (DarkTurquoise) |
| permission | question: allow, call_omo_agent: deny |
| **GPT models** | adds `reasoningEffort: "medium"` |
| **Claude models** | adds `thinking: { type: "enabled", budgetTokens: 32000 }` |

### Step 6: Post-Processing

After the base config is built, three post-processing steps are applied:

1. **Variant**: If the model resolution produced a variant, it is set on the config
2. **User overrides**: Applied in two layers:
   - If the override specifies a **category**, the category's config is applied first (model, variant, temperature, reasoning effort, text verbosity, thinking config, top_p, max tokens, and the category's `prompt_append` is appended to the prompt)
   - Then the override's own properties are deep-merged, and the override's `prompt_append` is appended
3. **Environment context**: Unless environment injection is disabled, an `<omo-env>` XML block is appended to the end of the prompt containing current date, current time, timezone, and locale

## Dynamic Inputs Summary

| Input | What It Influences |
|-------|--------------------|
| Available agents (list of name + description + metadata) | Key triggers section, tool selection table, explore section, librarian section, oracle section, delegation table — each section is only present if the relevant agent exists |
| Available tools (list of tool names categorized as lsp/ast/search/session/command) | Tool selection table — lists tools as FREE cost tier |
| Available skills (list of name + description + location: plugin/user/project) | Category+skills delegation guide — split into built-in and user-installed, with user-installed getting priority treatment |
| Available categories (list of name + description) | Category+skills delegation guide — listed with descriptions, used in the mandatory selection protocol |
| useTaskSystem flag (boolean) | Task management section — switches between TaskCreate/TaskUpdate API and todowrite API |
| Model string | Agent config: GPT models get reasoningEffort, Claude models get thinking budget. Does NOT affect prompt content. |

## Conditional Logic

| Condition | Effect on Prompt |
|-----------|-----------------|
| **Model is GPT** | Agent config gets `reasoningEffort: "medium"` instead of `thinking: { type: "enabled", budgetTokens: 32000 }`. The prompt text itself does not change. |
| **useTaskSystem is true** | The Task Management section uses TaskCreate/TaskUpdate API language. The todo hook note references "TASK CONTINUATION". Section header says "Task Management (CRITICAL)" and workflow uses task-specific terminology. |
| **useTaskSystem is false** | The Task Management section uses todowrite API language. The todo hook note references "TODO CONTINUATION". Section header says "Todo Management (CRITICAL)" and workflow uses todo-specific terminology. |
| **Oracle agent is available** | The `<Oracle_Usage>` section is included with when-to/when-not-to rules, usage pattern, and background task policy. Oracle-related hard blocks and anti-patterns reference a real agent. |
| **Oracle agent is not available** | The Oracle section is omitted entirely (empty string). Hard blocks and anti-patterns still reference Oracle but the guidance has no target agent. |
| **Explore agent is available** | The Explore section is included with use-when/avoid-when guidance from explore agent metadata. |
| **Explore agent is not available** | The Explore section is omitted entirely. |
| **Librarian agent is available** | The Librarian section is included with trigger phrases from librarian metadata. |
| **Librarian agent is not available** | The Librarian section is omitted entirely. |
| **No categories and no skills** | The Category + Skills Delegation Guide is omitted entirely. |
| **Skills include user-installed skills** | The delegation guide adds a priority notice: "User-installed skills OVERRIDE built-in defaults. ALWAYS prefer YOUR SKILLS when domain matches." |
| **No agents have delegation triggers** | The Delegation Table contains no rows (just the header). |
| **No agents have key triggers** | The Key Triggers section is omitted entirely. |
| **Environment injection disabled** | The `<omo-env>` block is not appended to the prompt. |
| **Agent is disabled** | Sisyphus config is not created at all. |
| **No model available in fallback chain** | Sisyphus config is not created at all (unless override or first-run-no-cache). |
