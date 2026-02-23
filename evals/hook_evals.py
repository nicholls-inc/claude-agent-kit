#!/usr/bin/env python3
"""Deterministic tests for hook-router behavioral contracts.

Replaces hook-evals.sh. Uses pytest with parametrized datasets from evals/datasets/.

Tests:
  - ULW detection (scripts.detect.detect_ulw)
  - PreToolUse blocking (scripts.hook_router.handle_pre_tool_use)
  - Prometheus write guard
  - SessionStart persona injection
  - Boulder resume injection
  - Stop continuation (ULW enabled blocks, all disabled allows, max blocks auto-disables,
    continuation disabled allows)
"""

import io
import json
import os
import sys

import pytest

# Ensure repo root is importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

DATASETS = os.path.join(ROOT_DIR, "evals", "datasets")

from scripts.detect import detect_ulw
from scripts.sanitize import HookInput
import scripts.hook_router as hook_router
from scripts.state import write_json


# ---- Dataset loading ----------------------------------------------------------


def _load_dataset(name):
    path = os.path.join(DATASETS, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_ulw_data = _load_dataset("ulw-triggers.json")
_pretool_data = _load_dataset("pretool-cases.json")
_hook_data = _load_dataset("hook-inputs.json")


# ---- ULW Detection Tests -----------------------------------------------------


class TestULWDetection:
    """Parametrized ULW keyword detection tests."""

    @pytest.mark.parametrize(
        "input_text,expect_match,note",
        [
            (case["input"], case["expect_match"], case["note"])
            for case in _ulw_data["cases"]
        ],
        ids=[case["note"] for case in _ulw_data["cases"]],
    )
    def test_ulw_detection(self, input_text, expect_match, note):
        result = detect_ulw(input_text)
        assert result is expect_match, (
            f"ULW: {note} (input={input_text!r}, expected={expect_match}, got={result})"
        )


# ---- Helper: capture stdout from hook handler --------------------------------


def _capture_stdout(func, *args, **kwargs):
    """Capture stdout output from a function call."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        func(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


def _make_hook_input(**kwargs):
    """Create a HookInput with given fields."""
    return HookInput(**kwargs)


# ---- PreToolUse Blocking Tests -----------------------------------------------


def _setup_runtime_state(tmp_path, persona):
    """Set up runtime state files with the given persona."""
    state_dir = tmp_path / ".agent-kit" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    runtime_file = str(state_dir / "runtime.local.json")
    runtime_data = {
        "version": 1,
        "sessions": {"global": {"activePersona": persona}},
    }
    write_json(runtime_file, runtime_data)
    return runtime_file


class TestPreToolUseBlocking:
    """Parametrized PreToolUse blocking tests."""

    @pytest.mark.parametrize(
        "tool_name,command,expect_block,note",
        [
            (case["tool_name"], case["command"], case["expect_block"], case["note"])
            for case in _pretool_data["cases"]
        ],
        ids=[case["note"] for case in _pretool_data["cases"]],
    )
    def test_pretool_standard_cases(self, tmp_path, monkeypatch, tool_name, command, expect_block, note):
        runtime_file = _setup_runtime_state(tmp_path, "sisyphus")
        boulder_file = str(tmp_path / ".agent-kit" / "boulder.json")
        ralph_file = str(tmp_path / ".agent-kit" / "ralph-loop.local.md")

        monkeypatch.setattr(hook_router, "RUNTIME_FILE", runtime_file)
        monkeypatch.setattr(hook_router, "BOULDER_FILE", boulder_file)
        monkeypatch.setattr(hook_router, "RALPH_FILE", ralph_file)

        hook_input = _make_hook_input(
            event="PreToolUse",
            tool_name=tool_name,
            tool_command=command,
        )
        output = _capture_stdout(hook_router.handle_pre_tool_use, hook_input)

        if expect_block:
            assert '"decision":"block"' in output, (
                f"PreToolUse: {note} (expected block, got: {output!r})"
            )
        else:
            assert '"decision":"block"' not in output, (
                f"PreToolUse: {note} (expected allow, got: {output!r})"
            )

    @pytest.mark.parametrize(
        "tool_name,command,expect_block,note",
        [
            (case["tool_name"], case["command"], case["expect_block"], case["note"])
            for case in _pretool_data["prometheus_cases"]
        ],
        ids=[case["note"] for case in _pretool_data["prometheus_cases"]],
    )
    def test_pretool_prometheus_cases(self, tmp_path, monkeypatch, tool_name, command, expect_block, note):
        runtime_file = _setup_runtime_state(tmp_path, "prometheus")
        boulder_file = str(tmp_path / ".agent-kit" / "boulder.json")
        ralph_file = str(tmp_path / ".agent-kit" / "ralph-loop.local.md")

        monkeypatch.setattr(hook_router, "RUNTIME_FILE", runtime_file)
        monkeypatch.setattr(hook_router, "BOULDER_FILE", boulder_file)
        monkeypatch.setattr(hook_router, "RALPH_FILE", ralph_file)

        hook_input = _make_hook_input(
            event="PreToolUse",
            tool_name=tool_name,
            tool_command=command,
        )
        output = _capture_stdout(hook_router.handle_pre_tool_use, hook_input)

        if expect_block:
            assert '"decision":"block"' in output, (
                f"Prometheus: {note} (expected block, got: {output!r})"
            )
        else:
            assert '"decision":"block"' not in output, (
                f"Prometheus: {note} (expected allow, got: {output!r})"
            )


# ---- SessionStart Persona Injection Tests ------------------------------------


class TestSessionStartPersona:
    """SessionStart persona injection tests from hook-inputs.json.

    The Python hook_router emits dynamic sections (tool selection, delegation
    tables, etc.) rather than the literal "Persona: X" text that the bash
    version used.  We verify that personas with dynamic sections produce
    non-empty output containing expected section headers, and that prometheus
    (which has no dynamic sections) produces empty output.
    """

    # Expected section markers per persona based on build_sections.py PERSONA_SECTIONS
    _PERSONA_MARKERS = {
        "sisyphus": "## Tool Selection",
        "hephaestus": "## Tool Selection",
        "atlas": "## Tool Selection",
        "prometheus": None,  # No dynamic sections
    }

    @pytest.mark.parametrize(
        "persona,expect_contains,note",
        [
            (case["persona"], case["expect_contains"], case["note"])
            for case in _hook_data["session_start"]["personas"]
        ],
        ids=[case["note"] for case in _hook_data["session_start"]["personas"]],
    )
    def test_persona_injection(self, tmp_path, monkeypatch, persona, expect_contains, note):
        runtime_file = _setup_runtime_state(tmp_path, persona)
        boulder_file = str(tmp_path / ".agent-kit" / "boulder.json")
        ralph_file = str(tmp_path / ".agent-kit" / "ralph-loop.local.md")

        monkeypatch.setattr(hook_router, "RUNTIME_FILE", runtime_file)
        monkeypatch.setattr(hook_router, "BOULDER_FILE", boulder_file)
        monkeypatch.setattr(hook_router, "RALPH_FILE", ralph_file)

        hook_input = _make_hook_input(event="SessionStart")
        output = _capture_stdout(hook_router.handle_session_start, hook_input)

        expected_marker = self._PERSONA_MARKERS.get(persona)
        if expected_marker is None:
            # Prometheus has no dynamic sections — output may be empty
            assert "## Tool Selection" not in output, (
                f"SessionStart: {note} (prometheus should have no dynamic sections)"
            )
        else:
            assert expected_marker in output, (
                f"SessionStart: {note} (expected {expected_marker!r} in dynamic sections output)"
            )


# ---- Boulder Resume Injection Tests -----------------------------------------


class TestBoulderResume:
    """Boulder resume injection tests from hook-inputs.json."""

    def test_boulder_resume_contains_plan_path(self, tmp_path, monkeypatch):
        boulder_cfg = _hook_data["session_start"]["boulder_resume"]
        expect_plan = boulder_cfg["expect_contains_plan_path"]
        expect_resume = boulder_cfg["expect_contains_resume"]

        # Set up runtime state with sisyphus persona
        runtime_file = _setup_runtime_state(tmp_path, "sisyphus")
        boulder_file = str(tmp_path / ".agent-kit" / "boulder.json")
        ralph_file = str(tmp_path / ".agent-kit" / "ralph-loop.local.md")

        # Write active boulder
        write_json(boulder_file, boulder_cfg["boulder_json"])

        monkeypatch.setattr(hook_router, "RUNTIME_FILE", runtime_file)
        monkeypatch.setattr(hook_router, "BOULDER_FILE", boulder_file)
        monkeypatch.setattr(hook_router, "RALPH_FILE", ralph_file)

        hook_input = _make_hook_input(event="SessionStart")
        output = _capture_stdout(hook_router.handle_session_start, hook_input)

        assert expect_plan in output, (
            f"Boulder resume: expected plan path {expect_plan!r} in output"
        )
        assert expect_resume in output, (
            f"Boulder resume: expected {expect_resume!r} in output"
        )


# ---- Stop Continuation Tests -------------------------------------------------


class TestStopContinuation:
    """Stop handler tests from hook-inputs.json stop cases."""

    def _setup_stop(self, tmp_path, monkeypatch, runtime_json):
        """Set up state files for stop tests."""
        state_dir = tmp_path / ".agent-kit" / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        runtime_file = str(state_dir / "runtime.local.json")
        boulder_file = str(tmp_path / ".agent-kit" / "boulder.json")
        ralph_file = str(tmp_path / ".agent-kit" / "ralph-loop.local.md")

        write_json(runtime_file, runtime_json)

        # Ensure no boulder or ralph active
        if os.path.exists(boulder_file):
            os.unlink(boulder_file)
        if os.path.exists(ralph_file):
            os.unlink(ralph_file)

        monkeypatch.setattr(hook_router, "RUNTIME_FILE", runtime_file)
        monkeypatch.setattr(hook_router, "BOULDER_FILE", boulder_file)
        monkeypatch.setattr(hook_router, "RALPH_FILE", ralph_file)

    def test_ulw_enabled_blocks_stop(self, tmp_path, monkeypatch):
        case = _hook_data["stop"]["ulw_enabled"]
        self._setup_stop(tmp_path, monkeypatch, case["runtime_json"])

        hook_input = _make_hook_input(event="Stop")
        output = _capture_stdout(hook_router.handle_stop, hook_input)

        assert case["expect_block"] is True
        assert '"decision":"block"' in output, (
            f"Stop: {case['note']} (expected block, got: {output!r})"
        )

    def test_all_disabled_allows_stop(self, tmp_path, monkeypatch):
        case = _hook_data["stop"]["all_disabled"]
        self._setup_stop(tmp_path, monkeypatch, case["runtime_json"])

        hook_input = _make_hook_input(event="Stop")
        output = _capture_stdout(hook_router.handle_stop, hook_input)

        assert '"decision":"block"' not in output, (
            f"Stop: {case['note']} (expected allow, got: {output!r})"
        )

    def test_max_blocks_reached_auto_disables(self, tmp_path, monkeypatch):
        case = _hook_data["stop"]["max_blocks_reached"]
        self._setup_stop(tmp_path, monkeypatch, case["runtime_json"])

        hook_input = _make_hook_input(event="Stop")
        output = _capture_stdout(hook_router.handle_stop, hook_input)

        assert '"decision":"block"' not in output, (
            f"Stop: {case['note']} (expected allow after max blocks, got: {output!r})"
        )

    def test_continuation_disabled_allows_stop(self, tmp_path, monkeypatch):
        case = _hook_data["stop"]["continuation_disabled"]
        self._setup_stop(tmp_path, monkeypatch, case["runtime_json"])

        hook_input = _make_hook_input(event="Stop")
        output = _capture_stdout(hook_router.handle_stop, hook_input)

        assert '"decision":"block"' not in output, (
            f"Stop: {case['note']} (expected allow when disabled, got: {output!r})"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
