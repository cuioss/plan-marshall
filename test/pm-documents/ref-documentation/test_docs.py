#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for docs.py - documentation content quality operations (review and tone analysis).

Tier 2 (direct import) tests with 3 subprocess CLI plumbing tests retained.
"""

import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

TEST_DIR = Path(__file__).parent
SCRIPT_PATH = get_script_path('pm-documents', 'ref-documentation', 'docs.py')
FIXTURES_DIR = TEST_DIR / 'fixtures'

_review_mod = load_script_module('pm-documents', 'ref-documentation', '_cmd_review.py', '_cmd_review')
_tone_mod = load_script_module('pm-documents', 'ref-documentation', '_cmd_analyze_tone.py', '_cmd_analyze_tone')

cmd_review = _review_mod.cmd_review
analyze_content_line = _review_mod.analyze_content_line
cmd_analyze_tone = _tone_mod.cmd_analyze_tone


def _review_args(file=None, directory=None, recursive=False, output=None):
    return Namespace(command='review', file=file, directory=directory, recursive=recursive, output=output)


def _tone_args(file=None, directory=None, output=None, pretty=False):
    return Namespace(command='analyze-tone', file=file, directory=directory, output=output, pretty=pretty)


# =============================================================================
# CLI plumbing (subprocess)
# =============================================================================


def test_script_exists():
    assert SCRIPT_PATH.exists(), f'Script not found: {SCRIPT_PATH}'


def test_main_help_lists_both_subcommands():
    result = run_script(SCRIPT_PATH, '--help')

    combined = result.stdout + result.stderr
    assert 'review' in combined, 'review subcommand should appear in help'
    assert 'analyze-tone' in combined, 'analyze-tone subcommand should appear in help'


def test_review_help_shows_usage():
    result = run_script(SCRIPT_PATH, 'review', '--help')

    combined = result.stdout + result.stderr
    assert 'usage' in combined.lower(), f'Review help should show usage: {combined}'


# =============================================================================
# analyze_content_line — line-level pattern detection (Tier 2)
# =============================================================================


def test_analyze_content_line_flags_marketing_adjective():
    issues = analyze_content_line('This is an amazing library.', 7, 'doc.adoc')

    assert len(issues) == 1
    issue = issues[0]
    assert issue['type'] == 'tone'
    assert issue['subtype'] == 'promotional_adjective'
    assert issue['text'] == 'amazing'
    assert issue['line'] == 7
    assert issue['file'] == 'doc.adoc'


def test_analyze_content_line_flags_qualification_buzzword():
    issues = analyze_content_line('A robust, enterprise-grade solution.', 3, 'doc.adoc')

    subtypes = {i['subtype'] for i in issues}
    assert subtypes == {'qualification_buzzword'}
    assert {i['text'] for i in issues} == {'robust', 'enterprise-grade'}


def test_analyze_content_line_flags_todo_completeness_marker():
    issues = analyze_content_line('TODO: document the rest', 1, 'doc.adoc')

    assert len(issues) == 1
    assert issues[0]['type'] == 'completeness'
    assert issues[0]['subtype'] == 'todo_marker'


def test_analyze_content_line_clean_line_yields_no_issues():
    issues = analyze_content_line('The validator checks the token signature.', 5, 'doc.adoc')

    assert issues == []


# =============================================================================
# Review subcommand (Tier 2)
# =============================================================================


def test_review_clean_fixture_reports_zero_issues():
    valid_file = FIXTURES_DIR / 'valid.adoc'

    result = cmd_review(_review_args(file=str(valid_file)))

    assert result['status'] == 'success'
    assert result['data']['files_analyzed'] == 1
    assert result['data']['total_issues'] == 0
    assert result['metrics']['tone_issues'] == 0
    assert result['metrics']['completeness_issues'] == 0


def test_review_detects_marketing_and_completeness_issues(tmp_path):
    doc = tmp_path / 'promo.adoc'
    doc.write_text('= Doc\n\nOur powerful, world-class engine.\n\nTODO: finish this section\n')

    result = cmd_review(_review_args(file=str(doc)))

    assert result['status'] == 'success'
    assert result['data']['total_issues'] >= 3
    assert result['metrics']['tone_issues'] >= 2
    assert result['metrics']['completeness_issues'] >= 1
    issue_types = {i['type'] for i in result['data']['issues']}
    assert issue_types == {'tone', 'completeness'}


def test_review_skips_code_blocks(tmp_path):
    doc = tmp_path / 'code.adoc'
    doc.write_text('= Doc\n\n[source,text]\n----\nThis is an amazing powerful example.\n----\n')

    result = cmd_review(_review_args(file=str(doc)))

    assert result['status'] == 'success'
    assert result['data']['total_issues'] == 0


def test_review_directory_aggregates_file_count():
    result = cmd_review(_review_args(directory=str(FIXTURES_DIR)))

    assert result['status'] == 'success'
    assert result['data']['files_analyzed'] >= 1


def test_review_writes_output_file(tmp_path):
    doc = tmp_path / 'doc.adoc'
    doc.write_text('= Doc\n\nClean technical content here.\n')
    output = tmp_path / 'report.json'

    result = cmd_review(_review_args(file=str(doc), output=str(output)))

    assert result['status'] == 'success'
    assert output.exists(), 'Review should write the report to the output path'
    assert '"total_issues"' in output.read_text()


def test_review_missing_args_returns_error():
    result = cmd_review(_review_args())

    assert result['status'] == 'error'
    assert result['error'] == 'missing_args'


# =============================================================================
# Analyze-tone subcommand (Tier 2)
# =============================================================================


def test_analyze_tone_detects_promotional_and_performance_claims():
    sample_content = """= Sample Documentation

== Introduction

Our best-in-class library is the perfect, ultimate solution.
It runs 10x faster than the alternatives.
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.adoc', delete=False) as f:
        f.write(sample_content)
        sample_file = Path(f.name)

    try:
        result = cmd_analyze_tone(_tone_args(file=str(sample_file)))

        assert result['status'] == 'success'
        assert result['summary']['total_issues'] >= 2
        assert result['summary']['promotional_count'] >= 1
        assert result['summary']['performance_claim_count'] >= 1
        categories = {i['category'] for i in result['all_issues']}
        assert 'promotional' in categories
        assert 'performance_claim' in categories
    finally:
        sample_file.unlink(missing_ok=True)


def test_analyze_tone_writes_pretty_output(tmp_path):
    sample = tmp_path / 'sample.adoc'
    sample.write_text('= Doc\n\nThe ultimate, perfect tool for the job.\n')
    output = tmp_path / 'analysis.json'

    result = cmd_analyze_tone(_tone_args(file=str(sample), output=str(output), pretty=True))

    assert result['status'] == 'success'
    assert output.exists(), 'Pretty output file should be written'
    content = output.read_text()
    assert 'promotional' in content
    assert '\n  ' in content, 'Pretty output should be indented'


def test_analyze_tone_clean_directory_reports_no_issues(tmp_path):
    (tmp_path / 'sample.adoc').write_text('= Sample\n\nTechnical documentation content.\n')

    result = cmd_analyze_tone(_tone_args(directory=str(tmp_path)))

    assert result['status'] == 'success'
    assert result['summary']['total_issues'] == 0
    assert result['all_issues'] == []


def test_analyze_tone_skips_attribute_and_heading_lines(tmp_path):
    doc = tmp_path / 'doc.adoc'
    doc.write_text('= The Best Perfect Heading\n:author: ideal\n\nNeutral body text.\n')

    result = cmd_analyze_tone(_tone_args(file=str(doc)))

    assert result['status'] == 'success'
    assert result['summary']['total_issues'] == 0


def test_analyze_tone_missing_args_returns_error():
    result = cmd_analyze_tone(_tone_args())

    assert result['status'] == 'error'
    assert result['error'] == 'missing_args'
