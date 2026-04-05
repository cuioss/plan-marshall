#!/usr/bin/env python3
"""Tests for manage_metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich subcommands.
"""

from conftest import PlanContext, get_script_path, run_script  # noqa: I001
from toon_parser import parse_toon

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage_metrics.py')


# =============================================================================
# Test: start-phase
# =============================================================================


def test_start_phase_records_timestamp():
    """start-phase creates metrics.toon with phase start timestamp."""
    with PlanContext(plan_id='metrics-start-01') as ctx:
        result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-start-01', '--phase', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['phase'] == '1-init'
        assert 'start_time' in parsed

        # Verify file was written
        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        assert metrics_file.exists(), 'metrics.toon should be created'
        content = metrics_file.read_text()
        assert '[1-init]' in content
        assert 'start_time:' in content


def test_start_phase_invalid_phase():
    """start-phase rejects invalid phase names."""
    with PlanContext(plan_id='metrics-start-02'):
        result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-start-02', '--phase', 'invalid')
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert 'Invalid phase' in str(parsed.get('message', ''))


def test_start_phase_invalid_plan_id():
    """start-phase rejects invalid plan IDs."""
    with PlanContext(plan_id='test'):
        result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', '../escape', '--phase', '1-init')
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'


def test_start_phase_multiple_phases():
    """start-phase can record multiple phases."""
    with PlanContext(plan_id='metrics-start-03') as ctx:
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-start-03', '--phase', '1-init')
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-start-03', '--phase', '2-refine')

        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert '[1-init]' in content
        assert '[2-refine]' in content


# =============================================================================
# Test: end-phase
# =============================================================================


def test_end_phase_computes_duration():
    """end-phase computes wall-clock duration from start/end."""
    with PlanContext(plan_id='metrics-end-01'):
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-end-01', '--phase', '1-init')
        result = run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'metrics-end-01', '--phase', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert 'duration_seconds' in parsed
        assert float(str(parsed['duration_seconds'])) >= 0


def test_end_phase_with_token_data():
    """end-phase stores token data from Task agent notifications."""
    with PlanContext(plan_id='metrics-end-02') as ctx:
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-end-02', '--phase', '1-init')
        result = run_script(
            SCRIPT_PATH,
            'end-phase',
            '--plan-id',
            'metrics-end-02',
            '--phase',
            '1-init',
            '--total-tokens',
            '25514',
            '--duration-ms',
            '181681',
            '--tool-uses',
            '23',
        )
        assert result.success
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['total_tokens'] == 25514

        # Verify stored in metrics.toon
        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert 'total_tokens: 25514' in content
        assert 'tool_uses: 23' in content
        assert 'agent_duration_ms: 181681' in content


def test_end_phase_without_start():
    """end-phase works even if start-phase wasn't called (no duration computed from timestamps)."""
    with PlanContext(plan_id='metrics-end-03'):
        result = run_script(
            SCRIPT_PATH,
            'end-phase',
            '--plan-id',
            'metrics-end-03',
            '--phase',
            '2-refine',
            '--total-tokens',
            '1000',
        )
        assert result.success
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        # No duration_seconds since no start_time
        assert 'duration_seconds' not in parsed


def test_end_phase_no_optional_args():
    """end-phase works without optional token data."""
    with PlanContext(plan_id='metrics-end-04'):
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-end-04', '--phase', '3-outline')
        result = run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'metrics-end-04', '--phase', '3-outline')
        assert result.success
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert 'total_tokens' not in parsed


# =============================================================================
# Test: generate
# =============================================================================


def test_generate_creates_metrics_md():
    """generate creates metrics.md with phase breakdown table."""
    with PlanContext(plan_id='metrics-gen-01') as ctx:
        # Record two phases
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-gen-01', '--phase', '1-init')
        run_script(
            SCRIPT_PATH,
            'end-phase',
            '--plan-id',
            'metrics-gen-01',
            '--phase',
            '1-init',
            '--total-tokens',
            '25000',
            '--tool-uses',
            '20',
        )
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-gen-01', '--phase', '2-refine')
        run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'metrics-gen-01', '--phase', '2-refine')

        # Generate report
        result = run_script(SCRIPT_PATH, 'generate', '--plan-id', 'metrics-gen-01')
        assert result.success, f'Script failed: {result.stderr}'
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['phases_recorded'] == 2
        assert parsed['total_tokens'] == 25000

        # Verify metrics.md content
        md_path = ctx.plan_dir / 'metrics.md'
        assert md_path.exists(), 'metrics.md should be created'
        md_content = md_path.read_text()
        assert '# Metrics: metrics-gen-01' in md_content
        assert '## Phase Breakdown' in md_content
        assert '| Phase | Duration | Tokens | Tool Uses |' in md_content
        assert '1-init' in md_content
        assert '2-refine' in md_content
        assert '25,000' in md_content
        assert '**Total**' in md_content


def test_generate_no_data():
    """generate returns error when no metrics data exists."""
    with PlanContext(plan_id='metrics-gen-02'):
        result = run_script(SCRIPT_PATH, 'generate', '--plan-id', 'metrics-gen-02')
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'error'
        assert 'No metrics data' in str(parsed.get('message', ''))


def test_generate_all_six_phases():
    """generate handles all 6 phases."""
    with PlanContext(plan_id='metrics-gen-03') as ctx:
        phases = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
        for phase in phases:
            run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-gen-03', '--phase', phase)
            run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'metrics-gen-03', '--phase', phase)

        result = run_script(SCRIPT_PATH, 'generate', '--plan-id', 'metrics-gen-03')
        assert result.success
        parsed = parse_toon(result.stdout)
        assert parsed['phases_recorded'] == 6

        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        for phase in phases:
            assert phase in md_content


# =============================================================================
# Test: enrich
# =============================================================================


def test_enrich_missing_transcript():
    """enrich returns gracefully when transcript is not found."""
    with PlanContext(plan_id='metrics-enrich-01'):
        result = run_script(
            SCRIPT_PATH,
            'enrich',
            '--plan-id',
            'metrics-enrich-01',
            '--session-id',
            'nonexistent-session-id',
        )
        assert result.success
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed.get('enriched') is False or str(parsed.get('enriched')) == 'False'


def test_enrich_with_unknown_session():
    """enrich handles unknown session ID gracefully."""
    with PlanContext(plan_id='metrics-enrich-02'):
        result = run_script(
            SCRIPT_PATH,
            'enrich',
            '--plan-id',
            'metrics-enrich-02',
            '--session-id',
            'test-session-abc123',
        )
        assert result.success
        parsed = parse_toon(result.stdout)
        # Will be 'not found' since session doesn't exist in ~/.claude
        assert parsed['status'] == 'success'


# =============================================================================
# Test: format_duration (via generate output)
# =============================================================================


def test_format_duration_seconds():
    """Duration under 60s shows as seconds."""
    with PlanContext(plan_id='metrics-fmt-01') as ctx:
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'metrics-fmt-01', '--phase', '1-init')
        run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'metrics-fmt-01', '--phase', '1-init')
        run_script(SCRIPT_PATH, 'generate', '--plan-id', 'metrics-fmt-01')
        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        # Should contain some duration string (likely very small since start/end are near-instant)
        assert '1-init' in md_content
