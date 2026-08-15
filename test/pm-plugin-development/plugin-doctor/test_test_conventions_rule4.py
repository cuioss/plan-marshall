#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the four warning-severity house-style rules of doctor-test-conventions.

The rules are the structural half of the test-authoring standards: a 400-line
module budget, a collected module that declares no test, a hand-rolled import
preamble, and a historical citation in test prose. Each rule has a positive
fixture that fires it and a negative control that does not.
"""

import textwrap
from pathlib import Path

from conftest import load_script_module

_analyze_test_conventions = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_test_conventions.py', '_analyze_test_conventions'
)

analyze_test_module_line_budget = _analyze_test_conventions.analyze_test_module_line_budget
analyze_test_helper_module_misnamed = _analyze_test_conventions.analyze_test_helper_module_misnamed
analyze_test_module_preamble = _analyze_test_conventions.analyze_test_module_preamble
analyze_test_docstring_prose = _analyze_test_conventions.analyze_test_docstring_prose
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
    """A module named test_*.py that declares no test is flagged."""
    _write(tmp_path, 'test_helpers.py', 'def build_plan():\n    return {}\n')

    findings = analyze_test_helper_module_misnamed(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-helper-module-misnamed'
    assert findings[0]['severity'] == 'warning'


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


# ---------------------------------------------------------------------------
# test-module-preamble-boilerplate
# ---------------------------------------------------------------------------


def test_spec_from_file_location_is_flagged(tmp_path):
    """A spec_from_file_location preamble is flagged."""
    _write(
        tmp_path,
        'test_preamble.py',
        """
        import importlib.util

        def test_x():
            spec = importlib.util.spec_from_file_location('m', '/tmp/m.py')
            assert spec is not None
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-module-preamble-boilerplate'
    assert findings[0]['details']['kind'] == 'spec_from_file_location'


def test_deep_parent_chain_is_flagged(tmp_path):
    """A Path(__file__) chain of depth three or more is flagged with its depth."""
    _write(
        tmp_path,
        'test_chain.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).parent.parent.parent

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['kind'] == 'parent_chain'
    assert findings[0]['details']['parent_chain_depth'] == 3


def test_shallow_parent_chain_is_not_flagged(tmp_path):
    """A two-deep .parent hop is ordinary path work and is not flagged."""
    _write(
        tmp_path,
        'test_shallow.py',
        """
        from pathlib import Path

        HERE = Path(__file__).parent.parent

        def test_x():
            assert HERE
        """,
    )

    assert analyze_test_module_preamble(tmp_path) == []


def test_conftest_helpers_are_not_flagged(tmp_path):
    """The sanctioned conftest helpers produce no finding."""
    _write(
        tmp_path,
        'test_clean.py',
        """
        from conftest import get_scripts_dir, load_script_module

        MODULE = load_script_module('bundle', 'skill', 'script.py', 'script')

        def test_x():
            assert get_scripts_dir('bundle', 'skill')
        """,
    )

    assert analyze_test_module_preamble(tmp_path) == []


def test_one_chain_yields_one_finding(tmp_path):
    """A single deep chain reports once, not once per .parent link."""
    _write(
        tmp_path,
        'test_once.py',
        """
        from pathlib import Path

        ROOT = Path(__file__).parent.parent.parent.parent

        def test_x():
            assert ROOT
        """,
    )

    findings = analyze_test_module_preamble(tmp_path)

    assert len(findings) == 1
    assert findings[0]['details']['parent_chain_depth'] == 4


# ---------------------------------------------------------------------------
# test-docstring-historical-prose
# ---------------------------------------------------------------------------


def test_lesson_id_in_docstring_is_flagged(tmp_path):
    """A lesson id cited in a test docstring is flagged."""
    _write(
        tmp_path,
        'test_prose.py',
        '''
        def test_x():
            """Pins the fallback (closes lesson 2026-07-09-04-001)."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert len(findings) == 1
    assert findings[0]['rule_id'] == 'test-docstring-historical-prose'
    assert findings[0]['severity'] == 'warning'


def test_pr_reference_in_docstring_is_flagged(tmp_path):
    """A PR reference cited in a test docstring is flagged."""
    _write(
        tmp_path,
        'test_pr.py',
        '''
        def test_x():
            """Retains bot review on large plans (PR #551 reviewer finding)."""
            assert True
        ''',
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['pr_reference']


def test_plan_deliverable_id_in_comment_is_flagged(tmp_path):
    """A deliverable id cited in a comment is flagged — comments are prose too."""
    _write(
        tmp_path,
        'test_comment.py',
        """
        def test_x():
            # TASK-004 introduced this guard
            assert True
        """,
    )

    findings = analyze_test_docstring_prose(tmp_path)

    assert [f['details']['kind'] for f in findings] == ['plan_deliverable_id']


def test_present_tense_docstring_is_not_flagged(tmp_path):
    """A docstring stating the invariant in the present tense produces no finding."""
    _write(
        tmp_path,
        'test_clean_prose.py',
        '''
        def test_x():
            """An uninventoried test path resolves through the paths.tests fallback."""
            assert True
        ''',
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_citation_shape_as_string_data_is_not_flagged(tmp_path):
    """A lesson id used as test DATA is not a citation and is not flagged.

    This is the rule's structural discriminator: the same textual shapes appear
    far more often as the corpus a test operates on than as prose, so the scan
    reaches docstrings and comments only.
    """
    _write(
        tmp_path,
        'test_data.py',
        '''
        LESSON_IDS = ['2026-07-09-04-001', '2026-05-02-01-001']

        def test_x():
            """Every seeded lesson id round-trips through the validator."""
            assert all(validate(i) for i in LESSON_IDS)
        ''',
    )

    assert analyze_test_docstring_prose(tmp_path) == []


def test_one_finding_per_prose_segment(tmp_path):
    """A docstring carrying two citation shapes reports once, not once per shape."""
    _write(
        tmp_path,
        'test_multi.py',
        '''
        def test_x():
            """Guard added in PR #551 for lesson 2026-07-09-04-001."""
            assert True
        ''',
    )

    assert len(analyze_test_docstring_prose(tmp_path)) == 1


# ---------------------------------------------------------------------------
# Shared traversal behaviour
# ---------------------------------------------------------------------------


def test_missing_test_root_is_a_noop(tmp_path):
    """Every rule returns no findings when the test root does not exist."""
    absent = tmp_path / 'no-such-tree'

    assert analyze_test_module_line_budget(absent) == []
    assert analyze_test_helper_module_misnamed(absent) == []
    assert analyze_test_module_preamble(absent) == []
    assert analyze_test_docstring_prose(absent) == []
