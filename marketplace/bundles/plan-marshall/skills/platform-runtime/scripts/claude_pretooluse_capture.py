#!/usr/bin/env python3
"""Observe-only PreToolUse capture leaf for Claude Code.

Registered TEMPORARILY as a matcher-less ``hooks.PreToolUse`` entry by the human
operator. It exists to VALIDATE the shared ``pretooluse_gate`` accessors against
the real PreToolUse payload schema BEFORE the enforcement hook is armed: it
imports the SAME shared gate the enforcement leaf will use and records, for every
sampled call, the verbatim payload paired with the gate's extracted fields and
would-be context verdict. If a best-guess field name in ``pretooluse_gate`` is
wrong, the recorded would-be verdict (or an empty extracted field) reveals it, and
the fix is applied in the single shared module before enforcement is finalized.

Contract — this leaf NEVER blocks a call:

- It reads stdin best-effort and parses via the shared gate (no-raise).
- It appends one JSON object per line to a capture file under ``.plan/temp/``,
  pairing the raw payload with the gate's ``sub_agent_identity`` / ``cwd`` /
  ``tool_name`` extractions and the ``context_gate`` would-be verdict.
- It ALWAYS exits 0 and emits NOTHING on stdout, on every path — well-formed,
  malformed, or empty stdin, and even on an internal error (a failed append is
  swallowed). A capture run can therefore never block any tool call.

Usage (invoked by Claude Code's PreToolUse hook mechanism, not directly):
    echo '{"tool_name": "Bash", "tool_input": {"command": "ls"}}' \\
        | python3 claude_pretooluse_capture.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# pretooluse_gate is a sibling module in this same scripts directory. Ensure the
# directory is importable whether the leaf is run directly or via the executor.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import pretooluse_gate as gate  # noqa: E402

# Plan-dir name is configurable via the executor-exported PLAN_DIR_NAME env var,
# with a fallback for standalone invocation.
_PLAN_DIR_NAME = os.environ.get("PLAN_DIR_NAME", ".plan")

#: Capture file the sampled records are appended to, one JSON object per line.
_CAPTURE_PATH = Path(_PLAN_DIR_NAME) / "temp" / "pretooluse-payload-samples.jsonl"


def _build_record(payload: dict) -> dict:
    """Pair the verbatim payload with the shared gate's extractions + verdict.

    Uses ONLY the shared ``pretooluse_gate`` accessors — never a private
    field-name copy — so the recorded fields exercise exactly the accessors the
    enforcement leaf will rely on.

    Args:
        payload: The parsed PreToolUse payload.

    Returns:
        The record dict pairing the raw payload with the extracted fields and
        the would-be ``context_gate`` verdict.
    """
    return {
        "payload": payload,
        "extracted": {
            "sub_agent_identity": gate.sub_agent_identity(payload),
            "cwd": gate.cwd(payload),
            "tool_name": gate.tool_name(payload),
        },
        "would_be_context_verdict": gate.context_gate(payload),
    }


def _append_record(record: dict) -> None:
    """Append *record* as one JSON line to the capture file.

    Best-effort: creates the parent directory if needed and swallows any OS or
    serialization error so the capture run can never block a tool call.
    """
    try:
        _CAPTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_CAPTURE_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except (OSError, TypeError, ValueError):
        # Observe-only: a failed capture append must never surface as a blocked
        # call. Degrade silently.
        return


def main() -> int:
    """Read stdin, record the payload + gate verdict, always exit 0 silently."""
    try:
        raw = sys.stdin.read()
        payload = gate.parse(raw)
        record = _build_record(payload)
        _append_record(record)
    except Exception:
        # Whole-leaf best-effort/no-raise contract: any unexpected error degrades
        # to a silent no-op so the capture run never blocks a call.
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
