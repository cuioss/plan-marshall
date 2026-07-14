#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the unified ``manage-locks/merge_lock.py`` — the single main-anchored
merge-to-main serializer fronted by a FIFO admission queue.

Contract under test (lock-reconciliation-analysis.md §4 behavioural-equivalence
criteria + §5 massive-parallel-concurrency invariants (ii) + (iv); the FIFO
merge-queue admission layer + its canonical contract in manage-locks/SKILL.md;
ADR-002):

* **Atomic acquire** — ``acquire`` creates the lock file via ``O_EXCL`` and
  records the holder ``plan_id`` in the file contents.
* **FIFO admission (fairness)** — ``acquire`` first FIFO-enqueues ``--plan-id``
  into ``merge-queue.json``; ONLY the FIFO-front plan (the oldest entry by
  admit-``ts``) is admission-eligible. A non-front plan returns
  ``admission: blocked`` WITHOUT attempting the ``O_EXCL`` create — it never
  contends the kernel race — even when the lock file is FREE.
* **Idempotent re-poll position preservation** — a plan already in the queue
  KEEPS its FIFO position on re-poll; it is never re-appended to the back, so a
  plan polling repeatedly never loses priority to a later-arriving plan.
* **Release advances the front** — ``release`` dequeues ``--plan-id`` from
  ``merge-queue.json`` so the next FIFO entry becomes the front and is admitted
  on its next re-poll.
* **No double-grant** — exactly one of N concurrent ``acquire`` calls holds the
  lock; the rest return ``status: blocked``. Two plans never both hold the lock.
* **``blocked`` still escalates** — a blocked admission returns ``status: blocked``
  + ``blocking_plan_id`` (when a foreign live holder holds the lock) +
  ``waiting_count``, so the Pre-Merge Gate's poll/backoff loop and last-resort
  orchestrator escalation fire. ``blocked`` is NOT a hard error (no ``error_code``).
* **Stale reclamation** — a lock whose recorded holder has no live plan dir (on
  main OR in its worktree) is reclaimable (``reclaimed: true``) by the FIFO-front
  plan; a lock whose holder IS live is NOT reclaimable.
* **Idempotent release** — ``release`` removes the lock so the next acquire
  succeeds; release is idempotent (already-free / foreign-holder → no-op success,
  the foreign holder's lock left intact) and ALWAYS dequeues the FIFO entry.
* **``check`` holder read** — ``check`` returns ``{free}`` when no lock file
  exists and ``{held, holder_plan_id}`` when one does, without creating or
  mutating the lock, and never touching the FIFO queue.
* **Holder liveness via the shared core** — liveness is the imported
  :func:`_locks_core.holder_is_dead`, NOT a re-implemented copy; both main and
  worktree paths are consulted.
* **Main-anchored resolution (the single exception)** — both the lock AND the
  FIFO queue resolve to the MAIN checkout regardless of caller cwd, even when cwd
  is pinned to a worktree fixture.

Real-parallel obligations (§5 (ii) + (iv)): the no-double-grant invariant (ii) and
the dead-holder-reclaim-without-evicting-a-live-holder invariant (iv) are BOTH
asserted under REAL spawned-subprocess contention — N processes racing the SAME
main-anchored ``merge.lock`` + ``merge-queue.json`` via the CLI entry point — not
sequential calls. A sequential test can never exercise the kernel ``O_EXCL`` race
window (ii), the FIFO enqueue read-modify-write race, nor the interleave between
the stale-holder unlink and the atomic re-create (iv).

Isolation (test-isolation lessons): every test runs against an isolated
``PLAN_BASE_DIR`` staged under ``tmp_path`` so the suite never contends for the
real ``.plan/merge.lock`` / ``.plan/merge-queue.json`` under ``-n auto``. Under
``PLAN_BASE_DIR`` the lock resolves to ``<PLAN_BASE_DIR>/merge.lock``, the queue
to ``<PLAN_BASE_DIR>/merge-queue.json``, and holder plan dirs to
``<PLAN_BASE_DIR>/plans/{holder}``.

Filename note: this file is named ``test_manage_locks_merge_lock.py`` rather than
``test_merge_lock.py`` because pytest's default ``prepend`` import mode requires
unique test-module basenames across the suite.
"""

from __future__ import annotations

import json
import time
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'merge_lock.py')

merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_under_test')

# Capture the REAL _push_title_token before the autouse _TokenRecorder stub
# replaces it, so the canonical-seam CLI-shape test below can exercise the
# actual icon-optional push wrapper (it resolves _run_executor as a module
# global, so a monkeypatch on merge_lock._run_executor still takes effect).
_REAL_PUSH_TITLE_TOKEN = merge_lock._push_title_token

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
import sys as _sys  # noqa: E402

_locks_core = _sys.modules[merge_lock.log_lock_event.__module__]


def _read_lock_log() -> str:
    """Read the main-anchored [LOCK] log, '' when no emission landed yet."""
    log_path = _locks_core._resolve_lock_log_path()
    if not log_path.exists():
        return ''
    return str(log_path.read_text(encoding='utf-8'))


def _read_queue(queue_path: Path) -> dict:
    """Read the persisted FIFO merge-queue state as a dict ('{}' when absent)."""
    if not queue_path.exists():
        return {}
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


def _waiting_plan_ids(queue_path: Path) -> list[str]:
    """Return the FIFO ``waiting`` plan_ids in stored (serialized arrival / list) order."""
    return [e['plan_id'] for e in _read_queue(queue_path).get('waiting', [])]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stage an isolated PLAN_BASE_DIR under tmp_path.

    Layout::

        tmp_path/main/.plan/local/                  (PLAN_BASE_DIR — main stand-in)
        tmp_path/main/.plan/local/plans/            (holder plan dirs resolve here)
        tmp_path/main/.plan/local/merge.lock        (the O_EXCL lock resolves here)
        tmp_path/main/.plan/local/merge-queue.json  (the FIFO queue resolves here)

    Sets PLAN_BASE_DIR to the main stand-in so the lock resolves to
    ``<base>/merge.lock``, the FIFO queue to ``<base>/merge-queue.json``, and
    ``holder_is_dead(holder)`` resolves the holder plan dir to
    ``<base>/plans/{holder}``.
    """
    base = tmp_path / 'main' / '.plan' / 'local'
    (base / 'plans').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return {
        'base': base,
        'lock_path': base / 'merge.lock',
        'queue_path': base / 'merge-queue.json',
    }


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


class _TokenRecorder:
    """Records the best-effort title-token set/clear/push calls so a test can
    assert WHAT was surfaced without spawning the real executor subprocess.

    Installed over the three module-level seams ``_set_title_token`` /
    ``_clear_title_token`` / ``_push_title_token`` — the same seam-mock approach
    used by ``test_build_queue.py`` for the D6 wrapper.
    """

    def __init__(self) -> None:
        self.set_states: list[str] = []
        self.cleared: list[str] = []
        self.pushed_icons: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, state: self.set_states.append(state))
        monkeypatch.setattr(merge_lock, '_clear_title_token', lambda p: self.cleared.append(p))
        # icon is optional: a glyph push (acquire) records the icon; a plain
        # icon-less repaint (the clear path) records None.
        monkeypatch.setattr(
            merge_lock, '_push_title_token', lambda _p, icon=None: self.pushed_icons.append(icon)
        )


@pytest.fixture(autouse=True)
def _stub_title_tokens(monkeypatch: pytest.MonkeyPatch) -> _TokenRecorder:
    """Autouse: stub the three best-effort title-token seams for EVERY test so the
    direct ``run_acquire`` / ``run_release`` unit tests never spawn the real
    executor subprocess (the token surface is best-effort and out-of-scope for the
    lock-correctness assertions). Tests that care about the token surface request
    this fixture by name and assert on the recorder.

    The CLI-subprocess concurrency tests run in a SEPARATE spawned process where
    this monkeypatch does not apply — there the real best-effort wrappers run and
    swallow any executor failure, exactly as in production.
    """
    recorder = _TokenRecorder()
    recorder.install(monkeypatch)
    return recorder


# =============================================================================
# Atomic acquire + holder recording
# =============================================================================


class TestAcquire:
    def test_acquire_creates_lock_and_records_holder(self, isolated_base: dict) -> None:
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success', result
        assert result['action'] == 'acquired'
        assert result['admission'] == 'admitted'
        assert result['holder'] == 'plan-a'
        assert result['reclaimed'] is False

        lock_path = isolated_base['lock_path']
        assert lock_path.is_file()
        # Holder source recorded in the file contents.
        assert lock_path.read_text(encoding='utf-8').strip() == 'plan-a'

    def test_acquire_is_atomic_o_excl(self, isolated_base: dict) -> None:
        """The lock file is created exclusively — a pre-existing file from a live
        holder blocks a second atomic create (the primitive returns False)."""
        lock_path = isolated_base['lock_path']
        # First acquire wins and creates the file.
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        # The low-level atomic create against the existing file must fail.
        assert merge_lock._try_atomic_create(lock_path, 'plan-b') is False

    def test_lone_acquirer_is_the_fifo_front(self, isolated_base: dict) -> None:
        """A lone acquirer is trivially the FIFO front and is admitted; the queue
        records it as the single waiting entry while it holds the lock."""
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['admission'] == 'admitted'
        assert result['waiting_count'] == 1
        # The acquiring plan is enqueued (front) for the duration of its hold.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['plan-a']


# =============================================================================
# FIFO admission — only the FIFO front may attempt the O_EXCL create
# =============================================================================


class TestFifoAdmission:
    """The FIFO admission layer: ``acquire`` enqueues into ``merge-queue.json`` and
    admits ONLY the FIFO-front plan (the first entry in serialized arrival order). A
    non-front plan returns ``admission: blocked`` WITHOUT attempting the ``O_EXCL``
    create — even when the lock file is FREE, a non-front plan never contends the
    kernel race. This is the fairness property that makes the longest-waiting plan
    merge next."""

    def test_non_front_plan_blocks_even_when_lock_is_free(self, isolated_base: dict) -> None:
        """A non-front plan is blocked purely by FIFO ordering — the lock file does
        not even exist yet (no plan has acquired it), yet a later-arriving plan
        behind the front in the queue still returns ``blocked``."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        # Seed the queue directly so 'front' is the oldest entry and 'behind' is
        # strictly later — no lock file is created (no acquire has run yet).
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )
        assert not isolated_base['lock_path'].exists()

        # 'behind' polls: it is NOT the FIFO front, so it blocks WITHOUT creating
        # the lock — the lock file stays absent.
        result = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert result['status'] == 'blocked'
        assert result['admission'] == 'blocked'
        # No foreign holder yet — the lock is unheld, the block is FIFO-only.
        assert result['blocking_plan_id'] is None
        # The non-front plan never created the lock file.
        assert not isolated_base['lock_path'].exists()

    def test_front_plan_is_admitted_over_a_later_waiter(self, isolated_base: dict) -> None:
        """The FIFO front is admission-eligible and wins the O_EXCL create; the
        later waiter behind it stays blocked."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )

        # The front polls and is admitted (creates the lock).
        front = merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        assert front['admission'] == 'admitted'
        assert front['holder'] == 'front'
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'front'

        # The waiter behind it polls and is blocked by the now-live front holder.
        behind = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert behind['admission'] == 'blocked'
        assert behind['blocking_plan_id'] == 'front'

    def test_acquire_enqueues_in_arrival_order(self, isolated_base: dict) -> None:
        """Successive single-shot acquires enqueue in arrival order: the first
        acquirer becomes the front (admitted), each later acquirer appends behind
        it in the FIFO ``waiting`` list."""
        base = isolated_base['base']
        for name in ('a', 'b', 'c'):
            _make_live_plan(base, name)

        a = merge_lock.run_acquire(Namespace(plan_id='a', timeout=5.0))
        assert a['admission'] == 'admitted'
        b = merge_lock.run_acquire(Namespace(plan_id='b', timeout=5.0))
        assert b['admission'] == 'blocked'
        c = merge_lock.run_acquire(Namespace(plan_id='c', timeout=5.0))
        assert c['admission'] == 'blocked'

        # The FIFO queue records all three in arrival order, front first.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['a', 'b', 'c']
        # Each blocked waiter names the live front holder as the blocker.
        assert b['blocking_plan_id'] == 'a'
        assert c['blocking_plan_id'] == 'a'

    def test_blocked_payload_carries_waiting_count_not_poll_window(self, isolated_base: dict) -> None:
        """The blocked admission payload carries ``waiting_count`` (the queue depth)
        and ``blocking_plan_id`` — and crucially NOT the retired internal-wait
        ``poll_window_seconds`` field (acquire no longer waits internally)."""
        for name in ('plan-a', 'plan-b'):
            _make_live_plan(isolated_base['base'], name)
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # waiting_count is the queue depth (front 'plan-a' + waiter 'plan-b').
        assert result['waiting_count'] == 2
        # The internal-wait field was retired with the wait loop.
        assert 'poll_window_seconds' not in result
        # blocked is NOT a hard error — no error_code is set.
        assert result.get('error_code') is None

    def test_front_is_list_position_not_min_ts_under_inverted_ts(self, isolated_base: dict) -> None:
        """Regression: the FIFO front is the FIRST ``waiting`` entry (serialized
        arrival order), NOT the entry with the smallest admit-``ts``.

        Under concurrent enqueue a ``ts`` sampled before the serialized ``rmw_json``
        section can disagree with the append order, so a ``min(ts)`` front selector
        could pick a different plan than the file's first entry. During a drain that
        made the genuine list-front poll ``blocked`` with no holder — the
        no-double-grant drain flake. The queue below has append order
        ``[first, second]`` but INVERTED admit-``ts`` (``first``'s ts is LARGER), so
        a min-ts selector would wrongly elect ``second`` as the front.
        """
        base = isolated_base['base']
        for name in ('first', 'second'):
            _make_live_plan(base, name)
        # Append order [first, second], but ts is inverted (first.ts > second.ts).
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'first', 'ts': 2.0},
                {'plan_id': 'second', 'ts': 1.0},
            ]}),
            encoding='utf-8',
        )
        assert not isolated_base['lock_path'].exists()

        # 'first' is the list-position front → admitted. A min-ts selector would
        # have elected 'second' and wrongly blocked 'first' here.
        first = merge_lock.run_acquire(Namespace(plan_id='first', timeout=5.0))
        assert first['admission'] == 'admitted', first
        assert first['holder'] == 'first'

        # 'second' (later in arrival order despite the smaller ts) is blocked
        # behind the now-live front.
        second = merge_lock.run_acquire(Namespace(plan_id='second', timeout=5.0))
        assert second['admission'] == 'blocked', second
        assert second['blocking_plan_id'] == 'first'


# =============================================================================
# Idempotent re-poll — a blocked plan re-polling KEEPS its FIFO position
# =============================================================================


class TestIdempotentRepoll:
    """The idempotent re-poll fast-path: a plan already in the queue KEEPS its FIFO
    position on a re-poll — it is never re-appended to the back. A plan polling
    repeatedly therefore never loses priority to a later-arriving plan, mirroring
    ``build_queue.run_acquire``'s idempotent re-poll fast-path."""

    def test_repoll_blocked_plan_keeps_fifo_position(self, isolated_base: dict) -> None:
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        # front acquires (becomes the live holder); w1 then w2 queue behind it.
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        w1 = merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        w2 = merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert w1['admission'] == 'blocked'
        assert w2['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

        # w1 re-polls while still blocked — it must NOT move behind w2.
        re_w1 = merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        assert re_w1['admission'] == 'blocked'
        # The FIFO order is unchanged: w1 still ahead of w2.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

    def test_repoll_does_not_re_append_or_grow_queue(self, isolated_base: dict) -> None:
        """Re-polling an already-queued plan is idempotent on the queue itself — the
        ``waiting`` depth does not grow, the plan appears exactly once."""
        for name in ('front', 'waiter'):
            _make_live_plan(isolated_base['base'], name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='waiter', timeout=5.0))

        # Re-poll the waiter several times.
        for _ in range(3):
            res = merge_lock.run_acquire(Namespace(plan_id='waiter', timeout=5.0))
            assert res['admission'] == 'blocked'

        waiting = _waiting_plan_ids(isolated_base['queue_path'])
        # The waiter appears exactly once despite the repeated re-polls.
        assert waiting.count('waiter') == 1
        assert waiting == ['front', 'waiter']

    def test_front_repoll_against_foreign_live_holder_keeps_front_position(
        self, isolated_base: dict
    ) -> None:
        """The FIFO FRONT itself can be blocked when a FOREIGN live holder holds
        the lock (e.g. a reentrant holder that pre-existed the queue). The front's
        re-poll keeps its front position so it is first in line on release."""
        base = isolated_base['base']
        _make_live_plan(base, 'holder')
        _make_live_plan(base, 'front')
        # 'holder' holds the lock but is NOT in the FIFO queue; 'front' is the
        # queue front behind a foreign live holder.
        merge_lock.run_acquire(Namespace(plan_id='holder', timeout=5.0))
        # Drop holder from the queue so 'front' is the genuine FIFO front while
        # 'holder' still holds the lock file.
        merge_lock._dequeue_fifo('holder')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [{'plan_id': 'front', 'ts': 1.0}]}), encoding='utf-8'
        )

        first = merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        assert first['admission'] == 'blocked'
        assert first['blocking_plan_id'] == 'holder'
        # Re-poll: front stays the front, still blocked by the live foreign holder.
        again = merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        assert again['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front']


# =============================================================================
# Release advances the FIFO front
# =============================================================================


class TestReleaseAdvancesFront:
    """``release`` dequeues ``--plan-id`` so the NEXT FIFO entry becomes the front
    and is admitted on its next re-poll. This is the FIFO hand-off: the
    longest-waiting plan merges next once the current holder releases."""

    def test_release_dequeues_holder_advancing_next_waiter_to_front(self, isolated_base: dict) -> None:
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'w1', 'w2']

        # The holder releases — it is dequeued, advancing w1 to the front.
        rel = merge_lock.run_release(Namespace(plan_id='front'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['w1', 'w2']

        # w1 (now the front) re-polls and is admitted; w2 stays blocked behind it.
        re_w1 = merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        assert re_w1['admission'] == 'admitted'
        assert re_w1['holder'] == 'w1'
        re_w2 = merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert re_w2['admission'] == 'blocked'
        assert re_w2['blocking_plan_id'] == 'w1'

    def test_non_front_waiter_stays_blocked_until_its_turn(self, isolated_base: dict) -> None:
        """FIFO order is honoured across releases: a non-front waiter that re-polls
        stays blocked even though it could win the kernel race, because an earlier
        waiter holds priority and must be served first."""
        base = isolated_base['base']
        for name in ('front', 'w1', 'w2'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))

        # Holder releases → w1 advances to front. The lock file is now free.
        merge_lock.run_release(Namespace(plan_id='front'))
        assert not isolated_base['lock_path'].exists()

        # w2 (non-front) re-polls: the lock is free, but w2 is behind w1 → blocked.
        re_w2 = merge_lock.run_acquire(Namespace(plan_id='w2', timeout=5.0))
        assert re_w2['admission'] == 'blocked'
        # w2 stays behind w1 — the front did not change.
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['w1', 'w2']

    def test_full_fifo_drain_serves_plans_in_arrival_order(self, isolated_base: dict) -> None:
        """End-to-end FIFO drain: three plans queue in arrival order and are served
        front-first across successive acquire/release rounds — never out of order."""
        base = isolated_base['base']
        for name in ('a', 'b', 'c'):
            _make_live_plan(base, name)
        # Enqueue in arrival order: a is admitted, b and c queue behind.
        merge_lock.run_acquire(Namespace(plan_id='a', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='b', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='c', timeout=5.0))

        served: list[str] = ['a']  # 'a' was admitted first.

        # Drain b then c in FIFO order.
        merge_lock.run_release(Namespace(plan_id='a'))
        b = merge_lock.run_acquire(Namespace(plan_id='b', timeout=5.0))
        assert b['admission'] == 'admitted'
        served.append('b')

        merge_lock.run_release(Namespace(plan_id='b'))
        c = merge_lock.run_acquire(Namespace(plan_id='c', timeout=5.0))
        assert c['admission'] == 'admitted'
        served.append('c')

        # Served strictly in arrival order, never out of FIFO order.
        assert served == ['a', 'b', 'c']
        # The queue is empty after the final holder releases.
        merge_lock.run_release(Namespace(plan_id='c'))
        assert _waiting_plan_ids(isolated_base['queue_path']) == []

    def test_release_when_waiting_present_returns_post_removal_count(self, isolated_base: dict) -> None:
        """``release`` reports the post-removal ``waiting_count`` — the holder's own
        entry is gone, so the count reflects the remaining waiters."""
        base = isolated_base['base']
        for name in ('front', 'w1'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='w1', timeout=5.0))

        rel = merge_lock.run_release(Namespace(plan_id='front'))
        assert rel['action'] == 'released'
        # Front dequeued; w1 remains → post-removal depth is 1.
        assert rel['waiting_count'] == 1


# =============================================================================
# No double-merge — concurrent serialization (one wins, the others block)
# =============================================================================


class TestNoDoubleMerge:
    def test_second_acquire_against_live_holder_blocks(self, isolated_base: dict) -> None:
        """A live holder blocks the second acquire — it serializes and returns the
        structured ``blocked`` payload (NOT a hard error), distinct from the
        former TIMEOUT error outcome."""
        # plan-a acquires and is live (its plan dir exists).
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # plan-b cannot acquire while plan-a holds it → blocked.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # blocked is NOT a hard error — no error_code is set.
        assert result.get('error_code') is None

    def test_acquire_succeeds_after_holder_releases(self, isolated_base: dict) -> None:
        """After the holder releases, the next acquire wins (serialized handoff)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        rel = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['holder'] == 'plan-b'

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_admits_exactly_one_under_real_contention(
        self, isolated_base: dict
    ) -> None:
        """§5 (ii): N spawned subprocesses race the SAME main-anchored merge.lock +
        merge-queue.json via the CLI entry point. EXACTLY ONE returns
        ``status: success/acquired``; every other returns ``status: blocked``. Two
        plans never both hold the lock — under the FIFO layer only the front plan
        is admission-eligible AND the kernel O_EXCL race is the final k=1 arbiter,
        so the no-double-merge property holds. This is the make-or-break property
        and MUST run under genuine process-level contention, not sequential calls.

        Runs under ``PLAN_BASE_DIR`` isolation (no contention for the real
        ``.plan/merge.lock``) and is stable under ``pytest-xdist`` ``-n auto`` with
        widened load-sensitive margins (``--timeout 30`` legacy compat flag,
        ``timeout=90`` outer subprocess kill budget) — matching the hardened
        sibling reclamation races."""
        base = isolated_base['base']
        n = 8
        # Each contender's plan dir is live, so a held lock is NEVER reclaimed —
        # FIFO admission + the kernel O_EXCL race are the sole arbiters.
        for i in range(n):
            _make_live_plan(base, f'race-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'race-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))

        # The script emits TOON, not JSON — parse with the TOON parser.
        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        blocked = [p for p in parsed if p.get('status') == 'blocked']

        # Exactly one winner; the rest blocked — never two holders.
        assert len(winners) == 1, parsed
        assert len(blocked) == n - 1, parsed
        # The single winner's plan_id is what the lock file records.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == winners[0]['holder']
        # Every blocked result's queue depth reflects all N contenders enqueued.
        for p in blocked:
            assert p['waiting_count'] >= 1, p

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_then_drained_serves_every_plan_exactly_once(
        self, isolated_base: dict
    ) -> None:
        """N contenders race once (one admitted, the rest blocked into the FIFO
        queue), then the queue is drained in-process: each release advances the
        next front, and every one of the N plans is admitted exactly once with no
        plan served twice and none lost. This pins the no-double-grant + no-lost
        FIFO entry property end-to-end across the contention + drain lifecycle."""
        base = isolated_base['base']
        n = 6
        for i in range(n):
            _make_live_plan(base, f'p-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH, 'acquire', '--plan-id', f'p-{i}', '--timeout', '30',
                env_overrides=env_overrides, timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))
        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        assert len(winners) == 1, parsed

        # Every contender enqueued exactly once — the FIFO queue holds all N.
        queued = _waiting_plan_ids(isolated_base['queue_path'])
        assert sorted(queued) == sorted(f'p-{i}' for i in range(n)), queued
        assert len(queued) == n

        # Drain the queue: release the current front, then the next front polls and
        # is admitted, until every plan has been served. Collect the serving order.
        served: list[str] = [winners[0]['holder']]
        current = winners[0]['holder']
        for _ in range(n - 1):
            merge_lock.run_release(Namespace(plan_id=current))
            front = _waiting_plan_ids(isolated_base['queue_path'])[0]
            admitted = merge_lock.run_acquire(Namespace(plan_id=front, timeout=5.0))
            assert admitted['admission'] == 'admitted', admitted
            served.append(front)
            current = front

        # Every plan served exactly once — no double-grant, no lost entry.
        assert sorted(served) == sorted(f'p-{i}' for i in range(n)), served
        assert len(set(served)) == n
        # The serving order is the FIFO arrival order recorded in the queue.
        assert served == queued, (served, queued)


# =============================================================================
# Reentrant per plan-id — a same-plan-id re-acquire is granted without blocking
# =============================================================================


class TestReentrantAcquire:
    """The self-holder short-circuit: when the lock is already held by the SAME
    ``plan_id``, a re-acquire returns ``status: success`` with ``action:
    already_held`` IMMEDIATELY — no second ``O_EXCL`` create, no staleness
    evaluation, no FIFO churn. This is the fix for the finalize auto-merge
    self-deadlock (``branch-cleanup`` holds the lock, then ``integrate_into_main``
    re-acquires it under the same ``plan_id``). The reentrant grant is NOT an
    independent second acquisition: release stays idempotent and holder-scoped, so
    the single real ``os.unlink`` fires once when the holder releases."""

    def test_same_plan_id_reacquire_is_already_held_success(self, isolated_base: dict) -> None:
        """A re-acquire for the SAME plan-id (already the live holder) returns a
        success with ``action: already_held`` rather than blocking or reclaiming."""
        # plan-a acquires the lock and is live (its plan dir exists), so the
        # holder is NOT dead.
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # The same plan-a re-acquires — granted reentrantly, not blocked.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        assert result['action'] == 'already_held'
        assert result['admission'] == 'admitted'
        assert result['holder'] == 'plan-a'
        # A reentrant grant is not a fresh acquire and not a reclaim.
        assert result['reclaimed'] is False
        # The lock file is unchanged — still recording plan-a, never re-created.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_reentrant_reacquire_does_not_block(self, isolated_base: dict) -> None:
        """The self-holder short-circuit returns IMMEDIATELY — even a ``timeout: 0``
        re-acquire (which would block instantly against a FOREIGN holder) succeeds
        for the same plan-id, proving it short-circuited before the FIFO layer."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        start = time.monotonic()
        # timeout=0 is the non-blocking try: a foreign holder would `blocked`
        # immediately; a self-holder must short-circuit to success.
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=0))
        elapsed = time.monotonic() - start
        assert result['status'] == 'success'
        assert result['action'] == 'already_held'
        # The reentrant grant returns essentially instantly — far under any budget.
        assert elapsed < 1.0

    def test_reentrant_grant_does_not_enqueue_into_fifo(self, isolated_base: dict) -> None:
        """The reentrant short-circuit fires BEFORE the FIFO enqueue — a self-holder
        re-acquire must not churn the queue with a duplicate entry. The acquiring
        plan keeps its single FIFO entry from the first acquire, unchanged."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        before = _waiting_plan_ids(isolated_base['queue_path'])

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['action'] == 'already_held'
        # The reentrant grant reports waiting_count 0 (it did not touch the queue)
        # and leaves the persisted FIFO state exactly as the first acquire left it.
        assert result['waiting_count'] == 0
        assert _waiting_plan_ids(isolated_base['queue_path']) == before

    def test_reentrant_reacquire_then_single_release_frees_lock(self, isolated_base: dict) -> None:
        """The reentrant grant must NOT be an independent second acquisition: after a
        self-holder re-acquire, ONE release removes the single underlying lock file
        (release is idempotent and holder-scoped — the single ``os.unlink`` fires
        once), and the next acquire by a different plan succeeds."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        # Reentrant re-acquire by the same holder — no second lock file created.
        reentrant = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert reentrant['action'] == 'already_held'

        # A single release frees the one underlying lock file.
        rel = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert rel['status'] == 'success'
        assert rel['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

        # The lock is now genuinely free — a different plan can acquire it.
        other = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert other['status'] == 'success'
        assert other['action'] == 'acquired'
        assert other['holder'] == 'plan-b'

    def test_foreign_live_holder_still_blocks(self, isolated_base: dict) -> None:
        """Cross-plan mutual exclusion is preserved: a FOREIGN live holder still
        blocks. The reentrant short-circuit only fires for the SAME plan-id. plan-b
        acquiring against a live plan-a holder still returns ``blocked``."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        # The lock still records the live foreign holder, never reentrantly granted.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_reentrant_grant_does_not_surface_lock_owned_token(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The reentrant ``already_held`` short-circuit returns before any title-token
        surface — the lock-owned 🔒 glyph was already set on the FIRST acquire, so the
        re-acquire surfaces no NEW token (it neither re-creates the lock nor blocks)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['action'] == 'already_held'
        # No new token of any kind — neither lock-owned (no re-create) nor
        # lock-waiting (not blocked).
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []


# =============================================================================
# Release
# =============================================================================


class TestRelease:
    def test_release_removes_lock(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

    def test_release_when_free_is_noop_success(self, isolated_base: dict) -> None:
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['status'] == 'success'
        assert result['action'] == 'noop'

    def test_release_twice_is_idempotent_noop(self, isolated_base: dict) -> None:
        """A second release (after the lock is already freed) is a no-op success —
        a crashed-and-retried finalize must not error on the second release."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        first = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert first['action'] == 'released'

        second = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert second['status'] == 'success'
        assert second['action'] == 'noop'

    def test_release_foreign_holder_is_noop_and_leaves_lock_intact(self, isolated_base: dict) -> None:
        """A caller that is not the recorded holder must not remove the lock."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['status'] == 'success'
        assert result['action'] == 'noop'
        assert result['holder'] == 'plan-a'
        # The foreign holder's lock is left intact.
        assert isolated_base['lock_path'].is_file()
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-a'

    def test_release_dequeues_even_when_caller_never_held_the_lock(self, isolated_base: dict) -> None:
        """A plan that gave up waiting (never held the lock) must STILL be dequeued
        from the FIFO queue on release — otherwise its stale entry would wedge the
        front. The foreign-holder release noop leaves the lock intact but removes
        the caller's own waiting entry so the front can advance."""
        base = isolated_base['base']
        for name in ('front', 'waiter'):
            _make_live_plan(base, name)
        merge_lock.run_acquire(Namespace(plan_id='front', timeout=5.0))
        merge_lock.run_acquire(Namespace(plan_id='waiter', timeout=5.0))
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front', 'waiter']

        # The waiter gives up: it releases though it never held the lock.
        rel = merge_lock.run_release(Namespace(plan_id='waiter'))
        assert rel['action'] == 'noop'
        # The front holder's lock is intact, but the waiter is gone from the queue.
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'front'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['front']


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


# =============================================================================
# _reclaim_stale_lock — atomic eviction of the OBSERVED stale file (deterministic
# in-process unit; pins the atomicity contract the concurrency tests exercise only
# stochastically)
# =============================================================================


class TestReclaimStaleLockHelper:
    """The reclaim eviction arbitrates on the SPECIFIC observed stale file, not the
    bare path: it renames the file aside to a per-reclaimer unique sidecar,
    re-confirms the renamed-away content is exactly the dead holder it decided to
    evict, and only then O_EXCL-recreates. The former blind ``os.unlink(path)``
    would evict whatever lived at the path — including a live holder a concurrent
    reclaimer had just installed — and let two acquirers both win. These
    deterministic units pin both branches: confirmed-dead reclaim, and the
    abort/restore branch when the path's holder changed to a live holder between
    observation and reclaim."""

    def test_reclaim_succeeds_for_observed_dead_holder(self, isolated_base: dict) -> None:
        """A lock file recording a dead holder (no live plan dir) is atomically
        reclaimed: the helper returns True, the dead file is gone, and the lock
        file now records the new holder."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # 'dead-holder' has no plan dir under <base>/plans → dead.
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is True
        # The lock now records the reclaiming holder.
        assert lock_path.read_text(encoding='utf-8').strip() == 'plan-b'
        # No reclaim sidecar left behind.
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_aborts_and_restores_when_holder_became_live(
        self, isolated_base: dict
    ) -> None:
        """The abort/restore branch: the file at the path changed to a LIVE holder
        between the liveness observation and the reclaim. The helper renames it
        aside, finds the renamed-away content is NOT the observed dead holder (it
        is a live holder), restores the file intact via ``os.replace``, and returns
        False — the live holder's lock survives unchanged and this reclaimer loses."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is now a LIVE holder (its plan dir exists), even
        # though the reclaimer OBSERVED a dead holder ('dead-holder') a beat earlier.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        # The live holder's lock file is restored intact — never evicted.
        assert lock_path.is_file()
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-winner'
        # The sidecar was replaced back, not left dangling.
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_aborts_and_restores_when_holder_changed_to_other_dead(
        self, isolated_base: dict
    ) -> None:
        """The observed-file arbitration also loses when the path's content changed
        to a DIFFERENT holder (even another dead one) before the rename — the
        renamed-away content must equal the SPECIFIC observed holder. A mismatch
        restores the file and returns False rather than stealing a slot the
        reclaimer never observed."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file is a different (also dead) holder than the one observed.
        lock_path.write_text('other-dead\n', encoding='utf-8')

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        # The file is restored intact (the different holder), not reclaimed.
        assert lock_path.read_text(encoding='utf-8').strip() == 'other-dead'
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_drops_sidecar_and_loses_when_restore_replace_raises(
        self, isolated_base: dict
    ) -> None:
        """The abort/restore branch when ``os.replace`` ITSELF raises: the helper
        observed a dead holder, renamed the file aside, then found the renamed-away
        content was NOT the observed dead holder — so it tries to restore the file
        via ``os.replace``, but that restore raises (a concurrent reclaimer already
        recreated the path). The helper must drop the now-stale sidecar via
        ``os.unlink`` and still lose cleanly with ``False`` — never granting this
        reclaimer the lock. This pins the best-effort-restore sub-branch the other
        abort tests (where ``os.replace`` succeeds) leave unexercised."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The file at the path is a LIVE holder (its plan dir exists) — different
        # from the observed dead holder, so the helper enters the restore branch.
        _make_live_plan(base, 'live-winner')
        lock_path.write_text('live-winner\n', encoding='utf-8')

        # Make the restore os.replace raise, simulating a concurrent reclaimer
        # having recreated the path before this loser could restore it.
        unlinked: list[str] = []
        real_unlink = merge_lock.os.unlink

        def _raising_replace(_src: str, _dst: str) -> None:
            raise OSError('restore target busy')

        def _recording_unlink(target: str) -> None:
            unlinked.append(target)
            real_unlink(target)

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'replace', _raising_replace)
        mp.setattr(merge_lock.os, 'unlink', _recording_unlink)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        # The reclaimer lost cleanly despite the restore failing.
        assert won is False
        # The now-stale sidecar was dropped via os.unlink (best-effort cleanup),
        # so no reclaim sidecar lingers on disk.
        assert len(unlinked) == 1, unlinked
        assert Path(unlinked[0]).name.startswith(f'{lock_path.name}.reclaim.')
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_returns_false_when_path_already_gone(self, isolated_base: dict) -> None:
        """When a racing reclaimer already swapped/removed the file, the rename
        fails (the path is gone) and the helper loses cleanly with False — no
        sidecar, no recreate, fall through to lose."""
        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # No file at the path — simulates a racing reclaimer having claimed it.
        assert not lock_path.exists()

        won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')

        assert won is False
        assert not lock_path.exists()
        siblings = list(lock_path.parent.glob(f'{lock_path.name}.reclaim.*'))
        assert siblings == [], siblings

    def test_reclaim_uses_unique_sidecar_per_reclaimer(self, isolated_base: dict) -> None:
        """The sidecar target is a per-reclaimer unique name (``{lock}.reclaim.{pid}.{uuid}``)
        — a path only this reclaimer names, so two concurrent reclaimers never
        collide on the rename target. Exercised by confirming the rename target
        carries the pid and a uuid hex suffix during a successful reclaim (the
        sidecar is consumed by the time the helper returns, so assert via a wrapped
        ``os.rename`` seam)."""
        import os as _os

        lock_path = isolated_base['lock_path']
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        rename_targets: list[str] = []
        real_rename = _os.rename

        def _recording_rename(src: str, dst: str) -> None:
            rename_targets.append(dst)
            real_rename(src, dst)

        mp = pytest.MonkeyPatch()
        mp.setattr(merge_lock.os, 'rename', _recording_rename)
        try:
            won = merge_lock._reclaim_stale_lock(lock_path, 'dead-holder', 'plan-b')
        finally:
            mp.undo()

        assert won is True
        # The (single) rename targeted a unique sidecar carrying pid + a hex uuid.
        assert len(rename_targets) == 1, rename_targets
        target_name = Path(rename_targets[0]).name
        assert target_name.startswith(f'{lock_path.name}.reclaim.{_os.getpid()}.')
        # The uuid suffix is 32 hex chars.
        suffix = target_name.rsplit('.', 1)[-1]
        assert len(suffix) == 32 and all(c in '0123456789abcdef' for c in suffix)


# =============================================================================
# §5 (iv) — dead-holder reclaim WITHOUT evicting a live holder, under REAL
# spawned-process contention (the make-or-break liveness-under-races property)
# =============================================================================


class TestConcurrentReclamation:
    """§5 (iv): a crashed/dead holder is reclaimed without ever evicting a LIVE
    holder, asserted under REAL spawned-subprocess contention via the CLI entry
    point. Sequential reclaim tests (``TestStaleReclamation``) cannot exercise the
    interleave window between the dead-holder remove and the re-create, so these
    process-level races are the load-bearing concurrency obligation for the merge
    mutex's reclamation path."""

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_against_dead_holder_admits_exactly_one_reclaimer(
        self, isolated_base: dict
    ) -> None:
        """A dead-holder lock file + N live concurrent acquirers racing the SAME
        main-anchored merge.lock → EXACTLY ONE returns ``status: success``; every
        other returns ``status: blocked``. No second acquirer ever wins (FIFO
        admission + the kernel ``O_EXCL`` re-create after the stale unlink admit
        one), and the lock file ends up recording the single winner. The winner's
        ``reclaimed`` flag may be either True or False depending on which of the two
        equivalent dead-holder acquire paths it took under the race."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']

        # Pre-stage a DEAD holder: a lock file whose holder has NO live plan dir
        # (neither on main nor in a worktree) → reclaimable by construction. The
        # dead holder is NOT in the FIFO queue, so the racing live acquirers
        # contend for the front among themselves.
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text('dead-holder\n', encoding='utf-8')

        n = 8
        # Every contender's plan dir is live, so once one reclaims, the rest find a
        # LIVE holder and serialize (block) — they must NOT also reclaim.
        for i in range(n):
            _make_live_plan(base, f'reclaim-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'reclaim-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))

        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        blocked = [p for p in parsed if p.get('status') == 'blocked']

        # Exactly one reclaimer wins; the rest block — no double-grant of the
        # reclaimed k=1 mutex.
        assert len(winners) == 1, parsed
        assert len(blocked) == n - 1, parsed
        # The single winner took the dead holder's slot. Under genuine N-way
        # contention the winner may report `reclaimed: True` (it ran the
        # decide-dead → unlink → re-create path itself) OR `reclaimed: False` (a
        # racing process unlinked the stale file a beat earlier, so this winner's
        # plain initial O_EXCL create succeeded against the now-free path). Both
        # are correct dead-holder-reclaim outcomes.
        assert winners[0]['reclaimed'] in (True, False), winners[0]
        # The lock file records the single reclaimer, and the dead holder is gone.
        recorded = lock_path.read_text(encoding='utf-8').strip()
        assert recorded == winners[0]['holder']
        assert recorded != 'dead-holder'

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_acquire_never_evicts_a_live_holder(self, isolated_base: dict) -> None:
        """A LIVE holder holds the lock while N concurrent acquirers race it → NONE
        win, ALL block, and the live holder's lock is never reclaimed or evicted.
        This is the other half of §5 (iv): reclamation must NEVER steal a slot from a
        live holder under contention."""
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']

        # A LIVE holder owns the lock (its plan dir exists → NOT reclaimable). It is
        # dequeued from the FIFO queue so the racing contenders form the queue.
        merge_lock.run_acquire(Namespace(plan_id='live-holder', timeout=5.0))
        _make_live_plan(base, 'live-holder')
        merge_lock._dequeue_fifo('live-holder')

        n = 8
        for i in range(n):
            _make_live_plan(base, f'contender-{i}')

        env_overrides = {'PLAN_BASE_DIR': str(base)}

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'contender-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        with ThreadPoolExecutor(max_workers=n) as pool:
            results = list(pool.map(_acquire, range(n)))

        parsed = [parse_toon(r.stdout) for r in results]
        winners = [p for p in parsed if p.get('status') == 'success']
        blocked = [p for p in parsed if p.get('status') == 'blocked']

        # NO contender ever evicts the live holder — all block, none acquire.
        assert winners == [], parsed
        assert len(blocked) == n, parsed
        # The live holder's lock survives unchanged across the whole race.
        assert lock_path.read_text(encoding='utf-8').strip() == 'live-holder'
        # Every blocked contender names the live holder as the blocker.
        for p in blocked:
            assert p['blocking_plan_id'] == 'live-holder', p

    @pytest.mark.xdist_group(name="manage_locks_contention")
    def test_concurrent_reclaim_admits_exactly_one_across_repeated_trials(
        self, isolated_base: dict
    ) -> None:
        """Hardened regression for the stale-reclaim TOCTOU double-grant (D1 fix).

        The single-shot ``test_concurrent_acquire_against_dead_holder_admits_exactly_one_reclaimer``
        exercises the dead-holder N-way race ONCE — it catches the double-grant
        only when that one trial happens to hit the narrow interleave window.
        Before the D1 atomic-eviction fix the race could produce TWO winners
        (the canonical ``assert 2 == 1`` failure) whenever two reclaimers both
        decided the holder dead and the second's blind ``os.unlink(path)`` evicted
        the first's freshly-installed LIVE holder. Under repetition that flake
        surfaces reliably.

        This test re-runs the SAME dead-holder reclaim race under repeated trials,
        re-staging the dead holder and clearing the FIFO queue per trial, and
        asserts on EVERY trial that EXACTLY ONE acquirer wins and the remaining
        ``n-1`` block — turning the stochastic single-shot check into a
        deterministic-under-repetition regression guard. It runs under
        ``PLAN_BASE_DIR`` isolation and is stable under ``pytest-xdist`` ``-n auto``
        with widened load-sensitive margins (``--timeout 30`` legacy compat flag,
        ``timeout=90`` outer subprocess kill budget).
        """
        base = isolated_base['base']
        lock_path = isolated_base['lock_path']
        queue_path = isolated_base['queue_path']
        env_overrides = {'PLAN_BASE_DIR': str(base)}

        n = 8
        trials = 10

        # Live contender plan dirs are stable across trials — staged once.
        for i in range(n):
            _make_live_plan(base, f'reclaim-{i}')

        def _acquire(i: int):
            return run_script(
                SCRIPT_PATH,
                'acquire',
                '--plan-id',
                f'reclaim-{i}',
                '--timeout',
                '30',
                env_overrides=env_overrides,
                timeout=90,
            )

        for trial in range(trials):
            # Re-stage the DEAD holder for this trial and clear the FIFO queue so
            # each trial starts from the same dead-holder-held, empty-queue state
            # the race must arbitrate.
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text('dead-holder\n', encoding='utf-8')
            if queue_path.exists():
                queue_path.unlink()

            with ThreadPoolExecutor(max_workers=n) as pool:
                results = list(pool.map(_acquire, range(n)))

            parsed = [parse_toon(r.stdout) for r in results]
            winners = [p for p in parsed if p.get('status') == 'success']
            blocked = [p for p in parsed if p.get('status') == 'blocked']

            # The make-or-break invariant on EVERY trial: exactly one winner, the
            # rest blocked — never the ``assert 2 == 1`` double-grant. The trial
            # index is folded into the assertion message so a regression names the
            # offending trial.
            assert len(winners) == 1, (trial, parsed)
            assert len(blocked) == n - 1, (trial, parsed)
            # The lock file records the single winner, and the dead holder is gone.
            recorded = lock_path.read_text(encoding='utf-8').strip()
            assert recorded == winners[0]['holder'], (trial, recorded, winners)
            assert recorded != 'dead-holder', (trial, recorded)

            # Release the winner's lock so the next trial starts from a clean
            # dead-holder-held state rather than the prior winner's live lock.
            merge_lock.run_release(Namespace(plan_id=winners[0]['holder']))


# =============================================================================
# Main-anchored resolution (the single deliberate exception)
# =============================================================================


class TestMainAnchoredResolution:
    def test_lock_resolves_to_main_even_when_cwd_is_a_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Under PLAN_BASE_DIR (the main-checkout stand-in), the lock resolves to
        ``<base>/merge.lock`` regardless of the process cwd — pinning cwd into a
        worktree fixture does NOT redirect the lock to a worktree-relative path."""
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        # A worktree fixture with its own .plan/local — cwd is pinned here.
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = merge_lock._resolve_main_lock_path()
        # Resolves to MAIN's base, NOT the worktree-relative .plan/local.
        assert resolved == main_base / 'merge.lock'
        assert worktree / '.plan' / 'local' / 'merge.lock' != resolved

    def test_queue_resolves_to_main_even_when_cwd_is_a_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The FIFO merge-queue resolves to ``<base>/merge-queue.json`` against the
        MAIN checkout regardless of the process cwd — same main-anchored contract
        as the lock file, so all sessions contend for one shared queue."""
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        resolved = merge_lock._resolve_merge_queue_path()
        assert resolved == main_base / 'merge-queue.json'
        assert worktree / '.plan' / 'local' / 'merge-queue.json' != resolved

    def test_acquire_writes_to_main_base_from_worktree_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        # The lock AND the queue landed under MAIN's base, not the worktree.
        assert (main_base / 'merge.lock').is_file()
        assert (main_base / 'merge-queue.json').is_file()
        assert not (worktree / '.plan' / 'local' / 'merge.lock').exists()
        assert not (worktree / '.plan' / 'local' / 'merge-queue.json').exists()


# =============================================================================
# Shared-core delegation guard — no re-implemented liveness / resolution / rmw
# =============================================================================


class TestSharedCoreDelegation:
    """The unified merge_lock builds on the shared coordination core — it imports
    ``holder_is_dead`` and ``rmw_json`` from ``_locks_core`` and
    ``resolve_main_anchored_path`` from ``marketplace_paths`` rather than
    re-implementing any. These guards fail if a parallel copy is ever
    reintroduced."""

    def test_imports_shared_liveness_predicate(self) -> None:
        # holder_is_dead must be imported from the shared core, not redefined.
        assert hasattr(merge_lock, 'holder_is_dead')

    def test_imports_shared_rmw_json(self) -> None:
        # The FIFO enqueue/dequeue runs through the shared rmw_json, not a
        # re-implemented serialized read-modify-write.
        assert hasattr(merge_lock, 'rmw_json')

    def test_imports_shared_resolver(self) -> None:
        assert hasattr(merge_lock, 'resolve_main_anchored_path')

    def test_no_inline_liveness_copy(self) -> None:
        # The former inline ``_holder_is_dead`` / ``_main_plan_local_base`` copies
        # were dropped — liveness lives once in _locks_core now.
        assert not hasattr(merge_lock, '_holder_is_dead')
        assert not hasattr(merge_lock, '_main_plan_local_base')

    def test_no_inline_git_common_dir_in_source(self) -> None:
        # No inline ``git rev-parse --git-common-dir`` subprocess call remains —
        # resolution belongs to the shared utility.
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert '--git-common-dir' not in src

    def test_no_status_marker_scan_in_source(self) -> None:
        # The status-marker scan (layer #2) was dropped — no merging_on_main
        # marker or cross-plan scan survives in the unified file primitive.
        src = SCRIPT_PATH.read_text(encoding='utf-8')
        assert 'merging_on_main' not in src
        assert '_find_holder' not in src


# =============================================================================
# Title-token surface (best-effort, OUTSIDE the O_EXCL window)
# =============================================================================


class TestTitleTokenSurface:
    """The merge lock surfaces its state in the terminal title — ⏳ (lock-waiting)
    on a blocked admission, 🔒 (lock-owned) once the lock is held, and a clear on
    every release path. Every write is best-effort and placed OUTSIDE the O_EXCL
    check-then-act window (mirrors D6's build-phase pair)."""

    def test_acquire_surfaces_lock_owned_on_fresh_acquire(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        # `lock-owned` state set (bare state name, no glyph) + 🔒 pushed.
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]
        # No waiting token on an uncontended acquire.
        assert 'lock-waiting' not in _stub_title_tokens.set_states

    def test_acquire_surfaces_lock_owned_on_reclaim(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A reclaim of a dead holder's lock also surfaces `lock-owned` (🔒)."""
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        merge_lock._dequeue_fifo('plan-dead')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['reclaimed'] is True
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]

    def test_blocked_acquire_surfaces_lock_waiting(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A blocked admission against a live holder surfaces `lock-waiting` (⏳),
        never `lock-owned`. The token fires on the blocked return path — acquire no
        longer sleeps internally, so the surface is gated on the blocked outcome,
        not on a backoff poll."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.6))
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == ['lock-waiting']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        assert 'lock-owned' not in _stub_title_tokens.set_states

    def test_non_front_blocked_acquire_surfaces_lock_waiting(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A non-front FIFO block surfaces `lock-waiting` (⏳) too — even when the
        lock is FREE, a plan behind the front is waiting for its turn."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == ['lock-waiting']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]

    def test_blocked_release_surfaces_lock_cleared(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """Symmetric partner of `test_blocked_acquire_surfaces_lock_waiting`: a
        plan that was blocked against a live foreign holder (⏳ pushed) and then
        calls `release` has its token CLEARED. The lock stays held by the foreign
        holder (release is scoped to the caller), but the blocked waiter's own
        stale `lock-waiting` token is cleared via the foreign-holder noop branch."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        # Drop plan-a's own acquire surface so the assertions below see only the
        # blocked waiter's tokens (mirrors `test_blocked_acquire_surfaces_lock_waiting`).
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()
        # plan-b blocks behind the live holder, surfacing `lock-waiting` (⏳).
        blocked = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.6))
        assert blocked['status'] == 'blocked'
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        _stub_title_tokens.cleared.clear()

        # The blocked waiter gives up and releases — its stale token is cleared and
        # the foreign holder's lock is left intact.
        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'
        assert _stub_title_tokens.cleared == ['plan-b']
        assert isolated_base['lock_path'].is_file()

    def test_non_front_blocked_release_surfaces_lock_cleared(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """Symmetric partner of `test_non_front_blocked_acquire_surfaces_lock_waiting`:
        a non-front FIFO waiter (⏳ pushed, lock FREE) that then calls `release` has
        its token CLEARED via the already-free noop branch, and is dequeued so the
        front can advance."""
        base = isolated_base['base']
        for name in ('front', 'behind'):
            _make_live_plan(base, name)
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'front', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )
        # `behind` blocks as a non-front waiter, surfacing `lock-waiting` (⏳).
        blocked = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert blocked['status'] == 'blocked'
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_WAITING]
        _stub_title_tokens.cleared.clear()

        # `behind` gives up and releases — the lock was never held by anyone, so the
        # already-free noop branch clears its stale token and dequeues it.
        result = merge_lock.run_release(Namespace(plan_id='behind'))
        assert result['action'] == 'noop'
        assert _stub_title_tokens.cleared == ['behind']
        assert 'behind' not in _waiting_plan_ids(isolated_base['queue_path'])

    def test_release_clears_token_on_released_path(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == ['plan-a']
        # The released path also fires a plain, icon-less repaint through the
        # canonical seam (icon=None) so the 🔒 glyph disappears LIVE instead of
        # lingering until the next render event.
        assert _stub_title_tokens.pushed_icons == [None], (
            'release must repaint (icon-less push) after clearing the token'
        )

    def test_release_clears_token_on_already_free_noop(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'noop'
        # The already-free noop still clears this caller's stale token.
        assert _stub_title_tokens.cleared == ['plan-a']

    def test_release_clears_token_on_foreign_holder_noop(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'
        # The foreign-holder noop clears the CALLER's (plan-b's) stale token, and
        # leaves plan-a's lock intact.
        assert _stub_title_tokens.cleared == ['plan-b']
        assert isolated_base['lock_path'].is_file()

    def test_token_write_failure_never_breaks_acquire(self, isolated_base: dict) -> None:
        """The best-effort wrappers swallow any underlying executor failure — a
        token write that raises NEVER affects the lock acquire outcome. This
        exercises the REAL _set_title_token / _push_title_token wrappers by making
        the underlying _run_executor raise."""

        def _raising_run_executor(*_a: object, **_k: object) -> dict:
            raise OSError('tty gone')

        # Patch the low-level executor seam (NOT the higher-level token seams), so
        # the real best-effort try/except wrappers run and swallow the error.
        import pytest as _pytest

        mp = _pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_run_executor', _raising_run_executor)
        try:
            result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        finally:
            mp.undo()

        # The lock was acquired despite the token channel raising.
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert isolated_base['lock_path'].is_file()

    def test_token_clear_failure_never_breaks_release(self, isolated_base: dict) -> None:
        """Symmetric to ``test_token_write_failure_never_breaks_acquire`` on the
        RELEASE side: the best-effort ``_clear_title_token`` wrapper swallows any
        underlying executor failure, so a token-clear that raises NEVER aborts the
        lock release. Exercises the REAL ``_clear_title_token`` wrapper by making
        the low-level ``_run_executor`` seam raise, and asserts the lock file is
        still removed (the release succeeded despite the token channel raising)."""

        def _raising_run_executor(*_a: object, **_k: object) -> dict:
            raise OSError('tty gone')

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        # Patch the low-level executor seam (NOT the higher-level token seams), so
        # the real best-effort try/except wrapper runs and swallows the error.
        import pytest as _pytest

        mp = _pytest.MonkeyPatch()
        mp.setattr(merge_lock, '_run_executor', _raising_run_executor)
        try:
            result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        finally:
            mp.undo()

        # The lock was released despite the token-clear channel raising.
        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()

    def test_lock_owned_token_set_only_after_atomic_create_succeeds(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The O_EXCL-window-not-widened invariant: the ``lock-owned`` token writes
        run STRICTLY AFTER the atomic ``_try_atomic_create`` has already succeeded,
        never interleaved inside the check-then-act. Record the ordered sequence of
        (atomic-create, token-set) events through wrapped seams and assert the
        atomic create's success is observed BEFORE the first ``lock-owned`` set —
        proving the token surface cannot reopen the closed TOCTOU window."""
        events: list[str] = []

        real_atomic_create = merge_lock._try_atomic_create

        def _recording_atomic_create(lock_path: Path, holder: str) -> bool:
            ok: bool = real_atomic_create(lock_path, holder)
            events.append(f'atomic_create:{"ok" if ok else "eexist"}')
            return ok

        monkeypatch.setattr(merge_lock, '_try_atomic_create', _recording_atomic_create)
        monkeypatch.setattr(
            merge_lock, '_set_title_token', lambda _p, state: events.append(f'set:{state}')
        )
        monkeypatch.setattr(merge_lock, '_push_title_token', lambda _p, icon: events.append('push'))

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'

        # The successful atomic create MUST be recorded before the first lock-owned
        # set — the token write is strictly after the window closed, never inside it.
        assert 'atomic_create:ok' in events
        assert 'set:lock-owned' in events
        assert events.index('atomic_create:ok') < events.index('set:lock-owned'), events
        # No token of any kind precedes the successful atomic create.
        first_token_idx = next(
            (i for i, e in enumerate(events) if e.startswith(('set:', 'push'))), len(events)
        )
        assert events.index('atomic_create:ok') < first_token_idx, events

    def test_release_repaint_via_surface_lock_cleared_default(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The default (set_title_token=True) _surface_lock_cleared both clears the
        token AND fires the icon-less repaint — the consolidation of the clear path
        onto the shared repaint seam."""
        _stub_title_tokens.pushed_icons.clear()
        merge_lock._surface_lock_cleared('plan-a')
        assert _stub_title_tokens.cleared == ['plan-a']
        assert _stub_title_tokens.pushed_icons == [None]

    def test_surface_lock_cleared_suppressed_fires_neither_clear_nor_repaint(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """set_title_token=False suppresses the ENTIRE surface — no clear AND no
        repaint fire (the early return precedes both writes)."""
        _stub_title_tokens.pushed_icons.clear()
        merge_lock._surface_lock_cleared('plan-a', set_title_token=False)
        assert _stub_title_tokens.cleared == []
        assert _stub_title_tokens.pushed_icons == []

    def test_push_title_token_omits_icon_for_plain_repaint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The canonical push seam omits --icon for a plain repaint (icon=None) and
        includes --icon <glyph> when a glyph is supplied. Exercises the REAL
        _push_title_token wrapper (captured before the autouse stub) with a
        recording _run_executor."""
        calls: list[tuple] = []
        monkeypatch.setattr(merge_lock, '_run_executor', lambda notation, *args: calls.append((notation, args)))

        _REAL_PUSH_TITLE_TOKEN('plan-a')  # plain repaint — no icon
        _REAL_PUSH_TITLE_TOKEN('plan-b', merge_lock._ICON_LOCK_OWNED)  # glyph push

        assert calls[0][1] == ('session', 'push-title-token', '--plan-id', 'plan-a'), (
            'plain repaint must call session push-title-token with NO --icon'
        )
        assert '--icon' not in calls[0][1]
        assert calls[1][1] == (
            'session', 'push-title-token', '--plan-id', 'plan-b', '--icon', merge_lock._ICON_LOCK_OWNED
        ), 'a glyph push must include --icon <glyph>'

    def test_lock_owned_state_maps_to_lock_icon(self) -> None:
        """Guard the glyph contract: the lock-owned/lock-waiting icon constants
        match the canonical manage-terminal-title glyph vocabulary (🔒 / ⏳), and
        the bare STATE NAMES are passed to manage-status (no hard-coded glyph in
        the lock branching)."""
        assert merge_lock._ICON_LOCK_OWNED == '\U0001f512'
        assert merge_lock._ICON_LOCK_WAITING == '⏳'
        assert merge_lock._STATE_LOCK_OWNED == 'lock-owned'
        assert merge_lock._STATE_LOCK_WAITING == 'lock-waiting'


# =============================================================================
# Title-token suppression contract (set_title_token=False)
# =============================================================================


class TestTitleTokenSuppression:
    """The ``set_title_token`` parameter gates the entire title-token surface so the
    move-back merge lock (a brief, finalize-internal mutex) never flashes a spurious
    glyph into the terminal title. ``set_title_token=False`` suppresses ALL three
    title surfaces — ``lock-owned`` (🔒), ``lock-waiting`` (⏳), and the release
    clear — while the default (``set_title_token`` absent, or ``True``) preserves the
    full surface. These tests assert BOTH halves of the contract through the same
    ``_TokenRecorder`` seam ``TestTitleTokenSurface`` uses."""

    def test_acquire_suppresses_lock_owned_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A fresh acquire with ``set_title_token=False`` surfaces NO token — the
        🔒 ``lock-owned`` glyph never reaches the title even though the lock is held."""
        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-a', timeout=5.0, set_title_token=False)
        )
        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        # No state set, no icon pushed — the title surface is fully suppressed.
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_acquire_suppresses_lock_owned_on_reclaim_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The reclaim path also honors suppression — a reclaimed acquire with
        ``set_title_token=False`` surfaces no 🔒 token."""
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        merge_lock._dequeue_fifo('plan-dead')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', timeout=5.0, set_title_token=False)
        )
        assert result['reclaimed'] is True
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_blocked_acquire_suppresses_lock_waiting_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A blocked acquire against a live holder with ``set_title_token=False``
        surfaces no ⏳ ``lock-waiting`` token."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')
        _stub_title_tokens.set_states.clear()
        _stub_title_tokens.pushed_icons.clear()

        result = merge_lock.run_acquire(
            Namespace(plan_id='plan-b', timeout=0.6, set_title_token=False)
        )
        assert result['status'] == 'blocked'
        assert _stub_title_tokens.set_states == []
        assert _stub_title_tokens.pushed_icons == []

    def test_release_suppresses_clear_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """A release with ``set_title_token=False`` clears NO token — there was never
        a token set by the suppressed acquire, so there is nothing to clear."""
        merge_lock.run_acquire(
            Namespace(plan_id='plan-a', timeout=5.0, set_title_token=False)
        )
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(
            Namespace(plan_id='plan-a', set_title_token=False)
        )
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == []

    def test_release_noop_suppresses_clear_when_set_title_token_false(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The already-free / foreign-holder noop release paths also honor
        suppression — ``set_title_token=False`` clears no token on the noop path."""
        result = merge_lock.run_release(
            Namespace(plan_id='plan-a', set_title_token=False)
        )
        assert result['action'] == 'noop'
        assert _stub_title_tokens.cleared == []

    def test_acquire_default_still_surfaces_token(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The default (``set_title_token`` absent → True) preserves the full surface —
        a default acquire still surfaces the 🔒 ``lock-owned`` token."""
        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert result['status'] == 'success'
        assert _stub_title_tokens.set_states == ['lock-owned']
        assert _stub_title_tokens.pushed_icons == [merge_lock._ICON_LOCK_OWNED]

    def test_release_default_still_clears_token(
        self, isolated_base: dict, _stub_title_tokens: _TokenRecorder
    ) -> None:
        """The default (``set_title_token`` absent → True) preserves the release
        clear — a default release still clears the title token."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _stub_title_tokens.cleared.clear()

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'
        assert _stub_title_tokens.cleared == ['plan-a']


# =============================================================================
# CLI argparse plumbing
# =============================================================================


class TestCli:
    def test_acquire_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'acquire')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_check_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'check')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_release_requires_plan_id(self) -> None:
        result = run_script(SCRIPT_PATH, 'release')
        assert result.returncode != 0
        assert '--plan-id' in result.stderr or '--plan-id' in result.stdout

    def test_acquire_accepts_no_title_token_flag(self, isolated_base: dict) -> None:
        """The ``--no-title-token`` flag is a valid acquire argument (it maps to
        ``set_title_token=False``) — argparse accepts it and the acquire succeeds."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}
        result = run_script(
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--no-title-token',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['action'] == 'acquired'

    def test_release_accepts_no_title_token_flag(self, isolated_base: dict) -> None:
        """The ``--no-title-token`` flag is a valid release argument matching a
        ``--no-title-token`` acquire — argparse accepts it and the release succeeds."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}
        run_script(
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--no-title-token',
            env_overrides=env_overrides,
        )
        result = run_script(
            SCRIPT_PATH, 'release', '--plan-id', 'plan-a', '--no-title-token',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['action'] == 'released'

    def test_acquire_accepts_legacy_timeout_flag(self, isolated_base: dict) -> None:
        """The legacy ``--timeout`` flag is still accepted for call-site
        compatibility (acquire no longer waits internally, but the flag must parse)."""
        env_overrides = {'PLAN_BASE_DIR': str(isolated_base['base'])}
        result = run_script(
            SCRIPT_PATH, 'acquire', '--plan-id', 'plan-a', '--timeout', '0',
            env_overrides=env_overrides,
        )
        assert result.returncode == 0, result.stderr
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['admission'] == 'admitted'


# =============================================================================
# [LOCK] event emission (best-effort, OUTSIDE the O_EXCL window)
# =============================================================================


class TestLockEventEmission:
    """Each merge-lock lifecycle point emits a ``[LOCK]`` event into the SINGLE
    main-anchored global lock-event log via the shared
    :func:`_locks_core.log_lock_event`: ``acquired`` on a fresh O_EXCL create,
    ``reclaimed`` on a stale-reclaim re-create (carrying the reclaimed-from
    holder), ``blocked`` on a blocked admission (carrying holder/waiter), and
    ``released`` on the real os.unlink. ``check`` and the foreign / already-free
    release noops emit nothing. Every emission is best-effort and OUTSIDE the
    atomic window — a logging failure never breaks the lock action.

    The ``isolated_base`` fixture stages PLAN_BASE_DIR at ``<tmp>/main/.plan/local``
    so the lock-event log resolves to the per-test ``<tmp>/main/.plan/logs`` dir."""

    def test_acquire_emits_lock_acquired(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        content = _read_lock_log()
        # lock_id is the holder plan_id; the family is `merge`.
        assert '[LOCK] (merge:acquired) plan-a' in content

    def test_reclaim_emits_lock_reclaimed_with_reclaimed_from(self, isolated_base: dict) -> None:
        """A reclaim of a dead holder's lock emits ``reclaimed`` carrying the
        reclaimed-from holder for correlation."""
        # plan-dead acquires but never gets a plan dir → dead → reclaimable. It is
        # dequeued so plan-b becomes the FIFO front and reclaims.
        merge_lock.run_acquire(Namespace(plan_id='plan-dead', timeout=5.0))
        merge_lock._dequeue_fifo('plan-dead')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))
        assert result['reclaimed'] is True

        content = _read_lock_log()
        assert '[LOCK] (merge:reclaimed) plan-b' in content
        # The reclaimed-from holder is carried as a correlation field.
        assert 'reclaimed_from: plan-dead' in content

    def test_blocked_acquire_emits_lock_blocked_with_holder_and_waiter(
        self, isolated_base: dict
    ) -> None:
        """A blocked admission against a LIVE holder emits ``blocked`` carrying the
        blocking holder and the waiter."""
        merge_lock.run_acquire(Namespace(plan_id='plan-live', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-live')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))
        assert result['status'] == 'blocked'

        content = _read_lock_log()
        assert '[LOCK] (merge:blocked) plan-b' in content
        assert 'holder: plan-live' in content
        assert 'waiter: plan-b' in content

    def test_release_emits_lock_released(self, isolated_base: dict) -> None:
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'released'

        content = _read_lock_log()
        assert '[LOCK] (merge:released) plan-a' in content

    def test_check_emits_no_lock_event(self, isolated_base: dict) -> None:
        """``check`` is a non-mutating read — it changes no ownership and emits
        nothing into the lock-event timeline."""
        merge_lock.run_check(Namespace(plan_id='plan-a'))

        assert _read_lock_log() == ''

    def test_already_free_release_emits_no_lock_event(self, isolated_base: dict) -> None:
        """An already-free release noop removed no lock this caller held — it
        emits nothing (only the real ``released`` branch emits)."""
        result = merge_lock.run_release(Namespace(plan_id='plan-a'))
        assert result['action'] == 'noop'

        assert '[LOCK] (merge:released)' not in _read_lock_log()

    def test_foreign_holder_release_emits_no_lock_event(self, isolated_base: dict) -> None:
        """A foreign-holder release noop leaves the lock intact and changes no
        ownership — it emits no ``released`` event."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        result = merge_lock.run_release(Namespace(plan_id='plan-b'))
        assert result['action'] == 'noop'

        content = _read_lock_log()
        # plan-a's acquire emitted; plan-b's foreign-holder noop did NOT emit a
        # released event.
        assert '[LOCK] (merge:released)' not in content

    def test_lock_event_lands_in_main_anchored_log_not_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The [LOCK] event lands in the MAIN-anchored global log even when cwd is
        pinned to a worktree — asserted via the PLAN_BASE_DIR override, not a
        worktree path. A worktree-relative .plan/logs dir must hold no lock log."""
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'plans').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        content = _read_lock_log()
        assert '[LOCK] (merge:acquired) plan-a' in content
        # No lock-event log under the worktree-relative .plan/logs.
        assert not (worktree / '.plan' / 'logs').exists()

    def test_log_failure_never_breaks_acquire(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A [LOCK]-emission failure NEVER aborts the lock acquire — the emission
        is best-effort, with the swallow try/except INSIDE ``log_lock_event``
        itself. Make the REAL ``log_lock_event``'s internal resolver raise (the
        seam ``_resolve_lock_log_path`` on the shared core) and assert the
        function swallows it and the acquire still succeeds with the lock file
        created. Patching the bare ``log_lock_event`` name would (correctly) NOT
        be swallowed — the call sites invoke it directly — so the realistic
        failure is one inside the helper's own try/except."""
        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))

        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert isolated_base['lock_path'].is_file()

    def test_log_failure_never_breaks_release(
        self, isolated_base: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Symmetric on the RELEASE side: a [LOCK]-emission failure (the real
        helper's internal resolver raising, swallowed by its own try/except)
        NEVER aborts the lock release — the lock file is still removed."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        assert isolated_base['lock_path'].is_file()

        def _raising_resolver() -> object:
            raise OSError('log dir gone')

        monkeypatch.setattr(_locks_core, '_resolve_lock_log_path', _raising_resolver)

        result = merge_lock.run_release(Namespace(plan_id='plan-a'))

        assert result['status'] == 'success'
        assert result['action'] == 'released'
        assert not isolated_base['lock_path'].exists()


# =============================================================================
# Live-worktree guard (D3) — refuse auto-reclaim of a mid-recovery holder
# =============================================================================
#
# A holder judged dead-by-plan-dir-absence (its plan dir is in NEITHER main NOR
# its worktree's .plan) may still be MID-RECOVERY — its worktree DIRECTORY is on
# disk (an interrupted finalize move-back moved the plan dir out but left the
# worktree). The acquire path evaluates the `holder_has_live_worktree` guard
# BEFORE the auto-reclaim branch and REFUSES to reclaim such a holder, returning
# a `blocked` payload carrying `stale_holder_live_worktree: true` so the existing
# branch-cleanup budget-exhaustion escalation asks the operator to confirm rather
# than the primitive force-releasing a mid-recovery holder. No new grant path is
# opened — the reclaim is refused, not attempted.


class TestLiveWorktreeGuard:
    def test_plan_dir_dead_but_live_worktree_holder_is_not_reclaimed(self, isolated_base: dict) -> None:
        """A plan-dir-dead holder whose worktree DIRECTORY is still on disk is
        NOT auto-reclaimed: acquire returns `blocked` with the
        `stale_holder_live_worktree` discriminator and leaves the lock intact."""
        base = isolated_base['base']
        # 'mid-recovery' holds the lock. Its plan dir exists in NEITHER main NOR
        # its worktree's .plan (holder_is_dead True), but its worktree DIRECTORY
        # is present (an interrupted move-back) → holder_has_live_worktree True.
        merge_lock.run_acquire(Namespace(plan_id='mid-recovery', timeout=5.0))
        # Drop it from the FIFO queue so 'plan-b' becomes the genuine front and
        # reaches the holder-inspection / guard code below.
        merge_lock._dequeue_fifo('mid-recovery')
        (base / 'worktrees' / 'mid-recovery').mkdir(parents=True, exist_ok=True)

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))

        assert result['status'] == 'blocked'
        assert result['admission'] == 'blocked'
        assert result['stale_holder_live_worktree'] is True
        assert result['blocking_plan_id'] == 'mid-recovery'
        # The lock file was NOT reclaimed/recreated — it still records the
        # original mid-recovery holder (no new grant path opened).
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'mid-recovery'

    def test_plan_dir_dead_and_worktree_absent_still_reclaims(self, isolated_base: dict) -> None:
        """Guard boundary: a GENUINELY-dead holder (plan dir AND worktree both
        absent) is still reclaimed exactly as before — the guard does not block
        the ordinary reclaim path, and the discriminator is absent."""
        merge_lock.run_acquire(Namespace(plan_id='fully-dead', timeout=5.0))
        merge_lock._dequeue_fifo('fully-dead')
        # No worktree directory for 'fully-dead' → holder_has_live_worktree False.

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=5.0))

        assert result['status'] == 'success'
        assert result['action'] == 'acquired'
        assert result['reclaimed'] is True
        assert 'stale_holder_live_worktree' not in result
        assert isolated_base['lock_path'].read_text(encoding='utf-8').strip() == 'plan-b'

    def test_ordinary_foreign_live_holder_block_omits_discriminator(self, isolated_base: dict) -> None:
        """A normal foreign-live-holder block (the holder's plan dir exists) must
        NOT carry the guard discriminator — the field is present ONLY on the
        refuse-auto-reclaim path."""
        merge_lock.run_acquire(Namespace(plan_id='plan-a', timeout=5.0))
        _make_live_plan(isolated_base['base'], 'plan-a')

        result = merge_lock.run_acquire(Namespace(plan_id='plan-b', timeout=0.3))

        assert result['status'] == 'blocked'
        assert result['blocking_plan_id'] == 'plan-a'
        assert 'stale_holder_live_worktree' not in result

    def test_prune_retains_live_worktree_waiter(self, isolated_base: dict) -> None:
        """`_prune_dead_waiting` retains a dead-by-plan-dir waiter whose worktree
        directory is still on disk (mid-recovery), while still dropping a waiter
        that is both plan-dir-dead AND worktree-absent."""
        base = isolated_base['base']
        _make_live_plan(base, 'live')  # alive by plan dir
        (base / 'worktrees' / 'mid-recovery').mkdir(parents=True, exist_ok=True)  # live worktree only

        waiting = [
            {'plan_id': 'live', 'ts': 1.0},
            {'plan_id': 'mid-recovery', 'ts': 2.0},
            {'plan_id': 'fully-dead', 'ts': 3.0},
        ]

        pruned_ids = [e['plan_id'] for e in merge_lock._prune_dead_waiting(waiting)]

        assert 'live' in pruned_ids
        # Retained despite being plan-dir-dead — its worktree is still present.
        assert 'mid-recovery' in pruned_ids
        # Genuinely gone (plan dir AND worktree absent) → pruned.
        assert 'fully-dead' not in pruned_ids

    def test_live_worktree_waiter_not_pruned_from_fifo_front(self, isolated_base: dict) -> None:
        """End-to-end: a mid-recovery waiter (plan-dir-dead, live worktree) at the
        FIFO front is NOT pruned during an acquire, so a later live waiter behind
        it does not jump the queue."""
        base = isolated_base['base']
        (base / 'worktrees' / 'mid-recovery').mkdir(parents=True, exist_ok=True)
        _make_live_plan(base, 'behind')
        isolated_base['queue_path'].write_text(
            json.dumps({'waiting': [
                {'plan_id': 'mid-recovery', 'ts': 1.0},
                {'plan_id': 'behind', 'ts': 2.0},
            ]}),
            encoding='utf-8',
        )

        # 'behind' polls: the mid-recovery front is RETAINED (live worktree), so
        # 'behind' stays non-front → blocked, and the front is unchanged.
        result = merge_lock.run_acquire(Namespace(plan_id='behind', timeout=5.0))
        assert result['admission'] == 'blocked'
        assert _waiting_plan_ids(isolated_base['queue_path']) == ['mid-recovery', 'behind']
