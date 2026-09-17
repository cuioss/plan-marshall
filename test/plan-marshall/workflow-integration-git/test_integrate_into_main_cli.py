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

    def run_acquire(self, args: Namespace) -> dict:
        self.acquired += 1
        self.acquire_set_title_tokens.append(getattr(args, 'set_title_token', 'absent'))
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


class TestResolveWorktreePathViaStatusChannel:
    """Direct coverage of the CHANNEL itself, against the single resolver seam.

    Previously this layer had no direct tests — every case stubbed the channel
    wholesale, so nothing exercised the code that talks to the resolver. That is
    exactly the layer the migration rewrote, and the layer whose classification
    the probe ladder above depends on.

    The load-bearing property pinned here: the recoverable
    "no worktree configured" verdict is derived STRUCTURALLY from the resolver's
    ``has_worktree`` face, not by matching the resolver's error text. A textual
    derivation would silently unhook the structural-probe fallback the moment
    the resolver reworded an error.
    """

    def test_resolves_the_path_through_the_resolver_seam(self, tmp_path: Path) -> None:
        worktree = tmp_path / 'wt'
        worktree.mkdir()

        with patch_query_worktree_path(True, str(worktree)) as mock:
            path, err = integrate_into_main._resolve_worktree_path_via_status_channel('ok-plan')

        assert err is None, err
        assert path == worktree
        assert mock.call_count == 1

    def test_no_worktree_verdict_is_structural_and_recoverable(self) -> None:
        """``use_worktree=false`` yields the verbatim recoverable message.

        The message is emitted off ``has_worktree``, so it is a constant this
        module owns rather than resolver text — which is what keeps it inside
        ``_EXPECTED_ERROR_SUBSTRINGS`` and the probe fallback reachable.
        """
        with patch_query_worktree_path(False):
            path, err = integrate_into_main._resolve_worktree_path_via_status_channel('no-wt')

        assert path is None
        assert err is not None
        message = str(err.get('error') or err.get('message') or '').lower()
        assert 'no worktree configured' in message
        assert any(s in message for s in integrate_into_main._EXPECTED_ERROR_SUBSTRINGS), (
            'the no-worktree verdict fell outside the recoverable set, which '
            'makes the structural-probe fallback unreachable'
        )

    def test_resolution_failure_surfaces_the_resolver_message(self, monkeypatch) -> None:
        """A resolver failure is surfaced verbatim, never rewritten."""
        import file_ops  # local import: the handle is needed only to patch a seam here

        def _raise(_plan_id):
            raise file_ops.WorktreeResolutionError('status.json not found for plan')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)

        path, err = integrate_into_main._resolve_worktree_path_via_status_channel('gone-plan')

        assert path is None
        assert err is not None
        assert 'status.json not found' in str(err.get('error') or err.get('message'))

    def test_no_plan_sentinel_is_refused_without_shelling_out(self) -> None:
        """``NO_PLAN`` has no dedicated worktree, so the move-back refuses it.

        The resolver ACCEPTS the sentinel (it resolves to the main checkout);
        the refusal belongs here, because there is no worktree to move a plan
        dir back FROM. Asserting the zero call-count also pins that the sentinel
        never pays a ``get-worktree-path`` round trip.
        """
        with patch_query_worktree_path(True) as mock:
            path, err = integrate_into_main._resolve_worktree_path_via_status_channel(NO_PLAN_SENTINEL)

        assert path is None
        assert err is not None
        assert 'no worktree configured' in str(err.get('error') or err.get('message')).lower()
        assert mock.call_count == 0, 'the sentinel must never reach get-worktree-path'


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

    def _build_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
        plan_id = 'main-probe-plan'

        # Stage main + the worktree at the canonical get_worktree_root()/{plan_id}
        # layout so the REAL structural probe can resolve the SOURCE.
        worktree_path = _stage_worktree_at_canonical_root(tmp_path, monkeypatch, plan_id)
        main_local = tmp_path / 'main' / '.plan' / 'local'
        main_plan_dir = main_local / 'plans' / plan_id
        (main_local / 'plans').mkdir(parents=True, exist_ok=True)

        wt_plan_dir = worktree_path / '.plan' / 'local' / 'plans' / plan_id
        (wt_plan_dir / 'references.json').write_text(json.dumps({'modified_files': ['doc/foo.md']}))
        wt_global_logs = worktree_path / '.plan' / 'local' / 'logs'
        wt_global_logs.mkdir(parents=True)
        (wt_global_logs / 'work.log').write_text('[STATUS] hello\n')

        # cwd is MAIN — the moved-in-from-main invocation. (PLAN_BASE_DIR, not cwd,
        # drives resolution, but pinning cwd to main proves cwd-independence.)
        monkeypatch.chdir(tmp_path / 'main')

        # SOURCE channel returns a recoverable NOT_FOUND (main's status.json moved
        # into the worktree); the REAL structural probe must rescue it.
        recoverable = integrate_into_main.make_error(
            'No worktree configured for this plan — status.metadata.use_worktree is false or worktree_path is unset',
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

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

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

        result = integrate_into_main.run_integrate_into_main(Namespace(plan_id=env['plan_id']))

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
