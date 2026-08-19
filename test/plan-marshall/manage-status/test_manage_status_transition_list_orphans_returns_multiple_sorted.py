#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back.

Split from test_manage_status.py: covers cmd_transition (incl. inline
strict-verify guard for guarded boundaries, and last-phase symmetry with
cmd_archive), cmd_archive (incl. --reason flag), cmd_delete_plan (incl. the main-anchored
lesson carry-back, its five-value ``lesson_carry_back_action`` and that
vocabulary's stated relationship to ``_lessons_query.RESTORE_ACTIONS``, and the
veto that refuses the deletion when a carried lesson did not land), cmd_list (incl.
worktree moved-in plan discovery), cmd_list_orphans, and cmd_mark_step_done
loop-back target validation.
"""


import json
import shutil
from argparse import Namespace

import _handshake_commands as _cmds  # noqa: E402
import _invariants as _inv  # noqa: E402
import pytest
from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _query,
    _seed_legitimate_plan,
    _seed_plan_with_4_plan_capture,
    _seed_plan_with_5_execute_capture,
    cmd_list_orphans,
    cmd_transition,
)

from conftest import run_script


@pytest.fixture
def _stubbed_invariants(monkeypatch):
    """Deterministic invariant registry shared across cmd_capture / cmd_verify."""
    state = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'main_dirty_files': [],
        'worktree_sha': None,
        'worktree_dirty': None,
        'worktree_orphan': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'unfinished_tasks_count': 2,
        'phase_steps_complete': None,
        'pending_findings_by_type': '',
        'pending_findings_blocking_count': 0,
    }

    def always(_pid, _md):
        return True

    def make_capture(name):
        def _cap(_pid, _md, _phase):
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('main_dirty_files', always, make_capture('main_dirty_files')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('unfinished_tasks_count', always, make_capture('unfinished_tasks_count')),
        ('pending_findings_by_type', always, make_capture('pending_findings_by_type')),
        ('pending_findings_blocking_count', always, make_capture('pending_findings_blocking_count')),
    ]
    monkeypatch.setattr(_inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(_cmds, 'INVARIANTS', stubbed)
    return state


@pytest.fixture
def _stub_metadata(monkeypatch):
    """Replace _load_status_metadata so cmd_verify sees a metadata dict free
    of worktree fields (avoids the worktree-resolution assertion).
    """
    md: dict = {}
    monkeypatch.setattr(_cmds, '_load_status_metadata', lambda _pid: md)
    return md


def test_list_orphans_returns_multiple_sorted(plan_context):
    """(d) Multiple orphans are all returned, sorted by id."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-many'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    for name in ('zeta-orphan', 'alpha-orphan', 'mid-orphan'):
        d = plans_dir / name
        d.mkdir(parents=True)
        (d / 'stray.txt').write_text('x')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 3
    ids = [o['id'] for o in result['orphans']]
    assert ids == ['alpha-orphan', 'mid-orphan', 'zeta-orphan'], (
        f'orphans must be returned in sorted id order, got {ids}'
    )
    for orphan in result['orphans']:
        assert orphan['contents'] == ['stray.txt']


def test_list_orphans_mixed_eight_orphans_plus_two_legitimate_plans(plan_context):
    """CLI resolvability + filter contract: 8 orphans + 2 legitimate plans → ONLY the 8 orphans returned."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-mixed'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    orphan_names = [f'orphan-{i:02d}' for i in range(8)]
    for name in orphan_names:
        (plans_dir / name).mkdir(parents=True)

    _seed_legitimate_plan('lesson-alpha')
    _seed_legitimate_plan('lesson-beta')

    result = cmd_list_orphans(Namespace())
    assert result['status'] == 'success'
    assert result['total'] == 8, (
        f"Expected exactly 8 orphans (legitimate lesson-* plans must be filtered out), "
        f"got total={result['total']} ids={[o['id'] for o in result['orphans']]}"
    )
    returned_ids = [o['id'] for o in result['orphans']]
    assert returned_ids == sorted(orphan_names), (
        f'Expected sorted orphan ids {sorted(orphan_names)}, got {returned_ids}'
    )
    assert 'lesson-alpha' not in returned_ids
    assert 'lesson-beta' not in returned_ids

    cli_result = run_script(SCRIPT_PATH, 'list-orphans')
    assert cli_result.success, (
        f'list-orphans subcommand must be resolvable via the script entry point. '
        f'stderr: {cli_result.stderr}'
    )
    assert 'status: success' in cli_result.stdout
    for name in orphan_names:
        assert name in cli_result.stdout, f'orphan {name} missing from CLI output'
    assert 'lesson-alpha' not in cli_result.stdout
    assert 'lesson-beta' not in cli_result.stdout


def test_list_orphans_unreadable_dir_emits_sentinel(plan_context, monkeypatch):
    """(1) OSError on iterdir → contents=['<unreadable>'] sentinel."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-unreadable'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    orphan_dir = plan_context.fixture_dir / 'plans' / 'unreadable-orphan'
    orphan_dir.mkdir(parents=True)

    from pathlib import Path as _Path

    original_iterdir = _Path.iterdir

    def patched_iterdir(self):
        if self == orphan_dir:
            raise PermissionError('simulated unreadable dir')
        return original_iterdir(self)

    monkeypatch.setattr(_Path, 'iterdir', patched_iterdir)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 1
    entry = result['orphans'][0]
    assert entry['id'] == 'unreadable-orphan'
    assert entry['contents'] == ['<unreadable>'], (
        f'Unreadable orphan must surface ["<unreadable>"] sentinel, got '
        f'{entry["contents"]!r}. An empty list would trigger silent '
        f'deletion under planning.md Step 3b.'
    )


def test_list_orphans_file_at_plans_dir_returns_zero(monkeypatch, tmp_path):
    """(2) Stray FILE at plans_dir path → total=0 cleanly, no exception."""
    stray_file = tmp_path / 'plans'
    stray_file.write_text('this is a file, not a directory\n')

    monkeypatch.setattr(_query, 'get_plans_dir', lambda: stray_file)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success', (
        f'Stray file at plans_dir must yield clean success, got {result!r}. '
        f'Regression: plans_dir.exists() returned True for the file and '
        f'iterdir() raised NotADirectoryError.'
    )
    assert result['total'] == 0
    assert result['orphans'] == []


def test_list_orphans_empty_status_json_not_flagged(plan_context, monkeypatch):
    """(3) Empty ``{}`` status.json must NOT be reported as orphan."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-empty-status'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    plan_dir = plans_dir / 'empty-status-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0, (
        f'Empty {{}} status.json must NOT be flagged as orphan (matches '
        f'require_plan_exists file-presence guard), got '
        f'total={result["total"]} orphans={result["orphans"]!r}. '
        f'Regression: the filter is using parsed-truthy `if status:` '
        f'instead of `(plan_dir / "status.json").is_file()`.'
    )
    assert result['orphans'] == []


def test_transition_5_execute_refuses_on_handshake_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition refuses to advance when the captured 5-execute row drifts."""
    plan_id = 'transition-drift-5exec'
    _seed_plan_with_5_execute_capture(plan_id)

    _stubbed_invariants['main_sha'] = 'drifted-sha-xyz'
    plan_dir = plan_context.plan_dir_for(plan_id)
    status_before = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))

    result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))

    assert result is not None
    assert result['status'] == 'drift', (
        f'Expected status: drift on guarded-boundary transition with drifted '
        f'capture, got {result!r}. The inline guard in cmd_transition is not '
        f'firing for 5-execute -> 6-finalize.'
    )
    assert result['phase'] == '5-execute'
    diff_names = {d['invariant'] for d in result['diffs']}
    assert 'main_sha' in diff_names

    status_after = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == status_before['current_phase'] == '5-execute', (
        'cmd_transition wrote status despite drift — the guard is not '
        'short-circuiting before write_status.'
    )
    assert status_after['phases'] == status_before['phases'], (
        'Phase status list mutated despite drift refusal — write_status fired.'
    )


def test_transition_5_execute_drift_toon_byte_equivalent(plan_context, _stubbed_invariants, _stub_metadata):
    """The dict returned by cmd_transition on drift must equal cmd_verify's dict."""
    plan_id = 'transition-drift-equiv'
    _seed_plan_with_5_execute_capture(plan_id)
    _stubbed_invariants['main_sha'] = 'drifted-sha-equiv'

    transition_result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
    verify_result = _cmds.cmd_verify(
        Namespace(plan_id=plan_id, phase='5-execute', strict=True)
    )

    assert transition_result == verify_result, (
        'cmd_transition drift dict diverges from cmd_verify dict. '
        f'transition={transition_result!r} verify={verify_result!r}. '
        'The inline guard MUST return the verify result unchanged.'
    )


def test_transition_4_plan_skips_handshake_verify_on_drift(plan_context, _stubbed_invariants, _stub_metadata):
    """cmd_transition --completed 4-plan ignores handshake drift."""
    plan_id = 'transition-4plan-skip'
    _seed_plan_with_4_plan_capture(plan_id)

    _stubbed_invariants['main_sha'] = 'drifted-sha-4plan'

    result = cmd_transition(Namespace(plan_id=plan_id, completed='4-plan'))

    assert result is not None
    assert result['status'] == 'success', (
        f'cmd_transition refused a non-guarded transition (4-plan -> '
        f'5-execute) despite drift, got {result!r}. The boundary set '
        f"_BLOCKING_BOUNDARIES MUST gate the verify call — non-guarded "
        f'transitions stay drift-blind.'
    )
    assert result['next_phase'] == '5-execute'

    status_after = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert status_after['current_phase'] == '5-execute', (
        'Non-guarded transition failed to advance current_phase despite '
        'returning success — write_status did not fire.'
    )
