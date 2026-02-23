#!/usr/bin/env python3
"""Single entrypoint for all CC hook events.

Replaces hook-router.sh.

CONTRACT:
  - Reads stdin JSON from CC hook events.
  - First positional arg (sys.argv[1]) identifies the event type.
  - stdout rules:
      SessionStart / UserPromptSubmit -> plain text only (or empty)
      PreToolUse / Stop               -> valid JSON only (or empty)
  - On ANY error: log to stderr, exit 0, print nothing to stdout (fail-open).

ENV:
  AGENT_KIT_DEBUG=1 -> write diagnostics to .agent-kit/evidence/debug/
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

# --- Module imports (all Wave 1-2) ---
from scripts._debug import debug
from scripts.state import read_json, write_json
from scripts.detect import detect_ulw, detect_persona_switch
from scripts.sanitize import parse_hook_input
from scripts.telemetry import emit_event, emit_score
from scripts.build_sections import compose_sections, discover_agents, discover_skills

# --- Constants ---
BOULDER_FILE = ".agent-kit/boulder.json"
RUNTIME_FILE = ".agent-kit/state/runtime.local.json"
RALPH_FILE = ".agent-kit/ralph-loop.local.md"
SESSION_KEY_DEFAULT = "global"
STOP_MAX_BLOCKS = 8
STOP_COOLDOWN_SECONDS = 3

# Resolve plugin root (parent of scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)


# --- Utility helpers ---

def _json_escape(s: str) -> str:
    """JSON-encode a string value."""
    return json.dumps(s)


def _emit_block_json(reason: str):
    """Emit a block decision as JSON to stdout."""
    escaped = _json_escape(reason)
    sys.stdout.write(f'{{"decision":"block","reason":{escaped}}}\n')


def _now_ms() -> int:
    """Millisecond timestamp."""
    return int(time.time() * 1000)


def _now_epoch() -> int:
    """Current epoch seconds."""
    return int(time.time())


def _now_iso() -> str:
    """Current UTC time in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _session_key(hook_input) -> str:
    """Get session key from hook input or default."""
    if hook_input.session_id:
        return hook_input.session_id
    return SESSION_KEY_DEFAULT


def _get_trace_id(hook_input) -> str:
    """Get trace ID for telemetry."""
    if hook_input.session_id:
        return hook_input.session_id
    return str(int(time.time() * 1000000))


# --- Runtime state helpers ---

def _runtime_get(key_path: str) -> str:
    """Get a value from runtime state using a simple dot-path."""
    runtime = read_json(RUNTIME_FILE)
    parts = key_path.strip(".").split(".")
    current = runtime
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return ""
    if current is None:
        return ""
    return str(current)


def _active_persona(hook_input) -> str:
    """Get current active persona from runtime state."""
    sk = _session_key(hook_input)
    runtime = read_json(RUNTIME_FILE)

    version = runtime.get("version", 1)
    if version != 1:
        return "sisyphus"

    sessions = runtime.get("sessions", {})
    session = sessions.get(sk, {})
    persona = session.get("activePersona", "sisyphus")

    if persona in ("sisyphus", "hephaestus", "prometheus", "atlas"):
        return persona
    return "sisyphus"


def _runtime_set_ulw_enabled(hook_input):
    """Enable ULW in runtime state."""
    sk = _session_key(hook_input)
    runtime = read_json(RUNTIME_FILE)

    runtime.setdefault("version", 1)
    runtime.setdefault("sessions", {})
    runtime["sessions"].setdefault(sk, {})
    runtime["sessions"][sk].setdefault("ulw", {})
    runtime["sessions"][sk]["ulw"]["enabled"] = True
    runtime["sessions"][sk]["ulw"]["updatedAt"] = _now_iso()
    runtime["sessions"][sk]["ulw"].setdefault("stopBlocks", 0)

    write_json(RUNTIME_FILE, runtime)


def _stop_continuation_disabled(hook_input) -> bool:
    """Check if stop continuation is disabled."""
    sk = _session_key(hook_input)
    runtime = read_json(RUNTIME_FILE)

    version = runtime.get("version", 1)
    if version != 1:
        return False

    sessions = runtime.get("sessions", {})
    session = sessions.get(sk, {})
    stop_cont = session.get("stopContinuation", {})
    return stop_cont.get("disabled", False) is True


def _boulder_active() -> bool:
    """Check if an active boulder (plan) is running."""
    boulder = read_json(BOULDER_FILE)

    version = boulder.get("version", 1)
    if version != 1:
        return False

    active = boulder.get("active", False)
    status = boulder.get("status", "")
    return active is True and status != "done"


def _ralph_active(hook_input) -> bool:
    """Check if ralph-loop is active."""
    if not os.path.isfile(RALPH_FILE):
        return False

    try:
        with open(RALPH_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return False

    # Check status: active
    if not re.search(r"^status:\s*active", content, re.MULTILINE | re.IGNORECASE):
        return False

    # Check for RALPH_DONE in assistant text or prompt
    combined = (hook_input.assistant_text or "") + " " + (hook_input.prompt or "")
    if "RALPH_DONE" in combined:
        # Mark as done
        try:
            new_content = re.sub(
                r"^status:\s*active",
                "status: done",
                content,
                flags=re.MULTILINE | re.IGNORECASE,
            )
            with open(RALPH_FILE, "w", encoding="utf-8") as f:
                f.write(new_content)
        except OSError:
            pass
        return False

    # Check iteration limits
    iter_match = re.search(r"^iterations:\s*(\d+)", content, re.MULTILINE)
    max_match = re.search(r"^max_iterations:\s*(\d+)", content, re.MULTILINE)

    if iter_match and max_match:
        iterations = int(iter_match.group(1))
        max_iterations = int(max_match.group(1))
        if iterations >= max_iterations:
            # Mark as done
            try:
                new_content = re.sub(
                    r"^status:\s*active",
                    "status: done",
                    content,
                    flags=re.MULTILINE | re.IGNORECASE,
                )
                with open(RALPH_FILE, "w", encoding="utf-8") as f:
                    f.write(new_content)
            except OSError:
                pass
            return False

    return True


def _increment_ralph_iteration():
    """Increment the iteration counter in ralph-loop file."""
    if not os.path.isfile(RALPH_FILE):
        return

    try:
        with open(RALPH_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return

    iter_match = re.search(r"^iterations:\s*(\d+)", content, re.MULTILINE)
    if iter_match:
        iterations = int(iter_match.group(1))
        next_val = iterations + 1
        new_content = re.sub(
            r"^iterations:\s*\d+",
            f"iterations: {next_val}",
            content,
            flags=re.MULTILINE,
        )
    else:
        new_content = content + f"\niterations: 1\n"

    try:
        with open(RALPH_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError:
        pass


def _ulw_enabled(hook_input) -> bool:
    """Check if ultrawork mode is enabled."""
    sk = _session_key(hook_input)
    runtime = read_json(RUNTIME_FILE)

    version = runtime.get("version", 1)
    if version != 1:
        return False

    sessions = runtime.get("sessions", {})
    session = sessions.get(sk, {})
    ulw = session.get("ulw", {})
    return ulw.get("enabled", False) is True


def _resume_block() -> str:
    """Generate resume context for active boulder."""
    boulder = read_json(BOULDER_FILE)
    plan_path = boulder.get("planPath", "")
    if not plan_path:
        return ""

    task_num = ""
    task_label = ""
    current_task = boulder.get("currentTask", {})
    if isinstance(current_task, dict):
        task_num = str(current_task.get("number", ""))
        task_label = str(current_task.get("label", ""))

    lines = ["Resume context:"]
    lines.append(f"- Active plan: {plan_path}")
    if task_num or task_label:
        lines.append(f"- Current task: {task_num} {task_label}")
    lines.append("- Continue with /claude-agent-kit:start-work")
    lines.append("- Escape hatch: /claude-agent-kit:stop-continuation")
    return "\n".join(lines)


def _build_dynamic_sections(persona: str) -> str:
    """Build dynamic prompt sections for the given persona."""
    agents_dir = os.path.join(PLUGIN_ROOT, "agents")
    skills_dir = os.path.join(PLUGIN_ROOT, "skills")

    try:
        agents = discover_agents(agents_dir)
        skills = discover_skills(skills_dir)
        return compose_sections(persona, agents, skills)
    except Exception:
        return ""


# --- Handler functions ---

def handle_session_start(hook_input):
    """Handle SessionStart event."""
    start_ms = _now_ms()
    debug("handler=SessionStart")

    persona = _active_persona(hook_input)

    # Build and output dynamic sections
    sections = _build_dynamic_sections(persona)
    if sections:
        sys.stdout.write(sections)

    # Boulder resume context
    has_resume = False
    if _boulder_active():
        sys.stdout.write("\n")
        resume = _resume_block()
        if resume:
            sys.stdout.write(resume + "\n")
        has_resume = True

    end_ms = _now_ms()
    trace_id = _get_trace_id(hook_input)
    emit_event(trace_id, "hook.session_start", {
        "persona": persona,
        "boulder_active": has_resume,
        "has_resume": has_resume,
    })
    emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)


def handle_user_prompt_submit(hook_input):
    """Handle UserPromptSubmit event."""
    start_ms = _now_ms()
    debug("handler=UserPromptSubmit")

    persona = _active_persona(hook_input)

    # Detect persona skill invocation — override target persona for dynamic sections
    text = hook_input.prompt or ""
    target_persona = detect_persona_switch(text)
    if target_persona:
        persona = target_persona
        debug(f"persona_switch_detected target={persona}")

    # Build and output dynamic sections
    sections = _build_dynamic_sections(persona)
    if sections:
        sys.stdout.write(sections)

    # ULW detection
    ulw_triggered = False
    if detect_ulw(text):
        _runtime_set_ulw_enabled(hook_input)
        ulw_triggered = True
        sys.stdout.write("\n")
        sys.stdout.write(
            "Ultrawork mode is active.\n"
            "\n"
            "Execution contract:\n"
            "- Continue until requested work is complete.\n"
            "- Use parallel exploration for unknown areas.\n"
            "- Run verification gates before completion (tests, typecheck, build).\n"
            "- Only stop when done or when /claude-agent-kit:stop-continuation is used.\n"
        )

    end_ms = _now_ms()
    trace_id = _get_trace_id(hook_input)
    emit_event(trace_id, "hook.user_prompt_submit", {
        "persona": persona,
        "ulw_triggered": ulw_triggered,
    })
    emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)


def handle_pre_tool_use(hook_input):
    """Handle PreToolUse event."""
    start_ms = _now_ms()
    debug("handler=PreToolUse")

    tool_name = hook_input.tool_name or ""
    cmd = hook_input.tool_command or hook_input.tool_args or hook_input.prompt or ""

    decision = "allow"
    block_reason = ""

    # Check for destructive bash commands
    if tool_name.lower() == "bash":
        if re.search(
            r"(^|[\s;|&])(rm\s+-rf|mkfs(\s|$)|dd\s+if=)",
            cmd,
            re.IGNORECASE,
        ):
            decision = "block"
            block_reason = "destructive_bash"
            _emit_block_json("Blocked destructive Bash pattern by safety guardrails")

    # Prometheus write guard
    if decision == "allow":
        persona = _active_persona(hook_input)
        if persona == "prometheus":
            if tool_name in ("Write", "Edit", "MultiEdit"):
                if re.search(
                    r"[^\s]+\.(ts|tsx|js|jsx|json|yaml|yml|sh|py|go|rs|java|rb|php|c|cpp)",
                    cmd,
                    re.IGNORECASE,
                ):
                    decision = "block"
                    block_reason = "prometheus_write_guard"
                    _emit_block_json(
                        "Prometheus persona is planning-only: write markdown artifacts under .agent-kit/"
                    )

    end_ms = _now_ms()
    trace_id = _get_trace_id(hook_input)
    emit_event(trace_id, "hook.pretool", {
        "tool_name": tool_name,
        "decision": decision,
        "block_reason": block_reason,
    })
    emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)


def handle_stop(hook_input):
    """Handle Stop event."""
    start_ms = _now_ms()
    debug("handler=Stop")

    decision = "allow"
    ulw_is_active = False
    boulder_is_active = False
    ralph_is_active = False
    ralph_iteration = 0
    stop_blocks = 0

    # Check if continuation is disabled
    if _stop_continuation_disabled(hook_input):
        end_ms = _now_ms()
        trace_id = _get_trace_id(hook_input)
        emit_event(trace_id, "hook.stop", {
            "decision": "allow",
            "stop_blocks": 0,
            "ulw_active": False,
            "boulder_active": False,
            "ralph_active": False,
            "ralph_iteration": 0,
            "reason": "continuation_disabled",
        })
        emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)
        return

    # Check active states
    if _ralph_active(hook_input):
        ralph_is_active = True
        # Read current iteration count
        try:
            with open(RALPH_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            iter_match = re.search(r"^iterations:\s*(\d+)", content, re.MULTILINE)
            if iter_match:
                ralph_iteration = int(iter_match.group(1))
        except OSError:
            pass

    if _boulder_active():
        boulder_is_active = True

    if _ulw_enabled(hook_input):
        ulw_is_active = True

    # If nothing is active, allow stop
    needs_block = boulder_is_active or ralph_is_active or ulw_is_active
    if not needs_block:
        end_ms = _now_ms()
        trace_id = _get_trace_id(hook_input)
        emit_event(trace_id, "hook.stop", {
            "decision": "allow",
            "stop_blocks": 0,
            "ulw_active": ulw_is_active,
            "boulder_active": boulder_is_active,
            "ralph_active": ralph_is_active,
            "ralph_iteration": ralph_iteration,
        })
        emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)
        return

    # Read current stop state
    sk = _session_key(hook_input)
    runtime = read_json(RUNTIME_FILE)
    sessions = runtime.get("sessions", {})
    session = sessions.get(sk, {})
    ulw_state = session.get("ulw", {})

    now_epoch = _now_epoch()
    last_stop = ulw_state.get("lastStopEpoch", 0)
    blocks = ulw_state.get("stopBlocks", 0)
    stop_blocks = blocks

    # Cooldown check
    if isinstance(last_stop, (int, float)) and (now_epoch - last_stop) < STOP_COOLDOWN_SECONDS:
        end_ms = _now_ms()
        trace_id = _get_trace_id(hook_input)
        emit_event(trace_id, "hook.stop", {
            "decision": "allow",
            "stop_blocks": stop_blocks,
            "ulw_active": ulw_is_active,
            "boulder_active": boulder_is_active,
            "ralph_active": ralph_is_active,
            "ralph_iteration": ralph_iteration,
            "reason": "cooldown",
        })
        emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)
        return

    # Max blocks check — auto-disable
    if blocks >= STOP_MAX_BLOCKS:
        runtime.setdefault("version", 1)
        runtime.setdefault("sessions", {})
        runtime["sessions"].setdefault(sk, {})
        runtime["sessions"][sk].setdefault("ulw", {})
        runtime["sessions"][sk]["ulw"]["enabled"] = False
        runtime["sessions"][sk].setdefault("stopContinuation", {})
        runtime["sessions"][sk]["stopContinuation"]["disabled"] = True
        runtime["sessions"][sk]["stopContinuation"]["disabledReason"] = "auto-disabled after max stop blocks"
        runtime["sessions"][sk]["stopContinuation"]["disabledAt"] = _now_iso()
        write_json(RUNTIME_FILE, runtime)

        end_ms = _now_ms()
        trace_id = _get_trace_id(hook_input)
        emit_event(trace_id, "hook.stop", {
            "decision": "allow",
            "stop_blocks": stop_blocks,
            "ulw_active": ulw_is_active,
            "boulder_active": boulder_is_active,
            "ralph_active": ralph_is_active,
            "ralph_iteration": ralph_iteration,
            "reason": "max_blocks_auto_disabled",
        })
        emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)
        return

    # Block stop
    decision = "block"

    # Increment stop blocks counter
    runtime.setdefault("version", 1)
    runtime.setdefault("sessions", {})
    runtime["sessions"].setdefault(sk, {})
    runtime["sessions"][sk].setdefault("ulw", {})
    runtime["sessions"][sk]["ulw"]["stopBlocks"] = blocks + 1
    runtime["sessions"][sk]["ulw"]["lastStopEpoch"] = now_epoch
    runtime["sessions"][sk]["ulw"]["lastStopAt"] = _now_iso()
    write_json(RUNTIME_FILE, runtime)

    # Increment ralph iteration if active
    if ralph_is_active:
        _increment_ralph_iteration()

    _emit_block_json("Continuation active: finish work or use /claude-agent-kit:stop-continuation")

    end_ms = _now_ms()
    trace_id = _get_trace_id(hook_input)
    emit_event(trace_id, "hook.stop", {
        "decision": decision,
        "stop_blocks": stop_blocks,
        "ulw_active": ulw_is_active,
        "boulder_active": boulder_is_active,
        "ralph_active": ralph_is_active,
        "ralph_iteration": ralph_iteration,
    })
    emit_score(trace_id, "hook.latency_ms", end_ms - start_ms)


# --- Main entry point ---

def main():
    # Read stdin (may be empty)
    stdin_json = ""
    if not sys.stdin.isatty():
        stdin_json = sys.stdin.read()

    # Parse and sanitize input
    hook_input = parse_hook_input(stdin_json)

    # Determine event type: from CLI arg, then from parsed input, then unknown
    event_type = ""
    if len(sys.argv) > 1:
        event_type = sys.argv[1]
    if not event_type:
        event_type = hook_input.event or "unknown"

    debug(f"event={event_type}")

    # Dispatch
    if event_type == "SessionStart":
        handle_session_start(hook_input)
    elif event_type == "UserPromptSubmit":
        handle_user_prompt_submit(hook_input)
    elif event_type == "PreToolUse":
        handle_pre_tool_use(hook_input)
    elif event_type == "Stop":
        handle_stop(hook_input)
    else:
        debug(f"unknown event: {event_type}")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        # Fail-open: log to stderr, exit 0
        print(f"[hook-router] fail-open: {e}", file=sys.stderr)
        sys.exit(0)
