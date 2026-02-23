#!/usr/bin/env python3
"""judge-persona.py — LLM-as-judge for persona behavioral contracts.

Evaluates all four persona behavioral contracts using Claude Sonnet.
For each trace:
  1. Extracts conversation text + tool call sequence
  2. Loads the persona-specific rubric from rubrics/
  3. Sends to Claude Sonnet for scoring
  4. Posts scores back to Langfuse

Usage:
  uv run evals/llm-judge/judge-persona.py --trace-id TRACE_ID --persona sisyphus
  uv run evals/llm-judge/judge-persona.py --days 7
  uv run evals/llm-judge/judge-persona.py --dataset evals/datasets/persona-examples/sisyphus-good.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/llm-judge/judge-persona.py", file=sys.stderr)
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package required. Run via: uv run evals/llm-judge/judge-persona.py", file=sys.stderr)
    sys.exit(1)


RUBRICS_DIR = Path(__file__).parent / "rubrics"
VALID_PERSONAS = {"sisyphus", "hephaestus", "prometheus", "atlas"}

# Dimension names per persona (matching rubric headers)
PERSONA_DIMENSIONS = {
    "sisyphus": [
        "workflow_discipline",
        "orchestration_quality",
        "verification_completeness",
        "task_completion",
        "tool_usage_discipline",
        "failure_handling",
    ],
    "hephaestus": [
        "execution_depth",
        "verification_rigor",
        "decision_quality",
        "autonomy",
        "tool_usage_discipline",
        "failure_handling",
    ],
    "prometheus": [
        "planning_discipline",
        "plan_quality",
        "acceptance_criteria",
        "scope_discipline",
        "tool_usage_discipline",
        "failure_handling",
    ],
    "atlas": [
        "boulder_state_adherence",
        "task_advancement",
        "verification_gate",
        "bounded_execution",
        "tool_usage_discipline",
        "failure_handling",
    ],
}


def load_rubric(persona: str) -> str:
    """Load rubric markdown for a persona."""
    rubric_path = RUBRICS_DIR / f"{persona}.md"
    universal_path = RUBRICS_DIR / "universal.md"

    rubric = rubric_path.read_text()
    if universal_path.exists():
        universal = universal_path.read_text()
        rubric = f"{rubric}\n\n---\n\n{universal}"

    return rubric


def extract_trace_context(trace) -> str:
    """Extract conversation and tool calls as a formatted string for the judge."""
    observations = trace.observations if hasattr(trace, "observations") else []
    sorted_obs = sorted(observations, key=lambda o: getattr(o, "start_time", "") or "")

    parts = []
    for obs in sorted_obs:
        obs_type = getattr(obs, "type", "")
        name = getattr(obs, "name", "")

        if obs_type == "GENERATION":
            inp = getattr(obs, "input", "")
            out = getattr(obs, "output", "")
            if inp:
                parts.append(f"[USER INPUT]\n{_truncate(str(inp), 1000)}")
            if out:
                parts.append(f"[ASSISTANT OUTPUT]\n{_truncate(str(out), 2000)}")

        elif obs_type == "SPAN":
            inp = getattr(obs, "input", "")
            out = getattr(obs, "output", "")
            level = getattr(obs, "level", "")
            status = f" [{level}]" if level else ""
            parts.append(
                f"[TOOL: {name}]{status}\n"
                f"  Input: {_truncate(str(inp), 500)}\n"
                f"  Output: {_truncate(str(out), 500)}"
            )

    return "\n\n".join(parts)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... [truncated, {len(text)} total chars]"


def judge_trace(
    client: anthropic.Anthropic,
    trace_context: str,
    persona: str,
) -> dict:
    """Run LLM-as-judge evaluation on a trace."""
    rubric = load_rubric(persona)
    dimensions = PERSONA_DIMENSIONS[persona]

    prompt = f"""You are an expert evaluator for AI agent sessions. You will evaluate a session trace
against a specific persona behavioral contract.

## Rubric

{rubric}

## Session Trace

{trace_context}

## Instructions

Score each dimension from 1-5 based on the rubric above. Return your evaluation as JSON with this exact structure:

```json
{{
  "scores": {{
{chr(10).join(f'    "{d}": <1-5>,' for d in dimensions)}
  }},
  "reasoning": {{
{chr(10).join(f'    "{d}": "<brief explanation>",' for d in dimensions)}
  }},
  "overall_score": <1-5 average>,
  "summary": "<2-3 sentence overall assessment>"
}}
```

Return ONLY the JSON object, no other text."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse response
    response_text = response.content[0].text
    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(1)
    else:
        # Try to find raw JSON
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        print(f"  WARNING: Failed to parse judge response as JSON", file=sys.stderr)
        result = {"scores": {}, "reasoning": {}, "overall_score": 0, "summary": "Parse error"}

    return result


def post_judge_scores(langfuse: "Langfuse", trace_id: str, persona: str, result: dict):
    """Post LLM-judge scores to Langfuse."""
    scores = result.get("scores", {})
    for dimension, score in scores.items():
        langfuse.score(
            trace_id=trace_id,
            name=f"judge.{persona}.{dimension}",
            value=score,
            comment=result.get("reasoning", {}).get(dimension, ""),
        )

    overall = result.get("overall_score", 0)
    if overall:
        langfuse.score(
            trace_id=trace_id,
            name=f"judge.{persona}.overall",
            value=overall,
            comment=result.get("summary", ""),
        )


def get_trace_persona(trace) -> str:
    """Extract persona from trace metadata."""
    metadata = getattr(trace, "metadata", {}) or {}
    return metadata.get("persona", metadata.get("hook.persona", "unknown"))


def main():
    parser = argparse.ArgumentParser(description="LLM-as-judge persona evaluation")
    parser.add_argument("--trace-id", help="Evaluate a specific trace")
    parser.add_argument("--persona", help="Override persona detection")
    parser.add_argument("--days", type=int, default=7, help="Process traces from last N days")
    parser.add_argument("--dry-run", action="store_true", help="Print results without posting")
    parser.add_argument("--dataset", help="Path to JSON dataset for offline evaluation")
    args = parser.parse_args()

    langfuse = Langfuse()
    client = anthropic.Anthropic()

    if args.dataset:
        with open(args.dataset) as f:
            dataset = json.load(f)

        class FakeTrace:
            def __init__(self, data):
                self.id = data.get("trace_id", "offline")
                self.observations = []
                self.metadata = data.get("metadata", {})
                for tc in data.get("tool_calls", []):
                    obs = type("Obs", (), {
                        "type": "SPAN",
                        "name": tc.get("name", ""),
                        "input": tc.get("input", ""),
                        "output": tc.get("output", ""),
                        "level": tc.get("level"),
                        "start_time": tc.get("timestamp", ""),
                    })()
                    self.observations.append(obs)
                for msg in data.get("messages", []):
                    obs = type("Obs", (), {
                        "type": "GENERATION",
                        "name": "generation",
                        "input": msg.get("user", ""),
                        "output": msg.get("assistant", ""),
                        "level": None,
                        "start_time": msg.get("timestamp", ""),
                    })()
                    self.observations.append(obs)

        trace = FakeTrace(dataset)
        persona = args.persona or dataset.get("metadata", {}).get("persona", "sisyphus")
        trace_context = extract_trace_context(trace)

        print(f"\nEvaluating trace: {trace.id} (persona: {persona})")
        result = judge_trace(client, trace_context, persona)

        print(f"\n  Overall: {result.get('overall_score', 'N/A')}/5")
        print(f"  Summary: {result.get('summary', 'N/A')}")
        for dim, score in result.get("scores", {}).items():
            reasoning = result.get("reasoning", {}).get(dim, "")
            print(f"  {dim}: {score}/5 — {reasoning}")

        if not args.dry_run:
            post_judge_scores(langfuse, trace.id, persona, result)
            print("\nScores posted to Langfuse.")

    elif args.trace_id:
        trace = langfuse.get_trace(args.trace_id)
        persona = args.persona or get_trace_persona(trace)

        if persona not in VALID_PERSONAS:
            print(f"ERROR: Unknown persona '{persona}'", file=sys.stderr)
            sys.exit(1)

        trace_context = extract_trace_context(trace)
        print(f"\nEvaluating trace: {args.trace_id} (persona: {persona})")
        result = judge_trace(client, trace_context, persona)

        print(f"\n  Overall: {result.get('overall_score', 'N/A')}/5")
        print(f"  Summary: {result.get('summary', 'N/A')}")
        for dim, score in result.get("scores", {}).items():
            reasoning = result.get("reasoning", {}).get(dim, "")
            print(f"  {dim}: {score}/5 — {reasoning}")

        if not args.dry_run:
            post_judge_scores(langfuse, args.trace_id, persona, result)
            print("\nScores posted to Langfuse.")

    else:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        traces = langfuse.get_traces(from_timestamp=since)

        evaluated = 0
        for trace_summary in traces.data:
            trace = langfuse.get_trace(trace_summary.id)
            persona = args.persona or get_trace_persona(trace)

            if persona not in VALID_PERSONAS:
                continue

            trace_context = extract_trace_context(trace)
            print(f"\nEvaluating trace: {trace_summary.id} (persona: {persona})")
            result = judge_trace(client, trace_context, persona)

            print(f"  Overall: {result.get('overall_score', 'N/A')}/5")

            if not args.dry_run:
                post_judge_scores(langfuse, trace_summary.id, persona, result)
            evaluated += 1

        print(f"\nEvaluated {evaluated} traces.")

    langfuse.flush()


if __name__ == "__main__":
    main()
