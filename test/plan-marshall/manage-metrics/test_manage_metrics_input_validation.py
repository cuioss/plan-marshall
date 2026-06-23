#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis identifier-validation rejection-path tests for ``manage-metrics.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--phase``, ``--session-id``.
"""

from __future__ import annotations

import pytest
from _pm_input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')


# =============================================================================
# --plan-id (start-phase, end-phase, generate, phase-boundary, accumulate-agent-usage, enrich)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_generate_rejects_invalid_plan_id(axis, bad_value):
    """``manage_metrics generate --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'generate', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# --phase (start-phase, end-phase, accumulate-agent-usage)
# =============================================================================


def test_start_phase_rejects_invalid_phase():
    """``manage_metrics start-phase --plan-id <ok> --phase <bad>`` → invalid_phase TOON."""
    result = run_script(
        SCRIPT_PATH,
        'start-phase',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        'unknown-phase',
    )
    assert_invalid_field(result, 'invalid_phase')


# =============================================================================
# --session-id (enrich)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['session_id'])
def test_enrich_rejects_invalid_session_id(axis, bad_value):
    """``manage_metrics enrich --plan-id <ok> --session-id <bad>`` → invalid_session_id TOON."""
    result = run_script(
        SCRIPT_PATH,
        'enrich',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--session-id',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_session_id')


# =============================================================================
# --termination-cause (record-dispatch-boundary)
#
# Lesson 2026-05-10-15-001: the recorder migrated from the overloaded
# `unknown` fallback to the canonical `clean_exit_queue_empty` success-path
# value. The legacy literal `unknown` is now rejected schema-wide via the
# argparse ``choices=`` list; the canonical value is accepted.
# =============================================================================


def test_record_dispatch_boundary_rejects_legacy_unknown_termination_cause():
    """``--termination-cause unknown`` is rejected at argparse — no fallback."""
    result = run_script(
        SCRIPT_PATH,
        'record-dispatch-boundary',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        '5-execute',
        '--termination-cause',
        'unknown',
    )
    assert result.returncode != 0, 'argparse MUST reject the legacy `unknown` value'
    # argparse error messages enumerate the accepted set on stderr.
    combined = (result.stdout or '') + (result.stderr or '')
    assert 'clean_exit_queue_empty' in combined
    assert 'unknown' not in (
        combined.split('choose from')[1] if 'choose from' in combined else ''
    ) or 'invalid choice' in combined


def test_record_dispatch_boundary_accepts_clean_exit_queue_empty():
    """``--termination-cause clean_exit_queue_empty`` is accepted at argparse."""
    result = run_script(
        SCRIPT_PATH,
        'record-dispatch-boundary',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        '5-execute',
        '--termination-cause',
        'clean_exit_queue_empty',
    )
    # Accepted by argparse; the call may still surface a plan-not-found or
    # similar runtime error, but the parser-level rejection MUST NOT fire.
    combined = (result.stdout or '') + (result.stderr or '')
    assert 'invalid choice' not in combined
    assert "argument --termination-cause" not in combined or 'choose from' not in combined
