#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-ledger reconciliation: a disagreement becomes a finding, not a silent choice."""


from datetime import UTC, datetime, timedelta

from _ledger_reconciliation_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _findings_of,
    _ledger,
    _ns_reconcile,
    _seed_guarded_plan_dirs,
    _write_execution_log,
    cmd_end_phase,
    cmd_reconcile_ledgers,
    cmd_record_dispatch_boundary,
    cmd_start_phase,
    manage_metrics,
)
from _manage_metrics_fixtures import (
    ns_end_phase,
    ns_record_dispatch_boundary,
    ns_start_phase,
)

from conftest import load_script_module


class TestDeclaredAndUndecidableStates:
    """A structural absence is declared; an unreadable source is not a clean verdict."""

    def test_a_phase_the_execution_log_cannot_cover_is_declared_not_reported(self, plan_context):
        """4-plan boundary rows are absent from execution_log BY CONSTRUCTION."""
        plan_id = 'recon-structural'
        cmd_start_phase(ns_start_phase(plan_id, '4-plan'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '4-plan', 'step_complete', total_tokens=7000)
        )
        cmd_end_phase(ns_end_phase(plan_id, '4-plan', total_tokens=7000))
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        block = next(b for b in result['phases'] if b['phase'] == '4-plan')
        assert block['state'] == 'structurally_excluded'
        assert '5-execute, 6-finalize' in block['reason']
        # Declared, so its one boundary row is NOT reported as a divergence.
        assert _findings_of(result, 'row_absent_from_execution_log') == []

    def test_an_unreadable_execution_log_is_not_evaluated_rather_than_clean(self, plan_context):
        """A missing manifest must not turn every boundary row into an orphan."""
        plan_id = 'recon-no-manifest'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=8000)
        )

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        assert result['execution_log_readable'] is False
        assert 'not found' in result['execution_log_reason']
        block = next(b for b in result['phases'] if b['phase'] == '6-finalize')
        assert block['state'] == 'not_evaluated'
        assert _findings_of(result, 'row_absent_from_execution_log') == []

    def test_the_union_is_published_per_phase_and_in_total(self, plan_context):
        """Neither ledger's own count is the number of dispatches; the union is.

        Two boundary rows and one unrelated execution-log row are three distinct
        observations: each ledger under-reports on its own, and only the union
        shows all three.
        """
        plan_id = 'recon-union'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        for tokens in (100, 200):
            cmd_record_dispatch_boundary(
                ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=tokens)
            )
        _write_execution_log(
            plan_context, plan_id,
            [('push', '6-finalize', '2020-01-01T00:00:00+00:00', 4000)],
        )

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        block = next(b for b in result['phases'] if b['phase'] == '6-finalize')
        assert block['execution_log_rows'] == 1
        assert block['boundary_rows'] == 2
        assert block['union_rows'] == 3
        assert result['union_rows'] == 3

    def test_reconciliation_mutates_nothing(self, plan_context):
        """The reconciliation is a reader. Its inputs are byte-identical after."""
        plan_id = 'recon-readonly'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=8000)
        )
        cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=8000))
        _write_execution_log(plan_context, plan_id, [])
        plan_dir = plan_context.plan_dir_for(plan_id)
        before = {
            path: path.read_bytes()
            for path in sorted(plan_dir.rglob('*'))
            if path.is_file()
        }

        cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        after = {
            path: path.read_bytes()
            for path in sorted(plan_dir.rglob('*'))
            if path.is_file()
        }
        assert after == before


def test_reconciliation_execution_log_phases_match_writer():
    """The mirrored ledger population is held to its writer, not to prose.

    `manage-metrics` runs in a different process from `manage-execution-manifest`
    and cannot import its private module at runtime, so the population it
    declares is a hand-mirror. A widened writer would otherwise leave this module
    declaring phases structurally excluded that the ledger had started covering —
    suppressing real findings under a stale declaration.
    """
    core = load_script_module(
        'plan-marshall', 'manage-execution-manifest', '_manifest_core.py', 'mc_reconcile_drift'
    )

    assert tuple(_ledger.EXECUTION_LOG_PHASES) == tuple(core.VALID_RECORD_PHASES)


class TestPairingIsMaximal:
    """An unpaired row is a real absence, never an artefact of the pairing order."""

    @staticmethod
    def _row(offset_seconds: int, label: str) -> dict:
        stamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=offset_seconds)
        return {
            'step_id': f'{label}{offset_seconds}',
            'timestamp': stamp.isoformat(),
            'parsed_timestamp': stamp,
            'total_tokens': 0,
            'outcome': 'executed',
            'termination_cause': 'step_complete',
        }

    def test_a_nearer_partner_is_given_up_when_another_row_needs_it(self):
        """The case greedy nearest-first gets wrong, and reports twice.

        Boundary rows at t=0 and t=250, execution rows at t=240 and t=500, window
        300 s. Nearest-first lets t=240 take t=250 (gap 10) over t=0 (gap 240),
        stranding t=500 and t=0 although each has a legal partner — two findings
        where a perfect pairing exists. Both ledgers agree here, so the honest
        answer is no finding at all.
        """
        execution_rows = [self._row(240, 'e'), self._row(500, 'e')]
        boundary_rows = [self._row(0, 'b'), self._row(250, 'b')]

        pairs, unpaired_execution, unpaired_boundary = _ledger.pair_rows(
            execution_rows, boundary_rows, 300
        )

        assert len(pairs) == 2
        assert unpaired_execution == []
        assert unpaired_boundary == []

    def test_a_genuine_absence_is_still_reported(self):
        """The negative control: maximal pairing does not mean pairing everything.

        Without it, a `pair_rows` that paired every row unconditionally would
        satisfy the test above while destroying the verb's whole purpose.
        """
        execution_rows = [self._row(0, 'e'), self._row(10000, 'e')]
        boundary_rows = [self._row(0, 'b')]

        pairs, unpaired_execution, unpaired_boundary = _ledger.pair_rows(
            execution_rows, boundary_rows, 300
        )

        assert len(pairs) == 1
        assert [row['step_id'] for row in unpaired_execution] == ['e10000']
        assert unpaired_boundary == []

    def test_which_rows_are_reported_does_not_depend_on_input_order(self):
        """The REPORTED set is stable under re-ordering — including under ties.

        The corpus is chosen so a row is genuinely left over (a perfect matching
        would make this vacuous: every ordering trivially reports nothing) and so
        two execution rows share a timestamp. Ties are the case that matters:
        Python's sort is stable, so before the sort key became total the
        manifest's own row order decided which tied row went unpaired, and the
        same data written in a different order named a different dispatch in the
        emitted finding.
        """
        tied_a = self._row(100, 'a')
        tied_b = self._row(100, 'b')
        execution_rows = [tied_a, tied_b]
        boundary_rows = [self._row(100, 'x')]

        forward = _ledger.pair_rows(execution_rows, boundary_rows, 300)
        swapped = _ledger.pair_rows([tied_b, tied_a], boundary_rows, 300)

        # Precondition: exactly one row IS left over, so there is something to
        # disagree about.
        assert len(forward[1]) == 1
        assert [row['step_id'] for row in forward[1]] == [row['step_id'] for row in swapped[1]]
        assert [row['step_id'] for row in forward[2]] == [row['step_id'] for row in swapped[2]]

    def test_the_sort_key_is_total_over_the_rows_own_values(self):
        """Two rows sharing a timestamp order by their remaining recorded fields.

        Pinned directly, because the ordering is what makes the reported set a
        property of the data rather than of the manifest's row order — and a
        timestamp-only key looks correct while leaving that decided by input
        order.
        """
        first = self._row(100, 'a')
        second = self._row(100, 'b')

        assert _ledger._row_sort_key(first) < _ledger._row_sort_key(second)
        assert _ledger._row_sort_key(first)[:2] == _ledger._row_sort_key(second)[:2]


class TestMixedTimezoneAwarenessDoesNotCrash:
    """A stamp with no offset is read as UTC, not left naive to poison a compare.

    Mixing naive and aware datetimes in one phase makes the sort and the pairing
    subtraction raise `TypeError` — an uncaught crash, where this module's rule
    is that unusable input degrades to a reported state. Both writers emit an
    explicit UTC offset, so reading a bare stamp as UTC is the only reading
    consistent with the corpus.
    """

    @staticmethod
    def _row(stamp: str, label: str) -> dict:
        return {
            'step_id': label,
            'timestamp': stamp,
            'parsed_timestamp': _ledger._parse_iso(stamp),
            'total_tokens': 0,
            'outcome': 'executed',
            'termination_cause': 'step_complete',
        }

    def test_a_zoneless_stamp_parses_aware(self):
        parsed = _ledger._parse_iso('2026-01-01T10:00:00')

        assert parsed is not None
        assert parsed.tzinfo is not None
        assert parsed == datetime(2026, 1, 1, 10, tzinfo=UTC)

    def test_mixed_awareness_pairs_instead_of_raising(self):
        """The reviewer-reported crash: naive on one side, aware on the other."""
        execution_rows = [self._row('2026-01-01T10:00:00', 'e-naive')]
        boundary_rows = [self._row('2026-01-01T10:00:10Z', 'b-aware')]

        pairs, unpaired_execution, unpaired_boundary = _ledger.pair_rows(
            execution_rows, boundary_rows, 300
        )

        assert len(pairs) == 1
        assert unpaired_execution == []
        assert unpaired_boundary == []

    def test_mixed_awareness_sorts_instead_of_raising(self):
        """The same crash on the sort path, which runs before any pairing."""
        rows = [
            self._row('2026-01-01T10:00:10Z', 'aware'),
            self._row('2026-01-01T10:00:00', 'naive'),
        ]

        assert [row['step_id'] for row in sorted(rows, key=_ledger._row_sort_key)] == [
            'naive',
            'aware',
        ]
