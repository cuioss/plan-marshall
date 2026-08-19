#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-ledger reconciliation: a disagreement becomes a finding, not a silent choice."""


from datetime import timedelta

import pytest
from _ledger_reconciliation_fixtures import (
    _boundary_timestamps,
    _findings_of,
    _ledger,
    _ns_reconcile,
    _parse_stamp,
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
