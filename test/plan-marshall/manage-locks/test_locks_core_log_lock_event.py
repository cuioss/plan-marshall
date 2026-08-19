#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-locks ``_locks_core.py`` shared coordination primitives.

``_locks_core`` is the single TOCTOU-safe coordination surface that both the
merge mutex and the build-queue limiter build on. It is imported as a module
(never an executor entry point) and exposes two public pieces plus the private
helpers they compose:

  * :func:`holder_is_dead` — the plan-liveness predicate. A recorded holder is
    dead when its plan dir lives in NEITHER the main checkout NOR the holder's
    worktree.
  * :func:`rmw_json` — a serialized, main-anchored read-modify-write for JSON
    state files, guarded by an ``O_EXCL`` guard-file mutex and committed via an
    atomic temp-file replace.

Isolation: under the autouse ``_plan_base_dir_sandbox`` fixture, ``PLAN_BASE_DIR``
is redirected into a per-test tmp dir; ``resolve_main_anchored_path`` (which
``holder_is_dead`` and the call sites of ``rmw_json`` anchor on) honours that
override, so ``holder_is_dead`` resolves liveness against the sandbox tree rather
than the real main checkout. Tests that exercise ``holder_is_dead`` therefore use
the ``plan_context`` fixture (whose ``PLAN_BASE_DIR`` redirect wins over the
autouse default) and build plan/worktree dirs under ``plan_context.fixture_dir``.
The guard / RMW tests operate on free-standing JSON files under ``tmp_path`` and
need no plan-tree scaffolding.
"""


from __future__ import annotations

from _locks_core_fixtures import _lock_log_base, _mod, log_lock_event


def test_log_lock_event_appends_not_overwrites(tmp_path, monkeypatch):
    # A second emission appends to the SAME log file; the first line survives.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='first')
    log_lock_event('merge', 'released', lock_id='first')

    content = log_path.read_text(encoding='utf-8')
    assert '[LOCK] (merge:acquired) first' in content
    assert '[LOCK] (merge:released) first' in content


def test_log_lock_event_swallows_resolution_failure(tmp_path, monkeypatch):
    # A failure ANYWHERE in the emission body (here: the path resolver raising)
    # is swallowed — log_lock_event is best-effort and MUST NOT raise into the
    # lock action it observes.
    _lock_log_base(tmp_path, monkeypatch)

    def _boom() -> object:
        raise RuntimeError('resolution failed')

    monkeypatch.setattr(_mod, '_resolve_lock_log_path', _boom)

    # No exception propagates.
    log_lock_event('merge', 'acquired', lock_id='plan-a')


def test_log_lock_event_swallows_unwritable_dir(tmp_path, monkeypatch):
    # An open() that raises (unwritable dir / encoding error) is swallowed too —
    # the emission is OUTSIDE the lock's atomic window, so a write failure can
    # never affect lock correctness.
    _lock_log_base(tmp_path, monkeypatch)

    def _raising_open(*_a: object, **_k: object) -> object:
        raise OSError('disk full')

    monkeypatch.setattr('builtins.open', _raising_open)

    # No exception propagates despite the write failing.
    log_lock_event('merge', 'released', lock_id='plan-a')
