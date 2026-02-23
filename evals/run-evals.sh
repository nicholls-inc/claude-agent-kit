#!/usr/bin/env bash
set -euo pipefail

# run-evals.sh — Orchestrator for the evaluation suite.
#
# Runs all deterministic eval scripts and reports summary.
# Exit 0 if all pass, 1 if any fail.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

suites_run=0
suites_failed=0

run_suite() {
  local name="$1"
  local script="$2"

  printf '\n\033[1;34m━━━ Running: %s ━━━\033[0m\n' "${name}"

  if [[ ! -x "${script}" ]]; then
    printf '\033[31mERROR: %s not found or not executable\033[0m\n' "${script}"
    suites_failed=$((suites_failed + 1))
    suites_run=$((suites_run + 1))
    return
  fi

  if "${script}"; then
    suites_run=$((suites_run + 1))
  else
    suites_failed=$((suites_failed + 1))
    suites_run=$((suites_run + 1))
  fi
}

# ─── Run eval suites ────────────────────────────────────────────────

run_suite "Hook Evals" "${SCRIPT_DIR}/hook-evals.sh"
run_suite "State Evals" "${SCRIPT_DIR}/state-evals.sh"

# Run prompt regression if it exists (Phase 3)
if [[ -x "${SCRIPT_DIR}/prompt-regression.sh" ]]; then
  run_suite "Prompt Regression" "${SCRIPT_DIR}/prompt-regression.sh"
fi

# ─── Final Summary ──────────────────────────────────────────────────

printf '\n\033[1;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n'
printf '\033[1m=== Evaluation Suite Summary ===\033[0m\n'
printf '  Suites run:    %d\n' "${suites_run}"
printf '  Suites failed: %d\n' "${suites_failed}"

if [[ "${suites_failed}" -gt 0 ]]; then
  printf '\n\033[31m%d suite(s) failed.\033[0m\n' "${suites_failed}"
  exit 1
else
  printf '\n\033[32mAll evaluation suites passed.\033[0m\n'
  exit 0
fi
