#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""
Tests for the shared `_plan_parsing` module.

Focuses on the `_slugify_section_name()` helper algorithm and the
`parse_document_sections()` round-trip behavior. The module lives at
`marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py`
and is imported directly after a local `sys.path.insert` (matching the
established pattern in `test/plan-marshall/plan-marshall/test_phase_handshake.py`)
so the underscore-prefixed module is reachable by name even though ruff would
otherwise classify it as third-party (it lives outside the configured `src`
roots).

Although `_slugify_section_name` carries a leading underscore (module-private
by convention), it is the canonical slug helper intended for direct import by
sibling modules and tests; importing it directly keeps the behavioral contract
under explicit test coverage rather than only exercising it through
`parse_document_sections`.
"""

import sys

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-solution-outline', '_plan_parsing.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _plan_parsing import _slugify_section_name, parse_document_sections  # noqa: E402


# =============================================================================
# _slugify_section_name() — character class handling
# =============================================================================


class TestSlugifySectionNameCharacterClasses:
    """Verify how `_slugify_section_name` collapses non-alnum character runs."""

    def test_parentheses_collapse_to_single_underscore(self):
        # Arrange
        heading = 'Suggested fix (two options)'

        # Act
        slug = _slugify_section_name(heading)

        # Assert — parens and the spaces around them collapse to single underscores;
        # the trailing ')' becomes a trailing '_' that is stripped by .strip('_').
        assert slug == 'suggested_fix_two_options'

    def test_brackets_collapse_to_single_underscore(self):
        # Arrange
        heading = 'Section [draft]'

        # Act
        slug = _slugify_section_name(heading)

        # Assert
        assert slug == 'section_draft'

    def test_ampersand_collapses_with_surrounding_spaces(self):
        # Arrange
        heading = 'Tools & Tactics'

        # Act
        slug = _slugify_section_name(heading)

        # Assert — `' & '` (space-amp-space) is a single non-alnum run -> one '_'.
        assert slug == 'tools_tactics'

    def test_slash_collapses_to_underscore(self):
        # Arrange
        heading = 'input/output'

        # Act
        slug = _slugify_section_name(heading)

        # Assert
        assert slug == 'input_output'

    def test_multiple_spaces_collapse_to_single_underscore(self):
        # Arrange — three internal spaces.
        heading = 'a   b'

        # Act
        slug = _slugify_section_name(heading)

        # Assert — the run of three spaces collapses to one '_'.
        assert slug == 'a_b'

    def test_trailing_punctuation_is_stripped_leading_is_preserved(self):
        # Arrange
        heading = '!hello!'

        # Act
        slug = _slugify_section_name(heading)

        # Assert — both '!' chars become '_' via the regex; the trailing '_' is
        # stripped by .rstrip('_'), but the leading '_' is preserved so that
        # inputs whose first char is non-alnum stay distinguishable from inputs
        # that already start with an alphanumeric. (See helper docstring for
        # the sentinel-key rationale.)
        assert slug == '_hello'


# =============================================================================
# _slugify_section_name() — edge cases
# =============================================================================


class TestSlugifySectionNameEdgeCases:
    """Edge cases that document the helper's behavior at the boundaries."""

    def test_all_punctuation_heading_returns_empty_string(self):
        # Arrange — every character is non-alnum.
        heading = '!@#$%'

        # Act
        slug = _slugify_section_name(heading)

        # Assert — the entire string collapses to one '_', and .rstrip('_')
        # removes that single trailing underscore, leaving the empty string.
        # Documenting actual behavior: callers MUST be prepared to handle ''
        # as a section key for headings with no alphanumeric content.
        assert slug == '', (
            'All-punctuation headings are expected to slugify to "" because the '
            "single '_' produced by the regex is the only character and is "
            "removed by .rstrip('_'). If this changes, callers that special-case "
            'empty section keys must be reviewed.'
        )

    def test_non_ascii_letters_are_treated_as_non_alnum(self):
        # Arrange — German umlaut. The character class `[a-z0-9_-]` is ASCII-only,
        # so the lowercase 'ü' is collapsed even though it is a letter in Unicode.
        heading = 'Über'

        # Act
        slug = _slugify_section_name(heading)

        # Assert — 'Ü' lowercases to 'ü' which is replaced by '_'. The leading
        # '_' is preserved because the helper only rstrip's, never lstrip's.
        # This is a documented limitation: non-ASCII letters are lossy.
        assert slug == '_ber', (
            'ASCII invariant: the regex `[^a-z0-9_-]` treats non-ASCII letters '
            'such as "ü" as non-alnum and replaces them with "_". The leading '
            "'_' survives because the helper uses .rstrip('_') only — see "
            'helper docstring for the sentinel-key rationale.'
        )

    @pytest.mark.parametrize(
        'heading',
        [
            'Suggested fix (two options)',
            'Section [draft]',
            'Tools & Tactics',
            'input/output',
            'a   b',
            '!hello!',
            '!@#$%',
            'Über',
            'already_a_slug',
            '',
        ],
    )
    def test_idempotence(self, heading):
        # Arrange — `heading` is a parametrized input.

        # Act
        first = _slugify_section_name(heading)
        second = _slugify_section_name(first)

        # Assert — applying the helper twice MUST yield the same result as
        # applying it once. This guarantees stable section keys when the
        # helper is composed with itself (e.g., normalization passes).
        assert first == second, (
            f'Idempotence violated for input {heading!r}: '
            f'first pass produced {first!r}, second pass produced {second!r}'
        )


# =============================================================================
# parse_document_sections() — round-trip regression
# =============================================================================


class TestParseDocumentSectionsRoundTrip:
    """Verify that `parse_document_sections` keys go through `_slugify_section_name`."""

    def test_parens_in_heading_produce_paren_free_key(self):
        # Arrange — a minimal markdown document with one H2 heading containing
        # parens. The implementation must call `_slugify_section_name` on the
        # heading text so the resulting key has no parens.
        content = '## Heading with (parens)\nbody\n'

        # Act
        sections = parse_document_sections(content)

        # Assert — the slugified key is present, and the legacy un-slugified
        # key (with literal parens) is absent. This protects against regressions
        # where the heading-to-key transform skips slugification.
        assert 'heading_with_parens' in sections, (
            f'Expected slugified key "heading_with_parens" in sections; got keys {list(sections.keys())}'
        )
        assert 'heading_with_(parens)' not in sections, (
            'Unexpected un-slugified key "heading_with_(parens)" present; '
            'parse_document_sections must call _slugify_section_name on headings.'
        )

    def test_lesson_regression_suggested_fix_two_options(self):
        # Arrange — exact regression case from the lesson
        # `lesson-2026-04-26-22-005`: a "Suggested fix (two options)" heading
        # was producing the un-slugified key, breaking section lookups.
        content = '## Suggested fix (two options)\nbody'

        # Act
        sections = parse_document_sections(content)

        # Assert — slugified key present, un-slugified key absent.
        assert 'suggested_fix_two_options' in sections, (
            f'Expected slugified key "suggested_fix_two_options" in sections; '
            f'got keys {list(sections.keys())}'
        )
        assert 'suggested_fix_(two_options)' not in sections, (
            'Regression: un-slugified key "suggested_fix_(two_options)" present. '
            'parse_document_sections must route heading text through _slugify_section_name.'
        )
