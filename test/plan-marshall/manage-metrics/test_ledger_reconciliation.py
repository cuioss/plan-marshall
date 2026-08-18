#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-ledger reconciliation: a disagreement becomes a finding, not a silent choice.

The two row ledgers — `execution.toon`'s `execution_log[]` and each phase's
`work/metrics-dispatch-boundaries-{phase}.toon` — are written by independent
call sites with no shared transaction and no shared key, so a dispatch can land
in one and not the other in BOTH directions. Nothing previously reconciled them,
and nothing told a reader that only their union counts every dispatch.

These tests pin that the reconciliation emits one finding per divergent row in
each direction, that the two partiality shapes are labelled DISTINCTLY (a phase
whose boundary never closed versus a row with no partner), that a re-entered
phase is called out as its own shape, and that a structurally-impossible absence
is declared rather than reported. Each includes a negative control, because a
reconciliation that fires on agreement is worse than none.
"""

import importlib.util
from datetime import UTC, datetime, timedelta

import pytest
from _manage_metrics_fixtures import (
    ns,
    ns_end_phase,
    ns_record_dispatch_boundary,
    ns_start_phase,
)
from toon_parser import serialize_toon

from conftest import get_script_path, load_script_module

_spec = importlib.util.spec_from_file_location(
    'manage_metrics_reconcile', get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')
)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)

cmd_start_phase = manage_metrics.cmd_start_phase
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_record_dispatch_boundary = manage_metrics.cmd_record_dispatch_boundary
cmd_reconcile_ledgers = manage_metrics.cmd_reconcile_ledgers

_ledger = load_script_module(
    'plan-marshall', 'manage-metrics', '_ledger_reconciliation.py', 'ledger_reconciliation_mod'
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        plan_dir = real_get_plan_dir(plan_id)
        plan_dir.mkdir(parents=True, exist_ok=True)
        sentinel = plan_dir / 'status.json'
        if not sentinel.is_file():
            sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


def _ns_reconcile(plan_id: str, window_seconds: int | None = None):
    argv = ['reconcile-ledgers', '--plan-id', plan_id]
    if window_seconds is not None:
        argv += ['--window-seconds', str(window_seconds)]
    return ns(*argv)


def _write_execution_log(plan_context, plan_id: str, rows: list[tuple[str, str, str, int]]) -> None:
    """Write an `execution.toon` holding the given `execution_log[]` rows.

    Each row is `(step_id, phase, timestamp, total_tokens)`. Serialized through
    the PRODUCTION `serialize_toon`, so the reconciliation is exercised against
    the tabular `execution_log[N]{cols}:` bytes the manifest writer actually
    produces. A hand-written shape would let these tests pass against a form
    nothing emits — and the first draft of this helper did exactly that, guessing
    a dotted `execution_log.0.step_id` layout the writer never emits.

    An empty row list writes a manifest carrying no `execution_log` key at all:
    that is the readable-but-empty state, which the reconciliation must
    distinguish from an unreadable manifest.
    """
    manifest: dict = {'plan_id': plan_id}
    if rows:
        manifest['execution_log'] = [
            {
                'step_id': step_id,
                'phase': phase,
                'outcome': 'executed',
                'total_tokens': total_tokens,
                'tool_uses': 0,
                'duration_ms': 0,
                'timestamp': timestamp,
            }
            for step_id, phase, timestamp, total_tokens in rows
        ]
    plan_dir = plan_context.plan_dir_for(plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'execution.toon').write_text(serialize_toon(manifest), encoding='utf-8')


def _boundary_timestamps(plan_context, plan_id: str, phase: str) -> list[str]:
    path = plan_context.plan_dir_for(plan_id) / 'work' / f'metrics-dispatch-boundaries-{phase}.toon'
    return [
        line.split(',', 1)[0].strip()
        for line in path.read_text(encoding='utf-8').splitlines()
        if line and not line.startswith(('plan_id:', 'phase:', 'rows[]'))
    ]


def _parse_stamp(raw: str) -> datetime:
    """Parse a recorded ISO timestamp, tolerating the writer's `Z` suffix."""
    return datetime.fromisoformat(raw.strip().replace('Z', '+00:00'))


def _findings_of(result: dict, kind: str) -> list[dict]:
    return [finding for finding in result['findings'] if finding['finding'] == kind]


class TestManifestParsing:
    """The execution-log reader parses what the manifest writer produces."""

    def test_execution_log_rows_are_read_from_the_manifest(self, plan_context):
        _write_execution_log(
            plan_context, 'recon-parse',
            [('push', '6-finalize', '2026-01-01T10:00:00+00:00', 4000)],
        )
        rows, reason = _ledger.load_execution_log(plan_context.plan_dir_for('recon-parse'))

        assert reason == ''
        assert rows is not None
        assert _ledger.execution_rows_for_phase(rows, '6-finalize')[0]['step_id'] == 'push'


class TestDivergentRowsProduceFindings:
    """One finding per row present in one ledger and absent from the other."""

    def test_a_boundary_row_with_no_execution_log_row_is_a_finding(self, plan_context):
        """Spend recorded at the dispatch boundary that no execution_log sum sees."""
        plan_id = 'recon-orphan-boundary'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=90000)
        )
        # An execution log that exists and is readable, but names nothing here.
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        orphans = _findings_of(result, 'row_absent_from_execution_log')
        assert len(orphans) == 1
        assert orphans[0]['phase'] == '6-finalize'
        assert orphans[0]['total_tokens'] == 90000

    def test_an_execution_log_row_with_no_boundary_row_is_a_finding(self, plan_context):
        """The divergence is reported in BOTH directions, not only one."""
        plan_id = 'recon-orphan-exec'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        _write_execution_log(
            plan_context, plan_id,
            [('push', '6-finalize', '2026-01-01T10:00:00+00:00', 4000)],
        )

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        orphans = _findings_of(result, 'row_absent_from_boundary_ledger')
        assert len(orphans) == 1
        assert orphans[0]['step_id'] == 'push'

    def test_one_finding_per_divergent_row_not_one_per_phase(self, plan_context):
        """Three unpaired boundary rows are three findings."""
        plan_id = 'recon-per-row'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        for tokens in (100, 200, 300):
            cmd_record_dispatch_boundary(
                ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=tokens)
            )
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        assert len(_findings_of(result, 'row_absent_from_execution_log')) == 3

    def test_agreeing_ledgers_produce_no_divergence_finding(self, plan_context):
        """The negative control: a paired row is not reported.

        Without it, a reconciliation that fires on everything would satisfy every
        positive test above while carrying no information at all.
        """
        plan_id = 'recon-agree'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=4000)
        )
        cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=4000))
        # Pair on the boundary row's own recorded timestamp.
        stamp = _boundary_timestamps(plan_context, plan_id, '6-finalize')[0]
        _write_execution_log(plan_context, plan_id, [('push', '6-finalize', stamp, 4000)])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        assert _findings_of(result, 'row_absent_from_execution_log') == []
        assert _findings_of(result, 'row_absent_from_boundary_ledger') == []
        assert result['findings_count'] == 0

    def test_the_window_is_a_real_bound_in_both_directions(self, plan_context):
        """One corpus, two windows: the gap decides whether the rows pair.

        The positive control is inside the test on purpose. Asserting only that a
        narrow window fails to pair would pass against a reconciliation that
        never pairs anything, so the SAME corpus is re-run at a window wide
        enough to admit the gap and must then reconcile clean.
        """
        plan_id = 'recon-window'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=4000)
        )
        cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=4000))
        boundary_stamp = _parse_stamp(_boundary_timestamps(plan_context, plan_id, '6-finalize')[0])
        # Ten minutes after the boundary row — outside a 60s window, inside 3600s.
        _write_execution_log(
            plan_context, plan_id,
            [('push', '6-finalize', (boundary_stamp + timedelta(minutes=10)).isoformat(), 4000)],
        )

        narrow = cmd_reconcile_ledgers(_ns_reconcile(plan_id, window_seconds=60))
        wide = cmd_reconcile_ledgers(_ns_reconcile(plan_id, window_seconds=3600))

        assert len(_findings_of(narrow, 'row_absent_from_boundary_ledger')) == 1
        assert len(_findings_of(narrow, 'row_absent_from_execution_log')) == 1
        assert wide['findings_count'] == 0


class TestTheTwoPartialityShapes:
    """D4's required shapes: never-closed, and closed-then-re-entered."""

    def test_a_never_closed_phase_is_labelled_distinctly_from_an_absent_row(self, plan_context):
        """`boundary_never_closed` and `row_absent_*` are different findings.

        Collapsing them would report a whole unclosed phase as a pile of orphan
        rows, hiding that the ROWS are present and that what no close recorded is
        the phase's own summary of them.
        """
        plan_id = 'recon-unclosed'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=500000)
        )
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        unclosed = _findings_of(result, 'boundary_never_closed')
        assert len(unclosed) == 1
        assert unclosed[0]['total_tokens'] == 500000
        assert 'end_time' in unclosed[0]['detail']
        # The distinctness itself: the orphan row is ALSO reported, separately.
        assert len(_findings_of(result, 'row_absent_from_execution_log')) == 1

    def test_a_closed_phase_produces_no_never_closed_finding(self, plan_context):
        """The negative control for the never-closed shape."""
        plan_id = 'recon-closed'
        cmd_start_phase(ns_start_phase(plan_id, '6-finalize'))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '6-finalize', 'step_complete', total_tokens=500000)
        )
        cmd_end_phase(ns_end_phase(plan_id, '6-finalize', total_tokens=500000))
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        assert _findings_of(result, 'boundary_never_closed') == []

    def test_a_re_entered_phase_is_its_own_shape(self, plan_context):
        """Closed-then-re-entered: the aggregate is cumulative, the ledgers are not."""
        plan_id = 'recon-reentered'
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=1000))
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=2000))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '5-execute', 'step_complete', total_tokens=1000)
        )
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        re_entered = _findings_of(result, 'phase_re_entered')
        assert len(re_entered) == 1
        assert 'cumulative across closes' in re_entered[0]['detail']

    def test_a_single_close_produces_no_re_entry_finding(self, plan_context):
        """The negative control for the re-entry shape."""
        plan_id = 'recon-single-close'
        cmd_start_phase(ns_start_phase(plan_id, '5-execute'))
        cmd_end_phase(ns_end_phase(plan_id, '5-execute', total_tokens=1000))
        cmd_record_dispatch_boundary(
            ns_record_dispatch_boundary(plan_id, '5-execute', 'step_complete', total_tokens=1000)
        )
        _write_execution_log(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        assert _findings_of(result, 'phase_re_entered') == []


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
