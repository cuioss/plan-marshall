# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _write_marshal_with_ci,
    cmd_compose,
    pytest,
    read_manifest,
)

# =============================================================================
# Compose-time frontmatter-order sort
#
# ``automatic-review`` (frontmatter order 30) must land before every
# plan-mutating step (``archive-plan``, ``record-metrics``, ``branch-cleanup``,
# ``plan-marshall:plan-retrospective``). The ``_sort_steps_by_frontmatter_order``
# choke-point is the SOLE ordering authority (the bot-enforcement placement
# validator was removed): a misordered candidate list is sorted back into
# frontmatter ``order:`` sequence, so ``automatic-review`` lands strictly before
# every plan-mutating anchor and compose succeeds (``status='success'``).
#
# Construction: we pass an explicit ``--phase-6-steps`` candidate list where
# ``automatic-review`` is already present in the wrong position; Row 7 (default)
# preserves the candidate ordering verbatim, so the misplacement reaches the sort
# choke-point, which reorders it ahead of the anchor.
# =============================================================================


class TestAutomatedReviewPlacement:
    """Compose-time frontmatter-order sort places ``automatic-review`` before plan-mutating anchors."""

    @staticmethod
    def _candidates_with_review_after(anchor: str) -> str:
        """Build a phase_6 candidate CSV where ``automatic-review`` follows ``anchor``.

        The candidate list mirrors the canonical ordering for the steps that
        always remain (push, create-pr, lessons-capture) so the manifest
        is otherwise plausible; only the ``automatic-review`` / ``anchor`` pair
        is deliberately misordered. The anchor is inserted before
        ``automatic-review`` so the sort choke-point must reorder it back ahead
        of the parametrized anchor.
        """
        return ','.join(['push', 'create-pr', 'lessons-capture', anchor, 'automatic-review'])

    def test_compose_sorts_automated_review_before_archive_plan(self, plan_context):
        """Misplaced ``automatic-review`` after ``archive-plan`` → sorted before it, compose succeeds."""
        plan_id = 'placement-archive-plan'
        # GitHub provider — the misplacement reaches the sort choke-point, which
        # reorders automatic-review ahead of the anchor.
        _write_marshal_with_ci(plan_context.fixture_dir, provider='github')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=self._candidates_with_review_after('archive-plan'),
            )
        )

        assert result is not None
        # The sort choke-point corrects the misplacement, so compose succeeds.
        assert result['status'] == 'success', f'expected success status, got {result!r}'
        # The persisted manifest sorts ``automatic-review`` strictly before the
        # ``archive-plan`` anchor.
        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automatic-review' in steps
        assert 'archive-plan' in steps
        assert steps.index('automatic-review') < steps.index('archive-plan'), (
            f'automatic-review must sort before archive-plan: {steps!r}'
        )

    @pytest.mark.parametrize(
        'anchor',
        ['record-metrics', 'branch-cleanup', 'plan-marshall:plan-retrospective'],
    )
    def test_compose_sorts_automated_review_before_other_plan_mutating_steps(self, plan_context, anchor: str):
        """Misplaced ``automatic-review`` after each remaining anchor → sorted before it, compose succeeds.

        Parametrized over the three plan-mutating anchors NOT covered by the
        ``archive-plan`` test above. Together these cover the full plan-mutating
        anchor set the sort must place ``automatic-review`` ahead of:
        ``archive-plan``, ``record-metrics``, ``branch-cleanup``,
        ``plan-marshall:plan-retrospective``.
        """
        # Plan IDs must be kebab-case; the colon-prefixed retrospective anchor
        # would otherwise leak a ``:`` into the directory name.
        anchor_slug = anchor.replace(':', '-').replace('plan-marshall-', 'pm-')
        plan_id = f'placement-{anchor_slug}'
        _write_marshal_with_ci(plan_context.fixture_dir, provider='github')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=self._candidates_with_review_after(anchor),
            )
        )

        assert result is not None
        # The sort choke-point corrects the misplacement, so compose succeeds
        # for every anchor.
        assert result['status'] == 'success', f'expected success status for anchor={anchor!r}, got {result!r}'
        # The persisted manifest sorts ``automatic-review`` strictly before the
        # parametrized anchor.
        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        assert 'automatic-review' in steps
        assert anchor in steps
        assert steps.index('automatic-review') < steps.index(anchor), (
            f'automatic-review must sort before anchor={anchor!r}: {steps!r}'
        )
