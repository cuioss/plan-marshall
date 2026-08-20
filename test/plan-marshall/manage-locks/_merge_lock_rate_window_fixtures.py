#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``merge lock rate window`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for the ``merge_lock.py`` ``rate-window`` verbs — the cross-plan claim on
ONE review bot's rate window, co-tenanting the merge-lock store.

Contract under test (manage-locks/SKILL.md § "The rate window shares the STORE,
never the MUTEX" + § Canonical invocations → ``merge_lock — rate-window {claim,
check,release}``):

* **TOCTOU-safe claim** — the claim mutation runs inside the shared
  :func:`_locks_core.rmw_json` critical section, so N concurrent claimers on the
  same ``bot_kind`` produce exactly ONE holder; the rest are ``blocked``.
* **Idempotent for the self-holder** — a re-claim by the current holder renews the
  same record in place rather than contending or creating a second claim.
* **Holder-liveness reclamation** — a claim whose recorded holder no longer
  corresponds to a live plan is reclaimable (reusing the shared
  :func:`_locks_core.holder_is_dead` predicate); a LIVE holder's unexpired window
  is not.
* **Expiry reclamation** — an elapsed window is reclaimable even when its holder
  is live: the window, not the plan, is what the claim guards.
* **Recursion cap** — a plan may generate at most ``attempt_cap`` recovery events
  per bot per PR; the attempt past the cap is REFUSED with an explicit
  ``recovery_cap_exhausted`` verdict and mutates nothing. The counter is scoped to
  ``(bot_kind, pr_number)`` and SURVIVES a release, so releasing and re-claiming
  cannot reset the cap.
* **Non-mutating check** — ``check`` never writes the store; it reports the
  window's own observable state (``expired`` / ``seconds_remaining``), which is
  what the recovery sequence polls between paced sleeps and what gates the
  trigger-comment fallback.
* **Store co-tenancy, NOT mutex coupling** — a rate-window claim leaves the
  ``waiting`` FIFO list and ``merge.lock`` untouched, and a merge acquire/release
  round-trip leaves ``rate_windows`` intact (the sibling-key-preservation
  invariant; its merge-side half lives in
  ``test_manage_locks_merge_lock.py``).
* **Degraded-state tolerance** — a corrupt or absent ``rate_windows`` value
  degrades to an empty mapping and is rebuilt rather than crashing.

Isolation: every test runs against an isolated ``PLAN_BASE_DIR`` staged under
``tmp_path`` so the suite never contends for the real
``.plan/local/merge-queue.json`` under ``-n auto``.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

merge_lock = load_script_module(
    'plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_rate_window_under_test'
)


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _read_store(queue_path: Path) -> dict:
    """Read the persisted merge-queue store as a dict ('{}' when absent)."""
    if not queue_path.exists():
        return {}
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


def _claim(
    plan_id: str, bot_kind: str = 'coderabbit', pr_number: int = 42, window_seconds: float = 3600.0
) -> dict:
    result: dict = merge_lock.run_rate_window(
        Namespace(
            action='claim',
            plan_id=plan_id,
            bot_kind=bot_kind,
            pr_number=pr_number,
            window_seconds=window_seconds,
        )
    )
    return result


def _check(plan_id: str, bot_kind: str = 'coderabbit') -> dict:
    result: dict = merge_lock.run_rate_window(
        Namespace(action='check', plan_id=plan_id, bot_kind=bot_kind)
    )
    return result


def _release(plan_id: str, bot_kind: str = 'coderabbit') -> dict:
    result: dict = merge_lock.run_rate_window(
        Namespace(action='release', plan_id=plan_id, bot_kind=bot_kind)
    )
    return result
