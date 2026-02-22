#!/usr/bin/env python3
"""persona-trace-analyzer.py — Automated tool-pattern analysis for persona traces.

Extracts deterministic behavioral scores from Langfuse traces without LLM calls.
Each persona has specific tool-pattern expectations derived from its contract.

Scores computed:
  Sisyphus:   workflow_sequence, parallel_exploration, verification_present, no_nested_orchestration
  Hephaestus: execution_depth, verification_depth, retry_quality, no_nested_orchestration, persistence
  Prometheus: plan_produced, no_code_edits, artifact_location, checklist_format
  Atlas:      boulder_read, task_advancement, verification_before_done, bounded_continuation, single_slice_focus

Usage:
  uv run evals/persona-trace-analyzer.py [--trace-id TRACE_ID] [--persona NAME] [--days 7]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/persona-trace-analyzer.py", file=sys.stderr)
    sys.exit(1)


# --- Tool classification helpers ---

EXPLORE_TOOLS = {"Glob", "Grep", "Read", "Task"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}
PERSONA_AGENTS = {"sisyphus", "hephaestus", "atlas", "prometheus"}

VERIFICATION_COMMANDS = re.compile(
    r"\b(test|jest|pytest|vitest|mocha|typecheck|tsc|mypy|pyright|"
    r"build|make|cargo build|go build|npm run build|"
    r"lint|eslint|flake8|ruff|shellcheck)\b",
    re.IGNORECASE,
)

CODE_EXTENSIONS = re.compile(
    r"\.(ts|tsx|js|jsx|py|go|rs|java|rb|php|c|cpp|sh)$", re.IGNORECASE
)


def extract_tool_sequence(trace) -> list[dict]:
    """Extract ordered tool call sequence from trace observations."""
    observations = trace.observations if hasattr(trace, "observations") else []
    tools = []
    for obs in sorted(observations, key=lambda o: getattr(o, "start_time", "") or ""):
        if hasattr(obs, "type") and obs.type == "SPAN":
            tool = {
                "name": getattr(obs, "name", ""),
                "input": str(getattr(obs, "input", "") or ""),
                "output": str(getattr(obs, "output", "") or ""),
                "level": getattr(obs, "level", None),
            }
            tools.append(tool)
    return tools


def get_trace_persona(trace) -> str:
    """Extract persona from trace metadata."""
    metadata = getattr(trace, "metadata", {}) or {}
    return metadata.get("persona", metadata.get("hook.persona", "unknown"))


# --- Sisyphus scores ---

def score_sisyphus(tools: list[dict]) -> dict:
    scores = {}

    # workflow_sequence: explore actions before edit actions
    first_edit_idx = None
    last_explore_before_edit = None
    for i, t in enumerate(tools):
        if t["name"] in EDIT_TOOLS and first_edit_idx is None:
            first_edit_idx = i
        if t["name"] in EXPLORE_TOOLS and (first_edit_idx is None or i < first_edit_idx):
            last_explore_before_edit = i

    scores["sisyphus.workflow_sequence"] = 1 if (
        last_explore_before_edit is not None
        and first_edit_idx is not None
        and last_explore_before_edit < first_edit_idx
    ) else 0

    # parallel_exploration: Task tool used (spawning leaf workers)
    has_task_call = any(t["name"] == "Task" for t in tools)
    scores["sisyphus.parallel_exploration"] = 1 if has_task_call else 0

    # verification_present: Bash with verification after last edit
    last_edit_idx = max(
        (i for i, t in enumerate(tools) if t["name"] in EDIT_TOOLS),
        default=-1,
    )
    has_verification = False
    if last_edit_idx >= 0:
        for t in tools[last_edit_idx + 1:]:
            if t["name"] == "Bash" and VERIFICATION_COMMANDS.search(t["input"]):
                has_verification = True
                break
    scores["sisyphus.verification_present"] = 1 if has_verification else 0

    # no_nested_orchestration: no Task calls spawn persona agents
    nested = False
    for t in tools:
        if t["name"] == "Task":
            inp_lower = t["input"].lower()
            if any(p in inp_lower for p in PERSONA_AGENTS):
                nested = True
                break
    scores["sisyphus.no_nested_orchestration"] = 0 if nested else 1

    return scores


# --- Hephaestus scores ---

def score_hephaestus(tools: list[dict]) -> dict:
    scores = {}

    # execution_depth: count of edit/write calls
    edit_count = sum(1 for t in tools if t["name"] in EDIT_TOOLS)
    scores["hephaestus.execution_depth"] = edit_count

    # verification_depth: distinct verification types
    verification_types = set()
    for t in tools:
        if t["name"] == "Bash":
            inp = t["input"].lower()
            if re.search(r"\b(test|jest|pytest|vitest|mocha)\b", inp):
                verification_types.add("test")
            if re.search(r"\b(tsc|typecheck|mypy|pyright)\b", inp):
                verification_types.add("typecheck")
            if re.search(r"\b(build|make|cargo build|go build|npm run build)\b", inp):
                verification_types.add("build")
            if re.search(r"\b(lint|eslint|flake8|ruff|shellcheck)\b", inp):
                verification_types.add("lint")
    scores["hephaestus.verification_depth"] = len(verification_types)

    # retry_quality: after a failed verification, next action is targeted edit
    retry_quality = True
    for i, t in enumerate(tools):
        if t["name"] == "Bash" and t.get("level") == "ERROR":
            if VERIFICATION_COMMANDS.search(t["input"]):
                # Look at next non-Bash action
                for nt in tools[i + 1:]:
                    if nt["name"] in EDIT_TOOLS:
                        break  # Good: targeted fix
                    elif nt["name"] in EXPLORE_TOOLS - {"Read"}:
                        retry_quality = False  # Bad: random exploration
                        break
                    elif nt["name"] == "Bash":
                        continue  # Skip consecutive Bash
                    else:
                        break
    scores["hephaestus.retry_quality"] = 1 if retry_quality else 0

    # no_nested_orchestration
    nested = any(
        t["name"] == "Task" and any(p in t["input"].lower() for p in PERSONA_AGENTS)
        for t in tools
    )
    scores["hephaestus.no_nested_orchestration"] = 0 if nested else 1

    # persistence: session didn't stop early (heuristic: has both edits and verification)
    has_edits = edit_count > 0
    has_verification = len(verification_types) > 0
    scores["hephaestus.persistence"] = 1 if (has_edits and has_verification) else 0

    return scores


# --- Prometheus scores ---

def score_prometheus(tools: list[dict]) -> dict:
    scores = {}

    # plan_produced: Write call creating .md under .agent-kit/
    plan_produced = any(
        t["name"] == "Write" and ".agent-kit/" in t["input"] and t["input"].endswith(".md")
        for t in tools
    )
    scores["prometheus.plan_produced"] = 1 if plan_produced else 0

    # no_code_edits: no Edit/Write targeting code files
    code_edits = any(
        t["name"] in EDIT_TOOLS and CODE_EXTENSIONS.search(t["input"])
        for t in tools
    )
    scores["prometheus.no_code_edits"] = 0 if code_edits else 1

    # artifact_location: all Write targets under .agent-kit/ or .md
    all_writes_safe = all(
        ".agent-kit/" in t["input"] or t["input"].endswith(".md")
        for t in tools
        if t["name"] == "Write"
    )
    scores["prometheus.artifact_location"] = 1 if all_writes_safe else 0

    # checklist_format: plan content contains - [ ] items
    has_checklist = any(
        "- [ ]" in t["output"]
        for t in tools
        if t["name"] == "Write" and ".agent-kit/" in t["input"]
    )
    scores["prometheus.checklist_format"] = 1 if has_checklist else 0

    return scores


# --- Atlas scores ---

def score_atlas(tools: list[dict]) -> dict:
    scores = {}

    # boulder_read: early Read of boulder.json
    boulder_read = False
    for i, t in enumerate(tools[:10]):  # Check first 10 tool calls
        if t["name"] == "Read" and "boulder.json" in t["input"]:
            boulder_read = True
            break
    scores["atlas.boulder_read"] = 1 if boulder_read else 0

    # task_advancement: Edit modifies plan (- [ ] -> - [x]) AND Write updates boulder.json
    plan_edit = any(
        t["name"] == "Edit" and ("- [x]" in t["input"] or "- [x]" in t.get("output", ""))
        for t in tools
    )
    boulder_write = any(
        t["name"] == "Write" and "boulder.json" in t["input"]
        for t in tools
    )
    scores["atlas.task_advancement"] = 1 if (plan_edit and boulder_write) else 0

    # verification_before_done: verification Bash before last boulder write
    last_boulder_write_idx = max(
        (i for i, t in enumerate(tools) if t["name"] == "Write" and "boulder.json" in t["input"]),
        default=-1,
    )
    has_verification_before = False
    if last_boulder_write_idx > 0:
        for t in tools[:last_boulder_write_idx]:
            if t["name"] == "Bash" and VERIFICATION_COMMANDS.search(t["input"]):
                has_verification_before = True
                break
    scores["atlas.verification_before_done"] = 1 if has_verification_before else 0

    # bounded_continuation: heuristic — session didn't use excessive tool calls
    scores["atlas.bounded_continuation"] = 1 if len(tools) <= 100 else 0

    # single_slice_focus: no interleaving of different task reads
    boulder_reads = [
        t for t in tools if t["name"] == "Read" and "boulder.json" in t["input"]
    ]
    scores["atlas.single_slice_focus"] = 1 if len(boulder_reads) <= 3 else 0

    return scores


PERSONA_SCORERS = {
    "sisyphus": score_sisyphus,
    "hephaestus": score_hephaestus,
    "prometheus": score_prometheus,
    "atlas": score_atlas,
}


def post_scores_to_langfuse(langfuse: "Langfuse", trace_id: str, scores: dict):
    """Post all computed scores to Langfuse."""
    for name, value in scores.items():
        langfuse.score(
            trace_id=trace_id,
            name=name,
            value=value,
        )


def analyze_trace(langfuse: "Langfuse", trace, persona: str = None, dry_run: bool = False) -> dict:
    """Analyze a single trace and return scores."""
    if persona is None:
        persona = get_trace_persona(trace)

    tools = extract_tool_sequence(trace)

    if persona not in PERSONA_SCORERS:
        print(f"  Unknown persona '{persona}', skipping.", file=sys.stderr)
        return {}

    scores = PERSONA_SCORERS[persona](tools)

    trace_id = trace.id if hasattr(trace, "id") else str(trace)
    print(f"\nTrace: {trace_id} (persona: {persona})")
    for k, v in sorted(scores.items()):
        status = "PASS" if v else "FAIL" if isinstance(v, (bool, int)) and v == 0 else str(v)
        print(f"  {k}: {v} ({status})")

    if not dry_run:
        post_scores_to_langfuse(langfuse, trace_id, scores)

    return scores


def main():
    parser = argparse.ArgumentParser(description="Automated persona trace analysis")
    parser.add_argument("--trace-id", help="Analyze a specific trace")
    parser.add_argument("--persona", help="Override persona detection")
    parser.add_argument("--days", type=int, default=7, help="Analyze traces from last N days")
    parser.add_argument("--dry-run", action="store_true", help="Print scores without posting")
    parser.add_argument("--dataset", help="Path to JSON dataset file for offline analysis")
    args = parser.parse_args()

    langfuse = Langfuse()

    if args.dataset:
        # Offline mode: analyze frozen trace datasets
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

        trace = FakeTrace(dataset)
        analyze_trace(langfuse, trace, persona=args.persona, dry_run=args.dry_run)

    elif args.trace_id:
        trace = langfuse.get_trace(args.trace_id)
        analyze_trace(langfuse, trace, persona=args.persona, dry_run=args.dry_run)

    else:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        traces = langfuse.get_traces(from_timestamp=since)

        for trace_summary in traces.data:
            trace = langfuse.get_trace(trace_summary.id)
            persona = args.persona or get_trace_persona(trace)
            if persona in PERSONA_SCORERS:
                analyze_trace(langfuse, trace, persona=persona, dry_run=args.dry_run)

    langfuse.flush()


if __name__ == "__main__":
    main()
