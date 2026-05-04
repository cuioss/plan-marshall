#!/usr/bin/env python3
"""Tests for Rule 1 (unique fixture-module basenames) of doctor-test-conventions.

The rule flags helper modules under the test tree whose basename is a
generic name (`_fixtures.py`, `_helpers.py`, `_common.py`) or that
collides with another helper module in a different sibling test
directory. Lesson `2026-04-29-22-002` documents the original incident.
"""

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_analyze_test_conventions = _load_module('_analyze_test_conventions', '_analyze_test_conventions.py')
analyze_unique_fixture_basenames = _analyze_test_conventions.analyze_unique_fixture_basenames


def _write(path: Path, content: str = '') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def test_clean_tree_emits_no_findings(tmp_path):
    """Domain-prefixed helpers in different directories produce zero findings."""
    test_root = tmp_path / 'test'
    _write(test_root / 'plan-marshall' / 'manage-foo' / '_manage_foo_fixtures.py')
    _write(test_root / 'plan-marshall' / 'manage-bar' / '_manage_bar_helpers.py')

    findings = analyze_unique_fixture_basenames(test_root)

    assert findings == []


def test_generic_basename_fixtures_flagged(tmp_path):
    """A bare ``_fixtures.py`` is flagged as generic."""
    test_root = tmp_path / 'test'
    target = _write(test_root / 'plan-marshall' / 'foo' / '_fixtures.py')

    findings = analyze_unique_fixture_basenames(test_root)

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == 'unique-fixture-basenames'
    assert finding['file'] == str(target)
    assert finding['details']['kind'] == 'generic_basename'
    assert finding['details']['basename'] == '_fixtures.py'
    assert finding['severity'] == 'error'


def test_generic_basename_helpers_and_common_flagged(tmp_path):
    """Both ``_helpers.py`` and ``_common.py`` count as generic."""
    test_root = tmp_path / 'test'
    helpers = _write(test_root / 'a' / '_helpers.py')
    common = _write(test_root / 'b' / '_common.py')

    findings = analyze_unique_fixture_basenames(test_root)

    flagged_files = {f['file'] for f in findings}
    assert flagged_files == {str(helpers), str(common)}


def test_cross_directory_collision_reports_both(tmp_path):
    """Two domain-prefixed helpers sharing a basename in sibling dirs are both flagged."""
    test_root = tmp_path / 'test'
    first = _write(test_root / 'plan-marshall' / 'alpha' / '_alpha_x.py')
    second = _write(test_root / 'plan-marshall' / 'beta' / '_alpha_x.py')

    findings = analyze_unique_fixture_basenames(test_root)

    assert len(findings) == 2
    flagged_files = {f['file'] for f in findings}
    assert flagged_files == {str(first), str(second)}
    for finding in findings:
        assert finding['details']['kind'] == 'cross_directory_collision'
        assert finding['details']['basename'] == '_alpha_x.py'


def test_generic_name_in_two_dirs_only_emits_generic_findings(tmp_path):
    """Generic basenames take precedence over the collision branch (no duplicate findings)."""
    test_root = tmp_path / 'test'
    first = _write(test_root / 'a' / '_fixtures.py')
    second = _write(test_root / 'b' / '_fixtures.py')

    findings = analyze_unique_fixture_basenames(test_root)

    assert len(findings) == 2
    for finding in findings:
        assert finding['details']['kind'] == 'generic_basename'
    assert {f['file'] for f in findings} == {str(first), str(second)}


def test_init_files_are_ignored(tmp_path):
    """``__init__.py`` and dunder files do not count as helper modules."""
    test_root = tmp_path / 'test'
    _write(test_root / 'plan-marshall' / 'foo' / '__init__.py')
    _write(test_root / 'plan-marshall' / 'bar' / '__init__.py')

    findings = analyze_unique_fixture_basenames(test_root)

    assert findings == []


def test_missing_test_root_returns_empty(tmp_path):
    """A non-existent test root yields zero findings without error."""
    findings = analyze_unique_fixture_basenames(tmp_path / 'does-not-exist')
    assert findings == []


def test_finding_carries_standard_anchor(tmp_path):
    """Every finding includes the doc anchor for cross-reference resolution."""
    test_root = tmp_path / 'test'
    _write(test_root / 'foo' / '_fixtures.py')

    findings = analyze_unique_fixture_basenames(test_root)

    assert findings[0]['details']['standard_anchor'] == 'doctor-test-conventions.md#unique-fixture-basenames'
