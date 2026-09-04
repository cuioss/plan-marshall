#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-ledger reconciliation reads a three-state token column, not a number.

``execution_log[]``'s token columns are three-state: a measured value, the
writer's ``unmeasured`` token for a column whose flag the caller omitted, or an
unrecognised cell. This reader used to run every cell through an ``_as_int``
coercion that returned ``0`` for all three, so an unmeasured column re-entered
the reconciliation looking like a dispatch that spent nothing.

These tests pin the distinction at THIS reader's own output — a measured ``0``
and an unmeasured column must be separable in what the reconciliation returns,
not merely in what the writer wrote. Each has its measured-value control beside
it, because a reader that labelled everything ``unmeasured`` would satisfy the
positive half alone.

The contract covers BOTH ledgers. The dispatch-boundary reader was left running
its cell through an ``_as_int`` coercion that returns ``0`` for this module's own
``unmeasured`` token, and the two boundary-derived findings then hard-stamped
``COLUMN_MEASURED`` whatever the rows carried — so the classes below pin the
boundary reader's per-row state, the DERIVED (never stamped) aggregate state of a
sum taken over those rows, and the population coverage published beside it.
"""


from _ledger_reconciliation_fixtures import (  # a fixture is used by NAME, not by reference
    _findings_of,
    _ledger,
    _ns_reconcile,
    _seed_guarded_plan_dirs,
    cmd_reconcile_ledgers,
    cmd_start_phase,
    manage_metrics,
)
from _manage_metrics_fixtures import ns_start_phase
from toon_parser import serialize_toon

from conftest import load_script_module

#: One phase for every row below — the reconciliation's per-phase blocks are not
#: what these tests measure, so keeping them in one phase keeps the arrange short.
PHASE = '6-finalize'


def _write_rows(plan_context, plan_id: str, rows: list[tuple[str, object]]) -> None:
    """Write an ``execution.toon`` whose rows carry the given ``total_tokens`` cells.

    Each row is ``(step_id, total_tokens)`` and the cell is written VERBATIM, so a
    test can put the writer's ``unmeasured`` token — or any other non-numeric
    value — into the column the reader is under test for.
    """
    manifest = {
        'plan_id': plan_id,
        'execution_log': [
            {
                'step_id': step_id,
                'phase': PHASE,
                'outcome': 'executed',
                'total_tokens': total_tokens,
                'tool_uses': 0,
                'duration_ms': 0,
                'timestamp': f'2026-01-01T10:0{index}:00+00:00',
            }
            for index, (step_id, total_tokens) in enumerate(rows)
        ],
    }
    plan_dir = plan_context.plan_dir_for(plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'execution.toon').write_text(serialize_toon(manifest), encoding='utf-8')


class TestTokenColumnStates:
    """``read_token_column`` separates the three states and keeps the int floor."""

    def test_a_measured_integer_is_measured(self):
        assert _ledger.read_token_column(4000) == (4000, _ledger.COLUMN_MEASURED)

    def test_a_measured_zero_is_measured_not_unmeasured(self):
        """The control the whole contract turns on: ``0`` is a MEASUREMENT."""
        assert _ledger.read_token_column(0) == (0, _ledger.COLUMN_MEASURED)

    def test_an_all_digit_string_still_parses(self):
        """The int-parsing floor — every historical all-numeric row reads as before."""
        assert _ledger.read_token_column('12000') == (12000, _ledger.COLUMN_MEASURED)

    def test_the_writer_token_is_unmeasured(self):
        assert _ledger.read_token_column(_ledger.UNMEASURED_COLUMN_TOKEN) == (
            0,
            _ledger.COLUMN_UNMEASURED,
        )

    def test_an_absent_column_is_unrecognised_not_a_measured_zero(self):
        assert _ledger.read_token_column(None) == (0, _ledger.COLUMN_UNRECOGNISED)

    def test_junk_is_unrecognised_rather_than_coerced(self):
        assert _ledger.read_token_column('12x') == (0, _ledger.COLUMN_UNRECOGNISED)


class TestNormalisedRowsCarryTheState:
    """The reader's OWN output separates the two zero-shaped rows."""

    def test_a_measured_zero_and_an_unmeasured_column_differ_in_the_reader_output(
        self, plan_context
    ):
        """Both rows read ``total_tokens == 0``; only the state tells them apart.

        Asserting the number alone would pass against the coercing predecessor,
        which is exactly why the state field exists.
        """
        _write_rows(
            plan_context,
            'recon-states',
            [('measured', 0), ('omitted', _ledger.UNMEASURED_COLUMN_TOKEN)],
        )
        rows, reason = _ledger.load_execution_log(plan_context.plan_dir_for('recon-states'))

        assert reason == ''
        assert rows is not None
        by_step = {
            row['step_id']: row for row in _ledger.execution_rows_for_phase(rows, PHASE)
        }
        assert by_step['measured']['total_tokens'] == 0
        assert by_step['omitted']['total_tokens'] == 0
        assert by_step['measured']['total_tokens_state'] == _ledger.COLUMN_MEASURED
        assert by_step['omitted']['total_tokens_state'] == _ledger.COLUMN_UNMEASURED


class TestFindingsPublishTheState:
    """An unpaired-row finding says whether its token figure was measured."""

    def test_an_unmeasured_row_finding_is_labelled_unmeasured(self, plan_context):
        plan_id = 'recon-finding-unmeasured'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_rows(plan_context, plan_id, [('push', _ledger.UNMEASURED_COLUMN_TOKEN)])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        orphans = _findings_of(result, 'row_absent_from_boundary_ledger')
        assert len(orphans) == 1
        assert orphans[0]['total_tokens'] == 0
        assert orphans[0]['total_tokens_state'] == _ledger.COLUMN_UNMEASURED

    def test_a_measured_zero_row_finding_is_labelled_measured(self, plan_context):
        """The matched negative control for the assertion above."""
        plan_id = 'recon-finding-measured'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_rows(plan_context, plan_id, [('push', 0)])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        orphans = _findings_of(result, 'row_absent_from_boundary_ledger')
        assert len(orphans) == 1
        assert orphans[0]['total_tokens'] == 0
        assert orphans[0]['total_tokens_state'] == _ledger.COLUMN_MEASURED


def _write_boundary_rows(plan_context, plan_id: str, cells: list[object]) -> None:
    """Write a dispatch-boundary file whose ``total_tokens`` column is ``cells[i]``.

    The cell is written VERBATIM. The production writer
    (``cmd_record_dispatch_boundary``) still defaults its legacy five columns to
    ``0``, so it cannot itself emit an unmeasured cell there — which is exactly
    why the READER must be pinned directly: an archived file, a hand-edited one,
    or a later writer change would otherwise arrive at a reader that silently
    coerces the token to a measured zero, and no test would notice.

    The header is the same three lines the writer emits, so the reader's own
    header-skip is exercised rather than bypassed.
    """
    path = plan_context.plan_dir_for(plan_id) / 'work' / f'metrics-dispatch-boundaries-{PHASE}.toon'
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f'plan_id: {plan_id}\n'
        f'phase: {PHASE}\n'
        'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms,'
        'input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}:\n'
    )
    body = ''.join(
        f'2026-01-01T10:0{index}:00+00:00,step_complete,{cell},0,0,'
        f'{_ledger.UNMEASURED_COLUMN_TOKEN},{_ledger.UNMEASURED_COLUMN_TOKEN},'
        f'{_ledger.UNMEASURED_COLUMN_TOKEN},{_ledger.UNMEASURED_COLUMN_TOKEN}\n'
        for index, cell in enumerate(cells)
    )
    path.write_text(header + body, encoding='utf-8')


class TestBoundaryRowsCarryTheStateToo:
    """The OTHER ledger's reader reads the same three states, not an ``_as_int``.

    ``load_boundary_rows`` ran its token cell through ``_as_int``, which returns
    ``0`` for this module's OWN ``unmeasured`` token — so an omitted boundary
    measurement re-entered the reconciliation looking measured, at the one reader
    the three-state contract had not reached.
    """

    def test_a_measured_boundary_cell_is_measured(self, plan_context):
        """The control — the state must not read ``unmeasured`` for everything."""
        _write_boundary_rows(plan_context, 'recon-bnd-measured', [90000])
        path = (
            plan_context.plan_dir_for('recon-bnd-measured')
            / 'work'
            / f'metrics-dispatch-boundaries-{PHASE}.toon'
        )

        rows = _ledger.load_boundary_rows(path)

        assert [row['total_tokens'] for row in rows] == [90000]
        assert [row['total_tokens_state'] for row in rows] == [_ledger.COLUMN_MEASURED]

    def test_a_measured_zero_boundary_cell_is_still_measured(self, plan_context):
        """⛔ The distinction the contract turns on, at this reader."""
        _write_boundary_rows(plan_context, 'recon-bnd-zero', [0])
        path = (
            plan_context.plan_dir_for('recon-bnd-zero')
            / 'work'
            / f'metrics-dispatch-boundaries-{PHASE}.toon'
        )

        rows = _ledger.load_boundary_rows(path)

        assert rows[0]['total_tokens_state'] == _ledger.COLUMN_MEASURED

    def test_the_writer_token_is_not_coerced_to_a_measured_zero(self, plan_context):
        _write_boundary_rows(
            plan_context, 'recon-bnd-unmeasured', [_ledger.UNMEASURED_COLUMN_TOKEN]
        )
        path = (
            plan_context.plan_dir_for('recon-bnd-unmeasured')
            / 'work'
            / f'metrics-dispatch-boundaries-{PHASE}.toon'
        )

        rows = _ledger.load_boundary_rows(path)

        assert rows[0]['total_tokens'] == 0
        assert rows[0]['total_tokens_state'] == _ledger.COLUMN_UNMEASURED

    def test_an_unreadable_boundary_cell_is_unrecognised(self, plan_context):
        _write_boundary_rows(plan_context, 'recon-bnd-junk', ['12x'])
        path = (
            plan_context.plan_dir_for('recon-bnd-junk')
            / 'work'
            / f'metrics-dispatch-boundaries-{PHASE}.toon'
        )

        rows = _ledger.load_boundary_rows(path)

        assert rows[0]['total_tokens_state'] == _ledger.COLUMN_UNRECOGNISED


class TestTheAggregateStateIsDerivedNotStamped:
    """A sum is only as readable as its least-readable term."""

    def test_an_all_measured_population_aggregates_measured(self):
        """The control — deriving must not report every aggregate unmeasured."""
        rows = [
            {'total_tokens_state': _ledger.COLUMN_MEASURED},
            {'total_tokens_state': _ledger.COLUMN_MEASURED},
        ]

        assert _ledger.aggregate_token_state(rows) == _ledger.COLUMN_MEASURED

    def test_one_unmeasured_row_makes_the_sum_a_floor(self):
        rows = [
            {'total_tokens_state': _ledger.COLUMN_MEASURED},
            {'total_tokens_state': _ledger.COLUMN_UNMEASURED},
        ]

        assert _ledger.aggregate_token_state(rows) == _ledger.COLUMN_UNMEASURED

    def test_an_unrecognised_row_outranks_an_unmeasured_one(self):
        rows = [
            {'total_tokens_state': _ledger.COLUMN_UNMEASURED},
            {'total_tokens_state': _ledger.COLUMN_UNRECOGNISED},
        ]

        assert _ledger.aggregate_token_state(rows) == _ledger.COLUMN_UNRECOGNISED

    def test_an_empty_population_is_not_measured(self):
        """⛔ Over zero rows 'every row was measured' is VACUOUSLY true.

        Stamping the aggregate ``measured`` there publishes a fabricated zero as
        a measurement — the vacuous-guard shape reconstructed at the aggregate.
        """
        assert _ledger.aggregate_token_state([]) == _ledger.COLUMN_UNMEASURED

    def test_the_state_counts_partition_the_population(self):
        rows = [
            {'total_tokens_state': _ledger.COLUMN_MEASURED},
            {'total_tokens_state': _ledger.COLUMN_UNMEASURED},
            {'total_tokens_state': _ledger.COLUMN_UNRECOGNISED},
            {},  # a row carrying no state at all is counted, never dropped
        ]

        counts = _ledger.summarize_token_states(rows)

        assert sum(counts.values()) == len(rows)
        assert counts[_ledger.COLUMN_UNRECOGNISED] == 2


class TestBoundaryDerivedFindingsPublishTheState:
    """Both boundary-derived findings read the state instead of stamping it."""

    def test_an_orphan_boundary_finding_reports_its_own_state(self, plan_context):
        plan_id = 'recon-bnd-orphan-unmeasured'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_boundary_rows(plan_context, plan_id, [_ledger.UNMEASURED_COLUMN_TOKEN])
        _write_rows(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        orphans = _findings_of(result, 'row_absent_from_execution_log')
        assert len(orphans) == 1
        assert orphans[0]['total_tokens'] == 0
        assert orphans[0]['total_tokens_state'] == _ledger.COLUMN_UNMEASURED

    def test_a_measured_orphan_boundary_finding_is_still_labelled_measured(self, plan_context):
        """The matched control — the hard-stamped verdict was RIGHT for this row."""
        plan_id = 'recon-bnd-orphan-measured'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_boundary_rows(plan_context, plan_id, [90000])
        _write_rows(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        orphans = _findings_of(result, 'row_absent_from_execution_log')
        assert orphans[0]['total_tokens'] == 90000
        assert orphans[0]['total_tokens_state'] == _ledger.COLUMN_MEASURED

    def test_a_never_closed_aggregate_over_an_unmeasured_row_is_a_floor(self, plan_context):
        plan_id = 'recon-bnd-unclosed-floor'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_boundary_rows(plan_context, plan_id, [4000, _ledger.UNMEASURED_COLUMN_TOKEN])
        _write_rows(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        unclosed = _findings_of(result, 'boundary_never_closed')
        assert len(unclosed) == 1
        assert unclosed[0]['total_tokens'] == 4000
        assert unclosed[0]['total_tokens_state'] == _ledger.COLUMN_UNMEASURED

    def test_a_never_closed_aggregate_over_measured_rows_stays_measured(self, plan_context):
        """The control — the aggregate must not read ``unmeasured`` unconditionally."""
        plan_id = 'recon-bnd-unclosed-measured'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_boundary_rows(plan_context, plan_id, [4000, 6000])
        _write_rows(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        unclosed = _findings_of(result, 'boundary_never_closed')
        assert unclosed[0]['total_tokens'] == 10000
        assert unclosed[0]['total_tokens_state'] == _ledger.COLUMN_MEASURED

    def test_the_never_closed_finding_publishes_its_population_coverage(self, plan_context):
        """The size of the gap, not merely its existence."""
        plan_id = 'recon-bnd-unclosed-coverage'
        cmd_start_phase(ns_start_phase(plan_id, PHASE))
        _write_boundary_rows(
            plan_context, plan_id, [4000, _ledger.UNMEASURED_COLUMN_TOKEN, '12x']
        )
        _write_rows(plan_context, plan_id, [])

        result = cmd_reconcile_ledgers(_ns_reconcile(plan_id))

        unclosed = _findings_of(result, 'boundary_never_closed')[0]
        assert unclosed['total_tokens_rows_in_population'] == 3
        assert unclosed['total_tokens_rows_measured'] == 1
        assert unclosed['total_tokens_rows_unmeasured'] == 1
        assert unclosed['total_tokens_rows_unrecognised'] == 1


def test_reconciliation_unmeasured_token_matches_writer():
    """The mirrored literal agrees with the manifest writer's own definition.

    This module runs in a different process from ``manage-execution-manifest`` and
    cannot import its private module, so the token is a hand-mirror — the same
    cross-skill shape ``EXECUTION_LOG_PHASES`` already uses. Without this check the
    two could drift into different literals, at which point every unmeasured
    column would silently read as unrecognised here.

    The in-skill sibling is checked in the same assertion pair: ``manage-metrics``
    defines the token for its OWN dispatch-boundary row, and this module keeps a
    separate copy because importing back into the entry script would close an
    import cycle. Three definitions, one literal.
    """
    core = load_script_module(
        'plan-marshall',
        'manage-execution-manifest',
        '_manifest_core.py',
        module_name='_mem_core_recon_token_drift',
    )

    assert _ledger.UNMEASURED_COLUMN_TOKEN == core.UNMEASURED_COLUMN_TOKEN
    assert _ledger.UNMEASURED_COLUMN_TOKEN == manage_metrics.UNMEASURED_COLUMN_TOKEN
