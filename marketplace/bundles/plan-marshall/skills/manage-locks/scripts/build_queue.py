#!/usr/bin/env python3
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

It exposes two actions:

  * ``acquire`` — generate an admission id ``{plan_id}:{uuid4}`` and, under the
    serialized read-modify-write: prune any dead active holders (their plan dir
    lives in NEITHER the main checkout NOR the holder's worktree — the shared
    :func:`_locks_core.holder_is_dead` predicate), then if ``len(active) <
    max_slots`` append ``{id, ts}`` to ``active`` → ``admission: admitted``;
    else append ``{id, ts}`` to ``waiting`` → ``admission: blocked``. The script
    does NOT loop or wait — the wait+retry loop is the build wrapper's
    responsibility (D6); a ``blocked`` admission is a structured signal the
    caller re-polls ``acquire`` against, not an error.
  * ``release`` — remove ``--id`` from ``active`` (and defensively from
    ``waiting``), FIFO-promote the oldest waiting entry (by admit-``ts``) into
    the freed slot when capacity allows, and append an id+timestamp entry to the
    ``run_log``.

**Main-anchored resolution — via the single sanctioned utility (ADR-002):** the
queue file always resolves against the MAIN checkout regardless of the caller's
cwd, because cross-session coordination is inherently main-scoped: phase-5+
callers run with cwd pinned to their own worktree, yet they must all contend for
one shared queue. This script routes ``build-queue.json`` through the single
sanctioned :func:`marketplace_paths.resolve_main_anchored_path` — the ONE
mechanism covering the bounded exception set (``merge.lock``,
``run-configuration.json``, ``lessons-learned``, ``build-queue.json``). No new
git-common-dir copy is introduced.

**Concurrency correctness (TOCTOU / check-then-act):** the admit/release cycle is
a read-modify-write (read the queue → decide admit/promote → write the queue) —
a classic check-then-act window across concurrent build sessions. Every mutation
runs inside :func:`_locks_core.rmw_json`, which serializes the cycle with an
``O_EXCL`` guard-file mutex and commits via an atomic temp-file replace, so the
slot boundary is never over-admitted and a FIFO promote never double-promotes or
loses a waiting entry. The TOCTOU / check-then-act mitigation menu lives in
``dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``
and is not duplicated here.

**Holder liveness via the shared core (no duplicate).** The plan-liveness
predicate is :func:`_locks_core.holder_is_dead`, imported from the shared
coordination core, NOT re-implemented here — a holder is dead when its plan dir
lives in NEITHER the main checkout NOR the holder's worktree. The plan_id is
recovered from the admission id (everything before the trailing ``:{uuid4}``), so
a crashed session whose plan dir is gone has its active slot reclaimed under
contention without ever evicting a live slot holder.
"""

from __future__ import annotations

import sys
import time
import uuid
from argparse import Namespace
from pathlib import Path
from typing import Any

from _locks_core import holder_is_dead, rmw_json  # type: ignore[import-not-found]
from file_ops import get_marshal_path, read_json  # type: ignore[import-not-found]
from marketplace_paths import (  # type: ignore[import-not-found]
    resolve_main_anchored_path,
)
from triage_helpers import (  # type: ignore[import-not-found]
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
    """Resolve the build-queue path against the MAIN checkout, cwd-independent.

    Delegates to the shared main-anchored resolver
    :func:`marketplace_paths.resolve_main_anchored_path` — the single sanctioned
    mechanism (ADR-002). The queue lives at ``<main>/.plan/local/build-queue.json``.
    """
    return resolve_main_anchored_path(_QUEUE_FILENAME)


def _resolve_max_slots() -> int:
    """Read ``build_queue.max_slots`` from marshal.json, defaulting to 5.

    marshal.json is the cwd-relative tracked config (content-identical across
    main and the pinned worktree, since it is git-tracked). A missing file,
    missing ``build_queue`` block, missing ``max_slots`` key, or a non-positive /
    non-integer value all fall back to the conservative default so a
    misconfigured queue still admits at a sane bound rather than zero.
    """
    config = read_json(get_marshal_path(), default={})
    if not isinstance(config, dict):
        return _DEFAULT_MAX_SLOTS
    block = config.get('build_queue')
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

    A holder is dead when its plan dir lives in NEITHER the main checkout NOR the
    holder's worktree (the shared :func:`_locks_core.holder_is_dead` predicate).
    Reclaiming dead active slots before the capacity check frees slots wedged by
    a crashed build session without ever evicting a LIVE holder.
    """
    return [e for e in active if not holder_is_dead(_plan_id_of(e['id']))]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def run_acquire(args: Namespace) -> dict[str, Any]:
    """Acquire a build slot for ``--plan-id`` (admit or enqueue).

    Generates an admission id ``{plan_id}:{uuid4}`` and, under the serialized
    read-modify-write, prunes dead active holders, then admits the id when a slot
    is free (``len(active) < max_slots``) or appends it to the FIFO waiting queue
    otherwise. Returns ``admission: admitted`` (with the freshly-claimed slot) or
    ``admission: blocked`` (queued behind the waiting entries ahead of it). The
    script never loops — a ``blocked`` result is a structured signal the build
    wrapper re-polls against, not an error.
    """
    plan_id: str = args.plan_id
    try:
        queue_path = _resolve_queue_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    max_slots = _resolve_max_slots()
    entry_id = f'{plan_id}:{uuid.uuid4()}'
    ts = time.time()
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        active = _prune_dead_active(_entry_list(state, 'active'))
        waiting = _entry_list(state, 'waiting')
        run_log = _entry_list(state, 'run_log')

        entry = {'id': entry_id, 'plan_id': plan_id, 'ts': ts}
        if len(active) < max_slots:
            active.append(entry)
            outcome['admission'] = 'admitted'
        else:
            waiting.append(entry)
            outcome['admission'] = 'blocked'
        outcome['active_count'] = len(active)
        outcome['waiting_count'] = len(waiting)
        return {'active': active, 'waiting': waiting, 'run_log': run_log}

    rmw_json(queue_path, _mutate)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'id': entry_id,
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
    records it as the ``promoted`` id. Appends an id+timestamp entry to the
    ``run_log``. Releasing an id that is not present is an idempotent no-op
    success (``action: noop``) so a crashed-and-retried release does not error.
    """
    plan_id: str = args.plan_id
    target_id: str = args.id
    try:
        queue_path = _resolve_queue_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    max_slots = _resolve_max_slots()
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        active = _entry_list(state, 'active')
        waiting = _entry_list(state, 'waiting')
        run_log = _entry_list(state, 'run_log')

        before = len(active) + len(waiting)
        active = [e for e in active if e['id'] != target_id]
        waiting = [e for e in waiting if e['id'] != target_id]
        removed = (len(active) + len(waiting)) < before
        outcome['action'] = 'released' if removed else 'noop'

        # FIFO-promote the oldest waiting entry (smallest admit-ts) when the
        # release freed a slot. Each released slot promotes exactly one distinct
        # waiting entry — never two — so concurrent releases (serialized by the
        # rmw guard) cannot double-promote or lose a waiting entry.
        promoted: str | None = None
        if waiting and len(active) < max_slots:
            oldest = min(waiting, key=lambda e: e.get('ts', 0.0))
            waiting = [e for e in waiting if e['id'] != oldest['id']]
            active.append(oldest)
            promoted = oldest['id']
        outcome['promoted'] = promoted

        run_log.append({'id': target_id, 'plan_id': plan_id, 'ts': time.time()})
        outcome['active_count'] = len(active)
        outcome['waiting_count'] = len(waiting)
        return {'active': active, 'waiting': waiting, 'run_log': run_log}

    rmw_json(queue_path, _mutate)

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
    sys.exit(safe_main(main))
