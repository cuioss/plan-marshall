#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Operation-level tests for ``chat extract-signal``.

These exercise the runtime operation boundary — the turn the platform-runtime
router hands to the target implementation — for both targets and the missing
/unreadable-transcript shapes:

- ``ClaudeRuntime.chat_extract_signal`` reduces a located transcript and returns
  the seven-field normalized record (plus ``session_id`` / ``transcript_path``);
- it returns a ``transcript_not_found`` no-op when no transcript can be located;
- a read failure surfaces as a structured ``io_error``, NOT an absent-transcript
  no-op;
- ``OpenCodeRuntime.chat_extract_signal`` is an honest no-op whose signal fields
  are ABSENT rather than zero;
- the router dispatches ``chat extract-signal`` end-to-end (unit-arg dispatch is
  covered in ``test_platform_runtime_router.py``).

The pure reduction mechanics are covered in the ``test_platform_runtime_chat_*``
reducer/provenance/gate modules; this file does not re-derive them.
"""

import json

import _chat_signal_reducer
import claude_runtime
import platform_runtime
import pytest
from claude_runtime import ClaudeRuntime
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


@pytest.fixture()
def projects_at_tmp(tmp_path, monkeypatch):
    """Point the Claude projects dir at an isolated tmp_path.

    ``chat extract-signal`` resolves its transcript through
    ``claude_runtime._find_transcript``, which reads the module-level
    ``_CLAUDE_PROJECTS_DIR`` constant (bound at import time), unlike the
    normalized-tokens op whose ``_find_enrich_transcript`` resolves
    ``Path.home()`` live. So the fixture patches that constant directly rather
    than ``Path.home``.
    """
    projects = tmp_path / "home" / ".claude" / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(claude_runtime, "_CLAUDE_PROJECTS_DIR", projects)
    return projects


def _parse(toon_str: str) -> dict:
    result = parse_toon(toon_str)
    assert isinstance(result, dict), f"parse_toon returned non-dict: {toon_str!r}"
    return result


def _write_transcript(projects_dir, *lines: str):
    root = projects_dir / "plan"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "22222222-2222-2222-2222-222222222222.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _turn(role: str, content) -> str:
    return json.dumps({"type": "turn", "message": {"role": role, "content": content}})


class TestClaudeGetExtractSignal:
    def test_claude_reduces_a_signal_bearing_transcript(self, projects_at_tmp):
        """The op locates the transcript and returns the seven-field record."""
        _write_transcript(
            projects_at_tmp,
            _turn("user", "please revert that change"),
            _turn("assistant", "[STATUS] ack"),
            _turn("user", "<system-reminder>wrapper</system-reminder>"),
        )
        result = _parse(
            ClaudeRuntime().chat_extract_signal("22222222-2222-2222-2222-222222222222")
        )

        assert result["status"] == "success"
        assert result["operation"] == "chat extract-signal"
        assert result["session_id"] == "22222222-2222-2222-2222-222222222222"
        assert result["raw_turn_count"] == 3
        assert result["operator_turn_count"] == 1
        assert result["no_signal"] is False
        assert "please revert that change" in result["reduced_transcript"]
        # Platform-owned field: the resolved transcript path rides the success record.
        assert result["transcript_path"].endswith("22222222-2222-2222-2222-222222222222.jsonl")

    def test_claude_no_signal_transcript_still_succeeds(self, projects_at_tmp):
        """A transcript with no operator signal returns a record, not an error."""
        _write_transcript(
            projects_at_tmp,
            _turn("user", "<system-reminder>wrapper</system-reminder>"),
        )
        result = _parse(
            ClaudeRuntime().chat_extract_signal("22222222-2222-2222-2222-222222222222")
        )
        assert result["status"] == "success"
        assert result["operator_turn_count"] == 0
        assert result["no_signal"] is True
        # The empty reduction is still reported (measured), present as empty.
        assert result["reduced_bytes"] == 0

    def test_claude_missing_transcript_is_noop(self, projects_at_tmp):
        """No transcript on disk → the op returns a transcript_not_found no-op."""
        result = _parse(
            ClaudeRuntime().chat_extract_signal("22222222-2222-2222-2222-222222222299")
        )
        assert result["status"] == "no-op"
        assert result["reason"] == "transcript_not_found"
        assert result["operation"] == "chat extract-signal"

    def test_claude_io_error_is_not_an_absent_transcript(self, projects_at_tmp, monkeypatch):
        """A read failure surfaces as io_error, never folded into transcript_not_found.

        ``FileNotFoundError`` is an ``OSError``, so mapping every ``OSError`` to
        the no-op would let an unreadable transcript read as absent — silently
        turning it into no signal instead of surfacing the failure.
        """
        _write_transcript(
            projects_at_tmp,
            _turn("user", "please revert that change"),
        )

        def _raise(_path):
            raise PermissionError("locked")

        monkeypatch.setattr(_chat_signal_reducer, "reduce_chat_signal", _raise)
        result = _parse(
            ClaudeRuntime().chat_extract_signal("22222222-2222-2222-2222-222222222222")
        )
        assert result["status"] == "error"
        assert result["error"] == "io_error"
        assert "Failed to read session transcript" in result["message"]

    def test_claude_transcript_removed_after_discovery_is_absent(self, projects_at_tmp, monkeypatch):
        """A transcript that vanishes mid-read maps to transcript_not_found, not io_error.

        Discovery succeeded (the transcript existed at ``_find_transcript`` time)
        but the file is gone by the time ``reduce_chat_signal`` reads it. That is
        an honest \u201cno transcript can be located\u201d, the same no-op discovery's
        ``None`` path emits — NOT the read-failure the general ``OSError`` clause
        describes. ``FileNotFoundError`` must be caught before ``OSError``.
        """
        _write_transcript(
            projects_at_tmp,
            _turn("user", "please revert that change"),
        )

        def _vanish(_path):
            raise FileNotFoundError("transcript removed")

        monkeypatch.setattr(_chat_signal_reducer, "reduce_chat_signal", _vanish)
        result = _parse(
            ClaudeRuntime().chat_extract_signal("22222222-2222-2222-2222-222222222222")
        )
        assert result["status"] == "no-op"
        assert result["reason"] == "transcript_not_found"

    def test_claude_reaches_the_reducer_via_attribute_access(self, projects_at_tmp, monkeypatch):
        """The impl resolves ``reduce_chat_signal`` at call time, so it is patchable.

        Pins the correctness contract: ``_claude_runtime_impl`` reaches the
        reducer by module attribute access (``_chat_signal_reducer.reduce_chat_signal``),
        so a test monkeypatch of that name is honored and control of the op
        remains testable.
        """
        _write_transcript(
            projects_at_tmp,
            _turn("user", "please revert that change"),
        )
        sentinel = {"status": "success", "reduced_transcript": "driven-by-patch"}
        monkeypatch.setattr(
            _chat_signal_reducer, "reduce_chat_signal", lambda _path: sentinel
        )
        result = _parse(
            ClaudeRuntime().chat_extract_signal("22222222-2222-2222-2222-222222222222")
        )
        assert result["reduced_transcript"] == "driven-by-patch"
        assert result["status"] == "success"


class TestOpenCodeExtractSignal:
    def test_opencode_is_an_honest_noop(self):
        """OpenCode exposes no transcript → the op is a transcript_not_found no-op."""
        result = _parse(OpenCodeRuntime().chat_extract_signal("any-session"))
        assert result["status"] == "no-op"
        assert result["operation"] == "chat extract-signal"
        assert result["reason"] == "transcript_not_found"

    def test_opencode_signal_fields_are_absent_never_zero(self):
        """The declinable-primitive posture: no counters, no no_signal, no reduction.

        A zero asserts "measured, and there was none"; OpenCode measured nothing.
        Adding a zero-initialized ``no_signal: true`` + empty ``reduced_transcript``
        would make an unmeasured target indistinguishable from one whose transcript
        genuinely carried no signal — polluting the corpus that reads those fields.
        """
        result = _parse(OpenCodeRuntime().chat_extract_signal("any-session"))
        for field in ("operator_turn_count", "gate_decision_count", "no_signal",
                      "reduced_transcript", "reduced_bytes", "raw_turn_count"):
            assert field not in result, f"opencode must NOT emit {field}"


class TestRouterExtractSignalIntegration:
    def test_main_routes_chat_extract_signal_noop_end_to_end(
        self, tmp_path, monkeypatch, projects_at_tmp, capsys
    ):
        """The router dispatches the op; a missing transcript yields a no-op TOON."""
        marshal_dir = tmp_path / ".plan"
        marshal_dir.mkdir(parents=True, exist_ok=True)
        (marshal_dir / "marshal.json").write_text(
            json.dumps({"runtime": {"target": "claude"}}), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        rc = platform_runtime.main(
            [
                "chat",
                "extract-signal",
                "--session-id",
                "22222222-2222-2222-2222-222222222277",
            ]
        )
        assert rc == 0
        emitted = _parse(capsys.readouterr().out)
        assert emitted["status"] == "no-op"
        assert emitted["operation"] == "chat extract-signal"
        assert emitted["reason"] == "transcript_not_found"

    def test_main_rejects_abbreviated_session_flag(self, tmp_path, monkeypatch, projects_at_tmp):
        """``allow_abbrev=False``: a prefix of --session-id is not accepted.

        The router's argparse exits with SystemExit(2) on the unrecognised
        argument name, exactly as the per-op parser does.
        """
        marshal_dir = tmp_path / ".plan"
        marshal_dir.mkdir(parents=True, exist_ok=True)
        (marshal_dir / "marshal.json").write_text(
            json.dumps({"runtime": {"target": "claude"}}), encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit):
            platform_runtime.main(
                [
                    "chat",
                    "extract-signal",
                    "--session",
                    "22222222-2222-2222-2222-222222222277",
                ]
            )
