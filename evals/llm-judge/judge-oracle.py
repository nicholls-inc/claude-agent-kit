#!/usr/bin/env python3
"""judge-oracle.py — LLM-as-judge for oracle architecture advice quality.

Evaluates oracle agent traces for recommendation quality, verbosity compliance,
and effort tag presence.

Usage:
  uv run evals/llm-judge/judge-oracle.py --trace-id TRACE_ID
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/llm-judge/judge-oracle.py", file=sys.stderr)
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package required. Run via: uv run evals/llm-judge/judge-oracle.py", file=sys.stderr)
    sys.exit(1)


RUBRIC_PATH = Path(__file__).parent / "rubrics" / "oracle-quality.md"
EFFORT_TAGS = re.compile(r"\b(Quick|Short|Medium|Large)\b")


def load_rubric() -> str:
    return RUBRIC_PATH.read_text()


def extract_oracle_response(trace) -> str:
    """Extract the oracle's response from trace."""
    observations = trace.observations if hasattr(trace, "observations") else []
    parts = []
    for obs in sorted(observations, key=lambda o: getattr(o, "start_time", "") or ""):
        if getattr(obs, "type", "") == "GENERATION":
            out = getattr(obs, "output", "")
            if out:
                parts.append(str(out))
    return "\n\n".join(parts)


def compute_automated_scores(response: str) -> dict:
    """Compute boolean scores without LLM."""
    scores = {}

    # effort_tag_present
    scores["oracle.effort_tag_present"] = 1 if EFFORT_TAGS.search(response) else 0

    # verbosity_compliance: bottom line <= 3 sentences, steps <= 7
    # Heuristic: count sentences in first paragraph, count numbered items
    paragraphs = response.strip().split("\n\n")
    first_para = paragraphs[0] if paragraphs else ""
    sentence_count = len(re.findall(r"[.!?]+", first_para))
    step_count = len(re.findall(r"^\s*\d+\.", response, re.MULTILINE))

    verbose = sentence_count > 5 or step_count > 7
    scores["oracle.verbosity_compliance"] = 0 if verbose else 1

    return scores


def judge_oracle(client: anthropic.Anthropic, response: str) -> dict:
    """Evaluate oracle quality using LLM-as-judge."""
    rubric = load_rubric()

    prompt = f"""You are evaluating architecture advice from an AI oracle agent.

## Rubric

{rubric}

## Oracle Response

{response[:3000]}

## Instructions

Score recommendation_quality from 1-5. Return JSON:

```json
{{
  "scores": {{
    "recommendation_quality": <1-5>
  }},
  "reasoning": {{
    "recommendation_quality": "<explanation>"
  }},
  "summary": "<1-2 sentence assessment>"
}}
```

Return ONLY the JSON object."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = resp.content[0].text
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
    parser = argparse.ArgumentParser(description="LLM-as-judge oracle quality evaluation")
    parser.add_argument("--trace-id", required=True, help="Trace ID to evaluate")
    parser.add_argument("--dry-run", action="store_true", help="Print without posting")
    args = parser.parse_args()

    langfuse = Langfuse()
    client = anthropic.Anthropic()

    trace = langfuse.get_trace(args.trace_id)
    response = extract_oracle_response(trace)

    auto_scores = compute_automated_scores(response)
    llm_result = judge_oracle(client, response)

    all_scores = {**auto_scores}
    for dim, score in llm_result.get("scores", {}).items():
        all_scores[f"oracle.{dim}"] = score

    print(f"\nTrace: {args.trace_id}")
    print(f"  Summary: {llm_result.get('summary', 'N/A')}")
    for k, v in sorted(all_scores.items()):
        print(f"  {k}: {v}")

    if not args.dry_run:
        for name, value in all_scores.items():
            langfuse.score(trace_id=args.trace_id, name=name, value=value)
        print("\nScores posted to Langfuse.")

    langfuse.flush()


if __name__ == "__main__":
    main()
