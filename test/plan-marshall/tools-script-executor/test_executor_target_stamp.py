#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The executor's harness stamp is informational, never a lock (LB-94 D1/D2).

The PLAN-LB-43 D5 contract this file used to assert — "a foreign harness run is
refused by name with ``executor_target_mismatch``" — is retired. One executor
serves every harness: ``GENERATED_FOR`` is a fixed sentinel (never a harness
name), and a call from any harness dispatches.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

ge = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py')

_TARGET_SIGNALS = ('ANTIGRAVITY_AGENT', 'OPENCODE', 'CLAUDE_CODE_SESSION_ID')


def _env(signal: str | None = None) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in (*_TARGET_SIGNALS, 'PYTHONPATH')}
    if signal is not None:
        env[signal] = '1'
    return env


@pytest.fixture()
def stamped_executor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Generate a real executor into a fixture project."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    result = ge.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='opencode')
    assert result['status'] == 'success', result
    executor = plan_dir / 'execute-script.py'
    assert executor.is_file()
    return executor


def _run(executor: Path, env: dict[str, str], args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(executor), *(args if args is not None else ['--list'])],
        cwd=executor.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_generator_stamps_a_target_independent_identity(stamped_executor: Path) -> None:
    text = stamped_executor.read_text(encoding='utf-8')

    assert "GENERATED_FOR = 'any'" in text
    assert '_EXECUTOR_TARGET' not in text
    assert "EXECUTOR_PLUGIN_ROOT = ''" not in text


@pytest.mark.parametrize('signal', _TARGET_SIGNALS, ids=_TARGET_SIGNALS)
def test_every_harness_runs_the_same_executor_by_name(stamped_executor: Path, signal: str) -> None:
    """No harness is refused: every signal lists the notation set and exits 0."""
    result = _run(stamped_executor, _env(signal))

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'executor_target_mismatch' not in result.stdout
    assert 'executor_target_mismatch' not in result.stderr


def test_a_plain_terminal_caller_still_runs(stamped_executor: Path) -> None:
    result = _run(stamped_executor, _env())

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_recovery_command_names_the_running_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The printed recovery command carries the runtime harness as a hint only."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    assert ge.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='opencode')['status'] == 'success'

    source = (plan_dir / 'execute-script.py').read_text(encoding='utf-8')
    assert 'def _recovery_command(' in source
    # The target is read from the runtime harness, not from the retired stamp.
    assert 'resolved_target = target or _runtime_harness()' in source
