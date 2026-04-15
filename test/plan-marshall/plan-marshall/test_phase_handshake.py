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
        result = cmds.cmd_capture(
            _ns(plan_id='cap-d', phase='5-execute', override=True, reason='manual commit')
        )
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
        '\n# Header line\n\nSome prose description.\n\n- one\n\n- two\n\n'
        'Another paragraph.\n- three\n',
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
    target = (
        bundles
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
        / 'standards'
        / 'required-steps.md'
    )
    _write_required_steps(target, '- commit-push\n')
    monkeypatch.setattr(inv, 'find_marketplace_path', lambda: bundles)
    resolved = inv._resolve_required_steps_path('6-finalize')
    assert resolved == target


def test_resolve_required_steps_path_missing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
    metadata = {'phase_steps': {'5-execute': {'step-a': 'done', 'step-b': 'done'}}}
    result = inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert isinstance(result, str)
    assert len(result) == 16  # _hash_dict returns first 16 hex chars


def test_capture_phase_steps_missing_step(required_steps_path: Path) -> None:
    metadata = {'phase_steps': {'5-execute': {'step-a': 'done'}}}
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.missing == ['step-b']
    assert excinfo.value.not_done == []


def test_capture_phase_steps_skipped_fails(required_steps_path: Path) -> None:
    metadata = {
        'phase_steps': {'5-execute': {'step-a': 'done', 'step-b': 'skipped'}}
    }
    with pytest.raises(inv.PhaseStepsIncomplete) as excinfo:
        inv._capture_phase_steps_complete('pid', metadata, '5-execute')
    assert excinfo.value.missing == []
    assert excinfo.value.not_done == [{'step': 'step-b', 'outcome': 'skipped'}]


def test_capture_phase_steps_no_required_file_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inv, '_resolve_required_steps_path', lambda _p: None)
    result = inv._capture_phase_steps_complete('pid', {}, '5-execute')
    assert result is None


def test_capture_phase_steps_empty_required_file_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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


def test_cmd_capture_phase_steps_success(
    only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {'5-execute': {'step-a': 'done', 'step-b': 'done'}}
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
    stub_metadata['phase_steps'] = {'5-execute': {'step-a': 'done'}}
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
        '5-execute': {'step-a': 'done', 'step-b': 'skipped'}
    }
    with PlanContext(plan_id='psc-skip'):
        result = cmds.cmd_capture(_ns(plan_id='psc-skip', phase='5-execute'))
        assert result['status'] == 'error'
        assert result['error'] == 'phase_steps_incomplete'
        assert result['not_done'] == [{'step': 'step-b', 'outcome': 'skipped'}]
        assert store.get_row('psc-skip', '5-execute') is None


def test_cmd_verify_phase_steps_drift_when_step_regresses(
    only_phase_steps_invariant, stub_metadata, required_steps_path: Path
) -> None:
    stub_metadata['phase_steps'] = {'5-execute': {'step-a': 'done', 'step-b': 'done'}}
    with PlanContext(plan_id='psc-drift'):
        cap = cmds.cmd_capture(_ns(plan_id='psc-drift', phase='5-execute'))
        assert cap['status'] == 'success'
        # Regress: a previously-done step is now skipped.
        stub_metadata['phase_steps'] = {
            '5-execute': {'step-a': 'done', 'step-b': 'skipped'}
        }
        result = cmds.cmd_verify(_ns(plan_id='psc-drift', phase='5-execute'))
        assert result['status'] == 'drift'
        diff_names = {d['invariant'] for d in result['diffs']}
        assert 'phase_steps_complete' in diff_names
