# Atlas Prompt Generation

## Overview

Atlas is the **master orchestrator** agent. Named after the Titan who holds up the celestial heavens, Atlas holds up the entire workflow — coordinating every agent, every task, every verification until completion. Unlike Sisyphus (which does work and delegates), Atlas **never writes code itself**. It is purely a conductor: it delegates all implementation via task(), verifies results, and manages a notepad system for cumulative intelligence across stateless subagent sessions.

Atlas uses a **template-with-placeholders** approach rather than the section-builder-composition approach used by Sisyphus and Hephaestus. A large static prompt template contains placeholder markers that are replaced at runtime with dynamically generated sections. Atlas also has **separate templates for GPT and Claude models**, selected based on whether the resolved model is a GPT-family model.

## Assembly Pipeline

### Step 1: Gather Runtime Context

Atlas is created after Sisyphus, Hephaestus, and all general agents. It receives:
- **Available agents**: The same list built for Sisyphus/Hephaestus
- **Available skills**: The same skill list
- **User categories**: The user's category configuration (not just the merged version)
- **Model**: The resolved model string

### Step 2: Gating and Model Resolution

1. **Disabled check**: If Atlas is in the disabled agents list, it is skipped
2. **Model resolution**: A pipeline resolves the final model. Atlas is a "primary" mode agent, so it respects the user's UI-selected model.
3. If no model can be resolved, Atlas is not created

### Step 3: Select Base Template (GPT vs Claude)

Based on whether the resolved model is a GPT-family model (detected by checking for `gpt-`, `gpt4`, `o1`, `o3`, `o4` prefixes, or `openai/`/`github-copilot/gpt-` provider prefixes), one of two base templates is selected:
- **Claude template** (default): Narrative style, extended reasoning, detailed workflow sections
- **GPT template**: Compact, XML-tagged, follows GPT-5.2 Prompting Guide principles

Both templates contain the same 5 placeholder markers at the same positions.

### Step 4: Build Dynamic Sections and Replace Placeholders

Five section builders generate dynamic content, and the results are substituted into the selected template via string replacement:

| Placeholder | What Is Generated |
|-------------|-------------------|
| **Category Section** | A list of all available categories with their temperature values and descriptions. Each category is shown as spawning a "Sisyphus-Junior-{category}" with optimized settings. Includes a task() usage pattern example. Built from the merged category config (built-in defaults + user overrides). |
| **Agent Selection Section** | A list of available agents with truncated descriptions (first sentence only). If no agents are available, shows "No agents available." |
| **Decision Matrix** | A combined routing guide mapping categories to task() commands and agents to task() commands. Ends with a mutual exclusivity rule: "NEVER provide both category AND agent." |
| **Skills Section** | Skill selection guidance showing counts of built-in and user-installed skills. Includes mandatory evaluation rules: for every skill, ask "Does this skill's domain overlap with my task?" If no skills exist, this section is empty. |
| **Category + Skills Delegation Guide** | The same shared delegation guide used by Sisyphus and Hephaestus — full category list, skill priority rules, and the mandatory 2-step selection protocol. |

### Step 5: Template Structures

#### Claude Template Structure

```
<identity>
  Atlas - Master Orchestrator
  "Conductor, not musician. General, not soldier."
  Delegates, coordinates, and verifies. Never writes code.

<mission>
  Complete ALL tasks in a work plan via task() until fully done.
  One task per delegation. Parallel when independent. Verify everything.

<delegation_system>
  How to delegate: task() with EITHER category OR agent (mutually exclusive)
  [Category Section — dynamic]
  [Agent Selection Section — dynamic]
  [Decision Matrix — dynamic]
  [Skills Section — dynamic]
  [Category + Skills Delegation Guide — dynamic]
  6-Section Prompt Structure (MANDATORY for every delegation):
    1. TASK — quote exact checkbox item
    2. EXPECTED OUTCOME — files, functionality, verification command
    3. REQUIRED TOOLS — tool whitelist
    4. MUST DO — exhaustive requirements, pattern references
    5. MUST NOT DO — scope limits, forbidden actions
    6. CONTEXT — notepad paths, inherited wisdom, dependencies
  Minimum 30 lines per delegation prompt.

<workflow>
  Step 0: Register Tracking — create a tracking todo
  Step 1: Analyze Plan — read todo file, parse checkboxes, build parallelization map
  Step 2: Initialize Notepad — create .sisyphus/notepads/{plan-name}/ with
    learnings.md, decisions.md, issues.md, problems.md
  Step 3: Execute Tasks
    3.1 Parallelization Check — parallel tasks → multiple task() in one message
    3.2 Pre-Delegation — read notepad files, extract wisdom, include in prompt
    3.3 Invoke task()
    3.4 Verify (MANDATORY after every delegation):
      A. Automated: lsp_diagnostics → build → tests
      B. Manual Code Review (NON-NEGOTIABLE): Read every changed file line by line,
        check logic, stubs, patterns, imports; cross-reference claims vs actual code
      C. Hands-On QA: browser for frontend, interactive_bash for CLI, curl for API
      D. Check Boulder State: Read plan file directly, count remaining tasks
    3.5 Handle Failures — always use session_id for retries, max 3 attempts
    3.6 Loop Until Done
  Step 4: Final Report — completed/failed counts, files modified, accumulated wisdom

<parallel_execution>
  Exploration (explore/librarian): ALWAYS background
  Task execution: NEVER background
  Parallel task groups: invoke multiple in ONE message
  Cancel disposable tasks individually, NEVER cancel all at once

<notepad_protocol>
  Purpose: cumulative intelligence for stateless subagents
  Before every delegation: read notepad, extract wisdom, include as "Inherited Wisdom"
  After every completion: instruct subagent to append findings (never overwrite)

<verification_rules>
  "You are the QA gate. Subagents lie. Verify EVERYTHING."
  After each delegation: both automated AND manual verification mandatory
  Evidence required: diagnostics clean, build passes, tests pass, logic correct, boulder state checked

<boundaries>
  YOU DO: read files, run commands, use diagnostics/grep/glob, manage todos, coordinate, verify
  YOU DELEGATE: all code writing/editing, bug fixes, test creation, documentation, git operations

<critical_overrides>
  NEVER: write code yourself, trust subagent claims, background task execution,
    short prompts (<30 lines), skip diagnostics, batch multiple tasks, start fresh on failures
  ALWAYS: 6-section prompts, read notepad first, project-level QA, pass inherited wisdom,
    parallelize independent tasks, verify with own tools, store and reuse session_id
```

#### GPT Template Structure

The GPT template covers the same content but is restructured following GPT-5.2 Prompting Guide principles. Key differences from the Claude template:

```
<identity>                         — Same, more compact
<mission>                          — Same
<output_verbosity_spec>            — GPT-ONLY: explicit verbosity constraints
                                     (2-4 sentences for updates, ≤5 bullets for analysis,
                                     avoid long paragraphs, don't rephrase unless semantics change)
<scope_and_design_constraints>     — GPT-ONLY: implement ONLY what plan specifies,
                                     no extra features, no scope creep, simplest interpretation
<uncertainty_and_ambiguity>        — GPT-ONLY: ask 1-3 precise questions OR state interpretation,
                                     never fabricate, prefer "Based on the plan...",
                                     default to sequential when unsure about parallelization
<tool_usage_rules>                 — GPT-ONLY: always use tools over internal knowledge,
                                     parallelize independent calls, verify after every delegation
<delegation_system>                — Same 5 dynamic placeholders + 6-section prompt
<workflow>                         — Same Steps 0-4 but more compact; Step 3.4 Verify is
                                     restructured as 4-Phase Critical QA:
                                     Phase 1: READ CODE FIRST (before running anything)
                                       — git diff, read every changed file, critically evaluate
                                     Phase 2: AUTOMATED VERIFICATION (targeted then broad)
                                       — per-file diagnostics, then targeted tests, then full suite
                                     Phase 3: HANDS-ON QA (mandatory for user-facing changes)
                                       — actually run/open/interact with deliverable
                                     Phase 4: GATE DECISION (3 YES/NO questions)
                                       — "Can I explain every line? Did I see it work?
                                       Am I confident nothing broke?" ALL must be YES.
<parallel_execution>               — Same rules, more compact
<notepad_protocol>                 — Same, more compact
<verification_rules>               — Enhanced emphasis: "Subagents ROUTINELY LIE about completion"
                                     — they claim done when code has syntax errors, stubs, wrong logic;
                                     "Assume every claim is false until YOU personally verify it"
                                     — 4-phase protocol reference, phase 3 NOT optional
<boundaries>                       — Same
<critical_rules>                   — Same NEVER/ALWAYS rules
<user_updates_spec>                — GPT-ONLY: brief updates (1-2 sentences) only at major phases
                                     or plan-changing discoveries; concrete outcomes only;
                                     don't expand scope
```

### Step 6: Build Agent Config

| Property | Value |
|----------|-------|
| description | Static orchestrator description |
| mode | `"primary"` |
| model | Resolved model (if provided) |
| temperature | 0.1 (low for deterministic orchestration) |
| color | `#10B981` (Emerald) |
| Tool restrictions | Only task and call_omo_agent tools are allowed |

### Step 7: Post-Processing

After the base config is built:

1. **Variant**: Set from model resolution if present
2. **User overrides**: Category override applied first (if specified), then direct overrides deep-merged, then prompt_append appended

**Not applied**: Environment context — Atlas does not receive the `<omo-env>` injection.

## Dynamic Inputs Summary

| Input | What It Influences |
|-------|--------------------|
| Available agents | Agent Selection Section content, Decision Matrix agent rows |
| Available skills | Skills Section content, Category+Skills Delegation Guide |
| User categories | Category Section content, Decision Matrix category rows, Category+Skills Delegation Guide |
| Model | Template selection: GPT vs Claude base template |

## Conditional Logic

| Condition | Effect on Prompt |
|-----------|-----------------|
| **Model is GPT-family** | GPT template selected — adds output_verbosity_spec, scope_and_design_constraints, uncertainty_and_ambiguity, tool_usage_rules, user_updates_spec sections. Verification restructured as 4-Phase Critical QA with explicit gate decision. |
| **Model is not GPT-family** | Claude template selected — narrative style, extended reasoning, verification as 4-step checklist. |
| **No agents available** | Agent Selection Section shows "No agents available." Decision Matrix has no agent rows. |
| **No skills available** | Skills Section is empty. |
| **No categories defined** | Only built-in default categories appear in Category Section. |
| **User has custom categories** | Custom categories appear alongside built-in defaults in Category Section and Decision Matrix with user-provided descriptions. |
| **Agent is disabled** | Atlas is not created at all. |
| **No model resolved** | Atlas is not created at all. |

## GPT vs Claude Differences

| Aspect | Claude Template | GPT Template |
|--------|----------------|--------------|
| **Style** | Narrative, extended reasoning sections | Compact, XML-tagged, principle-driven |
| **Extra sections** | None | output_verbosity_spec, scope_and_design_constraints, uncertainty_and_ambiguity, tool_usage_rules, user_updates_spec |
| **Verification** | 4-step checklist: Automated + Manual Code Review + Hands-On QA + Boulder State | 4-Phase Critical QA with Phase 1 "read before running" and Phase 4 gate decision (3 YES/NO questions) |
| **Subagent trust** | "Subagents lie. Verify EVERYTHING." | "Subagents ROUTINELY LIE about completion" — explicitly lists what they lie about (syntax errors, stubs, wrong logic, scope creep) |
| **Scope discipline** | Implicit in workflow instructions | Explicit section: "implement ONLY what the plan specifies, no extra features" |
| **Verbosity control** | Implicit | Explicit constraints: "2-4 sentences for updates", "avoid long paragraphs", "prefer bullets and tables" |
| **Uncertainty handling** | Implicit in workflow | Explicit: "ask 1-3 precise questions", "never fabricate", "default to sequential when unsure" |
| **Design philosophy** | Optimized for Claude's tendency to be "helpful" — forces explicit delegation | Follows GPT-5.2 Prompting Guide: explicit verbosity, scope discipline, tool preference, grounding bias |
