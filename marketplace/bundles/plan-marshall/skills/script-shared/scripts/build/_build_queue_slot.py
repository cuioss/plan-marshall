#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build-queue slot wrapper for the build execute path (D6).

Provides :func:`build_queue_slot` — a context manager every ``cmd_run`` build
site wraps around its ``execute_direct(...)`` call so that, **only when
``plan_id`` names a real plan** (neither falsy nor the ``NO_PLAN`` sentinel),
the build participates in the machine-global build queue
(``plan-marshall:manage-locks:build_queue``, the bounded-``k``-slot admitter over
the single machine-global ``build-queue.json``).

This is the **in-process fallback** limiter path of the D5 build-execute routing
seam: a build that is NOT routed to the marshalld daemon (the project is
unregistered, or the daemon is down) acquires its slot here, against the SAME
machine-global ``build-queue.json`` the daemon's scheduler coordinates on for
registered builds. ``build_queue.py`` is the shared reader/writer of that one
file for BOTH paths — one file, one slot budget, one path per build, never
stacked. A build that DID route to the daemon must not also acquire a fallback
slot; the ``routed`` guard below (and the routing seam returning before it is
ever called) enforce the no-stacking invariant.

This module is a **pure concurrency limiter**: it admits, waits, and releases
build-queue slots and does nothing else. It writes no terminal-title state.

The one thing it additionally *reports* is the queue's own ``warnings`` — today,
a surviving per-repo ``build.queue.max_slots`` that no longer takes effect. Each
is surfaced once per invocation, deduplicated by ``code`` across the blocked
re-polls (see :func:`_surface_warnings`), to stderr and to the plan work log. A
warning never blocks, delays, or aborts the build; reporting is not gating.

Behaviour:

* **routed → NO-OP passthrough.** When ``routed`` is true the build already ran
  on (or is being served by) the marshalld daemon, whose child holds the single
  machine-global slot; taking a fallback slot here would double-count the build
  (stacking). The context manager therefore yields immediately without touching
  the queue — the explicit no-stacking guard.
* **No plan_id → NO-OP passthrough.** When ``names_real_plan(plan_id)`` is false
  the context manager yields immediately and does nothing else. A build invoked
  without a plan (ad-hoc CLI run, the standalone ``run`` subcommand) therefore
  runs completely unchanged — this is the critical backward-compatibility
  guarantee, and enrolling those builds in the shared queue would serialize work
  that has always run free.
* **plan_id set → acquire / wait / release.** On entry it calls ``build_queue
  acquire``. On ``admitted`` it yields so the caller runs the build. On
  ``blocked`` it sleeps ``_WAIT_SECONDS`` and re-polls ``acquire`` WITHOUT
  releasing first, up to ``build.queue.max_retries`` (default 10 from
  marshal.json). Because ``run_acquire`` is idempotent for an already-queued
  ``plan_id``, the plan KEEPS its FIFO position across retries rather than being
  shuffled to the back. Whether the slot is admitted or the retries are
  exhausted, the held / queued admission id is ALWAYS released in a ``finally``
  block, so the queue never leaks a slot or a waiting entry.
* **Retries exhausted → BuildQueueTimeout.** When the build is still blocked
  after the final retry the queued id is released (cleanup) and
  :class:`BuildQueueTimeout` is raised, carrying a structured "try again later"
  message the build site turns into an error result without running the build.

The queue ``acquire`` / ``release`` calls are NOT best-effort: an ``acquire``
that cannot reach the queue is a hard failure (the build must not silently
bypass the concurrency limiter), and a ``release`` failure is logged but cannot
itself abort an already-finished build.

The queue primitive ``manage-locks/scripts/build_queue.py`` is NOT an
executor-registered notation — like its sibling ``merge_lock.py`` it is loaded
by FILE PATH and its ``run_acquire`` / ``run_release`` handlers are called
in-process with an ``argparse.Namespace``. This mirrors
``integrate_into_main.py``'s ``_load_merge_lock`` pattern (the single owner of
the lock logic is reused, never re-implemented or shelled out to).
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import time
from argparse import Namespace
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from file_ops import get_marshal_path, read_json
from marketplace_paths import names_real_plan
from plan_logging import log_entry

logger = logging.getLogger(__name__)

# build_queue.py lives in the sibling manage-locks skill. Resolve its path from
# this file's location (…/script-shared/scripts/build/_build_queue_slot.py →
# …/manage-locks/scripts/build_queue.py) so the SINGLE owner of the queue logic
# is reused by file-path import, mirroring integrate_into_main._load_merge_lock.
_THIS_DIR = Path(__file__).resolve().parent
_BUILD_QUEUE_PATH = _THIS_DIR.parent.parent.parent / 'manage-locks' / 'scripts' / 'build_queue.py'

# Seconds to sleep between blocked-acquire retries. A module constant (not a
# parameter) so unit tests can monkeypatch it to 0 — the build wrapper never
# needs to vary the wait interval per invocation.
_WAIT_SECONDS = 60

_DEFAULT_MAX_RETRIES = 10

# Lazily-imported build_queue module (file-path import; see _load_build_queue).
_build_queue_mod: Any = None


# Sibling-skill ``scripts`` dirs that ``build_queue.py`` imports transitively
# (``_locks_core`` from manage-locks, ``file_ops`` from tools-file-ops,
# ``triage_helpers`` from script-shared/scripts/workflow, ``_machine_config``
# from this file's OWN dir; ``marketplace_paths`` lives in script-shared/scripts).
# A file-path import does not inherit the importing skill's PYTHONPATH for these
# transitive imports, so they are ensured on ``sys.path`` before the exec —
# the build subprocess's executor PYTHONPATH does not include manage-locks.
_BUILD_QUEUE_DEP_DIRS: tuple[Path, ...] = (
    _BUILD_QUEUE_PATH.parent,  # manage-locks/scripts
    _THIS_DIR.parent.parent.parent / 'tools-file-ops' / 'scripts',  # file_ops
    _THIS_DIR.parent / 'workflow',  # triage_helpers
    _THIS_DIR.parent,  # marketplace_paths, toon_parser
    _THIS_DIR,  # _machine_config (the machine-global cap resolver)
)


def _load_build_queue() -> Any:
    """Import the sibling ``build_queue.py`` by file path (cached).

    Mirrors ``integrate_into_main._load_merge_lock`` — the queue primitive is NOT
    an executor-registered notation, so it is reused as the single owner of the
    queue logic via an in-process file-path import rather than a subprocess. The
    sibling-skill ``scripts`` dirs ``build_queue.py`` imports transitively are
    ensured on ``sys.path`` first, since a file-path import does not carry them.
    """
    global _build_queue_mod
    if _build_queue_mod is not None:
        return _build_queue_mod
    for dep_dir in _BUILD_QUEUE_DEP_DIRS:
        dep_str = str(dep_dir)
        if dep_dir.is_dir() and dep_str not in sys.path:
            sys.path.insert(0, dep_str)
    spec = importlib.util.spec_from_file_location('build_queue', _BUILD_QUEUE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load build_queue from {_BUILD_QUEUE_PATH}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _build_queue_mod = module
    return module


class BuildQueueTimeout(RuntimeError):
    """Raised when a build cannot acquire a slot within ``max_retries`` polls.

    Carries the plan_id, the exhausted retry count, and a "try again later"
    message the build site renders into a structured error result instead of
    running the build.
    """

    def __init__(self, plan_id: str, max_retries: int) -> None:
        self.plan_id = plan_id
        self.max_retries = max_retries
        super().__init__(f'build queue saturated for plan {plan_id!r} after {max_retries} retries — try again later')


def _resolve_max_retries() -> int:
    """Read ``build.queue.max_retries`` from marshal.json, defaulting to 10.

    A missing file, missing ``build`` block, missing ``queue`` block, missing
    ``max_retries`` key, or a non-positive / non-integer value all degrade to the
    conservative default so a misconfigured queue still bounds the wait loop
    rather than spinning forever. A ``bool`` is rejected although it is an
    ``int`` subclass, so ``true`` never becomes a retry budget of 1.

    Unlike the slot CAP — which is machine-global, because every caller contends
    for one shared slot budget — ``max_retries`` stays a per-repo
    ``marshal.json`` key: it bounds only THIS caller's own wait loop and is
    never evaluated against another caller's entries.
    """
    config = read_json(get_marshal_path(), default={})
    if not isinstance(config, dict):
        return _DEFAULT_MAX_RETRIES
    build = config.get('build')
    if not isinstance(build, dict):
        return _DEFAULT_MAX_RETRIES
    block = build.get('queue')
    if not isinstance(block, dict):
        return _DEFAULT_MAX_RETRIES
    raw = block.get('max_retries')
    if isinstance(raw, bool) or not isinstance(raw, int):
        return _DEFAULT_MAX_RETRIES
    return raw if raw > 0 else _DEFAULT_MAX_RETRIES


def _acquire(plan_id: str) -> dict[str, Any]:
    """Call ``build_queue.run_acquire`` in-process and return its result dict.

    Any exception from the queue handler (file-path import failure, I/O error in
    the read-modify-write) degrades to a ``status: error`` dict so the caller can
    branch on ``status`` — an acquire that cannot reach the queue is a hard
    failure the wait loop turns into a raise, never a silent bypass.
    """
    try:
        bq = _load_build_queue()
        result = bq.run_acquire(Namespace(plan_id=plan_id))
    except Exception as exc:  # surface as a structured error dict
        return {'status': 'error', 'error': f'acquire failed: {exc}'}
    return result if isinstance(result, dict) else {'status': 'error', 'error': 'non-dict acquire result'}


def _surface_warnings(result: dict[str, Any], plan_id: str, seen: set[str]) -> None:
    """Surface each new ``acquire`` warning to stderr and the plan work log.

    Emission mirrors ``_build_execute_factory._record_resolution``: stderr
    unconditionally (the only sink a build subprocess has without a configured
    logging handler — a ``logger.warning`` call here would be discarded), and the
    plan's captured work log at ``WARNING`` when ``plan_id`` names a real plan.

    **Deduplicated by ``code``, not by message.** ``seen`` is created once per
    :func:`build_queue_slot` invocation and threaded through every re-poll, so a
    build that blocks and re-polls N times reports the demoted-key warning ONCE
    rather than N+1 times. The code is the stable identity for this: a message
    embeds the live cap resolution, so two messages for one condition can differ
    in text while naming the same problem, and deduplicating on text would let
    the queue spam a blocked build.

    A warning is a report, never a verdict: nothing here blocks, delays, or
    aborts the build. Malformed entries are skipped rather than raised on,
    because a queue result that fails to describe itself must not take down a
    build that was legitimately admitted.

    Args:
        result: The ``acquire`` result dict.
        plan_id: The acquiring plan. The ``names_real_plan`` test below is
            redundant at the sole call site — :func:`build_queue_slot` already
            returned early for a plan-less build — and is kept so the emitter
            owns its own precondition rather than inheriting it from a caller.
        seen: Codes already surfaced during this invocation; mutated in place.
    """
    for warning in result.get('warnings') or []:
        if not isinstance(warning, dict):
            continue
        code = warning.get('code')
        message = warning.get('message')
        if not isinstance(code, str) or not isinstance(message, str) or code in seen:
            continue
        seen.add(code)
        line = f'[BUILD-QUEUE] {message}'
        # The stderr sink is best-effort BY CONTRACT (see the docstring above): a
        # report must never take down a build that was legitimately admitted. The
        # guard is load-bearing at BOTH ``_wait_for_admission`` call sites, which
        # run with an entry already on the machine-global build-queue.json: a
        # raising ``print`` (closed/full stderr, a broken pipe) must not turn a
        # legitimate admission into a failed build.
        #
        # Scoped to ``Exception``, deliberately NOT ``BaseException``: a
        # ``KeyboardInterrupt`` raised while writing a warning must still abort
        # the build, and swallowing it here would make an interrupt during
        # warning output silently unkillable.
        #
        # That scope does NOT leave the slot leaking, and the two concerns are
        # distinct: a ``BaseException`` from here propagates into
        # ``_wait_for_admission``'s ``except BaseException`` arm, which RELEASES
        # the admitted-or-queued id and RE-RAISES. Releasing is not swallowing —
        # the interrupt stays fatal, and the host's shared slot budget stays
        # whole. Do NOT widen this guard to ``BaseException`` to "also handle"
        # the leak: that swallow is what would make an interrupt unkillable, and
        # the cleanup scope already covers it.
        #
        # The asymmetry with the ``log_entry`` call below is intentional and must
        # not be "tidied" into a shared wrapper: ``plan_logging.log_entry``
        # already swallows its own exceptions internally, so a second guard round
        # it would be dead code.
        try:
            print(line, file=sys.stderr)
        except Exception:
            pass
        if names_real_plan(plan_id):
            log_entry('work', plan_id, 'WARNING', line)


def _release(plan_id: str, admission_id: str) -> None:
    """Best-effort release of ``admission_id`` (logged, never raised).

    Release is idempotent at the queue (a not-present id is a no-op success), so
    releasing a blocked or already-released id is benign. A release that fails is
    logged at WARNING — the build has already finished, so a release failure
    cannot abort it.
    """
    result = _release_raw(plan_id, admission_id)
    if result.get('status') != 'success':
        logger.warning(
            'build_queue release failed for %s (id=%s): %s',
            plan_id,
            admission_id,
            result.get('error', 'unknown'),
        )


def _release_raw(plan_id: str, admission_id: str) -> dict[str, Any]:
    """Raw ``build_queue.run_release`` call (separated so tests can assert on it)."""
    try:
        bq = _load_build_queue()
        result = bq.run_release(Namespace(plan_id=plan_id, id=admission_id))
    except Exception as exc:  # surface as a structured error dict
        return {'status': 'error', 'error': f'release failed: {exc}'}
    return result if isinstance(result, dict) else {'status': 'error', 'error': 'non-dict release result'}


def _wait_for_admission(plan_id: str, max_retries: int) -> str:
    """Acquire a slot, polling while blocked, and return the admitted id.

    Re-polls ``acquire`` WITHOUT releasing first. Because ``run_acquire`` is
    idempotent for an already-queued ``plan_id`` — it reuses the existing waiting
    entry in place rather than appending a new one — the plan KEEPS its FIFO
    position across every retry. Releasing-then-re-acquiring (the prior
    behaviour) pushed the plan to the back of the waiting queue on each poll,
    defeating FIFO; that release is therefore gone from the loop. Raises
    :class:`BuildQueueTimeout` when still blocked after ``max_retries`` re-polls
    (the final queued id IS released first, as cleanup, so an exhausted plan does
    not leak a waiting entry).

    Each ``acquire`` result's ``warnings`` are surfaced through
    :func:`_surface_warnings`, deduplicated by ``code`` across every re-poll via
    the ``seen`` set created here — so the whole wait reports a given condition
    once, not once per poll.

    From the moment the first ``acquire`` commits an entry, EVERY non-return exit
    releases that entry and re-raises — the pre-loop warning surfacing included,
    since it runs before :func:`build_queue_slot` establishes its release
    ``finally`` and a leaked machine-global entry never self-heals. Releasing is
    not swallowing: a ``KeyboardInterrupt`` still propagates and still aborts the
    build.
    """
    seen: set[str] = set()
    result = _acquire(plan_id)
    if result.get('status') != 'success':
        # acquire is NOT best-effort: a queue we cannot reach is a hard failure.
        raise RuntimeError(f'build_queue acquire failed for {plan_id!r}: {result.get("error")}')

    # Read the id FIRST, before anything else can raise. The acquire above has
    # already committed an entry to the machine-global queue, so from this point
    # every non-return exit needs an id to release — and the read itself is the
    # one step that cannot be covered, because a result carrying no ``id`` leaves
    # nothing to release in the first place.
    admission_id = str(result['id'])

    # The cleanup scope opens HERE, not after the admitted-return decision, and
    # that placement is the whole point: ``_surface_warnings`` and the
    # ``admission`` read below run with an entry already on the machine-global
    # ``build-queue.json``, outside ``build_queue_slot``'s release ``finally``
    # (which is only established once this function has RETURNED). A
    # ``BaseException`` escaping either of them with the scope opened later left
    # an ADMITTED entry with no release path in scope — permanently shrinking
    # every caller's admission capacity on the host, since nothing self-heals it.
    #
    # The same scope covers the poll loop below, where ``admission_id`` is a
    # QUEUED waiting entry rather than a held slot: a hard acquire failure, retry
    # exhaustion, or an interrupt during ``time.sleep`` must release the queued
    # id or the waiting entry leaks. ``BaseException`` so cleanup also runs on
    # ``KeyboardInterrupt`` / ``SystemExit`` — the handler RELEASES and RE-RAISES
    # and never swallows, so an interrupt stays fatal.
    #
    # Both ``return admission_id`` statements are INSIDE this try deliberately: a
    # ``return`` bypasses the handler, so a live held slot is still never
    # released here (its release is owned by ``build_queue_slot``'s ``finally``).
    try:
        _surface_warnings(result, plan_id, seen)
        if result.get('admission') == 'admitted':
            return admission_id

        for _ in range(max_retries):
            time.sleep(_WAIT_SECONDS)
            # Re-poll WITHOUT releasing — run_acquire is idempotent for an
            # already-queued plan_id, so the waiting entry keeps its FIFO
            # position in place instead of being shuffled to the back on each
            # retry.
            result = _acquire(plan_id)
            if result.get('status') != 'success':
                raise RuntimeError(f'build_queue acquire failed for {plan_id!r}: {result.get("error")}')
            _surface_warnings(result, plan_id, seen)
            admission_id = str(result['id'])
            if result.get('admission') == 'admitted':
                return admission_id

        # Retries exhausted while still blocked — fail (the queued id is released
        # by the handler below as cleanup, so an exhausted plan does not leak a
        # waiting entry).
        raise BuildQueueTimeout(plan_id, max_retries)
    except BaseException:
        _release(plan_id, admission_id)
        raise


@contextmanager
def build_queue_slot(plan_id: str | None, *, routed: bool = False) -> Iterator[None]:
    """Context manager wrapping a build in the machine-global build queue.

    When ``routed`` is true this is a pure no-op passthrough — the build was
    routed to the marshalld daemon, whose child already holds the single
    machine-global slot, so acquiring a fallback slot here would stack a second
    slot on the same build (the no-stacking guard). When ``plan_id`` does not
    name a real plan this is likewise a no-op passthrough — the body runs
    unchanged with no queue interaction (the backward-compatibility guarantee
    for plan-less builds). When ``plan_id`` names a REAL plan and the build was
    NOT routed, the body runs only after a slot is admitted on the shared
    machine-global ``build-queue.json``; the slot is released in a ``finally``
    regardless of how the body exits.

    Args:
        plan_id: The plan acquiring a slot; anything :func:`names_real_plan`
            rejects is a plan-less no-op.
        routed: When true, the build is served by the daemon — take no fallback
            slot (the explicit no-stacking guard).

    Raises:
        BuildQueueTimeout: when no slot is admitted within ``max_retries``.
    """
    if routed or not names_real_plan(plan_id):
        yield
        return
    assert plan_id is not None  # names_real_plan() rejects None

    max_retries = _resolve_max_retries()
    admission_id = _wait_for_admission(plan_id, max_retries)

    try:
        yield
    finally:
        _release(plan_id, admission_id)
