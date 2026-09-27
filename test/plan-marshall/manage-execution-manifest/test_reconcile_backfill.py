# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_reconcile_fixtures import (
    GHOST,
    REAL_A,
    REAL_B,
    _reconcile_ns,
    _seed_manifest,
    _write_marshal,
    cmd_reconcile,
    read_manifest,
)

# =============================================================================
# The backfill direction — narrow by construction
# =============================================================================


class TestBackfillIsNarrow:
    def test_candidate_new_since_compose_is_backfilled(self, plan_context):
        """REAL_B entered live config AFTER this manifest was composed."""
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-backfill', [REAL_A], candidate_steps=[REAL_A])

        result = cmd_reconcile(_reconcile_ns('rec-backfill', apply=True))
        assert result['status'] == 'success'
        assert result['backfill'] == [REAL_B]
        assert REAL_B in read_manifest('rec-backfill')['phase_6']['steps']

    def test_matrix_dropped_candidate_is_not_re_added(self, plan_context):
        """The decision matrix saw REAL_B and dropped it — that must stand.

        This is the whole reason ``candidate_steps`` is snapshotted. Without
        it, "in live config but not in the manifest" would re-add every step
        the matrix deliberately subtracted, defeating the composer.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-matrix', [REAL_A], candidate_steps=[REAL_A, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-matrix', apply=True))
        assert result['backfill'] == []
        assert REAL_B not in read_manifest('rec-matrix')['phase_6']['steps'], (
            'a candidate the matrix already considered and dropped must not be resurrected by reconcile'
        )

    def test_absent_candidate_snapshot_reports_indeterminate(self, plan_context):
        """A manifest frozen before ``candidate_steps` existed cannot be diffed.

        Fail closed: report that backfill could not be determined rather than
        guessing a set that would re-add matrix-dropped steps.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-legacy', [REAL_A], candidate_steps=None)

        result = cmd_reconcile(_reconcile_ns('rec-legacy', apply=True))
        assert result['status'] == 'success'
        assert result['backfill_determinable'] is False
        assert result['backfill'] == []
        assert REAL_B not in read_manifest('rec-legacy')['phase_6']['steps']

    def test_drop_still_works_without_a_candidate_snapshot(self, plan_context):
        """The drop direction needs no snapshot — only loadability and live config."""
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-legacy-drop', [REAL_A, GHOST], candidate_steps=None)

        result = cmd_reconcile(_reconcile_ns('rec-legacy-drop', apply=True))
        assert result['stale'] == [GHOST]
        assert GHOST not in read_manifest('rec-legacy-drop')['phase_6']['steps']
