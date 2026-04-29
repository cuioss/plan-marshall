#!/usr/bin/env python3
"""6-axis identifier-validation rejection-path tests for ``manage-findings.py``.

In-scope flags from TASK-1: ``--plan-id``, ``--component``, ``--module``,
``--phase``, ``--hash-id``.
"""

from __future__ import annotations

import pytest
from _input_validation_fixtures import (  # type: ignore[import-not-found]
    HAPPY_VALUES,
    MALFORMED_AXES,
    assert_invalid_field,
)

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-findings', 'manage-findings.py')


# =============================================================================
# --plan-id
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['plan_id'])
def test_query_rejects_invalid_plan_id(axis, bad_value):
    """``manage-findings query --plan-id <bad>`` → invalid_plan_id TOON."""
    result = run_script(SCRIPT_PATH, 'query', '--plan-id', bad_value)
    assert_invalid_field(result, 'invalid_plan_id')


# =============================================================================
# --component (plan-finding add)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['component'])
def test_add_rejects_invalid_component(axis, bad_value):
    """``manage-findings add --plan-id <ok> --component <bad> ...`` → invalid_component TOON."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--component',
        bad_value,
        '--type',
        'sonar',
        '--source',
        'sonar',
        '--title',
        't',
        '--detail',
        'd',
    )
    assert_invalid_field(result, 'invalid_component')


# =============================================================================
# --module
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['module'])
def test_add_rejects_invalid_module(axis, bad_value):
    """``manage-findings add --module <bad> ...`` → invalid_module TOON."""
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--module',
        bad_value,
        '--type',
        'sonar',
        '--source',
        'sonar',
        '--title',
        't',
        '--detail',
        'd',
    )
    assert_invalid_field(result, 'invalid_module')


# =============================================================================
# --hash-id (plan-finding get/resolve/promote, qgate resolve, assessment get)
# =============================================================================


@pytest.mark.parametrize('axis,bad_value', MALFORMED_AXES['hash_id'])
def test_get_rejects_invalid_hash_id(axis, bad_value):
    """``manage-findings get --plan-id <ok> --hash-id <bad>`` → invalid_hash_id TOON."""
    result = run_script(
        SCRIPT_PATH,
        'get',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--hash-id',
        bad_value,
    )
    assert_invalid_field(result, 'invalid_hash_id')


# =============================================================================
# --phase (qgate add/query/resolve/clear)
# =============================================================================


def test_qgate_query_rejects_invalid_phase():
    """``manage-findings qgate query --plan-id <ok> --phase <bad>`` → invalid_phase TOON.

    ``add_phase_arg`` uses argparse ``choices=`` (not a type validator),
    so the canonical message format is "argument --phase: invalid choice".
    """
    result = run_script(
        SCRIPT_PATH,
        'qgate',
        'query',
        '--plan-id',
        HAPPY_VALUES['plan_id'],
        '--phase',
        'unknown-phase',
    )
    assert_invalid_field(result, 'invalid_phase')


def test_query_accepts_canonical_plan_id():
    result = run_script(SCRIPT_PATH, 'query', '--plan-id', HAPPY_VALUES['plan_id'])
    assert result.returncode == 0
    if result.stdout.strip():
        from toon_parser import parse_toon  # type: ignore[import-not-found]

        data = parse_toon(result.stdout)
        assert data.get('error') != 'invalid_plan_id'
