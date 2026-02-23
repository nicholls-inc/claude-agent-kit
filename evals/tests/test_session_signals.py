"""Tests for session-signals.py — pure logic functions."""

import sys
from pathlib import Path

# Add parent dir to path so we can import the module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the module with hyphens by using importlib
import importlib

mod = importlib.import_module("session-signals")

bigram_jaccard = mod.bigram_jaccard
compute_signals = mod.compute_signals
_compute_overall_quality = mod._compute_overall_quality
REPAIR_PATTERNS = mod.REPAIR_PATTERNS
FRUSTRATION_MILD = mod.FRUSTRATION_MILD
FRUSTRATION_MODERATE = mod.FRUSTRATION_MODERATE
FRUSTRATION_SEVERE = mod.FRUSTRATION_SEVERE
POSITIVE_PATTERNS = mod.POSITIVE_PATTERNS
ESCALATION_PATTERNS = mod.ESCALATION_PATTERNS
VERIFICATION_COMMANDS = mod.VERIFICATION_COMMANDS
QUALITY_NUMERIC = mod.QUALITY_NUMERIC


# --- Helper to build fake traces ---

class FakeObs:
    def __init__(self, obs_type, name="", inp="", out="", level=None, status=None):
        self.type = obs_type
        self.name = name
        self.input = inp
        self.output = out
        self.level = level
        self.status_message = status


class FakeTrace:
    def __init__(self, observations=None):
        self.observations = observations or []


# --- bigram_jaccard ---

def test_bigram_jaccard_identical():
    assert bigram_jaccard("hello world foo", "hello world foo") == 1.0


def test_bigram_jaccard_empty():
    assert bigram_jaccard("", "hello world") == 0.0
    assert bigram_jaccard("hello world", "") == 0.0
    assert bigram_jaccard("", "") == 0.0


def test_bigram_jaccard_single_word():
    assert bigram_jaccard("hello", "world") == 0.0


def test_bigram_jaccard_partial_overlap():
    sim = bigram_jaccard("hello world foo", "hello world bar")
    assert 0.0 < sim < 1.0


def test_bigram_jaccard_no_overlap():
    sim = bigram_jaccard("alpha beta gamma", "delta epsilon zeta")
    assert sim == 0.0


# --- Regex pattern tests ---

def test_repair_patterns_match():
    assert REPAIR_PATTERNS.search("i meant something else")
    assert REPAIR_PATTERNS.search("no, I wanted the other one")
    assert REPAIR_PATTERNS.search("let me rephrase that")
    assert REPAIR_PATTERNS.search("that's not what I asked")


def test_repair_patterns_no_match():
    assert not REPAIR_PATTERNS.search("great job, thanks")
    assert not REPAIR_PATTERNS.search("please add a new function")


def test_frustration_mild():
    assert FRUSTRATION_MILD.search("this is frustrating")
    assert FRUSTRATION_MILD.search("it's not working")
    assert not FRUSTRATION_MILD.search("thanks for the help")


def test_frustration_moderate():
    assert FRUSTRATION_MODERATE.search("what are you doing")
    assert FRUSTRATION_MODERATE.search("you keep making mistakes")
    assert FRUSTRATION_MODERATE.search("wrong again please fix")


def test_frustration_severe():
    assert FRUSTRATION_SEVERE.search("WHAT THE HELL")
    assert FRUSTRATION_SEVERE.search("this is shit")
    assert FRUSTRATION_SEVERE.search("wtf is this")
    assert FRUSTRATION_SEVERE.search("!!!")


def test_positive_patterns():
    assert POSITIVE_PATTERNS.search("thank you so much")
    assert POSITIVE_PATTERNS.search("that's exactly what I wanted")
    assert POSITIVE_PATTERNS.search("excellent work")


def test_escalation_patterns():
    assert ESCALATION_PATTERNS.search("i give up")
    assert ESCALATION_PATTERNS.search("forget it, I'll do it myself")
    assert ESCALATION_PATTERNS.search("never mind")


def test_verification_commands():
    assert VERIFICATION_COMMANDS.search("npm test")
    assert VERIFICATION_COMMANDS.search("pytest -v")
    assert VERIFICATION_COMMANDS.search("tsc --noEmit")
    assert VERIFICATION_COMMANDS.search("eslint src/")
    assert not VERIFICATION_COMMANDS.search("echo hello")


# --- compute_signals ---

def test_compute_signals_empty_trace():
    trace = FakeTrace()
    signals = compute_signals(trace)
    assert signals["signal.turn_count"] == 0
    assert signals["signal.efficiency_score"] == 1.0
    assert signals["signal.repair_count"] == 0
    assert signals["signal.repair_ratio"] == 0.0
    assert signals["signal.repetition_count"] == 0
    assert signals["signal.frustration_severity"] == 0
    assert signals["signal.positive_feedback"] == 0
    assert signals["signal.escalation_requested"] == 0
    assert signals["signal.tool_call_count"] == 0
    assert signals["signal.tool_failure_rate"] == 0.0
    assert signals["signal.verification_present"] == 0


def test_compute_signals_basic_session():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="Add a function", out="I'll add that function now."),
        FakeObs("SPAN", name="Edit", inp="src/utils.py"),
        FakeObs("SPAN", name="Bash", inp="pytest tests/"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.turn_count"] == 1
    assert signals["signal.tool_call_count"] == 2
    assert signals["signal.verification_present"] == 1


def test_compute_signals_repair_detection():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="i meant the other function"),
        FakeObs("GENERATION", inp="that's not what I asked"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.repair_count"] == 2
    assert signals["signal.repair_ratio"] == 1.0


def test_compute_signals_frustration():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="WHAT THE HELL ARE YOU DOING"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.frustration_severity"] == 3


def test_compute_signals_escalation():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="i give up, forget it"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.escalation_requested"] == 1


def test_compute_signals_tool_failure_rate():
    trace = FakeTrace([
        FakeObs("SPAN", name="Bash", inp="npm test", level="ERROR"),
        FakeObs("SPAN", name="Bash", inp="npm test"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.tool_failure_rate"] == 0.5


def test_compute_signals_verification_after_code_edit():
    trace = FakeTrace([
        FakeObs("SPAN", name="Edit", inp="src/app.ts"),
        FakeObs("SPAN", name="Bash", inp="npm test"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.verification_present"] == 1


def test_compute_signals_no_verification_after_non_code_edit():
    trace = FakeTrace([
        FakeObs("SPAN", name="Edit", inp="README.md"),
        FakeObs("SPAN", name="Bash", inp="echo done"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.verification_present"] == 0


def test_compute_signals_repetition_detection():
    trace = FakeTrace([
        FakeObs("GENERATION", out="I will now edit the file to fix the bug in the function"),
        FakeObs("GENERATION", out="I will now edit the file to fix the bug in the function"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.repetition_count"] >= 1


def test_compute_signals_positive_feedback():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="thank you, that's perfect"),
    ])
    signals = compute_signals(trace)
    assert signals["signal.positive_feedback"] >= 1


# --- _compute_overall_quality ---

def test_overall_quality_excellent():
    signals = {
        "signal.positive_feedback": 1,
        "signal.efficiency_score": 0.9,
        "signal.verification_present": 1,
        "signal.escalation_requested": 0,
        "signal.frustration_severity": 0,
        "signal.repetition_count": 0,
        "signal.turn_count": 3,
        "signal.repair_ratio": 0.0,
    }
    assert _compute_overall_quality(signals) == "Excellent"


def test_overall_quality_severe():
    signals = {
        "signal.escalation_requested": 1,
        "signal.frustration_severity": 0,
        "signal.repetition_count": 0,
        "signal.turn_count": 3,
        "signal.repair_ratio": 0.0,
        "signal.positive_feedback": 0,
        "signal.efficiency_score": 0.5,
        "signal.verification_present": 0,
    }
    assert _compute_overall_quality(signals) == "Severe"


def test_overall_quality_severe_from_frustration():
    signals = {
        "signal.escalation_requested": 0,
        "signal.frustration_severity": 3,
        "signal.repetition_count": 0,
        "signal.turn_count": 3,
        "signal.repair_ratio": 0.0,
        "signal.positive_feedback": 0,
        "signal.efficiency_score": 0.5,
        "signal.verification_present": 0,
    }
    assert _compute_overall_quality(signals) == "Severe"


def test_overall_quality_poor():
    signals = {
        "signal.escalation_requested": 0,
        "signal.frustration_severity": 2,
        "signal.repetition_count": 0,
        "signal.turn_count": 5,
        "signal.repair_ratio": 0.1,
        "signal.positive_feedback": 0,
        "signal.efficiency_score": 0.5,
        "signal.verification_present": 0,
    }
    assert _compute_overall_quality(signals) == "Poor"


def test_overall_quality_good():
    signals = {
        "signal.escalation_requested": 0,
        "signal.frustration_severity": 0,
        "signal.repetition_count": 0,
        "signal.turn_count": 4,
        "signal.repair_ratio": 0.1,
        "signal.positive_feedback": 0,
        "signal.efficiency_score": 0.7,
        "signal.verification_present": 0,
    }
    assert _compute_overall_quality(signals) == "Good"


def test_overall_quality_neutral():
    signals = {
        "signal.escalation_requested": 0,
        "signal.frustration_severity": 0,
        "signal.repetition_count": 0,
        "signal.turn_count": 6,
        "signal.repair_ratio": 0.2,
        "signal.positive_feedback": 0,
        "signal.efficiency_score": 0.5,
        "signal.verification_present": 0,
    }
    assert _compute_overall_quality(signals) == "Neutral"


# --- QUALITY_NUMERIC ---

def test_quality_numeric_mapping():
    assert QUALITY_NUMERIC["Severe"] == 1
    assert QUALITY_NUMERIC["Poor"] == 2
    assert QUALITY_NUMERIC["Neutral"] == 3
    assert QUALITY_NUMERIC["Good"] == 4
    assert QUALITY_NUMERIC["Excellent"] == 5


# --- Efficiency score ---

def test_efficiency_at_baseline():
    trace = FakeTrace([FakeObs("GENERATION", inp=f"msg{i}", out=f"resp{i}") for i in range(5)])
    signals = compute_signals(trace)
    assert signals["signal.efficiency_score"] == 1.0


def test_efficiency_degrades_above_baseline():
    trace = FakeTrace([FakeObs("GENERATION", inp=f"msg{i}", out=f"resp{i}") for i in range(10)])
    signals = compute_signals(trace)
    assert signals["signal.efficiency_score"] < 1.0
    assert signals["signal.efficiency_score"] > 0.0
