# SPDX-License-Identifier: FSL-1.1-ALv2

import json

from _manage_execution_manifest_reconcile_fixtures import (
    GHOST,
    REAL_A,
    REAL_B,
    _emitted_for,
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


class TestBackfillHonoursCommitPushDisabled:
    """A push-only step added after compose never reaches a local-only plan."""

    def test_push_only_candidates_are_refused_on_a_local_only_plan(self, plan_context):
        """The live value is consulted, exactly as compose's parameter is."""
        _write_marshal(
            plan_context.fixture_dir,
            [REAL_B, 'push', 'pre-push-quality-gate'],
            commit_and_push=False,
        )
        _seed_manifest('rec-local-only', [REAL_B], candidate_steps=[REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-local-only', apply=True))

        assert result['backfill'] == []
        assert result['backfill_refused'] == ['push', 'pre-push-quality-gate'], result
        assert result['commit_and_push'] is False, result
        steps = read_manifest('rec-local-only')['phase_6']['steps']
        assert 'push' not in steps and 'pre-push-quality-gate' not in steps

    def test_the_same_candidates_are_backfilled_when_pushing(self, plan_context):
        """Matched control: only the value differs from the refusal above."""
        _write_marshal(
            plan_context.fixture_dir,
            [REAL_B, 'push', 'pre-push-quality-gate'],
            commit_and_push=True,
        )
        _seed_manifest('rec-with-push', [REAL_B], candidate_steps=[REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-with-push', apply=True))

        assert result['backfill'] == ['push', 'pre-push-quality-gate'], result
        assert result['backfill_refused'] == []
        assert 'push' in read_manifest('rec-with-push')['phase_6']['steps']

    def test_a_push_only_step_already_composed_is_not_reported_as_refused(self, plan_context):
        """The refusal names candidates this run WOULD have backfilled, and no others."""
        _write_marshal(plan_context.fixture_dir, [REAL_B, 'push'], commit_and_push=False)
        _seed_manifest('rec-local-composed', [REAL_B], candidate_steps=[REAL_B, 'push'])

        result = cmd_reconcile(_reconcile_ns('rec-local-composed', apply=True))

        assert result['backfill'] == []
        assert result['backfill_refused'] == [], result

    def test_a_refused_backfill_is_logged_even_when_nothing_changes(self, plan_context):
        """The refusal audit line does not depend on another change being applied."""
        _write_marshal(plan_context.fixture_dir, [REAL_B, 'push'], commit_and_push=False)
        _seed_manifest('rec-local-logged', [REAL_B], candidate_steps=[REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-local-logged', apply=True))

        assert result['reconciled'] is False, result
        messages = _emitted_for('rec-local-logged')
        assert any('refused to backfill push' in message for message in messages), messages

    def test_a_malformed_phase_block_applies_the_floor(self, plan_context):
        """A present phase block that is not an object is a failed read too.

        The value-shaped defect is pinned above; its PARENT can be malformed in
        exactly the same way, and reading that as the default would backfill
        push-only steps into a plan whose configuration nobody can read.
        """
        (plan_context.fixture_dir / 'marshal.json').write_text(
            json.dumps(
                {
                    'plan': {
                        'phase-6-finalize': {'steps': {REAL_B: {}, 'push': {}}},
                        'phase-5-execute': 'not-an-object',
                    },
                    'build': {},
                }
            ),
            encoding='utf-8',
        )
        _seed_manifest('rec-malformed-block', [REAL_B], candidate_steps=[REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-malformed-block', apply=True))

        assert result['backfill'] == [], result
        assert result['backfill_refused'] == ['push'], result
        assert 'not-an-object' in result['backfill_refused_reason'], result
        assert 'push' not in read_manifest('rec-malformed-block')['phase_6']['steps']

    def test_a_non_object_plan_block_is_a_failed_read(self, plan_context):
        """The `plan` block itself can be malformed; that is not "no commit_and_push".

        The `phase-5-execute` shape is pinned above. The parent is the same kind of
        failed read, and its answer is observable in the result's own
        `commit_and_push` field: a default there would report a readable configuration.
        """
        (plan_context.fixture_dir / 'marshal.json').write_text(
            json.dumps({'plan': 'not-an-object', 'build': {}}), encoding='utf-8'
        )
        _seed_manifest('rec-malformed-plan', [REAL_B], candidate_steps=[REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-malformed-plan', apply=True))

        assert result['commit_and_push'] is None, result

    def test_a_malformed_commit_and_push_applies_the_floor(self, plan_context):
        """A present value that is not bool-shaped is a FAILED read, not the default.

        ``_read_live_commit_and_push`` once answered ``True`` for it, so reconcile
        backfilled push-only steps into a plan whose configuration nobody could read —
        the direction the local-only floor exists to block. The refusal names the
        value it could not read.
        """
        _write_marshal(plan_context.fixture_dir, [REAL_B, 'push'], commit_and_push='sometimes')
        _seed_manifest('rec-malformed', [REAL_B], candidate_steps=[REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-malformed', apply=True))

        assert result['backfill'] == [], result
        assert result['backfill_refused'] == ['push'], result
        assert 'sometimes' in result['backfill_refused_reason'], result
        assert 'push' not in read_manifest('rec-malformed')['phase_6']['steps']
