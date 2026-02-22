#!/usr/bin/env bash
set -euo pipefail

# state-read.sh — Fail-open JSON state file reader.
#
# CONTRACT:
#   - Accept a file path as $1.
#   - If file exists and contains valid JSON: print contents to stdout.
#   - If file is missing or corrupt: print "{}" to stdout and exit 0 (fail-open).
#   - Create parent directory if missing.
#   - Never print errors to stdout.
#
# USAGE:
#   ./state-read.sh .agent-kit/boulder.json
#   # prints JSON content or {} if missing/corrupt

STATE_FILE="${1:-}"

if [[ -z "${STATE_FILE}" ]]; then
  echo "{}"
  exit 0
fi

# --- Ensure parent directory exists ---
PARENT_DIR="$(dirname "${STATE_FILE}")"
if [[ -n "${PARENT_DIR}" ]] && [[ "${PARENT_DIR}" != "." ]]; then
  mkdir -p "${PARENT_DIR}" 2>/dev/null || true
fi

# --- Read and validate ---
if [[ ! -f "${STATE_FILE}" ]]; then
  echo "{}"
  exit 0
fi

CONTENT="$(cat "${STATE_FILE}" 2>/dev/null)" || {
  echo "{}"
  exit 0
}

if [[ -z "${CONTENT}" ]]; then
  echo "{}"
  exit 0
fi

# --- Validate JSON ---
if command -v jq >/dev/null 2>&1; then
  if printf '%s' "${CONTENT}" | jq -e . >/dev/null 2>&1; then
    printf '%s\n' "${CONTENT}"
    exit 0
  else
    echo "{}"
    exit 0
  fi
else
  # No jq: basic check — starts with { or [
  if [[ "${CONTENT}" =~ ^[[:space:]]*[\{\[] ]]; then
    printf '%s\n' "${CONTENT}"
    exit 0
  else
    echo "{}"
    exit 0
  fi
fi
