#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.
"""


from __future__ import annotations

import json
from argparse import Namespace

from _manage_locks_merge_lock_fixtures import (
    _make_live_plan,
    # Fixtures — resolved by pytest, not referenced by name:
    _stub_title_tokens,  # noqa: F401
    _waiting_plan_ids,
    isolated_base,  # noqa: F401
    merge_lock,
)

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
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        w1 = merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        w2 = merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert w1['admission'] == 'blocked'
        assert w2['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

        # w1 re-polls while still blocked — it must NOT move behind w2.
        re_w1 = merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        assert re_w1['admission'] == 'blocked'
        # The FIFO order is unchanged: w1 still ahead of w2.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

    def test_repoll_does_not_re_append_or_grow_queue(self, isolated_base: dict) -> None:
        """Re-polling an already-queued plan is idempotent on the queue itself — the
        ``waiting`` depth does not grow, the plan appears exactly once."""
        for name in ('front', 'waiter'):
            _make_live_plan(isolated_base['base'], name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='waiter', timeout=5.0))

        # Re-poll the waiter several times.
        for _ in range(3):
            res = merge_lock.run_acquire(Namespace(plan_id='waiter', timeout=5.0))
            assert res['admission'] == 'blocked'

        waiting = _waiting_plan_ids(isolated_base['queue_path'])
        # The waiter appears exactly once despite the repeated re-polls.
        assert waiting.count('waiter') == 1
        assert waiting == ['front', 'waiter']

    def test_front_repoll_against_foreign_live_holder_keeps_front_position(
        self, isolated_base: dict
    ) -> None:
        """The FIFO FRONT itself can be blocked when a FOREIGN live holder holds
        the lock (e.g. a reentrant holder that pre-existed the queue). The front's
        re-poll keeps its front position so it is first in line on release."""
        base = isolated_base['base']
        _make_live_plan(base, 'holder')
        _make_live_plan(base, 'front')
        # 'holder' holds the lock but is NOT in the FIFO queue; 'front' is the
        # queue front behind a foreign live holder.
        merge_lock.run_acquire(Namespace(plan_id='holder', timeout=5.0))
        # Drop holder from the queue so 'front' is the genuine FIFO front while
        # 'holder' still holds the lock file.
        merge_lock._dequeue_fifo('holder')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [{'plan_id': 'front', 'ts': 1.0}]}), encoding='utf-8'
        )

        first = merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        assert first['admission'] == 'blocked'
        assert first['blocking_plan_id'] == 'holder'
        # Re-poll: front stays the front, still blocked by the live foreign holder.
        again = merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
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
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

        # The holder releases — it is dequeued, advancing w1 to the front.
        rel = merge_lock.run_release(Namespace(plan_id='front'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['w1', 'w2']

        # w1 (now the front) re-polls and is admitted; w2 stays blocked behind it.
        re_w1 = merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        assert re_w1['admission'] == 'admitted'
        assert re_w1['holder'] == 'w1'
        re_w2 = merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert re_w2['admission'] == 'blocked'
        assert re_w2['blocking_plan_id'] == 'w1'

    def test_non_front_waiter_stays_blocked_until_its_turn(self, isolated_base: dict) -> None:
        """FIFO order is honoured across releases: a non-front waiter that re-polls
        stays blocked even though it could win the kernel race, because an earlier
        waiter holds priority and must be served first."""
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))

        # Holder releases → w1 advances to front. The lock file is now free.
        merge_lock.run_release(Namespace(plan_id='front'))
        assert not isolated_base['lock_path'].exists()

        # w2 (non-front) re-polls: the lock is free, but w2 is behind w1 → blocked.
        re_w2 = merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
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
        merge_lock.run_acquire(Namespace(plan_id='a', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='b', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='c', timeout=5.0))

        served: list[str] = ['a']  # 'a' was admitted first.

        # Drain b then c in FIFO order.
        merge_lock.run_release(Namespace(plan_id='a'))
        b = merge_lock.run_acquire(Namespace(plan_id='b', timeout=5.0))
        assert b['admission'] == 'admitted'
        served.append('b')

        merge_lock.run_release(Namespace(plan_id='b'))
        c = merge_lock.run_acquire(Namespace(plan_id='c', timeout=5.0))
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
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))

        rel = merge_lock.run_release(Namespace(plan_id='front'))
        assert rel['action'] == 'released'
        # Front dequeued; w1 remains → post-removal depth is 1.
        assert rel['waiting_count'] == 1
