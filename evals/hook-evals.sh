#!/usr/bin/env bash
set -euo pipefail

# hook-evals.sh — Deterministic tests for hook-router.sh behavioral contracts.
#
# Tests: ULW detection, PreToolUse blocking, Prometheus write guard,
#        SessionStart persona injection, boulder resume, Stop continuation.
#
# Requires: jq

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASETS="${SCRIPT_DIR}/datasets"

# Temp workspace for state files
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

# ─── Dependency check ───────────────────────────────────────────────

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required for hook-evals.sh" >&2
  exit 1
fi

# ─── ULW Detection Tests ────────────────────────────────────────────

printf '\n\033[1m=== ULW Detection (detect-ulw.sh) ===\033[0m\n'

ULW_SCRIPT="${ROOT_DIR}/scripts/detect-ulw.sh"
ULW_DATASET="${DATASETS}/ulw-triggers.json"

if [[ ! -x "${ULW_SCRIPT}" ]]; then
  fail "detect-ulw.sh not found or not executable"
else
  count=$(jq '.cases | length' "${ULW_DATASET}")
  for i in $(seq 0 $((count - 1))); do
    input=$(jq -r ".cases[$i].input" "${ULW_DATASET}")
    expect=$(jq -r ".cases[$i].expect_match" "${ULW_DATASET}")
    note=$(jq -r ".cases[$i].note" "${ULW_DATASET}")

    if printf '%s' "${input}" | "${ULW_SCRIPT}" >/dev/null 2>&1; then
      matched="true"
    else
      matched="false"
    fi

    if [[ "${matched}" == "${expect}" ]]; then
      pass "ULW: ${note} (input='${input}', expect=${expect})"
    else
      fail "ULW: ${note} (input='${input}', expect=${expect}, got=${matched})"
    fi
  done
fi

# ─── PreToolUse Blocking Tests ──────────────────────────────────────

printf '\n\033[1m=== PreToolUse Blocking (hook-router.sh) ===\033[0m\n'

HOOK_ROUTER="${ROOT_DIR}/scripts/hook-router.sh"
PRETOOL_DATASET="${DATASETS}/pretool-cases.json"

_run_pretool_test() {
  local tool_name="$1"
  local command="$2"
  local persona="${3:-sisyphus}"

  # Set up minimal runtime state
  local runtime_dir="${WORK_DIR}/.agent-kit/state"
  mkdir -p "${runtime_dir}"
  local runtime_file="${WORK_DIR}/.agent-kit/state/runtime.local.json"
  printf '{"version":1,"sessions":{"global":{"activePersona":"%s"}}}' "${persona}" > "${runtime_file}"

  # Build stdin JSON
  local stdin_json
  stdin_json=$(jq -n --arg tn "${tool_name}" --arg cmd "${command}" '{
    hook_event: "PreToolUse",
    tool_name: $tn,
    tool_input: { command: $cmd }
  }')

  # Run hook-router in the work dir context
  local output
  output=$(cd "${WORK_DIR}" && printf '%s' "${stdin_json}" | \
    HOOK_EVENT="PreToolUse" HOOK_TOOL_NAME="${tool_name}" HOOK_TOOL_COMMAND="${command}" \
    AGENT_KIT_DEBUG="" "${HOOK_ROUTER}" "PreToolUse" 2>/dev/null) || true

  printf '%s' "${output}"
}

if [[ ! -x "${HOOK_ROUTER}" ]]; then
  fail "hook-router.sh not found or not executable"
else
  # Standard cases (non-prometheus)
  count=$(jq '.cases | length' "${PRETOOL_DATASET}")
  for i in $(seq 0 $((count - 1))); do
    tool_name=$(jq -r ".cases[$i].tool_name" "${PRETOOL_DATASET}")
    command=$(jq -r ".cases[$i].command" "${PRETOOL_DATASET}")
    expect_block=$(jq -r ".cases[$i].expect_block" "${PRETOOL_DATASET}")
    note=$(jq -r ".cases[$i].note" "${PRETOOL_DATASET}")

    output=$(_run_pretool_test "${tool_name}" "${command}" "sisyphus")

    if [[ "${expect_block}" == "true" ]]; then
      if printf '%s' "${output}" | grep -q '"decision":"block"'; then
        pass "PreToolUse: ${note}"
      else
        fail "PreToolUse: ${note} (expected block, got: '${output}')"
      fi
    else
      if [[ -z "${output}" ]] || ! printf '%s' "${output}" | grep -q '"decision":"block"'; then
        pass "PreToolUse: ${note}"
      else
        fail "PreToolUse: ${note} (expected allow, got: '${output}')"
      fi
    fi
  done

  # Prometheus cases
  printf '\n\033[1m=== Prometheus Write Guard ===\033[0m\n'

  pcount=$(jq '.prometheus_cases | length' "${PRETOOL_DATASET}")
  for i in $(seq 0 $((pcount - 1))); do
    tool_name=$(jq -r ".prometheus_cases[$i].tool_name" "${PRETOOL_DATASET}")
    command=$(jq -r ".prometheus_cases[$i].command" "${PRETOOL_DATASET}")
    expect_block=$(jq -r ".prometheus_cases[$i].expect_block" "${PRETOOL_DATASET}")
    note=$(jq -r ".prometheus_cases[$i].note" "${PRETOOL_DATASET}")

    output=$(_run_pretool_test "${tool_name}" "${command}" "prometheus")

    if [[ "${expect_block}" == "true" ]]; then
      if printf '%s' "${output}" | grep -q '"decision":"block"'; then
        pass "Prometheus: ${note}"
      else
        fail "Prometheus: ${note} (expected block, got: '${output}')"
      fi
    else
      if [[ -z "${output}" ]] || ! printf '%s' "${output}" | grep -q '"decision":"block"'; then
        pass "Prometheus: ${note}"
      else
        fail "Prometheus: ${note} (expected allow, got: '${output}')"
      fi
    fi
  done
fi

# ─── SessionStart Persona Injection Tests ───────────────────────────

printf '\n\033[1m=== SessionStart Persona Injection ===\033[0m\n'

HOOK_DATASET="${DATASETS}/hook-inputs.json"

_run_session_start() {
  local persona="$1"

  local runtime_dir="${WORK_DIR}/.agent-kit/state"
  mkdir -p "${runtime_dir}"
  local runtime_file="${WORK_DIR}/.agent-kit/state/runtime.local.json"
  printf '{"version":1,"sessions":{"global":{"activePersona":"%s"}}}' "${persona}" > "${runtime_file}"

  # Ensure no boulder active
  rm -f "${WORK_DIR}/.agent-kit/boulder.json" 2>/dev/null || true

  local stdin_json='{"hook_event":"SessionStart"}'

  cd "${WORK_DIR}" && printf '%s' "${stdin_json}" | \
    HOOK_EVENT="SessionStart" AGENT_KIT_DEBUG="" "${HOOK_ROUTER}" "SessionStart" 2>/dev/null || true
}

if [[ -x "${HOOK_ROUTER}" ]]; then
  pcount=$(jq '.session_start.personas | length' "${HOOK_DATASET}")
  for i in $(seq 0 $((pcount - 1))); do
    persona=$(jq -r ".session_start.personas[$i].persona" "${HOOK_DATASET}")
    expect=$(jq -r ".session_start.personas[$i].expect_contains" "${HOOK_DATASET}")
    note=$(jq -r ".session_start.personas[$i].note" "${HOOK_DATASET}")

    output=$(_run_session_start "${persona}")

    if printf '%s' "${output}" | grep -q "${expect}"; then
      pass "SessionStart: ${note} (contains '${expect}')"
    else
      fail "SessionStart: ${note} (expected '${expect}' in output)"
    fi
  done
fi

# ─── Boulder Resume Injection Tests ────────────────────────────────

printf '\n\033[1m=== Boulder Resume Injection ===\033[0m\n'

_run_session_start_with_boulder() {
  local runtime_dir="${WORK_DIR}/.agent-kit/state"
  mkdir -p "${runtime_dir}"
  local runtime_file="${WORK_DIR}/.agent-kit/state/runtime.local.json"
  printf '{"version":1,"sessions":{"global":{"activePersona":"sisyphus"}}}' > "${runtime_file}"

  # Set up active boulder
  local boulder_json
  boulder_json=$(jq -c '.' <<< "$(jq '.session_start.boulder_resume.boulder_json' "${HOOK_DATASET}")")
  printf '%s' "${boulder_json}" > "${WORK_DIR}/.agent-kit/boulder.json"

  local stdin_json='{"hook_event":"SessionStart"}'

  cd "${WORK_DIR}" && printf '%s' "${stdin_json}" | \
    HOOK_EVENT="SessionStart" AGENT_KIT_DEBUG="" "${HOOK_ROUTER}" "SessionStart" 2>/dev/null || true
}

if [[ -x "${HOOK_ROUTER}" ]]; then
  expect_plan=$(jq -r '.session_start.boulder_resume.expect_contains_plan_path' "${HOOK_DATASET}")
  expect_resume=$(jq -r '.session_start.boulder_resume.expect_contains_resume' "${HOOK_DATASET}")

  output=$(_run_session_start_with_boulder)

  if printf '%s' "${output}" | grep -q "${expect_plan}"; then
    pass "Boulder resume: contains plan path '${expect_plan}'"
  else
    fail "Boulder resume: expected plan path '${expect_plan}' in output"
  fi

  if printf '%s' "${output}" | grep -q "${expect_resume}"; then
    pass "Boulder resume: contains '${expect_resume}'"
  else
    fail "Boulder resume: expected '${expect_resume}' in output"
  fi
fi

# ─── Stop Continuation Tests ───────────────────────────────────────

printf '\n\033[1m=== Stop Continuation ===\033[0m\n'

_run_stop_test() {
  local runtime_json="$1"

  local runtime_dir="${WORK_DIR}/.agent-kit/state"
  mkdir -p "${runtime_dir}"
  printf '%s' "${runtime_json}" > "${WORK_DIR}/.agent-kit/state/runtime.local.json"

  # Ensure no boulder or ralph active (unless test sets them)
  rm -f "${WORK_DIR}/.agent-kit/boulder.json" 2>/dev/null || true
  rm -f "${WORK_DIR}/.agent-kit/ralph-loop.local.md" 2>/dev/null || true

  local stdin_json='{"hook_event":"Stop"}'

  cd "${WORK_DIR}" && printf '%s' "${stdin_json}" | \
    HOOK_EVENT="Stop" AGENT_KIT_DEBUG="" "${HOOK_ROUTER}" "Stop" 2>/dev/null || true
}

if [[ -x "${HOOK_ROUTER}" ]]; then
  # ULW enabled → should block
  runtime_json=$(jq -c '.stop.ulw_enabled.runtime_json' "${HOOK_DATASET}")
  expect_block=$(jq -r '.stop.ulw_enabled.expect_block' "${HOOK_DATASET}")
  note=$(jq -r '.stop.ulw_enabled.note' "${HOOK_DATASET}")

  output=$(_run_stop_test "${runtime_json}")

  if [[ "${expect_block}" == "true" ]]; then
    if printf '%s' "${output}" | grep -q '"decision":"block"'; then
      pass "Stop: ${note}"
    else
      fail "Stop: ${note} (expected block, got: '${output}')"
    fi
  fi

  # All disabled → should allow
  runtime_json=$(jq -c '.stop.all_disabled.runtime_json' "${HOOK_DATASET}")
  note=$(jq -r '.stop.all_disabled.note' "${HOOK_DATASET}")

  output=$(_run_stop_test "${runtime_json}")

  if [[ -z "${output}" ]] || ! printf '%s' "${output}" | grep -q '"decision":"block"'; then
    pass "Stop: ${note}"
  else
    fail "Stop: ${note} (expected allow, got: '${output}')"
  fi

  # Max blocks reached → should auto-disable and allow
  runtime_json=$(jq -c '.stop.max_blocks_reached.runtime_json' "${HOOK_DATASET}")
  note=$(jq -r '.stop.max_blocks_reached.note' "${HOOK_DATASET}")

  output=$(_run_stop_test "${runtime_json}")

  if [[ -z "${output}" ]] || ! printf '%s' "${output}" | grep -q '"decision":"block"'; then
    pass "Stop: ${note}"
  else
    fail "Stop: ${note} (expected allow after max blocks, got: '${output}')"
  fi

  # Continuation disabled → should allow
  runtime_json=$(jq -c '.stop.continuation_disabled.runtime_json' "${HOOK_DATASET}")
  note=$(jq -r '.stop.continuation_disabled.note' "${HOOK_DATASET}")

  output=$(_run_stop_test "${runtime_json}")

  if [[ -z "${output}" ]] || ! printf '%s' "${output}" | grep -q '"decision":"block"'; then
    pass "Stop: ${note}"
  else
    fail "Stop: ${note} (expected allow when disabled, got: '${output}')"
  fi
fi

# ─── Summary ────────────────────────────────────────────────────────

printf '\n\033[1m=== Hook Evals Summary ===\033[0m\n'
printf '  Passed:  %d\n' "${passes}"
printf '  Failed:  %d\n' "${failures}"

if [[ "${failures}" -gt 0 ]]; then
  printf '\n\033[31m%d hook eval(s) failed.\033[0m\n' "${failures}"
  exit 1
else
  printf '\n\033[32mAll hook evals passed.\033[0m\n'
  exit 0
fi
