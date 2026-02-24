"""Tests for LLM judge modules — pure logic functions (no API calls)."""

import sys
import importlib
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm-judge"))

langfuse_stub = types.ModuleType("langfuse")
langfuse_stub.Langfuse = type("Langfuse", (), {})
sys.modules["langfuse"] = langfuse_stub

anthropic_stub = types.ModuleType("anthropic")
anthropic_stub.Anthropic = type("Anthropic", (), {})
sys.modules["anthropic"] = anthropic_stub

judge_persona = importlib.import_module("judge-persona")
judge_plan = importlib.import_module("judge-plan")
judge_search = importlib.import_module("judge-search")
judge_oracle = importlib.import_module("judge-oracle")


# --- Helpers ---

class FakeObs:
    def __init__(self, obs_type, name="", inp="", out="", level=None, start_time=""):
        self.type = obs_type
        self.name = name
        self.input = inp
        self.output = out
        self.level = level
        self.start_time = start_time


class FakeTrace:
    def __init__(self, observations=None, metadata=None):
        self.observations = observations or []
        self.metadata = metadata or {}
        self.id = "test-trace"


# ─── judge-persona.py ─────────────────────────────────────────────

def test_persona_dimensions_all_personas():
    for persona in ["sisyphus", "hephaestus", "prometheus", "atlas"]:
        dims = judge_persona.PERSONA_DIMENSIONS[persona]
        assert len(dims) > 0
        assert "tool_usage_discipline" in dims
        assert "failure_handling" in dims


def test_persona_valid_personas():
    assert judge_persona.VALID_PERSONAS == {"sisyphus", "hephaestus", "prometheus", "atlas"}


def test_persona_load_rubric():
    for persona in ["sisyphus", "hephaestus", "prometheus", "atlas"]:
        rubric = judge_persona.load_rubric(persona)
        assert len(rubric) > 0


def test_persona_extract_trace_context():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="Add a feature", out="I'll do that", start_time="2026-01-01T00:00:00Z"),
        FakeObs("SPAN", name="Edit", inp="src/app.ts", out="edited", start_time="2026-01-01T00:00:01Z"),
    ])
    context = judge_persona.extract_trace_context(trace)
    assert "[USER INPUT]" in context
    assert "[ASSISTANT OUTPUT]" in context
    assert "[TOOL: Edit]" in context


def test_persona_extract_trace_context_empty():
    trace = FakeTrace()
    context = judge_persona.extract_trace_context(trace)
    assert context == ""


def test_persona_truncate():
    short = judge_persona._truncate("hello", 100)
    assert short == "hello"

    long_text = "a" * 200
    truncated = judge_persona._truncate(long_text, 50)
    assert len(truncated) < 200
    assert "truncated" in truncated


def test_persona_get_trace_persona():
    trace = FakeTrace(metadata={"persona": "atlas"})
    assert judge_persona.get_trace_persona(trace) == "atlas"


# ─── judge-plan.py ─────────────────────────────────────────────────

def test_plan_dimensions():
    assert "structure" in judge_plan.DIMENSIONS
    assert "task_granularity" in judge_plan.DIMENSIONS
    assert "verifiability" in judge_plan.DIMENSIONS
    assert "actionability" in judge_plan.DIMENSIONS
    assert "scope_discipline" in judge_plan.DIMENSIONS
    assert len(judge_plan.DIMENSIONS) == 5


def test_plan_load_rubric():
    rubric = judge_plan.load_rubric()
    assert len(rubric) > 0


def test_plan_print_result(capsys):
    result = {
        "overall_score": 4,
        "summary": "Good plan",
        "scores": {"structure": 5, "scope_discipline": 3},
        "reasoning": {"structure": "Well organized", "scope_discipline": "Some scope creep"},
    }
    judge_plan.print_result(result, "Test Plan")
    captured = capsys.readouterr()
    assert "Test Plan" in captured.out
    assert "4" in captured.out
    assert "Good plan" in captured.out


# ─── judge-search.py ──────────────────────────────────────────────

def test_search_compute_automated_scores_empty():
    scores = judge_search.compute_automated_scores([])
    assert scores["explore.path_format"] == 1  # vacuously true
    assert scores["explore.output_structure"] == 0
    assert scores["explore.parallel_execution"] == 0


def test_search_compute_automated_scores_absolute_paths():
    tool_calls = [
        {"name": "Glob", "output": "/Users/test/src/app.ts\n/Users/test/src/util.ts"},
    ]
    scores = judge_search.compute_automated_scores(tool_calls)
    assert scores["explore.path_format"] == 1


def test_search_compute_automated_scores_only_absolute_detected():
    # Function only detects lines starting with / as paths;
    # relative paths like src/app.ts are not counted at all
    tool_calls = [
        {"name": "Glob", "output": "src/app.ts\n/abs/path.ts"},
    ]
    scores = judge_search.compute_automated_scores(tool_calls)
    # Only /abs/path.ts is detected as a path, and it's absolute → passes
    assert scores["explore.path_format"] == 1


def test_search_compute_automated_scores_structured_output():
    tool_calls = [
        {"name": "Read", "output": "Found the following files:\nresult: success"},
    ]
    scores = judge_search.compute_automated_scores(tool_calls)
    assert scores["explore.output_structure"] == 1


def test_search_compute_automated_scores_parallel():
    tool_calls = [
        {"name": "Glob", "output": "file1"},
        {"name": "Grep", "output": "file2"},
        {"name": "Read", "output": "file3"},
    ]
    scores = judge_search.compute_automated_scores(tool_calls)
    assert scores["explore.parallel_execution"] == 1


def test_search_compute_automated_scores_not_enough_parallel():
    tool_calls = [
        {"name": "Glob", "output": "file1"},
        {"name": "Read", "output": "file2"},
    ]
    scores = judge_search.compute_automated_scores(tool_calls)
    assert scores["explore.parallel_execution"] == 0


def test_search_extract_search_context():
    trace = FakeTrace([
        FakeObs("GENERATION", inp="find auth files", out="Searching for auth", start_time="2026-01-01T00:00:00Z"),
        FakeObs("SPAN", name="Glob", inp="**/*auth*", out="src/auth.ts", start_time="2026-01-01T00:00:01Z"),
    ])
    context, tool_calls = judge_search.extract_search_context(trace)
    assert "[QUERY]" in context
    assert "[TOOL: Glob]" in context
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "Glob"


# ─── judge-oracle.py ──────────────────────────────────────────────

def test_oracle_compute_automated_scores_effort_tag():
    scores = judge_oracle.compute_automated_scores("## Bottom Line\nThis is a Medium effort refactor.")
    assert scores["oracle.effort_tag_present"] == 1


def test_oracle_compute_automated_scores_no_effort_tag():
    scores = judge_oracle.compute_automated_scores("This is just regular text without tags.")
    assert scores["oracle.effort_tag_present"] == 0


def test_oracle_compute_automated_scores_verbose():
    # More than 5 sentences in first paragraph
    verbose = ". ".join(["Sentence"] * 8) + "."
    scores = judge_oracle.compute_automated_scores(verbose)
    assert scores["oracle.verbosity_compliance"] == 0


def test_oracle_compute_automated_scores_concise():
    concise = "This is concise. Two sentences."
    scores = judge_oracle.compute_automated_scores(concise)
    assert scores["oracle.verbosity_compliance"] == 1


def test_oracle_compute_automated_scores_too_many_steps():
    many_steps = "\n".join([f"{i}. Step {i}" for i in range(1, 9)])
    scores = judge_oracle.compute_automated_scores(many_steps)
    assert scores["oracle.verbosity_compliance"] == 0


def test_oracle_extract_oracle_response():
    trace = FakeTrace([
        FakeObs("GENERATION", out="Bottom line: refactor the auth module", start_time="2026-01-01T00:00:00Z"),
        FakeObs("GENERATION", out="Steps: 1. Extract interface", start_time="2026-01-01T00:00:01Z"),
    ])
    response = judge_oracle.extract_oracle_response(trace)
    assert "Bottom line" in response
    assert "Extract interface" in response


def test_oracle_extract_oracle_response_empty():
    trace = FakeTrace()
    response = judge_oracle.extract_oracle_response(trace)
    assert response == ""


def test_oracle_effort_tags_all_levels():
    for tag in ["Quick", "Short", "Medium", "Large"]:
        assert judge_oracle.EFFORT_TAGS.search(f"This is a {tag} task")
