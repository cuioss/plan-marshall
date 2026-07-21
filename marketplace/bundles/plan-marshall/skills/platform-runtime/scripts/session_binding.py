#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure session->plan binding policy for platform-runtime.

The single importable home of the per-session ``active-plan`` cache policy —
the read side (relocated from ``claude_runtime._read_active_plan``), the write
side (relocated from the executor template's ``_write_active_plan``), and a
conflict/stale-slot scan. Kept as a pure, dependency-free module so it is
unit-testable against a tmp cache without going through the generated executor.

Four entry points:

- :func:`resolve_plan` — read the caller session's bound plan_id.
- :func:`bind` — last-driven-wins unconditional write of the caller's OWN slot.
  NO protect-active, NO stale-slot reclaim, NO plan-dir-exists check.
- :func:`unbind` — remove the caller's OWN slot (the teardown counterpart of
  :func:`bind`), pruning the now-empty session directory.
- :func:`doctor` — visit every directory under
  ``~/.cache/plan-marshall/sessions/``, build a plan->sessions reverse index in
  memory from the live slots, flag any plan bound by more than one live session,
  and (when ``fix``) GC slots whose plan is archived/deleted plus orphan
  directories that yield no live slot at all.

Concurrency-correctness: the ``active-plan`` cache is per-session (keyed by
``session_id``), so :func:`bind` writes only the caller's own slot — there is no
cross-session check-then-act window. :func:`doctor` keeps NO shared mutable
index (no ``index.json``), so the per-file scan-then-GC is idempotent. No new
shared-file TOCTOU hazard is introduced. Every path is best-effort / no-raise.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Per-session active-plan cache root. Resolved once at import; tests redirect
# the cache to a tmp dir by monkeypatching this module attribute. Path.home()
# raises RuntimeError when HOME is unset/inaccessible (minimal containers,
# restricted CI), so resolve it behind a fallback to keep import side-effect-free.
try:
    _CACHE_HOME = Path.home()
except (RuntimeError, OSError):
    _CACHE_HOME = Path(os.environ.get("HOME") or "/tmp")
_SESSION_CACHE_BASE = _CACHE_HOME / ".cache" / "plan-marshall" / "sessions"

# Tracked plan-directory name (mirrors the executor / claude_runtime resolution).
_PLAN_DIR_NAME = os.environ.get("PLAN_DIR_NAME", ".plan")

# Single-segment cap for the session-id and plan-id cache values. Both are
# written / read as one path segment under the cache root, so the security
# boundary is single-segment safety (traversal rejection + length cap), matching
# the executor template's original ``_validate_active_plan_id`` — NOT a canonical
# UUID match (that stricter shape is only needed for transcript-path globbing,
# which lives in claude_runtime).
_SEGMENT_MAX_LEN = 120


# ---------------------------------------------------------------------------
# Shape validators
# ---------------------------------------------------------------------------


def _valid_segment(value: str) -> bool:
    """Return True when ``value`` is a safe single-segment cache key.

    The session-id and plan-id are each written as one path segment under the
    cache root, so any value containing ``/`` or ``\\``, matching a
    path-traversal sentinel, exceeding the length cap, or empty is rejected —
    the guard against escaping the session-cache root.
    """
    if not isinstance(value, str):
        return False
    if not value or len(value) > _SEGMENT_MAX_LEN:
        return False
    if "\x00" in value:
        return False
    if "/" in value or "\\" in value:
        return False
    if value in (".", ".."):
        return False
    return True


def _valid_session_id(session_id: str) -> bool:
    """Return True when ``session_id`` is a safe single-segment cache key."""
    return _valid_segment(session_id)


def _valid_plan_id(plan_id: str) -> bool:
    """Return True when ``plan_id`` is a safe single-segment cache value."""
    return _valid_segment(plan_id)


def _active_plan_path(session_id: str) -> Path:
    """Return the ``active-plan`` cache file path for ``session_id``."""
    return _SESSION_CACHE_BASE / session_id / "active-plan"


# ---------------------------------------------------------------------------
# Read / write policy
# ---------------------------------------------------------------------------


def resolve_plan(session_id: str) -> str | None:
    """Return the plan_id bound to ``session_id``, or ``None`` when unbound.

    Best-effort read of
    ``~/.cache/plan-marshall/sessions/{session_id}/active-plan``. A malformed
    session_id, a missing/unreadable file, or an empty value yields ``None``.
    Never raises.
    """
    if not _valid_session_id(session_id):
        return None
    try:
        raw = _active_plan_path(session_id).read_text(encoding="utf-8").strip()
        return raw or None
    except OSError:
        return None


def bind(session_id: str, plan_id: str) -> bool:
    """Bind ``plan_id`` to ``session_id``'s slot, last-driven-wins.

    Validates the session-UUID and plan-id shapes, then UNCONDITIONALLY writes
    the caller's own slot — NO protect-active, NO stale-slot reclaim, NO
    plan-dir-exists check. Because the cache is per-session this touches only the
    caller's slot and has no cross-session check-then-act window.

    Returns True when the slot was written, False on validation failure or any
    I/O error. Best-effort: never raises.
    """
    if not _valid_session_id(session_id) or not _valid_plan_id(plan_id):
        return False
    try:
        target = _active_plan_path(session_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(plan_id, encoding="utf-8")
        return True
    except OSError:
        return False


def _remove_slot_and_prune(path: Path) -> bool:
    """Remove an ``active-plan`` slot file and prune its now-empty session dir.

    The single home of the unlink-then-rmdir body, shared by the public
    :func:`unbind` teardown and the doctor's orphan-directory prune. ``path`` is
    the ``active-plan`` file path; an already-absent file is not an error (the
    orphan-directory case has no slot file at all, only the empty directory).

    Returns True when the slot is gone, False on any I/O error. Never raises.
    """
    try:
        path.unlink(missing_ok=True)
        # Best-effort: prune the now-empty session directory so teardown/GC does
        # not leak empty dirs over time. Non-empty / already-gone → OSError,
        # ignored.
        try:
            path.parent.rmdir()
        except OSError:
            pass
        return True
    except OSError:
        return False


def unbind(session_id: str) -> bool:
    """Remove ``session_id``'s own ``active-plan`` slot — the teardown of :func:`bind`.

    Deletes ``~/.cache/plan-marshall/sessions/{session_id}/active-plan`` and
    prunes the now-empty session directory. Same validation, same per-session
    scope, and the same best-effort / no-raise contract as :func:`bind`: because
    the cache is keyed by ``session_id`` this touches only the caller's own slot,
    so there is no cross-session check-then-act window.

    Returns True when the slot was removed (or was already absent), False on
    validation failure or any I/O error. Never raises.
    """
    if not _valid_session_id(session_id):
        return False
    return _remove_slot_and_prune(_active_plan_path(session_id))


# ---------------------------------------------------------------------------
# Doctor — reverse-index conflict scan + stale-slot GC
# ---------------------------------------------------------------------------


def _plan_is_live(plan_id: str) -> bool:
    """Return True when ``plan_id`` names a live (non-archived, non-deleted) plan.

    A plan is live when its main-checkout plan dir
    (``{PLAN_DIR_NAME}/local/plans/{plan_id}``) exists, OR its phase-5+ worktree
    copy
    (``{PLAN_DIR_NAME}/local/worktrees/{plan_id}/{PLAN_DIR_NAME}/local/plans/{plan_id}``)
    exists. Resolved relative to cwd (the project root). Archived plans (moved to
    ``archived-plans/``) and deleted plans are NOT live and their session slots
    are GC-eligible.

    Best-effort: any resolution error yields False (treated as not-live).
    """
    if not _valid_plan_id(plan_id):
        return False
    try:
        base = Path(_PLAN_DIR_NAME) / "local"
        if (base / "plans" / plan_id).is_dir():
            return True
        worktree = (
            base / "worktrees" / plan_id / _PLAN_DIR_NAME / "local" / "plans" / plan_id
        )
        return worktree.is_dir()
    except (OSError, ValueError):
        return False


def _iter_slots() -> list[tuple[str, str]]:
    """Return ``(session_id, plan_id)`` for every readable active-plan slot.

    Scans ``_SESSION_CACHE_BASE/*/active-plan``. Slots with a malformed
    session-dir name or an empty/unreadable value are skipped. Best-effort — a
    scan error yields an empty list.
    """
    slots: list[tuple[str, str]] = []
    try:
        session_dirs = sorted(_SESSION_CACHE_BASE.iterdir())
    except OSError:
        return slots
    for session_dir in session_dirs:
        try:
            if not session_dir.is_dir():
                continue
        except OSError:
            continue
        session_id = session_dir.name
        if not _valid_session_id(session_id):
            continue
        plan_id = resolve_plan(session_id)
        if plan_id:
            slots.append((session_id, plan_id))
    return slots


def _iter_orphan_dirs() -> list[str]:
    """Return the session-dir names under the cache root that yield no live slot.

    An orphan directory is one that :func:`_iter_slots` skips — its
    ``active-plan`` file is absent, empty, or unreadable, so :func:`resolve_plan`
    returns ``None`` and the directory carries no binding at all. These are the
    residue :func:`unbind`'s prune could not remove (a non-empty dir at teardown,
    or a slot written by a crashed writer). Best-effort — a scan error yields an
    empty list.
    """
    orphans: list[str] = []
    try:
        session_dirs = sorted(_SESSION_CACHE_BASE.iterdir())
    except OSError:
        return orphans
    for session_dir in session_dirs:
        try:
            if not session_dir.is_dir():
                continue
        except OSError:
            continue
        session_id = session_dir.name
        if not _valid_session_id(session_id):
            continue
        if resolve_plan(session_id) is None:
            orphans.append(session_id)
    return orphans


def _gc_slot(session_id: str) -> bool:
    """Remove a stale session's ``active-plan`` file. Best-effort; returns success.

    Slot removal is one behaviour with two callers — the doctor's stale-slot GC
    here and the public :func:`unbind` teardown — so this delegates to
    :func:`unbind` rather than carrying a second copy of the unlink+prune body.
    """
    return unbind(session_id)


def doctor(fix: bool = False) -> dict[str, Any]:
    """Visit every session directory under the cache root and report binding health.

    Walks EVERY directory under ``~/.cache/plan-marshall/sessions/`` — not just
    the ones that yield a readable slot — builds an in-memory plan->sessions
    reverse index from the live slots, and:

    - flags any plan bound by more than one session (a conflict — two live
      sessions driving the same plan),
    - identifies slots whose bound plan is archived/deleted (stale slots), and
    - identifies orphan directories that carry no binding at all (absent, empty,
      or unreadable ``active-plan`` file).

    When ``fix`` is True, GCs each stale slot (removes its ``active-plan`` file)
    and prunes each orphan directory. The scan keeps NO shared mutable index — it
    is per-file and idempotent.

    Returns a dict::

        {
          "scanned": int,                 # live slots scanned
          "conflicts": [                  # plans bound by >1 session
              {"plan_id": str, "sessions": [session_id, ...]}, ...
          ],
          "stale": [                      # slots whose plan is not live
              {"session_id": str, "plan_id": str}, ...
          ],
          "gc_removed": int,              # stale slots removed (0 unless fix)
          "orphans": [session_id, ...],   # dirs yielding no live slot
          "orphans_removed": int,         # orphan dirs pruned (0 unless fix)
          "fix": bool,
        }

    ``scanned`` keeps its existing meaning — the count of live slots scanned —
    and does NOT include orphan directories.

    Best-effort: an unreadable slot is skipped; never raises.
    """
    reverse: dict[str, list[str]] = {}
    stale: list[dict[str, str]] = []

    for session_id, plan_id in _iter_slots():
        reverse.setdefault(plan_id, []).append(session_id)
        if not _plan_is_live(plan_id):
            stale.append({"session_id": session_id, "plan_id": plan_id})

    conflicts = [
        {"plan_id": pid, "sessions": sorted(sids)}
        for pid, sids in sorted(reverse.items())
        if len(sids) > 1
    ]

    # Computed against the pre-fix state: orphan dirs and stale slots are
    # disjoint (a stale slot resolves to a plan_id, an orphan resolves to None),
    # so the two prune loops below never double-count the same directory.
    orphans = _iter_orphan_dirs()

    gc_removed = 0
    orphans_removed = 0
    if fix:
        for slot in stale:
            if _gc_slot(slot["session_id"]):
                gc_removed += 1
        for orphan_id in orphans:
            if _remove_slot_and_prune(_active_plan_path(orphan_id)):
                orphans_removed += 1

    return {
        "scanned": sum(len(sids) for sids in reverse.values()),
        "conflicts": conflicts,
        "stale": stale,
        "gc_removed": gc_removed,
        "orphans": orphans,
        "orphans_removed": orphans_removed,
        "fix": fix,
    }
