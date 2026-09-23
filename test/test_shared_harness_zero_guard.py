# SPDX-License-Identifier: FSL-1.1-ALv2
"""Whole-tree guard: no collected module declares zero tests.

Such a module is imported by pytest, collects nothing, and is invisible in the
run. The whole-tree guard follows
``test/marketplace/test_prefix_strip_idiom_retired.py``: the scan returns its
population alongside its offender list, and the assertion checks the population
is non-empty BEFORE checking the offender list is empty, so a mis-rooted walk
cannot pass vacuously. Positive controls prove the detector fires; negative
controls prove it does not over-fire.
"""

from _shared_harness_fixtures import TEST_ROOT, scan_for_testless_collected_modules


def test_no_collected_module_under_test_declares_zero_tests():
    """Every module pytest collects under ``test/`` declares at least one test."""
    offenders, scanned = scan_for_testless_collected_modules(TEST_ROOT)

    # Population first: an empty offender list is only meaningful once the walk
    # is known to have read something.
    assert scanned > 0, (
        f'Scanned 0 collected modules under {TEST_ROOT} — the guard examined '
        'nothing, so its clean result is vacuous. Check TEST_ROOT resolution.'
    )
    assert offenders == [], (
        f"{len(offenders)} module(s) of {scanned} match pytest's collection "
        'pattern while declaring no test. pytest imports them and collects '
        'nothing, so they are invisible in the run. Rename each to '
        f'_{{domain}}_fixtures.py per test/README.md: {offenders}'
    )


def test_scanned_population_covers_the_real_test_tree():
    """The population is large enough to be the real tree, not a stray directory."""
    _offenders, scanned = scan_for_testless_collected_modules(TEST_ROOT)

    assert scanned > 100, f'Only {scanned} collected modules scanned — too few to be the test tree'


def test_detector_fires_on_a_testless_test_prefixed_module(tmp_path):
    """Positive control: ``test_*.py`` with only helpers is reported."""
    offender = tmp_path / 'test_helpers.py'
    offender.write_text('def create_thing():\n    return 1\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 1
    assert offenders == [str(offender)]


def test_detector_fires_on_the_suffix_spelling(tmp_path):
    """Positive control: ``*_test.py`` is collected too, so it is guarded too."""
    offender = tmp_path / 'thing_test.py'
    offender.write_text('VALUE = 1\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 1
    assert offenders == [str(offender)]


def test_detector_accepts_a_module_that_declares_tests(tmp_path):
    """Negative control: a real test module is not flagged.

    Without this, a detector that flagged every collected module would satisfy
    both positive controls while failing the whole tree.
    """
    real = tmp_path / 'test_real.py'
    real.write_text('def test_something():\n    assert True\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 1
    assert offenders == []


def test_detector_accepts_a_test_class(tmp_path):
    """Negative control: a ``Test*`` class counts as declaring tests."""
    real = tmp_path / 'test_classy.py'
    real.write_text('class TestThing:\n    def test_it(self):\n        assert True\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert offenders == []


def test_a_fixtures_module_is_not_collected_and_not_flagged(tmp_path):
    """Negative control: the supported helper name is outside the population.

    This is the shape the guard steers offenders toward, so flagging it would
    make the remedy fail the check.
    """
    helper = tmp_path / '_domain_fixtures.py'
    helper.write_text('def create_thing():\n    return 1\n', encoding='utf-8')

    offenders, scanned = scan_for_testless_collected_modules(tmp_path)

    assert scanned == 0
    assert offenders == []


def test_scan_reports_zero_population_for_a_missing_root(tmp_path):
    """A mis-rooted walk reports 0, never a false clean pass.

    This is what makes the population assertion in the whole-tree test load
    bearing.
    """
    offenders, scanned = scan_for_testless_collected_modules(tmp_path / 'does-not-exist')

    assert offenders == []
    assert scanned == 0
