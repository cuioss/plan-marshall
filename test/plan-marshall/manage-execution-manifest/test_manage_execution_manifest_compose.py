# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_manage_execution_manifest_compose.py: default."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# Decision Matrix Tests — table-driven cases (one per row of the matrix +
# the requested 8th case for early_terminate analysis-with-empty-files)
# =============================================================================





# =============================================================================
# Default phase-6 ordering — finalize-step-simplify precedes the push barrier
#
# The dispatcher's commit instrumentation commits each ``mutates_source: true``
# step's output before advancing, so the correct ordering (simplify before the
# pure ``push`` barrier) falls out of plain ``order:`` values with no special
# placement invariant. This test pins the default ordering so a regression that
# swaps the two in ``DEFAULT_PHASE_6_STEPS`` is caught.
# =============================================================================
def test_default_code_shaped_feature_runs_full_phases(plan_context):
    """Row 7 — default: feature plan gets the full Phase 5 and Phase 6 sets."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-default',
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=12,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['rule_fired'] == 'default'
    assert result['phase_5']['early_terminate'] is False
    assert result['phase_5']['verification_steps_count'] == 2  # quality-gate + module-tests
    assert result['phase_6']['steps_count'] == len(DEFAULT_PHASE_6_STEPS)



class TestDefaultPhase6Ordering:
    """``finalize-step-simplify`` composes at an index earlier than ``push``."""

    def test_default_compose_places_simplify_before_push(self, plan_context):
        # A default code-shaped feature compose (change_type=feature, files>0, so
        # simplify_inactive keeps the step) MUST emit ``finalize-step-simplify`` at
        # an earlier index than the ``push`` barrier.
        result = cmd_compose(_compose_ns(plan_id='default-order-simplify-before-push'))

        assert result is not None
        assert result['status'] == 'success', f'expected success, got {result!r}'

        manifest = read_manifest('default-order-simplify-before-push')
        assert manifest is not None
        steps = manifest['phase_6']['steps']
        # Both steps survive the default feature compose.
        assert 'push' in steps
        assert 'finalize-step-simplify' in steps
        # The ordering invariant: simplify precedes the push barrier.
        assert steps.index('finalize-step-simplify') < steps.index('push')
