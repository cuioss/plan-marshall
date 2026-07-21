#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis identifier-validation rejection-path tests for ``manage-logging.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--phase``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
    assert_plan_id_axis_rejected,
)

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-logging', 'manage-logging.py')


# =============================================================================
# --plan-id (work / decision / script / separator / read)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_work_rejects_invalid_plan_id(axis, bad_value):
    """``manage-logging work --plan-id <bad> --level INFO --message m`` → invalid_plan_id TOON."""
    assert_plan_id_axis_rejected(
        SCRIPT_PATH, 'work', bad_value, extra_args=('--level', 'INFO', '--message', 'msg')
    )


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_read_rejects_invalid_plan_id(axis, bad_value):
    """``manage-logging read --plan-id <bad> --type work`` → invalid_plan_id TOON."""
    assert_plan_id_axis_rejected(SCRIPT_PATH, 'read', bad_value, extra_args=('--type', 'work'))


# =============================================================================
# --phase (read --phase)
# =============================================================================


def test_read_rejects_invalid_phase():
    """``manage-logging read --plan-id <ok> --type work --phase <bad>`` → invalid_phase TOON."""
    result = run_script(
        SCRIPT_PATH,
        'read',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--type',
        'work',
        '--phase',
        'unknown-phase',
    )
    assert_invalid_field(result, 'invalid_phase')
