#!/usr/bin/env python3
"""Orchestrator for the evaluation suite.

Replaces run-evals.sh. Runs hook_evals, state_evals, and prompt_regression
via subprocess pytest invocations and reports summary.

Exit 0 if all pass, 1 if any fail.
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
BLUE = "\033[1;34m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_suite(name, script_path, use_pytest=True):
    """Run a single eval suite. Returns True on success.

    If use_pytest is True, runs via `python3 -m pytest <script> -v`.
    If use_pytest is False, runs as a standalone script via `python3 <script>`.
    """
    print(f"\n{BLUE}--- Running: {name} ---{RESET}")

    if not os.path.isfile(script_path):
        print(f"{RED}ERROR: {script_path} not found{RESET}")
        return False

    if use_pytest:
        result = subprocess.run(
            ["python3", "-m", "pytest", script_path, "-v"],
            cwd=ROOT_DIR,
        )
    else:
        result = subprocess.run(
            ["python3", script_path],
            cwd=ROOT_DIR,
        )
    return result.returncode == 0


def main():
    # (name, script_path, use_pytest)
    suites = [
        ("Hook Evals", os.path.join(SCRIPT_DIR, "hook_evals.py"), True),
        ("State Evals", os.path.join(SCRIPT_DIR, "state_evals.py"), True),
    ]

    # Prompt regression is a standalone script, not a pytest module
    prompt_regression = os.path.join(SCRIPT_DIR, "prompt_regression.py")
    if os.path.isfile(prompt_regression):
        suites.append(("Prompt Regression", prompt_regression, False))

    suites_run = 0
    suites_failed = 0

    for name, script, use_pytest in suites:
        suites_run += 1
        if not run_suite(name, script, use_pytest=use_pytest):
            suites_failed += 1

    # Final summary
    print(f"\n{BLUE}{'=' * 41}{RESET}")
    print(f"{BOLD}=== Evaluation Suite Summary ==={RESET}")
    print(f"  Suites run:    {suites_run}")
    print(f"  Suites failed: {suites_failed}")

    if suites_failed > 0:
        print(f"\n{RED}{suites_failed} suite(s) failed.{RESET}")
        return 1
    else:
        print(f"\n{GREEN}All evaluation suites passed.{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
