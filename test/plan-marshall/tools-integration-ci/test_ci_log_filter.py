#!/usr/bin/env python3
"""Tests for ``_ci_log_filter.py`` — CI failure-log error-extraction filtering.

Covers the two public helpers of the central filter spec
(`tools-integration-ci/standards/api-contract.md` § CI Failure Log Download &
Filtering):

- ``filter_log(raw_log, error_style)`` — generic context-window heuristic,
  overlapping-window collapse, elision markers, no-match trailing fallback, and
  the ``maven`` / ``gradle`` / ``npm`` structured-parser routing with fallback
  to generic.
- ``slugify_check_name(name)`` — collision-free, file-name-safe stem derivation
  with stable fallback.

Real-fixture assertions (primary, required) load committed REAL CI log fixtures
from ``fixtures/ci-logs/{github,gitlab}/{pass,fail}.log`` (provenance in
``fixtures/ci-logs/SOURCE.md``) and assert ``filter_log`` extracts the correct
error portion from the REAL failure logs and yields no-error output for the REAL
pass logs, for both the GitHub-Actions-shaped and GitLab-job-trace-shaped
framings. The GitHub failure log is additionally routed through a structured
build-tool mode to exercise the no-structured-error fallback path on real
content. Real Maven / Gradle / npm build logs (committed under the build-system
fixture trees) drive the structured-parser routing assertions.

Synthetic-unit assertions supplement the real-fixture coverage for branches that
cannot be exercised from the captured logs alone (window overlap collapse,
explicit elision markers, empty/no-error edge cases, very large logs, and the
full slugify matrix).
"""

from __future__ import annotations

from pathlib import Path

import _ci_log_filter
import pytest
from _ci_log_filter import (
    CONTEXT_LINES,
    ELISION_MARKER,
    SLUG_FALLBACK,
    filter_log,
    slugify_check_name,
)

# Real CI-log fixtures live beside this test file.
_FIXTURE_ROOT = Path(__file__).parent / 'fixtures' / 'ci-logs'

# Real Maven / Gradle / npm build logs already committed under the build-system
# fixture trees. Resolved relative to this test file so resolution never depends
# on cwd.
_TEST_ROOT = Path(__file__).resolve().parents[1]  # test/plan-marshall
_MAVEN_FAILURE = _TEST_ROOT / 'build-maven' / 'fixtures' / 'log-test-data' / 'maven-failure-real.log'
_MAVEN_SUCCESS = _TEST_ROOT / 'build-maven' / 'fixtures' / 'log-test-data' / 'maven-success-real.log'
_GRADLE_FAILURE = _TEST_ROOT / 'build-gradle' / 'fixtures' / 'log-test-data' / 'gradle-failure-real.log'
_NPM_ESLINT = _TEST_ROOT / 'build-npm' / 'fixtures' / 'log-test-data' / 'npm-eslint-errors.log'


def _read_fixture(provider: str, kind: str) -> str:
    """Read a real CI-log fixture (``provider`` ∈ github/gitlab, ``kind`` ∈ pass/fail)."""
    path = _FIXTURE_ROOT / provider / f'{kind}.log'
    return path.read_text(encoding='utf-8')


# =============================================================================
# Real-fixture assertions (primary, required)
# =============================================================================


class TestRealFixturesExist:
    """The committed real fixtures and their provenance file must be present."""

    @pytest.mark.parametrize('provider', ['github', 'gitlab'])
    @pytest.mark.parametrize('kind', ['pass', 'fail'])
    def test_fixture_present_and_nonempty(self, provider: str, kind: str) -> None:
        # Arrange / Act
        path = _FIXTURE_ROOT / provider / f'{kind}.log'
        # Assert
        assert path.is_file(), f'missing real fixture: {path}'
        assert path.read_text(encoding='utf-8').strip(), f'empty real fixture: {path}'

    def test_source_provenance_present(self) -> None:
        # Arrange / Act
        source = _FIXTURE_ROOT / 'SOURCE.md'
        # Assert
        assert source.is_file(), 'SOURCE.md provenance file is required'
        assert source.read_text(encoding='utf-8').strip()


class TestRealGitHubFixtures:
    """``filter_log`` on the REAL GitHub-Actions-shaped pytest logs."""

    def test_fail_generic_extracts_error_portion(self) -> None:
        # Arrange
        raw = _read_fixture('github', 'fail')
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — the real failure markers survive filtering.
        assert 'AssertionError' in filtered
        assert 'IndexError: list index out of range' in filtered
        assert 'FAILED' in filtered
        # The filtered output is a strict subset (passing-test noise dropped).
        assert len(filtered.splitlines()) < len(raw.splitlines())
        assert 'test_create_interface PASSED' not in filtered

    def test_fail_default_style_matches_generic(self) -> None:
        # Arrange
        raw = _read_fixture('github', 'fail')
        # Act / Assert — default error_style is 'generic'.
        assert filter_log(raw) == filter_log(raw, 'generic')

    def test_fail_structured_mode_falls_back_to_generic(self) -> None:
        # Arrange — pytest output is not Maven; the maven parser finds no
        # structured errors, so filter_log falls back to the generic heuristic.
        raw = _read_fixture('github', 'fail')
        # Act
        structured = filter_log(raw, 'maven')
        generic = filter_log(raw, 'generic')
        # Assert
        assert structured == generic
        assert 'AssertionError' in structured

    def test_pass_yields_no_error_extraction(self) -> None:
        # Arrange
        raw = _read_fixture('github', 'pass')
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — no error/fail markers anywhere in the real pass log, so the
        # generic heuristic matches nothing and returns the trailing-context
        # fallback (no error portion extracted).
        assert 'AssertionError' not in filtered
        assert 'IndexError' not in filtered
        assert 'FAILED' not in filtered
        # Fallback is the raw log's trailing CONTEXT_LINES lines.
        expected_tail = '\n'.join(raw.splitlines()[-CONTEXT_LINES:])
        assert filtered == expected_tail


class TestRealGitLabFixtures:
    """``filter_log`` on the REAL GitLab-job-trace-shaped quality-gate logs."""

    def test_fail_generic_extracts_error_portion(self) -> None:
        # Arrange
        raw = _read_fixture('gitlab', 'fail')
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — the real ruff failure markers survive filtering.
        assert 'Found 3 errors.' in filtered
        assert 'ERROR: Job failed' in filtered
        assert len(filtered.splitlines()) < len(raw.splitlines())

    def test_pass_yields_no_error_extraction(self) -> None:
        # Arrange
        raw = _read_fixture('gitlab', 'pass')
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — clean run, no error markers; trailing-context fallback only.
        assert 'error' not in filtered.lower()
        assert 'fail' not in filtered.lower()
        expected_tail = '\n'.join(raw.splitlines()[-CONTEXT_LINES:])
        assert filtered == expected_tail


class TestRealBuildToolStructuredRouting:
    """``maven`` / ``gradle`` / ``npm`` modes on REAL build-tool logs."""

    def test_maven_failure_routes_and_surfaces_errors(self) -> None:
        # Arrange
        raw = _MAVEN_FAILURE.read_text(encoding='utf-8')
        # Act
        filtered = filter_log(raw, 'maven')
        # Assert — real Maven compile/test failures surface; passing-test noise
        # is dropped regardless of structured-render vs generic fallback.
        assert filtered.strip()
        assert 'cannot find symbol' in filtered
        assert 'HttpHandlerTest' not in filtered or 'Failures: 0' not in filtered

    def test_gradle_failure_routes_and_surfaces_errors(self) -> None:
        # Arrange
        raw = _GRADLE_FAILURE.read_text(encoding='utf-8')
        # Act
        filtered = filter_log(raw, 'gradle')
        # Assert
        assert filtered.strip()
        assert 'cannot find symbol' in filtered

    def test_npm_failure_routes_and_surfaces_errors(self) -> None:
        # Arrange
        raw = _NPM_ESLINT.read_text(encoding='utf-8')
        # Act
        filtered = filter_log(raw, 'npm')
        # Assert
        assert filtered.strip()
        # eslint error content is retained (structured render or generic fallback).
        assert 'no-unused-vars' in filtered or 'problems' in filtered

    def test_maven_success_has_no_error_extraction(self) -> None:
        # Arrange — a clean Maven build has no error-severity issues, so the
        # structured path returns None and filter_log falls back to generic.
        raw = _MAVEN_SUCCESS.read_text(encoding='utf-8')
        # Act
        structured = filter_log(raw, 'maven')
        generic = filter_log(raw, 'generic')
        # Assert — both paths agree; no fabricated error content.
        assert structured == generic


# =============================================================================
# Synthetic-unit assertions (supplement)
# =============================================================================


class TestGenericContextWindow:
    """Generic heuristic: window selection, overlap collapse, elision."""

    def test_single_match_keeps_symmetric_context(self) -> None:
        # Arrange — a single ERROR line surrounded by plenty of context.
        lines = [f'line {i}' for i in range(20)]
        lines[10] = 'ERROR: boom'
        raw = '\n'.join(lines)
        # Act
        filtered = filter_log(raw, 'generic')
        out_lines = filtered.splitlines()
        # Assert — CONTEXT_LINES on each side of the match are kept.
        assert 'ERROR: boom' in out_lines
        assert f'line {10 - CONTEXT_LINES}' in out_lines
        assert f'line {10 + CONTEXT_LINES}' in out_lines
        # Lines well outside the window are dropped (head elided).
        assert 'line 0' not in out_lines
        assert out_lines[0] == ELISION_MARKER

    def test_overlapping_windows_collapse_without_internal_elision(self) -> None:
        # Arrange — two matches close enough that their windows overlap.
        lines = [f'line {i}' for i in range(20)]
        lines[8] = 'first ERROR'
        lines[10] = 'second FAIL'
        raw = '\n'.join(lines)
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — a single contiguous block (no elision marker BETWEEN the two
        # matches, since the windows merged).
        assert 'first ERROR' in filtered
        assert 'second FAIL' in filtered
        between = filtered.split('first ERROR', 1)[1].split('second FAIL', 1)[0]
        assert ELISION_MARKER not in between

    def test_nonadjacent_windows_separated_by_elision(self) -> None:
        # Arrange — two matches far apart so their windows do NOT overlap.
        lines = [f'line {i}' for i in range(40)]
        lines[5] = 'ERROR one'
        lines[30] = 'ERROR two'
        raw = '\n'.join(lines)
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — an elision marker appears between the two kept windows.
        between = filtered.split('ERROR one', 1)[1].split('ERROR two', 1)[0]
        assert ELISION_MARKER in between

    def test_matches_are_case_insensitive(self) -> None:
        # Arrange
        raw = 'context\nan exception was raised\ncontext'
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — 'exception' matches the heuristic regardless of case.
        assert 'an exception was raised' in filtered

    def test_traceback_marker_matches(self) -> None:
        # Arrange
        lines = ['ok', 'ok', 'Traceback (most recent call last):', 'ok', 'ok']
        raw = '\n'.join(lines)
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert
        assert 'Traceback (most recent call last):' in filtered


class TestGenericEdgeCases:
    """Empty, no-error, and very-large generic inputs."""

    def test_empty_log_returns_empty(self) -> None:
        # Arrange / Act / Assert
        assert filter_log('', 'generic') == ''

    def test_no_error_log_returns_trailing_fallback(self) -> None:
        # Arrange — no heuristic match anywhere.
        lines = [f'clean line {i}' for i in range(10)]
        raw = '\n'.join(lines)
        # Act
        filtered = filter_log(raw, 'generic')
        # Assert — trailing CONTEXT_LINES lines as the fallback.
        assert filtered == '\n'.join(lines[-CONTEXT_LINES:])

    def test_unknown_style_treated_as_generic(self) -> None:
        # Arrange
        raw = 'a\nb\nFAIL here\nc\nd'
        # Act / Assert — an unrecognized style routes through generic.
        assert filter_log(raw, 'totally-unknown') == filter_log(raw, 'generic')

    def test_very_large_log_filters_to_match_windows(self) -> None:
        # Arrange — a large log with a single error buried in the middle.
        lines = [f'noise {i}' for i in range(5000)]
        lines[2500] = 'ERROR: the one real failure'
        raw = '\n'.join(lines)
        # Act
        filtered = filter_log(raw, 'generic')
        out_lines = filtered.splitlines()
        # Assert — output is tiny relative to input but contains the error.
        assert 'ERROR: the one real failure' in filtered
        assert len(out_lines) <= 2 * CONTEXT_LINES + 3


class TestSlugifyCheckName:
    """``slugify_check_name`` collision-free behavior and fallbacks."""

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('verify / verify', 'verify-verify'),
            ('Build (3.12)', 'build-3-12'),
            ('lint', 'lint'),
            ('UPPER CASE', 'upper-case'),
            ('a__b--c', 'a-b-c'),
            ('  leading and trailing  ', 'leading-and-trailing'),
            ('dependency-review / dependency-review', 'dependency-review-dependency-review'),
        ],
    )
    def test_known_slugs(self, name: str, expected: str) -> None:
        # Arrange / Act / Assert
        assert slugify_check_name(name) == expected

    @pytest.mark.parametrize('name', ['', '///', '   ', '!!!', '...'])
    def test_punctuation_only_falls_back(self, name: str) -> None:
        # Arrange / Act / Assert — no usable characters → stable fallback.
        assert slugify_check_name(name) == SLUG_FALLBACK

    def test_result_is_filename_safe(self) -> None:
        # Arrange / Act
        slug = slugify_check_name('Weird / Name: with @chars!')
        # Assert — only [a-z0-9-], no leading/trailing/repeated separators.
        assert all(c.isalnum() or c == '-' for c in slug)
        assert not slug.startswith('-')
        assert not slug.endswith('-')
        assert '--' not in slug

    def test_distinct_inputs_yield_distinct_slugs(self) -> None:
        # Arrange — two different check names must not collide after slugging.
        names = ['verify / verify', 'verify / lint', 'build (3.11)', 'build (3.12)']
        # Act
        slugs = [slugify_check_name(n) for n in names]
        # Assert
        assert len(set(slugs)) == len(slugs)

    def test_module_constant_fallback_value(self) -> None:
        # Arrange / Act / Assert — guard the documented fallback token.
        assert _ci_log_filter.SLUG_FALLBACK == 'check'
