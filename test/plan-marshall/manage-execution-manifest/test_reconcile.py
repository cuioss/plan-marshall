# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_reconcile.py: stale."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_reconcile_fixtures import (
    GHOST,
    REAL_A,
    REAL_B,
    _emitted_for,
    _reconcile_ns,
    _seed_manifest,
    _write_marshal,
    cmd_reconcile,
    load_script_module,
    read_manifest,
)

# =============================================================================
# The drop direction — a frozen step live config has also dropped
# =============================================================================


class TestStaleStepIsDroppedNotFailed:
    def test_frozen_step_absent_from_live_config_is_reported_stale(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-stale', [REAL_A, GHOST, REAL_B], candidate_steps=[REAL_A, GHOST, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-stale'))
        assert result is not None
        assert result['status'] == 'success', (
            f'a frozen step that live config has ALSO dropped must reconcile, not fail: {result}'
        )
        assert result['stale'] == [GHOST]
        assert result['broken'] == []

    def test_apply_drops_the_stale_step_from_the_manifest(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-apply', [REAL_A, GHOST, REAL_B], candidate_steps=[REAL_A, GHOST, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-apply', apply=True))
        assert result['status'] == 'success'
        assert result['applied'] is True

        persisted = read_manifest('rec-apply')
        assert GHOST not in persisted['phase_6']['steps']
        assert REAL_A in persisted['phase_6']['steps']
        assert REAL_B in persisted['phase_6']['steps']

    def test_apply_prunes_the_dropped_step_params_entry(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-params', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-params', apply=True))

        persisted = read_manifest('rec-params')
        assert GHOST not in persisted['phase_6']['step_params'], 'a dropped step must not keep a params snapshot behind'

    def test_dry_run_does_not_write(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-dry', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        result = cmd_reconcile(_reconcile_ns('rec-dry'))
        assert result['applied'] is False
        assert GHOST in read_manifest('rec-dry')['phase_6']['steps'], (
            'reconcile without --apply is a report, not a mutation'
        )

    def test_dry_run_emits_no_decision_log_line(self, plan_context):
        """A dry run must not write an audit record for a change it did not make.

        The decision log is a record of subtractions that HAPPENED. Emitting
        from a dry run both mutates a file the verb promises not to touch and
        asserts a drop that never occurred — a false audit trail, which is
        worse than none.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-dry-log', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-dry-log'))
        assert _emitted_for('rec-dry-log') == [], (
            f'a dry run emitted a decision-log line: {_emitted_for("rec-dry-log")}'
        )

    def test_apply_emits_one_decision_log_line_per_dropped_step(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-apply-log', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-apply-log', apply=True))
        messages = _emitted_for('rec-apply-log')
        assert len(messages) == 1
        assert 'frozen_manifest_stale' in messages[0]
        assert GHOST in messages[0]

    def test_the_emitted_line_is_readable_by_the_retrospective_reader(self, plan_context):
        """The writer→reader contract, exercised end to end against real bytes.

        The retrospective's routing-decisions aspect reads this line back to
        establish WHY a step left ``phase_6.steps``; a step whose removal it cannot
        attribute falls through to predicate re-evaluation and is reported as a
        mis-prune that never happened.

        The substring assertions above pin the gate name and the step id and
        NOTHING about the shape, which is exactly how this emission drifted out of
        the reader's grammar — no ``[STATUS]`` tag, the step id in backticks —
        while its own test stayed green. This one runs the reader's real resolver
        over the writer's real output, so neither side can move alone.
        """
        crd = load_script_module(
            'plan-marshall',
            'plan-retrospective',
            'check-routing-decisions.py',
            'crd_reconcile_emission_shape',
        )
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        _seed_manifest('rec-reader-shape', [REAL_A, GHOST], candidate_steps=[REAL_A, GHOST])

        cmd_reconcile(_reconcile_ns('rec-reader-shape', apply=True))

        causes = crd.resolve_removal_causes(_emitted_for('rec-reader-shape'))
        assert causes == {GHOST: 'frozen_manifest_stale'}

    def test_the_backfill_line_is_not_read_as_a_removal(self, plan_context):
        """An addition must never resolve as a cause for its own step's removal.

        The backfill record deliberately keeps its own shape rather than borrowing
        the subtraction formatter: rendered through it, a step this verb ADDED
        would be published as one it dropped, and the reader would resolve the
        cause in the wrong direction.
        """
        crd = load_script_module(
            'plan-marshall',
            'plan-retrospective',
            'check-routing-decisions.py',
            'crd_reconcile_backfill_shape',
        )
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-reader-backfill', [REAL_A], candidate_steps=[REAL_A])

        cmd_reconcile(_reconcile_ns('rec-reader-backfill', apply=True))

        messages = _emitted_for('rec-reader-backfill')
        assert any('frozen_manifest_backfill' in m for m in messages), messages
        assert crd.resolve_removal_causes(messages) == {}
