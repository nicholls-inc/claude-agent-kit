#!/usr/bin/env bash
set -euo pipefail

# detect-ulw.sh — Detect ultrawork/ulw keyword in text.
#
# CONTRACT:
#   - Accept text on stdin or as $1.
#   - Exit 0 if "ulw" or "ultrawork" appears as a standalone word.
#   - Exit 1 if not found.
#   - Word-boundary match only: "bulwark" must NOT match.
#
# USAGE:
#   echo "enable ulw mode" | ./detect-ulw.sh    # exit 0
#   ./detect-ulw.sh "please use ultrawork"       # exit 0
#   echo "bulwark" | ./detect-ulw.sh             # exit 1

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

# --- Word-boundary match using grep -iwP (Perl regex) or fallback ---
# Pattern: standalone "ulw" or "ultrawork" (case-insensitive, word-boundary)

_match_with_grep_perl() {
  printf '%s' "${INPUT}" | grep -iqP '\b(ulw|ultrawork)\b'
}

_match_with_grep_extended() {
  # POSIX ERE: use [[:<:]] / [[:>:]] on macOS, \b may not work everywhere.
  # Fallback: surround with spaces/anchors for word-boundary simulation.
  local padded
  padded=" ${INPUT} "
  printf '%s' "${padded}" | grep -iqE '(^|[^a-zA-Z0-9_])(ulw|ultrawork)([^a-zA-Z0-9_]|$)'
}

if _match_with_grep_perl 2>/dev/null; then
  exit 0
elif _match_with_grep_extended 2>/dev/null; then
  exit 0
else
  exit 1
fi
