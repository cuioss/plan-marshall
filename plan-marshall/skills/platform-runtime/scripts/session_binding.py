#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pure session->plan binding policy for platform-runtime.

The single importable home of the per-session session-binding cache policy —
the read side (relocated from ``claude_runtime._read_active_plan``), the write
side (relocated from the executor template's ``_write_active_plan``), and a
conflict/stale-slot scan. Kept as a pure, dependency-free module so it is
unit-testable against a tmp cache without going through the generated executor.

Two KIND-DISJOINT slots live side by side under each session directory: the
plan slot ``active-plan`` (a plan id) and the orchestrator slot
``active-orchestrator`` (an epic slug). They are mutually exclusive by
last-driven-wins — binding one kind clears the other — so a session drives
EITHER a plan OR an epic, never both. The plan read path
(``active-plan`` / :func:`resolve_plan` / :func:`bind`) is unchanged; the
orchestrator slot is a parallel addition that leaves it byte-for-byte intact.

Entry points:

- :func:`resolve_plan` — read the caller session's bound plan_id.
- :func:`resolve_orchestrator` — read the caller session's bound epic slug.
- :func:`bind` — last-driven-wins unconditional write of the caller's OWN plan
  slot, clearing the orchestrator slot for mutual exclusion. NO protect-active,
  NO stale-slot reclaim, NO plan-dir-exists check.
- :func:`bind_orchestrator` — last-driven-wins write of the caller's OWN
  orchestrator slot, clearing the plan slot for mutual exclusion.
- :func:`unbind` — remove BOTH of the caller's OWN slots (the teardown
  counterpart of :func:`bind` / :func:`bind_orchestrator`), pruning the
  now-empty session directory.
- :func:`doctor` — visit every directory under
  ``~/.cache/plan-marshall/sessions/``, build a plan->sessions reverse index in
  memory from the live plan slots, flag any plan bound by more than one live
  session, and (when ``fix``) GC slots whose plan is archived/deleted plus
  orphan directories that yield no live slot at all. A session dir carrying only
  an orchestrator slot is a live binding, NOT an orphan, so it is never GC'd.

Concurrency-correctness: the session cache is per-session (keyed by
``session_id``), so :func:`bind` / :func:`bind_orchestrator` write only the
caller's own slots — there is no cross-session check-then-act window, and the
mutual-exclusion clear touches only the caller's own sibling slot.
:func:`doctor` keeps NO shared mutable index (no ``index.json``), so the
per-file scan-then-GC is idempotent. No new shared-file TOCTOU hazard is
introduced. Every path is best-effort / no-raise.
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


def _active_orchestrator_path(session_id: str) -> Path:
    """Return the ``active-orchestrator`` cache file path for ``session_id``.

    The kind-disjoint sibling of :func:`_active_plan_path` — the epic-binding
    slot, holding an orchestrator epic slug rather than a plan id. Lives under
    the same per-session directory so a single :func:`unbind` prunes the
    directory once both slots are gone.
    """
    return _SESSION_CACHE_BASE / session_id / "active-orchestrator"


def _clear_slot(path: Path) -> None:
    """Best-effort remove a single cache slot file (no directory prune).

    The mutual-exclusion primitive: :func:`bind` clears the orchestrator slot
    and :func:`bind_orchestrator` clears the plan slot through this helper, so
    binding one kind retires the other (last-driven-wins across kinds). An
    already-absent file is not an error. Never raises — a clear failure must not
    turn a successful bind into a reported failure.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


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


def resolve_orchestrator(session_id: str) -> str | None:
    """Return the epic slug bound to ``session_id``, or ``None`` when unbound.

    The orchestrator-slot counterpart of :func:`resolve_plan`, reading
    ``~/.cache/plan-marshall/sessions/{session_id}/active-orchestrator``. A
    malformed session_id, a missing/unreadable file, or an empty value yields
    ``None``. Never raises.
    """
    if not _valid_session_id(session_id):
        return None
    try:
        raw = _active_orchestrator_path(session_id).read_text(encoding="utf-8").strip()
        return raw or None
    except OSError:
        return None


def bind(session_id: str, plan_id: str) -> bool:
    """Bind ``plan_id`` to ``session_id``'s plan slot, last-driven-wins.

    Validates the session-UUID and plan-id shapes, then UNCONDITIONALLY writes
    the caller's own plan slot — NO protect-active, NO stale-slot reclaim, NO
    plan-dir-exists check — and clears the sibling orchestrator slot for
    kind-disjoint mutual exclusion (a session drives EITHER a plan OR an epic).
    Because the cache is per-session this touches only the caller's own slots and
    has no cross-session check-then-act window.

    Returns True when the plan slot was written, False on validation failure or
    any I/O error. Best-effort: never raises.
    """
    if not _valid_session_id(session_id) or not _valid_plan_id(plan_id):
        return False
    try:
        target = _active_plan_path(session_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(plan_id, encoding="utf-8")
    except OSError:
        return False
    # Mutual exclusion: a plan binding retires any orchestrator binding on the
    # same session (last-driven-wins across kinds). Best-effort — the clear never
    # turns a successful plan write into a reported failure.
    _clear_slot(_active_orchestrator_path(session_id))
    return True


def bind_orchestrator(session_id: str, slug: str) -> bool:
    """Bind an epic ``slug`` to ``session_id``'s orchestrator slot, last-driven-wins.

    The orchestrator-slot counterpart of :func:`bind`: validates the session-UUID
    and slug shapes (the same generic :func:`_valid_segment`), UNCONDITIONALLY
    writes the caller's own ``active-orchestrator`` slot, and clears the sibling
    plan slot for kind-disjoint mutual exclusion. Because the cache is per-session
    this touches only the caller's own slots and has no cross-session
    check-then-act window.

    Returns True when the orchestrator slot was written, False on validation
    failure or any I/O error. Best-effort: never raises — a caller fires this as
    a side effect of the per-verb repaint, so it must never break that call.
    """
    if not _valid_session_id(session_id) or not _valid_segment(slug):
        return False
    try:
        target = _active_orchestrator_path(session_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(slug, encoding="utf-8")
    except OSError:
        return False
    # Mutual exclusion: an orchestrator binding retires any plan binding on the
    # same session, mirroring bind()'s symmetric clear.
    _clear_slot(_active_plan_path(session_id))
    return True


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
    """Remove BOTH of ``session_id``'s own slots — the teardown of :func:`bind`.

    Deletes both ``~/.cache/plan-marshall/sessions/{session_id}/active-plan`` and
    ``.../active-orchestrator`` and prunes the now-empty session directory. Same
    validation, same per-session scope, and the same best-effort / no-raise
    contract as :func:`bind` / :func:`bind_orchestrator`: because the cache is
    keyed by ``session_id`` this touches only the caller's own slots, so there is
    no cross-session check-then-act window. Removing both slots is what makes the
    teardown kind-agnostic — a session bound to either kind is fully released.

    The first :func:`_remove_slot_and_prune` call's ``rmdir`` is a no-op while the
    sibling slot still exists (a non-empty dir), so the directory is pruned by the
    second call once both slots are gone.

    Returns True when both slots were removed (or were already absent), False on
    validation failure or any I/O error. Never raises.
    """
    if not _valid_session_id(session_id):
        return False
    plan_removed = _remove_slot_and_prune(_active_plan_path(session_id))
    orchestrator_removed = _remove_slot_and_prune(_active_orchestrator_path(session_id))
    return plan_removed and orchestrator_removed


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


def _scan_session_dirs() -> tuple[list[tuple[str, str]], list[str]]:
    """Walk the cache root once, splitting live slots from orphan directories.

    Visits every directory under ``_SESSION_CACHE_BASE``, resolving each valid
    session-id exactly once. Returns ``(slots, orphans)``: ``slots`` is
    ``(session_id, plan_id)`` for every readable active-plan slot, ``orphans`` is
    the session-dir names whose ``active-plan`` file is absent, empty, or
    unreadable (:func:`resolve_plan` returns ``None``) — the residue
    :func:`unbind`'s prune could not remove (a non-empty dir at teardown, or a
    slot written by a crashed writer).

    A session dir carrying only an ``active-orchestrator`` slot (no readable plan
    slot but a live epic binding) is NEITHER a plan slot NOR an orphan: it is a
    live orchestrator binding, kind-disjoint from the plan reverse-index, so it is
    excluded from both lists and the GC never touches it. A directory with a
    malformed name is skipped from both. Best-effort — a scan error yields two
    empty lists.
    """
    slots: list[tuple[str, str]] = []
    orphans: list[str] = []
    try:
        session_dirs = sorted(_SESSION_CACHE_BASE.iterdir())
    except OSError:
        return slots, orphans
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
        elif resolve_orchestrator(session_id):
            # Live orchestrator binding — kind-disjoint from the plan
            # reverse-index and NOT an orphan, so leave it untouched by the GC.
            continue
        else:
            orphans.append(session_id)
    return slots, orphans


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

    # A single pass over the cache root splits live slots from orphan dirs, so
    # a stale slot (resolves to a plan_id) and an orphan (resolves to None) are
    # disjoint by construction — the two prune loops below never double-count
    # the same directory.
    slots, orphans = _scan_session_dirs()

    for session_id, plan_id in slots:
        reverse.setdefault(plan_id, []).append(session_id)
        if not _plan_is_live(plan_id):
            stale.append({"session_id": session_id, "plan_id": plan_id})

    conflicts = [
        {"plan_id": pid, "sessions": sorted(sids)}
        for pid, sids in sorted(reverse.items())
        if len(sids) > 1
    ]

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
