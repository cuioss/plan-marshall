#!/usr/bin/env python3
"""Tests for integrate_into_main.py — the atomic finalize move-back script.

Contract under test (solution_outline.md §5):

* **Happy path** — ACQUIRES the merge lock, FOLDS the plan's own global logs into
  the plan dir, MOVES the plan dir back from the worktree to main, and RELEASES the
  lock. The executor is NOT regenerated — on-main executor regeneration is the
  project-level finalize-step-sync-plugin-cache step's responsibility (Deliverable 5).
* **Idempotent re-run** — an already-integrated plan (plan dir on main, none in the
  worktree) is a no-op success that never acquires the lock.
* **Rollback-on-partial-failure** — a move-back step that raises rolls the plan dir
  BACK into the worktree (authoritative copy never split) and releases the lock.
* **Lock released on every exit path** — including the rollback path.
* **cwd invariant** — the script never mutates the process cwd.
* **Worktree NOT removed** — the worktree directory survives the call.
* **Executor never touched** — integrate neither moves nor regenerates any
  ``.plan/execute-script.py``; the success payload carries no regen fields.

cwd-independence (this plan, Deliverable 1): integrate resolves its SOURCE
(worktree via ``manage-status get-worktree-path``, stubbed here at the
``_resolve_worktree_path_for_plan`` seam) and its DESTINATION (main via the
sanctioned ``resolve_main_anchored_path`` resolver, driven REAL through
``PLAN_BASE_DIR``) cwd-independently. The
:class:`TestIntegrateCwdIndependent` regression suite invokes the script from the
**worktree** cwd (the misuse that produced the historical false ``noop``) WITHOUT
mocking the DESTINATION resolver, exercising the real path resolution
(related lesson 2026-06-03-13-001).

Isolation (test-isolation lessons 2026-06-02-12-001/002/003): every test runs
against an isolated tree staged under ``tmp_path`` with cwd pinned to a stable
location; the ``merge_lock`` delegation is stubbed so no real lock file is
contended — the suite never contends for the real ``.plan/`` under ``-n auto``.
"""

from __future__ import annotations

import importlib.util
import json
import os
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'integrate_into_main.py')

_spec = importlib.util.spec_from_file_location('integrate_into_main', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
integrate_into_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(integrate_into_main)


# =============================================================================
# Fixtures
# =============================================================================


class _FakeMergeLock:
    """Stub merge_lock module recording acquire/release calls."""

    def __init__(self, acquire_status: str = 'success') -> None:
        self.acquire_status = acquire_status
        self.acquired = 0
        self.released = 0

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        if self.acquire_status != 'success':
            return {'status': 'error', 'error_code': 'TIMEOUT', 'plan_id': args.plan_id}
        return {'status': 'success', 'plan_id': args.plan_id, 'action': 'acquired'}

    def run_release(self, args: Namespace) -> dict:
        self.released += 1
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

    Resolution seams (cwd-independent — Deliverable 1):

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

        # Deliverable 5: the success payload carries NO regen fields — integrate
        # no longer regenerates the executor.
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
        """Deliverable 5: integrate neither moves nor regenerates any executor.
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
# cwd-independence regression (Deliverable 1 — related lesson 2026-06-03-13-001)
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

    def test_move_back_from_worktree_cwd_is_not_noop(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

    def test_destination_resolver_is_real_not_mocked(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
# Lock acquisition failure
# =============================================================================


class TestIntegrateLockFailure:
    def test_acquire_failure_surfaces_and_never_moves_or_releases(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = isolated_env
        failing_lock = _FakeMergeLock(acquire_status='error')
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: failing_lock)

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        assert result['status'] == 'error'
        # No move happened (plan dir still in worktree); no release (nothing held).
        assert env['wt_plan_dir'].is_dir()
        assert not env['main_plan_dir'].exists()
        assert failing_lock.acquired == 1
        assert failing_lock.released == 0


# =============================================================================
# Not-found / missing worktree-resident plan dir
# =============================================================================


class TestIntegrateNotFound:
    def test_missing_worktree_plan_dir_errors_without_acquiring_lock(
        self, isolated_env: dict
    ) -> None:
        env = isolated_env
        import shutil

        shutil.rmtree(env['wt_plan_dir'])

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert result['status'] == 'error'
        assert result.get('error_code') == integrate_into_main.ErrorCode.NOT_FOUND
        # The lock was never acquired (idempotence/not-found guards run first).
        assert env['fake_lock'].acquired == 0

    def test_worktree_resolution_failure_errors_without_acquiring_lock(
        self, isolated_env: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A SOURCE resolution failure (no worktree configured / resolver error)
        surfaces the resolver's error TOON verbatim and never acquires the lock.
        """
        env = isolated_env
        err = integrate_into_main.make_error(
            'No worktree configured for this plan',
            code=integrate_into_main.ErrorCode.NOT_FOUND,
            plan_id=env['plan_id'],
        )
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_for_plan',
            lambda pid: (None, err),
        )

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert result['status'] == 'error'
        assert result.get('error_code') == integrate_into_main.ErrorCode.NOT_FOUND
        assert env['fake_lock'].acquired == 0


# =============================================================================
# Reclaim a status.json-less orphan destination (this plan, Deliverable 3)
# =============================================================================


class TestIntegrateReclaimOrphan:
    """Move-back reclaims a ``status.json``-less orphan slot at the destination.

    A mis-resolved metrics/logging write while the authoritative plan dir was
    worktree-resident can materialize a ``logs/``/``work/``-only residue at main's
    plan-dir slot. That residue lacks the ``status.json`` sentinel, so it is NOT an
    authoritative plan dir and NOT a completed integration. The move-back must:

    * decline to short-circuit as ``noop`` (the idempotence guard keys on an
      AUTHORITATIVE destination, not any directory),
    * absorb the orphan's stale ``logs/``/``work/`` residue into the
      worktree-resident plan dir before the move,
    * remove the emptied orphan slot and move the real plan dir in,

    all WITHOUT error. An AUTHORITATIVE destination (``status.json`` present) is the
    opposite case — it is refused rather than clobbered (covered separately below).

    The cwd-independence resolution seams are unaffected: the DESTINATION is still
    resolved by the REAL ``resolve_main_anchored_path`` via ``PLAN_BASE_DIR`` and the
    SOURCE by the stubbed ``_resolve_worktree_path_for_plan`` — identical to the
    happy-path fixture — so adding orphan coverage does not perturb those seams.
    """

    def test_orphan_logs_only_destination_is_reclaimed_not_noop(self, isolated_env: dict) -> None:
        env = isolated_env
        # Stage a status.json-less orphan at main's slot: a logs/ residue only.
        orphan = env['main_plan_dir']
        (orphan / 'logs').mkdir(parents=True)
        (orphan / 'logs' / 'stray.log').write_text('[STATUS] stray residue\n')
        assert not (orphan / 'status.json').exists()

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        # An ACTUAL reclaiming move-back — NOT a false noop short-circuit.
        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result

        # The real (status.json-bearing) plan dir now resides on main...
        assert env['main_plan_dir'].is_dir()
        assert not env['main_plan_dir'].is_symlink()
        assert (env['main_plan_dir'] / 'status.json').is_file()
        # ...and is GONE from the worktree (moved, not copied).
        assert not env['wt_plan_dir'].exists()

        # The lock was acquired AND released (the reclaim path is a real move-back).
        assert env['fake_lock'].acquired == 1
        assert env['fake_lock'].released == 1

    def test_orphan_residue_is_absorbed_into_moved_plan_dir(self, isolated_env: dict) -> None:
        env = isolated_env
        # Orphan carries both a logs/ and a work/ residue file, neither of which
        # collides with a worktree-resident same-named file.
        orphan = env['main_plan_dir']
        (orphan / 'logs').mkdir(parents=True)
        (orphan / 'logs' / 'stray.log').write_text('[STATUS] orphan log\n')
        (orphan / 'work').mkdir(parents=True)
        (orphan / 'work' / 'scratch.toon').write_text('orphan: work\n')

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result

        # Both orphan residue files were absorbed into the moved plan dir.
        absorbed_log = env['main_plan_dir'] / 'logs' / 'stray.log'
        absorbed_work = env['main_plan_dir'] / 'work' / 'scratch.toon'
        assert absorbed_log.is_file()
        assert absorbed_log.read_text() == '[STATUS] orphan log\n'
        assert absorbed_work.is_file()
        assert absorbed_work.read_text() == 'orphan: work\n'

    def test_worktree_resident_copy_wins_on_residue_collision(self, isolated_env: dict) -> None:
        env = isolated_env
        # The worktree-resident plan dir already has a logs/work.log (from the
        # global-log fold) — give the orphan a same-named log with DIFFERENT bytes.
        orphan = env['main_plan_dir']
        (orphan / 'logs').mkdir(parents=True)
        (orphan / 'logs' / 'work.log').write_text('[STATUS] ORPHAN copy — must NOT win\n')

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))
        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result

        # The worktree-resident (authoritative) copy survives the collision: the
        # folded global log content, not the orphan's bytes.
        folded = env['main_plan_dir'] / 'logs' / 'work.log'
        assert folded.is_file()
        assert folded.read_text() == '[STATUS] hello\n'

    def test_authoritative_destination_is_refused_not_clobbered(self, isolated_env: dict) -> None:
        """An AUTHORITATIVE (status.json-bearing) destination that survives the
        idempotence guard (because the worktree copy is STILL resident) must be
        refused by the move-back rather than clobbered — the rollback path leaves the
        authoritative copy WHOLLY in the worktree.
        """
        env = isolated_env
        # Stage a REAL (status.json-bearing) plan dir at main's slot AS WELL AS the
        # worktree-resident one. The idempotence guard only short-circuits when the
        # worktree copy is ABSENT, so with both present the reclaim/refuse branch of
        # _move_back_dir runs and must refuse the authoritative destination.
        authoritative = env['main_plan_dir']
        authoritative.mkdir(parents=True)
        (authoritative / 'status.json').write_text('{"sentinel": true}\n')

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

        # Refused (not clobbered): an error, rolled back to the worktree.
        assert result['status'] == 'error', result
        assert 'rolled back' in result['error']

        # The authoritative main destination is untouched (its sentinel survives)...
        assert (env['main_plan_dir'] / 'status.json').read_text() == '{"sentinel": true}\n'
        # ...and the worktree-resident copy is still WHOLLY present (never split).
        assert env['wt_plan_dir'].is_dir()
        assert (env['wt_plan_dir'] / 'status.json').is_file()

        # The lock was released even on this refuse/rollback path.
        assert env['fake_lock'].released == 1


# =============================================================================
# cwd-independent SOURCE resolution — structural probe + channel/probe fallback
# (this plan, Deliverable 1 — the moved-in-from-main case)
# =============================================================================


def _stage_worktree_at_canonical_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plan_id: str
) -> Path:
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


class TestStructuralWorktreeProbe:
    """Direct coverage of :func:`_structural_worktree_probe`.

    The probe is the moved-in-from-main fallback: it confirms ``status.json`` at the
    canonical ``get_worktree_root() / {plan_id} / .plan/local/plans/{plan_id}/``
    layout on disk, independent of any ``manage-status`` channel read (which fails on
    main once the plan dir has MOVED into the worktree, ADR-002).
    """

    def test_probe_resolves_when_status_json_present_at_canonical_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_id = 'probe-plan'
        worktree_path = _stage_worktree_at_canonical_root(tmp_path, monkeypatch, plan_id)

        # cwd is irrelevant to the probe — pin it somewhere unrelated to prove it.
        monkeypatch.chdir(tmp_path)

        probed = integrate_into_main._structural_worktree_probe(plan_id)
        assert probed == worktree_path

    def test_probe_returns_none_when_status_json_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_id = 'probe-plan'
        worktree_path = _stage_worktree_at_canonical_root(tmp_path, monkeypatch, plan_id)
        # Remove the sentinel: a worktree dir without status.json is NOT resolvable.
        (worktree_path / '.plan' / 'local' / 'plans' / plan_id / 'status.json').unlink()

        assert integrate_into_main._structural_worktree_probe(plan_id) is None

    def test_probe_returns_none_when_worktree_root_unresolvable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Outside a git repo / with no base dir, ``get_worktree_root`` raises
        ``RuntimeError`` — the probe swallows it and yields ``None`` rather than
        propagating (there is simply no worktree root to probe)."""

        def boom() -> Path:
            raise RuntimeError('no base dir resolvable')

        monkeypatch.setattr(integrate_into_main, 'get_worktree_root', boom)
        assert integrate_into_main._structural_worktree_probe('any-plan') is None


class TestResolveWorktreePathFallback:
    """Coverage of :func:`_resolve_worktree_path_for_plan`'s channel→probe ladder.

    The function tries the canonical ``manage-status get-worktree-path`` channel
    first, then the structural probe ONLY for a recoverable
    channel-could-not-resolve error (the moved-in-from-main case). A critical
    infrastructure failure short-circuits verbatim without consulting the probe.
    """

    def test_channel_success_short_circuits_without_probe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_id = 'chan-plan'
        channel_path = Path('/staged/worktrees') / plan_id
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_via_status_channel',
            lambda pid: (channel_path, None),
        )

        # If the channel resolves, the probe must NOT be consulted at all.
        def fail_probe(pid: str) -> Path | None:
            raise AssertionError('probe must not run when the channel resolves')

        monkeypatch.setattr(integrate_into_main, '_structural_worktree_probe', fail_probe)

        path, err = integrate_into_main._resolve_worktree_path_for_plan(plan_id)
        assert err is None
        assert path == channel_path

    def test_recoverable_channel_error_falls_through_to_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The moved-in-from-main case: the channel cannot read main's now-absent
        status.json (a recoverable 'no worktree configured' NOT_FOUND), and the
        structural probe rescues it by confirming status.json in the worktree."""
        plan_id = 'moved-in-plan'
        worktree_path = _stage_worktree_at_canonical_root(tmp_path, monkeypatch, plan_id)

        recoverable = integrate_into_main.make_error(
            'No worktree configured for this plan — '
            'status.metadata.use_worktree is false or worktree_path is unset',
            code=integrate_into_main.ErrorCode.NOT_FOUND,
            plan_id=plan_id,
        )
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_via_status_channel',
            lambda pid: (None, recoverable),
        )

        path, err = integrate_into_main._resolve_worktree_path_for_plan(plan_id)
        assert err is None, err
        assert path == worktree_path

    def test_critical_channel_error_surfaces_verbatim_without_probe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A critical infrastructure failure (e.g. executor missing) is NOT a
        recoverable channel-could-not-resolve case — it surfaces verbatim and the
        structural probe is never consulted."""
        plan_id = 'crit-plan'
        critical = integrate_into_main.make_error(
            'plan-marshall executor not available (.plan/execute-script.py missing)',
            code=integrate_into_main.ErrorCode.NOT_FOUND,
            plan_id=plan_id,
        )
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_via_status_channel',
            lambda pid: (None, critical),
        )

        def fail_probe(pid: str) -> Path | None:
            raise AssertionError('probe must not run for a critical channel error')

        monkeypatch.setattr(integrate_into_main, '_structural_worktree_probe', fail_probe)

        path, err = integrate_into_main._resolve_worktree_path_for_plan(plan_id)
        assert path is None
        assert err is critical

    def test_recoverable_channel_error_with_probe_miss_surfaces_channel_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Recoverable channel error AND the probe also misses (genuinely no
        worktree / plan absent): the channel's NOT_FOUND error is surfaced."""
        plan_id = 'absent-plan'
        recoverable = integrate_into_main.make_error(
            'No worktree configured for this plan',
            code=integrate_into_main.ErrorCode.NOT_FOUND,
            plan_id=plan_id,
        )
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_via_status_channel',
            lambda pid: (None, recoverable),
        )
        monkeypatch.setattr(
            integrate_into_main, '_structural_worktree_probe', lambda pid: None
        )

        path, err = integrate_into_main._resolve_worktree_path_for_plan(plan_id)
        assert path is None
        assert err is recoverable


class TestIntegrateFromMainViaStructuralProbe:
    """End-to-end move-back driven from MAIN cwd through the REAL fallback ladder.

    This is the moved-in-from-main case at the script level: the channel
    (``_resolve_worktree_path_via_status_channel``) returns a recoverable
    NOT_FOUND (main's status.json has MOVED into the worktree), and the REAL
    structural probe resolves the SOURCE from the canonical worktree layout —
    WITHOUT stubbing ``_resolve_worktree_path_for_plan`` wholesale. The DESTINATION
    is the REAL ``resolve_main_anchored_path`` via ``PLAN_BASE_DIR``. cwd is pinned
    to MAIN (not the worktree), exactly the invocation the fallback makes correct.
    """

    def _build_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> dict:
        plan_id = 'main-probe-plan'

        # Stage main + the worktree at the canonical get_worktree_root()/{plan_id}
        # layout so the REAL structural probe can resolve the SOURCE.
        worktree_path = _stage_worktree_at_canonical_root(tmp_path, monkeypatch, plan_id)
        main_local = tmp_path / 'main' / '.plan' / 'local'
        main_plan_dir = main_local / 'plans' / plan_id
        (main_local / 'plans').mkdir(parents=True, exist_ok=True)

        wt_plan_dir = worktree_path / '.plan' / 'local' / 'plans' / plan_id
        (wt_plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['doc/foo.md']})
        )
        wt_global_logs = worktree_path / '.plan' / 'local' / 'logs'
        wt_global_logs.mkdir(parents=True)
        (wt_global_logs / 'work.log').write_text('[STATUS] hello\n')

        # cwd is MAIN — the moved-in-from-main invocation. (PLAN_BASE_DIR, not cwd,
        # drives resolution, but pinning cwd to main proves cwd-independence.)
        monkeypatch.chdir(tmp_path / 'main')

        # SOURCE channel returns a recoverable NOT_FOUND (main's status.json moved
        # into the worktree); the REAL structural probe must rescue it.
        recoverable = integrate_into_main.make_error(
            'No worktree configured for this plan — '
            'status.metadata.use_worktree is false or worktree_path is unset',
            code=integrate_into_main.ErrorCode.NOT_FOUND,
            plan_id=plan_id,
        )
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_via_status_channel',
            lambda pid: (None, recoverable),
        )

        fake_lock = _FakeMergeLock()
        monkeypatch.setattr(integrate_into_main, '_load_merge_lock', lambda: fake_lock)

        return {
            'plan_id': plan_id,
            'main_plan_dir': main_plan_dir,
            'worktree_path': worktree_path,
            'wt_plan_dir': wt_plan_dir,
            'fake_lock': fake_lock,
        }

    def test_move_back_from_main_resolves_source_via_probe_and_integrates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = self._build_env(tmp_path, monkeypatch)

        result = integrate_into_main.run_integrate_into_main(
            Namespace(plan_id=env['plan_id'])
        )

        # An ACTUAL move-back driven from main cwd — the structural probe resolved
        # the SOURCE worktree from status.json, never a false noop / NOT_FOUND.
        assert result['status'] == 'success', result
        assert result['action'] == 'integrated', result

        # Plan dir now resident at MAIN...
        assert env['main_plan_dir'].is_dir()
        assert (env['main_plan_dir'] / 'status.json').is_file()
        # ...and GONE from the worktree (moved, not copied).
        assert not env['wt_plan_dir'].exists()

        # The folded global log travelled to the plan dir.
        assert (env['main_plan_dir'] / 'logs' / 'work.log').is_file()
        assert 'work.log' in result['folded_logs']

        # Lock acquired AND released — the probe path is a real move-back.
        assert env['fake_lock'].acquired == 1
        assert env['fake_lock'].released == 1

    def test_probe_resolved_source_is_not_clobbered_by_a_critical_channel_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the channel returns a CRITICAL error (not the recoverable
        moved-in-from-main shape), the probe is skipped and integrate surfaces the
        critical error verbatim — no move-back is attempted."""
        env = self._build_env(tmp_path, monkeypatch)

        critical = integrate_into_main.make_error(
            'manage-status get-worktree-path failed: boom',
            code=integrate_into_main.ErrorCode.NOT_FOUND,
            plan_id=env['plan_id'],
        )
        monkeypatch.setattr(
            integrate_into_main,
            '_resolve_worktree_path_via_status_channel',
            lambda pid: (None, critical),
        )

        result = integrate_into_main.run_integrate_into_main(
            Namespace(plan_id=env['plan_id'])
        )

        assert result['status'] == 'error', result
        # No move-back happened; the worktree-resident plan dir is untouched and the
        # merge lock was never acquired (resolution failed before lock acquisition).
        assert env['wt_plan_dir'].is_dir()
        assert not env['main_plan_dir'].exists()
        assert env['fake_lock'].acquired == 0


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestIntegrateCli:
    def test_integrate_requires_plan_id(self) -> None:
        from conftest import run_script

        result = run_script(SCRIPT_PATH, 'integrate')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout
