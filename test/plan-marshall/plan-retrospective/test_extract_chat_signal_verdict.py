# SPDX-License-Identifier: FSL-1.1-ALv2
"""Skip-token and routing-verdict tests for the ``extract-chat-signal.py`` consumer.

The two-tier degradation path keys on two tokens that are normative in
``references/chat-history-analysis.md``:

- ``transcript_unavailable`` — the runtime declined (no transcript) or the op
  could not be invoked; the consumer surfaces the genuine-absence token.
- ``transcript_too_large`` — NOT emitted here; a transcript that fits is fed to
  Tier 1, and one that exceeds the read budget is refused by the orchestrator
  from ``over_budget``.

⛔ Every budget case in this module sizes its own reduced transcript, because
``over_budget`` is derived from ``reduced_transcript_delivered_bytes`` — the
text this consumer emits — and never from the forwarded ``reduced_bytes``. A
case that only sets ``reduced_bytes`` states nothing about the verdict.

All reduction and counter semantics are runtime-owned and pinned in the
platform-runtime tests. This module pins only what the consumer owns: the
skip-token routing, the budget-derived verdict, and the transcript-path
passthrough.
"""

from __future__ import annotations

from _extract_chat_signal_fixtures import _runtime_record, transcript_of_exactly
from _extract_chat_signal_fixtures import run_consumer as _run


class TestSkipToken:
    def test_missing_transcript_is_transcript_unavailable(self, monkeypatch):
        """The no-op (no transcript) is the canonical absence token."""
        result = _run(monkeypatch, None, 'no-op')
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'

    def test_both_absent_and_withheld_map_to_the_same_token(self, monkeypatch):
        """A genuine data absence and a declined runtime both use the token.

        The transcript-present-but-absent distinction is the runtime's, surfaced
        as no-op vs success; this skill's downstream aggregation keys on the
        token, never on the runtime status.
        """
        absent = _run(monkeypatch, None, 'no-op')
        withheld = _run(monkeypatch, None, None)
        assert absent['reason'] == withheld['reason'] == 'transcript_unavailable'

    def test_over_budget_is_success_not_skipped(self, monkeypatch):
        """A transcript that exceeds the budget is still ``success``.

        ``over_budget`` is a routing decision for the orchestrator's Tier-2
        fallback, not a data absence — so ``status`` stays success and the
        payload keeps the reduced content. The transcript is sized past the
        budget, because the budget now reads the DELIVERED text; the forwarded
        ``reduced_bytes`` is left deliberately larger still, so the case cannot
        be passing on the figure it no longer consults.
        """
        record = _runtime_record(
            reduced_bytes=5000,
            no_signal=False,
            reduced_transcript=transcript_of_exactly(1400),
        )
        result = _run(monkeypatch, record, 'success', read_budget=1000)
        assert result['status'] == 'success'
        assert result['reduced_transcript_delivered_bytes'] == 1400
        assert result['over_budget'] is True
        assert 'reason' not in result


class TestVerdictPropagation:
    def test_no_signal_forwards_truthfully(self, monkeypatch):
        result = _run(monkeypatch, _runtime_record(no_signal=True), 'success')
        assert result['no_signal'] is True
        assert result['status'] == 'success'

    def test_skipped_forces_no_signal_true(self, monkeypatch):
        """An absent transcript is never healthy signal."""
        result = _run(monkeypatch, None, 'no-op')
        assert result['no_signal'] is True
        assert result['over_budget'] is False

    def test_over_budget_and_no_signal_independent(self, monkeypatch):
        """A big reduced transcript with real signal reads healthy-but-large.

        The transcript's size is stated here rather than inherited from a
        fixture default: the assertion is about a budget boundary, so the case
        that decides it belongs in the case, not in a default a later edit could
        move out from under this test without touching it.
        """
        record = _runtime_record(reduced_bytes=9000, no_signal=False, reduced_transcript=transcript_of_exactly(300))
        result = _run(monkeypatch, record, 'success', read_budget=100)
        assert result['over_budget'] is True
        assert result['no_signal'] is False

    def test_forwarded_over_budget_with_delivered_under_is_not_over_budget(self, monkeypatch):
        """The discriminating case: the derivation moved to the delivered figure.

        The forwarded ``reduced_bytes`` is far over the budget while the text
        this script actually emits is comfortably under it. An ``over_budget``
        still derived from the forwarded number reads ``True`` here; derived
        from what is delivered, it reads ``False``. Neither re-pinned case above
        can prove that on its own — each of those would also pass under the old
        derivation, because there both figures sit on the same side of the
        budget.
        """
        record = _runtime_record(reduced_bytes=9000, no_signal=False, reduced_transcript=transcript_of_exactly(50))
        result = _run(monkeypatch, record, 'success', read_budget=100)

        assert result['reduced_bytes'] == 9000
        assert result['reduced_transcript_delivered_bytes'] == 50
        assert result['over_budget'] is False


class TestTranscriptPath:
    def test_success_payload_carries_the_runtime_resolved_path(self, monkeypatch):
        """The path is the RUNTIME's discovery, passed through verbatim.

        This consumer never resolves a transcript path itself; the value is
        whatever the op attached.
        """
        record = _runtime_record(transcript_path='/proj/p/session.jsonl')
        result = _run(monkeypatch, record, 'success')
        assert result['transcript_path'] == '/proj/p/session.jsonl'

    def test_skipped_payload_carries_no_path(self, monkeypatch):
        """No transcript was resolved, so there is no path to report."""
        result = _run(monkeypatch, None, 'no-op')
        assert result['reason'] == 'transcript_unavailable'
        assert 'transcript_path' not in result
