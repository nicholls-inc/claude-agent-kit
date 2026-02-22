#!/usr/bin/env python3
"""session-signals.py — Plano-style heuristic session quality signals.

Computes lightweight, deterministic quality indicators from Langfuse traces
without any LLM calls. Posts computed signals as scores to Langfuse.

Signals:
  signal.turn_count         — Count of user-assistant exchanges
  signal.efficiency_score   — 1 / (1 + 0.3 * (turns - baseline))
  signal.repair_count       — User corrections detected
  signal.repair_ratio       — repair_count / user_turns
  signal.repetition_count   — Near-duplicate assistant responses
  signal.frustration_severity — 0-3 severity scale
  signal.positive_feedback  — Count of positive user messages
  signal.escalation_requested — User gave up
  signal.tool_call_count    — Total tool calls
  signal.tool_failure_rate  — Error rate of tool calls
  signal.verification_present — Verification ran after last edit
  signal.overall_quality    — Aggregate categorical rating

Usage:
  uv run evals/session-signals.py [--trace-id TRACE_ID] [--days 7]
"""

import argparse
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

try:
    from langfuse import Langfuse
except ImportError:
    print("ERROR: langfuse package required. Run via: uv run evals/session-signals.py", file=sys.stderr)
    sys.exit(1)


# --- Configuration ---

BASELINE_TURNS = 5
EFFICIENCY_DECAY = 0.3

REPAIR_PATTERNS = re.compile(
    r"\b(i meant|no,? i|let me rephrase|correction|actually i want|"
    r"that's not what|i said|wrong|not what i asked)\b",
    re.IGNORECASE,
)

FRUSTRATION_MILD = re.compile(
    r"\b(this is frustrating|doesn't work|not working|broken|annoying)\b",
    re.IGNORECASE,
)
FRUSTRATION_MODERATE = re.compile(
    r"\b(confused|what are you doing|i already told you|why did you|"
    r"you keep|wrong again|still wrong)\b",
    re.IGNORECASE,
)
FRUSTRATION_SEVERE = re.compile(
    r"[A-Z]{5,}|[!?]{3,}|\b(fuck|shit|damn|hell|crap|wtf)\b",
    re.IGNORECASE,
)

POSITIVE_PATTERNS = re.compile(
    r"\b(thank you|thanks|perfect|great|excellent|awesome|exactly what i wanted|"
    r"that's exactly|nice|well done|good job)\b",
    re.IGNORECASE,
)

ESCALATION_PATTERNS = re.compile(
    r"\b(i give up|this doesn't work|forget it|do it manually|"
    r"never mind|nevermind|i'll do it myself)\b",
    re.IGNORECASE,
)

VERIFICATION_COMMANDS = re.compile(
    r"\b(test|jest|pytest|vitest|mocha|typecheck|tsc|mypy|pyright|"
    r"build|make|cargo build|go build|npm run build|"
    r"lint|eslint|flake8|ruff|shellcheck)\b",
    re.IGNORECASE,
)

CODE_EXTENSIONS = re.compile(
    r"\.(ts|tsx|js|jsx|py|go|rs|java|rb|php|c|cpp|sh)$", re.IGNORECASE
)


def bigram_jaccard(a: str, b: str) -> float:
    """Compute bigram Jaccard similarity between two strings."""
    if not a or not b:
        return 0.0
    words_a = a.lower().split()
    words_b = b.lower().split()
    if len(words_a) < 2 or len(words_b) < 2:
        return 0.0
    bigrams_a = set(zip(words_a, words_a[1:]))
    bigrams_b = set(zip(words_b, words_b[1:]))
    intersection = bigrams_a & bigrams_b
    union = bigrams_a | bigrams_b
    return len(intersection) / len(union) if union else 0.0


def compute_signals(trace) -> dict:
    """Compute all session signals from a Langfuse trace."""
    signals = {}

    # Extract messages and tool calls from trace observations
    observations = trace.observations if hasattr(trace, "observations") else []

    user_messages = []
    assistant_messages = []
    tool_calls = []

    for obs in observations:
        if hasattr(obs, "type"):
            if obs.type == "GENERATION":
                # Approximate: input is user, output is assistant
                if hasattr(obs, "input") and obs.input:
                    text = str(obs.input) if not isinstance(obs.input, str) else obs.input
                    user_messages.append(text)
                if hasattr(obs, "output") and obs.output:
                    text = str(obs.output) if not isinstance(obs.output, str) else obs.output
                    assistant_messages.append(text)
            elif obs.type == "SPAN" and hasattr(obs, "name"):
                tool_call = {
                    "name": obs.name,
                    "input": getattr(obs, "input", None),
                    "output": getattr(obs, "output", None),
                    "status": getattr(obs, "status_message", None),
                    "level": getattr(obs, "level", None),
                }
                tool_calls.append(tool_call)

    # --- Turn count ---
    turn_count = max(len(user_messages), len(assistant_messages))
    signals["signal.turn_count"] = turn_count

    # --- Efficiency score ---
    efficiency = 1.0 / (1.0 + EFFICIENCY_DECAY * max(0, turn_count - BASELINE_TURNS))
    signals["signal.efficiency_score"] = round(efficiency, 3)

    # --- Repair count/ratio ---
    repair_count = sum(1 for msg in user_messages if REPAIR_PATTERNS.search(msg))
    user_turn_count = len(user_messages) or 1
    signals["signal.repair_count"] = repair_count
    signals["signal.repair_ratio"] = round(repair_count / user_turn_count, 3)

    # --- Repetition count ---
    repetition_count = 0
    for i in range(len(assistant_messages)):
        for j in range(i + 1, len(assistant_messages)):
            sim = bigram_jaccard(assistant_messages[i], assistant_messages[j])
            if sim >= 0.5:
                repetition_count += 1
    signals["signal.repetition_count"] = repetition_count

    # --- Frustration severity ---
    max_frustration = 0
    for msg in user_messages:
        if FRUSTRATION_SEVERE.search(msg):
            max_frustration = max(max_frustration, 3)
        elif FRUSTRATION_MODERATE.search(msg):
            max_frustration = max(max_frustration, 2)
        elif FRUSTRATION_MILD.search(msg):
            max_frustration = max(max_frustration, 1)
    signals["signal.frustration_severity"] = max_frustration

    # --- Positive feedback ---
    positive_count = sum(1 for msg in user_messages if POSITIVE_PATTERNS.search(msg))
    signals["signal.positive_feedback"] = positive_count

    # --- Escalation requested ---
    escalation = any(ESCALATION_PATTERNS.search(msg) for msg in user_messages)
    signals["signal.escalation_requested"] = 1 if escalation else 0

    # --- Tool call count ---
    signals["signal.tool_call_count"] = len(tool_calls)

    # --- Tool failure rate ---
    failed_tools = sum(
        1 for tc in tool_calls
        if tc.get("level") == "ERROR"
        or (tc.get("status") and "error" in str(tc["status"]).lower())
    )
    signals["signal.tool_failure_rate"] = round(
        failed_tools / len(tool_calls), 3
    ) if tool_calls else 0.0

    # --- Verification present ---
    last_edit_idx = -1
    has_verification_after_edit = False
    for i, tc in enumerate(tool_calls):
        name = tc.get("name", "")
        if name in ("Edit", "Write", "MultiEdit"):
            # Check if it targets a code file
            inp = str(tc.get("input", ""))
            if CODE_EXTENSIONS.search(inp):
                last_edit_idx = i

    if last_edit_idx >= 0:
        for tc in tool_calls[last_edit_idx + 1:]:
            if tc.get("name") == "Bash":
                inp = str(tc.get("input", ""))
                if VERIFICATION_COMMANDS.search(inp):
                    has_verification_after_edit = True
                    break

    signals["signal.verification_present"] = 1 if has_verification_after_edit else 0

    # --- Overall quality ---
    quality = _compute_overall_quality(signals)
    signals["signal.overall_quality"] = quality

    return signals


def _compute_overall_quality(signals: dict) -> str:
    """Aggregate signals into a categorical quality rating."""
    if (
        signals.get("signal.escalation_requested", 0)
        or signals.get("signal.frustration_severity", 0) >= 3
        or signals.get("signal.repetition_count", 0) >= 5
        or signals.get("signal.turn_count", 0) > 15
    ):
        return "Severe"

    if (
        signals.get("signal.repair_ratio", 0) > 0.3
        or signals.get("signal.frustration_severity", 0) >= 2
        or signals.get("signal.repetition_count", 0) >= 3
        or signals.get("signal.turn_count", 0) > 12
    ):
        return "Poor"

    if (
        signals.get("signal.positive_feedback", 0) > 0
        and signals.get("signal.efficiency_score", 0) > 0.8
        and signals.get("signal.verification_present", 0)
    ):
        return "Excellent"

    if (
        signals.get("signal.efficiency_score", 0) > 0.6
        and signals.get("signal.repair_ratio", 0) < 0.15
    ):
        return "Good"

    return "Neutral"


QUALITY_NUMERIC = {
    "Severe": 1,
    "Poor": 2,
    "Neutral": 3,
    "Good": 4,
    "Excellent": 5,
}


def post_signals_to_langfuse(langfuse: "Langfuse", trace_id: str, signals: dict):
    """Post all computed signals as scores to Langfuse."""
    for name, value in signals.items():
        if name == "signal.overall_quality":
            numeric_val = QUALITY_NUMERIC.get(value, 3)
            langfuse.score(
                trace_id=trace_id,
                name=name,
                value=numeric_val,
                comment=value,
            )
        elif isinstance(value, (int, float)):
            langfuse.score(
                trace_id=trace_id,
                name=name,
                value=value,
            )


def main():
    parser = argparse.ArgumentParser(description="Compute session quality signals")
    parser.add_argument("--trace-id", help="Process a specific trace ID")
    parser.add_argument("--days", type=int, default=7, help="Process traces from last N days")
    parser.add_argument("--dry-run", action="store_true", help="Print signals without posting")
    args = parser.parse_args()

    langfuse = Langfuse()

    if args.trace_id:
        trace = langfuse.get_trace(args.trace_id)
        signals = compute_signals(trace)
        print(f"\nTrace: {args.trace_id}")
        for k, v in sorted(signals.items()):
            print(f"  {k}: {v}")
        if not args.dry_run:
            post_signals_to_langfuse(langfuse, args.trace_id, signals)
            print("\nSignals posted to Langfuse.")
    else:
        # Process recent traces
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        traces = langfuse.get_traces(from_timestamp=since)

        processed = 0
        for trace_summary in traces.data:
            trace = langfuse.get_trace(trace_summary.id)
            signals = compute_signals(trace)
            print(f"\nTrace: {trace_summary.id} — {signals.get('signal.overall_quality', 'Unknown')}")
            if not args.dry_run:
                post_signals_to_langfuse(langfuse, trace_summary.id, signals)
            processed += 1

        print(f"\nProcessed {processed} traces.")

    langfuse.flush()


if __name__ == "__main__":
    main()
