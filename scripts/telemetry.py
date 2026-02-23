#!/usr/bin/env python3
"""Fire-and-forget event/score emission to Langfuse.

Replaces langfuse-emit.sh.

CONTRACT:
  - Sends events or scores to Langfuse ingestion API.
  - Fire-and-forget via daemon thread (never blocks hooks).
  - On ANY failure: silently returns (fail-open).
  - Never outputs to stdout.

ENV:
  LANGFUSE_PUBLIC_KEY  — Langfuse public key
  LANGFUSE_SECRET_KEY  — Langfuse secret key
  LANGFUSE_BASE_URL    — Langfuse host URL

CLI:
  python3 telemetry.py event <trace_id> <event_name> <metadata_json>
  python3 telemetry.py score <trace_id> <score_name> <value> [data_type]
"""

import base64
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


def _get_config():
    """Get Langfuse configuration from environment."""
    base_url = os.environ.get("LANGFUSE_BASE_URL", "")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    return base_url, public_key, secret_key


def _is_enabled():
    """Check if Langfuse telemetry is configured."""
    base_url, public_key, secret_key = _get_config()
    return bool(base_url and public_key and secret_key)


def _auth_header():
    """Build HTTP Basic Auth header."""
    _, public_key, secret_key = _get_config()
    creds = f"{public_key}:{secret_key}".encode("utf-8")
    encoded = base64.b64encode(creds).decode("utf-8")
    return f"Basic {encoded}"


def _now_iso():
    """Current UTC time in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _generate_id(prefix: str):
    """Generate a unique ID."""
    return f"{prefix}-{int(time.time() * 1000000)}"


def _post(endpoint: str, body: dict):
    """POST to Langfuse API. Fire-and-forget, ignores all errors."""
    try:
        base_url, _, _ = _get_config()
        url = f"{base_url}/api/public{endpoint}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _post_background(endpoint: str, body: dict):
    """Fire-and-forget POST in a daemon thread."""
    t = threading.Thread(target=_post, args=(endpoint, body), daemon=True)
    t.start()


def emit_event(trace_id: str, name: str, metadata: dict | str | None = None):
    """Emit an event to Langfuse (fire-and-forget)."""
    if not _is_enabled():
        return

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, ValueError):
            metadata = {}
    elif metadata is None:
        metadata = {}

    body = {
        "batch": [{
            "id": _generate_id(name),
            "type": "event-create",
            "timestamp": _now_iso(),
            "body": {
                "traceId": trace_id,
                "name": name,
                "metadata": metadata,
            },
        }],
    }
    _post_background("/ingestion", body)


def emit_score(trace_id: str, name: str, value, data_type: str = "NUMERIC"):
    """Emit a score to Langfuse (fire-and-forget)."""
    if not _is_enabled():
        return

    # Coerce value to appropriate type
    if data_type == "BOOLEAN":
        value = bool(value) if not isinstance(value, bool) else value
    else:
        try:
            value = float(value)
        except (ValueError, TypeError):
            value = 0

    body = {
        "batch": [{
            "id": _generate_id(name),
            "type": "score-create",
            "timestamp": _now_iso(),
            "body": {
                "traceId": trace_id,
                "name": name,
                "value": value,
                "dataType": data_type,
            },
        }],
    }
    _post_background("/ingestion", body)


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    mode = sys.argv[1]
    trace_id = sys.argv[2] if len(sys.argv) > 2 else ""

    if not mode or not trace_id:
        sys.exit(0)

    if mode == "event":
        event_name = sys.argv[3] if len(sys.argv) > 3 else ""
        metadata = sys.argv[4] if len(sys.argv) > 4 else "{}"
        if not event_name:
            sys.exit(0)
        emit_event(trace_id, event_name, metadata)

    elif mode == "score":
        score_name = sys.argv[3] if len(sys.argv) > 3 else ""
        value = sys.argv[4] if len(sys.argv) > 4 else "0"
        data_type = sys.argv[5] if len(sys.argv) > 5 else "NUMERIC"
        if not score_name:
            sys.exit(0)
        emit_score(trace_id, score_name, value, data_type)

    sys.exit(0)


if __name__ == "__main__":
    main()
