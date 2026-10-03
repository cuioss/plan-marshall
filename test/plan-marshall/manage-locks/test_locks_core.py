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
    _atomic_write_json,
    _mod,
    _read_json_or_empty,
    holder_has_live_worktree,
    holder_is_dead,
    read_json_guarded,
)


def test_mid_recovery_holder_is_dead_by_plan_dir_but_has_live_worktree(plan_context):
    # The guard scenario: an interrupted finalize move-back leaves the worktree on
    # disk WITH its git plumbing intact (a `.git` marker) but the plan dir has been
    # moved out of BOTH main and the worktree's .plan. holder_is_dead is True
    # (plan-dir absent everywhere) while holder_has_live_worktree is True (the
    # genuine git-worktree marker is still present), so the acquire guard refuses to
    # auto-reclaim it.
    base = plan_context.fixture_dir
    worktree = base / 'worktrees' / 'lc-mid-recovery'
    worktree.mkdir(parents=True, exist_ok=True)
    (worktree / '.git').write_text('gitdir: /main/.git/worktrees/lc-mid-recovery\n', encoding='utf-8')

    assert holder_is_dead('lc-mid-recovery') is True
    assert holder_has_live_worktree('lc-mid-recovery') is True


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
# held_guard — the one acquire/release implementation
# =============================================================================


def test_held_guard_holds_the_guard_inside_the_body_and_removes_it_after(tmp_path):
    guard = tmp_path / 'section.lock'

    with _mod.held_guard(guard):
        held_inside = guard.exists()

    assert (held_inside, guard.exists()) == (True, False)


def test_held_guard_removes_the_guard_when_the_body_raises(tmp_path):
    """The release is a ``finally``: a raising body must not wedge the guard."""
    guard = tmp_path / 'section.lock'

    with pytest.raises(RuntimeError, match='critical section failed'), _mod.held_guard(guard):
        raise RuntimeError('critical section failed')

    assert not guard.exists()


def test_held_guard_blocks_a_second_acquirer_until_release(tmp_path, monkeypatch):
    """A second acquirer enters only after the first holder leaves its block.

    The ordering is established without a wall-clock wait. The worker's backoff
    sleep is the observable proof that it reached the held guard and was turned
    away, so the holder releases only after that signal — and the worker can
    record its entry only once the guard file is gone.
    """
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.001)
    guard = tmp_path / 'section.lock'
    turned_away = threading.Event()
    real_sleep = time.sleep
    events: list[str] = []
    errors: list[Exception] = []

    def signalling_sleep(seconds: float) -> None:
        turned_away.set()
        real_sleep(seconds)

    monkeypatch.setattr(_mod.time, 'sleep', signalling_sleep)

    def second_acquirer() -> None:
        try:
            with _mod.held_guard(guard):
                events.append('second-entered')
        except Exception as exc:  # broad on purpose: surfaced by the assertion below
            errors.append(exc)

    worker = threading.Thread(target=second_acquirer)
    with _mod.held_guard(guard):
        worker.start()
        blocked = turned_away.wait(timeout=30)
        events.append('first-releasing')
    worker.join(timeout=30)

    assert (blocked, worker.is_alive(), errors) == (True, False, [])
    assert events == ['first-releasing', 'second-entered']
    assert not guard.exists()


def test_held_guard_reclaims_a_guard_older_than_the_stale_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', -1.0)
    guard = tmp_path / 'section.lock'
    guard.write_text('', encoding='utf-8')  # left behind by a killed holder

    with _mod.held_guard(guard):
        entered = True

    assert (entered, guard.exists()) == (True, False)


def test_held_guard_does_not_run_the_body_when_a_fresh_guard_is_held(tmp_path, monkeypatch):
    """Matched control for the stale reclaim: a guard inside the threshold is honoured.

    The same pre-existing guard file that is reclaimed above blocks here, where
    only the threshold differs. The ``TimeoutError`` reaches the caller and the
    block never runs.
    """
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_TIMEOUT_SECONDS', 0.05)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.005)
    guard = tmp_path / 'section.lock'
    guard.write_text('', encoding='utf-8')
    entered = False

    with pytest.raises(TimeoutError), _mod.held_guard(guard):
        entered = True

    assert (entered, guard.exists()) == (False, True)


# =============================================================================
# rmw_json — unchanged on top of held_guard
# =============================================================================


def test_rmw_json_commits_and_returns_the_mutated_state_and_releases_the_guard(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'count': 1}), encoding='utf-8')

    result = _mod.rmw_json(path, lambda state: {**state, 'count': state['count'] + 1})

    assert result == {'count': 2}
    assert json.loads(path.read_text(encoding='utf-8')) == {'count': 2}
    assert not (tmp_path / 'state.json.lock').exists()


def test_rmw_json_releases_the_guard_and_commits_nothing_when_the_mutator_raises(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'count': 1}), encoding='utf-8')
    before = path.read_bytes()

    def failing_mutator(_state):
        raise RuntimeError('mutator failed')

    with pytest.raises(RuntimeError, match='mutator failed'):
        _mod.rmw_json(path, failing_mutator)

    assert path.read_bytes() == before
    assert not (tmp_path / 'state.json.lock').exists()


# =============================================================================
# read_json_guarded — the guarded, NON-COMMITTING read
# =============================================================================


def test_read_json_guarded_returns_the_state_without_writing(tmp_path):
    """The read-only counterpart to ``rmw_json``: same answer, no commit."""
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'active': [{'id': 'plan-a:1'}]}), encoding='utf-8')
    before = path.read_bytes()

    assert read_json_guarded(path) == {'active': [{'id': 'plan-a:1'}]}
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    'body',
    [
        pytest.param('{ not json', id='invalid-json'),
        pytest.param('[{"id": "plan-a:1"}]', id='top-level-list'),
        pytest.param('42', id='top-level-scalar'),
    ],
)
def test_read_json_guarded_leaves_an_unreadable_file_byte_identical(tmp_path, body):
    """A file the read could not interpret is a file the read must not rewrite.

    This is the whole reason the helper exists. ``rmw_json`` reports a corrupt,
    truncated or non-dict file as ``{}`` and then COMMITS whatever its mutator
    returns — so a read expressed as an identity mutator writes that ``{}`` back
    and destroys every entry the file held. The empty mapping is still the
    reported interpretation here (a reader and a mutator must not disagree about
    what an unreadable file means); what changes is that nothing is written.
    """
    path = tmp_path / 'state.json'
    path.write_text(body, encoding='utf-8')
    before = path.read_bytes()

    assert read_json_guarded(path) == {}
    assert path.read_bytes() == before


def test_read_json_guarded_does_not_create_a_missing_file(tmp_path):
    """A read of an absent state file reports empty and creates nothing.

    ``rmw_json`` materialises the file on its commit, so a read routed through
    it turned "nothing has coordinated yet" into a committed empty state.
    """
    path = tmp_path / 'state.json'

    assert read_json_guarded(path) == {}
    assert not path.exists()


def test_read_json_guarded_takes_the_guard_so_it_cannot_read_mid_mutation(tmp_path, monkeypatch):
    """The guard is kept, not traded away: a held guard blocks the read.

    Dropping to a bare unguarded read would swap this defect for the torn read
    the ``rmw_json`` call was chosen to avoid, so the guarded-ness is pinned
    rather than assumed. Its matched control is
    :func:`test_read_json_guarded_returns_the_state_without_writing` above, which
    reads successfully against a FREE guard — without that pair, this assertion
    would pass equally against a helper that never acquired anything and simply
    always raised.
    """
    monkeypatch.setattr(_mod, '_GUARD_STALE_SECONDS', 10_000.0)
    monkeypatch.setattr(_mod, '_GUARD_TIMEOUT_SECONDS', 0.05)
    monkeypatch.setattr(_mod, '_GUARD_BACKOFF_SECONDS', 0.005)
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'v': 1}), encoding='utf-8')

    held_fd = _acquire_guard(tmp_path / 'state.json.lock')
    try:
        with pytest.raises(TimeoutError):
            read_json_guarded(path)
    finally:
        os.close(held_fd)
        (tmp_path / 'state.json.lock').unlink()


def test_read_json_guarded_releases_the_guard_it_took(tmp_path):
    """A read must not wedge the file for the next caller.

    The guard is removed in a ``finally``, so a second read — and any subsequent
    mutation — succeeds. Without this, one ``limit get`` would block every later
    acquire until the stale-reclaim threshold elapsed.
    """
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'v': 1}), encoding='utf-8')

    read_json_guarded(path)

    assert not (tmp_path / 'state.json.lock').exists()
    assert read_json_guarded(path) == {'v': 1}
