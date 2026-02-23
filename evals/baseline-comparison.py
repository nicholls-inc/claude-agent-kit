#!/usr/bin/env python3
"""baseline-comparison.py — Compare plugin vs vanilla Claude Code sessions.

Fetches paired traces from Langfuse (tagged plugin:true/plugin:false),
computes delta scores, and generates a comparison report.

Usage:
  uv run evals/baseline-comparison.py --days 30
  uv run evals/baseline-comparison.py --output evals/reports/baseline-comparison.md
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/baseline-comparison.py", file=sys.stderr)
    sys.exit(1)


REPORT_DIR = Path(__file__).parent / "reports"
TASKS_DATASET = Path(__file__).parent / "datasets" / "baseline-tasks.json"


def fetch_paired_traces(langfuse: "Langfuse", days: int) -> dict:
    """Fetch traces grouped by task, separated by plugin/vanilla."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    traces = langfuse.get_traces(from_timestamp=since)

    pairs = {}  # task_name -> {"plugin": trace, "vanilla": trace}

    for trace_summary in traces.data:
        trace = langfuse.get_trace(trace_summary.id)
        metadata = getattr(trace, "metadata", {}) or {}

        task_name = metadata.get("baseline_task", None)
        is_plugin = metadata.get("plugin", None)

        if task_name is None or is_plugin is None:
            continue

        if task_name not in pairs:
            pairs[task_name] = {}

        key = "plugin" if is_plugin else "vanilla"
        pairs[task_name][key] = trace

    return pairs


def compute_trace_metrics(trace) -> dict:
    """Compute basic metrics from a trace."""
    observations = trace.observations if hasattr(trace, "observations") else []

    tool_count = 0
    turn_count = 0
    has_verification = False

    for obs in observations:
        obs_type = getattr(obs, "type", "")
        if obs_type == "SPAN":
            tool_count += 1
            if getattr(obs, "name", "") == "Bash":
                inp = str(getattr(obs, "input", "")).lower()
                if any(v in inp for v in ["test", "typecheck", "tsc", "build", "lint"]):
                    has_verification = True
        elif obs_type == "GENERATION":
            turn_count += 1

    # Get token usage from trace metadata
    usage = getattr(trace, "usage", {}) or {}
    total_tokens = usage.get("total_tokens", 0) or 0

    return {
        "turns": turn_count,
        "tokens": total_tokens,
        "tool_calls": tool_count,
        "verification": has_verification,
    }


def get_trace_scores(langfuse: "Langfuse", trace_id: str) -> dict:
    """Get all scores posted on a trace."""
    scores = {}
    try:
        trace = langfuse.get_trace(trace_id)
        for score in getattr(trace, "scores", []) or []:
            scores[score.name] = score.value
    except Exception:
        pass
    return scores


def generate_report(pairs: dict, langfuse: "Langfuse") -> str:
    """Generate markdown comparison report."""
    lines = [
        "# Plugin vs Vanilla Baseline Comparison",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Task | Plugin Turns | Vanilla Turns | Plugin Tokens | Vanilla Tokens | Plugin Verification | Vanilla Verification | Plugin Quality | Vanilla Quality |",
        "|------|-------------|---------------|---------------|----------------|--------------------|--------------------|----------------|-----------------|",
    ]

    summary = {"plugin_wins": 0, "vanilla_wins": 0, "ties": 0}

    for task_name, pair in sorted(pairs.items()):
        plugin_trace = pair.get("plugin")
        vanilla_trace = pair.get("vanilla")

        if not plugin_trace or not vanilla_trace:
            continue

        pm = compute_trace_metrics(plugin_trace)
        vm = compute_trace_metrics(vanilla_trace)

        # Get quality scores
        p_scores = get_trace_scores(langfuse, plugin_trace.id)
        v_scores = get_trace_scores(langfuse, vanilla_trace.id)
        p_quality = p_scores.get("signal.overall_quality", "N/A")
        v_quality = v_scores.get("signal.overall_quality", "N/A")

        lines.append(
            f"| {task_name} | {pm['turns']} | {vm['turns']} | "
            f"{pm['tokens']:,} | {vm['tokens']:,} | "
            f"{'Yes' if pm['verification'] else 'No'} | "
            f"{'Yes' if vm['verification'] else 'No'} | "
            f"{p_quality} | {v_quality} |"
        )

        # Simple win counting: fewer turns and has verification = better
        p_score = (10 - min(pm["turns"], 10)) + (2 if pm["verification"] else 0)
        v_score = (10 - min(vm["turns"], 10)) + (2 if vm["verification"] else 0)

        if p_score > v_score:
            summary["plugin_wins"] += 1
        elif v_score > p_score:
            summary["vanilla_wins"] += 1
        else:
            summary["ties"] += 1

    lines.extend([
        "",
        "## Summary",
        "",
        f"- Plugin wins: {summary['plugin_wins']}",
        f"- Vanilla wins: {summary['vanilla_wins']}",
        f"- Ties: {summary['ties']}",
        f"- Total paired tasks: {sum(summary.values())}",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Plugin vs vanilla baseline comparison")
    parser.add_argument("--days", type=int, default=30, help="Look back N days for traces")
    parser.add_argument("--output", help="Output file path for report")
    args = parser.parse_args()

    langfuse = Langfuse()

    print("Fetching paired traces...")
    pairs = fetch_paired_traces(langfuse, args.days)
    print(f"Found {len(pairs)} task pairs.")

    report = generate_report(pairs, langfuse)

    output_path = args.output or str(REPORT_DIR / "baseline-comparison.md")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report)
    print(f"\nReport written to: {output_path}")
    print(report)

    langfuse.flush()


if __name__ == "__main__":
    main()
