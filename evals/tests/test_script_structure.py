#!/usr/bin/env python3
"""Validates Python eval script structure and conventions.

Replaces test_bash_scripts.sh. Checks:
  - run_evals.py references hook_evals, state_evals, prompt_regression
  - run_judges.py references judge-persona.py, session-signals.py, persona-trace-analyzer.py
  - All referenced scripts exist
  - Eval Python scripts have correct shebang
  - Dataset JSON files are valid
  - Persona example datasets have trace_id and tool_calls
"""

import json
import os
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVALS_DIR = os.path.join(ROOT_DIR, "evals")
JUDGES_DIR = os.path.join(EVALS_DIR, "llm-judge")
DATASETS_DIR = os.path.join(EVALS_DIR, "datasets")
PERSONA_EXAMPLES_DIR = os.path.join(DATASETS_DIR, "persona-examples")


def _read_file(path):
    """Read file content as string."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---- run_evals.py tests ------------------------------------------------------


class TestRunEvals:
    """Tests for run_evals.py structure."""

    @pytest.fixture(autouse=True)
    def _paths(self):
        self.script_path = os.path.join(EVALS_DIR, "run_evals.py")
        self.content = _read_file(self.script_path)

    def test_exists(self):
        assert os.path.isfile(self.script_path), "run_evals.py not found"

    def test_references_hook_evals(self):
        assert "hook_evals" in self.content, "run_evals.py missing hook_evals reference"

    def test_references_state_evals(self):
        assert "state_evals" in self.content, "run_evals.py missing state_evals reference"

    def test_references_prompt_regression(self):
        assert "prompt_regression" in self.content, "run_evals.py missing prompt_regression reference"

    def test_correct_shebang(self):
        assert self.content.startswith("#!/usr/bin/env python3"), (
            "run_evals.py has incorrect shebang"
        )


# ---- run_judges.py tests -----------------------------------------------------


class TestRunJudges:
    """Tests for run_judges.py structure."""

    @pytest.fixture(autouse=True)
    def _paths(self):
        self.script_path = os.path.join(JUDGES_DIR, "run_judges.py")
        self.content = _read_file(self.script_path)

    def test_exists(self):
        assert os.path.isfile(self.script_path), "run_judges.py not found"

    def test_references_judge_persona(self):
        assert "judge-persona.py" in self.content, (
            "run_judges.py missing judge-persona.py reference"
        )

    def test_references_session_signals(self):
        assert "session-signals.py" in self.content, (
            "run_judges.py missing session-signals.py reference"
        )

    def test_references_persona_trace_analyzer(self):
        assert "persona-trace-analyzer.py" in self.content, (
            "run_judges.py missing persona-trace-analyzer.py reference"
        )

    def test_correct_shebang(self):
        assert self.content.startswith("#!/usr/bin/env python3"), (
            "run_judges.py has incorrect shebang"
        )

    def test_supports_dry_run(self):
        assert "--dry-run" in self.content, "run_judges.py missing --dry-run support"

    def test_supports_days(self):
        assert "--days" in self.content, "run_judges.py missing --days support"


# ---- Referenced scripts exist ------------------------------------------------


class TestReferencedScriptsExist:
    """Verify all referenced scripts actually exist on disk."""

    @pytest.mark.parametrize("script_name", [
        "hook_evals.py",
        "state_evals.py",
        "prompt_regression.py",
    ])
    def test_eval_script_exists(self, script_name):
        path = os.path.join(EVALS_DIR, script_name)
        assert os.path.isfile(path), f"Referenced script {script_name} missing"

    @pytest.mark.parametrize("script_name", [
        "session-signals.py",
        "persona-trace-analyzer.py",
    ])
    def test_evals_python_script_exists(self, script_name):
        path = os.path.join(EVALS_DIR, script_name)
        assert os.path.isfile(path), f"Referenced script {script_name} missing"

    @pytest.mark.parametrize("script_name", [
        "judge-persona.py",
    ])
    def test_judge_script_exists(self, script_name):
        path = os.path.join(JUDGES_DIR, script_name)
        assert os.path.isfile(path), f"Referenced judge {script_name} missing"


# ---- Shebang checks for all eval Python scripts -----------------------------


class TestEvalScriptShebangs:
    """All eval Python scripts have the correct shebang."""

    @pytest.mark.parametrize("script_path", [
        os.path.join(EVALS_DIR, "run_evals.py"),
        os.path.join(EVALS_DIR, "hook_evals.py"),
        os.path.join(EVALS_DIR, "state_evals.py"),
        os.path.join(EVALS_DIR, "prompt_regression.py"),
        os.path.join(JUDGES_DIR, "run_judges.py"),
    ])
    def test_shebang(self, script_path):
        basename = os.path.basename(script_path)
        content = _read_file(script_path)
        assert content.startswith("#!/usr/bin/env python3"), (
            f"{basename}: incorrect or missing shebang"
        )


# ---- Dataset JSON integrity --------------------------------------------------


class TestDatasetIntegrity:
    """Validate all dataset JSON files."""

    @pytest.fixture(autouse=True)
    def _collect_datasets(self):
        self.datasets = []
        if os.path.isdir(DATASETS_DIR):
            for fname in os.listdir(DATASETS_DIR):
                if fname.endswith(".json"):
                    self.datasets.append(os.path.join(DATASETS_DIR, fname))

    @pytest.mark.parametrize("dataset_path", [
        os.path.join(DATASETS_DIR, f)
        for f in sorted(os.listdir(DATASETS_DIR))
        if f.endswith(".json")
    ] if os.path.isdir(DATASETS_DIR) else [])
    def test_dataset_is_valid_json(self, dataset_path):
        basename = os.path.basename(dataset_path)
        with open(dataset_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"dataset {basename} is invalid JSON: {e}")
        assert data is not None, f"dataset {basename} parsed to None"


# ---- Persona example dataset structure ---------------------------------------


class TestPersonaExamples:
    """Persona example datasets have required fields."""

    @pytest.mark.parametrize("example_path", [
        os.path.join(PERSONA_EXAMPLES_DIR, f)
        for f in sorted(os.listdir(PERSONA_EXAMPLES_DIR))
        if f.endswith(".json")
    ] if os.path.isdir(PERSONA_EXAMPLES_DIR) else [])
    def test_has_trace_id(self, example_path):
        basename = os.path.basename(example_path)
        with open(example_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "trace_id" in data, f"persona example {basename} missing trace_id"

    @pytest.mark.parametrize("example_path", [
        os.path.join(PERSONA_EXAMPLES_DIR, f)
        for f in sorted(os.listdir(PERSONA_EXAMPLES_DIR))
        if f.endswith(".json")
    ] if os.path.isdir(PERSONA_EXAMPLES_DIR) else [])
    def test_has_tool_calls(self, example_path):
        basename = os.path.basename(example_path)
        with open(example_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "tool_calls" in data, f"persona example {basename} missing tool_calls"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
