#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-lessons.py``.

In-scope flags from TASK-1: ``--component``, ``--lesson-id``, ``--plan-id``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-lessons', 'manage-lessons.py')


# =============================================================================
# --component (add, list)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['component'])
def test_add_rejects_invalid_component(axis, bad_value):
    """``manage-lessons add --component <bad> ...`` → invalid_component TOON."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--component',
        bad_value,
        '--category',
        'improvement',
        '--title',
        'A',
    )
    assert_invalid_field(result, 'invalid_component')


# =============================================================================
# --lesson-id (get, update, set-body, remove, supersede, convert)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['lesson_id'])
def test_get_rejects_invalid_lesson_id(axis, bad_value):
    """``manage-lessons get --lesson-id <bad>`` → invalid_lesson_id TOON."""
    result = run_script(SCRIPT_PATH, 'get', '--lesson-id', bad_value)
    assert_invalid_field(result, 'invalid_lesson_id')


# =============================================================================
# --plan-id (convert)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_convert_to_plan_rejects_invalid_plan_id(axis, bad_value):
    """``manage-lessons convert-to-plan --lesson-id <ok> --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(
        SCRIPT_PATH,
        'convert-to-plan',
        '--lesson-id',
        HAPPY_VALUES['lesson_id'],
        '--plan-id',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_plan_id')


def test_get_accepts_canonical_lesson_id():
    result = run_script(SCRIPT_PATH, 'get', '--lesson-id', HAPPY_VALUES['lesson_id'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_lesson_id'
