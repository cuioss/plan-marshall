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
import json
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
_cmd_sync_defaults = _load_module('_cmd_sync_defaults_for_retention_test', '_cmd_sync_defaults.py')

cmd_system = _cmd_system_plan.cmd_system
cmd_sync_defaults = _cmd_sync_defaults.cmd_sync_defaults
validate_plugin_cache_retention = _config_defaults.validate_plugin_cache_retention

_VERSIONS_FIELD = 'plugin_cache_keep_versions'
_DAYS_FIELD = 'plugin_cache_keep_days'
_NO_PLAN_BODY_FIELD = 'no_plan_body_days'
_BUILD_RESULTS_FIELD = 'build_results_days'


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


# =============================================================================
# no_plan_body_days (NO_PLAN sentinel body retention)
# =============================================================================


def test_no_plan_body_days_is_seeded_with_documented_default():
    """`get_default_config()` seeds the sentinel-body knob at the documented 7."""
    retention = _config_defaults.get_default_config()['system']['retention']

    assert retention[_NO_PLAN_BODY_FIELD] == 7


def test_no_plan_body_days_outlives_its_retention_siblings():
    """The sentinel is never archived, so its bodies must outlive both the log
    window and a real plan's archived window — otherwise a body could be reaped
    mid-operation, or sooner than the plan-bound equivalent it stands in for."""
    retention = _config_defaults.get_default_config()['system']['retention']

    assert retention[_NO_PLAN_BODY_FIELD] > retention['logs_days']
    assert retention[_NO_PLAN_BODY_FIELD] >= retention['archived_plans_days']


def test_retention_set_accepts_no_plan_body_days(plan_context):
    """The knob joins the fail-closed whitelist, so the operator can set it."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(
        Namespace(sub_noun='retention', verb='set', field=_NO_PLAN_BODY_FIELD, value='14')
    )

    assert result['status'] == 'success'
    assert result['value'] == 14
    verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
    assert verify['retention'][_NO_PLAN_BODY_FIELD] == 14


def test_sync_defaults_backfills_no_plan_body_days(plan_context):
    """A marshal.json written BEFORE the knob existed acquires it on sync.

    This is the documented migration path for existing projects: the knob is not
    seeded retroactively by an upgrade, it arrives through `sync-defaults`'
    non-destructive deep-merge. The pre-knob retention block below is the exact
    shape those projects carry, and every one of its user-set values must survive
    the merge untouched.
    """
    pre_knob_retention = {
        'logs_days': 3,
        'archived_plans_days': 5,
        'lessons_superseded_days': 0,
        'temp_on_maintenance': True,
        'plugin_cache_keep_versions': 5,
        'plugin_cache_keep_days': 3,
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(
        json.dumps({'system': {'retention': dict(pre_knob_retention)}}, indent=2),
        encoding='utf-8',
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    merged = json.loads(marshal_path.read_text(encoding='utf-8'))['system']['retention']

    assert merged[_NO_PLAN_BODY_FIELD] == 7, 'the missing knob must be back-filled at its default'
    assert any(path.endswith(_NO_PLAN_BODY_FIELD) for path in result['added']), (
        f'sync-defaults must report the added knob; added={result["added"]}'
    )
    # Non-destructive: the operator's pre-existing values are preserved verbatim.
    for field, value in pre_knob_retention.items():
        assert merged[field] == value, f'sync-defaults must not overwrite {field}'


# =============================================================================
# build_results_days (per-plan build-output retention)
# =============================================================================


def test_build_results_days_is_seeded_equal_to_archived_plans_days():
    """The knob is seeded, and seeded EQUAL to `archived_plans_days`.

    A build's output belongs to the plan that caused it, so the two defaults are
    declared from ONE value rather than two literals. Asserting the equality —
    rather than the number — is what keeps them from drifting: a future change
    to `archived_plans_days` alone fails here instead of silently leaving build
    results governed by a stale window.
    """
    retention = _config_defaults.get_default_config()['system']['retention']

    assert _BUILD_RESULTS_FIELD in retention
    assert retention[_BUILD_RESULTS_FIELD] == retention['archived_plans_days']


def test_retention_set_accepts_build_results_days(plan_context):
    """The knob joins the fail-closed whitelist, so the operator can set it."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(
        Namespace(sub_noun='retention', verb='set', field=_BUILD_RESULTS_FIELD, value='21')
    )

    assert result['status'] == 'success'
    assert result['value'] == 21
    verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
    assert verify['retention'][_BUILD_RESULTS_FIELD] == 21


def test_sync_defaults_backfills_build_results_days(plan_context):
    """A marshal.json written BEFORE the knob existed acquires it on sync.

    Same migration path the sentinel-body knob takes: the value arrives through
    `sync-defaults`' non-destructive deep-merge, and every user-set value in the
    pre-knob block survives it untouched.
    """
    pre_knob_retention = {
        'logs_days': 3,
        'archived_plans_days': 5,
        'lessons_superseded_days': 0,
        'no_plan_body_days': 7,
        'temp_on_maintenance': True,
        'plugin_cache_keep_versions': 5,
        'plugin_cache_keep_days': 3,
    }
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(
        json.dumps({'system': {'retention': dict(pre_knob_retention)}}, indent=2),
        encoding='utf-8',
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    merged = json.loads(marshal_path.read_text(encoding='utf-8'))['system']['retention']

    assert merged[_BUILD_RESULTS_FIELD] == 5, 'the missing knob must be back-filled at its default'
    assert any(path.endswith(_BUILD_RESULTS_FIELD) for path in result['added']), (
        f'sync-defaults must report the added knob; added={result["added"]}'
    )
    for field, value in pre_knob_retention.items():
        assert merged[field] == value, f'sync-defaults must not overwrite {field}'
