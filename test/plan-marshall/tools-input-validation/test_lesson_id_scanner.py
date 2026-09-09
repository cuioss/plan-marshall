#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the lesson-ID reference scanner in input_validation.

Covers the three public helpers added under "Lesson-ID reference scanner
(live-anchored)" in input_validation.py:

  - scan_lesson_id_tokens(text)
  - verify_lesson_ids_exist(tokens)
  - verify_lesson_id_regex_against_inventory()

plus the typed exceptions LessonInventoryUnavailable and
LessonRegexAnchoringError. Blank-line separation conveys the AAA structure
and the tests use module-private helpers (no conftest.py per the repo's
_fixtures.py convention).

The inventory fixtures here are copied from live ``manage-lessons list``
output rather than hand-typed, so the regex shape is asserted against real
data even at test-collection time.
"""

import re
import subprocess

import input_validation as _iv
import pytest
from input_validation import (
    LESSON_ID_RE,
    LessonInventoryUnavailable,
    LessonRegexAnchoringError,
    scan_lesson_id_tokens,
    verify_lesson_id_regex_against_inventory,
    verify_lesson_ids_exist,
)

# =============================================================================
# Fixture data — sample IDs sourced from real `manage-lessons list` output.
# Hand-typed shapes go in BAD_TOKENS only.
# =============================================================================

REAL_LESSON_IDS = (
    '2026-04-24-12-003',
    '2026-04-29-10-001',
    '2026-04-30-23-001',
    '2026-05-03-21-002',
)


def _fake_completed_process(stdout: str, returncode: int = 0, stderr: str = ''):
    """Build a CompletedProcess-shaped object suitable for patching subprocess.run."""
    return subprocess.CompletedProcess(args=['mock'], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture(autouse=True)
def _reset_anchor_cache(monkeypatch):
    """Reset the per-process ``_lesson_anchor_checked`` flag between tests.

    The runtime anchor is cached for performance, but every test case
    here exercises a different inventory shape, so we need a clean
    starting slate or later tests would silently skip the anchor check.
    """
    monkeypatch.setattr(_iv, '_lesson_anchor_checked', False)
    yield
    monkeypatch.setattr(_iv, '_lesson_anchor_checked', False)


# =============================================================================
# Test: scan_lesson_id_tokens
# =============================================================================


class TestScanLessonIdTokens:
    """scan_lesson_id_tokens(text) → list[str]."""

    @pytest.fixture()
    def live_lesson_ids(self, monkeypatch):
        """Pin the live lesson-id set the scanner validates against."""
        monkeypatch.setattr(_iv, '_list_live_lesson_ids', lambda: list(REAL_LESSON_IDS))

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('', []),
            ('plain prose, no identifiers here', []),
            ('see lesson 2026-04-29-10-001 for details', ['2026-04-29-10-001']),
            (
                'lessons 2026-05-03-21-002, 2026-04-29-10-001, and 2026-04-30-23-001 all apply here',
                ['2026-05-03-21-002', '2026-04-29-10-001', '2026-04-30-23-001'],
            ),
            (
                '2026-04-24-12-003 leads off, then trailing 2026-05-03-21-002',
                ['2026-04-24-12-003', '2026-05-03-21-002'],
            ),
            # 4-segment YYYY-MM-DD-NNN must NOT be picked up by a 5-segment scanner.
            ('reference 2026-04-29-001 looks lessonish but is 4-segment', []),
            # When an extra "-1" trails the 5-segment shape, the embedded boundary
            # uses non-digit lookarounds, and "-" is not a digit, so the canonical
            # 5-segment substring still matches. The trailing extension is rejected
            # as part of the token but does NOT block the inner match.
            ('see 2026-04-29-10-001-1 here', ['2026-04-29-10-001']),
            # A leading digit fused to the year (no separator) trips the negative
            # lookbehind in _LESSON_ID_EMBEDDED_RE: `(?<!\d)`.
            ('garbage12026-04-29-10-001', []),
            # The last segment is greedy ([0-9]+), so additional trailing digits
            # before any boundary are absorbed into the same token rather than
            # yielding a partial 3-digit match.
            ('see 2026-04-29-10-0019999 here', ['2026-04-29-10-0019999']),
            # The canonical regex permits 1+ digits in the last segment.
            ('shortest viable id 2026-04-29-10-1 matches', ['2026-04-29-10-1']),
        ],
        ids=[
            'empty-text',
            'prose-carrying-no-identifier',
            'one-id-embedded-in-prose',
            'three-ids-returned-in-the-order-the-text-carries-them',
            'ids-at-the-very-start-and-the-very-end',
            'a-four-segment-lookalike-does-not-match',
            'a-trailing-sixth-segment-does-not-block-the-inner-match',
            'a-digit-fused-to-the-year-blocks-the-match',
            'extra-trailing-digits-are-absorbed-into-the-last-segment',
            'a-single-digit-last-segment-matches',
        ],
    )
    def test_scan_returns_the_ids_the_text_carries(self, live_lesson_ids, text, expected):
        """Every id the text carries comes back, in order, and nothing else does."""
        assert scan_lesson_id_tokens(text) == expected

    def test_anchor_failure_propagates(self, monkeypatch):
        # Inventory has IDs but none match the canonical regex.
        bad_inventory = ['not-a-lesson-id', 'also-bogus']
        monkeypatch.setattr(_iv, '_list_live_lesson_ids', lambda: bad_inventory)

        with pytest.raises(LessonRegexAnchoringError):
            scan_lesson_id_tokens('lesson 2026-04-29-10-001 here')

    def test_inventory_unavailable_degrades_with_warning(self, monkeypatch, capsys):
        """When the inventory subprocess is unavailable (e.g., fresh CI checkout
        with no .plan/execute-script.py), the scanner anchor degrades to a
        warning + no-op rather than raising, so callers that don't strictly
        need the live anchor check can still proceed."""

        def _raise():
            raise LessonInventoryUnavailable('subprocess died')

        monkeypatch.setattr(_iv, '_list_live_lesson_ids', _raise)

        # The scanner runs successfully because the anchor degraded.
        result = scan_lesson_id_tokens('lesson 2026-04-29-10-001 here')

        # The regex still matches (anchor's no-op preserves scanner
        # functionality) AND the warning was emitted to stderr.
        assert result == ['2026-04-29-10-001']
        captured = capsys.readouterr()
        assert 'live inventory unavailable' in captured.err
        assert 'subprocess died' in captured.err


# =============================================================================
# Test: verify_lesson_ids_exist
# =============================================================================


class TestVerifyLessonIdsExist:
    """verify_lesson_ids_exist(tokens) → dict[token, present_bool]."""

    @pytest.fixture()
    def live_lesson_ids(self, monkeypatch):
        """Pin the live lesson-id set the scanner validates against."""
        monkeypatch.setattr(_iv, '_list_live_lesson_ids', lambda: list(REAL_LESSON_IDS))

    @pytest.mark.parametrize(
        ('tokens', 'expected'),
        [
            (
                ['2026-04-29-10-001', '2026-05-03-21-002'],
                {'2026-04-29-10-001': True, '2026-05-03-21-002': True},
            ),
            (['2099-12-31-23-999'], {'2099-12-31-23-999': False}),
            (
                ['2026-04-30-23-001', '2099-01-01-00-001'],
                {'2026-04-30-23-001': True, '2099-01-01-00-001': False},
            ),
            ([], {}),
            # One entry, not three duplicate keys.
            (
                ['2026-04-29-10-001', '2026-04-29-10-001', '2026-04-29-10-001'],
                {'2026-04-29-10-001': True},
            ),
        ],
        ids=[
            'every-token-is-in-the-inventory',
            'a-phantom-token-is-reported-absent',
            'present-and-phantom-tokens-in-one-call',
            'no-tokens-yields-no-entries',
            'a-repeated-token-yields-one-entry',
        ],
    )
    def test_each_token_is_reported_present_or_absent(self, live_lesson_ids, tokens, expected):
        """Each distinct token gets exactly one verdict against the live inventory."""
        assert verify_lesson_ids_exist(tokens) == expected

    def test_subprocess_failure_raises_typed_exception(self, monkeypatch):
        # Let the anchor pass via its own mock so we can isolate the second
        # call's failure. The implementation calls _list_live_lesson_ids twice
        # (once via the anchor, once via the existence check); the second call
        # must raise to surface as LessonInventoryUnavailable.
        call_state = {'count': 0}

        def _stub():
            call_state['count'] += 1
            if call_state['count'] == 1:
                return list(REAL_LESSON_IDS)
            raise LessonInventoryUnavailable('mocked subprocess failure on second call')

        monkeypatch.setattr(_iv, '_list_live_lesson_ids', _stub)

        with pytest.raises(LessonInventoryUnavailable):
            verify_lesson_ids_exist(['2026-04-29-10-001'])

    def test_subprocess_nonzero_exit_raises(self, monkeypatch):
        # Patch subprocess.run so the underlying _list_live_lesson_ids surfaces
        # a non-zero exit as LessonInventoryUnavailable. This exercises the real
        # exception-translation code path, not just our stub.
        monkeypatch.setattr(
            subprocess,
            'run',
            lambda *args, **kwargs: _fake_completed_process(stdout='', returncode=2, stderr='boom'),
        )

        with pytest.raises(LessonInventoryUnavailable):
            verify_lesson_ids_exist(['2026-04-29-10-001'])

    def test_subprocess_oserror_raises(self, monkeypatch):
        # Simulate the OSError branch (e.g., python3 not found).
        def _raise(*_args, **_kwargs):
            raise OSError('cannot exec python3')

        monkeypatch.setattr(subprocess, 'run', _raise)

        with pytest.raises(LessonInventoryUnavailable):
            verify_lesson_ids_exist(['2026-04-29-10-001'])


# =============================================================================
# Test: verify_lesson_id_regex_against_inventory (the runtime anchor)
# =============================================================================


class TestVerifyLessonIdRegexAgainstInventory:
    """verify_lesson_id_regex_against_inventory() — runtime regex/data anchor."""

    def test_passes_when_inventory_has_matching_ids(self, monkeypatch):
        monkeypatch.setattr(
            _iv,
            '_list_live_lesson_ids',
            lambda: list(REAL_LESSON_IDS),
        )

        # Should NOT raise.
        verify_lesson_id_regex_against_inventory()

        # Anchor cache flipped on.
        assert _iv._lesson_anchor_checked is True

    def test_passes_when_inventory_mixes_matching_and_other_shapes(self, monkeypatch):
        # At least one valid match must be enough.
        mixed = ['malformed-thing', '2026-04-29-10-001', 'also-bad']
        monkeypatch.setattr(_iv, '_list_live_lesson_ids', lambda: mixed)

        # Should NOT raise.
        verify_lesson_id_regex_against_inventory()

        assert _iv._lesson_anchor_checked is True

    def test_raises_when_inventory_has_only_wrong_shape_ids(self, monkeypatch):
        bogus = ['not-a-lesson', '12345', 'foo-bar-baz-qux-quux']
        monkeypatch.setattr(_iv, '_list_live_lesson_ids', lambda: bogus)

        with pytest.raises(LessonRegexAnchoringError) as excinfo:
            verify_lesson_id_regex_against_inventory()

        # Anchor must NOT cache on failure (so subsequent calls keep failing).
        assert _iv._lesson_anchor_checked is False
        # Error includes the regex pattern and at least one of the sample IDs.
        assert excinfo.value.regex == LESSON_ID_RE.pattern
        assert excinfo.value.sample_ids == bogus

    def test_empty_inventory_is_noop_and_warns(self, monkeypatch, capsys):
        monkeypatch.setattr(_iv, '_list_live_lesson_ids', lambda: [])

        # Should NOT raise.
        verify_lesson_id_regex_against_inventory()

        # Anchor cached so we don't re-spawn subprocess on every call.
        assert _iv._lesson_anchor_checked is True
        captured = capsys.readouterr()
        assert 'WARNING' in captured.err
        assert 'lesson-ID anchor' in captured.err

    def test_cached_result_skips_subsequent_subprocess_calls(self, monkeypatch):
        # Count how many times the inventory helper is invoked.
        call_count = {'n': 0}

        def _stub():
            call_count['n'] += 1
            return list(REAL_LESSON_IDS)

        monkeypatch.setattr(_iv, '_list_live_lesson_ids', _stub)

        verify_lesson_id_regex_against_inventory()
        verify_lesson_id_regex_against_inventory()
        verify_lesson_id_regex_against_inventory()

        # Only the first call hit the helper; subsequent calls used cache.
        assert call_count['n'] == 1

    def test_inventory_unavailable_degrades_with_warning(self, monkeypatch, capsys):
        """When _list_live_lesson_ids raises LessonInventoryUnavailable
        (typical on a fresh CI checkout with no .plan/execute-script.py),
        the anchor degrades: warns on stderr, marks itself as checked, and
        returns. The scanner must remain functional even when the live-data
        check can't run, so downstream callers don't crash on bootstrap
        environments."""

        def _raise():
            raise LessonInventoryUnavailable('subprocess unavailable')

        monkeypatch.setattr(_iv, '_list_live_lesson_ids', _raise)

        # Anchor returns normally instead of raising.
        verify_lesson_id_regex_against_inventory()

        # Warning emitted AND cache flipped (so subsequent calls don't keep
        # re-spawning the doomed subprocess).
        captured = capsys.readouterr()
        assert 'live inventory unavailable' in captured.err
        assert 'subprocess unavailable' in captured.err
        assert _iv._lesson_anchor_checked is True


# =============================================================================
# Test: existing validate_lesson_id / is_valid_lesson_id behavior unchanged
# =============================================================================


class TestExistingLessonIdValidatorsUnchanged:
    """Smoke tests confirming the new scanner did not regress the existing
    validate_lesson_id / is_valid_lesson_id contract that other scripts rely on.
    """

    def test_validate_lesson_id_accepts_real_ids(self):
        from input_validation import validate_lesson_id

        for lid in REAL_LESSON_IDS:
            assert validate_lesson_id(lid) == lid

    def test_is_valid_lesson_id_rejects_bogus(self):
        from input_validation import is_valid_lesson_id

        assert is_valid_lesson_id('not-an-id') is False
        assert is_valid_lesson_id('') is False
        assert is_valid_lesson_id('2026-04-29-001') is False  # 4-segment

    def test_lesson_id_re_matches_every_real_id(self):
        # Sanity: the canonical regex matches every fixture ID — same invariant
        # the runtime anchor enforces against live data.
        for lid in REAL_LESSON_IDS:
            assert re.fullmatch(LESSON_ID_RE.pattern, lid) is not None
