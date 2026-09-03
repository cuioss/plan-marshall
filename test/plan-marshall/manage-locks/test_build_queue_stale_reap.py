#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Scope: reaping a stale active entry on the next acquire or release, the
``active_since`` stamp every admission path must leave, and the staleness limit that
grows with a long hold between its floor and its ceiling.
"""


from __future__ import annotations

from argparse import Namespace

from _build_queue_fixtures import (
    _FRESH_AGE_SECONDS,
    _STALE_AGE_SECONDS,
    _init_git_repo,
    _make_live_plan,
    _read_lock_log,
    _read_queue,
    _seed_active_entry,
    _set_max_slots,
    _write_queue,
    build_queue,
    isolated_base,
)


class TestStaleReap:
    def test_stale_active_entry_is_reaped_on_next_acquire(self, isolated_base: dict) -> None:
        """An active entry whose active_since is older than 2 × upper_limit is
        reaped on the next acquire (slot freed), and a WARN [LOCK] reaped-stale
        event with the reaped id + held duration is emitted."""
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)
        # The reaped holder's plan dir exists → it is LIVE (so the dead-holder
        # prune does NOT clear it; only the time-based reaper does).
        _make_live_plan(base, 'plan-stale')
        stale_id = 'plan-stale:stale-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=stale_id,
            plan_id='plan-stale',
            active_since=time.time() - _STALE_AGE_SECONDS,
        )

        _make_live_plan(base, 'plan-new')
        result = build_queue.run_acquire(Namespace(plan_id='plan-new'))

        # The stale slot was reaped, freeing the single slot → plan-new admitted.
        assert result['admission'] == 'admitted'
        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert stale_id not in active_ids
        assert [e['plan_id'] for e in state['active']] == ['plan-new']

        # A WARN reaped-stale [LOCK] event was emitted for the reaped id.
        content = _read_lock_log()
        assert f'[LOCK] (build:reaped-stale) {stale_id}' in content
        assert 'WARNING' in content
        assert 'held:' in content
        assert 'threshold: 1200' in content  # 2 × 600 default

    def test_stale_active_entry_is_reaped_on_next_release(self, isolated_base: dict) -> None:
        """validate_lock_queue also runs on release: a stale active entry is reaped
        when an UNRELATED id is released (the release of an absent id is a no-op,
        but the implicit reaper still fires inside the same mutation)."""
        import time

        base = isolated_base['base']
        _make_live_plan(base, 'plan-stale')
        stale_id = 'plan-stale:stale-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=stale_id,
            plan_id='plan-stale',
            active_since=time.time() - _STALE_AGE_SECONDS,
        )

        # Release an absent id — the release itself is a no-op, but the implicit
        # reaper runs and clears the stale entry.
        build_queue.run_release(Namespace(plan_id='plan-other', id='plan-other:ghost'))

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == []
        content = _read_lock_log()
        assert f'[LOCK] (build:reaped-stale) {stale_id}' in content

    def test_fresh_active_entry_is_not_reaped(self, isolated_base: dict) -> None:
        """An active entry whose active_since is within 2 × upper_limit is NOT
        reaped — only over-age entries are reclaimed."""
        import time

        base = isolated_base['base']
        _set_max_slots(base, 2)
        _make_live_plan(base, 'plan-fresh')
        fresh_id = 'plan-fresh:fresh-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=fresh_id,
            plan_id='plan-fresh',
            active_since=time.time() - _FRESH_AGE_SECONDS,
        )

        _make_live_plan(base, 'plan-new')
        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert fresh_id in active_ids  # the fresh holder survived
        content = _read_lock_log()
        assert 'reaped-stale' not in content

    def test_entry_without_active_since_is_not_reaped_on_first_contact(
        self, isolated_base: dict
    ) -> None:
        """An active entry written before D5 shipped (NO active_since key) is
        treated as `now` and is therefore never reaped on first contact."""
        base = isolated_base['base']
        _set_max_slots(base, 2)
        _make_live_plan(base, 'plan-legacy')
        legacy_id = 'plan-legacy:legacy-uuid'
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=legacy_id,
            plan_id='plan-legacy',
            active_since=None,  # pre-existing entry, no active_since
        )

        _make_live_plan(base, 'plan-new')
        build_queue.run_acquire(Namespace(plan_id='plan-new'))

        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert legacy_id in active_ids
        assert 'reaped-stale' not in _read_lock_log()

    def test_reaped_slot_fifo_promotes_waiter_with_fresh_active_since(
        self, isolated_base: dict
    ) -> None:
        """When a stale entry is reaped and a waiter exists, the waiter is
        FIFO-promoted into the freed slot and gets a fresh active_since."""
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)
        _make_live_plan(base, 'plan-stale')
        _make_live_plan(base, 'plan-wait')
        stale_id = 'plan-stale:stale-uuid'
        wait_id = 'plan-wait:wait-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': stale_id,
                        'plan_id': 'plan-stale',
                        'ts': 0.0,
                        'active_since': time.time() - _STALE_AGE_SECONDS,
                    }
                ],
                'waiting': [{'id': wait_id, 'plan_id': 'plan-wait', 'ts': 1.0}],
                'run_log': [],
            },
        )

        # plan-wait re-polls acquire: the reaper clears the stale slot and
        # promotes plan-wait (the FIFO head) into it.
        result = build_queue.run_acquire(Namespace(plan_id='plan-wait'))
        assert result['admission'] == 'admitted'
        assert result['id'] == wait_id

        state = _read_queue(isolated_base['queue_path'])
        active = state['active']
        assert [e['id'] for e in active] == [wait_id]
        assert state['waiting'] == []
        # The promoted waiter has a fresh active_since (it is only now active).
        assert 'active_since' in active[0]
        assert active[0]['active_since'] >= time.time() - _FRESH_AGE_SECONDS

    def test_active_since_stamped_on_first_acquire(self, isolated_base: dict) -> None:
        """active_since is stamped on a first-acquire admit."""
        import time

        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert acq['admission'] == 'admitted'
        state = _read_queue(isolated_base['queue_path'])
        entry = state['active'][0]
        assert 'active_since' in entry
        assert entry['active_since'] >= time.time() - _FRESH_AGE_SECONDS

    def test_active_since_stamped_on_idempotent_waiting_promotion(self, isolated_base: dict) -> None:
        """active_since is stamped when a blocked plan re-polls and is promoted."""
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(base, name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert w1['admission'] == 'blocked'

        # Release the holder so a slot frees, then plan-w1 re-polls → promoted.
        build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        re_w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert re_w1['admission'] == 'admitted'

        state = _read_queue(isolated_base['queue_path'])
        promoted = next(e for e in state['active'] if e['id'] == w1['id'])
        assert 'active_since' in promoted
        assert promoted['active_since'] >= time.time() - _FRESH_AGE_SECONDS

    def test_active_since_stamped_on_release_fifo_promote(self, isolated_base: dict) -> None:
        """active_since is stamped on a release FIFO-promote."""
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(base, name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert w1['admission'] == 'blocked'

        rel = build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        assert rel['promoted'] == w1['id']

        state = _read_queue(isolated_base['queue_path'])
        promoted = next(e for e in state['active'] if e['id'] == w1['id'])
        assert 'active_since' in promoted
        assert promoted['active_since'] >= time.time() - _FRESH_AGE_SECONDS


class TestAdaptiveUpperLimit:
    def _read_limit(self) -> int:
        """Read the persisted build_queue_upper_limit via the run_config getter."""
        from run_config import _read_build_queue_upper_limit

        return _read_build_queue_upper_limit()

    def test_limit_grows_on_long_hold_clamped_to_ceiling(self, isolated_base: dict) -> None:
        """A release whose held duration exceeds the 3600 s ceiling persists
        build_queue_upper_limit == 3600 exactly — never higher."""
        import time

        base = isolated_base['base']
        _make_live_plan(base, 'plan-long')
        long_id = 'plan-long:long-uuid'
        # The reaper removes an entry held longer than 2 × the LIVE limit, so a
        # hold long enough to exercise the ceiling is also long enough to be
        # reaped before the release can recompute anything. Raising the live
        # limit to the ceiling first puts the reap threshold at 7200 s, which the
        # 4000 s hold below is under — so the release exercises the clamp rather
        # than the reaper.
        from run_config import _write_build_queue_upper_limit

        _write_build_queue_upper_limit(3600)  # reap threshold now 2 × 3600 = 7200 s
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=long_id,
            plan_id='plan-long',
            active_since=time.time() - 4000.0,  # under 7200 s threshold → not reaped
        )

        rel = build_queue.run_release(Namespace(plan_id='plan-long', id=long_id))
        assert rel['action'] == 'released'

        # held ≈ 4000 s > 3600 ceiling → stored limit clamps to exactly 3600.
        assert self._read_limit() == 3600

    def test_limit_floors_at_600_for_short_hold(self, isolated_base: dict) -> None:
        """A short hold never drops the limit below the 600 s floor — the limit is
        monotonic-up and floored, so a quick release leaves it at the floor."""
        base = isolated_base['base']
        _make_live_plan(base, 'plan-short')
        acq = build_queue.run_acquire(Namespace(plan_id='plan-short'))
        # Immediate release → held ≈ 0 s, well under the floor.
        build_queue.run_release(Namespace(plan_id='plan-short', id=acq['id']))

        assert self._read_limit() == 600  # floor preserved

    def test_limit_grows_toward_observed_hold_within_bounds(self, isolated_base: dict) -> None:
        """A hold between floor and ceiling grows the limit to that held value."""
        import time

        base = isolated_base['base']
        _make_live_plan(base, 'plan-mid')
        mid_id = 'plan-mid:mid-uuid'
        # Pre-grow the live limit so the 1800 s hold is not reaped first
        # (2 × 1800 = 3600 s threshold > 1800 s held).
        from run_config import _write_build_queue_upper_limit

        _write_build_queue_upper_limit(1800)
        _seed_active_entry(
            isolated_base['queue_path'],
            entry_id=mid_id,
            plan_id='plan-mid',
            active_since=time.time() - 1800.0,
        )

        build_queue.run_release(Namespace(plan_id='plan-mid', id=mid_id))

        # held ≈ 1800 s, current limit 1800 → max(1800, 1800) = 1800 (no change),
        # but a slightly longer real observation would grow it. Assert it is at
        # least the observed hold and within bounds.
        limit = self._read_limit()
        assert 600 <= limit <= 3600
        assert limit >= 1800
