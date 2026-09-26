# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _LARGE_FOOTPRINT,
    _SECURITY_STEP,
    _capture_decision_log,
    _compose,
    _composed_steps,
    _restore_patched_seams,
    _stub_footprint,
)

# =============================================================================
# (b) An absent / unusable change-shape signal fails toward inclusion
# =============================================================================


def test_stale_declared_surface_fails_toward_inclusion(plan_context):
    """A stale (empty) DECLARED surface keeps the sweep when the worktree has one.

    ``affected_files_count`` comes from ``references.json::affected_files``, which
    is legitimately empty early in a plan's life while the worktree already carries
    the change. The gate reads both surfaces, so either one alone keeps the step —
    the fail-toward-inclusion contract on the second leg.

    Pre-fix failure (observed against pre-fix HEAD):
    ``KeyError: 'security_class_omitted'``, reached first. Behind it, the old gate
    never consulted the live footprint at all, so ``affected_files_count == 0`` was
    an independent drop leg and the membership assertion would have failed too.
    """
    plan_id = 'secclass-stale-declared-surface'
    _stub_footprint(_LARGE_FOOTPRINT)
    _capture_decision_log()

    result = _compose(plan_id, change_type='feature', affected_files_count=0)

    assert result['security_class_omitted'] == []
    assert _SECURITY_STEP in _composed_steps(plan_id)
