#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage-locks`` test modules.

Holds the definitions used by modules of MORE THAN ONE unit in this
directory. A definition used by one unit belongs in that unit's own
helper; this file is for what genuinely crosses them.
"""

from __future__ import annotations

from pathlib import Path


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE.

    Liveness is derived from the plan directory existing under the isolated
    base, so staging one is how a test makes a recorded holder count as alive.
    Every unit in this directory that reasons about holder liveness needs it —
    the build queue, the merge lock, its rate window and its conditional
    release — which is what puts it here rather than in one unit's helper.
    """
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


def _write_lock(lock_path: Path, holder: str) -> None:
    """Stage a held lock file recording ``holder`` (mirrors _try_atomic_create)."""
    lock_path.write_text(holder + '\n', encoding='utf-8')
