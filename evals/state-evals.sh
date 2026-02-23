#!/usr/bin/env bash
set -euo pipefail

# state-evals.sh — Deterministic tests for state-read.sh and state-write.sh.
#
# Tests: missing file fallback, corrupt file fallback, write+read roundtrip,
#        concurrent write safety.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

STATE_READ="${ROOT_DIR}/scripts/state-read.sh"
STATE_WRITE="${ROOT_DIR}/scripts/state-write.sh"

# Temp workspace
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

if [[ ! -x "${STATE_READ}" ]]; then
  echo "ERROR: state-read.sh not found or not executable" >&2
  exit 1
fi
if [[ ! -x "${STATE_WRITE}" ]]; then
  echo "ERROR: state-write.sh not found or not executable" >&2
  exit 1
fi

# ─── state-read.sh Tests ────────────────────────────────────────────

printf '\n\033[1m=== state-read.sh ===\033[0m\n'

# Missing file returns {}
output=$("${STATE_READ}" "${WORK_DIR}/nonexistent.json")
if [[ "${output}" == "{}" ]]; then
  pass "state-read: missing file returns {}"
else
  fail "state-read: missing file returns '${output}', expected '{}'"
fi

# Empty path returns {}
output=$("${STATE_READ}" "")
if [[ "${output}" == "{}" ]]; then
  pass "state-read: empty path returns {}"
else
  fail "state-read: empty path returns '${output}', expected '{}'"
fi

# Corrupt file returns {}
printf 'not valid json at all' > "${WORK_DIR}/corrupt.json"
output=$("${STATE_READ}" "${WORK_DIR}/corrupt.json")
if [[ "${output}" == "{}" ]]; then
  pass "state-read: corrupt file returns {}"
else
  fail "state-read: corrupt file returns '${output}', expected '{}'"
fi

# Empty file returns {}
printf '' > "${WORK_DIR}/empty.json"
output=$("${STATE_READ}" "${WORK_DIR}/empty.json")
if [[ "${output}" == "{}" ]]; then
  pass "state-read: empty file returns {}"
else
  fail "state-read: empty file returns '${output}', expected '{}'"
fi

# Valid JSON file returns contents
printf '{"hello":"world"}' > "${WORK_DIR}/valid.json"
output=$("${STATE_READ}" "${WORK_DIR}/valid.json")
if printf '%s' "${output}" | grep -q '"hello"'; then
  pass "state-read: valid JSON preserves content"
else
  fail "state-read: valid JSON not preserved, got '${output}'"
fi

# Creates parent directory
output=$("${STATE_READ}" "${WORK_DIR}/deep/nested/dir/file.json")
if [[ -d "${WORK_DIR}/deep/nested/dir" ]]; then
  pass "state-read: creates parent directory"
else
  fail "state-read: did not create parent directory"
fi

# ─── state-write.sh Tests ───────────────────────────────────────────

printf '\n\033[1m=== state-write.sh ===\033[0m\n'

# Basic write succeeds
"${STATE_WRITE}" "${WORK_DIR}/write-test.json" '{"key":"value"}'
if [[ -f "${WORK_DIR}/write-test.json" ]]; then
  pass "state-write: creates file"
else
  fail "state-write: file not created"
fi

# Write + read roundtrip preserves fields
test_json='{"version":1,"active":true,"planPath":".agent-kit/plans/test.md"}'
"${STATE_WRITE}" "${WORK_DIR}/roundtrip.json" "${test_json}"
output=$("${STATE_READ}" "${WORK_DIR}/roundtrip.json")
if printf '%s' "${output}" | grep -q '"planPath"'; then
  pass "state-write: roundtrip preserves planPath"
else
  fail "state-write: roundtrip lost planPath, got '${output}'"
fi
if printf '%s' "${output}" | grep -q '"active":true'; then
  pass "state-write: roundtrip preserves active flag"
else
  fail "state-write: roundtrip lost active flag, got '${output}'"
fi

# Creates parent directory
"${STATE_WRITE}" "${WORK_DIR}/new/dir/state.json" '{"created":true}'
if [[ -f "${WORK_DIR}/new/dir/state.json" ]]; then
  pass "state-write: creates nested parent directory"
else
  fail "state-write: did not create nested directory"
fi

# Write with stdin
printf '{"stdin":true}' | "${STATE_WRITE}" "${WORK_DIR}/stdin-test.json"
output=$("${STATE_READ}" "${WORK_DIR}/stdin-test.json")
if printf '%s' "${output}" | grep -q '"stdin":true'; then
  pass "state-write: accepts stdin input"
else
  fail "state-write: stdin input not preserved, got '${output}'"
fi

# Missing path fails
if "${STATE_WRITE}" "" '{"bad":true}' 2>/dev/null; then
  fail "state-write: empty path should fail"
else
  pass "state-write: empty path returns error"
fi

# Missing content fails
if "${STATE_WRITE}" "${WORK_DIR}/no-content.json" 2>/dev/null </dev/null; then
  fail "state-write: no content should fail"
else
  pass "state-write: no content returns error"
fi

# ─── Concurrent Write Safety ───────────────────────────────────────

printf '\n\033[1m=== Concurrent Write Safety ===\033[0m\n'

# Two rapid sequential writes — both should survive (last wins)
"${STATE_WRITE}" "${WORK_DIR}/concurrent.json" '{"write":1}'
"${STATE_WRITE}" "${WORK_DIR}/concurrent.json" '{"write":2}'
output=$("${STATE_READ}" "${WORK_DIR}/concurrent.json")
if printf '%s' "${output}" | grep -q '"write":2'; then
  pass "concurrent: sequential writes — last write wins"
else
  fail "concurrent: sequential writes — expected write:2, got '${output}'"
fi

# Verify file is not corrupt after rapid writes
if command -v jq >/dev/null 2>&1; then
  if printf '%s' "${output}" | jq -e . >/dev/null 2>&1; then
    pass "concurrent: file is valid JSON after rapid writes"
  else
    fail "concurrent: file is corrupt after rapid writes"
  fi
fi

# ─── Summary ────────────────────────────────────────────────────────

printf '\n\033[1m=== State Evals Summary ===\033[0m\n'
printf '  Passed:  %d\n' "${passes}"
printf '  Failed:  %d\n' "${failures}"

if [[ "${failures}" -gt 0 ]]; then
  printf '\n\033[31m%d state eval(s) failed.\033[0m\n' "${failures}"
  exit 1
else
  printf '\n\033[32mAll state evals passed.\033[0m\n'
  exit 0
fi
