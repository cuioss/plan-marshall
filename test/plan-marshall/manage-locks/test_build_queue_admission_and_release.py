#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Its sections, in order:

* Admit under capacity / block at capacity
* Release frees + FIFO-promotes
* Idempotent acquire — FIFO position preserved across re-polls (b8c531 / e738fe)
"""

from __future__ import annotations

import json
import os
import time
from argparse import Namespace
from pathlib import Path

from _build_queue_fixtures import (
    _init_git_repo,
    _make_live_plan,
    _read_queue,
    _set_max_slots,
    build_queue,
    isolated_base,
)

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
        _set_max_slots(isolated_base['home'], 2)
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
        # No machine-config.json → default 5. Five admits, the sixth blocks.
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

    def test_configured_machine_global_cap_is_honored(self, isolated_base: dict) -> None:
        _set_max_slots(isolated_base['home'], 1)
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
        _set_max_slots(isolated_base['home'], 1)
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
        _set_max_slots(isolated_base['home'], 1)
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
        _set_max_slots(isolated_base['home'], 1)
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

    def test_re_acquire_non_head_waiter_stays_blocked_when_one_slot_frees(self, isolated_base: dict) -> None:
        """FIFO order is honoured when a single slot frees: only the oldest
        waiting plan is promotable. A non-head waiter that re-polls stays blocked
        even though a slot is free, because an earlier waiter holds priority."""
        _set_max_slots(isolated_base['home'], 2)
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
# D4: a slot is held per build INVOCATION, not per plan
# =============================================================================
# ``acquire`` used to hand a second concurrent build of the same plan the
# EXISTING active id: both builds then ran on one entry, and the first release
# freed the slot while the second was still running. The acquire now carries a
# per-invocation token; a re-poll with its own token keeps its FIFO place, and a
# second invocation of the same plan is a second entry. Without a token the
# identity falls back to the plan id, which is exactly the pre-token behaviour a
# re-poll of a legacy caller needs.

_DOCUMENTED_RESULT_FIELDS = (
    'id',
    'admission',
    'active_count',
    'waiting_count',
    'warnings',
    'max_slots',
    'max_slots_source',
    'cap_agreement',
    'cap_compared_count',
    'cap_unstamped_count',
    'cap_disagreement',
)


class TestPerInvocationToken:
    def test_two_tokens_for_one_plan_are_two_invocations(self, isolated_base: dict) -> None:
        """At cap 1 the second invocation of one plan is BLOCKED, keeps its own
        FIFO place across a re-poll, and is promoted when the first releases."""
        _set_max_slots(isolated_base['home'], 1)
        _make_live_plan(isolated_base['base'], 'plan-a')

        first = build_queue.run_acquire(Namespace(plan_id='plan-a', token='token-1'))
        second = build_queue.run_acquire(Namespace(plan_id='plan-a', token='token-2'))

        assert first['admission'] == 'admitted'
        assert second['admission'] == 'blocked', 'a second invocation is its own queue entry'
        assert second['id'] != first['id']

        # A re-poll with its OWN token keeps the entry, in place.
        again = build_queue.run_acquire(Namespace(plan_id='plan-a', token='token-2'))
        assert again['id'] == second['id']
        assert again['admission'] == 'blocked'
        state = _read_queue(isolated_base['queue_path'])
        assert [e['id'] for e in state['waiting']] == [second['id']]

        # Releasing the first invocation promotes the second.
        build_queue.run_release(Namespace(plan_id='plan-a', id=first['id']))
        promoted = build_queue.run_acquire(Namespace(plan_id='plan-a', token='token-2'))
        assert promoted['admission'] == 'admitted'
        assert promoted['id'] == second['id']

    def test_the_documented_result_fields_survive_the_token(self, isolated_base: dict) -> None:
        """Every field a consumer reads is still reported, with its own value."""
        result = build_queue.run_acquire(Namespace(plan_id='plan-a', token='token-1'))

        for field in _DOCUMENTED_RESULT_FIELDS:
            assert field in result, f'{field} is a documented result field'
        assert result['id'].startswith('plan-a:')
        assert result['warnings'] == []
        assert result['active_count'] == 1
        assert result['waiting_count'] == 0

    def test_a_legacy_entry_without_a_token_is_not_matched_by_a_token_acquire(self, isolated_base: dict) -> None:
        """An entry written before the token existed is a different invocation.

        It is left untouched (existing reap/prune still owns it) rather than
        adopted, because adopting it would put two invocations on one slot —
        the very defect this deliverable removes.
        """
        _set_max_slots(isolated_base['home'], 5)
        # A LIVE plan dir, so the dead-holder prune does not reclaim the legacy
        # entry before the token logic can be observed.
        _make_live_plan(isolated_base['base'], 'plan-a')
        legacy = {
            'id': 'plan-a:legacy-uuid',
            'plan_id': 'plan-a',
            'ts': 1.0,
            'active_since': time.time(),
            'project_root': str(isolated_base['main_repo']),
            'admitted_under_max_slots': 5,
        }
        (isolated_base['queue_path']).write_text(
            json.dumps({'active': [legacy], 'waiting': [], 'run_log': []}), encoding='utf-8'
        )

        result = build_queue.run_acquire(Namespace(plan_id='plan-a', token='token-1'))

        assert result['id'] != legacy['id'], 'the token names a new invocation, never the legacy entry'
        state = _read_queue(isolated_base['queue_path'])
        assert len(state['active']) == 2
        assert {e['id'] for e in state['active']} == {legacy['id'], result['id']}

    def test_a_tokenless_acquire_keeps_the_legacy_plan_identity(self, isolated_base: dict) -> None:
        """Without a token the identity is the plan id — a re-poll is idempotent.

        This is the compatibility half of the change: an older caller that knows
        nothing of tokens keeps the behaviour it had.
        """
        _make_live_plan(isolated_base['base'], 'plan-a')

        first = build_queue.run_acquire(Namespace(plan_id='plan-a'))
        second = build_queue.run_acquire(Namespace(plan_id='plan-a'))

        assert second['id'] == first['id']
        assert second['admission'] == 'admitted'


# =============================================================================
# D3: the per-directory lock's FIFO
# =============================================================================
# The lock is a queue, and "queue, never reject" only holds if a LATER waiter can
# never block an EARLIER one. Ordering is list position among one directory's
# waiters; a set-membership test ("is anybody else waiting for this directory?")
# makes two waiters block each other forever, which is the failure these pin.


def _directory_namespace(directory: Path, ticket: str, plan_id: str = 'plan-a') -> Namespace:
    return Namespace(directory=str(directory.resolve()), plan_id=plan_id, command='module-tests', pid=os.getpid(), ticket=ticket)


class TestDirectoryLockFifo:
    def test_two_waiters_are_admitted_in_arrival_order(self, isolated_base: dict) -> None:
        directory = isolated_base['base'] / 'W1'
        directory.mkdir(parents=True, exist_ok=True)

        holder = build_queue.run_directory_acquire(_directory_namespace(directory, 't-holder', 'holder'))
        first = build_queue.run_directory_acquire(_directory_namespace(directory, 't-first', 'first'))
        second = build_queue.run_directory_acquire(_directory_namespace(directory, 't-second', 'second'))

        assert holder['admission'] == 'admitted'
        assert first['admission'] == 'blocked'
        assert second['admission'] == 'blocked'

        build_queue.run_directory_release(Namespace(directory=str(directory.resolve()), ticket='t-holder'))

        # The LATER waiter polls first and must stay blocked behind the earlier
        # one; the earlier waiter is then admitted.
        again_second = build_queue.run_directory_acquire(_directory_namespace(directory, 't-second', 'second'))
        again_first = build_queue.run_directory_acquire(_directory_namespace(directory, 't-first', 'first'))

        assert again_second['admission'] == 'blocked', 'a later waiter must not jump the queue'
        assert again_first['admission'] == 'admitted'

    def test_a_waiting_ticket_is_removed_on_release(self, isolated_base: dict) -> None:
        directory = isolated_base['base'] / 'W1'
        directory.mkdir(parents=True, exist_ok=True)
        build_queue.run_directory_acquire(_directory_namespace(directory, 't-holder', 'holder'))
        build_queue.run_directory_acquire(_directory_namespace(directory, 't-waiter', 'waiter'))

        build_queue.run_directory_release(Namespace(directory=str(directory.resolve()), ticket='t-waiter'))

        state = _read_queue(isolated_base['queue_path'])
        assert state.get('directory_waiters') == []
        assert str(directory.resolve()) in state['directory_locks'], "a waiter's release must not free the holder"


class TestDirectoryRecovery:
    """`directory status` / `directory clear` — the operator escape hatch.

    A build killed past its own release can leave a holder whose pid still reads
    as alive. Nothing in admission may steal that directory (it would corrupt a
    live build's output tree), so the recovery is explicit and operator-invoked.
    """

    def _stage_holder(self, isolated_base: dict, directory: Path, **overrides) -> None:
        record = {
            'plan_id': 'dead-build',
            'command': 'module-tests',
            'pid': 999_999,
            'acquired_at': time.time(),
            'ticket': 't-dead',
            **overrides,
        }
        (isolated_base['queue_path']).write_text(
            json.dumps({'active': [], 'waiting': [], 'run_log': [], 'directory_locks': {str(directory.resolve()): record}}),
            encoding='utf-8',
        )

    def test_status_reports_the_holder_and_marks_a_dead_pid_reclaimable(self, isolated_base: dict) -> None:
        directory = isolated_base['base'] / 'W1'
        directory.mkdir(parents=True, exist_ok=True)
        self._stage_holder(isolated_base, directory)

        result = build_queue.run_directory_status(Namespace(directory=str(directory)))

        assert result['status'] == 'success'
        assert len(result['holders']) == 1
        holder = result['holders'][0]
        assert holder['plan_id'] == 'dead-build'
        assert holder['pid'] == 999_999
        assert holder['reclaimable'] is True
        assert result['reclaimable_count'] == 1

    def test_clear_reclaims_a_dead_holder_without_force(self, isolated_base: dict) -> None:
        directory = isolated_base['base'] / 'W1'
        directory.mkdir(parents=True, exist_ok=True)
        self._stage_holder(isolated_base, directory)

        result = build_queue.run_directory_clear(Namespace(directory=str(directory), force=False))

        assert result['action'] == 'cleared'
        assert result['cleared_holder']['plan_id'] == 'dead-build'
        assert _read_queue(isolated_base['queue_path']).get('directory_locks') == {}

    def test_clear_refuses_a_live_holder_without_force(self, isolated_base: dict) -> None:
        directory = isolated_base['base'] / 'W1'
        directory.mkdir(parents=True, exist_ok=True)
        self._stage_holder(isolated_base, directory, pid=os.getpid(), acquired_at=time.time())

        result = build_queue.run_directory_clear(Namespace(directory=str(directory), force=False))

        assert result['action'] == 'refused_live'
        assert str(directory.resolve()) in _read_queue(isolated_base['queue_path'])['directory_locks']

    def test_force_clears_a_live_holder_on_the_operators_assertion(self, isolated_base: dict) -> None:
        directory = isolated_base['base'] / 'W1'
        directory.mkdir(parents=True, exist_ok=True)
        self._stage_holder(isolated_base, directory, pid=os.getpid(), acquired_at=time.time())

        result = build_queue.run_directory_clear(Namespace(directory=str(directory), force=True))

        assert result['action'] == 'cleared'
        assert _read_queue(isolated_base['queue_path']).get('directory_locks') == {}

    def test_clear_of_an_unheld_directory_is_an_idempotent_noop(self, isolated_base: dict) -> None:
        result = build_queue.run_directory_clear(Namespace(directory=str(isolated_base['base'] / 'nobody'), force=False))

        assert result['status'] == 'success'
        assert result['action'] == 'noop'
