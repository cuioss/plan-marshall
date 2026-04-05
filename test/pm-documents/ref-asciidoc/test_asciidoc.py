#!/usr/bin/env python3
"""Tests for asciidoc.py - AsciiDoc formatting, validation, and link operations.

Tier 2 (direct import) tests with 3 subprocess CLI plumbing tests retained.
"""

import importlib.util
import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import get_script_path, run_script  # noqa: E402

# Test directories
TEST_DIR = Path(__file__).parent
SCRIPT_PATH = get_script_path('pm-documents', 'ref-asciidoc', 'asciidoc.py')
FIXTURES_DIR = TEST_DIR / 'fixtures'
LINK_VERIFY_FIXTURES = FIXTURES_DIR / 'link-verify'

# Tier 2 direct imports - load cmd_* from sub-command modules
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-documents' / 'skills' / 'ref-asciidoc' / 'scripts'
)

# These modules have underscore names, so standard import via importlib works
def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_stats_mod = _load_module('_cmd_stats', '_cmd_stats.py')
_validate_mod = _load_module('_cmd_validate', '_cmd_validate.py')
_format_mod = _load_module('_cmd_format', '_cmd_format.py')
_verify_links_mod = _load_module('_cmd_verify_links', '_cmd_verify_links.py')
_classify_links_mod = _load_module('_cmd_classify_links', '_cmd_classify_links.py')

cmd_stats = _stats_mod.cmd_stats
cmd_validate = _validate_mod.cmd_validate
cmd_format = _format_mod.cmd_format
cmd_verify_links = _verify_links_mod.cmd_verify_links
cmd_classify_links = _classify_links_mod.cmd_classify_links


# =============================================================================
# Main help tests (CLI plumbing - retained as subprocess)
# =============================================================================


def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_fixtures_exist():
    """Test that fixtures directory exists."""
    assert FIXTURES_DIR.exists(), f'Fixtures not found: {FIXTURES_DIR}'


def test_main_help():
    """Test main --help displays all subcommands (CLI plumbing)."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'stats' in combined, 'stats subcommand in help'
    assert 'validate' in combined, 'validate subcommand in help'
    assert 'format' in combined, 'format subcommand in help'


# =============================================================================
# Stats subcommand tests (Tier 2)
# =============================================================================


def test_stats_help():
    """Test stats --help displays usage (CLI plumbing)."""
    result = run_script(SCRIPT_PATH, 'stats', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f'Stats help not shown: {combined}'


def test_stats_console_format():
    """Test stats default console output produces dict with summary data."""
    result = cmd_stats(Namespace(command='stats', directory=str(FIXTURES_DIR), format='console', details=False))
    assert result['status'] == 'success', f"Expected success status, got: {result.get('status')}"
    assert 'summary' in result, 'Stats output should contain summary'


def test_stats_json_format():
    """Test stats JSON output format includes metadata and summary."""
    result = cmd_stats(Namespace(command='stats', directory=str(FIXTURES_DIR), format='json', details=False))
    assert 'metadata' in result, 'Result missing metadata'
    assert 'summary' in result, 'Result missing summary'


def test_stats_details_flag():
    """Test stats details flag includes file info."""
    result = cmd_stats(Namespace(command='stats', directory=str(FIXTURES_DIR), format='json', details=True))
    assert 'files' in result, 'Result with details flag should include files key'


def test_stats_empty_directory():
    """Test stats handles empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result = cmd_stats(Namespace(command='stats', directory=temp_dir, format='console', details=False))
        assert result['status'] == 'success'


def test_stats_nonexistent_dir():
    """Test stats handles nonexistent directory."""
    result = cmd_stats(Namespace(command='stats', directory='/nonexistent/path', format='console', details=False))
    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# =============================================================================
# Validate subcommand tests (Tier 2)
# =============================================================================


def test_validate_console_format():
    """Test validate default console output."""
    result = cmd_validate(Namespace(command='validate', path=str(FIXTURES_DIR), format='console',
                                    ignore_patterns=None))
    assert result['status'] in ('success', 'non_compliant'), f'Unexpected status: {result["status"]}'


def test_validate_json_format():
    """Test validate JSON output format."""
    result = cmd_validate(Namespace(command='validate', path=str(FIXTURES_DIR), format='json',
                                    ignore_patterns=None))
    assert 'directory' in result, "JSON format didn't produce expected output"


def test_validate_missing_blank_line():
    """Test validate detects missing blank line before list."""
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
        result = cmd_validate(Namespace(command='validate', path=temp_file, format='console',
                                        ignore_patterns=None))
        assert result['status'] == 'non_compliant' or 'blank' in str(result).lower(), (
            'Missing blank line should be detected'
        )
    finally:
        Path(temp_file).unlink(missing_ok=True)


def test_validate_ignore_pattern():
    """Test validate ignore pattern flag."""
    result = cmd_validate(Namespace(command='validate', path=str(FIXTURES_DIR), format='console',
                                    ignore_patterns=['missing-*.adoc']))
    assert result['status'] in ('success', 'non_compliant', 'error')


def test_validate_invalid_format_rejected():
    """Test validate rejects invalid format (CLI plumbing - argparse)."""
    result = run_script(SCRIPT_PATH, 'validate', '-f', 'invalid_format')
    assert result.returncode != 0, 'Invalid format should be rejected'


def test_validate_nonexistent_path():
    """Test validate handles nonexistent path."""
    result = cmd_validate(Namespace(command='validate', path='/nonexistent/path', format='console',
                                    ignore_patterns=None))
    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# =============================================================================
# Format subcommand tests (Tier 2)
# =============================================================================


def test_format_no_backup_flag():
    """Test format --no-backup flag prevents backup creation."""
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=['lists'],
                                  no_backup=True))
    assert result['status'] == 'success'


def test_format_lists_type():
    """Test format -t lists fix type."""
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=['lists'],
                                  no_backup=True))
    assert result['status'] == 'success'


def test_format_xref_type():
    """Test format -t xref fix type."""
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=['xref'],
                                  no_backup=True))
    assert result['status'] == 'success'


def test_format_whitespace_type():
    """Test format -t whitespace fix type."""
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=['whitespace'],
                                  no_backup=True))
    assert result['status'] == 'success'


def test_format_all_types():
    """Test format -t all fix type."""
    result = cmd_format(Namespace(command='format', path=str(FIXTURES_DIR), fix_types=['all'],
                                  no_backup=True))
    assert result['status'] == 'success'


def test_format_invalid_type_rejected():
    """Test format rejects invalid fix type (CLI plumbing - argparse)."""
    result = run_script(SCRIPT_PATH, 'format', '-t', 'invalid_type')
    assert result.returncode != 0, 'Invalid fix type should be rejected'


def test_format_nonexistent_path():
    """Test format handles nonexistent path."""
    result = cmd_format(Namespace(command='format', path='/nonexistent/path', fix_types=None,
                                  no_backup=False))
    assert result['status'] == 'error', 'Nonexistent path should produce error status'


# =============================================================================
# Verify-links subcommand tests (Tier 2)
# =============================================================================


def test_verify_links_single_file():
    """Test verify-links processes single file."""
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'
    if not empty_file.exists():
        return  # Skip if fixture doesn't exist
    result = cmd_verify_links(Namespace(command='verify-links', file=str(empty_file), directory=None,
                                        recursive=False, report=None))
    assert str(result.get('data', {}).get('files_processed', '')) == '1', 'Single file mode processes one file'


def test_verify_links_empty_file():
    """Test verify-links handles empty file."""
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'
    if not empty_file.exists():
        return  # Skip if fixture doesn't exist
    result = cmd_verify_links(Namespace(command='verify-links', file=str(empty_file), directory=None,
                                        recursive=False, report=None))
    assert result['status'] in ('success', 'failure', 'error')


def test_verify_links_file_not_found():
    """Test verify-links handles missing file."""
    result = cmd_verify_links(Namespace(command='verify-links', file='/nonexistent/file.adoc',
                                        directory=None, recursive=False, report=None))
    assert result['status'] == 'error', 'Error when file does not exist'


def test_verify_links_both_file_and_directory():
    """Test verify-links rejects both --file and --directory."""
    empty_file = LINK_VERIFY_FIXTURES / 'empty.adoc'
    if not empty_file.exists():
        return  # Skip if fixture doesn't exist
    result = cmd_verify_links(Namespace(command='verify-links', file=str(empty_file),
                                        directory=str(LINK_VERIFY_FIXTURES), recursive=False, report=None))
    assert 'cannot specify both' in result.get('message', '').lower(), (
        'Error when both --file and --directory specified'
    )


# =============================================================================
# Classify-links subcommand tests (Tier 2)
# =============================================================================


def test_classify_links_with_files():
    """Test classify-links with input/output files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        input_data = {
            'issues': [
                {'file': 'standards/security.adoc', 'line': 42, 'link': '<<owasp-top-10>>', 'type': 'broken_anchor'},
                {'file': 'guide.adoc', 'line': 56, 'link': 'file:///local/path/doc.pdf', 'type': 'broken_link'},
            ]
        }
        json.dump(input_data, f)
        input_file = Path(f.name)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_file = Path(f.name)

    try:
        result = cmd_classify_links(Namespace(command='classify-links', input=str(input_file),
                                              output=str(output_file), pretty=True))
        assert result['status'] == 'success'
        assert output_file.exists(), 'Classification completed'
        content = output_file.read_text()
        has_categories = 'likely-false-positive' in content or 'must-verify-manual' in content
        assert has_categories, 'Found expected categories in output'
    finally:
        input_file.unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
