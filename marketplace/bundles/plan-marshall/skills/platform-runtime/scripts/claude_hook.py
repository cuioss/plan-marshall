#!/usr/bin/env python3
"""
SessionStart hook for Claude Code — captures session_id into CLAUDE_ENV_FILE.

Called by Claude Code as a SessionStart hook. Reads the JSON payload from stdin,
extracts session_id, and writes CLAUDE_CODE_SESSION_ID={session_id} to the
$CLAUDE_ENV_FILE file so subsequent tool invocations in the same session can
read the session id from the environment.

Exit codes:
    0 — success (env var written, or hook explicitly chose not to act)
    1 — malformed stdin (not JSON, or session_id field missing)
    2 — runtime error (CLAUDE_ENV_FILE not set, or write failure)

Usage (invoked by Claude Code hook mechanism, not directly):
    echo '{"session_id": "abc123"}' | python3 claude_hook.py

Emits nothing to stdout on success. Error details go to stderr so Claude Code
can surface them without interfering with the hook's env-var delivery channel.
"""

import json
import os
import sys


def main() -> int:
    """Read stdin JSON, extract session_id, write to CLAUDE_ENV_FILE."""
    # Read and parse stdin
    raw = sys.stdin.read()
    if not raw.strip():
        print("claude_hook: stdin is empty — no session payload received", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"claude_hook: malformed JSON on stdin: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print(
            f"claude_hook: expected JSON object, got {type(payload).__name__}",
            file=sys.stderr,
        )
        return 1

    session_id = payload.get("session_id")
    if not session_id:
        print(
            "claude_hook: 'session_id' field missing or empty in hook payload",
            file=sys.stderr,
        )
        return 1

    if not isinstance(session_id, str):
        print(
            f"claude_hook: 'session_id' must be a string, got {type(session_id).__name__}",
            file=sys.stderr,
        )
        return 1

    # Write to CLAUDE_ENV_FILE so the session id propagates into the environment
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        print(
            "claude_hook: CLAUDE_ENV_FILE is not set — cannot write session id",
            file=sys.stderr,
        )
        return 2

    try:
        with open(env_file, "a", encoding="utf-8") as fh:
            fh.write(f"CLAUDE_CODE_SESSION_ID={session_id}\n")
    except OSError as exc:
        print(f"claude_hook: failed to write to CLAUDE_ENV_FILE ({env_file}): {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
