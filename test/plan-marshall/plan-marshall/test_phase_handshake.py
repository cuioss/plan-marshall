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


@pytest.mark.xfail(
    strict=False,
    reason=(
        'Root-cause notation fix (underscore manage_status -> hyphen manage-status '
        'in _handshake_commands.py:_load_status_metadata) is owned by plan '
        'renaming-a-marketplace-script-file-silently-chang. Until that plan lands, '
        '_load_status_metadata invokes an unresolvable executor notation. This '
        'contract test flips to a real pass once the sibling fix merges; the xfail '
        'marker is removed in a follow-up.'
    ),
)
def test_load_status_metadata_uses_resolvable_manage_status_notation() -> None:
    """End-to-end contract: _load_status_metadata must invoke a resolvable notation.

    Unlike every other handshake test, this test does NOT monkeypatch
    ``_load_status_metadata`` — it inspects the real source so a notation
    regression in that function is caught structurally. The existing suite
    patches ``_load_status_metadata`` everywhere, so an unresolvable script
    notation inside it is invisible to those tests.

    The executor (``.plan/execute-script.py``) only maps the hyphenated
    notation ``plan-marshall:manage-status:manage-status``. An underscore
    variant (``manage_status``) fails to resolve, the subprocess exits
    non-zero, ``_load_status_metadata`` swallows it and returns ``{}``, and
    every downstream ``metadata.get('use_worktree')`` silently yields
    ``None`` — producing a spurious ``worktree_metadata_drift`` for plans
    that legitimately run in a worktree.
    """
    handshake_src = (SCRIPTS_DIR / '_handshake_commands.py').read_text(encoding='utf-8')
    canonical_notation = 'plan-marshall:manage-status:manage-status'
    underscore_notation = 'plan-marshall:manage-status:manage_status'

    assert canonical_notation in handshake_src, (
        '_handshake_commands.py must invoke manage-status via the canonical '
        f'hyphenated notation {canonical_notation!r} that the executor maps.'
    )
    assert underscore_notation not in handshake_src, (
        '_handshake_commands.py must not invoke the underscore notation '
        f'{underscore_notation!r} — it is absent from the executor SCRIPTS '
        'mapping and resolves to a non-zero exit, which _load_status_metadata '
        'swallows into an empty metadata dict.'
    )


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


# --- (e) qgate aggregation across all phase files ------------------------
#
# The qgate blocking type cannot be queried via ``manage-findings query
# --type qgate`` because Q-Gate findings live in ``qgate-{phase}.jsonl``
# (canonical query iterates only ``FINDING_TYPES`` which excludes
# ``qgate``). The aggregation helper loops every phase and sums the
# per-phase qgate query results so a producer-mismatch row filed under
# any phase still blocks the 6-finalize boundary.


def test_qgate_aggregated_helper_loops_every_qgate_phase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_query_pending_qgate_count_aggregated`` issues one query per phase.

    Pins the contract that the helper enumerates every value in
    ``QGATE_PHASES`` and routes through the ``qgate list --phase {p}
    --resolution pending`` subcommand (NOT the canonical ``list --type
    qgate`` path that returns 0 for the qgate type). Without this
    enumeration a producer-mismatch row filed under ``5-execute`` would
    fail to block the ``5-execute → 6-finalize`` boundary even though
    ``qgate`` is in the configured blocking partition.
    """
    # Arrange — capture every script invocation made by the helper.
    captured: list[list[str]] = []
    per_phase_counts = {
        '2-refine': 0,
        '3-outline': 1,  # one pending qgate row at 3-outline
        '4-plan': 0,
        '5-execute': 2,  # two pending qgate rows at 5-execute (producer-mismatch)
        '6-finalize': 0,
    }

    def _fake_run(args: list[str]) -> str:
        captured.append(args)
        # Locate the ``--phase`` flag and emit the per-phase count.
        phase_idx = args.index('--phase')
        phase = args[phase_idx + 1]
        return f'filtered_count: {per_phase_counts.get(phase, 0)}\n'

    monkeypatch.setattr(inv, '_run_script', _fake_run)

    # Act
    total = inv._query_pending_qgate_count_aggregated('any-plan')

    # Assert — sum across all phases (1 + 2 = 3) and exactly one query per
    # phase value defined in QGATE_PHASES.
    assert total == 3
    assert len(captured) == len(inv.QGATE_PHASES)
    for args in captured:
        # Every call MUST hit the qgate subcommand surface, not the
        # canonical query path that misses qgate findings entirely.
        assert args[1] == 'qgate'
        assert args[2] == 'list'
        # And every call MUST filter by ``--resolution pending`` — the same
        # contract the per-type query enforces for the other blocking types.
        resolution_idx = args.index('--resolution')
        assert args[resolution_idx + 1] == 'pending'

    # Every phase in QGATE_PHASES was queried exactly once (set equality
    # pins the loop's coverage of the phase list).
    queried_phases = {args[args.index('--phase') + 1] for args in captured}
    assert queried_phases == set(inv.QGATE_PHASES)


def test_qgate_aggregated_helper_returns_none_on_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any per-phase query failure poisons the aggregate to ``None``.

    The aggregated helper inherits the conservative "not applicable"
    contract from ``_query_pending_count_for_type`` — silent
    under-counting would let a transition advance with unresolved Q-Gate
    rows in flight, defeating the whole boundary guard.
    """
    # Arrange — the executor returns ``None`` for one phase (script failed).
    def _fake_run(args: list[str]) -> str | None:
        phase = args[args.index('--phase') + 1]
        if phase == '4-plan':
            return None  # simulated executor failure
        return 'filtered_count: 0\n'

    monkeypatch.setattr(inv, '_run_script', _fake_run)

    # Act
    total = inv._query_pending_qgate_count_aggregated('any-plan')

    # Assert — partial visibility -> ``None``, not 0.
    assert total is None


def test_capture_blocks_at_finalize_when_qgate_pending_via_aggregator(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """qgate is in the default blocking partition for 6-finalize: a
    pending qgate row (from any phase) MUST trip ``BlockingFindingsPresent``.

    Stubs the aggregating helper to return a non-zero count — the same
    semantics a real producer-mismatch row filed under ``phase=5-execute``
    would produce after this fix. Pre-fix the canonical
    ``--type qgate`` query returned 0 always, so the gate never tripped.
    This test pins the corrected behaviour structurally.
    """
    # Arrange — qgate aggregator reports a pending row; canonical per-type
    # query continues to report zeros for the other blocking types.
    monkeypatch.setattr(
        inv,
        '_query_pending_qgate_count_aggregated',
        lambda _plan_id: 1,
    )
    stub_blocking_types['6-finalize'] = ['qgate']

    # Act
    with PlanContext(plan_id='pf-block-qgate'):
        result = cmds.cmd_capture(_ns(plan_id='pf-block-qgate', phase='6-finalize'))

        # Assert — the aggregator's count rolls up into the blocking total
        # and the capture refuses to persist the row.
        assert result['status'] == 'error'
        assert result['error'] == 'blocking_findings_present'
        assert result['blocking_count'] == 1
        assert result['blocking_types'] == ['qgate']
        assert result['per_type'] == {'qgate': 1}
        assert store.get_row('pf-block-qgate', '6-finalize') is None


def test_capture_succeeds_at_finalize_when_qgate_finding_accepted(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """qgate findings resolved via ``accepted`` / ``taken_into_account``
    drop out of the pending count; the boundary clears.

    Mirrors the resolution-escape-valve contract documented in
    ``phase-handshake.md`` § Resolution model: any non-``pending``
    resolution counts as resolved for blocking purposes. The aggregator
    returns 0 because every per-phase qgate query filters by
    ``--resolution pending``, so resolved rows never contribute.
    """
    # Arrange — every qgate row across every phase has been resolved.
    monkeypatch.setattr(
        inv,
        '_query_pending_qgate_count_aggregated',
        lambda _plan_id: 0,
    )
    stub_blocking_types['6-finalize'] = ['qgate']

    # Act
    with PlanContext(plan_id='pf-qgate-accepted'):
        result = cmds.cmd_capture(_ns(plan_id='pf-qgate-accepted', phase='6-finalize'))

        # Assert — capture succeeds, the boundary clears.
        assert result['status'] == 'success'
        assert result['invariants']['pending_findings_blocking_count'] in (0, '0')
        row = store.get_row('pf-qgate-accepted', '6-finalize')
        assert row is not None
        assert row['pending_findings_blocking_count'] in (0, '0')


def test_capture_routes_only_qgate_via_aggregator(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The qgate-aggregator route MUST NOT leak into other blocking types.

    Pins that ``_capture_pending_findings_blocking_count`` only routes the
    ``qgate`` partition entry through the aggregating helper —
    ``bug``, ``lint-issue``, ``sonar-issue``, ``pr-comment``, etc. continue
    to use the canonical per-type query. A regression that routes every
    type through the aggregator would over-count and incorrectly block.
    Conversely, a regression that routes ``qgate`` through the per-type
    query would re-introduce the silent no-op the aggregator was added to
    fix.
    """
    # Arrange — track aggregator invocations and which finding_type values
    # the canonical per-type query receives. The per-type query is also
    # invoked by the passive ``_capture_pending_findings_by_type`` row for
    # every type in _PENDING_FINDING_TYPES, so the assertion only checks
    # that ``qgate`` is NEVER passed to it (route-isolation contract) —
    # not that the call list is exhaustive of the blocking partition.
    aggregator_calls: list[str] = []
    type_query_types: list[str] = []

    def _fake_aggregator(plan_id: str) -> int:
        aggregator_calls.append(plan_id)
        return 0

    def _fake_type_query(_plan_id: str, finding_type: str) -> int:
        type_query_types.append(finding_type)
        return 0

    monkeypatch.setattr(inv, '_query_pending_qgate_count_aggregated', _fake_aggregator)
    monkeypatch.setattr(inv, '_query_pending_count_for_type', _fake_type_query)

    # Standard partition with qgate alongside non-qgate blocking types.
    stub_blocking_types['6-finalize'] = ['build-error', 'qgate', 'lint-issue']

    # Act
    with PlanContext(plan_id='pf-qgate-route'):
        result = cmds.cmd_capture(_ns(plan_id='pf-qgate-route', phase='6-finalize'))

    # Assert — qgate dispatched to aggregator exactly once.
    assert result['status'] == 'success'
    assert aggregator_calls == ['pf-qgate-route']

    # ``qgate`` MUST NEVER reach the per-type query path — that is the
    # silent no-op the aggregator exists to bypass.
    assert 'qgate' not in type_query_types

    # Non-qgate blocking types MUST hit the per-type query at least once
    # (they may also be queried by the passive _capture_pending_findings_
    # by_type row, hence ``in`` rather than ``==``).
    assert 'build-error' in type_query_types
    assert 'lint-issue' in type_query_types


# --- (f) intra-finalize boundary re-capture (production scenarios) -------
#
# The phase-6-finalize standards (``automated-review.md`` and
# ``sonar-roundtrip.md``) re-issue ``phase_handshake capture --phase
# 6-finalize`` between the consumer-side dispatch loop and
# ``mark-step-done``. These tests pin the production pairing of finding
# type and boundary so a regression that drops the re-capture from one
# of the two standards documents (e.g., during a future restructure)
# surfaces as a clear test failure naming the boundary that lost its
# gate.


def test_pending_pr_comment_blocks_automated_review_to_branch_cleanup(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
) -> None:
    """automated-review → branch-cleanup intra-finalize re-capture.

    In production the ``automated-review.md`` standard re-issues
    ``phase_handshake capture --phase 6-finalize`` immediately after the
    per-finding consumer dispatch and immediately before
    ``mark-step-done --step automated-review``. With ``pr-comment`` in
    the configured blocking partition for 6-finalize (the default seeded
    by ``determine_mode.py``), a pending pr-comment finding refuses the
    capture — and therefore refuses the boundary advance into
    ``branch-cleanup``.
    """
    # Arrange — production-matching partition: pr-comment blocks at
    # 6-finalize per the default seeded by `marshall-steward`.
    stub_query_counts['pr-comment'] = 2
    stub_blocking_types['6-finalize'] = ['pr-comment']

    # Act — exact call shape automated-review.md issues in production.
    with PlanContext(plan_id='pf-intra-autoreview'):
        result = cmds.cmd_capture(_ns(plan_id='pf-intra-autoreview', phase='6-finalize'))

    # Assert — capture refuses; the orchestrator surfaces the structured
    # error envelope and refuses to proceed to branch-cleanup.
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 2
    assert 'pr-comment' in result['blocking_types']
    assert result['per_type'] == {'pr-comment': 2}
    assert store.get_row('pf-intra-autoreview', '6-finalize') is None


def test_pending_sonar_issue_blocks_sonar_roundtrip_to_next(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
) -> None:
    """sonar-roundtrip → next intra-finalize re-capture.

    In production the ``sonar-roundtrip.md`` standard re-issues
    ``phase_handshake capture --phase 6-finalize`` immediately after the
    per-finding consumer dispatch and immediately before
    ``mark-step-done --step sonar-roundtrip``. With ``sonar-issue`` in
    the blocking partition (default), a pending sonar-issue finding
    refuses the capture — gating the boundary into the next finalize
    step.
    """
    # Arrange — production-matching partition: sonar-issue is in the
    # global block list (every phase) per the default partition.
    stub_query_counts['sonar-issue'] = 1
    stub_blocking_types['6-finalize'] = ['sonar-issue']

    # Act — exact call shape sonar-roundtrip.md issues in production.
    with PlanContext(plan_id='pf-intra-sonar'):
        result = cmds.cmd_capture(_ns(plan_id='pf-intra-sonar', phase='6-finalize'))

    # Assert — capture refuses; the next finalize step does not run.
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert 'sonar-issue' in result['blocking_types']
    assert result['per_type'] == {'sonar-issue': 1}
    assert store.get_row('pf-intra-sonar', '6-finalize') is None


def test_intra_finalize_recapture_clears_after_resolution(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
) -> None:
    """The intra-finalize re-capture loop-back contract: clears after fix.

    Pins the loop-back guidance documented in ``automated-review.md``
    and ``sonar-roundtrip.md`` Phase Boundary Re-Capture sections — the
    boundary is satisfied "only when capture returns ``status: success``"
    after each pending finding is resolved.
    """
    # Arrange — pending pr-comment refuses the capture.
    stub_query_counts['pr-comment'] = 1
    stub_blocking_types['6-finalize'] = ['pr-comment']

    with PlanContext(plan_id='pf-intra-loop'):
        # First capture refuses.
        first = cmds.cmd_capture(_ns(plan_id='pf-intra-loop', phase='6-finalize'))
        assert first['status'] == 'error'
        assert first['error'] == 'blocking_findings_present'

        # Resolution dropping the pending count to zero — the same effect
        # as ``manage-findings resolve --resolution fixed`` /
        # ``--resolution accepted`` /etc. unblocks the boundary.
        stub_query_counts['pr-comment'] = 0

        # Re-issued capture (the loop-back call from the standards doc)
        # now succeeds and persists the row.
        second = cmds.cmd_capture(_ns(plan_id='pf-intra-loop', phase='6-finalize'))
        assert second['status'] == 'success'
        assert second['invariants']['pending_findings_blocking_count'] in (0, '0')
        row = store.get_row('pf-intra-loop', '6-finalize')
        assert row is not None


# =============================================================================
# D4: Round-trip tests for every blocking type in the dict[str, Callable] mapping
# =============================================================================
#
# For each type registered in ``_GLOBAL_BLOCKING_TYPES`` / ``_FINALIZE_BLOCKING_TYPES``:
#   1. Stub the producer-side query to emit a non-zero pending count.
#   2. Drive ``_capture_pending_findings_blocking_count`` directly.
#   3. Assert the queried count == the produced count.
#
# The "silent zero" tripwire fires when any newly-mapped type returns a count of
# zero for its first-traffic capture — that signals a missing dispatch entry in
# the per-type registry.


import determine_mode as _determine_mode_for_roundtrip  # type: ignore[import-not-found]  # noqa: E402


@pytest.mark.parametrize(
    'finding_type',
    sorted(_determine_mode_for_roundtrip._FINALIZE_BLOCKING_TYPES.keys()),
)
def test_blocking_type_roundtrip_queried_matches_produced(
    finding_type: str,
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Round-trip: producing N findings of this type → query reports exactly N.

    Pins the dispatch contract for every type in the mapping. A regression
    that adds a type without wiring its callable surfaces as the queried
    count diverging from the produced count (typically zero — the "silent
    zero" failure mode this test is designed to catch).
    """
    # Arrange — produce 3 findings of this type. The qgate path uses a
    # different storage shape (aggregated across phases), so stub the
    # aggregator separately to emit the same count.
    produced_count = 3
    if finding_type == 'qgate':
        monkeypatch.setattr(
            inv, '_query_pending_qgate_count_aggregated', lambda _plan_id: produced_count
        )
    else:
        stub_query_counts[finding_type] = produced_count

    # 6-finalize is the only guarded boundary; using 5-execute means the
    # capture returns the count rather than raising BlockingFindingsPresent
    # — that keeps every parametrised case symmetric regardless of type.
    stub_blocking_types['5-execute'] = [finding_type]

    # Act
    queried_count = inv._capture_pending_findings_blocking_count(
        'plan-roundtrip', {}, '5-execute'
    )

    # Assert — queried == produced.
    assert queried_count == produced_count, (
        f'Round-trip failed for blocking type {finding_type!r}: '
        f'queried={queried_count}, produced={produced_count}. '
        f'A queried count of 0 indicates a missing dispatch entry in the '
        f'dict[str, Callable] mapping (silent-zero failure mode).'
    )


def test_blocking_type_silent_zero_tripwire_all_types_have_dispatch(
    only_pending_findings_invariants,
    stub_metadata,
    stub_query_counts,
    stub_blocking_types,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No type in the mapping silently returns zero when traffic exists.

    Constructs a fixture where every registered blocking type has a pending
    count of 1, configures all of them as blocking for ``5-execute``, and
    asserts the capture's total matches the produced sum. A type whose
    dispatch routes nowhere would contribute 0 and break the equality.
    """
    # Arrange
    mapping_keys = sorted(_determine_mode_for_roundtrip._FINALIZE_BLOCKING_TYPES.keys())

    monkeypatch.setattr(
        inv, '_query_pending_qgate_count_aggregated', lambda _plan_id: 1
    )
    for finding_type in mapping_keys:
        if finding_type == 'qgate':
            continue  # handled by the aggregator stub above
        stub_query_counts[finding_type] = 1

    stub_blocking_types['5-execute'] = list(mapping_keys)

    # Act
    queried_total = inv._capture_pending_findings_blocking_count(
        'plan-tripwire', {}, '5-execute'
    )

    # Assert — every type contributes exactly 1.
    expected_total = len(mapping_keys)
    assert queried_total == expected_total, (
        f'Silent-zero tripwire fired: expected total {expected_total} '
        f'(one per registered type), got {queried_total}. '
        f'A type without a dispatch entry contributed 0 instead of 1.'
    )


# =============================================================================
# Tri-state worktree assertion (metadata→disk direction) — full phase matrix
# =============================================================================
#
# ``_resolve_worktree_assertion`` implements the tri-state phase-entry contract
# documented in workflow-integration-git/standards/worktree-handling.md:
#
# - use_worktree==true AND worktree_path empty AND phase in
#   {1-init, 2-refine, 3-outline, 4-plan} → deferred-pending (return None).
# - use_worktree==true AND worktree_path empty AND phase in
#   {5-execute, 6-finalize} → worktree_unresolved error.
#
# These tests parametrize across every (phase, metadata-state) cell so neither
# half of the tri-state can regress silently — a future refactor that flips
# 4-plan into the post-materialization set, or weakens the empty-path error
# for 5-execute, immediately trips a red bar.


_PRE_MATERIALIZATION_PHASES_FOR_TEST = ('1-init', '2-refine', '3-outline', '4-plan')
_POST_MATERIALIZATION_PHASES_FOR_TEST = ('5-execute', '6-finalize')
_ALL_PHASES_FOR_TEST = _PRE_MATERIALIZATION_PHASES_FOR_TEST + _POST_MATERIALIZATION_PHASES_FOR_TEST


class TestTriStateWorktreeAssertion:
    """Pin the full tri-state contract of ``_resolve_worktree_assertion``.

    Covers the 6 phase × 2 metadata-state matrix:

    - 6 phases: 1-init, 2-refine, 3-outline, 4-plan, 5-execute, 6-finalize
    - 2 empty-path metadata states: ``use_worktree=true`` with
      ``worktree_path=''`` (deferred-pending vs error split by phase) and
      ``use_worktree=false`` (assertion always passes regardless of phase).
    """

    @pytest.mark.parametrize('phase', _PRE_MATERIALIZATION_PHASES_FOR_TEST)
    def test_deferred_pending_returns_none_for_pre_materialization_phases(
        self, phase: str
    ) -> None:
        """use_worktree=true + worktree_path='' + pre-materialization phase → None.

        The orchestrator may opt the plan into worktree mode before the
        on-disk directory has been created. During 1-init through 4-plan
        the worktree has not yet been materialized, so the assertion must
        let the boundary advance (deferred-pending). The empty
        ``worktree_path`` is the legitimate transitional shape, not an
        error.
        """
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is None, (
            f'Tri-state regressed for phase {phase!r}: expected None '
            f'(deferred-pending pass-through) for use_worktree=true with '
            f"empty worktree_path, got {result!r}. The tri-state contract "
            f'must let pre-materialization phases advance with an empty path.'
        )

    @pytest.mark.parametrize('phase', _POST_MATERIALIZATION_PHASES_FOR_TEST)
    def test_worktree_unresolved_error_for_post_materialization_phases(
        self, phase: str
    ) -> None:
        """use_worktree=true + worktree_path='' + post-materialization phase → error.

        By the time phase-5-execute or phase-6-finalize runs, the worktree
        directory must exist. An empty ``worktree_path`` post-materialization
        is a real writer-chain failure (phase-5-execute did not create the
        worktree, or status.metadata was stomped between phases). The
        assertion fails loud with ``worktree_unresolved`` so the boundary
        refuses to advance until metadata is repaired.
        """
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is not None, (
            f'Tri-state regressed for phase {phase!r}: expected '
            f'worktree_unresolved error for use_worktree=true with empty '
            f'worktree_path, got None. Post-materialization phases must '
            f'NEVER pass with an empty path — the deferred-pending window '
            f'closes at the 5-execute boundary.'
        )
        assert result['status'] == 'error'
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_use_worktree_false_passes_for_every_phase(self, phase: str) -> None:
        """use_worktree=false → None for every phase (main-checkout pass-through).

        Plans routed against the main checkout never trip the assertion,
        regardless of phase. This is the symmetric guard against a future
        refactor that accidentally requires a worktree for some subset of
        phases — main-checkout plans must run end-to-end.
        """
        metadata = {'use_worktree': False, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, phase)
        assert result is None, (
            f'Main-checkout regression for phase {phase!r}: expected None '
            f'when use_worktree=false, got {result!r}. The assertion must '
            f'not fire for plans that never opted into a worktree.'
        )

    def test_legacy_single_arg_caller_preserves_strict_empty_path_failure(self) -> None:
        """phase=None (legacy callers) → strict pre-tri-state behaviour.

        Callers that haven't been migrated to pass the phase argument get
        the conservative strict behaviour: empty ``worktree_path`` always
        fails, no deferred-pending window. This preserves backward
        compatibility for any consumer still on the legacy single-arg API.
        """
        metadata = {'use_worktree': True, 'worktree_path': ''}
        result = cmds._resolve_worktree_assertion(metadata, None)
        assert result is not None
        assert result['error'] == 'worktree_unresolved'
        assert result['reason'] == 'worktree_path_missing'


# =============================================================================
# Inverse-direction orphan invariant — canonical-path bypass for pre-mat phases
# =============================================================================
#
# ``_capture_worktree_orphan`` is the inverse direction of the worktree
# assertion: it fires when a worktree directory exists on disk under
# ``.plan/local/worktrees/{plan_id}`` but metadata reports use_worktree!=true
# (writer-chain drift). The tri-state contract has one bypass: when
# use_worktree==true AND the canonical orphan path is present, the capture
# returns None for ALL phases — that's the materialized-just-not-yet-persisted
# window OR the legitimate post-materialization steady state.
#
# These tests pin both halves of the inverse direction.


class TestOrphanCanonicalBypass:
    """Pin the inverse-direction (disk→metadata) tri-state contract.

    Covers two complementary scenarios:

    - ``use_worktree==true`` (in any shape — bool, 'true', 1) AND canonical
      orphan dir present → capture returns None (no drift, the orphan dir
      is the legitimate worktree).
    - ``use_worktree`` not truthy AND orphan dir present → raises
      :class:`WorktreeMetadataDrift` for every phase, because the orphan
      shape signals a writer-chain bug.
    """

    @pytest.fixture
    def isolated_repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Point ``_repo_root`` at an isolated tmp_path with a worktrees dir.

        The capture uses ``_repo_root()`` to derive the canonical orphan
        path. Patching the helper directly avoids depending on
        ``PLAN_BASE_DIR`` semantics (which would only work if the fixture
        directory layout exactly matched ``.plan/local``).
        """
        monkeypatch.setattr(inv, '_repo_root', lambda: tmp_path)
        return tmp_path

    @staticmethod
    def _create_canonical_orphan(repo_root: Path, plan_id: str) -> Path:
        """Create the canonical worktree dir for ``plan_id`` under ``repo_root``."""
        orphan = repo_root / '.plan' / 'local' / 'worktrees' / plan_id
        orphan.mkdir(parents=True, exist_ok=True)
        return orphan

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_bypass_when_use_worktree_true_and_canonical_path_present(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """use_worktree=true + canonical orphan path → None (no drift) for any phase.

        The metadata→disk direction (worktree exists, path missing in
        metadata) is owned by ``_resolve_worktree_assertion``. The inverse
        capture must NOT raise here — it would double-report the same drift
        condition and refuse to advance even when the metadata→disk
        direction is being repaired.
        """
        plan_id = 'orphan-bypass-true'
        self._create_canonical_orphan(isolated_repo, plan_id)
        metadata = {'use_worktree': True}
        result = inv._capture_worktree_orphan(plan_id, metadata, phase)
        assert result is None, (
            f'Inverse-direction tri-state regressed for phase {phase!r}: '
            f'expected None (bypass) when use_worktree=true and canonical '
            f'orphan path is present, got {result!r}. The inverse capture '
            f'must yield to _resolve_worktree_assertion in the metadata→'
            f'disk direction.'
        )

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_raises_writer_chain_drift_when_use_worktree_false(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """use_worktree=false + canonical orphan path → WorktreeMetadataDrift.

        The orphan-dir-exists-but-metadata-denies-it shape is the writer-
        chain drift surfaced by lesson 2026-05-08-14-001. It must raise for
        every phase — including 5-execute and 6-finalize — so the boundary
        refuses to persist a row that would silently absorb the drift.
        """
        plan_id = 'orphan-drift-false'
        orphan = self._create_canonical_orphan(isolated_repo, plan_id)
        metadata = {'use_worktree': False}
        with pytest.raises(inv.WorktreeMetadataDrift) as exc_info:
            inv._capture_worktree_orphan(plan_id, metadata, phase)
        assert exc_info.value.plan_id == plan_id
        assert exc_info.value.worktree_dir == str(orphan)
        assert exc_info.value.use_worktree is False

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_raises_writer_chain_drift_when_use_worktree_missing(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """No use_worktree key + canonical orphan path → WorktreeMetadataDrift.

        Absence of the ``use_worktree`` key is treated as the falsy case
        per ``_is_truthy_metadata``. An orphan dir without a positive
        metadata claim is writer-chain drift for every phase.
        """
        plan_id = 'orphan-drift-missing'
        self._create_canonical_orphan(isolated_repo, plan_id)
        metadata: dict[str, object] = {}
        with pytest.raises(inv.WorktreeMetadataDrift):
            inv._capture_worktree_orphan(plan_id, metadata, phase)

    @pytest.mark.parametrize('phase', _ALL_PHASES_FOR_TEST)
    def test_returns_none_when_orphan_directory_absent(
        self, isolated_repo: Path, phase: str
    ) -> None:
        """No orphan dir → None for every (phase, metadata-state) combination.

        The capture's first gate is the orphan-directory existence check.
        When the directory is absent, neither truthy nor falsy
        ``use_worktree`` can produce a drift signal — there is nothing on
        disk to drift against.
        """
        plan_id = 'orphan-absent'
        # Note: no _create_canonical_orphan call — directory deliberately absent.
        for use_worktree_value in (True, False, None):
            metadata = {'use_worktree': use_worktree_value} if use_worktree_value is not None else {}
            result = inv._capture_worktree_orphan(plan_id, metadata, phase)
            assert result is None, (
                f'Capture returned {result!r} for phase {phase!r} with '
                f'use_worktree={use_worktree_value!r} and no orphan dir; '
                f'the orphan-absent gate must return None unconditionally.'
            )


# =============================================================================
# references_valid invariant
# =============================================================================
#
# ``_capture_references_valid`` emits a deterministic hash over the structural
# health of references.json:
#
#   {present: bool, top_level_is_dict: bool, required_field_set: sorted list}
#
# Four failure modes must produce a hash that differs from the valid-baseline
# hash so drift surfaces at every phase boundary:
#
# 1. present + valid (all required keys) → stable hash across capture/verify.
# 2. missing file → present=False → different hash.
# 3. non-dict content (file_not_found error or non-dict references) → different hash.
# 4. missing required field → required_field_set shrinks → different hash.
#
# The invariant is passive (never raises). Tests drive ``_capture_references_valid``
# directly by stubbing ``_run_script`` so no executor hop is needed.


def _make_refs_toon_success(fields: dict) -> str:
    """Build a TOON string that ``manage-references read`` would emit on success.

    ``cmd_read`` summarizes list fields as ``"N items"`` strings — this helper
    mirrors that output so the nested ``references`` object can be parsed as a
    plain dict of scalar key-value pairs with no TOON list syntax to trip the
    parser.
    """
    lines = ['status: success', 'plan_id: test-plan']
    # Emit the ``references`` sub-key with each field on its own line.
    # Keys are present if and only if they appear in ``fields``.
    lines.append('references:')
    for k, v in fields.items():
        if isinstance(v, list):
            # Mirror cmd_read's list-summary behaviour.
            lines.append(f'  {k}: {len(v)} items')
        else:
            lines.append(f'  {k}: {v}')
    return '\n'.join(lines) + '\n'


def _make_refs_toon_error() -> str:
    """Build a TOON string that ``manage-references read`` would emit when the file is missing."""
    return 'status: error\nerror: file_not_found\nmessage: references.json not found\n'


# --- (a) present + valid: hash is stable across two independent captures ---


def test_references_valid_hash_stable_for_valid_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Capture of a present, valid references.json produces the same hash twice.

    Pins the "hash stable across capture/verify" contract: two independent
    calls with the same manage-references read output must emit equal hashes
    so verify reports ``ok`` rather than drift.
    """
    valid_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    monkeypatch.setattr(inv, '_run_script', lambda _args: valid_toon)

    hash_a = inv._capture_references_valid('any', {}, '2-refine')
    hash_b = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_a is not None
    assert isinstance(hash_a, str)
    assert len(hash_a) == 16  # _hash_dict returns first 16 hex chars
    assert hash_a == hash_b, (
        'Hash is not stable: two captures of the same valid references.json '
        f'produced different values: {hash_a!r} vs {hash_b!r}.'
    )


# --- (b) missing file: hash differs from valid baseline ---


def test_references_valid_hash_differs_for_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing references.json produces a hash that differs from the valid baseline.

    The hash payload has ``present=False`` for the missing-file case, so even
    when the hash function itself is deterministic the two payloads diverge and
    drift detection fires on verify.
    """
    valid_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    error_toon = _make_refs_toon_error()

    monkeypatch.setattr(inv, '_run_script', lambda _args: valid_toon)
    hash_valid = inv._capture_references_valid('any', {}, '2-refine')

    monkeypatch.setattr(inv, '_run_script', lambda _args: error_toon)
    hash_missing = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_valid is not None
    assert hash_missing is not None
    assert hash_valid != hash_missing, (
        'Hash did not change when references.json was reported as missing: '
        f'valid={hash_valid!r}, missing={hash_missing!r}. '
        'Drift detection would silently pass a deleted references.json.'
    )


# --- (c) non-dict content: hash differs from valid baseline ---


def test_references_valid_hash_differs_for_non_dict_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """An error response from manage-references read produces a hash that differs from the valid baseline.

    Covers the ``present=False`` branch of the hash payload: when
    ``manage-references read`` reports ``status: error`` (file deleted,
    corrupted JSON, or any other read failure), ``_capture_references_valid``
    must emit a hash that diverges from the well-formed-file baseline so drift
    detection fires on verify.
    """
    valid_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })

    # ``manage-references read`` translates corruption / unreadable JSON into a
    # top-level ``status: error`` TOON response, which routes through the
    # ``present=False`` branch of ``_capture_references_valid``. The
    # ``present=True, top_level_is_dict=False`` branch (references sub-key
    # present but not a dict) is structurally unreachable through the
    # manage-references read surface, so it is not exercised here.
    error_toon = _make_refs_toon_error()

    monkeypatch.setattr(inv, '_run_script', lambda _args: valid_toon)
    hash_valid = inv._capture_references_valid('any', {}, '2-refine')

    monkeypatch.setattr(inv, '_run_script', lambda _args: error_toon)
    hash_error = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_valid is not None
    assert hash_error is not None
    assert hash_valid != hash_error, (
        'Hash did not change for error-response content: '
        f'valid={hash_valid!r}, error={hash_error!r}. '
        'Drift detection would silently accept a corrupted references.json.'
    )


# --- (d) missing required field: hash differs from valid baseline ---


def test_references_valid_hash_differs_for_missing_required_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Removing a required field from references.json produces a different hash.

    Phase-1-init promises ``branch``, ``base_branch``, and ``modified_files``.
    Dropping any one of them shrinks ``required_field_set`` in the hash payload
    and the drift detection fires on verify. This test drops ``modified_files``.
    """
    full_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        'modified_files': [],
    })
    partial_toon = _make_refs_toon_success({
        'branch': 'feature/my-plan',
        'base_branch': 'main',
        # modified_files intentionally absent — simulates silent deletion of the field
    })

    monkeypatch.setattr(inv, '_run_script', lambda _args: full_toon)
    hash_full = inv._capture_references_valid('any', {}, '2-refine')

    monkeypatch.setattr(inv, '_run_script', lambda _args: partial_toon)
    hash_partial = inv._capture_references_valid('any', {}, '2-refine')

    assert hash_full is not None
    assert hash_partial is not None
    assert hash_full != hash_partial, (
        'Hash did not change when a required field (modified_files) was removed: '
        f'full={hash_full!r}, partial={hash_partial!r}. '
        'Drift detection would silently accept references.json with missing keys.'
    )


# --- (e) HANDSHAKE_FIELDS schema includes references_valid ----------------


def test_handshake_fields_includes_references_valid() -> None:
    """The TOON column schema must include ``references_valid``.

    Without this column the row writer would silently drop the invariant value
    at persistence time, defeating the drift guard at every phase boundary.
    """
    assert 'references_valid' in store.HANDSHAKE_FIELDS
