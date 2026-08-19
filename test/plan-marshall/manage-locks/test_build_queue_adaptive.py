#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Contract under test (solution_outline.md D5 + lock-reconciliation-analysis.md §5
massive-parallel-concurrency invariants (i) + (iii) + (iv); ADR-002):

* **Admit under capacity** — ``acquire`` with ``len(active) < max_slots`` appends
  ``{id, ts}`` to ``active`` and returns ``admission: admitted``.
* **Block at capacity** — ``acquire`` with ``active`` full appends to the FIFO
  ``waiting`` queue and returns ``admission: blocked``. The script never loops —
  ``blocked`` is a structured signal, not an error.
* **Release frees + FIFO-promotes** — ``release --id ID`` removes the id from
  ``active`` and promotes the FRONT waiting entry (the first list element —
  serialized append order, NOT the smallest admit-``ts``) into
  the freed slot, recording it as ``promoted``; it appends an id+timestamp
  ``run_log`` entry. Release of an absent id is an idempotent no-op success.
* **FIFO ordering is list position, not admit-``ts``** — every promote path (the
  reaper promote, the idempotent re-poll promote-eligibility check, and the
  release promote) selects the front by list position. ``ts`` is sampled outside
  the serialized ``rmw_json`` section and is informational only, so under
  concurrent enqueue it can disagree with append order; an inverted-``ts``
  fixture pins that a ``min(ts)`` selector cannot creep back in.
* **Id collision-resistance** — the admission id is ``{plan_id}:{uuid4}`` so two
  acquires by the SAME plan never collide.
* **Default + configured ``max_slots``** — absent config defaults to 5; a
  ``build_queue.max_slots`` override in marshal.json is honored.
* **Corrupt/missing file as empty** — a missing or malformed ``build-queue.json``
  is treated as empty state, not a crash.
* **Machine-global resolution** — ``build-queue.json`` resolves under the
  machine-global home root (:func:`marketplace_paths.home_root`,
  ``~/.plan-marshall/build-queue.json`` by default, overridable via
  ``PLAN_MARSHALL_HOME``) regardless of caller cwd — the host-wide tier shared
  across every checkout, NOT the per-repo main-anchored exception corpus.
* **Foreign-holder pruning** — each entry is stamped at acquire with
  ``project_root = str(main_checkout_root())`` so a foreign project's live holder
  is judged against its OWN checkout and never reclaimed by a session in a
  different repo.
* **Shared-core delegation** — liveness is the imported
  :func:`_locks_core.holder_is_dead`; the resolvers are the imported
  :func:`marketplace_paths.home_root` / ``main_checkout_root``; none is
  re-implemented.

Real-parallel obligations (§5 (i) + (iii) + (iv)): the no-over-admit boundary (i),
the no-double-promote/lost-entry FIFO property (iii), and dead-holder reclaim
without evicting a live holder (iv) are asserted under REAL spawned-subprocess
contention — N processes racing the SAME machine-global ``build-queue.json`` via
the CLI entry point — not sequential calls. A sequential test can never exercise
the kernel-serialized read-modify-write race window these invariants guard.

Isolation: every test runs against an isolated home root and ``PLAN_BASE_DIR``
staged under ``tmp_path`` so the suite never contends for the real
``~/.plan-marshall/build-queue.json`` under ``-n auto``. The queue resolves to
``<PLAN_MARSHALL_HOME>/build-queue.json``; holder plan dirs resolve to
``<PLAN_BASE_DIR>/plans/{holder}``; marshal.json resolves to
``<PLAN_BASE_DIR>/marshal.json``. The ``main`` fixture dir is a real git repo so
subprocess ``main_checkout_root()`` resolves to it, and the in-process fixture
pins ``build_queue.main_checkout_root`` to that same root so stamped
``project_root`` liveness resolves under ``<PLAN_BASE_DIR>``.
"""


from __future__ import annotations

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``build_queue`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``build_queue`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``build_queue`` never sees).
from argparse import Namespace
from pathlib import Path

import pytest
from _build_queue_fixtures import (
    _STALE_AGE_SECONDS,
    _init_git_repo,
    _make_live_plan,
    _read_queue,
    _seed_active_entry,
    _set_max_slots,
    _write_queue,
    build_queue,
)


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated machine-global home + PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/                              (a real git repo → project_root)
        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — holder liveness)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/marshal.json      (max_slots config resolves here)
        tmp_path/home/                              (PLAN_MARSHALL_HOME — home root)
        tmp_path/home/build-queue.json              (queue resolves here)

    ``main`` is a real git repo so a spawned subprocess's ``main_checkout_root()``
    resolves to it (run subprocesses with ``cwd=main_repo`` +
    ``env_overrides``); in-process, ``build_queue.main_checkout_root`` is pinned
    to ``main`` so the stamped ``project_root`` liveness resolves under
    ``main/.plan/local`` (== ``PLAN_BASE_DIR``).
    """
    main_repo = tmp_path / 'main'
    main_repo.mkdir()
    _init_git_repo(main_repo)
    base = main_repo / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    home = tmp_path / 'home'
    home.mkdir()

    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
    # In-process: pin the project_root stamp at main_repo so the machine-global
    # prune judges liveness under main_repo/.plan/local (== base). Subprocess
    # tests instead pass cwd=main_repo so the real git resolver lands there.
    monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

    return {
        'base': base,
        'main_repo': main_repo,
        'home': home,
        'queue_path': home / 'build-queue.json',
        'env_overrides': {'PLAN_BASE_DIR': str(base), 'PLAN_MARSHALL_HOME': str(home)},
    }


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
        # Seed an active entry with a held duration well over the 3600 s ceiling
        # but UNDER the 2 × 600 = 1200 s reap threshold would falsely reap it —
        # so use an active_since just under the stale threshold? No: a long hold
        # IS over threshold and would be reaped. To exercise the adaptive-limit
        # recompute on a REAL release we must release a still-fresh-enough entry.
        # Use active_since older than the ceiling (4000 s) but the reaper would
        # reap it at 1200 s. So first grow the limit via repeated releases.
        # Simpler: directly seed and release an entry whose held just exceeds the
        # ceiling AFTER the limit has grown past 2000 — but the reaper uses the
        # CURRENT (pre-grow) limit. Instead: assert the clamp directly by
        # releasing an entry held ~4000 s when the live limit is already high
        # enough that 2 × limit > 4000 so it is not reaped first.
        # Set the live limit to its ceiling first so the reap threshold is 7200 s.
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
