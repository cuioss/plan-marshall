# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cmd_preflight's multi-version pollution detection and marking.

``generate_executor preflight`` regenerates the executor in place (safe derived
state, ADR-002) when it discovers more than one version dir per bundle in the
plugin-cache context — that pollution otherwise lets an older version's scripts
shadow the current ones on PYTHONPATH. These tests drive the real
``_detect_multi_version_pollution`` detector through ``cmd_preflight`` against
synthetic cache fixtures, with the heavy manifest/generate dependencies mocked
so only the pollution branch is exercised.

They also cover the marking predicate ``_mark_superseded_version_dirs``, whose
contract is that a retention-pinned version — the newest-on-disk, the
``marshal.json``-provisioned, or the manifest-named one — is NEVER marked. That
pin is what makes marker saturation (every dir marked, zero live) structurally
impossible, and therefore what keeps the pollution detector non-vacuous and
``marketplace_bundles.find_bundles`` out of its degraded all-orphaned fallback.
"""

import types

from conftest import load_script_module

gen = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py')


def _make_version_bundle(root, bundle, versions):
    """Create ``root/{bundle}/{version}/skills/demo-skill/scripts`` per version."""
    for version in versions:
        (root / bundle / version / 'skills' / 'demo-skill' / 'scripts').mkdir(parents=True)


def _preflight_args():
    return types.SimpleNamespace(marketplace=False, marketplace_root=None, target=None)


def _stub_preflight_deps(monkeypatch, base_path):
    """Mock the heavy/environmental dependencies of cmd_preflight.

    Leaves ``_detect_multi_version_pollution`` REAL so the pollution branch is
    genuinely exercised against ``base_path``. Returns the list that records
    each ``cmd_generate`` call so a test can assert whether an in-place
    regeneration fired.
    """
    generate_calls: list = []
    monkeypatch.setattr(gen, 'get_base_path', lambda **kwargs: base_path)
    monkeypatch.setattr(gen, 'read_marshal_target', lambda *a, **k: 'claude')
    # Empty manifest → both changed_at sentinels empty → no version-staleness regen,
    # so the ONLY regeneration trigger under test is multi-version pollution.
    monkeypatch.setattr(gen, 'read_installed_manifest', lambda *a, **k: {})
    monkeypatch.setattr(gen, 'read_executor_version', lambda *a, **k: 'unknown')
    monkeypatch.setattr(gen, 'read_marshal_provisioned_version', lambda *a, **k: 'unknown')
    monkeypatch.setattr(gen, 'cmd_generate', lambda args: generate_calls.append(args) or {'status': 'success'})
    return generate_calls


class TestDetectMultiVersionPollution:
    def test_clean_tree_returns_empty(self, tmp_path, monkeypatch):
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.200'])
        assert gen._detect_multi_version_pollution(tmp_path) == []

    def test_single_bundle_multi_version_detected(self, tmp_path):
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200'])
        assert gen._detect_multi_version_pollution(tmp_path) == ['plan-marshall']

    def test_multiple_polluted_bundles_sorted(self, tmp_path):
        _make_version_bundle(tmp_path, 'pm-dev-java', ['0.1.100', '0.1.200'])
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200'])
        # Lexical sort: 'plan-marshall' < 'pm-dev-java' ('l' < 'm' at index 1).
        assert gen._detect_multi_version_pollution(tmp_path) == ['plan-marshall', 'pm-dev-java']

    def test_none_base_path_returns_empty(self):
        assert gen._detect_multi_version_pollution(None) == []


def _stub_pins(monkeypatch, provisioned: str = 'unknown', manifest_version: str = ''):
    """Pin the two non-disk retention inputs so a fixture controls them."""
    monkeypatch.setattr(gen, 'read_marshal_provisioned_version', lambda *a, **k: provisioned)
    manifest = {'version': manifest_version} if manifest_version else {}
    monkeypatch.setattr(gen, 'read_installed_manifest', lambda *a, **k: manifest)


def _marked(root, bundle: str) -> set[str]:
    """Return the names of ``bundle``'s version dirs carrying ``.orphaned_at``."""
    return {d.name for d in (root / bundle).iterdir() if (d / '.orphaned_at').exists()}


def _live(root, bundle: str) -> set[str]:
    """Return the names of ``bundle``'s LIVE (unmarked) version dirs."""
    return {d.name for d in gen._live_version_dirs(root / bundle)}


class TestMarkSupersededVersionDirs:
    def test_newest_on_disk_is_never_marked(self, tmp_path, monkeypatch):
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200', '0.1.300'])
        _stub_pins(monkeypatch)

        gen._mark_superseded_version_dirs(tmp_path, ['plan-marshall'])

        assert '0.1.300' not in _marked(tmp_path, 'plan-marshall')
        assert _marked(tmp_path, 'plan-marshall') == {'0.1.100', '0.1.200'}

    def test_provisioned_version_is_never_marked(self, tmp_path, monkeypatch):
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200', '0.1.300'])
        _stub_pins(monkeypatch, provisioned='0.1.100')

        gen._mark_superseded_version_dirs(tmp_path, ['plan-marshall'])

        assert '0.1.100' not in _marked(tmp_path, 'plan-marshall')

    def test_manifest_named_version_is_never_marked(self, tmp_path, monkeypatch):
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200', '0.1.300'])
        _stub_pins(monkeypatch, manifest_version='0.1.200')

        gen._mark_superseded_version_dirs(tmp_path, ['plan-marshall'])

        assert '0.1.200' not in _marked(tmp_path, 'plan-marshall')

    def test_marker_can_never_saturate_to_zero_live(self, tmp_path, monkeypatch):
        # The observed production defect: repeated marking passes converged on
        # "every dir marked, zero live". With the newest-on-disk pin, at least one
        # live dir survives every pass no matter how many times marking runs.
        _make_version_bundle(tmp_path, 'plan-marshall', [f'0.1.{n}' for n in range(1, 8)])
        _stub_pins(monkeypatch)

        for _ in range(5):
            polluted = gen._detect_multi_version_pollution(tmp_path)
            gen._mark_superseded_version_dirs(tmp_path, polluted)
            assert _live(tmp_path, 'plan-marshall'), 'at least one version dir must remain live'

        assert _live(tmp_path, 'plan-marshall') == {'0.1.7'}

    def test_marking_still_clears_the_pollution_signal(self, tmp_path, monkeypatch):
        # The pin must not defeat the reason marking exists: after one pass the
        # detector reports clean, so the NEXT preflight does not regenerate again.
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200'])
        _stub_pins(monkeypatch)

        gen._mark_superseded_version_dirs(tmp_path, ['plan-marshall'])

        assert gen._detect_multi_version_pollution(tmp_path) == []

    def test_detector_stays_non_vacuous_when_older_dirs_are_marked(self, tmp_path, monkeypatch):
        # A pre-marked older dir does not blind the detector: the two remaining
        # live dirs are still counted and reported as pollution.
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200', '0.1.300'])
        (tmp_path / 'plan-marshall' / '0.1.100' / '.orphaned_at').write_text('2026-01-01T00:00:00Z')
        _stub_pins(monkeypatch)

        assert gen._detect_multi_version_pollution(tmp_path) == ['plan-marshall']

    def test_a_pre_marked_newest_does_not_cascade_to_zero_live(self, tmp_path, monkeypatch):
        # The saturation seed: the newest dir arrives already marked (a legacy
        # pre-fix state). Marking must still leave a live dir behind rather than
        # promoting an older dir and marking everything else.
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200', '0.1.300'])
        (tmp_path / 'plan-marshall' / '0.1.300' / '.orphaned_at').write_text('2026-01-01T00:00:00Z')
        _stub_pins(monkeypatch)

        gen._mark_superseded_version_dirs(tmp_path, ['plan-marshall'])

        assert _live(tmp_path, 'plan-marshall')


class TestPreflightPollution:
    def test_multi_version_fixture_triggers_regeneration(self, tmp_path, monkeypatch):
        # Arrange: a plugin-cache fixture with TWO version dirs for one bundle → pollution.
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.100', '0.1.200'])
        generate_calls = _stub_preflight_deps(monkeypatch, tmp_path)

        # Act
        result = gen.cmd_preflight(_preflight_args())

        # Assert: the pollution branch fired and regenerated the executor in place.
        # Pollution is surfaced through executor_action (six-field TOON contract),
        # not a dedicated output field.
        assert result['status'] == 'success'
        assert result['executor_action'] == 'regenerated'
        assert len(generate_calls) == 1

    def test_single_version_fixture_reports_fresh(self, tmp_path, monkeypatch):
        # Arrange: a single version dir → no pollution, nothing stale.
        _make_version_bundle(tmp_path, 'plan-marshall', ['0.1.200'])
        generate_calls = _stub_preflight_deps(monkeypatch, tmp_path)

        # Act
        result = gen.cmd_preflight(_preflight_args())

        # Assert: clean + fresh, and NO regeneration fired.
        assert result['status'] == 'success'
        assert result['executor_action'] == 'fresh'
        assert generate_calls == []
