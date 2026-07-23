#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
from conftest import get_script_path

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
        'unfinished_tasks_count': 1,
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
        ('unfinished_tasks_count', always, make_capture('unfinished_tasks_count')),
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
    """``use_worktree=true`` + missing ``worktree_path`` → unresolved.

    Default ``phase=None`` is the fail-closed path: with no boundary phase to
    confirm a pre-materialization planning phase, an empty path refuses.
    """
    err = cmds._resolve_worktree_assertion({'use_worktree': True})
    assert err is not None
    assert err['status'] == 'error'
    assert err['error'] == 'worktree_unresolved'
    assert err['reason'] == 'worktree_path_missing'


def test_assertion_fails_when_worktree_path_empty() -> None:
    """Empty-string ``worktree_path`` is the same refusal as missing (phase=None)."""
    err = cmds._resolve_worktree_assertion({'use_worktree': True, 'worktree_path': '   '})
    assert err is not None
    assert err['error'] == 'worktree_unresolved'
    assert err['reason'] == 'worktree_path_missing'


@pytest.mark.parametrize('phase', ['1-init', '2-refine', '3-outline', '4-plan'])
def test_assertion_passes_when_path_empty_at_planning_phase(phase: str) -> None:
    """Regression (PR #580): empty path is the legitimate pre-materialization
    state for the on-main planning phases; the assertion must pass there so a
    worktree-routed plan can capture handshake invariants before phase-5."""
    assert cmds._resolve_worktree_assertion({'use_worktree': True}, phase) is None
    assert cmds._resolve_worktree_assertion({'use_worktree': True, 'worktree_path': ''}, phase) is None


@pytest.mark.parametrize('phase', ['5-execute', '6-finalize'])
def test_assertion_fails_when_path_empty_post_materialization(phase: str) -> None:
    """Phase-5 onward the worktree MUST be materialized: empty path → unresolved."""
    err = cmds._resolve_worktree_assertion({'use_worktree': True}, phase)
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


def test_assertion_fails_when_path_is_not_a_git_worktree(outside_repo_dir: Path) -> None:
    """Existing dir but ``git rev-parse`` exits non-zero → refusal."""
    # ``plain`` must be OUTSIDE the repo: pytest's tmp_path now roots under the
    # repo-local --basetemp, where ``git rev-parse`` succeeds (the dir is inside
    # a git worktree), surfacing worktree_path_stale instead of not_a_git_worktree.
    plain = outside_repo_dir / 'not-a-repo'
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


def test_cmd_capture_refuses_on_unresolved_worktree(stubbed_invariants, stub_metadata, plan_context) -> None:
    """``cmd_capture`` surfaces the assertion error verbatim, with plan_id/phase."""
    stub_metadata['use_worktree'] = True
    # No worktree_path → unresolved.
    plan_context.plan_dir_for('cap-wt-missing')
    result = cmds.cmd_capture(_ns(plan_id='cap-wt-missing', phase='5-execute'))
    assert result['status'] == 'error'
    assert result['error'] == 'worktree_unresolved'
    assert result['reason'] == 'worktree_path_missing'
    assert result['plan_id'] == 'cap-wt-missing'
    assert result['phase'] == '5-execute'


def test_cmd_verify_refuses_on_filesystem_missing_worktree(
    stubbed_invariants, stub_metadata, tmp_path: Path, plan_context
) -> None:
    """``cmd_verify`` refuses when the persisted worktree path no longer exists."""
    ghost = tmp_path / 'gone'
    # First capture with a valid (no-worktree) state so a row exists.
    plan_context.plan_dir_for('ver-wt-missing')
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


def test_cmd_capture_succeeds_at_planning_phase_before_materialization(
    stubbed_invariants, stub_metadata, plan_context
) -> None:
    """Regression (PR #580): a worktree-routed plan captures the 1-init handshake
    while ``worktree_path`` is still empty (worktree materializes at phase-5).

    Before the phase-gating fix ``cmd_capture`` refused here with
    ``worktree_unresolved`` / ``worktree_path_missing``, blocking the planning
    drift gate for every worktree plan in phases 1-4.
    """
    stub_metadata['use_worktree'] = True
    # No worktree_path key — exactly the metadata phase-1-init persists.
    plan_context.plan_dir_for('cap-wt-pending')
    result = cmds.cmd_capture(_ns(plan_id='cap-wt-pending', phase='1-init'))
    assert result['status'] == 'success'
    assert result['phase'] == '1-init'
    # Pre-materialization: worktree_path is empty, so the worktree-state
    # invariants are not captured. This is the observable contract that the
    # unified materialization predicate exposes in place of the dropped
    # applicability column.
    assert 'worktree_sha' not in result['invariants']


def test_cmd_capture_succeeds_on_main_checkout(stubbed_invariants, stub_metadata, plan_context) -> None:
    """``use_worktree=false`` path: assertion passes, capture proceeds normally."""
    stub_metadata['use_worktree'] = False
    plan_context.plan_dir_for('cap-main')
    result = cmds.cmd_capture(_ns(plan_id='cap-main', phase='5-execute'))
    assert result['status'] == 'success'
    assert result['phase'] == '5-execute'
    # Main-checkout plan: no worktree_path, so the worktree-state invariants
    # are absent from the captured output.
    assert 'worktree_sha' not in result['invariants']


def test_cmd_capture_succeeds_on_resolved_worktree(
    stubbed_invariants, stub_metadata, git_worktree: Path, plan_context
) -> None:
    """Valid worktree + ``use_worktree=true`` → assertion passes, capture proceeds."""
    stub_metadata['use_worktree'] = True
    stub_metadata['worktree_path'] = str(git_worktree)
    stubbed_invariants['worktree_sha'] = 'wt-sha'
    stubbed_invariants['worktree_dirty'] = 0
    plan_context.plan_dir_for('cap-wt-ok')
    result = cmds.cmd_capture(_ns(plan_id='cap-wt-ok', phase='5-execute'))
    assert result['status'] == 'success'
    # Resolved worktree: the worktree-state invariants ARE captured and appear
    # in the output. This is the observable contract the unified materialization
    # predicate exposes in place of the dropped applicability column.
    assert result['invariants']['worktree_sha'] == 'wt-sha'


# =============================================================================
# CLI --strict flag: non-zero exit on worktree_unresolved
# =============================================================================


def _capture_row_for_strict_test(plan_id: str) -> None:
    """Helper: write a minimal handshake row so ``verify`` has something to read.

    Persists directly via ``_handshake_store.upsert_row`` since the goal of
    the strict-flag tests is the exit code on the refusal path, not the
    capture pipeline (which is exercised elsewhere).
    """
    import _handshake_store as store

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
            'unfinished_tasks_count': 0,
            'override': False,
            'override_reason': '',
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
    monkeypatch: pytest.MonkeyPatch, plan_context,
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

    plan_context.plan_dir_for(plan_id)
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


# =============================================================================
# Original strict-resolves test (unchanged behavior)
# =============================================================================


def test_cli_strict_exits_zero_when_worktree_resolves(
    stubbed_invariants, monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
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

    plan_context.plan_dir_for(plan_id)
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


# =============================================================================
# Layer-D enforcement: main_dirty_files / main_checkout_dirtied_during_plan
# =============================================================================
#
# Companion to ``_check_main_dirty_drift`` in ``_handshake_commands.py`` and
# ``_capture_main_dirty_files`` / ``_main_dirty_drift_diff`` in
# ``_invariants.py``. The check raises
# ``MainCheckoutDirtiedDuringPlan`` and ``cmd_verify`` translates the
# exception into the structured ``error: main_checkout_dirtied_during_plan``
# payload. Origin: deliverable D2 of plan ``lesson-2026-05-08-08-001``.
#
# The five scenarios below exercise the contract end-to-end through
# ``cmd_capture`` / ``cmd_verify``:
#
#   (a) clean baseline + clean live  → strict verify succeeds
#   (b) baseline subset of live      → strict verify fails with payload
#       listing the offending paths
#   (c) ``use_worktree=false`` plan  → invariant gated off (no error)
#   (d) ``.plan/`` paths in live set → filtered, NOT a drift signal
#   (e) baseline-equal live set      → proper-superset rule yields no error
# =============================================================================


def _patch_main_dirty_files(
    monkeypatch: pytest.MonkeyPatch, sequence: list[list[str] | None]
):
    """Replace ``inv._capture_main_dirty_files`` with a sequence-driven stub.

    Each call returns the next entry from ``sequence`` (cycling on the last
    entry once exhausted, so monotonically extra calls during the same test
    keep returning the most recent value). Returns a small holder object
    exposing ``calls`` so the test can assert how many captures fired.
    """

    class _Holder:
        calls = 0

        @staticmethod
        def stub(_plan_id: str, _metadata: dict, _phase: str):
            idx = min(_Holder.calls, len(sequence) - 1)
            _Holder.calls += 1
            return sequence[idx]

    monkeypatch.setattr(inv, '_capture_main_dirty_files', _Holder.stub)
    return _Holder


def _layer_d_invariants() -> list:
    """Narrowed INVARIANTS list containing only ``main_dirty_files``.

    Capture/verify go through the registry; narrowing keeps the test
    coupled to the layer-D contract instead of every other invariant.

    The capture entry is a thin trampoline that defers to the
    *current* ``inv._capture_main_dirty_files`` attribute at call time
    so monkeypatches applied AFTER this list is constructed still take
    effect (registry tuples cache the function reference at construction
    time, but the trampoline re-resolves the attribute on every call).
    """
    def _trampoline(plan_id, metadata, phase):
        return inv._capture_main_dirty_files(plan_id, metadata, phase)

    return [('main_dirty_files', inv._always, _trampoline)]


def test_layer_d_clean_baseline_and_live_succeeds(
    monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
) -> None:
    """(a) Worktree-routed plan, no dirty paths at either capture → verify ok.

    Uses a planning-phase boundary (``4-plan``) where the layer-D check is
    RETAINED; a clean baseline+live set must still verify ``ok`` there.
    """
    plan_id = 'layer-d-clean'
    md_state = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)
    _patch_main_dirty_files(monkeypatch, [[], []])

    plan_context.plan_dir_for(plan_id)
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='4-plan'))
    assert cap['status'] == 'success', cap
    result = cmds.cmd_verify(_ns(plan_id=plan_id, phase='4-plan'))

    assert result['status'] == 'ok', f'clean baseline+live must verify ok, got {result}'


def test_layer_d_proper_superset_drift_raises_at_planning_boundary(
    monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
) -> None:
    """(b) Worktree plan, live set is a proper superset → structured error.

    The layer-D leak-into-main guard is RETAINED at the planning-phase
    boundaries that still run on main. Verified at ``4-plan``; the relaxation
    at the ``5-execute → 6-finalize`` boundary is pinned by
    ``test_layer_d_relaxed_at_phase_5_boundary`` below.
    """
    plan_id = 'layer-d-drift'
    md_state = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)

    baseline = ['existing.txt']
    live = ['existing.txt', 'leaked-readme.md', 'src/leaked.py']
    _patch_main_dirty_files(monkeypatch, [baseline, live])

    plan_context.plan_dir_for(plan_id)
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='4-plan'))
    assert cap['status'] == 'success', cap
    result = cmds.cmd_verify(_ns(plan_id=plan_id, phase='4-plan'))

    assert result['status'] == 'error'
    assert result['error'] == 'main_checkout_dirtied_during_plan'
    assert result['plan_id'] == plan_id
    assert result['phase'] == '4-plan'
    assert sorted(result['baseline']) == ['existing.txt']
    assert sorted(result['observed']) == ['existing.txt', 'leaked-readme.md', 'src/leaked.py']
    assert sorted(result['newly_dirty']) == ['leaked-readme.md', 'src/leaked.py'], (
        'newly_dirty must list ONLY the paths that appeared between captures, '
        f'got {result["newly_dirty"]}'
    )


def test_layer_d_relaxed_at_phase_5_boundary(
    monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
) -> None:
    """Layer-D leak-into-main guard is RELAXED at the 5-execute → 6-finalize
    boundary under the cwd-pinned move model (Option 5' / ADR-002).

    The SAME proper-superset drift input that raises at ``4-plan`` must verify
    ``ok`` at ``5-execute``: once the worktree is materialized and the
    orchestrator's cwd is pinned to it, plan work lands in the worktree by
    construction, so the leak-into-main guard has nothing to catch.
    """
    plan_id = 'layer-d-relaxed-p5'
    md_state = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)

    baseline = ['existing.txt']
    live = ['existing.txt', 'leaked-readme.md', 'src/leaked.py']
    _patch_main_dirty_files(monkeypatch, [baseline, live])

    plan_context.plan_dir_for(plan_id)
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='5-execute'))
    assert cap['status'] == 'success', cap
    result = cmds.cmd_verify(_ns(plan_id=plan_id, phase='5-execute'))

    assert result['status'] == 'ok', (
        'layer-D drift must be RELAXED at the 5-execute boundary under the '
        f'cwd-pinned move model; got {result}'
    )


def test_layer_d_main_checkout_plan_is_gated_off(
    monkeypatch: pytest.MonkeyPatch, plan_context,
) -> None:
    """(c) ``use_worktree=false`` plan dirties main freely → no drift error.

    Verified at ``4-plan`` so the worktree-routing gate (gate 2) is genuinely
    exercised rather than short-circuited by the phase-5 relaxation (gate 1).
    """
    plan_id = 'layer-d-main-checkout'
    md_state = {'use_worktree': False}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)

    # Even with a wildly different baseline vs live set, the gate must
    # short-circuit because the invariant only fires for worktree-routed plans.
    _patch_main_dirty_files(
        monkeypatch,
        [['baseline.txt'], ['baseline.txt', 'new-leak-1.py', 'new-leak-2.py']],
    )

    plan_context.plan_dir_for(plan_id)
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='4-plan'))
    assert cap['status'] == 'success', cap
    result = cmds.cmd_verify(_ns(plan_id=plan_id, phase='4-plan'))

    assert result['status'] == 'ok', (
        'main-checkout plans must not trip the layer-D drift invariant '
        f'(use_worktree=false gate); got {result}'
    )


def test_layer_d_dot_plan_paths_are_filtered_and_do_not_trip(
    monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
) -> None:
    """(d) ``.plan/`` artifacts in main MUST be filtered before drift check.

    Drives the real ``_capture_main_dirty_files`` (which calls
    :func:`_filter_main_dirty_paths`) by stubbing ``git_dirty_files`` and
    confirming the captured list is empty even though git reports
    ``.plan/`` paths as dirty. Then verify must produce ``status: ok``
    because the filter strips the would-be drift.

    Verified at ``4-plan`` so the filter logic is genuinely exercised rather
    than short-circuited by the phase-5 relaxation.
    """
    plan_id = 'layer-d-dot-plan-filter'
    md_state = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)

    # First capture: nothing dirty.
    # Second capture: only ``.plan/`` paths dirty — must be filtered out.
    sequence = [
        [],
        ['.plan/local/plans/foo/work.log', '.plan/temp/scratch.toon'],
    ]
    counter = [0]

    def _git_dirty_files_stub(_cwd):
        idx = min(counter[0], len(sequence) - 1)
        counter[0] += 1
        return sequence[idx]

    monkeypatch.setattr(inv, 'git_dirty_files', _git_dirty_files_stub)

    plan_context.plan_dir_for(plan_id)
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='4-plan'))
    assert cap['status'] == 'success', cap
    result = cmds.cmd_verify(_ns(plan_id=plan_id, phase='4-plan'))

    assert result['status'] == 'ok', (
        '``.plan/`` paths must be filtered before the drift check fires, '
        f'got {result}'
    )


def test_layer_d_baseline_equal_live_yields_no_drift(
    monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
) -> None:
    """(e) Pre-existing dirty file unchanged across boundaries → no drift.

    Proper-superset rule: identical sets are not a strict superset, so the
    invariant must NOT raise. This guards against the off-by-one error
    where a non-strict-subset comparison would erroneously fire on stable
    pre-existing dirt.
    """
    plan_id = 'layer-d-baseline-equal'
    md_state = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)

    # Same dirty file at both captures — baseline-equal. Verified at ``4-plan``
    # so the proper-superset rule is genuinely exercised rather than
    # short-circuited by the phase-5 relaxation.
    baseline = ['preexisting-dirty.txt']
    live = ['preexisting-dirty.txt']
    _patch_main_dirty_files(monkeypatch, [baseline, live])

    plan_context.plan_dir_for(plan_id)
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='4-plan'))
    assert cap['status'] == 'success', cap
    result = cmds.cmd_verify(_ns(plan_id=plan_id, phase='4-plan'))

    assert result['status'] == 'ok', (
        'baseline-equal main-dirty (identical sets across boundaries) '
        f'must not trigger the proper-superset drift check; got {result}'
    )


def test_cli_strict_propagates_nonzero_exit_on_main_dirty_drift(
    monkeypatch: pytest.MonkeyPatch, git_worktree: Path, plan_context,
) -> None:
    """``verify --strict`` exits non-zero on layer-D drift at a planning boundary.

    Mirrors the strict-flag test for ``worktree_unresolved``: drives
    ``main()`` directly so the in-process monkeypatched metadata loader and
    capture stub apply. Uses
    ``4-plan`` because the layer-D guard is RETAINED at the planning-phase
    boundaries (and relaxed at ``5-execute`` per the move model).
    """
    plan_id = 'strict-layer-d-drift'
    md_state = {'use_worktree': True, 'worktree_path': str(git_worktree)}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md_state)
    narrowed = _layer_d_invariants()
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    monkeypatch.setattr(cmds, 'INVARIANTS', narrowed)

    _patch_main_dirty_files(
        monkeypatch,
        [['existing.txt'], ['existing.txt', 'leaked.md']],
    )

    plan_context.plan_dir_for(plan_id)
    # Capture establishes the baseline row.
    cap = cmds.cmd_capture(_ns(plan_id=plan_id, phase='4-plan'))
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
            '4-plan',
            '--strict',
        ],
    )
    main_fn = _load_phase_handshake_module()
    with pytest.raises(SystemExit) as excinfo:
        main_fn()
    assert excinfo.value.code == 1, (
        '--strict must exit non-zero on main_checkout_dirtied_during_plan, '
        f'got {excinfo.value.code}'
    )
