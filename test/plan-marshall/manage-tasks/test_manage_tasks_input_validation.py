#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-tasks.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--task-number``, ``--domain``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')


# =============================================================================
# --plan-id (list, read, exists, next, etc.)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_list_rejects_invalid_plan_id(axis, bad_value):
    """``manage-tasks list --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'list', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# --task-number (read, exists, update, remove, finalize-step, etc.)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['task_number'])
def test_read_rejects_invalid_task_number(axis, bad_value):
    """``manage-tasks read --plan-id <ok> --task-number <bad>`` → invalid_task_number TOON."""
    result = run_script(
        SCRIPT_PATH,
        'read',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--task-number',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_task_number')


# =============================================================================
# --domain (tasks-by-domain, update --domain)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['domain'])
def test_tasks_by_domain_rejects_invalid_domain(axis, bad_value):
    """``manage-tasks tasks-by-domain --plan-id <ok> --domain <bad>`` → invalid_domain TOON."""
    result = run_script(
        SCRIPT_PATH,
        'tasks-by-domain',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--domain',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_domain')


def test_list_accepts_canonical_plan_id():
    result = run_script(SCRIPT_PATH, 'list', '--plan-id', HAPPY_VALUES['plan_id'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_plan_id'
