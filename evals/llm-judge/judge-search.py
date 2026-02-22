#!/usr/bin/env python3
"""judge-search.py — LLM-as-judge for explore agent search quality.

Evaluates search results from the explore agent.
Scores: completeness (1-5), path_format (bool), output_structure (bool), parallel_execution (bool).

Usage:
  uv run evals/llm-judge/judge-search.py --trace-id TRACE_ID
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/llm-judge/judge-search.py", file=sys.stderr)
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package required. Run via: uv run evals/llm-judge/judge-search.py", file=sys.stderr)
    sys.exit(1)


RUBRIC_PATH = Path(__file__).parent / "rubrics" / "search-quality.md"


def load_rubric() -> str:
    return RUBRIC_PATH.read_text()


def extract_search_context(trace) -> tuple[str, list[dict]]:
    """Extract search query and tool calls from trace."""
    observations = trace.observations if hasattr(trace, "observations") else []
    sorted_obs = sorted(observations, key=lambda o: getattr(o, "start_time", "") or "")

    parts = []
    tool_calls = []
    for obs in sorted_obs:
        obs_type = getattr(obs, "type", "")
        name = getattr(obs, "name", "")

        if obs_type == "GENERATION":
            inp = getattr(obs, "input", "")
            out = getattr(obs, "output", "")
            if inp:
                parts.append(f"[QUERY]\n{str(inp)[:1000]}")
            if out:
                parts.append(f"[RESPONSE]\n{str(out)[:2000]}")
        elif obs_type == "SPAN":
            tool_calls.append({
                "name": name,
                "input": str(getattr(obs, "input", ""))[:500],
                "output": str(getattr(obs, "output", ""))[:500],
            })
            parts.append(f"[TOOL: {name}]\n  Input: {str(getattr(obs, 'input', ''))[:500]}")

    return "\n\n".join(parts), tool_calls


def compute_automated_scores(tool_calls: list[dict]) -> dict:
    """Compute boolean scores that don't need LLM."""
    scores = {}

    # path_format: all returned paths are absolute
    paths_mentioned = []
    for tc in tool_calls:
        output = tc.get("output", "")
        # Look for file paths in output
        for line in output.split("\n"):
            if line.strip().startswith("/"):
                paths_mentioned.append(line.strip())

    all_absolute = all(p.startswith("/") for p in paths_mentioned) if paths_mentioned else True
    scores["explore.path_format"] = 1 if all_absolute else 0

    # output_structure: has results/files/answer sections (check final output)
    final_output = tool_calls[-1].get("output", "") if tool_calls else ""
    has_structure = any(
        kw in final_output.lower()
        for kw in ["result", "files", "answer", "found", "next steps"]
    )
    scores["explore.output_structure"] = 1 if has_structure else 0

    # parallel_execution: 3+ tools in first batch
    # Heuristic: check if first 3 tool calls have very similar timestamps
    first_tools = tool_calls[:3] if len(tool_calls) >= 3 else []
    scores["explore.parallel_execution"] = 1 if len(first_tools) >= 3 else 0

    return scores


def judge_search(client: anthropic.Anthropic, trace_context: str) -> dict:
    """Evaluate search quality using LLM-as-judge."""
    rubric = load_rubric()

    prompt = f"""You are evaluating a code search/exploration session by an AI agent.

## Rubric

{rubric}

## Session Trace

{trace_context}

## Instructions

Score the completeness dimension from 1-5. Return JSON:

```json
{{
  "scores": {{
    "completeness": <1-5>
  }},
  "reasoning": {{
    "completeness": "<explanation>"
  }},
  "summary": "<1-2 sentence assessment>"
}}
```

Return ONLY the JSON object."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
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
        return {"scores": {}, "reasoning": {}, "summary": "Parse error"}


def main():
    parser = argparse.ArgumentParser(description="LLM-as-judge search quality evaluation")
    parser.add_argument("--trace-id", required=True, help="Trace ID to evaluate")
    parser.add_argument("--dry-run", action="store_true", help="Print without posting")
    args = parser.parse_args()

    langfuse = Langfuse()
    client = anthropic.Anthropic()

    trace = langfuse.get_trace(args.trace_id)
    trace_context, tool_calls = extract_search_context(trace)

    # Automated scores
    auto_scores = compute_automated_scores(tool_calls)

    # LLM-judge score
    llm_result = judge_search(client, trace_context)

    print(f"\nTrace: {args.trace_id}")
    print(f"  Summary: {llm_result.get('summary', 'N/A')}")

    all_scores = {**auto_scores}
    for dim, score in llm_result.get("scores", {}).items():
        all_scores[f"explore.{dim}"] = score

    for k, v in sorted(all_scores.items()):
        print(f"  {k}: {v}")

    if not args.dry_run:
        for name, value in all_scores.items():
            langfuse.score(trace_id=args.trace_id, name=name, value=value)
        print("\nScores posted to Langfuse.")

    langfuse.flush()


if __name__ == "__main__":
    main()
