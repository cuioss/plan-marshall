#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for self_review.py — pre-submission self-review candidate surfacing."""

import subprocess  # noqa: I001
from pathlib import Path

import pytest
# The shared resolver-contract fixtures live under ``test/_shared/``, the
# bundle-neutral home for cross-bundle test helpers (also on mypy_path), so
# the helper is imported here rather than duplicated per bundle.
from _resolve_project_dir_fixtures import (
    assert_sentinel_accepted,
    assert_worktree_face_routes_through_resolver,
)
from _self_review_patterns import CANDIDATE_LISTS, candidate_list_prose
from self_review import (
    _build_parser,
    _compose_candidate_output,
    _detect_advertised_form_help_strings,
    _detect_contract_sources,
    _detect_count_prose,
    _detect_description_vs_body,
    _detect_flag_guard_pairs,
    _detect_keep_markers,
    _detect_markdown_sections,
    _detect_ordinal_references,
    _detect_producer_consumer,
    _detect_regexes,
    _detect_same_document_consistency,
    _detect_scan_derived_keys,
    _detect_source_of_truth,
    _detect_symmetric_pairs,
    _detect_touched_claims,
    _detect_unguarded_boundaries,
    _detect_user_facing_strings,
    _detect_worked_example_pairs,
    _diff_hunks,
    _find_skill_dir,
    _iter_added_lines,
    _iter_changed_line_pairs,
    _load_test_tree_blob,
    _name_in_test_blob,
    _resolve_footprint,
    _run_git,
    _symmetric_pair_has_test,
    _truncate,
    _worked_example_pairs,
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
        diff = '+++ b/bar.py\n@@ -1,2 +1,2 @@\n-removed_line\n+added_line\n kept_line\n'
        added = _iter_added_lines(diff)
        assert added == [('bar.py', 1, 'added_line')]

    def test_handles_multiple_files(self):
        diff = '+++ b/a.py\n@@ -0,0 +1,1 @@\n+from_a\ndiff --git a/b.py b/b.py\n+++ b/b.py\n@@ -0,0 +1,1 @@\n+from_b\n'
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
        assert any(e['context'] == 'argparse_help' and 'Set the foo flag' in e['text'] for e in out)

    def test_detects_argparse_description(self):
        added = [('foo.py', 5, 'parser = argparse.ArgumentParser(description="Tool to do X")')]
        out = _detect_user_facing_strings(added)
        assert any(e['context'] == 'argparse_description' for e in out)

    def test_detects_raise_message(self):
        added = [('foo.py', 5, '    raise ValueError("bad input shape")')]
        out = _detect_user_facing_strings(added)
        assert any(e['context'] == 'raise_message' and 'bad input shape' in e['text'] for e in out)

    def test_detects_markdown_heading(self):
        added = [('doc.md', 3, '## Section Two')]
        out = _detect_user_facing_strings(added)
        assert out == [{'file': 'doc.md', 'line': 3, 'context': 'markdown_heading', 'text': 'Section Two'}]

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
        md.write_text('# Top\n\n## Section A\n\n## Section B\n\n## Section C\n')
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
    def test_detects_each_pairing(
        self, source_name: str, expected_partner: str, tmp_path: Path
    ):
        added = [('foo.py', 1, f'def {source_name}(self):')]
        out = _detect_symmetric_pairs(added, tmp_path)
        assert len(out) == 1
        assert out[0]['name'] == source_name
        assert out[0]['partner'] == expected_partner
        # No test/ tree under tmp_path -> Tier-2 missing-test signal.
        assert out[0]['test_present'] is False

    def test_skips_function_without_pair_token(self, tmp_path: Path):
        added = [('foo.py', 1, 'def compute_value(x):')]
        out = _detect_symmetric_pairs(added, tmp_path)
        assert out == []

    def test_skips_non_python_files(self, tmp_path: Path):
        added = [('doc.md', 1, 'def save_state(self):')]
        out = _detect_symmetric_pairs(added, tmp_path)
        assert out == []

    def test_entry_carries_test_present_field(self, tmp_path: Path):
        # Every emitted entry MUST carry the new test_present key alongside the
        # pre-existing file/line/name/partner fields.
        added = [('foo.py', 1, 'def save_state(self):')]
        out = _detect_symmetric_pairs(added, tmp_path)
        assert len(out) == 1
        assert set(out[0].keys()) == {
            'file',
            'line',
            'name',
            'partner',
            'test_present',
        }

    def test_test_present_true_when_test_tree_references_name(
        self, tmp_path: Path
    ):
        # A matching test reference in the test tree -> test_present=true.
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_thing.py').write_text(
            'def test_save_state():\n    assert save_state() is None\n',
            encoding='utf-8',
        )
        added = [('foo.py', 1, 'def save_state(self):')]
        out = _detect_symmetric_pairs(added, tmp_path)
        assert len(out) == 1
        assert out[0]['name'] == 'save_state'
        assert out[0]['test_present'] is True

    def test_test_present_false_when_no_reference(self, tmp_path: Path):
        # A test tree that never mentions the function -> Tier-2 false signal.
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_other.py').write_text(
            'def test_unrelated():\n    assert compute_value() == 1\n',
            encoding='utf-8',
        )
        added = [('foo.py', 1, 'def save_state(self):')]
        out = _detect_symmetric_pairs(added, tmp_path)
        assert len(out) == 1
        assert out[0]['test_present'] is False


# =============================================================================
# Test: _symmetric_pair_has_test
# =============================================================================


class TestSymmetricPairHasTest:
    def test_returns_true_on_word_boundary_match(self, tmp_path: Path):
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text(
            'def test_save():\n    save()\n', encoding='utf-8'
        )
        assert _symmetric_pair_has_test('save', tmp_path) is True

    def test_substring_does_not_satisfy_search(self, tmp_path: Path):
        # `save_state` in the test tree must NOT satisfy a search for `save`:
        # the word-boundary guard rejects the substring-only overlap.
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text(
            'def test_save_state():\n    save_state()\n', encoding='utf-8'
        )
        assert _symmetric_pair_has_test('save', tmp_path) is False

    def test_longer_identifier_substring_does_not_match(self, tmp_path: Path):
        # Symmetric guard on the other side: searching for `save_state` must
        # not match `save_state_v2` references.
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text(
            'def test_save_state_v2():\n    save_state_v2()\n', encoding='utf-8'
        )
        assert _symmetric_pair_has_test('save_state', tmp_path) is False

    def test_missing_test_dir_returns_false(self, tmp_path: Path):
        assert _symmetric_pair_has_test('save_state', tmp_path) is False

    def test_no_reference_in_test_tree_returns_false(self, tmp_path: Path):
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text(
            'def test_unrelated():\n    pass\n', encoding='utf-8'
        )
        assert _symmetric_pair_has_test('save_state', tmp_path) is False

    def test_searches_nested_test_files(self, tmp_path: Path):
        nested = tmp_path / 'test' / 'sub' / 'deep'
        nested.mkdir(parents=True)
        (nested / 'test_deep.py').write_text(
            'def test_load_state():\n    load_state()\n', encoding='utf-8'
        )
        assert _symmetric_pair_has_test('load_state', tmp_path) is True

    def test_ignores_non_python_test_files(self, tmp_path: Path):
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'fixture.txt').write_text('save_state()\n', encoding='utf-8')
        assert _symmetric_pair_has_test('save_state', tmp_path) is False


# =============================================================================
# Test: _load_test_tree_blob
# =============================================================================


class TestLoadTestTreeBlob:
    def test_missing_test_dir_returns_empty(self, tmp_path: Path):
        assert _load_test_tree_blob(tmp_path) == ''

    def test_concatenates_all_python_test_files(self, tmp_path: Path):
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text('alpha_token()\n', encoding='utf-8')
        (test_dir / 'test_b.py').write_text('beta_token()\n', encoding='utf-8')
        blob = _load_test_tree_blob(tmp_path)
        assert 'alpha_token' in blob
        assert 'beta_token' in blob

    def test_collects_nested_python_files(self, tmp_path: Path):
        nested = tmp_path / 'test' / 'sub' / 'deep'
        nested.mkdir(parents=True)
        (nested / 'test_deep.py').write_text('deep_token()\n', encoding='utf-8')
        assert 'deep_token' in _load_test_tree_blob(tmp_path)

    def test_excludes_non_python_files(self, tmp_path: Path):
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'fixture.txt').write_text('txt_token()\n', encoding='utf-8')
        assert 'txt_token' not in _load_test_tree_blob(tmp_path)

    def test_reads_each_file_once(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Regression guard for the O(N*M) disk-I/O fix: building the blob must
        # read each test file exactly once, regardless of how many membership
        # queries later run against it.
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text('save_state()\n', encoding='utf-8')
        (test_dir / 'test_b.py').write_text('load_state()\n', encoding='utf-8')

        read_counts: dict[str, int] = {}
        original_read_text = Path.read_text

        def _counting_read_text(self: Path, *args: object, **kwargs: object) -> str:
            read_counts[self.name] = read_counts.get(self.name, 0) + 1
            return original_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, 'read_text', _counting_read_text)
        _load_test_tree_blob(tmp_path)
        assert read_counts == {'test_a.py': 1, 'test_b.py': 1}


# =============================================================================
# Test: _name_in_test_blob
# =============================================================================


class TestNameInTestBlob:
    def test_empty_blob_returns_false(self):
        assert _name_in_test_blob('save', '') is False

    def test_word_boundary_match_returns_true(self):
        assert _name_in_test_blob('save', 'def test_save():\n    save()\n') is True

    def test_substring_only_returns_false(self):
        assert _name_in_test_blob('save', 'def test_save_state():\n    save_state()\n') is False

    def test_longer_identifier_substring_returns_false(self):
        assert _name_in_test_blob('save_state', 'save_state_v2()\n') is False

    def test_blob_match_equivalent_to_symmetric_pair_has_test(self, tmp_path: Path):
        # The cached-blob path must agree with the single-query entry point so
        # the perf refactor is behaviour-preserving.
        test_dir = tmp_path / 'test'
        test_dir.mkdir()
        (test_dir / 'test_a.py').write_text(
            'def test_load_state():\n    load_state()\n', encoding='utf-8'
        )
        blob = _load_test_tree_blob(tmp_path)
        assert _name_in_test_blob('load_state', blob) == _symmetric_pair_has_test(
            'load_state', tmp_path
        )
        assert _name_in_test_blob('load_state', blob) is True


# =============================================================================
# Test: _detect_flag_guard_pairs
# =============================================================================


class TestDetectFlagGuardPairs:
    def test_guard_covering_both_forms_is_both(self):
        added = [
            ('inject.py', 5, "    if '--plan-id' in args:"),
            ('inject.py', 6, "    if '--plan-id=' in args:"),
        ]
        out = _detect_flag_guard_pairs(added)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == 'inject.py'
        assert entry['flag'] == '--plan-id'
        assert entry['forms_covered'] == 'both'
        # line records the first guard occurrence for the flag.
        assert entry['line'] == 5

    def test_guard_covering_only_space_form_is_space(self):
        added = [('inject.py', 10, "    if '--project-dir' in args:")]
        out = _detect_flag_guard_pairs(added)
        assert len(out) == 1
        assert out[0]['flag'] == '--project-dir'
        assert out[0]['forms_covered'] == 'space'
        assert out[0]['line'] == 10

    def test_guard_covering_only_equals_form_is_equals(self):
        added = [('inject.py', 12, "    if '--project-dir=' in argv:")]
        out = _detect_flag_guard_pairs(added)
        assert len(out) == 1
        assert out[0]['flag'] == '--project-dir'
        assert out[0]['forms_covered'] == 'equals'

    def test_startswith_guard_is_recognized(self):
        added = [('inject.py', 3, '    if arg.startswith("--plan-id="):')]
        out = _detect_flag_guard_pairs(added)
        assert len(out) == 1
        assert out[0]['flag'] == '--plan-id'
        assert out[0]['forms_covered'] == 'equals'

    def test_asymmetric_pair_one_both_one_single_form(self):
        # Replays the PR #508 scenario: --plan-id covers both forms, while its
        # sibling --project-dir covers only the space form.
        added = [
            ('inject.py', 1, "    if '--plan-id' in args or '--plan-id=' in args:"),
            ('inject.py', 4, "    if '--project-dir' in args:"),
        ]
        out = _detect_flag_guard_pairs(added)
        by_flag = {e['flag']: e['forms_covered'] for e in out}
        assert by_flag == {'--plan-id': 'both', '--project-dir': 'space'}

    def test_no_flag_guard_returns_empty(self):
        added = [('inject.py', 1, '    total = len(items) + 1')]
        out = _detect_flag_guard_pairs(added)
        assert out == []

    def test_skips_non_python_files(self):
        added = [('doc.md', 1, "if '--plan-id' in args:")]
        out = _detect_flag_guard_pairs(added)
        assert out == []

    def test_every_entry_carries_required_fields(self):
        added = [("inject.py", 7, "    if '--flag' in args:")]
        out = _detect_flag_guard_pairs(added)
        assert len(out) == 1
        assert set(out[0].keys()) == {'file', 'line', 'flag', 'forms_covered'}


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
        assert _detect_symmetric_pairs([], tmp_path) == []
        assert _detect_flag_guard_pairs([]) == []
        assert _detect_producer_consumer([]) == []
        assert _detect_source_of_truth([]) == []
        assert _detect_same_document_consistency([]) == []
        assert _detect_description_vs_body([], tmp_path) == []


# =============================================================================
# Test: _find_skill_dir & _detect_contract_sources
# =============================================================================


def _build_skill_fixture(root: Path) -> Path:
    """Build a fixture project tree with one skill containing SKILL.md, standards/,
    and a script. Returns the project root."""
    project = root / 'project'
    skill = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill'
    skill.mkdir(parents=True)
    (skill / 'SKILL.md').write_text('---\nname: my-skill\n---\n# My Skill\n')
    standards = skill / 'standards'
    standards.mkdir()
    (standards / 'rule-a.md').write_text('# Rule A\n')
    (standards / 'rule-b.md').write_text('# Rule B\n```json\n{"x": 1}\n```\n')
    scripts = skill / 'scripts'
    scripts.mkdir()
    (scripts / 'do_thing.py').write_text('def main(): pass\n')
    # Outside-skill file
    (project / 'README.md').write_text('# Project\n')
    return project


class TestFindSkillDir:
    def test_finds_enclosing_skill_for_script(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        modified = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill' / 'scripts' / 'do_thing.py'
        skill_dir = _find_skill_dir(modified, project)
        assert skill_dir == project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill'

    def test_returns_none_for_file_outside_any_skill(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        modified = project / 'README.md'
        assert _find_skill_dir(modified, project) is None

    def test_returns_none_when_path_escapes_project(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        outside = tmp_path / 'somewhere_else.py'
        outside.write_text('')
        assert _find_skill_dir(outside, project) is None


class TestDetectContractSources:
    def test_emits_skill_md_and_standards_for_in_skill_file(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/do_thing.py'
        contract, schema = _detect_contract_sources([rel], project, radius=3)
        assert len(contract) == 1
        entry = contract[0]
        assert entry['file'] == rel
        sources = entry['sources']
        assert 'marketplace/bundles/b1/skills/my-skill/SKILL.md' in sources
        assert 'marketplace/bundles/b1/skills/my-skill/standards/rule-a.md' in sources
        assert 'marketplace/bundles/b1/skills/my-skill/standards/rule-b.md' in sources

    def test_modified_files_outside_skill_emit_no_contract_entry(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        contract, _ = _detect_contract_sources(['README.md'], project, radius=3)
        assert contract == []

    def test_schema_bearing_files_detect_fenced_json(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/do_thing.py'
        _, schema = _detect_contract_sources([rel], project, radius=3)
        # rule-b.md contains a fenced JSON block; rule-a.md does not.
        files = {entry['file']: entry['format'] for entry in schema}
        assert 'marketplace/bundles/b1/skills/my-skill/standards/rule-b.md' in files
        assert files['marketplace/bundles/b1/skills/my-skill/standards/rule-b.md'] == 'json'
        assert 'marketplace/bundles/b1/skills/my-skill/standards/rule-a.md' not in files

    def test_radius_zero_only_includes_immediate_directory(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/do_thing.py'
        # radius=0 means only the modified file's own parent dir is scanned.
        # do_thing.py's parent is scripts/, which has no markdown files.
        _, schema = _detect_contract_sources([rel], project, radius=0)
        assert schema == []

    def test_deduplicates_schema_bearing_files_across_modified_files(self, tmp_path: Path):
        project = _build_skill_fixture(tmp_path)
        rels = [
            'marketplace/bundles/b1/skills/my-skill/scripts/do_thing.py',
            'marketplace/bundles/b1/skills/my-skill/SKILL.md',
        ]
        _, schema = _detect_contract_sources(rels, project, radius=3)
        files = [entry['file'] for entry in schema]
        # rule-b.md should appear at most once even though two modified files
        # are within radius of it.
        assert files.count('marketplace/bundles/b1/skills/my-skill/standards/rule-b.md') == 1

    def test_toon_block_is_recognized_alongside_json(self, tmp_path: Path):
        project = tmp_path / 'project'
        skill = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: my-skill\n---\n')
        standards = skill / 'standards'
        standards.mkdir()
        (standards / 'toon-schema.md').write_text('# Schema\n```toon\nstatus: ok\n```\n')
        scripts = skill / 'scripts'
        scripts.mkdir()
        (scripts / 'mod.py').write_text('')
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/mod.py'
        _, schema = _detect_contract_sources([rel], project, radius=3)
        files = {entry['file']: entry['format'] for entry in schema}
        assert files.get('marketplace/bundles/b1/skills/my-skill/standards/toon-schema.md') == 'toon'

    @staticmethod
    def _build_sibling_script_fixture(root: Path) -> Path:
        """Build a project with a sibling skill 'sib-skill' (carrying SKILL.md +
        a script) and a separate workflow doc that references it. Returns the
        project root."""
        project = root / 'project'
        sib = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'sib-skill'
        (sib / 'scripts').mkdir(parents=True)
        (sib / 'SKILL.md').write_text('---\nname: sib-skill\n---\n# Sib\n')
        (sib / 'scripts' / 'do_thing.py').write_text('def main(): pass\n')
        # A workflow doc living in a DIFFERENT skill directory.
        wf = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'consumer' / 'workflow'
        wf.mkdir(parents=True)
        (wf.parent / 'SKILL.md').write_text('---\nname: consumer\n---\n# Consumer\n')
        return project

    def test_doc_prose_reference_surfaces_sibling_skill_md(self, tmp_path: Path):
        # An .md doc whose added lines reference a sibling script AND a TOON
        # field surfaces that script's SKILL.md as a contract source.
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'marketplace/bundles/b1/skills/consumer/workflow/run.md'
        added = [
            (rel, 1, 'Run python3 .plan/execute-script.py b1:sib-skill:do_thing run'),
            (rel, 2, 'Parse the {status} field from the TOON output.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        by_file = {e['file']: e['sources'] for e in contract}
        assert rel in by_file
        assert 'marketplace/bundles/b1/skills/sib-skill/SKILL.md' in by_file[rel]

    def test_doc_prose_reference_unioned_with_structural_sources(self, tmp_path: Path):
        # The doc lives inside the 'consumer' skill (structural source) AND
        # references the sibling script (doc-prose source). Both must appear.
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'marketplace/bundles/b1/skills/consumer/workflow/run.md'
        added = [
            (rel, 1, 'execute-script.py b1:sib-skill:do_thing run --plan-id X'),
            (rel, 2, 'On {error} the run aborts.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        by_file = {e['file']: e['sources'] for e in contract}
        sources = by_file[rel]
        # Structural source: the consumer skill's own SKILL.md.
        assert 'marketplace/bundles/b1/skills/consumer/SKILL.md' in sources
        # Doc-prose source: the referenced sibling script's SKILL.md.
        assert 'marketplace/bundles/b1/skills/sib-skill/SKILL.md' in sources

    def test_dangling_notation_surfaces_nothing(self, tmp_path: Path):
        # A notation whose SKILL.md does not exist on disk surfaces no source.
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'README.md'
        (project / 'README.md').write_text('# Project\n')
        added = [
            (rel, 1, 'execute-script.py b1:does-not-exist:ghost run'),
            (rel, 2, 'Reads the {status} field.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        assert contract == []

    def test_notation_without_toon_field_surfaces_nothing(self, tmp_path: Path):
        # An execute-script notation with NO TOON-field token in the added lines
        # does not surface the sibling SKILL.md (both signals required).
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'README.md'
        (project / 'README.md').write_text('# Project\n')
        added = [
            (rel, 1, 'execute-script.py b1:sib-skill:do_thing run'),
            (rel, 2, 'Plain prose with no field token.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        assert contract == []

    def test_toon_field_without_notation_surfaces_nothing(self, tmp_path: Path):
        # A TOON-field token with NO execute-script notation surfaces nothing.
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'README.md'
        (project / 'README.md').write_text('# Project\n')
        added = [
            (rel, 1, 'Parse the {status} field from somewhere.'),
            (rel, 2, 'No script notation here.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        assert contract == []

    def test_signals_on_separate_added_lines_are_both_honored(self, tmp_path: Path):
        # The notation and the TOON-field token need not share a line.
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'README.md'
        (project / 'README.md').write_text('# Project\n')
        added = [
            (rel, 5, 'execute-script.py b1:sib-skill:do_thing run'),
            (rel, 9, 'Later the doc mentions {error} handling.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        by_file = {e['file']: e['sources'] for e in contract}
        assert 'marketplace/bundles/b1/skills/sib-skill/SKILL.md' in by_file[rel]

    def test_added_none_keeps_augmentation_inert(self, tmp_path: Path):
        # Callers that pass no diff content get only structural sources — the
        # content-aware augmentation is inert (backward-compatible default).
        project = _build_skill_fixture(tmp_path)
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/do_thing.py'
        contract, _ = _detect_contract_sources([rel], project, radius=3)
        assert len(contract) == 1
        assert contract[0]['file'] == rel

    def test_py_modified_file_with_both_signals_is_not_augmented(self, tmp_path: Path):
        # The doc-prose augmentation is .md-only: a modified .py file carrying
        # BOTH an execute-script notation and a {field} token in its added lines
        # must NOT surface the sibling SKILL.md. A top-level .py outside any
        # skill isolates the .md-only guard from the directory-structural branch.
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'top_level.py'
        (project / 'top_level.py').write_text('# module\n')
        added = [
            (rel, 1, '# execute-script.py b1:sib-skill:do_thing run'),
            (rel, 2, '# reads the {status} field'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        assert contract == []

    def test_repeated_notation_in_doc_surfaces_single_source(self, tmp_path: Path):
        # The same {bundle}:{skill} notation referenced on multiple added lines
        # is deduplicated to one source entry (set + sorted in the resolver).
        project = self._build_sibling_script_fixture(tmp_path)
        rel = 'README.md'
        (project / 'README.md').write_text('# Project\n')
        added = [
            (rel, 1, 'execute-script.py b1:sib-skill:do_thing run'),
            (rel, 2, 'Again: execute-script.py b1:sib-skill:do_thing surface'),
            (rel, 3, 'Parse the {status} field.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        by_file = {e['file']: e['sources'] for e in contract}
        sib = 'marketplace/bundles/b1/skills/sib-skill/SKILL.md'
        assert by_file[rel].split('; ').count(sib) == 1

    def test_two_distinct_notations_surface_both_sources(self, tmp_path: Path):
        # A doc referencing two distinct sibling scripts (both with an on-disk
        # SKILL.md) surfaces both SKILL.md paths, sorted and unioned.
        project = self._build_sibling_script_fixture(tmp_path)
        # Add a second sibling skill with its own SKILL.md + script.
        sib2 = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'sib-two'
        (sib2 / 'scripts').mkdir(parents=True)
        (sib2 / 'SKILL.md').write_text('---\nname: sib-two\n---\n# Sib Two\n')
        (sib2 / 'scripts' / 'other.py').write_text('def main(): pass\n')
        rel = 'README.md'
        (project / 'README.md').write_text('# Project\n')
        added = [
            (rel, 1, 'execute-script.py b1:sib-skill:do_thing run'),
            (rel, 2, 'execute-script.py b1:sib-two:other run'),
            (rel, 3, 'Both emit a {status} field.'),
        ]
        contract, _ = _detect_contract_sources([rel], project, radius=3, added=added)
        by_file = {e['file']: e['sources'] for e in contract}
        sources = by_file[rel]
        assert 'marketplace/bundles/b1/skills/sib-skill/SKILL.md' in sources
        assert 'marketplace/bundles/b1/skills/sib-two/SKILL.md' in sources


class TestContractRadiusMonotonicBreadth:
    """The --contract-radius dial (wired by the coverage-gathering contract's
    scope rung in pre-submission-self-review) must produce strictly wider
    schema-bearing breadth at a larger radius. Proves the scope→radius wiring
    has a real effect the workflow relies on (D13)."""

    @staticmethod
    def _build_nested_schema_fixture(root: Path) -> tuple[Path, str]:
        """Build a tree where a schema-bearing markdown sits several levels ABOVE
        the modified file, so a small radius excludes it and a large radius
        includes it. Returns (project_root, modified_rel_path)."""
        project = root / 'project'
        # A schema-bearing md at the bundle level — several dirs above the file.
        bundle = project / 'marketplace' / 'bundles' / 'b1'
        bundle.mkdir(parents=True)
        (bundle / 'bundle-schema.md').write_text('# Bundle Schema\n```json\n{"k": 1}\n```\n')
        # The modified file sits deep under the bundle, in a scripts/ dir with no md.
        scripts = bundle / 'skills' / 'my-skill' / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / 'mod.py').write_text('def main(): pass\n')
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/mod.py'
        return project, rel

    def test_larger_radius_surfaces_strictly_wider_schema_set(self, tmp_path: Path):
        project, rel = self._build_nested_schema_fixture(tmp_path)

        _, schema_narrow = _detect_contract_sources([rel], project, radius=1)
        _, schema_wide = _detect_contract_sources([rel], project, radius=5)
        narrow_files = {entry['file'] for entry in schema_narrow}
        wide_files = {entry['file'] for entry in schema_wide}

        # The bundle-level schema is out of reach at radius 1 but in reach at
        # radius 5; the wide set is a strict superset of the narrow set.
        schema_path = 'marketplace/bundles/b1/bundle-schema.md'
        assert schema_path not in narrow_files
        assert schema_path in wide_files
        assert narrow_files < wide_files


class TestSchemaBearingVendoredExclusion:
    """The schema-bearing walk (``_collect_schema_bearing_within_radius`` for
    ``radius > 0``) must never descend into vendored / large / generated trees
    (``node_modules``, ``.git``, ``target``, ``.plan``, ``__pycache__``). A
    vendored ``*.md`` carrying a fenced schema block within the anchor radius
    must NOT be surfaced, while a genuine in-radius schema-bearing ``*.md``
    outside every vendored tree is still surfaced. Guards the diff-scoped-design
    boundedness fix for the surfacer's sole unscoped recursive walk."""

    @staticmethod
    def _build_vendored_fixture(root: Path, vendored_dir: str) -> tuple[Path, str]:
        """Build a bundle carrying a genuine schema-bearing md AND a vendored
        subtree whose md also carries a fenced schema block, several levels above
        the modified file. Returns (project_root, modified_rel_path)."""
        project = root / 'project'
        bundle = project / 'marketplace' / 'bundles' / 'b1'
        bundle.mkdir(parents=True)
        # Genuine, non-vendored schema-bearing md at the bundle level.
        (bundle / 'genuine-schema.md').write_text('# Genuine\n```json\n{"k": 1}\n```\n')
        # Vendored subtree with its own schema-bearing md — must be pruned.
        vendored = bundle / vendored_dir / 'pkg'
        vendored.mkdir(parents=True)
        (vendored / 'vendored-schema.md').write_text('# Vendored\n```json\n{"v": 2}\n```\n')
        # The modified file sits deep under the bundle, in a scripts/ dir with no md.
        scripts = bundle / 'skills' / 'my-skill' / 'scripts'
        scripts.mkdir(parents=True)
        (scripts / 'mod.py').write_text('def main(): pass\n')
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/mod.py'
        return project, rel

    @pytest.mark.parametrize('vendored_dir', ['node_modules', '.git', 'target', '.plan', '__pycache__'])
    def test_vendored_schema_md_is_not_surfaced(self, tmp_path: Path, vendored_dir: str):
        project, rel = self._build_vendored_fixture(tmp_path, vendored_dir)

        _, schema = _detect_contract_sources([rel], project, radius=5)
        surfaced = {entry['file'] for entry in schema}

        genuine = 'marketplace/bundles/b1/genuine-schema.md'
        vendored = f'marketplace/bundles/b1/{vendored_dir}/pkg/vendored-schema.md'
        # The genuine in-radius schema-bearing md is still surfaced.
        assert genuine in surfaced
        # The vendored subtree md is pruned — the walk never descends into it.
        assert vendored not in surfaced

    def test_genuine_nested_schema_below_vendored_sibling_still_surfaced(self, tmp_path: Path):
        # A genuine schema-bearing md nested OUTSIDE a vendored sibling directory
        # is still reached by the recursive walk — pruning removes only the
        # vendored subtree, not the rest of the anchor's tree.
        project, rel = self._build_vendored_fixture(tmp_path, 'node_modules')
        nested = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill'
        (nested / 'nested-schema.md').write_text('# Nested\n```toon\nstatus: ok\n```\n')

        _, schema = _detect_contract_sources([rel], project, radius=5)
        surfaced = {entry['file'] for entry in schema}

        assert 'marketplace/bundles/b1/skills/my-skill/nested-schema.md' in surfaced
        assert 'marketplace/bundles/b1/node_modules/pkg/vendored-schema.md' not in surfaced


# =============================================================================
# Test: _detect_keep_markers
# =============================================================================


class TestDetectKeepMarkers:
    def test_marker_with_token_still_in_post_image_emits_keep_protected(self, tmp_path: Path):
        # Post-image contains both the marker and the protected identifier on
        # another line. The detector should emit a keep_protected candidate
        # and the identifier should appear in protected_identifiers.
        md = tmp_path / 'doc.md'
        md.write_text(
            '# Doc\n'
            '<!-- self-review: keep my_token -->\n'
            'The token my_token must remain.\n'
        )
        added = [('doc.md', 2, '<!-- self-review: keep my_token -->')]
        candidates, protected = _detect_keep_markers(added, tmp_path)
        assert len(candidates) == 1
        entry = candidates[0]
        assert entry['file'] == 'doc.md'
        assert entry['line'] == 2
        assert entry['identifier'] == 'my_token'
        assert entry['kind'] == 'keep_protected'
        assert protected == ['my_token']

    def test_marker_with_token_removed_from_post_image_emits_keep_violation(self, tmp_path: Path):
        # Post-image contains the marker only; the protected identifier no
        # longer appears anywhere outside the marker comment. Detector should
        # emit a keep_violation candidate at the marker line and the
        # identifier should NOT appear in protected_identifiers.
        md = tmp_path / 'doc.md'
        md.write_text(
            '# Doc\n'
            '<!-- self-review: keep dropped_token -->\n'
            'Some prose that no longer references it.\n'
        )
        added = [('doc.md', 2, '<!-- self-review: keep dropped_token -->')]
        candidates, protected = _detect_keep_markers(added, tmp_path)
        assert len(candidates) == 1
        entry = candidates[0]
        assert entry['file'] == 'doc.md'
        assert entry['line'] == 2
        assert entry['identifier'] == 'dropped_token'
        assert entry['kind'] == 'keep_violation'
        assert protected == []

    def test_marker_syntax_variations_and_multiple_markers_in_same_file(self, tmp_path: Path):
        # Three markers on different lines:
        #   1. extra whitespace inside the marker
        #   2. canonical syntax
        #   3. another marker, same file
        # All three identifiers remain grep-able in the post-image. All three
        # must be recognized and appear in protected_identifiers (deduped,
        # sorted).
        md = tmp_path / 'doc.md'
        md.write_text(
            '# Doc\n'
            '<!--  self-review:   keep   alpha_token   -->\n'
            '<!-- self-review: keep beta_token -->\n'
            'Refers to alpha_token and beta_token and gamma_token.\n'
            '<!-- self-review: keep gamma_token -->\n'
        )
        added = [
            ('doc.md', 2, '<!--  self-review:   keep   alpha_token   -->'),
            ('doc.md', 3, '<!-- self-review: keep beta_token -->'),
            ('doc.md', 5, '<!-- self-review: keep gamma_token -->'),
        ]
        candidates, protected = _detect_keep_markers(added, tmp_path)
        assert len(candidates) == 3
        identifiers = {c['identifier'] for c in candidates}
        assert identifiers == {'alpha_token', 'beta_token', 'gamma_token'}
        # Every candidate must be keep_protected (all tokens grep-able).
        assert all(c['kind'] == 'keep_protected' for c in candidates)
        # protected_identifiers is sorted and deduplicated.
        assert protected == ['alpha_token', 'beta_token', 'gamma_token']


# =============================================================================
# Test: _diff_hunks merge-base anchor (d29024 staged-diff redirect)
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '--initial-branch=main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test User')


def _commit(repo: Path, message: str, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', message)


class TestDiffHunksMergeBaseAnchor:
    """``_diff_hunks`` diffs the working tree against the base..HEAD merge-base.

    The contract has three load-bearing properties:

    * uncommitted (staged + unstaged) pre-submission changes are still surfaced
      (the diff TARGET is the working tree, preserving the pre-commit timing);
    * commits absorbed from the base branch (at/below the merge-base) are
      excluded from the surfaced diff (the diff ANCHOR is the merge-base);
    * a merge-base resolution failure falls back to the two-dot diff without
      returning an empty surface.
    """

    def _build_absorb_repo(self, repo: Path) -> None:
        """feature branch with a genuine plan change + an absorbed base commit."""
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})

        _git(repo, 'checkout', '-b', 'feature')
        _commit(repo, 'plan change', {'plan_change.py': 'print("plan_marker_line")\n'})

        _git(repo, 'checkout', 'main')
        _commit(repo, 'upstream only', {'upstream_only.py': 'print("upstream_marker_line")\n'})

        _git(repo, 'checkout', 'feature')
        _git(repo, 'merge', 'main', '--no-edit')

    def test_uncommitted_changes_are_surfaced(self, tmp_path):
        """A staged-but-uncommitted change must appear in the surfaced diff."""
        repo = tmp_path / 'repo'
        self._build_absorb_repo(repo)

        # Pre-submission edit: staged, not yet committed.
        (repo / 'new_uncommitted.py').write_text('print("uncommitted_marker")\n')
        _git(repo, 'add', 'new_uncommitted.py')

        diff_text = _diff_hunks(repo, 'main')
        added = _iter_added_lines(diff_text)
        files = {entry[0] for entry in added}
        assert 'new_uncommitted.py' in files, (
            'uncommitted (staged) pre-submission change must be surfaced'
        )

    def test_absorbed_base_commit_is_excluded(self, tmp_path):
        """A commit absorbed from the base branch must NOT appear in the diff."""
        repo = tmp_path / 'repo'
        self._build_absorb_repo(repo)

        diff_text = _diff_hunks(repo, 'main')
        added = _iter_added_lines(diff_text)
        files = {entry[0] for entry in added}
        # The genuine plan change is present.
        assert 'plan_change.py' in files
        # The absorbed-upstream file sits at/below the merge-base and is excluded.
        assert 'upstream_only.py' not in files, (
            'absorbed-merge content (at/below merge-base) must be excluded'
        )

    def test_merge_base_resolution_failure_falls_back_to_two_dot(self, tmp_path):
        """When merge-base resolution fails, fall back to the two-dot diff.

        With no HEAD commits relative to a nonexistent ref, merge-base cannot
        resolve; the function must still produce a non-empty diff surface from
        the two-dot fallback rather than returning ''.
        """
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        _commit(repo, 'plan change', {'plan_change.py': 'print("plan_marker_line")\n'})

        # merge-base against a nonexistent ref fails to resolve; the anchor
        # falls back to the base_branch arg ('main'), which DOES resolve, so the
        # two-dot diff still yields the feature change.
        diff_text = _diff_hunks(repo, 'main')
        assert diff_text != '', 'fallback must not return an empty surface'
        added = _iter_added_lines(diff_text)
        files = {entry[0] for entry in added}
        assert 'plan_change.py' in files

    def test_run_git_helper_resolves_merge_base(self, tmp_path):
        """Sanity: the merge-base the anchor relies on resolves for this fixture."""
        repo = tmp_path / 'repo'
        self._build_absorb_repo(repo)
        rc, out, _ = _run_git(repo, 'merge-base', 'main', 'HEAD')
        assert rc == 0
        assert out.strip(), 'merge-base must resolve to a non-empty sha'


class TestResolveFootprint:
    """``_resolve_footprint`` derives the live plan footprint via compute-footprint.

    The footprint replaces the old ``references.modified_files`` ledger read: it
    is the on-demand ``{base}...HEAD`` ∪ porcelain set read straight from the
    worktree, used to restrict the surfaced diff to plan-touched files.
    """

    def test_returns_live_branch_diff_and_porcelain(self, tmp_path):
        """Footprint = committed plan-branch diff ∪ uncommitted working-tree state."""
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})

        _git(repo, 'checkout', '-b', 'feature')
        _commit(repo, 'plan change', {'committed.py': 'print("committed")\n'})

        # An uncommitted working-tree file: must appear via the porcelain union.
        (repo / 'uncommitted.py').write_text('print("uncommitted")\n')

        footprint = _resolve_footprint(repo, 'main')

        assert 'committed.py' in footprint
        assert 'uncommitted.py' in footprint
        assert 'base.txt' not in footprint

    def test_empty_on_git_error(self, outside_repo_dir):
        """A non-git directory yields an empty footprint (do-not-filter)."""
        # ``not_a_repo`` must be OUTSIDE the repo: pytest's tmp_path now roots
        # under the repo-local --basetemp, where the footprint resolves against
        # the surrounding worktree instead of erroring into an empty result.
        not_a_repo = outside_repo_dir / 'plain'
        not_a_repo.mkdir()

        footprint = _resolve_footprint(not_a_repo, 'main')

        assert footprint == []


# =============================================================================
# Test: _detect_producer_consumer
# =============================================================================


class TestDetectProducerConsumer:
    def test_producer_without_consumer_surfaces_candidate(self):
        # An output['key'] = ... producer with no consumer anywhere -> candidate.
        added = [('mod.py', 5, "    output['dangling'] = compute()")]
        out = _detect_producer_consumer(added)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == 'mod.py'
        assert entry['line'] == 5
        assert entry['key'] == 'dangling'
        assert entry['consumed'] is False

    def test_double_quoted_producer_is_detected(self):
        added = [('mod.py', 2, '    output["only"] = value')]
        out = _detect_producer_consumer(added)
        assert len(out) == 1
        assert out[0]['key'] == 'only'

    def test_subscript_read_consumes_producer(self):
        # The same key read back via subscript -> not surfaced.
        added = [
            ('mod.py', 5, "    output['used'] = compute()"),
            ('mod.py', 9, "    if output['used']:"),
        ]
        out = _detect_producer_consumer(added)
        assert out == []

    def test_get_read_consumes_producer(self):
        # A .get('key') read suppresses the candidate.
        added = [
            ('mod.py', 5, "    output['fetched'] = compute()"),
            ('mod.py', 9, "    val = output.get('fetched')"),
        ]
        out = _detect_producer_consumer(added)
        assert out == []

    def test_cross_file_consumption_suppresses_candidate(self):
        # Produced in one file, consumed in another -> not a dangling producer.
        added = [
            ('producer.py', 5, "    output['shared'] = compute()"),
            ('consumer.py', 3, "    use(state['shared'])"),
        ]
        out = _detect_producer_consumer(added)
        assert out == []

    def test_producer_line_own_key_does_not_self_consume(self):
        # The LHS subscript on the producer line must not register the key as
        # consumed (otherwise no producer would ever surface).
        added = [('mod.py', 5, "    output['k'] = compute()")]
        out = _detect_producer_consumer(added)
        assert len(out) == 1
        assert out[0]['key'] == 'k'

    def test_skips_non_python_files(self):
        added = [('doc.md', 1, "output['x'] = 1")]
        out = _detect_producer_consumer(added)
        assert out == []


# =============================================================================
# Test: _detect_source_of_truth
# =============================================================================


class TestDetectSourceOfTruth:
    def test_divergent_constant_across_two_files_surfaces_candidate(self):
        added = [
            ('a.py', 3, 'MAX_RETRIES = 5'),
            ('b.py', 7, 'MAX_RETRIES = 3'),
        ]
        out = _detect_source_of_truth(added)
        assert len(out) == 1
        entry = out[0]
        assert entry['name'] == 'MAX_RETRIES'
        assert 'a.py' in entry['files']
        assert 'b.py' in entry['files']
        assert '5' in entry['values']
        assert '3' in entry['values']

    def test_identical_constant_across_two_files_surfaces_nothing(self):
        # Same value in two files is not a drift.
        added = [
            ('a.py', 3, 'MAX_RETRIES = 5'),
            ('b.py', 7, 'MAX_RETRIES = 5'),
        ]
        out = _detect_source_of_truth(added)
        assert out == []

    def test_constant_in_single_file_surfaces_nothing(self):
        added = [('a.py', 3, 'MAX_RETRIES = 5')]
        out = _detect_source_of_truth(added)
        assert out == []

    def test_lowercase_name_is_not_a_constant(self):
        # Only UPPER_SNAKE_CASE bindings are treated as SoT constants.
        added = [
            ('a.py', 3, 'max_retries = 5'),
            ('b.py', 7, 'max_retries = 3'),
        ]
        out = _detect_source_of_truth(added)
        assert out == []

    def test_skips_non_python_files(self):
        added = [
            ('a.md', 1, 'MAX_RETRIES = 5'),
            ('b.md', 1, 'MAX_RETRIES = 3'),
        ]
        out = _detect_source_of_truth(added)
        assert out == []


# =============================================================================
# Test: _detect_same_document_consistency
# =============================================================================


class TestDetectSameDocumentConsistency:
    @pytest.mark.parametrize(
        'keyword_line',
        [
            'The runner MUST flush before exit.',
            'Agents MUST NOT edit the main checkout.',
            'The gate SHALL reject empty input.',
            'NEVER call git without -C.',
            'The cwd ALWAYS stays pinned.',
            'A --phase argument is REQUIRED.',
            'Direct gh access is FORBIDDEN.',
        ],
    )
    def test_normative_directive_surfaces_candidate(self, keyword_line: str):
        added = [('rule.md', 4, keyword_line)]
        out = _detect_same_document_consistency(added)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == 'rule.md'
        assert entry['line'] == 4
        assert entry['keyword'] in keyword_line
        assert entry['text'] == keyword_line

    def test_non_normative_line_surfaces_nothing(self):
        added = [('rule.md', 4, 'This is plain descriptive prose.')]
        out = _detect_same_document_consistency(added)
        assert out == []

    def test_skips_non_markdown_files(self):
        added = [('mod.py', 1, '# The runner MUST flush before exit.')]
        out = _detect_same_document_consistency(added)
        assert out == []


# =============================================================================
# Test: _detect_description_vs_body
# =============================================================================


class TestDetectDescriptionVsBody:
    @staticmethod
    def _write_doc(root: Path, rel: str, content: str) -> None:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def test_frontmatter_description_with_body_edit_surfaces_candidate(self, tmp_path: Path):
        rel = 'skill/SKILL.md'
        self._write_doc(
            tmp_path,
            rel,
            '---\n'
            'name: skill\n'
            'description: Surfaces two-track classification model.\n'
            '---\n'
            '# Skill\n'
            'The body now implements a single-track model only.\n',
        )
        # An added body line (line 6, below the closing --- on line 4).
        added = [(rel, 6, 'The body now implements a single-track model only.')]
        out = _detect_description_vs_body(added, tmp_path)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == rel
        assert entry['line'] == 3
        assert entry['key'] == 'description'
        assert 'two-track' in entry['description']

    def test_summary_key_is_also_recognized(self, tmp_path: Path):
        rel = 'skill/DOC.md'
        self._write_doc(
            tmp_path,
            rel,
            '---\n'
            'summary: Old model summary.\n'
            '---\n'
            '# Doc\n'
            'New body content.\n',
        )
        added = [(rel, 5, 'New body content.')]
        out = _detect_description_vs_body(added, tmp_path)
        assert len(out) == 1
        assert out[0]['key'] == 'summary'

    def test_frontmatter_only_edit_surfaces_nothing(self, tmp_path: Path):
        # Only the description line itself changed; no body edit -> no candidate.
        rel = 'skill/SKILL.md'
        self._write_doc(
            tmp_path,
            rel,
            '---\n'
            'name: skill\n'
            'description: A description.\n'
            '---\n'
            '# Skill\n'
            'Unchanged body.\n',
        )
        added = [(rel, 3, 'description: A description.')]
        out = _detect_description_vs_body(added, tmp_path)
        assert out == []

    def test_no_frontmatter_description_surfaces_nothing(self, tmp_path: Path):
        rel = 'skill/SKILL.md'
        self._write_doc(
            tmp_path,
            rel,
            '---\n'
            'name: skill\n'
            '---\n'
            '# Skill\n'
            'Body content here.\n',
        )
        added = [(rel, 5, 'Body content here.')]
        out = _detect_description_vs_body(added, tmp_path)
        assert out == []

    def test_skips_non_markdown_files(self, tmp_path: Path):
        added = [('mod.py', 5, 'some code')]
        out = _detect_description_vs_body(added, tmp_path)
        assert out == []


# =============================================================================
# Test: _detect_unguarded_boundaries (Facet 1)
# =============================================================================


class TestDetectUnguardedBoundaries:
    def test_subprocess_without_check_outside_try_surfaces_candidate(self):
        added = [
            ('mod.py', 10, 'def run():'),
            ('mod.py', 11, '    subprocess.run(["ls"])'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == 'mod.py'
        assert entry['line'] == 11
        assert entry['boundary'] == 'subprocess.run'
        assert entry['guarded'] is False

    def test_subprocess_with_check_true_surfaces_nothing(self):
        added = [
            ('mod.py', 10, 'def run():'),
            ('mod.py', 11, '    subprocess.run(["ls"], check=True)'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert out == []

    def test_subprocess_inside_try_surfaces_nothing(self):
        added = [
            ('mod.py', 10, 'def run():'),
            ('mod.py', 11, '    try:'),
            ('mod.py', 12, '        subprocess.run(["ls"])'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert out == []

    def test_open_call_outside_try_surfaces_candidate(self):
        added = [
            ('mod.py', 20, 'def load():'),
            ('mod.py', 21, '    fh = open("data.txt")'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert len(out) == 1
        assert out[0]['boundary'] == 'open'
        assert out[0]['guarded'] is False

    def test_path_read_text_outside_try_surfaces_candidate(self):
        added = [
            ('mod.py', 30, 'def load():'),
            ('mod.py', 31, '    body = path.read_text()'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert len(out) == 1
        assert out[0]['boundary'] == 'read_text'

    def test_file_io_inside_try_surfaces_nothing(self):
        added = [
            ('mod.py', 40, 'def load():'),
            ('mod.py', 41, '    try:'),
            ('mod.py', 42, '        fh = open("data.txt")'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert out == []

    def test_def_header_resets_try_window(self):
        # The try in the first function must NOT guard the open() in the second.
        added = [
            ('mod.py', 10, 'def first():'),
            ('mod.py', 11, '    try:'),
            ('mod.py', 12, '        pass'),
            ('mod.py', 13, 'def second():'),
            ('mod.py', 14, '    fh = open("data.txt")'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert len(out) == 1
        assert out[0]['line'] == 14
        assert out[0]['boundary'] == 'open'

    def test_urllib_network_call_surfaces_nothing(self):
        added = [
            ('mod.py', 10, 'def fetch():'),
            ('mod.py', 11, '    resp = urllib.request.urlopen("http://x")'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert out == []

    def test_socket_network_call_surfaces_nothing(self):
        added = [
            ('mod.py', 10, 'def connect():'),
            ('mod.py', 11, '    s = socket.socket()'),
        ]
        out = _detect_unguarded_boundaries(added)
        assert out == []

    def test_skips_non_python_files(self):
        added = [('doc.md', 5, 'subprocess.run(["ls"])')]
        out = _detect_unguarded_boundaries(added)
        assert out == []

    def test_subprocess_inside_existing_try_block_surfaces_nothing(self, tmp_path: Path):
        # The try block is NOT part of the diff (pre-existing) — only the
        # subprocess.run line is added.  Without post-image walking this case
        # was incorrectly flagged as unguarded.
        mod_py = tmp_path / 'mod.py'
        mod_py.write_text(
            'def run():\n'
            '    try:\n'
            '        pass\n'
            '        subprocess.run(["ls"])\n'
        )
        added = [('mod.py', 4, '        subprocess.run(["ls"])')]
        out = _detect_unguarded_boundaries(added, tmp_path)
        assert out == []

    def test_subprocess_outside_try_with_project_dir_surfaces_candidate(self, tmp_path: Path):
        # Confirm that the post-image path still surfaces genuinely unguarded
        # calls when project_dir is provided.
        mod_py = tmp_path / 'mod.py'
        mod_py.write_text(
            'def run():\n'
            '    subprocess.run(["ls"])\n'
        )
        added = [('mod.py', 2, '    subprocess.run(["ls"])')]
        out = _detect_unguarded_boundaries(added, tmp_path)
        assert len(out) == 1
        assert out[0]['line'] == 2
        assert out[0]['boundary'] == 'subprocess.run'


# =============================================================================
# Test: _detect_count_prose (Facet 2)
# =============================================================================


class TestDetectCountProse:
    @staticmethod
    def _build_skill(root: Path, skill_md_body: str) -> Path:
        """Lay down a skill directory with a SKILL.md and a sibling script."""
        project = root / 'project'
        skill = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill'
        (skill / 'scripts').mkdir(parents=True)
        (skill / 'SKILL.md').write_text(skill_md_body)
        (skill / 'scripts' / 'mod.py').write_text('')
        return project

    def test_count_prose_surfaces_word_and_digit_counts(self, tmp_path: Path):
        body = (
            '---\n'
            'name: my-skill\n'
            '---\n'
            '# My Skill\n'
            'Emit twelve fields from the parsed input.\n'
            'There are 5 rules enforced.\n'
        )
        project = self._build_skill(tmp_path, body)
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/mod.py'
        out = _detect_count_prose([rel], project)
        texts = [e['text'] for e in out]
        assert any('twelve fields' in t for t in texts)
        assert any('5 rules' in t for t in texts)
        # Every entry points at the SKILL.md path.
        for entry in out:
            assert entry['file'] == 'marketplace/bundles/b1/skills/my-skill/SKILL.md'

    def test_digit_not_adjacent_to_cardinality_noun_surfaces_nothing(self, tmp_path: Path):
        body = (
            '---\n'
            'name: my-skill\n'
            '---\n'
            '# My Skill\n'
            'This skill is version 3 and was built in 2026.\n'
        )
        project = self._build_skill(tmp_path, body)
        rel = 'marketplace/bundles/b1/skills/my-skill/scripts/mod.py'
        out = _detect_count_prose([rel], project)
        assert out == []

    def test_modified_file_outside_skill_dir_surfaces_nothing(self, tmp_path: Path):
        project = tmp_path / 'project'
        project.mkdir()
        (project / 'README.md').write_text('Three steps are required.\n')
        rel = 'README.md'
        out = _detect_count_prose([rel], project)
        assert out == []

    def test_deduplicates_per_file_line(self, tmp_path: Path):
        # The same skill dir reached via two modified siblings yields each
        # count-prose line exactly once.
        body = (
            '---\n'
            'name: my-skill\n'
            '---\n'
            '# My Skill\n'
            'Nine steps in the workflow.\n'
        )
        project = self._build_skill(tmp_path, body)
        skill = project / 'marketplace' / 'bundles' / 'b1' / 'skills' / 'my-skill'
        (skill / 'scripts' / 'other.py').write_text('')
        rels = [
            'marketplace/bundles/b1/skills/my-skill/scripts/mod.py',
            'marketplace/bundles/b1/skills/my-skill/scripts/other.py',
        ]
        out = _detect_count_prose(rels, project)
        matched = [e for e in out if 'Nine steps' in e['text']]
        assert len(matched) == 1


# =============================================================================
# Test: _detect_ordinal_references (same-document ordinal cross-references)
# =============================================================================


class TestDetectOrdinalReferences:
    @staticmethod
    def _write_md(root: Path, body: str) -> str:
        """Write a doc.md under ``root`` and return its repo-relative path."""
        md = root / 'doc.md'
        md.write_text(body, encoding='utf-8')
        return 'doc.md'

    def test_item_reference_into_touched_list_surfaces_candidate(self, tmp_path: Path):
        # Post-image: an ordered list (lines 1-3) plus a reference line (line 5).
        body = (
            '1. First item\n'
            '2. Second item\n'
            '3. Third item\n'
            '\n'
            'See item 2 for details.\n'
        )
        rel = self._write_md(tmp_path, body)
        # The diff touched both the reference line and a list line (line 2),
        # so the referenced block counts as touched.
        added = [(rel, 2, '2. Second item'), (rel, 5, 'See item 2 for details.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert len(out) == 1
        entry = out[0]
        assert entry['file'] == rel
        assert entry['line'] == 5
        assert entry['text'] == 'See item 2 for details.'
        # list_line resolves to the post-image line of item 2.
        assert entry['list_line'] == 2

    def test_step_reference_form_is_recognized(self, tmp_path: Path):
        body = (
            '1. Configure\n'
            '2. Build\n'
            '3. Verify\n'
            '\n'
            'Re-run step 3 if it fails.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [(rel, 3, '3. Verify'), (rel, 5, 'Re-run step 3 if it fails.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert len(out) == 1
        assert out[0]['list_line'] == 3

    def test_bare_parenthesized_ordinal_is_recognized(self, tmp_path: Path):
        body = (
            '1. Alpha\n'
            '2. Beta\n'
            '\n'
            'The guard described in (1) runs first.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [(rel, 1, '1. Alpha'), (rel, 4, 'The guard described in (1) runs first.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert len(out) == 1
        assert out[0]['list_line'] == 1

    def test_reference_into_untouched_list_surfaces_nothing(self, tmp_path: Path):
        # The ordered list exists in the post-image but the diff did NOT touch
        # any of its lines — only the reference line was added.
        body = (
            '1. First item\n'
            '2. Second item\n'
            '\n'
            'See item 2 for details.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [(rel, 4, 'See item 2 for details.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert out == []

    def test_reference_to_nonexistent_ordinal_surfaces_nothing(self, tmp_path: Path):
        # 'item 9' points at an ordinal absent from any ordered-list block.
        body = (
            '1. First item\n'
            '2. Second item\n'
            '\n'
            'See item 9 for details.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [(rel, 1, '1. First item'), (rel, 4, 'See item 9 for details.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert out == []

    def test_non_ordinal_numeric_token_surfaces_nothing(self, tmp_path: Path):
        # A bare digit not in an 'item/step/point N' or '(N)' shape, plus a
        # version-style number, must not fire even with a touched list present.
        body = (
            '1. First item\n'
            '2. Second item\n'
            '\n'
            'This is version 2 built in 2026 with 2 retries.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [
            (rel, 2, '2. Second item'),
            (rel, 4, 'This is version 2 built in 2026 with 2 retries.'),
        ]
        out = _detect_ordinal_references(added, tmp_path)
        assert out == []

    def test_word_boundary_discipline_no_false_positive(self, tmp_path: Path):
        # 'itemize' / 'stepwise' must not be read as 'item'/'step' references,
        # and a decimal like '(1.5)' must not match the bare-(N) form.
        body = (
            '1. First item\n'
            '2. Second item\n'
            '\n'
            'The itemized list and stepwise plan tolerate (1.5) ratios.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [
            (rel, 1, '1. First item'),
            (rel, 4, 'The itemized list and stepwise plan tolerate (1.5) ratios.'),
        ]
        out = _detect_ordinal_references(added, tmp_path)
        assert out == []

    def test_skips_non_markdown_files(self, tmp_path: Path):
        added = [('mod.py', 1, '# See item 1 below')]
        out = _detect_ordinal_references(added, tmp_path)
        assert out == []

    def test_deduplicates_per_file_line_ordinal(self, tmp_path: Path):
        # The same 'item 2' reference appearing twice on one added line yields a
        # single candidate.
        body = (
            '1. First item\n'
            '2. Second item\n'
            '\n'
            'See item 2; yes item 2 again.\n'
        )
        rel = self._write_md(tmp_path, body)
        added = [(rel, 2, '2. Second item'), (rel, 4, 'See item 2; yes item 2 again.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert len(out) == 1

    def test_multiple_lists_same_ordinal_resolves_by_proximity(self, tmp_path: Path):
        # Two separate ordered-list blocks both contain ordinals 1 and 2.
        # A reference to 'item 1' on line 10 (near the second block) must resolve
        # to the second block, not the first, even though both contain ordinal 1.
        body = (
            '1. Alpha\n'      # line 1  — block A
            '2. Beta\n'       # line 2  — block A
            '\n'
            'Some text here.\n'  # line 4  — separator
            '\n'
            '1. Gamma\n'      # line 6  — block B
            '2. Delta\n'      # line 7  — block B
            '\n'
            'See item 1 for details.\n'  # line 9 — reference
        )
        rel = self._write_md(tmp_path, body)
        # Diff touched block B (line 6) and the reference line (line 9).
        added = [(rel, 6, '1. Gamma'), (rel, 9, 'See item 1 for details.')]
        out = _detect_ordinal_references(added, tmp_path)
        # Must surface exactly one candidate, resolving to block B (list_line=6).
        assert len(out) == 1
        assert out[0]['list_line'] == 6

    def test_separator_blank_after_list_does_not_keep_block_open(self, tmp_path: Path):
        # A blank line followed by non-list content must close the list block.
        # Touching only that trailing blank line must NOT surface the block's
        # ordinal references as candidates (the block is untouched aside from
        # the closing blank, which is not part of the block).
        body = (
            '1. First item\n'   # line 1
            '2. Second item\n'  # line 2
            '\n'                # line 3 — separator blank (closes block)
            'Not a list item.\n'  # line 4
            '\n'
            'See item 2 for more.\n'  # line 6 — reference
        )
        rel = self._write_md(tmp_path, body)
        # Diff touches only the separator blank (line 3) and the reference (line 6).
        # Since line 3 is NOT inside the block (it closes the block), the block
        # is untouched — no candidate should surface.
        added = [(rel, 3, ''), (rel, 6, 'See item 2 for more.')]
        out = _detect_ordinal_references(added, tmp_path)
        assert out == []


# =============================================================================
# Test: _iter_changed_line_pairs (Facet 3 diff walk)
# =============================================================================


class TestIterChangedLinePairs:
    def test_yields_adjacent_removed_added_pair(self):
        diff = (
            '+++ b/foo.py\n'
            '@@ -1,3 +1,3 @@\n'
            ' kept_one\n'
            '-old_line\n'
            '+new_line\n'
            ' kept_two\n'
        )
        pairs = _iter_changed_line_pairs(diff)
        assert pairs == [('foo.py', 2, 'old_line', 'new_line')]

    def test_ignores_unpaired_added_line(self):
        diff = (
            '+++ b/foo.py\n'
            '@@ -1,2 +1,3 @@\n'
            ' kept_one\n'
            '+lone_addition\n'
            ' kept_two\n'
        )
        pairs = _iter_changed_line_pairs(diff)
        assert pairs == []

    def test_ignores_unpaired_removed_line(self):
        diff = (
            '+++ b/foo.py\n'
            '@@ -1,3 +1,2 @@\n'
            ' kept_one\n'
            '-lone_removal\n'
            ' kept_two\n'
        )
        pairs = _iter_changed_line_pairs(diff)
        assert pairs == []

    def test_context_line_breaks_pending_removal(self):
        # A removal followed by a context line (not an addition) is not a pair.
        diff = (
            '+++ b/foo.py\n'
            '@@ -1,3 +1,3 @@\n'
            '-removed_first\n'
            ' context_between\n'
            '+added_later\n'
        )
        pairs = _iter_changed_line_pairs(diff)
        assert pairs == []


# =============================================================================
# Test: _detect_touched_claims (Facet 3)
# =============================================================================


class TestDetectTouchedClaims:
    def test_single_token_swap_surfaces_added_line(self):
        pairs = [('foo.py', 5, 'count is twelve here', 'count is fifteen here')]
        out = _detect_touched_claims(pairs)
        assert len(out) == 1
        assert out[0] == {'file': 'foo.py', 'line': 5, 'text': 'count is fifteen here'}

    def test_many_token_difference_surfaces_nothing(self):
        pairs = [('foo.py', 5, 'the old line entirely', 'a completely different sentence')]
        out = _detect_touched_claims(pairs)
        assert out == []

    def test_identical_lines_surface_nothing(self):
        pairs = [('foo.py', 5, 'same content', 'same content')]
        out = _detect_touched_claims(pairs)
        assert out == []

    def test_differing_token_count_surfaces_nothing(self):
        # Lines that tokenize to different lengths are not a single-token swap.
        pairs = [('foo.py', 5, 'two words', 'two extra words here')]
        out = _detect_touched_claims(pairs)
        assert out == []


# =============================================================================
# Test: _detect_advertised_form_help_strings (advertised-form help string)
# =============================================================================


class TestDetectAdvertisedFormHelpStrings:
    """A multi-form ``help=`` string whose handler forwards the raw value.

    The detector fires only when BOTH a multi-form ``help=`` string (an `` or ``
    disjunction adjacent to a form noun like ``URL``/``path``/``number``) AND a
    raw pass-through of ``args.<dest>`` (no normalization) are present in the
    same file's added lines. It mirrors the review-anchor exclusion of
    ``contract_sources``/``count_prose``: surfaced candidates are NOT summed into
    ``counts.total`` (see ``TestCountsTotalInvariant``).
    """

    def test_multi_form_help_with_raw_pass_surfaces_candidate(self):
        added = [
            ('cli.py', 10, "    p.add_argument('--issue', help='Issue number or URL')"),
            ('cli.py', 25, '    target = str(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert len(out) == 1
        assert out[0]['file'] == 'cli.py'
        assert out[0]['line'] == 10
        assert out[0]['arg'] == 'issue'
        assert out[0]['help_text'] == 'Issue number or URL'
        assert out[0]['raw_pass_line'] == 25

    def test_dest_kwarg_overrides_flag_derived_dest(self):
        added = [
            (
                'cli.py',
                10,
                "    p.add_argument('--issue-ref', dest='issue', help='ref name or URL')",
            ),
            ('cli.py', 25, '    return f"{args.issue}"'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert len(out) == 1
        assert out[0]['arg'] == 'issue'
        assert out[0]['raw_pass_line'] == 25

    def test_flag_dashes_map_to_underscore_dest(self):
        added = [
            ('cli.py', 10, "    p.add_argument('--issue-ref', help='Issue ref or URL')"),
            ('cli.py', 30, '    value = args.issue_ref'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert len(out) == 1
        assert out[0]['arg'] == 'issue_ref'
        assert out[0]['raw_pass_line'] == 30

    def test_single_form_help_surfaces_nothing(self):
        # No `` or `` disjunction — single advertised form, no contract to drift.
        added = [
            ('cli.py', 10, "    p.add_argument('--issue', help='Issue number')"),
            ('cli.py', 25, '    target = str(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert out == []

    def test_normalized_value_surfaces_nothing(self):
        # The raw value is routed through a normalization call (`parse`), so the
        # advertised forms are reconciled — not a raw pass-through.
        added = [
            ('cli.py', 10, "    p.add_argument('--issue', help='Issue number or URL')"),
            ('cli.py', 25, '    target = parse(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert out == []

    def test_no_raw_pass_site_surfaces_nothing(self):
        # Multi-form help but the dest is never read back — no drift surface.
        added = [
            ('cli.py', 10, "    p.add_argument('--issue', help='Issue number or URL')"),
            ('cli.py', 25, '    unrelated = compute_other()'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert out == []

    def test_skips_non_python_files(self):
        added = [
            ('doc.md', 10, "p.add_argument('--issue', help='Issue number or URL')"),
            ('doc.md', 25, 'target = str(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert out == []

    def test_attribute_access_not_confused_with_longer_dest(self):
        # ``args.issue`` must not match ``args.issue_url`` — the raw-pass search
        # uses a trailing identifier-boundary guard. Only the genuine ``args.issue``
        # read counts; here there is none, so no candidate is surfaced.
        added = [
            ('cli.py', 10, "    p.add_argument('--issue', help='Issue number or URL')"),
            ('cli.py', 25, '    target = str(args.issue_url)'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert out == []

    def test_empty_added_surfaces_nothing(self):
        assert _detect_advertised_form_help_strings([]) == []

    # ---- Multi-line add_argument: post-image walk-back (project_dir) ----

    # A multi-line add_argument call whose ``--flag`` and ``help=`` sit on
    # different physical lines. Only the help= line and the raw-pass line are
    # present in the diff; the ``--flag`` line is absent.
    _MULTI_LINE_SOURCE = (
        "def build_parser(p):\n"
        "    p.add_argument(\n"
        "        '--issue',\n"
        "        help='Issue number or URL',\n"
        "    )\n"
        "\n"
        "def run(args):\n"
        "    target = str(args.issue)\n"
    )

    def test_multiline_diff_only_does_not_resolve_dest(self):
        # Without project_dir, the --flag line is absent from the diff, so the
        # help= continuation line alone cannot resolve the dest — no candidate.
        added = [
            ('cli.py', 4, "        help='Issue number or URL',"),
            ('cli.py', 8, '    target = str(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added)
        assert out == []

    def test_multiline_post_image_walkback_surfaces_candidate(self, tmp_path):
        # With project_dir, the detector walks backwards through the file's
        # post-image from the help= line to the opening add_argument( and
        # resolves the dest from the preceding --flag line.
        (tmp_path / 'cli.py').write_text(self._MULTI_LINE_SOURCE, encoding='utf-8')
        added = [
            ('cli.py', 4, "        help='Issue number or URL',"),
            ('cli.py', 8, '    target = str(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added, tmp_path)
        assert len(out) == 1
        assert out[0]['file'] == 'cli.py'
        assert out[0]['line'] == 4
        assert out[0]['arg'] == 'issue'
        assert out[0]['help_text'] == 'Issue number or URL'
        assert out[0]['raw_pass_line'] == 8

    def test_multiline_post_image_dest_kwarg_walkback(self, tmp_path):
        # An explicit dest= on a preceding line of the multi-line call wins
        # over the flag-derived dest, resolved via the post-image walk-back.
        source = (
            "def build_parser(p):\n"
            "    p.add_argument(\n"
            "        '--issue-ref',\n"
            "        dest='issue',\n"
            "        help='ref name or URL',\n"
            "    )\n"
            "\n"
            "def run(args):\n"
            "    return f'{args.issue}'\n"
        )
        (tmp_path / 'cli.py').write_text(source, encoding='utf-8')
        added = [
            ('cli.py', 5, "        help='ref name or URL',"),
            ('cli.py', 9, "    return f'{args.issue}'"),
        ]
        out = _detect_advertised_form_help_strings(added, tmp_path)
        assert len(out) == 1
        assert out[0]['arg'] == 'issue'
        assert out[0]['raw_pass_line'] == 9

    def test_multiline_missing_post_image_falls_back_to_none(self, tmp_path):
        # project_dir is supplied but the file does not exist on disk (empty
        # post-image), so the walk-back cannot resolve the dest — no candidate.
        added = [
            ('cli.py', 4, "        help='Issue number or URL',"),
            ('cli.py', 8, '    target = str(args.issue)'),
        ]
        out = _detect_advertised_form_help_strings(added, tmp_path)
        assert out == []


# =============================================================================
# Test: _detect_scan_derived_keys
# =============================================================================


class TestDetectScanDerivedKeys:
    """The scan-versus-anchor shape behind the unreachable-guard candidate list.

    Fires on the conjunction of a sequence decomposition and a first-match scan
    over that same sequence. See
    ``standards/unreachable-guard-detection.md`` for the gate verdict.
    """

    # The PR #1013 pre-fix scanning derivation, in added-line-tuple form.
    _SCANNING_FORM = [
        ('gen.py', 1, 'def _split_bundle_version(path):'),
        ('gen.py', 2, '    parts = Path(path).parts'),
        ('gen.py', 3, '    for index, part in enumerate(parts):'),
        ('gen.py', 4, '        if index > 0 and _VERSION_DIR_NAME_RE.match(part):'),
        ('gen.py', 5, '            return parts[index - 1], part'),
        ('gen.py', 6, '    return None'),
    ]

    def test_scanning_derivation_surfaces_candidate(self):
        out = _detect_scan_derived_keys(list(self._SCANNING_FORM))
        assert len(out) == 1
        assert out[0]['file'] == 'gen.py'
        assert out[0]['line'] == 3
        assert out[0]['name'] == '_split_bundle_version'
        assert out[0]['sequence'] == 'parts'

    def test_no_caller_in_diff_yields_key_consumed_false(self):
        out = _detect_scan_derived_keys(list(self._SCANNING_FORM))
        assert out[0]['key_consumed'] is False

    def test_identity_consuming_caller_yields_key_consumed_true(self):
        added = list(self._SCANNING_FORM) + [
            ('gen.py', 8, 'def _check_provenance(paths):'),
            ('gen.py', 9, '    by_bundle = {}'),
            ('gen.py', 10, '    for p in paths:'),
            ('gen.py', 11, '        bundle, version = _split_bundle_version(p)'),
            ('gen.py', 12, '        by_bundle.setdefault(bundle, set()).add(version)'),
            ('gen.py', 13, '    return any(len(v) > 1 for v in by_bundle.values())'),
        ]
        out = _detect_scan_derived_keys(added)
        surfaced = [e for e in out if e['name'] == '_split_bundle_version']
        assert len(surfaced) == 1
        assert surfaced[0]['key_consumed'] is True

    #: A post-image carrying the scanning derivation on lines 1-6 (the diff's
    #: added lines) and an identity-consuming caller on lines 9-14 that the diff
    #: never touched. Used by the diff-scoping pair below.
    _POST_IMAGE_WITH_UNTOUCHED_CALLER = (
        'def _split_bundle_version(path):\n'
        '    parts = Path(path).parts\n'
        '    for index, part in enumerate(parts):\n'
        '        if index > 0 and _VERSION_DIR_NAME_RE.match(part):\n'
        '            return parts[index - 1], part\n'
        '    return None\n'
        '\n'
        '\n'
        'def _check_provenance(paths):\n'
        '    by_bundle = {}\n'
        '    for p in paths:\n'
        '        bundle, version = _split_bundle_version(p)\n'
        '        by_bundle.setdefault(bundle, set()).add(version)\n'
        '    return any(len(v) > 1 for v in by_bundle.values())\n'
    )

    #: The caller's post-image lines 9-14, as added-line tuples.
    _CALLER_ADDED_LINES = [
        ('gen.py', 9, 'def _check_provenance(paths):'),
        ('gen.py', 10, '    by_bundle = {}'),
        ('gen.py', 11, '    for p in paths:'),
        ('gen.py', 12, '        bundle, version = _split_bundle_version(p)'),
        ('gen.py', 13, '        by_bundle.setdefault(bundle, set()).add(version)'),
        ('gen.py', 14, '    return any(len(v) > 1 for v in by_bundle.values())'),
    ]

    def test_untouched_caller_in_post_image_leaves_key_consumed_false(self, tmp_path):
        # The documented invariant: "a caller that lives outside the surfaced
        # diff is invisible here". With project_dir supplied the file's FULL
        # post-image is walked to resolve the candidate block, so an
        # identity-consuming caller the diff never touched must NOT flip the
        # Tier-2 flag.
        (tmp_path / 'gen.py').write_text(self._POST_IMAGE_WITH_UNTOUCHED_CALLER)

        out = _detect_scan_derived_keys(list(self._SCANNING_FORM), tmp_path)

        surfaced = [e for e in out if e['name'] == '_split_bundle_version']
        assert len(surfaced) == 1, (
            f'The candidate must still surface off the post-image — otherwise '
            f'the flag assertion below is vacuous. Got: {out}'
        )
        assert surfaced[0]['key_consumed'] is False

    def test_touched_caller_in_post_image_still_sets_key_consumed(self, tmp_path):
        # The complementary positive over the IDENTICAL post-image: with the
        # caller's lines present in the diff, the flag must still resolve true.
        # Without this, the negative above would pass equally if the diff filter
        # suppressed every caller — collapsing the Tier-2 flag to a constant
        # False and making its own guard unreachable.
        (tmp_path / 'gen.py').write_text(self._POST_IMAGE_WITH_UNTOUCHED_CALLER)

        added = list(self._SCANNING_FORM) + list(self._CALLER_ADDED_LINES)
        out = _detect_scan_derived_keys(added, tmp_path)

        surfaced = [e for e in out if e['name'] == '_split_bundle_version']
        assert len(surfaced) == 1
        assert surfaced[0]['key_consumed'] is True

    def test_anchored_derivation_surfaces_nothing(self):
        # The shipped post-fix form indexes the decomposition at a fixed
        # position anchored on a known root — no scan loop, no candidate.
        added = [
            ('gen.py', 1, 'def _split_bundle_version(path, base_path):'),
            ('gen.py', 2, '    relative = Path(path).relative_to(base_path)'),
            ('gen.py', 3, '    parts = relative.parts'),
            ('gen.py', 4, '    if len(parts) < 2 or not _VERSION_DIR_NAME_RE.match(parts[1]):'),
            ('gen.py', 5, '        return None'),
            ('gen.py', 6, '    return parts[0], parts[1]'),
        ]
        assert _detect_scan_derived_keys(added) == []

    def test_full_traversal_without_first_match_exit_surfaces_nothing(self):
        # A loop that collects every match is a traversal, not a first-match
        # selection — the collapse-to-one-key failure mode does not arise.
        added = [
            ('scan.py', 1, 'def collect(path):'),
            ('scan.py', 2, "    parts = path.split('/')"),
            ('scan.py', 3, '    found = []'),
            ('scan.py', 4, '    for part in parts:'),
            ('scan.py', 5, '        if _NAME_RE.match(part):'),
            ('scan.py', 6, '            found.append(part)'),
            ('scan.py', 7, '    return found'),
        ]
        assert _detect_scan_derived_keys(added) == []

    def test_loop_over_undecomposed_sequence_surfaces_nothing(self):
        # An ordinary search over a caller-supplied list is not the shape: the
        # sequence was never derived by decomposing a single value.
        added = [
            ('scan.py', 1, 'def pick(names):'),
            ('scan.py', 2, '    for name in names:'),
            ('scan.py', 3, '        if _NAME_RE.match(name):'),
            ('scan.py', 4, '            return name'),
            ('scan.py', 5, '    return None'),
        ]
        assert _detect_scan_derived_keys(added) == []

    def test_non_python_file_surfaces_nothing(self):
        added = [
            ('guide.md', 1, 'def _split_bundle_version(path):'),
            ('guide.md', 2, '    parts = Path(path).parts'),
            ('guide.md', 3, '    for part in parts:'),
            ('guide.md', 4, '        if _RE.match(part):'),
            ('guide.md', 5, '            return part'),
        ]
        assert _detect_scan_derived_keys(added) == []

    def test_empty_added_surfaces_nothing(self):
        assert _detect_scan_derived_keys([]) == []


# =============================================================================
# Test: _detect_worked_example_pairs / _worked_example_pairs
# =============================================================================
#
# Fixture provenance and durability. The clause-(d) control texts below are the
# pre- and post-fix bodies of ``## Fail-Closed Classification`` clause (d) in
# ``ref-code-quality/standards/error-handling.md``. The PRE-fix text exists only
# at ``de00dca9b^`` — a branch commit of a SQUASH-merged PR, so it is reachable
# from no branch ref and is a garbage-collection candidate. It is therefore
# checked in here as literal content: a fixture that resolved it from git at run
# time would pass today and silently stop testing anything once the object is
# pruned, which is precisely the vacuous-guard shape this candidate class exists
# to prevent.

#: Clause (d) as it shipped BEFORE the fix. The clause requires "an affirmative
#: success signal"; the GOOD example branches on ``outcome.applied`` — a CHANGE
#: flag — so the worked contrast demonstrates the shape its own clause forbids.
_PRE_FIX_CLAUSE_D = '''### (d) Require an affirmative success signal, never absence-of-change

"Nothing changed" is satisfied both by an operation that succeeded idempotently and by an operation that never ran. Absence-of-change is therefore not evidence of success; require the operation to report its own outcome and branch on that.

```text
// BAD — an empty diff is read as proof the fix landed
applyFix(file)
if (diff(file).isEmpty()) {
    markResolved()   // equally true when applyFix silently did nothing
}

// GOOD — the operation reports whether it applied, and that is what is read
outcome = applyFix(file)
if (outcome.applied) markResolved() else markUnresolved(outcome.reason)
```
'''

#: Clause (d) as it reads on ``main`` AFTER the fix: the GOOD example branches on
#: ``outcome.status == "success"``, which is the affirmative success signal the
#: clause requires. ``applied`` survives as metadata, never as the predicate.
_POST_FIX_CLAUSE_D = '''### (d) Require an affirmative success signal, never absence-of-change

"Nothing changed" is satisfied both by an operation that succeeded idempotently and by an operation that never ran. Absence-of-change is therefore not evidence of success; require the operation to report its own outcome and branch on that. Success and change are two distinct fields: the operation reports whether it succeeded independently of whether it changed anything, so `applied` / `changed` is metadata about the edit and never the success predicate.

```text
// BAD — an empty diff is read as proof the fix landed
applyFix(file)
if (diff(file).isEmpty()) {
    markResolved()   // equally true when applyFix silently did nothing
}

// GOOD — the operation reports its own success, and THAT is what is branched on
outcome = applyFix(file)   // { status: "success" | "skipped" | "error", applied: bool }
if (outcome.status == "success") {
    markResolved()          // ran and passed — including the idempotent no-op,
                            // which reports success with applied == false
} else {
    markUnresolved(outcome.reason)   // never ran (skipped), or ran and failed
}
```
'''

#: Clause (f) as it shipped BEFORE the fix. Its GOOD marker comment names a
#: "readback" mechanism the body never performs — a COMMENT-versus-body claim,
#: not a predicate-versus-predicate disagreement. The decided disposition is
#: silence; see the case table in the implementor SKILL.md rule 19.
_PRE_FIX_CLAUSE_F = '''### (f) Write direction — check the persist, never refer to a store that rejected it

The rules above cover the read direction. The write direction is symmetric and is the one most often missed: a producer that persists a finding MUST check the persist call's exit status, and MUST NOT emit a clean or referral signal on a failed persist.

```text
// BAD — the persist result is discarded, then the caller is referred to the store
for (f in findings) store.add(f)         // a rejection exits 0 and is never read
return { status: "triage_required" }     // "go read the store" — which is empty

// GOOD — the persist is checked, and a short readback downgrades the referral
persisted = []
for (f in findings) {
    if (store.add(f).status == "success") persisted.add(f)
}
if (persisted.size < findings.size) {
    return { status: "error", error: "finding_persist_failed" }
}
return { status: "triage_required" }
```
'''

#: Clause (c) verbatim from the same document — a pair the predicate extractor
#: was NOT authored against. Its directive is a ``Read X first`` form (not the
#: anaphoric ``branch on that`` of clause (d)), and its GOOD example agrees.
_CLAUSE_C_AGREES = '''### (c) Branch on a dispatched producer's status before folding its payload

A producer that crashed, was skipped, or refused returns an empty payload — structurally identical to a producer that ran and found nothing. Read the producer's own status field first; only then fold its payload into the aggregate.

```text
// BAD — the payload is folded without reading the producer's verdict
result = producer.run()
findings.addAll(result.findings)   // a crashed producer contributes zero findings

// GOOD — a failed producer can never read as clean
result = producer.run()
if (result.status != "success") {
    return report(status = "error", reason = producer.name + " did not complete")
}
findings.addAll(result.findings)
```
'''

#: A clause whose GOOD half branches on nothing recoverable — the example is a
#: data table, not a control-flow demonstration.
_NO_BRANCH_PREDICATE = '''### (a) Order specific rows before a catch-all

Read the table top-down; only then act.

```text
// BAD — the broad row is tested first and shadows every specific row below it
PATTERNS = [
    ("bundles/**",        "production"),
    ("bundles/*/test/**", "test"),
]

// GOOD — most specific first; the catch-all is the last resort
PATTERNS = [
    ("bundles/*/test/**", "test"),
    ("bundles/**",        "production"),
]
```
'''

#: A clause with a real BAD/GOOD pair but NO normative predicate directive — the
#: prose states a rule without naming what to branch on, read, or check.
_NO_DIRECTIVE = '''### Symmetric Diagnostic Fields Across Sibling Branches

When one runtime condition drives two sibling branches, the fallback branch MUST record the SAME reason literal into the audit field.

```text
// BAD — the fallback branch under the SAME condition never names the reason
if (mode == "strict" && incompatible) failLoud("env_set")

// GOOD — the sibling branch mirrors the same literal into the audit field
if (mode == "auto" && incompatible) reason = "env_set"
```
'''

#: A lone GOOD example with no BAD counterpart. Its predicate WOULD disagree with
#: the clause, so a green silence here is load-bearing: it proves the pair — not
#: the GOOD half alone — is the unit of adjudication.
_GOOD_WITHOUT_BAD = '''### (d) Require an affirmative success signal, never absence-of-change

Require the operation to report its own outcome and branch on that.

```text
// GOOD — the operation reports whether it applied, and that is what is read
if (outcome.applied) markResolved()
```
'''

#: One clause, one fenced block, TWO GOOD regions — the first agrees with the
#: clause, the second does not. Each region is adjudicated independently.
_MULTIPLE_GOOD_BLOCKS = '''### (x) Branch on the reported status, never on the change flag

Read the reported status field first; only then act on the outcome.

```text
// BAD — branches on the change flag
if (outcome.applied) act()

// GOOD — branches on the reported status
if (outcome.status == "ok") act()

// GOOD — still branches on the change flag
if (outcome.applied) act()
```
'''

#: The same disagreement as ``_PRE_FIX_CLAUSE_D`` but with ``#`` comment markers
#: inside the fence. The ``# ...`` lines must NOT be read as markdown headings —
#: the surfaced entry's ``clause`` proves heading detection is fence-aware.
_HASH_MARKERS_IN_FENCE = '''### (d) Require an affirmative success signal, never absence-of-change

Require the operation to report its own outcome and branch on that.

```python
# BAD — an empty diff is read as proof the fix landed
if diff(file).is_empty():
    mark_resolved()

# GOOD — the operation reports whether it applied
if outcome.applied:
    mark_resolved()
```
'''


def _marker_line(fixture: str, marker_text: str) -> int:
    """Return the 1-based line of ``marker_text`` inside ``fixture``.

    Resolving the expected line from the fixture itself keeps the assertion
    pinned to the marker rather than to a hand-counted offset that a future
    fixture edit would silently invalidate.
    """
    return fixture.splitlines().index(marker_text) + 1


def _adjudicate(fixture: str, path: str = 'error-handling.md') -> list[dict]:
    return _worked_example_pairs(path, fixture.splitlines(), None)


class TestWorkedExamplePairsControlPair:
    """The matched positive/negative control on the checked-in clause-(d) texts.

    The pair discriminates: the SAME clause heading and the SAME prose directive
    appear in both fixtures, and only the GOOD example's branch predicate differs
    (``outcome.applied`` vs ``outcome.status == "success"``). A check that fired
    on registration alone, or that fired on the whole pair-bearing shape, would
    fail one arm or the other.
    """

    def test_pre_fix_clause_d_is_surfaced_as_contradicting(self):
        records = _adjudicate(_PRE_FIX_CLAUSE_D)
        contradicting = [r for r in records if r['agrees'] is False]

        assert len(contradicting) == 1, (
            f'Expected exactly one contradicting pair. Got: {records}'
        )
        entry = contradicting[0]
        assert entry['file'] == 'error-handling.md'
        assert entry['line'] == _marker_line(
            _PRE_FIX_CLAUSE_D,
            '// GOOD — the operation reports whether it applied, and that is what is read',
        )
        assert entry['clause'] == (
            '(d) Require an affirmative success signal, never absence-of-change'
        )
        # The load-bearing half: the entry names BOTH predicates, so the
        # assertion cannot be satisfied by the class merely being registered.
        assert entry['example_predicate'] == 'outcome.applied'
        assert 'success' in entry['required_predicate']

    def test_post_fix_clause_d_is_silent(self):
        records = _adjudicate(_POST_FIX_CLAUSE_D)

        assert [r for r in records if r['agrees'] is False] == [], (
            'The live post-fix clause (d) was surfaced as contradicting — the '
            'class fires on the whole pair-bearing shape instead of on the '
            'predicate disagreement'
        )

    def test_post_fix_negative_is_not_vacuously_clean(self):
        # Silence is only meaningful if the pair was FOUND and ADJUDICATED. A
        # negative that passed because the fixture carried no recognizable pair
        # would prove nothing about the discriminator.
        records = _adjudicate(_POST_FIX_CLAUSE_D)

        assert len(records) == 1, f'The post-fix pair was not found: {records}'
        assert records[0]['agrees'] is True
        assert records[0]['example_predicate'] == 'outcome.status == "success"'

    def test_the_two_fixtures_differ_only_in_the_demonstration(self):
        # Pins the discriminator's premise: both fixtures carry the SAME clause
        # heading, so the opposite verdicts cannot be explained by the clause.
        assert (
            _PRE_FIX_CLAUSE_D.splitlines()[0] == _POST_FIX_CLAUSE_D.splitlines()[0]
        )
        assert 'outcome.applied' in _PRE_FIX_CLAUSE_D
        assert 'outcome.status' in _POST_FIX_CLAUSE_D


class TestWorkedExamplePairsGenerality:
    """The extractor is exercised on pairs it was NOT authored against."""

    def test_clause_c_read_directive_agrees(self):
        # Clause (c) uses a ``Read X first`` directive rather than clause (d)'s
        # anaphoric ``branch on that``, so this exercises the OTHER extraction
        # path end-to-end on real shipped text.
        records = _adjudicate(_CLAUSE_C_AGREES)

        assert len(records) == 1
        assert records[0]['agrees'] is True
        assert records[0]['example_predicate'] == 'result.status != "success"'
        assert 'status' in records[0]['required_predicate']

    def test_hash_comment_markers_inside_a_fence_do_not_open_a_section(self):
        # A ``# BAD`` / ``# GOOD`` line matches the markdown-heading shape. The
        # surfaced entry's clause must still be the real ``###`` heading, which
        # it can only be if heading detection is suppressed inside fences.
        records = _adjudicate(_HASH_MARKERS_IN_FENCE)
        contradicting = [r for r in records if r['agrees'] is False]

        assert len(contradicting) == 1
        assert contradicting[0]['clause'] == (
            '(d) Require an affirmative success signal, never absence-of-change'
        )
        assert contradicting[0]['example_predicate'] == 'outcome.applied'


class TestWorkedExamplePairsRelationalCases:
    """Every relational case carries a DECIDED disposition, each pinned here.

    The class's silence on a case is a decision on the record rather than an
    accident, so each non-surfacing case gets its own assertion.
    """

    def test_clause_with_no_worked_example_surfaces_nothing(self):
        prose_only = (
            '### (d) Require an affirmative success signal\n'
            '\n'
            'Require the operation to report its own outcome and branch on that.\n'
        )
        assert _adjudicate(prose_only) == []

    def test_good_block_without_a_bad_counterpart_surfaces_nothing(self):
        # The GOOD half here WOULD disagree with its clause, so the silence is
        # attributable to the missing BAD half and not to an agreeing predicate.
        assert _adjudicate(_GOOD_WITHOUT_BAD) == []

    def test_clause_with_no_normative_directive_is_not_adjudicable(self):
        records = _adjudicate(_NO_DIRECTIVE)

        assert len(records) == 1, f'The pair itself must still be found: {records}'
        assert records[0]['agrees'] is None
        assert records[0]['required_predicate'] == ''

    def test_good_example_with_no_branch_predicate_is_not_adjudicable(self):
        records = _adjudicate(_NO_BRANCH_PREDICATE)

        assert len(records) == 1, f'The pair itself must still be found: {records}'
        assert records[0]['agrees'] is None
        assert records[0]['example_predicate'] == ''

    def test_multiple_good_blocks_are_adjudicated_independently(self):
        records = _adjudicate(_MULTIPLE_GOOD_BLOCKS)

        assert len(records) == 2, f'Each GOOD region is its own record: {records}'
        assert [r['agrees'] for r in records] == [True, False]
        assert records[0]['example_predicate'] == 'outcome.status == "ok"'
        assert records[1]['example_predicate'] == 'outcome.applied'

    def test_comment_names_a_mechanism_the_body_lacks_is_not_surfaced(self):
        # DECIDED disposition, not an oversight: the pre-fix clause (f) defect is
        # a COMMENT-versus-body claim ("a short readback downgrades the referral"
        # over a body that performs no readback), which is a different shape from
        # the predicate-versus-predicate disagreement this class adjudicates.
        # Every deterministic formulation of the comment check fired on correct
        # sibling examples in the audited population, so it is a broader net
        # rather than a better extractor and is left to ordinary review.
        records = _adjudicate(_PRE_FIX_CLAUSE_F)

        assert [r for r in records if r['agrees'] is False] == []
        # Non-vacuous: the pair WAS found and adjudicated, and its branch
        # predicate genuinely agrees with the clause's ``check X`` directive.
        assert len(records) == 1
        assert records[0]['agrees'] is True


class TestDetectWorkedExamplePairsDiffScope:
    """The diff-driven detector is restricted to touched clause sections."""

    def _write(self, tmp_path: Path, body: str) -> Path:
        target = tmp_path / 'doc.md'
        target.write_text(body)
        return tmp_path

    def test_touched_section_surfaces_the_contradiction(self, tmp_path):
        project_dir = self._write(tmp_path, _PRE_FIX_CLAUSE_D)
        touched_line = _marker_line(
            _PRE_FIX_CLAUSE_D,
            '// GOOD — the operation reports whether it applied, and that is what is read',
        )
        added = [('doc.md', touched_line, 'irrelevant content')]

        out = _detect_worked_example_pairs(added, project_dir)

        assert len(out) == 1
        assert out[0]['agrees'] is False
        assert out[0]['example_predicate'] == 'outcome.applied'

    def test_untouched_section_surfaces_nothing(self, tmp_path):
        # The same document, but the diff touches a line far past the clause's
        # span, so the section is out of the diff's scope.
        project_dir = self._write(tmp_path, _PRE_FIX_CLAUSE_D + '\n## Later\n\nprose\n')
        last_line = len(
            (_PRE_FIX_CLAUSE_D + '\n## Later\n\nprose\n').splitlines()
        )
        added = [('doc.md', last_line, 'prose')]

        assert _detect_worked_example_pairs(added, project_dir) == []

    def test_non_markdown_and_missing_project_dir_surface_nothing(self, tmp_path):
        project_dir = self._write(tmp_path, _PRE_FIX_CLAUSE_D)

        assert _detect_worked_example_pairs([('doc.py', 1, 'x = 1')], project_dir) == []
        assert _detect_worked_example_pairs([('doc.md', 1, 'x')], None) == []
        assert _detect_worked_example_pairs([], project_dir) == []


class TestScanWorkedExamplesVerb:
    """The population-scan verb reports the denominator its verdict is drawn from."""

    def _scan(self, repo: Path, *extra: str):
        from conftest import get_script_path, run_script

        script = get_script_path(
            'pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py'
        )
        return run_script(
            script,
            'scan-worked-examples',
            '--plan-id',
            'population-scan-plan',
            '--project-dir',
            str(repo),
            *extra,
        )

    @staticmethod
    def _populate(repo: Path) -> None:
        (repo / 'standards').mkdir(parents=True, exist_ok=True)
        (repo / 'standards' / 'pre-fix.md').write_text(_PRE_FIX_CLAUSE_D)
        (repo / 'standards' / 'post-fix.md').write_text(_POST_FIX_CLAUSE_D)
        (repo / 'standards' / 'no-pair.md').write_text('# Title\n\nprose only\n')

    def test_reports_population_and_contradicting_count(self, tmp_path):
        repo = tmp_path / 'repo'
        repo.mkdir()
        self._populate(repo)

        result = self._scan(repo, '--paths-glob', 'standards/*.md')
        assert result.success, f'scan failed: stderr={result.stderr}'
        data = result.toon()

        # The denominator is published alongside the verdict: a zero from a real
        # population is distinguishable from a zero from an empty one.
        assert int(data['population']['distinct_paths']) == 3
        assert int(data['population']['pair_bearing_files']) == 2
        assert int(data['population']['pairs_total']) == 2
        assert int(data['population']['pairs_contradicting']) == 1
        assert int(data['population']['pairs_agreeing']) == 1
        assert data['paths_glob'] == 'standards/*.md'
        assert 'standards/*.md' in data['boundary']

        entries = data['worked_example_pairs']
        assert len(entries) == 1
        assert entries[0]['file'] == 'standards/pre-fix.md'

    def test_unadjudicated_list_is_opt_in(self, tmp_path):
        repo = tmp_path / 'repo'
        repo.mkdir()
        (repo / 'standards').mkdir()
        (repo / 'standards' / 'no-directive.md').write_text(_NO_DIRECTIVE)

        without = self._scan(repo, '--paths-glob', 'standards/*.md')
        assert without.success
        data_without = without.toon()
        assert int(data_without['population']['pairs_unadjudicated']) == 1
        assert 'unadjudicated_pairs' not in data_without

        with_flag = self._scan(
            repo, '--paths-glob', 'standards/*.md', '--include-unadjudicated'
        )
        assert with_flag.success
        assert len(with_flag.toon()['unadjudicated_pairs']) == 1

    def test_absolute_paths_glob_is_rejected(self, tmp_path):
        repo = tmp_path / 'repo'
        repo.mkdir()

        result = self._scan(repo, '--paths-glob', '/etc/*.md')

        assert not result.success
        assert result.toon()['error'] == 'paths_glob_invalid'

    def test_parent_directory_paths_glob_is_rejected(self, tmp_path):
        repo = tmp_path / 'repo'
        repo.mkdir()

        result = self._scan(repo, '--paths-glob', '../*.md')

        assert not result.success
        assert result.toon()['error'] == 'paths_glob_invalid'

    def test_empty_population_is_reported_as_zero_not_as_a_clean_verdict(self, tmp_path):
        # The vacuous case the published denominator exists to expose: no file
        # matched, so the zero contradiction count carries a zero population.
        repo = tmp_path / 'repo'
        repo.mkdir()

        result = self._scan(repo, '--paths-glob', 'standards/*.md')
        assert result.success
        data = result.toon()

        assert int(data['population']['distinct_paths']) == 0
        assert int(data['population']['pairs_total']) == 0
        assert int(data['population']['pairs_contradicting']) == 0


# =============================================================================
# Test: counts.total invariant (review-anchor lists excluded from total)
# =============================================================================


class TestCountsTotalInvariant:
    """``counts.total`` sums exactly the registry's ``in_total`` lists.

    The end-to-end ``surface`` output sums every candidate list into
    ``counts.total`` EXCEPT those the ``CANDIDATE_LISTS`` registry marks
    ``in_total=False``. This test drives the real ``_cmd_surface`` path over a git
    fixture whose uncommitted diff triggers the advertised-form detector, and
    asserts the new detector populates its own list while leaving ``total`` equal
    to the sum of the INCLUDED lists only.
    """

    #: The lists excluded from ``counts.total``, derived from the registry rather
    #: than hand-mirrored. The hand-written tuple this replaces named only the
    #: four review-anchor lists and omitted ``protected_identifiers``, which is
    #: ALSO excluded from ``total`` — so the invariant below held only while that
    #: list happened to be empty in every fixture.
    _EXCLUDED_FROM_TOTAL = tuple(
        spec.key for spec in CANDIDATE_LISTS if not spec.in_total
    )

    def _surface(self, repo: Path):
        from conftest import get_script_path, run_script

        script = get_script_path(
            'pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py'
        )
        result = run_script(
            script,
            'surface',
            '--plan-id',
            'counts-invariant-plan',
            '--project-dir',
            str(repo),
            '--base-branch',
            'main',
        )
        assert result.success, f'surface failed: stderr={result.stderr}'
        return result.toon()

    def test_advertised_form_excluded_from_total(self, tmp_path):
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        # An uncommitted change that triggers the advertised-form detector: a
        # multi-form help string plus a raw pass-through of args.issue.
        (repo / 'cli.py').write_text(
            'import argparse\n'
            '\n'
            'def build(p):\n'
            "    p.add_argument('--issue', help='Issue number or URL')\n"
            '\n'
            'def run(args):\n'
            '    return str(args.issue)\n'
        )
        _git(repo, 'add', 'cli.py')

        data = self._surface(repo)

        # The new detector fired.
        assert int(data['counts']['advertised_form_help_strings']) >= 1
        assert len(data['advertised_form_help_strings']) >= 1

        # counts.total equals the sum of every count EXCEPT the four review-anchor
        # lists — proving the advertised-form list is excluded.
        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum

    def test_total_invariant_holds_with_no_advertised_form(self, tmp_path):
        # A diff that does NOT trigger the advertised-form detector must still
        # satisfy the invariant — total == sum of included lists.
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'plain.py').write_text('x = 1\nprint("hello")\n')
        _git(repo, 'add', 'plain.py')

        data = self._surface(repo)

        assert int(data['counts']['advertised_form_help_strings']) == 0
        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum

    def test_ordinal_references_included_in_total(self, tmp_path):
        # An uncommitted .md diff that adds an ordered list AND a same-document
        # ordinal reference into it triggers the ordinal_references detector,
        # which IS summed into counts.total (unlike the review-anchor lists).
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'guide.md').write_text(
            '1. First item\n'
            '2. Second item\n'
            '3. Third item\n'
            '\n'
            'See item 2 for the prerequisite.\n'
        )
        _git(repo, 'add', 'guide.md')

        data = self._surface(repo)

        # The new detector fired and populated its own list.
        assert int(data['counts']['ordinal_references']) >= 1
        assert len(data['ordinal_references']) >= 1

        # ordinal_references is marked in_total — it is summed into total. The
        # invariant (total == sum of included lists) therefore still holds, and
        # the included sum carries the ordinal_references count.
        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum
        assert 'ordinal_references' not in self._EXCLUDED_FROM_TOTAL


    def test_scan_derived_keys_included_in_total(self, tmp_path):
        # An uncommitted .py diff carrying the scan-versus-anchor derivation
        # triggers the scan_derived_keys detector, which IS summed into
        # counts.total (unlike the review-anchor lists).
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'gen.py').write_text(
            'import re\n'
            'from pathlib import Path\n'
            '\n'
            "_VERSION_DIR_NAME_RE = re.compile(r'^0-9')\n"
            '\n'
            'def split_bundle_version(path):\n'
            '    parts = Path(path).parts\n'
            '    for index, part in enumerate(parts):\n'
            '        if index > 0 and _VERSION_DIR_NAME_RE.match(part):\n'
            '            return parts[index - 1], part\n'
            '    return None\n'
        )
        _git(repo, 'add', 'gen.py')

        data = self._surface(repo)

        # The new detector fired and populated its own list.
        assert int(data['counts']['scan_derived_keys']) >= 1
        assert len(data['scan_derived_keys']) >= 1

        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum
        assert 'scan_derived_keys' not in self._EXCLUDED_FROM_TOTAL

    def test_worked_example_pairs_included_in_total(self, tmp_path):
        # An uncommitted .md diff carrying a clause whose GOOD example branches
        # on a predicate its clause does not require triggers the
        # worked_example_pairs detector, which IS summed into counts.total
        # (unlike the review-anchor lists). This drives the REAL surface path, so
        # it also pins that the diff-scoped detector is wired into the emitter.
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'clause.md').write_text(_PRE_FIX_CLAUSE_D)
        _git(repo, 'add', 'clause.md')

        data = self._surface(repo)

        assert int(data['counts']['worked_example_pairs']) >= 1
        entries = data['worked_example_pairs']
        assert len(entries) >= 1
        assert entries[0]['example_predicate'] == 'outcome.applied'

        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum
        assert 'worked_example_pairs' not in self._EXCLUDED_FROM_TOTAL

    def test_worked_example_pairs_invariant_holds_when_list_is_empty(self, tmp_path):
        # The inclusion invariant must hold whether or not the list fires — and
        # the post-fix clause text is the discriminating empty case, not merely
        # a diff with no markdown in it.
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'clause.md').write_text(_POST_FIX_CLAUSE_D)
        _git(repo, 'add', 'clause.md')

        data = self._surface(repo)

        assert int(data['counts']['worked_example_pairs']) == 0
        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum

    def test_scan_derived_keys_invariant_holds_when_list_is_empty(self, tmp_path):
        # The inclusion invariant must hold whether or not the list fires.
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'plain.py').write_text('x = 1\ny = x + 1\n')
        _git(repo, 'add', 'plain.py')

        data = self._surface(repo)

        assert int(data['counts']['scan_derived_keys']) == 0
        counts = data['counts']
        included_sum = sum(
            int(v)
            for k, v in counts.items()
            if k != 'total' and k not in self._EXCLUDED_FROM_TOTAL
        )
        assert int(counts['total']) == included_sum


# =============================================================================
# Resolver-migration contract
# =============================================================================
#
# ``surface`` is the one verb here that binds a working tree. Its ``--plan-id``
# branch resolves through ``resolve_project_dir``, which delegates the worktree
# face to ``file_ops.resolve_plan_context``. The assertions below go through the
# SCRIPT's own imported symbol, so they state that THIS script routes through
# the resolver — not merely that the shared helper does.
#
# ``--project-dir`` remains a first-class escape hatch here (unlike most Bucket
# B scripts, ``self_review`` legitimately needs ``--plan-id`` for its
# modified-files lookup even when the path is supplied), so the no-resolution
# case is pinned too.


class TestSurfaceResolverMigration:
    def test_plan_id_branch_routes_through_the_resolver(self):
        """The worktree face reaches the single ``get-worktree-path`` seam."""
        import self_review

        assert_worktree_face_routes_through_resolver(
            lambda plan_id: self_review.resolve_project_dir(plan_id, None, default=None)
        )

    def test_no_plan_sentinel_is_accepted(self):
        """``--plan-id NO_PLAN`` resolves to the main checkout without shelling out.

        The plan-less path matters for this verb specifically: a pre-submission
        self-review is exactly the kind of ad-hoc, plan-less invocation the
        sentinel exists to serve.
        """
        import self_review

        assert_sentinel_accepted(
            lambda plan_id: self_review.resolve_project_dir(plan_id, None, default=None)
        )

    def test_explicit_project_dir_bypasses_resolution_entirely(self, tmp_path, monkeypatch, capsys):
        """``--project-dir`` short-circuits before any worktree resolution.

        The escape hatch must not pay (or fail on) a plan resolution: a caller
        who already knows the path supplies it, and ``--plan-id`` is then only a
        lookup key for the modified-files read. The seam is armed to RAISE, so a
        resolution that happens at all fails the test — which is what makes this
        a genuine short-circuit assertion rather than one satisfied by a
        resolution whose result is merely discarded.

        Driven IN-PROCESS (``_cmd_surface`` directly, not ``run_script``): a
        subprocess would not inherit the monkeypatched seam, leaving the guard
        armed in this process and unarmed in the one under test.
        """
        import file_ops  # noqa: PLC0415
        import self_review

        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})

        def _forbidden(_plan_id):
            raise AssertionError('--project-dir still consulted the worktree resolver')

        monkeypatch.setattr(file_ops, '_query_worktree_path', _forbidden)

        # Build the namespace from the REAL parser rather than hand-rolling a
        # Namespace: the handler reads options (``--contract-radius``) that a
        # hand-built stand-in silently omits, and every such omission is an
        # AttributeError that reads as a resolver failure it is not.
        args = _build_parser().parse_args(
            [
                'surface',
                '--plan-id',
                'escape-hatch-plan',
                '--project-dir',
                str(repo),
                '--base-branch',
                'main',
            ]
        )
        rc = self_review._cmd_surface(args)

        out = capsys.readouterr().out
        assert rc == 0, out
        assert 'worktree_resolution_failed' not in out


# =============================================================================
# Test: CANDIDATE_LISTS registry (single-sourced candidate vocabulary)
# =============================================================================


class TestCandidateListRegistry:
    """The registry is the single code-side source of the candidate vocabulary.

    ``counts``, the emitted payload key set, and the ``surface`` help prose are
    all derived from ``CANDIDATE_LISTS``. These cases pin the registry's own
    integrity and prove each derivation actually reads it, so a list cannot be
    added to the emitter without appearing in the count and the help string.
    """

    def test_keys_and_labels_are_unique(self):
        keys = [spec.key for spec in CANDIDATE_LISTS]
        labels = [spec.label for spec in CANDIDATE_LISTS]

        assert len(set(keys)) == len(keys), f'Duplicate registry key: {keys}'
        assert len(set(labels)) == len(labels), f'Duplicate registry label: {labels}'
        assert all(keys) and all(labels), 'Registry entries must be non-empty'

    def test_in_total_partition_is_not_degenerate(self):
        # Both sides of the partition must be populated. A registry where every
        # entry carried the same in_total value would make the total formula
        # either "sum everything" or "sum nothing", and the exclusion assertions
        # elsewhere in this module would stop discriminating.
        included = [spec.key for spec in CANDIDATE_LISTS if spec.in_total]
        excluded = [spec.key for spec in CANDIDATE_LISTS if not spec.in_total]

        assert included, 'No candidate list feeds counts.total'
        assert excluded, 'No candidate list is excluded from counts.total'

    def test_surface_help_is_derived_from_the_registry(self):
        # The help string must enumerate the registry rather than a hand-mirrored
        # copy: every label present, and the cardinality stated as a derived
        # number rather than a literal word that can go stale.
        help_text = ' '.join(_build_parser().format_help().split())

        assert f'Emit {len(CANDIDATE_LISTS)} candidate lists' in help_text
        missing = [spec.label for spec in CANDIDATE_LISTS if spec.label not in help_text]
        assert not missing, f'Registry labels absent from surface help: {missing}'

    def test_candidate_list_prose_enumerates_every_entry(self):
        prose = candidate_list_prose()

        assert prose.split(', ') == [spec.label for spec in CANDIDATE_LISTS]

    @staticmethod
    def _empty_detected() -> dict:
        return {spec.key: [] for spec in CANDIDATE_LISTS}

    def test_compose_derives_counts_and_payload_from_the_registry(self):
        detected = self._empty_detected()
        detected['regexes'] = [{'file': 'a.py', 'line': 1, 'pattern': 'x'}]
        detected['contract_sources'] = [{'file': 'a.py', 'sources': 's'}]

        composed = _compose_candidate_output(detected)

        assert set(composed) - {'counts'} == {spec.key for spec in CANDIDATE_LISTS}
        assert composed['counts']['regexes'] == 1
        assert composed['counts']['contract_sources'] == 1
        # regexes is in_total, contract_sources is not — so total counts one.
        assert composed['counts']['total'] == 1

    def test_compose_rejects_a_detector_result_with_no_registry_entry(self):
        # The drift direction that would otherwise be SILENT: an emitter gains a
        # list, the registry does not, and the list vanishes from both the
        # payload and the count with no error.
        detected = self._empty_detected()
        detected['brand_new_list'] = []

        with pytest.raises(ValueError, match='brand_new_list'):
            _compose_candidate_output(detected)

    def test_compose_rejects_a_registry_entry_with_no_detector_result(self):
        detected = self._empty_detected()
        dropped = CANDIDATE_LISTS[0].key
        del detected[dropped]

        with pytest.raises(ValueError, match=dropped):
            _compose_candidate_output(detected)

    def test_emitted_payload_and_counts_keys_equal_the_registry(self, tmp_path):
        # End-to-end: the real surface output's counts keys (minus ``total``) and
        # its top-level payload keys must BOTH equal the registry key set.
        repo = tmp_path / 'repo'
        _init_repo(repo)
        _commit(repo, 'base', {'base.txt': 'base\n'})
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'plain.py').write_text('x = 1\ny = x + 1\n')
        _git(repo, 'add', 'plain.py')

        from conftest import get_script_path, run_script

        script = get_script_path(
            'pm-plugin-development', 'ext-self-review-plan-marshall', 'self_review.py'
        )
        result = run_script(
            script,
            'surface',
            '--plan-id',
            'registry-vocabulary-plan',
            '--project-dir',
            str(repo),
            '--base-branch',
            'main',
        )
        assert result.success, f'surface failed: stderr={result.stderr}'
        data = result.toon()

        registry_keys = {spec.key for spec in CANDIDATE_LISTS}

        assert set(data['counts']) - {'total'} == registry_keys
        assert registry_keys <= set(data), (
            f'Payload is missing registry keys: {sorted(registry_keys - set(data))}'
        )
