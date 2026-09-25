# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    _mem,
    _pinned_footprint,
    cmd_compose,
    pytest,
    read_manifest,
)


@pytest.mark.parametrize(
    'change_type,affected_files_count,footprint,expect_prefilter_drop,expect_in_manifest',
    [
        # Code-touching change types with a declared surface → kept (unchanged).
        ('feature', 5, [], False, True),
        ('bug_fix', 1, [], False, True),
        ('tech_debt', 3, [], False, True),
        ('enhancement', 5, [], False, True),
        # ⭐ The regression this gate exists to close: the two change types the old
        # gate excluded now KEEP the step, because a declared surface exists.
        ('analysis', 5, [], False, True),
        ('verification', 5, [], False, True),
        # Zero declared files but a live footprint → the pre-filter still keeps it
        # (fail toward inclusion).
        ('feature', 0, ['src/a.py'], False, True),
        # Same for an excluded change type — but here the six-row matrix separately
        # narrows phase_6 for a zero-files verification plan, so the step is absent
        # from the manifest for a reason that is NOT this pre-filter. The
        # security_class_omitted assertion is what pins the pre-filter's behaviour.
        ('verification', 0, ['src/a.py'], False, False),
        # Only the genuine no-change-surface case drops it.
        ('feature', 0, [], True, False),
        ('verification', 0, [], True, False),
        ('analysis', 0, [], True, False),
    ],
)
def test_security_class_inactive_gate(
    plan_context,
    change_type,
    affected_files_count,
    footprint,
    expect_prefilter_drop,
    expect_in_manifest,
):
    """A security-class step drops only when there is no declared AND no live change surface."""
    slug = f'{change_type}-{affected_files_count}-{len(footprint)}'.replace('_', '-')
    plan_id = f'matrix-secaudit-{slug}'
    # Use a non-surgical, code-shaped scope so the surgical Row 5 path
    # doesn't intersect-narrow phase_6.steps and confuse the assertion.
    with _pinned_footprint(footprint):
        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type=change_type,
                scope_estimate='multi_module',
                affected_files_count=affected_files_count,
            )
        )
    assert result is not None and result['status'] == 'success'
    dropped_steps = [record['step'] for record in result['security_class_omitted']]
    expected_dropped = ['finalize-step-security-audit'] if expect_prefilter_drop else []
    assert dropped_steps == expected_dropped
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert ('finalize-step-security-audit' in manifest['phase_6']['steps']) is expect_in_manifest



def test_security_class_inactive_noop_when_step_absent_from_candidates(plan_context):
    """When no security-class step is a candidate, the pre-filter is a no-op even on a failing gate."""
    candidates_without_secaudit = [s for s in DEFAULT_PHASE_6_STEPS if s != 'finalize-step-security-audit']
    with _pinned_footprint([]):
        result = cmd_compose(
            _compose_ns(
                plan_id='matrix-secaudit-absent',
                change_type='analysis',
                scope_estimate='multi_module',
                affected_files_count=0,  # gate would fail
                phase_6_steps=','.join(candidates_without_secaudit),
            )
        )
    assert result is not None and result['status'] == 'success'
    # No-op: no population member was present, so nothing was dropped.
    assert result['security_class_omitted'] == []
    manifest = read_manifest('matrix-secaudit-absent')
    assert manifest is not None
    assert 'finalize-step-security-audit' not in manifest['phase_6']['steps']



def test_security_class_inactive_emits_status_decision_log_only_on_drop(plan_context):
    """The per-drop [STATUS] decision-log line fires exactly once on the dropped branch."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        # Dropped branch: no declared files AND no live footprint.
        with _pinned_footprint([]):
            cmd_compose(
                _compose_ns(
                    plan_id='matrix-secaudit-drop',
                    change_type='analysis',
                    scope_estimate='multi_module',
                    affected_files_count=0,
                )
            )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [(pid, msg) for pid, msg in captured if 'security_class_inactive' in msg]
    assert len(drop_entries) == 1, f'expected one security-class omission entry, got {captured!r}'
    pid, msg = drop_entries[0]
    assert pid == 'matrix-secaudit-drop'
    assert msg == (
        '(plan-marshall:manage-execution-manifest:compose) [STATUS] security_class_inactive — '
        'dropped finalize-step-security-audit from phase_6.steps: '
        'no declared affected files and empty live footprint'
    )



def test_security_class_inactive_no_decision_log_on_kept_branch(plan_context):
    """No security-class omission log fires when the plan has a change surface."""
    captured: list[tuple[str, str]] = []
    original_emit = _mem._emit_decision_log

    def _capture(plan_id, message):
        captured.append((plan_id, message))

    _mem._emit_decision_log = _capture
    try:
        with _pinned_footprint([]):
            cmd_compose(
                _compose_ns(
                    plan_id='matrix-secaudit-kept',
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                )
            )
    finally:
        _mem._emit_decision_log = original_emit

    drop_entries = [(pid, msg) for pid, msg in captured if 'security_class_inactive' in msg]
    assert drop_entries == []
