"""Shared debug/logging utilities for agent-kit scripts.

Writes diagnostic logs to .agent-kit/evidence/debug/ when AGENT_KIT_DEBUG=1.
Import-only utility — no standalone CLI.
"""

import os
from datetime import datetime

DEBUG_DIR = ".agent-kit/evidence/debug"


def debug(message: str, source: str = "hook-router") -> None:
    """Write a debug message to the debug log file.

    Only writes when AGENT_KIT_DEBUG=1. Never writes to stdout.
    """
    if os.environ.get("AGENT_KIT_DEBUG") != "1":
        return

    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        log_path = os.path.join(DEBUG_DIR, f"{source}.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{ts} {message}\n")
    except OSError:
        pass
