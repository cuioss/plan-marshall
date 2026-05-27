#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Shared imports, module loaders, and fixtures for phase_handshake test splits.

Sibling helper module imported explicitly by every per-section
test_phase_handshake_*.py file. This avoids a sibling conftest.py that
would shadow the top-level test/conftest.py.

The imports below mirror the original test_phase_handshake.py prologue,
including the sys.path manipulation needed to load the
``_git_helpers`` / ``_handshake_store`` / ``_handshake_commands`` /
``_invariants`` modules that ship under the script directory but are
not on PYTHONPATH at test-collection time.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _git_helpers as git_helpers  # noqa: E402, F401
import _handshake_commands as cmds  # noqa: E402
import _handshake_store as store  # noqa: E402, F401
import _invariants as inv  # noqa: E402


# =============================================================================
# Fixtures (pytest discovers these because test files import them with
# ``from _fixtures import ...``; pytest-style fixtures defined in a non-
# conftest module work as long as the test file performs the import).
# =============================================================================


@pytest.fixture
def stubbed_invariants(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Replace INVARIANTS with a deterministic stub set and return a mutable state dict."""
    state: dict[str, object] = {
        'main_sha': 'abc123',
        'main_dirty': 0,
        'worktree_sha': None,
        'worktree_dirty': None,
        'task_state_hash': 'hash-tasks',
        'qgate_open_count': 0,
        'config_hash': 'hash-cfg',
        'pending_tasks_count': 2,
    }

    def always(_pid: str, _md: dict) -> bool:
        return True

    def worktree_applies(_pid: str, md: dict) -> bool:
        return bool(md.get('worktree_path'))

    def make_capture(name: str):
        def _cap(_pid: str, md: dict, _phase: str):
            if name.startswith('worktree') and not md.get('worktree_path'):
                return None
            return state[name]

        return _cap

    stubbed = [
        ('main_sha', always, make_capture('main_sha')),
        ('main_dirty', always, make_capture('main_dirty')),
        ('worktree_sha', worktree_applies, make_capture('worktree_sha')),
        ('worktree_dirty', worktree_applies, make_capture('worktree_dirty')),
        ('task_state_hash', always, make_capture('task_state_hash')),
        ('qgate_open_count', always, make_capture('qgate_open_count')),
        ('config_hash', always, make_capture('config_hash')),
        ('pending_tasks_count', always, make_capture('pending_tasks_count')),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(cmds, 'INVARIANTS', stubbed)
    return state


@pytest.fixture
def stub_metadata(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Replace _load_status_metadata with a mutable dict."""
    md: dict[str, object] = {}
    monkeypatch.setattr(cmds, '_load_status_metadata', lambda _pid: md)
    return md


def _ns(**kwargs) -> types.SimpleNamespace:
    kwargs.setdefault('override', False)
    kwargs.setdefault('reason', None)
    kwargs.setdefault('strict', False)
    return types.SimpleNamespace(**kwargs)


def _write_required_steps(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')


@pytest.fixture
def required_steps_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Install a controllable required-steps.md for phase `5-execute`."""
    f = tmp_path / 'required-steps.md'
    _write_required_steps(f, '- step-a\n- step-b\n')

    def _resolve(phase: str) -> Path | None:
        if phase == '5-execute':
            return f
        return None

    monkeypatch.setattr(inv, '_resolve_required_steps_path', _resolve)
    return f


@pytest.fixture
def only_phase_steps_invariant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace INVARIANTS with just the real phase_steps_complete entry.

    This lets cmd_capture / cmd_verify exercise the real invariant code path
    without the other invariants trying to shell out.
    """
    stubbed = [
        (
            'phase_steps_complete',
            lambda _pid, _md: True,
            inv._capture_phase_steps_complete,
        ),
    ]
    monkeypatch.setattr(inv, 'INVARIANTS', stubbed)
    monkeypatch.setattr(cmds, 'INVARIANTS', stubbed)
