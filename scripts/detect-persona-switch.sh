#!/usr/bin/env bash
set -euo pipefail

# detect-persona-switch.sh — Detect persona skill invocations in text.
#
# CONTRACT:
#   - Accept text on stdin or as $1.
#   - If a persona skill invocation is found (e.g., /claude-agent-kit:sisyphus):
#     print the persona name to stdout, exit 0.
#   - If not found: print nothing, exit 1.
#   - Requires the claude-agent-kit: namespace prefix to avoid false positives.
#
# USAGE:
#   echo "/claude-agent-kit:hephaestus" | ./detect-persona-switch.sh  # prints "hephaestus", exit 0
#   ./detect-persona-switch.sh "/claude-agent-kit:sisyphus"            # prints "sisyphus", exit 0
#   echo "/claude-agent-kit:plan" | ./detect-persona-switch.sh         # exit 1
#   echo "switch to sisyphus" | ./detect-persona-switch.sh             # exit 1

# --- Gather input: $1 or stdin ---
INPUT=""
if [[ $# -ge 1 ]]; then
  INPUT="$1"
elif [[ ! -t 0 ]]; then
  INPUT="$(cat)"
fi

if [[ -z "${INPUT}" ]]; then
  exit 1
fi

# --- Extract persona name from skill invocation ---
# Pattern: optional leading /, then claude-agent-kit: followed by a persona name
# Case-insensitive match, requires namespace prefix

_extract_with_grep_perl() {
  printf '%s' "${INPUT}" | grep -ioP '/?claude-agent-kit:(sisyphus|hephaestus|atlas|prometheus)' | head -1 | sed 's/.*://' | tr '[:upper:]' '[:lower:]'
}

_extract_with_grep_extended() {
  printf '%s' "${INPUT}" | grep -ioE '/?claude-agent-kit:(sisyphus|hephaestus|atlas|prometheus)' | head -1 | sed 's/.*://' | tr '[:upper:]' '[:lower:]'
}

persona=""
persona="$(_extract_with_grep_perl 2>/dev/null)" || true

if [[ -z "${persona}" ]]; then
  persona="$(_extract_with_grep_extended 2>/dev/null)" || true
fi

if [[ -n "${persona}" ]]; then
  printf '%s' "${persona}"
  exit 0
else
  exit 1
fi
