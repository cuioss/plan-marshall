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
from _build_queue_fixtures import _init_git_repo, _make_live_plan, _read_queue, _set_max_slots, build_queue


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
# Admit under capacity / block at capacity
# =============================================================================


class TestAdmission:
    def test_acquire_under_capacity_is_admitted(self, isolated_base: dict) -> None:
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['status'] == 'success', result
        assert result['admission'] == 'admitted'
        assert result['id'].startswith('plan-a:')
        assert result['active_count'] == 1
        assert result['waiting_count'] == 0

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [result['id']]
        assert state['waiting'] == []

    def test_acquire_at_capacity_is_blocked_and_queued(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 2)
        # Two live holders fill both slots.
        for name in ('plan-a', 'plan-b'):
            _make_live_plan(isolated_base['base'], name)
            build_queue.run_acquire(Namespace(plan_id=name))

        _make_live_plan(isolated_base['base'], 'plan-c')
        result = build_queue.run_acquire(Namespace(plan_id='plan-c'))

        assert result['admission'] == 'blocked'
        assert result['active_count'] == 2
        assert result['waiting_count'] == 1

        state = _read_queue(isolated_base['queue_path'])
        assert len(state['active']) == 2
        assert [e['id'] for e in state['waiting']] == [result['id']]

    def test_default_max_slots_is_five(self, isolated_base: dict) -> None:
        # No marshal.json → default 5. Five admits, the sixth blocks.
        for i in range(5):
            name = f'plan-{i}'
            _make_live_plan(isolated_base['base'], name)
            res = build_queue.run_acquire(Namespace(plan_id=name))
            assert res['admission'] == 'admitted', res
            assert res['max_slots'] == 5

        _make_live_plan(isolated_base['base'], 'plan-6')
        sixth = build_queue.run_acquire(Namespace(plan_id='plan-6'))
        assert sixth['admission'] == 'blocked'
        assert sixth['max_slots'] == 5

    def test_configured_max_slots_override_is_honored(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        _make_live_plan(isolated_base['base'], 'plan-a')
        first = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert first['admission'] == 'admitted'
        assert first['max_slots'] == 1

        _make_live_plan(isolated_base['base'], 'plan-b')
        second = build_queue.run_acquire(Namespace(plan_id='plan-b'))
        assert second['admission'] == 'blocked'

    def test_id_is_plan_id_colon_uuid_and_collision_resistant(self, isolated_base: dict) -> None:
        a = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        b = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        # Both ids carry the plan_id prefix but differ in the uuid suffix.
        assert a['id'].startswith('plan-a:')
        assert b['id'].startswith('plan-a:')
        assert a['id'] != b['id']


# =============================================================================
# Release frees + FIFO-promotes
# =============================================================================


class TestRelease:
    def test_release_frees_slot_and_records_run_log(self, isolated_base: dict) -> None:
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        rel = build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'
        assert rel['active_count'] == 0

        state = _read_queue(isolated_base['queue_path'])
        assert state['active'] == []
        # A run-log entry is appended for the released id.
        assert [e['id'] for e in state['run_log']] == [acq['id']]

    def test_release_fifo_promotes_oldest_waiting_entry(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        # One LIVE holder fills the single slot; two more LIVE plans queue behind
        # it (live so the slot holder is never pruned as a dead holder).
        for name in ('plan-held', 'plan-w1', 'plan-w2'):
            _make_live_plan(isolated_base['base'], name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        first_wait = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        second_wait = build_queue.run_acquire(Namespace(plan_id='plan-w2'))
        assert first_wait['admission'] == 'blocked'
        assert second_wait['admission'] == 'blocked'

        rel = build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        # The OLDEST waiting entry (plan-w1) is promoted, not plan-w2.
        assert rel['promoted'] == first_wait['id']
        assert rel['active_count'] == 1
        assert rel['waiting_count'] == 1

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [first_wait['id']]
        assert [e['id'] for e in state['waiting']] == [second_wait['id']]

    def test_release_absent_id_is_idempotent_noop(self, isolated_base: dict) -> None:
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id='plan-a:ghost-uuid'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'noop'
        assert rel['promoted'] is None

    def test_release_no_waiting_does_not_promote(self, isolated_base: dict) -> None:
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))
        assert rel['promoted'] is None

    def test_noop_release_does_not_append_run_log_entry(self, isolated_base: dict) -> None:
        """A no-op release (the id was NOT present in active/waiting) leaves the
        run_log untouched — only a REAL release accretes an audit entry, so an
        absent-id retry storm cannot grow build-queue.json without bound."""
        # One real release seeds the log with a single entry.
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))
        seeded = _read_queue(isolated_base['queue_path'])['run_log']
        assert [e['id'] for e in seeded] == [acq['id']]

        # A no-op release of an absent id is a success but appends nothing.
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id='plan-a:ghost-uuid'))
        assert rel['action'] == 'noop'

        after = _read_queue(isolated_base['queue_path'])['run_log']
        assert [e['id'] for e in after] == [acq['id']], after

    def test_run_log_is_pruned_to_most_recent_100_entries(self, isolated_base: dict) -> None:
        """The run_log is a bounded audit tail: after each real release it is
        pruned to the most recent 100 entries, so a long-lived cluster cannot let
        build-queue.json grow indefinitely. Across 150 real releases the log holds
        exactly the last 100 ids in append order (the oldest 50 are dropped)."""
        released_ids: list[str] = []
        for i in range(150):
            plan = f'plan-{i}'
            acq = build_queue.run_acquire(Namespace(plan_id=plan))
            build_queue.run_release(Namespace(plan_id=plan, id=acq['id']))
            released_ids.append(acq['id'])

        run_log = _read_queue(isolated_base['queue_path'])['run_log']
        assert len(run_log) == 100
        # The retained window is the most recent 100 releases, in append order.
        assert [e['id'] for e in run_log] == released_ids[-100:]


# =============================================================================
# Idempotent acquire — FIFO position preserved across re-polls (b8c531 / e738fe)
# =============================================================================


class TestIdempotentAcquire:
    def test_re_acquire_active_holder_reuses_id_without_new_entry(self, isolated_base: dict) -> None:
        """A plan already holding an active slot re-acquires its SAME id with no
        duplicate active entry — acquire is idempotent for an active holder."""
        _make_live_plan(isolated_base['base'], 'plan-a')
        first = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert first['admission'] == 'admitted'

        second = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert second['admission'] == 'admitted'
        assert second['id'] == first['id']
        assert second['active_count'] == 1

        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [first['id']]
        assert state['waiting'] == []

    def test_re_acquire_blocked_plan_keeps_fifo_position(self, isolated_base: dict) -> None:
        """The FIFO-preservation guarantee: a blocked plan that re-polls acquire
        KEEPS its waiting entry in place (same id, same FIFO position) instead of
        being shuffled to the back of the queue on each poll."""
        _set_max_slots(isolated_base['base'], 1)
        # plan-held fills the single slot; plan-w1 then plan-w2 queue behind it.
        for name in ('plan-held', 'plan-w1', 'plan-w2'):
            _make_live_plan(isolated_base['base'], name)
        build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        w2 = build_queue.run_acquire(Namespace(plan_id='plan-w2'))
        assert w1['admission'] == 'blocked'
        assert w2['admission'] == 'blocked'

        # plan-w1 re-polls while still blocked — it must NOT move behind plan-w2.
        re_w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert re_w1['admission'] == 'blocked'
        assert re_w1['id'] == w1['id']
        assert re_w1['waiting_count'] == 2

        state = _read_queue(isolated_base['queue_path'])
        # The waiting order is unchanged: plan-w1 still ahead of plan-w2.
        assert [e['id'] for e in state['waiting']] == [w1['id'], w2['id']]

    def test_re_acquire_blocked_plan_admitted_when_slot_frees(self, isolated_base: dict) -> None:
        """Once the holder releases, the oldest waiting plan's next re-poll is
        admitted (reusing its existing id) — the re-poll promotes the FIFO head
        without a release-then-re-acquire round trip."""
        _set_max_slots(isolated_base['base'], 1)
        for name in ('plan-held', 'plan-w1', 'plan-w2'):
            _make_live_plan(isolated_base['base'], name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        w2 = build_queue.run_acquire(Namespace(plan_id='plan-w2'))

        # The holder releases. FIFO-promote moves plan-w1 into the freed slot.
        build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))

        # plan-w1 re-polls and finds itself already promoted to active (the
        # release promoted it); its id is unchanged and it is admitted.
        re_w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert re_w1['admission'] == 'admitted'
        assert re_w1['id'] == w1['id']

        # plan-w2 re-polls but the slot is taken by plan-w1 → still blocked.
        re_w2 = build_queue.run_acquire(Namespace(plan_id='plan-w2'))
        assert re_w2['admission'] == 'blocked'
        assert re_w2['id'] == w2['id']

    def test_re_acquire_non_head_waiter_stays_blocked_when_one_slot_frees(
        self, isolated_base: dict
    ) -> None:
        """FIFO order is honoured when a single slot frees: only the oldest
        waiting plan is promotable. A non-head waiter that re-polls stays blocked
        even though a slot is free, because an earlier waiter holds priority."""
        _set_max_slots(isolated_base['base'], 2)
        for name in ('plan-h1', 'plan-h2', 'plan-w1', 'plan-w2'):
            _make_live_plan(isolated_base['base'], name)
        h1 = build_queue.run_acquire(Namespace(plan_id='plan-h1'))
        build_queue.run_acquire(Namespace(plan_id='plan-h2'))
        w1 = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        w2 = build_queue.run_acquire(Namespace(plan_id='plan-w2'))
        assert w1['admission'] == 'blocked'
        assert w2['admission'] == 'blocked'

        # Free exactly ONE slot by releasing plan-h1. The release already
        # FIFO-promotes plan-w1, so plan-w1 is now active. plan-w2 re-polls: only
        # one slot total is free-able and it went to plan-w1 → plan-w2 blocked.
        build_queue.run_release(Namespace(plan_id='plan-h1', id=h1['id']))
        re_w2 = build_queue.run_acquire(Namespace(plan_id='plan-w2'))
        assert re_w2['admission'] == 'blocked'
        assert re_w2['id'] == w2['id']

        state = _read_queue(isolated_base['queue_path'])
        active_plans = {e['plan_id'] for e in state['active']}
        assert active_plans == {'plan-h2', 'plan-w1'}
        assert [e['id'] for e in state['waiting']] == [w2['id']]
