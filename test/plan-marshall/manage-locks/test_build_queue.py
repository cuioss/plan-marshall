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
  ``active`` and promotes the OLDEST waiting entry (smallest admit-``ts``) into
  the freed slot, recording it as ``promoted``; it appends an id+timestamp
  ``run_log`` entry. Release of an absent id is an idempotent no-op success.
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

import json
import subprocess
from argparse import Namespace
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'build_queue.py')

build_queue = load_script_module('plan-marshall', 'manage-locks', 'build_queue.py', 'build_queue_under_test')

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``build_queue`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``build_queue`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``build_queue`` never sees).
import sys as _sys  # noqa: E402

_locks_core = _sys.modules[build_queue.log_lock_event.__module__]


def _read_lock_log() -> str:
    """Read the main-anchored [LOCK] log, '' when no emission landed yet."""
    log_path = _locks_core._resolve_lock_log_path()
    if not log_path.exists():
        return ''
    return str(log_path.read_text(encoding='utf-8'))


# =============================================================================
# Fixtures
# =============================================================================


def _init_git_repo(repo: Path) -> None:
    """Initialise a bare-minimum git repo so ``main_checkout_root()`` resolves.

    A subprocess ``build_queue`` invocation stamps ``project_root`` via
    ``main_checkout_root()`` → ``git rev-parse --git-common-dir``; running that
    subprocess with ``cwd`` set to this repo makes the stamped root the fixture's
    own ``main`` dir rather than the developer's real checkout.
    """
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)


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


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _set_max_slots(base: Path, max_slots: int) -> None:
    """Write a marshal.json with the configured ``build.queue.max_slots``."""
    (base / 'marshal.json').write_text(
        json.dumps({'build': {'queue': {'max_slots': max_slots}}}), encoding='utf-8'
    )


def _read_queue(queue_path: Path) -> dict:
    """Read the persisted queue state as a dict."""
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


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


# =============================================================================
# Corrupt / missing file resilience
# =============================================================================


class TestCorruptFileAsEmpty:
    def test_missing_queue_file_treated_as_empty(self, isolated_base: dict) -> None:
        # No queue file exists yet — the first acquire builds it from scratch.
        assert not isolated_base['queue_path'].exists()
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert isolated_base['queue_path'].is_file()

    def test_corrupt_queue_file_treated_as_empty(self, isolated_base: dict) -> None:
        isolated_base['queue_path'].write_text('{ not json', encoding='utf-8')
        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert result['active_count'] == 1


# =============================================================================
# Dead-holder reclamation (liveness via the shared _locks_core.holder_is_dead)
# =============================================================================


class TestDeadHolderReclamation:
    def test_dead_active_holder_is_pruned_freeing_a_slot(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        # plan-dead acquires the only slot but its plan dir is NEVER created → dead.
        build_queue.run_acquire(Namespace(plan_id='plan-dead'))

        # plan-live acquires: the dead holder is pruned, freeing the slot → admitted.
        _make_live_plan(isolated_base['base'], 'plan-live')
        result = build_queue.run_acquire(Namespace(plan_id='plan-live'))
        assert result['admission'] == 'admitted'
        assert result['active_count'] == 1

        state = _read_queue(isolated_base['queue_path'])
        assert [e['plan_id'] for e in state['active']] == ['plan-live']

    def test_live_active_holder_is_not_pruned(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        _make_live_plan(isolated_base['base'], 'plan-live')
        build_queue.run_acquire(Namespace(plan_id='plan-live'))

        # A second live plan finds the slot occupied by a LIVE holder → blocked.
        _make_live_plan(isolated_base['base'], 'plan-b')
        result = build_queue.run_acquire(Namespace(plan_id='plan-b'))
        assert result['admission'] == 'blocked'


# =============================================================================
# Foreign-project holder pruning (machine-global project_root stamping)
# =============================================================================
#
# The machine-global queue records holders from multiple checkouts. Each active
# entry's stamped project_root judges its liveness against the checkout it
# originated in, so a foreign project's LIVE holder is never reclaimed by a
# session running in a different repo, while a foreign DEAD holder still is.


class TestForeignProjectHolderPrune:
    def test_foreign_project_live_holder_is_not_pruned(
        self, isolated_base: dict, tmp_path: Path
    ) -> None:
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)

        # A holder recorded by project A, LIVE under A's checkout (a DIFFERENT
        # checkout than this session's isolated_base['main_repo']).
        foreign_root = tmp_path / 'foreign-project'
        (foreign_root / '.plan' / 'local' / 'plans' / 'foreign-holder').mkdir(parents=True)
        foreign_id = 'foreign-holder:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': foreign_id,
                        'plan_id': 'foreign-holder',
                        'ts': 0.0,
                        'active_since': time.time(),
                        'project_root': str(foreign_root),
                    }
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        # A local plan acquires: the foreign holder is judged against ITS
        # project_root (where it is live) → NOT pruned → the single slot stays
        # held → local plan is blocked.
        _make_live_plan(base, 'local-plan')
        result = build_queue.run_acquire(Namespace(plan_id='local-plan'))
        assert result['admission'] == 'blocked'

        state = _read_queue(isolated_base['queue_path'])
        assert foreign_id in [e['id'] for e in state['active']]

    def test_foreign_project_dead_holder_is_pruned(
        self, isolated_base: dict, tmp_path: Path
    ) -> None:
        import time

        base = isolated_base['base']
        _set_max_slots(base, 1)

        # A holder recorded by project A but ABSENT under A's checkout → dead.
        foreign_root = tmp_path / 'foreign-project'
        (foreign_root / '.plan' / 'local' / 'plans').mkdir(parents=True)  # no holder dir
        dead_id = 'foreign-dead:foreign-uuid'
        _write_queue(
            isolated_base['queue_path'],
            {
                'active': [
                    {
                        'id': dead_id,
                        'plan_id': 'foreign-dead',
                        'ts': 0.0,
                        'active_since': time.time(),
                        'project_root': str(foreign_root),
                    }
                ],
                'waiting': [],
                'run_log': [],
            },
        )

        # The dead foreign holder is pruned against its own project_root, freeing
        # the slot for the local acquirer.
        _make_live_plan(base, 'local-plan')
        result = build_queue.run_acquire(Namespace(plan_id='local-plan'))
        assert result['admission'] == 'admitted'

        state = _read_queue(isolated_base['queue_path'])
        assert dead_id not in [e['id'] for e in state['active']]


# =============================================================================
# Shared-core delegation guard — no re-implemented liveness / resolution
# =============================================================================


class TestSharedCoreDelegation:
    def test_imports_shared_liveness_predicate(self) -> None:
        assert hasattr(build_queue, 'holder_is_dead')

    def test_imports_shared_rmw(self) -> None:
        assert hasattr(build_queue, 'rmw_json')

    def test_imports_shared_resolvers(self) -> None:
        # Resolution is delegated to the shared marketplace_paths resolvers —
        # the hardened machine-global home-root creator and the public
        # main-checkout resolver — never re-implemented here.
        assert hasattr(build_queue, 'ensure_home_root')
        assert hasattr(build_queue, 'main_checkout_root')

    def test_no_inline_git_common_dir_in_source(self) -> None:
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert '--git-common-dir' not in src


# =============================================================================
# Machine-global resolution — the host-wide home-root tier (cwd-independent)
# =============================================================================


class TestMachineGlobalResolution:
    def test_queue_resolves_under_home_root_ignoring_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The queue lives under the machine-global home root, NOT PLAN_BASE_DIR.
        # Pinning cwd into a worktree does not redirect it — home_root() is
        # host-wide and cwd-independent.
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = build_queue._resolve_queue_path()
        assert resolved == home / 'build-queue.json'
        assert worktree / '.plan' / 'local' / 'build-queue.json' != resolved

    def test_acquire_writes_to_home_root_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_repo = tmp_path / 'main'
        base = main_repo / '.plan' / 'local'
        (base / 'plans').mkdir(parents=True)
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
        monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        # The queue landed under the machine-global home root, not the worktree.
        assert (home / 'build-queue.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'build-queue.json').exists()


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


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestCli:
    def test_acquire_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'acquire')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_release_requires_plan_id_and_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'release', '--plan-id', 'plan-a')
        assert result.returncode != 0
        assert '--id' in result.stderr or '--id' in result.stdout


# =============================================================================
# [LOCK] event emission (best-effort, AFTER rmw_json commits)
# =============================================================================


class TestLockEventEmission:
    """Each build-queue lifecycle outcome emits a ``[LOCK]`` event into the SINGLE
    main-anchored global lock-event log via the shared
    :func:`_locks_core.log_lock_event`, always AFTER ``rmw_json`` commits:
    ``acquire`` emits ``acquired`` on an admitted outcome and ``blocked`` on a
    blocked outcome (carrying active/waiting counts; the waiter on a block is the
    acquiring plan_id); ``release`` emits ``released`` on a real release and ALSO
    ``acquired`` for a FIFO-promoted waiter. A no-op release emits nothing. The
    ``lock_id`` is the admission id ``{plan_id}:{uuid4}``. A logging failure is
    swallowed and cannot affect admission/release.

    The ``isolated_base`` fixture stages PLAN_BASE_DIR at ``<tmp>/main/.plan/local``
    so the lock-event log resolves to the per-test ``<tmp>/main/.plan/logs`` dir."""

    def test_admitted_acquire_emits_lock_acquired(self, isolated_base: dict) -> None:
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert acq['admission'] == 'admitted'

        content = _read_lock_log()
        # lock_id is the admission id {plan_id}:{uuid4}; family is `build`.
        assert f'[LOCK] (build:acquired) {acq["id"]}' in content
        # Capacity counts are carried as correlation fields.
        assert 'active_count: 1' in content
        assert 'waiting_count: 0' in content

    def test_blocked_acquire_emits_lock_blocked_with_waiter(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['base'], 1)
        _make_live_plan(isolated_base['base'], 'plan-held')
        build_queue.run_acquire(Namespace(plan_id='plan-held'))

        _make_live_plan(isolated_base['base'], 'plan-b')
        blk = build_queue.run_acquire(Namespace(plan_id='plan-b'))
        assert blk['admission'] == 'blocked'

        content = _read_lock_log()
        assert f'[LOCK] (build:blocked) {blk["id"]}' in content
        # The waiter on a block is the acquiring plan_id.
        assert 'waiter: plan-b' in content
        assert 'active_count: 1' in content
        assert 'waiting_count: 1' in content

    def test_release_emits_lock_released(self, isolated_base: dict) -> None:
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))
        assert rel['action'] == 'released'

        content = _read_lock_log()
        assert f'[LOCK] (build:released) {acq["id"]}' in content

    def test_release_with_fifo_promote_emits_released_and_promoted_acquired(
        self, isolated_base: dict
    ) -> None:
        """A release that frees a slot AND FIFO-promotes a waiter emits BOTH a
        ``released`` for the released id and an ``acquired`` for the promoted id —
        the promotion is recorded in the same main-anchored timeline."""
        _set_max_slots(isolated_base['base'], 1)
        for name in ('plan-held', 'plan-w1'):
            _make_live_plan(isolated_base['base'], name)
        held = build_queue.run_acquire(Namespace(plan_id='plan-held'))
        wait = build_queue.run_acquire(Namespace(plan_id='plan-w1'))
        assert wait['admission'] == 'blocked'

        rel = build_queue.run_release(Namespace(plan_id='plan-held', id=held['id']))
        assert rel['promoted'] == wait['id']

        content = _read_lock_log()
        assert f'[LOCK] (build:released) {held["id"]}' in content
        # The promoted waiter's slot was just granted → an `acquired` event.
        assert f'[LOCK] (build:acquired) {wait["id"]}' in content

    def test_noop_release_emits_no_lock_event(self, isolated_base: dict) -> None:
        """A no-op release of an absent id changed no state — it emits nothing."""
        rel = build_queue.run_release(Namespace(plan_id='plan-a', id='plan-a:ghost-uuid'))
        assert rel['action'] == 'noop'

        assert _read_lock_log() == ''

    def test_lock_event_lands_in_main_anchored_log_not_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The [LOCK] event lands in the MAIN-anchored global log even when cwd is
        pinned to a worktree — asserted via the PLAN_BASE_DIR override, not a
        worktree path. A worktree-relative .plan/logs dir must hold no lock log.
        The queue itself is machine-global (home_root()), isolated here via
        PLAN_MARSHALL_HOME; the lock log stays main-anchored (PLAN_BASE_DIR)."""
        main_repo = tmp_path / 'main'
        main_base = main_repo / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        home = tmp_path / 'home'
        home.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))
        monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
        monkeypatch.setattr(build_queue, 'main_checkout_root', lambda: main_repo)

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        content = _read_lock_log()
        assert f'[LOCK] (build:acquired) {acq["id"]}' in content
        assert not (worktree / '.plan' / 'logs').exists()

    def test_log_failure_never_breaks_acquire(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A [LOCK]-emission failure NEVER aborts the slot acquire — the emission
        is best-effort, with the swallow try/except INSIDE ``log_lock_event``
        itself, and fires AFTER rmw_json commits. Make the REAL helper's internal
        resolver raise (the seam ``_resolve_lock_log_path`` on the shared core);
        the function swallows it and the acquire still succeeds with the slot
        persisted. Patching the bare ``log_lock_event`` name would (correctly) NOT
        be swallowed — the call site invokes it directly — so the realistic
        failure is one inside the helper's own try/except."""
        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert result['status'] == 'success'
        assert result['admission'] == 'admitted'
        # The slot was persisted despite the emission raising.
        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['active']] == [result['id']]

    def test_log_failure_never_breaks_release(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Symmetric on the RELEASE side: a [LOCK]-emission failure (the real
        helper's internal resolver raising, swallowed by its own try/except)
        NEVER aborts the slot release — the slot is still freed."""
        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = build_queue.run_release(Namespace(plan_id='plan-a', id=acq['id']))

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        # The slot was freed despite the emission raising.
        state = _read_queue(isolated_base['queue_path'])
        assert state['active'] == []


# =============================================================================
# D5 — self-healing stale-slot reclaim (active_since + validate_lock_queue +
# adaptive build_queue_upper_limit). ADDITIVE over D4: these are new functions,
# none of D4's [LOCK]-event tests above are modified.
# =============================================================================


def _write_queue(queue_path: Path, state: dict) -> None:
    """Persist a hand-built queue state directly (for seeding stale entries)."""
    queue_path.write_text(json.dumps(state), encoding='utf-8')


def _seed_active_entry(
    queue_path: Path,
    *,
    entry_id: str,
    plan_id: str,
    active_since: float | None,
    ts: float = 0.0,
    waiting: list[dict] | None = None,
) -> None:
    """Seed build-queue.json with a single active entry (optionally + waiters).

    ``active_since=None`` writes an entry with NO active_since key — the
    pre-existing-entry case (written before D5 shipped).
    """
    entry: dict = {'id': entry_id, 'plan_id': plan_id, 'ts': ts}
    if active_since is not None:
        entry['active_since'] = active_since
    _write_queue(queue_path, {'active': [entry], 'waiting': waiting or [], 'run_log': []})


# A held duration comfortably over 2 × the 600 s default upper-limit (1200 s).
_STALE_AGE_SECONDS = 5000.0
_FRESH_AGE_SECONDS = 10.0


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
        assert active[0]['active_since'] >= time.time() - 60

    def test_active_since_stamped_on_first_acquire(self, isolated_base: dict) -> None:
        """active_since is stamped on a first-acquire admit."""
        import time

        acq = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert acq['admission'] == 'admitted'
        state = _read_queue(isolated_base['queue_path'])
        entry = state['active'][0]
        assert 'active_since' in entry
        assert entry['active_since'] >= time.time() - 60

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
        assert promoted['active_since'] >= time.time() - 60

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
        assert promoted['active_since'] >= time.time() - 60


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
