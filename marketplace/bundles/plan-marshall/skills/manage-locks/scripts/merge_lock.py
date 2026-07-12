#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unified merge lock — the SINGLE main-anchored merge-to-main serializer with a
FIFO admission queue.

Notation: ``plan-marshall:manage-locks:merge_lock``

This standalone script serializes the merge-to-main critical section across
concurrently-finalizing plans with one main-anchored lock file at the MAIN
checkout's ``.plan/local/merge.lock``, fronted by a main-anchored FIFO admission
queue at ``.plan/local/merge-queue.json``. It is the SINGLE merge serializer used
by BOTH consumers — ``integrate_into_main``'s inner move-back mutex and the
``branch-cleanup.md`` Pre-Merge Gate — reconciling the two formerly-duplicated
merge-lock layers (the file ``O_EXCL`` lock and the ``status.metadata``
marker-scan) into one primitive on the shared ``_locks_core`` coordination core.

**The FIFO admission layer (fairness).** The bare ``O_EXCL`` mutex grants the
lock to whichever racing acquirer wins the kernel ``EEXIST`` race — under N
concurrently-finalizing plans this has no ordering, so the plan that happens to
re-poll first after a release wins, never the longest-waiting one. This script
layers a FIFO admission queue (``merge-queue.json``, managed through the SAME
shared :func:`_locks_core.rmw_json` TOCTOU-safe read-modify-write the build queue
uses) onto the lock so the longest-waiting plan merges next. ``acquire`` first
FIFO-enqueues ``--plan-id`` into ``merge-queue.json`` (idempotently — a plan
already in the queue KEEPS its FIFO position (its existing list slot), never
re-appended to the back, mirroring ``build_queue.run_acquire``'s idempotent
fast-path). A plan is admission-eligible ONLY when it is the FIFO front (the first
entry in serialized arrival order — list position, not admit-``ts``, see
``_fifo_front``); when eligible it attempts the existing ``O_EXCL`` create and on success returns
``admission: admitted``. A non-front plan, or a front plan that loses the
``O_EXCL`` create, returns ``admission: blocked`` — a structured re-poll signal,
NOT an error and NOT an internal wait. Re-polling is the CONSUMER's job (the
Pre-Merge Gate's poll/backoff loop, bounded by ``merge_queue_wait_budget_seconds``);
this script no longer sleeps internally for the queue case. The ``O_EXCL`` mutex
stays the final ``k=1`` grant — the FIFO layer decides WHO may attempt it, the
kernel race decides the single winner.

It exposes three actions:

  * ``acquire`` — FIFO-enqueue ``--plan-id`` into ``merge-queue.json`` (idempotent,
    FIFO-position-preserving), then — only when this plan is the FIFO front —
    atomically create the lock file via ``O_EXCL``, writing the holder source
    (the acquiring ``plan_id``). A lock whose recorded holder no longer
    corresponds to a live plan is reclaimed (re-verified atomically after the
    reclaim decision). On a successful create or reclaim, returns
    ``status: success`` with ``admission: admitted``. **Reentrant per ``plan_id``:**
    when the existing lock is already held by the SAME ``plan_id``, acquire returns
    ``status: success`` with ``action: already_held`` and ``admission: admitted``
    immediately — no second ``O_EXCL`` create, no staleness check — so the
    finalize auto-merge path (``branch-cleanup`` then ``integrate_into_main``,
    re-acquiring under the same ``plan_id``) does not self-deadlock. The reentrant
    grant is not a second independent acquisition: release stays idempotent and
    holder-scoped, so the single ``os.unlink`` fires once when the holder releases.
    A non-front plan, or a front plan that loses the ``O_EXCL`` race against a
    FOREIGN live holder, returns ``status: blocked`` with ``admission: blocked``
    (carrying ``blocking_plan_id`` + ``waiting_count``) — NOT a hard error — so the
    consumer's poll/backoff loop re-polls (preserving FIFO position) until admitted
    or its budget is exhausted, then the Pre-Merge Gate's ``AskUserQuestion``
    last-resort escape hatch fires. A genuine error (resolution failure,
    unremovable file) stays ``status: error``.
  * ``check`` — a non-blocking holder read: ``status: free`` when no lock file
    exists, ``status: held`` + ``holder_plan_id`` when one does. Never attempts
    to create or mutate the lock, and never touches the FIFO queue.
  * ``release`` — remove the lock file (only when this caller holds it), then
    dequeue ``--plan-id`` from ``merge-queue.json`` so the next FIFO entry becomes
    the front and is admitted on its next re-poll.

**Reconciliation (the unified design).** This primitive KEEPS the file
``O_EXCL`` lock's proven correctness core — atomic ``O_EXCL`` create,
main-anchored resolution, cross-tree (main + worktree) holder-liveness
reclamation, idempotent foreign-safe release. It LAYERS ON the richer surface of
the former status-marker scan — the ``check`` action and the structured
``blocked`` + ``blocking_plan_id`` timeout payload that drives consumer re-poll —
AND the FIFO admission queue that gives merge contention a fair ordering. It DROPS
the status-marker scan's storage mechanism (the cross-plan ``status.metadata``
scan), its non-atomic optimistic write, and its lexicographic ``plan_id``
tiebreaker — the tiebreaker existed only to patch the scan's missing atomicity,
and the ``O_EXCL`` kernel race (loser gets ``EEXIST`` and re-polls) is the sole
arbiter of the single winner, so the tiebreaker is dead by construction. The merge
lock stays a ``k=1`` kernel-race mutex; the FIFO queue is the fairness layer in
FRONT of that mutex, deciding admission order, not a second concurrency bound.

**Holder liveness via the shared core (no duplicate).** The plan-liveness
predicate is :func:`_locks_core.holder_is_dead`, imported from the shared
coordination core, NOT re-implemented here — a holder is dead when its plan dir
lives in NEITHER the main checkout NOR the holder's worktree (both main-anchored,
cwd-independent). Checking both is load-bearing: an actively-executing holder's
plan dir has been MOVED into the worktree (ADR-002), so a main-only check would
wrongly declare it dead and let a concurrent acquirer steal the lock. The same
predicate prunes dead FIFO-queue entries so a crashed waiter's entry never blocks
the front indefinitely.

**Main-anchored resolution — via the single sanctioned utility (ADR-002):** every
other path resolution in the codebase is uniform cwd-relative (see
``persona-plan-marshall-agent`` / ``tools-script-executor/standards/cwd-policy.md``
and :func:`file_ops.get_base_dir`). The merge lock always resolves both its lock
file AND its FIFO queue file against the MAIN checkout regardless of the caller's
cwd, because cross-session coordination is inherently main-scoped: phase-5+
callers run with cwd pinned to their own worktree, yet they must all contend for
one shared lock and one shared queue. This script CALLS the single sanctioned
main-anchored resolver :func:`marketplace_paths.resolve_main_anchored_path`, the
ONE mechanism covering the bounded exception set (``merge.lock``,
``merge-queue.json``, ``run-configuration.json``, ``lessons-learned``,
``build-queue.json``). See ADR-002
(``doc/adr/002-Plan-scoped_operations_move_into_a_cwd-pinned_hermetic_worktree.adoc``)
and ``tools-script-executor/standards/cwd-policy.md`` for the contract.

**Concurrency correctness (TOCTOU / check-then-act):** ``acquire`` is a two-layer
check-then-act — the FIFO enqueue/promote (read-modify-write of
``merge-queue.json``) followed by the ``O_EXCL`` create on ``merge.lock``. The
FIFO mutation runs entirely inside :func:`_locks_core.rmw_json` (serialized
``O_EXCL`` guard + atomic temp-file replace), so two sessions cannot both observe
the same queue pre-state and both decide they are the front. The lock grant stays
a check-then-act (does-the-lock-exist → create it) collapsed into a single atomic
``os.open(..., O_CREAT | O_EXCL | O_WRONLY)``: two sessions racing to create the
same path — exactly one wins (the other gets ``FileExistsError`` and re-polls).
Neither layer widens the other's window. Stale reclamation is itself a
check-then-act (decide-holder-is-dead → evict → recreate) whose eviction step must
arbitrate on the SPECIFIC observed stale file, not the bare path:
:func:`_reclaim_stale_lock` claims that specific file by ``os.rename``-ing it aside
to a per-reclaimer unique sidecar (``{lock}.reclaim.{pid}.{uuid}``) — a target only
this reclaimer names — then re-confirms the renamed-away content is exactly the
dead holder it decided to evict AND that the holder is still dead. A concurrent
reclaimer that already swapped a LIVE holder into the path before this rename is
caught by that re-confirmation: the sidecar is ``os.replace``-d back to restore the
live holder and the reclaimer loses cleanly. When the path is already gone (a
racing reclaimer claimed it a beat earlier) the rename fails with
``FileNotFoundError`` and the reclaimer falls through to lose. Only on a confirmed
dead-holder match does the reclaimer unlink the sidecar and ``O_EXCL``-recreate the
lock for itself. This eviction-of-the-observed-file arbitration closes the former
blind-``os.unlink(path)`` window, where a reclaimer could remove a live holder a
concurrent reclaimer had just installed and both acquirers would then recreate and
win — a silent double-grant of the ``k=1`` mutex. See the TOCTOU / check-then-act
mitigation menu (option (c), atomic primitive) in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.

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
and ``lock-waiting`` is set on the ``blocked`` admission return (it never runs
inside the FIFO mutation or between the holder-read and the re-create). This
guarantees the token surface does not widen the kernel race the lock's correctness
depends on. The release path clears the ``lock-owned`` state AND fires a plain,
icon-less repaint through the SAME canonical ``session push-title-token`` seam
(``_push_title_token`` with no icon) so the glyph disappears LIVE instead of
lingering until the next render event; that repaint runs only after the real
``os.unlink``, so it too stays outside the ``O_EXCL`` window. All three surfaces
(``_surface_lock_owned`` / ``_surface_lock_waiting`` / ``_surface_lock_cleared``)
are consumers of that one repaint seam.

**[LOCK] observability (best-effort, OUTSIDE the atomic window).** Each merge-lock
lifecycle point emits a ``[LOCK]`` event through the shared
:func:`_locks_core.log_lock_event` helper into the SINGLE main-anchored global
lock-event log: ``acquired`` after a fresh ``O_EXCL`` create succeeds (carrying the
FIFO ``waiting_count``), ``reclaimed`` after a stale-reclaim re-create succeeds
(carrying the reclaimed-from holder), ``blocked`` on a non-front or lock-contended
admission (carrying the blocking holder / waiter correlation and ``waiting_count``),
and ``released`` after the real ``os.unlink`` (the ``action: released`` branch ONLY
— never the foreign/already-free noops, which changed no ownership). ``check`` is a
non-mutating read and emits nothing. The ``lock_id`` is the holder ``plan_id``.
Like the title-token surface, every emission is best-effort, placed OUTSIDE the
``O_EXCL`` check-then-act window, and unconditional (the ``[LOCK]`` timeline always
records, independent of the ``set_title_token`` opt-out) — a logging failure can
never affect lock acquisition or release.

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
import uuid
from argparse import Namespace
from pathlib import Path
from typing import Any

from _locks_core import holder_has_live_worktree, holder_is_dead, log_lock_event, rmw_json
from file_ops import get_executor_path
from manage_terminal_title import TITLE_TOKEN_GLYPHS
from marketplace_paths import (
    resolve_main_anchored_path,
)
from toon_parser import parse_toon
from triage_helpers import (
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)

logger = logging.getLogger(__name__)

# Backoff parameter retained for the reentrant/timeout legacy semantics of the
# acquire CLI surface. The queue case no longer waits internally — re-polling is
# the consumer's job — but `--timeout` is kept (default 0 = non-blocking try) so
# existing call sites and the `--timeout 0` non-blocking contract are unbroken.
_DEFAULT_TIMEOUT_SECONDS = 0.0
_LOCK_FILENAME = 'merge.lock'
_QUEUE_FILENAME = 'merge-queue.json'

# Title-token state names persisted via manage-status (the bare state string;
# manage-terminal-title owns the state → glyph rendering).
_STATE_LOCK_WAITING = 'lock-waiting'
_STATE_LOCK_OWNED = 'lock-owned'

# Title-token icons for the two merge-lock phases (⏳ waiting on a live holder,
# 🔒 holding the lock), fed to the push ``--icon`` only — the lock branching
# passes the bare STATE NAME to manage-status, never a glyph. The glyph
# vocabulary is the display contract OWNED by manage-terminal-title; these two
# are derived from its single ``TITLE_TOKEN_GLYPHS`` source of truth rather than
# re-literalled here (mirrors _build_queue_slot.py's build-phase pair).
_ICON_LOCK_WAITING = TITLE_TOKEN_GLYPHS[_STATE_LOCK_WAITING]
_ICON_LOCK_OWNED = TITLE_TOKEN_GLYPHS[_STATE_LOCK_OWNED]

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


def _resolve_merge_queue_path() -> Path:
    """Resolve the FIFO merge-queue path against the MAIN checkout, cwd-independent.

    Delegates to the same single sanctioned main-anchored resolver
    :func:`marketplace_paths.resolve_main_anchored_path` (ADR-002). The queue lives
    at ``<main>/.plan/local/merge-queue.json`` — the FIFO active+waiting fairness
    state in FRONT of the ``O_EXCL`` ``merge.lock``. ``merge-queue.json`` is one of
    the bounded-exception files routed through that utility, mirroring how
    ``build_queue.py`` resolves ``build-queue.json``.
    """
    return resolve_main_anchored_path(_QUEUE_FILENAME)


# ---------------------------------------------------------------------------
# FIFO merge-queue state helpers (rmw_json-managed, mirrors build_queue.py)
# ---------------------------------------------------------------------------


def _queue_waiting(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ``state['waiting']`` as a list of FIFO entry dicts, junk → empty.

    A corrupt or absent ``waiting`` value (missing, non-list, or holding entries
    without a string ``plan_id``) degrades to an empty list so a malformed
    ``merge-queue.json`` is rebuilt from scratch rather than crashing the mutator.
    Each retained entry must carry a string ``plan_id`` (the FIFO identity); the
    list order is the arrival order and the sole FIFO-front key (see
    :func:`_fifo_front`).  The admit-``ts`` is retained as an informational
    enqueue timestamp only; a non-numeric ``ts`` value (e.g., a string from a
    manually edited state file) is coerced to ``0.0`` so the field stays a float
    rather than tripping later numeric consumers.
    """
    raw = state.get('waiting')
    if not isinstance(raw, list):
        return []
    waiting: list[dict[str, Any]] = []
    for e in raw:
        if not isinstance(e, dict):
            continue
        plan_id = e.get('plan_id')
        if not isinstance(plan_id, str):
            continue
        ts = e.get('ts', 0.0)
        if not isinstance(ts, (int, float)):
            ts = 0.0
        waiting.append({'plan_id': plan_id, 'ts': float(ts)})
    return waiting


def _prune_dead_waiting(waiting: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop FIFO entries whose holder plan is dead AND has no live worktree.

    A waiter is dead-by-plan-dir when its plan dir lives in NEITHER the main
    checkout NOR its worktree (the shared :func:`_locks_core.holder_is_dead`
    predicate). Pruning such waiters before selecting the FIFO front frees the
    queue from a crashed session that would otherwise wedge the front indefinitely
    — its entry is never released (the crash skipped the release), so without this
    prune it would block every live waiter behind it forever.

    The live-worktree guard (:func:`_locks_core.holder_has_live_worktree`) narrows
    the prune: a waiter judged dead-by-plan-dir but whose worktree directory is
    still on disk may be MID-RECOVERY (an interrupted finalize move-back moved the
    plan dir out but left the worktree), so it is RETAINED rather than silently
    pruned. Only a waiter that is both plan-dir-dead AND worktree-absent is
    genuinely gone and dropped.
    """
    return [
        e
        for e in waiting
        if not holder_is_dead(e.get('plan_id', '')) or holder_has_live_worktree(e.get('plan_id', ''))
    ]


def _fifo_front(waiting: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the FIFO-front entry (first by serialized arrival order), or None when empty.

    The ``waiting`` list order IS the arrival order: every enqueue/dequeue mutation
    runs inside the serialized :func:`_locks_core.rmw_json` critical section, so the
    list records plans in the exact order their enqueues were serialized. The front
    (the first list entry) is therefore the longest-waiting plan and the only
    admission-eligible one. List position — NOT the informational admit-``ts`` field
    — is the single ordering key: ``ts`` is sampled per call from the wall clock and
    under concurrent enqueue can disagree with serialization order (a ``ts`` sampled
    before the rmw section does not reflect when the append actually landed), so
    selecting the front by ``min(ts)`` could pick a different entry than the file's
    first and split the queue's notion of "front" — the no-double-grant drain race.
    Using list position keeps one source of truth for arrival order.
    """
    if not waiting:
        return None
    return waiting[0]


def _enqueue_fifo(plan_id: str, ts: float) -> dict[str, Any]:
    """Idempotently FIFO-enqueue ``plan_id`` and report whether it is the front.

    Runs a single serialized read-modify-write of ``merge-queue.json`` via
    :func:`_locks_core.rmw_json`: prune dead waiters, then — if ``plan_id`` already
    has a ``waiting`` entry — REUSE it (KEEPING its FIFO position; never re-append
    to the back, mirroring ``build_queue.run_acquire``'s idempotent re-poll
    fast-path). Only a plan with no existing entry is appended to ``waiting`` with
    a fresh admit-``ts``. Returns a small outcome dict carrying ``is_front`` (True
    when this plan is the FIFO front and therefore admission-eligible) and
    ``waiting_count`` (the post-mutation queue depth) for the caller's ``[LOCK]``
    correlation. The FIFO mutation is entirely inside ``rmw_json`` so two sessions
    cannot both observe the same queue pre-state and both decide they are front.
    """
    queue_path = _resolve_merge_queue_path()
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        waiting = _prune_dead_waiting(_queue_waiting(state))
        # Idempotent re-poll: an already-queued plan KEEPS its FIFO position.
        if not any(e['plan_id'] == plan_id for e in waiting):
            waiting.append({'plan_id': plan_id, 'ts': ts})
        front = _fifo_front(waiting)
        outcome['is_front'] = front is not None and front['plan_id'] == plan_id
        outcome['waiting_count'] = len(waiting)
        return {'waiting': waiting}

    rmw_json(queue_path, _mutate)
    return outcome


def _dequeue_fifo(plan_id: str) -> int:
    """Remove ``plan_id`` from the FIFO queue, returning the post-removal depth.

    Runs a single serialized read-modify-write of ``merge-queue.json`` via
    :func:`_locks_core.rmw_json`: prune dead waiters and drop this plan's entry so
    the next FIFO entry (the next-oldest admit-``ts``) becomes the front and is
    admitted on its next re-poll. Idempotent — removing a plan_id not in the queue
    is a benign no-op (a crashed-and-retried release does not error). Returns the
    post-removal ``waiting`` depth for ``[LOCK]`` correlation.
    """
    queue_path = _resolve_merge_queue_path()
    waiting_count = 0

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        nonlocal waiting_count
        waiting = [e for e in _prune_dead_waiting(_queue_waiting(state)) if e['plan_id'] != plan_id]
        waiting_count = len(waiting)
        return {'waiting': waiting}

    rmw_json(queue_path, _mutate)
    return waiting_count


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


def _reclaim_stale_lock(lock_path: Path, observed_holder: str, new_holder: str) -> bool:
    """Atomically reclaim a stale lock by evicting the SPECIFIC observed file.

    The reclaim eviction must arbitrate on the exact stale file the caller
    decided to evict, never the bare path — otherwise a concurrent reclaimer that
    installs a LIVE holder at the path between the liveness decision and the
    eviction would be silently evicted, and both acquirers would recreate and win
    (a double-grant of the ``k=1`` mutex). This helper closes that window:

    1. ``os.rename`` the lock file aside to a per-reclaimer unique sidecar
       (``{lock_path}.reclaim.{pid}.{uuid}``) — a target only this reclaimer
       names. The rename atomically claims the specific file currently at the
       path. ``FileNotFoundError`` / ``OSError`` (a racing reclaimer swapped or
       removed it first) → return False to lose.
    2. Read the renamed-away content and confirm it is exactly ``observed_holder``
       AND that the holder is still dead. If the file at the path had changed to a
       live (or different) holder before our rename, ``os.replace`` the sidecar
       back to restore it intact and return False (lose cleanly).
    3. On a confirmed dead-holder match, unlink the sidecar and ``O_EXCL``-recreate
       the lock for ``new_holder``. The recreate uses ``O_EXCL`` so that even after
       the path was freed, a third reclaimer racing the now-empty path is still
       arbitrated by the kernel — exactly one ``O_EXCL`` create wins. Return its
       result (False on ``EEXIST`` → lose).

    Returns True only when this reclaimer atomically evicted the observed dead
    holder AND recreated the lock for ``new_holder``; False on every loss path.
    Restoring the sidecar (step 2) is best-effort-correct: a failure to restore
    leaves the sidecar on disk but never grants this reclaimer the lock.
    """
    sidecar = lock_path.with_name(f'{lock_path.name}.reclaim.{os.getpid()}.{uuid.uuid4().hex}')
    try:
        os.rename(str(lock_path), str(sidecar))
    except FileNotFoundError:
        # The path was already swapped or removed by a racing reclaimer — this
        # reclaimer did not claim the observed file. Lose cleanly.
        return False

    # The observed file is now ours (at the sidecar). Confirm it is exactly the
    # dead holder we decided to evict, and that the holder is still dead.
    renamed_holder = _read_holder(sidecar)
    if renamed_holder != observed_holder or not holder_is_dead(renamed_holder):
        # The file at the path had changed to a different / now-live holder before
        # our rename claimed it. Restore it intact so the live holder keeps its
        # lock, then lose cleanly.
        try:
            os.replace(str(sidecar), str(lock_path))
        except OSError:
            # Best-effort restore: a concurrent reclaimer already recreated the
            # path, so the sidecar is now stale. Drop it and lose either way.
            try:
                os.unlink(str(sidecar))
            except OSError:
                pass
        return False

    # Confirmed dead-holder match — drop the sidecar and recreate the lock for us.
    try:
        os.unlink(str(sidecar))
    except OSError:
        pass
    return _try_atomic_create(lock_path, new_holder)


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
    """Best-effort: clear the merge-lock title token for ``plan_id`` AND repaint.

    Clears the persisted ``title_token`` state (manage-status) and then fires a
    plain, icon-less repaint through the canonical ``session push-title-token``
    seam so the ⏳/🔒 glyph disappears LIVE instead of lingering until the next
    render event. Both writes run only AFTER the real ``os.unlink`` (the release
    branch), so they stay OUTSIDE the ``O_EXCL`` check-then-act window and
    cannot widen the kernel race.

    When ``set_title_token`` is False the surface is suppressed entirely — the
    move-back merge lock never set a token, so there is nothing to clear and no
    repaint should fire. Mirrors the gating in :func:`_surface_lock_owned` /
    :func:`_surface_lock_waiting` so all three title surfaces share one
    suppression contract.
    """
    if not set_title_token:
        return
    _clear_title_token(plan_id)
    # Plain, icon-less repaint through the canonical seam so the lock glyph
    # disappears live once the state has been cleared.
    _push_title_token(plan_id)


def _push_title_token(plan_id: str, icon: str | None = None) -> None:
    """Best-effort push through the canonical ``session push-title-token`` seam.

    The single repaint seam shared by every merge-lock title surface. When
    ``icon`` is supplied it pushes that glyph (⏳ waiting / 🔒 owned); when
    ``icon`` is None it is a PLAIN repaint (no ``--icon``) that re-renders the
    title with the default active icon — the icon-optional push the clear path
    uses to drop the lock glyph live. Best-effort: any failure is swallowed at
    DEBUG so it never affects lock acquire/release.
    """
    args = ['session', 'push-title-token', '--plan-id', plan_id]
    if icon is not None:
        args += ['--icon', icon]
    try:
        _run_executor(_PUSH_TOKEN_NOTATION, *args)
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

    Called on a ``blocked`` admission return (non-front, or front-but-lock-lost) —
    it never runs inside the FIFO mutation or the holder-read → re-create
    check-then-act, so it cannot widen the ``O_EXCL`` race. When
    ``set_title_token`` is False the surface is suppressed entirely (no glyph
    reaches the terminal title).
    """
    if not set_title_token:
        return
    _set_title_token(plan_id, _STATE_LOCK_WAITING)
    _push_title_token(plan_id, _ICON_LOCK_WAITING)


# ---------------------------------------------------------------------------
# Acquire result builders (shared between admitted / blocked outcomes)
# ---------------------------------------------------------------------------


def _admitted_result(
    plan_id: str, action: str, lock_path: Path, reclaimed: bool, waiting_count: int
) -> dict[str, Any]:
    """Build the ``admission: admitted`` success payload (acquired / reclaimed / already_held)."""
    return {
        'status': 'success',
        'plan_id': plan_id,
        'action': action,
        'admission': 'admitted',
        'lock_path': str(lock_path),
        'holder': plan_id,
        'reclaimed': reclaimed,
        'waiting_count': waiting_count,
    }


def _blocked_result(
    plan_id: str,
    blocking_plan_id: str | None,
    lock_path: Path,
    waiting_count: int,
    *,
    stale_holder_live_worktree: bool = False,
) -> dict[str, Any]:
    """Build the ``admission: blocked`` structured re-poll payload (NOT an error).

    Returned when this plan is NOT the FIFO front, or is the front but lost the
    ``O_EXCL`` create against a foreign live holder. The consumer's poll/backoff
    loop re-polls (idempotently preserving FIFO position) against this signal until
    admitted or its wait budget is exhausted, then fires the Pre-Merge Gate's
    last-resort ``AskUserQuestion`` carrying ``blocking_plan_id``.

    ``stale_holder_live_worktree`` (default False) adds the refuse-auto-reclaim
    discriminator to the payload — set True ONLY on the live-worktree guard path
    (holder dead by plan-dir absence but its worktree directory is still on disk),
    so the existing branch-cleanup budget-exhaustion escalation can ask the
    operator to confirm rather than the primitive force-releasing a mid-recovery
    holder. The ordinary non-front / foreign-live-holder blocked payload omits the
    field entirely.
    """
    result: dict[str, Any] = {
        'status': 'blocked',
        'plan_id': plan_id,
        'admission': 'blocked',
        'blocking_plan_id': blocking_plan_id,
        'lock_path': str(lock_path),
        'waiting_count': waiting_count,
    }
    if stale_holder_live_worktree:
        result['stale_holder_live_worktree'] = True
    return result


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def run_acquire(args: Namespace) -> dict[str, Any]:
    """Acquire the main-anchored merge lock for ``--plan-id`` via the FIFO queue.

    FIFO-enqueues ``--plan-id`` into ``merge-queue.json`` (idempotently, preserving
    FIFO position on re-poll), then — only when this plan is the FIFO front —
    attempts the atomic ``O_EXCL`` create on ``merge.lock``. On a successful create
    (or stale-reclaim of a dead holder) returns ``status: success`` with
    ``admission: admitted``. A non-front plan, or a front plan that loses the
    ``O_EXCL`` race against a FOREIGN live holder, returns ``status: blocked`` with
    ``admission: blocked`` (carrying ``blocking_plan_id`` + ``waiting_count``) — a
    structured re-poll signal, NOT a hard error and NOT an internal wait; the
    consumer re-polls until admitted or its budget is exhausted. A resolution
    failure stays ``status: error``.

    **Reentrant per plan_id.** When the existing lock is already held by the SAME
    ``plan_id``, this acquire is reentrant: it returns ``status: success`` with
    ``action: already_held`` and ``admission: admitted`` immediately — no second
    ``O_EXCL`` create, no staleness evaluation. This is the self-holder
    short-circuit that lets the finalize auto-merge path re-enter the merge lock
    keyed by the same plan_id (``branch-cleanup`` acquires it, then
    ``integrate_into_main`` re-acquires it under the same ``plan_id``) without
    self-deadlocking. The reentrant grant is NOT an independent second acquisition
    — release is idempotent and holder-scoped, so the single real ``os.unlink``
    happens once when the holder releases (and dequeues the FIFO entry). Cross-plan
    mutual exclusion is unaffected: a FOREIGN live holder still blocks.

    The legacy ``--timeout`` flag is accepted for call-site compatibility but no
    longer drives an internal wait loop — re-polling is the consumer's job. A
    non-front / lock-contended acquire returns ``blocked`` immediately so the
    consumer's poll/backoff loop owns the wait.
    """
    plan_id: str = args.plan_id
    # Default True preserves the title-token surface; callers (the move-back
    # merge lock) pass set_title_token=False to suppress the spurious glyph.
    set_title_token: bool = getattr(args, 'set_title_token', True)

    try:
        lock_path = _resolve_main_lock_path()
    except RuntimeError as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)

    # Reentrant self-holder short-circuit FIRST — before touching the FIFO queue.
    # If this same plan already holds the lock, the finalize auto-merge path is
    # re-entering; grant immediately so it does not self-deadlock or churn the
    # queue. The plan is not enqueued (it already holds the lock); waiting_count
    # is returned as 0 (not read from the queue) to avoid unnecessary I/O on
    # a fast-path that performs no queue mutation.
    if lock_path.exists() and _read_holder(lock_path) == plan_id:
        return _admitted_result(plan_id, 'already_held', lock_path, reclaimed=False, waiting_count=0)

    # FIFO enqueue (idempotent, position-preserving) — decides admission eligibility.
    try:
        enqueue = _enqueue_fifo(plan_id, time.time())
    except (RuntimeError, OSError) as exc:
        return make_error(str(exc), code=ErrorCode.NOT_FOUND, plan_id=plan_id)
    waiting_count: int = enqueue['waiting_count']

    # Not the FIFO front → blocked (re-poll signal). Surface ⏳, emit [LOCK]
    # blocked, and return WITHOUT attempting the O_EXCL create — only the front
    # plan may contend for the lock, so a non-front plan never races the kernel.
    if not enqueue['is_front']:
        holder = _read_holder(lock_path) if lock_path.exists() else ''
        _surface_lock_waiting(plan_id, set_title_token)
        log_lock_event(
            'merge', 'blocked', lock_id=plan_id, lock_file=_LOCK_FILENAME,
            holder=holder or None, waiter=plan_id, waiting_count=waiting_count,
        )
        return _blocked_result(plan_id, holder or None, lock_path, waiting_count)

    # This plan is the FIFO front → it is admission-eligible. Attempt the atomic
    # O_EXCL create; the front plan is the only contender, so the kernel race is
    # the sole arbiter of the single winner.
    if _try_atomic_create(lock_path, plan_id):
        # Lock held — surface 🔒 (best-effort, AFTER the atomic create, OUTSIDE
        # the O_EXCL window), emit [LOCK] acquired.
        _surface_lock_owned(plan_id, set_title_token)
        log_lock_event(
            'merge', 'acquired', lock_id=plan_id, lock_file=_LOCK_FILENAME, waiting_count=waiting_count
        )
        return _admitted_result(plan_id, 'acquired', lock_path, reclaimed=False, waiting_count=waiting_count)

    # The lock exists — inspect the holder. A dead holder is reclaimed atomically
    # (evict the SPECIFIC observed stale file → re-confirm dead → O_EXCL recreate).
    holder = _read_holder(lock_path)

    # Live-worktree guard (evaluated BEFORE the auto-reclaim branch, so it never
    # widens the O_EXCL / sidecar-reclaim window — no new grant path is opened).
    # A holder judged dead by plan-dir absence may still be MID-RECOVERY: its
    # worktree directory is on disk (an interrupted finalize move-back moved the
    # plan dir out but left the worktree). Refuse to auto-reclaim such a holder;
    # return a structured `blocked` signal carrying `stale_holder_live_worktree`
    # so the EXISTING branch-cleanup budget-exhaustion escalation asks the operator
    # to confirm, rather than the primitive force-releasing a mid-recovery holder.
    # No new force-release CLI verb is introduced.
    if holder_is_dead(holder) and holder_has_live_worktree(holder):
        _surface_lock_waiting(plan_id, set_title_token)
        log_lock_event(
            'merge', 'blocked', lock_id=plan_id, lock_file=_LOCK_FILENAME,
            holder=holder or None, waiter=plan_id, waiting_count=waiting_count,
            stale_holder_live_worktree=True,
        )
        return _blocked_result(
            plan_id, holder or None, lock_path, waiting_count, stale_holder_live_worktree=True
        )

    if holder_is_dead(holder):
        reclaimed_from = holder
        if _reclaim_stale_lock(lock_path, reclaimed_from, plan_id):
            _surface_lock_owned(plan_id, set_title_token)
            log_lock_event(
                'merge', 'reclaimed', lock_id=plan_id, lock_file=_LOCK_FILENAME,
                reclaimed_from=reclaimed_from or None, waiting_count=waiting_count,
            )
            return _admitted_result(plan_id, 'acquired', lock_path, reclaimed=True, waiting_count=waiting_count)
        # Reclaim lost (a concurrent reclaimer won, or a live holder was installed
        # in between) — re-read the holder for the blocked payload below.
        holder = _read_holder(lock_path)

    # Front, but a FOREIGN live holder holds the lock (or the reclaim lost) →
    # blocked (re-poll signal). The consumer re-polls; this plan keeps its FIFO
    # front position, so it is first in line when the holder releases.
    _surface_lock_waiting(plan_id, set_title_token)
    log_lock_event(
        'merge', 'blocked', lock_id=plan_id, lock_file=_LOCK_FILENAME,
        holder=holder or None, waiter=plan_id, waiting_count=waiting_count,
    )
    return _blocked_result(plan_id, holder or None, lock_path, waiting_count)


def run_check(args: Namespace) -> dict[str, Any]:
    """Non-blocking read of the current merge-lock holder.

    Reads the lock file without attempting to create or mutate it, and never
    touches the FIFO queue. Returns ``status: free`` when no lock file exists, or
    ``status: held`` + ``holder_plan_id`` when one does (including a self-held
    lock). This serves the Pre-Merge Gate's ``check`` consumer directly from the
    file primitive.
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
    """Release the main-anchored merge lock held by ``--plan-id`` and dequeue it.

    Removes the lock file only when this caller is the recorded holder, then
    dequeues ``--plan-id`` from ``merge-queue.json`` so the next FIFO entry becomes
    the front and is admitted on its next re-poll. A release of a lock not held by
    this caller (foreign holder, or already free) does not remove the lock file but
    STILL dequeues this plan from the FIFO queue and is a no-op success — release
    must be idempotent so a finalize that crashed mid-merge and retried does not
    error on the second release, and a plan that gave up waiting must not leave a
    stale FIFO entry blocking the front.
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

    # Always dequeue this plan from the FIFO queue — whether it held the lock, was
    # still waiting, or gave up — so the next FIFO entry can advance to the front.
    # Idempotent: removing an absent plan_id is a benign no-op.
    try:
        waiting_count = _dequeue_fifo(plan_id)
    except (RuntimeError, TimeoutError) as exc:
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
            'waiting_count': waiting_count,
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
            'waiting_count': waiting_count,
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
    log_lock_event(
        'merge', 'released', lock_id=plan_id, lock_file=_LOCK_FILENAME, waiting_count=waiting_count
    )
    return {
        'status': 'success',
        'plan_id': plan_id,
        'action': 'released',
        'lock_path': str(lock_path),
        'waiting_count': waiting_count,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point — ``acquire`` / ``check`` / ``release`` actions."""
    parser = create_workflow_cli(
        description='Unified merge lock: the single main-anchored merge-to-main serializer with a FIFO admission queue',
        epilog="""
Examples:
  merge_lock.py acquire --plan-id EXAMPLE-PLAN [--timeout 0]
  merge_lock.py check --plan-id EXAMPLE-PLAN
  merge_lock.py release --plan-id EXAMPLE-PLAN
""",
        subcommands=[
            {
                'name': 'acquire',
                'help': 'FIFO-enqueue and atomically acquire the main-anchored merge lock (front-only, non-blocking)',
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
                        'help': f'Legacy compatibility flag; acquire no longer waits internally (default: {_DEFAULT_TIMEOUT_SECONDS})',
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
                'help': 'Release the main-anchored merge lock held by --plan-id and dequeue it from the FIFO queue',
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
    safe_main(main)()
