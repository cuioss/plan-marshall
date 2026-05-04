#!/usr/bin/env python3
"""Unit tests for assert_test_identifiers helper.

Covers the library function ``assert_identifiers_in_log(written_identifiers,
log_path)`` and the CLI entrypoint exposed by ``assert_test_identifiers.py``.
The helper diffs pytest node identifiers written or modified by the current
task against the captured module-test log and reports a DiffResult so
execute-task can block silently-skipped tests.

Design notes:

* Substring matching is intentional — pytest node identifiers contain ``::``
  separators, so realistic nodeids like ``test/foo.py::test_bar`` cannot
  ambiguously collide with a longer identifier like ``test_barbaz`` (the
  separator anchors the left side). Fixtures use realistic pytest output so
  tests reflect actual execute-task usage rather than a synthetic edge case.
* Match is case-sensitive — so ``Test_Foo`` will not match ``test_foo``.
* Log fixtures are written via ``tmp_path`` so each test has an isolated
  filesystem and the helper's IO paths are exercised end-to-end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Cross-skill imports — PYTHONPATH is configured by the root test/conftest.py
# which adds every marketplace scripts/ directory, including
# marketplace/bundles/plan-marshall/skills/execute-task/scripts.
from assert_test_identifiers import (  # noqa: E402
    DiffResult,
    assert_identifiers_in_log,
)

from conftest import run_script  # noqa: E402

# Path to the script for CLI subprocess tests
SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'execute-task'
    / 'scripts'
    / 'assert_test_identifiers.py'
)


# =============================================================================
# Fixture helpers
# =============================================================================


def _pytest_log_lines(nodeids: list[str], status: str = 'PASSED') -> str:
    """Build a realistic pytest log snippet containing the given nodeids.

    The shape mirrors pytest's verbose output so tests exercise substring
    matching against real-world line content (leading module path, ``::``
    separator, trailing status + percent).
    """
    lines = [
        'platform darwin -- Python 3.11.6, pytest-8.0.0',
        f'collected {len(nodeids)} items',
        '',
    ]
    for nid in nodeids:
        lines.append(f'{nid} {status} [100%]')
    lines.append('')
    lines.append(f'========= {len(nodeids)} passed in 0.42s =========')
    return '\n'.join(lines)


def _write_log(tmp_path: Path, content: str, name: str = 'module-tests.log') -> Path:
    """Write content to a log file under tmp_path and return the path."""
    log_path = tmp_path / name
    log_path.write_text(content, encoding='utf-8')
    return log_path


def _write_identifiers(tmp_path: Path, identifiers: list[str], name: str = 'identifiers.txt') -> Path:
    """Write newline-delimited identifiers to a fixture file."""
    ids_path = tmp_path / name
    ids_path.write_text('\n'.join(identifiers) + '\n', encoding='utf-8')
    return ids_path


# =============================================================================
# (d) Fires when any written identifier is missing from the log
# =============================================================================


def test_fires_when_identifier_is_missing(tmp_path):
    """Missing identifier → passed=False, missing populated, found preserves order."""
    # Arrange
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_alpha',
        'test/plan-marshall/execute-task/test_foo.py::test_beta',
        'test/plan-marshall/execute-task/test_foo.py::test_gamma',
    ]
    # Log reports only alpha and gamma — beta was silently skipped.
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines([written[0], written[2]]),
    )

    # Act
    result = assert_identifiers_in_log(written, log_path)

    # Assert
    assert isinstance(result, DiffResult)
    assert result.passed is False
    # Missing preserves input order (beta is the only absent one)
    assert result.missing == (written[1],)
    # Found preserves input order (alpha before gamma, both present)
    assert result.found == (written[0], written[2])


def test_fires_when_all_identifiers_missing(tmp_path):
    """All identifiers missing → passed=False, missing==input, found empty."""
    # Arrange
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_one',
        'test/plan-marshall/execute-task/test_foo.py::test_two',
    ]
    # Log reports an unrelated test
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines(['test/plan-marshall/execute-task/test_bar.py::test_other']),
    )

    # Act
    result = assert_identifiers_in_log(written, log_path)

    # Assert
    assert result.passed is False
    assert result.missing == tuple(written)
    assert result.found == ()


# =============================================================================
# (e) Passes when all identifiers are present
# =============================================================================


def test_passes_when_all_identifiers_present(tmp_path):
    """All identifiers present → passed=True, missing empty, found preserves order."""
    # Arrange
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_alpha',
        'test/plan-marshall/execute-task/test_foo.py::test_beta',
        'test/plan-marshall/execute-task/test_foo.py::test_gamma',
    ]
    log_path = _write_log(tmp_path, _pytest_log_lines(written))

    # Act
    result = assert_identifiers_in_log(written, log_path)

    # Assert
    assert result.passed is True
    assert result.missing == ()
    # Input order is preserved in found (not alphabetical, not log order)
    assert result.found == tuple(written)


# =============================================================================
# (3) Empty written_identifiers → vacuous pass
# =============================================================================


def test_empty_identifiers_vacuous_pass(tmp_path):
    """Empty input → passed=True, found=(), missing=(). Log not required."""
    # Arrange — no log file at all; vacuous pass must short-circuit before IO
    nonexistent_log = tmp_path / 'does-not-exist.log'

    # Act
    result = assert_identifiers_in_log([], nonexistent_log)

    # Assert
    assert result.passed is True
    assert result.found == ()
    assert result.missing == ()


def test_empty_identifiers_as_tuple_vacuous_pass(tmp_path):
    """An empty tuple (not just list) also triggers the vacuous pass."""
    # Arrange
    nonexistent_log = tmp_path / 'does-not-exist.log'

    # Act
    result = assert_identifiers_in_log((), nonexistent_log)

    # Assert
    assert result.passed is True
    assert result.found == ()
    assert result.missing == ()


# =============================================================================
# (4) Nonexistent log path raises FileNotFoundError
# =============================================================================


def test_nonexistent_log_raises_file_not_found(tmp_path):
    """Missing log path raises FileNotFoundError with a clear message."""
    # Arrange
    missing_log = tmp_path / 'never-created.log'
    written = ['test/plan-marshall/execute-task/test_foo.py::test_alpha']

    # Act / Assert
    with pytest.raises(FileNotFoundError) as excinfo:
        assert_identifiers_in_log(written, missing_log)

    # Assert message carries the path so callers can surface it verbatim
    message = str(excinfo.value)
    assert 'module-test log' in message
    assert str(missing_log) in message


def test_log_path_is_directory_raises_file_not_found(tmp_path):
    """A directory masquerading as a log path also raises FileNotFoundError."""
    # Arrange — create a directory where a log file is expected
    not_a_file = tmp_path / 'log-dir'
    not_a_file.mkdir()
    written = ['test/plan-marshall/execute-task/test_foo.py::test_alpha']

    # Act / Assert
    with pytest.raises(FileNotFoundError) as excinfo:
        assert_identifiers_in_log(written, not_a_file)

    message = str(excinfo.value)
    assert 'not a regular file' in message
    assert str(not_a_file) in message


# =============================================================================
# (5) Anchored-regex matching: distinct names + prefix-collision guardrail
# =============================================================================


def test_realistic_nodeids_with_distinct_names_dont_collide(tmp_path):
    """Realistic pytest nodeids with distinct function names are unambiguous.

    In normal execute-task usage the written identifiers are full pytest
    nodeids with distinct function names. The anchored-regex matcher
    resolves correctly for any non-colliding name.
    """
    # Arrange — two nodeids with completely different function names
    alpha_id = 'test/plan-marshall/execute-task/test_foo.py::test_alpha'
    gamma_id = 'test/plan-marshall/execute-task/test_foo.py::test_gamma'

    # Log only reports gamma
    log_path = _write_log(tmp_path, _pytest_log_lines([gamma_id]))

    # Act — search for alpha (not a substring of gamma)
    result = assert_identifiers_in_log([alpha_id], log_path)

    # Assert — alpha is correctly flagged as missing
    assert result.passed is False
    assert result.missing == (alpha_id,)
    assert result.found == ()


def test_prefix_collision_does_not_false_match(tmp_path):
    """Anchored matching prevents prefix-name collisions.

    The helper matches each identifier with ``{identifier}(?:\\s|$)`` so that
    a shorter identifier which is a character-prefix of a longer identifier
    on the same log line does NOT false-match — ``test_bar`` must not
    silently be reported as present when only ``test_barbaz`` actually ran.
    This is the core guardrail the diff assertion exists to provide.
    """
    # Arrange — long id is written to log, short id is a prefix of it
    short_id = 'test/plan-marshall/execute-task/test_foo.py::test_bar'
    long_id = 'test/plan-marshall/execute-task/test_foo.py::test_barbaz'
    log_path = _write_log(tmp_path, _pytest_log_lines([long_id]))

    # Act — search for the short id
    result = assert_identifiers_in_log([short_id], log_path)

    # Assert — short id is correctly flagged as missing (no false positive)
    assert result.passed is False
    assert result.found == ()
    assert result.missing == (short_id,)


# =============================================================================
# (6) Order preservation in found/missing
# =============================================================================


def test_order_preservation_mixed_found_missing(tmp_path):
    """Mixed found/missing input → each tuple preserves the input order."""
    # Arrange — 5 identifiers in a specific order
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_alpha',  # present
        'test/plan-marshall/execute-task/test_foo.py::test_beta',  # missing
        'test/plan-marshall/execute-task/test_foo.py::test_gamma',  # present
        'test/plan-marshall/execute-task/test_foo.py::test_delta',  # missing
        'test/plan-marshall/execute-task/test_foo.py::test_epsilon',  # present
    ]
    # Log reports alpha, gamma, epsilon (in a DIFFERENT order than input)
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines([written[4], written[0], written[2]]),
    )

    # Act
    result = assert_identifiers_in_log(written, log_path)

    # Assert — order reflects INPUT, not log order
    assert result.passed is False
    assert result.found == (written[0], written[2], written[4])
    assert result.missing == (written[1], written[3])


# =============================================================================
# (7) Case sensitivity
# =============================================================================


def test_case_sensitive_matching(tmp_path):
    """Case-sensitive matching: ``Test_Foo`` does not match ``test_foo`` line."""
    # Arrange
    # Log uses lowercase pytest convention (realistic)
    lowercase_id = 'test/plan-marshall/execute-task/test_foo.py::test_bar'
    log_path = _write_log(tmp_path, _pytest_log_lines([lowercase_id]))

    # Search for the same nodeid but with mixed case — should NOT match
    mixed_case_id = 'Test/Plan-Marshall/Execute-Task/Test_Foo.py::Test_Bar'

    # Act
    result = assert_identifiers_in_log([mixed_case_id], log_path)

    # Assert
    assert result.passed is False
    assert result.missing == (mixed_case_id,)
    assert result.found == ()


def test_case_sensitive_function_name_only(tmp_path):
    """Capitalising just the function name still fails the match."""
    # Arrange
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines(['test/plan-marshall/execute-task/test_foo.py::test_bar']),
    )
    # Caller passes the same path but with ``Test_Bar`` (capitalised)
    searched = 'test/plan-marshall/execute-task/test_foo.py::Test_Bar'

    # Act
    result = assert_identifiers_in_log([searched], log_path)

    # Assert
    assert result.passed is False
    assert result.missing == (searched,)


# =============================================================================
# (8) CLI integration via subprocess
# =============================================================================


def test_cli_all_found_exit_zero(tmp_path):
    """CLI: every identifier present → exit 0, TOON reports passed=true."""
    # Arrange
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_alpha',
        'test/plan-marshall/execute-task/test_foo.py::test_beta',
    ]
    log_path = _write_log(tmp_path, _pytest_log_lines(written))
    ids_path = _write_identifiers(tmp_path, written)

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(ids_path),
        '--log',
        str(log_path),
        cwd=tmp_path,
    )

    # Assert
    assert result.returncode == 0, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    # TOON parser coerces ``true`` → bool, ``0`` → int — accept both shapes
    assert data['passed'] in (True, 'true')
    assert int(data['found_count']) == 2
    assert int(data['missing_count']) == 0


def test_cli_some_missing_exit_one(tmp_path):
    """CLI: one identifier missing → exit 1, TOON reports passed=false + missing[]."""
    # Arrange
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_alpha',
        'test/plan-marshall/execute-task/test_foo.py::test_beta',
        'test/plan-marshall/execute-task/test_foo.py::test_gamma',
    ]
    # Log only reports alpha + gamma
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines([written[0], written[2]]),
    )
    ids_path = _write_identifiers(tmp_path, written)

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(ids_path),
        '--log',
        str(log_path),
        cwd=tmp_path,
    )

    # Assert
    assert result.returncode == 1, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['passed'] in (False, 'false')
    assert int(data['found_count']) == 2
    assert int(data['missing_count']) == 1
    # missing[] should be populated — the TOON parser surfaces it as a list
    assert 'missing' in data
    # The missing entry should be the beta identifier (substring match
    # in stdout is the most robust cross-parser check).
    assert written[1] in result.stdout


def test_cli_nonexistent_log_exit_two(tmp_path):
    """CLI: log file missing → exit 2, TOON emits status=error."""
    # Arrange
    written = ['test/plan-marshall/execute-task/test_foo.py::test_alpha']
    ids_path = _write_identifiers(tmp_path, written)
    missing_log = tmp_path / 'never-created.log'

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(ids_path),
        '--log',
        str(missing_log),
        cwd=tmp_path,
    )

    # Assert
    assert result.returncode == 2, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'error'
    assert 'module-test log' in str(data.get('error', ''))


def test_cli_nonexistent_identifiers_file_exit_two(tmp_path):
    """CLI: identifiers file missing → exit 2, TOON emits status=error."""
    # Arrange — create a log but NOT an identifiers file
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines(['test/plan-marshall/execute-task/test_foo.py::test_alpha']),
    )
    missing_ids = tmp_path / 'never-created-ids.txt'

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(missing_ids),
        '--log',
        str(log_path),
        cwd=tmp_path,
    )

    # Assert
    assert result.returncode == 2, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'error'
    assert 'identifiers file' in str(data.get('error', ''))


def test_cli_blank_lines_in_identifiers_file_are_stripped(tmp_path):
    """CLI: blank / whitespace-only lines in the identifiers file are stripped."""
    # Arrange — identifiers file with stray blank lines and padding
    written = [
        'test/plan-marshall/execute-task/test_foo.py::test_alpha',
        'test/plan-marshall/execute-task/test_foo.py::test_beta',
    ]
    ids_content = (
        '\n'  # leading blank
        f'{written[0]}\n'
        '   \n'  # whitespace-only
        f'{written[1]}\n'
        '\n'  # trailing blank
    )
    ids_path = tmp_path / 'ids.txt'
    ids_path.write_text(ids_content, encoding='utf-8')
    log_path = _write_log(tmp_path, _pytest_log_lines(written))

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(ids_path),
        '--log',
        str(log_path),
        cwd=tmp_path,
    )

    # Assert — only the 2 real identifiers are counted; blanks are ignored
    assert result.returncode == 0, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['passed'] in (True, 'true')
    assert int(data['found_count']) == 2
    assert int(data['missing_count']) == 0


def test_cli_empty_identifiers_file_vacuous_pass(tmp_path):
    """CLI: an identifiers file with only blank lines → vacuous pass (exit 0)."""
    # Arrange — file with only blanks
    ids_path = tmp_path / 'ids.txt'
    ids_path.write_text('\n   \n\n', encoding='utf-8')
    # Log path can point at anything — vacuous pass short-circuits IO,
    # but the CLI still reads the identifiers file first. Give it a real log
    # to mirror realistic usage even though it won't be searched.
    log_path = _write_log(tmp_path, '')

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(ids_path),
        '--log',
        str(log_path),
        cwd=tmp_path,
    )

    # Assert
    assert result.returncode == 0, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    assert data['passed'] in (True, 'true')
    assert int(data['found_count']) == 0
    assert int(data['missing_count']) == 0


@pytest.mark.parametrize(
    ('identifiers', 'found_count', 'missing_count', 'expected_exit'),
    [
        # All found → exit 0
        (
            ['test/plan-marshall/execute-task/test_foo.py::test_one'],
            1,
            0,
            0,
        ),
        # All missing → exit 1
        (
            ['test/plan-marshall/execute-task/test_foo.py::test_missing'],
            0,
            1,
            1,
        ),
    ],
)
def test_cli_exit_code_matrix(tmp_path, identifiers, found_count, missing_count, expected_exit):
    """Parametrised sanity check for the exit-code contract."""
    # Arrange — log always contains test_one
    log_path = _write_log(
        tmp_path,
        _pytest_log_lines(['test/plan-marshall/execute-task/test_foo.py::test_one']),
    )
    ids_path = _write_identifiers(tmp_path, identifiers)

    # Act
    result = run_script(
        SCRIPT_PATH,
        'run',
        '--identifiers-file',
        str(ids_path),
        '--log',
        str(log_path),
        cwd=tmp_path,
    )

    # Assert
    assert result.returncode == expected_exit, f'CLI stderr: {result.stderr}'
    data = result.toon()
    assert data['status'] == 'success'
    assert int(data['found_count']) == found_count
    assert int(data['missing_count']) == missing_count
