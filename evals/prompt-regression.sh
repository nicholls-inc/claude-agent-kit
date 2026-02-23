#!/usr/bin/env bash
set -euo pipefail

# prompt-regression.sh — Detect prompt changes and re-run evals if any changed.
#
# CONTRACT:
#   1. Runs prompt-version.sh to get current hashes.
#   2. Compares against datasets/prompt-baseline.json.
#   3. If hashes changed: re-runs hook-evals.sh, logs changes, updates baseline.
#   4. Exits non-zero if tests fail after a prompt change.
#
# USAGE:
#   ./evals/prompt-regression.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BASELINE="${SCRIPT_DIR}/datasets/prompt-baseline.json"
VERSION_SCRIPT="${ROOT_DIR}/scripts/prompt-version.sh"
HOOK_EVALS="${SCRIPT_DIR}/hook-evals.sh"

passes=0
failures=0

pass() {
  printf '  \033[32mPASS\033[0m %s\n' "$1"
  passes=$((passes + 1))
}

fail() {
  printf '  \033[31mFAIL\033[0m %s\n' "$1"
  failures=$((failures + 1))
}

# ─── Dependency check ───────────────────────────────────────────────

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required for prompt-regression.sh" >&2
  exit 1
fi

if [[ ! -x "${VERSION_SCRIPT}" ]]; then
  echo "ERROR: prompt-version.sh not found or not executable" >&2
  exit 1
fi

# ─── Generate current hashes ────────────────────────────────────────

printf '\n\033[1m=== Prompt Regression Detection ===\033[0m\n'

CURRENT_JSON="$("${VERSION_SCRIPT}")"

# ─── Compare against baseline ───────────────────────────────────────

if [[ ! -f "${BASELINE}" ]]; then
  printf '  No baseline found. Generating initial baseline.\n'
  printf '%s\n' "${CURRENT_JSON}" > "${BASELINE}"
  pass "Initial baseline generated at ${BASELINE}"
  printf '\n\033[1m=== Prompt Regression Summary ===\033[0m\n'
  printf '  Passed:  %d\n' "${passes}"
  printf '  Failed:  %d\n' "${failures}"
  printf '\n\033[32mAll prompt regression checks passed.\033[0m\n'
  exit 0
fi

BASELINE_JSON="$(cat "${BASELINE}")"

# Find changed prompts
changed_prompts=()
all_keys="$(printf '%s\n%s' "${CURRENT_JSON}" "${BASELINE_JSON}" | jq -r 'keys[]' | sort -u)"

for key in ${all_keys}; do
  current_hash="$(printf '%s' "${CURRENT_JSON}" | jq -r --arg k "${key}" '.[$k] // "missing"')"
  baseline_hash="$(printf '%s' "${BASELINE_JSON}" | jq -r --arg k "${key}" '.[$k] // "missing"')"

  if [[ "${current_hash}" != "${baseline_hash}" ]]; then
    changed_prompts+=("${key}")
    if [[ "${baseline_hash}" == "missing" ]]; then
      printf '  \033[33mNEW\033[0m  %s\n' "${key}"
    elif [[ "${current_hash}" == "missing" ]]; then
      printf '  \033[33mDEL\033[0m  %s\n' "${key}"
    else
      printf '  \033[33mCHG\033[0m  %s (%.8s → %.8s)\n' "${key}" "${baseline_hash}" "${current_hash}"
    fi
  fi
done

if [[ ${#changed_prompts[@]} -eq 0 ]]; then
  pass "No prompt changes detected"
  printf '\n\033[1m=== Prompt Regression Summary ===\033[0m\n'
  printf '  Passed:  %d\n' "${passes}"
  printf '  Failed:  %d\n' "${failures}"
  printf '\n\033[32mAll prompt regression checks passed.\033[0m\n'
  exit 0
fi

printf '\n  %d prompt(s) changed. Running regression tests...\n\n' "${#changed_prompts[@]}"

# ─── Re-run deterministic tests ────────────────────────────────────

if [[ -x "${HOOK_EVALS}" ]]; then
  if "${HOOK_EVALS}"; then
    pass "Hook evals pass after prompt changes"
  else
    fail "Hook evals FAILED after prompt changes"
  fi
else
  fail "hook-evals.sh not found or not executable"
fi

# ─── Update baseline on success ────────────────────────────────────

if [[ "${failures}" -eq 0 ]]; then
  printf '%s\n' "${CURRENT_JSON}" > "${BASELINE}"
  printf '\n  Baseline updated.\n'
fi

# ─── Summary ────────────────────────────────────────────────────────

printf '\n\033[1m=== Prompt Regression Summary ===\033[0m\n'
printf '  Changed: %d prompt(s)\n' "${#changed_prompts[@]}"
printf '  Passed:  %d\n' "${passes}"
printf '  Failed:  %d\n' "${failures}"

if [[ "${failures}" -gt 0 ]]; then
  printf '\n\033[31m%d prompt regression check(s) failed.\033[0m\n' "${failures}"
  exit 1
else
  printf '\n\033[32mAll prompt regression checks passed.\033[0m\n'
  exit 0
fi
