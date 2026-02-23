#!/usr/bin/env python3
"""Detect prompt changes and re-run evals if any changed.

Replaces prompt-regression.sh. Uses scripts.prompt_version.compute_hashes.

CONTRACT:
  1. Compute current prompt hashes.
  2. Compare against evals/datasets/prompt-baseline.json.
  3. If hashes changed: re-run hook_evals.py via pytest, log changes, update baseline.
  4. Exit non-zero if tests fail after a prompt change.
"""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.prompt_version import compute_hashes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASELINE_PATH = os.path.join(SCRIPT_DIR, "datasets", "prompt-baseline.json")
HOOK_EVALS_PATH = os.path.join(SCRIPT_DIR, "hook_evals.py")

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _load_baseline():
    """Load baseline hashes from JSON file. Returns None if missing."""
    if not os.path.isfile(BASELINE_PATH):
        return None
    try:
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_baseline(hashes):
    """Save hashes as the new baseline."""
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    passes = 0
    failures = 0

    print(f"\n{BOLD}=== Prompt Regression Detection ==={RESET}")

    # Generate current hashes
    current_hashes = compute_hashes(ROOT_DIR)

    # Load baseline
    baseline = _load_baseline()
    if baseline is None:
        print("  No baseline found. Generating initial baseline.")
        _save_baseline(current_hashes)
        passes += 1
        print(f"  {GREEN}PASS{RESET} Initial baseline generated at {BASELINE_PATH}")
        print(f"\n{BOLD}=== Prompt Regression Summary ==={RESET}")
        print(f"  Passed:  {passes}")
        print(f"  Failed:  {failures}")
        print(f"\n{GREEN}All prompt regression checks passed.{RESET}")
        return 0

    # Find changed prompts
    all_keys = sorted(set(list(current_hashes.keys()) + list(baseline.keys())))
    changed_prompts = []

    for key in all_keys:
        current_hash = current_hashes.get(key, "missing")
        baseline_hash = baseline.get(key, "missing")

        if current_hash != baseline_hash:
            changed_prompts.append(key)
            if baseline_hash == "missing":
                print(f"  {YELLOW}NEW{RESET}  {key}")
            elif current_hash == "missing":
                print(f"  {YELLOW}DEL{RESET}  {key}")
            else:
                print(f"  {YELLOW}CHG{RESET}  {key} ({baseline_hash[:8]} -> {current_hash[:8]})")

    if not changed_prompts:
        passes += 1
        print(f"  {GREEN}PASS{RESET} No prompt changes detected")
        print(f"\n{BOLD}=== Prompt Regression Summary ==={RESET}")
        print(f"  Passed:  {passes}")
        print(f"  Failed:  {failures}")
        print(f"\n{GREEN}All prompt regression checks passed.{RESET}")
        return 0

    print(f"\n  {len(changed_prompts)} prompt(s) changed. Running regression tests...\n")

    # Re-run hook evals via pytest
    if os.path.isfile(HOOK_EVALS_PATH):
        result = subprocess.run(
            ["python3", "-m", "pytest", HOOK_EVALS_PATH, "-v"],
            cwd=ROOT_DIR,
        )
        if result.returncode == 0:
            passes += 1
            print(f"  {GREEN}PASS{RESET} Hook evals pass after prompt changes")
        else:
            failures += 1
            print(f"  {RED}FAIL{RESET} Hook evals FAILED after prompt changes")
    else:
        failures += 1
        print(f"  {RED}FAIL{RESET} hook_evals.py not found")

    # Update baseline on success
    if failures == 0:
        _save_baseline(current_hashes)
        print("\n  Baseline updated.")

    # Summary
    print(f"\n{BOLD}=== Prompt Regression Summary ==={RESET}")
    print(f"  Changed: {len(changed_prompts)} prompt(s)")
    print(f"  Passed:  {passes}")
    print(f"  Failed:  {failures}")

    if failures > 0:
        print(f"\n{RED}{failures} prompt regression check(s) failed.{RESET}")
        return 1
    else:
        print(f"\n{GREEN}All prompt regression checks passed.{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
