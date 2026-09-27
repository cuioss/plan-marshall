# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _read_task,
    _write_task,
    cmd_compose,
)


def test_non_build_command_passes_through_unchanged(plan_context, monkeypatch):
    """Case (d): a non-build verification command (raw shell ``grep``)
    receives no ``execution_tier`` field from the resolver, so the composer
    leaves the command in place and adds no annotation."""
    plan_id = 'tier-non-build'
    raw = 'grep -nE "TODO" CLAUDE.md'
    _write_task(plan_context.plans_dir, plan_id, 1, [raw])
    # ``_resolve_command_tier`` already returns ``None`` for non-build
    # commands via the existing parse short-circuit — no monkeypatch needed.

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=1))

    assert result is not None and result['status'] == 'success'
    task = _read_task(plan_context.plans_dir, plan_id, 1)
    assert task['verification']['commands'] == [raw]
    assert 'bash_timeout_seconds' not in task['verification']
