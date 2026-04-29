#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for
``manage-execution-manifest.py``.

In-scope flags from TASK-1: ``--plan-id``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py'
)


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_read_rejects_invalid_plan_id(axis, bad_value):
    """``manage-execution-manifest read --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


def test_read_accepts_canonical_plan_id():
    """Canonical ``--plan-id`` passes validator (downstream may still error
    with plan_not_found, etc.)."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', HAPPY_VALUES['plan_id'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_plan_id'
