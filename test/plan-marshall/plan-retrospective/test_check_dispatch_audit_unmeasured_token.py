# SPDX-License-Identifier: FSL-1.1-ALv2
"""The dispatch audit files the writer's ``unmeasured`` token as ``no_evidence``.

``ran_inline`` is the bucket a reader treats as evidence a step ran inline, so a
column nobody measured must never land there. The audit already refuses to coerce
an unreadable ``total_tokens`` to ``0``; these tests pin that the writer's
explicit ``unmeasured`` token takes the same route, and — the control that makes
the pair meaningful — that an explicitly-measured ``0`` still classifies
``ran_inline``.

Written as pure calls on the two derivations rather than through a materialized
plan directory: the classification is a property of the token record alone, and
the surrounding plan state is not what is under test.
"""


from __future__ import annotations

from conftest import load_script_module

_cda = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-dispatch-audit.py', 'cda_token_state_mod'
)

_core = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    '_manifest_core.py',
    module_name='_mem_core_cda_token_drift',
)

#: The phase the audit's finalize-scoped token reader accepts.
FINALIZE_PHASE = '6-finalize'


def _manifest(*rows: tuple[str, object]) -> dict:
    return {
        'execution_log': [
            {'step_id': step_id, 'phase': FINALIZE_PHASE, 'total_tokens': total_tokens}
            for step_id, total_tokens in rows
        ]
    }


class TestTokenRecordReading:
    """``finalize_token_records`` maps each cell to a value or to ``None``."""

    def test_the_unmeasured_token_reads_as_no_record(self):
        records = _cda.finalize_token_records(
            _manifest(('push', _core.UNMEASURED_COLUMN_TOKEN))
        )

        assert records['push'] is None

    def test_an_explicit_zero_still_reads_as_a_measurement(self):
        """The control: the change must not widen ``None`` to every zero-shaped cell."""
        records = _cda.finalize_token_records(_manifest(('push', 0)))

        assert records['push'] == 0

    def test_a_measured_value_is_unchanged(self):
        records = _cda.finalize_token_records(_manifest(('push', 12_000)))

        assert records['push'] == 12_000


class TestCoverageClassification:
    """The audit's own output separates the two zero-shaped states."""

    def test_an_unmeasured_column_lands_in_no_evidence(self):
        coverage = _cda.evaluate_dispatch_coverage(
            ['push'],
            _cda.finalize_token_records(_manifest(('push', _core.UNMEASURED_COLUMN_TOKEN))),
            finalize_dispatch_line_count=0,
        )

        assert coverage['no_evidence'] == 1
        assert coverage['no_evidence_steps'] == ['push']
        assert coverage['ran_inline'] == 0

    def test_a_measured_zero_lands_in_ran_inline(self):
        """The matched negative control for the assertion above."""
        coverage = _cda.evaluate_dispatch_coverage(
            ['push'],
            _cda.finalize_token_records(_manifest(('push', 0))),
            finalize_dispatch_line_count=0,
        )

        assert coverage['ran_inline'] == 1
        assert coverage['no_evidence'] == 0

    def test_an_unmeasured_column_is_not_counted_as_dispatched(self):
        """It contributes to no ``missing_dispatch_emission`` claim either."""
        coverage = _cda.evaluate_dispatch_coverage(
            ['push'],
            _cda.finalize_token_records(_manifest(('push', _core.UNMEASURED_COLUMN_TOKEN))),
            finalize_dispatch_line_count=0,
        )

        assert coverage['dispatched'] == 0
        assert coverage['missing_dispatch_emission'] == 0
        assert coverage['findings'] == []
