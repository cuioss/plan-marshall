#!/usr/bin/env python3
"""Cooperative merge lock — the SINGLE main-anchored coordination file.

Notation: ``plan-marshall:workflow-integration-git:merge_lock``

This standalone script serializes concurrent ``integrate_into_main`` (D5)
finalizes across sessions with one main-anchored lock file at the MAIN
checkout's ``.plan/local/merge.lock``. It exposes two actions:

  * ``acquire`` — atomically create the lock file via ``O_EXCL``, writing the
    holder source (the acquiring ``plan_id``). If the file already exists, wait
    and retry with simple backoff until it frees; a lock whose recorded holder
    no longer corresponds to a live plan may be reclaimed (re-verified
    atomically after the reclaim decision).
  * ``release`` — remove the lock file (only when this caller holds it).

**Main-anchored resolution — via the single sanctioned utility (ADR-002):** every
other path resolution in the codebase is uniform cwd-relative (see
``dev-agent-behavior-rules`` / ``tools-script-executor/standards/cwd-policy.md``
and :func:`file_ops.get_base_dir`). The merge lock always resolves its lock file
against the MAIN checkout regardless of the caller's cwd, because cross-session
coordination is inherently main-scoped: phase-5+ callers run with cwd pinned to
their own worktree, yet they must all contend for one shared lock. This script
no longer owns that resolution — it CALLS the single sanctioned main-anchored
resolver :func:`marketplace_paths.resolve_main_anchored_path`, which is the ONE
mechanism covering the bounded exception set of three corpora: ``merge.lock``,
``run-configuration.json``, and ``lessons-learned``. merge_lock is one of those
three consumers; the codebase cannot regrow a pervasive git-common-dir-style
hack because new cross-session state routes through that one utility. See
ADR-002 (``doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc``)
and ``tools-script-executor/standards/cwd-policy.md`` (D6) for the contract.

**Concurrency correctness (TOCTOU / check-then-act):** ``acquire`` is a
check-then-act (does-the-lock-exist → create it) collapsed into a single atomic
``os.open(..., O_CREAT | O_EXCL | O_WRONLY)``: two sessions racing to create the
same path — exactly one wins (the other gets ``FileExistsError`` and retries).
Stale reclamation is itself a check-then-act (decide-holder-is-dead → remove →
recreate) and re-verifies atomically by removing the stale file and immediately
re-attempting the ``O_EXCL`` create; if a third session won the race in between,
the reclaiming session loses cleanly and retries. See the TOCTOU / check-then-act
mitigation menu in
``dev-general-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.

No fair queue, no elaborate data structure (per the simplify-and-delete goal):
the lock file CONTENTS are a single line recording the holder ``plan_id``.
"""

from __future__ import annotations

import errno
import os
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from marketplace_paths import (  # type: ignore[import-not-found]
    PLAN_DIR_NAME,
    resolve_main_anchored_path,
)
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)

# Simple-backoff parameters: poll the lock at a fixed interval up to a bounded
# total wait. Deliberately minimal — no exponential backoff, no jitter, no
# queue. A finalize merge is short, so a long total budget covers contention
# without busy-spinning.
_BACKOFF_SECONDS = 0.25
_DEFAULT_TIMEOUT_SECONDS = 30.0
_LOCK_FILENAME = 'merge.lock'


# ---------------------------------------------------------------------------
# Main-anchored resolution (the single deliberate exception, ADR-002)
# ---------------------------------------------------------------------------


def _resolve_main_lock_path() -> Path:
    """Resolve the merge-lock path against the MAIN checkout, cwd-independent.

    Delegates to the shared main-anchored resolver
    :func:`marketplace_paths.resolve_main_anchored_path` — the single sanctioned
    mechanism (ADR-002) that resolves to the main checkout regardless of cwd
    (test override first, then git-common-dir). The lock lives at
    ``<main>/.plan/local/merge.lock``. merge_lock is now ONE of three consumers
    of that utility (alongside ``run_config`` and ``manage-lessons``), not the
    sole owner of the resolution.
    """
    return resolve_main_anchored_path(_LOCK_FILENAME)


# ---------------------------------------------------------------------------
# Holder liveness (stale-reclamation predicate)
# ---------------------------------------------------------------------------


def _main_plan_local_base() -> Path:
    """Resolve the main checkout's ``.plan/local`` base, cwd-independent.

    Returns the same anchor :func:`_resolve_main_lock_path` uses for the lock
    file, via the shared :func:`marketplace_paths.resolve_main_anchored_path`
    utility: the ``set_base_dir()`` / ``PLAN_BASE_DIR`` override stand-in under
    test isolation, else ``<main-root>/.plan/local`` resolved via the git common
    dir. Both holder-liveness checks below MUST anchor here — never the caller's
    cwd-relative plan root — so a holder is judged against main + its worktree
    regardless of which worktree the acquiring caller is pinned to.
    """
    return resolve_main_anchored_path('')


def _holder_is_dead(holder: str) -> bool:
    """Return True when the recorded holder no longer corresponds to a live plan.

    Under the move-based model (ADR-002) a live plan's directory resides in
    EITHER of two places, so the liveness check MUST consult both:

      * the main checkout — ``<main>/.plan/local/plans/{holder}`` — before
        move-in (phases 1-4) or after move-back (finalize complete); and
      * the holder's worktree —
        ``<main>/.plan/local/worktrees/{holder}/.plan/local/plans/{holder}`` —
        while the plan is executing or mid-finalize (after move-in, before
        move-back), when the directory does NOT exist on main.

    Checking only the main checkout (the prior behaviour) wrongly declares an
    actively-executing holder dead — its plan dir has been MOVED into the
    worktree — letting a concurrent acquirer steal the lock and break finalize
    serialization. Both paths are anchored at the main checkout
    (:func:`_main_plan_local_base`, cwd-independent), matching the main-anchored
    lock resolution. An empty/malformed holder is treated as dead so a corrupt
    lock file is reclaimable; resolution failures propagate loudly (a real bug,
    not transient unavailability) rather than being swallowed as "dead".
    """
    holder = holder.strip()
    if not holder:
        return True
    base = _main_plan_local_base()
    main_plan = base / 'plans' / holder
    worktree_plan = base / 'worktrees' / holder / PLAN_DIR_NAME / 'local' / 'plans' / holder
    return not (main_plan.exists() or worktree_plan.exists())


def _read_holder(lock_path: Path) -> str:
    """Read the recorded holder from the lock file (best effort, '' on error)."""
    try:
        return lock_path.read_text(encoding='utf-8').strip()
    except OSError:
        return ''


def _try_atomic_create(lock_path: Path, holder: str) -> bool:
    """Attempt the atomic ``O_EXCL`` create. Return True on success.

    Collapses the check-then-act into one syscall: ``O_CREAT | O_EXCL`` fails
    with ``EEXIST`` when the file already exists, so exactly one racing creator
    wins. Returns False on ``EEXIST`` (someone else holds it); re-raises any
    other OSError.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            return False
        raise
    try:
        os.write(fd, (holder + '\n').encode('utf-8'))
    finally:
        os.close(fd)
    return True


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def run_acquire(args: Namespace) -> dict[str, Any]:
    """Acquire the main-anchored merge lock for ``--plan-id`` (the holder).

    Atomically creates the lock file recording the holder. If the lock is held,
    retries with simple backoff until it frees or the timeout elapses; a lock
    whose holder is dead is reclaimed (atomically re-verified). Returns
    ``status: success`` with the resolved ``lock_path`` on acquisition, or
    ``status: error`` (TIMEOUT) when the wait budget is exhausted.
    """
    plan_id: str = args.plan_id
    # Guard against the `0` falsy trap: `--timeout 0` (a non-blocking try) is a
    # valid explicit value, so fall back to the default ONLY on None, never via
    # `or` (which would treat 0 as "unset" and block for the full default).
    timeout_val = getattr(args, 'timeout', None)
    timeout: float = timeout_val if timeout_val is not None else _DEFAULT_TIMEOUT_SECONDS

    try:
        lock_path = _resolve_main_lock_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    deadline = time.monotonic() + timeout
    reclaimed = False
    while True:
        if _try_atomic_create(lock_path, plan_id):
            return {
                'status': 'success',
                'plan_id': plan_id,
                'action': 'acquired',
                'lock_path': str(lock_path),
                'holder': plan_id,
                'reclaimed': reclaimed,
            }

        # The lock is held — inspect the holder for stale reclamation.
        holder = _read_holder(lock_path)
        if _holder_is_dead(holder):
            # Reclaim: remove the stale file and immediately re-attempt the
            # O_EXCL create. If a third session won the race in between, our
            # create loses cleanly (EEXIST) and we fall through to retry.
            try:
                os.unlink(str(lock_path))
            except OSError:
                # Someone else already removed/replaced it — fall through to retry.
                pass
            else:
                reclaimed = True
                if _try_atomic_create(lock_path, plan_id):
                    return {
                        'status': 'success',
                        'plan_id': plan_id,
                        'action': 'acquired',
                        'lock_path': str(lock_path),
                        'holder': plan_id,
                        'reclaimed': True,
                    }

        if time.monotonic() >= deadline:
            return make_error(
                f'merge lock held by {holder or "(unknown)"}; timed out after {timeout}s',
                code=ErrorCode.TIMEOUT,
                plan_id=plan_id,
                lock_path=str(lock_path),
                holder=holder,
            )
        time.sleep(_BACKOFF_SECONDS)


def run_release(args: Namespace) -> dict[str, Any]:
    """Release the main-anchored merge lock held by ``--plan-id``.

    Removes the lock file only when this caller is the recorded holder. A
    release of a lock not held by this caller (foreign holder, or already free)
    is a no-op success — release must be idempotent so a finalize that crashed
    mid-merge and retried does not error on the second release.
    """
    plan_id: str = args.plan_id

    try:
        lock_path = _resolve_main_lock_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    if not lock_path.exists():
        return {
            'status': 'success',
            'plan_id': plan_id,
            'action': 'noop',
            'lock_path': str(lock_path),
            'message': 'lock not held (already free)',
        }

    holder = _read_holder(lock_path)
    if holder != plan_id:
        # Do not remove a foreign holder's lock — release is scoped to the
        # caller. Report a no-op so a crashed-and-retried release is benign.
        return {
            'status': 'success',
            'plan_id': plan_id,
            'action': 'noop',
            'lock_path': str(lock_path),
            'holder': holder,
            'message': f'lock held by {holder}, not this caller; left intact',
        }

    try:
        os.unlink(str(lock_path))
    except OSError as exc:
        return make_error(
            f'failed to remove lock file {lock_path}: {exc}',
            code=ErrorCode.INVALID_INPUT,
            plan_id=plan_id,
            lock_path=str(lock_path),
        )
    return {
        'status': 'success',
        'plan_id': plan_id,
        'action': 'released',
        'lock_path': str(lock_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point — ``acquire`` / ``release`` actions."""
    parser = create_workflow_cli(
        description='Cooperative merge lock: the single main-anchored coordination file',
        epilog="""
Examples:
  merge_lock.py acquire --plan-id EXAMPLE-PLAN [--timeout 30]
  merge_lock.py release --plan-id EXAMPLE-PLAN
""",
        subcommands=[
            {
                'name': 'acquire',
                'help': 'Atomically acquire the main-anchored merge lock (simple-backoff retry)',
                'handler': run_acquire,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Holder source — the plan_id acquiring the lock (mandatory)',
                    },
                    {
                        'flags': ['--timeout'],
                        'dest': 'timeout',
                        'type': float,
                        'help': f'Max seconds to wait for the lock (default: {_DEFAULT_TIMEOUT_SECONDS})',
                    },
                ],
            },
            {
                'name': 'release',
                'help': 'Release the main-anchored merge lock held by --plan-id',
                'handler': run_release,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Holder source — the plan_id releasing the lock (mandatory)',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
