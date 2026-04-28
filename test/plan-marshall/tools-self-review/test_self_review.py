#!/usr/bin/env python3
"""Tests for self_review.py — pre-submission self-review candidate surfacing."""

from pathlib import Path  # noqa: I001

import pytest
from self_review import (  # type: ignore[import-not-found]
    _detect_markdown_sections,
    _detect_regexes,
    _detect_symmetric_pairs,
    _detect_user_facing_strings,
    _iter_added_lines,
    _truncate,
)


# =============================================================================
# Test: _truncate
# =============================================================================


class TestTruncate:
    def test_under_limit(self):
        assert _truncate('abc', 10) == 'abc'

    def test_at_limit(self):
        assert _truncate('abcdefghij', 10) == 'abcdefghij'

    def test_over_limit_adds_ellipsis(self):
        result = _truncate('abcdefghijklmnop', 10)
        assert result == 'abcdefg...'
        assert len(result) == 10


# =============================================================================
# Test: _iter_added_lines (diff parsing)
# =============================================================================


class TestIterAddedLines:
    def test_extracts_added_lines_with_correct_post_image_line_no(self):
        diff = (
            'diff --git a/foo.py b/foo.py\n'
            'index 0000000..1111111 100644\n'
            '--- a/foo.py\n'
            '+++ b/foo.py\n'
            '@@ -1,3 +1,4 @@\n'
            ' line_one\n'
            '+inserted\n'
            ' line_two\n'
            ' line_three\n'
        )
        added = _iter_added_lines(diff)
        assert added == [('foo.py', 2, 'inserted')]

    def test_skips_removed_lines(self):
        diff = (
            '+++ b/bar.py\n'
            '@@ -1,2 +1,2 @@\n'
            '-removed_line\n'
            '+added_line\n'
            ' kept_line\n'
        )
        added = _iter_added_lines(diff)
        assert added == [('bar.py', 1, 'added_line')]

    def test_handles_multiple_files(self):
        diff = (
            '+++ b/a.py\n'
            '@@ -0,0 +1,1 @@\n'
            '+from_a\n'
            'diff --git a/b.py b/b.py\n'
            '+++ b/b.py\n'
            '@@ -0,0 +1,1 @@\n'
            '+from_b\n'
        )
        added = _iter_added_lines(diff)
        assert added == [('a.py', 1, 'from_a'), ('b.py', 1, 'from_b')]


# =============================================================================
# Test: _detect_regexes
# =============================================================================


class TestDetectRegexes:
    def test_detects_re_compile(self):
        added = [('foo.py', 5, 'pattern = re.compile(r"^[a-z]+$")')]
        out = _detect_regexes(added)
        assert len(out) == 1
        assert out[0]['file'] == 'foo.py'
        assert out[0]['line'] == 5
        assert '^[a-z]+$' in out[0]['pattern']

    def test_detects_fnmatch(self):
        added = [('foo.py', 10, 'if fnmatch.fnmatch(name, "*.py"): pass')]
        out = _detect_regexes(added)
        assert any(e['pattern'] == '*.py' for e in out)

    def test_detects_raw_string_with_metachars(self):
        added = [('foo.py', 1, '    PAT = r"\\d+\\.\\d+"')]
        out = _detect_regexes(added)
        assert len(out) == 1
        assert '\\d+\\.\\d+' in out[0]['pattern']

    def test_skips_plain_strings_without_metachars(self):
        added = [('foo.py', 1, '    name = "plain text"')]
        out = _detect_regexes(added)
        assert out == []

    def test_skips_non_python_non_markdown_files(self):
        added = [('foo.txt', 1, 'pattern = re.compile(r"^x$")')]
        out = _detect_regexes(added)
        assert out == []


# =============================================================================
# Test: _detect_user_facing_strings
# =============================================================================


class TestDetectUserFacingStrings:
    def test_detects_print_argument(self):
        added = [('foo.py', 5, '    print("Hello, world")')]
        out = _detect_user_facing_strings(added)
        assert any(e['context'] == 'print' and e['text'] == 'Hello, world' for e in out)

    def test_detects_argparse_help(self):
        added = [('foo.py', 5, '    parser.add_argument("--foo", help="Set the foo flag")')]
        out = _detect_user_facing_strings(added)
        assert any(
            e['context'] == 'argparse_help' and 'Set the foo flag' in e['text'] for e in out
        )

    def test_detects_argparse_description(self):
        added = [('foo.py', 5, 'parser = argparse.ArgumentParser(description="Tool to do X")')]
        out = _detect_user_facing_strings(added)
        assert any(e['context'] == 'argparse_description' for e in out)

    def test_detects_raise_message(self):
        added = [('foo.py', 5, '    raise ValueError("bad input shape")')]
        out = _detect_user_facing_strings(added)
        assert any(
            e['context'] == 'raise_message' and 'bad input shape' in e['text'] for e in out
        )

    def test_detects_markdown_heading(self):
        added = [('doc.md', 3, '## Section Two')]
        out = _detect_user_facing_strings(added)
        assert out == [
            {'file': 'doc.md', 'line': 3, 'context': 'markdown_heading', 'text': 'Section Two'}
        ]

    def test_detects_markdown_bullet(self):
        added = [('doc.md', 5, '- bullet item one')]
        out = _detect_user_facing_strings(added)
        assert any(e['context'] == 'markdown_bullet' and e['text'] == 'bullet item one' for e in out)

    def test_detects_docstring_after_def(self):
        added = [
            ('foo.py', 1, 'def my_func():'),
            ('foo.py', 2, '    """Docstring text here."""'),
        ]
        out = _detect_user_facing_strings(added)
        assert any(e['context'] == 'docstring' for e in out)


# =============================================================================
# Test: _detect_markdown_sections
# =============================================================================


class TestDetectMarkdownSections:
    def test_emits_entry_with_siblings(self, tmp_path: Path):
        # Set up post-image markdown with parent/child structure.
        md = tmp_path / 'docs' / 'guide.md'
        md.parent.mkdir()
        md.write_text(
            '# Top\n'
            '\n'
            '## Section A\n'
            '\n'
            '## Section B\n'
            '\n'
            '## Section C\n'
        )
        # Pretend Section B (line 5) was added.
        added = [('docs/guide.md', 5, '## Section B')]
        out = _detect_markdown_sections(added, tmp_path)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == 'docs/guide.md'
        assert entry['line'] == 5
        assert entry['heading'] == 'Section B'
        # Siblings of Section B at depth 2 under "Top": Section A and Section C.
        assert 'Section A' in entry['siblings']
        assert 'Section C' in entry['siblings']
        assert 'Section B' not in entry['siblings']

    def test_no_siblings_when_only_one_peer(self, tmp_path: Path):
        md = tmp_path / 'lone.md'
        md.write_text('# Only Top\n\n## Single Child\n')
        added = [('lone.md', 3, '## Single Child')]
        out = _detect_markdown_sections(added, tmp_path)
        assert len(out) == 1
        assert out[0]['siblings'] == ''

    def test_skips_non_md_paths(self, tmp_path: Path):
        added = [('foo.py', 1, '## Not a heading')]
        out = _detect_markdown_sections(added, tmp_path)
        assert out == []


# =============================================================================
# Test: _detect_symmetric_pairs
# =============================================================================


class TestDetectSymmetricPairs:
    @pytest.mark.parametrize(
        ('source_name', 'expected_partner'),
        [
            ('save_state', 'load_state'),
            ('load_state', 'save_state'),
            ('init_context', 'restore_context'),
            ('push_frame', 'pop_frame'),
            ('acquire_lock', 'release_lock'),
            ('open_socket', 'close_socket'),
            ('start_timer', 'stop_timer'),
        ],
    )
    def test_detects_each_pairing(self, source_name: str, expected_partner: str):
        added = [('foo.py', 1, f'def {source_name}(self):')]
        out = _detect_symmetric_pairs(added)
        assert len(out) == 1
        assert out[0]['name'] == source_name
        assert out[0]['partner'] == expected_partner

    def test_skips_function_without_pair_token(self):
        added = [('foo.py', 1, 'def compute_value(x):')]
        out = _detect_symmetric_pairs(added)
        assert out == []

    def test_skips_non_python_files(self):
        added = [('doc.md', 1, 'def save_state(self):')]
        out = _detect_symmetric_pairs(added)
        assert out == []


# =============================================================================
# Test: empty diff edge case
# =============================================================================


class TestEmptyDiff:
    def test_iter_added_lines_returns_empty_for_empty_diff(self):
        assert _iter_added_lines('') == []

    def test_detectors_return_empty_for_empty_added_list(self, tmp_path: Path):
        assert _detect_regexes([]) == []
        assert _detect_user_facing_strings([]) == []
        assert _detect_markdown_sections([], tmp_path) == []
        assert _detect_symmetric_pairs([]) == []
