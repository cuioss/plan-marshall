# SPDX-License-Identifier: FSL-1.1-ALv2
"""Consumer routing and field-mapping tests for ``extract-chat-signal.py``.

The consumer no longer parses a transcript: it hands the platform-runtime
``chat extract-signal`` operation a ``session_id`` (via :func:`_run_chat_signal_op`)
and translates the runtime's normalized record into the aspect's Tier-1/Tier-2
contract. These tests drive ``cmd_run`` through a monkeypatched
``_run_chat_signal_op`` and pin that translation — the field-name mapping, the
consumer-owned ``over_budget`` decision, and the skip-token routing for a
runtime no-op / uninvokable op.

Where a runtime test already pins a behaviour (the reducer, the counters, the
gate channel), this module does NOT restate it — it pins only what the consumer
owns: the hop semantics and the translation.
"""

from __future__ import annotations

from _extract_chat_signal_fixtures import (
    SESSION_ID,
    _runtime_record,
)

from conftest import parse_ns  # noqa: E402


def _run(monkeypatch, record, status='success', *, read_budget=None, session_id=SESSION_ID):
    """Drive ``cmd_run`` through the mocked hop seam."""
    import _extract_chat_signal_fixtures as fx

    def _fake(_sid):
        return record, status

    monkeypatch.setattr(fx._mod, '_run_chat_signal_op', _fake)
    args = parse_ns(
        'plan-marshall',
        'plan-retrospective',
        'extract-chat-signal.py',
        'run',
        '--session-id',
        session_id,
    )
    if read_budget is not None:
        args.read_budget_bytes = read_budget
    return fx._mod.cmd_run(args)


class TestRouting:
    def test_success_record_maps_the_seven_fields(self, monkeypatch):
        record = _runtime_record(
            raw_turn_count=25,
            kept_raw_count=7,
            operator_turn_count=3,
            gate_decision_count=2,
            reduced_bytes=4096,
            no_signal=False,
            reduced_transcript='user: please revert that change',
            transcript_path='/transcripts/p/session.jsonl',
        )
        result = _run(monkeypatch, record, 'success')

        assert result['status'] == 'success'
        assert result['aspect'] == 'chat-signal-extraction'
        assert result['session_id'] == SESSION_ID
        # Field-name mapping: runtime ``kept_raw_count`` → consumer
        # ``reduced_turn_count``, so existing aggregations keep their vocabulary.
        assert result['reduced_turn_count'] == 7
        assert result['dropped_turn_count'] == 25 - 7
        assert result['raw_turn_count'] == 25
        assert result['operator_turn_count'] == 3
        assert result['gate_decision_count'] == 2
        assert result['reduced_bytes'] == 4096
        assert result['no_signal'] is False
        assert result['reduced_transcript'] == 'user: please revert that change'
        assert result['transcript_path'] == '/transcripts/p/session.jsonl'

    def test_no_signal_is_forwarded_from_the_runtime(self, monkeypatch):
        """The consumer forwards ``no_signal``; the runtime derives it."""
        result = _run(monkeypatch, _runtime_record(no_signal=True), 'success')
        assert result['status'] == 'success'
        assert result['no_signal'] is True

    def test_noop_routes_to_skipped_not_success(self, monkeypatch):
        """A runtime no-op (no transcript) is the canonical data-absence token."""
        result = _run(monkeypatch, None, 'no-op')
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'
        assert result['no_signal'] is True
        assert result['over_budget'] is False

    def test_error_status_routes_to_skipped_too(self, monkeypatch):
        """The skip token contract keys on the absence, not the runtime status."""
        result = _run(monkeypatch, None, 'error')
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'

    def test_uninvokable_op_routes_to_skipped(self, monkeypatch):
        """``_run_chat_signal_op`` returning ``(None, None)`` still degrades."""
        result = _run(monkeypatch, None, None)
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'

    def test_skipped_branch_zeroes_the_counters(self, monkeypatch):
        result = _run(monkeypatch, None, 'no-op')
        for key in (
            'raw_turn_count',
            'reduced_turn_count',
            'dropped_turn_count',
            'operator_turn_count',
            'gate_decision_count',
            'reduced_bytes',
        ):
            assert result[key] == 0
        assert result['reduced_transcript'] == ''

    def test_skipped_branch_reports_session_id_and_budget(self, monkeypatch):
        result = _run(monkeypatch, None, 'no-op', read_budget=12345)
        assert result['session_id'] == SESSION_ID
        assert result['read_budget_bytes'] == 12345


class TestBudgetOwnership:
    def test_over_budget_derived_by_consumer_not_runtime(self, monkeypatch):
        """The runtime never reports ``over_budget``; the consumer derives it.

        The record carries no ``over_budget`` field — the runtime made no
        decision. The consumer compares ``reduced_bytes`` against its own
        ``read_budget_bytes``.
        """
        record = _runtime_record(reduced_bytes=1500)
        assert 'over_budget' not in record
        result = _run(monkeypatch, record, 'success', read_budget=1000)
        assert result['over_budget'] is True

    def test_over_budget_strictly_greater_than(self, monkeypatch):
        """An exact fit still routes: ``over_budget`` is ``>`` not ``>=``."""
        result = _run(monkeypatch, _runtime_record(reduced_bytes=100), 'success', read_budget=100)
        assert result['over_budget'] is False
        result = _run(monkeypatch, _runtime_record(reduced_bytes=101), 'success', read_budget=100)
        assert result['over_budget'] is True

    def test_default_budget_is_two_mib(self):
        from _extract_chat_signal_fixtures import _mod

        assert _mod.DEFAULT_READ_BUDGET_BYTES == 2 * 1024 * 1024

    def test_default_budget_used_when_flag_omitted(self, monkeypatch):
        result = _run(monkeypatch, _runtime_record(reduced_bytes=50), 'success')
        from _extract_chat_signal_fixtures import _mod

        assert result['read_budget_bytes'] == _mod.DEFAULT_READ_BUDGET_BYTES


class TestRecordDrift:
    def test_missing_reduced_bytes_treated_as_zero(self, monkeypatch):
        record = dict(_runtime_record())
        del record['reduced_bytes']
        result = _run(monkeypatch, record, 'success')
        assert result['reduced_bytes'] == 0
        assert result['over_budget'] is False

    def test_non_integer_counts_coerced_for_consumer_fields(self, monkeypatch):
        """The mapped fields the consumer derives are coerced via ``int``.

        ``raw_turn_count`` is the runtime's own counter and is passed through
        verbatim; only the fields the consumer computes or remaps
        (``reduced_turn_count``, ``dropped_turn_count``, ``operator_turn_count``,
        ``gate_decision_count``, ``reduced_bytes``) go through ``int()``.
        """
        record = _runtime_record(raw_turn_count='4', kept_raw_count='2')
        result = _run(monkeypatch, record, 'success')
        assert result['reduced_turn_count'] == 2
        assert result['reduced_bytes'] == 0
        assert result['dropped_turn_count'] == 2

    def test_missing_transcript_path_yields_none(self, monkeypatch):
        record = dict(_runtime_record())
        del record['transcript_path']
        result = _run(monkeypatch, record, 'success', session_id=SESSION_ID)
        assert result['status'] == 'success'
        assert result['transcript_path'] is None

    def test_missing_kept_raw_count_defaults_zero(self, monkeypatch):
        record = dict(_runtime_record())
        del record['kept_raw_count']
        result = _run(monkeypatch, record, 'success')
        assert result['reduced_turn_count'] == 0
