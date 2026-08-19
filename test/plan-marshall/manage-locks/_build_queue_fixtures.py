#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``build queue`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json
import subprocess

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``build_queue`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``build_queue`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``build_queue`` never sees).
import sys as _sys  # noqa: E402
from pathlib import Path

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'build_queue.py')


build_queue = load_script_module('plan-marshall', 'manage-locks', 'build_queue.py', 'build_queue_under_test')


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
