#!/usr/bin/env python3
"""Unified merge lock — the SINGLE main-anchored merge-to-main serializer.

Notation: ``plan-marshall:manage-locks:merge_lock``

This standalone script serializes the merge-to-main critical section across
concurrently-finalizing plans with one main-anchored lock file at the MAIN
checkout's ``.plan/local/merge.lock``. It is the SINGLE merge serializer used by
BOTH consumers — ``integrate_into_main``'s inner move-back mutex and the
``branch-cleanup.md`` Pre-Merge Gate — reconciling the two formerly-duplicated
merge-lock layers (the file ``O_EXCL`` lock and the ``status.metadata``
marker-scan) into one primitive on the shared ``_locks_core`` coordination core.

It exposes three actions:

  * ``acquire`` — atomically create the lock file via ``O_EXCL``, writing the
    holder source (the acquiring ``plan_id``). If the file already exists, wait
    and retry with simple backoff until it frees; a lock whose recorded holder
    no longer corresponds to a live plan is reclaimed (re-verified atomically
    after the reclaim decision). On wait-budget elapse against a LIVE holder,
    returns a structured ``status: blocked`` payload (``blocking_plan_id`` +
    ``poll_window_seconds``) — NOT a hard error — so the Pre-Merge Gate's
    orchestrator escalation (the ``AskUserQuestion`` Wait-and-retry / Skip path)
    still fires. A genuine error (resolution failure, unremovable file) stays
    ``status: error``.
  * ``check`` — a non-blocking holder read: ``status: free`` when no lock file
    exists, ``status: held`` + ``holder_plan_id`` when one does. Never attempts
    to create or mutate the lock.
  * ``release`` — remove the lock file (only when this caller holds it).

**Reconciliation (the unified design).** This primitive KEEPS the file
``O_EXCL`` lock's proven correctness core — atomic ``O_EXCL`` create,
main-anchored resolution, cross-tree (main + worktree) holder-liveness
reclamation, idempotent foreign-safe release. It LAYERS ON the richer surface of
the former status-marker scan — the ``check`` action and the structured
``blocked`` + ``blocking_plan_id`` timeout payload that drives orchestrator
escalation. It DROPS the status-marker scan's storage mechanism (the cross-plan
``status.metadata`` scan), its non-atomic optimistic write, and its lexicographic
``plan_id`` tiebreaker — the tiebreaker existed only to patch the scan's missing
atomicity, and the ``O_EXCL`` kernel race (loser gets ``EEXIST`` and retries) is
the sole arbiter here, so the tiebreaker is dead by construction. The merge lock
stays a ``k=1`` kernel-race mutex with NO FIFO waiting queue (the build queue is
the only primitive that needs one).

**Holder liveness via the shared core (no duplicate).** The plan-liveness
predicate is :func:`_locks_core.holder_is_dead`, imported from the shared
coordination core, NOT re-implemented here — a holder is dead when its plan dir
lives in NEITHER the main checkout NOR the holder's worktree (both main-anchored,
cwd-independent). Checking both is load-bearing: an actively-executing holder's
plan dir has been MOVED into the worktree (ADR-002), so a main-only check would
wrongly declare it dead and let a concurrent acquirer steal the lock.

**Main-anchored resolution — via the single sanctioned utility (ADR-002):** every
other path resolution in the codebase is uniform cwd-relative (see
``dev-agent-behavior-rules`` / ``tools-script-executor/standards/cwd-policy.md``
and :func:`file_ops.get_base_dir`). The merge lock always resolves its lock file
against the MAIN checkout regardless of the caller's cwd, because cross-session
coordination is inherently main-scoped: phase-5+ callers run with cwd pinned to
their own worktree, yet they must all contend for one shared lock. This script
CALLS the single sanctioned main-anchored resolver
:func:`marketplace_paths.resolve_main_anchored_path`, the ONE mechanism covering
the bounded exception set (``merge.lock``, ``run-configuration.json``,
``lessons-learned``, ``build-queue.json``). See ADR-002
(``doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc``)
and ``tools-script-executor/standards/cwd-policy.md`` for the contract.

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

**Title-token surface (best-effort, OUTSIDE the atomic window).** ``acquire`` and
``release`` surface the merge-lock state in the terminal title — ⏳ (``lock-waiting``)
while a live holder blocks this caller and 🔒 (``lock-owned``) once the lock is
held — mirroring the build wrapper's build-phase pair (🕐/🔨, D6). Every
``manage-status title-token`` set/clear and every ``platform_runtime
session push-title-token`` is best-effort: it is wrapped so a failure NEVER
affects lock acquisition or release. The token is a display affordance, not a
correctness primitive. Critically, the token writes are placed OUTSIDE the
``O_EXCL`` check-then-act window — ``lock-owned`` is set only AFTER the atomic
create has already succeeded (the lock is held, so the TOCTOU window is closed),
and ``lock-waiting`` is set once before the wait loop sleeps (it never runs
between the holder-read and the re-create). This guarantees the token surface
does not widen the kernel race the lock's correctness depends on.

**[LOCK] observability (best-effort, OUTSIDE the atomic window).** Each merge-lock
lifecycle point emits a ``[LOCK]`` event through the shared
:func:`_locks_core.log_lock_event` helper into the SINGLE main-anchored global
lock-event log: ``acquired`` after a fresh ``O_EXCL`` create succeeds,
``reclaimed`` after a stale-reclaim re-create succeeds (carrying the reclaimed-from
holder), ``blocked`` on the wait-budget timeout against a LIVE holder (carrying
the blocking holder / waiter correlation), and ``released`` after the real
``os.unlink`` (the ``action: released`` branch ONLY — never the foreign/already-free
noops, which changed no ownership). ``check`` is a non-mutating read and emits
nothing. The ``lock_id`` is the holder ``plan_id``. Like the title-token surface,
every emission is best-effort, placed OUTSIDE the ``O_EXCL`` check-then-act
window, and unconditional (the ``[LOCK]`` timeline always records, independent of
the ``set_title_token`` opt-out) — a logging failure can never affect lock
acquisition or release.

**Two invocation channels, by registration status (mirrors D6).** The two
best-effort title-token operations live in executor-registered skills
(``manage-status`` and ``platform-runtime``) whose multi-module layouts make a
file-path import fragile; they are invoked through the executor
(``python3 .plan/execute-script.py {notation} ...``) as a subprocess, exactly as
``_build_queue_slot.py`` (D6) invokes them. The glyph vocabulary lives once in
``manage-terminal-title`` (the ``state → glyph`` map); the push ``--icon`` carries
the resolved glyph, while ``manage-status`` is passed the bare state name — the
lock branching never hard-codes a glyph.
"""

from __future__ import annotations

import errno
import logging
import os
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from _locks_core import holder_is_dead, log_lock_event  # type: ignore[import-not-found]
from file_ops import get_executor_path  # type: ignore[import-not-found]
from marketplace_paths import (  # type: ignore[import-not-found]
    resolve_main_anchored_path,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)

logger = logging.getLogger(__name__)

# Simple-backoff parameters: poll the lock at a fixed interval up to a bounded
# total wait. Deliberately minimal — no exponential backoff, no jitter, no
# queue. A finalize merge is short, so a long total budget covers contention
# without busy-spinning.
_BACKOFF_SECONDS = 0.25
_DEFAULT_TIMEOUT_SECONDS = 30.0
_LOCK_FILENAME = 'merge.lock'

# Title-token icons for the two merge-lock phases. The glyph vocabulary is the
# display contract owned by manage-terminal-title; these two are the lock-phase
# pair (⏳ waiting on a live holder, 🔒 holding the lock). They feed the push
# ``--icon`` only — the lock branching passes the bare STATE NAME to
# manage-status, never a glyph (mirrors _build_queue_slot.py's build-phase pair).
_ICON_LOCK_WAITING = '⏳'  # ⏳
_ICON_LOCK_OWNED = '\U0001f512'  # 🔒

# Title-token state names persisted via manage-status (the bare state string;
# manage-terminal-title owns the state → glyph rendering).
_STATE_LOCK_WAITING = 'lock-waiting'
_STATE_LOCK_OWNED = 'lock-owned'

_TITLE_TOKEN_NOTATION = 'plan-marshall:manage-status:manage-status'
_PUSH_TOKEN_NOTATION = 'plan-marshall:platform-runtime:platform_runtime'


# ---------------------------------------------------------------------------
# Main-anchored resolution (the single deliberate exception, ADR-002)
# ---------------------------------------------------------------------------


def _resolve_main_lock_path() -> Path:
    """Resolve the merge-lock path against the MAIN checkout, cwd-independent.

    Delegates to the shared main-anchored resolver
    :func:`marketplace_paths.resolve_main_anchored_path` — the single sanctioned
    mechanism (ADR-002) that resolves to the main checkout regardless of cwd
    (test override first, then git-common-dir). The lock lives at
    ``<main>/.plan/local/merge.lock``. merge_lock is ONE of the bounded-exception
    consumers of that utility, not the sole owner of the resolution.
    """
    return resolve_main_anchored_path(_LOCK_FILENAME)


# ---------------------------------------------------------------------------
# Lock-file holder read + atomic create
# ---------------------------------------------------------------------------


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
# Best-effort title-token surface (executor channel, mirrors D6)
# ---------------------------------------------------------------------------


def _run_executor(notation: str, *cli_args: str) -> dict[str, Any]:
    """Invoke ``{notation}`` through the executor and parse its TOON stdout.

    Returns the parsed TOON dict on a clean (exit 0) run. On a non-zero exit or
    unparseable output, returns ``{'status': 'error', ...}`` so the caller can
    branch on ``status`` without catching exceptions for the common failure path.
    Never raises for a subprocess failure — the token call sites are all
    best-effort and swallow any error themselves. Mirrors
    ``_build_queue_slot._run_executor`` (D6).
    """
    cmd = [sys.executable, str(get_executor_path()), notation, *cli_args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return {'status': 'error', 'error': f'executor invocation failed: {exc}'}
    if proc.returncode != 0:
        return {
            'status': 'error',
            'error': f'{notation} exited {proc.returncode}',
            'stderr': proc.stderr.strip(),
        }
    try:
        parsed = parse_toon(proc.stdout)
    except Exception as exc:  # noqa: BLE001 — any parse failure degrades to error
        return {'status': 'error', 'error': f'unparseable TOON from {notation}: {exc}'}
    return parsed if isinstance(parsed, dict) else {'status': 'error', 'error': 'non-dict TOON'}


def _set_title_token(plan_id: str, state: str) -> None:
    """Best-effort ``manage-status title-token set --state {state}``.

    Wrapped so any failure (script error, parse error, missing plan) is swallowed
    at DEBUG — the title token is a display affordance and MUST NOT influence the
    lock acquire/release outcome. The bare STATE NAME is passed; the lock
    branching never hard-codes a glyph.
    """
    try:
        _run_executor(
            _TITLE_TOKEN_NOTATION, 'title-token', 'set', '--plan-id', plan_id, '--state', state
        )
    except Exception as exc:  # noqa: BLE001 — token writes are best-effort
        logger.debug('title-token set(%s) for %s failed: %s', state, plan_id, exc)


def _clear_title_token(plan_id: str) -> None:
    """Best-effort ``manage-status title-token clear`` (every release path)."""
    try:
        _run_executor(_TITLE_TOKEN_NOTATION, 'title-token', 'clear', '--plan-id', plan_id)
    except Exception as exc:  # noqa: BLE001 — token writes are best-effort
        logger.debug('title-token clear for %s failed: %s', plan_id, exc)


def _surface_lock_cleared(plan_id: str, set_title_token: bool = True) -> None:
    """Best-effort: clear the merge-lock title token for ``plan_id``.

    When ``set_title_token`` is False the clear is suppressed entirely — the
    move-back merge lock never set a token, so there is nothing to clear and no
    title write should fire. Mirrors the gating in :func:`_surface_lock_owned` /
    :func:`_surface_lock_waiting` so all three title surfaces share one
    suppression contract while the underlying ``_clear_title_token`` seam keeps
    its single-argument signature.
    """
    if not set_title_token:
        return
    _clear_title_token(plan_id)


def _push_title_token(plan_id: str, icon: str) -> None:
    """Best-effort ``platform_runtime session push-title-token --icon {icon}``."""
    try:
        _run_executor(
            _PUSH_TOKEN_NOTATION, 'session', 'push-title-token', '--plan-id', plan_id, '--icon', icon
        )
    except Exception as exc:  # noqa: BLE001 — token push is best-effort
        logger.debug('push-title-token(%s) for %s failed: %s', icon, plan_id, exc)


def _surface_lock_owned(plan_id: str, set_title_token: bool = True) -> None:
    """Best-effort: surface the ``lock-owned`` state (🔒) for ``plan_id``.

    Called only AFTER the atomic ``O_EXCL`` create has already succeeded — the
    lock is held, so the TOCTOU window is closed and these writes cannot widen it.
    When ``set_title_token`` is False the surface is suppressed entirely (no
    glyph reaches the terminal title) — the move-back merge lock uses this so the
    brief integration lock does not flash a spurious 🔒 into the title.
    """
    if not set_title_token:
        return
    _set_title_token(plan_id, _STATE_LOCK_OWNED)
    _push_title_token(plan_id, _ICON_LOCK_OWNED)


def _surface_lock_waiting(plan_id: str, set_title_token: bool = True) -> None:
    """Best-effort: surface the ``lock-waiting`` state (⏳) for ``plan_id``.

    Called once before the wait loop sleeps against a LIVE holder — it never runs
    inside the holder-read → re-create check-then-act, so it cannot widen the
    O_EXCL race. When ``set_title_token`` is False the surface is suppressed
    entirely (no glyph reaches the terminal title).
    """
    if not set_title_token:
        return
    _set_title_token(plan_id, _STATE_LOCK_WAITING)
    _push_title_token(plan_id, _ICON_LOCK_WAITING)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def run_acquire(args: Namespace) -> dict[str, Any]:
    """Acquire the main-anchored merge lock for ``--plan-id`` (the holder).

    Atomically creates the lock file recording the holder. If the lock is held,
    retries with simple backoff until it frees or the timeout elapses; a lock
    whose holder is dead is reclaimed (atomically re-verified). Returns
    ``status: success`` with the resolved ``lock_path`` on acquisition. On
    wait-budget elapse against a LIVE holder, returns a structured
    ``status: blocked`` payload (``blocking_plan_id`` + ``poll_window_seconds``),
    distinct from a hard error, so the Pre-Merge Gate's orchestrator escalation
    still fires. A resolution failure stays ``status: error``.
    """
    plan_id: str = args.plan_id
    # Guard against the `0` falsy trap: `--timeout 0` (a non-blocking try) is a
    # valid explicit value, so fall back to the default ONLY on None, never via
    # `or` (which would treat 0 as "unset" and block for the full default).
    timeout_val = getattr(args, 'timeout', None)
    timeout: float = timeout_val if timeout_val is not None else _DEFAULT_TIMEOUT_SECONDS
    # Default True preserves the title-token surface; callers (the move-back
    # merge lock) pass set_title_token=False to suppress the spurious glyph.
    set_title_token: bool = getattr(args, 'set_title_token', True)

    try:
        lock_path = _resolve_main_lock_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    deadline = time.monotonic() + timeout
    reclaimed = False
    # Surface the `lock-waiting` token (⏳) exactly once, the first time this
    # caller actually sleeps against a live holder — never inside the
    # holder-read → re-create check-then-act, so the O_EXCL window is untouched.
    waiting_surfaced = False
    while True:
        if _try_atomic_create(lock_path, plan_id):
            # Lock held — surface `lock-owned` (🔒). Best-effort, AFTER the atomic
            # create succeeded, so the TOCTOU window is already closed.
            _surface_lock_owned(plan_id, set_title_token)
            # [LOCK] `acquired` — best-effort, after the atomic create, OUTSIDE
            # the O_EXCL window; unconditional (independent of set_title_token).
            log_lock_event('merge', 'acquired', lock_id=plan_id, lock_file=_LOCK_FILENAME)
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
        if holder_is_dead(holder):
            # Capture the reclaimed-from holder before the stale file is removed
            # so the `reclaimed` [LOCK] event can correlate it.
            reclaimed_from = holder
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
                    # Reclaimed — surface `lock-owned` (🔒), AFTER the atomic
                    # re-create succeeded (TOCTOU window already closed).
                    _surface_lock_owned(plan_id, set_title_token)
                    # [LOCK] `reclaimed` — best-effort, after the re-create,
                    # OUTSIDE the O_EXCL window; carry the reclaimed-from holder.
                    log_lock_event(
                        'merge',
                        'reclaimed',
                        lock_id=plan_id,
                        lock_file=_LOCK_FILENAME,
                        reclaimed_from=reclaimed_from or None,
                    )
                    return {
                        'status': 'success',
                        'plan_id': plan_id,
                        'action': 'acquired',
                        'lock_path': str(lock_path),
                        'holder': plan_id,
                        'reclaimed': True,
                    }

        if time.monotonic() >= deadline:
            # The wait budget elapsed against a LIVE holder. Return a structured
            # `blocked` payload (NOT a hard error) so the Pre-Merge Gate's
            # orchestrator escalation (AskUserQuestion Wait-and-retry / Skip)
            # still fires. `--timeout 0` non-blocking try lands here immediately
            # on a held lock, with no sleep.
            # [LOCK] `blocked` — best-effort, on the timeout return; carry the
            # blocking holder / waiter correlation (holder=blocking, waiter=self).
            log_lock_event(
                'merge',
                'blocked',
                lock_id=plan_id,
                lock_file=_LOCK_FILENAME,
                holder=holder or None,
                waiter=plan_id,
            )
            return {
                'status': 'blocked',
                'plan_id': plan_id,
                'blocking_plan_id': holder or None,
                'lock_path': str(lock_path),
                'poll_window_seconds': timeout,
            }
        # About to wait on a live holder — surface `lock-waiting` (⏳) once. This
        # runs OUTSIDE the check-then-act (after the deadline check, before the
        # sleep), so it never widens the O_EXCL race the lock depends on.
        if not waiting_surfaced:
            _surface_lock_waiting(plan_id, set_title_token)
            waiting_surfaced = True
        time.sleep(_BACKOFF_SECONDS)


def run_check(args: Namespace) -> dict[str, Any]:
    """Non-blocking read of the current merge-lock holder.

    Reads the lock file without attempting to create or mutate it. Returns
    ``status: free`` when no lock file exists, or ``status: held`` +
    ``holder_plan_id`` when one does (including a self-held lock). This serves
    the Pre-Merge Gate's ``check`` consumer directly from the file primitive.
    """
    plan_id: str = args.plan_id

    try:
        lock_path = _resolve_main_lock_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    if not lock_path.exists():
        return {
            'status': 'free',
            'plan_id': plan_id,
            'lock_path': str(lock_path),
        }

    holder = _read_holder(lock_path)
    return {
        'status': 'held',
        'plan_id': plan_id,
        'holder_plan_id': holder or None,
        'lock_path': str(lock_path),
    }


def run_release(args: Namespace) -> dict[str, Any]:
    """Release the main-anchored merge lock held by ``--plan-id``.

    Removes the lock file only when this caller is the recorded holder. A
    release of a lock not held by this caller (foreign holder, or already free)
    is a no-op success — release must be idempotent so a finalize that crashed
    mid-merge and retried does not error on the second release.
    """
    plan_id: str = args.plan_id
    # Default True preserves the title-token clear; callers (the move-back merge
    # lock) pass set_title_token=False — they never set a token, so there is
    # nothing to clear.
    set_title_token: bool = getattr(args, 'set_title_token', True)

    try:
        lock_path = _resolve_main_lock_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    if not lock_path.exists():
        # Already free — this caller holds no lock, so clear any stale
        # `lock-owned` token (best-effort). Mirrors the idempotent-release noop.
        _surface_lock_cleared(plan_id, set_title_token)
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
        # This caller does not hold the lock, so clear its own stale token.
        _surface_lock_cleared(plan_id, set_title_token)
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
    # Lock removed — clear the `lock-owned` token (best-effort, after removal so
    # the token never lingers past the lock it represents).
    _surface_lock_cleared(plan_id, set_title_token)
    # [LOCK] `released` — best-effort, after the real os.unlink; this is the only
    # release branch that changed ownership (the noop/foreign branches above do
    # not emit, since they removed no lock this caller held).
    log_lock_event('merge', 'released', lock_id=plan_id, lock_file=_LOCK_FILENAME)
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
    """Entry point — ``acquire`` / ``check`` / ``release`` actions."""
    parser = create_workflow_cli(
        description='Unified merge lock: the single main-anchored merge-to-main serializer',
        epilog="""
Examples:
  merge_lock.py acquire --plan-id EXAMPLE-PLAN [--timeout 30]
  merge_lock.py check --plan-id EXAMPLE-PLAN
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
                    {
                        'flags': ['--no-title-token'],
                        'dest': 'set_title_token',
                        'action': 'store_false',
                        'help': 'Suppress the terminal-title glyph surface (no ⏳/🔒 reaches the title)',
                    },
                ],
            },
            {
                'name': 'check',
                'help': 'Non-blocking read of the current merge-lock holder',
                'handler': run_check,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Querying plan_id (mandatory)',
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
                    {
                        'flags': ['--no-title-token'],
                        'dest': 'set_title_token',
                        'action': 'store_false',
                        'help': 'Suppress the terminal-title glyph clear (matches a --no-title-token acquire)',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
