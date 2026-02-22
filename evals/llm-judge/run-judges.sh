#!/usr/bin/env bash
set -euo pipefail

# run-judges.sh — Run all LLM-as-judge evaluations.
#
# Processes recent Langfuse traces through persona, plan, search, and oracle judges.
# Intended to be run weekly or on prompt changes.
#
# USAGE:
#   ./evals/llm-judge/run-judges.sh [--days 7] [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVALS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DAYS="${1:-7}"
DRY_RUN=""

for arg in "$@"; do
  case "${arg}" in
    --days)
      shift
      DAYS="${1:-7}"
      shift
      ;;
    --dry-run)
      DRY_RUN="--dry-run"
      ;;
  esac
done

printf '\033[1m=== Running LLM-as-Judge Evaluations ===\033[0m\n'
printf '  Days: %s\n' "${DAYS}"
printf '  Dry run: %s\n\n' "${DRY_RUN:-no}"

# Check uv is available
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

suites_run=0
suites_failed=0

run_judge() {
  local name="$1"
  local script="$2"
  shift 2

  printf '\n\033[1;34m━━━ %s ━━━\033[0m\n' "${name}"

  if uv run "${script}" --days "${DAYS}" ${DRY_RUN} "$@"; then
    suites_run=$((suites_run + 1))
  else
    suites_failed=$((suites_failed + 1))
    suites_run=$((suites_run + 1))
  fi
}

# Session signals (no LLM, fast)
run_judge "Session Signals" "${EVALS_DIR}/session-signals.py"

# Persona trace analysis (no LLM, fast)
run_judge "Persona Trace Analysis" "${EVALS_DIR}/persona-trace-analyzer.py"

# LLM-as-judge evaluations (uses Claude Sonnet, slower)
run_judge "Persona Judge" "${SCRIPT_DIR}/judge-persona.py"

printf '\n\033[1;34m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m\n'
printf '\033[1m=== Judge Suite Summary ===\033[0m\n'
printf '  Judges run:    %d\n' "${suites_run}"
printf '  Judges failed: %d\n' "${suites_failed}"

if [[ "${suites_failed}" -gt 0 ]]; then
  printf '\n\033[31m%d judge(s) failed.\033[0m\n' "${suites_failed}"
  exit 1
else
  printf '\n\033[32mAll judges completed successfully.\033[0m\n'
  exit 0
fi
