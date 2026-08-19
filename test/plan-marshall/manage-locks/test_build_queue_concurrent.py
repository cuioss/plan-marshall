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

from argparse import Namespace
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from _build_queue_fixtures import (
    SCRIPT_PATH,
    _init_git_repo,
    _make_live_plan,
    _read_queue,
    _set_max_slots,
    build_queue,
)
from toon_parser import parse_toon

from conftest import run_script


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


# =============================================================================
# §5 (i) — no over-admit at the slot boundary, under REAL spawned-process
# contention (the make-or-break property)
# =============================================================================


class TestConcurrentAdmissionBoundary:
    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_admits_exactly_max_slots(self, isolated_base: dict) -> None:
        """§5 (i): with ``max_slots = k`` and ``k + m`` spawned subprocesses racing
        the SAME main-anchored build-queue.json via the CLI, EXACTLY ``k`` are
        admitted and ``m`` are blocked — never ``k + 1``. The serialized
        read-modify-write is the sole arbiter of the slot boundary."""
        base = isolated_base['base']
        k = 3
        total = 8  # k admitted + (total - k) blocked
        _set_max_slots(base, k)
        for i in range(total):
            _make_live_plan(base, f'race-{i}')

        env_overrides = isolated_base['env_overrides']
        main_repo = isolated_base['main_repo']

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'race-{i}',
                env_overrides=env_overrides,
                cwd=str(main_repo),
                timeout=30,
            )

        with ThreadPoolExecutor(max_workers=total) as pool:
            results = list(pool.map(_acquire, range(total)))

        parsed = [parse_toon(r.stdout) for r in results]
        admitted = [p for p in parsed if p.get('admission') == 'admitted']
        blocked = [p for p in parsed if p.get('admission') == 'blocked']

        # EXACTLY k admitted, the rest blocked — never over-admit.
        assert len(admitted) == k, parsed
        assert len(blocked) == total - k, parsed

        # The persisted state agrees: exactly k active, no duplicates.
        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        assert len(active_ids) == k
        assert len(set(active_ids)) == k

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_n_plus_one_racers_never_admit_n_plus_one(self, isolated_base: dict) -> None:
        """§5 (i), tightest boundary: with ``max_slots = N`` and exactly ``N + 1``
        spawned subprocesses racing the SAME main-anchored build-queue.json, EXACTLY
        ``N`` are admitted and the single extra racer is blocked — never ``N + 1``.
        A single off-by-one in the check-then-act window would over-admit the one
        extra contender, so the N+1 margin is the make-or-break stressor for the
        'never N+1' property the serialized read-modify-write guarantees."""
        base = isolated_base['base']
        n = 5
        total = n + 1
        _set_max_slots(base, n)
        for i in range(total):
            _make_live_plan(base, f'edge-{i}')

        env_overrides = isolated_base['env_overrides']
        main_repo = isolated_base['main_repo']

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'edge-{i}',
                env_overrides=env_overrides,
                cwd=str(main_repo),
                timeout=30,
            )

        with ThreadPoolExecutor(max_workers=total) as pool:
            results = list(pool.map(_acquire, range(total)))

        parsed = [parse_toon(r.stdout) for r in results]
        admitted = [p for p in parsed if p.get('admission') == 'admitted']
        blocked = [p for p in parsed if p.get('admission') == 'blocked']

        # EXACTLY n admitted, exactly one blocked — the over-admit-by-one failure
        # mode would yield n + 1 admitted and zero blocked.
        assert len(admitted) == n, parsed
        assert len(blocked) == 1, parsed

        # The persisted state agrees: exactly n active, no duplicate ids, and the
        # one waiting entry is the single blocked racer.
        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        waiting_ids = [e['id'] for e in state['waiting']]
        assert len(active_ids) == n
        assert len(set(active_ids)) == n
        assert len(waiting_ids) == 1
        assert waiting_ids == [blocked[0]['id']]
        # Active and waiting partitions are disjoint — no id is both.
        assert set(active_ids).isdisjoint(set(waiting_ids))

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_massive_parallel_admits_exactly_max_slots(self, isolated_base: dict) -> None:
        """§5 (i), massive-parallel: a large ``max_slots = k`` with a large excess of
        spawned subprocesses (``k + m``, all racing the SAME main-anchored
        build-queue.json via the CLI) admits EXACTLY ``k`` and blocks the remaining
        ``m`` — never ``k + 1`` and never fewer than ``k``. Sustained high
        contention is the regression stressor for the serialized slot boundary:
        every admitted id is distinct, every blocked id is queued, and the union
        accounts for all ``k + m`` racers with no entry lost or duplicated."""
        base = isolated_base['base']
        k = 5
        total = 24  # k admitted + (total - k) blocked, heavy oversubscription
        _set_max_slots(base, k)
        for i in range(total):
            _make_live_plan(base, f'mass-{i}')

        env_overrides = isolated_base['env_overrides']
        main_repo = isolated_base['main_repo']

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'mass-{i}',
                env_overrides=env_overrides,
                cwd=str(main_repo),
                timeout=60,
            )

        with ThreadPoolExecutor(max_workers=total) as pool:
            results = list(pool.map(_acquire, range(total)))

        parsed = [parse_toon(r.stdout) for r in results]
        admitted = [p for p in parsed if p.get('admission') == 'admitted']
        blocked = [p for p in parsed if p.get('admission') == 'blocked']

        # EXACTLY k admitted, the rest blocked — never over-admit under load.
        assert len(admitted) == k, parsed
        assert len(blocked) == total - k, parsed

        # Every racer produced a decisive admit/block verdict — none errored out.
        assert len(admitted) + len(blocked) == total, parsed

        # The persisted state is internally consistent: exactly k distinct active
        # ids, total - k distinct waiting ids, partitions disjoint, and the union
        # of all persisted ids equals the full set of returned admission ids (no
        # entry lost or double-counted under the race).
        state = _read_queue(isolated_base['queue_path'])
        active_ids = [e['id'] for e in state['active']]
        waiting_ids = [e['id'] for e in state['waiting']]
        assert len(active_ids) == k
        assert len(set(active_ids)) == k
        assert len(waiting_ids) == total - k
        assert len(set(waiting_ids)) == total - k
        assert set(active_ids).isdisjoint(set(waiting_ids))
        all_returned_ids = {p['id'] for p in parsed}
        assert set(active_ids) | set(waiting_ids) == all_returned_ids


# =============================================================================
# §5 (iii) — concurrent release + FIFO promote never double-promotes or loses a
# waiting entry, under REAL spawned-process contention
# =============================================================================


class TestConcurrentReleaseFifoPromote:
    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_releases_promote_each_waiter_exactly_once(self, isolated_base: dict) -> None:
        """§5 (iii): k active holders + w waiting entries; releasing all k active
        slots concurrently promotes each freed slot to exactly ONE distinct
        waiting entry — no entry promoted twice, none dropped. The serialized
        read-modify-write guarantees the FIFO promote is race-free."""
        base = isolated_base['base']
        k = 4
        _set_max_slots(base, k)

        # Fill k active slots (live holders so they are never pruned).
        active_ids = []
        for i in range(k):
            name = f'active-{i}'
            _make_live_plan(base, name)
            res = build_queue.run_acquire(Namespace(plan_id=name))
            assert res['admission'] == 'admitted'
            active_ids.append((name, res['id']))

        # Queue w waiting entries behind the full active set.
        w = 4
        waiting_ids = []
        for i in range(w):
            name = f'wait-{i}'
            _make_live_plan(base, name)
            res = build_queue.run_acquire(Namespace(plan_id=name))
            assert res['admission'] == 'blocked'
            waiting_ids.append(res['id'])

        env_overrides = isolated_base['env_overrides']
        main_repo = isolated_base['main_repo']

        def _release(item: tuple[str, str]):
            name, entry_id = item
            return run_script(
                SCRIPT_PATH,
                'release',
                '--plan-id',
                name,
                '--id',
                entry_id,
                env_overrides=env_overrides,
                cwd=str(main_repo),
                timeout=30,
            )

        with ThreadPoolExecutor(max_workers=k) as pool:
            results = list(pool.map(_release, active_ids))

        parsed = [parse_toon(r.stdout) for r in results]
        promoted = [p['promoted'] for p in parsed if p.get('promoted')]

        # Each release that freed a slot promoted exactly one waiter; with k
        # releases and w == k waiters, every waiter is promoted exactly once.
        assert Counter(promoted) == Counter(dict.fromkeys(waiting_ids, 1)), promoted
        # No waiter promoted twice.
        assert len(promoted) == len(set(promoted))

        # Final state: all w waiters now active, waiting queue empty, no original
        # active id remains active.
        state = _read_queue(isolated_base['queue_path'])
        final_active = {e['id'] for e in state['active']}
        assert final_active == set(waiting_ids), state
        assert state['waiting'] == []
