#!/usr/bin/env python3
"""judge-plan.py — LLM-as-judge for plan quality.

Evaluates plans produced by prometheus/metis agents using Claude Sonnet.
Scores: structure, task_granularity, verifiability, actionability, scope_discipline.

Usage:
  uv run evals/llm-judge/judge-plan.py --file .agent-kit/plans/my-plan.md
  uv run evals/llm-judge/judge-plan.py --trace-id TRACE_ID
  uv run evals/llm-judge/judge-plan.py --dataset evals/datasets/plan-examples/
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/llm-judge/judge-plan.py", file=sys.stderr)
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package required. Run via: uv run evals/llm-judge/judge-plan.py", file=sys.stderr)
    sys.exit(1)


RUBRIC_PATH = Path(__file__).parent / "rubrics" / "plan-quality.md"

DIMENSIONS = [
    "structure",
    "task_granularity",
    "verifiability",
    "actionability",
    "scope_discipline",
]


def load_rubric() -> str:
    return RUBRIC_PATH.read_text()


def judge_plan(client: anthropic.Anthropic, plan_content: str, context: str = "") -> dict:
    """Evaluate a plan using LLM-as-judge."""
    rubric = load_rubric()

    prompt = f"""You are an expert evaluator for implementation plans produced by AI planning agents.

## Rubric

{rubric}

## Plan Content

{plan_content}

{f"## Additional Context{chr(10)}{context}" if context else ""}

## Instructions

Score each dimension from 1-5 based on the rubric. Return your evaluation as JSON:

```json
{{
  "scores": {{
{chr(10).join(f'    "{d}": <1-5>,' for d in DIMENSIONS)}
  }},
  "reasoning": {{
{chr(10).join(f'    "{d}": "<brief explanation>",' for d in DIMENSIONS)}
  }},
  "overall_score": <1-5 average>,
  "summary": "<2-3 sentence assessment>"
}}
```

Return ONLY the JSON object."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)
    else:
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"scores": {}, "reasoning": {}, "overall_score": 0, "summary": "Parse error"}


def print_result(result: dict, label: str = ""):
    if label:
        print(f"\n{label}")
    print(f"  Overall: {result.get('overall_score', 'N/A')}/5")
    print(f"  Summary: {result.get('summary', 'N/A')}")
    for dim, score in result.get("scores", {}).items():
        reasoning = result.get("reasoning", {}).get(dim, "")
        print(f"  {dim}: {score}/5 — {reasoning}")


def main():
    parser = argparse.ArgumentParser(description="LLM-as-judge plan quality evaluation")
    parser.add_argument("--file", help="Path to a plan .md file")
    parser.add_argument("--trace-id", help="Evaluate plan from a Langfuse trace")
    parser.add_argument("--dataset", help="Directory of plan files to evaluate")
    parser.add_argument("--dry-run", action="store_true", help="Print without posting")
    args = parser.parse_args()

    client = anthropic.Anthropic()
    langfuse = Langfuse()

    if args.file:
        plan_content = Path(args.file).read_text()
        result = judge_plan(client, plan_content)
        print_result(result, f"Plan: {args.file}")

    elif args.dataset:
        dataset_dir = Path(args.dataset)
        for plan_file in sorted(dataset_dir.glob("*.md")):
            plan_content = plan_file.read_text()
            result = judge_plan(client, plan_content)
            print_result(result, f"Plan: {plan_file.name}")

    elif args.trace_id:
        trace = langfuse.get_trace(args.trace_id)
        observations = trace.observations if hasattr(trace, "observations") else []

        plan_content = None
        for obs in observations:
            if getattr(obs, "type", "") == "SPAN" and getattr(obs, "name", "") == "Write":
                inp = str(getattr(obs, "input", ""))
                if ".agent-kit/" in inp and inp.endswith(".md"):
                    plan_content = str(getattr(obs, "output", ""))
                    break

        if not plan_content:
            print("No plan artifact found in trace.", file=sys.stderr)
            sys.exit(1)

        result = judge_plan(client, plan_content)
        print_result(result, f"Trace: {args.trace_id}")

        if not args.dry_run:
            for dim, score in result.get("scores", {}).items():
                langfuse.score(
                    trace_id=args.trace_id,
                    name=f"plan_quality.{dim}",
                    value=score,
                    comment=result.get("reasoning", {}).get(dim, ""),
                )
            print("\nScores posted to Langfuse.")

    langfuse.flush()


if __name__ == "__main__":
    main()
