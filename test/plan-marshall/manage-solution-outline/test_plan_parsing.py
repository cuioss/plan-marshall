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

from _plan_parsing import (  # noqa: E402
    _extract_affected_files,
    _extract_profiles,
    _slugify_section_name,
    parse_document_sections,
)


# =============================================================================
# _slugify_section_name() — character class handling
# =============================================================================


class TestSlugifySectionNameCharacterClasses:
    """Verify how `_slugify_section_name` collapses non-alnum character runs."""

    def test_parentheses_collapse_to_single_underscore(self):
        heading = 'Suggested fix (two options)'

        slug = _slugify_section_name(heading)

        # parens and the spaces around them collapse to single underscores;
        # the trailing ')' becomes a trailing '_' that is stripped by .strip('_').
        assert slug == 'suggested_fix_two_options'

    def test_brackets_collapse_to_single_underscore(self):
        heading = 'Section [draft]'

        slug = _slugify_section_name(heading)

        assert slug == 'section_draft'

    def test_ampersand_collapses_with_surrounding_spaces(self):
        heading = 'Tools & Tactics'

        slug = _slugify_section_name(heading)

        # `' & '` (space-amp-space) is a single non-alnum run -> one '_'.
        assert slug == 'tools_tactics'

    def test_slash_collapses_to_underscore(self):
        heading = 'input/output'

        slug = _slugify_section_name(heading)

        assert slug == 'input_output'

    def test_multiple_spaces_collapse_to_single_underscore(self):
        # three internal spaces.
        heading = 'a   b'

        slug = _slugify_section_name(heading)

        # the run of three spaces collapses to one '_'.
        assert slug == 'a_b'

    def test_trailing_punctuation_is_stripped_leading_is_preserved(self):
        heading = '!hello!'

        slug = _slugify_section_name(heading)

        # both '!' chars become '_' via the regex; the trailing '_' is
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
        # every character is non-alnum.
        heading = '!@#$%'

        slug = _slugify_section_name(heading)

        # the entire string collapses to one '_', and .rstrip('_')
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
        # German umlaut. The character class `[a-z0-9_-]` is ASCII-only,
        # so the lowercase 'ü' is collapsed even though it is a letter in Unicode.
        heading = 'Über'

        slug = _slugify_section_name(heading)

        # 'Ü' lowercases to 'ü' which is replaced by '_'. The leading
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
        # `heading` is a parametrized input.

        first = _slugify_section_name(heading)
        second = _slugify_section_name(first)

        # applying the helper twice MUST yield the same result as
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
        # a minimal markdown document with one H2 heading containing
        # parens. The implementation must call `_slugify_section_name` on the
        # heading text so the resulting key has no parens.
        content = '## Heading with (parens)\nbody\n'

        sections = parse_document_sections(content)

        # the slugified key is present, and the legacy un-slugified
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
        # exact regression case from the lesson
        # `lesson-2026-04-26-22-005`: a "Suggested fix (two options)" heading
        # was producing the un-slugified key, breaking section lookups.
        content = '## Suggested fix (two options)\nbody'

        sections = parse_document_sections(content)

        # slugified key present, un-slugified key absent.
        assert 'suggested_fix_two_options' in sections, (
            f'Expected slugified key "suggested_fix_two_options" in sections; got keys {list(sections.keys())}'
        )
        assert 'suggested_fix_(two_options)' not in sections, (
            'Regression: un-slugified key "suggested_fix_(two_options)" present. '
            'parse_document_sections must route heading text through _slugify_section_name.'
        )


# =============================================================================
# _extract_affected_files() — per-file intent marker parsing
# =============================================================================


class TestExtractAffectedFilesIntent:
    """Verify `_extract_affected_files` returns {path, intent} objects."""

    @pytest.mark.parametrize('intent', ['read', 'write-new', 'write-replace', 'delete'])
    def test_parses_each_valid_intent_marker(self, intent):
        content = f'**Affected files:**\n- `src/main/java/A.java` ({intent})\n'
        result = _extract_affected_files(content)
        assert result == [{'path': 'src/main/java/A.java', 'intent': intent}]

    def test_parses_multiple_entries_with_distinct_intents(self):
        content = (
            '**Affected files:**\n'
            '- `src/main/java/New.java` (write-new)\n'
            '- `src/main/java/Old.java` (write-replace)\n'
            '- `src/main/java/Gone.java` (delete)\n'
        )
        result = _extract_affected_files(content)
        assert result == [
            {'path': 'src/main/java/New.java', 'intent': 'write-new'},
            {'path': 'src/main/java/Old.java', 'intent': 'write-replace'},
            {'path': 'src/main/java/Gone.java', 'intent': 'delete'},
        ]

    def test_entry_without_marker_yields_none_intent(self):
        content = '**Affected files:**\n- `src/main/java/A.java`\n'
        result = _extract_affected_files(content)
        assert result == [{'path': 'src/main/java/A.java', 'intent': None}]

    def test_surrounding_whitespace_is_stripped(self):
        content = '**Affected files:**\n-   `src/main/java/A.java`   (read)  \n'
        result = _extract_affected_files(content)
        assert result == [{'path': 'src/main/java/A.java', 'intent': 'read'}]

    def test_no_affected_files_section_returns_empty(self):
        result = _extract_affected_files('No affected files here.')
        assert result == []


# =============================================================================
# _extract_profiles() — inline bucket-comment tolerance (P3b regex drift)
# =============================================================================


class TestExtractProfilesBucketComment:
    """Verify `_extract_profiles` parses the documented inline bucket form.

    The canonical documented form records the file-type bucket as a trailing
    same-line HTML comment on the ``**Profiles:**`` line:
    ``**Profiles:** <!-- bucket: documentation_only -->`` followed by the
    ``- `` bullet list. The widened validator regex MUST parse this form while
    still extracting profiles only from the bullets — the comment text must
    never be mis-read as a profile.
    """

    def test_inline_bucket_comment_form_parses_profiles(self):
        content = (
            '**Profiles:** <!-- bucket: documentation_only -->\n'
            '- implementation\n'
            '- module_testing\n'
        )
        result = _extract_profiles(content)
        assert result == ['implementation', 'module_testing']

    @pytest.mark.parametrize(
        'bucket',
        [
            'production_only',
            'test_only',
            'documentation_only',
            'mixed_code',
            'mixed_with_docs',
            'unknown',
        ],
    )
    def test_inline_bucket_comment_parses_for_every_documented_bucket(self, bucket):
        # the widened `[^\n]*` lead-in must tolerate ANY documented
        # bucket value on the `**Profiles:**` line, not just the one literal
        # ('documentation_only') the happy-path test uses. The six bucket names
        # are the canonical vocabulary from
        # phase-3-outline/standards/outline-workflow-detail.md § File-type classifier.
        content = f'**Profiles:** <!-- bucket: {bucket} -->\n- implementation\n'

        result = _extract_profiles(content)

        # profiles come only from the bullet; the bucket token never leaks.
        assert result == ['implementation'], (
            f'Widened regex must parse the inline bucket form for bucket {bucket!r}; '
            f'got {result!r}'
        )
        assert bucket not in result

    def test_inline_arbitrary_trailing_text_parses_profiles(self):
        # the widening is `[^\n]*` (any non-newline run), not a regex
        # that hard-codes the `<!-- bucket: ... -->` shape. Arbitrary trailing
        # prose on the `**Profiles:**` line must still let the bullets parse.
        content = '**Profiles:**   trailing notes — see deliverable 6\n- implementation\n'

        result = _extract_profiles(content)

        assert result == ['implementation']

    def test_inline_bucket_comment_not_mis_parsed_as_profile(self):
        # Negative case: the bucket token ("documentation_only") and the comment
        # markers must not leak into the returned profile list.
        content = '**Profiles:** <!-- bucket: documentation_only -->\n- implementation\n'
        result = _extract_profiles(content)
        assert result == ['implementation']
        assert 'documentation_only' not in result
        assert all('bucket' not in profile for profile in result)

    def test_plain_form_without_comment_still_parses(self):
        # Regression guard: the widened regex must not break the comment-free form.
        content = '**Profiles:**\n- implementation\n- verification\n'
        result = _extract_profiles(content)
        assert result == ['implementation', 'verification']

    def test_indented_first_bullet_after_inline_comment_parses(self):
        # the `\s*` segment after the line break tolerates leading
        # whitespace before the first bullet. Pair it with the inline comment
        # to exercise both widening segments together.
        content = '**Profiles:** <!-- bucket: documentation_only -->\n  - implementation\n'

        result = _extract_profiles(content)

        assert result == ['implementation']

    def test_inline_comment_form_is_case_insensitive(self):
        # `_extract_profiles` compiles its search with re.IGNORECASE,
        # so a lower-cased `**profiles:**` heading still parses. Guard the flag
        # against accidental removal during a future regex edit.
        content = '**profiles:** <!-- bucket: documentation_only -->\n- implementation\n'

        result = _extract_profiles(content)

        assert result == ['implementation']

    def test_no_profiles_section_returns_empty(self):
        result = _extract_profiles('No profiles section here.')
        assert result == []
