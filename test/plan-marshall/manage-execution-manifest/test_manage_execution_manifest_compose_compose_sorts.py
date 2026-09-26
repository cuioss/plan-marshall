# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# Ascending frontmatter-order emission (archive-order barrier fix)
#
# cmd_compose never re-sorted the marshal.json ``phase_6.steps`` map by
# frontmatter order, so ``manage-config sync-defaults`` back-filling a missing
# default-on step by APPENDING it landed the new step after ``archive-plan``
# (terminus order 1100) regardless of its own order. cmd_compose now sorts the FINAL
# ``phase_6.steps`` by resolved frontmatter order before persistence, so
# ``archive-plan`` sorts last among order-resolvable steps automatically.
# =============================================================================


def test_compose_sorts_phase_6_steps_by_frontmatter_order(plan_context):
    """Regression: a candidate list placing ``archive-plan`` BEFORE a lower-order
    step emits the lower-order step first in the composed manifest.

    Reproduces the live bug: ``finalize-step-preference-emitter`` (order 992) was
    appended AFTER ``archive-plan`` (terminus order 1100) by ``manage-config
    sync-defaults``. cmd_compose now sorts ``phase_6.steps`` by resolved
    frontmatter order, so the preference-emitter is emitted strictly before
    ``archive-plan``, which sorts last among order-resolvable steps.
    """
    # Bug-reproducing candidate order: archive-plan (terminus order 1100) precedes the
    # lower-order preference-emitter (order 992) — exactly the layout
    # sync-defaults produced by appending the back-filled default-on step.
    candidates = [
        'push',
        'create-pr',
        'lessons-capture',
        'archive-plan',  # order 1100 (terminus)
        'finalize-step-preference-emitter',  # order 992 — appended AFTER archive-plan
    ]
    result = cmd_compose(
        _compose_ns(
            plan_id='order-barrier-fix',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=5,
            phase_6_steps=','.join(candidates),
        )
    )
    assert result is not None and result['status'] == 'success'
    manifest = read_manifest('order-barrier-fix')
    assert manifest is not None
    steps = manifest['phase_6']['steps']
    assert 'archive-plan' in steps and 'finalize-step-preference-emitter' in steps
    # The composer sorted by frontmatter order: the low-order step now precedes
    # archive-plan even though the input placed it after.
    assert steps.index('finalize-step-preference-emitter') < steps.index('archive-plan')
    # archive-plan (order 1100, the highest/terminus) sorts last among order-resolvable steps.
    assert steps[-1] == 'archive-plan'
