#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for integrate_into_main.py — the atomic finalize move-back script.

Contract under test (solution_outline.md §5):

* **Happy path** — ACQUIRES the merge lock, FOLDS the plan's own global logs into
  the plan dir, MOVES the plan dir back from the worktree to main, and RELEASES the
  lock. The executor is NOT regenerated — on-main executor regeneration is the
  project-level finalize-step-sync-plugin-cache step's responsibility.
* **Idempotent re-run** — an already-integrated plan (plan dir on main, none in the
  worktree) is a no-op success that never acquires the lock.
* **Rollback-on-partial-failure** — a move-back step that raises rolls the plan dir
  BACK into the worktree (authoritative copy never split) and releases the lock.
* **Lock released on every exit path** — including the rollback path.
* **Bounded admission wait, dequeue on expiry** — the acquire forwards a bounded
  ``wait_seconds``; when admission is still blocked once it lapses, the plan is
  dequeued from the merge FIFO queue (the foreign holder's lock left intact) and
  the blocked payload is surfaced with ``dequeued`` reporting the outcome.
* **cwd invariant** — the script never mutates the process cwd.
* **Worktree NOT removed** — the worktree directory survives the call.
* **Executor never touched** — integrate neither moves nor regenerates any
  ``.plan/execute-script.py``; the success payload carries no regen fields.

cwd-independence: integrate resolves its SOURCE
(worktree via ``file_ops.resolve_plan_context`` — the single plan-context
resolver, which owns the ``manage-status get-worktree-path`` shell-out; stubbed
in most cases at the composite ``_resolve_worktree_path_for_plan`` seam, and
driven for real against ``file_ops._query_worktree_path`` in
:class:`TestResolveWorktreePathViaStatusChannel`) and its DESTINATION (main via the
sanctioned ``resolve_main_anchored_path`` resolver, driven REAL through
``PLAN_BASE_DIR``) cwd-independently. The
:class:`TestIntegrateCwdIndependent` regression suite invokes the script from the
**worktree** cwd — the misuse that yields a false ``noop`` — WITHOUT mocking
the DESTINATION resolver, exercising the real path resolution.

Isolation: every test runs
against an isolated tree staged under ``tmp_path`` with cwd pinned to a stable
location; the ``merge_lock`` delegation is stubbed so no real lock file is
contended — the suite never contends for the real ``.plan/`` under ``-n auto``.
"""

from __future__ import annotations

import json
import os
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
from _resolve_project_dir_fixtures import (
    NO_PLAN_SENTINEL,
    patch_query_worktree_path,
)

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'integrate_into_main.py')

integrate_into_main = load_script_module(
    'plan-marshall', 'workflow-integration-git', 'integrate_into_main.py', 'integrate_into_main'
)


# =============================================================================
# Fixtures
# =============================================================================


class _FakeMergeLock:
    """Stub merge_lock module recording acquire/release calls.

    Records the ``set_title_token`` value forwarded on each acquire/release so a
    test can assert integrate suppresses the merge-lock title-token surface during
    the brief, finalize-internal move-back mutex (no spurious ⏳/🔒 glyph).
    """

    def __init__(self, acquire_status: str = 'success') -> None:
        self.acquire_status = acquire_status
        self.acquired = 0
        self.released = 0
        self.acquire_set_title_tokens: list[object] = []
        self.release_set_title_tokens: list[object] = []
        self.acquire_wait_seconds: list[object] = []

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        self.acquire_set_title_tokens.append(getattr(args, 'set_title_token', 'absent'))
        self.acquire_wait_seconds.append(getattr(args, 'wait_seconds', 'absent'))
        if self.acquire_status != 'success':
            return {'status': 'error', 'error_code': 'TIMEOUT', 'plan_id': args.plan_id}
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'acquired'}

    def run_release(self, args: Namespace) -> dict:
        self.released += 1
        self.release_set_title_tokens.append(getattr(args, 'set_title_token', 'absent'))
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'released'}


@pytest.fixture
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated main + worktree layout with the plan dir resident in the
    worktree (the move-in already ran).

    Layout::

        tmp_path/
          main/.plan/local/                       (main destination root)
          worktrees/{plan_id}/.plan/local/plans/{plan_id}/   (worktree-resident plan)
          worktrees/{plan_id}/.plan/local/logs/work.log      (plan's global logs)

    Resolution seams (cwd-independent):

    * **DESTINATION** is resolved by the REAL ``resolve_main_anchored_path`` via
      ``PLAN_BASE_DIR`` pointing at the staged main ``.plan/local`` — NOT mocked.
    * **SOURCE** worktree-path resolution (``_resolve_worktree_path_for_plan``)
      is stubbed to return the staged worktree path — that seam is orthogonal to
      the cwd-independence defect under test.

    Pins cwd to ``main`` by default (the historical finalize move-back path); the
    :class:`TestIntegrateCwdIndependent` suite re-pins cwd to the worktree to
    exercise the misuse that produced the historical false ``noop``.
    """
    plan_id = 'sample-plan'

    main = tmp_path / 'main'
    main_local = main / '.plan' / 'local'
    main_plan_dir = main_local / 'plans' / plan_id
    # main destination does NOT yet hold the plan dir (it is resident in the worktree)
    (main_local / 'plans').mkdir(parents=True)

    worktrees_root = tmp_path / 'worktrees'
    worktree_path = worktrees_root / plan_id
    wt_plan_dir = worktree_path / '.plan' / 'local' / 'plans' / plan_id
    wt_plan_dir.mkdir(parents=True)
    (wt_plan_dir / 'status.json').write_text('{}\n')
    # references.json with NO marketplace script change by default.
    (wt_plan_dir / 'references.json').write_text(json.dumps({'modified_files': ['doc/foo.md']}))
    wt_global_logs = worktree_path / '.plan' / 'local' / 'logs'
    wt_global_logs.mkdir(parents=True)
    (wt_global_logs / 'work.log').write_text('[STATUS] hello\n')

    monkeypatch.chdir(main)

    # DESTINATION: drive the REAL resolve_main_anchored_path at the staged main
    # via PLAN_BASE_DIR (the sanctioned test override). resolve_main_anchored_path
    # returns file_ops.get_base_dir() / subpath, so 'plans/{plan_id}' resolves to
    # main/.plan/local/plans/{plan_id} regardless of cwd.
    monkeypatch.setenv('PLAN_BASE_DIR', str(main_local))

    # SOURCE: stub the worktree-path resolver (orthogonal seam) to the staged
    # worktree path. Mirrors the manage-status get-worktree-path channel.
    monkeypatch.setattr(
        integrate_into_main,
        '_resolve_worktree_path_for_plan',
        lambda pid: (worktree_path, None),
    )

    fake_lock = _FakeMergeLock()
    monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: fake_lock)

    return {
        'plan_id': plan_id,
        'main': main,
        'main_plan_dir': main_plan_dir,
        'worktrees_root': worktrees_root,
        'worktree_path': worktree_path,
        'wt_plan_dir': wt_plan_dir,
        'wt_global_logs': wt_global_logs,
        'fake_lock': fake_lock,
    }


# =============================================================================
# Happy path
# =============================================================================


# =============================================================================
# cwd-independent SOURCE resolution — structural probe + channel/probe fallback
# (the moved-in-from-main case)
# =============================================================================


def _stage_worktree_at_canonical_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plan_id: str) -> Path:
    """Stage a worktree at the canonical ``get_worktree_root() / {plan_id}`` layout.

    Drives the DESTINATION resolver (``resolve_main_anchored_path``) via
    ``PLAN_BASE_DIR`` pointing at a staged main ``.plan/local``, AND pins the SOURCE
    probe's ``get_worktree_root()`` seam at ``{main}/worktrees`` so the worktree
    resolves deterministically regardless of the autouse ``PLAN_BASE_DIR`` sandbox or
    the process cwd. Materializes
    ``{root}/{plan_id}/.plan/local/plans/{plan_id}/status.json`` — exactly the
    on-disk shape :func:`_structural_worktree_probe` keys on. Returns the staged
    worktree path (``get_worktree_root() / plan_id``).
    """
    main_local = tmp_path / 'main' / '.plan' / 'local'
    main_local.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(main_local))

    worktree_root = main_local / 'worktrees'
    # Pin the SOURCE probe's worktree-root seam directly (rather than relying on
    # the env-var-derived get_base_dir(), which the autouse sandbox also sets):
    # the probe calls the module-bound ``get_worktree_root`` in integrate_into_main.
    monkeypatch.setattr(integrate_into_main, 'get_worktree_root', lambda: worktree_root)

    worktree_path = worktree_root / plan_id
    status_json = worktree_path / '.plan' / 'local' / 'plans' / plan_id / 'status.json'
    status_json.parent.mkdir(parents=True)
    status_json.write_text('{}\n')
    return worktree_path


# =============================================================================
# Happy path
# =============================================================================


class TestIntegrateHappyPath:
    def test_moves_plan_dir_back_folds_logs_and_releases_lock(self, isolated_env: dict) -> None:
        env = isolated_env
        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'success', result
        assert result['action'] == 'integrated'

        # Plan dir is now resident on main as a real directory...
        assert env['main_plan_dir'].is_dir()
        assert not env['main_plan_dir'].is_symlink()
        assert (env['main_plan_dir'] / 'status.json').is_file()
        # ...and GONE from the worktree (moved, not copied).
        assert not env['wt_plan_dir'].exists()

        # The plan's global logs were folded into the plan dir's logs/.
        folded = env['main_plan_dir'] / 'logs' / 'work.log'
        assert folded.is_file()
        assert 'work.log' in result['folded_logs']

        # The lock was acquired AND released.
        assert env['fake_lock'].acquired == 1
        assert env['fake_lock'].released == 1

        # The success payload carries NO regen fields — integrate does not
        # regenerate the executor.
        assert 'regenerated' not in result
        assert 'regen_detail' not in result

    def test_does_not_change_cwd(self, isolated_env: dict) -> None:
        env = isolated_env
        cwd_before = os.getcwd()
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert os.getcwd() == cwd_before

    def test_does_not_remove_worktree(self, isolated_env: dict) -> None:
        env = isolated_env
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        # The worktree directory itself survives — branch-cleanup owns removal.
        assert env['worktree_path'].is_dir()

    def test_executor_never_touched_by_integrate(self, isolated_env: dict) -> None:
        """Integrate neither moves nor regenerates any executor.
        Stage both a main-resident executor and a worktree-bound one, and assert
        both are left byte-for-byte untouched across the move-back — integrate has
        no executor responsibility at all.
        """
        env = isolated_env
        # Stage a main-resident executor (it must stay present and unchanged)...
        main_executor = env['main'] / '.plan' / 'execute-script.py'
        main_executor.write_text('# main executor — must stay untouched\n')
        # ...and a worktree-bound one (it must NOT travel to main).
        wt_executor = env['worktree_path'] / '.plan' / 'execute-script.py'
        wt_executor.write_text('# worktree-bound executor — MUST NOT reach main\n')

        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        # Main's executor is present and byte-for-byte unchanged (never regenerated).
        assert main_executor.read_text() == '# main executor — must stay untouched\n'
        # The worktree-bound executor is left where it was (worktree removal handles it),
        # never file-moved onto a fresh main slot.
        assert wt_executor.is_file()


# =============================================================================
# Merge-lock title-token suppression
# =============================================================================


class TestIntegrateSuppressesMergeLockTitleToken:
    """The move-back merge lock is a brief, finalize-internal mutex — flashing a
    ⏳/🔒 glyph into the terminal title is spurious noise. integrate forwards
    ``set_title_token=False`` on BOTH the acquire and the release so no merge-lock
    glyph reaches the title during integration."""

    def test_acquire_forwards_set_title_token_false(self, isolated_env: dict) -> None:
        env = isolated_env
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        # The single acquire forwarded set_title_token=False (not absent, not True).
        assert env['fake_lock'].acquire_set_title_tokens == [False]

    def test_release_forwards_set_title_token_false(self, isolated_env: dict) -> None:
        env = isolated_env
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        # The single release forwarded set_title_token=False (mirrors the acquire).
        assert env['fake_lock'].release_set_title_tokens == [False]

    def test_rollback_release_also_forwards_set_title_token_false(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The release on the rollback (move-back-failure) exit path also forwards
        ``set_title_token=False`` — every release path mirrors the suppressed
        acquire so a crashed move-back never leaves a clear targeting an unset token."""
        env = isolated_env

        def boom(src: Path, dst: Path) -> None:
            raise OSError('simulated move-back failure')

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', boom)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert result['status'] == 'error'
        assert env['fake_lock'].acquire_set_title_tokens == [False]
        assert env['fake_lock'].release_set_title_tokens == [False]


# =============================================================================
# cwd-independence regression
# =============================================================================


class TestIntegrateCwdIndependent:
    """Regression suite for the false-``noop``-from-worktree-cwd defect.

    The historical bug resolved both SOURCE and DESTINATION cwd-relatively
    (``get_worktree_root()`` / ``get_plan_dir()``), so invoking integrate from the
    worktree cwd resolved the DESTINATION inside the worktree, found the plan dir
    "already there", and returned a false ``action: noop`` — the move-back never
    happened. These tests pin cwd to the WORKTREE and assert an actual move,
    WITHOUT mocking the DESTINATION resolver (the real ``resolve_main_anchored_path``
    runs, driven through ``PLAN_BASE_DIR``).
    """

    def test_move_back_from_worktree_cwd_is_not_noop(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        env = isolated_env
        # Re-pin cwd to the WORKTREE — the misuse that triggered the false noop.
        monkeypatch.chdir(env['worktree_path'])

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        # An ACTUAL move-back, never noop — the DESTINATION resolved to the staged
        # main via the REAL resolver despite cwd being the worktree.
        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result
        # Plan dir now resident at MAIN (not inside the worktree)...
        assert env['main_plan_dir'].is_dir()
        assert (env['main_plan_dir'] / 'status.json').is_file()
        # ...and ABSENT from the worktree.
        assert not env['wt_plan_dir'].exists()

    def test_destination_resolver_is_real_not_mocked(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """The DESTINATION resolution must run the real resolve_main_anchored_path.

        Guard against a regression where the test stubs the resolver and so cannot
        catch the cwd-dependence defect: assert the resolved main_plan_dir lands
        exactly under the PLAN_BASE_DIR-staged main, computed by the real resolver.
        """
        env = isolated_env
        monkeypatch.chdir(env['worktree_path'])

        # Sanity: the real resolver targets the staged main, cwd notwithstanding.
        resolved = integrate_into_main.resolve_main_anchored_path(f'plans/{env["plan_id"]}')
        assert resolved == env['main_plan_dir']

        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert env['main_plan_dir'].is_dir()


# =============================================================================
# Idempotent re-run
# =============================================================================


class TestIntegrateIdempotent:
    def test_rerun_is_noop_success_without_acquiring_lock(self, isolated_env: dict) -> None:
        env = isolated_env
        first = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert first['status'] == 'success'
        assert first['action'] == 'integrated'

        # A re-run observes the plan dir already on main (and gone from the worktree)
        # and short-circuits WITHOUT acquiring the lock.
        acquired_before = env['fake_lock'].acquired
        second = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert second['status'] == 'success'
        assert second['action'] == 'noop'
        assert env['fake_lock'].acquired == acquired_before  # no new acquire


# =============================================================================
# Rollback-on-partial-failure
# =============================================================================


class TestIntegrateRollback:
    def test_move_back_failure_rolls_back_to_worktree_and_releases_lock(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = isolated_env

        def boom(src: Path, dst: Path) -> None:
            raise OSError('simulated move-back failure')

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', boom)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'error', result
        assert 'rolled back' in result['error']

        # Plan dir is still WHOLLY in the worktree (rolled back / never moved).
        assert env['wt_plan_dir'].is_dir()
        assert (env['wt_plan_dir'] / 'status.json').is_file()
        assert not env['main_plan_dir'].exists()

        # The lock was released even on the rollback path.
        assert env['fake_lock'].released == 1


# =============================================================================
# Release ownership — a lock the same plan already held stays held
# =============================================================================


class _AlreadyHeldMergeLock(_FakeMergeLock):
    """Stub whose acquire reports the reentrant ``already_held`` grant."""

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        self.acquire_set_title_tokens.append(getattr(args, 'set_title_token', 'absent'))
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'already_held'}


class TestIntegrateLeavesSelfHeldLockWithItsHolder:
    """integrate releases only a lock it took itself.

    branch-cleanup holds the merge lock under the plan id across the merge window
    and calls integrate inside it. integrate's acquire is then a reentrant
    ``already_held`` grant, and releasing on that grant would drop the lock out
    from under its holder mid-window.
    """

    def test_lock_held_by_the_same_plan_is_still_held_after_integrate(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Real merge_lock: a lock pre-acquired by the plan survives integrate."""
        env = isolated_env
        real_merge_lock = integrate_into_main._load_module_by_path(
            'merge_lock_real_under_integrate_core', integrate_into_main._MERGE_LOCK_PATH
        )
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: real_merge_lock)
        # A live holder: the holder's plan dir exists on main, so the reentrant
        # grant — not a stale reclaim — is what answers integrate's acquire.
        (env['main'] / '.plan' / 'local' / 'plans' / env['plan_id']).mkdir(parents=True, exist_ok=True)
        lock_path = real_merge_lock._resolve_main_lock_path()

        held = real_merge_lock.run_acquire(Namespace(plan_id=env['plan_id'], set_title_token=False))
        assert held['action'] == 'acquired', held

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result
        assert lock_path.is_file(), 'integrate released a lock it did not take'
        assert lock_path.read_text(encoding='utf-8').strip() == env['plan_id']

    def test_already_held_grant_issues_no_release(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """On the success path an ``already_held`` grant releases nothing."""
        env = isolated_env
        held_lock = _AlreadyHeldMergeLock()
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: held_lock)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'success', result
        assert held_lock.acquired == 1
        assert held_lock.released == 0

    def test_already_held_grant_issues_no_release_on_rollback(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On the rollback path an ``already_held`` grant releases nothing either."""
        env = isolated_env
        held_lock = _AlreadyHeldMergeLock()
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: held_lock)

        def boom(src: Path, dst: Path) -> None:
            raise OSError('simulated move-back failure')

        monkeypatch.setattr(integrate_into_main, '_move_back_dir', boom)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'error', result
        assert held_lock.released == 0


# =============================================================================
# Bounded admission wait — dequeue on expiry
# =============================================================================


class _BlockedMergeLock(_FakeMergeLock):
    """Stub whose acquire stays blocked past its bound and whose release can fail."""

    def __init__(self, release_raises: bool = False) -> None:
        super().__init__()
        self.release_raises = release_raises

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        self.acquire_wait_seconds.append(getattr(args, 'wait_seconds', 'absent'))
        return {
            'status': 'blocked',
            'plan_id': args.plan_id,
            'admission': 'blocked',
            'blocked_reason': 'lock_held_by_live_holder',
            'blocking_plan_id': 'foreign-plan',
            'timed_out': True,
            'waited_seconds': 0,
        }

    def run_release(self, args: Namespace) -> dict:
        self.released += 1
        if self.release_raises:
            raise OSError('simulated dequeue failure')
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'noop'}


class TestIntegrateBoundedAdmissionWait:
    """The move-back acquire waits a bounded time, and a plan that gives up is dequeued.

    The acquire FIFO-enqueues the plan and only a release dequeues it. A blocked
    integrate that returned without dequeuing left its entry queued for good — no
    finalize call site retries the integrate result — so a live worktree could
    wedge every plan queued behind it.
    """

    def test_acquire_forwards_the_bounded_wait(self, isolated_env: dict) -> None:
        env = isolated_env
        integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert env['fake_lock'].acquire_wait_seconds == [integrate_into_main._MOVE_BACK_ACQUIRE_WAIT_SECONDS]

    def test_bound_sits_below_the_merge_lock_ceiling(self) -> None:
        real_merge_lock = integrate_into_main._load_module_by_path(
            'merge_lock_real_under_integrate_core_ceiling', integrate_into_main._MERGE_LOCK_PATH
        )
        assert 0 < integrate_into_main._MOVE_BACK_ACQUIRE_WAIT_SECONDS <= real_merge_lock._ACQUIRE_WAIT_CEILING_SECONDS

    def test_foreign_holder_blocks_then_plan_is_dequeued(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Real merge_lock: a foreign live holder outlasts the bound.

        integrate surfaces ``blocked`` with ``timed_out``, its own FIFO entry is
        gone afterwards, the foreign lock is untouched, and the plan dir never
        left the worktree.
        """
        env = isolated_env
        real_merge_lock = integrate_into_main._load_module_by_path(
            'merge_lock_real_under_integrate_core_blocked', integrate_into_main._MERGE_LOCK_PATH
        )
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: real_merge_lock)
        monkeypatch.setattr(integrate_into_main, '_MOVE_BACK_ACQUIRE_WAIT_SECONDS', 0.05)

        # A live foreign holder: its plan dir exists on main, so it is neither
        # reclaimed as stale nor pruned from the FIFO queue.
        foreign_plan_id = 'foreign-plan'
        foreign_plan_dir = env['main'] / '.plan' / 'local' / 'plans' / foreign_plan_id
        foreign_plan_dir.mkdir(parents=True)
        (foreign_plan_dir / 'status.json').write_text('{}\n')
        held = real_merge_lock.run_acquire(Namespace(plan_id=foreign_plan_id, set_title_token=False))
        assert held['action'] == 'acquired', held
        lock_path = real_merge_lock._resolve_main_lock_path()

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        # (a) blocked once the bound lapsed, and the dequeue is reported.
        assert result['status'] == 'blocked', result
        assert result['timed_out'] is True, result
        assert result['blocking_plan_id'] == foreign_plan_id, result
        assert result['dequeued'] is True, result
        # (b) the plan's own FIFO entry is gone; the foreign holder's is not.
        queued = [entry['plan_id'] for entry in real_merge_lock._queue_waiting(real_merge_lock._read_store())]
        assert env['plan_id'] not in queued, queued
        assert foreign_plan_id in queued, queued
        # (c) the foreign holder still holds the lock.
        assert lock_path.is_file()
        assert lock_path.read_text(encoding='utf-8').strip() == foreign_plan_id
        # (d) nothing moved: the plan dir is still wholly in the worktree.
        assert (env['wt_plan_dir'] / 'status.json').is_file()
        assert not env['main_plan_dir'].exists()

    def test_failed_dequeue_is_reported_not_masked(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        """A dequeue that raises still surfaces the blocked payload, with ``dequeued: false``."""
        env = isolated_env
        blocked_lock = _BlockedMergeLock(release_raises=True)
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: blocked_lock)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'blocked', result
        assert result['dequeued'] is False, result
        assert blocked_lock.released == 1
        assert (env['wt_plan_dir'] / 'status.json').is_file()

    def test_successful_dequeue_is_reported(self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        env = isolated_env
        blocked_lock = _BlockedMergeLock()
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: blocked_lock)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'blocked', result
        assert result['dequeued'] is True, result
        assert blocked_lock.released == 1

    def test_acquire_error_is_surfaced_without_a_dequeue(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An acquire ``status: error`` never enqueued anything, so nothing is released."""
        env = isolated_env
        error_lock = _FakeMergeLock(acquire_status='error')
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: error_lock)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'error', result
        assert 'dequeued' not in result
        assert error_lock.released == 0
