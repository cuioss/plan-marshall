# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _make_tier_stub,
    _mem,
    _read_task,
    _write_task,
    cmd_compose,
    read_manifest,
)


def test_mixed_tier_routes_to_both_locations(plan_context, monkeypatch):
    """Case (c): a task with two verification commands — one ``orchestrator``,
    one ``per_task`` — routes to both locations simultaneously."""
    plan_id = 'tier-mixed'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify plan-marshall"',
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "quality-gate plan-marshall"',
        ],
    )
    monkeypatch.setattr(
        _mem,
        '_resolve_command_tier',
        _make_tier_stub(orchestrator_verbs={'verify'}, per_task_timeout=360),
    )

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=2))

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    # The routed step ID is BARE — see test_orchestrator_tier_routes_to_phase_5.
    assert 'verify:module-tests' in manifest['phase_5']['verification_steps']
    assert 'default:verify:module-tests' not in manifest['phase_5']['verification_steps']
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    # Orchestrator command pruned; per_task command retained.
    assert len(task['verification']['commands']) == 1
    assert 'quality-gate' in task['verification']['commands'][0]
    assert task['verification']['bash_timeout_seconds'] == 360
