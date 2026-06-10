#!/usr/bin/env python3
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

import json
import os
import threading
import time

from conftest import load_script_module

_mod = load_script_module('plan-marshall', 'manage-locks', '_locks_core.py', '_locks_core_under_test')

holder_is_dead = _mod.holder_is_dead
rmw_json = _mod.rmw_json
_read_json_or_empty = _mod._read_json_or_empty
_acquire_guard = _mod._acquire_guard
_atomic_write_json = _mod._atomic_write_json


# =============================================================================
# holder_is_dead — empty / malformed holder
# =============================================================================


def test_holder_is_dead_empty_string_is_dead(plan_context):
    # An empty holder is treated as dead so a corrupt lock file is reclaimable.
    assert holder_is_dead('') is True


def test_holder_is_dead_whitespace_only_is_dead(plan_context):
    # Whitespace is stripped to empty → dead.
    assert holder_is_dead('   ') is True


# =============================================================================
# holder_is_dead — liveness via main checkout
# =============================================================================


def test_holder_is_dead_false_when_main_plan_dir_exists(plan_context):
    # A holder whose plan dir lives on main (phases 1-4 / post-finalize) is alive.
    plan_context.plan_dir_for('lc-alive-main')

    assert holder_is_dead('lc-alive-main') is False


# =============================================================================
# holder_is_dead — liveness via the holder's worktree
# =============================================================================


def test_holder_is_dead_false_when_worktree_plan_dir_exists(plan_context):
    # While executing, the plan dir is MOVED into the worktree and does NOT
    # exist on main. Checking only main would wrongly declare the holder dead;
    # the worktree-resident path must keep it alive.
    base = plan_context.fixture_dir
    worktree_plan = base / 'worktrees' / 'lc-alive-wt' / '.plan' / 'local' / 'plans' / 'lc-alive-wt'
    worktree_plan.mkdir(parents=True, exist_ok=True)

    assert holder_is_dead('lc-alive-wt') is False


def test_holder_is_dead_true_when_neither_path_exists(plan_context):
    # No main plan dir and no worktree plan dir → the holder is dead.
    assert holder_is_dead('lc-no-such-holder') is True


# =============================================================================
# _read_json_or_empty — missing / corrupt / non-dict / valid
# =============================================================================


def test_read_json_missing_file_returns_empty(tmp_path):
    missing = tmp_path / 'state.json'

    assert _read_json_or_empty(missing) == {}


def test_read_json_corrupt_content_returns_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{not valid json', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_non_dict_list_returns_empty(tmp_path):
    # A valid-JSON but non-dict top-level shape is also treated as empty so a
    # malformed file cannot corrupt a dict-expecting consumer.
    path = tmp_path / 'state.json'
    path.write_text('[1, 2, 3]', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_scalar_returns_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('42', encoding='utf-8')

    assert _read_json_or_empty(path) == {}


def test_read_json_valid_dict_is_returned(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'slots': {'a': 1}}), encoding='utf-8')

    assert _read_json_or_empty(path) == {'slots': {'a': 1}}


# =============================================================================
# _atomic_write_json — round-trip / overwrite / no temp residue
# =============================================================================


def test_atomic_write_round_trips(tmp_path):
    path = tmp_path / 'state.json'

    _atomic_write_json(path, {'held_by': 'plan-x'})

    assert json.loads(path.read_text(encoding='utf-8')) == {'held_by': 'plan-x'}


def test_atomic_write_overwrites_existing(tmp_path):
    path = tmp_path / 'state.json'
    _atomic_write_json(path, {'v': 1})

    _atomic_write_json(path, {'v': 2})

    assert json.loads(path.read_text(encoding='utf-8')) == {'v': 2}


def test_atomic_write_creates_parent_dirs(tmp_path):
    path = tmp_path / 'nested' / 'dir' / 'state.json'

    _atomic_write_json(path, {'ok': True})

    assert json.loads(path.read_text(encoding='utf-8')) == {'ok': True}


def test_atomic_write_leaves_no_temp_file(tmp_path):
    path = tmp_path / 'state.json'

    _atomic_write_json(path, {'v': 1})

    # The temp file (``{name}.{pid}.tmp``) is consumed by os.replace — only the
    # committed file should remain in the directory.
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != 'state.json']
    assert leftovers == []


def test_atomic_write_large_payload_round_trips_without_truncation(tmp_path):
    # POSIX permits os.write to return a partial count, so a single os.write
    # call does not guarantee the whole buffer reaches the file for a large
    # payload. The write-loop must keep writing until every byte is flushed —
    # a large state dict (well past any single-write boundary) must round-trip
    # intact, never truncated to a parse error or a short read.
    path = tmp_path / 'state.json'
    large_state = {'slots': {f'plan-{i:05d}': {'pid': i, 'note': 'x' * 64} for i in range(5000)}}

    _atomic_write_json(path, large_state)

    assert json.loads(path.read_text(encoding='utf-8')) == large_state


# =============================================================================
# _acquire_guard — free / stale-reclamation / timeout
# =============================================================================


def test_acquire_guard_on_free_returns_fd(tmp_path):
    guard = tmp_path / 'state.json.lock'

    fd = _acquire_guard(guard)
    try:
        assert isinstance(fd, int)
        assert guard.exists()
    finally:
        os.close(fd)
        guard.unlink()


def test_acquire_guard_creates_parent_dir(tmp_path):
    guard = tmp_path / 'nested' / 'state.json.lock'

    fd = _acquire_guard(guard)
    try:
        assert guard.exists()
    finally:
        os.close(fd)
        guard.unlink()


def test_acquire_guard_reclaims_stale_guard(tmp_path, monkeypatch):
    # A guard older than the stale threshold is reclaimed (a crashed mutator
    # left it behind). Shrink the threshold so a freshly-created guard counts as
    # stale, then assert acquisition still succeeds.
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', -1.0)
    guard = tmp_path / 'state.json.lock'
    guard.write_text('', encoding='utf-8')  # pre-existing (stale) guard

    fd = _acquire_guard(guard)
    try:
        assert guard.exists()
    finally:
        os.close(fd)
        guard.unlink()


def test_acquire_guard_times_out_when_held(tmp_path, monkeypatch):
    # A guard that is held and NOT stale cannot be acquired within the budget →
    # TimeoutError. Keep the stale threshold high so the held guard is never
    # reclaimed, and shrink the timeout/backoff so the spin resolves fast.
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_TIMEOUT_SECONDS', 0.05)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.005)
    guard = tmp_path / 'state.json.lock'

    held_fd = _acquire_guard(guard)
    try:
        raised = False
        try:
            _acquire_guard(guard)
        except TimeoutError:
            raised = True
        assert raised, 'expected TimeoutError when the guard is held and not stale'
    finally:
        os.close(held_fd)
        guard.unlink()


# =============================================================================
# rmw_json — missing pre-state / existing pre-state / mutate semantics
# =============================================================================


def test_rmw_json_missing_file_mutates_over_empty(tmp_path):
    path = tmp_path / 'state.json'

    result = rmw_json(path, lambda state: {**state, 'count': 1})

    assert result == {'count': 1}
    assert json.loads(path.read_text(encoding='utf-8')) == {'count': 1}


def test_rmw_json_receives_existing_state(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'count': 1}), encoding='utf-8')

    seen: dict = {}

    def _mutate(state):
        seen.update(state)
        return {**state, 'count': state['count'] + 1}

    result = rmw_json(path, _mutate)

    assert seen == {'count': 1}  # mutate saw the freshly-read pre-state
    assert result == {'count': 2}
    assert json.loads(path.read_text(encoding='utf-8')) == {'count': 2}


def test_rmw_json_corrupt_pre_state_treated_as_empty(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{corrupt', encoding='utf-8')

    result = rmw_json(path, lambda state: {**state, 'rebuilt': True})

    assert result == {'rebuilt': True}


def test_rmw_json_removes_guard_after_commit(tmp_path):
    path = tmp_path / 'state.json'
    guard = path.with_name(f'{path.name}{_mod._GUARD_SUFFIX}')

    rmw_json(path, lambda state: {**state, 'v': 1})

    # The guard is always removed in a ``finally`` so a later mutator is not
    # blocked by a leftover guard file.
    assert not guard.exists()


def test_rmw_json_removes_guard_when_mutate_raises(tmp_path):
    # Even when the mutate callback raises, the guard MUST be removed so a
    # crashed mutator does not wedge the file forever.
    path = tmp_path / 'state.json'
    guard = path.with_name(f'{path.name}{_mod._GUARD_SUFFIX}')

    def _boom(_state):
        raise ValueError('mutate failed')

    raised = False
    try:
        rmw_json(path, _boom)
    except ValueError:
        raised = True

    assert raised
    assert not guard.exists()


def test_rmw_json_returns_committed_state(tmp_path):
    path = tmp_path / 'state.json'

    returned = rmw_json(path, lambda state: {'final': 'state'})

    assert returned == {'final': 'state'}


# =============================================================================
# rmw_json — serialization under concurrency (TOCTOU correctness)
# =============================================================================


def test_rmw_json_serializes_concurrent_increments(tmp_path):
    # Two threads each run N increment mutations against the same file. If the
    # read-modify-write were not serialized by the guard, lost updates would
    # leave the final count below 2*N. The guard must make every increment
    # observe the prior committed state, so the final count equals 2*N exactly.
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'count': 0}), encoding='utf-8')
    per_thread = 25

    def _worker():
        for _ in range(per_thread):
            rmw_json(path, lambda state: {'count': state.get('count', 0) + 1})

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = json.loads(path.read_text(encoding='utf-8'))
    assert final['count'] == 2 * per_thread


def test_rmw_json_second_caller_sees_first_committed_state(tmp_path, monkeypatch):
    # A second mutator that contends on the guard must read the FIRST mutator's
    # committed state, never the stale pre-state. Simulate the race
    # single-threaded by having the first mutate commit, then the second mutate
    # asserts it observed the first's write.
    path = tmp_path / 'state.json'

    rmw_json(path, lambda state: {'owner': 'first'})

    observed: dict = {}

    def _second(state):
        observed.update(state)
        return {**state, 'owner': 'second'}

    result = rmw_json(path, _second)

    assert observed == {'owner': 'first'}  # second saw first's committed state
    assert result == {'owner': 'second'}


def test_rmw_json_blocks_until_guard_released(tmp_path, monkeypatch):
    # When the guard is already held by another holder, a fresh rmw_json call
    # must spin (not error) until the guard is released, then proceed. Hold the
    # guard from a background thread, release it shortly after, and assert the
    # rmw_json call completes successfully once the guard frees.
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_TIMEOUT_SECONDS', 5.0)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.005)

    path = tmp_path / 'state.json'
    guard = path.with_name(f'{path.name}{_mod._GUARD_SUFFIX}')

    held_fd = _acquire_guard(guard)
    release_done = threading.Event()

    def _release_after_delay():
        time.sleep(0.05)
        os.close(held_fd)
        guard.unlink()
        release_done.set()

    releaser = threading.Thread(target=_release_after_delay)
    releaser.start()

    # This call must block on the held guard, then succeed once it is released.
    result = rmw_json(path, lambda state: {**state, 'after': 'release'})
    releaser.join()

    assert release_done.is_set()
    assert result == {'after': 'release'}
    assert not guard.exists()
