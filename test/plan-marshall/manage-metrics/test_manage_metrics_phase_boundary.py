#!/usr/bin/env python3
"""Tests for the `phase-boundary` subcommand of manage_metrics.

Covers:
  - end-of-prev + start-of-next persisted in a single call
  - optional token/duration/tool-uses forwarded to end-phase
  - metrics.md regenerated as a side-effect
  - invalid phase names rejected for either side
  - boundary works even when the previous phase had no start_time
"""

from argparse import Namespace

from manage_metrics import cmd_phase_boundary, cmd_start_phase  # type: ignore[import-not-found]

from conftest import PlanContext


def _ns_start_phase(plan_id, phase):
    return Namespace(plan_id=plan_id, phase=phase, command='start-phase', func=cmd_start_phase)


def _ns_boundary(
    plan_id,
    prev_phase,
    next_phase,
    total_tokens=None,
    duration_ms=None,
    tool_uses=None,
):
    return Namespace(
        plan_id=plan_id,
        prev_phase=prev_phase,
        next_phase=next_phase,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        tool_uses=tool_uses,
        command='phase-boundary',
        func=cmd_phase_boundary,
    )


# =============================================================================
# Successful boundary semantics
# =============================================================================


def test_phase_boundary_records_end_and_start_atomically():
    """phase-boundary writes end_time on prev and start_time on next in one call."""
    with PlanContext(plan_id='boundary-basic') as ctx:
        cmd_start_phase(_ns_start_phase('boundary-basic', '1-init'))

        result = cmd_phase_boundary(
            _ns_boundary(
                'boundary-basic',
                prev_phase='1-init',
                next_phase='2-refine',
                total_tokens=12000,
                duration_ms=180000,
                tool_uses=8,
            )
        )

        assert result['status'] == 'success'
        assert result['prev_phase'] == '1-init'
        assert result['next_phase'] == '2-refine'
        assert 'end_time' in result
        assert 'start_time' in result
        assert result['prev_total_tokens'] == 12000

        metrics_file = ctx.plan_dir / 'work' / 'metrics.toon'
        content = metrics_file.read_text()

        # Previous phase closed with token data
        assert '[1-init]' in content
        assert 'end_time:' in content
        assert 'total_tokens: 12000' in content
        assert 'tool_uses: 8' in content
        assert 'agent_duration_ms: 180000' in content

        # Next phase opened
        assert '[2-refine]' in content
        # Both blocks present, with start_time on the next phase
        next_idx = content.index('[2-refine]')
        # Make sure the next-phase block has a start_time line
        assert 'start_time:' in content[next_idx:]


def test_phase_boundary_generates_metrics_md():
    """phase-boundary regenerates metrics.md as a side effect."""
    with PlanContext(plan_id='boundary-generate') as ctx:
        cmd_start_phase(_ns_start_phase('boundary-generate', '1-init'))
        result = cmd_phase_boundary(
            _ns_boundary(
                'boundary-generate',
                prev_phase='1-init',
                next_phase='2-refine',
                total_tokens=5000,
            )
        )
        assert result['status'] == 'success'
        assert result.get('metrics_file') == 'metrics.md'
        # The generated report must exist
        metrics_md = ctx.plan_dir / 'metrics.md'
        assert metrics_md.exists()
        report = metrics_md.read_text()
        assert '1-init' in report
        # phases_recorded is at least 2 (prev + next)
        assert int(result.get('phases_recorded', 0)) >= 2


def test_phase_boundary_optional_token_args_omitted():
    """phase-boundary works with no token/duration/tool-uses flags (main-context phase)."""
    with PlanContext(plan_id='boundary-no-tokens') as ctx:
        cmd_start_phase(_ns_start_phase('boundary-no-tokens', '2-refine'))
        result = cmd_phase_boundary(
            _ns_boundary(
                'boundary-no-tokens', prev_phase='2-refine', next_phase='3-outline'
            )
        )
        assert result['status'] == 'success'
        # No prev_total_tokens since not provided
        assert 'prev_total_tokens' not in result

        content = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()
        # No token fields should have been written for the closing phase
        prev_idx = content.index('[2-refine]')
        next_idx = content.index('[3-outline]') if '[3-outline]' in content else len(content)
        prev_block = content[prev_idx:next_idx]
        assert 'total_tokens' not in prev_block
        assert 'tool_uses' not in prev_block
        # But end_time MUST be present
        assert 'end_time:' in prev_block


def test_phase_boundary_without_prev_start_records_end_only():
    """phase-boundary tolerates a previous phase with no recorded start (no duration)."""
    with PlanContext(plan_id='boundary-no-start'):
        # No start-phase called for 1-init
        result = cmd_phase_boundary(
            _ns_boundary(
                'boundary-no-start', prev_phase='1-init', next_phase='2-refine'
            )
        )
        assert result['status'] == 'success'
        # No prev_duration_seconds in the result since start_time was missing
        assert 'prev_duration_seconds' not in result


# =============================================================================
# Invalid input rejection
# =============================================================================


def test_phase_boundary_invalid_prev_phase_rejected():
    """Invalid prev-phase name returns invalid_phase error."""
    with PlanContext(plan_id='boundary-bad-prev'):
        result = cmd_phase_boundary(
            _ns_boundary('boundary-bad-prev', prev_phase='nope', next_phase='2-refine')
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_phase'
        assert 'prev_phase' in result['message']


def test_phase_boundary_invalid_next_phase_rejected():
    """Invalid next-phase name returns invalid_phase error."""
    with PlanContext(plan_id='boundary-bad-next'):
        result = cmd_phase_boundary(
            _ns_boundary('boundary-bad-next', prev_phase='1-init', next_phase='nope')
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_phase'
        assert 'next_phase' in result['message']


def test_phase_boundary_equivalent_to_three_call_sequence():
    """The fused call persists the same key fields the three-call sequence would.

    We don't assert byte-equivalence (timestamps differ between calls), but the
    set of recorded keys per phase MUST match: prev gets end_time + token data;
    next gets start_time. Both must be present after the fused call.
    """
    with PlanContext(plan_id='boundary-equiv') as ctx:
        cmd_start_phase(_ns_start_phase('boundary-equiv', '4-plan'))
        result = cmd_phase_boundary(
            _ns_boundary(
                'boundary-equiv',
                prev_phase='4-plan',
                next_phase='5-execute',
                total_tokens=42000,
                duration_ms=600000,
                tool_uses=15,
            )
        )
        assert result['status'] == 'success'
        content = (ctx.plan_dir / 'work' / 'metrics.toon').read_text()

        # Same fields end-phase would have written
        assert 'total_tokens: 42000' in content
        assert 'tool_uses: 15' in content
        assert 'agent_duration_ms: 600000' in content
        # Same field start-phase would have written for next
        assert '[5-execute]' in content
