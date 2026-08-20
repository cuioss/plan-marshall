#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py `print-phase-breakdown` subcommand."""


import io
from contextlib import redirect_stdout

from _manage_metrics_fixtures import (
    ns_generate,
    ns_print_phase_breakdown,
)
from _print_phase_breakdown_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _UNSEEDED_PLAN_IDS,
    _extract_phase_breakdown_section,
    _seed_guarded_plan_dirs,
    _seed_metrics_md,
    cmd_generate,
    cmd_print_phase_breakdown,
    manage_metrics,
    write_metrics,
)


class TestExtractedSectionCarriesBillingColumn:
    """The extracted breakdown carries the first-class `Billing (cost)` column.

    The breakdown section is what most consumers actually read — a cost figure
    rendered only in the Phase Details bullets is a figure the report declines to
    put where the comparison happens.
    """

    def test_extracted_section_carries_the_billing_column(self, plan_context):
        _seed_metrics_md('metrics-billing-column')
        data = manage_metrics.read_metrics_raw('metrics-billing-column')
        data['phases']['1-init']['billing_weighted_total'] = 41003
        data['phases']['2-refine']['billing_weighted_total'] = 78000
        write_metrics('metrics-billing-column', data)
        cmd_generate(ns_generate('metrics-billing-column'))

        content = (
            plan_context.plan_dir_for('metrics-billing-column') / 'metrics.md'
        ).read_text(encoding='utf-8')
        section = _extract_phase_breakdown_section(content)

        assert section is not None
        assert 'Billing (cost)' in section
        assert '41,003' in section
        assert '78,000' in section
        # Its own Total, aggregated independently of the Tokens column.
        assert '119,003' in section


class TestExtractedSectionCarriesPopulationQualifiedHeader:
    """The extracted breakdown names the population its Tokens column measures.

    The breakdown section is what the finalize summary inlines, so it is where
    most readers meet the Tokens figure. A qualifier that survives only in the
    full metrics.md — and is lost by the extraction the summary actually uses —
    would leave that reader with the bare, population-silent column this plan
    exists to remove.
    """

    def test_extracted_section_header_names_the_default_population(self, plan_context):
        _seed_metrics_md('metrics-population-header')

        content = (
            plan_context.plan_dir_for('metrics-population-header') / 'metrics.md'
        ).read_text(encoding='utf-8')
        section = _extract_phase_breakdown_section(content)

        assert section is not None
        header = next(ln for ln in section.splitlines() if ln.startswith('| Phase'))
        tokens_col = [c.strip() for c in header.strip('|').split('|')][4]
        assert tokens_col == 'Tokens (dispatched unless marked)'
        # Not the bare column, and not a single-population claim over a column
        # that carries inline rows too.
        assert tokens_col != 'Tokens'
        assert tokens_col != 'Tokens (dispatched)'


class TestExtractPhaseBreakdownSection:
    """Unit tests for the pure-string helper."""

    def test_extracts_section_with_following_heading(self):
        content = (
            '# Header\n'
            '\n'
            '## Phase Breakdown\n'
            '\n'
            '| Phase | Duration |\n'
            '|-------|----------|\n'
            '| 1-init | 1m |\n'
            '\n'
            '## Phase Details\n'
            '\n'
            'body\n'
        )
        section = _extract_phase_breakdown_section(content)
        assert section is not None
        assert section.startswith('## Phase Breakdown')
        assert '| 1-init | 1m |' in section
        # Stops before the next ## heading.
        assert '## Phase Details' not in section
        assert 'body' not in section

    def test_extracts_section_until_eof_when_no_following_heading(self):
        content = '## Phase Breakdown\n\n| col |\n| --- |\n| val |\n'
        section = _extract_phase_breakdown_section(content)
        assert section is not None
        assert section.startswith('## Phase Breakdown')
        assert '| val |' in section

    def test_returns_none_when_heading_missing(self):
        content = '# Header\n\nNo breakdown section here.\n## Other\n'
        assert _extract_phase_breakdown_section(content) is None

    def test_section_ends_with_single_newline(self):
        content = '## Phase Breakdown\n\n| col |\n| val |\n\n\n## Next\n'
        section = _extract_phase_breakdown_section(content)
        assert section is not None
        # Trailing blank lines normalised to exactly one trailing newline.
        assert section.endswith('| val |\n')


class TestCmdPrintPhaseBreakdown:
    """Tier-2 import tests for the cmd_* function."""

    def test_default_writes_artifact_and_returns_toon(self, plan_context):
        """No --output-file → writes work/phase-breakdown-output.txt and emits TOON."""
        _seed_metrics_md('metrics-print-01')
        plan_dir = plan_context.plan_dir_for('metrics-print-01')
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = cmd_print_phase_breakdown(ns_print_phase_breakdown('metrics-print-01'))
        assert result['status'] == 'success'
        assert result['file'] == 'work/phase-breakdown-output.txt'
        assert result['bytes_written'] > 0
        assert result['plan_id'] == 'metrics-print-01'
        assert '_print_only' not in result
        # Nothing on stdout in direct-write mode.
        assert buf.getvalue() == ''
        # Artifact file exists and contains verbatim section.
        artifact = plan_dir / 'work' / 'phase-breakdown-output.txt'
        assert artifact.is_file()
        section = artifact.read_text(encoding='utf-8')
        assert section.startswith('## Phase Breakdown')
        assert 'Phase Details' not in section
        assert result['bytes_written'] == len(section.encode('utf-8'))

    def test_explicit_relative_output_file_creates_parent_dirs(self, plan_context):
        """--output-file with a nested relative path creates missing parents."""
        _seed_metrics_md('metrics-print-explicit')
        plan_dir = plan_context.plan_dir_for('metrics-print-explicit')
        result = cmd_print_phase_breakdown(
            ns_print_phase_breakdown('metrics-print-explicit', output_file='work/nested/breakdown.txt')
        )
        assert result['status'] == 'success'
        assert result['file'] == 'work/nested/breakdown.txt'
        assert result['bytes_written'] > 0
        artifact = plan_dir / 'work' / 'nested' / 'breakdown.txt'
        assert artifact.is_file()
        assert artifact.read_text(encoding='utf-8').startswith('## Phase Breakdown')

    def test_legacy_stdout_mode_with_dash(self, plan_context):
        """--output-file - retains legacy stdout-only behavior with the _print_only sentinel."""
        _seed_metrics_md('metrics-print-stdout')
        plan_dir = plan_context.plan_dir_for('metrics-print-stdout')
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = cmd_print_phase_breakdown(
                ns_print_phase_breakdown('metrics-print-stdout', output_file='-')
            )
        assert result['status'] == 'success'
        assert result['_print_only'] is True
        assert 'file' not in result
        output = buf.getvalue()
        assert output.startswith('## Phase Breakdown')
        assert 'Phase Details' not in output
        assert result['bytes_written'] == len(output.encode('utf-8'))
        # Default artifact file is NOT created in legacy mode.
        assert not (plan_dir / 'work' / 'phase-breakdown-output.txt').exists()

    def test_absolute_output_file_rejected(self, plan_context):
        """Absolute --output-file paths are rejected with output_file_must_be_relative."""
        _seed_metrics_md('metrics-print-abs')
        result = cmd_print_phase_breakdown(
            ns_print_phase_breakdown('metrics-print-abs', output_file='/tmp/breakdown.txt')
        )
        assert result['status'] == 'error'
        assert result['error'] == 'output_file_must_be_relative'
        assert result['plan_id'] == 'metrics-print-abs'

    def test_traversal_output_file_rejected(self, plan_context):
        """Path traversal sequences are rejected with output_file_must_be_relative."""
        _seed_metrics_md('metrics-print-trav')
        result = cmd_print_phase_breakdown(
            ns_print_phase_breakdown('metrics-print-trav', output_file='../../etc/passwd')
        )
        assert result['status'] == 'error'
        assert result['error'] == 'output_file_must_be_relative'
        assert result['plan_id'] == 'metrics-print-trav'

    def test_error_when_metrics_md_missing(self, plan_context):
        # No generate call → no metrics.md.
        result = cmd_print_phase_breakdown(ns_print_phase_breakdown('metrics-print-02'))
        assert result['status'] == 'error'
        assert result['error'] == 'metrics_md_not_found'
        assert '_print_only' not in result

    def test_error_when_section_missing(self, plan_context):
        md_path = plan_context.plan_dir_for('metrics-print-03') / 'metrics.md'
        md_path.write_text('# Metrics\n\nNo phase breakdown section here.\n', encoding='utf-8')
        result = cmd_print_phase_breakdown(ns_print_phase_breakdown('metrics-print-03'))
        assert result['status'] == 'error'
        assert result['error'] == 'phase_breakdown_section_not_found'
