#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A pytest run that ERRORED must report WHAT broke, not an empty ``failures[]``.

pytest reports a test module that raised while being COLLECTED, and a fixture
that raised at setup/teardown, under its ``E`` report character — as ``ERROR``
short-summary lines under an ``=== ERRORS ===`` banner, never as ``FAILED``
lines. A parser that reads only ``FAILED`` renders such a run as an empty
``failures[]``: the build still goes red, so no gate is defeated, but a triage
consumer reading ``failures[]`` to learn what broke is told nothing.

Every case here is written against the log shape a live run actually produces —
including the header padding, which is the trap. pytest pads a block header out
to the terminal width with ``_``, so a SHORT name (``test_alpha``) gets a wide
rule while a LONG one (``ERROR collecting test/some/deep/path.py``) consumes the
width and collapses to exactly one underscore per side. A header pattern tuned to
the wide form matches every short name and silently misses every long one, which
is how a collection error came back carrying neither a line number nor its
assertion message. The two padding widths are asserted against each other below.
"""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall',
    'build-pyproject',
    '_pyproject_cmd_parse.py',
    '_pyproject_cmd_parse_collection_errors',
)

parse_log = _mod.parse_log
slice_failure_details = _mod.slice_failure_details
_has_pytest_output = _mod._has_pytest_output
CATEGORY_COLLECTION_ERROR = _mod.CATEGORY_COLLECTION_ERROR
CATEGORY_TEST_FAILURE = _mod.CATEGORY_TEST_FAILURE

_BROKEN_MODULE = 'test/plan-marshall/build-pyproject/test_broken_import.py'

#: A module-import assertion failure, transcribed from a live `module-tests` run.
#: The block header carries the COLLAPSED single-underscore padding a path this
#: long produces; the short-summary line carries NO ` - message` tail, which is
#: why the message can only come from the block's `E   ` gutter.
_COLLECTION_ERROR_LOG = f"""==================================== ERRORS ====================================
_ ERROR collecting {_BROKEN_MODULE} _
{_BROKEN_MODULE}:7: in <module>
    assert _SENTINEL == 1, 'deliberate module-import assertion'
E   AssertionError: deliberate module-import assertion
E   assert 0 == 1
=========================== short test summary info ============================
ERROR {_BROKEN_MODULE}
======================== 398 passed, 1 error in 8.51s ========================
"""

#: A fixture that raised at setup. This spelling DOES name a test and DOES carry
#: a summary message, so it exercises the other half of the pairing: the
#: `ERROR at setup of <test>` header must resolve to the same key as the
#: `ERROR <path>::<test>` summary line.
_SETUP_ERROR_LOG = """==================================== ERRORS ====================================
______________________ ERROR at setup of test_widget ______________________
test/test_widget.py:4: in a_fixture
    raise RuntimeError('fixture blew up')
E   RuntimeError: fixture blew up
=========================== short test summary info ============================
ERROR test/test_widget.py::test_widget - RuntimeError: fixture blew up
======================== 10 passed, 1 error in 1.10s ========================
"""


@contextmanager
def _temp_log(content: str) -> Iterator[str]:
    """Write content to a temp .log file, yield its path, and unlink on exit."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as handle:
        handle.write(content)
        handle.flush()
        path = handle.name
    try:
        yield path
    finally:
        Path(path).unlink()


def _error_issues(content: str) -> list:
    """Parse ``content`` and return only its collection/setup ERROR issues."""
    with _temp_log(content) as path:
        issues, _, _ = parse_log(path)
    return [issue for issue in issues if issue.category == CATEGORY_COLLECTION_ERROR]


# =============================================================================
# The finding: an errored run reports what broke.
# =============================================================================


def test_collection_error_is_reported_at_all():
    """The defect verbatim: a collection error yielded an EMPTY issue list."""
    assert len(_error_issues(_COLLECTION_ERROR_LOG)) == 1


def test_collection_error_names_its_file_line_and_message():
    """File, line and message all reach the consumer — not just the file.

    Each of the three is asserted separately because each has its own failure
    mode: the file comes from the short-summary line, the line number only from
    the block's traceback frame, and the message only from the block's ``E``
    gutter (the collection-error summary line carries no message tail at all).
    """
    issue = _error_issues(_COLLECTION_ERROR_LOG)[0]

    assert issue.file == _BROKEN_MODULE
    assert issue.line == 7
    assert issue.message == 'AssertionError: deliberate module-import assertion'


def test_collection_error_message_is_not_a_restatement_of_the_file_name():
    """The matched negative: the terse fallback must NOT be what is published.

    ``Error collecting <path>`` is well-formed and non-empty, so a message
    assertion alone would pass on it while telling a triage consumer nothing it
    did not already have from ``file``. This pins that the block's real message
    won.
    """
    issue = _error_issues(_COLLECTION_ERROR_LOG)[0]

    assert not issue.message.startswith('Error collecting')


def test_collection_error_carries_its_traceback_detail():
    """The captured block, not the one-line message, is what triage reads."""
    issue = _error_issues(_COLLECTION_ERROR_LOG)[0]

    assert issue.detail is not None
    assert 'assert _SENTINEL == 1' in issue.detail
    assert 'AssertionError: deliberate module-import assertion' in issue.detail


def test_collection_error_category_routes_to_the_test_failure_store():
    """``_build_shared`` routes any ``test_``-prefixed category to test-failure.

    A test module that could not even be imported is a broken test, not a build
    error, and a triage consumer looks for it in the same place.
    """
    issue = _error_issues(_COLLECTION_ERROR_LOG)[0]

    assert issue.category == CATEGORY_COLLECTION_ERROR
    assert issue.category.startswith('test_')


def test_errored_run_is_reported_as_a_failure():
    """The build status stays red — an ERRORS-only run is not a green run."""
    with _temp_log(_COLLECTION_ERROR_LOG) as path:
        _, _, build_status = parse_log(path)

    assert build_status == 'FAILURE'


# =============================================================================
# The `parse --failures-detail` slice verb reports the same population.
# =============================================================================


def test_slice_failures_detail_counts_the_collection_error():
    """The slice verb returned ``total_failures: 0`` over a demonstrably red build."""
    with _temp_log(_COLLECTION_ERROR_LOG) as path:
        result = slice_failure_details(path, failures_detail=True)

    assert result['status'] == 'success'
    assert result['total_failures'] == 1
    assert result['root_causes'] == 1


def test_slice_named_test_matches_a_setup_error():
    """A setup error is addressable by test name, exactly like a failure is."""
    with _temp_log(_SETUP_ERROR_LOG) as path:
        result = slice_failure_details(path, test_name='test_widget')

    assert result['matched'] == 1
    assert 'fixture blew up' in result['failures'][0]['detail']


# =============================================================================
# Routing: an ERROR-only log must reach the pytest parser at all.
# =============================================================================


def test_error_only_log_is_detected_as_pytest_output():
    """No FAILED line, and a count line carrying neither `passed` nor `failed`.

    Without ERROR-line detection this log routes to NO parser, so the whole
    population is dropped before any of it can be read.
    """
    content = f'ERROR {_BROKEN_MODULE}\n!!! Interrupted: 1 error during collection !!!\n'

    assert _has_pytest_output(content) is True


def test_a_log_with_neither_marker_is_still_not_pytest_output():
    """Matched control: the widened detection did not become unconditional."""
    assert _has_pytest_output('Success: no issues found in 5 source files\n') is False


# =============================================================================
# Block-header padding width — the trap this fix turned on.
# =============================================================================


def test_a_single_underscore_padded_header_still_resolves_its_block():
    """A long name collapses the padding to one underscore per side.

    Resolving the block is what supplies the line number and the message, so a
    header pattern that misses this form degrades the record to its terse
    fallback while still LOOKING populated.
    """
    issue = _error_issues(_COLLECTION_ERROR_LOG)[0]

    assert issue.line == 7


def test_a_wide_padded_header_still_resolves_its_block():
    """Matched positive control: the historic wide-rule form is not regressed."""
    with _temp_log(_SETUP_ERROR_LOG) as path:
        issues, _, _ = parse_log(path)

    errored = [issue for issue in issues if issue.category == CATEGORY_COLLECTION_ERROR]
    assert len(errored) == 1
    assert errored[0].line == 4
    assert errored[0].message == 'RuntimeError: fixture blew up'


# =============================================================================
# Coexistence with the FAILED population.
# =============================================================================


def test_failed_and_error_lines_are_both_reported():
    """The two report characters are additive, not alternatives."""
    content = f"""==================================== ERRORS ====================================
_ ERROR collecting {_BROKEN_MODULE} _
{_BROKEN_MODULE}:7: in <module>
    assert _SENTINEL == 1
E   AssertionError: import-time assert
=========================== short test summary info ============================
FAILED test/test_other.py::test_thing - AssertionError: assert 1 == 2
ERROR {_BROKEN_MODULE}
======================== 5 passed, 1 failed, 1 error in 2.00s ========================
"""
    with _temp_log(content) as path:
        issues, summary, _ = parse_log(path)

    categories = {issue.category for issue in issues}
    assert CATEGORY_TEST_FAILURE in categories
    assert CATEGORY_COLLECTION_ERROR in categories
    assert summary is not None
    assert summary.failed == 1


def test_error_without_a_block_falls_back_to_the_terse_message():
    """A `--tb=no` run has no ERRORS section, so only the summary line exists.

    The record is still emitted — a degraded message beats no record at all —
    and its line number is honestly absent rather than invented.
    """
    content = f'ERROR {_BROKEN_MODULE}\n======================== 5 passed, 1 error in 2.00s ========================\n'
    issues = _error_issues(content)

    assert len(issues) == 1
    assert issues[0].message == f'Error collecting {_BROKEN_MODULE}'
    assert issues[0].line is None


def test_a_green_log_yields_no_error_records():
    """Control: the ERROR collector does not manufacture records from a green run."""
    content = '======================== 398 passed in 8.51s ========================\n'

    assert _error_issues(content) == []


# =============================================================================
# Whitespace in a node id or a path — the second trap.
# =============================================================================
#
# pytest renders a string parameter through ``ascii_escaped``, which escapes
# non-ascii and non-printable characters but leaves a plain SPACE intact. So
# ``test_x[a b]`` reaches the short-summary line with its space, and a ``\\S+``
# capture does not truncate such a line — it fails to match it ENTIRELY. The
# record is then ABSENT rather than partial, which is the failure mode a
# presence-only assertion would never surface.

_SPACED_TEST_ID = 'test_widget[a b]'

#: A setup error whose node id carries a space. Both halves of the pairing must
#: tolerate it: the ``ERROR at setup of <test>`` block header AND the
#: ``ERROR <path>::<test>`` summary line resolve to the same key, or the block is
#: never found and the record silently degrades to its terse message.
_SPACED_SETUP_ERROR_LOG = f"""==================================== ERRORS ====================================
____________________ ERROR at setup of {_SPACED_TEST_ID} ____________________
test/test_widget.py:4: in a_fixture
    raise RuntimeError('boom')
E   RuntimeError: boom
=========================== short test summary info ============================
ERROR test/test_widget.py::{_SPACED_TEST_ID} - RuntimeError: boom
======================== 10 passed, 1 error in 1.10s ========================
"""

_SPACED_PATH = 'test/plan-marshall/build-pyproject/broken module/test_x.py'

#: A collection error whose FILE PATH carries a space — the same defect reached
#: through the other capture group.
_SPACED_PATH_COLLECTION_LOG = f"""==================================== ERRORS ====================================
_ ERROR collecting {_SPACED_PATH} _
{_SPACED_PATH}:3: in <module>
    raise ImportError('no such thing')
E   ImportError: no such thing
=========================== short test summary info ============================
ERROR {_SPACED_PATH}
======================== 5 passed, 1 error in 2.00s ========================
"""


def test_a_setup_error_whose_node_id_carries_a_space_yields_one_record():
    """The record exists at all — under ``\\S+`` the line matched nothing."""
    assert len(_error_issues(_SPACED_SETUP_ERROR_LOG)) == 1


def test_a_spaced_node_id_record_resolves_its_block_not_just_its_presence():
    """Presence is not enough: the record must RESOLVE its block.

    A terse fallback record would satisfy a presence-only assertion while
    carrying no line number and a restated message, so the line and the message
    are both pinned. The line can only come from the block, which is what proves
    the header/summary pairing survived the widening.
    """
    issue = _error_issues(_SPACED_SETUP_ERROR_LOG)[0]

    assert issue.file == 'test/test_widget.py'
    assert issue.line == 4
    assert issue.message == 'RuntimeError: boom'
    assert issue.detail is not None and 'a_fixture' in issue.detail


def test_a_collection_error_whose_path_carries_a_space_names_that_path():
    """The path capture tolerates the space, and the whole path is reported.

    The message comes from the block's ``E`` gutter — a collection error's
    summary line carries no tail — so asserting it also proves the block was
    found under the spaced key.
    """
    issues = _error_issues(_SPACED_PATH_COLLECTION_LOG)

    assert len(issues) == 1
    assert issues[0].file == _SPACED_PATH
    assert issues[0].line == 3
    assert issues[0].message == 'ImportError: no such thing'


def test_a_message_containing_py_colons_still_splits_at_the_first_py():
    """⛔ The control the LAZY path quantifier exists for.

    A greedy ``(.+\\.py)`` would run to the LAST ``.py`` on the line and swallow
    the node id and half the message into the file path. Lazy takes the FIRST,
    so a message that itself names a ``path.py::test`` still splits correctly.
    This is why the widening must not be "simplified" to a greedy group.
    """
    content = (
        '=========================== short test summary info ============================\n'
        'ERROR test/test_alpha.py::test_thing - '
        'ValueError: could not import test/test_beta.py::test_other\n'
        '======================== 5 passed, 1 error in 2.00s ========================\n'
    )

    issues = _error_issues(content)

    assert len(issues) == 1
    assert issues[0].file == 'test/test_alpha.py'
    assert issues[0].message == 'ValueError: could not import test/test_beta.py::test_other'


def test_the_unspaced_fixtures_parse_identically_after_the_widening():
    """Matched control: the widened captures did not regress the original forms.

    The cases above this section already assert each field individually; this one
    states the non-regression as its own claim, over both summary spellings at
    once, so a widening that broke the common case fails here by name.
    """
    collection = _error_issues(_COLLECTION_ERROR_LOG)
    setup = _error_issues(_SETUP_ERROR_LOG)

    assert [(i.file, i.line, i.message) for i in collection] == [
        (_BROKEN_MODULE, 7, 'AssertionError: deliberate module-import assertion')
    ]
    assert [(i.file, i.line, i.message) for i in setup] == [
        ('test/test_widget.py', 4, 'RuntimeError: fixture blew up')
    ]
