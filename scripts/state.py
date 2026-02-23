#!/usr/bin/env python3
"""Fail-open JSON state file reader and atomic writer.

Replaces state-read.sh and state-write.sh.

CONTRACT:
  read_json(path) -> dict:
    - If file exists and contains valid JSON: return parsed dict.
    - If file is missing or corrupt: return {} (fail-open).
    - Create parent directory if missing.

  write_json(path, data) -> bool:
    - Atomic write via tempfile + os.rename.
    - Create parent directory if missing.
    - Returns True on success, False on failure.

CLI:
  python3 state.py read <path>
  python3 state.py write <path> [json|-]
"""

import json
import os
import sys
import tempfile


def read_json(path: str) -> dict:
    """Read a JSON file, returning {} on any error (fail-open)."""
    if not path:
        return {}

    # Ensure parent directory exists
    parent = os.path.dirname(path)
    if parent and parent != ".":
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError:
            pass

    if not os.path.isfile(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return {}

    if not content.strip():
        return {}

    try:
        data = json.loads(content)
        if isinstance(data, (dict, list)):
            return data
        return {}
    except (json.JSONDecodeError, ValueError):
        return {}


def write_json(path: str, data) -> bool:
    """Atomically write JSON data to a file.

    Uses tempfile + os.rename for atomic write.
    Creates parent directories as needed.
    Returns True on success, False on failure.
    """
    if not path:
        print("state-write: missing file path argument", file=sys.stderr)
        return False

    # Accept dict/list or string
    if isinstance(data, str):
        json_content = data
    else:
        json_content = json.dumps(data)

    if not json_content:
        print("state-write: no JSON content provided", file=sys.stderr)
        return False

    parent = os.path.dirname(path)
    if parent and parent != ".":
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as e:
            print(f"state-write: failed to create directory {parent}: {e}", file=sys.stderr)
            return False

    # Lock directory for mutual exclusion
    lock_dir = f"{path}.lock"
    try:
        os.mkdir(lock_dir)
    except FileExistsError:
        print(f"state-write: lock busy for {path}", file=sys.stderr)
        return False
    except OSError as e:
        print(f"state-write: lock failed for {path}: {e}", file=sys.stderr)
        return False

    temp_path = None
    try:
        # Write to temp file in same directory
        fd, temp_path = tempfile.mkstemp(
            prefix=".state-write.",
            dir=parent if parent and parent != "." else ".",
        )
        try:
            os.write(fd, (json_content + "\n").encode("utf-8"))
        finally:
            os.close(fd)

        # Atomic rename
        os.rename(temp_path, path)
        temp_path = None  # rename succeeded, don't clean up
        return True

    except OSError as e:
        print(f"state-write: failed: {e}", file=sys.stderr)
        return False

    finally:
        # Cleanup temp file if still exists
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        # Release lock
        try:
            os.rmdir(lock_dir)
        except OSError:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: state.py read <path> | state.py write <path> [json|-]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "read":
        path = sys.argv[2] if len(sys.argv) > 2 else ""
        result = read_json(path)
        print(json.dumps(result, separators=(",", ":")))

    elif command == "write":
        if len(sys.argv) < 3:
            print("state-write: missing file path argument", file=sys.stderr)
            sys.exit(1)

        path = sys.argv[2]
        content = ""

        if len(sys.argv) > 3 and sys.argv[3] != "-":
            content = sys.argv[3]
        elif not sys.stdin.isatty():
            content = sys.stdin.read()

        if not content:
            print("state-write: no JSON content provided", file=sys.stderr)
            sys.exit(1)

        if write_json(path, content):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
