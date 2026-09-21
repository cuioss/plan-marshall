# SPDX-License-Identifier: FSL-1.1-ALv2
"""Consumer routing and field-mapping tests for ``extract-chat-signal.py``.

The consumer no longer parses a transcript: it hands the platform-runtime
``chat extract-signal`` operation a ``session_id`` (via :func:`_run_chat_signal_op`)
and translates the runtime's normalized record into the aspect's Tier-1/Tier-2
contract. These tests drive ``cmd_run`` through a monkeypatched
``_run_chat_signal_op`` and pin that translation — the field-name mapping, the
consumer-owned ``over_budget`` decision (taken on DELIVERED bytes, never on the
forwarded ``reduced_bytes``), the transcript's survival across the TOON boundary
``main()`` prints through, and the skip-token routing for a runtime no-op /
uninvokable op.

Where a runtime test already pins a behaviour (the reducer, the counters, the
gate channel), this module does NOT restate it — it pins only what the consumer
owns: the hop semantics and the translation.
"""

from __future__ import annotations

from _extract_chat_signal_fixtures import (
    SESSION_ID,
    TRANSCRIPT_WITH_TOON_SHAPES,
    _runtime_record,
    emit_and_reparse,
    transcript_of_exactly,
)
from _extract_chat_signal_fixtures import (
    run_consumer as _run,
)

# (run_consumer lives in the shared fixture module; the _run alias keeps every
# call site reading naturally while the one authoritative copy stays singular.)


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

    def test_new_consumer_fields_forwarded_with_non_default_values(self, monkeypatch):
        """The added kept-text / population / residual / guard fields map through.

        Each new consumer field is asserted with a non-default value so the
        test fails when the mapping drops the field rather than forwarding
        the runtime record.
        """
        record = _runtime_record(
            kept_text_chars=512,
            kept_text_bytes=520,
            signal_gate_population=4,
            residual_counts={'harness_injection': 2},
            symmetric_pair_dropped=1,
        )
        result = _run(monkeypatch, record, 'success')

        assert result['kept_text_chars'] == 512
        assert result['kept_text_bytes'] == 520
        assert result['signal_gate_population'] == 4
        assert result['residual_counts'] == {'harness_injection': 2}
        assert result['symmetric_pair_dropped'] == 1

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
        decision. The consumer measures the transcript IT emits and compares
        that against its own ``read_budget_bytes``.
        """
        record = _runtime_record(reduced_bytes=1500, reduced_transcript=transcript_of_exactly(1500))
        assert 'over_budget' not in record
        result = _run(monkeypatch, record, 'success', read_budget=1000)
        assert result['over_budget'] is True

    def test_over_budget_strictly_greater_than(self, monkeypatch):
        """An exact fit still routes: ``over_budget`` is ``>`` not ``>=``.

        The boundary is walked in DELIVERED bytes, which is the figure the
        comparison reads. Each arm states the size it built rather than leaving
        it to a literal a later edit could desynchronise from the budget.
        """
        fits = _runtime_record(reduced_transcript=transcript_of_exactly(100))
        result = _run(monkeypatch, fits, 'success', read_budget=100)
        assert result['reduced_transcript_delivered_bytes'] == 100
        assert result['over_budget'] is False

        one_over = _runtime_record(reduced_transcript=transcript_of_exactly(101))
        result = _run(monkeypatch, one_over, 'success', read_budget=100)
        assert result['reduced_transcript_delivered_bytes'] == 101
        assert result['over_budget'] is True

    def test_default_budget_is_two_mib(self):
        from _extract_chat_signal_fixtures import _mod

        assert _mod.DEFAULT_READ_BUDGET_BYTES == 2 * 1024 * 1024

    def test_default_budget_used_when_flag_omitted(self, monkeypatch):
        result = _run(monkeypatch, _runtime_record(reduced_bytes=50), 'success')
        from _extract_chat_signal_fixtures import _mod

        assert result['read_budget_bytes'] == _mod.DEFAULT_READ_BUDGET_BYTES


class TestDeliveredTranscript:
    """The payload survives its own serialization, and says how much it delivered.

    Two properties, each with the matched control that makes it non-vacuous:

    * **Survival** — the reduced transcript reads back byte-identical across the
      TOON boundary ``main()`` prints through, and no line of it becomes a
      top-level key. The control is the same payload with the transcript left
      unmarked, asserted to be corrupted — without it the positive arm could be
      passing because the round trip is trivially lossless for any string, which
      it is not.
    * **Measurement** — ``reduced_transcript_delivered_bytes`` measures what this
      script emits. The control is a record whose forwarded ``reduced_bytes``
      disagrees with it: a field that merely copied the runtime's figure passes
      an agreeing case and fails the disagreeing one.
    """

    def test_colon_bearing_transcript_survives_the_toon_boundary(self, monkeypatch):
        record = _runtime_record(
            no_signal=False,
            reduced_transcript=TRANSCRIPT_WITH_TOON_SHAPES,
            reduced_bytes=len(TRANSCRIPT_WITH_TOON_SHAPES.encode('utf-8')),
        )
        result = _run(monkeypatch, record, 'success')

        reparsed = emit_and_reparse(result)

        assert reparsed['reduced_transcript'] == TRANSCRIPT_WITH_TOON_SHAPES
        assert reparsed['status'] == 'success', 'a transcript line forged the envelope status'

    def test_no_phantom_top_level_key_appears(self, monkeypatch):
        """The emitted key set is the parsed key set — nothing leaked, nothing lost.

        A truncating emission loses the keys that followed the transcript and
        gains the transcript's own lines as siblings, so comparing the two sets
        catches both directions at once.
        """
        record = _runtime_record(no_signal=False, reduced_transcript=TRANSCRIPT_WITH_TOON_SHAPES)
        result = _run(monkeypatch, record, 'success')

        reparsed = emit_and_reparse(result)

        assert set(reparsed) == set(result), (
            f'emitted {sorted(set(result) - set(reparsed))} were lost; '
            f'{sorted(set(reparsed) - set(result))} appeared from nowhere'
        )

    def test_an_unmarked_transcript_would_corrupt_the_payload(self, monkeypatch):
        """The matched NEGATIVE control for the two survival arms above.

        Two corruptions are asserted, and a third is deliberately NOT — the
        envelope's own ``status`` is not forgeable at this payload's key order,
        so asserting it would be a vacuous premise rather than a missing guard.

        ``cmd_run`` builds its success return as ``{**base, **record, 'status':
        'success', ...}``. ``reduced_transcript`` arrives through ``**record``
        and therefore keeps *record's* position; ``status`` is in neither
        ``base`` nor ``record``, so it is inserted after every record key. The
        emitted document consequently carries the transcript FIRST and the
        genuine ``status: success`` line LAST. ``parse_toon`` is last-wins on a
        repeated top-level key, so the unmarked transcript's flush-left
        ``status: blocked`` line does become a phantom top-level key and is then
        overwritten by the real one emitted after it.

        ⛔ Do not "restore" a ``reparsed['status'] != 'success'`` assertion here:
        no fixture can satisfy it while ``status`` follows the transcript in key
        order. ⛔ And do not reorder the consumer payload to make such an
        assertion pass — re-emitting ``status`` after the transcript is exactly
        what makes the real envelope robust against a forged status line, so
        inverting it would trade a passing assertion for a genuine defect. The
        corruption this control exists to prove is still fully observable in the
        two assertions below: the transcript is truncated at its first newline,
        and its remaining lines surface as phantom sibling keys.
        """
        record = _runtime_record(no_signal=False, reduced_transcript=TRANSCRIPT_WITH_TOON_SHAPES)
        result = _run(monkeypatch, record, 'success')
        unmarked = dict(result)
        unmarked['reduced_transcript'] = str(result['reduced_transcript'])

        reparsed = emit_and_reparse(unmarked)

        assert reparsed['reduced_transcript'] != TRANSCRIPT_WITH_TOON_SHAPES, 'control did not lose the transcript'
        assert set(reparsed) != set(unmarked), 'control produced no phantom key'

    def test_delivered_bytes_equals_the_emitted_transcript_size(self, monkeypatch):
        record = _runtime_record(no_signal=False, reduced_transcript=TRANSCRIPT_WITH_TOON_SHAPES)
        result = _run(monkeypatch, record, 'success')

        emitted = emit_and_reparse(result)['reduced_transcript']

        assert result['reduced_transcript_delivered_bytes'] == len(emitted.encode('utf-8'))

    def test_delivered_and_forwarded_byte_counts_are_reported_separately(self, monkeypatch):
        """The matched control for the measurement arm: the two figures diverge.

        The runtime claims a reduction far larger than the text it handed over.
        A ``reduced_transcript_delivered_bytes`` that merely re-published the
        forwarded number would read 9000 here; the delivered figure is the size
        of what this script emits, and both are published so the gap is visible.
        """
        transcript = transcript_of_exactly(120)
        record = _runtime_record(no_signal=False, reduced_bytes=9000, reduced_transcript=transcript)
        result = _run(monkeypatch, record, 'success')

        assert result['reduced_bytes'] == 9000
        assert result['reduced_transcript_delivered_bytes'] == 120

    def test_skip_path_carries_the_same_delivery_shape(self, monkeypatch):
        """The skip path emits the key too, at the value its empty text earns."""
        result = _run(monkeypatch, None, 'no-op')

        assert result['reduced_transcript_delivered_bytes'] == 0
        assert emit_and_reparse(result)['reduced_transcript'] == ''


class TestRecordDrift:
    def test_missing_reduced_bytes_treated_as_zero(self, monkeypatch):
        """A record with no ``reduced_bytes`` forwards a zero, not a crash.

        ⛔ No ``over_budget`` assertion rides along here. The budget is decided
        on the DELIVERED figure, so a record missing the forwarded one says
        nothing about the verdict — asserting it anyway would read as evidence
        that the two are still wired together.
        """
        record = dict(_runtime_record())
        del record['reduced_bytes']
        result = _run(monkeypatch, record, 'success')
        assert result['reduced_bytes'] == 0

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
        distinct = '33333333-3333-3333-3333-333333333333'
        result = _run(monkeypatch, record, 'success', session_id=distinct)
        assert result['status'] == 'success'
        assert result['transcript_path'] is None

    def test_missing_kept_raw_count_defaults_zero(self, monkeypatch):
        record = dict(_runtime_record())
        del record['kept_raw_count']
        result = _run(monkeypatch, record, 'success')
        assert result['reduced_turn_count'] == 0
