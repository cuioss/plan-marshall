#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: F811 — tests take the imported fixture as a parameter
"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.
"""


from __future__ import annotations

from argparse import Namespace

from _build_queue_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _STALE_AGE_SECONDS,
    _init_git_repo,
    _make_live_plan,
    _read_queue,
    _set_max_slots,
    _write_queue,
    build_queue,
    isolated_base,
)

# =============================================================================
# FIFO front is list position, NOT admit-ts (inverted-ts regression)
# =============================================================================


class TestFifoFrontIsListPositionNotMinTs:
    """Regression: the FIFO front is the FIRST ``waiting`` entry (serialized
    arrival order), NOT the entry with the smallest admit-``ts``.

    ``ts`` is sampled from the wall clock BEFORE ``run_acquire`` enters the
    serialized ``rmw_json`` section, so under concurrent enqueue it can disagree
    with the order the appends actually landed: subprocess A can sample an earlier
    ``ts`` than B yet have its append run AFTER B's. A ``min(ts)`` / ``sorted(...,
    key=ts)`` selector then elects a different entry than the file's first, and
    the queue carries two disagreeing notions of "front" — the FIFO-fairness
    divergence its sibling ``merge_lock._fifo_front`` already fixed.

    Every fixture below appends ``[first, second]`` but writes INVERTED admit-``ts``
    (``first.ts = 2.0`` > ``second.ts = 1.0``), so a min-ts selector would wrongly
    elect ``second``. Each of the three promote call sites is covered separately —
    a single test would leave the other two unpinned. Every assertion is
    timing-free: ``ts`` values are written directly into the fixture file, never
    sampled from the wall clock, and no test depends on process concurrency.
    """

    @staticmethod
    def _seed_inverted_ts_queue(isolated_base: dict, *, active: list[dict]) -> tuple[str, str]:
        """Seed the queue with append order [first, second] and inverted admit-ts.

        Returns the ``(first_id, second_id)`` waiting-entry ids. The caller supplies
        the ``active`` list so each promote path can stage its own holder shape.
        """
        base = isolated_base['base']
        for name in ('plan-first', 'plan-second'):
            _make_live_plan(base, name)
        first_id = 'plan-first:first-uuid'
        second_id = 'plan-second:second-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': active,
                # Append order [first, second]; ts INVERTED (first.ts > second.ts).
                'waiting': [
                    {'id': first_id, 'plan_id': 'plan-first', 'ts': 2.0},
                    {'id': second_id, 'plan_id': 'plan-second', 'ts': 1.0},
                ],
                'run_log': [],
            },
        )
        return first_id, second_id

    def test_release_promotes_list_front_not_min_ts(self, isolated_base: dict) -> None:
        """``run_release``'s FIFO promote elects the list front, not min-ts.

        Covers the release promote site. A min-ts selector would have promoted
        ``plan-second`` (ts 1.0) over the genuine append-order front ``plan-first``.
        """
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)
        _make_live_plan(base, 'plan-held')
        held_id = 'plan-held:held-uuid'
        first_id, second_id = self._seed_inverted_ts_queue(
            isolated_base,
            active=[{'id': held_id, 'plan_id': 'plan-held', 'ts': 0.0, 'active_since': time.time()}],
        )

        result = build_queue.run_release(Namespace(plan_id='plan-held', id=held_id))

        assert result['action'] == 'released', result
        assert result['promoted'] == first_id, result

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [first_id]
        assert [e['id'] for e in state['waiting']] == [second_id]

    def test_acquire_repoll_promotes_list_front_not_min_ts(self, isolated_base: dict) -> None:
        """``run_acquire``'s idempotent re-poll promote-eligibility check uses list
        position, not min-ts.

        Covers the acquire re-poll promote site. With exactly one free slot, only
        the append-order front is promote-eligible: ``plan-first`` re-polls to
        ``admitted`` while ``plan-second`` (smaller ts, later in append order)
        re-polls to ``blocked``.
        """
        base = isolated_base['base']
        # max_slots 1 with an EMPTY active list → exactly one free slot.
        _set_max_slots(base, 1)
        first_id, second_id = self._seed_inverted_ts_queue(isolated_base, active=[])

        # plan-second re-polls first: it is NOT the list front, so it stays blocked
        # even though its ts is the smallest.
        second = build_queue.run_acquire(Namespace(plan_id='plan-second'))
        assert second['admission'] == 'blocked', second
        assert second['id'] == second_id

        # plan-first re-polls: it IS the list front, so it takes the free slot.
        first = build_queue.run_acquire(Namespace(plan_id='plan-first'))
        assert first['admission'] == 'admitted', first
        assert first['id'] == first_id

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [first_id]
        assert [e['id'] for e in state['waiting']] == [second_id]

    def test_reaper_promotes_list_front_not_min_ts(self, isolated_base: dict) -> None:
        """``validate_lock_queue``'s post-reap promote elects the list front, not
        min-ts.

        Covers the reaper promote site. The over-age holder is reaped, freeing the
        single slot, and the append-order front ``plan-first`` is promoted into it
        — a min-ts selector would have promoted ``plan-second``.
        """
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)
        _make_live_plan(base, 'plan-stale')
        stale_id = 'plan-stale:stale-uuid'
        first_id, second_id = self._seed_inverted_ts_queue(
            isolated_base,
            active=[
                {
                    'id': stale_id,
                    'plan_id': 'plan-stale',
                    'ts': 0.0,
                    'active_since': time.time() - _STALE_AGE_SECONDS,
                }
            ],
        )

        # An unrelated no-op release fires the implicit reaper, which reaps the
        # over-age holder and promotes the FIFO front into the freed slot.
        build_queue.run_release(Namespace(plan_id='plan-other', id='plan-other:ghost'))

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [first_id]
        assert [e['id'] for e in state['waiting']] == [second_id]

    def test_fifo_front_n_slices_by_list_position(self, isolated_base: dict) -> None:
        """The ``_fifo_front_n`` helper slices by list position and clamps n <= 0.

        A direct unit assertion on the helper so the invariant is pinned at its
        source as well as through the three call sites above.
        """
        waiting = [
            {'id': 'a', 'plan_id': 'plan-a', 'ts': 9.0},
            {'id': 'b', 'plan_id': 'plan-b', 'ts': 1.0},
            {'id': 'c', 'plan_id': 'plan-c', 'ts': 5.0},
        ]

        # Selection follows list position, NOT ascending ts (which would be b,c,a).
        assert [e['id'] for e in build_queue._fifo_front_n(waiting, 1)] == ['a']
        assert [e['id'] for e in build_queue._fifo_front_n(waiting, 2)] == ['a', 'b']
        # n beyond the list length yields the whole list, never an IndexError.
        assert [e['id'] for e in build_queue._fifo_front_n(waiting, 99)] == ['a', 'b', 'c']
        # A caller at capacity (free <= 0) promotes nothing.
        assert build_queue._fifo_front_n(waiting, 0) == []
        assert build_queue._fifo_front_n(waiting, -1) == []
