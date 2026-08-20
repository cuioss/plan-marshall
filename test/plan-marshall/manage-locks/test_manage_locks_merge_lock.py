#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
from _manage_locks_merge_lock_fixtures import (
    _make_live_plan,
    _read_queue,
    _TokenRecorder,
    _waiting_plan_ids,
    merge_lock,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — main stand-in)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/merge.lock        (the O_EXCL lock resolves here)
        tmp_path/main/.plan/local/merge-queue.json  (the FIFO queue resolves here)

    Sets PLAN_BASE_DIR to the main stand-in so the lock resolves to
    ``<base>/merge.lock``, the FIFO queue to ``<base>/merge-queue.json``, and
    ``holder_is_dead(holder)`` resolves the holder plan dir to
    ``<base>/plans/{holder}``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


@pytest.fixture(autouse=True)
def _stub_title_tokens(monkeypatch: pytest.MonkeyPatch) -> _TokenRecorder:
    """Autouse: stub the three best-effort title-token seams for EVERY test so the
    direct ``run_acquire`` / ``run_release`` unit tests never spawn the real
    executor subprocess (the token surface is best-effort and out-of-scope for the
    lock-correctness assertions). Tests that care about the token surface request
    this fixture by name and assert on the recorder.

    The CLI-subprocess concurrency tests run in a SEPARATE spawned process where
    this monkeypatch does not apply — there the real best-effort wrappers run and
    swallow any executor failure, exactly as in production.
    """
    recorder = _TokenRecorder()
    recorder.install(monkeypatch)
    return recorder


# =============================================================================
# Atomic acquire + holder recording
# =============================================================================


class TestAcquire:
    def test_acquire_creates_lock_and_records_holder(self, isolated_base: dict) -> None:
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success', result
        assert result['action'] == 'acquired'
        assert result['admission'] == 'admitted'
        assert result['holder'] == 'plan-a'
        assert result['reclaimed'] is False

        lock_path = isolated_base['lock_path']
        assert lock_path.is_file()
        # Holder source recorded in the file contents.
        assert lock_path.read_text(encoding='utf-8').strip() == 'plan-a'

    def test_acquire_is_atomic_o_excl(self, isolated_base: dict) -> None:
        """The lock file is created exclusively — a pre-existing file from a live
        holder blocks a second atomic create (the primitive returns False)."""
        lock_path = isolated_base['lock_path']
        # First acquire wins and creates the file.
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        # The low-level atomic create against the existing file must fail.
        assert merge_lock._try_atomic_create(lock_path, 'plan-b') is False

    def test_lone_acquirer_is_the_fifo_front(self, isolated_base: dict) -> None:
        """A lone acquirer is trivially the FIFO front and is admitted; the queue
        records it as the single waiting entry while it holds the lock."""
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['admission'] == 'admitted'
        assert result['waiting_count'] == 1
        # The acquiring plan is enqueued (front) for the duration of its hold.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['plan-a']


# =============================================================================
# Sibling-key preservation — the FIFO mutators share the store with co-tenants
# =============================================================================


class TestSiblingKeyPreservation:
    """``merge-queue.json`` is a SHARED store, not a single-purpose queue file: the
    rate-window claim co-tenants a ``rate_windows`` top-level key alongside
    ``waiting``.

    The pre-fix ``_enqueue_fifo`` / ``_dequeue_fifo`` mutators returned a
    freshly-constructed ``{'waiting': waiting}``, which DISCARDS every other
    top-level key — so a co-tenant key would be silently erased by the very next
    merge acquire or release. Every assertion in this class is RED against that
    wholesale-replace behaviour and green only once both mutators merge into the
    state they were handed. This is what makes the store reuse verified rather than
    merely plausible."""

    def test_acquire_preserves_an_unrelated_top_level_key(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [], 'rate_windows': {'coderabbit': {'holder': 'plan-x'}}}),
            encoding='utf-8',
        )

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        store = _read_queue(isolated_base['queue_path'])
        assert store['rate_windows'] == {'coderabbit': {'holder': 'plan-x'}}
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['plan-a']

    def test_release_preserves_an_unrelated_top_level_key(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [], 'rate_windows': {'coderabbit': {'holder': 'plan-x'}}}),
            encoding='utf-8',
        )
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        merge_lock.run_release(Namespace(plan_id='plan-a'))

        store = _read_queue(isolated_base['queue_path'])
        assert store['rate_windows'] == {'coderabbit': {'holder': 'plan-x'}}
        assert _waiting_plan_ids(isolated_base['queue_path']) == []

    def test_full_acquire_release_round_trip_preserves_the_co_tenant(self, isolated_base: dict) -> None:
        """The round-trip is the real exposure: an acquire followed by a release is
        two wholesale replaces, either of which would drop the co-tenant."""
        co_tenant = {'coderabbit': {'holder': 'plan-x', 'pr_number': 7, 'expires_at': 1.0, 'attempts': 2}}
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [], 'rate_windows': co_tenant}), encoding='utf-8'
        )

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        merge_lock.run_release(Namespace(plan_id='plan-a'))

        assert _read_queue(isolated_base['queue_path'])['rate_windows'] == co_tenant


# =============================================================================
# FIFO admission — only the FIFO front may attempt the O_EXCL create
# =============================================================================


class TestFifoAdmission:
    """The FIFO admission layer: ``acquire`` enqueues into ``merge-queue.json`` and
    admits ONLY the FIFO-front plan (the first entry in serialized arrival order). A
    non-front plan returns ``admission: blocked`` WITHOUT attempting the ``O_EXCL``
    create — even when the lock file is FREE, a non-front plan never contends the
    kernel race. This is the fairness property that makes the longest-waiting plan
    merge next."""

    def test_non_front_plan_blocks_even_when_lock_is_free(self, isolated_base: dict) -> None:
        """A non-front plan is blocked purely by FIFO ordering — the lock file does
        not even exist yet (no plan has acquired it), yet a later-arriving plan
        behind the front in the queue still returns ``blocked``."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        # Seed the queue directly so 'front' is the oldest entry and 'behind' is
        # strictly later — no lock file is created (no acquire has run yet).
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )
        assert not isolated_base['lock_path'].exists()

        # 'behind' polls: it is NOT the FIFO front, so it blocks WITHOUT creating
        # the lock — the lock file stays absent.
        result = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert result['status'] == 'blocked'
        assert result['admission'] == 'blocked'
        # No foreign holder yet — the lock is unheld, the block is FIFO-only.
        assert result['blocking_plan_id'] is None
        # The non-front plan never created the lock file.
        assert not isolated_base['lock_path'].exists()

    def test_front_plan_is_admitted_over_a_later_waiter(self, isolated_base: dict) -> None:
        """The FIFO front is admission-eligible and wins the O_EXCL create; the
        later waiter behind it stays blocked."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )

        # The front polls and is admitted (creates the lock).
        front = merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        assert front['admission'] == 'admitted'
        assert front['holder'] == 'front'
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'front'

        # The waiter behind it polls and is blocked by the now-live front holder.
        behind = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert behind['admission'] == 'blocked'
        assert behind['blocking_plan_id'] == 'front'

    def test_acquire_enqueues_in_arrival_order(self, isolated_base: dict) -> None:
        """Successive single-shot acquires enqueue in arrival order: the first
        acquirer becomes the front (admitted), each later acquirer appends behind
        it in the FIFO ``waiting`` list."""
        base = isolated_base['base']
        for name in ('a', 'b', 'c'):
            _make_live_plan(base, name)

        a = merge_lock.run_acquire(Namespace(plan_id='a', timeout=5.0))
        assert a['admission'] == 'admitted'
        b = merge_lock.run_acquire(Namespace(plan_id='b', timeout=5.0))
        assert b['admission'] == 'blocked'
        c = merge_lock.run_acquire(Namespace(plan_id='c', timeout=5.0))
        assert c['admission'] == 'blocked'

        # The FIFO queue records all three in arrival order, front first.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['a', 'b', 'c']
        # Each blocked waiter names the live front holder as the blocker.
        assert b['blocking_plan_id'] == 'a'
        assert c['blocking_plan_id'] == 'a'

    def test_blocked_payload_carries_waiting_count_not_poll_window(self, isolated_base: dict) -> None:
        """The blocked admission payload carries ``waiting_count`` (the queue depth)
        and ``blocking_plan_id`` — and crucially NOT the retired internal-wait
        ``poll_window_seconds`` field (acquire no longer waits internally)."""
        for name in ('plan-a', 'plan-b'):
            _make_live_plan(isolated_base['base'], name)
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # waiting_count is the queue depth (front 'plan-a' + waiter 'plan-b').
        assert result['waiting_count'] == 2
        # The internal-wait field was retired with the wait loop.
        assert 'poll_window_seconds' not in result
        # blocked is NOT a hard error — no error_code is set.
        assert result.get('error_code') is None

    def test_front_is_list_position_not_min_ts_under_inverted_ts(self, isolated_base: dict) -> None:
        """Regression: the FIFO front is the FIRST ``waiting`` entry (serialized
        arrival order), NOT the entry with the smallest admit-``ts``.

        Under concurrent enqueue a ``ts`` sampled before the serialized ``rmw_json``
        section can disagree with the append order, so a ``min(ts)`` front selector
        could pick a different plan than the file's first entry. During a drain that
        made the genuine list-front poll ``blocked`` with no holder — the
        no-double-grant drain flake. The queue below has append order
        ``[first, second]`` but INVERTED admit-``ts`` (``first``'s ts is LARGER), so
        a min-ts selector would wrongly elect ``second`` as the front.
        """
        base = isolated_base['base']
        for name in ('first', 'second'):
            _make_live_plan(base, name)
        # Append order [first, second], but ts is inverted (first.ts > second.ts).
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'first', 'ts': 2.0},
                {'plan_id': 'second', 'ts': 1.0},
            ]}),
            encoding='utf-8',
        )
        assert not isolated_base['lock_path'].exists()

        # 'first' is the list-position front → admitted. A min-ts selector would
        # have elected 'second' and wrongly blocked 'first' here.
        first = merge_lock.run_acquire(Namespace(plan_id='first', timeout=5.0))
        assert first['admission'] == 'admitted', first
        assert first['holder'] == 'first'

        # 'second' (later in arrival order despite the smaller ts) is blocked
        # behind the now-live front.
        second = merge_lock.run_acquire(Namespace(plan_id='second', timeout=5.0))
        assert second['admission'] == 'blocked', second
        assert second['blocking_plan_id'] == 'first'
