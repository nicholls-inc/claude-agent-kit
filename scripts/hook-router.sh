#!/usr/bin/env bash
set -euo pipefail

# hook-router.sh — Single entrypoint for all CC hook events.
#
# CONTRACT:
#   - Reads stdin JSON from CC hook events.
#   - First positional arg ($1) identifies the event type.
#   - Sources sanitize-hook-input.sh for safe input parsing.
#   - Dispatches to handler functions per event type.
#   - stdout rules:
#       SessionStart / UserPromptSubmit → plain text only (or empty)
#       PreToolUse / Stop               → valid JSON only (or empty)
#   - On ANY error: log to stderr, exit 0, print nothing to stdout (fail-open).
#
# ENV:
#   OMO_DEBUG=1  → write diagnostics to .sisyphus/evidence/cc-omo-parity/debug/
#                   (never to stdout)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly DEBUG_DIR=".sisyphus/evidence/cc-omo-parity/debug"
readonly BOULDER_FILE=".sisyphus/boulder.json"
readonly RUNTIME_FILE=".sisyphus/cc-omo/runtime.local.json"
readonly RALPH_FILE=".sisyphus/ralph-loop.local.md"
readonly SESSION_KEY_DEFAULT="global"
readonly STOP_MAX_BLOCKS=8
readonly STOP_COOLDOWN_SECONDS=3

# --- Fail-open trap: on ANY error, silence stdout and exit 0 ---
_fail_open() {
  local line="${1:-unknown}"
  echo "[hook-router] fail-open at line ${line}" >&2
  exit 0
}
trap '_fail_open ${LINENO}' ERR

# --- Debug helper: writes to debug dir, never stdout ---
_debug() {
  if [[ "${OMO_DEBUG:-}" == "1" ]]; then
    mkdir -p "${DEBUG_DIR}"
    local ts
    ts="$(date +%Y%m%dT%H%M%S 2>/dev/null || echo "unknown")"
    printf '%s %s\n' "${ts}" "$*" >> "${DEBUG_DIR}/hook-router.log"
  fi
}

_json_escape() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${1:-}" | jq -Rr @json
  else
    local s="${1:-}"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '"%s"' "${s}"
  fi
}

_emit_block_json() {
  local reason="$1"
  local escaped
  escaped="$(_json_escape "${reason}")"
  printf '{"decision":"block","reason":%s}\n' "${escaped}"
}

_read_json_file() {
  local file_path="$1"
  if [[ -x "${SCRIPT_DIR}/state-read.sh" ]]; then
    "${SCRIPT_DIR}/state-read.sh" "${file_path}"
  else
    echo "{}"
  fi
}

_write_json_file() {
  local file_path="$1"
  local json_content="$2"
  if [[ -x "${SCRIPT_DIR}/state-write.sh" ]]; then
    "${SCRIPT_DIR}/state-write.sh" "${file_path}" "${json_content}" >/dev/null
  else
    return 1
  fi
}

_now_epoch() {
  date +%s 2>/dev/null || echo "0"
}

_now_iso() {
  date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "1970-01-01T00:00:00Z"
}

_session_key() {
  if [[ -n "${HOOK_SESSION_ID:-}" ]]; then
    printf '%s' "${HOOK_SESSION_ID}"
  else
    printf '%s' "${SESSION_KEY_DEFAULT}"
  fi
}

_runtime_get() {
  local key="$1"
  local runtime_json
  runtime_json="$(_read_json_file "${RUNTIME_FILE}")"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "${runtime_json}" | jq -r "${key} // empty" 2>/dev/null || true
  else
    echo ""
  fi
}

_runtime_set_ulw_enabled() {
  local session_key
  session_key="$(_session_key)"
  local runtime_json
  runtime_json="$(_read_json_file "${RUNTIME_FILE}")"
  local updated
  if command -v jq >/dev/null 2>&1; then
    updated="$(printf '%s' "${runtime_json}" | jq -c --arg sk "${session_key}" --arg ts "$(_now_iso)" '
      .version = 1
      | .sessions = (.sessions // {})
      | .sessions[$sk] = (.sessions[$sk] // {})
      | .sessions[$sk].ulw = (.sessions[$sk].ulw // {})
      | .sessions[$sk].ulw.enabled = true
      | .sessions[$sk].ulw.updatedAt = $ts
      | .sessions[$sk].ulw.stopBlocks = (.sessions[$sk].ulw.stopBlocks // 0)
    ' 2>/dev/null)"
    if [[ -n "${updated}" ]]; then
      _write_json_file "${RUNTIME_FILE}" "${updated}" || true
    fi
  fi
}

_stop_continuation_disabled() {
  local session_key
  session_key="$(_session_key)"
  local runtime_json
  runtime_json="$(_read_json_file "${RUNTIME_FILE}")"
  if command -v jq >/dev/null 2>&1; then
    local version
    version="$(printf '%s' "${runtime_json}" | jq -r '.version // 1' 2>/dev/null || echo "1")"
    if [[ "${version}" != "1" ]]; then
      return 1
    fi
    local val
    val="$(printf '%s' "${runtime_json}" | jq -r --arg sk "${session_key}" '.sessions[$sk].stopContinuation.disabled // false' 2>/dev/null || echo "false")"
    [[ "${val}" == "true" ]]
  else
    grep -q '"stopContinuation"' "${RUNTIME_FILE}" 2>/dev/null && grep -q '"disabled"[[:space:]]*:[[:space:]]*true' "${RUNTIME_FILE}" 2>/dev/null
  fi
}

_boulder_active() {
  local boulder_json
  boulder_json="$(_read_json_file "${BOULDER_FILE}")"
  if command -v jq >/dev/null 2>&1; then
    local version
    version="$(printf '%s' "${boulder_json}" | jq -r '.version // 1' 2>/dev/null || echo "1")"
    if [[ "${version}" != "1" ]]; then
      return 1
    fi
    local active status
    active="$(printf '%s' "${boulder_json}" | jq -r '.active // false' 2>/dev/null || echo "false")"
    status="$(printf '%s' "${boulder_json}" | jq -r '.status // ""' 2>/dev/null || echo "")"
    [[ "${active}" == "true" && "${status}" != "done" ]]
  else
    grep -q '"active"[[:space:]]*:[[:space:]]*true' "${BOULDER_FILE}" 2>/dev/null
  fi
}

_ralph_active() {
  [[ -f "${RALPH_FILE}" ]] || return 1
  grep -qi '^status:[[:space:]]*active' "${RALPH_FILE}" 2>/dev/null || return 1

  if printf '%s %s' "${HOOK_ASSISTANT_TEXT:-}" "${HOOK_PROMPT:-}" | grep -q 'RALPH_DONE'; then
    perl -0pi -e 's/^status:\s*active/status: done/m' "${RALPH_FILE}" 2>/dev/null || true
    return 1
  fi

  local iterations max_iterations
  iterations="$(sed -n 's/^iterations:[[:space:]]*//p' "${RALPH_FILE}" 2>/dev/null | awk 'NR==1{print; exit}')"
  max_iterations="$(sed -n 's/^max_iterations:[[:space:]]*//p' "${RALPH_FILE}" 2>/dev/null | awk 'NR==1{print; exit}')"
  if [[ -n "${iterations}" && -n "${max_iterations}" ]] && [[ "${iterations}" =~ ^[0-9]+$ ]] && [[ "${max_iterations}" =~ ^[0-9]+$ ]]; then
    if [[ "${iterations}" -ge "${max_iterations}" ]]; then
      perl -0pi -e 's/^status:\s*active/status: done/m' "${RALPH_FILE}" 2>/dev/null || true
      return 1
    fi
  fi

  return 0
}

_increment_ralph_iteration() {
  [[ -f "${RALPH_FILE}" ]] || return 0
  local iterations next
  iterations="$(sed -n 's/^iterations:[[:space:]]*//p' "${RALPH_FILE}" 2>/dev/null | awk 'NR==1{print; exit}')"
  if [[ -z "${iterations}" || ! "${iterations}" =~ ^[0-9]+$ ]]; then
    iterations=0
  fi
  next=$((iterations + 1))

  if grep -q '^iterations:' "${RALPH_FILE}" 2>/dev/null; then
    perl -0pi -e "s/^iterations:\\s*\\d+/iterations: ${next}/m" "${RALPH_FILE}" 2>/dev/null || true
  else
    printf '\niterations: %s\n' "${next}" >> "${RALPH_FILE}" 2>/dev/null || true
  fi
}

_ulw_enabled() {
  local session_key
  session_key="$(_session_key)"
  local runtime_json
  runtime_json="$(_read_json_file "${RUNTIME_FILE}")"
  if command -v jq >/dev/null 2>&1; then
    local version
    version="$(printf '%s' "${runtime_json}" | jq -r '.version // 1' 2>/dev/null || echo "1")"
    if [[ "${version}" != "1" ]]; then
      return 1
    fi
    local enabled
    enabled="$(printf '%s' "${runtime_json}" | jq -r --arg sk "${session_key}" '.sessions[$sk].ulw.enabled // false' 2>/dev/null || echo "false")"
    [[ "${enabled}" == "true" ]]
  else
    grep -q '"ulw"' "${RUNTIME_FILE}" 2>/dev/null && grep -q '"enabled"[[:space:]]*:[[:space:]]*true' "${RUNTIME_FILE}" 2>/dev/null
  fi
}

_resume_block() {
  local boulder_json
  boulder_json="$(_read_json_file "${BOULDER_FILE}")"
  local plan_path=""
  local task_num=""
  local task_label=""
  if command -v jq >/dev/null 2>&1; then
    plan_path="$(printf '%s' "${boulder_json}" | jq -r '.planPath // empty' 2>/dev/null || true)"
    task_num="$(printf '%s' "${boulder_json}" | jq -r '.currentTask.number // empty' 2>/dev/null || true)"
    task_label="$(printf '%s' "${boulder_json}" | jq -r '.currentTask.label // empty' 2>/dev/null || true)"
  fi
  [[ -n "${plan_path}" ]] || return 0
  printf 'Resume context:\n'
  printf -- '- Active plan: %s\n' "${plan_path}"
  if [[ -n "${task_num}" || -n "${task_label}" ]]; then
    printf -- '- Current task: %s %s\n' "${task_num}" "${task_label}"
  fi
  printf -- '- Continue with /omo:start-work\n'
  printf -- '- Escape hatch: /omo:stop-continuation\n'
}

_active_persona() {
  local session_key runtime_json persona
  session_key="$(_session_key)"
  runtime_json="$(_read_json_file "${RUNTIME_FILE}")"
  if command -v jq >/dev/null 2>&1; then
    persona="$(printf '%s' "${runtime_json}" | jq -r --arg sk "${session_key}" 'if (.version // 1) == 1 then (.sessions[$sk].activePersona // "sisyphus") else "sisyphus" end' 2>/dev/null || echo "sisyphus")"
  else
    persona="sisyphus"
  fi
  case "${persona}" in
    sisyphus|hephaestus|prometheus|atlas) printf '%s' "${persona}" ;;
    *) printf 'sisyphus' ;;
  esac
}

_persona_injection_block() {
  local persona
  persona="$(_active_persona)"
  case "${persona}" in
    hephaestus)
      cat <<'EOF'
Persona: hephaestus
- Operate as a deep autonomous implementer.
- Focus on execution depth, verification, and completion.
- Keep orchestration simple; do not use nested delegation.
EOF
      ;;
    prometheus)
      cat <<'EOF'
Persona: prometheus
- Operate as planner-only unless user asks to execute.
- Prefer markdown planning artifacts under .sisyphus/.
- Avoid implementation edits while in planning mode.
EOF
      ;;
    atlas)
      cat <<'EOF'
Persona: atlas
- Operate as execution coordinator for active plans.
- Resume from boulder state and advance one task slice at a time.
- Enforce verification before marking tasks complete.
EOF
      ;;
    *)
      cat <<'EOF'
Persona: sisyphus
- Operate as orchestrator: explore, plan, execute, verify.
- Use parallel exploration for unknown areas.
- Deliver complete, validated outcomes.
EOF
      ;;
  esac
}

# --- Read stdin (may be empty) ---
STDIN_JSON=""
if [[ ! -t 0 ]]; then
  STDIN_JSON="$(cat)"
fi

# --- Source sanitize-hook-input.sh for safe variable export ---
# shellcheck source=sanitize-hook-input.sh
if [[ -f "${SCRIPT_DIR}/sanitize-hook-input.sh" ]]; then
  export SANITIZE_INPUT="${STDIN_JSON}"
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/sanitize-hook-input.sh"
fi

# --- Determine event type ---
EVENT_TYPE="${1:-${HOOK_EVENT:-unknown}}"
readonly EVENT_TYPE

_debug "event=${EVENT_TYPE}"

# --- Handler functions (stubs for Wave 2) ---

handle_session_start() {
  _debug "handler=SessionStart"
  _persona_injection_block
  if _boulder_active; then
    printf '\n'
    _resume_block
  fi
}

handle_user_prompt_submit() {
  _debug "handler=UserPromptSubmit"
  _persona_injection_block
  local text="${HOOK_PROMPT:-}"
  if [[ -z "${text}" ]]; then
    text="${STDIN_JSON:-}"
  fi
  if [[ -x "${SCRIPT_DIR}/detect-ulw.sh" ]] && printf '%s' "${text}" | "${SCRIPT_DIR}/detect-ulw.sh"; then
    _runtime_set_ulw_enabled
    printf '\n'
    cat <<'EOF'
Ultrawork mode is active.

Execution contract:
- Continue until requested work is complete.
- Use parallel exploration for unknown areas.
- Run verification gates before completion (tests, typecheck, build).
- Only stop when done or when /omo:stop-continuation is used.
EOF
  fi
}

handle_pre_tool_use() {
  _debug "handler=PreToolUse"
  local tool_name="${HOOK_TOOL_NAME:-}"
  local cmd="${HOOK_TOOL_COMMAND:-}"
  if [[ -z "${cmd}" ]]; then
    cmd="${HOOK_TOOL_ARGS:-}"
  fi
  if [[ -z "${cmd}" ]]; then
    cmd="${HOOK_PROMPT:-}"
  fi

  if [[ "${tool_name}" == "Bash" ]] || [[ "${tool_name}" == "bash" ]]; then
    if printf '%s' "${cmd}" | grep -Eiq '(^|[[:space:];|&])(rm[[:space:]]+-rf|mkfs([[:space:]]|$)|dd[[:space:]]+if=)'; then
      _emit_block_json "Blocked destructive Bash pattern by OMO guardrails"
      return 0
    fi
  fi

  local persona
  persona="$(_active_persona)"
  if [[ "${persona}" == "prometheus" ]]; then
    if [[ "${tool_name}" == "Write" || "${tool_name}" == "Edit" || "${tool_name}" == "MultiEdit" ]]; then
      if printf '%s' "${cmd}" | grep -Eiq '([^[:space:]]+\.(ts|tsx|js|jsx|json|yaml|yml|sh|py|go|rs|java|rb|php|c|cpp))'; then
        _emit_block_json "Prometheus persona is planning-only: write markdown artifacts under .sisyphus/"
        return 0
      fi
    fi
  fi
}

handle_stop() {
  _debug "handler=Stop"
  if _stop_continuation_disabled; then
    return 0
  fi

  local needs_block="false"
  local ralph_is_active="false"
  if _ralph_active; then
    ralph_is_active="true"
  fi
  if _boulder_active || [[ "${ralph_is_active}" == "true" ]] || _ulw_enabled; then
    needs_block="true"
  fi
  [[ "${needs_block}" == "true" ]] || return 0

  local session_key
  session_key="$(_session_key)"
  local runtime_json
  runtime_json="$(_read_json_file "${RUNTIME_FILE}")"

  if ! command -v jq >/dev/null 2>&1; then
    return 0
  fi

  local now_epoch last_stop blocks
  now_epoch="$(_now_epoch)"
  last_stop="$(printf '%s' "${runtime_json}" | jq -r --arg sk "${session_key}" '.sessions[$sk].ulw.lastStopEpoch // 0' 2>/dev/null || echo "0")"
  blocks="$(printf '%s' "${runtime_json}" | jq -r --arg sk "${session_key}" '.sessions[$sk].ulw.stopBlocks // 0' 2>/dev/null || echo "0")"

  if [[ $((now_epoch - last_stop)) -lt ${STOP_COOLDOWN_SECONDS} ]]; then
    return 0
  fi

  if [[ "${blocks}" -ge "${STOP_MAX_BLOCKS}" ]]; then
    local disabled_json
    disabled_json="$(printf '%s' "${runtime_json}" | jq -c --arg sk "${session_key}" --arg ts "$(_now_iso)" '
      .version = 1
      | .sessions = (.sessions // {})
      | .sessions[$sk] = (.sessions[$sk] // {})
      | .sessions[$sk].ulw = (.sessions[$sk].ulw // {})
      | .sessions[$sk].ulw.enabled = false
      | .sessions[$sk].stopContinuation = (.sessions[$sk].stopContinuation // {})
      | .sessions[$sk].stopContinuation.disabled = true
      | .sessions[$sk].stopContinuation.disabledReason = "auto-disabled after max stop blocks"
      | .sessions[$sk].stopContinuation.disabledAt = $ts
    ' 2>/dev/null)"
    if [[ -n "${disabled_json}" ]]; then
      _write_json_file "${RUNTIME_FILE}" "${disabled_json}" || true
    fi
    return 0
  fi

  local updated
  updated="$(printf '%s' "${runtime_json}" | jq -c --arg sk "${session_key}" --arg ts "$(_now_iso)" --argjson now "${now_epoch}" '
    .version = 1
    | .sessions = (.sessions // {})
    | .sessions[$sk] = (.sessions[$sk] // {})
    | .sessions[$sk].ulw = (.sessions[$sk].ulw // {})
    | .sessions[$sk].ulw.stopBlocks = ((.sessions[$sk].ulw.stopBlocks // 0) + 1)
    | .sessions[$sk].ulw.lastStopEpoch = $now
    | .sessions[$sk].ulw.lastStopAt = $ts
  ' 2>/dev/null)"
  if [[ -n "${updated}" ]]; then
    _write_json_file "${RUNTIME_FILE}" "${updated}" || true
  fi

  if [[ "${ralph_is_active}" == "true" ]]; then
    _increment_ralph_iteration
  fi

  _emit_block_json "Continuation active: finish work or use /omo:stop-continuation"
}

# --- Dispatch ---
case "${EVENT_TYPE}" in
  SessionStart)
    handle_session_start
    ;;
  UserPromptSubmit)
    handle_user_prompt_submit
    ;;
  PreToolUse)
    handle_pre_tool_use
    ;;
  Stop)
    handle_stop
    ;;
  *)
    _debug "unknown event: ${EVENT_TYPE}"
    ;;
esac

exit 0
