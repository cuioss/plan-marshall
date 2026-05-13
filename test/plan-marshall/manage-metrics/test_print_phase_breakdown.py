#!/usr/bin/env python3
"""Tests for manage_metrics.py `print-phase-breakdown` subcommand.

Covers:
- Successful extraction of the `## Phase Breakdown` section from metrics.md.
- Error when metrics.md is missing.
- Error when metrics.md exists but lacks the Phase Breakdown heading.
- Section bounded correctly when followed by another `##` heading.
- Direct cmd_* call (Tier 2 import) and CLI plumbing (subprocess).
"""

# ruff: noqa: I001
import io
from argparse import Namespace
from contextlib import redirect_stdout

from manage_metrics import (  # type: ignore[import-not-found]
    _extract_phase_breakdown_section,
    cmd_end_phase,
    cmd_generate,
    cmd_print_phase_breakdown,
    cmd_start_phase,
    write_metrics,
)

from conftest import PlanContext, get_script_path, run_script
from toon_parser import parse_toon  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage_metrics.py')


def _ns_print_breakdown(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, command='print-phase-breakdown', func=cmd_print_phase_breakdown)


def _ns_start_phase(plan_id: str, phase: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_end_phase(plan_id: str, phase: str, total_tokens: int | None = None) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        input_tokens=None,
        output_tokens=None,
        duration_ms=None,
        tool_uses=None,
        command='end-phase',
        func=cmd_end_phase,
    )


def _ns_generate(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, command='generate', func=cmd_generate)


def _seed_metrics_md(plan_id: str) -> None:
    """Seed metrics.md by recording a couple of phases and calling generate."""
    cmd_start_phase(_ns_start_phase(plan_id, '1-init'))
    cmd_end_phase(_ns_end_phase(plan_id, '1-init', total_tokens=25_000))
    cmd_start_phase(_ns_start_phase(plan_id, '2-refine'))
    cmd_end_phase(_ns_end_phase(plan_id, '2-refine', total_tokens=10_000))
    result = cmd_generate(_ns_generate(plan_id))
    assert result['status'] == 'success'


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

    def test_success_prints_section_and_skips_toon(self):
        with PlanContext(plan_id='metrics-print-01'):
            _seed_metrics_md('metrics-print-01')
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = cmd_print_phase_breakdown(_ns_print_breakdown('metrics-print-01'))
            assert result['status'] == 'success'
            assert result['_print_only'] is True
            assert result['bytes_written'] > 0
            output = buf.getvalue()
            assert output.startswith('## Phase Breakdown')
            assert 'Phase Details' not in output

    def test_error_when_metrics_md_missing(self):
        with PlanContext(plan_id='metrics-print-02'):
            # No generate call → no metrics.md.
            result = cmd_print_phase_breakdown(_ns_print_breakdown('metrics-print-02'))
            assert result['status'] == 'error'
            assert result['error'] == 'metrics_md_not_found'
            assert '_print_only' not in result

    def test_error_when_section_missing(self):
        with PlanContext(plan_id='metrics-print-03') as ctx:
            md_path = ctx.plan_dir / 'metrics.md'
            md_path.write_text('# Metrics\n\nNo phase breakdown section here.\n', encoding='utf-8')
            result = cmd_print_phase_breakdown(_ns_print_breakdown('metrics-print-03'))
            assert result['status'] == 'error'
            assert result['error'] == 'phase_breakdown_section_not_found'


class TestCliPlumbing:
    """Subprocess test verifying the CLI surface (argparse wiring + stdout)."""

    def test_cli_success_prints_only_section(self):
        with PlanContext(plan_id='metrics-print-cli-01'):
            _seed_metrics_md('metrics-print-cli-01')
            result = run_script(
                SCRIPT_PATH, 'print-phase-breakdown', '--plan-id', 'metrics-print-cli-01'
            )
            assert result.returncode == 0, f'stderr: {result.stderr}'
            stdout = result.stdout
            assert stdout.startswith('## Phase Breakdown'), stdout[:200]
            # Success path skips TOON status output entirely.
            assert 'status: success' not in stdout
            assert 'status: error' not in stdout

    def test_cli_error_emits_toon_when_metrics_missing(self):
        with PlanContext(plan_id='metrics-print-cli-02'):
            result = run_script(
                SCRIPT_PATH, 'print-phase-breakdown', '--plan-id', 'metrics-print-cli-02'
            )
            assert result.returncode == 0
            payload = parse_toon(result.stdout)
            assert payload['status'] == 'error'
            assert payload['error'] == 'metrics_md_not_found'


def _seed_phases(plan_id: str, phases: dict) -> None:
    """Write a metrics.toon file with the given phases dict, bypassing start/end."""
    write_metrics(plan_id, {'phases': phases})


def _render_breakdown(plan_id: str) -> list[str]:
    """Call cmd_generate and return the Phase Breakdown table lines from metrics.md.

    Returns the list of lines starting with the header row and ending with the
    Total row (whitespace stripped).
    """
    result = cmd_generate(_ns_generate(plan_id))
    assert result['status'] == 'success', result
    from file_ops import get_plan_dir  # type: ignore[import-not-found]

    md_path = get_plan_dir(plan_id) / 'metrics.md'
    content = md_path.read_text(encoding='utf-8')
    section = _extract_phase_breakdown_section(content)
    assert section is not None
    # Strip down to table rows.
    table_lines = [ln for ln in section.splitlines() if ln.startswith('|')]
    return table_lines


class TestPhaseBreakdownRenderingRule:
    """Tests for the symmetric per-cell + Total rendering rule (D1 / Tier 3+4b)."""

    def test_all_cells_dash_total_dash(self):
        """All per-phase cells '-' → every Total cell is '-' (never '0')."""
        with PlanContext(plan_id='render-rule-01'):
            _seed_phases(
                'render-rule-01',
                {
                    '1-init': {},  # No numeric fields.
                    '2-refine': {},
                },
            )
            lines = _render_breakdown('render-rule-01')
            total_line = next(ln for ln in lines if '**Total**' in ln)
            # Every numeric cell on the Total row is '-' (no '0', no '0s').
            cells = [c.strip() for c in total_line.split('|') if c.strip()]
            # cells = ['**Total**', '**-**', '**-**', '**-**', '**-**', '**-**']
            assert cells[0] == '**Total**'
            for numeric_cell in cells[1:]:
                assert numeric_cell == '**-**', f'expected dash, got {numeric_cell!r}'

    def test_subset_present_total_marker(self):
        """Subset present → Total cell carries the (n=k/N) marker."""
        with PlanContext(plan_id='render-rule-02'):
            _seed_phases(
                'render-rule-02',
                {
                    '1-init': {'total_tokens': 1000},
                    '2-refine': {},
                    '3-outline': {'total_tokens': 2000},
                },
            )
            lines = _render_breakdown('render-rule-02')
            total_line = next(ln for ln in lines if '**Total**' in ln)
            # Tokens subset has 2/3 phases contributing.
            assert '3,000 (n=2/3)' in total_line, total_line
            # Other numeric columns stay '-'.
            cells = [c.strip() for c in total_line.split('|') if c.strip()]
            # Duration cell.
            assert cells[1] == '**-**'

    def test_all_cells_present_plain_sum(self):
        """All per-phase cells present → Total renders plain sum (no marker)."""
        with PlanContext(plan_id='render-rule-03'):
            _seed_phases(
                'render-rule-03',
                {
                    '1-init': {'total_tokens': 1000, 'input_tokens': 500, 'output_tokens': 50},
                    '2-refine': {'total_tokens': 2000, 'input_tokens': 1500, 'output_tokens': 75},
                },
            )
            lines = _render_breakdown('render-rule-03')
            total_line = next(ln for ln in lines if '**Total**' in ln)
            # 2 contributors out of 2 breakdown rows → plain sum, no marker.
            assert '3,000' in total_line
            assert '2,000' in total_line  # input total
            assert '125' in total_line  # output total
            assert '(n=' not in total_line, total_line

    def test_duration_agent_fallback_per_cell(self):
        """1-init has only agent_duration_seconds → cell renders '{value}s (agent)'."""
        with PlanContext(plan_id='render-rule-04'):
            _seed_phases(
                'render-rule-04',
                {
                    '1-init': {'agent_duration_seconds': 179.8},
                },
            )
            lines = _render_breakdown('render-rule-04')
            init_line = next(ln for ln in lines if '1-init' in ln)
            assert '179.8s (agent)' in init_line, init_line

    def test_duration_wall_clock_preferred_over_agent_fallback(self):
        """1-init has duration_seconds → renders wall-clock (agent fallback NOT triggered)."""
        with PlanContext(plan_id='render-rule-05'):
            _seed_phases(
                'render-rule-05',
                {
                    '1-init': {
                        'duration_seconds': 42.0,
                        'agent_duration_seconds': 179.8,
                    },
                },
            )
            lines = _render_breakdown('render-rule-05')
            init_line = next(ln for ln in lines if '1-init' in ln)
            # Wall-clock formatting is '42.0s', no '(agent)' marker on this cell.
            assert '42.0s' in init_line, init_line
            assert '(agent)' not in init_line, init_line

    def test_duration_total_marker_with_agent_fallback_contribution(self):
        """Total Duration respects the partial-Total marker when 1-init contributes an agent fallback."""
        with PlanContext(plan_id='render-rule-06'):
            _seed_phases(
                'render-rule-06',
                {
                    '1-init': {'agent_duration_seconds': 179.8},
                    '2-refine': {'duration_seconds': 60.0},
                    '3-outline': {},  # No duration of any kind.
                },
            )
            lines = _render_breakdown('render-rule-06')
            total_line = next(ln for ln in lines if '**Total**' in ln)
            # Two contributors out of three breakdown rows → marker '(n=2/3)'.
            assert '(n=2/3)' in total_line, total_line
            # 1-init cell renders agent fallback.
            init_line = next(ln for ln in lines if '1-init' in ln)
            assert '179.8s (agent)' in init_line, init_line
