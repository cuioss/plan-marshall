#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for phase_handshake script internals.

Covers `_git_helpers`, `_handshake_store`, and the command handlers in
`_handshake_commands` by driving them directly. The invariant registry is
stubbed per test so the handlers do not need a real execute-script.py.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest
from conftest import PlanContext, get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _git_helpers as git_helpers  # noqa: E402
import _handshake_commands as cmds  # noqa: E402
import _handshake_store as store  # noqa: E402
import _invariants as inv  # noqa: E402


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with one commit and a .gitignore."""
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'], check=True)
    (tmp_path / '.gitignore').write_text('.plan/\n')
    (tmp_path / 'README.md').write_text('x\n')
    subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'commit', '-q', '-m', 'init'], check=True)
    return tmp_path


@pytest.fixture
def stubbed_invariants(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Replace INVARIANTS with a deterministic stub set and return a mutable state dict."""
    state: dict[str, object] = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'worktree_sha': None,
        'worktree_dirty': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'pending_tasks_count': 2,
    }

    def always(_pid: str, _md: dict) -> bool:
        return True

    def worktree_applies(_pid: str, md: dict) -> bool:
        return bool(md.get('worktree_path'))

    def make_capture(name: str):
        def _cap(_pid: str, md: dict, _phase: str):
            if name.startswith('worktree') and not md.get('worktree_path'):
                return None
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('worktree_sha', worktree_applies, make_capture('worktree_sha')),
        ('worktree_dirty', worktree_applies, make_capture('worktree_dirty')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('pending_tasks_count', always, make_capture('pending_tasks_count')),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(cmds, 'INVARIANTS', stubbed)
    return state


@pytest.fixture
def stub_metadata(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Replace _load_status_metadata with a mutable dict."""
    md: dict[str, object] = {}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _ns(**kwargs) -> types.SimpleNamespace:
    kwargs.setdefault('override', False)
    kwargs.setdefault('reason', None)
    kwargs.setdefault('strict', False)
    return types.SimpleNamespace(**kwargs)


# =============================================================================
# _git_helpers
# =============================================================================


def test_git_head_returns_sha(repo: Path) -> None:
    sha = git_helpers.git_head(repo)
    assert sha is not None
    assert len(sha) == 40


def test_git_dirty_count_clean_repo(repo: Path) -> None:
    assert git_helpers.git_dirty_count(repo) == 0


def test_git_dirty_count_with_untracked(repo: Path) -> None:
    (repo / 'new.txt').write_text('y\n')
    assert git_helpers.git_dirty_count(repo) == 1


def test_git_head_outside_repo(tmp_path: Path) -> None:
    assert git_helpers.git_head(tmp_path) is None


# =============================================================================
# _handshake_store
# =============================================================================


def test_store_upsert_and_load() -> None:
    with PlanContext(plan_id='handshake-store-a'):
        store.upsert_row('handshake-store-a', {'phase': '5-execute', 'main_sha': 'abc'})
        rows = store.load_rows('handshake-store-a')
        assert len(rows) == 1
        assert rows[0]['phase'] == '5-execute'
        assert rows[0]['main_sha'] == 'abc'


def test_store_upsert_replaces_existing_phase() -> None:
    with PlanContext(plan_id='handshake-store-b'):
        store.upsert_row('handshake-store-b', {'phase': '5-execute', 'main_sha': 'old'})
        store.upsert_row('handshake-store-b', {'phase': '5-execute', 'main_sha': 'new'})
        rows = store.load_rows('handshake-store-b')
        assert len(rows) == 1
        assert rows[0]['main_sha'] == 'new'


def test_store_multiple_phases() -> None:
    with PlanContext(plan_id='handshake-store-c'):
        store.upsert_row('handshake-store-c', {'phase': '5-execute', 'main_sha': 'a'})
        store.upsert_row('handshake-store-c', {'phase': '6-finalize', 'main_sha': 'b'})
        rows = store.load_rows('handshake-store-c')
        phases = {r['phase'] for r in rows}
        assert phases == {'5-execute', '6-finalize'}


def test_store_remove_row() -> None:
    with PlanContext(plan_id='handshake-store-d'):
        store.upsert_row('handshake-store-d', {'phase': '5-execute', 'main_sha': 'a'})
        store.upsert_row('handshake-store-d', {'phase': '6-finalize', 'main_sha': 'b'})
        removed = store.remove_row('handshake-store-d', '5-execute')
        assert removed is True
        rows = store.load_rows('handshake-store-d')
        assert len(rows) == 1
        assert rows[0]['phase'] == '6-finalize'


def test_store_remove_missing_phase_returns_false() -> None:
    with PlanContext(plan_id='handshake-store-e'):
        store.upsert_row('handshake-store-e', {'phase': '5-execute', 'main_sha': 'a'})
        assert store.remove_row('handshake-store-e', '3-outline') is False


def test_store_load_missing_file() -> None:
    with PlanContext(plan_id='handshake-store-f'):
        assert store.load_rows('handshake-store-f') == []


# =============================================================================
# cmd_capture / cmd_verify
# =============================================================================


def test_capture_first_time_success(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='cap-a'):
        result = cmds.cmd_capture(_ns(plan_id='cap-a', phase='5-execute'))
        assert result['status'] == 'success'
        assert result['phase'] == '5-execute'
        assert result['worktree_applicable'] is False
        assert 'main_sha' in result['invariants']
        assert 'worktree_sha' not in result['invariants']  # empty when not applicable


def test_capture_worktree_applicable(stubbed_invariants, stub_metadata) -> None:
    stub_metadata['worktree_path'] = '/tmp/fake-worktree'
    stubbed_invariants['worktree_sha'] = 'wt-sha'
    stubbed_invariants['worktree_dirty'] = 0
    with PlanContext(plan_id='cap-b'):
        result = cmds.cmd_capture(_ns(plan_id='cap-b', phase='5-execute'))
        assert result['worktree_applicable'] is True
        assert result['invariants']['worktree_sha'] == 'wt-sha'


def test_capture_override_requires_reason(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='cap-c'):
        result = cmds.cmd_capture(_ns(plan_id='cap-c', phase='5-execute', override=True))
        assert result['status'] == 'error'
        assert result['error'] == 'missing_reason'


def test_capture_override_with_reason_stores_flag(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='cap-d'):
        result = cmds.cmd_capture(_ns(plan_id='cap-d', phase='5-execute', override=True, reason='manual commit'))
        assert result['status'] == 'success'
        assert result['override'] is True
        row = store.get_row('cap-d', '5-execute')
        assert row is not None
        assert row['override'] is True
        assert row['override_reason'] == 'manual commit'


def test_verify_ok_no_drift(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-a'):
        cmds.cmd_capture(_ns(plan_id='ver-a', phase='5-execute'))
        result = cmds.cmd_verify(_ns(plan_id='ver-a', phase='5-execute'))
        assert result['status'] == 'ok'


def test_verify_drift_main_dirty(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-b'):
        cmds.cmd_capture(_ns(plan_id='ver-b', phase='5-execute'))
        stubbed_invariants['main_dirty'] = 5
        result = cmds.cmd_verify(_ns(plan_id='ver-b', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'main_dirty' in diff_names


def test_verify_drift_main_sha(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-c'):
        cmds.cmd_capture(_ns(plan_id='ver-c', phase='5-execute'))
        stubbed_invariants['main_sha'] = 'def456'
        result = cmds.cmd_verify(_ns(plan_id='ver-c', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'main_sha' in diff_names


def test_verify_drift_task_state_hash(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-d'):
        cmds.cmd_capture(_ns(plan_id='ver-d', phase='5-execute'))
        stubbed_invariants['task_state_hash'] = 'different-hash'
        result = cmds.cmd_verify(_ns(plan_id='ver-d', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'task_state_hash' in diff_names


def test_verify_drift_qgate_count(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-e'):
        cmds.cmd_capture(_ns(plan_id='ver-e', phase='5-execute'))
        stubbed_invariants['qgate_open_count'] = 3
        result = cmds.cmd_verify(_ns(plan_id='ver-e', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'qgate_open_count' in diff_names


def test_verify_drift_config_hash(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-f'):
        cmds.cmd_capture(_ns(plan_id='ver-f', phase='5-execute'))
        stubbed_invariants['config_hash'] = 'rotated'
        result = cmds.cmd_verify(_ns(plan_id='ver-f', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'config_hash' in diff_names


def test_capture_persists_pending_tasks_count_to_handshakes_toon(stubbed_invariants, stub_metadata) -> None:
    """``pending_tasks_count`` must round-trip through handshakes.toon.

    The HANDSHAKE_FIELDS column list now includes ``pending_tasks_count`` —
    capturing must persist the value, and re-loading via ``store.get_row``
    must surface it. This guards against a regression where the column was
    dropped from the schema or the registry tuple was unwired.
    """
    stubbed_invariants['pending_tasks_count'] = 4
    with PlanContext(plan_id='cap-pending-persist'):
        result = cmds.cmd_capture(_ns(plan_id='cap-pending-persist', phase='5-execute'))
        assert result['status'] == 'success'
        # Captured-invariants payload echoes the column.
        assert result['invariants'].get('pending_tasks_count') in (4, '4')

        # Persisted row has the column populated, not blanked out.
        row = store.get_row('cap-pending-persist', '5-execute')
        assert row is not None
        assert 'pending_tasks_count' in row, f'pending_tasks_count must be a HANDSHAKE_FIELDS column, got {list(row)}'
        assert row['pending_tasks_count'] in (4, '4'), row


def test_verify_drift_pending_tasks_count(stubbed_invariants, stub_metadata) -> None:
    """A change in pending_tasks_count between capture and verify is drift."""
    stubbed_invariants['pending_tasks_count'] = 3
    with PlanContext(plan_id='ver-pending'):
        cmds.cmd_capture(_ns(plan_id='ver-pending', phase='5-execute'))
        # Mid-phase the queue drains: every task completed.
        stubbed_invariants['pending_tasks_count'] = 0
        result = cmds.cmd_verify(_ns(plan_id='ver-pending', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'pending_tasks_count' in diff_names


def test_handshake_fields_includes_pending_tasks_count() -> None:
    """The TOON column schema must include ``pending_tasks_count``.

    Without this column the row writer would silently drop the value at
    persistence time, defeating the phase-5-execute transition guard.
    """
    assert 'pending_tasks_count' in store.HANDSHAKE_FIELDS


def test_verify_skipped_no_capture(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='ver-g'):
        result = cmds.cmd_verify(_ns(plan_id='ver-g', phase='5-execute'))
        assert result['status'] == 'skipped'


def test_list_returns_all_captures(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='list-a'):
        cmds.cmd_capture(_ns(plan_id='list-a', phase='5-execute'))
        cmds.cmd_capture(_ns(plan_id='list-a', phase='6-finalize'))
        result = cmds.cmd_list(_ns(plan_id='list-a'))
        assert result['count'] == 2
        phases = {r['phase'] for r in result['handshakes']}
        assert phases == {'5-execute', '6-finalize'}


def test_clear_removes_one_phase(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='clr-a'):
        cmds.cmd_capture(_ns(plan_id='clr-a', phase='5-execute'))
        cmds.cmd_capture(_ns(plan_id='clr-a', phase='6-finalize'))
        result = cmds.cmd_clear(_ns(plan_id='clr-a', phase='5-execute'))
        assert result['removed'] is True
        remaining = cmds.cmd_list(_ns(plan_id='clr-a'))
        assert remaining['count'] == 1
        assert remaining['handshakes'][0]['phase'] == '6-finalize'


def test_clear_missing_phase_reports_not_removed(stubbed_invariants, stub_metadata) -> None:
    with PlanContext(plan_id='clr-b'):
        result = cmds.cmd_clear(_ns(plan_id='clr-b', phase='5-execute'))
        assert result['status'] == 'success'
        assert result['removed'] is False


# =============================================================================
# phase_steps_complete invariant
# =============================================================================


def _write_required_steps(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')


# --- parser ---------------------------------------------------------------


def test_parse_required_steps_bullet_format(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(
        f,
        '# Required steps\n\n- commit-push\n- create-pr\n- record-metrics\n',
    )
    assert inv._parse_required_steps(f) == ['commit-push', 'create-pr', 'record-metrics']


def test_parse_required_steps_ignores_blank_and_comments(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(
        f,
        '\n# Header line\n\nSome prose description.\n\n- one\n\n- two\n\nAnother paragraph.\n- three\n',
    )
    assert inv._parse_required_steps(f) == ['one', 'two', 'three']


def test_parse_required_steps_strips_inline_code(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '- `commit-push`\n- `create-pr`\n')
    assert inv._parse_required_steps(f) == ['commit-push', 'create-pr']


def test_parse_required_steps_empty_file(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '')
    assert inv._parse_required_steps(f) == []


def test_parse_required_steps_no_bullets(tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '# Title\n\nJust prose, no bullet list at all.\n')
    assert inv._parse_required_steps(f) == []


def test_parse_required_steps_missing_file_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / 'does-not-exist.md'
    assert inv._parse_required_steps(f) == []


# --- resolver -------------------------------------------------------------


def test_resolve_required_steps_path_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bundles = tmp_path / 'bundles'
    target = bundles / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'required-steps.md'
    _write_required_steps(target, '- commit-push\n')
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: bundles)
    resolved = inv._resolve_required_steps_path('6-finalize')
    assert resolved == target


def test_resolve_required_steps_path_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bundles = tmp_path / 'bundles'
    (bundles / 'plan-marshall' / 'skills' / 'phase-9-ghost' / 'standards').mkdir(parents=True)
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: bundles)
    assert inv._resolve_required_steps_path('9-ghost') is None


def test_resolve_required_steps_path_no_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: None)
    assert inv._resolve_required_steps_path('6-finalize') is None


# --- capture --------------------------------------------------------------


@pytest.fixture
def required_steps_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Install a controllable required-steps.md for phase `5-execute`."""
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '- step-a\n- step-b\n')

    def _resolve(phase: str) -> Path | None:
        if phase == '5-execute':
            return f
        return None

    monkeypatch.setattr(inv, '_resolve_required_steps_path', _resolve)
    return f


def test_capture_phase_steps_all_done(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {
            '5-execute': {
                'step-a': {'outcome': 'done', 'display_detail': None},
                'step-b': {'outcome': 'done', 'display_detail': None},
            }
        }
    }
    result = inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert isinstance(result, str)
    assert len(result) == 16  # _hash_dict returns first 16 hex chars


def test_capture_phase_steps_missing_step(required_steps_path: Path) -> None:
    metadata = {'phase_steps': {'5-execute': {'step-a': {'outcome': 'done', 'display_detail': None}}}}
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.missing == ['step-b']
    assert excinfo.value.not_done == []
    assert excinfo.value.legacy_format == []


def test_capture_phase_steps_skipped_fails(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {
            '5-execute': {
                'step-a': {'outcome': 'done', 'display_detail': None},
                'step-b': {'outcome': 'skipped', 'display_detail': None},
            }
        }
    }
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.missing == []
    assert excinfo.value.not_done == [{'step': 'step-b', 'outcome': 'skipped'}]
    assert excinfo.value.legacy_format == []


def test_capture_phase_steps_legacy_bare_string_fails(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {
            '5-execute': {
                'step-a': 'done',
                'step-b': {'outcome': 'done', 'display_detail': None},
            }
        }
    }
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.legacy_format == ['step-a']
    assert excinfo.value.missing == []
    assert excinfo.value.not_done == []


def test_capture_phase_steps_no_required_file_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: None)
    result = inv._capture_phase_steps_complete('pid', {}, '5-execute')
    assert result is None


def test_capture_phase_steps_empty_required_file_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '# Only prose, no bullets\n')
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: f)
    result = inv._capture_phase_steps_complete('pid', {}, '5-execute')
    assert result is None


def test_capture_phase_steps_no_phase_entry(required_steps_path: Path) -> None:
    metadata = {'phase_steps': {}}
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert set(excinfo.value.missing) == {'step-a', 'step-b'}


# --- cmd_capture / cmd_verify integration --------------------------------


@pytest.fixture
def only_phase_steps_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace INVARIANTS with just the real phase_steps_complete entry.

    This lets cmd_capture / cmd_verify exercise the real invariant code path
    without the other invariants trying to shell out.
    """
    stubbed = [
        (
            'phase_steps_complete',
            lambda _pid, _md: True,
            inv._capture_phase_steps_complete,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(cmds, 'INVARIANTS', stubbed)


def test_cmd_capture_phase_steps_success(only_phase_steps_invariant, stub_metadata, required_steps_path: Path) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'done', 'display_detail': None},
        }
    }
    with PlanContext(plan_id='psc-ok'):
        result = cmds.cmd_capture(_ns(plan_id='psc-ok', phase='5-execute'))
        assert result['status'] == 'success'
        assert 'phase_steps_complete' in result['invariants']
        # Row should be persisted.
        row = store.get_row('psc-ok', '5-execute')
        assert row is not None
        assert row['phase_steps_complete'] != ''


def test_cmd_capture_phase_steps_incomplete_returns_error(
    only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {'5-execute': {'step-a': {'outcome': 'done', 'display_detail': None}}}
    with PlanContext(plan_id='psc-fail'):
        result = cmds.cmd_capture(_ns(plan_id='psc-fail', phase='5-execute'))
        assert result['status'] == 'error'
        assert result['error'] == 'phase_steps_incomplete'
        assert result['missing'] == ['step-b']
        # Row must NOT be persisted on failure.
        assert store.get_row('psc-fail', '5-execute') is None


def test_cmd_capture_phase_steps_skipped_returns_error(
    only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'skipped', 'display_detail': None},
        }
    }
    with PlanContext(plan_id='psc-skip'):
        result = cmds.cmd_capture(_ns(plan_id='psc-skip', phase='5-execute'))
        assert result['status'] == 'error'
        assert result['error'] == 'phase_steps_incomplete'
        assert result['not_done'] == [{'step': 'step-b', 'outcome': 'skipped'}]
        assert store.get_row('psc-skip', '5-execute') is None


def test_cmd_capture_phase_steps_legacy_returns_error(
    only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': 'done',
            'step-b': {'outcome': 'done', 'display_detail': None},
        }
    }
    with PlanContext(plan_id='psc-legacy'):
        result = cmds.cmd_capture(_ns(plan_id='psc-legacy', phase='5-execute'))
        assert result['status'] == 'error'
        assert result['error'] == 'phase_steps_incomplete'
        assert result['legacy_format'] == ['step-a']
        assert store.get_row('psc-legacy', '5-execute') is None


def test_cmd_verify_phase_steps_drift_when_step_regresses(
    only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {
        '5-execute': {
            'step-a': {'outcome': 'done', 'display_detail': None},
            'step-b': {'outcome': 'done', 'display_detail': None},
        }
    }
    with PlanContext(plan_id='psc-drift'):
        cap = cmds.cmd_capture(_ns(plan_id='psc-drift', phase='5-execute'))
        assert cap['status'] == 'success'
        # Regress: a previously-done step is now skipped.
        stub_metadata['phase_steps'] = {
            '5-execute': {
                'step-a': {'outcome': 'done', 'display_detail': None},
                'step-b': {'outcome': 'skipped', 'display_detail': None},
            }
        }
        result = cmds.cmd_verify(_ns(plan_id='psc-drift', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'phase_steps_complete' in diff_names


# =============================================================================
# pending-findings invariant rows (TASK-7 / TASK-8)
# =============================================================================
#
# These tests cover the two new pluggable invariants — ``pending_findings_by_type``
# and ``pending_findings_blocking_count`` — added to enforce the phase-boundary
# blocking-finding contract documented in the BlockingFindingsPresent docstring:
#
# - Per-type capture is passive at every phase (records the queue snapshot).
# - Blocking-count capture refuses (raises BlockingFindingsPresent → cmd_capture
#   returns ``error: blocking_findings_present``) at the *guarded* boundary
#   ``6-finalize`` when a blocking-type pending finding is present. The intra-
#   finalize boundaries (``automated-review → branch-cleanup`` and
#   ``sonar-roundtrip → next``) are guarded by re-issuing
#   ``capture --phase 6-finalize`` so they trip the same exception.
# - Verify-strict behaviour: ``cmd_verify`` translates the exception into a
#   ``drift`` payload on the ``pending_findings_blocking_count`` invariant so
#   the CLI ``--strict`` flag lifts that into a non-zero exit (exercised
#   structurally below — ``cmd_verify`` is the value-producing path the CLI
#   wraps with the strict-exit check).
# - Long-lived non-blocking types (``insight``, ``tip``, ``best-practice``,
#   ``improvement``) MUST NOT block when they are the only pending findings,
#   even when their counts are non-zero.
# - ``accepted`` and ``taken_into_account`` resolutions count as resolved —
#   the per-type query is filtered by ``--resolution pending``, so any finding
#   in those resolutions is structurally excluded from both rows.


@pytest.fixture
def only_pending_findings_invariants(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace INVARIANTS with just the two real pending-finding entries.

    Mirrors :func:`only_phase_steps_invariant` so cmd_capture / cmd_verify
    exercise the real per-type and blocking-count code paths without the
    other invariants shelling out to the executor.
    """
    stubbed = [
        (
            'pending_findings_by_type',
            lambda _pid, _md: True,
            inv._capture_pending_findings_by_type,
        ),
        (
            'pending_findings_blocking_count',
            lambda _pid, _md: True,
            inv._capture_pending_findings_blocking_count,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(cmds, 'INVARIANTS', stubbed)


@pytest.fixture
def stub_query_counts(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Stub ``_query_pending_count_for_type`` with a per-type pending counter.

    Returns the mutable mapping; tests assign per-type counts (``state['bug']
    = 2``) before invoking captures. Unset types resolve to ``0`` — the same
    "no pending findings of this type" outcome the real query produces when
    the JSONL file is empty.
    """
    state: dict[str, int] = {}

    def _query(_plan_id: str, finding_type: str) -> int:
        return state.get(finding_type, 0)

    monkeypatch.setattr(inv, '_query_pending_count_for_type', _query)
    return state


@pytest.fixture
def stub_blocking_types(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str] | None]:
    """Stub ``_read_blocking_finding_types`` with a per-phase mapping.

    Tests populate ``state[phase] = ['bug', 'lint-issue']`` (etc.) before
    capture. Unset phases resolve to ``None`` — matching the production
    contract that "no partition configured" means "nothing blocks".
    """
    state: dict[str, list[str] | None] = {}

    def _read(_plan_id: str, phase: str) -> list[str] | None:
        return state.get(phase)

    monkeypatch.setattr(inv, '_read_blocking_finding_types', _read)
    return state


# --- (a) per-type capture matches manage-findings query output -----------


def test_capture_pending_findings_by_type_compact_summary(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """The per-type row mirrors the per-type query and stays sorted/stable."""
    # Arrange — three types have pending findings, the rest are zero.
    stub_query_counts['bug'] = 2
    stub_query_counts['lint-issue'] = 1
    stub_query_counts['insight'] = 5
    # No blocking partition configured → blocking row must remain 0.
    stub_blocking_types['5-execute'] = None

    # Act
    with PlanContext(plan_id='pf-by-type'):
        result = cmds.cmd_capture(_ns(plan_id='pf-by-type', phase='5-execute'))

        # Assert
        assert result['status'] == 'success'
        summary = result['invariants']['pending_findings_by_type']
        # Every known type appears with its count, in registry order.
        assert 'bug=2' in summary
        assert 'lint-issue=1' in summary
        assert 'insight=5' in summary
        # Types with zero pending findings still appear (passive snapshot).
        assert 'tip=0' in summary
        assert 'best-practice=0' in summary
        # Blocking row reflects "nothing blocks" — partition unset.
        assert result['invariants']['pending_findings_blocking_count'] in (0, '0')


def test_capture_pending_findings_by_type_persists_to_handshakes_toon(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """The per-type row round-trips through handshakes.toon under the schema."""
    # Arrange
    stub_query_counts['triage'] = 4
    stub_blocking_types['5-execute'] = None

    # Act
    with PlanContext(plan_id='pf-persist'):
        cmds.cmd_capture(_ns(plan_id='pf-persist', phase='5-execute'))

        # Assert
        row = store.get_row('pf-persist', '5-execute')
        assert row is not None
        assert 'pending_findings_by_type' in row
        assert 'triage=4' in row['pending_findings_by_type']
        assert 'pending_findings_blocking_count' in row


def test_handshake_fields_includes_pending_finding_columns() -> None:
    """The TOON column schema must include both pending-finding columns.

    Without these columns the row writer would silently drop the values at
    persistence time, defeating the phase-6-finalize boundary guard.
    """
    assert 'pending_findings_by_type' in store.HANDSHAKE_FIELDS
    assert 'pending_findings_blocking_count' in store.HANDSHAKE_FIELDS


# --- (b) verify-strict blocks transition at guarded boundary -------------


def test_capture_at_finalize_boundary_blocks_when_blocking_type_pending(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """5-execute → 6-finalize: capture --phase 6-finalize must refuse.

    A pending ``bug`` finding (configured as blocking for 6-finalize) makes
    the capture raise BlockingFindingsPresent; cmd_capture surfaces it as a
    structured error and refuses to persist the row.
    """
    # Arrange
    stub_query_counts['bug'] = 1
    stub_query_counts['lint-issue'] = 0
    stub_blocking_types['6-finalize'] = ['bug', 'lint-issue']

    # Act
    with PlanContext(plan_id='pf-block-finalize'):
        result = cmds.cmd_capture(_ns(plan_id='pf-block-finalize', phase='6-finalize'))

        # Assert
        assert result['status'] == 'error'
        assert result['error'] == 'blocking_findings_present'
        assert result['blocking_count'] == 1
        assert result['blocking_types'] == ['bug', 'lint-issue']
        assert result['per_type'] == {'bug': 1, 'lint-issue': 0}
        # Row must NOT be persisted on failure — boundary is gated.
        assert store.get_row('pf-block-finalize', '6-finalize') is None


def test_capture_blocks_automated_review_to_branch_cleanup_boundary(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """automated-review → branch-cleanup boundary is guarded via re-capture.

    The phase-6-finalize orchestrator re-issues
    ``phase_handshake capture --phase 6-finalize`` at this checkpoint, so a
    pending blocking-type finding trips the same exception. This test pins
    the contract that the exception fires for the same phase key the
    orchestrator passes — there is no separate "automated-review" phase.
    """
    # Arrange — a Sonar issue is configured as blocking for 6-finalize.
    stub_query_counts['sonar-issue'] = 2
    stub_blocking_types['6-finalize'] = ['sonar-issue']

    # Act
    with PlanContext(plan_id='pf-block-autoreview'):
        result = cmds.cmd_capture(_ns(plan_id='pf-block-autoreview', phase='6-finalize'))

        # Assert
        assert result['status'] == 'error'
        assert result['error'] == 'blocking_findings_present'
        assert result['blocking_count'] == 2
        assert result['per_type'] == {'sonar-issue': 2}
        assert store.get_row('pf-block-autoreview', '6-finalize') is None


def test_capture_blocks_sonar_roundtrip_next_boundary(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """sonar-roundtrip → next boundary is guarded via re-capture.

    Same mechanism as automated-review → branch-cleanup: the orchestrator
    issues ``capture --phase 6-finalize`` and a pending blocking finding
    refuses persistence. Pinned with a different blocking-type set so a
    regression that hard-codes the blocking partition would fail here.
    """
    # Arrange
    stub_query_counts['pr-comment'] = 3
    stub_blocking_types['6-finalize'] = ['pr-comment']

    # Act
    with PlanContext(plan_id='pf-block-sonar'):
        result = cmds.cmd_capture(_ns(plan_id='pf-block-sonar', phase='6-finalize'))

        # Assert
        assert result['status'] == 'error'
        assert result['error'] == 'blocking_findings_present'
        assert result['blocking_count'] == 3
        assert result['per_type'] == {'pr-comment': 3}
        assert store.get_row('pf-block-sonar', '6-finalize') is None


def test_verify_at_finalize_boundary_reports_drift_for_strict_mode(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """cmd_verify translates BlockingFindingsPresent into drift on the
    blocking-count column — the CLI ``--strict`` flag turns drift into exit 1.

    First captures a clean row (no blocking findings), then introduces a
    pending blocking-type finding; verify must surface drift on
    ``pending_findings_blocking_count`` so the CLI strict guard fires.
    """
    # Arrange — capture with the boundary clean.
    stub_blocking_types['6-finalize'] = ['bug']

    # Act — initial clean capture, then a regression.
    with PlanContext(plan_id='pf-verify-strict'):
        cap = cmds.cmd_capture(_ns(plan_id='pf-verify-strict', phase='6-finalize'))
        assert cap['status'] == 'success'

        # Mid-phase a blocking-type finding lands.
        stub_query_counts['bug'] = 1
        result = cmds.cmd_verify(_ns(plan_id='pf-verify-strict', phase='6-finalize'))

        # Assert — verify treats the blocker as drift on the dedicated column,
        # which the CLI's ``--strict`` flag promotes to exit 1.
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'pending_findings_blocking_count' in diff_names


# --- (c) verify-strict allows transition with only non-blocking types ---


def test_capture_at_finalize_succeeds_when_only_long_lived_findings_pending(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """Only the four long-lived non-blocking types pending → boundary clears.

    ``insight``, ``tip``, ``best-practice``, ``improvement`` are not in the
    blocking partition for 6-finalize, so non-zero counts on them MUST NOT
    block the transition. cmd_capture succeeds and persists the row; verify
    sees no drift on the blocking-count column.
    """
    # Arrange — every long-lived type has pending findings, none are blocking.
    stub_query_counts['insight'] = 7
    stub_query_counts['tip'] = 4
    stub_query_counts['best-practice'] = 2
    stub_query_counts['improvement'] = 9
    stub_blocking_types['6-finalize'] = ['bug', 'lint-issue', 'sonar-issue']

    # Act
    with PlanContext(plan_id='pf-long-lived'):
        result = cmds.cmd_capture(_ns(plan_id='pf-long-lived', phase='6-finalize'))

        # Assert — capture succeeded.
        assert result['status'] == 'success'
        assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
        # Per-type row reflects the long-lived counts — passive snapshot.
        summary = result['invariants']['pending_findings_by_type']
        assert 'insight=7' in summary
        assert 'tip=4' in summary
        assert 'best-practice=2' in summary
        assert 'improvement=9' in summary
        # Row was persisted: the boundary is satisfied.
        row = store.get_row('pf-long-lived', '6-finalize')
        assert row is not None
        assert row['pending_findings_blocking_count'] in (0, '0')

        # Verify is clean — no drift surfaces on the blocking-count column.
        verify = cmds.cmd_verify(_ns(plan_id='pf-long-lived', phase='6-finalize'))
        assert verify['status'] == 'ok'


def test_blocking_count_zero_when_no_partition_configured(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """Phases without a blocking_finding_types config slot capture as 0.

    Passive snapshot semantics: the per-type row still records every
    pending finding (so retrospective analysis sees the queue), but the
    blocking-count column is a hard zero because nothing is configured to
    block.
    """
    # Arrange — pending findings but no partition configured for this phase.
    stub_query_counts['bug'] = 5
    stub_blocking_types['3-outline'] = None  # explicit "no partition"

    # Act
    with PlanContext(plan_id='pf-no-partition'):
        result = cmds.cmd_capture(_ns(plan_id='pf-no-partition', phase='3-outline'))

        # Assert
        assert result['status'] == 'success'
        assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
        summary = result['invariants']['pending_findings_by_type']
        assert 'bug=5' in summary


def test_blocking_count_passive_at_non_guarded_boundary(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """Non-guarded phases capture the blocking total without raising.

    A pending blocking-type finding at phase ``5-execute`` records the count
    but MUST NOT raise — only ``6-finalize`` is in ``_BLOCKING_BOUNDARIES``.
    Retrospective analysis reads the row to see the queue at every phase
    boundary.
    """
    # Arrange — a blocking-type finding pending at a non-guarded phase.
    stub_query_counts['bug'] = 2
    stub_blocking_types['5-execute'] = ['bug']

    # Act
    with PlanContext(plan_id='pf-passive'):
        result = cmds.cmd_capture(_ns(plan_id='pf-passive', phase='5-execute'))

        # Assert — captured with the non-zero total, no exception raised.
        assert result['status'] == 'success'
        assert result['invariants']['pending_findings_blocking_count'] in (2, '2')


# --- (d) accepted / taken_into_account resolutions count as resolved -----


def test_query_pending_count_excludes_accepted_and_taken_into_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_query_pending_count_for_type`` filters by ``--resolution pending``.

    The blocking-count contract documents that ``accepted`` and
    ``taken_into_account`` resolutions count as resolved. The implementation
    encodes that property by passing ``--resolution pending`` to
    ``manage-findings query``, so any finding in any other resolution
    bucket — including ``accepted`` and ``taken_into_account`` — is
    structurally excluded from both pending-finding rows.

    This test pins the filter argument so a regression that drops
    ``--resolution pending`` would surface immediately.
    """
    # Arrange — capture the args that ``_run_script`` is asked to send.
    captured: list[list[str]] = []

    def _fake_run(args: list[str]) -> str:
        captured.append(args)
        return 'filtered_count: 0\n'

    monkeypatch.setattr(inv, '_run_script', _fake_run)

    # Act
    inv._query_pending_count_for_type('any-plan', 'bug')

    # Assert — the resolution filter pins ``pending`` exclusively.
    assert len(captured) == 1
    args = captured[0]
    # ``--resolution pending`` — the filter that excludes ``accepted`` and
    # ``taken_into_account`` from the count.
    resolution_idx = args.index('--resolution')
    assert args[resolution_idx + 1] == 'pending'
    # The query targets the requested type — pins the per-type partitioning.
    type_idx = args.index('--type')
    assert args[type_idx + 1] == 'bug'


def test_capture_blocking_count_excludes_resolved_findings(
    only_pending_findings_invariants, stub_metadata, stub_query_counts, stub_blocking_types
) -> None:
    """End-to-end: a 6-finalize capture clears even when blocking-type
    findings exist in resolved buckets (``accepted`` / ``taken_into_account``).

    The stub mirrors the real query semantics: ``stub_query_counts`` only
    counts pending findings, so a value of ``0`` is exactly what the real
    query returns when every blocking-type finding is in an ``accepted``
    or ``taken_into_account`` resolution. Boundary clears.
    """
    # Arrange — every blocking-type finding has been accepted or
    # taken_into_account, so pending counts are zero.
    stub_query_counts['bug'] = 0
    stub_query_counts['lint-issue'] = 0
    stub_query_counts['sonar-issue'] = 0
    stub_blocking_types['6-finalize'] = ['bug', 'lint-issue', 'sonar-issue']

    # Act
    with PlanContext(plan_id='pf-accepted'):
        result = cmds.cmd_capture(_ns(plan_id='pf-accepted', phase='6-finalize'))

        # Assert — no exception, capture succeeded, boundary cleared.
        assert result['status'] == 'success'
        assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
        row = store.get_row('pf-accepted', '6-finalize')
        assert row is not None
