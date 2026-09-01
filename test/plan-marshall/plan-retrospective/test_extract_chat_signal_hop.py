# SPDX-License-Identifier: FSL-1.1-ALv2
"""The real subprocess hop of ``extract-chat-signal.py`` against TOON stdout.

``cmd_run`` tests drive ``_run_chat_signal_op`` through a monkeypatched seam so
the consumer logic is tested without a live executor. That bypasses exactly the
surface these tests exist to guard: turning the runtime's TOON stdout into the
record ``cmd_run`` translates. ``platform_runtime`` emits TOON (``toon_success``),
never JSON, so the hop must parse with ``toon_parser.parse_toon`` — a
``json.loads`` reader would raise on every real response and the consumer would
silently skip. Only ``subprocess.run`` is replaced here; the original
``_run_chat_signal_op`` parsing runs untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from types import SimpleNamespace  # noqa: E402

from _extract_chat_signal_fixtures import SESSION_ID, _mod  # noqa: E402

# The TOON success document ``chat_extract_signal`` emits on stdout, exactly as
# ``runtime_base.toon_success`` + ``serialize_toon`` render it (flat fields,
# lowercase booleans). This is the real wire format the hop must parse.
_TOON_SUCCESS = (
    "status: success\n"
    "operation: chat extract-signal\n"
    f"session_id: {SESSION_ID}\n"
    "transcript_path: /transcripts/project/session.jsonl\n"
    "reduced_transcript: user: please revert that change\n"
    "raw_turn_count: 25\n"
    "kept_raw_count: 7\n"
    "operator_turn_count: 3\n"
    "gate_decision_count: 2\n"
    "reduced_bytes: 4096\n"
    "no_signal: false\n"
)

_TOON_NOOP = (
    "status: no-op\n"
    "operation: chat extract-signal\n"
    "reason: transcript_not_found\n"
    "alternative: run on a target that exposes a session transcript, or record "
    "the session with session capture first\n"
)


def _run_hop(monkeypatch, stdout):
    """Drive the real ``_run_chat_signal_op`` with only ``subprocess.run`` faked."""
    monkeypatch.setattr(
        _mod.subprocess,
        'run',
        lambda *a, **k: SimpleNamespace(stdout=stdout),
    )
    return _mod._run_chat_signal_op(SESSION_ID)


class TestToonSuccessParsing:
    def test_success_record_is_parsed_from_toon_stdout(self, monkeypatch):
        record, status = _run_hop(monkeypatch, _TOON_SUCCESS)
        assert status == 'success'
        assert record['raw_turn_count'] == 25
        assert record['kept_raw_count'] == 7
        assert record['operator_turn_count'] == 3
        assert record['gate_decision_count'] == 2
        assert record['reduced_bytes'] == 4096
        assert record['no_signal'] is False
        assert record['transcript_path'] == '/transcripts/project/session.jsonl'
        assert record['reduced_transcript'] == 'user: please revert that change'

    def test_no_op_is_not_treated_as_success(self, monkeypatch):
        record, status = _run_hop(monkeypatch, _TOON_NOOP)
        assert status == 'no-op'
        assert record is None


class TestUnparseableOutput:
    def test_garbage_stdout_degrades_to_none(self, monkeypatch):
        record, status = _run_hop(monkeypatch, 'not toon at all')
        assert status is None
        assert record is None
