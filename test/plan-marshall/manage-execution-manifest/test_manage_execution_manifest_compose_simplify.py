# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    _mem,
    cmd_compose,
    pytest,
    read_manifest,
)

# =============================================================================
# Pre-Filter: simplify_inactive (finalize-step-simplify gate)
#
# finalize-step-simplify is a candidate by default (it sits in
# DEFAULT_PHASE_6_STEPS). The simplify_inactive pre-filter DROPS it unless
# BOTH change_type ∈ {feature, bug_fix, tech_debt, enhancement}
# AND affected_files_count > 0.
# These tests enforce the merged plan's never-checked criterion: a
# code-touching plan composes the step into phase_6.steps; a docs-only /
# zero-affected-files plan does NOT; and the drop-only decision-log line fires
# only on the dropped branch.
#
# See standards/decision-rules.md § Pre-Filter: simplify_inactive.
# =============================================================================


@pytest.mark.parametrize(
    'change_type,affected_files_count,expect_present,expect_omitted',
    [
        # Gate passes: all four code-touching change types with files > 0.
        ('feature', 5, True, False),
        ('bug_fix', 1, True, False),
        ('tech_debt', 3, True, False),
        ('enhancement', 5, True, False),
        # Gate fails on change_type: not a code-touching type.
        ('analysis', 5, False, True),
        ('verification', 5, False, True),
        # Gate fails on affected_files_count == 0 (even for a code-touching type).
        ('feature', 0, False, True),
        ('bug_fix', 0, False, True),
        ('enhancement', 0, False, True),
    ],
)
def test_simplify_inactive_gate(plan_context, change_type, affected_files_count, expect_present, expect_omitted):
    """finalize-step-simplify lands only when change_type ∈ {feature, bug_fix, tech_debt, enhancement} AND files > 0."""
    slug = f'{change_type}-{affected_files_count}'.replace('_', '-')
    plan_id = f'matrix-simplify-{slug}'
    # Use a non-surgical, code-shaped scope so the surgical Row 5 path
    # doesn't intersect-narrow phase_6.steps and confuse the assertion.
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type=change_type,
            scope_estimate='multi_module',
            affected_files_count=affected_files_count,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['simplify_omitted'] is expect_omitted
    manifest = read_manifest(plan_id)
    assert manifest is not None
    if expect_present:
        assert 'finalize-step-simplify' in manifest['phase_6']['steps']
    else:
        assert 'finalize-step-simplify' not in manifest['phase_6']['steps']


def test_simplify_inactive_noop_when_step_absent_from_candidates(plan_context):
    """When finalize-step-simplify is not a candidate, the pre-filter is a no-op even on a failing gate."""
    candidates_without_simplify = [s for s in DEFAULT_PHASE_6_STEPS if s != 'finalize-step-simplify']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-simplify-absent',
            change_type='analysis',  # gate would fail
            scope_estimate='multi_module',
            affected_files_count=0,  # gate would fail
            phase_6_steps=','.join(candidates_without_simplify),
        )
    )
    assert result is not None and result['status'] == 'success'
    # No-op: the step was never present, so the pre-filter did not "fire".
    assert result['simplify_omitted'] is False
    manifest = read_manifest('matrix-simplify-absent')
    assert manifest is not None
    assert 'finalize-step-simplify' not in manifest['phase_6']['steps']


def test_simplify_inactive_emits_decision_log_only_on_drop(plan_context):
    """The drop-only decision-log line fires exactly once on the dropped branch and not on the kept branch."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        # Dropped branch: analysis change_type fails the gate.
        cmd_compose(
            _compose_ns(
                plan_id='matrix-simplify-drop',
                change_type='analysis',
                scope_estimate='multi_module',
                affected_files_count=3,
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [(pid, msg) for pid, msg in captured if 'finalize-step-simplify omitted' in msg]
    assert len(drop_entries) == 1, f'expected one simplify omission entry, got {captured!r}'
    pid, msg = drop_entries[0]
    assert pid == 'matrix-simplify-drop'
    assert msg == (
        '(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — '
        'change_type=analysis affected_files_count=3'
    )


def test_simplify_inactive_no_decision_log_on_kept_branch(plan_context):
    """No simplify-omission log fires when the gate passes (step retained)."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        cmd_compose(
            _compose_ns(
                plan_id='matrix-simplify-kept',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
            )
        )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [(pid, msg) for pid, msg in captured if 'finalize-step-simplify omitted' in msg]
    assert drop_entries == []
