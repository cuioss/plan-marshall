#!/usr/bin/env python3
"""Build-queue slot wrapper for the build execute path (D6).

Provides :func:`build_queue_slot` — a context manager every ``cmd_run`` build
site wraps around its ``execute_direct(...)`` call so that, **only when a
``plan_id`` is set**, the build participates in the cluster-wide build queue
(``plan-marshall:manage-locks:build_queue``, the bounded-``k``-slot admitter
from D5).

Behaviour:

* **No plan_id → NO-OP passthrough.** When ``plan_id`` is falsy the context
  manager yields immediately and does nothing else. A build invoked without a
  plan (ad-hoc CLI run, the standalone ``run`` subcommand) therefore runs
  completely unchanged — this is the critical backward-compatibility guarantee.
* **plan_id set → acquire / wait / release.** On entry it calls ``build_queue
  acquire``. On ``admitted`` it best-effort sets the ``building`` title-token
  (🔨) and yields so the caller runs the build. On ``blocked`` it best-effort
  sets the ``build-waiting`` title-token (🕐), sleeps ``_WAIT_SECONDS`` and
  re-polls, up to ``build_queue.max_retries`` (default 10 from marshal.json).
  Whether the slot is admitted or the retries are exhausted, the held / queued
  admission id is ALWAYS released and the title-token ALWAYS cleared in a
  ``finally`` block, so the queue never leaks a slot or a waiting entry and the
  terminal-title state never gets stuck.
* **Retries exhausted → BuildQueueTimeout.** When the build is still blocked
  after the final retry the queued id is released (cleanup) and
  :class:`BuildQueueTimeout` is raised, carrying a structured "try again later"
  message the build site turns into an error result without running the build.

**Title-token writes are best-effort.** Every ``manage-status title-token`` and
``platform_runtime session push-title-token`` call is wrapped so a failure
NEVER affects the build outcome — the token is a display affordance, not a
correctness primitive. The queue ``acquire`` / ``release`` calls are NOT
best-effort: an ``acquire`` that cannot reach the queue is a hard failure (the
build must not silently bypass the concurrency limiter), and a ``release``
failure is logged but cannot itself abort an already-finished build.

**Two invocation channels, by registration status.**

* The queue primitive ``manage-locks/scripts/build_queue.py`` is NOT an
  executor-registered notation — like its sibling ``merge_lock.py`` it is loaded
  by FILE PATH and its ``run_acquire`` / ``run_release`` handlers are called
  in-process with an ``argparse.Namespace``. This mirrors
  ``integrate_into_main.py``'s ``_load_merge_lock`` pattern (the single owner of
  the lock logic is reused, never re-implemented or shelled out to).
* The two best-effort title-token operations live in executor-registered skills
  (``manage-status`` and ``platform-runtime``) whose multi-module layouts make a
  file-path import fragile; they are invoked through the executor
  (``python3 .plan/execute-script.py {notation} ...``) as a subprocess. A
  failure of either is swallowed — the title token is a display affordance, not
  a correctness primitive.
"""

from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
import time
from argparse import Namespace
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from file_ops import get_executor_path, get_marshal_path, read_json  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]

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

# Title-token icons for the two build phases. The glyph vocabulary is the
# display contract shared with manage-terminal-title; these two are the build
# phase pair (🕐 waiting for a slot, 🔨 actively building).
_ICON_BUILD_WAITING = '🕐'
_ICON_BUILDING = '🔨'

_TITLE_TOKEN_NOTATION = 'plan-marshall:manage-status:manage-status'
_PUSH_TOKEN_NOTATION = 'plan-marshall:platform-runtime:platform_runtime'

# Lazily-imported build_queue module (file-path import; see _load_build_queue).
_build_queue_mod: Any = None


# Sibling-skill ``scripts`` dirs that ``build_queue.py`` imports transitively
# (``_locks_core`` from manage-locks, ``file_ops`` from tools-file-ops,
# ``triage_helpers`` from script-shared/scripts/workflow; ``marketplace_paths``
# lives in script-shared/scripts which is already this file's own dir). A
# file-path import does not inherit the importing skill's PYTHONPATH for these
# transitive imports, so they are ensured on ``sys.path`` before the exec —
# the build subprocess's executor PYTHONPATH does not include manage-locks.
_BUILD_QUEUE_DEP_DIRS: tuple[Path, ...] = (
    _BUILD_QUEUE_PATH.parent,                                          # manage-locks/scripts
    _THIS_DIR.parent.parent.parent / 'tools-file-ops' / 'scripts',     # file_ops
    _THIS_DIR.parent / 'workflow',                                     # triage_helpers
    _THIS_DIR.parent,                                                  # marketplace_paths, toon_parser
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
        super().__init__(
            f'build queue saturated for plan {plan_id!r} after {max_retries} '
            f'retries — try again later'
        )


def _resolve_max_retries() -> int:
    """Read ``build_queue.max_retries`` from marshal.json, defaulting to 10.

    Mirrors ``build_queue.py::_resolve_max_slots`` — a missing file, missing
    ``build_queue`` block, missing ``max_retries`` key, or a non-positive /
    non-integer value all degrade to the conservative default so a misconfigured
    queue still bounds the wait loop rather than spinning forever.
    """
    config = read_json(get_marshal_path(), default={})
    if not isinstance(config, dict):
        return _DEFAULT_MAX_RETRIES
    block = config.get('build_queue')
    if not isinstance(block, dict):
        return _DEFAULT_MAX_RETRIES
    raw = block.get('max_retries')
    if isinstance(raw, bool) or not isinstance(raw, int):
        return _DEFAULT_MAX_RETRIES
    return raw if raw > 0 else _DEFAULT_MAX_RETRIES


def _run_executor(notation: str, *cli_args: str) -> dict[str, Any]:
    """Invoke ``{notation}`` through the executor and parse its TOON stdout.

    Returns the parsed TOON dict on a clean (exit 0) run. On a non-zero exit or
    unparseable output, returns ``{'status': 'error', ...}`` so the caller can
    branch on ``status`` without catching exceptions for the common failure
    path. Never raises for a subprocess failure — the queue/token call sites
    decide whether a given failure is fatal.
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
    except Exception as exc:  # noqa: BLE001 — surface as a structured error dict
        return {'status': 'error', 'error': f'acquire failed: {exc}'}
    return result if isinstance(result, dict) else {'status': 'error', 'error': 'non-dict acquire result'}


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
            plan_id, admission_id, result.get('error', 'unknown'),
        )


def _release_raw(plan_id: str, admission_id: str) -> dict[str, Any]:
    """Raw ``build_queue.run_release`` call (separated so tests can assert on it)."""
    try:
        bq = _load_build_queue()
        result = bq.run_release(Namespace(plan_id=plan_id, id=admission_id))
    except Exception as exc:  # noqa: BLE001 — surface as a structured error dict
        return {'status': 'error', 'error': f'release failed: {exc}'}
    return result if isinstance(result, dict) else {'status': 'error', 'error': 'non-dict release result'}


def _set_title_token(plan_id: str, state: str) -> None:
    """Best-effort ``manage-status title-token set --state {state}``.

    Wrapped so any failure (script error, parse error, missing plan) is
    swallowed at DEBUG — the title token is a display affordance and MUST NOT
    influence the build outcome.
    """
    try:
        _run_executor(
            _TITLE_TOKEN_NOTATION, 'title-token', 'set', '--plan-id', plan_id, '--state', state
        )
    except Exception as exc:  # noqa: BLE001 — token writes are best-effort
        logger.debug('title-token set(%s) for %s failed: %s', state, plan_id, exc)


def _clear_title_token(plan_id: str) -> None:
    """Best-effort ``manage-status title-token clear`` (always in finally)."""
    try:
        _run_executor(_TITLE_TOKEN_NOTATION, 'title-token', 'clear', '--plan-id', plan_id)
    except Exception as exc:  # noqa: BLE001 — token writes are best-effort
        logger.debug('title-token clear for %s failed: %s', plan_id, exc)


def _push_title_token(plan_id: str, icon: str) -> None:
    """Best-effort ``platform_runtime session push-title-token --icon {icon}``."""
    try:
        _run_executor(
            _PUSH_TOKEN_NOTATION, 'session', 'push-title-token', '--plan-id', plan_id, '--icon', icon
        )
    except Exception as exc:  # noqa: BLE001 — token push is best-effort
        logger.debug('push-title-token(%s) for %s failed: %s', icon, plan_id, exc)


def _wait_for_admission(plan_id: str, max_retries: int) -> str:
    """Acquire a slot, polling while blocked, and return the admitted id.

    Sets the ``build-waiting`` token (🕐) on each blocked poll and releases the
    superseded blocked id before re-polling so the FIFO waiting queue never
    accumulates stale entries for this plan. Raises :class:`BuildQueueTimeout`
    when still blocked after ``max_retries`` re-polls (the final blocked id is
    released first).
    """
    result = _acquire(plan_id)
    if result.get('status') != 'success':
        # acquire is NOT best-effort: a queue we cannot reach is a hard failure.
        raise RuntimeError(
            f'build_queue acquire failed for {plan_id!r}: {result.get("error")}'
        )

    admission_id = str(result['id'])
    if result.get('admission') == 'admitted':
        return admission_id

    # Blocked: surface the waiting state, then poll.
    _set_title_token(plan_id, 'build-waiting')
    _push_title_token(plan_id, _ICON_BUILD_WAITING)

    for _ in range(max_retries):
        time.sleep(_WAIT_SECONDS)
        # Drop the prior blocked entry before re-polling so the waiting queue
        # does not accumulate one stale entry per retry for this plan.
        _release(plan_id, admission_id)
        result = _acquire(plan_id)
        if result.get('status') != 'success':
            raise RuntimeError(
                f'build_queue acquire failed for {plan_id!r}: {result.get("error")}'
            )
        admission_id = str(result['id'])
        if result.get('admission') == 'admitted':
            return admission_id

    # Retries exhausted while still blocked — release the queued id and fail.
    _release(plan_id, admission_id)
    raise BuildQueueTimeout(plan_id, max_retries)


@contextmanager
def build_queue_slot(plan_id: str | None) -> Iterator[None]:
    """Context manager wrapping a build in the cluster build queue.

    When ``plan_id`` is falsy this is a pure no-op passthrough — the body runs
    unchanged with no queue interaction (the backward-compatibility guarantee
    for plan-less builds). When ``plan_id`` is set, the body runs only after a
    slot is admitted; the slot is released and the title-token cleared in a
    ``finally`` regardless of how the body exits.

    Raises:
        BuildQueueTimeout: when no slot is admitted within ``max_retries``.
    """
    if not plan_id:
        yield
        return

    max_retries = _resolve_max_retries()
    admission_id = _wait_for_admission(plan_id, max_retries)

    # Admitted — surface the building state and run the build.
    _set_title_token(plan_id, 'building')
    _push_title_token(plan_id, _ICON_BUILDING)
    try:
        yield
    finally:
        _release(plan_id, admission_id)
        _clear_title_token(plan_id)
