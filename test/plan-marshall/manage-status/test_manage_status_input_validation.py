#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage_status.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--phase``, ``--field``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')


# =============================================================================
# --plan-id
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_read_rejects_invalid_plan_id(axis, bad_value):
    """``manage_status read --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# --phase (set-phase, update-phase, route, mark-step-done)
# =============================================================================


def test_route_rejects_invalid_phase():
    """``manage_status route --phase <bad>`` → invalid_phase TOON."""
    result = run_script(SCRIPT_PATH, 'route', '--phase', 'unknown-phase')
    assert_invalid_field(result, 'invalid_phase')


def test_set_phase_rejects_invalid_phase():
    """``manage_status set-phase --plan-id <ok> --phase <bad>`` → invalid_phase TOON."""
    result = run_script(
        SCRIPT_PATH,
        'set-phase',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        'unknown-phase',
    )
    assert_invalid_field(result, 'invalid_phase')


# =============================================================================
# --field (metadata)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['field'])
def test_metadata_rejects_invalid_field(axis, bad_value):
    """``manage_status metadata --plan-id <ok> --field <bad>`` → invalid_field TOON."""
    result = run_script(
        SCRIPT_PATH,
        'metadata',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--field',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_field')
