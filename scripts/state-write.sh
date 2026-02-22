#!/usr/bin/env bash
set -euo pipefail

# state-write.sh — Atomic JSON state file writer.
#
# CONTRACT:
#   - Accept file path as $1 and JSON content as $2 (or stdin).
#   - Write to a temp file then mv (atomic write).
#   - Create parent directory if missing.
#   - Exit 0 on success, exit 1 on failure.
#   - Never print errors to stdout — errors go to stderr only.
#
# USAGE:
#   ./state-write.sh .sisyphus/boulder.json '{"task": 1}'
#   echo '{"task": 1}' | ./state-write.sh .sisyphus/boulder.json

STATE_FILE="${1:-}"

if [[ -z "${STATE_FILE}" ]]; then
  echo "state-write: missing file path argument" >&2
  exit 1
fi

# --- Read JSON content from $2 or stdin ---
JSON_CONTENT="${2:-}"
if [[ -z "${JSON_CONTENT}" ]] && [[ ! -t 0 ]]; then
  JSON_CONTENT="$(cat)"
fi

if [[ -z "${JSON_CONTENT}" ]]; then
  echo "state-write: no JSON content provided" >&2
  exit 1
fi

# --- Ensure parent directory exists ---
PARENT_DIR="$(dirname "${STATE_FILE}")"
if [[ -n "${PARENT_DIR}" ]] && [[ "${PARENT_DIR}" != "." ]]; then
  if ! mkdir -p "${PARENT_DIR}" 2>/dev/null; then
    echo "state-write: failed to create directory ${PARENT_DIR}" >&2
    exit 1
  fi
fi

# --- Atomic write: temp file + mv ---
TEMP_FILE=""
LOCK_DIR="${STATE_FILE}.lock"
_cleanup() {
  if [[ -d "${LOCK_DIR}" ]]; then
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
  if [[ -n "${TEMP_FILE}" ]] && [[ -f "${TEMP_FILE}" ]]; then
    rm -f "${TEMP_FILE}" 2>/dev/null || true
  fi
}
trap _cleanup EXIT

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "state-write: lock busy for ${STATE_FILE}" >&2
  exit 1
fi

TEMP_FILE="$(mktemp "${PARENT_DIR}/.state-write.XXXXXX" 2>/dev/null)" || {
  echo "state-write: failed to create temp file" >&2
  exit 1
}

if ! printf '%s\n' "${JSON_CONTENT}" > "${TEMP_FILE}"; then
  echo "state-write: failed to write temp file" >&2
  exit 1
fi

if ! mv "${TEMP_FILE}" "${STATE_FILE}"; then
  echo "state-write: failed to move temp file to ${STATE_FILE}" >&2
  exit 1
fi

# mv succeeded, clear TEMP_FILE so cleanup doesn't try to remove it
TEMP_FILE=""

exit 0
