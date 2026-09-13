#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""6-axis identifier-validation rejection-path tests for ``manage-plan-documents.py``.

In-scope flags from TASK-1: ``--plan-id``.

The script's CLI shape is ``<doc-type> <verb>`` (e.g. ``request read``).
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_plan_id_axis_rejected,
)

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-plan-documents', 'manage-plan-documents.py')

# ⛔ Vacuity guard — the axis populations are imported, so an emptied one collects
# zero cases at the parametrize sites below and still reports green.
assert MALFORMED_AXES['plan_id'], 'MALFORMED_AXES["plan_id"] is empty'


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_request_read_rejects_invalid_plan_id(axis, bad_value):
    """``manage-plan-documents request read --plan-id <bad>`` → invalid_plan_id TOON."""
    assert_plan_id_axis_rejected(SCRIPT_PATH, ('request', 'read'), bad_value)


def test_request_read_accepts_canonical_plan_id():
    result = run_script(SCRIPT_PATH, 'request', 'read', '--plan-id', HAPPY_VALUES['plan_id'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_plan_id'
