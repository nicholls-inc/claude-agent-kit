# Rubrics

Scoring criteria for LLM-as-judge evaluations. Each rubric defines dimensions, scoring scales (1-5), and concrete examples for each level. Loaded at evaluation time by the judge scripts.

## Persona Rubrics

Define behavioral contracts that each persona must follow. Used by `judge-persona.py`.

- **sisyphus.md** — Orchestrator contract: explore-before-edit workflow, parallel exploration via Task tool, verification after edits, proper delegation
- **hephaestus.md** — Executor contract: deep execution with multiple edit passes, multi-type verification (test + typecheck + build + lint), retry on failure, autonomous decision-making
- **prometheus.md** — Planner contract: plan-only output (no code edits), markdown checklist format, artifacts under `.agent-kit/`, scoped acceptance criteria
- **atlas.md** — Coordinator contract: boulder.json state management, single-task-at-a-time advancement, verification gates before marking done, bounded execution (<=100 tool calls)
- **universal.md** — Cross-cutting dimensions applied to all personas: tool usage discipline (right tool for the job, no waste) and failure handling (diagnose, recover, escalate)

## Specialized Rubrics

Define quality criteria for specific agent outputs. Used by the corresponding judge scripts.

- **plan-quality.md** — Used by `judge-plan.py`. Dimensions: structure (Context/Tasks/Verification sections), task granularity (3-10 well-scoped tasks), verifiability (runnable verification commands), actionability (references specific files/patterns), scope discipline (tightly scoped, explicit exclusions)
- **search-quality.md** — Used by `judge-search.py`. Evaluates: absolute path format, structured output (Result/Files/Answer sections), parallel tool execution, search completeness
- **oracle-quality.md** — Used by `judge-oracle.py`. Evaluates: effort tag presence (Quick/Short/Medium/Large), verbosity compliance (bottom line <=3 sentences, steps <=7), recommendation quality
- **metis-quality.md** — Pre-planning agent: question quality, coverage of ambiguities, context gathering thoroughness
- **momus-quality.md** — Plan review agent: critique specificity, actionable feedback, scope discipline enforcement

## Scoring Scale

All persona and plan rubrics use a 1-5 scale:

| Score | Meaning |
|---|---|
| 1 | Critical failure — contract violated or output unusable |
| 2 | Below expectations — minimal adherence, significant gaps |
| 3 | Acceptable — meets basic requirements with some issues |
| 4 | Good — minor issues, generally strong adherence |
| 5 | Excellent — full contract adherence, no issues |
