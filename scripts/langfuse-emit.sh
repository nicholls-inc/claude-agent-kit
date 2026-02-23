#!/usr/bin/env bash
set -euo pipefail

# langfuse-emit.sh — Fire-and-forget event/score emission to Langfuse.
#
# CONTRACT:
#   - Sends events or scores to Langfuse ingestion API.
#   - Runs curl in background so hooks are never slowed down.
#   - On ANY failure (Langfuse down, bad credentials): silently exits 0.
#   - Never outputs to stdout (would corrupt hook output).
#
# ENV (from .claude/settings.local.json):
#   LANGFUSE_PUBLIC_KEY   — Langfuse public key
#   LANGFUSE_SECRET_KEY   — Langfuse secret key
#   LANGFUSE_BASE_URL     — Langfuse host URL
#
# USAGE:
#   # Emit an event:
#   ./langfuse-emit.sh event <trace_id> <event_name> <metadata_json>
#
#   # Emit a score:
#   ./langfuse-emit.sh score <trace_id> <score_name> <value> [data_type]
#     data_type: BOOLEAN or NUMERIC (default: NUMERIC)

# --- Fail silently on missing config ---
LANGFUSE_BASE_URL="${LANGFUSE_BASE_URL:-}"
LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-}"
LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-}"

if [[ -z "${LANGFUSE_BASE_URL}" || -z "${LANGFUSE_PUBLIC_KEY}" || -z "${LANGFUSE_SECRET_KEY}" ]]; then
  exit 0
fi

MODE="${1:-}"
TRACE_ID="${2:-}"

if [[ -z "${MODE}" || -z "${TRACE_ID}" ]]; then
  exit 0
fi

_auth_header() {
  local encoded
  encoded=$(printf '%s:%s' "${LANGFUSE_PUBLIC_KEY}" "${LANGFUSE_SECRET_KEY}" | base64 2>/dev/null | tr -d '\n')
  printf 'Basic %s' "${encoded}"
}

_post() {
  local endpoint="$1"
  local body="$2"
  local auth
  auth="$(_auth_header)"

  # Fire-and-forget: background curl, discard all output
  curl -sS -X POST \
    "${LANGFUSE_BASE_URL}/api/public${endpoint}" \
    -H "Authorization: ${auth}" \
    -H "Content-Type: application/json" \
    -d "${body}" \
    >/dev/null 2>&1 &
}

case "${MODE}" in
  event)
    EVENT_NAME="${3:-}"
    METADATA="${4:-"{}"}"
    [[ -n "${EVENT_NAME}" ]] || exit 0

    BODY=$(cat <<ENDJSON
{
  "batch": [{
    "id": "$(uuidgen 2>/dev/null || printf '%s-%s' "${EVENT_NAME}" "$(date +%s%N 2>/dev/null || date +%s)")",
    "type": "event-create",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || echo "1970-01-01T00:00:00.000Z")",
    "body": {
      "traceId": "${TRACE_ID}",
      "name": "${EVENT_NAME}",
      "metadata": ${METADATA}
    }
  }]
}
ENDJSON
    )
    _post "/ingestion" "${BODY}"
    ;;

  score)
    SCORE_NAME="${3:-}"
    VALUE="${4:-0}"
    DATA_TYPE="${5:-NUMERIC}"
    [[ -n "${SCORE_NAME}" ]] || exit 0

    BODY=$(cat <<ENDJSON
{
  "batch": [{
    "id": "$(uuidgen 2>/dev/null || printf '%s-%s' "${SCORE_NAME}" "$(date +%s%N 2>/dev/null || date +%s)")",
    "type": "score-create",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || echo "1970-01-01T00:00:00.000Z")",
    "body": {
      "traceId": "${TRACE_ID}",
      "name": "${SCORE_NAME}",
      "value": ${VALUE},
      "dataType": "${DATA_TYPE}"
    }
  }]
}
ENDJSON
    )
    _post "/ingestion" "${BODY}"
    ;;
esac

exit 0
