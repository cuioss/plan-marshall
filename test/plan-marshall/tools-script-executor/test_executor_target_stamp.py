#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Executor target stamp: a foreign-harness run is refused by name (D5).

The generator stamps the generating harness and plugin root into the executor.
The executor compares that stamp with the ambient runtime signal and refuses a
mismatch with ``executor_target_mismatch`` — naming the observed target, the
expected target and the regenerate command — instead of resolving scripts into
another harness's tree. The same executor under its own target runs unchanged.
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


def _env(**signals: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in (*_TARGET_SIGNALS, 'PYTHONPATH')}
    env.update(signals)
    return env


@pytest.fixture()
def stamped_executor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Generate a real OpenCode-stamped executor into a fixture project."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    result = ge.generate_executor({}, MARKETPLACE_ROOT, dry_run=False, target='opencode')
    assert result['status'] == 'success', result
    executor = plan_dir / 'execute-script.py'
    assert executor.is_file()
    return executor


def _run(executor: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(executor), '--list'],
        cwd=executor.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_generator_stamps_target_and_plugin_root(stamped_executor: Path) -> None:
    text = stamped_executor.read_text(encoding='utf-8')
    assert "_EXECUTOR_TARGET = 'opencode'" in text
    assert "EXECUTOR_PLUGIN_ROOT = ''" not in text


def test_a_foreign_harness_is_refused_by_name(stamped_executor: Path) -> None:
    result = _run(stamped_executor, _env(CLAUDE_CODE_SESSION_ID='fixture'))

    assert result.returncode != 0
    assert 'executor_target_mismatch' in result.stdout
    assert 'observed_target' in result.stdout and 'claude' in result.stdout
    assert 'expected_target' in result.stdout and 'opencode' in result.stdout
    assert 'regenerate_command' in result.stdout
    assert '--target claude' in result.stdout


def test_the_own_harness_runs_unchanged(stamped_executor: Path) -> None:
    result = _run(stamped_executor, _env(OPENCODE='1'))

    assert result.returncode == 0
    assert 'executor_target_mismatch' not in result.stdout
