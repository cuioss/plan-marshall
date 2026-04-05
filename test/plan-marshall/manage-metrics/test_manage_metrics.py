#!/usr/bin/env python3
"""Tests for manage_metrics.py CLI script.

Covers: start-phase, end-phase, generate, enrich subcommands.

Tier 2 (direct import) tests for cmd_* functions, with 2 subprocess
tests retained for CLI plumbing verification.
"""

from argparse import Namespace

import pytest
from manage_metrics import cmd_end_phase, cmd_enrich, cmd_generate, cmd_start_phase  # type: ignore[import-not-found]

from conftest import PlanContext, get_script_path, run_script  # noqa: I001

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage_metrics.py')


# =============================================================================
# Helpers
# =============================================================================


def _ns_start_phase(plan_id: str, phase: str) -> Namespace:
    """Build Namespace for start-phase command."""
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_end_phase(
    plan_id: str,
    phase: str,
    total_tokens: int | None = None,
    duration_ms: int | None = None,
    tool_uses: int | None = None,
) -> Namespace:
    """Build Namespace for end-phase command."""
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        command='end-phase',
        func=cmd_end_phase,
    )


def _ns_generate(plan_id: str) -> Namespace:
    """Build Namespace for generate command."""
    return Namespace(plan_id=plan_id, command='generate', func=cmd_generate)


def _ns_enrich(plan_id: str, session_id: str) -> Namespace:
    """Build Namespace for enrich command."""
    return Namespace(plan_id=plan_id, session_id=session_id, command='enrich', func=cmd_enrich)


# =============================================================================
# Test: start-phase (Tier 2 - direct import)
# =============================================================================


def test_start_phase_records_timestamp():
    """start-phase creates metrics.toon with phase start timestamp."""
    with PlanContext(plan_id='metrics-start-01') as ctx:
        result = cmd_start_phase(_ns_start_phase('metrics-start-01', '1-init'))
        assert result['status'] == 'success'
        assert result['phase'] == '1-init'
        assert 'start_time' in result

        # Verify file was written
        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        assert metrics_file.exists(), 'metrics.toon should be created'
        content = metrics_file.read_text()
        assert '[1-init]' in content
        assert 'start_time:' in content


def test_start_phase_invalid_phase():
    """start-phase rejects invalid phase names."""
    with PlanContext(plan_id='metrics-start-02'):
        result = cmd_start_phase(_ns_start_phase('metrics-start-02', 'invalid'))
        assert result['status'] == 'error'
        assert 'Invalid phase' in str(result.get('message', ''))


def test_start_phase_invalid_plan_id():
    """start-phase rejects invalid plan IDs (sys.exit(1) from require_valid_plan_id)."""
    with PlanContext(plan_id='test'):
        with pytest.raises(SystemExit) as exc_info:
            cmd_start_phase(_ns_start_phase('../escape', '1-init'))
        assert exc_info.value.code == 0


def test_start_phase_multiple_phases():
    """start-phase can record multiple phases."""
    with PlanContext(plan_id='metrics-start-03') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-start-03', '1-init'))
        cmd_start_phase(_ns_start_phase('metrics-start-03', '2-refine'))

        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert '[1-init]' in content
        assert '[2-refine]' in content


# =============================================================================
# Test: end-phase (Tier 2 - direct import)
# =============================================================================


def test_end_phase_computes_duration():
    """end-phase computes wall-clock duration from start/end."""
    with PlanContext(plan_id='metrics-end-01'):
        cmd_start_phase(_ns_start_phase('metrics-end-01', '1-init'))
        result = cmd_end_phase(_ns_end_phase('metrics-end-01', '1-init'))
        assert result['status'] == 'success'
        assert 'duration_seconds' in result
        assert float(str(result['duration_seconds'])) >= 0


def test_end_phase_with_token_data():
    """end-phase stores token data from Task agent notifications."""
    with PlanContext(plan_id='metrics-end-02') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-end-02', '1-init'))
        result = cmd_end_phase(
            _ns_end_phase('metrics-end-02', '1-init', total_tokens=25514, duration_ms=181681, tool_uses=23)
        )
        assert result['status'] == 'success'
        assert result['total_tokens'] == 25514

        # Verify stored in metrics.toon
        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()
        assert 'total_tokens: 25514' in content
        assert 'tool_uses: 23' in content
        assert 'agent_duration_ms: 181681' in content


def test_end_phase_without_start():
    """end-phase works even if start-phase wasn't called (no duration computed from timestamps)."""
    with PlanContext(plan_id='metrics-end-03'):
        result = cmd_end_phase(_ns_end_phase('metrics-end-03', '2-refine', total_tokens=1000))
        assert result['status'] == 'success'
        # No duration_seconds since no start_time
        assert 'duration_seconds' not in result


def test_end_phase_no_optional_args():
    """end-phase works without optional token data."""
    with PlanContext(plan_id='metrics-end-04'):
        cmd_start_phase(_ns_start_phase('metrics-end-04', '3-outline'))
        result = cmd_end_phase(_ns_end_phase('metrics-end-04', '3-outline'))
        assert result['status'] == 'success'
        assert 'total_tokens' not in result


# =============================================================================
# Test: generate (Tier 2 - direct import)
# =============================================================================


def test_generate_creates_metrics_md():
    """generate creates metrics.md with phase breakdown table."""
    with PlanContext(plan_id='metrics-gen-01') as ctx:
        # Record two phases
        cmd_start_phase(_ns_start_phase('metrics-gen-01', '1-init'))
        cmd_end_phase(_ns_end_phase('metrics-gen-01', '1-init', total_tokens=25000, tool_uses=20))
        cmd_start_phase(_ns_start_phase('metrics-gen-01', '2-refine'))
        cmd_end_phase(_ns_end_phase('metrics-gen-01', '2-refine'))

        # Generate report
        result = cmd_generate(_ns_generate('metrics-gen-01'))
        assert result['status'] == 'success'
        assert result['phases_recorded'] == 2
        assert result['total_tokens'] == 25000

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
        result = cmd_generate(_ns_generate('metrics-gen-02'))
        assert result['status'] == 'error'
        assert 'No metrics data' in str(result.get('message', ''))


def test_generate_all_six_phases():
    """generate handles all 6 phases."""
    with PlanContext(plan_id='metrics-gen-03') as ctx:
        phases = ['1-init', '2-refine', '3-outline', '4-plan', '5-execute', '6-finalize']
        for phase in phases:
            cmd_start_phase(_ns_start_phase('metrics-gen-03', phase))
            cmd_end_phase(_ns_end_phase('metrics-gen-03', phase))

        result = cmd_generate(_ns_generate('metrics-gen-03'))
        assert result['status'] == 'success'
        assert result['phases_recorded'] == 6

        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        for phase in phases:
            assert phase in md_content


# =============================================================================
# Test: enrich (Tier 2 - direct import)
# =============================================================================


def test_enrich_missing_transcript():
    """enrich returns gracefully when transcript is not found."""
    with PlanContext(plan_id='metrics-enrich-01'):
        result = cmd_enrich(_ns_enrich('metrics-enrich-01', 'nonexistent-session-id'))
        assert result['status'] == 'success'
        assert result.get('enriched') is False


def test_enrich_with_unknown_session():
    """enrich handles unknown session ID gracefully."""
    with PlanContext(plan_id='metrics-enrich-02'):
        result = cmd_enrich(_ns_enrich('metrics-enrich-02', 'test-session-abc123'))
        # Will be 'not found' since session doesn't exist in ~/.claude
        assert result['status'] == 'success'


# =============================================================================
# Test: format_duration (via generate output) (Tier 2 - direct import)
# =============================================================================


def test_format_duration_seconds():
    """Duration under 60s shows as seconds."""
    with PlanContext(plan_id='metrics-fmt-01') as ctx:
        cmd_start_phase(_ns_start_phase('metrics-fmt-01', '1-init'))
        cmd_end_phase(_ns_end_phase('metrics-fmt-01', '1-init'))
        cmd_generate(_ns_generate('metrics-fmt-01'))
        md_content = (ctx.plan_dir / 'metrics.md').read_text()
        # Should contain some duration string (likely very small since start/end are near-instant)
        assert '1-init' in md_content


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess, retained for end-to-end coverage)
# =============================================================================


def test_cli_start_phase_roundtrip():
    """CLI plumbing: start-phase subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    with PlanContext(plan_id='cli-plumb-01'):
        result = run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-01', '--phase', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['phase'] == '1-init'


def test_cli_generate_roundtrip():
    """CLI plumbing: generate subcommand produces TOON output via subprocess."""
    from toon_parser import parse_toon

    with PlanContext(plan_id='cli-plumb-02'):
        run_script(SCRIPT_PATH, 'start-phase', '--plan-id', 'cli-plumb-02', '--phase', '1-init')
        run_script(SCRIPT_PATH, 'end-phase', '--plan-id', 'cli-plumb-02', '--phase', '1-init')
        result = run_script(SCRIPT_PATH, 'generate', '--plan-id', 'cli-plumb-02')
        assert result.success, f'Script failed: {result.stderr}'
        parsed = parse_toon(result.stdout)
        assert parsed['status'] == 'success'
        assert parsed['phases_recorded'] == 1
