#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the module-shape rules of doctor-test-conventions.

Two warning-severity rules govern whether a module is the right shape to be
collected at all: `test-module-line-budget` (a collected module over 400
lines) and `test-helper-module-misnamed` (a module matching pytest's
collection patterns that declares no test). Each has a positive fixture that
fires it and a negative control that does not."""

import textwrap
from pathlib import Path

from conftest import load_script_module

_analyze_test_conventions = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_test_conventions.py', '_analyze_test_conventions'
)

analyze_test_module_line_budget = _analyze_test_conventions.analyze_test_module_line_budget
analyze_test_helper_module_misnamed = _analyze_test_conventions.analyze_test_helper_module_misnamed
TEST_MODULE_LINE_BUDGET = _analyze_test_conventions.TEST_MODULE_LINE_BUDGET


def _write(test_root: Path, rel_path: str, content: str) -> Path:
    """Materialize one module under the scratch test root."""
    target = test_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content), encoding='utf-8')
    return target


# ---------------------------------------------------------------------------
# test-module-line-budget
# ---------------------------------------------------------------------------


def test_module_over_budget_is_flagged(tmp_path):
    """A collected test module over the 400-line budget is flagged."""
    body = 'def test_x():\n    assert True\n' + '# filler\n' * TEST_MODULE_LINE_BUDGET
    _write(tmp_path, 'test_big.py', body)

    findings = analyze_test_module_line_budget(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-module-line-budget'
    assert findings[0]['severity'] == 'warning'


def test_module_within_budget_is_not_flagged(tmp_path):
    """A collected test module at or under the budget produces no finding."""
    _write(tmp_path, 'test_small.py', 'def test_x():\n    assert True\n')

    assert analyze_test_module_line_budget(tmp_path) == []


def test_line_budget_finding_carries_count_and_budget(tmp_path):
    """The finding reports the module's line count, the budget, and the overage."""
    over_by = 5
    line_count = TEST_MODULE_LINE_BUDGET + over_by
    _write(tmp_path, 'test_big.py', '# filler\n' * line_count)

    details = analyze_test_module_line_budget(tmp_path)[0]['details']

    assert details['line_count'] == line_count
    assert details['budget'] == TEST_MODULE_LINE_BUDGET
    assert details['over_by'] == over_by


def test_uncollected_module_over_budget_is_not_flagged(tmp_path):
    """A helper module over the budget is out of scope — the rule governs collected modules."""
    _write(tmp_path, '_domain_fixtures.py', '# filler\n' * (TEST_MODULE_LINE_BUDGET + 50))

    assert analyze_test_module_line_budget(tmp_path) == []


# ---------------------------------------------------------------------------
# test-helper-module-misnamed
# ---------------------------------------------------------------------------


def test_collected_module_without_tests_is_flagged(tmp_path):
    """A module named test_*.py that declares no test is flagged, build-failing.

    This rule ships at ``error`` rather than ``warning``: its violation count
    over the tree reached zero, so it guards a clean tree instead of describing
    a non-compliant one.
    """
    _write(tmp_path, 'test_helpers.py', 'def build_plan():\n    return {}\n')

    findings = analyze_test_helper_module_misnamed(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-helper-module-misnamed'
    assert findings[0]['severity'] == 'error'


def test_collected_module_with_test_function_is_not_flagged(tmp_path):
    """A module declaring a test function produces no finding."""
    _write(tmp_path, 'test_real.py', 'def test_x():\n    assert True\n')

    assert analyze_test_helper_module_misnamed(tmp_path) == []


def test_collected_module_with_test_class_is_not_flagged(tmp_path):
    """A module declaring only a Test* class produces no finding."""
    _write(tmp_path, 'test_classy.py', 'class TestThing:\n    def test_x(self):\n        assert True\n')

    assert analyze_test_helper_module_misnamed(tmp_path) == []


def test_underscore_helper_without_tests_is_not_flagged(tmp_path):
    """A correctly-named helper module is out of scope — it is never collected."""
    _write(tmp_path, '_domain_fixtures.py', 'def build_plan():\n    return {}\n')

    assert analyze_test_helper_module_misnamed(tmp_path) == []


def test_trailing_suffix_collected_module_is_flagged(tmp_path):
    """The *_test.py collection pattern is covered, not only test_*.py."""
    _write(tmp_path, 'thing_test.py', 'VALUE = 1\n')

    findings = analyze_test_helper_module_misnamed(tmp_path)

    assert [f['rule_id'] for f in findings] == ['test-helper-module-misnamed']


def test_missing_test_root_is_a_noop(tmp_path):
    """Both module-shape rules return no findings when the test root is absent."""
    absent = tmp_path / 'no-such-tree'

    assert analyze_test_module_line_budget(absent) == []
    assert analyze_test_helper_module_misnamed(absent) == []
