#!/usr/bin/env bash
set -euo pipefail

# sanitize-hook-input.sh — Defensive parsing of CC hook stdin JSON.
#
# CONTRACT:
#   - Parse stdin JSON (passed via SANITIZE_INPUT env var or stdin).
#   - Use jq if available; fall back to grep/sed extraction.
#   - Never eval any input content.
#   - Redact fields named: token, key, secret, password.
#
# USAGE:
#   Sourced by hook-router.sh — not typically run standalone.
#   export SANITIZE_INPUT='{"event":"PreToolUse","tool_name":"Bash"}'
#   source sanitize-hook-input.sh
#   echo "$HOOK_EVENT"  # PreToolUse

readonly _MAX_PROMPT_LENGTH=2000
readonly _REDACTED="[REDACTED]"
readonly _HOOK_INPUT_DEBUG_DIR=".sisyphus/evidence/cc-omo-parity/hook-input"

# --- Gather raw JSON input ---
_RAW_JSON="${SANITIZE_INPUT:-}"
if [[ -z "${_RAW_JSON}" ]] && [[ ! -t 0 ]]; then
  _RAW_JSON="$(cat)"
fi

# --- Redact sensitive fields from raw JSON ---
_redact_sensitive() {
  local json="$1"
  # Replace values for sensitive field names (token, key, secret, password).
  # Works with both jq and sed fallback.
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${json}" | jq -c '
      walk(if type == "object" then
        with_entries(
          if (.key | test("(?i)token|key|secret|password")) then .value = "[REDACTED]"
          else . end
        )
      else . end)
    ' 2>/dev/null || printf '%s' "${json}"
  else
    # Fallback: sed-based redaction for "key": "value" patterns
    printf '%s' "${json}" \
      | sed -E 's/("(token|key|secret|password)"[[:space:]]*:[[:space:]]*)"[^"]*"/\1"[REDACTED]"/gI' 2>/dev/null \
      || printf '%s' "${json}"
  fi
}

# --- Extract a field value from JSON ---
_extract_field() {
  local json="$1"
  local field="$2"

  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${json}" | jq -r ".${field} // empty" 2>/dev/null || true
  else
    # Fallback: basic grep/sed extraction (handles simple flat JSON)
    printf '%s' "${json}" \
      | sed -n "s/.*\"${field}\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" 2>/dev/null \
      | head -1 || true
  fi
}

_extract_field_multi() {
  local json="$1"
  local expr="$2"

  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${json}" | jq -r "${expr} // empty" 2>/dev/null || true
  else
    printf '%s' "${json}" \
      | sed -n "s/.*\"[A-Za-z0-9_]*\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" 2>/dev/null \
      | awk 'NR==1{print; exit}' || true
  fi
}

# --- Truncate string to max length ---
_truncate() {
  local str="$1"
  local max="$2"
  if [[ "${#str}" -gt "${max}" ]]; then
    printf '%s' "${str:0:${max}}"
  else
    printf '%s' "${str}"
  fi
}

# --- Parse and export safe variables ---
_SAFE_JSON="$(_redact_sensitive "${_RAW_JSON}")"

HOOK_EVENT="$(_extract_field_multi "${_SAFE_JSON}" '.event // .hook_event // .type')"
HOOK_TOOL_NAME="$(_extract_field_multi "${_SAFE_JSON}" '.tool_name // .toolName // .tool // .name // .tool?.name')"

_command_raw="$(_extract_field_multi "${_SAFE_JSON}" '.command // .tool_input?.command // .input?.command // .toolInput?.command')"
HOOK_TOOL_COMMAND="$(_truncate "${_command_raw}" "${_MAX_PROMPT_LENGTH}")"

_args_raw="$(_extract_field_multi "${_SAFE_JSON}" '.arguments // .tool_input?.arguments // .input?.arguments // .toolInput?.arguments')"
HOOK_TOOL_ARGS="$(_truncate "${_args_raw}" "${_MAX_PROMPT_LENGTH}")"

HOOK_SESSION_ID="$(_extract_field_multi "${_SAFE_JSON}" '.session_id // .sessionId // .session?.id')"

_assistant_raw="$(_extract_field_multi "${_SAFE_JSON}" '.assistant_message // .assistant?.message // .output // .response // .completion')"
HOOK_ASSISTANT_TEXT="$(_truncate "${_assistant_raw}" "${_MAX_PROMPT_LENGTH}")"

_raw_prompt="$(_extract_field "${_SAFE_JSON}" "prompt")"
if [[ -z "${_raw_prompt}" ]]; then
  _raw_prompt="$(_extract_field_multi "${_SAFE_JSON}" '.input // .text // .message // .user_prompt')"
fi
HOOK_PROMPT="$(_truncate "${_raw_prompt}" "${_MAX_PROMPT_LENGTH}")"

export HOOK_EVENT
export HOOK_TOOL_NAME
export HOOK_PROMPT
export HOOK_TOOL_COMMAND
export HOOK_TOOL_ARGS
export HOOK_SESSION_ID
export HOOK_ASSISTANT_TEXT

if [[ "${OMO_DEBUG:-}" == "1" ]]; then
  mkdir -p "${_HOOK_INPUT_DEBUG_DIR}" 2>/dev/null || true
  printf '%s\n' "${_SAFE_JSON}" > "${_HOOK_INPUT_DEBUG_DIR}/latest-redacted.json" 2>/dev/null || true
fi

# Clean up internal vars
unset _RAW_JSON _SAFE_JSON _raw_prompt _command_raw _args_raw _assistant_raw
