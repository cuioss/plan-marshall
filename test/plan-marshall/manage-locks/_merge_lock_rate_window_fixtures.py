#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``merge lock rate window`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
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
