"""Defensive parsing of CC hook stdin JSON.

Replaces sanitize-hook-input.sh.

CONTRACT:
  - Parse raw JSON from hook events.
  - Redact fields matching: token, key, secret, password.
  - Truncate long fields to max length.
  - Return a structured HookInput dataclass.

Import-only module — no standalone CLI needed.
"""

import json
import os
import re
from dataclasses import dataclass, field

MAX_PROMPT_LENGTH = 2000
REDACTED = "[REDACTED]"
HOOK_INPUT_DEBUG_DIR = ".agent-kit/evidence/hook-input"

# Pattern for sensitive field names
_SENSITIVE_PATTERN = re.compile(r"(?i)token|key|secret|password")


@dataclass
class HookInput:
    """Parsed and sanitized hook input."""
    event: str = ""
    tool_name: str = ""
    tool_command: str = ""
    tool_args: str = ""
    session_id: str = ""
    assistant_text: str = ""
    prompt: str = ""


def _redact_sensitive(data):
    """Recursively redact sensitive field values in a dict/list."""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if isinstance(k, str) and _SENSITIVE_PATTERN.search(k):
                result[k] = REDACTED
            else:
                result[k] = _redact_sensitive(v)
        return result
    elif isinstance(data, list):
        return [_redact_sensitive(item) for item in data]
    return data


def _truncate(s: str, max_len: int = MAX_PROMPT_LENGTH) -> str:
    """Truncate a string to max length."""
    if len(s) > max_len:
        return s[:max_len]
    return s


def _extract(data: dict, *paths: str) -> str:
    """Extract first non-empty value from multiple dotted paths.

    Supports paths like 'event', 'hook_event', 'tool_input.command'.
    """
    for path in paths:
        parts = path.split(".")
        current = data
        try:
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
            if current is not None and current != "":
                return str(current)
        except (TypeError, AttributeError):
            continue
    return ""


def parse_hook_input(raw_json: str) -> HookInput:
    """Parse and sanitize raw hook input JSON.

    Returns a HookInput dataclass with safe, redacted values.
    """
    result = HookInput()

    if not raw_json or not raw_json.strip():
        return result

    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError):
        return result

    if not isinstance(data, dict):
        return result

    # Redact sensitive fields
    safe_data = _redact_sensitive(data)

    # Extract fields with fallback paths (matching sanitize-hook-input.sh)
    result.event = _extract(safe_data, "event", "hook_event", "type")
    result.tool_name = _extract(safe_data, "tool_name", "toolName", "tool", "name")

    command_raw = _extract(safe_data, "command", "tool_input.command", "input.command", "toolInput.command")
    result.tool_command = _truncate(command_raw)

    args_raw = _extract(safe_data, "arguments", "tool_input.arguments", "input.arguments", "toolInput.arguments")
    result.tool_args = _truncate(args_raw)

    result.session_id = _extract(safe_data, "session_id", "sessionId")

    assistant_raw = _extract(safe_data, "assistant_message", "output", "response", "completion")
    result.assistant_text = _truncate(assistant_raw)

    prompt_raw = _extract(safe_data, "prompt", "input", "text", "message", "user_prompt")
    result.prompt = _truncate(prompt_raw)

    # Debug output
    if os.environ.get("AGENT_KIT_DEBUG") == "1":
        try:
            os.makedirs(HOOK_INPUT_DEBUG_DIR, exist_ok=True)
            debug_path = os.path.join(HOOK_INPUT_DEBUG_DIR, "latest-redacted.json")
            with open(debug_path, "w", encoding="utf-8") as f:
                json.dump(safe_data, f)
                f.write("\n")
        except OSError:
            pass

    return result
