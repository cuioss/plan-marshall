#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-metrics.py `print-phase-breakdown` subcommand."""


# ruff: noqa: I001
import pytest
from conftest import run_script
from toon_parser import parse_toon
from _manage_metrics_fixtures import (
    ns_generate,
    ns_print_phase_breakdown,
)
from _print_phase_breakdown_fixtures import (
    SCRIPT_PATH,
    _UNSEEDED_PLAN_IDS,
    _render_breakdown,
    _seed_metrics_md,
    _seed_phases,
    cmd_generate,
    cmd_print_phase_breakdown,
    manage_metrics,
    write_metrics,
)


@pytest.fixture(autouse=True)
def _seed_guarded_plan_dirs(plan_context, monkeypatch):
    """Auto-seed ``status.json`` at the require_plan_exists chokepoint.

    The patched guard resolves the plan dir via the real ``get_plan_dir`` and, for
    any plan_id NOT registered as unseeded, writes the ``status.json`` sentinel
    before delegating to the genuine ``require_plan_exists``. This keeps every
    positive test's happy path intact without per-test seeding, while the
    negative tests (which call ``_register_unseeded``) still exercise the real
    ``plan_not_found`` failure.
    """
    _UNSEEDED_PLAN_IDS.clear()
    real_require = manage_metrics.require_plan_exists
    real_get_plan_dir = manage_metrics.get_plan_dir

    def _seeding_require(plan_id):
        if plan_id not in _UNSEEDED_PLAN_IDS:
            plan_dir = real_get_plan_dir(plan_id)
            plan_dir.mkdir(parents=True, exist_ok=True)
            sentinel = plan_dir / 'status.json'
            if not sentinel.is_file():
                sentinel.write_text('{}', encoding='utf-8')
        return real_require(plan_id)

    monkeypatch.setattr(manage_metrics, 'require_plan_exists', _seeding_require)
    return plan_context


class TestCliPlumbing:
    """Subprocess test verifying the CLI surface (argparse wiring + stdout)."""

    def test_cli_default_emits_toon_envelope(self, plan_context):
        """Default invocation writes the artifact and emits a TOON envelope on stdout."""
        _seed_metrics_md('metrics-print-cli-01')
        plan_dir = plan_context.plan_dir_for('metrics-print-cli-01')
        result = run_script(
            SCRIPT_PATH, 'print-phase-breakdown', '--plan-id', 'metrics-print-cli-01'
        )
        assert result.returncode == 0, f'stderr: {result.stderr}'
        payload = parse_toon(result.stdout)
        assert payload['status'] == 'success'
        assert payload['plan_id'] == 'metrics-print-cli-01'
        assert payload['file'] == 'work/phase-breakdown-output.txt'
        assert int(payload['bytes_written']) > 0
        # Artifact written to disk.
        artifact = plan_dir / 'work' / 'phase-breakdown-output.txt'
        assert artifact.is_file()
        assert artifact.read_text(encoding='utf-8').startswith('## Phase Breakdown')

    def test_cli_dash_output_file_retains_legacy_stdout(self, plan_context):
        """--output-file - retains section-only stdout (no TOON envelope)."""
        _seed_metrics_md('metrics-print-cli-dash')
        result = run_script(
            SCRIPT_PATH,
            'print-phase-breakdown',
            '--plan-id',
            'metrics-print-cli-dash',
            '--output-file',
            '-',
        )
        assert result.returncode == 0, f'stderr: {result.stderr}'
        stdout = result.stdout
        assert stdout.startswith('## Phase Breakdown'), stdout[:200]
        assert 'status: success' not in stdout
        assert 'status: error' not in stdout

    def test_cli_error_emits_toon_when_metrics_missing(self, plan_context):
        result = run_script(
            SCRIPT_PATH, 'print-phase-breakdown', '--plan-id', 'metrics-print-cli-02'
        )
        assert result.returncode == 0
        payload = parse_toon(result.stdout)
        assert payload['status'] == 'error'
        assert payload['error'] == 'metrics_md_not_found'

    def test_cli_rejects_absolute_output_file(self, plan_context):
        _seed_metrics_md('metrics-print-cli-abs')
        result = run_script(
            SCRIPT_PATH,
            'print-phase-breakdown',
            '--plan-id',
            'metrics-print-cli-abs',
            '--output-file',
            '/tmp/breakdown.txt',
        )
        assert result.returncode == 0
        payload = parse_toon(result.stdout)
        assert payload['status'] == 'error'
        assert payload['error'] == 'output_file_must_be_relative'


class TestPhaseBreakdownRenderingRule:
    """Tests for the symmetric per-cell + Total rendering rule (D1 / Tier 3+4b)."""

    def test_all_cells_dash_total_dash(self, plan_context):
        """All per-phase cells '-' → every Total cell is '-' (never '0')."""
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

    def test_subset_present_total_marker(self, plan_context):
        """Subset present → Total cell carries the (n=k/N) marker."""
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
        # Tokens subset has 2 of the canonical six phases contributing; the
        # completeness denominator is the canonical six, not the present-row count.
        assert '3,000 (n=2/6)' in total_line, total_line
        # Other numeric columns stay '-'.
        cells = [c.strip() for c in total_line.split('|') if c.strip()]
        # Duration cell.
        assert cells[1] == '**-**'

    def test_all_present_cells_use_canonical_six_denominator(self, plan_context):
        """All present per-phase cells contribute, yet the completeness denominator
        is the canonical six — a 2-of-6 subset renders the partial (n=2/6) marker,
        not a plain sum. The denominator is len(PHASE_NAMES), not the present-row
        count, so a fewer-than-six fixture can never look complete.
        """
        _seed_phases(
            'render-rule-03',
            {
                '1-init': {'total_tokens': 1000, 'tool_uses': 5},
                '2-refine': {'total_tokens': 2000, 'tool_uses': 7},
            },
        )
        lines = _render_breakdown('render-rule-03')
        total_line = next(ln for ln in lines if '**Total**' in ln)
        # 2 contributing phases out of the canonical six → partial marker (n=2/6).
        assert '3,000 (n=2/6)' in total_line  # tokens total
        assert '12 (n=2/6)' in total_line  # tool_uses total

    def test_worked_cell_uses_max_of_agent_and_subagent_duration(self, plan_context):
        """Worked cell = max(agent_duration_ms, subagent_duration_ms) via format_duration.

        Non-double-counting attribution: the longer span subsumes the shorter
        overlap so the Worked <= wall invariant holds. Prior additive formula
        (120 + 60 = 180s) would have rendered '3m0s'; the corrected max(...)
        form renders the longer single-source span (120s = '2m0s').
        """
        _seed_phases(
            'render-rule-04',
            {
                '1-init': {'agent_duration_ms': 120000, 'subagent_duration_ms': 60000},
            },
        )
        lines = _render_breakdown('render-rule-04')
        init_line = next(ln for ln in lines if '1-init' in ln)
        # worked = max(120000, 60000) ms = 120 s = '2m0s'; no '(agent)' marker.
        assert '2m0s' in init_line, init_line
        assert '3m0s' not in init_line, init_line  # guard against regression to sum
        assert '(agent)' not in init_line, init_line

    def test_reported_wall_column_renders_wall_clock(self, plan_context):
        """The Reported (wall) column renders duration_seconds independent of worked."""
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

    def test_total_marker_with_partial_worked_contribution(self, plan_context):
        """Total Worked respects the partial-Total marker when only some phases worked."""
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
        # Two of the canonical six phases contribute worked time; the completeness
        # denominator is the canonical six, not the present-row count → marker '(n=2/6)'.
        assert '(n=2/6)' in total_line, total_line


class TestEndToEndPhaseBreakdownRendering:
    """End-to-end regression: metrics.toon → generate → print-phase-breakdown.

    Exercises the producer→consumer contract that the phase-6-finalize Phase
    Breakdown override path depends on — distinct from the cmd_generate-only
    unit tests in TestPhaseBreakdownRenderingRule. The captured section is the
    exact content the override renderer inlines into the finalize summary.
    """

    def test_captured_section_carries_three_time_columns_with_idle(self, plan_context):
        """generate → print-phase-breakdown captures Worked/Reported/Idle with the
        worked rollup including subagent_duration_ms and the correct idle residual.
        """
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

        gen_result = cmd_generate(ns_generate('metrics-e2e-01'))
        assert gen_result['status'] == 'success'

        print_result = cmd_print_phase_breakdown(ns_print_phase_breakdown('metrics-e2e-01'))
        assert print_result['status'] == 'success'
        assert print_result['file'] == 'work/phase-breakdown-output.txt'
        from file_ops import get_plan_dir
        section = (get_plan_dir('metrics-e2e-01') / print_result['file']).read_text(encoding='utf-8')

        # The captured section begins with the heading and carries the three
        # time columns in order, followed by the two work measures and the
        # derived-cost column.
        assert section.startswith('## Phase Breakdown')
        header = next(ln for ln in section.splitlines() if ln.startswith('| Phase'))
        cols = [c.strip() for c in header.strip('|').split('|')]
        assert cols == [
            'Phase',
            'Worked',
            'Reported (wall)',
            'Idle',
            'Tokens (dispatched unless marked)',
            'Tool Uses',
            'Billing (cost)',
        ]

        # 5-execute worked = max(agent 200s, subagent 100s) = 200000 ms = '3m20s'.
        # The longer attribution span (agent_duration_ms) subsumes the shorter
        # subagent overlap rather than being summed with it.
        exec_line = next(ln for ln in section.splitlines() if ln.startswith('| 5-execute'))
        exec_cells = [c.strip() for c in exec_line.strip('|').split('|')]
        assert exec_cells[1] == '3m20s'  # Worked = max(200s, 100s) = 200s
        assert exec_cells[2] == '10m0s'  # Reported (wall) = 600 s
        # idle = max(0, 600 - 200) = 400 s = '6m40s'.
        assert exec_cells[3] == '6m40s'  # Idle

    def test_captured_section_idle_zero_clamp_safety_net(self, plan_context):
        """The Idle zero-clamp safety net still fires when a single attribution
        source exceeds the wall span (e.g., out-of-window subagent attribution
        artefact). Under the corrected max(...) Worked formula this is a rare
        path — both attribution spans must individually stay within the phase
        window — but the clamp remains in place defensively.
        """
        write_metrics(
            'metrics-e2e-02',
            {
                'phases': {
                    # subagent attribution (180s) artefactually exceeds the
                    # recorded wall span (120s). With Worked = max(...) = 180s,
                    # Idle = max(0, 120 - 180) = 0 → renders '-'.
                    '5-execute': {
                        'start_time': '2026-05-22T10:00:00+00:00',
                        'end_time': '2026-05-22T10:02:00+00:00',
                        'duration_seconds': 120,
                        'agent_duration_ms': 100000,
                        'subagent_duration_ms': 180000,
                    },
                },
            },
        )

        assert cmd_generate(ns_generate('metrics-e2e-02'))['status'] == 'success'
        print_result = cmd_print_phase_breakdown(ns_print_phase_breakdown('metrics-e2e-02'))
        assert print_result['status'] == 'success'
        from file_ops import get_plan_dir
        section = (get_plan_dir('metrics-e2e-02') / print_result['file']).read_text(encoding='utf-8')

        exec_line = next(ln for ln in section.splitlines() if ln.startswith('| 5-execute'))
        exec_cells = [c.strip() for c in exec_line.strip('|').split('|')]
        assert exec_cells[1] == '3m0s'  # Worked = max(100s, 180s) = 180 s
        assert exec_cells[2] == '2m0s'  # Reported (wall) = 120 s
        # idle = max(0, 120 - 180) = 0 → renders the zero-clamped cell '-'.
        assert exec_cells[3] == '-'  # Idle clamped to zero → absent per-cell

    def test_captured_section_total_row_sums_three_time_columns(self, plan_context):
        """The captured Total row sums Worked, Reported (wall), and Idle independently
        across multiple phases — the producer→consumer contract for the override path.
        """
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

        assert cmd_generate(ns_generate('metrics-e2e-03'))['status'] == 'success'
        print_result = cmd_print_phase_breakdown(ns_print_phase_breakdown('metrics-e2e-03'))
        assert print_result['status'] == 'success'
        from file_ops import get_plan_dir
        section = (get_plan_dir('metrics-e2e-03') / print_result['file']).read_text(encoding='utf-8')

        total_line = next(ln for ln in section.splitlines() if '**Total**' in ln)
        total_cells = [c.strip() for c in total_line.strip('|').split('|')]
        # Per-phase worked with max(...):
        #   1-init:    max(120s, 0)    = 120s
        #   5-execute: max(240s, 120s) = 240s
        # worked total = 120 + 240 = 360 s = '6m0s';
        # wall total   = 180 + 600 = 780 s = '13m0s';
        # idle total   = (180-120) + (600-240) = 60 + 360 = 420 s = '7m0s'.
        # Only two of the canonical six phases are present, so the completeness
        # denominator is six → every time-column Total carries the (n=2/6) marker.
        assert total_cells[1] == '**6m0s (n=2/6)**'   # Worked
        assert total_cells[2] == '**13m0s (n=2/6)**'  # Reported (wall)
        assert total_cells[3] == '**7m0s (n=2/6)**'   # Idle
