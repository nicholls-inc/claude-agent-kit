#!/usr/bin/env python3
"""Dynamic prompt section builder for persona agents.

Scans agents/*.md and skills/*/SKILL.md, extracts metadata from frontmatter,
and generates context-aware prompt sections for injection via hooks.

CONTRACT:
  - Called by hook-router.sh at SessionStart and UserPromptSubmit.
  - Prints dynamic sections to stdout (plain text).
  - On ANY error: prints nothing to stdout, logs to stderr, exits 0 (fail-open).
  - Requires only Python 3 stdlib (no pip dependencies).
"""

import argparse
import os
import re
import sys


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(filepath):
    """Extract YAML frontmatter fields from a markdown file.

    Reads lines between the first pair of '---' delimiters and extracts
    key: value pairs. All values are strings. Handles only single-line fields.
    """
    fields = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return fields

    in_frontmatter = False
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter:
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", stripped)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                fields[key] = value

    return fields


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_agents(agents_dir):
    """Scan agents/*.md, parse metadata, return list of dicts.

    Filters out agents with category=persona from the subagent list.
    """
    agents = []
    if not os.path.isdir(agents_dir):
        return agents

    for filename in sorted(os.listdir(agents_dir)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(agents_dir, filename)
        meta = parse_frontmatter(filepath)
        if not meta.get("name"):
            continue
        meta["_filename"] = filename
        agents.append(meta)

    return agents


def discover_skills(skills_dir):
    """Scan skills/*/SKILL.md, parse metadata, return list of dicts."""
    skills = []
    if not os.path.isdir(skills_dir):
        return skills

    for dirname in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, dirname, "SKILL.md")
        if not os.path.isfile(skill_path):
            continue
        meta = parse_frontmatter(skill_path)
        if not meta.get("name"):
            continue
        meta["_dirname"] = dirname
        skills.append(meta)

    return skills


def subagents_only(agents):
    """Filter to non-persona agents."""
    return [a for a in agents if a.get("category") != "persona"]


def find_agent(agents, name):
    """Find an agent by name."""
    for a in agents:
        if a.get("name") == name:
            return a
    return None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

COST_ORDER = {"free": 0, "cheap": 1, "moderate": 2, "expensive": 3}


def build_key_triggers(agents):
    """Build key-trigger bullet list from agent metadata."""
    subs = subagents_only(agents)
    triggers = []
    for a in subs:
        kt = a.get("keyTrigger")
        if kt:
            triggers.append(f"- {kt} -> delegate to {a['name']}")

    if not triggers:
        return ""

    # Hardcoded trigger always appended
    triggers.append('- "look into X" + "create PR" -> investigate AND implement (never just research)')

    lines = ["## Key Triggers", ""]
    lines.append("When you detect these patterns, route immediately:")
    lines.extend(triggers)
    return "\n".join(lines)


def build_tool_selection(agents):
    """Build cost-sorted tool selection table."""
    lines = ["## Tool Selection (Cost-Aware)", ""]
    lines.append("| Tool / Agent | Cost | When to Use |")
    lines.append("|---|---|---|")

    # Built-in tools are always FREE
    lines.append("| Grep, Glob, Read | FREE | Direct file/content search — always try first |")
    lines.append("| Bash | FREE | System commands, git operations, build/test |")

    # Agents sorted by cost tier
    subs = subagents_only(agents)
    sorted_agents = sorted(subs, key=lambda a: COST_ORDER.get(a.get("costTier", "expensive"), 3))
    for a in sorted_agents:
        desc = a.get("description", "").split(".")[0]
        tier = a.get("costTier", "unknown").upper()
        lines.append(f"| {a['name']} | {tier} | {desc} |")

    lines.append("")
    lines.append("**Default flow**: Direct tools (FREE) -> cheap agents -> expensive agents.")
    lines.append("Exhaust cheaper options before escalating.")
    return "\n".join(lines)


def build_explore_guide(agents):
    """Build explore agent usage guide."""
    explore = find_agent(agents, "explore")
    if not explore:
        return ""

    lines = ["## Explore Agent Guide", ""]

    avoid = explore.get("avoidWhen")
    if avoid:
        lines.append("**Use Direct Tools (Grep/Glob) when:**")
        for item in avoid.split(";"):
            item = item.strip()
            if item:
                lines.append(f"- {item}")
        lines.append("")

    use = explore.get("useWhen")
    if use:
        lines.append("**Use Explore Agent when:**")
        for item in use.split(";"):
            item = item.strip()
            if item:
                lines.append(f"- {item}")
        lines.append("")

    lines.append("Fire multiple explore agents in parallel for broad searches.")
    lines.append("Always run explore in the background.")
    return "\n".join(lines)


def build_librarian_guide(agents):
    """Build librarian agent usage guide."""
    librarian = find_agent(agents, "librarian")
    if not librarian:
        return ""

    lines = ["## Librarian Agent Guide", ""]
    lines.append("**Librarian = External Research**. For open-source repos, official docs, GitHub issues/PRs.")
    lines.append("")

    use = librarian.get("useWhen")
    if use:
        lines.append("**Fire Librarian when:**")
        for item in use.split(";"):
            item = item.strip()
            if item:
                lines.append(f"- {item}")
        lines.append("")

    lines.append("Always run librarian in the background.")
    lines.append("Collect results before completing the task.")
    return "\n".join(lines)


def build_oracle_guide(agents):
    """Build oracle consultation guide wrapped in tags."""
    oracle = find_agent(agents, "oracle")
    if not oracle:
        return ""

    lines = ["<Oracle_Usage>", "## Oracle Consultation", ""]

    use = oracle.get("useWhen")
    if use:
        lines.append("**Consult Oracle when:**")
        for item in use.split(";"):
            item = item.strip()
            if item:
                lines.append(f"- {item}")
        lines.append("")

    avoid = oracle.get("avoidWhen")
    if avoid:
        lines.append("**Do NOT consult Oracle for:**")
        for item in avoid.split(";"):
            item = item.strip()
            if item:
                lines.append(f"- {item}")
        lines.append("")

    lines.append("**Usage pattern:**")
    lines.append("1. Announce: \"Consulting Oracle on [topic]\"")
    lines.append("2. Invoke Oracle with focused question")
    lines.append("3. Wait for and incorporate response before proceeding")
    lines.append("")
    lines.append("**Background policy:** Always collect Oracle results before final answer.")
    lines.append("NEVER cancel an Oracle consultation.")
    lines.append("</Oracle_Usage>")
    return "\n".join(lines)


def build_delegation_table(agents):
    """Build domain-to-agent routing table."""
    subs = subagents_only(agents)
    rows = []
    for a in subs:
        domains = a.get("delegationDomains")
        if domains:
            for domain in domains.split(";"):
                domain = domain.strip()
                if domain:
                    rows.append(f"| {domain} | {a['name']} |")

    if not rows:
        return ""

    lines = ["## Delegation Routing", ""]
    lines.append("| Domain | Agent |")
    lines.append("|---|---|")
    lines.extend(rows)
    return "\n".join(lines)


def build_skills_guide(skills):
    """Build skill table and evaluation protocol."""
    if not skills:
        return ""

    lines = ["## Skills Guide", ""]
    lines.append("Available skills (invoke with `/claude-agent-kit:<name>`):")
    lines.append("")
    lines.append("| Skill | Description |")
    lines.append("|---|---|")
    for s in skills:
        desc = s.get("description", "").split(".")[0]
        lines.append(f"| {s['name']} | {desc} |")

    lines.append("")
    lines.append("**Evaluation protocol:**")
    lines.append("1. For every task, check: does a skill's domain overlap with this work?")
    lines.append("2. If yes, use the skill — it encodes best practices for that domain.")
    lines.append("3. Skills that spawn subagents (context: fork) run in isolated sessions.")
    return "\n".join(lines)


def build_hard_blocks(agents):
    """Build static constraint rules."""
    lines = ["## Hard Blocks (NEVER violate)", ""]
    lines.append("- NEVER suppress type errors or linter warnings to make code compile")
    lines.append("- NEVER commit changes without explicit user request")
    lines.append("- NEVER speculate about code you haven't read — read it first")
    lines.append("- NEVER leave the codebase in a broken state (build fails, tests fail)")
    lines.append("- NEVER deliver a final answer without collecting pending background results")

    oracle = find_agent(agents, "oracle")
    if oracle:
        lines.append("- NEVER cancel an Oracle consultation — always wait for results")
        lines.append("- NEVER deliver final answer before collecting Oracle results")

    return "\n".join(lines)


def build_anti_patterns(agents):
    """Build anti-pattern list."""
    lines = ["## Anti-Patterns (Blocking)", ""]
    lines.append("If you catch yourself doing any of these, STOP and correct:")
    lines.append("")
    lines.append("- Type safety violations (any-casts, ts-ignore, suppressing errors)")
    lines.append("- Empty catch blocks that swallow errors silently")
    lines.append("- Deleting or skipping failing tests instead of fixing them")
    lines.append("- Firing expensive agents for tasks solvable with direct tools")
    lines.append("- Shotgun debugging (random changes hoping something works)")
    lines.append("- Bulk-cancelling background tasks instead of collecting results individually")

    oracle = find_agent(agents, "oracle")
    if oracle:
        lines.append("- Skipping Oracle results when they're available")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-persona composition
# ---------------------------------------------------------------------------

# Section order per persona
PERSONA_SECTIONS = {
    "sisyphus": [
        "key_triggers",
        "tool_selection",
        "explore_guide",
        "librarian_guide",
        "skills_guide",
        "delegation_table",
        "oracle_guide",
        "hard_blocks",
        "anti_patterns",
    ],
    "hephaestus": [
        "key_triggers",
        "tool_selection",
        "explore_guide",
        "librarian_guide",
        "skills_guide",
        "delegation_table",
        "oracle_guide",
        "hard_blocks",
        "anti_patterns",
    ],
    "atlas": [
        "tool_selection",
        "skills_guide",
        "delegation_table",
    ],
    "prometheus": [],  # Fully static — no dynamic sections
}


def compose_sections(persona, agents, skills):
    """Compose dynamic sections for a given persona. Returns string."""
    section_keys = PERSONA_SECTIONS.get(persona, [])
    if not section_keys:
        return ""

    builders = {
        "key_triggers": lambda: build_key_triggers(agents),
        "tool_selection": lambda: build_tool_selection(agents),
        "explore_guide": lambda: build_explore_guide(agents),
        "librarian_guide": lambda: build_librarian_guide(agents),
        "oracle_guide": lambda: build_oracle_guide(agents),
        "delegation_table": lambda: build_delegation_table(agents),
        "skills_guide": lambda: build_skills_guide(skills),
        "hard_blocks": lambda: build_hard_blocks(agents),
        "anti_patterns": lambda: build_anti_patterns(agents),
    }

    parts = []
    for key in section_keys:
        builder = builders.get(key)
        if builder:
            result = builder()
            if result:
                parts.append(result)

    if not parts:
        return ""

    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate dynamic prompt sections for persona agents."
    )
    parser.add_argument("--persona", required=True, help="Persona name (sisyphus, hephaestus, atlas, prometheus)")
    parser.add_argument("--agents-dir", required=True, help="Path to agents/ directory")
    parser.add_argument("--skills-dir", required=True, help="Path to skills/ directory")
    args = parser.parse_args()

    agents = discover_agents(args.agents_dir)
    skills = discover_skills(args.skills_dir)
    output = compose_sections(args.persona, agents, skills)

    if output:
        sys.stdout.write(output)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fail-open: log to stderr, print nothing to stdout, exit 0
        print(f"[build_sections] error: {e}", file=sys.stderr)
        sys.exit(0)
