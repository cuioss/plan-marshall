#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-plan-documents.py``.

In-scope flags from TASK-1: ``--plan-id``.

The script's CLI shape is ``<doc-type> <verb>`` (e.g. ``request read``).
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
    'plan-marshall', 'manage-plan-documents', 'manage-plan-documents.py'
)


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_request_read_rejects_invalid_plan_id(axis, bad_value):
    """``manage-plan-documents request read --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'request', 'read', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


def test_request_read_accepts_canonical_plan_id():
    result = run_script(
        SCRIPT_PATH, 'request', 'read', '--plan-id', HAPPY_VALUES['plan_id']
    )
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_plan_id'
