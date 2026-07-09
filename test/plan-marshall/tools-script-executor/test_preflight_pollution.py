# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for cmd_preflight's multi-version PYTHONPATH pollution detection.

``generate_executor preflight`` regenerates the executor in place (safe derived
state, ADR-002) when it discovers more than one version dir per bundle in the
plugin-cache context — that pollution otherwise lets an older version's scripts
shadow the current ones on PYTHONPATH. These tests drive the real
``_detect_multi_version_pollution`` detector through ``cmd_preflight`` against
synthetic cache fixtures, with the heavy manifest/generate dependencies mocked
so only the pollution branch is exercised.
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
