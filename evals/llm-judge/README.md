# LLM-as-Judge Evaluations

Uses Claude Sonnet to evaluate agent behavioral contracts against rubric-defined scoring dimensions. Supplements the deterministic trace analysis with nuanced, qualitative assessment.

## Quick Start

```bash
# Run all judges on traces from the last 7 days
./evals/llm-judge/run-judges.sh --days 7

# Dry run (no scores posted to Langfuse)
./evals/llm-judge/run-judges.sh --days 7 --dry-run
```

`run-judges.sh` runs three stages in order:

1. `session-signals.py` (no LLM, fast) — deterministic quality signals
2. `persona-trace-analyzer.py` (no LLM, fast) — rule-based persona scoring
3. `judge-persona.py` (LLM, slower) — rubric-based persona contract evaluation

## Judges

### judge-persona.py

Scores each persona's adherence to its behavioral contract across 6 dimensions (1-5 scale):

| Persona | Dimensions |
|---|---|
| Sisyphus | workflow_discipline, orchestration_quality, verification_completeness, task_completion, tool_usage_discipline, failure_handling |
| Hephaestus | execution_depth, verification_rigor, decision_quality, autonomy, tool_usage_discipline, failure_handling |
| Prometheus | planning_discipline, plan_quality, acceptance_criteria, scope_discipline, tool_usage_discipline, failure_handling |
| Atlas | boulder_state_adherence, task_advancement, verification_gate, bounded_execution, tool_usage_discipline, failure_handling |

```bash
# Single trace
uv run evals/llm-judge/judge-persona.py --trace-id TRACE_ID --persona sisyphus

# All recent traces
uv run evals/llm-judge/judge-persona.py --days 7

# Offline with frozen dataset
uv run evals/llm-judge/judge-persona.py --dataset evals/datasets/persona-examples/sisyphus-good.json
```

### judge-plan.py

Scores plans produced by prometheus/metis agents across 5 dimensions (1-5 scale): structure, task_granularity, verifiability, actionability, scope_discipline.

```bash
# Score a plan file directly
uv run evals/llm-judge/judge-plan.py --file .agent-kit/plans/my-plan.md

# Score from Langfuse trace
uv run evals/llm-judge/judge-plan.py --trace-id TRACE_ID

# Offline with reference plans
uv run evals/llm-judge/judge-plan.py --dataset evals/datasets/plan-examples/
```

### judge-search.py

Evaluates explore agent search quality. Computes automated boolean scores (`path_format`, `output_structure`, `parallel_execution`) plus an LLM-scored `completeness` dimension (1-5).

```bash
uv run evals/llm-judge/judge-search.py --trace-id TRACE_ID
```

### judge-oracle.py

Evaluates oracle agent architecture advice. Computes automated boolean scores (`effort_tag_present`, `verbosity_compliance`) plus an LLM-scored `recommendation_quality` dimension (1-5).

```bash
uv run evals/llm-judge/judge-oracle.py --trace-id TRACE_ID
```

## Rubrics

All rubrics live in `rubrics/`. They define the scoring criteria used by both human reviewers and LLM judges.

### Persona Rubrics

| Rubric | Evaluates |
|---|---|
| sisyphus.md | Orchestrator: exploration, planning, execution, verification sequence |
| hephaestus.md | Executor: execution depth, verification rigor, autonomy, decision quality |
| prometheus.md | Planner: planning discipline, plan quality, scope discipline, acceptance criteria |
| atlas.md | Coordinator: boulder adherence, task advancement, verification gates, bounded execution |
| universal.md | Cross-cutting dimensions applied to all personas: tool usage discipline, failure handling |

### Specialized Rubrics

| Rubric | Evaluates |
|---|---|
| plan-quality.md | Structure, granularity, verifiability, actionability, scope discipline |
| search-quality.md | Path format, output structure, parallel execution, completeness |
| oracle-quality.md | Effort tags, verbosity compliance, recommendation quality |
| metis-quality.md | Pre-planning agent output quality |
| momus-quality.md | Plan review agent feedback quality |

## Score Output

All scores are posted to Langfuse as trace-level scores with naming convention:

- `judge.{persona}.{dimension}` — LLM judge scores (1-5)
- `{persona}.{metric}` — automated trace analyzer scores (0/1 or numeric)
- `signal.{metric}` — session quality signals
- `explore.{metric}` — search quality scores
- `oracle.{metric}` — oracle quality scores

## Dependencies

Requires `uv` for Python dependency management. Dependencies from `pyproject.toml`:

- `langfuse>=2.0.0`
- `anthropic>=0.40.0`

Environment variables:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST` (optional)
- `ANTHROPIC_API_KEY`
