#!/usr/bin/env python3
"""Unit tests for scripts/build_sections.py."""

import os
import sys
import tempfile
import textwrap
import unittest

# Add scripts/ to path so we can import the module
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPT_DIR)

import build_sections  # noqa: E402


class TestParseFrontmatter(unittest.TestCase):
    """Tests for parse_frontmatter()."""

    def _write_temp(self, content):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write(textwrap.dedent(content))
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_basic_fields(self):
        path = self._write_temp("""\
            ---
            name: explore
            description: Codebase search specialist
            model: haiku
            costTier: cheap
            ---

            # Body content
            """)
        fields = build_sections.parse_frontmatter(path)
        self.assertEqual(fields["name"], "explore")
        self.assertEqual(fields["description"], "Codebase search specialist")
        self.assertEqual(fields["model"], "haiku")
        self.assertEqual(fields["costTier"], "cheap")

    def test_missing_frontmatter(self):
        path = self._write_temp("# No frontmatter here\nJust body.\n")
        fields = build_sections.parse_frontmatter(path)
        self.assertEqual(fields, {})

    def test_nonexistent_file(self):
        fields = build_sections.parse_frontmatter("/nonexistent/path.md")
        self.assertEqual(fields, {})

    def test_fields_with_colons_in_value(self):
        path = self._write_temp("""\
            ---
            name: test
            keyTrigger: "Where is X?"; "Find Y"
            useWhen: Need to search; broad pattern matching
            ---
            """)
        fields = build_sections.parse_frontmatter(path)
        self.assertEqual(fields["name"], "test")
        self.assertIn("Where is X?", fields["keyTrigger"])


class TestDiscoverAgents(unittest.TestCase):
    """Tests for discover_agents()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_agent(self, name, extra_fields=""):
        content = textwrap.dedent(f"""\
            ---
            name: {name}
            description: Test agent {name}
            model: haiku
            tools: Read, Grep
            maxTurns: 10
            {extra_fields}
            ---

            # {name}
            Body content.
            """)
        with open(os.path.join(self.tmpdir, f"{name}.md"), "w") as f:
            f.write(content)

    def test_discovers_all_agents(self):
        self._write_agent("explore", "category: search\ncostTier: cheap")
        self._write_agent("oracle", "category: advisor\ncostTier: expensive")
        self._write_agent("sisyphus", "category: persona")

        agents = build_sections.discover_agents(self.tmpdir)
        names = [a["name"] for a in agents]
        self.assertIn("explore", names)
        self.assertIn("oracle", names)
        self.assertIn("sisyphus", names)

    def test_filters_persona_from_subagents(self):
        self._write_agent("explore", "category: search")
        self._write_agent("sisyphus", "category: persona")

        agents = build_sections.discover_agents(self.tmpdir)
        subs = build_sections.subagents_only(agents)
        sub_names = [a["name"] for a in subs]
        self.assertIn("explore", sub_names)
        self.assertNotIn("sisyphus", sub_names)

    def test_nonexistent_dir(self):
        agents = build_sections.discover_agents("/nonexistent/agents")
        self.assertEqual(agents, [])


class TestDiscoverSkills(unittest.TestCase):
    """Tests for discover_skills()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_skill(self, name, description="Test skill"):
        skill_dir = os.path.join(self.tmpdir, name)
        os.makedirs(skill_dir, exist_ok=True)
        content = textwrap.dedent(f"""\
            ---
            name: {name}
            description: {description}
            ---

            # {name}
            Skill body.
            """)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write(content)

    def test_discovers_skills(self):
        self._write_skill("plan", "Create a plan")
        self._write_skill("start-work", "Start execution")

        skills = build_sections.discover_skills(self.tmpdir)
        names = [s["name"] for s in skills]
        self.assertIn("plan", names)
        self.assertIn("start-work", names)

    def test_nonexistent_dir(self):
        skills = build_sections.discover_skills("/nonexistent/skills")
        self.assertEqual(skills, [])


class TestSectionBuilders(unittest.TestCase):
    """Tests for individual section builders."""

    def _make_agents(self):
        return [
            {
                "name": "explore",
                "description": "Codebase search specialist. Finds files and code.",
                "category": "search",
                "costTier": "cheap",
                "keyTrigger": "Broad codebase search needed",
                "useWhen": "Need to search across many files; unknown file locations",
                "avoidWhen": "You already know the file path; searching a single known file",
                "delegationDomains": "codebase search; file discovery",
            },
            {
                "name": "librarian",
                "description": "External research agent. Retrieves documentation.",
                "category": "research",
                "costTier": "moderate",
                "keyTrigger": "External library mentioned",
                "useWhen": "Need official documentation; external repo investigation",
                "avoidWhen": "Question is about local codebase only",
                "delegationDomains": "external documentation; open-source research",
            },
            {
                "name": "oracle",
                "description": "Architecture advisor. High-IQ reasoning.",
                "category": "advisor",
                "costTier": "expensive",
                "keyTrigger": "Architecture decision needed",
                "useWhen": "Architecture decisions; debugging after 3 failures",
                "avoidWhen": "Simple implementation questions; routine code changes",
                "delegationDomains": "architecture review; debugging consultation",
            },
            {
                "name": "sisyphus",
                "description": "Main orchestrator.",
                "category": "persona",
            },
        ]

    def _make_skills(self):
        return [
            {"name": "plan", "description": "Create a durable implementation plan."},
            {"name": "start-work", "description": "Start executing a plan."},
        ]

    def test_build_key_triggers(self):
        agents = self._make_agents()
        result = build_sections.build_key_triggers(agents)
        self.assertIn("explore", result)
        self.assertIn("librarian", result)
        self.assertIn("oracle", result)
        self.assertIn("look into X", result)
        # Persona agents should NOT appear
        self.assertNotIn("sisyphus", result)

    def test_build_key_triggers_empty(self):
        # No agents with keyTrigger -> empty
        agents = [{"name": "test", "category": "search"}]
        result = build_sections.build_key_triggers(agents)
        self.assertEqual(result, "")

    def test_build_tool_selection(self):
        agents = self._make_agents()
        result = build_sections.build_tool_selection(agents)
        self.assertIn("Grep, Glob, Read", result)
        self.assertIn("FREE", result)
        self.assertIn("CHEAP", result)
        self.assertIn("EXPENSIVE", result)
        # Should be sorted by cost
        cheap_pos = result.find("CHEAP")
        expensive_pos = result.find("EXPENSIVE")
        self.assertLess(cheap_pos, expensive_pos)

    def test_build_explore_guide(self):
        agents = self._make_agents()
        result = build_sections.build_explore_guide(agents)
        self.assertIn("Explore Agent Guide", result)
        self.assertIn("search across many files", result)
        self.assertIn("already know the file path", result)

    def test_build_explore_guide_no_explore(self):
        agents = [a for a in self._make_agents() if a["name"] != "explore"]
        result = build_sections.build_explore_guide(agents)
        self.assertEqual(result, "")

    def test_build_librarian_guide(self):
        agents = self._make_agents()
        result = build_sections.build_librarian_guide(agents)
        self.assertIn("Librarian Agent Guide", result)
        self.assertIn("official documentation", result)

    def test_build_librarian_guide_no_librarian(self):
        agents = [a for a in self._make_agents() if a["name"] != "librarian"]
        result = build_sections.build_librarian_guide(agents)
        self.assertEqual(result, "")

    def test_build_oracle_guide(self):
        agents = self._make_agents()
        result = build_sections.build_oracle_guide(agents)
        self.assertIn("<Oracle_Usage>", result)
        self.assertIn("</Oracle_Usage>", result)
        self.assertIn("Architecture decisions", result)
        self.assertIn("NEVER cancel", result)

    def test_build_oracle_guide_no_oracle(self):
        agents = [a for a in self._make_agents() if a["name"] != "oracle"]
        result = build_sections.build_oracle_guide(agents)
        self.assertEqual(result, "")

    def test_build_delegation_table(self):
        agents = self._make_agents()
        result = build_sections.build_delegation_table(agents)
        self.assertIn("Delegation Routing", result)
        self.assertIn("codebase search", result)
        self.assertIn("explore", result)

    def test_build_delegation_table_no_domains(self):
        agents = [{"name": "test", "category": "search"}]
        result = build_sections.build_delegation_table(agents)
        self.assertEqual(result, "")

    def test_build_skills_guide(self):
        skills = self._make_skills()
        result = build_sections.build_skills_guide(skills)
        self.assertIn("Skills Guide", result)
        self.assertIn("plan", result)
        self.assertIn("start-work", result)

    def test_build_skills_guide_empty(self):
        result = build_sections.build_skills_guide([])
        self.assertEqual(result, "")

    def test_build_hard_blocks_with_oracle(self):
        agents = self._make_agents()
        result = build_sections.build_hard_blocks(agents)
        self.assertIn("NEVER cancel an Oracle", result)
        self.assertIn("collecting Oracle results", result)

    def test_build_hard_blocks_without_oracle(self):
        agents = [a for a in self._make_agents() if a["name"] != "oracle"]
        result = build_sections.build_hard_blocks(agents)
        self.assertIn("NEVER suppress type errors", result)
        self.assertNotIn("Oracle", result)

    def test_build_anti_patterns_with_oracle(self):
        agents = self._make_agents()
        result = build_sections.build_anti_patterns(agents)
        self.assertIn("Skipping Oracle results", result)

    def test_build_anti_patterns_without_oracle(self):
        agents = [a for a in self._make_agents() if a["name"] != "oracle"]
        result = build_sections.build_anti_patterns(agents)
        self.assertNotIn("Oracle", result)


class TestPersonaComposition(unittest.TestCase):
    """Tests for compose_sections()."""

    def _make_agents(self):
        return [
            {
                "name": "explore",
                "description": "Search specialist.",
                "category": "search",
                "costTier": "cheap",
                "keyTrigger": "Broad search",
                "useWhen": "Multi-file search",
                "avoidWhen": "Known file",
                "delegationDomains": "codebase search",
            },
            {
                "name": "oracle",
                "description": "Architecture advisor.",
                "category": "advisor",
                "costTier": "expensive",
                "useWhen": "Architecture decisions",
                "avoidWhen": "Simple tasks",
            },
            {
                "name": "sisyphus",
                "category": "persona",
            },
        ]

    def _make_skills(self):
        return [
            {"name": "plan", "description": "Create plan."},
        ]

    def test_sisyphus_gets_all_sections(self):
        agents = self._make_agents()
        skills = self._make_skills()
        result = build_sections.compose_sections("sisyphus", agents, skills)
        self.assertIn("Key Triggers", result)
        self.assertIn("Tool Selection", result)
        self.assertIn("Explore Agent Guide", result)
        self.assertIn("Skills Guide", result)
        self.assertIn("Hard Blocks", result)
        self.assertIn("Anti-Patterns", result)

    def test_hephaestus_gets_all_sections(self):
        agents = self._make_agents()
        skills = self._make_skills()
        result = build_sections.compose_sections("hephaestus", agents, skills)
        self.assertIn("Key Triggers", result)
        self.assertIn("Tool Selection", result)
        self.assertIn("Hard Blocks", result)

    def test_atlas_gets_subset(self):
        agents = self._make_agents()
        skills = self._make_skills()
        result = build_sections.compose_sections("atlas", agents, skills)
        self.assertIn("Tool Selection", result)
        self.assertIn("Skills Guide", result)
        # Atlas should NOT get key triggers, explore guide, etc.
        self.assertNotIn("Key Triggers", result)
        self.assertNotIn("Explore Agent Guide", result)
        self.assertNotIn("Hard Blocks", result)

    def test_prometheus_gets_nothing(self):
        agents = self._make_agents()
        skills = self._make_skills()
        result = build_sections.compose_sections("prometheus", agents, skills)
        self.assertEqual(result, "")

    def test_unknown_persona_gets_nothing(self):
        agents = self._make_agents()
        skills = self._make_skills()
        result = build_sections.compose_sections("unknown", agents, skills)
        self.assertEqual(result, "")


class TestConditionalSections(unittest.TestCase):
    """Tests that sections are conditionally omitted."""

    def test_no_explore_no_explore_guide(self):
        agents = [
            {"name": "librarian", "category": "research", "costTier": "moderate"},
            {"name": "sisyphus", "category": "persona"},
        ]
        result = build_sections.compose_sections("sisyphus", agents, [])
        self.assertNotIn("Explore Agent Guide", result)

    def test_no_librarian_no_librarian_guide(self):
        agents = [
            {"name": "explore", "category": "search", "costTier": "cheap",
             "useWhen": "test", "avoidWhen": "test"},
            {"name": "sisyphus", "category": "persona"},
        ]
        result = build_sections.compose_sections("sisyphus", agents, [])
        self.assertNotIn("Librarian Agent Guide", result)

    def test_no_oracle_no_oracle_section(self):
        agents = [
            {"name": "explore", "category": "search", "costTier": "cheap"},
            {"name": "sisyphus", "category": "persona"},
        ]
        result = build_sections.compose_sections("sisyphus", agents, [])
        self.assertNotIn("Oracle", result)

    def test_no_skills_no_skills_guide(self):
        agents = [
            {"name": "explore", "category": "search", "costTier": "cheap"},
        ]
        result = build_sections.compose_sections("sisyphus", agents, [])
        self.assertNotIn("Skills Guide", result)


class TestFailOpen(unittest.TestCase):
    """Tests for fail-open behavior."""

    def test_missing_agents_dir(self):
        agents = build_sections.discover_agents("/nonexistent/agents")
        self.assertEqual(agents, [])

    def test_missing_skills_dir(self):
        skills = build_sections.discover_skills("/nonexistent/skills")
        self.assertEqual(skills, [])

    def test_corrupt_frontmatter(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        f.write("---\nname: test\n---corrupted\n")
        f.close()
        self.addCleanup(os.unlink, f.name)
        # Should not raise, should return partial results
        fields = build_sections.parse_frontmatter(f.name)
        self.assertEqual(fields.get("name"), "test")

    def test_compose_with_empty_inputs(self):
        result = build_sections.compose_sections("sisyphus", [], [])
        # Should still produce hard_blocks and anti_patterns (they're static)
        self.assertIn("Hard Blocks", result)
        self.assertIn("Anti-Patterns", result)


class TestEndToEnd(unittest.TestCase):
    """End-to-end tests using the actual agents/ and skills/ directories."""

    def test_with_real_agents_dir(self):
        """Test with the actual plugin agents directory."""
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        agents_dir = os.path.join(root, "agents")
        skills_dir = os.path.join(root, "skills")

        if not os.path.isdir(agents_dir):
            self.skipTest("agents/ directory not found")

        agents = build_sections.discover_agents(agents_dir)
        skills = build_sections.discover_skills(skills_dir)

        # Should discover the known agents
        agent_names = [a["name"] for a in agents]
        self.assertIn("explore", agent_names)
        self.assertIn("sisyphus", agent_names)

        # Sisyphus should get dynamic sections
        result = build_sections.compose_sections("sisyphus", agents, skills)
        self.assertTrue(len(result) > 100, "Sisyphus sections should be substantial")
        self.assertIn("Tool Selection", result)

        # Prometheus should get nothing
        result = build_sections.compose_sections("prometheus", agents, skills)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
