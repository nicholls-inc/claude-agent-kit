#!/usr/bin/env python3
"""Deterministic tests for scripts.state.read_json and scripts.state.write_json.

Replaces state-evals.sh. Uses pytest with tmp_path fixture.

Tests:
  - state read: missing file, empty path, corrupt file, empty file, valid JSON, creates parent dir
  - state write: creates file, roundtrip preserves fields, creates nested dir, accepts string data,
    fails on empty path, fails on empty content
  - concurrent safety: sequential writes last wins, file is valid JSON after rapid writes
"""

import json
import os
import sys

# Ensure repo root is importable
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.state import read_json, write_json


# ---- state read tests --------------------------------------------------------


class TestStateRead:
    """Tests for read_json."""

    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = read_json(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_empty_path_returns_empty_dict(self):
        result = read_json("")
        assert result == {}

    def test_corrupt_file_returns_empty_dict(self, tmp_path):
        corrupt = tmp_path / "corrupt.json"
        corrupt.write_text("not valid json at all")
        result = read_json(str(corrupt))
        assert result == {}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        empty = tmp_path / "empty.json"
        empty.write_text("")
        result = read_json(str(empty))
        assert result == {}

    def test_valid_json_preserves_content(self, tmp_path):
        valid = tmp_path / "valid.json"
        valid.write_text('{"hello":"world"}')
        result = read_json(str(valid))
        assert "hello" in result
        assert result["hello"] == "world"

    def test_creates_parent_directory(self, tmp_path):
        deep_path = tmp_path / "deep" / "nested" / "dir" / "file.json"
        read_json(str(deep_path))
        assert (tmp_path / "deep" / "nested" / "dir").is_dir()


# ---- state write tests -------------------------------------------------------


class TestStateWrite:
    """Tests for write_json."""

    def test_creates_file(self, tmp_path):
        target = str(tmp_path / "write-test.json")
        result = write_json(target, {"key": "value"})
        assert result is True
        assert os.path.isfile(target)

    def test_roundtrip_preserves_fields(self, tmp_path):
        target = str(tmp_path / "roundtrip.json")
        data = {"version": 1, "active": True, "planPath": ".agent-kit/plans/test.md"}
        write_json(target, data)
        output = read_json(target)
        assert "planPath" in output
        assert output["planPath"] == ".agent-kit/plans/test.md"
        assert output["active"] is True

    def test_creates_nested_directory(self, tmp_path):
        target = str(tmp_path / "new" / "dir" / "state.json")
        result = write_json(target, {"created": True})
        assert result is True
        assert os.path.isfile(target)

    def test_accepts_data_from_string(self, tmp_path):
        target = str(tmp_path / "string-test.json")
        result = write_json(target, '{"stdin":true}')
        assert result is True
        output = read_json(target)
        assert output.get("stdin") is True

    def test_fails_on_empty_path(self):
        result = write_json("", '{"bad":true}')
        assert result is False

    def test_fails_on_empty_content(self, tmp_path):
        target = str(tmp_path / "no-content.json")
        result = write_json(target, "")
        assert result is False


# ---- concurrent safety tests -------------------------------------------------


class TestConcurrentSafety:
    """Tests for sequential/concurrent write safety."""

    def test_sequential_writes_last_wins(self, tmp_path):
        target = str(tmp_path / "concurrent.json")
        write_json(target, '{"write":1}')
        write_json(target, '{"write":2}')
        output = read_json(target)
        assert output.get("write") == 2

    def test_file_is_valid_json_after_rapid_writes(self, tmp_path):
        target = str(tmp_path / "rapid.json")
        for i in range(10):
            write_json(target, json.dumps({"write": i}))
        output = read_json(target)
        # Should be a valid dict, not empty (which would mean corruption)
        assert isinstance(output, dict)
        assert "write" in output
        # Verify the raw file is parseable JSON
        with open(target, "r") as f:
            parsed = json.loads(f.read())
        assert isinstance(parsed, dict)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
