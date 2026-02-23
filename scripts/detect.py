#!/usr/bin/env python3
"""Detection utilities for ultrawork triggers and persona switches.

Replaces detect-ulw.sh and detect-persona-switch.sh.

CONTRACT:
  detect_ulw(text) -> bool:
    - Returns True if "ulw" or "ultrawork" appears as a standalone word.
    - Word-boundary match: "bulwark" must NOT match.
    - Case-insensitive.

  detect_persona_switch(text) -> str | None:
    - Returns persona name if a persona skill invocation is found.
    - Requires claude-agent-kit: namespace prefix.
    - Returns None if not found.

CLI:
  python3 detect.py ulw "text"       # exit 0 if found, 1 if not
  python3 detect.py persona "text"   # prints persona name, exit 0/1
"""

import re
import sys

# Word-boundary match for "ulw" or "ultrawork" (case-insensitive)
_ULW_PATTERN = re.compile(r"\b(ulw|ultrawork)\b", re.IGNORECASE)

# Persona skill invocation: optional /, then claude-agent-kit: followed by persona name
_PERSONA_PATTERN = re.compile(
    r"/?claude-agent-kit:(sisyphus|hephaestus|atlas|prometheus)",
    re.IGNORECASE,
)


def detect_ulw(text: str) -> bool:
    """Detect ultrawork/ulw keyword in text."""
    if not text:
        return False
    return bool(_ULW_PATTERN.search(text))


def detect_persona_switch(text: str) -> str | None:
    """Detect persona skill invocation in text.

    Returns the persona name (lowercase) if found, None otherwise.
    """
    if not text:
        return None
    match = _PERSONA_PATTERN.search(text)
    if match:
        return match.group(1).lower()
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: detect.py ulw <text> | detect.py persona <text>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    # Get input from args or stdin
    if len(sys.argv) > 2:
        text = sys.argv[2]
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = ""

    if command == "ulw":
        sys.exit(0 if detect_ulw(text) else 1)

    elif command == "persona":
        result = detect_persona_switch(text)
        if result:
            sys.stdout.write(result)
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
