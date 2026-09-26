# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _make_tier_stub,
    _mem,
    _read_task,
    _write_task,
    cmd_compose,
)


def test_per_task_tier_annotates_task_with_bash_timeout_seconds(plan_context, monkeypatch):
    """Case (b): a per_task verification keeps its command and gains a
    ``bash_timeout_seconds`` annotation derived from the resolve TOON."""
    plan_id = 'tier-per-task'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "module-tests plan-marshall"',
        ],
    )
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_tier_stub(per_task_timeout=420))

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=2))

    assert result is not None and result['status'] == 'success'
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert len(task['verification']['commands']) == 1
    assert task['verification']['bash_timeout_seconds'] == 420
