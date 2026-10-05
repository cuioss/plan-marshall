# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI and unit tests for marketplace/targets/sync.py.

The all-targets runs point ``HOME`` at a per-test directory, so the three
default install locations resolve inside the sandbox and no run can reach
a real harness install.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import PROJECT_ROOT, ScriptResult, run_script
from marketplace.targets.sync import SYNC_TARGETS, TARGET_CONFIGS, sync_target

SYNC_SCRIPT = PROJECT_ROOT / 'marketplace' / 'targets' / 'sync.py'

ALL_TARGETS = ['claude', 'opencode', 'antigravity']


def _run_cli(*args: str, cwd: Path | None = None, home: Path | None = None) -> ScriptResult:
    return run_script(
        SYNC_SCRIPT,
        *args,
        cwd=cwd or PROJECT_ROOT,
        timeout=60,
        env_overrides={'HOME': str(home)} if home is not None else None,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _make_claude_tree(project: Path) -> None:
    plugin_doc = json.dumps({'name': 'demo', 'version': '0.1.0'}) + '\n'
    _write(project / 'target' / 'claude' / 'demo' / '.claude-plugin' / 'plugin.json', plugin_doc)
    _write(project / 'target' / 'claude' / 'demo' / 'README.md', '# demo\n')


def _make_opencode_tree(project: Path) -> None:
    _write(project / 'target' / 'opencode' / 'skill' / 'demo-skill' / 'SKILL.md', '---\nname: demo-skill\n---\n')


def _make_antigravity_tree(project: Path) -> None:
    _write(project / 'target' / 'antigravity' / 'skills' / 'demo-skill' / 'SKILL.md', '---\nname: demo-skill\n---\n')


@pytest.fixture
def sandbox(tmp_path: Path) -> tuple[Path, Path]:
    """An empty project directory and a sandboxed ``HOME``."""
    project = tmp_path / 'project'
    project.mkdir()
    home = tmp_path / 'home'
    home.mkdir()
    return project, home


class TestSyncCli:
    """CLI smoke tests for sync.py entrypoint."""

    def test_help_prints_usage_and_exits_zero(self):
        result = _run_cli('--help')
        assert result.returncode == 0
        assert '--target' in result.stdout
        assert 'claude' in result.stdout
        assert 'antigravity' in result.stdout
        assert 'opencode' in result.stdout

    def test_unknown_target_exits_two(self):
        result = _run_cli('--target', 'unknown-target')
        assert result.returncode == 2

    @pytest.mark.parametrize(
        'argv',
        [
            ['--source', '/nonexistent-source'],
            ['--target-dir', '/nonexistent-dest'],
            ['--target', 'claude', '--target-dir', '/nonexistent-dest'],
            ['--target', 'opencode', '--cache-root', '/nonexistent-cache'],
            ['--target', 'antigravity', '--from-worktree', '/nonexistent-worktree'],
            ['--target', 'opencode', '--skip-staleness-guard'],
        ],
        ids=[
            'source-without-target',
            'target-dir-without-target',
            'target-dir-with-claude',
            'cache-root-with-opencode',
            'from-worktree-with-antigravity',
            'skip-guard-with-opencode',
        ],
    )
    def test_flag_that_would_be_ignored_is_rejected(self, argv: list[str], sandbox: tuple[Path, Path]):
        project, home = sandbox

        result = _run_cli(*argv, cwd=project, home=home)

        assert result.returncode == 2
        assert result.stdout == ''


class TestSyncAllTargets:
    """A run with no ``--target`` attempts every harness and aggregates."""

    def test_run_without_target_attempts_all_three_and_reports_error_when_none_succeed(
        self, sandbox: tuple[Path, Path]
    ):
        project, home = sandbox

        result = _run_cli(cwd=project, home=home)

        assert result.returncode == 1
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert [row['target'] for row in data['targets']] == ALL_TARGETS
        assert [row['status'] for row in data['targets']] == ['error', 'error', 'error']
        for name in ALL_TARGETS:
            assert data[name]['status'] == 'error'
            assert data[name]['summary_message']

    def test_all_targets_succeeding_reports_success_and_syncs_each_install(self, sandbox: tuple[Path, Path]):
        project, home = sandbox
        _make_claude_tree(project)
        _make_opencode_tree(project)
        _make_antigravity_tree(project)

        result = _run_cli('--skip-staleness-guard', cwd=project, home=home)

        assert result.returncode == 0, result.stdout
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert [row['status'] for row in data['targets']] == ['success', 'success', 'success']
        assert int(data['claude']['synced_count']) == 1
        assert int(data['opencode']['skills_count']) == 1
        assert int(data['antigravity']['skills_count']) == 1
        assert (home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / 'demo' / '0.1.0' / 'README.md').is_file()
        assert (home / '.config' / 'opencode' / 'skills' / 'demo-skill' / 'SKILL.md').is_file()
        assert (
            home / '.gemini' / 'config' / 'plugins' / 'plan-marshall' / 'skills' / 'demo-skill' / 'SKILL.md'
        ).is_file()

    def test_later_targets_are_attempted_after_an_earlier_one_fails(self, sandbox: tuple[Path, Path]):
        project, home = sandbox
        # No target/claude/ — the first target in the fixed order fails.
        _make_opencode_tree(project)
        _make_antigravity_tree(project)

        result = _run_cli(cwd=project, home=home)

        assert result.returncode == 1
        data = parse_toon(result.stdout)
        assert data['status'] == 'partial'
        assert [(row['target'], row['status']) for row in data['targets']] == [
            ('claude', 'error'),
            ('opencode', 'success'),
            ('antigravity', 'success'),
        ]
        assert data['claude']['guard_outcome'] == 'stale'
        assert (home / '.config' / 'opencode' / 'skills' / 'demo-skill' / 'SKILL.md').is_file()

    def test_dry_run_writes_nothing_for_any_target(self, sandbox: tuple[Path, Path]):
        project, home = sandbox
        _make_claude_tree(project)
        _make_opencode_tree(project)
        _make_antigravity_tree(project)

        result = _run_cli('--dry-run', '--skip-staleness-guard', cwd=project, home=home)

        assert result.returncode == 0, result.stdout
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        for name in ALL_TARGETS:
            assert data[name]['dry_run'] is True
        assert int(data['claude']['synced_count']) == 0
        assert list(home.iterdir()) == []


class TestSyncEngineUnit:
    """Unit tests for TargetSyncConfig and sync_target function."""

    def test_registered_targets(self):
        assert list(SYNC_TARGETS) == ALL_TARGETS
        assert 'antigravity' in TARGET_CONFIGS
        assert 'opencode' in TARGET_CONFIGS

    def test_sync_target_unknown_target(self):
        buf = io.StringIO()
        exit_code = sync_target('non-existent', stdout=buf)
        assert exit_code == 1
        data = parse_toon(buf.getvalue())
        assert data['status'] == 'error'
        assert 'unknown target' in data['summary_message']
