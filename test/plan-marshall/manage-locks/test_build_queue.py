#!/usr/bin/env python3
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
* **Main-anchored resolution** — ``build-queue.json`` resolves to the MAIN
  checkout regardless of caller cwd (the fourth ADR-002 bounded-exception corpus).
* **Shared-core delegation** — liveness is the imported
  :func:`_locks_core.holder_is_dead` and resolution the imported
  :func:`marketplace_paths.resolve_main_anchored_path`; neither is re-implemented.

Real-parallel obligations (§5 (i) + (iii) + (iv)): the no-over-admit boundary (i),
the no-double-promote/lost-entry FIFO property (iii), and dead-holder reclaim
without evicting a live holder (iv) are asserted under REAL spawned-subprocess
contention — N processes racing the SAME main-anchored ``build-queue.json`` via
the CLI entry point — not sequential calls. A sequential test can never exercise
the kernel-serialized read-modify-write race window these invariants guard.

Isolation: every test runs against an isolated ``PLAN_BASE_DIR`` staged under
``tmp_path`` so the suite never contends for the real ``.plan/build-queue.json``
under ``-n auto``. Under ``PLAN_BASE_DIR`` the queue resolves to
``<PLAN_BASE_DIR>/build-queue.json``, holder plan dirs resolve to
``<PLAN_BASE_DIR>/plans/{holder}``, and marshal.json resolves to
``<PLAN_BASE_DIR>/marshal.json``.
"""

from __future__ import annotations

import json
from argparse import Namespace
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'build_queue.py')

build_queue = load_script_module('plan-marshall', 'manage-locks', 'build_queue.py', 'build_queue_under_test')


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — main stand-in)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/build-queue.json  (queue resolves here)
        tmp_path/main/.plan/local/marshal.json      (max_slots config resolves here)
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {'base': base, 'queue_path': base / 'build-queue.json'}


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _set_max_slots(base: Path, max_slots: int) -> None:
    """Write a marshal.json with the configured ``build_queue.max_slots``."""
    (base / 'marshal.json').write_text(
        json.dumps({'build_queue': {'max_slots': max_slots}}), encoding='utf-8'
    )


def _read_queue(queue_path: Path) -> dict:
    """Read the persisted queue state as a dict."""
    return json.loads(queue_path.read_text(encoding='utf-8'))


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
# Shared-core delegation guard — no re-implemented liveness / resolution
# =============================================================================


class TestSharedCoreDelegation:
    def test_imports_shared_liveness_predicate(self) -> None:
        assert hasattr(build_queue, 'holder_is_dead')

    def test_imports_shared_rmw(self) -> None:
        assert hasattr(build_queue, 'rmw_json')

    def test_imports_shared_resolver(self) -> None:
        assert hasattr(build_queue, 'resolve_main_anchored_path')

    def test_no_inline_git_common_dir_in_source(self) -> None:
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert '--git-common-dir' not in src


# =============================================================================
# Main-anchored resolution (the fourth deliberate exception corpus)
# =============================================================================


class TestMainAnchoredResolution:
    def test_queue_resolves_to_main_even_when_cwd_is_a_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = build_queue._resolve_queue_path()
        assert resolved == main_base / 'build-queue.json'
        assert worktree / '.plan' / 'local' / 'build-queue.json' != resolved

    def test_acquire_writes_to_main_base_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        assert result['admission'] == 'admitted'
        assert (main_base / 'build-queue.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'build-queue.json').exists()


# =============================================================================
# §5 (i) — no over-admit at the slot boundary, under REAL spawned-process
# contention (the make-or-break property)
# =============================================================================


class TestConcurrentAdmissionBoundary:
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

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'race-{i}',
                env_overrides=env_overrides,
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

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'edge-{i}',
                env_overrides=env_overrides,
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

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'mass-{i}',
                env_overrides=env_overrides,
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

        env_overrides = {'PLAN_BASE_DIR': str(base)}

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
