#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for asciidoc.py - AsciiDoc formatting, validation, and link operations.

Tier 2 (direct import) tests with subprocess CLI plumbing tests retained.
"""

import json
import os
import tempfile
import warnings
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, parse_ns, run_script

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

# Argument namespaces come from the script's OWN parser, so each carries every
# default the real CLI applies — several sites below omitted flags the parser
# defaults (``format``, ``details``, ``ignore_patterns``), which a hand-built
# namespace simply lacks. Parsed once at module scope: parse_ns re-executes the
# script module on every call.
_STATS_NS = parse_ns(
    'pm-documents',
    'ref-asciidoc',
    'asciidoc.py',
    'stats',
    '--directory',
    '.',
    register=False,
)
_VALIDATE_NS = parse_ns(
    'pm-documents',
    'ref-asciidoc',
    'asciidoc.py',
    'validate',
    '--path',
    '.',
    register=False,
)
_FORMAT_NS = parse_ns(
    'pm-documents',
    'ref-asciidoc',
    'asciidoc.py',
    'format',
    '--path',
    '.',
    register=False,
)
_VERIFY_LINKS_NS = parse_ns(
    'pm-documents',
    'ref-asciidoc',
    'asciidoc.py',
    'verify-links',
    '--file',
    'placeholder.adoc',
    register=False,
)
_CLASSIFY_NS = parse_ns(
    'pm-documents',
    'ref-asciidoc',
    'asciidoc.py',
    'classify-links',
    register=False,
)


def _ns(template: Namespace, **overrides) -> Namespace:
    """A parser-produced namespace with this test's values overlaid."""
    return Namespace(**{**vars(template), **overrides})


cmd_verify_links = _verify_links_mod.cmd_verify_links
verify_links = _verify_links_mod.verify_links
extract_anchors_from_file = _verify_links_mod.extract_anchors_from_file
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
    result = cmd_stats(_ns(_STATS_NS, directory=str(FIXTURES_DIR), format='console', details=False))

    assert result['status'] == 'success', f'Expected success status, got: {result.get("status")}'
    assert 'summary' in result, 'Stats output should contain summary'


def test_stats_json_format_includes_metadata_and_summary():
    result = cmd_stats(_ns(_STATS_NS, directory=str(FIXTURES_DIR), format='json', details=False))

    assert 'metadata' in result, 'Result missing metadata'
    assert 'summary' in result, 'Result missing summary'


def test_stats_details_flag_includes_files():
    result = cmd_stats(_ns(_STATS_NS, directory=str(FIXTURES_DIR), format='json', details=True))

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
        result = cmd_stats(_ns(_STATS_NS, directory=temp_dir, format='console', details=False))

        assert result['status'] == 'success'


def test_stats_nonexistent_directory_reports_error():
    result = cmd_stats(_ns(_STATS_NS, directory='/nonexistent/path', format='console', details=False))

    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# Tier 2: Validate subcommand


def test_validate_console_format_returns_status():
    result = cmd_validate(_ns(_VALIDATE_NS, path=str(FIXTURES_DIR), format='console', ignore_patterns=None))

    assert result['status'] in ('success', 'non_compliant'), f'Unexpected status: {result["status"]}'


def test_validate_json_format_includes_directory():
    result = cmd_validate(_ns(_VALIDATE_NS, path=str(FIXTURES_DIR), format='json', ignore_patterns=None))

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
        result = cmd_validate(_ns(_VALIDATE_NS, path=temp_file, format='console', ignore_patterns=None))

        assert result['status'] == 'non_compliant' or 'blank' in str(result).lower(), (
            'Missing blank line should be detected'
        )
    finally:
        Path(temp_file).unlink(missing_ok=True)


def test_validate_accepts_ignore_pattern():
    result = cmd_validate(
        _ns(_VALIDATE_NS, path=str(FIXTURES_DIR), format='console', ignore_patterns=['missing-*.adoc'])
    )

    assert result['status'] in ('success', 'non_compliant', 'error')


def test_validate_rejects_invalid_format():
    result = run_script(SCRIPT_PATH, 'validate', '-f', 'invalid_format')

    assert result.returncode != 0, 'Invalid format should be rejected'


def test_validate_nonexistent_path_reports_error():
    result = cmd_validate(_ns(_VALIDATE_NS, path='/nonexistent/path', format='console', ignore_patterns=None))

    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# Tier 2: Format subcommand


def test_format_no_backup_flag_succeeds():
    result = cmd_format(_ns(_FORMAT_NS, path=str(FIXTURES_DIR), fix_types=['lists'], no_backup=True))

    assert result['status'] == 'success'


@pytest.mark.parametrize('fix_type', FORMAT_FIX_TYPES)
def test_format_accepts_fix_type(fix_type):
    result = cmd_format(_ns(_FORMAT_NS, path=str(FIXTURES_DIR), fix_types=[fix_type], no_backup=True))

    assert result['status'] == 'success'


def test_format_rejects_invalid_fix_type():
    result = run_script(SCRIPT_PATH, 'format', '-t', 'invalid_type')

    assert result.returncode != 0, 'Invalid fix type should be rejected'


def test_format_nonexistent_path_reports_error():
    result = cmd_format(_ns(_FORMAT_NS, path='/nonexistent/path', fix_types=None, no_backup=False))

    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# Tier 2: Verify-links subcommand


def test_verify_links_processes_single_file():
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(empty_file), directory=None, recursive=False, report=None))

    assert str(result.get('data', {}).get('files_processed', '')) == '1', 'Single file mode processes one file'


def test_verify_links_handles_empty_file():
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(empty_file), directory=None, recursive=False, report=None))

    assert result['status'] in ('success', 'failure', 'error')


def test_verify_links_missing_file_reports_error():
    result = cmd_verify_links(
        _ns(_VERIFY_LINKS_NS, file='/nonexistent/file.adoc', directory=None, recursive=False, report=None)
    )

    assert result['status'] == 'error', 'Error when file does not exist'


def test_verify_links_file_mode_refuses_a_markdown_file(tmp_path):
    """A Markdown file is not an AsciiDoc file: the AsciiDoc grammar finds no links in it.

    Reporting ``total_links: 0`` with ``status: success`` over such a file is a pass
    over a file the checker never read. File mode refuses it with the same
    ``no_files``-class error directory mode already returns for a directory that
    holds no ``.adoc`` file.
    """
    md = tmp_path / 'notes.md'
    md.write_text(
        '# Title\n\nSee [the missing page](./missing.md) and [another](./nowhere.md).\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(md), directory=None, recursive=False, report=None))

    assert result['status'] == 'error'
    assert result['error'] == 'no_files'
    assert 'data' not in result, 'a refused file must not report a link count'


def test_verify_links_file_mode_refusal_is_the_directory_mode_error_class(tmp_path):
    """The refusal is the same error the directory mode returns, not a new one."""
    md = tmp_path / 'notes.md'
    md.write_text('one [link](./gone.md)\n', encoding='utf-8')
    empty_dir = tmp_path / 'docs'
    empty_dir.mkdir()

    file_mode = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(md), directory=None, recursive=False, report=None))
    dir_mode = cmd_verify_links(
        _ns(_VERIFY_LINKS_NS, file=None, directory=str(empty_dir), recursive=False, report=None)
    )

    assert file_mode['error'] == dir_mode['error'] == 'no_files'


def test_verify_links_file_mode_still_reads_an_asciidoc_file(tmp_path):
    """The refusal is scoped to non-AsciiDoc input; a real .adoc file is still checked."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Title\n\nNo links here.\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['status'] == 'success'
    assert result['data']['files_processed'] == 1
    assert result['data']['total_links'] == 0


def test_verify_links_rejects_both_file_and_directory():
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'

    result = cmd_verify_links(
        _ns(
            _VERIFY_LINKS_NS,
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
        result = cmd_classify_links(_ns(_CLASSIFY_NS, input=str(input_file), output=str(output_file), pretty=True))

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

        result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=None, directory=str(d), recursive=False, report=None))

        assert result['data']['files_processed'] == 2


def test_cmd_verify_links_empty_directory_reports_no_files():
    """A directory with no .adoc files yields a structured no_files error."""
    with tempfile.TemporaryDirectory() as tmp:
        result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=None, directory=tmp, recursive=False, report=None))

        assert result['status'] == 'error'
        assert result['error'] == 'no_files'


def test_cmd_verify_links_writes_report_file_when_requested():
    """``--report`` persists the full result as JSON to the given path."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_adoc(d, 'a.adoc', '= Doc\n\n[[ok]]\n<<ok>>\n')
        report = d / 'report.json'

        result = cmd_verify_links(
            _ns(_VERIFY_LINKS_NS, file=str(d / 'a.adoc'), directory=None, recursive=False, report=str(report))
        )

        assert report.exists()
        persisted = json.loads(report.read_text())
        assert persisted['status'] == result['status']
        assert 'data' in persisted


# Tier 2: ADR template / validator convergence round-trip


def _render_adr_template() -> str:
    """Render adr-template.adoc with sample values for every placeholder."""
    template_path = (
        Path(__file__).parents[3]
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'manage-adr'
        / 'templates'
        / 'adr-template.adoc'
    )
    content = template_path.read_text(encoding='utf-8')
    replacements = {
        '{{NUMBER}}': '0001',
        '{{TITLE}}': 'Round Trip',
        '{{STATUS}}': 'Proposed',
        '{{SUMMARY}}': 'Convergence proof',
        '{{TAGS}}': '',
        '{{AFFECTS}}': '',
        '{{SUPERSEDES}}': '',
        '{{CONTEXT}}': 'Context body.',
        '{{DECISION}}': 'Decision body.',
        '{{POSITIVE_CONSEQUENCES}}': 'Positive body.',
        '{{NEGATIVE_CONSEQUENCES}}': 'Negative body.',
        '{{RISKS}}': 'Risk body.',
        '{{ALTERNATIVES}}': 'Alternatives body.',
        '{{REFERENCES}}': 'References body.',
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)
    return content


def test_adr_template_renders_and_validates_clean():
    """A freshly generated ADR validates clean against the converged header set."""
    content = _render_adr_template()
    assert '{{' not in content, 'Unreplaced template placeholder'

    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_file = Path(f.name)

    try:
        result = _validate_mod.check_file_compliance(temp_file)

        assert result['compliant'], f'Fresh template failed validation: {result["issues"]}'
        assert result['missing_attrs'] == []
    finally:
        temp_file.unlink(missing_ok=True)


# Tier 2: verify-links ``link:`` macro grammar (PLAN-LB-113 D6)


def _link_macro_result(name: str):
    """Run ``verify-links`` on one ``link-verify`` fixture by name."""
    return cmd_verify_links(
        _ns(_VERIFY_LINKS_NS, file=str(LINK_VERIFY_FIXTURES / name), directory=None, recursive=False, report=None)
    )


def test_verify_links_relative_link_macro_to_an_existing_file_is_checked():
    result = _link_macro_result('link-macro-relative.adoc')

    data = result['data']
    assert data['total_links'] == 1
    assert data['broken_links'] == 0
    assert data['unchecked_link_classes'] == [], 'a relative target is verified, so no class stays unchecked'


def test_verify_links_relative_link_macro_to_a_missing_file_is_broken():
    result = _link_macro_result('link-macro-missing.adoc')

    data = result['data']
    assert data['broken_links'] == 1
    assert data['issues'][0]['type'] == 'broken'
    assert 'missing-target.adoc' in data['issues'][0]['description']


def test_verify_links_external_link_macro_is_reported_as_an_unchecked_class():
    result = _link_macro_result('link-macro-external.adoc')

    data = result['data']
    assert data['broken_links'] == 0, 'an external target is not fetched, so it is not broken either'
    assert data['unchecked_link_classes'] == [
        {
            'class': 'external-url',
            'count': 1,
            'first': {
                'file': str(LINK_VERIFY_FIXTURES / 'link-macro-external.adoc'),
                'line': 3,
                'link': 'link:https://example.com[Example]',
            },
        }
    ]


def test_verify_links_a_file_without_link_macros_reports_an_empty_unchecked_list():
    result = _link_macro_result('link-macro-none.adoc')

    data = result['data']
    assert data['total_links'] == 0
    assert data['unchecked_link_classes'] == []


def test_anchor_derivation_still_strips_a_link_macro_from_a_section_title(tmp_path):
    adoc = tmp_path / 'anchor.adoc'
    adoc.write_text('= Doc\n\n== See link:https://example.com[Example] Now\n\n<<see-now>>\n', encoding='utf-8')

    anchors = extract_anchors_from_file(str(adoc))

    assert 'see-now' in anchors, 'the link: macro in a title must still be stripped before slugging'


def test_verify_links_link_macro_needs_a_word_boundary_and_no_whitespace(tmp_path):
    """``backlink:`` and a target with a space are prose, not macros."""
    adoc = tmp_path / 'grammar.adoc'
    adoc.write_text(
        '= Doc\n\nA backlink:target-file.adoc[Back] is not a link: macro.\n\n'
        'Prose link: two words[Label] is not a macro either.\n\n'
        'A target may not hold a space: link:two words[Label] is not a macro.\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0
    assert result['data']['broken_links'] == 0


def test_verify_links_ignores_link_macros_inside_a_delimited_block(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\n----\nlink:missing.adoc[Example]\n----\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0, 'a listing block sample is not a live link'
    assert result['data']['broken_links'] == 0


def test_verify_links_internal_anchor_link_macro_resolves(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\n[[present]]\n\nSee link:#present[Present].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the macro must be extracted, or a zero-broken result is vacuous'
    assert result['data']['broken_links'] == 0
    assert result['data']['unchecked_link_classes'] == []


def test_verify_links_internal_anchor_link_macro_to_a_missing_anchor_is_broken(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:#ghost[Ghost].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 1
    assert 'ghost' in result['data']['issues'][0]['description']


def test_verify_links_non_asciidoc_fragment_is_an_unchecked_class(tmp_path):
    (tmp_path / 'manual.pdf').write_bytes(b'%PDF-1.4\n')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:manual.pdf#page=3[Manual].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'the file exists; only its anchor is unreadable'
    assert result['data']['unchecked_link_classes'] == [
        {
            'class': 'fragment',
            'count': 1,
            'first': {'file': str(adoc), 'line': 3, 'link': 'link:manual.pdf#page=3[Manual]'},
        }
    ]


def test_verify_links_relative_link_macro_to_a_missing_anchor_is_broken(tmp_path):
    (tmp_path / 'target.adoc').write_text('= Target\n\n[[present]]\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:target.adoc#ghost[Ghost].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the macro must be extracted, or a broken count is vacuous'
    assert result['data']['broken_links'] == 1
    assert 'ghost' in result['data']['issues'][0]['description']


def test_verify_links_ignores_inline_comment_and_escaped_macros(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\n'
        'An inline example: `link:missing-inline.adoc[x]`.\n\n'
        '// link:missing-comment.adoc[x]\n\n'
        'An escaped macro: \\link:missing-escaped.adoc[x].\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0
    assert result['data']['broken_links'] == 0


def test_verify_links_mixed_delimiters_do_not_hide_a_live_link(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\n----\nlink:missing-in-block.adoc[x]\n....\nlink:still-in-block.adoc[x]\n----\n\n'
        'link:missing-live.adoc[Live]\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'only the live link after the block is extracted'
    assert result['data']['broken_links'] == 1


def test_verify_links_relative_target_with_query_and_percent_encoding_is_found(tmp_path):
    (tmp_path / 'my doc.adoc').write_text('= Doc\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:my%20doc.adoc?mode=view[Doc].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the macro must be extracted, or zero-broken is vacuous'
    assert result['data']['broken_links'] == 0


def test_verify_links_asciidoctor_default_auto_id_resolves(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\n== Real Heading\n\nSee link:#_real_heading[Heading].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the macro must be extracted, or zero-broken is vacuous'
    assert result['data']['broken_links'] == 0


def test_verify_links_relative_link_in_a_title_uses_its_label(tmp_path):
    (tmp_path / 'other.adoc').write_text('= Other\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\n== See link:other.adoc[Other] Now\n\n<<see-other-now>>\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 2, 'the title macro and the cross-reference must both be extracted'
    assert result['data']['broken_links'] == 0


def test_verify_links_ignores_anchors_defined_in_comments_and_inline_code(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\n// [[ghost]]\n\nAn example: `[[inline-ghost]]`.\n\n'
        'See link:#ghost[Ghost] and link:#inline-ghost[Inline].\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 2, 'neither anchor is rendered, so both links are broken'


def test_verify_links_ignores_passthrough_examples(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\nAn example: +link:missing.adoc[x]+.\n\n++++\nlink:missing2.adoc[x]\n++++\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0
    assert result['data']['broken_links'] == 0


def test_verify_links_valid_metric_excludes_unchecked_classes(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nlink:https://example.com[Example]\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['unchecked_link_classes'][0]['count'] == 1
    assert result['metrics']['valid_links'] == 0, 'an unchecked link is not a verified link'


def test_verify_links_reports_a_broken_anchor_behind_a_monospace_label(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee <<missing,`Code`>> here.\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the monospace label must not delete the cross-reference'
    assert result['data']['broken_links'] == 1
    assert result['data']['issues'][0]['link'] == '<<missing,`Code`>>', 'the report must quote the source text'


def test_verify_links_attribute_bearing_target_is_an_unchecked_class(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:{docs-base}/guide.adoc[Guide].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'the attribute is not substituted, so the target is not broken'
    assert result['data']['unchecked_link_classes'] == [
        {
            'class': 'attribute-reference',
            'count': 1,
            'first': {'file': str(adoc), 'line': 3, 'link': 'link:{docs-base}/guide.adoc[Guide]'},
        }
    ]


def test_verify_links_missing_non_asciidoc_fragment_is_not_double_counted(tmp_path):
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:missing.pdf#page=3[Manual].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 1
    assert result['data']['unchecked_link_classes'] == [], 'a missing file is broken, not unchecked'
    assert result['metrics']['valid_links'] == 0


# =============================================================================
# Coverage edges: every `link:` form is either verified or named in
# `unchecked_link_classes`, and a bad target cannot abort the run
# =============================================================================


def test_verify_links_absolute_target_is_named_and_not_broken(tmp_path):
    """A leading `/` or `\\` is not relative, so joining it discards the file's directory."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:/etc/hostname[Host] and link:\\server\\share.adoc[Share].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'an absolute target is not relative to the file, so it is not broken'
    classes = {row['class']: row['count'] for row in result['data']['unchecked_link_classes']}
    assert classes == {'absolute-path': 2}, f'the absolute targets must be named under their own class: {classes}'


def test_verify_links_attribute_reference_after_a_hash_is_classed(tmp_path):
    """`link:#{section-id}[x]` is an attribute reference, not the literal anchor `{section-id}`."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:#{section-id}[Ref].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'the target carries an unresolved attribute, so it is not broken'
    assert [row['class'] for row in result['data']['unchecked_link_classes']] == ['attribute-reference']


def test_verify_links_masked_examples_are_named_by_their_mask_class(tmp_path):
    """A skipped example is still counted, so the field says what the checker did not examine."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\n'
        'A code span: `link:one.adoc[x]`.\n\n'
        'A passthrough: +link:two.adoc[x]+.\n\n'
        'A strong passthrough: ++link:three.adoc[x]++.\n\n'
        'A macro passthrough: pass:[link:four.adoc[x]].\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0, 'a masked example is not a live link'
    assert result['data']['broken_links'] == 0, 'a documented example must not become a false broken link'
    classes = {row['class']: row['count'] for row in result['data']['unchecked_link_classes']}
    assert classes == {
        'code-span': 1,
        'inline-passthrough': 1,
        'passthrough': 1,
        'pass-macro': 1,
    }, f'each mask must be named by its own class: {classes}'


def test_verify_links_percent_encoded_anchor_resolves(tmp_path):
    """An anchor is percent-decoded before the lookup, exactly as the path already is.

    The anchor is an explicit ID Asciidoctor registers (``my-anchor``), not a
    spaced one it would rewrite, so the decode is what the assertion turns on.
    """
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\n[[my-anchor]]\n\nSee link:#my%2Danchor[Anchor].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the macro must be extracted, or zero-broken is vacuous'
    assert result['data']['broken_links'] == 0, 'the encoded anchor names an anchor that exists'


def test_verify_links_nul_in_a_target_is_an_issue_not_an_abort(tmp_path):
    """A NUL byte makes Path.resolve() raise; the run must report it, not die on it."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:bad%00name.adoc[x].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['status'] == 'failure'
    assert result['data']['files_processed'] == 1
    assert result['data']['issues'], 'the unresolvable target must be reported on its link'
    assert result['data']['issues'][0]['type'] == 'unreadable', (
        'an unresolvable target was never examined, so it is not `broken`'
    )


def test_verify_links_nested_longer_delimiter_hides_its_inner_content():
    """A `----` line inside a `-----` listing is content, so the block closes only on `-----`."""
    adoc = LINK_VERIFY_FIXTURES / 'edge-cases' / 'nested-block.adoc'

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'only the live link after the block is extracted'
    assert result['data']['broken_links'] == 0, 'the nested inner link must not surface as broken'


def test_verify_links_edge_case_fixture_directory_verifies_every_live_link():
    """The fixture directory as a whole is clean, so its files are all load-bearing."""
    fixture_dir = LINK_VERIFY_FIXTURES / 'edge-cases'

    result = cmd_verify_links(
        _ns(_VERIFY_LINKS_NS, file=None, directory=str(fixture_dir), recursive=False, report=None)
    )

    assert result['status'] == 'success', f'the edge-case fixtures must be clean: {result["data"]["issues"]}'
    assert result['data']['files_processed'] == 3
    assert result['data']['total_links'] == 2, 'the nested block hides its inner link; the other two are live'


def test_verify_links_a_masked_anchor_is_not_a_real_anchor(tmp_path):
    """An anchor defined only inside a mask is not rendered, so a link to it is broken."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\nA ++[[ghost]]++ example.\n\nSee link:#ghost[Ghost].\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 1, 'the masked anchor is never rendered, so the link is broken'


def test_verify_links_a_pass_macro_hides_every_link_it_carries(tmp_path):
    """A pass macro with a nested label hides both of its links, so neither is a false broken."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\nA pass:[link:a-missing.adoc[x] link:b-missing.adoc[y]] example.\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'a documented example must not become a false broken link'
    assert [row['class'] for row in result['data']['unchecked_link_classes']] == ['pass-macro']
    assert result['data']['unchecked_link_classes'][0]['count'] == 2, (
        'the nesting-aware mask must cover both links, not stop at the first `]`'
    )


def test_verify_links_a_prose_cxx_does_not_swallow_a_later_passthrough(tmp_path):
    """A `C++` in prose is not a passthrough opener, so the real passthrough is still masked."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\nC++ is not AsciiDoc; a passthrough ++link:missing.adoc[x]++ follows.\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0, 'the passthrough example is not a live link'
    assert result['data']['broken_links'] == 0, 'the example must not become a false broken link'
    assert [row['class'] for row in result['data']['unchecked_link_classes']] == ['passthrough']


def test_verify_links_a_target_too_long_to_stat_is_an_issue_not_an_abort(tmp_path):
    """A path the filesystem refuses to stat is reported, never raised out of the run."""
    adoc = tmp_path / 'page.adoc'
    long_name = 'a' * 300 + '.adoc'
    adoc.write_text(f'= Page\n\nSee link:{long_name}[Long].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['files_processed'] == 1, 'the run completes over the file it could read'
    assert result['data']['issues'], 'the target that cannot be stat-ed must be reported on its link'
    assert result['data']['issues'][0]['type'] == 'unreadable', (
        'a filesystem failure is not a missing file, so it is not `broken`'
    )


def test_verify_links_unreadable_adoc_target_completes_the_run(tmp_path):
    """A target that cannot be read for anchors is an issue on its link, and the run completes."""
    (tmp_path / 'broken.adoc').mkdir()
    (tmp_path / 'good.adoc').write_text('= Good\n\n== Present\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\nSee link:broken.adoc#section[Broken] and link:good.adoc#present[Good].\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=None, directory=str(tmp_path), recursive=False, report=None))

    assert result['status'] == 'failure', 'the unreadable target is an issue'
    assert result['data']['files_processed'] == 3, 'the run must complete across every discovered file'
    assert result['data']['total_links'] == 2, 'both live links are extracted'
    assert result['data']['broken_links'] == 0, 'an unreadable target is reported with its reason, not as broken'
    assert result['metrics']['valid_links'] == 1, (
        'the one live link the checker verified is the only valid link — the file-level issue and the '
        'unreadable link must not both be subtracted'
    )
    unreadable = [issue for issue in result['data']['issues'] if issue['file'].endswith('page.adoc')]
    assert unreadable, 'the link whose target cannot be read must carry an issue of its own'
    assert 'could not be read' in unreadable[0]['description']
    assert not [issue for issue in result['data']['issues'] if issue['file'].endswith('good.adoc')], (
        'the readable file still yields its own clean result'
    )


# =============================================================================
# D2 — a mask never hides a reference without counting it
# =============================================================================


def _masked_reference_classes() -> dict[str, int]:
    """The unchecked-class counts of the masked-reference fixture, by class."""
    data = _link_macro_result('masked-reference-forms.adoc')['data']
    return {row['class']: row['count'] for row in data['unchecked_link_classes']}


def test_verify_links_counts_every_reference_form_a_mask_hides():
    """Each masked form is named under its mask class, and none becomes a false broken link.

    The fixture carries a passthrough-wrapped target, a target with an inline
    passthrough, a passthrough xref, a pass-macro cross-reference, a code-span
    xref and a double-backtick example. Before the mask counted them, the two
    spanning macros were in no count at all and the xref forms were dropped.
    """
    data = _link_macro_result('masked-reference-forms.adoc')['data']

    assert data['total_links'] == 0, 'every form in the fixture is masked, so none is a live link'
    assert data['broken_links'] == 0, 'a documented example must never become a false broken link'
    assert _masked_reference_classes() == {
        'passthrough': 2,
        'inline-passthrough': 1,
        'pass-macro': 1,
        'code-span': 2,
    }, f'every masked reference must be named under its own class: {_masked_reference_classes()}'


def test_verify_links_names_a_macro_whose_target_a_passthrough_wraps():
    """`link:++url++[x]` is counted under `passthrough`, not erased with its target."""
    rows = _link_macro_result('masked-reference-forms.adoc')['data']['unchecked_link_classes']
    row = next(row for row in rows if row['class'] == 'passthrough')

    assert row['count'] == 2, 'the passthrough-wrapped target and the passthrough xref are both counted'
    assert row['first']['link'] == 'link:++https://example.org/a_b++[Wrapped]', (
        'the first passthrough occurrence must quote the whole macro, prefix and label included'
    )


# =============================================================================
# D4 — the checker's remaining edges
# =============================================================================


def test_verify_links_absolute_xref_target_is_named_and_not_broken(tmp_path):
    """An absolute xref target is not joined onto the file's directory and never opened."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee xref:/etc/hostname[Host].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, (
        'a target outside the file directory is not relative, so it is not broken'
    )
    classes = {row['class']: row['count'] for row in result['data']['unchecked_link_classes']}
    assert classes == {'absolute-path': 1}, f'the absolute xref must be named under its class: {classes}'


def test_verify_links_xref_target_is_percent_decoded(tmp_path):
    """An xref target is decoded exactly as its anchor is."""
    (tmp_path / 'my doc.adoc').write_text('= Doc\n\nbody\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee xref:my%20doc.adoc[Doc].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 1, 'the xref must be extracted, or zero-broken is vacuous'
    assert result['data']['broken_links'] == 0, 'the encoded path names the file it resolves to'


def test_verify_links_xref_anchor_is_percent_decoded(tmp_path):
    """An xref anchor is decoded before the lookup."""
    (tmp_path / 'target.adoc').write_text('= Target\n\n[[my-anchor]]\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee xref:target.adoc#my%2Danchor[Anchor].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'the decoded anchor names one the target defines'


def test_verify_links_cross_file_fragment_is_percent_decoded(tmp_path):
    """A `link:` macro's fragment is decoded before the cross-file anchor lookup."""
    (tmp_path / 'target.adoc').write_text('= Target\n\n[[my-anchor]]\n', encoding='utf-8')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:target.adoc#my%2Danchor[Anchor].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['broken_links'] == 0, 'the decoded fragment names an anchor the target defines'


def test_verify_links_self_referencing_symlink_does_not_abort_the_run(tmp_path):
    """A symlink loop is reported on its link, never raised out of a multi-file run."""
    (tmp_path / 'real.adoc').write_text('= Real\n\nbody\n', encoding='utf-8')
    loop = tmp_path / 'loop.adoc'
    loop.symlink_to(loop.name)
    (tmp_path / 'page.adoc').write_text(
        '= Page\n\nSee link:loop.adoc[Loop] and link:real.adoc[Real].\n', encoding='utf-8'
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=None, directory=str(tmp_path), recursive=False, report=None))

    assert result['data']['files_processed'] == 3, 'the run completes over every discovered file'
    assert result['data']['total_links'] == 2, 'the self-referencing link and the real link are both extracted'
    assert any('loop.adoc' in issue['description'] for issue in result['data']['issues']), (
        'the loop must be named on its own link rather than aborting the run'
    )


def test_verify_links_double_backtick_span_pairs_as_one_span(tmp_path):
    """A double-backtick example is masked whole; it does not stay live as two empty spans."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nAn example: ``link:missing.adoc[x]``.\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0, 'the double-backtick example is not a live link'
    assert result['data']['broken_links'] == 0, 'a documented example must not become a false broken link'
    assert _ns_classes(result) == {'code-span': 1}, 'the example is counted once under its mask class'


def _ns_classes(result: dict) -> dict[str, int]:
    return {row['class']: row['count'] for row in result['data']['unchecked_link_classes']}


def test_verify_links_an_unreadable_only_run_names_the_count(tmp_path):
    """`broken_links: 0` beside `status: failure` also names the unreadable targets behind it."""
    (tmp_path / 'broken.adoc').mkdir()
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:broken.adoc#section[Broken].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['status'] == 'failure'
    assert result['data']['broken_links'] == 0
    assert result['data']['unreadable_targets'] == 1, (
        'the failure must be explained by an unreadable count, not only by a zero broken count'
    )


def test_verify_links_a_non_utf8_target_is_reported_not_raised(tmp_path):
    """A target that cannot be decoded is an issue on its link, and the run completes."""
    (tmp_path / 'target.adoc').write_bytes(b'= Target\n\n\xff\xfe\x00\n')
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:target.adoc#section[Target].\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['status'] == 'failure'
    assert result['data']['files_processed'] == 1
    assert result['data']['broken_links'] == 0, 'a decode failure is not a missing file'
    assert result['data']['unreadable_targets'] >= 1


@pytest.mark.skipif(os.geteuid() == 0, reason='a permission bit does not deny root, so the case cannot be produced')
def test_verify_links_a_permission_denied_target_is_reported_not_raised(tmp_path):
    """A target that cannot be opened for a permission reason is an issue, and the run completes."""
    target = tmp_path / 'target.adoc'
    target.write_text('= Target\n\n[[section]]\n', encoding='utf-8')
    target.chmod(0o000)
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\nSee link:target.adoc#section[Target].\n', encoding='utf-8')

    try:
        result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))
    finally:
        target.chmod(0o644)

    assert result['status'] == 'failure'
    assert result['data']['broken_links'] == 0, 'an unreadable target is not a missing one'


def test_verify_links_an_unterminated_block_is_named(tmp_path):
    """A delimited block left open at EOF is reported, never silently skipped."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text(
        '= Page\n\n----\nlink:hidden.adoc[Hidden]\n\nlink:also-hidden.adoc[Hidden]\n',
        encoding='utf-8',
    )

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['status'] == 'failure', 'an unterminated block leaves the rest of the file unchecked'
    assert result['data']['broken_links'] == 0, 'the links inside the open block were not examined'
    unterminated = [issue for issue in result['data']['issues'] if 'never closed' in issue['description']]
    assert unterminated, 'the open block must be named with the line that opened it'
    assert unterminated[0]['line'] == 3


def test_verify_links_a_mismatched_length_close_leaves_the_block_open_and_named(tmp_path):
    """A `----` inside a `-----` block is content, so the block stays open to EOF and is named."""
    adoc = tmp_path / 'page.adoc'
    adoc.write_text('= Page\n\n-----\n----\nlink:hidden.adoc[Hidden]\n', encoding='utf-8')

    result = cmd_verify_links(_ns(_VERIFY_LINKS_NS, file=str(adoc), directory=None, recursive=False, report=None))

    assert result['data']['total_links'] == 0, 'a mismatched-length delimiter is content, not a close'
    assert any('never closed' in issue['description'] for issue in result['data']['issues'])
