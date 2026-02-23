#!/usr/bin/env python3
"""Pure-Python validation test suite for the claude-agent-kit plugin structure.

Replaces tests/validate.sh. Run with:
    pytest tests/test_validate.py -v

Validates:
  - Agent frontmatter (agents/*.md)
  - Skill frontmatter (skills/*/SKILL.md)
  - Hooks JSON schema (hooks/hooks.json)
  - Python script syntax (scripts/*.py)
  - Cross-reference integrity (docs/agent-mapping.md <-> agents/)
  - Agent metadata fields (category, costTier)
  - Persona switch detection (scripts/detect.py)
"""

import glob
import json
import os
import py_compile
import re
import sys

import pytest

# ---------------------------------------------------------------------------
# Setup: paths and imports
# ---------------------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add scripts/ to sys.path so we can import project modules.
_scripts_dir = os.path.join(ROOT_DIR, "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from build_sections import parse_frontmatter  # noqa: E402
from detect import detect_persona_switch  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_MODELS = {"haiku", "sonnet", "opus"}
VALID_CATEGORIES = {"persona", "search", "research", "advisor", "reviewer", "preplanning"}
VALID_COST_TIERS = {"free", "cheap", "moderate", "expensive"}
VALID_HOOK_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "Stop",
    "PostToolUse",
    "PostToolUseFailure",
    "Notification",
    "SubagentStop",
    "SubagentTool",
    "PermissionRequest",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENTS_DIR = os.path.join(ROOT_DIR, "agents")
SKILLS_DIR = os.path.join(ROOT_DIR, "skills")
HOOKS_FILE = os.path.join(ROOT_DIR, "hooks", "hooks.json")
MAPPING_FILE = os.path.join(ROOT_DIR, "docs", "agent-mapping.md")


def _agent_files():
    """Return list of absolute paths to agents/*.md files."""
    pattern = os.path.join(AGENTS_DIR, "*.md")
    return sorted(glob.glob(pattern))


def _skill_files():
    """Return list of absolute paths to skills/*/SKILL.md files."""
    pattern = os.path.join(SKILLS_DIR, "*", "SKILL.md")
    return sorted(glob.glob(pattern))


def _python_scripts():
    """Return list of absolute paths to scripts/*.py files."""
    pattern = os.path.join(ROOT_DIR, "scripts", "*.py")
    return sorted(glob.glob(pattern))


def _skill_dirs():
    """Return list of absolute paths to skills/*/ directories."""
    entries = []
    if os.path.isdir(SKILLS_DIR):
        for name in sorted(os.listdir(SKILLS_DIR)):
            full = os.path.join(SKILLS_DIR, name)
            if os.path.isdir(full):
                entries.append(full)
    return entries


def _has_frontmatter(filepath):
    """Check whether a file has at least two '---' delimiter lines."""
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "---":
                count += 1
    return count >= 2


def _get_body(filepath):
    """Return the body text after the second '---' delimiter."""
    lines = []
    delimiter_count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "---":
                delimiter_count += 1
                continue
            if delimiter_count >= 2:
                lines.append(line)
    return "".join(lines)


def _rel(filepath):
    """Return the path relative to ROOT_DIR."""
    return os.path.relpath(filepath, ROOT_DIR)


# ---------------------------------------------------------------------------
# Agent frontmatter tests
# ---------------------------------------------------------------------------

_AGENT_FILES = _agent_files()


@pytest.mark.parametrize("agent_file", _AGENT_FILES, ids=[os.path.basename(f) for f in _AGENT_FILES])
class TestAgentFrontmatter:
    """Validate agents/*.md frontmatter and structure."""

    def test_has_frontmatter_delimiters(self, agent_file):
        assert _has_frontmatter(agent_file), (
            f"{_rel(agent_file)}: missing frontmatter delimiters (---)"
        )

    @pytest.mark.parametrize("field", ["name", "description", "model", "tools", "maxTurns"])
    def test_required_field_present(self, agent_file, field):
        fm = parse_frontmatter(agent_file)
        assert fm.get(field), (
            f"{_rel(agent_file)}: missing required field '{field}'"
        )

    def test_model_is_valid(self, agent_file):
        fm = parse_frontmatter(agent_file)
        model = fm.get("model", "")
        assert model.lower() in VALID_MODELS, (
            f"{_rel(agent_file)}: model '{model}' is not one of {VALID_MODELS}"
        )

    def test_max_turns_is_positive_integer(self, agent_file):
        fm = parse_frontmatter(agent_file)
        max_turns = fm.get("maxTurns", "")
        assert re.fullmatch(r"[1-9][0-9]*", max_turns), (
            f"{_rel(agent_file)}: maxTurns '{max_turns}' is not a positive integer"
        )

    def test_body_is_non_empty(self, agent_file):
        body = _get_body(agent_file)
        assert body.strip(), (
            f"{_rel(agent_file)}: body is empty"
        )


# ---------------------------------------------------------------------------
# Skill frontmatter tests
# ---------------------------------------------------------------------------

_SKILL_FILES = _skill_files()


@pytest.mark.parametrize("skill_file", _SKILL_FILES, ids=[_rel(f) for f in _SKILL_FILES])
class TestSkillFrontmatter:
    """Validate skills/*/SKILL.md frontmatter."""

    def test_has_frontmatter_delimiters(self, skill_file):
        assert _has_frontmatter(skill_file), (
            f"{_rel(skill_file)}: missing frontmatter delimiters (---)"
        )

    @pytest.mark.parametrize("field", ["name", "description"])
    def test_required_field_present(self, skill_file, field):
        fm = parse_frontmatter(skill_file)
        assert fm.get(field), (
            f"{_rel(skill_file)}: missing required field '{field}'"
        )

    def test_agent_ref_exists(self, skill_file):
        """If an 'agent' field is present, the referenced agent file must exist."""
        fm = parse_frontmatter(skill_file)
        agent_ref = fm.get("agent")
        if not agent_ref:
            pytest.skip("no agent field")
        agent_lower = agent_ref.lower()
        expected_path = os.path.join(AGENTS_DIR, f"{agent_lower}.md")
        assert os.path.isfile(expected_path), (
            f"{_rel(skill_file)}: agent ref '{agent_ref}' -> agents/{agent_lower}.md not found"
        )

    def test_context_fork_requires_agent(self, skill_file):
        """If context=fork, the 'agent' field must be present."""
        fm = parse_frontmatter(skill_file)
        context_val = fm.get("context", "")
        if context_val != "fork":
            pytest.skip("context is not fork")
        assert fm.get("agent"), (
            f"{_rel(skill_file)}: context=fork but no agent field"
        )

    def test_model_is_valid_if_present(self, skill_file):
        """If a 'model' field is present, it must be a valid model."""
        fm = parse_frontmatter(skill_file)
        model = fm.get("model")
        if not model:
            pytest.skip("no model field")
        assert model.lower() in VALID_MODELS, (
            f"{_rel(skill_file)}: model '{model}' is not one of {VALID_MODELS}"
        )


# ---------------------------------------------------------------------------
# Hooks validation tests
# ---------------------------------------------------------------------------

class TestHooksValidation:
    """Validate hooks/hooks.json structure and references."""

    def test_hooks_file_exists(self):
        assert os.path.isfile(HOOKS_FILE), "hooks/hooks.json: file not found"

    def test_valid_json(self):
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            json.load(f)  # Raises on invalid JSON

    def test_has_hooks_key(self):
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "hooks" in data, "hooks.json: missing 'hooks' top-level key"

    def test_hooks_is_dict(self):
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data.get("hooks"), dict), (
            "hooks.json: 'hooks' is not a record (expected object keyed by event name)"
        )

    def test_event_names_are_valid(self):
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
        for event_name in hooks:
            assert event_name in VALID_HOOK_EVENTS, (
                f"hooks.json: event '{event_name}' is not a known hook event"
            )

    def test_matchers_are_arrays(self):
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
        for event_name, matchers in hooks.items():
            assert isinstance(matchers, list), (
                f"hooks.json: event '{event_name}': value must be an array of matcher objects"
            )

    def test_matcher_structure(self):
        """Each matcher must be a dict containing a 'hooks' array of hook definitions."""
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
        for event_name, matchers in hooks.items():
            if not isinstance(matchers, list):
                continue
            for i, matcher in enumerate(matchers):
                assert isinstance(matcher, dict), (
                    f"hooks.json: event '{event_name}'[{i}]: matcher must be an object"
                )
                inner_hooks = matcher.get("hooks")
                assert isinstance(inner_hooks, list), (
                    f"hooks.json: event '{event_name}'[{i}]: missing or invalid 'hooks' array"
                )
                for j, hook in enumerate(inner_hooks):
                    assert "type" in hook, (
                        f"hooks.json: event '{event_name}'[{i}].hooks[{j}]: missing 'type'"
                    )
                    if hook.get("type") == "command":
                        assert "command" in hook, (
                            f"hooks.json: event '{event_name}'[{i}].hooks[{j}]: "
                            "type is 'command' but missing 'command' field"
                        )

    def test_command_scripts_exist(self):
        """All command scripts referenced in hooks must exist on disk."""
        with open(HOOKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})

        seen = set()
        for _event_name, matchers in hooks.items():
            if not isinstance(matchers, list):
                continue
            for matcher in matchers:
                if not isinstance(matcher, dict):
                    continue
                for hook in matcher.get("hooks", []):
                    cmd = hook.get("command", "")
                    if not cmd:
                        continue
                    # Resolve ${CLAUDE_PLUGIN_ROOT} to the repo root (.)
                    cmd = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}", ".", cmd)
                    if cmd in seen:
                        continue
                    seen.add(cmd)
                    resolved = os.path.join(ROOT_DIR, cmd.lstrip("./"))
                    assert os.path.isfile(resolved), (
                        f"hooks.json: command script '{cmd}' not found "
                        f"(resolved to {resolved})"
                    )


# ---------------------------------------------------------------------------
# Python script validation
# ---------------------------------------------------------------------------

_PYTHON_SCRIPTS = _python_scripts()


@pytest.mark.parametrize(
    "script_file",
    _PYTHON_SCRIPTS,
    ids=[os.path.basename(f) for f in _PYTHON_SCRIPTS],
)
def test_python_script_valid_syntax(script_file):
    """Every scripts/*.py file must have valid Python syntax."""
    try:
        py_compile.compile(script_file, doraise=True)
    except py_compile.PyCompileError as exc:
        pytest.fail(f"{os.path.basename(script_file)}: Python syntax error: {exc}")


# ---------------------------------------------------------------------------
# Cross-reference integrity
# ---------------------------------------------------------------------------

class TestCrossReferences:
    """Bidirectional consistency between agent files and docs/agent-mapping.md."""

    @staticmethod
    def _mapped_agents():
        """Extract agent names referenced in agent-mapping.md."""
        if not os.path.isfile(MAPPING_FILE):
            return set()
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        return set(re.findall(r"claude-agent-kit:([a-z0-9-]+)", content))

    @staticmethod
    def _agent_names():
        """Return set of agent names derived from agents/*.md filenames."""
        names = set()
        for path in _agent_files():
            name = os.path.splitext(os.path.basename(path))[0]
            names.add(name)
        return names

    def test_mapping_file_exists(self):
        assert os.path.isfile(MAPPING_FILE), "docs/agent-mapping.md: file not found"

    def test_mapped_agents_have_files(self):
        """Every agent listed in agent-mapping.md must have an agents/<name>.md file."""
        mapped = self._mapped_agents()
        for agent_name in sorted(mapped):
            expected = os.path.join(AGENTS_DIR, f"{agent_name}.md")
            assert os.path.isfile(expected), (
                f"agent-mapping.md: '{agent_name}' listed but agents/{agent_name}.md not found"
            )

    def test_agent_files_listed_in_mapping(self):
        """Every agents/<name>.md file must appear in agent-mapping.md."""
        mapped = self._mapped_agents()
        for agent_name in sorted(self._agent_names()):
            assert agent_name in mapped, (
                f"agents/{agent_name}.md: not listed in agent-mapping.md"
            )

    def test_every_skill_dir_has_skill_md(self):
        """Every skills/<name>/ directory must contain a SKILL.md file."""
        for skill_dir in _skill_dirs():
            dir_name = os.path.basename(skill_dir)
            skill_md = os.path.join(skill_dir, "SKILL.md")
            assert os.path.isfile(skill_md), (
                f"skills/{dir_name}/: missing SKILL.md"
            )


# ---------------------------------------------------------------------------
# Agent metadata validation
# ---------------------------------------------------------------------------

_AGENT_FILES_FOR_METADATA = _agent_files()


@pytest.mark.parametrize(
    "agent_file",
    _AGENT_FILES_FOR_METADATA,
    ids=[os.path.basename(f) for f in _AGENT_FILES_FOR_METADATA],
)
class TestAgentMetadata:
    """Validate optional metadata fields (category, costTier) on agents."""

    def test_category_is_valid_if_present(self, agent_file):
        fm = parse_frontmatter(agent_file)
        category = fm.get("category")
        if not category:
            pytest.skip("no category field")
        assert category in VALID_CATEGORIES, (
            f"{_rel(agent_file)}: category '{category}' is not one of: {VALID_CATEGORIES}"
        )

    def test_cost_tier_is_valid_if_present(self, agent_file):
        fm = parse_frontmatter(agent_file)
        cost_tier = fm.get("costTier")
        if not cost_tier:
            pytest.skip("no costTier field")
        assert cost_tier in VALID_COST_TIERS, (
            f"{_rel(agent_file)}: costTier '{cost_tier}' is not one of: {VALID_COST_TIERS}"
        )


# ---------------------------------------------------------------------------
# Persona switch detection
# ---------------------------------------------------------------------------

class TestPersonaSwitchDetection:
    """Test detect_persona_switch() from scripts/detect.py."""

    @pytest.mark.parametrize("persona", ["sisyphus", "hephaestus", "atlas", "prometheus"])
    def test_detects_persona_skill_invocation(self, persona):
        result = detect_persona_switch(f"/claude-agent-kit:{persona}")
        assert result == persona, (
            f"expected '{persona}', got '{result}' for /claude-agent-kit:{persona}"
        )

    def test_detects_without_leading_slash(self):
        result = detect_persona_switch("claude-agent-kit:sisyphus")
        assert result == "sisyphus", (
            f"expected 'sisyphus', got '{result}' for input without leading slash"
        )

    def test_rejects_non_persona_skill(self):
        result = detect_persona_switch("/claude-agent-kit:plan")
        assert result is None, (
            "should reject /claude-agent-kit:plan (not a persona)"
        )

    def test_rejects_plain_text_with_persona_name(self):
        result = detect_persona_switch("switch to sisyphus mode")
        assert result is None, (
            "should reject plain text containing persona name"
        )

    def test_rejects_empty_input(self):
        result = detect_persona_switch("")
        assert result is None, "should reject empty input"
