# Plan Examples

Reference plans for calibrating and validating `judge-plan.py`. Span the full quality range from poor to excellent.

## Files

| File | Expected Score | Description |
|---|---|---|
| excellent-plan.md | 5/5 | CSV export feature — clear Context/Tasks/Verification sections, 5 well-scoped tasks with file paths, runnable verification commands, explicit exclusions |
| good-plan.md | 4/5 | Rate limiting feature — solid structure, reasonable granularity, minor gaps in verification specificity |
| mediocre-plan.md | 3/5 | Basic structure present but tasks are vague, missing concrete file references, weak verification |
| poor-plan.md | 1-2/5 | Stream-of-consciousness format, no sections, no checklist, no verification |
| scope-creep-plan.md | 2/5 | Well-structured but massively over-scoped beyond the original request |

## Usage

```bash
# Score all reference plans
uv run evals/llm-judge/judge-plan.py --dataset evals/datasets/plan-examples/

# Score a single plan
uv run evals/llm-judge/judge-plan.py --file evals/datasets/plan-examples/excellent-plan.md
```

## Scoring Dimensions

Plans are evaluated on 5 dimensions (see `llm-judge/rubrics/plan-quality.md`):

1. **Structure** — Has Context/Tasks/Verification sections, checklist format
2. **Task Granularity** — 3-10 well-scoped, independently completable tasks
3. **Verifiability** — Concrete, runnable verification commands
4. **Actionability** — References specific files, patterns, and existing code
5. **Scope Discipline** — Tightly scoped to the request, explicit exclusions
