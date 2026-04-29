#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-files.py``.

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

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-files', 'manage-files.py')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_list_rejects_invalid_plan_id(axis, bad_value):
    """``manage-files list --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'list', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_exists_rejects_invalid_plan_id(axis, bad_value):
    """``manage-files exists --plan-id <bad> --file <f>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'exists', '--plan-id', bad_value, '--file', 'foo.md')
    assert_invalid_field(result, 'invalid_plan_id')


def test_list_accepts_canonical_plan_id():
    """Canonical ``--plan-id`` passes validator."""
    result = run_script(SCRIPT_PATH, 'list', '--plan-id', HAPPY_VALUES['plan_id'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_plan_id'
