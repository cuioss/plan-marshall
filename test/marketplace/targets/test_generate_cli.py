"""CLI smoke tests for marketplace/targets/generate.py."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATE_SCRIPT = PROJECT_ROOT / 'marketplace' / 'targets' / 'generate.py'


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=30,
    )


class TestGenerateCli:
    """Smoke-level checks for the generate.py CLI entry point."""

    def test_help_prints_usage_and_exits_zero(self):
        result = _run_cli('--help')
        assert result.returncode == 0
        assert '--target' in result.stdout
        assert 'claude' in result.stdout
        assert 'opencode' in result.stdout

    def test_unknown_target_exits_two(self):
        result = _run_cli('--target', 'nope', '--output', '/tmp/does-not-matter')
        assert result.returncode == 2
        assert 'invalid choice' in (result.stderr + result.stdout)

    def test_missing_target_exits_two(self):
        result = _run_cli('--output', '/tmp/does-not-matter')
        assert result.returncode == 2

    def test_claude_target_known_choice(self, tmp_path):
        # CLI accepts the choice and the claude target generates output successfully.
        out = tmp_path / 'claude-out'
        result = _run_cli('--target', 'claude', '--output', str(out))
        assert result.returncode == 0, result.stderr
        assert 'claude' in result.stdout

    def test_opencode_target_known_choice(self, tmp_path):
        out = tmp_path / 'opencode-out'
        result = _run_cli('--target', 'opencode', '--output', str(out))
        assert result.returncode == 0, result.stderr
        assert 'opencode' in result.stdout

    def test_all_target_known_choice(self, tmp_path):
        out = tmp_path / 'all-out'
        result = _run_cli('--target', 'all', '--output', str(out))
        assert result.returncode == 0, result.stderr

    def test_malformed_bundles_only_whitespace(self, tmp_path):
        # Empty/whitespace bundles parses to None — runs all bundles successfully.
        out = tmp_path / 'claude-out'
        result = _run_cli('--target', 'claude', '--output', str(out), '--bundles', '   ')
        assert result.returncode == 0, result.stderr

    def test_marketplace_dir_must_exist(self):
        result = _run_cli(
            '--target',
            'claude',
            '--marketplace-dir',
            '/path/that/should/not/exist/9999',
        )
        assert result.returncode == 2
        assert 'marketplace directory not found' in result.stderr
