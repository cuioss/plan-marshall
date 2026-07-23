#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for jsdoc.py - JSDoc documentation analysis tool.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.

The analysis surface (``analyze_jsdoc``) is exercised in-process against the
committed ``jsdoc/*.js`` fixtures — no per-test interpreter cold-start. Only
``test_main_help`` / ``test_analyze_help`` remain subprocess smokes to cover
the argparse CLI plumbing (mirrors the pm-documents ref-documentation /
ref-asciidoc in-process pattern).
"""

import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-dev-frontend', 'javascript', 'jsdoc.py')
FIXTURES_DIR = Path(__file__).parent / 'jsdoc'

# Load the analysis surface in-process. ``analyze_jsdoc`` returns the same dict
# the CLI serializes to TOON, so the tests assert directly against it.
_jsdoc = load_script_module('pm-dev-frontend', 'javascript', 'jsdoc.py', 'jsdoc')
analyze_jsdoc = _jsdoc.analyze_jsdoc
cmd_analyze = _jsdoc.cmd_analyze


# =============================================================================
# Main help tests (CLI plumbing - retained as subprocess)
# =============================================================================


def test_script_exists():
    """Test that the script exists."""
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help():
    """Test main --help displays all subcommands (CLI plumbing)."""
    result = run_script(SCRIPT_PATH, '--help')
    combined = result.stdout + result.stderr
    assert 'analyze' in combined, 'analyze subcommand in help'


def test_analyze_help():
    """Test analyze --help displays usage (CLI plumbing)."""
    result = run_script(SCRIPT_PATH, 'analyze', '--help')
    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), 'Analyze help not shown'


# =============================================================================
# Analyze surface tests (Tier 2 — direct import)
# =============================================================================


def test_analyze_valid_jsdoc_no_critical():
    """Test that fully documented file has no CRITICAL violations."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'valid-jsdoc.js'), is_directory=False, scope='all')
    assert int(data['metrics']['critical']) == 0, 'Fully documented file should have no critical violations'
    # Note: may have warnings due to optional param syntax [param] not matched by regex
    assert int(data['metrics']['total_violations']) <= 1, 'At most minor violations expected'


def test_analyze_missing_jsdoc_detects_violations():
    """Test that file with missing JSDoc reports specific violation types."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'missing-jsdoc.js'), is_directory=False, scope='all')
    assert data['status'] == 'violations_found', 'Should find violations'
    violations = data.get('data', {}).get('violations', [])
    violation_types = {v['type'] for v in violations}
    assert 'missing_jsdoc' in violation_types, 'Should detect missing JSDoc on functions'
    assert 'missing_class_doc' in violation_types, 'Should detect missing class documentation'


def test_analyze_missing_jsdoc_has_critical_for_exports():
    """Test that exported functions without JSDoc are CRITICAL."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'missing-jsdoc.js'), is_directory=False, scope='all')
    violations = data.get('data', {}).get('violations', [])
    critical_violations = [v for v in violations if v.get('severity') == 'CRITICAL']
    assert len(critical_violations) > 0, 'Exported items without JSDoc should be CRITICAL'


def test_analyze_partial_jsdoc_detects_missing_tags():
    """Test that partially documented file detects missing tags."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'partial-jsdoc.js'), is_directory=False, scope='all')
    assert data['status'] == 'violations_found', 'Partial JSDoc should have violations'
    violations = data.get('data', {}).get('violations', [])
    violation_types = {v['type'] for v in violations}
    assert (
        'missing_param_type' in violation_types
        or 'missing_returns' in violation_types
        or 'missing_jsdoc' in violation_types
    ), 'Should detect at least one type of incomplete documentation'


def test_analyze_web_component():
    """Test analyzing web component file."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'web-component.js'), is_directory=False, scope='all')
    assert data['status'] in ['clean', 'violations_found'], 'Analyzed web component'
    assert int(data['metrics']['total_files']) == 1, 'Should analyze one file'


def test_analyze_directory_scans_all_js_files():
    """Test analyzing directory finds all JavaScript fixture files."""
    data = analyze_jsdoc(str(FIXTURES_DIR), is_directory=True, scope='all')
    metrics = data.get('metrics', {})
    assert int(metrics.get('total_files', 0)) >= 4, 'Should find at least 4 fixture files'
    assert int(metrics.get('files_with_violations', 0)) >= 1, 'At least one file should have violations'


def test_analyze_scope_missing_excludes_syntax():
    """Test that 'missing' scope only detects missing JSDoc, not syntax issues."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'partial-jsdoc.js'), is_directory=False, scope='missing')
    violations = data.get('data', {}).get('violations', [])
    for v in violations:
        assert v['type'] in ('missing_jsdoc', 'missing_class_doc', 'missing_constructor_doc'), (
            f"'missing' scope should not report syntax violations, got: {v['type']}"
        )


def test_analyze_scope_syntax_excludes_missing():
    """Test that 'syntax' scope checks documentation quality, not presence."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'partial-jsdoc.js'), is_directory=False, scope='syntax')
    violations = data.get('data', {}).get('violations', [])
    for v in violations:
        assert v['type'] not in ('missing_jsdoc', 'missing_class_doc', 'missing_constructor_doc'), (
            f"'syntax' scope should not report missing JSDoc, got: {v['type']}"
        )


def test_analyze_missing_file_error():
    """Test error handling for missing file."""
    data = analyze_jsdoc('nonexistent.js', is_directory=False, scope='all')
    assert data['status'] == 'error', 'Returns error for missing file'
    assert 'FILE_NOT_FOUND' in str(data.get('error', '')), 'Error type should be FILE_NOT_FOUND'


def test_analyze_missing_directory_error():
    """Test error handling for missing directory."""
    data = analyze_jsdoc('/nonexistent/path', is_directory=True, scope='all')
    assert data['status'] == 'error', 'Returns error for missing directory'
    assert 'DIRECTORY_NOT_FOUND' in str(data.get('error', '')), 'Error type should be DIRECTORY_NOT_FOUND'


def test_analyze_metrics_complete():
    """Test all expected metric fields are present and consistent."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'missing-jsdoc.js'), is_directory=False, scope='all')
    metrics = data.get('metrics', {})
    for field in ('total_files', 'files_with_violations', 'critical', 'warnings', 'suggestions', 'total_violations'):
        assert field in metrics, f'Metrics missing field: {field}'
    total = int(metrics['critical']) + int(metrics['warnings']) + int(metrics['suggestions'])
    assert total == int(metrics['total_violations']), 'Severity counts should sum to total_violations'


def test_analyze_violation_structure():
    """Test violation objects have all required fields."""
    data = analyze_jsdoc(str(FIXTURES_DIR / 'missing-jsdoc.js'), is_directory=False, scope='all')
    violations = data.get('data', {}).get('violations', [])
    assert len(violations) > 0, 'Should have violations to check'
    for v in violations:
        assert 'file' in v, 'Violation must have file field'
        assert 'line' in v, 'Violation must have line field'
        assert 'type' in v, 'Violation must have type field'
        assert 'severity' in v, 'Violation must have severity field'
        assert v['severity'] in ('CRITICAL', 'WARNING', 'SUGGESTION'), f'Invalid severity: {v["severity"]}'


# =============================================================================
# CLI handler (cmd_analyze) in-process + empty-target behaviors
# =============================================================================


def test_cmd_analyze_file_prints_toon_and_returns_success(capsys):
    """cmd_analyze on a single file serializes the result to TOON and returns 0."""
    rc = cmd_analyze(Namespace(directory=None, file=str(FIXTURES_DIR / 'valid-jsdoc.js'), scope='all'))

    assert rc == 0
    assert 'status:' in capsys.readouterr().out


def test_cmd_analyze_directory_prints_toon_and_returns_success(capsys):
    """cmd_analyze on a directory serializes the aggregate result to TOON."""
    rc = cmd_analyze(Namespace(directory=str(FIXTURES_DIR), file=None, scope='all'))

    assert rc == 0
    out = capsys.readouterr().out
    assert 'status:' in out
    assert 'metrics' in out


def test_analyze_empty_directory_reports_zero_files_success():
    """A directory with no JavaScript files is a clean success with zero files —
    the no-files short-circuit, not an error."""
    with tempfile.TemporaryDirectory() as empty:
        data = analyze_jsdoc(empty, is_directory=True, scope='all')

        assert data['status'] == 'success'
        assert int(data['metrics']['total_files']) == 0
        assert data['data']['violations'] == []


# =============================================================================
# Main
# =============================================================================
