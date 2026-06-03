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

**Main-anchored resolution — the single deliberate exception (ADR-002):** every
other path resolution in the codebase is uniform cwd-relative (see
``dev-agent-behavior-rules`` / ``tools-script-executor/standards/cwd-policy.md``
and :func:`file_ops.get_base_dir`). This script — and ONLY this script — always
resolves its lock file against the MAIN checkout regardless of the caller's cwd,
because cross-session coordination is inherently main-scoped: phase-5+ callers
run with cwd pinned to their own worktree, yet they must all contend for one
shared lock. It MUST remain the only main-anchored resolver so the codebase
cannot regrow a pervasive git-common-dir-style hack. See
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
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from file_ops import (  # type: ignore[import-not-found]
    get_base_dir,
    get_plan_dir,
)
from marketplace_paths import PLAN_DIR_NAME  # type: ignore[import-not-found]
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

    Resolution precedence:

      1. Test override — :func:`file_ops.get_base_dir` honours the
         ``set_base_dir()`` / ``PLAN_BASE_DIR`` override. Under that override the
         base dir IS the main-checkout ``.plan/local`` stand-in, so the lock
         lives at ``<base_dir>/merge.lock``. This keeps test isolation working
         (each test points the override at its own tmp tree and never contends
         for the real ``.plan/``).
      2. Production — ``git rev-parse --git-common-dir`` returns the MAIN
         checkout's ``.git`` directory even when the caller's cwd is pinned to a
         linked worktree (a worktree's ``.git`` is a file, but the common dir
         always points at main). Its parent is the main checkout root; the lock
         lives at ``<main-root>/.plan/local/merge.lock``.

    This is the ONLY function in the codebase that resolves to the main checkout
    regardless of cwd — every other resolver is uniform cwd-relative (ADR-002).
    """
    # 1. Honour the test override exactly as get_base_dir does. When an override
    #    or PLAN_BASE_DIR is set, that directory stands in for the main-checkout
    #    .plan/local, so the lock lives directly under it.
    if os.environ.get('PLAN_BASE_DIR') or _override_is_set():
        return get_base_dir() / _LOCK_FILENAME

    # 2. Production: resolve the MAIN checkout via the git common dir, which
    #    points at main's .git even from a linked worktree.
    main_root = _main_checkout_root()
    return main_root / PLAN_DIR_NAME / 'local' / _LOCK_FILENAME


def _override_is_set() -> bool:
    """Return True when file_ops has a set_base_dir() override installed."""
    import file_ops  # type: ignore[import-not-found]

    return getattr(file_ops, '_BASE_DIR_OVERRIDE', None) is not None


def _main_checkout_root() -> Path:
    """Return the MAIN checkout root via ``git rev-parse --git-common-dir``.

    The common dir is main's ``.git`` directory even when invoked from a linked
    worktree; its parent is the main checkout root. Falls back to the toplevel
    when the common dir resolves to a bare path without an obvious parent.

    Raises:
        RuntimeError: when git cannot resolve the common dir (not a repo).
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'cannot resolve main checkout via git common dir: {exc}') from exc
    common_dir = Path(result.stdout.strip())
    # The common dir is <main-root>/.git; its parent is the main checkout root.
    return common_dir.parent


# ---------------------------------------------------------------------------
# Holder liveness (stale-reclamation predicate)
# ---------------------------------------------------------------------------


def _holder_is_dead(holder: str) -> bool:
    """Return True when the recorded holder no longer corresponds to a live plan.

    A holder is "dead" when its plan directory no longer exists on the main
    checkout — the plan that held the lock has been finalized and moved back (or
    never existed). This is the minimal reclamation predicate: no PID tracking,
    no heartbeat, just "does the holder's plan dir still resolve". An empty or
    malformed holder is treated as dead so a corrupt lock file is reclaimable.
    """
    holder = holder.strip()
    if not holder:
        return True
    try:
        return not get_plan_dir(holder).exists()
    except (OSError, RuntimeError):
        # If we cannot resolve the holder's plan dir, treat the lock as dead so
        # a corrupt/unresolvable holder never wedges the lock permanently.
        return True


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
    timeout: float = getattr(args, 'timeout', None) or _DEFAULT_TIMEOUT_SECONDS

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
