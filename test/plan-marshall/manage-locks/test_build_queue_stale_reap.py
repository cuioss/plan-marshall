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
from pathlib import Path

import pytest
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
