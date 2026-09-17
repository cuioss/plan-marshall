# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI and unit tests for marketplace/targets/sync.py."""

from __future__ import annotations

import io
from pathlib import Path

from toon_parser import parse_toon

from conftest import PROJECT_ROOT, ScriptResult, run_script
from marketplace.targets.sync import TARGET_CONFIGS, sync_target

SYNC_SCRIPT = PROJECT_ROOT / 'marketplace' / 'targets' / 'sync.py'


def _run_cli(*args: str, cwd: Path | None = None) -> ScriptResult:
    return run_script(
        SYNC_SCRIPT,
        *args,
        cwd=cwd or PROJECT_ROOT,
        timeout=60,
    )


class TestSyncCli:
    """CLI smoke tests for sync.py entrypoint."""

    def test_help_prints_usage_and_exits_zero(self):
        result = _run_cli('--help')
        assert result.returncode == 0
        assert '--target' in result.stdout
        assert 'antigravity' in result.stdout
        assert 'opencode' in result.stdout

    def test_missing_target_exits_two(self):
        result = _run_cli('--source', '/tmp/source', '--target-dir', '/tmp/dest')
        assert result.returncode == 2

    def test_unknown_target_exits_two(self):
        result = _run_cli('--target', 'unknown-target')
        assert result.returncode == 2


class TestSyncEngineUnit:
    """Unit tests for TargetSyncConfig and sync_target function."""

    def test_registered_targets(self):
        assert 'antigravity' in TARGET_CONFIGS
        assert 'opencode' in TARGET_CONFIGS

    def test_sync_target_unknown_target(self):
        buf = io.StringIO()
        exit_code = sync_target('non-existent', stdout=buf)
        assert exit_code == 1
        data = parse_toon(buf.getvalue())
        assert data['status'] == 'error'
        assert 'unknown target' in data['summary_message']
