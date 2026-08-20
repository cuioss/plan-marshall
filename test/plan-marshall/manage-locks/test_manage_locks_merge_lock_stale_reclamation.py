#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Its sections, in order:

* Fixtures
* check — non-blocking holder read (never touches the FIFO queue)
* Stale reclamation (liveness via the shared _locks_core.holder_is_dead)
"""


from __future__ import annotations

import json
import time
from argparse import Namespace

from _manage_locks_merge_lock_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _make_live_plan,
    _stub_title_tokens,
    _TokenRecorder,
    _waiting_plan_ids,
    isolated_base,  # noqa: F401 — used by name, not by reference
    merge_lock,
)

# =============================================================================
# Fixtures
# =============================================================================


# =============================================================================
# check — non-blocking holder read (never touches the FIFO queue)
# =============================================================================


class TestCheck:
    def test_check_free_when_no_lock_file(self, isolated_base: dict) -> None:
        result = merge_lock.run_check(Namespace(plan_id='plan-a'))
        assert result['status'] == 'free'
        # check never creates the lock file.
        assert not isolated_base['lock_path'].exists()

    def test_check_held_reports_holder(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_check(Namespace(plan_id='plan-b'))
        assert result['status'] == 'held'
        assert result['holder_plan_id'] == 'plan-a'

    def test_check_reports_self_held(self, isolated_base: dict) -> None:
        """check reports the global lock state, including a self-held lock."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_check(Namespace(plan_id='plan-a'))
        assert result['status'] == 'held'
        assert result['holder_plan_id'] == 'plan-a'

    def test_check_does_not_mutate_lock(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        before = isolated_base['lock_path'].read_text(encoding='utf-8')

        merge_lock.run_check(Namespace(plan_id='plan-b'))

        after = isolated_base['lock_path'].read_text(encoding='utf-8')
        assert before == after

    def test_check_does_not_touch_the_fifo_queue(self, isolated_base: dict) -> None:
        """``check`` is a pure holder read — it never enqueues the querying plan or
        otherwise mutates ``merge-queue.json``."""
        # No acquire yet: check against a free lock must not create the queue.
        merge_lock.run_check(Namespace(plan_id='plan-a'))
        assert not isolated_base['queue_path'].exists()

        # With a held lock, check by a third plan must not enqueue that plan.
        merge_lock.run_acquire(Namespace(plan_id='holder', timeout=5.0))
        before = _waiting_plan_ids(isolated_base['queue_path'])
        merge_lock.run_check(Namespace(plan_id='observer'))
        assert _waiting_plan_ids(isolated_base['queue_path']) == before
        assert 'observer' not in _waiting_plan_ids(isolated_base['queue_path'])


# =============================================================================
# Stale reclamation (liveness via the shared _locks_core.holder_is_dead)
# =============================================================================


class TestStaleReclamation:
    def test_dead_holder_lock_is_reclaimed(self, isolated_base: dict) -> None:
        """A lock whose holder has no live plan dir is reclaimable by the front."""
        # plan-dead acquires but its plan dir is NEVER created → dead holder. It
        # is dequeued so the next acquirer becomes the FIFO front.
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        merge_lock._dequeue_fifo('plan-dead')

        # plan-b acquires: it is the front, observes the held lock, finds the
        # holder dead, reclaims.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['holder'] == 'plan-b'
        assert result['reclaimed'] is True
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_live_holder_lock_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A lock whose holder IS live is NOT reclaimable (serializes/blocks)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-live', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-live')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-live'

    def test_liveness_uses_shared_core_predicate(self, isolated_base: dict) -> None:
        """Liveness is the imported shared-core predicate, exercised through the
        observable acquire behaviour. A ghost holder (no plan dir) is dead
        (reclaimable) once it is dequeued so the next plan is the front."""
        # A holder whose plan dir is missing is dead → reclaimable.
        merge_lock.run_acquire(Namespace(plan_id='ghost', timeout=5.0))
        merge_lock._dequeue_fifo('ghost')
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True

    def test_dead_waiter_is_pruned_from_the_fifo_front(self, isolated_base: dict) -> None:
        """A crashed waiter whose plan dir is gone is pruned from the FIFO queue so
        its stale entry never wedges the front. A live plan behind a dead front
        entry is promoted to the front and admitted."""
        base = isolated_base['base']
        # 'crashed' is enqueued at the front but has NO plan dir → dead waiter.
        # 'live' is enqueued behind it and IS live.
        _make_live_plan(base, 'live')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'crashed', 'ts': 1.0},
                {'plan_id': 'live', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )

        # 'live' polls: the dead 'crashed' front entry is pruned, promoting 'live'
        # to the front → admitted.
        result = merge_lock.run_acquire(Namespace(plan_id='live', timeout=5.0))
        assert result['admission'] == 'admitted'
        assert result['holder'] == 'live'
        # The dead waiter is gone from the queue.
        assert 'crashed' not in _waiting_plan_ids(isolated_base['queue_path'])

    def test_worktree_resident_holder_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A holder whose plan dir has been MOVED into its worktree (executing or
        mid-finalize, absent on the main checkout) is LIVE and MUST NOT be
        reclaimed. Checking only the main checkout would steal the lock from an
        actively-finalizing session and break serialization."""
        base = isolated_base['base']
        # plan-wt holds the lock and its plan dir lives ONLY in the worktree.
        merge_lock.run_acquire(Namespace(plan_id='plan-wt', timeout=5.0))
        (base / 'worktrees' / 'plan-wt' / '.plan' / 'local' / 'plans' / 'plan-wt').mkdir(parents=True)
        # A concurrent acquirer must serialize (block), NOT reclaim.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-wt'

    def test_timeout_zero_is_non_blocking(self, isolated_base: dict) -> None:
        """``--timeout 0`` is a valid non-blocking try: against a live holder it
        blocks IMMEDIATELY (acquire never waits internally for the queue case)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        start = time.monotonic()
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0))
        elapsed = time.monotonic() - start
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # Non-blocking: returns essentially instantly (no internal wait loop).
        assert elapsed < 5.0
