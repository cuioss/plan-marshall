#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for asciidoc.py - AsciiDoc formatting, validation, and link operations.

Tier 2 (direct import) tests with subprocess CLI plumbing tests retained.
"""

import json
import tempfile
import warnings
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

TEST_DIR = Path(__file__).parent
SCRIPT_PATH = get_script_path('pm-documents', 'ref-asciidoc', 'asciidoc.py')
FIXTURES_DIR = TEST_DIR / 'fixtures'
LINK_VERIFY_FIXTURES = FIXTURES_DIR / 'link-verify'


def _load_module(name, filename):
    return load_script_module('pm-documents', 'ref-asciidoc', filename, name)


_stats_mod = _load_module('_cmd_stats', '_cmd_stats.py')
_validate_mod = _load_module('_cmd_validate', '_cmd_validate.py')
_format_mod = _load_module('_cmd_format', '_cmd_format.py')
_verify_links_mod = _load_module('_cmd_verify_links', '_cmd_verify_links.py')
_classify_links_mod = _load_module('_cmd_classify_links', '_cmd_classify_links.py')

cmd_stats = _stats_mod.cmd_stats
analyze_file_stats = _stats_mod.analyze_file_stats
cmd_validate = _validate_mod.cmd_validate
cmd_format = _format_mod.cmd_format
cmd_verify_links = _verify_links_mod.cmd_verify_links
verify_links = _verify_links_mod.verify_links
extract_anchors_from_file = _verify_links_mod.extract_anchors_from_file
extract_links_from_file = _verify_links_mod.extract_links_from_file
cmd_classify_links = _classify_links_mod.cmd_classify_links

FORMAT_FIX_TYPES = ['lists', 'xref', 'whitespace', 'all']


# Tier 2: Main help (CLI plumbing)


def test_script_file_exists():
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_fixtures_directory_exists():
    assert FIXTURES_DIR.exists(), f'Fixtures not found: {FIXTURES_DIR}'


def test_main_help_lists_all_subcommands():
    result = run_script(SCRIPT_PATH, '--help')

    combined = result.stdout + result.stderr
    assert 'stats' in combined, 'stats subcommand in help'
    assert 'validate' in combined, 'validate subcommand in help'
    assert 'format' in combined, 'format subcommand in help'


# Tier 2: Stats subcommand


def test_stats_help_shows_usage():
    result = run_script(SCRIPT_PATH, 'stats', '--help')

    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f'Stats help not shown: {combined}'


def test_stats_console_format_returns_summary():
    result = cmd_stats(Namespace(command='stats', directory=str(FIXTURES_DIR), format='console', details=False))

    assert result['status'] == 'success', f'Expected success status, got: {result.get("status")}'
    assert 'summary' in result, 'Stats output should contain summary'


def test_stats_json_format_includes_metadata_and_summary():
    result = cmd_stats(Namespace(command='stats', directory=str(FIXTURES_DIR), format='json', details=False))

    assert 'metadata' in result, 'Result missing metadata'
    assert 'summary' in result, 'Result missing summary'


def test_stats_details_flag_includes_files():
    result = cmd_stats(Namespace(command='stats', directory=str(FIXTURES_DIR), format='json', details=True))

    assert 'files' in result, 'Result with details flag should include files key'


def test_stats_counts_indented_list_markers():
    """The leading horizontal-whitespace class must match space-indented and
    tab-indented list markers (``*``, numbered, ``::``). Six list lines are
    present; non-list lines must not be counted.
    """
    content = (
        '= Title\n'
        '\n'
        'Intro paragraph, not a list.\n'
        '* top-level bullet\n'
        '  * space-indented bullet\n'
        '\t* tab-indented bullet\n'
        '1. numbered marker\n'
        '  2. space-indented numbered marker\n'
        'term:: definition\n'
        'A plain sentence without markers.\n'
        'Use std::cout here -- C++ scope operator, not a labeled list.\n'
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False) as f:
        f.write(content)
        temp_file = Path(f.name)

    try:
        stats = analyze_file_stats(temp_file)

        assert stats['lists'] == 6, f'Expected 6 list markers, got {stats["lists"]}'
    finally:
        temp_file.unlink(missing_ok=True)


def test_stats_lists_regex_raises_no_future_warning():
    """The stats path must not raise FutureWarning (POSIX-class regex regression guard)."""
    content = '= Title\n\n* bullet\n  * indented bullet\n\tterm:: def\n'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False) as f:
        f.write(content)
        temp_file = Path(f.name)

    try:
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter('always')
            analyze_file_stats(temp_file)

        future_warnings = [w for w in recorded if issubclass(w.category, FutureWarning)]
        assert not future_warnings, f'Unexpected FutureWarning(s): {[str(w.message) for w in future_warnings]}'
    finally:
        temp_file.unlink(missing_ok=True)


def test_stats_handles_empty_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        result = cmd_stats(Namespace(command='stats', directory=temp_dir, format='console', details=False))

        assert result['status'] == 'success'


def test_stats_nonexistent_directory_reports_error():
    result = cmd_stats(Namespace(command='stats', directory='/nonexistent/path', format='console', details=False))

    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# Tier 2: Validate subcommand


def test_validate_console_format_returns_status():
    result = cmd_validate(Namespace(command='validate', path=str(FIXTURES_DIR), format='console', ignore_patterns=None))

    assert result['status'] in ('success', 'non_compliant'), f'Unexpected status: {result["status"]}'


def test_validate_json_format_includes_directory():
    result = cmd_validate(Namespace(command='validate', path=str(FIXTURES_DIR), format='json', ignore_patterns=None))

    assert 'directory' in result, "JSON format didn't produce expected output"


def test_validate_detects_missing_blank_line_before_list():
    content = """= Test Document
:toc: left
:toclevels: 3
:toc-title: Table of Contents
:sectnums:
:source-highlighter: highlight.js

== Section One
Some text directly before list:
* List item 1
* List item 2
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False) as f:
        f.write(content)
        temp_file = f.name

    try:
        result = cmd_validate(Namespace(command='validate', path=temp_file, format='console', ignore_patterns=None))

        assert result['status'] == 'non_compliant' or 'blank' in str(result).lower(), (
            'Missing blank line should be detected'
        )
    finally:
        Path(temp_file).unlink(missing_ok=True)


def test_validate_accepts_ignore_pattern():
    result = cmd_validate(
        Namespace(command='validate', path=str(FIXTURES_DIR), format='console', ignore_patterns=['missing-*.adoc'])
    )

    assert result['status'] in ('success', 'non_compliant', 'error')


def test_validate_rejects_invalid_format():
    result = run_script(SCRIPT_PATH, 'validate', '-f', 'invalid_format')

    assert result.returncode != 0, 'Invalid format should be rejected'


def test_validate_nonexistent_path_reports_error():
    result = cmd_validate(
        Namespace(command='validate', path='/nonexistent/path', format='console', ignore_patterns=None)
    )

    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# Tier 2: Format subcommand


def test_format_no_backup_flag_succeeds():
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=['lists'], no_backup=True))

    assert result['status'] == 'success'


@pytest.mark.parametrize('fix_type', FORMAT_FIX_TYPES)
def test_format_accepts_fix_type(fix_type):
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=[fix_type], no_backup=True))

    assert result['status'] == 'success'


def test_format_rejects_invalid_fix_type():
    result = run_script(SCRIPT_PATH, 'format', '-t', 'invalid_type')

    assert result.returncode != 0, 'Invalid fix type should be rejected'


def test_format_nonexistent_path_reports_error():
    result = cmd_format(Namespace(command='format', path='/nonexistent/path', fix_types=None, no_backup=False))

    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# Tier 2: Verify-links subcommand


def test_verify_links_processes_single_file():
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'

    result = cmd_verify_links(
        Namespace(command='verify-links', file=str(empty_file), directory=None, recursive=False, report=None)
    )

    assert str(result.get('data', {}).get('files_processed', '')) == '1', 'Single file mode processes one file'


def test_verify_links_handles_empty_file():
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'

    result = cmd_verify_links(
        Namespace(command='verify-links', file=str(empty_file), directory=None, recursive=False, report=None)
    )

    assert result['status'] in ('success', 'failure', 'error')


def test_verify_links_missing_file_reports_error():
    result = cmd_verify_links(
        Namespace(command='verify-links', file='/nonexistent/file.adoc', directory=None, recursive=False, report=None)
    )

    assert result['status'] == 'error', 'Error when file does not exist'


def test_verify_links_rejects_both_file_and_directory():
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'

    result = cmd_verify_links(
        Namespace(
            command='verify-links',
            file=str(empty_file),
            directory=str(LINK_VERIFY_FIXTURES),
            recursive=False,
            report=None,
        )
    )

    assert 'cannot specify both' in result.get('message', '').lower(), (
        'Error when both --file and --directory specified'
    )


# Tier 2: Classify-links subcommand


def test_classify_links_writes_categorized_output():
    input_data = {
        'issues': [
            {'file': 'standards/security.adoc', 'line': 42, 'link': '<<owasp-top-10>>', 'type': 'broken_anchor'},
            {'file': 'guide.adoc', 'line': 56, 'link': 'file:///local/path/doc.pdf', 'type': 'broken_link'},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(input_data, f)
        input_file = Path(f.name)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_file = Path(f.name)

    try:
        result = cmd_classify_links(
            Namespace(command='classify-links', input=str(input_file), output=str(output_file), pretty=True)
        )

        assert result['status'] == 'success'
        assert output_file.exists(), 'Classification completed'
        content = output_file.read_text()
        has_categories = 'likely-false-positive' in content or 'must-verify-manual' in content
        assert has_categories, 'Found expected categories in output'
    finally:
        input_file.unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)


# Tier 2: Link-verification core logic (anchor extraction, link resolution)


def _write_adoc(directory: Path, name: str, content: str) -> str:
    """Write an .adoc file under ``directory`` and return its string path."""
    path = directory / name
    path.write_text(content, encoding='utf-8')
    return str(path)


def test_extract_anchors_collects_explicit_ids_and_section_titles():
    """Anchors come from ``[[id]]``, ``[#id]``, and normalised section titles."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        adoc = _write_adoc(
            d,
            'a.adoc',
            '= Doc\n\n[[explicit-anchor]]\n[#hash-anchor]\n\n== My Section Heading\n\nbody\n',
        )

        anchors = extract_anchors_from_file(adoc)

        assert 'explicit-anchor' in anchors
        assert 'hash-anchor' in anchors
        assert 'my-section-heading' in anchors  # section title normalised to a slug


def test_verify_links_valid_cross_ref_to_explicit_anchor_has_no_issue():
    """A ``<<anchor>>`` that resolves to a defined ``[[anchor]]`` is not flagged."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        adoc = _write_adoc(d, 'a.adoc', '= Doc\n\n[[target]]\nSee <<target>> above.\n')

        _links, issues = verify_links([adoc])

        assert issues == []


def test_verify_links_cross_ref_resolves_section_title_anchor():
    """A cross-ref may resolve against a section-title-derived anchor."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        adoc = _write_adoc(d, 'a.adoc', '= Doc\n\n== Overview\n\nJump to <<overview>>.\n')

        _links, issues = verify_links([adoc])

        assert issues == []


def test_verify_links_broken_cross_ref_is_reported():
    """A ``<<missing>>`` with no matching anchor is a broken-link issue."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        adoc = _write_adoc(d, 'a.adoc', '= Doc\n\nDangling <<missing-anchor>> ref.\n')

        _links, issues = verify_links([adoc])

        broken = [i for i in issues if i.issue_type == 'broken']
        assert any('missing-anchor' in i.description for i in broken)


def test_verify_links_xref_to_missing_target_is_reported():
    """An ``xref:`` to a non-existent target file is a broken-link issue."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        adoc = _write_adoc(d, 'a.adoc', '= Doc\n\nSee xref:nope.adoc[Nope].\n')

        _links, issues = verify_links([adoc])

        assert any(i.issue_type == 'broken' and 'not found' in i.description for i in issues)


def test_verify_links_xref_to_existing_target_has_no_issue():
    """An ``xref:`` to a sibling file that exists resolves cleanly."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_adoc(d, 'b.adoc', '= B\n\nbody\n')
        a = _write_adoc(d, 'a.adoc', '= A\n\nSee xref:b.adoc[B].\n')

        _links, issues = verify_links([a])

        assert issues == []


def test_verify_links_xref_to_missing_anchor_in_existing_target_is_reported():
    """An ``xref:`` whose target exists but lacks the referenced anchor is broken."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_adoc(d, 'b.adoc', '= B\n\nno anchors here\n')
        a = _write_adoc(d, 'a.adoc', '= A\n\nSee xref:b.adoc#ghost[B].\n')

        _links, issues = verify_links([a])

        assert any(i.issue_type == 'broken' and 'ghost' in i.description for i in issues)


def test_verify_links_deprecated_double_angle_adoc_is_a_format_violation():
    """The legacy ``<<file.adoc>>`` include form is flagged as a format violation
    with an ``xref:`` migration suggestion."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        adoc = _write_adoc(d, 'a.adoc', '= Doc\n\nOld style <<legacy.adoc>> link.\n')

        _links, issues = verify_links([adoc])

        violations = [i for i in issues if i.issue_type == 'format_violation']
        assert violations
        assert violations[0].suggested_fix.startswith('xref:')


def test_cmd_verify_links_directory_mode_processes_every_adoc():
    """Directory mode verifies every .adoc file under the directory."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_adoc(d, 'one.adoc', '= One\n\nbody\n')
        _write_adoc(d, 'two.adoc', '= Two\n\nbody\n')

        result = cmd_verify_links(
            Namespace(command='verify-links', file=None, directory=str(d), recursive=False, report=None)
        )

        assert result['data']['files_processed'] == 2


def test_cmd_verify_links_empty_directory_reports_no_files():
    """A directory with no .adoc files yields a structured no_files error."""
    with tempfile.TemporaryDirectory() as tmp:
        result = cmd_verify_links(
            Namespace(command='verify-links', file=None, directory=tmp, recursive=False, report=None)
        )

        assert result['status'] == 'error'
        assert result['error'] == 'no_files'


def test_cmd_verify_links_writes_report_file_when_requested():
    """``--report`` persists the full result as JSON to the given path."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_adoc(d, 'a.adoc', '= Doc\n\n[[ok]]\n<<ok>>\n')
        report = d / 'report.json'

        result = cmd_verify_links(
            Namespace(command='verify-links', file=str(d / 'a.adoc'), directory=None, recursive=False, report=str(report))
        )

        assert report.exists()
        persisted = json.loads(report.read_text())
        assert persisted['status'] == result['status']
        assert 'data' in persisted
