#!/usr/bin/env python3
"""Tests for manage-metrics.py `print-phase-breakdown` subcommand.

Covers:
- Successful extraction of the `## Phase Breakdown` section from metrics.md.
- Error when metrics.md is missing.
- Error when metrics.md exists but lacks the Phase Breakdown heading.
- Section bounded correctly when followed by another `##` heading.
- Direct cmd_* call (Tier 2 import) and CLI plumbing (subprocess).
"""

# ruff: noqa: I001
import importlib.util
import io
from argparse import Namespace
from contextlib import redirect_stdout

from conftest import PlanContext, get_script_path, run_script
from toon_parser import parse_toon  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')

# The entrypoint filename is kebab-case (manage-metrics.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
_spec = importlib.util.spec_from_file_location('manage_metrics', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)
_extract_phase_breakdown_section = manage_metrics._extract_phase_breakdown_section
cmd_end_phase = manage_metrics.cmd_end_phase
cmd_generate = manage_metrics.cmd_generate
cmd_print_phase_breakdown = manage_metrics.cmd_print_phase_breakdown
cmd_start_phase = manage_metrics.cmd_start_phase
write_metrics = manage_metrics.write_metrics


def _ns_print_breakdown(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, command='print-phase-breakdown', func=cmd_print_phase_breakdown)


def _ns_start_phase(plan_id: str, phase: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_end_phase(plan_id: str, phase: str, total_tokens: int | None = None) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
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
            # (Worked, Reported (wall), Idle, Tokens, Tool Uses)
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
                    '1-init': {'total_tokens': 1000, 'tool_uses': 5},
                    '2-refine': {'total_tokens': 2000, 'tool_uses': 7},
                },
            )
            lines = _render_breakdown('render-rule-03')
            total_line = next(ln for ln in lines if '**Total**' in ln)
            # 2 contributors out of 2 breakdown rows → plain sum, no marker.
            assert '3,000' in total_line  # tokens total
            assert '12' in total_line  # tool_uses total
            assert '(n=' not in total_line, total_line

    def test_worked_cell_rolls_up_agent_and_subagent_duration(self):
        """Worked cell = agent_duration_ms + subagent_duration_ms via format_duration."""
        with PlanContext(plan_id='render-rule-04'):
            _seed_phases(
                'render-rule-04',
                {
                    '1-init': {'agent_duration_ms': 120000, 'subagent_duration_ms': 60000},
                },
            )
            lines = _render_breakdown('render-rule-04')
            init_line = next(ln for ln in lines if '1-init' in ln)
            # worked = 180000 ms = 180 s = '3m0s'; no '(agent)' marker on the cell.
            assert '3m0s' in init_line, init_line
            assert '(agent)' not in init_line, init_line

    def test_reported_wall_column_renders_wall_clock(self):
        """The Reported (wall) column renders duration_seconds independent of worked."""
        with PlanContext(plan_id='render-rule-05'):
            _seed_phases(
                'render-rule-05',
                {
                    '1-init': {
                        'duration_seconds': 42.0,
                        'agent_duration_ms': 30000,
                    },
                },
            )
            lines = _render_breakdown('render-rule-05')
            init_line = next(ln for ln in lines if '1-init' in ln)
            cells = [c.strip() for c in init_line.split('|') if c.strip()]
            # cells = [Phase, Worked, Reported (wall), Idle, Tokens, Tool Uses]
            assert cells[1] == '30.0s'  # worked (agent 30000 ms)
            assert cells[2] == '42.0s'  # reported (wall) = 42.0 s
            assert cells[3] == '12.0s'  # idle = max(0, 42 - 30) = 12 s

    def test_total_marker_with_partial_worked_contribution(self):
        """Total Worked respects the partial-Total marker when only some phases worked."""
        with PlanContext(plan_id='render-rule-06'):
            _seed_phases(
                'render-rule-06',
                {
                    '1-init': {'agent_duration_ms': 179800},
                    '2-refine': {'agent_duration_ms': 60000},
                    '3-outline': {},  # No duration of any kind.
                },
            )
            lines = _render_breakdown('render-rule-06')
            total_line = next(ln for ln in lines if '**Total**' in ln)
            # Two of three breakdown rows contribute worked time → marker '(n=2/3)'.
            assert '(n=2/3)' in total_line, total_line


class TestEndToEndPhaseBreakdownRendering:
    """End-to-end regression: metrics.toon → generate → print-phase-breakdown.

    Exercises the producer→consumer contract that the phase-6-finalize Phase
    Breakdown override path depends on — distinct from the cmd_generate-only
    unit tests in TestPhaseBreakdownRenderingRule. The captured section is the
    exact content the override renderer inlines into the finalize summary.
    """

    def test_captured_section_carries_three_time_columns_with_idle(self):
        """generate → print-phase-breakdown captures Worked/Reported/Idle with the
        worked rollup including subagent_duration_ms and the correct idle residual.
        """
        with PlanContext(plan_id='metrics-e2e-01'):
            # Seed a metrics.toon with full per-phase timing, as the live workflow
            # would after end-phase + enrich. 5-execute carries a subagent rollup
            # and genuine idle time (wall 600s > worked 200s + 100s).
            write_metrics(
                'metrics-e2e-01',
                {
                    'phases': {
                        '1-init': {
                            'start_time': '2026-05-22T10:00:00+00:00',
                            'end_time': '2026-05-22T10:02:00+00:00',
                            'duration_seconds': 120,
                            'agent_duration_ms': 90000,
                        },
                        '5-execute': {
                            'start_time': '2026-05-22T10:02:00+00:00',
                            'end_time': '2026-05-22T10:12:00+00:00',
                            'duration_seconds': 600,
                            'agent_duration_ms': 200000,
                            'subagent_duration_ms': 100000,
                        },
                    },
                },
            )

            gen_result = cmd_generate(_ns_generate('metrics-e2e-01'))
            assert gen_result['status'] == 'success'

            buf = io.StringIO()
            with redirect_stdout(buf):
                print_result = cmd_print_phase_breakdown(_ns_print_breakdown('metrics-e2e-01'))
            assert print_result['status'] == 'success'
            section = buf.getvalue()

            # The captured section begins with the heading and carries the three
            # time columns in order, followed by Tokens and Tool Uses.
            assert section.startswith('## Phase Breakdown')
            header = next(ln for ln in section.splitlines() if ln.startswith('| Phase'))
            cols = [c.strip() for c in header.strip('|').split('|')]
            assert cols == ['Phase', 'Worked', 'Reported (wall)', 'Idle', 'Tokens', 'Tool Uses']

            # 5-execute worked time includes subagent_duration_ms:
            # worked = 200000 + 100000 = 300000 ms = 300 s = '5m0s'.
            exec_line = next(ln for ln in section.splitlines() if ln.startswith('| 5-execute'))
            exec_cells = [c.strip() for c in exec_line.strip('|').split('|')]
            assert exec_cells[1] == '5m0s'  # Worked
            assert exec_cells[2] == '10m0s'  # Reported (wall) = 600 s
            # idle = max(0, 600 - 300) = 300 s = '5m0s'.
            assert exec_cells[3] == '5m0s'  # Idle

    def test_captured_section_idle_zero_clamp_when_worked_exceeds_wall(self):
        """When worked exceeds wall-clock, the captured Idle cell renders the zero clamp."""
        with PlanContext(plan_id='metrics-e2e-02'):
            write_metrics(
                'metrics-e2e-02',
                {
                    'phases': {
                        # worked (agent 100s + subagent 80s = 180s) > wall (120s).
                        '5-execute': {
                            'start_time': '2026-05-22T10:00:00+00:00',
                            'end_time': '2026-05-22T10:02:00+00:00',
                            'duration_seconds': 120,
                            'agent_duration_ms': 100000,
                            'subagent_duration_ms': 80000,
                        },
                    },
                },
            )

            assert cmd_generate(_ns_generate('metrics-e2e-02'))['status'] == 'success'
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_print_phase_breakdown(_ns_print_breakdown('metrics-e2e-02'))
            section = buf.getvalue()

            exec_line = next(ln for ln in section.splitlines() if ln.startswith('| 5-execute'))
            exec_cells = [c.strip() for c in exec_line.strip('|').split('|')]
            assert exec_cells[1] == '3m0s'  # Worked = 180 s
            assert exec_cells[2] == '2m0s'  # Reported (wall) = 120 s
            # idle = max(0, 120 - 180) = 0 → renders the zero-clamped cell '-'.
            assert exec_cells[3] == '-'  # Idle clamped to zero → absent per-cell

    def test_captured_section_total_row_sums_three_time_columns(self):
        """The captured Total row sums Worked, Reported (wall), and Idle independently
        across multiple phases — the producer→consumer contract for the override path.
        """
        with PlanContext(plan_id='metrics-e2e-03'):
            write_metrics(
                'metrics-e2e-03',
                {
                    'phases': {
                        '1-init': {
                            'start_time': '2026-05-22T10:00:00+00:00',
                            'end_time': '2026-05-22T10:03:00+00:00',
                            'duration_seconds': 180,
                            'agent_duration_ms': 120000,
                        },
                        '5-execute': {
                            'start_time': '2026-05-22T10:03:00+00:00',
                            'end_time': '2026-05-22T10:13:00+00:00',
                            'duration_seconds': 600,
                            'agent_duration_ms': 240000,
                            'subagent_duration_ms': 120000,
                        },
                    },
                },
            )

            assert cmd_generate(_ns_generate('metrics-e2e-03'))['status'] == 'success'
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_print_phase_breakdown(_ns_print_breakdown('metrics-e2e-03'))
            section = buf.getvalue()

            total_line = next(ln for ln in section.splitlines() if '**Total**' in ln)
            total_cells = [c.strip() for c in total_line.strip('|').split('|')]
            # worked total = 120 + 360 = 480 s = '8m0s';
            # wall total   = 180 + 600 = 780 s = '13m0s';
            # idle total   = (180-120) + (600-360) = 60 + 240 = 300 s = '5m0s'.
            assert total_cells[1] == '**8m0s**'   # Worked
            assert total_cells[2] == '**13m0s**'  # Reported (wall)
            assert total_cells[3] == '**5m0s**'   # Idle
