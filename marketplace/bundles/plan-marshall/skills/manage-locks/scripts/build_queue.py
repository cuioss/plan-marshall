#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build-queue concurrency limiter — the bounded-``k``-slot admitter with a FIFO
waiting queue.

Notation: ``plan-marshall:manage-locks:build_queue``

This standalone script caps how many build sessions run concurrently across the
cluster. It persists ``active`` + ``waiting`` + ``run_log`` state in the
main-anchored ``build-queue.json`` and mutates it through the shared
TOCTOU-safe read-modify-write core (:func:`_locks_core.rmw_json`), so two
sessions racing to claim or free a slot can never both observe the same
pre-state and both admit. It is modeled on ``merge_lock.py`` (the ``k=1`` merge
mutex); the build queue is the ``k>=1`` primitive that needs the FIFO waiting
queue.

Every entry that enters the ``active`` set records an ``active_since`` activation
timestamp (distinct from ``ts``, the admit/enqueue time used for FIFO ordering),
set on a first-acquire admit, an idempotent-waiting promotion, and a release
FIFO-promote. The self-healing reaper :func:`validate_lock_queue` runs implicitly
at the start of EVERY acquire and release — inside the SAME ``rmw_json``
mutation — and reaps any active entry whose age (``now - active_since``) exceeds
``2 × build_queue_upper_limit`` (the adaptive, monotonic-up, clamped ``[600 s,
3600 s]`` threshold tracked in the main-anchored ``run-configuration.json``),
freeing the slot, FIFO-promoting waiters, and emitting a WARN ``[LOCK]``
``reaped-stale`` event. This complements the dead-holder prune
(:func:`_prune_dead_active`): the prune clears a holder whose plan dir is GONE,
the reaper clears a hard-killed (``SIGKILL``-past-``finally``) holder whose plan
dir still exists.

It exposes two actions:

  * ``acquire`` — resolve the admission for ``--plan-id`` **idempotently** under
    the serialized read-modify-write: first run the implicit
    :func:`validate_lock_queue` reaper, then prune any dead active holders (their
    plan dir lives in NEITHER the main checkout NOR the holder's worktree — the
    shared :func:`_locks_core.holder_is_dead` predicate), then — if the plan
    already holds an ``active`` slot OR already has a ``waiting`` entry — REUSE
    that existing id without creating a duplicate (the waiting entry KEEPS its
    FIFO position, and is promoted to ``active`` only when a freed slot makes it
    eligible). Only a plan with no existing entry gets a fresh id
    ``{plan_id}:{uuid4}`` and is appended to ``active`` (stamped ``active_since``)
    → ``admission: admitted`` (slot free) or to the back of ``waiting`` →
    ``admission: blocked`` (at capacity). The script does NOT loop or wait — the
    wait+retry loop is the build wrapper's responsibility (D6); because re-polling
    ``acquire`` is idempotent, the wrapper re-polls WITHOUT releasing first, so a
    ``blocked`` plan retains its FIFO place rather than being shuffled to the
    back. A ``blocked`` admission is a structured signal the caller re-polls
    against, not an error.
  * ``release`` — first run the implicit :func:`validate_lock_queue` reaper, then
    remove ``--id`` from ``active`` (and defensively from ``waiting``),
    FIFO-promote the oldest waiting entry (by admit-``ts``) into the freed slot
    when capacity allows (stamping the promoted entry's ``active_since``), and —
    only on a real release — append an id+timestamp entry to the ``run_log``,
    pruning it to the most recent 100 entries so ``build-queue.json`` stays
    bounded. After the commit it recomputes the adaptive
    ``build_queue_upper_limit`` from the released entry's held duration
    (``now - active_since``), persisting ``max(current, held)`` clamped to
    ``[600 s, 3600 s]`` so the reap threshold tracks the longest observed real
    build without ever exceeding a 1 h ceiling.

**Machine-global resolution — the host-wide home-root tier:** the queue file
resolves under the machine-global home root (:func:`marketplace_paths.home_root`,
``~/.plan-marshall/build-queue.json`` by default, overridable via
``PLAN_MARSHALL_HOME``) regardless of the caller's cwd, because build-session
coordination spans EVERY checkout on the host, not just one repository: sessions
in different repos must all contend for the one shared queue. This is distinct
from the per-repo main-anchored exception (``merge.lock``,
``run-configuration.json``, ``lessons-learned``, ``merge-queue.json``,
``orchestrator``) that ``merge_lock`` still uses — build-queue.json is NOT a
member of that per-repo bounded set; it belongs to the machine-global tier.
Because the queue records holders from multiple checkouts, each active/waiting
entry is stamped at acquire with ``project_root = str(main_checkout_root())`` so
its liveness is later judged against the checkout it originated in.

**Concurrency correctness (TOCTOU / check-then-act):** the admit/release cycle is
a read-modify-write (read the queue → decide admit/promote → write the queue) —
a classic check-then-act window across concurrent build sessions. Every mutation
runs inside :func:`_locks_core.rmw_json`, which serializes the cycle with an
``O_EXCL`` guard-file mutex and commits via an atomic temp-file replace, so the
slot boundary is never over-admitted and a FIFO promote never double-promotes or
loses a waiting entry. The TOCTOU / check-then-act mitigation menu lives in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``
and is not duplicated here.

**Holder liveness via the shared core (no duplicate).** The plan-liveness
predicate is :func:`_locks_core.holder_is_dead`, imported from the shared
coordination core, NOT re-implemented here — a holder is dead when its plan dir
lives in NEITHER the checkout NOR the worktree of the project that recorded it.
Because the queue is machine-global, the prune passes each entry's stamped
``project_root`` so a foreign project's live holder is judged against its OWN
checkout and never reclaimed by a session in a different repo. The plan_id is
recovered from the admission id (everything before the trailing ``:{uuid4}``), so
a crashed session whose plan dir is gone has its active slot reclaimed under
contention without ever evicting a live slot holder.

**[LOCK] observability (best-effort, OUTSIDE the atomic window).** Each build-queue
lifecycle outcome emits a ``[LOCK]`` event through the shared
:func:`_locks_core.log_lock_event` helper into the SINGLE main-anchored global
lock-event log — always AFTER ``rmw_json`` commits, NEVER from inside the
``_mutate`` callback (which ``rmw_json``'s docstring forbids from doing its own
I/O). ``acquire`` emits ``acquired`` on an ``admitted`` outcome and ``blocked``
on a ``blocked`` outcome (carrying ``active_count`` / ``waiting_count``; the
waiter on a block is this ``plan_id``); ``release`` emits ``released`` on a real
release and ALSO ``acquired`` for a FIFO-promoted waiter (its slot was just
granted, so the promotion is recorded in the same timeline). BOTH actions emit a
WARN-level ``reaped-stale`` event (carrying ``held`` and ``threshold``) for each
over-age active entry the implicit :func:`validate_lock_queue` reaper reclaimed.
A no-op release emits nothing. The ``lock_id`` is the admission id
``{plan_id}:{uuid4}``. A
logging failure is swallowed and cannot affect admission/release.
"""

from __future__ import annotations

import time
import uuid
from argparse import Namespace
from pathlib import Path
from typing import Any

from _locks_core import holder_is_dead, log_lock_event, rmw_json
from file_ops import get_marshal_path, read_json
from marketplace_paths import (
    home_root,
    main_checkout_root,
)
from run_config import (
    _read_build_queue_upper_limit,
    _write_build_queue_upper_limit,
)
from triage_helpers import (
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)

_QUEUE_FILENAME = 'build-queue.json'
_DEFAULT_MAX_SLOTS = 5


# ---------------------------------------------------------------------------
# Main-anchored resolution + config
# ---------------------------------------------------------------------------


def _resolve_queue_path() -> Path:
    """Resolve the build-queue path under the machine-global home root.

    The build queue coordinates build sessions across EVERY checkout on the host,
    so it lives under the machine-global home-root tier
    (:func:`marketplace_paths.home_root`) — ``~/.plan-marshall/build-queue.json``
    by default, overridable via ``PLAN_MARSHALL_HOME`` — NOT a per-repo
    main-anchored path. It is host-wide and does not depend on git resolution.
    """
    return home_root() / _QUEUE_FILENAME


def _resolve_max_slots() -> int:
    """Read ``build.queue.max_slots`` from marshal.json, defaulting to 5.

    marshal.json is the cwd-relative tracked config (content-identical across
    main and the pinned worktree, since it is git-tracked). A missing file,
    missing ``build`` block, missing ``queue`` block, missing ``max_slots`` key,
    or a non-positive / non-integer value all fall back to the conservative
    default so a misconfigured queue still admits at a sane bound rather than
    zero.
    """
    config = read_json(get_marshal_path(), default={})
    if not isinstance(config, dict):
        return _DEFAULT_MAX_SLOTS
    build = config.get('build')
    if not isinstance(build, dict):
        return _DEFAULT_MAX_SLOTS
    block = build.get('queue')
    if not isinstance(block, dict):
        return _DEFAULT_MAX_SLOTS
    raw = block.get('max_slots')
    if isinstance(raw, bool) or not isinstance(raw, int):
        return _DEFAULT_MAX_SLOTS
    return raw if raw > 0 else _DEFAULT_MAX_SLOTS


# ---------------------------------------------------------------------------
# State shape helpers
# ---------------------------------------------------------------------------


def _entry_list(state: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Return ``state[key]`` as a list of entry dicts, treating junk as empty.

    A corrupt or absent ``active`` / ``waiting`` / ``run_log`` value (missing,
    non-list, or holding non-dict elements) degrades to an empty list so a
    malformed file is rebuilt from scratch rather than crashing the mutator.
    """
    raw = state.get(key)
    if not isinstance(raw, list):
        return []
    return [e for e in raw if isinstance(e, dict) and isinstance(e.get('id'), str)]


def _plan_id_of(entry_id: str) -> str:
    """Recover the holder ``plan_id`` from an admission id ``{plan_id}:{uuid4}``.

    The id is composed as ``{plan_id}:{uuid4}`` and a plan_id may itself contain
    colons, so the plan_id is everything BEFORE the final colon. An id with no
    colon (malformed) yields an empty plan_id, which :func:`holder_is_dead`
    treats as dead — so a malformed active entry is reclaimable.
    """
    head, sep, _tail = entry_id.rpartition(':')
    return head if sep else ''


def _prune_dead_active(active: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop active entries whose holder plan is dead (crashed session reclaim).

    A holder is dead when its plan dir lives in NEITHER the checkout NOR the
    worktree of the project that recorded it. Because the queue is machine-global
    (shared across every checkout), each entry's liveness is judged against the
    project it originated in — its stamped ``project_root`` — via
    ``holder_is_dead(plan_id, project_root=e.get('project_root'))``, so a FOREIGN
    project's live holder is never reclaimed by a session in a different checkout.
    A legacy entry lacking ``project_root`` falls back to caller-anchored
    resolution (``project_root=None``), which is harmless under the breaking
    clean-start. Reclaiming dead active slots before the capacity check frees
    slots wedged by a crashed build session without ever evicting a LIVE holder.
    """
    return [
        e
        for e in active
        if not holder_is_dead(_plan_id_of(e['id']), project_root=e.get('project_root'))
    ]


def validate_lock_queue(
    state: dict[str, Any], now: float, upper_limit: int, max_slots: int
) -> list[dict[str, Any]]:
    """Reap over-age active entries and FIFO-promote waiters into freed slots.

    A pure mutation over the passed-in ``state`` (it does NO file I/O — it is
    called from inside an ``rmw_json`` ``_mutate`` callback, which the rmw
    contract forbids from performing its own I/O). It is the queue's positive,
    time-based self-healing reaper, complementing the dead-holder prune
    (:func:`_prune_dead_active`): a holder that was hard-killed (``SIGKILL`` past
    the Python ``finally``) leaves a *live-looking* active entry — its plan dir
    still exists — that the liveness prune never clears, so without a time-based
    reaper its slot starves the queue indefinitely.

    The reap threshold is ``2 × upper_limit`` (the ``2 ×`` safety factor over the
    already monotonic-up adaptive limit makes a false reap of a genuinely long
    build vanishingly unlikely). Age is measured from ``active_since`` — the
    wall-clock time the entry entered ``active`` — NOT from ``ts`` (the
    admit/enqueue time used for FIFO ordering): a promoted entry's ``ts`` is its
    original enqueue time, so measuring age from ``ts`` would over-age a recently
    promoted entry. An entry with NO ``active_since`` (written before this change
    shipped) is treated as ``now`` and is therefore never reaped on first contact.

    After reaping, waiting entries are FIFO-promoted (oldest admit-``ts`` first)
    into the freed slots up to ``max_slots``, each stamped with a fresh
    ``active_since``. The function mutates ``state['active']`` / ``state['waiting']``
    in place and returns the list of reaped entries (each carrying its ``id`` and
    computed ``held`` duration) so the caller can emit a best-effort
    ``reaped-stale`` ``[LOCK]`` event AFTER the ``rmw_json`` commit.
    """
    threshold = 2 * upper_limit
    active = _entry_list(state, 'active')
    waiting = _entry_list(state, 'waiting')

    reaped: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    for entry in active:
        active_since = entry.get('active_since', now)
        held = now - active_since
        if held > threshold:
            reaped.append({'id': entry['id'], 'held': held})
        else:
            survivors.append(entry)
    active = survivors

    # FIFO-promote the oldest waiting entries (smallest admit-ts) into the slots
    # freed by the reap, stamping a fresh active_since on each promoted entry.
    if waiting and len(active) < max_slots:
        free = max_slots - len(active)
        promotable = sorted(waiting, key=lambda e: e.get('ts', 0.0))[:free]
        promoted_ids = {e['id'] for e in promotable}
        for entry in promotable:
            entry['active_since'] = now
            active.append(entry)
        waiting = [e for e in waiting if e['id'] not in promoted_ids]

    state['active'] = active
    state['waiting'] = waiting
    return reaped


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def run_acquire(args: Namespace) -> dict[str, Any]:
    """Acquire a build slot for ``--plan-id`` (admit or enqueue), idempotently.

    Under the serialized read-modify-write, prunes dead active holders, then
    resolves the admission for ``plan_id`` **idempotently**:

    * If ``plan_id`` already holds an ``active`` slot, its existing id is returned
      with ``admission: admitted`` — no new entry, no slot double-claim.
    * If ``plan_id`` already has a ``waiting`` entry, that entry KEEPS its FIFO
      position (it is NOT re-appended to the back). When a slot has since freed up
      and the entry is now within the first ``max_slots - len(active)`` waiting
      entries by admit-``ts``, it is promoted to ``active`` → ``admission:
      admitted`` (reusing its existing id); otherwise it stays ``blocked`` with
      the same id.
    * Only when ``plan_id`` has NO existing entry is a fresh admission id
      ``{plan_id}:{uuid4}`` generated and admitted (slot free) or enqueued at the
      back of the FIFO waiting queue (at capacity).

    Idempotence is the FIFO-preservation guarantee: the build wrapper re-polls
    ``acquire`` while blocked WITHOUT releasing first, so a queued plan retains its
    place rather than being shuffled to the back on every poll. A ``blocked``
    result is a structured signal the wrapper re-polls against, not an error.
    """
    plan_id: str = args.plan_id
    queue_path = _resolve_queue_path()
    # Stamp this session's originating checkout so a foreign project's live holder
    # is judged against ITS checkout (machine-global queue). main_checkout_root()
    # raises when the caller is not in a git repo — a real error for a build.
    try:
        project_root = str(main_checkout_root())
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    max_slots = _resolve_max_slots()
    upper_limit = _read_build_queue_upper_limit()
    new_entry_id = f'{plan_id}:{uuid.uuid4()}'
    ts = time.time()
    outcome: dict[str, Any] = {'reaped': []}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        # Self-healing reaper FIRST (inside the SAME rmw_json mutation): reap any
        # over-age active entry and FIFO-promote waiters into the freed slots,
        # then run the existing prune/admit logic on the reaped state. Running it
        # here (not as a separate rmw call) keeps the reap + admit decision in one
        # serialized read-modify-write, so a reap can never race a concurrent admit.
        outcome['reaped'] = validate_lock_queue(state, ts, upper_limit, max_slots)

        active = _prune_dead_active(_entry_list(state, 'active'))
        waiting = _entry_list(state, 'waiting')
        run_log = _entry_list(state, 'run_log')

        # Idempotent fast-path: a plan already holding an active slot keeps it.
        existing_active = next((e for e in active if e.get('plan_id') == plan_id), None)
        if existing_active is not None:
            outcome['id'] = existing_active['id']
            outcome['admission'] = 'admitted'
            outcome['active_count'] = len(active)
            outcome['waiting_count'] = len(waiting)
            return {'active': active, 'waiting': waiting, 'run_log': run_log}

        # Idempotent re-poll: a plan already in the waiting queue keeps its FIFO
        # position. Promote it ONLY when a slot has freed up AND it is within the
        # available-slot prefix of the FIFO-ordered (by admit-ts) waiting queue —
        # never re-append to the back.
        existing_waiting = next((e for e in waiting if e.get('plan_id') == plan_id), None)
        if existing_waiting is not None:
            free = max_slots - len(active)
            promotable = sorted(waiting, key=lambda e: e.get('ts', 0.0))[:max(free, 0)]
            if any(e['id'] == existing_waiting['id'] for e in promotable):
                waiting = [e for e in waiting if e['id'] != existing_waiting['id']]
                existing_waiting['active_since'] = time.time()
                active.append(existing_waiting)
                outcome['admission'] = 'admitted'
            else:
                outcome['admission'] = 'blocked'
            outcome['id'] = existing_waiting['id']
            outcome['active_count'] = len(active)
            outcome['waiting_count'] = len(waiting)
            return {'active': active, 'waiting': waiting, 'run_log': run_log}

        # First acquire for this plan: admit when a slot is free, else enqueue at
        # the back of the FIFO waiting queue. An admitted entry records
        # active_since (the slot activation time used by the reaper); a queued
        # entry does not — it is not active yet. Every new entry is stamped with
        # project_root so the machine-global prune judges its liveness against the
        # checkout it originated in.
        entry = {'id': new_entry_id, 'plan_id': plan_id, 'ts': ts, 'project_root': project_root}
        if len(active) < max_slots:
            entry['active_since'] = ts
            active.append(entry)
            outcome['admission'] = 'admitted'
        else:
            waiting.append(entry)
            outcome['admission'] = 'blocked'
        outcome['id'] = new_entry_id
        outcome['active_count'] = len(active)
        outcome['waiting_count'] = len(waiting)
        return {'active': active, 'waiting': waiting, 'run_log': run_log}

    rmw_json(queue_path, _mutate)

    # [LOCK] reaped-stale emission — best-effort, AFTER rmw_json commits (never
    # from inside _mutate). One WARN event per reaped over-age active entry.
    for reaped in outcome['reaped']:
        log_lock_event(
            'build',
            'reaped-stale',
            lock_id=reaped['id'],
            held=reaped['held'],
            threshold=2 * upper_limit,
        )

    # [LOCK] emission — best-effort, AFTER rmw_json commits (never from inside
    # _mutate). `admitted` → `acquired`; `blocked` → `blocked` (waiter is self).
    if outcome['admission'] == 'admitted':
        log_lock_event(
            'build',
            'acquired',
            lock_id=outcome['id'],
            active_count=outcome['active_count'],
            waiting_count=outcome['waiting_count'],
        )
    else:
        log_lock_event(
            'build',
            'blocked',
            lock_id=outcome['id'],
            waiter=plan_id,
            active_count=outcome['active_count'],
            waiting_count=outcome['waiting_count'],
        )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'id': outcome['id'],
        'admission': outcome['admission'],
        'max_slots': max_slots,
        'active_count': outcome['active_count'],
        'waiting_count': outcome['waiting_count'],
        'queue_path': str(queue_path),
    }


def run_release(args: Namespace) -> dict[str, Any]:
    """Release the build slot held by ``--id`` and FIFO-promote the next waiter.

    Removes ``--id`` from ``active`` (and defensively from ``waiting``, so a
    release of a still-queued id is benign), then — when a slot is now free —
    FIFO-promotes the oldest waiting entry (by admit-``ts``) into ``active`` and
    records it as the ``promoted`` id. On a real release (the id was actually
    present), appends an id+timestamp entry to the ``run_log`` and prunes it to
    the most recent 100 entries so ``build-queue.json`` stays bounded; a no-op
    release of an absent id leaves the ``run_log`` untouched. Releasing an id
    that is not present is an idempotent no-op success (``action: noop``) so a
    crashed-and-retried release does not error.
    """
    plan_id: str = args.plan_id
    target_id: str = args.id
    try:
        queue_path = _resolve_queue_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    max_slots = _resolve_max_slots()
    upper_limit = _read_build_queue_upper_limit()
    now = time.time()
    outcome: dict[str, Any] = {'reaped': [], 'held': None}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        # Self-healing reaper FIRST (inside the SAME rmw_json mutation), then the
        # existing release/promote logic runs on the reaped state — one serialized
        # read-modify-write covering reap + release.
        outcome['reaped'] = validate_lock_queue(state, now, upper_limit, max_slots)

        active = _entry_list(state, 'active')
        waiting = _entry_list(state, 'waiting')
        run_log = _entry_list(state, 'run_log')

        # Capture the released entry's active_since so the caller can compute the
        # held duration for the adaptive-limit recompute (only meaningful when the
        # released id was a real active holder).
        released_entry = next((e for e in active if e['id'] == target_id), None)
        if released_entry is not None and 'active_since' in released_entry:
            outcome['held'] = now - released_entry['active_since']

        before = len(active) + len(waiting)
        active = [e for e in active if e['id'] != target_id]
        waiting = [e for e in waiting if e['id'] != target_id]
        removed = (len(active) + len(waiting)) < before
        outcome['action'] = 'released' if removed else 'noop'

        # FIFO-promote the oldest waiting entry (smallest admit-ts) when the
        # release freed a slot. Each released slot promotes exactly one distinct
        # waiting entry — never two — so concurrent releases (serialized by the
        # rmw guard) cannot double-promote or lose a waiting entry. The promoted
        # entry is stamped with a fresh active_since (it is only now active).
        promoted: str | None = None
        if waiting and len(active) < max_slots:
            oldest = min(waiting, key=lambda e: e.get('ts', 0.0))
            waiting = [e for e in waiting if e['id'] != oldest['id']]
            oldest['active_since'] = time.time()
            active.append(oldest)
            promoted = oldest['id']
        outcome['promoted'] = promoted

        # Append to the run_log ONLY on a real release (the id was actually
        # present in active/waiting), so a no-op release of an absent id does not
        # accrete a stale entry, then prune to the most recent 100 entries — the
        # log is a bounded audit tail, not an unbounded history, so build-queue.json
        # cannot grow without limit across a long-lived cluster.
        if removed:
            run_log.append({'id': target_id, 'plan_id': plan_id, 'ts': time.time()})
            run_log = run_log[-100:]
        outcome['active_count'] = len(active)
        outcome['waiting_count'] = len(waiting)
        return {'active': active, 'waiting': waiting, 'run_log': run_log}

    rmw_json(queue_path, _mutate)

    # Adaptive-limit recompute (clamped [600, 3600]) — OUTSIDE _mutate (it writes
    # a SEPARATE config file, not the queue file). The new limit tracks the
    # longest observed real build held-duration monotonically-up; persist only
    # when it would actually change. _write_build_queue_upper_limit clamps to
    # [600, 3600], so a single anomalously long held lock cannot ratchet the
    # stored limit past the 3600 s ceiling.
    held = outcome['held']
    if held is not None:
        new_limit = max(upper_limit, int(held))
        if new_limit != upper_limit:
            _write_build_queue_upper_limit(new_limit)

    # [LOCK] reaped-stale emission — best-effort, AFTER rmw_json commits (never
    # from inside _mutate). One WARN event per reaped over-age active entry.
    for reaped in outcome['reaped']:
        log_lock_event(
            'build',
            'reaped-stale',
            lock_id=reaped['id'],
            held=reaped['held'],
            threshold=2 * upper_limit,
        )

    # [LOCK] emission — best-effort, AFTER rmw_json commits (never from inside
    # _mutate). A real release emits `released`; a no-op release emits nothing.
    # A FIFO-promoted waiter additionally emits `acquired` (its slot was just
    # granted), recording the promotion in the same main-anchored timeline.
    if outcome['action'] == 'released':
        log_lock_event(
            'build',
            'released',
            lock_id=target_id,
            active_count=outcome['active_count'],
            waiting_count=outcome['waiting_count'],
        )
        if outcome['promoted'] is not None:
            log_lock_event(
                'build',
                'acquired',
                lock_id=outcome['promoted'],
                active_count=outcome['active_count'],
                waiting_count=outcome['waiting_count'],
            )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'id': target_id,
        'action': outcome['action'],
        'promoted': outcome['promoted'],
        'max_slots': max_slots,
        'active_count': outcome['active_count'],
        'waiting_count': outcome['waiting_count'],
        'queue_path': str(queue_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point — ``acquire`` / ``release`` actions."""
    parser = create_workflow_cli(
        description='Build-queue concurrency limiter: bounded-k-slot admitter with a FIFO waiting queue',
        epilog="""
Examples:
  build_queue.py acquire --plan-id EXAMPLE-PLAN
  build_queue.py release --plan-id EXAMPLE-PLAN --id EXAMPLE-PLAN:UUID
""",
        subcommands=[
            {
                'name': 'acquire',
                'help': 'Admit a build slot (or enqueue when at capacity)',
                'handler': run_acquire,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Holder source — the plan_id acquiring a slot (mandatory)',
                    },
                ],
            },
            {
                'name': 'release',
                'help': 'Release a build slot and FIFO-promote the oldest waiting entry',
                'handler': run_release,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Holder source — the plan_id releasing a slot (mandatory)',
                    },
                    {
                        'flags': ['--id'],
                        'dest': 'id',
                        'required': True,
                        'help': 'The admission id returned by acquire (mandatory)',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
