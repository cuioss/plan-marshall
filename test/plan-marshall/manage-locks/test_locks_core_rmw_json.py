#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-locks ``_locks_core.py`` shared coordination primitives."""


from __future__ import annotations

import json
import os
import threading
import time

import pytest
from _locks_core_fixtures import (
    _acquire_guard,
    _lock_log_base,
    _mod,
    _resolve_lock_log_path,
    log_lock_event,
    rmw_json,
)

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


@pytest.mark.xdist_group(name="manage_locks_contention")
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


# =============================================================================
# [LOCK] event emission — log_lock_event + _resolve_lock_log_path
# =============================================================================

def test_resolve_lock_log_path_is_main_anchored(tmp_path, monkeypatch):
    # The lock-event log lives under the MAIN-anchored .plan/logs dir, derived
    # from <PLAN_BASE_DIR>.parent / logs / lock-{date}.log — NOT a worktree path.
    base, log_path = _lock_log_base(tmp_path, monkeypatch)

    assert log_path.parent == base.parent / 'logs'
    assert log_path.name.startswith('lock-')
    assert log_path.name.endswith('.log')


def test_resolve_lock_log_path_ignores_worktree_cwd(tmp_path, monkeypatch):
    # Pinning cwd into a worktree fixture does NOT redirect the lock-event log to
    # a worktree-relative path — it stays the single main-anchored timeline.
    base, _ = _lock_log_base(tmp_path, monkeypatch)
    worktree = tmp_path / 'worktrees' / 'some-plan'
    (worktree / '.plan' / 'local').mkdir(parents=True)
    monkeypatch.chdir(worktree)

    log_path = _resolve_lock_log_path()

    assert log_path.parent == base.parent / 'logs'
    assert (worktree / '.plan' / 'logs') != log_path.parent


def test_log_lock_event_appends_lock_tagged_line(tmp_path, monkeypatch):
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='plan-a')

    content = log_path.read_text(encoding='utf-8')
    # The bracketed [LOCK] tag + (family:event) + lock_id are on the header line,
    # carrying the standard [ts] [LEVEL] [hash] prefix.
    assert '[LOCK] (merge:acquired) plan-a' in content
    assert '[INFO]' in content


def test_log_lock_event_records_each_lifecycle_event(tmp_path, monkeypatch):
    # acquire / blocked / release / stale-reclaim for both primitives all land
    # in the SINGLE main-anchored timeline.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='m-1')
    log_lock_event('merge', 'blocked', lock_id='m-2', holder='m-1', waiter='m-2')
    log_lock_event('merge', 'released', lock_id='m-1')
    log_lock_event('merge', 'reclaimed', lock_id='m-3', reclaimed_from='m-dead')
    log_lock_event('build', 'acquired', lock_id='b-1:uuid', active_count=1, waiting_count=0)
    log_lock_event('build', 'blocked', lock_id='b-2:uuid', waiter='b-2', active_count=1, waiting_count=1)
    log_lock_event('build', 'released', lock_id='b-1:uuid', active_count=0, waiting_count=0)
    log_lock_event('build', 'reaped-stale', lock_id='b-3:uuid')

    content = log_path.read_text(encoding='utf-8')
    assert '[LOCK] (merge:acquired) m-1' in content
    assert '[LOCK] (merge:blocked) m-2' in content
    assert '[LOCK] (merge:released) m-1' in content
    assert '[LOCK] (merge:reclaimed) m-3' in content
    assert '[LOCK] (build:acquired) b-1:uuid' in content
    assert '[LOCK] (build:blocked) b-2:uuid' in content
    assert '[LOCK] (build:released) b-1:uuid' in content
    assert '[LOCK] (build:reaped-stale) b-3:uuid' in content


def test_log_lock_event_includes_correlation_fields(tmp_path, monkeypatch):
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'blocked', lock_id='m-2', holder='m-1', waiter='m-2')

    content = log_path.read_text(encoding='utf-8')
    # Correlation fields are appended as indented lines under the header.
    assert 'holder: m-1' in content
    assert 'waiter: m-2' in content


def test_log_lock_event_reaped_stale_is_warning_level(tmp_path, monkeypatch):
    # The reaped-stale event is logged at WARNING; every other event is INFO.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('build', 'reaped-stale', lock_id='b-stale:uuid')

    content = log_path.read_text(encoding='utf-8')
    assert '[WARNING]' in content
    assert '[LOCK] (build:reaped-stale) b-stale:uuid' in content


def test_log_lock_event_other_events_are_info_level(tmp_path, monkeypatch):
    # Every non-reaped-stale event is INFO — never WARNING.
    _, log_path = _lock_log_base(tmp_path, monkeypatch)

    log_lock_event('merge', 'acquired', lock_id='m-info')

    content = log_path.read_text(encoding='utf-8')
    assert '[INFO]' in content
    assert '[WARNING]' not in content


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
