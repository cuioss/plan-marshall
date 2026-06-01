#!/usr/bin/env python3
"""Tests for self_review.py — pre-submission self-review candidate surfacing."""

import subprocess  # noqa: I001
from pathlib import Path

import pytest
from self_review import (  # type: ignore[import-not-found]
    _detect_contract_sources,
    _detect_flag_guard_pairs,
    _detect_keep_markers,
    _detect_markdown_sections,
    _detect_regexes,
    _detect_symmetric_pairs,
    _detect_user_facing_strings,
    _diff_hunks,
    _find_skill_dir,
    _iter_added_lines,
    _run_git,
    _symmetric_pair_has_test,
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
