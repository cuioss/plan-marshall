# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the deterministic version + dist-manifest helpers in generate.py.

Covers the pure, git-independent surface:
- int-tuple version comparison (0.1.9 < 0.1.10 and a 0.2 base bump),
- changed_at carry-forward vs bump vs first-publish bootstrap,
- six-field dist-manifest completeness,
- base-version reading, --version resolution, and bundle plugin.json override.
"""

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_generate():
    """Load marketplace/targets/generate.py as an importable module by explicit path."""
    spec = importlib.util.spec_from_file_location(
        'targets_generate_under_test', PROJECT_ROOT / 'marketplace' / 'targets' / 'generate.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generate()


# =============================================================================
# int-tuple version comparison
# =============================================================================


class TestVersionTuple:
    def test_orders_numerically_not_lexically(self):
        # 0.1.9 < 0.1.10 — a lexical compare would wrongly rank '0.1.9' above '0.1.10'
        assert gen._version_tuple('0.1.9') < gen._version_tuple('0.1.10')

    def test_base_bump_orders_above_every_patch(self):
        assert gen._version_tuple('0.2') > gen._version_tuple('0.1.5')
        assert gen._version_tuple('0.2.0') > gen._version_tuple('0.1.99')

    def test_empty_and_unknown_sentinels_are_lowest(self):
        assert gen._version_tuple('') == ()
        assert gen._version_tuple('unknown') == ()
        assert gen._version_tuple('') < gen._version_tuple('0.1.0')

    def test_no_zero_padding_effect(self):
        # int-tuple compare, so 0.1.10 == parsed (0, 1, 10), not a padded string
        assert gen._version_tuple('0.1.10') == (0, 1, 10)


# =============================================================================
# changed_at derivation
# =============================================================================

_EXEC_FP_KEY = 'executor_scripts_fingerprint'
_EXEC_CHANGED_KEY = 'executor_changed_at_version'


class TestDeriveChangedAt:
    def test_first_publish_bootstraps_to_current(self):
        result = gen._derive_changed_at('0.1.10', 'fp-abc', None, _EXEC_FP_KEY, _EXEC_CHANGED_KEY)
        assert result == '0.1.10'

    def test_unchanged_fingerprint_carries_previous_forward(self):
        previous = {_EXEC_FP_KEY: 'fp-abc', _EXEC_CHANGED_KEY: '0.1.3'}
        result = gen._derive_changed_at('0.1.10', 'fp-abc', previous, _EXEC_FP_KEY, _EXEC_CHANGED_KEY)
        assert result == '0.1.3'

    def test_changed_fingerprint_advances_to_current(self):
        previous = {_EXEC_FP_KEY: 'fp-OLD', _EXEC_CHANGED_KEY: '0.1.3'}
        result = gen._derive_changed_at('0.1.10', 'fp-NEW', previous, _EXEC_FP_KEY, _EXEC_CHANGED_KEY)
        assert result == '0.1.10'

    def test_unchanged_but_previous_lacked_changed_at_bootstraps(self):
        previous = {_EXEC_FP_KEY: 'fp-abc'}  # no changed_at key at all
        result = gen._derive_changed_at('0.1.10', 'fp-abc', previous, _EXEC_FP_KEY, _EXEC_CHANGED_KEY)
        assert result == '0.1.10'


# =============================================================================
# dist-manifest completeness + mixed semantics
# =============================================================================

_SIX_FIELDS = {
    'version',
    'source_sha',
    'executor_scripts_fingerprint',
    'executor_changed_at_version',
    'config_seed_fingerprint',
    'config_changed_at_version',
}


class TestBuildDistManifest:
    def test_carries_all_six_fields(self):
        manifest = gen._build_dist_manifest('0.1.10', 'sha123', 'exec-fp', 'config-fp', None)

        assert set(manifest.keys()) == _SIX_FIELDS
        assert manifest['version'] == '0.1.10'
        assert manifest['source_sha'] == 'sha123'
        assert manifest['executor_scripts_fingerprint'] == 'exec-fp'
        assert manifest['config_seed_fingerprint'] == 'config-fp'
        # first publish bootstraps both changed_at to the current version
        assert manifest['executor_changed_at_version'] == '0.1.10'
        assert manifest['config_changed_at_version'] == '0.1.10'

    def test_mixed_changed_at_semantics(self):
        # exec fingerprint unchanged (carries 0.1.2); config fingerprint changed (advances)
        previous = {
            'executor_scripts_fingerprint': 'exec-fp',
            'executor_changed_at_version': '0.1.2',
            'config_seed_fingerprint': 'config-OLD',
            'config_changed_at_version': '0.1.2',
        }

        manifest = gen._build_dist_manifest('0.1.10', 'sha', 'exec-fp', 'config-NEW', previous)

        assert manifest['executor_changed_at_version'] == '0.1.2', 'unchanged executor fp carries forward'
        assert manifest['config_changed_at_version'] == '0.1.10', 'changed config fp advances to current'


# =============================================================================
# base-version reading, version resolution, previous-manifest loading
# =============================================================================


class TestVersionResolution:
    def test_read_base_version_reads_marketplace_metadata(self, tmp_path):
        (tmp_path / '.claude-plugin').mkdir()
        (tmp_path / '.claude-plugin' / 'marketplace.json').write_text(
            json.dumps({'metadata': {'version': '0.1'}}), encoding='utf-8'
        )
        assert gen._read_base_version(tmp_path) == '0.1'

    def test_read_base_version_falls_back_when_manifest_absent(self, tmp_path):
        assert gen._read_base_version(tmp_path) == '0.1'

    def test_read_base_version_falls_back_when_metadata_version_missing(self, tmp_path):
        (tmp_path / '.claude-plugin').mkdir()
        (tmp_path / '.claude-plugin' / 'marketplace.json').write_text(
            json.dumps({'metadata': {}}), encoding='utf-8'
        )
        assert gen._read_base_version(tmp_path) == '0.1'

    def test_resolve_version_explicit_wins_verbatim(self, tmp_path):
        assert gen._resolve_version('0.1.777', '0.1', tmp_path) == '0.1.777'

    def test_load_previous_manifest_none_path_is_first_publish(self):
        assert gen._load_previous_manifest(None) is None

    def test_load_previous_manifest_reads_json(self, tmp_path):
        manifest_path = tmp_path / 'dist-manifest.json'
        manifest_path.write_text(json.dumps({'version': '0.1.5'}), encoding='utf-8')
        loaded = gen._load_previous_manifest(manifest_path)
        assert loaded == {'version': '0.1.5'}

    def test_load_previous_manifest_missing_file_is_none(self, tmp_path):
        assert gen._load_previous_manifest(tmp_path / 'absent.json') is None


# =============================================================================
# bundle plugin.json version override
# =============================================================================


class TestOverrideBundlePluginVersions:
    def test_stamps_version_and_preserves_other_fields(self, tmp_path):
        plugin_dir = tmp_path / 'my-bundle' / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        plugin_json = plugin_dir / 'plugin.json'
        plugin_json.write_text(
            json.dumps({'name': 'my-bundle', 'version': '0.1', 'description': 'x'}), encoding='utf-8'
        )

        count = gen._override_bundle_plugin_versions(tmp_path, '0.1.42')

        assert count == 1
        data = json.loads(plugin_json.read_text())
        assert data['version'] == '0.1.42'
        # every other field is preserved verbatim
        assert data['name'] == 'my-bundle'
        assert data['description'] == 'x'

    def test_overrides_every_bundle_and_counts_them(self, tmp_path):
        for name in ('bundle-a', 'bundle-b', 'bundle-c'):
            plugin_dir = tmp_path / name / '.claude-plugin'
            plugin_dir.mkdir(parents=True)
            (plugin_dir / 'plugin.json').write_text(
                json.dumps({'name': name, 'version': '0.1'}), encoding='utf-8'
            )

        count = gen._override_bundle_plugin_versions(tmp_path, '0.1.5')

        assert count == 3
        for name in ('bundle-a', 'bundle-b', 'bundle-c'):
            data = json.loads((tmp_path / name / '.claude-plugin' / 'plugin.json').read_text())
            assert data['version'] == '0.1.5'
