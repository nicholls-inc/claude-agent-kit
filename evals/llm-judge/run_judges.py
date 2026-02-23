#!/usr/bin/env python3
"""Run all LLM-as-judge evaluations.

Replaces run-judges.sh. Processes recent Langfuse traces through persona,
session-signals, and persona-trace-analyzer judges.
Intended to be run weekly or on prompt changes.

USAGE:
  python3 evals/llm-judge/run_judges.py [--days 7] [--dry-run]
"""

import argparse
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EVALS_DIR = os.path.dirname(SCRIPT_DIR)

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
BLUE = "\033[1;34m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Judge definitions: (display_name, script_path)
JUDGES = [
    ("Session Signals", os.path.join(EVALS_DIR, "session-signals.py")),
    ("Persona Trace Analysis", os.path.join(EVALS_DIR, "persona-trace-analyzer.py")),
    ("Persona Judge", os.path.join(SCRIPT_DIR, "judge-persona.py")),
]


def run_judge(name, script, days, dry_run):
    """Run a single judge script via uv run. Returns True on success."""
    print(f"\n{BLUE}--- {name} ---{RESET}")

    cmd = ["uv", "run", script, "--days", str(days)]
    if dry_run:
        cmd.append("--dry-run")

    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run all LLM-as-judge evaluations.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no actual API calls)")
    args = parser.parse_args()

    print(f"{BOLD}=== Running LLM-as-Judge Evaluations ==={RESET}")
    print(f"  Days: {args.days}")
    print(f"  Dry run: {'yes' if args.dry_run else 'no'}\n")

    # Check uv is available
    if not shutil.which("uv"):
        print("ERROR: uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh", file=sys.stderr)
        return 1

    suites_run = 0
    suites_failed = 0

    for name, script in JUDGES:
        suites_run += 1
        if not run_judge(name, script, args.days, args.dry_run):
            suites_failed += 1

    # Summary
    print(f"\n{BLUE}{'=' * 41}{RESET}")
    print(f"{BOLD}=== Judge Suite Summary ==={RESET}")
    print(f"  Judges run:    {suites_run}")
    print(f"  Judges failed: {suites_failed}")

    if suites_failed > 0:
        print(f"\n{RED}{suites_failed} judge(s) failed.{RESET}")
        return 1
    else:
        print(f"\n{GREEN}All judges completed successfully.{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
