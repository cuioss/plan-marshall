#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage locks merge lock`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import json

# The shared core owns the [LOCK]-log resolver and the best-effort emission
# swallow. ``merge_lock`` does ``from _locks_core import log_lock_event``, so the
# function closes over the _locks_core module that ``merge_lock`` imported — that
# SAME module instance is recovered from the function's ``__module__`` (NOT a
# fresh ``load_script_module`` copy, which would be a different instance whose
# patches ``merge_lock`` never sees).
import sys as _sys  # noqa: E402
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-locks', 'merge_lock.py')


merge_lock = load_script_module('plan-marshall', 'manage-locks', 'merge_lock.py', 'merge_lock_under_test')


# Capture the REAL _push_title_token before the autouse _TokenRecorder stub
# replaces it, so the canonical-seam CLI-shape test below can exercise the
# actual icon-optional push wrapper (it resolves _run_executor as a module
# global, so a monkeypatch on merge_lock._run_executor still takes effect).
_REAL_PUSH_TITLE_TOKEN = merge_lock._push_title_token


# Same rationale for the set/clear wrappers: the owner-scoping tests below must
# exercise the REAL wrappers to observe the constructed argv, not the autouse
# _TokenRecorder stubs that replace them for every other test.
_REAL_SET_TITLE_TOKEN = merge_lock._set_title_token


_REAL_CLEAR_TITLE_TOKEN = merge_lock._clear_title_token


_locks_core = _sys.modules[merge_lock.log_lock_event.__module__]


def _read_lock_log() -> str:
    """Read the main-anchored [LOCK] log, '' when no emission landed yet."""
    log_path = _locks_core._resolve_lock_log_path()
    if not log_path.exists():
        return ''
    return str(log_path.read_text(encoding='utf-8'))


def _read_queue(queue_path: Path) -> dict:
    """Read the persisted FIFO merge-queue state as a dict ('{}' when absent)."""
    if not queue_path.exists():
        return {}
    data: dict = json.loads(queue_path.read_text(encoding='utf-8'))
    return data


def _waiting_plan_ids(queue_path: Path) -> list[str]:
    """Return the FIFO ``waiting`` plan_ids in stored (serialized arrival / list) order."""
    return [e['plan_id'] for e in _read_queue(queue_path).get('waiting', [])]


def _make_live_plan(base: Path, plan_id: str) -> None:
    """Create a holder plan directory so the holder counts as LIVE."""
    (base / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)


class _TokenRecorder:
    """Records the best-effort title-token set/clear/push calls so a test can
    assert WHAT was surfaced without spawning the real executor subprocess.

    Installed over the three module-level seams ``_set_title_token`` /
    ``_clear_title_token`` / ``_push_title_token`` — the same seam-mock approach
    used by ``test_build_queue.py`` for the D6 wrapper.
    """

    def __init__(self) -> None:
        self.set_states: list[str] = []
        self.cleared: list[str] = []
        self.pushed_icons: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(merge_lock, '_set_title_token', lambda _p, state: self.set_states.append(state))
        monkeypatch.setattr(merge_lock, '_clear_title_token', lambda p: self.cleared.append(p))
        # icon is optional: a glyph push (acquire) records the icon; a plain
        # icon-less repaint (the clear path) records None.
        monkeypatch.setattr(
            merge_lock, '_push_title_token', lambda _p, icon=None: self.pushed_icons.append(icon)
        )
