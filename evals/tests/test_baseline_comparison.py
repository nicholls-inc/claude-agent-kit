"""Tests for baseline-comparison.py — pure logic functions."""

import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

mod = importlib.import_module("baseline-comparison")

compute_trace_metrics = mod.compute_trace_metrics
generate_report = mod.generate_report


# --- Helpers ---

class FakeObs:
    def __init__(self, obs_type, name="", inp="", out="", level=None):
        self.type = obs_type
        self.name = name
        self.input = inp
        self.output = out
        self.level = level


class FakeTrace:
    def __init__(self, observations=None, usage=None, trace_id="test"):
        self.observations = observations or []
        self.usage = usage or {}
        self.id = trace_id
        self.scores = []
        self.metadata = {}


# --- compute_trace_metrics ---

def test_compute_trace_metrics_empty():
    trace = FakeTrace()
    metrics = compute_trace_metrics(trace)
    assert metrics["turns"] == 0
    assert metrics["tokens"] == 0
    assert metrics["tool_calls"] == 0
    assert metrics["verification"] is False


def test_compute_trace_metrics_counts_tools():
    trace = FakeTrace([
        FakeObs("SPAN", name="Read"),
        FakeObs("SPAN", name="Edit"),
        FakeObs("SPAN", name="Bash"),
    ])
    metrics = compute_trace_metrics(trace)
    assert metrics["tool_calls"] == 3


def test_compute_trace_metrics_counts_turns():
    trace = FakeTrace([
        FakeObs("GENERATION"),
        FakeObs("GENERATION"),
    ])
    metrics = compute_trace_metrics(trace)
    assert metrics["turns"] == 2


def test_compute_trace_metrics_detects_verification():
    trace = FakeTrace([
        FakeObs("SPAN", name="Bash", inp="npm test"),
    ])
    metrics = compute_trace_metrics(trace)
    assert metrics["verification"] is True


def test_compute_trace_metrics_no_verification():
    trace = FakeTrace([
        FakeObs("SPAN", name="Bash", inp="echo hello"),
    ])
    metrics = compute_trace_metrics(trace)
    assert metrics["verification"] is False


def test_compute_trace_metrics_verification_types():
    for cmd in ["npm test", "tsc --noEmit", "npm run build", "eslint .", "typecheck"]:
        trace = FakeTrace([FakeObs("SPAN", name="Bash", inp=cmd)])
        metrics = compute_trace_metrics(trace)
        assert metrics["verification"] is True, f"Expected verification for: {cmd}"


def test_compute_trace_metrics_token_usage():
    trace = FakeTrace(usage={"total_tokens": 5000})
    metrics = compute_trace_metrics(trace)
    assert metrics["tokens"] == 5000


def test_compute_trace_metrics_none_usage():
    trace = FakeTrace(usage=None)
    metrics = compute_trace_metrics(trace)
    assert metrics["tokens"] == 0


# --- generate_report ---

class FakeLangfuse:
    """Stub Langfuse client for testing generate_report."""
    def get_trace(self, trace_id):
        t = FakeTrace(trace_id=trace_id)
        t.scores = []
        return t

    def flush(self):
        pass


def test_generate_report_empty_pairs():
    report = generate_report({}, FakeLangfuse())
    assert "Plugin vs Vanilla Baseline Comparison" in report
    assert "Plugin wins: 0" in report


def test_generate_report_incomplete_pair():
    pairs = {
        "task1": {"plugin": FakeTrace(trace_id="p1")},  # missing vanilla
    }
    report = generate_report(pairs, FakeLangfuse())
    # Incomplete pairs are skipped, so no data rows
    assert "task1" not in report.split("Summary")[0].split("|------|")[1] if "|------|" in report else True


def test_generate_report_complete_pair():
    plugin_trace = FakeTrace([
        FakeObs("GENERATION"),
        FakeObs("SPAN", name="Bash", inp="npm test"),
    ], trace_id="plugin-1")
    vanilla_trace = FakeTrace([
        FakeObs("GENERATION"),
        FakeObs("GENERATION"),
        FakeObs("GENERATION"),
    ], trace_id="vanilla-1")

    pairs = {
        "add-feature": {"plugin": plugin_trace, "vanilla": vanilla_trace},
    }
    report = generate_report(pairs, FakeLangfuse())
    assert "add-feature" in report
    assert "Total paired tasks: 1" in report
