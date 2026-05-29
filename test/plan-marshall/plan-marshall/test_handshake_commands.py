#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for _handshake_commands helper-based executor resolution.

``_handshake_commands._load_status_metadata`` reads ``status.json`` metadata
by spawning ``manage-status read`` through the canonical executor proxy. The
executor path is resolved via ``file_ops.get_executor_path()`` (worktree-safe
resolution anchored on ``git rev-parse --git-common-dir``) rather than via
parent-arithmetic on ``__file__``. These tests pin three contracts:

1. When the resolved executor exists, its absolute path is forwarded into the
   spawned subprocess argv and the parsed ``plan.metadata`` is returned.
2. When ``get_executor_path`` raises ``RuntimeError`` (no git repo), the
   helper degrades to an empty metadata dict without spawning a subprocess.
3. When the resolved executor does not exist on disk, the helper degrades to
   an empty metadata dict without spawning a subprocess.

The shared module loader / fixtures live in ``_handshake_fixtures.py`` (a
sibling ``_fixtures``-style module — never a sibling ``conftest.py`` — so the
top-level ``test/conftest.py`` is not shadowed).
"""

from __future__ import annotations

from pathlib import Path

from _handshake_fixtures import cmds


def test_load_status_metadata_uses_resolved_executor(tmp_path, monkeypatch):
    """The helper-resolved executor path is forwarded into the spawned argv."""
    executor = tmp_path / 'execute-script.py'
    executor.write_text('# executor\n')
    captured = {}

    def fake_run(cmd, *args, **kwargs):
        captured['cmd'] = cmd

        class _Proc:
            returncode = 0
            stdout = 'plan:\n  metadata:\n    use_worktree: true\n'
            stderr = ''

        return _Proc()

    monkeypatch.setattr(cmds, 'get_executor_path', lambda: executor)
    monkeypatch.setattr(cmds.subprocess, 'run', fake_run)

    metadata = cmds._load_status_metadata('test-plan')

    assert metadata == {'use_worktree': True}
    assert str(executor) in captured['cmd']


def test_load_status_metadata_empty_when_helper_raises(monkeypatch):
    """RuntimeError from get_executor_path → empty dict, no subprocess spawn."""
    def _raise() -> Path:
        raise RuntimeError('no git repository')

    def _should_not_run(*args, **kwargs):
        raise AssertionError('subprocess.run must not be called when no executor')

    monkeypatch.setattr(cmds, 'get_executor_path', _raise)
    monkeypatch.setattr(cmds.subprocess, 'run', _should_not_run)

    metadata = cmds._load_status_metadata('test-plan')

    assert metadata == {}


def test_load_status_metadata_empty_when_executor_missing(tmp_path, monkeypatch):
    """A resolved-but-missing executor → empty dict, no subprocess spawn."""
    missing = tmp_path / 'execute-script.py'  # never created

    def _should_not_run(*args, **kwargs):
        raise AssertionError('subprocess.run must not be called for a missing executor')

    monkeypatch.setattr(cmds, 'get_executor_path', lambda: missing)
    monkeypatch.setattr(cmds.subprocess, 'run', _should_not_run)

    metadata = cmds._load_status_metadata('test-plan')

    assert metadata == {}
