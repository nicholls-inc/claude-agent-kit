"""Tests for persona-trace-analyzer.py — pure scoring functions."""

import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

mod = importlib.import_module("persona-trace-analyzer")

extract_tool_sequence = mod.extract_tool_sequence
get_trace_persona = mod.get_trace_persona
score_sisyphus = mod.score_sisyphus
score_hephaestus = mod.score_hephaestus
score_prometheus = mod.score_prometheus
score_atlas = mod.score_atlas
PERSONA_SCORERS = mod.PERSONA_SCORERS


# --- Helpers ---

def tool(name, inp="", out="", level=None):
    return {"name": name, "input": inp, "output": out, "level": level}


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
        self.id = "test-trace-001"


# --- extract_tool_sequence ---

def test_extract_tool_sequence_filters_spans():
    trace = FakeTrace([
        FakeObs("SPAN", name="Read", inp="file.py", start_time="2026-01-01T00:00:01Z"),
        FakeObs("GENERATION", name="gen", inp="hello", start_time="2026-01-01T00:00:00Z"),
        FakeObs("SPAN", name="Edit", inp="file.py", start_time="2026-01-01T00:00:02Z"),
    ])
    tools = extract_tool_sequence(trace)
    assert len(tools) == 2
    assert tools[0]["name"] == "Read"
    assert tools[1]["name"] == "Edit"


def test_extract_tool_sequence_empty():
    trace = FakeTrace()
    tools = extract_tool_sequence(trace)
    assert tools == []


# --- get_trace_persona ---

def test_get_trace_persona_from_metadata():
    trace = FakeTrace(metadata={"persona": "sisyphus"})
    assert get_trace_persona(trace) == "sisyphus"


def test_get_trace_persona_from_hook_persona():
    trace = FakeTrace(metadata={"hook.persona": "atlas"})
    assert get_trace_persona(trace) == "atlas"


def test_get_trace_persona_unknown():
    trace = FakeTrace(metadata={})
    assert get_trace_persona(trace) == "unknown"


# --- score_sisyphus ---

def test_sisyphus_good_workflow():
    tools = [
        tool("Glob", inp="**/*.ts"),
        tool("Read", inp="src/app.ts"),
        tool("Task", inp="explore: find related files"),
        tool("Edit", inp="src/app.ts"),
        tool("Bash", inp="npm test"),
    ]
    scores = score_sisyphus(tools)
    assert scores["sisyphus.workflow_sequence"] == 1
    assert scores["sisyphus.parallel_exploration"] == 1
    assert scores["sisyphus.verification_present"] == 1
    assert scores["sisyphus.no_nested_orchestration"] == 1


def test_sisyphus_no_exploration_before_edit():
    tools = [
        tool("Edit", inp="src/app.ts"),
    ]
    scores = score_sisyphus(tools)
    assert scores["sisyphus.workflow_sequence"] == 0


def test_sisyphus_no_task_calls():
    tools = [
        tool("Read", inp="src/app.ts"),
        tool("Edit", inp="src/app.ts"),
    ]
    scores = score_sisyphus(tools)
    assert scores["sisyphus.parallel_exploration"] == 0


def test_sisyphus_no_verification():
    tools = [
        tool("Read", inp="src/app.ts"),
        tool("Edit", inp="src/app.ts"),
    ]
    scores = score_sisyphus(tools)
    assert scores["sisyphus.verification_present"] == 0


def test_sisyphus_nested_orchestration():
    tools = [
        tool("Read", inp="src/app.ts"),
        tool("Task", inp="launch sisyphus to handle this"),
        tool("Edit", inp="src/app.ts"),
    ]
    scores = score_sisyphus(tools)
    assert scores["sisyphus.no_nested_orchestration"] == 0


# --- score_hephaestus ---

def test_hephaestus_good_session():
    tools = [
        tool("Edit", inp="src/fix.ts"),
        tool("Bash", inp="npm test", level="ERROR"),
        tool("Edit", inp="src/fix.ts"),
        tool("Bash", inp="npm test"),
        tool("Bash", inp="tsc --noEmit"),
    ]
    scores = score_hephaestus(tools)
    assert scores["hephaestus.execution_depth"] == 2
    assert scores["hephaestus.verification_depth"] == 2  # test + typecheck
    assert scores["hephaestus.retry_quality"] == 1
    assert scores["hephaestus.persistence"] == 1


def test_hephaestus_no_edits():
    tools = [
        tool("Read", inp="src/file.ts"),
    ]
    scores = score_hephaestus(tools)
    assert scores["hephaestus.execution_depth"] == 0
    assert scores["hephaestus.persistence"] == 0


def test_hephaestus_nested_orchestration():
    tools = [
        tool("Task", inp="run hephaestus agent"),
    ]
    scores = score_hephaestus(tools)
    assert scores["hephaestus.no_nested_orchestration"] == 0


def test_hephaestus_retry_quality_bad():
    tools = [
        tool("Bash", inp="npm test", level="ERROR"),
        tool("Glob", inp="**/*.ts"),  # random exploration instead of fix
    ]
    scores = score_hephaestus(tools)
    assert scores["hephaestus.retry_quality"] == 0


def test_hephaestus_verification_types():
    tools = [
        tool("Bash", inp="npm test"),
        tool("Bash", inp="tsc --noEmit"),
        tool("Bash", inp="npm run build"),
        tool("Bash", inp="eslint src/"),
    ]
    scores = score_hephaestus(tools)
    assert scores["hephaestus.verification_depth"] == 4  # test, typecheck, build, lint


# --- score_prometheus ---

def test_prometheus_good_plan():
    tools = [
        tool("Read", inp="src/app.ts"),
        tool("Write", inp=".agent-kit/plans/feature.md", out="# Plan\n\n- [ ] Task 1\n- [ ] Task 2"),
    ]
    scores = score_prometheus(tools)
    assert scores["prometheus.plan_produced"] == 1
    assert scores["prometheus.no_code_edits"] == 1
    assert scores["prometheus.artifact_location"] == 1
    assert scores["prometheus.checklist_format"] == 1


def test_prometheus_code_edit_violation():
    tools = [
        tool("Edit", inp="src/app.ts"),
    ]
    scores = score_prometheus(tools)
    assert scores["prometheus.no_code_edits"] == 0


def test_prometheus_no_plan_produced():
    tools = [
        tool("Read", inp="src/app.ts"),
    ]
    scores = score_prometheus(tools)
    assert scores["prometheus.plan_produced"] == 0


def test_prometheus_write_outside_agent_kit():
    tools = [
        tool("Write", inp="src/new-file.ts", out="code"),
    ]
    scores = score_prometheus(tools)
    assert scores["prometheus.artifact_location"] == 0


def test_prometheus_no_checklist():
    tools = [
        tool("Write", inp=".agent-kit/plans/plan.md", out="Just some text without checklist items"),
    ]
    scores = score_prometheus(tools)
    assert scores["prometheus.checklist_format"] == 0


# --- score_atlas ---

def test_atlas_good_session():
    tools = [
        tool("Read", inp=".agent-kit/boulder.json"),
        tool("Read", inp="src/file.ts"),
        tool("Edit", inp="src/file.ts", out="- [x] Task 1"),
        tool("Bash", inp="npm test"),
        tool("Write", inp=".agent-kit/boulder.json"),
    ]
    scores = score_atlas(tools)
    assert scores["atlas.boulder_read"] == 1
    assert scores["atlas.task_advancement"] == 1
    assert scores["atlas.verification_before_done"] == 1
    assert scores["atlas.bounded_continuation"] == 1
    assert scores["atlas.single_slice_focus"] == 1


def test_atlas_no_boulder_read():
    tools = [
        tool("Read", inp="src/file.ts"),
        tool("Edit", inp="src/file.ts"),
    ]
    scores = score_atlas(tools)
    assert scores["atlas.boulder_read"] == 0


def test_atlas_too_many_boulder_reads():
    tools = [
        tool("Read", inp=".agent-kit/boulder.json"),
        tool("Read", inp=".agent-kit/boulder.json"),
        tool("Read", inp=".agent-kit/boulder.json"),
        tool("Read", inp=".agent-kit/boulder.json"),
    ]
    scores = score_atlas(tools)
    assert scores["atlas.single_slice_focus"] == 0


def test_atlas_excessive_tools():
    tools = [tool("Read", inp="file.ts") for _ in range(101)]
    scores = score_atlas(tools)
    assert scores["atlas.bounded_continuation"] == 0


# --- PERSONA_SCORERS ---

def test_persona_scorers_contains_all():
    assert "sisyphus" in PERSONA_SCORERS
    assert "hephaestus" in PERSONA_SCORERS
    assert "prometheus" in PERSONA_SCORERS
    assert "atlas" in PERSONA_SCORERS
    assert len(PERSONA_SCORERS) == 4
