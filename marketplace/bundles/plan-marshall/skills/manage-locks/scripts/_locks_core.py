#!/usr/bin/env python3
"""Shared coordination core for the manage-locks primitives.

Notation: imported as a module (PYTHONPATH) — ``from _locks_core import
holder_is_dead, rmw_json``. NOT an executor entry point.

This module is the single TOCTOU-safe coordination surface that BOTH the unified
merge mutex (``merge_lock.py``, D3) and the build-queue limiter
(``build_queue.py``, D5) build on, so the two primitives do not each
re-implement holder-liveness or shared-file serialization. It exposes two
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
``dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``
and is not duplicated here.
"""

from __future__ import annotations

import errno
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from marketplace_paths import (  # type: ignore[import-not-found]
    PLAN_DIR_NAME,
    resolve_main_anchored_path,
)

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


def holder_is_dead(holder: str) -> bool:
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
    acquirer steal the lock and break serialization. Both paths are anchored at
    the main checkout (:func:`_main_plan_local_base`, cwd-independent), matching
    the main-anchored coordination-file resolution. An empty/malformed holder is
    treated as dead so a corrupt lock file is reclaimable; resolution failures
    propagate loudly (a real bug, not transient unavailability) rather than being
    swallowed as "dead".
    """
    holder = holder.strip()
    if not holder:
        return True
    base = _main_plan_local_base()
    main_plan = base / 'plans' / holder
    worktree_plan = base / 'worktrees' / holder / PLAN_DIR_NAME / 'local' / 'plans' / holder
    return not (main_plan.exists() or worktree_plan.exists())


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
        os.write(fd, json.dumps(data, indent=2).encode('utf-8'))
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
