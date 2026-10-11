#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for integrate_into_main.py — releasing the lock it took, and checking that release.

Contract under test:

* **Release on every exit path after a successful acquire** — a log-fold
  ``OSError`` (creating the destination ``logs/`` or listing the global-logs dir),
  an unexpected exception from the move-back, and an unexpected exception from any
  other work under the lock all release the lock this call took and return a
  non-success payload. A live plan therefore never strands the lock.
* **An interrupt propagates after the release** — a ``KeyboardInterrupt`` or
  ``SystemExit`` from the work under the lock is re-raised, never converted, and
  the lock this call took is released first; a reentrant grant is left alone.
* **A failed release is reported, never folded into success** — a release that
  answers ``status: error``, raises, or reports an action other than ``released``
  turns a success payload into an error carrying ``lock_released: false`` and
  ``release_failure`` (no ``action: integrated``), and leaves an error payload's
  original ``error`` text in place beside the release outcome.

Isolation: an isolated main + worktree tree staged under ``tmp_path``; the real
``merge_lock`` runs where the lock file itself is the claim, against the staged
main through ``PLAN_BASE_DIR``, and a stub stands in where only the release routing
is under test.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module

integrate_into_main = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'integrate_into_main.py', 'integrate_into_main'
)

_PLAN_ID = 'sample-plan'


class _ReleaseScriptedLock:
    """Stub merge_lock whose acquire succeeds and whose release answers a canned outcome."""

    def __init__(self, release_result: dict[str, Any] | None = None, *, release_raises: bool = False) -> None:
        self.release_result = release_result or {'status': 'success', 'action': 'released'}
        self.release_raises = release_raises
        self.released = 0

    def run_acquire(self, args: Namespace) -> dict:
        return {'status': 'success', 'action': 'acquired', 'plan_id': args.plan_id}

    def run_release(self, args: Namespace) -> dict:
        self.released += 1
        if self.release_raises:
            raise OSError('simulated lock-file unlink failure')
        return {**self.release_result, 'plan_id': args.plan_id}


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage main + a worktree holding the plan dir and one global log.

    The DESTINATION resolves through the REAL ``resolve_main_anchored_path`` via
    ``PLAN_BASE_DIR`` at the staged main ``.plan/local``; the SOURCE worktree-path
    seam is stubbed to the staged worktree. No other plan is queued, so the real
    merge_lock admits this plan on its first attempt.
    """
    main = tmp_path / 'main'
    main_local = main / '.plan' / 'local'
    (main_local / 'plans').mkdir(parents=True)

    worktree_path = tmp_path / 'worktrees' / _PLAN_ID
    wt_plan_dir = worktree_path / '.plan' / 'local' / 'plans' / _PLAN_ID
    wt_plan_dir.mkdir(parents=True)
    (wt_plan_dir / 'status.json').write_text('{}\n')
    wt_global_logs = worktree_path / '.plan' / 'local' / 'logs'
    wt_global_logs.mkdir(parents=True)
    (wt_global_logs / 'work.log').write_text('[STATUS] hello\n')

    monkeypatch.chdir(main)
    monkeypatch.setenv('PLAN_BASE_DIR', str(main_local))
    monkeypatch.setattr(integrate_into_main, '_resolve_worktree_path_for_plan', lambda pid: (worktree_path, None))

    return {
        'main_plan_dir': main_local / 'plans' / _PLAN_ID,
        'wt_plan_dir': wt_plan_dir,
        'wt_global_logs': wt_global_logs,
    }


def _use_real_lock(monkeypatch: pytest.MonkeyPatch, name: str) -> Path:
    real_merge_lock = integrate_into_main._load_module_by_path(name, integrate_into_main._MERGE_LOCK_PATH)
    monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: real_merge_lock)
    lock_path: Path = real_merge_lock._resolve_main_lock_path()
    return lock_path


def _use_stub(monkeypatch: pytest.MonkeyPatch, lock: _ReleaseScriptedLock) -> _ReleaseScriptedLock:
    monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: lock)
    return lock


# =============================================================================
# Release on every exit path after the acquire — real merge_lock
# =============================================================================


class TestLockTakenIsReleasedOnEveryExitPath:
    def test_success_path_releases_the_real_lock(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        lock_path = _use_real_lock(monkeypatch, 'merge_lock_real_release_success')

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result
        assert not lock_path.exists()

    def test_fold_destination_mkdir_failure_releases_and_reports_error(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A regular file where the plan dir's ``logs/`` must be created makes the
        fold's ``mkdir`` raise; the lock is still released and nothing moved."""
        env = isolated_env
        lock_path = _use_real_lock(monkeypatch, 'merge_lock_real_release_fold_mkdir')
        (env['wt_plan_dir'] / 'logs').write_text('not a directory\n')

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'error', result
        assert 'integration failed under the merge lock' in result['error'], result
        assert 'lock_released' not in result, result
        assert not lock_path.exists(), 'a fold failure stranded the lock this call took'
        assert (env['wt_plan_dir'] / 'status.json').is_file()
        assert not env['main_plan_dir'].exists()

    def test_global_logs_listing_failure_releases_and_reports_error(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        lock_path = _use_real_lock(monkeypatch, 'merge_lock_real_release_fold_iterdir')
        global_logs = isolated_env['wt_global_logs']
        real_iterdir = Path.iterdir

        def unreadable_global_logs(self: Path) -> Any:
            if self == global_logs:
                raise PermissionError(f'simulated unreadable dir: {self}')
            return real_iterdir(self)

        monkeypatch.setattr(Path, 'iterdir', unreadable_global_logs)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'error', result
        assert 'PermissionError' in result['error'], result
        assert not lock_path.exists(), 'a fold failure stranded the lock this call took'
        assert (isolated_env['wt_plan_dir'] / 'status.json').is_file()

    def test_unexpected_move_back_exception_rolls_back_and_releases(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-``OSError`` escaping the move-back is caught like any move-back
        failure: rolled back to the worktree, lock released, error returned."""
        lock_path = _use_real_lock(monkeypatch, 'merge_lock_real_release_move_back')

        def boom(src: Path, dst: Path) -> None:
            raise RuntimeError('simulated unexpected move-back fault')

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', boom)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'error', result
        assert 'rolled back' in result['error'], result
        assert 'simulated unexpected move-back fault' in result['error'], result
        assert not lock_path.exists()
        assert (isolated_env['wt_plan_dir'] / 'status.json').is_file()

    def test_unexpected_exception_outside_the_move_back_releases(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        lock_path = _use_real_lock(monkeypatch, 'merge_lock_real_release_unexpected')

        def fault(src: Path, dst: Path) -> list[str]:
            raise ValueError('simulated unexpected fold fault')

        monkeypatch.setattr(integrate_into_main, '_fold_global_logs', fault)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'error', result
        assert 'ValueError' in result['error'], result
        assert not lock_path.exists()


# =============================================================================
# An interrupt under the lock propagates after the release
# =============================================================================


_INTERRUPTS = [
    pytest.param(KeyboardInterrupt, id='keyboard-interrupt'),
    pytest.param(SystemExit, id='system-exit'),
]


class TestInterruptUnderTheLock:
    @pytest.mark.parametrize('interrupt', _INTERRUPTS)
    def test_interrupt_from_the_move_back_releases_then_propagates(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch, interrupt: type[BaseException]
    ) -> None:
        """A BaseException that is not an Exception is never turned into a payload,
        yet the lock this call took is released before it leaves the call."""
        lock_path = _use_real_lock(monkeypatch, f'merge_lock_real_release_{interrupt.__name__}')

        def interrupted(src: Path, dst: Path) -> None:
            assert lock_path.is_file(), 'the move-back must run under the lock'
            raise interrupt()

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', interrupted)

        with pytest.raises(interrupt):
            integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert not lock_path.exists(), 'an interrupt under the lock stranded the lock this call took'

    def test_interrupt_leaves_a_reentrant_lock_to_its_holder(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An ``already_held`` grant belongs to the outer holder, so an interrupt
        propagates without a release from this call."""
        lock = _ReleaseScriptedLock()
        monkeypatch.setattr(
            lock, 'run_acquire', lambda args: {'status': 'success', 'action': 'already_held', 'plan_id': args.plan_id}
        )
        _use_stub(monkeypatch, lock)

        def interrupted(src: Path, dst: Path) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', interrupted)

        with pytest.raises(KeyboardInterrupt):
            integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert lock.released == 0


# =============================================================================
# A failed release is reported
# =============================================================================


_RELEASE_OUTCOMES = [
    pytest.param(
        {'status': 'error', 'error': 'simulated unlink refusal'}, False, 'simulated unlink refusal', id='error'
    ),
    pytest.param({'status': 'success', 'action': 'noop'}, False, "'noop'", id='noop'),
    pytest.param(None, True, 'raised', id='raises'),
]


class TestFailedReleaseIsReported:
    @pytest.mark.parametrize(('release_result', 'release_raises', 'named'), _RELEASE_OUTCOMES)
    def test_success_payload_is_downgraded(
        self,
        isolated_env: dict,
        monkeypatch: pytest.MonkeyPatch,
        release_result: dict[str, Any] | None,
        release_raises: bool,
        named: str,
    ) -> None:
        """The plan dir moved, but the release did not prove the lock gone, so the
        caller gets an error naming the release failure — never action integrated."""
        env = isolated_env
        lock = _use_stub(monkeypatch, _ReleaseScriptedLock(release_result, release_raises=release_raises))

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'error', result
        assert 'action' not in result, result
        assert result['lock_released'] is False, result
        assert named in result['release_failure'], result
        assert 'may still be held' in result['error'], result
        assert result['integration_action'] == 'integrated', result
        assert lock.released == 1
        assert (env['main_plan_dir'] / 'status.json').is_file()

    def test_error_payload_keeps_its_original_error(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """A release failure on the rollback path never masks the move-back error."""
        release_error = {'status': 'error', 'error': 'simulated unlink refusal'}
        _use_stub(monkeypatch, _ReleaseScriptedLock(release_error))

        def boom(src: Path, dst: Path) -> None:
            raise OSError('simulated move-back failure')

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', boom)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'error', result
        assert 'simulated move-back failure' in result['error'], result
        assert result['lock_released'] is False, result
        assert 'simulated unlink refusal' in result['release_failure'], result
        assert result['release_result']['status'] == 'error', result

    def test_released_outcome_leaves_success_untouched(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _use_stub(monkeypatch, _ReleaseScriptedLock())

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=_PLAN_ID))

        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result
        assert 'lock_released' not in result, result
