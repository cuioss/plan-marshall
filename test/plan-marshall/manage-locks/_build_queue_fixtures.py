#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``build queue`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for ``manage-locks/build_queue.py`` — the bounded-``k``-slot build-queue
concurrency limiter with a FIFO waiting queue.

Contract under test (solution_outline.md D5 + lock-reconciliation-analysis.md §5
massive-parallel-concurrency invariants (i) + (iii) + (iv); ADR-002):

* **Admit under capacity** — ``acquire`` with ``len(active) < max_slots`` appends
  ``{id, ts}`` to ``active`` and returns ``admission: admitted``.
* **Block at capacity** — ``acquire`` with ``active`` full appends to the FIFO
  ``waiting`` queue and returns ``admission: blocked``. The script never loops —
  ``blocked`` is a structured signal, not an error.
* **Release frees + FIFO-promotes** — ``release --id ID`` removes the id from
  ``active`` and promotes the FRONT waiting entry (the first list element —
  serialized append order, NOT the smallest admit-``ts``) into
  the freed slot, recording it as ``promoted``; it appends an id+timestamp
  ``run_log`` entry. Release of an absent id is an idempotent no-op success.
* **FIFO ordering is list position, not admit-``ts``** — every promote path (the
  reaper promote, the idempotent re-poll promote-eligibility check, and the
  release promote) selects the front by list position. ``ts`` is sampled outside
  the serialized ``rmw_json`` section and is informational only, so under
  concurrent enqueue it can disagree with append order; an inverted-``ts``
  fixture pins that a ``min(ts)`` selector cannot creep back in.
* **Id collision-resistance** — the admission id is ``{plan_id}:{uuid4}`` so two
  acquires by the SAME plan never collide.
* **Default + configured ``max_slots``** — absent config defaults to 5; a
  ``build_queue.max_slots`` override in marshal.json is honored.
* **Corrupt/missing file as empty** — a missing or malformed ``build-queue.json``
  is treated as empty state, not a crash.
* **Machine-global resolution** — ``build-queue.json`` resolves under the
  machine-global home root (:func:`marketplace_paths.home_root`,
  ``~/.plan-marshall/build-queue.json`` by default, overridable via
  ``PLAN_MARSHALL_HOME``) regardless of caller cwd — the host-wide tier shared
  across every checkout, NOT the per-repo main-anchored exception corpus.
* **Foreign-holder pruning** — each entry is stamped at acquire with
  ``project_root = str(main_checkout_root())`` so a foreign project's live holder
  is judged against its OWN checkout and never reclaimed by a session in a
  different repo.
* **Shared-core delegation** — liveness is the imported
  :func:`_locks_core.holder_is_dead`; the resolvers are the imported
  :func:`marketplace_paths.home_root` / ``main_checkout_root``; none is
  re-implemented.

Real-parallel obligations (§5 (i) + (iii) + (iv)): the no-over-admit boundary (i),
the no-double-promote/lost-entry FIFO property (iii), and dead-holder reclaim
without evicting a live holder (iv) are asserted under REAL spawned-subprocess
contention — N processes racing the SAME machine-global ``build-queue.json`` via
the CLI entry point — not sequential calls. A sequential test can never exercise
the kernel-serialized read-modify-write race window these invariants guard.

Isolation: every test runs against an isolated home root and ``PLAN_BASE_DIR``
staged under ``tmp_path`` so the suite never contends for the real
``~/.plan-marshall/build-queue.json`` under ``-n auto``. The queue resolves to
``<PLAN_MARSHALL_HOME>/build-queue.json``; holder plan dirs resolve to
``<PLAN_BASE_DIR>/plans/{holder}``; marshal.json resolves to
``<PLAN_BASE_DIR>/marshal.json``. The ``main`` fixture dir is a real git repo so
subprocess ``main_checkout_root()`` resolves to it, and the in-process fixture
pins ``build_queue.main_checkout_root`` to that same root so stamped
``project_root`` liveness resolves under ``<PLAN_BASE_DIR>``.
"""


from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'build_queue.py')


build_queue = load_script_module('plan-marshall', 'manage-locks', 'build_queue.py', 'build_queue_under_test')


# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``build_queue`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``build_queue`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``build_queue`` never sees).
import sys as _sys  # noqa: E402

_locks_core = _sys.modules[build_queue.log_lock_event.__module__]


def _read_lock_log() -> str:
    """Read the main-anchored [LOCK] log, '' when no emission landed yet."""
    log_path = _locks_core._resolve_lock_log_path()
    if not log_path.exists():
        return ''
    return str(log_path.read_text(encoding='utf-8'))


# =============================================================================
# Fixtures
# =============================================================================


def _init_git_repo(repo: Path) -> None:
    """Initialise a bare-minimum git repo so ``main_checkout_root()`` resolves.

    A subprocess ``build_queue`` invocation stamps ``project_root`` via
    ``main_checkout_root()`` → ``git rev-parse --git-common-dir``; running that
    subprocess with ``cwd`` set to this repo makes the stamped root the fixture's
    own ``main`` dir rather than the developer's real checkout.
    """
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _set_max_slots(base: Path, max_slots: int) -> None:
    """Write a marshal.json with the configured ``build.queue.max_slots``."""
    (base / 'marshal.json').write_text(
        json.dumps({'build': {'queue': {'max_slots': max_slots}}}), encoding='utf-8'
    )


def _read_queue(queue_path: Path) -> dict:
    """Read the persisted queue state as a dict."""
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


# =============================================================================
# D5 — self-healing stale-slot reclaim (active_since + validate_lock_queue +
# adaptive build_queue_upper_limit). ADDITIVE over D4: these are new functions,
# none of D4's [LOCK]-event tests above are modified.
# =============================================================================

def _write_queue(queue_path: Path, state: dict) -> None:
    """Persist a hand-built queue state directly (for seeding stale entries)."""
    queue_path.write_text(json.dumps(state), encoding='utf-8')


def _seed_active_entry(
    queue_path: Path,
    *,
    entry_id: str,
    plan_id: str,
    active_since: float | None,
    ts: float = 0.0,
    waiting: list[dict] | None = None,
) -> None:
    """Seed build-queue.json with a single active entry (optionally + waiters).

    ``active_since=None`` writes an entry with NO active_since key — the
    pre-existing-entry case (written before D5 shipped).
    """
    entry: dict = {'id': entry_id, 'plan_id': plan_id, 'ts': ts}
    if active_since is not None:
        entry['active_since'] = active_since
    _write_queue(queue_path, {'active': [entry], 'waiting': waiting or [], 'run_log': []})


# A held duration comfortably over 2 × the 600 s default upper-limit (1200 s).
_STALE_AGE_SECONDS = 5000.0


_FRESH_AGE_SECONDS = 10.0
