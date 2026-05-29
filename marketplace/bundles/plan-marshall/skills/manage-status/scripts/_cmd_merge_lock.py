#!/usr/bin/env python3
"""Cross-plan merge-lock verb for manage-status.

Implements the ``merge-lock`` sub-verbs (``acquire`` / ``check`` /
``release``) that serialize the rebase/merge-to-main critical section
across concurrently-finalizing plans. The lock is a cooperative marker
stored under ``status.metadata`` of the acquiring plan — written, read,
and cleared exclusively through the ``_status_core`` helpers, never via
direct ``.plan/`` file access.

The marker carries two fields under ``status.metadata``:

  - ``merging_on_main`` (bool): ``True`` while the plan holds the lock.
  - ``merge_lock_acquired_at`` (ISO-8601 UTC string): the acquisition
    timestamp, so contention diagnostics can identify how long the
    holder has held the marker.

``acquire`` scans every OTHER plan's ``status.json`` (via the same
plan-discovery path ``cmd_list`` uses) for an existing holder. If the
lock is free it writes the marker for this plan, then re-reads to guard
against a concurrent writer (check-then-act TOCTOU): if another plan wrote
its marker in the same window, a deterministic tiebreaker resolves the
contention — the lexicographically LARGER ``plan_id`` yields (clears its
marker and keeps polling), so the smaller ``plan_id`` is the sole winner.
A sole writer (or the tiebreaker winner) returns ``status: acquired``.
If held it enters a ``time.sleep`` poll loop — fixed module-level
interval, total window 5 minutes / 300 s — re-checking each interval, and
on elapse returns ``status: blocked`` with ``blocking_plan_id``. The poll
lives entirely inside this Python handler; there is never a Bash poll loop.

``check`` is a non-blocking read returning the current holder (or none).
``release`` clears this plan's marker idempotently (no-op when not held).

``AskUserQuestion`` is NEVER issued from this module — the timeout path
only returns the structured ``blocked`` payload. The orchestrator
(branch-cleanup.md Pre-Merge Gate) owns the user-prompt escalation.

The poll window and interval are module-level constants so the test
suite can monkeypatch them to keep contention cases fast.
"""

from __future__ import annotations

import time
from typing import Any

from _status_core import read_status, write_status
from file_ops import get_plan_dir, now_utc_iso  # type: ignore[import-not-found]
from plan_logging import log_entry  # type: ignore[import-not-found]

# Total blocking-acquire window, in seconds. The default is 5 minutes; the
# constant is module-level so tests can monkeypatch it to a sub-second value.
MERGE_LOCK_POLL_WINDOW_SECONDS: float = 300.0

# Poll interval between re-checks while blocked, in seconds. Module-level so
# tests can monkeypatch it alongside the window.
MERGE_LOCK_POLL_INTERVAL_SECONDS: float = 5.0

# Marker field names under status.metadata.
_MARKER_FIELD = 'merging_on_main'
_ACQUIRED_AT_FIELD = 'merge_lock_acquired_at'


def _find_holder(exclude_plan_id: str) -> str | None:
    """Return the plan_id currently holding the merge-lock, or None.

    Scans every plan directory under the plans root (same discovery path
    ``cmd_list`` uses) and returns the first plan — other than
    ``exclude_plan_id`` — whose ``status.metadata.merging_on_main`` is
    truthy. Returns None when no other plan holds the marker.
    """
    # Imported lazily to mirror the discovery path cmd_list uses while keeping
    # this module's import surface minimal.
    from _status_core import _try_read_status_json, get_plans_dir

    plans_dir = get_plans_dir()
    if not plans_dir.exists():
        return None

    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir():
            continue
        if plan_dir.name == exclude_plan_id:
            continue
        status = _try_read_status_json(plan_dir)
        if not status:
            continue
        metadata = status.get('metadata') or {}
        if metadata.get(_MARKER_FIELD):
            return plan_dir.name
    return None


def _write_marker(plan_id: str) -> str:
    """Write the merge-lock marker for ``plan_id`` and return the timestamp."""
    status = read_status(plan_id)
    if 'metadata' not in status or not isinstance(status['metadata'], dict):
        status['metadata'] = {}
    acquired_at = now_utc_iso()
    status['metadata'][_MARKER_FIELD] = True
    status['metadata'][_ACQUIRED_AT_FIELD] = acquired_at
    write_status(plan_id, status)
    return acquired_at


def _clear_marker(plan_id: str) -> None:
    """Clear this plan's merge-lock marker (tiebreaker-loser path).

    Removes the ``merging_on_main`` / ``merge_lock_acquired_at`` fields from
    ``status.metadata`` via the same ``_status_core`` helpers ``release`` uses,
    so the loser of a concurrent-acquire tiebreaker relinquishes the lock
    without any direct ``.plan/`` file access. Idempotent — a no-op when the
    marker is absent.
    """
    status = read_status(plan_id)
    metadata = status.get('metadata')
    if isinstance(metadata, dict) and metadata.get(_MARKER_FIELD):
        metadata.pop(_MARKER_FIELD, None)
        metadata.pop(_ACQUIRED_AT_FIELD, None)
        write_status(plan_id, status)


def cmd_merge_lock_acquire(args: Any) -> dict[str, Any]:
    """Blocking acquire of the cross-plan merge-lock.

    Returns ``status: acquired`` when the marker is claimed (immediately or
    after a held lock frees within the poll window), or ``status: blocked``
    with ``blocking_plan_id`` when the poll window elapses while another
    plan still holds the lock.
    """
    plan_id: str = args.plan_id

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    deadline = time.monotonic() + MERGE_LOCK_POLL_WINDOW_SECONDS
    blocking_plan_id: str | None = None

    while True:
        holder = _find_holder(plan_id)
        if holder is None:
            # Optimistically claim the lock, then re-read to detect a
            # concurrent writer that observed holder=None in the same window.
            acquired_at = _write_marker(plan_id)

            # Double-check: did another plan also write its marker concurrently?
            # _find_holder excludes this plan, so a non-None result here means a
            # genuine competing holder, not our own freshly-written marker.
            competitor = _find_holder(plan_id)
            if competitor is not None and plan_id > competitor:
                # Deterministic tiebreaker: the lexicographically LARGER
                # plan_id yields. Relinquish our marker and keep polling so the
                # smaller plan_id is the sole winner.
                _clear_marker(plan_id)
                log_entry(
                    'work',
                    plan_id,
                    'INFO',
                    f'[MANAGE-STATUS] (merge-lock) {plan_id} yielded to '
                    f'{competitor} on concurrent-acquire tiebreaker — '
                    f'cleared marker, continuing poll',
                )
                blocking_plan_id = competitor
                if time.monotonic() >= deadline:
                    break
                time.sleep(MERGE_LOCK_POLL_INTERVAL_SECONDS)
                continue

            # No competitor, or we hold the smaller plan_id → we won.
            log_entry(
                'work',
                plan_id,
                'INFO',
                f'[MANAGE-STATUS] (merge-lock) acquired by {plan_id} at {acquired_at}',
            )
            return {
                'status': 'acquired',
                'plan_id': plan_id,
                'acquired_at': acquired_at,
            }

        blocking_plan_id = holder
        if time.monotonic() >= deadline:
            break
        time.sleep(MERGE_LOCK_POLL_INTERVAL_SECONDS)

    log_entry(
        'work',
        plan_id,
        'WARNING',
        f'[MANAGE-STATUS] (merge-lock) {plan_id} blocked — held by {blocking_plan_id} '
        f'after {MERGE_LOCK_POLL_WINDOW_SECONDS}s poll window',
    )
    return {
        'status': 'blocked',
        'plan_id': plan_id,
        'blocking_plan_id': blocking_plan_id,
        'poll_window_seconds': MERGE_LOCK_POLL_WINDOW_SECONDS,
    }


def cmd_merge_lock_check(args: Any) -> dict[str, Any]:
    """Non-blocking read of the current merge-lock holder.

    Returns ``status: free`` when no plan holds the lock, or
    ``status: held`` with ``holder_plan_id`` when one does. The querying
    plan's own marker counts as a holder — ``check`` reports the global
    state, including self-held locks.
    """
    plan_id: str = args.plan_id

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    # Self-held detection: read this plan's own marker directly, since
    # _find_holder excludes the querying plan.
    own_status = read_status(plan_id)
    own_metadata = own_status.get('metadata') or {}
    if own_metadata.get(_MARKER_FIELD):
        return {
            'status': 'held',
            'plan_id': plan_id,
            'holder_plan_id': plan_id,
        }

    holder = _find_holder(plan_id)
    if holder is None:
        return {
            'status': 'free',
            'plan_id': plan_id,
        }
    return {
        'status': 'held',
        'plan_id': plan_id,
        'holder_plan_id': holder,
    }


def cmd_merge_lock_release(args: Any) -> dict[str, Any]:
    """Idempotently clear this plan's merge-lock marker.

    Removes the ``merging_on_main`` / ``merge_lock_acquired_at`` fields from
    ``status.metadata``. A second release (or a release when the plan never
    held the lock) is a no-op — ``released`` is True only when a marker was
    actually present and cleared, ``False`` otherwise.
    """
    plan_id: str = args.plan_id

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    status = read_status(plan_id)
    metadata = status.get('metadata')
    was_held = bool(isinstance(metadata, dict) and metadata.get(_MARKER_FIELD))

    if was_held and isinstance(metadata, dict):
        metadata.pop(_MARKER_FIELD, None)
        metadata.pop(_ACQUIRED_AT_FIELD, None)
        write_status(plan_id, status)
        log_entry(
            'work',
            plan_id,
            'INFO',
            f'[MANAGE-STATUS] (merge-lock) released by {plan_id}',
        )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'released': was_held,
    }
