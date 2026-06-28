#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""In-process tests for the manage-tasks.py CLI dispatcher (``main``).

``test_manage_tasks_cli.py`` exercises the dispatcher through a subprocess
(Tier 3) — valuable for the real exit-code contract but invisible to coverage,
since the dispatcher then runs in a child interpreter. These tests call
``main()`` in-process (after setting ``sys.argv``) so coverage lands on
``build_parser()`` and the ``COMMANDS`` dispatch in manage-tasks.py, while still
asserting real behaviour: exit codes, emitted TOON status, and the read/exists
probes.

``main()`` is wrapped by ``@safe_main`` (``sys.exit(main())``), so every
dispatch raises ``SystemExit`` whose ``.code`` is the script's return value.
"""

import sys
from pathlib import Path

import pytest

from conftest import load_script_module

from _helpers import add_basic_task

# In-process dispatcher module (unique name) — coverage attributed to manage-tasks.py.
_mt = load_script_module('plan-marshall', 'manage-tasks', 'manage-tasks.py', 'inproc_manage_tasks_main')


def _run(monkeypatch, capsys, argv):
    """Invoke ``main()`` with ``argv`` and return (exit_code, stdout, stderr)."""
    monkeypatch.setattr(sys, 'argv', ['manage-tasks.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _mt.main()
    captured = capsys.readouterr()
    code = exc.value.code if exc.value.code is not None else 0
    return code, captured.out, captured.err


def _parse(out):
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    return parse_toon(out)


# =============================================================================
# Read-only probes on an empty / missing plan
# =============================================================================


def test_main_list_empty_returns_success(plan_context, monkeypatch, capsys):
    """``list`` dispatches and reports success on a plan with no tasks."""
    plan_context.plan_dir_for('mt-disp-list')

    code, out, _ = _run(monkeypatch, capsys, ['list', '--plan-id', 'mt-disp-list'])

    assert code == 0
    assert 'status: success' in out


def test_main_exists_false_for_missing_task(plan_context, monkeypatch, capsys):
    """``exists`` is a non-erroring boolean probe returning false for an absent task."""
    plan_context.plan_dir_for('mt-disp-exists')

    code, out, _ = _run(monkeypatch, capsys, ['exists', '--plan-id', 'mt-disp-exists', '--task-number', '1'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    # TOON scalar typing may surface the boolean as the literal token ``false``.
    assert str(data['exists']).lower() == 'false'


def test_main_read_missing_task_returns_error(plan_context, monkeypatch, capsys):
    """``read`` of an absent task dispatches to an error payload but exits 0."""
    plan_context.plan_dir_for('mt-disp-read')

    code, out, _ = _run(monkeypatch, capsys, ['read', '--plan-id', 'mt-disp-read', '--task-number', '99'])

    assert code == 0
    assert _parse(out)['status'] == 'error'


def test_main_loop_exit_guard_empty_returns_success(plan_context, monkeypatch, capsys):
    """loop-exit-guard reports success with pending_count 0 on an empty queue."""
    plan_context.plan_dir_for('mt-disp-guard')

    code, out, _ = _run(monkeypatch, capsys, ['loop-exit-guard', '--plan-id', 'mt-disp-guard'])

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert int(data['pending_count']) == 0


# =============================================================================
# Pure compute verb dispatch (no plan)
# =============================================================================


def test_main_derive_cost_size_returns_size_band(plan_context, monkeypatch, capsys):
    """derive-cost-size dispatches and returns a valid T-shirt size + token cost."""
    code, out, _ = _run(
        monkeypatch,
        capsys,
        [
            'derive-cost-size',
            '--step-count', '3',
            '--profile', 'implementation',
            '--skills-count', '2',
            '--target-file-count', '3',
        ],
    )

    assert code == 0
    data = _parse(out)
    assert data['status'] == 'success'
    assert data['cost_size'] in ('S', 'M', 'L', 'XL')
    assert int(data['predicted_cost_tokens']) >= 0


# =============================================================================
# prepare-add -> commit-add roundtrip through the dispatcher
# =============================================================================


def test_main_prepare_then_commit_creates_task(plan_context, monkeypatch, capsys):
    """prepare-add returns a scratch path; commit-add reads it and creates TASK-001."""
    # Arrange / Act: prepare-add
    code, out, _ = _run(monkeypatch, capsys, ['prepare-add', '--plan-id', 'mt-disp-add'])
    assert code == 0
    prep = _parse(out)
    assert prep['status'] == 'success'

    # Write a valid TOON task definition to the allocated scratch path.
    scratch = Path(prep['path'])
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text(
        'title: Dispatch Add\n'
        'deliverable: 1\n'
        'domain: java\n'
        'description: created through main() dispatch\n'
        'steps:\n'
        '  - src/main/java/X.java (write-new)\n'
        'depends_on: none\n',
        encoding='utf-8',
    )

    # Act: commit-add
    code, out, _ = _run(monkeypatch, capsys, ['commit-add', '--plan-id', 'mt-disp-add'])

    # Assert: TASK-001 created and the scratch consumed
    assert code == 0
    commit = _parse(out)
    assert commit['status'] == 'success'
    assert commit['file'] == 'TASK-001.json'
    assert not scratch.exists()


def test_main_get_alias_reads_existing_task(plan_context, monkeypatch, capsys):
    """The ``get`` alias dispatches to the read handler for an existing task."""
    add_basic_task(plan_id='mt-disp-get', title='Aliased Read', deliverable=1)

    code, out, _ = _run(monkeypatch, capsys, ['get', '--plan-id', 'mt-disp-get', '--task-number', '1'])

    assert code == 0
    assert 'status: success' in out
    assert 'Aliased Read' in out


def test_main_next_surfaces_pending_task(plan_context, monkeypatch, capsys):
    """``next`` dispatches and surfaces the only pending task."""
    add_basic_task(plan_id='mt-disp-next', title='Next Target', deliverable=1)

    code, out, _ = _run(monkeypatch, capsys, ['next', '--plan-id', 'mt-disp-next'])

    assert code == 0
    assert 'status: success' in out
    assert 'Next Target' in out


# =============================================================================
# argparse-level rejections at the dispatcher boundary
# =============================================================================


def test_main_missing_subcommand_exits_2(plan_context, monkeypatch, capsys):
    """No subcommand is an argparse error: SystemExit code 2."""
    code, _, err = _run(monkeypatch, capsys, [])

    assert code == 2
    assert 'usage' in err.lower() or 'error' in err.lower()


def test_main_update_unknown_flag_exits_2(plan_context, monkeypatch, capsys):
    """An unknown flag on a real subcommand is an argparse error: exit 2."""
    code, _, _ = _run(monkeypatch, capsys, ['update', '--plan-id', 'x', '--task-number', '1', '--bogus'])

    assert code == 2
