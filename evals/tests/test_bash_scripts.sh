#!/usr/bin/env bash
set -euo pipefail

# test_bash_scripts.sh — Tests for eval bash script orchestration logic.
#
# Tests: run-evals.sh suite dispatch, run-judges.sh structure,
#        prompt-regression.sh baseline handling.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVALS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${EVALS_DIR}/.." && pwd)"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

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

# ─── run-evals.sh tests ──────────────────────────────────────────

printf '\n\033[1m=== run-evals.sh Tests ===\033[0m\n'

# Script exists and is executable
if [[ -x "${EVALS_DIR}/run-evals.sh" ]]; then
  pass "run-evals.sh is executable"
else
  fail "run-evals.sh not executable"
fi

# Script references hook-evals.sh and state-evals.sh
if grep -q 'hook-evals.sh' "${EVALS_DIR}/run-evals.sh"; then
  pass "run-evals.sh references hook-evals.sh"
else
  fail "run-evals.sh missing hook-evals.sh reference"
fi

if grep -q 'state-evals.sh' "${EVALS_DIR}/run-evals.sh"; then
  pass "run-evals.sh references state-evals.sh"
else
  fail "run-evals.sh missing state-evals.sh reference"
fi

if grep -q 'prompt-regression.sh' "${EVALS_DIR}/run-evals.sh"; then
  pass "run-evals.sh references prompt-regression.sh"
else
  fail "run-evals.sh missing prompt-regression.sh reference"
fi

# All referenced scripts exist
for script in hook-evals.sh state-evals.sh prompt-regression.sh; do
  if [[ -x "${EVALS_DIR}/${script}" ]]; then
    pass "referenced script ${script} exists and is executable"
  else
    fail "referenced script ${script} missing or not executable"
  fi
done

# Script uses set -euo pipefail
if head -2 "${EVALS_DIR}/run-evals.sh" | grep -q 'set -euo pipefail'; then
  pass "run-evals.sh has strict mode"
else
  fail "run-evals.sh missing strict mode"
fi

# ─── run-judges.sh tests ─────────────────────────────────────────

printf '\n\033[1m=== run-judges.sh Tests ===\033[0m\n'

JUDGES_DIR="${EVALS_DIR}/llm-judge"

if [[ -x "${JUDGES_DIR}/run-judges.sh" ]]; then
  pass "run-judges.sh is executable"
else
  fail "run-judges.sh not executable"
fi

# Script references all judge scripts
for judge in judge-persona.py; do
  if grep -q "${judge}" "${JUDGES_DIR}/run-judges.sh"; then
    pass "run-judges.sh references ${judge}"
  else
    fail "run-judges.sh missing ${judge} reference"
  fi
done

# Script references session-signals.py and persona-trace-analyzer.py
if grep -q 'session-signals.py' "${JUDGES_DIR}/run-judges.sh"; then
  pass "run-judges.sh references session-signals.py"
else
  fail "run-judges.sh missing session-signals.py reference"
fi

if grep -q 'persona-trace-analyzer.py' "${JUDGES_DIR}/run-judges.sh"; then
  pass "run-judges.sh references persona-trace-analyzer.py"
else
  fail "run-judges.sh missing persona-trace-analyzer.py reference"
fi

# All referenced Python scripts exist
for pyscript in session-signals.py persona-trace-analyzer.py; do
  if [[ -f "${EVALS_DIR}/${pyscript}" ]]; then
    pass "referenced script ${pyscript} exists"
  else
    fail "referenced script ${pyscript} missing"
  fi
done

for pyscript in judge-persona.py; do
  if [[ -f "${JUDGES_DIR}/${pyscript}" ]]; then
    pass "referenced judge ${pyscript} exists"
  else
    fail "referenced judge ${pyscript} missing"
  fi
done

# Script uses set -euo pipefail
if head -2 "${JUDGES_DIR}/run-judges.sh" | grep -q 'set -euo pipefail'; then
  pass "run-judges.sh has strict mode"
else
  fail "run-judges.sh missing strict mode"
fi

# Script handles --dry-run flag
if grep -q '\-\-dry-run' "${JUDGES_DIR}/run-judges.sh"; then
  pass "run-judges.sh supports --dry-run"
else
  fail "run-judges.sh missing --dry-run support"
fi

# Script handles --days flag
if grep -q '\-\-days' "${JUDGES_DIR}/run-judges.sh"; then
  pass "run-judges.sh supports --days"
else
  fail "run-judges.sh missing --days support"
fi

# ─── prompt-regression.sh tests ──────────────────────────────────

printf '\n\033[1m=== prompt-regression.sh Tests ===\033[0m\n'

if [[ -x "${EVALS_DIR}/prompt-regression.sh" ]]; then
  pass "prompt-regression.sh is executable"
else
  fail "prompt-regression.sh not executable"
fi

# Script uses set -euo pipefail
if head -2 "${EVALS_DIR}/prompt-regression.sh" | grep -q 'set -euo pipefail'; then
  pass "prompt-regression.sh has strict mode"
else
  fail "prompt-regression.sh missing strict mode"
fi

# Script references prompt-version.sh
if grep -q 'prompt-version.sh' "${EVALS_DIR}/prompt-regression.sh"; then
  pass "prompt-regression.sh references prompt-version.sh"
else
  fail "prompt-regression.sh missing prompt-version.sh reference"
fi

# prompt-version.sh exists
if [[ -x "${ROOT_DIR}/scripts/prompt-version.sh" ]]; then
  pass "prompt-version.sh exists and is executable"
else
  fail "prompt-version.sh missing or not executable"
fi

# Script references baseline dataset
if grep -q 'prompt-baseline.json' "${EVALS_DIR}/prompt-regression.sh"; then
  pass "prompt-regression.sh references prompt-baseline.json"
else
  fail "prompt-regression.sh missing prompt-baseline.json reference"
fi

# Baseline dataset exists
if [[ -f "${EVALS_DIR}/datasets/prompt-baseline.json" ]]; then
  pass "prompt-baseline.json dataset exists"
else
  fail "prompt-baseline.json dataset missing"
fi

# Script references hook-evals.sh for re-running on changes
if grep -q 'hook-evals.sh' "${EVALS_DIR}/prompt-regression.sh"; then
  pass "prompt-regression.sh references hook-evals.sh for regression"
else
  fail "prompt-regression.sh missing hook-evals.sh regression reference"
fi

# ─── ROOT_DIR computation tests ──────────────────────────────────

printf '\n\033[1m=== ROOT_DIR Resolution Tests ===\033[0m\n'

# Verify ROOT_DIR resolves to repository root from evals/
for script in hook-evals.sh state-evals.sh prompt-regression.sh; do
  if grep -q 'SCRIPT_DIR}/.."' "${EVALS_DIR}/${script}"; then
    pass "${script}: ROOT_DIR resolves one level up (correct for evals/)"
  else
    fail "${script}: ROOT_DIR does not resolve one level up"
  fi
done

# ─── Dataset file integrity ──────────────────────────────────────

printf '\n\033[1m=== Dataset Integrity Tests ===\033[0m\n'

if command -v jq >/dev/null 2>&1; then
  for dataset in "${EVALS_DIR}"/datasets/*.json; do
    basename="$(basename "${dataset}")"
    if jq -e . "${dataset}" >/dev/null 2>&1; then
      pass "dataset ${basename} is valid JSON"
    else
      fail "dataset ${basename} is invalid JSON"
    fi
  done

  # Check persona example datasets
  for example in "${EVALS_DIR}"/datasets/persona-examples/*.json; do
    basename="$(basename "${example}")"
    if jq -e '.trace_id' "${example}" >/dev/null 2>&1; then
      pass "persona example ${basename} has trace_id"
    else
      fail "persona example ${basename} missing trace_id"
    fi
    if jq -e '.tool_calls' "${example}" >/dev/null 2>&1; then
      pass "persona example ${basename} has tool_calls"
    else
      fail "persona example ${basename} missing tool_calls"
    fi
  done
else
  printf '  SKIP: jq not available for dataset validation\n'
fi

# ─── Shebang and strict mode in all bash scripts ────────────────

printf '\n\033[1m=== Script Conventions Tests ===\033[0m\n'

for script in \
  "${EVALS_DIR}/run-evals.sh" \
  "${EVALS_DIR}/hook-evals.sh" \
  "${EVALS_DIR}/state-evals.sh" \
  "${EVALS_DIR}/prompt-regression.sh" \
  "${JUDGES_DIR}/run-judges.sh"; do

  basename="$(basename "${script}")"

  if head -1 "${script}" | grep -q '#!/usr/bin/env bash'; then
    pass "${basename}: correct shebang"
  else
    fail "${basename}: incorrect shebang"
  fi

  if head -3 "${script}" | grep -q 'set -euo pipefail'; then
    pass "${basename}: strict mode enabled"
  else
    fail "${basename}: strict mode missing"
  fi

  if [[ -x "${script}" ]]; then
    pass "${basename}: is executable"
  else
    fail "${basename}: not executable"
  fi
done

# ─── Summary ─────────────────────────────────────────────────────

printf '\n\033[1m=== Bash Script Tests Summary ===\033[0m\n'
printf '  Passed:  %d\n' "${passes}"
printf '  Failed:  %d\n' "${failures}"

if [[ "${failures}" -gt 0 ]]; then
  printf '\n\033[31m%d test(s) failed.\033[0m\n' "${failures}"
  exit 1
else
  printf '\n\033[32mAll bash script tests passed.\033[0m\n'
  exit 0
fi
