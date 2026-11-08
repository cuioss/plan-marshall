# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI smoke tests for marketplace/targets/generate.py."""

import json

from conftest import PROJECT_ROOT, ScriptResult, run_script

GENERATE_SCRIPT = PROJECT_ROOT / 'marketplace' / 'targets' / 'generate.py'


def _run_cli(*args: str) -> ScriptResult:
    return run_script(
        GENERATE_SCRIPT,
        *args,
        cwd=PROJECT_ROOT,
        # A full --output run now discovers scripts and materializes the default
        # config to compute the dist-manifest fingerprints, so the emit path does
        # more work than the pure equality check — give it generous headroom.
        timeout=180,
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

    def test_a_bundle_tree_target_emits_no_packs_directory(self, tmp_path):
        """A ``packs/`` directory belongs to no registered target any more."""
        out = tmp_path / 'opencode-packs-out'

        result = _run_cli('--target', 'opencode', '--output', str(out))

        assert result.returncode == 0, result.stderr
        assert not (out / 'packs').exists()

    def test_all_target_known_choice(self, tmp_path):
        out = tmp_path / 'all-out'
        result = _run_cli('--target', 'all', '--output', str(out))
        assert result.returncode == 0, result.stderr
        # --target all fans out one sub-directory per registered target, and it
        # reaches the post-emit path for every one of them.
        assert (out / 'claude' / 'dist-manifest.json').is_file()
        assert list((out / 'claude').glob('*/.claude-plugin/plugin.json'))

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


class TestDeterministicVersion:
    """The deterministic 0.1.N version + dist-manifest emission on the --output path."""

    def test_version_override_stamps_manifest_and_bundle_plugins(self, tmp_path):
        """--version wins verbatim: it lands in the dist-manifest and every bundle plugin.json."""
        out = tmp_path / 'claude-out'

        result = _run_cli('--target', 'claude', '--output', str(out), '--version', '0.1.999')

        assert result.returncode == 0, result.stderr
        manifest = json.loads((out / 'dist-manifest.json').read_text())
        assert manifest['version'] == '0.1.999'
        # every target-tree bundle plugin.json is stamped with the override version
        plugin_jsons = list(out.glob('*/.claude-plugin/plugin.json'))
        assert plugin_jsons, 'expected bundle plugin.json files in the generated target tree'
        for plugin_json in plugin_jsons:
            assert json.loads(plugin_json.read_text())['version'] == '0.1.999'

    def test_same_sha_yields_identical_version(self, tmp_path):
        """Two runs on the same source sha produce an identical deterministic version."""
        out1 = tmp_path / 'out1'
        out2 = tmp_path / 'out2'

        r1 = _run_cli('--target', 'claude', '--output', str(out1))
        r2 = _run_cli('--target', 'claude', '--output', str(out2))

        assert r1.returncode == 0, r1.stderr
        assert r2.returncode == 0, r2.stderr
        v1 = json.loads((out1 / 'dist-manifest.json').read_text())['version']
        v2 = json.loads((out2 / 'dist-manifest.json').read_text())['version']
        assert v1 == v2, 'the same source sha must yield an identical version'
        # the computed version is the deterministic 0.1.N shape
        assert v1.startswith('0.1.'), f'expected a 0.1.N version, got {v1!r}'

    def test_dist_manifest_carries_all_six_fields(self, tmp_path):
        """The emitted dist-manifest.json carries the full six-field schema."""
        out = tmp_path / 'claude-out'

        result = _run_cli('--target', 'claude', '--output', str(out))

        assert result.returncode == 0, result.stderr
        manifest = json.loads((out / 'dist-manifest.json').read_text())
        assert set(manifest.keys()) == {
            'version',
            'source_sha',
            'executor_scripts_fingerprint',
            'executor_changed_at_version',
            'config_seed_fingerprint',
            'config_changed_at_version',
        }
