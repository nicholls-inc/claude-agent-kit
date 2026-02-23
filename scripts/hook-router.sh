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
#   AGENT_KIT_DEBUG=1  → write diagnostics to .agent-kit/evidence/debug/
#                   (never to stdout)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly PLUGIN_ROOT

readonly DEBUG_DIR=".agent-kit/evidence/debug"
readonly BOULDER_FILE=".agent-kit/boulder.json"
readonly RUNTIME_FILE=".agent-kit/state/runtime.local.json"
readonly RALPH_FILE=".agent-kit/ralph-loop.local.md"
readonly SESSION_KEY_DEFAULT="global"
readonly STOP_MAX_BLOCKS=8
readonly STOP_COOLDOWN_SECONDS=3

# --- Fail-open trap: on ANY error, silence stdout and exit 0 ---
# shellcheck disable=SC2317,SC2329 # used by trap
_fail_open() {
  local line="${1:-unknown}"
  echo "[hook-router] fail-open at line ${line}" >&2
  exit 0
}
trap '_fail_open ${LINENO}' ERR

# --- Debug helper: writes to debug dir, never stdout ---
_debug() {
  if [[ "${AGENT_KIT_DEBUG:-}" == "1" ]]; then
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

# --- Telemetry helpers: fire-and-forget to Langfuse ---
_telemetry_enabled() {
  [[ -x "${SCRIPT_DIR}/langfuse-emit.sh" ]] && [[ -n "${LANGFUSE_BASE_URL:-}" ]]
}

_get_trace_id() {
  printf '%s' "${HOOK_SESSION_ID:-$(date +%s%N 2>/dev/null || date +%s)}"
}

_emit_langfuse_event() {
  _telemetry_enabled || return 0
  local event_name="$1"
  local metadata_json="${2:-"{}"}"
  "${SCRIPT_DIR}/langfuse-emit.sh" event "$(_get_trace_id)" "${event_name}" "${metadata_json}" 2>/dev/null || true
}

_emit_langfuse_score() {
  _telemetry_enabled || return 0
  local score_name="$1"
  local value="$2"
  local data_type="${3:-NUMERIC}"
  "${SCRIPT_DIR}/langfuse-emit.sh" score "$(_get_trace_id)" "${score_name}" "${value}" "${data_type}" 2>/dev/null || true
}

_now_ms() {
  # Millisecond timestamp for latency measurement
  if date +%s%N >/dev/null 2>&1; then
    echo $(( $(date +%s%N) / 1000000 ))
  else
    echo $(( $(date +%s) * 1000 ))
  fi
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

# shellcheck disable=SC2317,SC2329 # utility for hook handlers
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
  printf -- '- Continue with /claude-agent-kit:start-work\n'
  printf -- '- Escape hatch: /claude-agent-kit:stop-continuation\n'
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

_build_dynamic_sections() {
  local persona="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 "${SCRIPT_DIR}/build_sections.py" \
      --persona "${persona}" \
      --agents-dir "${PLUGIN_ROOT}/agents" \
      --skills-dir "${PLUGIN_ROOT}/skills" 2>/dev/null || true
  fi
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
  local _start_ms; _start_ms="$(_now_ms)"
  _debug "handler=SessionStart"
  local persona; persona="$(_active_persona)"
  _build_dynamic_sections "${persona}"
  local has_resume="false"
  if _boulder_active; then
    printf '\n'
    _resume_block
    has_resume="true"
  fi
  local _end_ms; _end_ms="$(_now_ms)"
  _emit_langfuse_event "hook.session_start" \
    "{\"persona\":\"${persona}\",\"boulder_active\":${has_resume},\"has_resume\":${has_resume}}"
  _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
}

handle_user_prompt_submit() {
  local _start_ms; _start_ms="$(_now_ms)"
  _debug "handler=UserPromptSubmit"
  local persona; persona="$(_active_persona)"

  # Detect persona skill invocation — override target persona for dynamic sections
  local text="${HOOK_PROMPT:-}"
  if [[ -z "${text}" ]]; then
    text="${STDIN_JSON:-}"
  fi
  local target_persona
  target_persona="$(printf '%s' "${text}" | "${SCRIPT_DIR}/detect-persona-switch.sh" 2>/dev/null)" || true
  if [[ -n "${target_persona}" ]]; then
    persona="${target_persona}"
    _debug "persona_switch_detected target=${persona}"
  fi

  _build_dynamic_sections "${persona}"
  local ulw_triggered="false"
  if [[ -x "${SCRIPT_DIR}/detect-ulw.sh" ]] && printf '%s' "${text}" | "${SCRIPT_DIR}/detect-ulw.sh"; then
    _runtime_set_ulw_enabled
    ulw_triggered="true"
    printf '\n'
    cat <<'EOF'
Ultrawork mode is active.

Execution contract:
- Continue until requested work is complete.
- Use parallel exploration for unknown areas.
- Run verification gates before completion (tests, typecheck, build).
- Only stop when done or when /claude-agent-kit:stop-continuation is used.
EOF
  fi
  local _end_ms; _end_ms="$(_now_ms)"
  _emit_langfuse_event "hook.user_prompt_submit" \
    "{\"persona\":\"${persona}\",\"ulw_triggered\":${ulw_triggered}}"
  _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
}

handle_pre_tool_use() {
  local _start_ms; _start_ms="$(_now_ms)"
  _debug "handler=PreToolUse"
  local tool_name="${HOOK_TOOL_NAME:-}"
  local cmd="${HOOK_TOOL_COMMAND:-}"
  if [[ -z "${cmd}" ]]; then
    cmd="${HOOK_TOOL_ARGS:-}"
  fi
  if [[ -z "${cmd}" ]]; then
    cmd="${HOOK_PROMPT:-}"
  fi

  local decision="allow"
  local block_reason=""

  if [[ "${tool_name}" == "Bash" ]] || [[ "${tool_name}" == "bash" ]]; then
    if printf '%s' "${cmd}" | grep -Eiq '(^|[[:space:];|&])(rm[[:space:]]+-rf|mkfs([[:space:]]|$)|dd[[:space:]]+if=)'; then
      decision="block"
      block_reason="destructive_bash"
      _emit_block_json "Blocked destructive Bash pattern by safety guardrails"
    fi
  fi

  if [[ "${decision}" == "allow" ]]; then
    local persona
    persona="$(_active_persona)"
    if [[ "${persona}" == "prometheus" ]]; then
      if [[ "${tool_name}" == "Write" || "${tool_name}" == "Edit" || "${tool_name}" == "MultiEdit" ]]; then
        if printf '%s' "${cmd}" | grep -Eiq '([^[:space:]]+\.(ts|tsx|js|jsx|json|yaml|yml|sh|py|go|rs|java|rb|php|c|cpp))'; then
          decision="block"
          block_reason="prometheus_write_guard"
          _emit_block_json "Prometheus persona is planning-only: write markdown artifacts under .agent-kit/"
        fi
      fi
    fi
  fi

  local _end_ms; _end_ms="$(_now_ms)"
  _emit_langfuse_event "hook.pretool" \
    "{\"tool_name\":\"${tool_name}\",\"decision\":\"${decision}\",\"block_reason\":\"${block_reason}\"}"
  _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
}

handle_stop() {
  local _start_ms; _start_ms="$(_now_ms)"
  _debug "handler=Stop"

  local decision="allow"
  local ulw_is_active="false"
  local boulder_is_active="false"
  local ralph_is_active="false"
  local ralph_iteration="0"
  local stop_blocks="0"

  if _stop_continuation_disabled; then
    local _end_ms; _end_ms="$(_now_ms)"
    _emit_langfuse_event "hook.stop" \
      "{\"decision\":\"allow\",\"stop_blocks\":0,\"ulw_active\":false,\"boulder_active\":false,\"ralph_active\":false,\"ralph_iteration\":0,\"reason\":\"continuation_disabled\"}"
    _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
    return 0
  fi

  if _ralph_active; then
    ralph_is_active="true"
    ralph_iteration="$(sed -n 's/^iterations:[[:space:]]*//p' "${RALPH_FILE}" 2>/dev/null | awk 'NR==1{print; exit}')"
    ralph_iteration="${ralph_iteration:-0}"
  fi
  if _boulder_active; then
    boulder_is_active="true"
  fi
  if _ulw_enabled; then
    ulw_is_active="true"
  fi

  local needs_block="false"
  if [[ "${boulder_is_active}" == "true" ]] || [[ "${ralph_is_active}" == "true" ]] || [[ "${ulw_is_active}" == "true" ]]; then
    needs_block="true"
  fi

  if [[ "${needs_block}" != "true" ]]; then
    local _end_ms; _end_ms="$(_now_ms)"
    _emit_langfuse_event "hook.stop" \
      "{\"decision\":\"allow\",\"stop_blocks\":0,\"ulw_active\":${ulw_is_active},\"boulder_active\":${boulder_is_active},\"ralph_active\":${ralph_is_active},\"ralph_iteration\":${ralph_iteration}}"
    _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
    return 0
  fi

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
  stop_blocks="${blocks}"

  if [[ $((now_epoch - last_stop)) -lt ${STOP_COOLDOWN_SECONDS} ]]; then
    local _end_ms; _end_ms="$(_now_ms)"
    _emit_langfuse_event "hook.stop" \
      "{\"decision\":\"allow\",\"stop_blocks\":${stop_blocks},\"ulw_active\":${ulw_is_active},\"boulder_active\":${boulder_is_active},\"ralph_active\":${ralph_is_active},\"ralph_iteration\":${ralph_iteration},\"reason\":\"cooldown\"}"
    _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
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
    local _end_ms; _end_ms="$(_now_ms)"
    _emit_langfuse_event "hook.stop" \
      "{\"decision\":\"allow\",\"stop_blocks\":${stop_blocks},\"ulw_active\":${ulw_is_active},\"boulder_active\":${boulder_is_active},\"ralph_active\":${ralph_is_active},\"ralph_iteration\":${ralph_iteration},\"reason\":\"max_blocks_auto_disabled\"}"
    _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
    return 0
  fi

  decision="block"

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

  _emit_block_json "Continuation active: finish work or use /claude-agent-kit:stop-continuation"

  local _end_ms; _end_ms="$(_now_ms)"
  _emit_langfuse_event "hook.stop" \
    "{\"decision\":\"${decision}\",\"stop_blocks\":${stop_blocks},\"ulw_active\":${ulw_is_active},\"boulder_active\":${boulder_is_active},\"ralph_active\":${ralph_is_active},\"ralph_iteration\":${ralph_iteration}}"
  _emit_langfuse_score "hook.latency_ms" "$(( _end_ms - _start_ms ))"
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
