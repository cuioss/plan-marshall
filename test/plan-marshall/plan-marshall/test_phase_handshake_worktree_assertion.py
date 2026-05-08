#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the phase-entry worktree assertion in phase_handshake.

Pins the resolved-path / unresolved-path / stale-path / refusal contract
exposed by ``_resolve_worktree_assertion`` and surfaced by ``cmd_capture``
/ ``cmd_verify``. Also exercises the ``--strict`` CLI flag's non-zero exit
on the ``error: worktree_unresolved`` refusal path so callers that swallow
TOON output still see the failure (mirrors the drift contract).

The companion implementation lives in ``_handshake_commands.py``
(``_resolve_worktree_assertion``) and is wired into the ``phase_handshake``
CLI's ``--strict`` exit handling. See TASK-14 in plan
``lesson-2026-05-07-11-001`` for the originating contract.
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

import _handshake_commands as cmds  # noqa: E402
import _invariants as inv  # noqa: E402


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def git_worktree(tmp_path: Path) -> Path:
    """Create a minimal git repo that doubles as a valid worktree top-level.

    The assertion under test invokes ``git rev-parse --show-toplevel`` and
    compares the resolved path to the candidate; a freshly initialised repo
    whose toplevel equals the input path satisfies the resolved-path branch.
    """
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
    """Replace INVARIANTS with a deterministic stub set.

    Mirrors the pattern in ``test_phase_handshake.py`` so cmd_capture /
    cmd_verify don't depend on the real invariant registry (which would
    otherwise reach for execute-script.py and live plan state).
    """
    state: dict[str, object] = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'worktree_sha': None,
        'worktree_dirty': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'pending_tasks_count': 1,
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
    """Replace ``_load_status_metadata`` with a mutable per-test dict."""
    md: dict[str, object] = {}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _ns(**kwargs) -> types.SimpleNamespace:
    kwargs.setdefault('override', False)
    kwargs.setdefault('reason', None)
    kwargs.setdefault('strict', False)
    return types.SimpleNamespace(**kwargs)


# =============================================================================
# _resolve_worktree_assertion: direct unit-level coverage
# =============================================================================


def test_assertion_passes_when_use_worktree_false() -> None:
    """``use_worktree=false`` short-circuits — no error regardless of path."""
    assert cmds._resolve_worktree_assertion({'use_worktree': False}) is None


def test_assertion_passes_when_use_worktree_missing() -> None:
    """Missing ``use_worktree`` is treated as falsy (no assertion)."""
    assert cmds._resolve_worktree_assertion({}) is None


def test_assertion_passes_for_valid_worktree(git_worktree: Path) -> None:
    """Resolved path: existing dir, valid worktree, toplevel matches."""
    metadata = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    assert cmds._resolve_worktree_assertion(metadata) is None


def test_assertion_fails_when_worktree_path_missing() -> None:
    """``use_worktree=true`` + missing ``worktree_path`` → unresolved."""
    err = cmds._resolve_worktree_assertion({'use_worktree': True})
    assert err is not None
    assert err['status'] == 'error'
    assert err['error'] == 'worktree_unresolved'
    assert err['reason'] == 'worktree_path_missing'


def test_assertion_fails_when_worktree_path_empty() -> None:
    """Empty-string ``worktree_path`` is the same refusal as missing."""
    err = cmds._resolve_worktree_assertion({'use_worktree': True, 'worktree_path': '   '})
    assert err is not None
    assert err['error'] == 'worktree_unresolved'
    assert err['reason'] == 'worktree_path_missing'


def test_assertion_fails_when_worktree_path_does_not_exist(tmp_path: Path) -> None:
    """Filesystem-missing path → ``worktree_path_not_found`` refusal."""
    ghost = tmp_path / 'no-such-worktree'
    metadata = {'use_worktree': True, 'worktree_path': str(ghost)}
    err = cmds._resolve_worktree_assertion(metadata)
    assert err is not None
    assert err['error'] == 'worktree_unresolved'
    assert err['reason'] == 'worktree_path_not_found'
    assert err['worktree_path'] == str(ghost)


def test_assertion_fails_when_path_is_not_a_git_worktree(tmp_path: Path) -> None:
    """Existing dir but ``git rev-parse`` exits non-zero → refusal."""
    plain = tmp_path / 'not-a-repo'
    plain.mkdir()
    metadata = {'use_worktree': True, 'worktree_path': str(plain)}
    err = cmds._resolve_worktree_assertion(metadata)
    assert err is not None
    assert err['error'] == 'worktree_unresolved'
    # Non-repo directories surface as ``not_a_git_worktree`` (rev-parse fails).
    assert err['reason'] == 'not_a_git_worktree'


def test_assertion_fails_on_stale_toplevel(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Toplevel mismatch (rev-parse returns a different path) → stale refusal.

    Simulated by stubbing ``subprocess.run`` so the assertion sees a
    mismatched ``--show-toplevel`` output without depending on real worktree
    plumbing, which would require fixture coordination across two repos.
    """
    fake_path = tmp_path / 'fake-worktree'
    fake_path.mkdir()
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()

    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if (
            isinstance(cmd, list)
            and len(cmd) >= 5
            and cmd[0] == 'git'
            and cmd[1] == '-C'
            and cmd[3] == 'rev-parse'
            and cmd[4] == '--show-toplevel'
        ):
            return subprocess.CompletedProcess(cmd, 0, stdout=str(elsewhere) + '\n', stderr='')
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(cmds.subprocess, 'run', fake_run)

    metadata = {'use_worktree': True, 'worktree_path': str(fake_path)}
    err = cmds._resolve_worktree_assertion(metadata)
    assert err is not None
    assert err['error'] == 'worktree_unresolved'
    assert err['reason'] == 'worktree_path_stale'
    assert err['worktree_path'] == str(fake_path)
    assert err['resolved_toplevel'] == str(elsewhere)


# =============================================================================
# cmd_capture / cmd_verify: integration with the assertion
# =============================================================================


def test_cmd_capture_refuses_on_unresolved_worktree(stubbed_invariants, stub_metadata) -> None:
    """``cmd_capture`` surfaces the assertion error verbatim, with plan_id/phase."""
    stub_metadata['use_worktree'] = True
    # No worktree_path → unresolved.
    with PlanContext(plan_id='cap-wt-missing'):
        result = cmds.cmd_capture(_ns(plan_id='cap-wt-missing', phase='5-execute'))
    assert result['status'] == 'error'
    assert result['error'] == 'worktree_unresolved'
    assert result['reason'] == 'worktree_path_missing'
    assert result['plan_id'] == 'cap-wt-missing'
    assert result['phase'] == '5-execute'


def test_cmd_verify_refuses_on_filesystem_missing_worktree(
    stubbed_invariants, stub_metadata, tmp_path: Path
) -> None:
    """``cmd_verify`` refuses when the persisted worktree path no longer exists."""
    ghost = tmp_path / 'gone'
    # First capture with a valid (no-worktree) state so a row exists.
    with PlanContext(plan_id='ver-wt-missing'):
        cap = cmds.cmd_capture(_ns(plan_id='ver-wt-missing', phase='5-execute'))
        assert cap['status'] == 'success'
        # Now flip status metadata to "use worktree, but it's gone".
        stub_metadata['use_worktree'] = True
        stub_metadata['worktree_path'] = str(ghost)
        result = cmds.cmd_verify(_ns(plan_id='ver-wt-missing', phase='5-execute'))
    assert result['status'] == 'error'
    assert result['error'] == 'worktree_unresolved'
    assert result['reason'] == 'worktree_path_not_found'
    assert result['plan_id'] == 'ver-wt-missing'
    assert result['phase'] == '5-execute'


def test_cmd_capture_succeeds_on_main_checkout(stubbed_invariants, stub_metadata) -> None:
    """``use_worktree=false`` path: assertion passes, capture proceeds normally."""
    stub_metadata['use_worktree'] = False
    with PlanContext(plan_id='cap-main'):
        result = cmds.cmd_capture(_ns(plan_id='cap-main', phase='5-execute'))
    assert result['status'] == 'success'
    assert result['phase'] == '5-execute'
    assert result['worktree_applicable'] is False


def test_cmd_capture_succeeds_on_resolved_worktree(
    stubbed_invariants, stub_metadata, git_worktree: Path
) -> None:
    """Valid worktree + ``use_worktree=true`` → assertion passes, capture proceeds."""
    stub_metadata['use_worktree'] = True
    stub_metadata['worktree_path'] = str(git_worktree)
    stubbed_invariants['worktree_sha'] = 'wt-sha'
    stubbed_invariants['worktree_dirty'] = 0
    with PlanContext(plan_id='cap-wt-ok'):
        result = cmds.cmd_capture(_ns(plan_id='cap-wt-ok', phase='5-execute'))
    assert result['status'] == 'success'
    assert result['worktree_applicable'] is True


# =============================================================================
# CLI --strict flag: non-zero exit on worktree_unresolved
# =============================================================================


def _capture_row_for_strict_test(plan_id: str) -> None:
    """Helper: write a minimal handshake row so ``verify`` has something to read.

    Persists directly via ``_handshake_store.upsert_row`` since the goal of
    the strict-flag tests is the exit code on the refusal path, not the
    capture pipeline (which is exercised elsewhere).
    """
    import _handshake_store as store  # type: ignore[import-not-found]

    store.upsert_row(
        plan_id,
        {
            'phase': '5-execute',
            'main_sha': 'abc123',
            'main_dirty': 0,
            'worktree_sha': '',
            'worktree_dirty': '',
            'task_state_hash': 'hash-tasks',
            'qgate_open_count': 0,
            'config_hash': 'hash-cfg',
            'pending_tasks_count': 0,
            'override': False,
            'override_reason': '',
            'worktree_applicable': False,
            'captured_at': '2026-05-07T00:00:00Z',
        },
    )


def _load_phase_handshake_module():
    """Import phase_handshake.py as a module and return the ``main`` callable.

    The script wraps ``main`` with ``@safe_main`` (in
    ``tools-file-ops:file_ops``), which calls ``sys.exit(rc)`` — so invoking
    ``main()`` raises ``SystemExit`` whose ``code`` is the script's exit
    status. Loading via ``importlib`` (rather than re-execing the script as
    ``__main__``) means the module body runs but the ``if __name__ ==
    '__main__'`` guard is skipped, leaving ``main()`` callable from the
    test.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location('phase_handshake_under_test', SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def test_cli_strict_propagates_nonzero_exit_on_worktree_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``verify --strict`` returns non-zero when assertion fails.

    Drives the script's ``main()`` directly (sys.argv injection) instead of
    spawning a subprocess so the in-process monkeypatched
    ``_load_status_metadata`` actually applies. Asserts via
    ``SystemExit.code`` because ``@safe_main`` calls ``sys.exit(rc)``.
    """
    plan_id = 'strict-wt-missing'

    # Force unresolved worktree on metadata read.
    monkeypatch.setattr(
        cmds,
        '_load_status_metadata',
        lambda _pid: {'use_worktree': True},
    )

    with PlanContext(plan_id=plan_id):
        _capture_row_for_strict_test(plan_id)
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'phase_handshake.py',
                'verify',
                '--plan-id',
                plan_id,
                '--phase',
                '5-execute',
                '--strict',
            ],
        )
        main_fn = _load_phase_handshake_module()
        with pytest.raises(SystemExit) as excinfo:
            main_fn()
        assert excinfo.value.code == 1, (
            f'--strict must exit non-zero on worktree_unresolved, got {excinfo.value.code}'
        )


def test_cli_strict_exits_zero_when_worktree_resolves(
    stubbed_invariants, monkeypatch: pytest.MonkeyPatch, git_worktree: Path
) -> None:
    """Counterpart to the unresolved case: clean worktree → exit 0 under --strict.

    Guards against a regression where the strict-mode handler treats every
    non-``ok`` return as failure (which would also reject the resolved
    worktree case if the handler conflated ``status: ok`` with the
    worktree-unresolved error path).

    The ``stubbed_invariants`` fixture pins a deterministic capture/observe
    pair so this test stays coupled to the worktree-assertion contract
    rather than the live invariant registry.
    """
    plan_id = 'strict-wt-ok'

    md_for_capture = {
        'use_worktree': True,
        'worktree_path': str(git_worktree),
    }
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_for_capture)

    with PlanContext(plan_id=plan_id):
        # Capture real invariants (under the stub) so verify finds no drift.
        cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='5-execute'))
        assert cap['status'] == 'success', cap
        monkeypatch.setattr(
            sys,
            'argv',
            [
                'phase_handshake.py',
                'verify',
                '--plan-id',
                plan_id,
                '--phase',
                '5-execute',
                '--strict',
            ],
        )
        main_fn = _load_phase_handshake_module()
        with pytest.raises(SystemExit) as excinfo:
            main_fn()
        assert excinfo.value.code == 0, (
            f'--strict on a resolved worktree must exit 0, got {excinfo.value.code}'
        )
