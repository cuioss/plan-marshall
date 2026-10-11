#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Its sections, in order:

* Fixtures
* Idempotent re-poll — a blocked plan re-polling KEEPS its FIFO position
* Release advances the FIFO front
* Release
* Dequeue-only — ``run_dequeue`` removes the FIFO entry and never touches the lock
"""

from __future__ import annotations

import json
from argparse import Namespace

import pytest
from _manage_locks_merge_lock_fixtures import (
    _make_live_plan,
    _stub_title_tokens,
    _TokenRecorder,
    _waiting_plan_ids,
    isolated_base,
    merge_lock,
)

# =============================================================================
# Fixtures
# =============================================================================


# =============================================================================
# Idempotent re-poll — a blocked plan re-polling KEEPS its FIFO position
# =============================================================================


class TestIdempotentRepoll:
    """The idempotent re-poll fast-path: a plan already in the queue KEEPS its FIFO
    position on a re-poll — it is never re-appended to the back. A plan polling
    repeatedly therefore never loses priority to a later-arriving plan, mirroring
    ``build_queue.run_acquire``'s idempotent re-poll fast-path."""

    def test_repoll_blocked_plan_keeps_fifo_position(self, isolated_base: dict) -> None:
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        # front acquires (becomes the live holder); w1 then w2 queue behind it.
        merge_lock.run_acquire(Namespace(plan_id='front'))
        w1 = merge_lock.run_acquire(Namespace(plan_id='w1'))
        w2 = merge_lock.run_acquire(Namespace(plan_id='w2'))
        assert w1['admission'] == 'blocked'
        assert w2['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

        # w1 re-polls while still blocked — it must NOT move behind w2.
        re_w1 = merge_lock.run_acquire(Namespace(plan_id='w1'))
        assert re_w1['admission'] == 'blocked'
        # The FIFO order is unchanged: w1 still ahead of w2.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

    def test_repoll_does_not_re_append_or_grow_queue(self, isolated_base: dict) -> None:
        """Re-polling an already-queued plan is idempotent on the queue itself — the
        ``waiting`` depth does not grow, the plan appears exactly once."""
        for name in ('front', 'waiter'):
            _make_live_plan(isolated_base['base'], name)
        merge_lock.run_acquire(Namespace(plan_id='front'))
        merge_lock.run_acquire(Namespace(plan_id='waiter'))

        # Re-poll the waiter several times.
        for _ in range(3):
            res = merge_lock.run_acquire(Namespace(plan_id='waiter'))
            assert res['admission'] == 'blocked'

        waiting = _waiting_plan_ids(isolated_base['queue_path'])
        # The waiter appears exactly once despite the repeated re-polls.
        assert waiting.count('waiter') == 1
        assert waiting == ['front', 'waiter']

    def test_front_repoll_against_foreign_live_holder_keeps_front_position(self, isolated_base: dict) -> None:
        """The FIFO FRONT itself can be blocked when a FOREIGN live holder holds
        the lock (e.g. a reentrant holder that pre-existed the queue). The front's
        re-poll keeps its front position so it is first in line on release."""
        base = isolated_base['base']
        _make_live_plan(base, 'holder')
        _make_live_plan(base, 'front')
        # 'holder' holds the lock but is NOT in the FIFO queue; 'front' is the
        # queue front behind a foreign live holder.
        merge_lock.run_acquire(Namespace(plan_id='holder'))
        # Drop holder from the queue so 'front' is the genuine FIFO front while
        # 'holder' still holds the lock file.
        merge_lock._dequeue_fifo('holder')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [{'plan_id': 'front', 'ts': 1.0}]}), encoding='utf-8'
        )

        first = merge_lock.run_acquire(Namespace(plan_id='front'))
        assert first['admission'] == 'blocked'
        assert first['blocking_plan_id'] == 'holder'
        # Re-poll: front stays the front, still blocked by the live foreign holder.
        again = merge_lock.run_acquire(Namespace(plan_id='front'))
        assert again['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front']


# =============================================================================
# Release advances the FIFO front
# =============================================================================


class TestReleaseAdvancesFront:
    """``release`` dequeues ``--plan-id`` so the NEXT FIFO entry becomes the front
    and is admitted on its next re-poll. This is the FIFO hand-off: the
    longest-waiting plan merges next once the current holder releases."""

    def test_release_dequeues_holder_advancing_next_waiter_to_front(self, isolated_base: dict) -> None:
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front'))
        merge_lock.run_acquire(Namespace(plan_id='w1'))
        merge_lock.run_acquire(Namespace(plan_id='w2'))
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

        # The holder releases — it is dequeued, advancing w1 to the front.
        rel = merge_lock.run_release(Namespace(plan_id='front'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['w1', 'w2']

        # w1 (now the front) re-polls and is admitted; w2 stays blocked behind it.
        re_w1 = merge_lock.run_acquire(Namespace(plan_id='w1'))
        assert re_w1['admission'] == 'admitted'
        assert re_w1['holder'] == 'w1'
        re_w2 = merge_lock.run_acquire(Namespace(plan_id='w2'))
        assert re_w2['admission'] == 'blocked'
        assert re_w2['blocking_plan_id'] == 'w1'

    def test_non_front_waiter_stays_blocked_until_its_turn(self, isolated_base: dict) -> None:
        """FIFO order is honoured across releases: a non-front waiter that re-polls
        stays blocked even though it could win the kernel race, because an earlier
        waiter holds priority and must be served first."""
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front'))
        merge_lock.run_acquire(Namespace(plan_id='w1'))
        merge_lock.run_acquire(Namespace(plan_id='w2'))

        # Holder releases → w1 advances to front. The lock file is now free.
        merge_lock.run_release(Namespace(plan_id='front'))
        assert not isolated_base['lock_path'].exists()

        # w2 (non-front) re-polls: the lock is free, but w2 is behind w1 → blocked.
        re_w2 = merge_lock.run_acquire(Namespace(plan_id='w2'))
        assert re_w2['admission'] == 'blocked'
        # w2 stays behind w1 — the front did not change.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['w1', 'w2']

    def test_full_fifo_drain_serves_plans_in_arrival_order(self, isolated_base: dict) -> None:
        """End-to-end FIFO drain: three plans queue in arrival order and are served
        front-first across successive acquire/release rounds — never out of order."""
        base = isolated_base['base']
        for name in ('a', 'b', 'c'):
            _make_live_plan(base, name)
        # Enqueue in arrival order: a is admitted, b and c queue behind.
        merge_lock.run_acquire(Namespace(plan_id='a'))
        merge_lock.run_acquire(Namespace(plan_id='b'))
        merge_lock.run_acquire(Namespace(plan_id='c'))

        served: list[str] = ['a']  # 'a' was admitted first.

        # Drain b then c in FIFO order.
        merge_lock.run_release(Namespace(plan_id='a'))
        b = merge_lock.run_acquire(Namespace(plan_id='b'))
        assert b['admission'] == 'admitted'
        served.append('b')

        merge_lock.run_release(Namespace(plan_id='b'))
        c = merge_lock.run_acquire(Namespace(plan_id='c'))
        assert c['admission'] == 'admitted'
        served.append('c')

        # Served strictly in arrival order, never out of FIFO order.
        assert served == ['a', 'b', 'c']
        # The queue is empty after the final holder releases.
        merge_lock.run_release(Namespace(plan_id='c'))
        assert _waiting_plan_ids(isolated_base['queue_path']) == []

    def test_release_when_waiting_present_returns_post_removal_count(self, isolated_base: dict) -> None:
        """``release`` reports the post-removal ``waiting_count`` — the holder's own
        entry is gone, so the count reflects the remaining waiters."""
        base = isolated_base['base']
        for name in ('front', 'w1'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front'))
        merge_lock.run_acquire(Namespace(plan_id='w1'))

        rel = merge_lock.run_release(Namespace(plan_id='front'))
        assert rel['action'] == 'released'
        # Front dequeued; w1 remains → post-removal depth is 1.
        assert rel['waiting_count'] == 1


# =============================================================================
# Release
# =============================================================================


class TestRelease:
    def test_release_removes_lock(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))
        assert isolated_base['lock_path'].is_file()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

    def test_release_when_free_is_noop_success(self, isolated_base: dict) -> None:
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['status'] == 'success'
        assert result['action'] == 'noop'

    def test_release_twice_is_idempotent_noop(self, isolated_base: dict) -> None:
        """A second release (after the lock is already freed) is a no-op success —
        a crashed-and-retried finalize must not error on the second release."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))
        first = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert first['action'] == 'released'

        second = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert second['status'] == 'success'
        assert second['action'] == 'noop'

    def test_release_foreign_holder_is_noop_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        """A caller that is not the recorded holder must not remove the lock."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['status'] == 'success'
        assert result['action'] == 'noop'
        assert result['holder'] == 'plan-a'
        # The foreign holder's lock is left intact.
        assert isolated_base['lock_path'].is_file()
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_release_dequeues_even_when_caller_never_held_the_lock(self, isolated_base: dict) -> None:
        """A plan that gave up waiting (never held the lock) must STILL be dequeued
        from the FIFO queue on release — otherwise its stale entry would wedge the
        front. The foreign-holder release noop leaves the lock intact but removes
        the caller's own waiting entry so the front can advance."""
        base = isolated_base['base']
        for name in ('front', 'waiter'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front'))
        merge_lock.run_acquire(Namespace(plan_id='waiter'))
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'waiter']

        # The waiter gives up: it releases though it never held the lock.
        rel = merge_lock.run_release(Namespace(plan_id='waiter'))
        assert rel['action'] == 'noop'
        # The front holder's lock is intact, but the waiter is gone from the queue.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'front'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front']


# =============================================================================
# Dequeue-only
# =============================================================================


class TestDequeueOnly:
    """``run_dequeue`` is the refused-acquire cleanup: it removes the plan's FIFO
    entry and leaves ``merge.lock`` and the co-tenant ``rate_windows`` key alone —
    even when the lock's recorded holder is the very plan being dequeued."""

    def test_removes_the_entry_and_reports_the_remaining_depth(self, isolated_base: dict) -> None:
        base = isolated_base['base']
        for name in ('front', 'waiter'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front'))
        merge_lock.run_acquire(Namespace(plan_id='waiter'))

        result = merge_lock.run_dequeue('waiter')

        assert result['status'] == 'success', result
        assert result['action'] == 'dequeued', result
        assert result['waiting_count'] == 1, result
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front']
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'front'

    def test_never_removes_a_lock_held_by_the_dequeued_plan(self, isolated_base: dict) -> None:
        """The contrast with ``run_release``: the holder IS the dequeued plan, and the
        lock file still survives, because a dequeue never touches the lock."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        merge_lock.run_acquire(Namespace(plan_id='plan-a'))

        result = merge_lock.run_dequeue('plan-a')

        assert result['status'] == 'success', result
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'
        assert _waiting_plan_ids(isolated_base['queue_path']) == []

    def test_preserves_the_rate_windows_key(self, isolated_base: dict) -> None:
        windows = {'coderabbit': {'holder': 'plan-a', 'pr_number': 7, 'expires_at': 1.0, 'attempts': 1}}
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [{'plan_id': 'plan-a', 'ts': 1.0}], 'rate_windows': windows}), encoding='utf-8'
        )
        _make_live_plan(isolated_base['base'], 'plan-a')

        merge_lock.run_dequeue('plan-a')

        stored = json.loads(isolated_base['queue_path'].read_text(encoding='utf-8'))
        assert stored['rate_windows'] == windows
        assert stored['waiting'] == []

    def test_absent_entry_is_an_idempotent_success(self, isolated_base: dict) -> None:
        first = merge_lock.run_dequeue('never-queued')
        second = merge_lock.run_dequeue('never-queued')

        assert first['status'] == 'success', first
        assert second['status'] == 'success', second
        assert second['waiting_count'] == 0, second
        assert not isolated_base['lock_path'].exists()

    def test_queue_failure_is_an_error_payload(self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch) -> None:
        def guard_timeout(plan_id: str) -> int:
            raise TimeoutError('simulated merge-queue guard timeout')

        monkeypatch.setattr(merge_lock, '_dequeue_fifo', guard_timeout)

        result = merge_lock.run_dequeue('plan-a')

        assert result['status'] == 'error', result
        assert 'simulated merge-queue guard timeout' in result['error'], result
