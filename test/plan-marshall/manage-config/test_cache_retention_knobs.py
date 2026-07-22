#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `system.retention` plugin-cache retention knobs.

`plugin_cache_keep_versions` (N) and `plugin_cache_keep_days` (D) are seeded
into `DEFAULT_SYSTEM_RETENTION`, which is simultaneously the fail-closed field
whitelist `reject_unknown_provisioning_field` enforces on
`manage-config system retention set`. These tests cover the config half of the
union-keep retention sweep: the seeded defaults, the operator set path (accepted
keys plus a rejected typo'd neighbour), and the numeric contract enforced by
`validate_plugin_cache_retention`.

Tier 2 (direct import) tests.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import create_marshal_json

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults = _load_module('_config_defaults', '_config_defaults.py')
_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_system = _cmd_system_plan.cmd_system
validate_plugin_cache_retention = _config_defaults.validate_plugin_cache_retention

_VERSIONS_FIELD = 'plugin_cache_keep_versions'
_DAYS_FIELD = 'plugin_cache_keep_days'


# =============================================================================
# Seeded defaults
# =============================================================================


def test_both_knobs_are_seeded_with_documented_defaults():
    """`get_default_config()` seeds both knobs into `system.retention` at 5 / 3."""
    retention = _config_defaults.get_default_config()['system']['retention']

    assert retention[_VERSIONS_FIELD] == 5
    assert retention[_DAYS_FIELD] == 3


def test_knobs_join_the_existing_retention_siblings():
    """The knobs live alongside the four pre-existing retention keys rather than
    in a new config block."""
    retention = _config_defaults.get_default_config()['system']['retention']

    assert {
        'logs_days',
        'archived_plans_days',
        'lessons_superseded_days',
        'temp_on_maintenance',
        _VERSIONS_FIELD,
        _DAYS_FIELD,
    } <= set(retention)


# =============================================================================
# Operator set path (whitelist + numeric contract)
# =============================================================================


@pytest.mark.parametrize(('field', 'value', 'expected'), [(_VERSIONS_FIELD, '9', 9), (_DAYS_FIELD, '0', 0)])
def test_retention_set_accepts_both_knobs(plan_context, field: str, value: str, expected: int):
    """`system retention set` accepts both knobs and round-trips through get."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(Namespace(sub_noun='retention', verb='set', field=field, value=value))

    assert result['status'] == 'success'
    assert result['value'] == expected
    verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
    assert verify['retention'][field] == expected


def test_retention_set_rejects_a_typod_neighbour(plan_context):
    """A near-miss key is rejected by the fail-closed whitelist rather than
    silently persisted where no reader would consult it."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(
        Namespace(sub_noun='retention', verb='set', field='plugin_cache_keep_version', value='5')
    )

    assert result['status'] == 'error'
    verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
    assert 'plugin_cache_keep_version' not in verify['retention']


@pytest.mark.parametrize(('field', 'value'), [(_VERSIONS_FIELD, '0'), (_DAYS_FIELD, '-1')])
def test_retention_set_rejects_out_of_contract_values(plan_context, field: str, value: str):
    """An out-of-contract numeric value returns status: error rather than
    persisting a keep-set the sweep cannot honour."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(Namespace(sub_noun='retention', verb='set', field=field, value=value))

    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_value'


# =============================================================================
# validate_plugin_cache_retention
# =============================================================================


@pytest.mark.parametrize('field', [_VERSIONS_FIELD, _DAYS_FIELD])
@pytest.mark.parametrize('value', [True, False, 'five', 1.5, None])
def test_validator_rejects_bool_and_non_int(field: str, value: object):
    """Booleans are rejected even though `bool` is an `int` subclass, and so is
    every non-int value."""
    with pytest.raises(ValueError):
        validate_plugin_cache_retention(value, f'system.retention.{field}')


def test_validator_rejects_zero_keep_versions():
    """Keeping zero versions would empty the cache the sweep prunes."""
    with pytest.raises(ValueError):
        validate_plugin_cache_retention(0, f'system.retention.{_VERSIONS_FIELD}')


def test_validator_rejects_negative_keep_days():
    """A negative age window is meaningless."""
    with pytest.raises(ValueError):
        validate_plugin_cache_retention(-1, f'system.retention.{_DAYS_FIELD}')


def test_validator_accepts_the_floor_values():
    """`keep_versions == 1` and `keep_days == 0` are the accepted floors —
    zero days disables the age arm of the union, not the union."""
    validate_plugin_cache_retention(1, f'system.retention.{_VERSIONS_FIELD}')
    validate_plugin_cache_retention(0, f'system.retention.{_DAYS_FIELD}')


def test_validator_error_names_the_offending_knob():
    """The rejection message names the dotted field path so the operator knows
    which knob failed."""
    with pytest.raises(ValueError, match='system.retention.plugin_cache_keep_versions'):
        validate_plugin_cache_retention(0, f'system.retention.{_VERSIONS_FIELD}')
