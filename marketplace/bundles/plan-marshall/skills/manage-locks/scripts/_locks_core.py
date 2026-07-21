#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared coordination core for the manage-locks primitives.

Notation: imported as a module (PYTHONPATH) — ``from _locks_core import
holder_is_dead, rmw_json``. NOT an executor entry point.

This module is the single TOCTOU-safe coordination surface that BOTH the unified
merge mutex (``merge_lock.py``, D3) and the build-queue limiter
(``build_queue.py``, D5) build on, so the two primitives do not each
re-implement holder-liveness or shared-file serialization. It exposes three
pieces:

  * :func:`holder_is_dead` — the plan-liveness predicate (lifted from the prior
    ``merge_lock._holder_is_dead`` / ``_main_plan_local_base``): a recorded
    holder is dead when its plan dir lives in NEITHER the main checkout NOR the
    holder's worktree. Both paths are main-anchored (cwd-independent) so a holder
    is judged correctly no matter which worktree the caller is pinned to.
  * :func:`rmw_json` — a TOCTOU-safe main-anchored read-modify-write for JSON
    state files. It serializes the read→mutate→write cycle with an ``O_EXCL``
    guard-file mutex and commits via an atomic temp-file replace, so two
    concurrent sessions cannot both observe the same pre-state and both claim a
    slot/lock. A missing or corrupt state file is treated as empty (``{}``).
  * :func:`log_lock_event` — the single best-effort ``[LOCK]`` emission point both
    lock primitives call at each lifecycle point (acquire / blocked / release /
    stale-reclaim). It appends a ``[LOCK]``-tagged line to the SINGLE
    main-anchored global lock-event log (resolved via the same
    ``resolve_main_anchored_path`` mechanism the lock files use), NEVER the
    per-worktree work-log — the locks are cross-session, main-anchored
    coordination, so their event timeline must be the one shared timeline across
    all sessions. Every emission is best-effort and OUTSIDE the lock's atomic
    window, so a logging failure can never affect lock correctness.

**Main-anchored resolution (ADR-002).** Every other resolver in the codebase is
uniform cwd-relative (:func:`file_ops.get_base_dir`). Cross-session coordination
is the deliberate exception: it resolves against the MAIN checkout via the single
sanctioned :func:`marketplace_paths.resolve_main_anchored_path` utility, so
phase-5+ callers pinned to their own worktrees all contend for one shared file.
:func:`holder_is_dead` anchors its liveness paths the same way.

**Concurrency correctness (TOCTOU / check-then-act).** :func:`rmw_json` collapses
the read-modify-write into a guarded critical section: the ``O_EXCL`` guard-file
admits exactly one mutator at a time (a racing creator gets ``EEXIST`` and spins
with simple backoff), the mutation runs against the freshly-read state, and the
commit is an atomic ``os.replace`` of a temp file written in the same directory.
The guard file is always removed in a ``finally`` so a crashed mutator does not
wedge the file forever — a stale guard is reclaimed once its age exceeds a bounded
threshold. The mitigation menu lives in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``
and is not duplicated here.
"""

from __future__ import annotations

import errno
import json
import os
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, Literal

from input_validation import is_valid_plan_id
from marketplace_paths import (
    PLAN_DIR_NAME,
    resolve_main_anchored_path,
)
from plan_logging import format_log_entry

# Guard-file spin parameters. Deliberately minimal — a coordination critical
# section (admit/release a slot, acquire/release the mutex) is short, so a fixed
# small backoff over a bounded budget serializes concurrent mutators without
# busy-spinning. A guard older than the stale threshold is reclaimed so a crashed
# mutator cannot wedge the file permanently.
_GUARD_BACKOFF_SECONDS = 0.01
_GUARD_TIMEOUT_SECONDS = 30.0
_GUARD_STALE_SECONDS = 60.0
_GUARD_SUFFIX = '.lock'


# ---------------------------------------------------------------------------
# Holder liveness (stale-reclamation predicate)
# ---------------------------------------------------------------------------


def _main_plan_local_base() -> Path:
    """Resolve the main checkout's ``.plan/local`` base, cwd-independent.

    Delegates to the single sanctioned main-anchored resolver
    :func:`marketplace_paths.resolve_main_anchored_path` (ADR-002): the
    ``set_base_dir()`` / ``PLAN_BASE_DIR`` override under test isolation, else
    ``<main-root>/.plan/local`` resolved via the git common dir. Both
    holder-liveness checks below MUST anchor here — never the caller's
    cwd-relative plan root — so a holder is judged against main + its worktree
    regardless of which worktree the acquiring caller is pinned to.
    """
    return resolve_main_anchored_path('')


def holder_is_dead(holder: str, project_root: str | Path | None = None) -> bool:
    """Return True when ``holder`` no longer corresponds to a live plan.

    Under the move-based model (ADR-002) a live plan's directory resides in
    EITHER of two places, so the liveness check MUST consult both:

      * the main checkout — ``<main>/.plan/local/plans/{holder}`` — before
        move-in (phases 1-4) or after move-back (finalize complete); and
      * the holder's worktree —
        ``<main>/.plan/local/worktrees/{holder}/.plan/local/plans/{holder}`` —
        while the plan is executing or mid-finalize (after move-in, before
        move-back), when the directory does NOT exist on main.

    Checking only the main checkout wrongly declares an actively-executing holder
    dead — its plan dir has been MOVED into the worktree — letting a concurrent
    acquirer steal the lock and break serialization.

    **Liveness base (``project_root``).** When ``project_root`` is ``None`` (the
    default, and the unchanged merge-lock behaviour) both paths anchor at the
    CALLER's main checkout via :func:`_main_plan_local_base` (cwd-independent).
    When ``project_root`` is supplied, both liveness paths resolve under
    ``Path(project_root) / .plan / local`` instead — this is the machine-global
    lock case, where a lock file shared across repos records a holder that lives
    in a DIFFERENT project's checkout: the acquirer must judge that holder's
    liveness against ITS project, not the acquirer's own, or a foreign live
    holder would be wrongly reclaimed. ``holder_has_live_worktree`` is left
    caller-anchored (only merge-lock, which stays per-repo, consumes it).

    An empty/malformed holder is treated as dead so a corrupt lock file is
    reclaimable; resolution failures propagate loudly (a real bug, not transient
    unavailability) rather than being swallowed as "dead".

    Path-traversal defense: ``holder`` is a plan-id joined directly onto the
    anchored ``.plan/local`` base to build both the main-checkout
    (``main_plan``) and worktree (``worktree_plan``) plan-dir paths. A crafted
    holder bearing a path separator, a ``..`` parent-dir segment, or an embedded
    NUL byte could escape the anchored base and resolve to an unrelated existing
    directory — whose presence would report a truly-dead holder "alive" and
    permanently block lock reclamation (a DoS). The shape check is the SAME
    canonical kebab-case validator (:func:`input_validation.is_valid_plan_id`)
    enforced at every ``--plan-id`` CLI boundary elsewhere in the marketplace —
    its allowlist regex (``^[a-z][a-z0-9-]*$``) already excludes every traversal
    character AND subsumes the prior empty/whitespace check, so any empty or
    malformed holder is classified dead (the corrupt-lock-file-reclaimable
    intent is preserved and strengthened) BEFORE the path is constructed.
    """
    holder = holder.strip()
    if not is_valid_plan_id(holder):
        return True
    if project_root is None:
        base = _main_plan_local_base()
    else:
        base = Path(project_root) / PLAN_DIR_NAME / 'local'
    main_plan = base / 'plans' / holder
    worktree_plan = base / 'worktrees' / holder / PLAN_DIR_NAME / 'local' / 'plans' / holder
    return not (main_plan.exists() or worktree_plan.exists())


def holder_has_live_worktree(holder: str) -> bool:
    """Return True only for a genuine live/mid-recovery worktree of ``holder``.

    A presence/heartbeat signal STRONGER than the plan-dir check
    :func:`holder_is_dead` consults. It does NOT trust the bare existence of the
    worktree DIRECTORY (``<main>/.plan/local/worktrees/{holder}``): an orphaned
    empty shell — a worktree dir left on disk after a never-persisted plan
    (class (a)) or an incomplete/post-migration finalize teardown (class (b)),
    carrying no git plumbing and no live plan — would masquerade as mid-recovery
    under a bare ``dir.exists()`` check and permanently block the merge-lock
    auto-reclaim. Instead it requires a CONCRETE live-worktree marker under
    ``worktrees/{holder}``, returning True for EITHER:

      * a git-worktree gitdir link — the ``.git`` marker at the worktree root
        (a ``.git`` file pointing at the registered worktree admin dir, or a
        ``.git`` directory); its presence means real git plumbing is still
        wired up, so the holder is a genuine (possibly mid-recovery) worktree; OR
      * a live plan dir moved into the worktree —
        ``worktrees/{holder}/.plan/local/plans/{holder}`` — present while the
        plan is executing or mid-finalize (after move-in, before move-back).

    and False for an orphaned empty shell carrying NEITHER marker.

    A holder judged dead-by-plan-dir-absence (its plan dir is in NEITHER the main
    checkout NOR its worktree's ``.plan``) may still be MID-RECOVERY — its
    worktree is on disk with git plumbing intact but the plan dir has been moved
    out (e.g. an interrupted finalize move-back). Auto-reclaiming such a holder
    would steal the lock from a live recovery, so the acquire path gates the
    automatic stale-reclaim on this predicate being False (see
    ``merge_lock.run_acquire``), and the FIFO prune retains a waiter whose
    worktree is genuinely live. Strengthening the predicate only NARROWS the
    "refuse reclaim" set — an orphaned shell now permits reclaim while a genuine
    mid-recovery worktree stays protected.

    Anchored at the main checkout (:func:`_main_plan_local_base`, cwd-independent)
    exactly like :func:`holder_is_dead`, so the judgement is correct regardless of
    which worktree the acquiring caller is pinned to. An empty/malformed holder has
    no worktree → False. Resolution failures propagate loudly (a real bug), never
    swallowed as "no live worktree".

    Path-traversal defense: ``holder`` is a plan-id that is joined directly onto
    the worktrees root to build a filesystem path. A crafted holder bearing a
    path separator, a ``..`` parent-dir segment, or an embedded NUL byte could
    escape the worktrees root and resolve to an unrelated existing directory —
    reporting a dead holder "alive" and permanently blocking lock reclamation
    (a DoS). The shape check is the SAME canonical kebab-case validator
    (:func:`input_validation.is_valid_plan_id`) enforced at every ``--plan-id``
    CLI boundary elsewhere in the marketplace — its allowlist regex
    (``^[a-z][a-z0-9-]*$``) already excludes every traversal character, so any
    such holder is rejected as having no live worktree BEFORE the path is
    constructed.
    """
    holder = holder.strip()
    if not is_valid_plan_id(holder):
        return False
    base = _main_plan_local_base()
    worktree_dir = base / 'worktrees' / holder
    # Genuine git-worktree gitdir link: a `.git` file (linked worktree) or a
    # `.git` directory. Its presence means the worktree's git plumbing is still
    # wired up — a mid-recovery holder that must NOT be auto-reclaimed.
    git_marker = worktree_dir / '.git'
    # Live plan dir moved into the worktree (executing / mid-finalize).
    live_plan_dir = worktree_dir / PLAN_DIR_NAME / 'local' / 'plans' / holder
    return git_marker.exists() or live_plan_dir.exists()


def holder_staleness(
    holder: str, project_root: str | Path | None = None
) -> Literal['fresh', 'stale', 'unknown']:
    """Return a main-anchored three-valued staleness verdict for ``holder``.

    The authoritative, cwd-independent answer to "is this recorded holder safe to
    force-release?" — composed ENTIRELY from the two main-anchored liveness
    predicates above (:func:`holder_is_dead` / :func:`holder_has_live_worktree`),
    so it consults ONLY main-anchored paths and NEVER a cwd-scoped plan/worktree
    enumeration. This is the guard the manual-release recovery path lacked: the
    operator/agent previously inferred death from a cwd-scoped ``manage-status
    list`` / ``worktree-list`` view that, from a pinned worktree, structurally
    cannot observe a holder living in a SIBLING worktree — the #948 incident shape,
    where a live holder read as absent and its lock was stolen. The three verdicts:

      * ``'fresh'`` — the holder is alive (its plan dir is on main OR in its own
        worktree) OR it is mid-recovery (a live worktree marker is present). A
        fresh holder MUST NOT be force-released.
      * ``'stale'`` — the holder is main-anchored-dead (plan dir in NEITHER the main
        checkout NOR its worktree) AND has no live worktree. Only a ``'stale'``
        holder is provably safe to reclaim/evict.
      * ``'unknown'`` — the main-anchored ``.plan/local`` resolution itself could not
        be established (a real resolution failure, surfaced explicitly). Per
        ADR-009 the absence of evidence is NEVER collapsed into ``'stale'`` — an
        ``'unknown'`` verdict fails closed at every authority-bearing consumer.

    ``project_root`` mirrors :func:`holder_is_dead`: ``None`` (default) anchors both
    liveness paths at the caller's main checkout; a supplied root anchors the
    plan-dir liveness under that project (the machine-global cross-repo case). The
    live-worktree probe stays caller-anchored, matching
    :func:`holder_has_live_worktree`.

    The ``'unknown'`` path is realized by catching the ``RuntimeError`` the shared
    main-anchored resolver raises on an unestablished base (the same failure
    :func:`holder_is_dead` / :func:`holder_has_live_worktree` let propagate loudly)
    and converting it to the explicit ``'unknown'`` verdict — the ONE place that
    conversion is sanctioned, precisely because the verdict's contract is to
    surface the resolution failure rather than swallow it as death.
    """
    try:
        dead = holder_is_dead(holder, project_root)
        live_worktree = holder_has_live_worktree(holder)
    except (RuntimeError, OSError):
        # Main-anchored .plan/local resolution could not be established, or a
        # filesystem probe failed (OSError: permission / unresolvable path) —
        # surface the failure explicitly as 'unknown'. NEVER swallow it as
        # 'stale' (ADR-009: evidence-absent fails closed, it is not proof of
        # death). Catching OSError as well as RuntimeError keeps the fail-closed
        # contract consistent with _status_query.py's _resolution_scope.
        return 'unknown'
    if not dead or live_worktree:
        return 'fresh'
    return 'stale'


# ---------------------------------------------------------------------------
# TOCTOU-safe main-anchored read-modify-write for JSON state files
# ---------------------------------------------------------------------------


def _read_json_or_empty(path: Path) -> dict[str, Any]:
    """Read the JSON state file, treating missing or corrupt content as empty.

    A coordination state file may be absent (first acquire) or partially written
    (a crash mid-replace, though :func:`rmw_json` commits atomically). Either
    way the safe interpretation is an empty mapping — the mutator rebuilds the
    state from scratch. Only a dict is accepted; any other top-level JSON shape
    (list, scalar) is also treated as empty so a malformed file cannot corrupt a
    consumer expecting dict semantics.
    """
    try:
        raw = path.read_text(encoding='utf-8')
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _acquire_guard(guard_path: Path) -> int:
    """Acquire the ``O_EXCL`` guard-file mutex, returning the open fd.

    Spins with a fixed small backoff until the guard is free or the budget
    elapses. A guard whose mtime is older than ``_GUARD_STALE_SECONDS`` is
    reclaimed (a crashed mutator left it behind) and the create is re-attempted;
    if a third session won the race in between, the create loses cleanly
    (``EEXIST``) and the spin continues.

    Raises:
        TimeoutError: when the guard cannot be acquired within the budget.
    """
    guard_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _GUARD_TIMEOUT_SECONDS
    while True:
        try:
            return os.open(str(guard_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
        # The guard is held — reclaim it if stale, else spin.
        try:
            age = time.time() - guard_path.stat().st_mtime
        except OSError:
            age = 0.0
        if age > _GUARD_STALE_SECONDS:
            try:
                os.unlink(str(guard_path))
            except OSError:
                pass  # Someone else already reclaimed it — fall through to retry.
            continue
        if time.monotonic() >= deadline:
            raise TimeoutError(f'could not acquire coordination guard {guard_path} within {_GUARD_TIMEOUT_SECONDS}s')
        time.sleep(_GUARD_BACKOFF_SECONDS)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Commit ``data`` to ``path`` via an atomic temp-file replace.

    Writes to a uniquely-named temp file in the SAME directory (so ``os.replace``
    is an atomic rename on the same filesystem), fsyncs, then replaces. A reader
    therefore never observes a partially-written state file — it sees either the
    old contents or the new contents, never a torn mix.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    fd = os.open(str(tmp_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
    try:
        # POSIX permits os.write to perform a partial write, so a single call
        # does not guarantee the whole buffer reaches the file for larger
        # payloads. Loop until every byte is written before fsync, otherwise the
        # committed state file would be silently truncated.
        payload = json.dumps(data, indent=2).encode('utf-8')
        while payload:
            written = os.write(fd, payload)
            payload = payload[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp_path), str(path))


def rmw_json(path: Path, mutate: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """Serialized read-modify-write of the JSON state file at ``path``.

    Admits exactly one mutator at a time via an ``O_EXCL`` guard-file mutex
    (``{path}{_GUARD_SUFFIX}``), reads the current state (missing/corrupt → empty
    ``{}``), applies ``mutate`` to obtain the next state, and commits it with an
    atomic temp-file replace. The guard is always removed in a ``finally`` so a
    crashed mutator does not wedge the file; a stale guard is reclaimed by
    :func:`_acquire_guard`. Two concurrent callers cannot both observe the same
    pre-state and both write — the second blocks on the guard until the first
    commits, then reads the first's committed state.

    Args:
        path: The JSON state file (resolve via ``resolve_main_anchored_path`` at
            the call site so it is main-anchored).
        mutate: A pure function ``state -> next_state``. It receives the
            freshly-read state dict and returns the state to commit. It MUST NOT
            perform its own file I/O — the serialization guarantee only covers
            the state passed in and the state returned.

    Returns:
        The committed next state (the dict ``mutate`` returned).

    Raises:
        TimeoutError: when the guard cannot be acquired within the budget.
    """
    guard_path = path.with_name(f'{path.name}{_GUARD_SUFFIX}')
    fd = _acquire_guard(guard_path)
    try:
        current = _read_json_or_empty(path)
        next_state = mutate(current)
        _atomic_write_json(path, next_state)
        return next_state
    finally:
        os.close(fd)
        try:
            os.unlink(str(guard_path))
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Best-effort [LOCK] event emission to the single main-anchored global log
# ---------------------------------------------------------------------------


def _resolve_lock_log_path() -> Path:
    """Resolve the single main-anchored ``[LOCK]`` event log, cwd-independent.

    Derives the global-log dir from the main-anchored ``.plan/local`` base
    (:func:`marketplace_paths.resolve_main_anchored_path` with an empty subpath)
    by stepping to its parent ``.plan/`` and appending ``logs/lock-{date}.log``.
    The result is the SINGLE main-anchored global lock-event timeline regardless
    of which worktree the caller is pinned to. This deliberately does NOT use
    ``plan_logging.get_log_path`` / ``log_work`` — those resolve cwd-relative
    (``get_base_dir()``) and would wrongly land the line in the per-worktree log.
    """
    main_local_base = resolve_main_anchored_path('')
    return main_local_base.parent / 'logs' / f'lock-{date.today()}.log'


def log_lock_event(lock: str, event: str, lock_id: str, **fields: Any) -> None:
    """Append a best-effort ``[LOCK]`` lifecycle line to the main-anchored log.

    This is the single ``[LOCK]``-emission point both lock primitives call at
    each lifecycle point (``merge_lock``: acquired / reclaimed / blocked /
    released; ``build_queue``: acquired / blocked / released / reaped-stale). The
    line is formatted via :func:`plan_logging.format_log_entry` so it carries the
    standard ``[ts] [LEVEL] [hash]`` header the retrospective
    ``_GLOBAL_LOG_LINE_RE`` / ``_TAG_RE`` already parse — the bracketed
    ``[LOCK]`` tag is auto-captured by ``analyze-logs._TAG_RE`` (raw-prefix
    convention, like ``[STATUS]`` / ``[DISPATCH]``), so no
    ``VALID_WORK_CATEGORIES`` registration is required.

    Args:
        lock: The lock family — ``merge`` or ``build``.
        event: The lifecycle event — ``acquired`` / ``blocked`` / ``released`` /
            ``reclaimed`` / ``reaped-stale``.
        lock_id: The lock identity (merge: holder ``plan_id``; build: admission
            ``{plan_id}:{uuid4}``).
        **fields: Correlation fields (e.g. ``holder`` / ``waiter`` on contention,
            ``active_count`` / ``waiting_count``, ``reclaimed_from``, ``held``,
            ``threshold``) appended verbatim as indented lines. A ``WARNING``
            level is used for the ``reaped-stale`` event; every other event is
            ``INFO``.

    The entire body is wrapped so ANY failure (resolution failure, unwritable
    dir, encoding error) is swallowed — the emission is an observability
    side-effect placed OUTSIDE the lock's atomic window and a logging failure
    MUST NOT raise into the lock action.
    """
    try:
        log_path = _resolve_lock_log_path()
        level = 'WARNING' if event == 'reaped-stale' else 'INFO'
        entry = format_log_entry(level, f'[LOCK] ({lock}:{event}) {lock_id}', **fields)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:  # noqa: BLE001 — [LOCK] emission is best-effort, never raises
        pass
