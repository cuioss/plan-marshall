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


def test_orchestrator_tier_routes_to_phase_5_and_drops_per_task(plan_context, monkeypatch):
    """Case (a): a deliverable whose verification resolves to ``orchestrator``
    appends the mapped phase-5 step ID to ``phase_5.verification_steps`` and
    removes the command from the task's verification list."""
    plan_id = 'tier-orchestrator'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify plan-marshall"',
        ],
    )
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(orchestrator_verbs={'verify'}))

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
        )
    )

    assert result is not None and result['status'] == 'success'
    manifest = read_manifest(plan_id)
    assert manifest is not None
    # The routed step ID is the BARE canonical-verify form (no ``default:``
    # prefix) — ``_VERB_TO_PHASE_5_STEP`` maps the ``verify`` verb to
    # ``verify:module-tests`` so the appended ID matches the boundary-normalized
    # phase-5 list and never produces a ``default:``-prefixed stray.
    assert 'verify:module-tests' in manifest['phase_5']['verification_steps']
    assert 'default:verify:module-tests' not in manifest['phase_5']['verification_steps']
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert task['verification']['commands'] == []
    assert 'bash_timeout_seconds' not in task['verification']
