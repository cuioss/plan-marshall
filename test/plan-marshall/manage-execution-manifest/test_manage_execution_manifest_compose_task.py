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


def test_task_command_survives_when_compose_fails_unresolvable_step(plan_context, monkeypatch):
    """Regression (8ae9e7): a task's original verification command MUST survive
    on disk when compose fails ``unresolvable_step`` on a routed ``verify:{verb}``.

    An orchestrator-tier command with a NON-canonical verb routes to the
    generalized bare ``verify:{verb}`` step, which the composer's routing pass
    also drops from the task's ``verification.commands``. The trailing verb is
    not in ``_verify_canonicals_universe()``, so the compose-time resolution gate
    (``check_emitted_steps_resolvable``) fails the whole compose with
    ``unresolvable_step`` — AFTER the routing pass ran. Because the task-file
    rewrite is now STAGED and only persisted once the gate passes, the original
    command is still on disk for the retry; the previous unconditional in-loop
    write silently dropped it (a genuine data-loss bug, not just a doc issue).
    """
    plan_id = 'tier-unresolvable-command-survives'
    original_cmd = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
        '--command-args "bogus-canonical plan-marshall"'
    )
    _write_task(plan_context.plans_dir, plan_id, 1, [original_cmd])
    # The non-canonical verb resolves to the orchestrator tier, so routing maps
    # it to the bare ``verify:bogus-canonical`` step and stages dropping the
    # command from the task.
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(orchestrator_verbs={'bogus-canonical'}))

    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='feature',
            scope_estimate='multi_module',
            affected_files_count=3,
        )
    )

    # Compose fails loud on the unresolvable routed step.
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'unresolvable_step'
    assert result['phase'] == 'phase_5'
    assert result['step_id'] == 'verify:bogus-canonical'
    # No manifest is written on the fail-loud path.
    assert read_manifest(plan_id) is None
    # THE REGRESSION ASSERTION: the original verification command is NOT lost —
    # the staged rewrite was never committed because the gate failed.
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert task['verification']['commands'] == [original_cmd]
