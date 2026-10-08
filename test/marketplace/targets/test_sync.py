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
from marketplace.targets.sync import (
    SYNC_TARGETS,
    TARGET_CONFIGS,
    _build_parser,
    _sync_one_for_aggregate,
    sync_target,
)

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


def _pin_registry(home: Path, version: str) -> Path:
    """Write the sandboxed home's plugin registry, pinning ``demo`` at ``version``.

    The path is the registry's default location under ``home``, which is where
    an all-targets run reads it when ``HOME`` points at the sandbox.
    """
    plugins_dir = home / '.claude' / 'plugins'
    entry = {
        'scope': 'user',
        'installPath': str(plugins_dir / 'cache' / 'plan-marshall' / 'demo' / version),
        'version': version,
    }
    registry = plugins_dir / 'installed_plugins.json'
    _write(registry, json.dumps({'version': 2, 'plugins': {'demo@plan-marshall': [entry]}}) + '\n')
    return registry


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
            ['--target', 'opencode', '--repin'],
            ['--target', 'antigravity', '--repin'],
            ['--target', 'opencode', '--registry-path', '/nonexistent-registry'],
            ['--target', 'antigravity', '--registry-path', '/nonexistent-registry'],
        ],
        ids=[
            'source-without-target',
            'target-dir-without-target',
            'target-dir-with-claude',
            'cache-root-with-opencode',
            'from-worktree-with-antigravity',
            'skip-guard-with-opencode',
            'repin-with-opencode',
            'repin-with-antigravity',
            'registry-path-with-opencode',
            'registry-path-with-antigravity',
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
        # The Claude leg was refused by the staleness guard: nothing was synced,
        # so the cache outcome is an error and there is no version to judge a
        # registry against.
        assert data['claude']['cache_status'] == 'error'
        assert 'registry_parity' not in data['claude']

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
        # The sandboxed home holds no plugin registry: parity is unreadable,
        # which is reported and leaves the Claude leg green.
        assert data['claude']['cache_status'] == 'success'
        assert data['claude']['registry_parity']['verdict'] == 'unreadable'
        assert data['claude']['registry_parity']['registry_state'] == 'absent'
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

    def test_registry_behind_makes_the_claude_row_partial_and_the_run_exit_nonzero(self, sandbox: tuple[Path, Path]):
        """A registry pinned behind the synced tree is not a green all-targets run.

        Every cache and component tree synced, so ``cache_status`` is
        ``success`` and the other two harnesses are green; the Claude row is
        ``partial`` because a restarted session would still load the old pin.
        """
        project, home = sandbox
        _make_claude_tree(project)
        _make_opencode_tree(project)
        _make_antigravity_tree(project)
        registry = _pin_registry(home, '0.0.9')
        before = registry.read_bytes()

        result = _run_cli('--skip-staleness-guard', cwd=project, home=home)

        assert result.returncode == 1, result.stdout
        data = parse_toon(result.stdout)
        assert data['status'] == 'partial'
        assert [(row['target'], row['status']) for row in data['targets']] == [
            ('claude', 'partial'),
            ('opencode', 'success'),
            ('antigravity', 'success'),
        ]
        assert (data['claude']['status'], data['claude']['cache_status']) == ('partial', 'success')
        assert data['claude']['registry_parity']['verdict'] == 'behind'
        for named in ('pinned 0.0.9', 'synced 0.1.0', 'registry_pin.py --apply'):
            assert named in data['claude']['summary_message']
        assert registry.read_bytes() == before

    def test_registry_ahead_leaves_the_claude_block_green_and_the_run_exit_zero(self, sandbox: tuple[Path, Path]):
        """CONTROL: a pin newer than the synced tree is reported and is not red."""
        project, home = sandbox
        _make_claude_tree(project)
        _make_opencode_tree(project)
        _make_antigravity_tree(project)
        _pin_registry(home, '0.2.0')

        result = _run_cli('--skip-staleness-guard', cwd=project, home=home)

        assert result.returncode == 0, result.stdout
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert (data['claude']['status'], data['claude']['cache_status']) == ('success', 'success')
        assert data['claude']['registry_parity']['verdict'] == 'ahead'

    def test_targets_table_keeps_exactly_its_three_columns(self, sandbox: tuple[Path, Path]):
        """``cache_status`` and ``registry_parity`` live in the Claude block, not in the table."""
        project, home = sandbox
        _make_claude_tree(project)
        _make_opencode_tree(project)
        _make_antigravity_tree(project)
        _pin_registry(home, '0.0.9')

        result = _run_cli('--skip-staleness-guard', cwd=project, home=home)

        assert 'targets[3]{target,status,summary_message}:' in result.stdout.splitlines()
        data = parse_toon(result.stdout)
        assert [sorted(row) for row in data['targets']] == [['status', 'summary_message', 'target']] * 3

    @pytest.mark.parametrize(
        ('target_name', 'raising_seam', 'expected_keys'),
        [
            ('claude', '_load_cache_sync_module', ['cache_status', 'status', 'summary_message']),
            ('opencode', '_deploy_target', ['status', 'summary_message']),
        ],
        ids=['claude-block-carries-cache-status', 'component-tree-block-does-not'],
    )
    def test_filesystem_fault_in_one_leg_is_recorded_as_that_legs_error_block(
        self, target_name: str, raising_seam: str, expected_keys: list[str], monkeypatch: pytest.MonkeyPatch
    ):
        def _raise(*_args: object, **_kwargs: object) -> None:
            raise PermissionError('denied')

        monkeypatch.setattr(f'marketplace.targets.sync.{raising_seam}', _raise)

        block = _sync_one_for_aggregate(target_name, _build_parser().parse_args([]))

        assert sorted(block) == expected_keys
        assert block['status'] == 'error'
        assert block.get('cache_status') == ('error' if target_name == 'claude' else None)
        assert 'PermissionError: denied' in block['summary_message']


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


def _make_generated_skill(source: Path, target_name: str) -> Path:
    """Build a generated skill holding a non-standard subdirectory and a loose root file."""
    skill = source / TARGET_CONFIGS[target_name].source_skills_dir / 'demo-skill'
    _write(skill / 'SKILL.md', '---\nname: demo-skill\n---\n')
    _write(skill / 'workflow' / 'x.md', '# x\n')
    _write(skill / 'notes.txt', 'loose\n')
    return skill


def _deploy(target_name: str, source: Path, dest: Path, *, dry_run: bool = False) -> None:
    exit_code = sync_target(target_name, source=source, dest=dest, dry_run=dry_run, stdout=io.StringIO())
    assert exit_code == 0


def _tree(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob('*'))


@pytest.mark.parametrize('target_name', ['opencode', 'antigravity'])
class TestDeploySkillMirror:
    """The deploy step installs the generated skill directory as it is, and nothing else."""

    def test_every_subdirectory_and_loose_file_of_a_generated_skill_is_installed(
        self, target_name: str, tmp_path: Path
    ):
        source, dest = tmp_path / 'source', tmp_path / 'dest'
        _make_generated_skill(source, target_name)

        _deploy(target_name, source, dest)

        assert _tree(dest / 'skills' / 'demo-skill') == ['SKILL.md', 'notes.txt', 'workflow', 'workflow/x.md']
        assert (dest / 'skills' / 'demo-skill' / 'workflow' / 'x.md').read_text(encoding='utf-8') == '# x\n'

    def test_subdirectory_removed_from_the_generated_skill_is_removed_from_the_install(
        self, target_name: str, tmp_path: Path
    ):
        source, dest = tmp_path / 'source', tmp_path / 'dest'
        skill = _make_generated_skill(source, target_name)
        _deploy(target_name, source, dest)
        (skill / 'workflow' / 'x.md').unlink()
        (skill / 'workflow').rmdir()
        (skill / 'notes.txt').unlink()

        _deploy(target_name, source, dest)

        assert not (dest / 'skills' / 'demo-skill' / 'workflow').exists()
        assert _tree(dest / 'skills' / 'demo-skill') == ['SKILL.md']

    def test_dry_run_leaves_the_installed_skill_untouched(self, target_name: str, tmp_path: Path):
        """A dry run neither installs a new file nor removes a stale one."""
        source, dest = tmp_path / 'source', tmp_path / 'dest'
        _make_generated_skill(source, target_name)
        _write(dest / 'skills' / 'demo-skill' / 'SKILL.md', 'installed\n')
        _write(dest / 'skills' / 'demo-skill' / 'stale' / 'old.md', 'stale\n')

        _deploy(target_name, source, dest, dry_run=True)

        assert _tree(dest / 'skills' / 'demo-skill') == ['SKILL.md', 'stale', 'stale/old.md']
        assert (dest / 'skills' / 'demo-skill' / 'SKILL.md').read_text(encoding='utf-8') == 'installed\n'
