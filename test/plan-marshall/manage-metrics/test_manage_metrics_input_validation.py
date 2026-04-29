#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage_metrics.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--phase``, ``--session-id``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage_metrics.py')


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
