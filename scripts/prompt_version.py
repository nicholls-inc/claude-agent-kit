#!/usr/bin/env python3
"""Compute SHA256 hashes of all agent and skill prompt files.

Replaces prompt-version.sh.

CONTRACT:
  - Scans agents/*.md and skills/*/SKILL.md.
  - Outputs JSON: {"agent:<name>": "<sha256>", "skill:<name>": "<sha256>", ...}
  - Used for prompt regression detection.

CLI:
  python3 prompt_version.py                    # outputs JSON to stdout
  python3 prompt_version.py --root-dir <path>  # custom root directory
"""

import hashlib
import json
import os
import sys


def compute_hashes(root_dir: str) -> dict:
    """Compute SHA256 hashes for all agent and skill prompt files."""
    hashes = {}

    # Agent prompts
    agents_dir = os.path.join(root_dir, "agents")
    if os.path.isdir(agents_dir):
        for filename in sorted(os.listdir(agents_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(agents_dir, filename)
            if not os.path.isfile(filepath):
                continue
            name = filename[:-3]  # strip .md
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                h.update(f.read())
            hashes[f"agent:{name}"] = h.hexdigest()

    # Skill prompts
    skills_dir = os.path.join(root_dir, "skills")
    if os.path.isdir(skills_dir):
        for dirname in sorted(os.listdir(skills_dir)):
            skill_path = os.path.join(skills_dir, dirname, "SKILL.md")
            if not os.path.isfile(skill_path):
                continue
            h = hashlib.sha256()
            with open(skill_path, "rb") as f:
                h.update(f.read())
            hashes[f"skill:{dirname}"] = h.hexdigest()

    return hashes


def main():
    # Determine root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    # Parse optional --root-dir argument
    args = sys.argv[1:]
    if "--root-dir" in args:
        idx = args.index("--root-dir")
        if idx + 1 < len(args):
            root_dir = args[idx + 1]

    hashes = compute_hashes(root_dir)
    print(json.dumps(hashes, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[prompt_version] error: {e}", file=sys.stderr)
        sys.exit(1)
