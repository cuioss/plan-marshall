#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for claude_pretooluse_capture.py — the observe-only PreToolUse capture leaf.

The leaf is a stdin->file hook script, so it is exercised via subprocess (a fresh
interpreter, exactly as Claude Code would invoke it) with a controlled cwd so the
``.plan/temp/`` capture file lands inside the test's tmp directory.

The shared ``pretooluse_gate`` module is also imported directly (sibling-import
scaffolding) so each test can assert the recorded extracted fields and would-be
verdict match exactly what the shared gate computes — proving the leaf delegates
to the shared accessors rather than carrying its own field-name copies.

Coverage:
  - Appends one JSON object per line pairing the verbatim payload with the
    shared gate's extracted fields + would-be context verdict.
  - Emits nothing on stdout and exits 0 on well-formed, malformed, and empty
    stdin; never raises (never blocks a call).
  - The recorded ``extracted`` / ``would_be_context_verdict`` equal the shared
    gate's own computation for the same payload.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path(
    "plan-marshall", "platform-runtime", "claude_pretooluse_capture.py"
)
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pretooluse_gate as gate  # noqa: E402


# =============================================================================
# Helpers
# =============================================================================


def _capture_file(tmp_path: Path) -> Path:
    """Path the leaf appends to when run with cwd=tmp_path (PLAN_DIR_NAME=.plan)."""
    return tmp_path / ".plan" / "temp" / "pretooluse-payload-samples.jsonl"


def _run(stdin: str, tmp_path: Path) -> object:
    """Run the capture leaf with the given stdin, cwd pinned to tmp_path."""
    return run_script(SCRIPT_PATH, input_data=stdin, cwd=str(tmp_path))


def _read_records(tmp_path: Path) -> list[dict]:
    """Read and JSON-decode every appended line from the capture file."""
    path = _capture_file(tmp_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _worktree_cwd() -> str:
    return f"/Users/dev/project/{gate.WORKTREE_PATH_SEGMENT}/my-plan"


# =============================================================================
# Append-one-record / exit 0 / no stdout
# =============================================================================


def test_appends_one_record_per_call(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    result = _run(json.dumps(payload), tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    records = _read_records(tmp_path)
    assert len(records) == 1
    assert records[0]["payload"] == payload


def test_appends_accumulate_one_line_per_invocation(tmp_path: Path) -> None:
    _run(json.dumps({"tool_name": "Bash"}), tmp_path)
    _run(json.dumps({"tool_name": "Edit"}), tmp_path)
    _run(json.dumps({"tool_name": "Read"}), tmp_path)

    records = _read_records(tmp_path)
    assert len(records) == 3
    assert [r["payload"]["tool_name"] for r in records] == ["Bash", "Edit", "Read"]


def test_record_pairs_payload_with_extracted_fields_and_verdict(tmp_path: Path) -> None:
    payload = {
        gate.SUB_AGENT_IDENTITY_FIELD: "execution-context-level-2",
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Bash",
        "tool_input": {"command": "cat foo"},
    }
    _run(json.dumps(payload), tmp_path)

    record = _read_records(tmp_path)[0]
    assert set(record.keys()) == {"payload", "extracted", "would_be_context_verdict"}
    assert set(record["extracted"].keys()) == {"sub_agent_identity", "cwd", "tool_name"}


# =============================================================================
# Delegation to the shared gate
# =============================================================================


def test_recorded_extractions_match_shared_gate(tmp_path: Path) -> None:
    payload = {
        gate.SUB_AGENT_IDENTITY_FIELD: "execution-context-level-1",
        gate.CWD_FIELD: _worktree_cwd(),
        "tool_name": "Edit",
    }
    _run(json.dumps(payload), tmp_path)

    record = _read_records(tmp_path)[0]
    assert record["extracted"]["sub_agent_identity"] == gate.sub_agent_identity(payload)
    assert record["extracted"]["cwd"] == gate.cwd(payload)
    assert record["extracted"]["tool_name"] == gate.tool_name(payload)
    assert record["would_be_context_verdict"] == gate.context_gate(payload)


def test_recorded_verdict_true_inside_plan_context(tmp_path: Path) -> None:
    payload = {gate.CWD_FIELD: _worktree_cwd()}
    _run(json.dumps(payload), tmp_path)
    assert _read_records(tmp_path)[0]["would_be_context_verdict"] is True


def test_recorded_verdict_false_outside_plan_context(tmp_path: Path) -> None:
    payload = {gate.CWD_FIELD: "/Users/dev/project", "tool_name": "Bash"}
    _run(json.dumps(payload), tmp_path)
    assert _read_records(tmp_path)[0]["would_be_context_verdict"] is False


# =============================================================================
# Never blocks — malformed / empty stdin still exits 0 with no stdout
# =============================================================================


def test_exits_zero_and_silent_on_empty_stdin(tmp_path: Path) -> None:
    result = _run("", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    # An empty payload still records a {} payload with a false verdict.
    records = _read_records(tmp_path)
    assert len(records) == 1
    assert records[0]["payload"] == {}
    assert records[0]["would_be_context_verdict"] is False


def test_exits_zero_and_silent_on_malformed_json(tmp_path: Path) -> None:
    result = _run("{not valid json", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    records = _read_records(tmp_path)
    assert len(records) == 1
    assert records[0]["payload"] == {}


def test_exits_zero_on_non_object_json(tmp_path: Path) -> None:
    result = _run("[1, 2, 3]", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    assert _read_records(tmp_path)[0]["payload"] == {}
