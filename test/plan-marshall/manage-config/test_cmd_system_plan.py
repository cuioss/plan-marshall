#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for system commands in manage-config.

Tests system retention commands. Plan phase commands are tested in
test_cmd_quality_phases.py.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import SCRIPT_PATH, create_marshal_json

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


_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_system = _cmd_system_plan.cmd_system
cmd_project = _cmd_system_plan.cmd_project
cmd_plan = _cmd_system_plan.cmd_plan

from conftest import run_script  # noqa: E402

# =============================================================================
# system Command Tests (Tier 2 - direct import)
# =============================================================================


def test_system_retention_get(plan_context, monkeypatch):
    """Test system retention get."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(Namespace(sub_noun='retention', verb='get'))

    assert result['status'] == 'success'
    assert 'retention' in result
    assert result['retention']['logs_days'] == 1


def test_system_retention_set(plan_context, monkeypatch):
    """Test system retention set."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(Namespace(sub_noun='retention', verb='set', field='logs_days', value='7'))

    assert result['status'] == 'success'
    assert result['field'] == 'logs_days'
    assert result['value'] == 7

    # Verify changed via another get
    verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
    assert verify['retention']['logs_days'] == 7


def test_system_retention_set_boolean(plan_context, monkeypatch):
    """Test system retention set with boolean value."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_system(Namespace(sub_noun='retention', verb='set', field='temp_on_maintenance', value='false'))

    assert result['status'] == 'success'
    assert result['value'] is False

    # Verify changed
    verify = cmd_system(Namespace(sub_noun='retention', verb='get'))
    assert verify['retention']['temp_on_maintenance'] is False


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_system_retention_get(plan_context):
    """Test CLI plumbing: system retention get outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'system', 'retention', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'logs_days' in result.stdout


def test_cli_system_retention_set(plan_context):
    """Test CLI plumbing: system retention set outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'system', 'retention', 'set', '--field', 'logs_days', '--value', '7')

    assert result.success, f'Should succeed: {result.stderr}'


# =============================================================================
# Malformed (non-dict) marshal.json block guards (Pattern B2)
# =============================================================================
#
# `config['system']`, `config['system']['retention']`, and `config['project']`
# are read from a hand-editable marshal.json and consumed as dicts (item
# assignment / `.get`). A non-dict value at any of those keys must produce a
# structured `status: error` (error_type='invalid_type') rather than crashing
# with an AttributeError/TypeError — the isinstance-guard contract.


def _marshal_with_block(**block_overrides) -> dict:
    """Return a minimal valid marshal.json config with the named top-level blocks set."""
    config: dict = {
        'skill_domains': {},
        'system': {'retention': {'logs_days': 1}},
        'plan': {},
        'project': {'default_base_branch': 'main'},
        'providers': [],
    }
    config.update(block_overrides)
    return config


def test_system_non_dict_system_block_returns_structured_error(plan_context):
    """A non-dict `config['system']` yields status: error from cmd_system."""
    create_marshal_json(plan_context.fixture_dir, config=_marshal_with_block(system=['not', 'a', 'dict']))

    result = cmd_system(Namespace(sub_noun='retention', verb='get'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_type'
    assert 'system block' in result['error']


def test_system_non_dict_retention_block_set_returns_structured_error(plan_context):
    """A non-dict `config['system']['retention']` yields status: error on the set verb."""
    create_marshal_json(
        plan_context.fixture_dir,
        config=_marshal_with_block(system={'retention': 'totally-wrong'}),
    )

    result = cmd_system(
        Namespace(sub_noun='retention', verb='set', field='logs_days', value='7')
    )

    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_type'
    assert 'retention block' in result['error']


def test_project_non_dict_project_block_get_returns_structured_error(plan_context):
    """A non-dict `config['project']` yields status: error from cmd_project get."""
    create_marshal_json(
        plan_context.fixture_dir,
        config=_marshal_with_block(project=['not', 'a', 'dict']),
    )

    result = cmd_project(Namespace(verb='get', field='default_base_branch'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_type'
    assert 'project block' in result['error']


def test_project_non_dict_project_block_set_returns_structured_error(plan_context):
    """A non-dict `config['project']` yields status: error from cmd_project set."""
    create_marshal_json(
        plan_context.fixture_dir,
        config=_marshal_with_block(project='totally-wrong'),
    )

    result = cmd_project(Namespace(verb='set', field='default_base_branch', value='develop'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'invalid_type'
    assert 'project block' in result['error']


# =============================================================================
# plan phase q_gate_validation validator dispatch (this plan, D2)
# =============================================================================
#
# `cmd_plan` delegates phase-based sub-nouns to `cmd_phase`, which routes the
# planning-time `q_gate_validation` field (off|once|until_clean) on
# phase-3-outline and phase-4-plan through `validate_q_gate_validation` at the
# set boundary. These tests exercise that delegation path end-to-end via
# `cmd_plan`: a valid value round-trips through set→get on both planning phases,
# an absent key surfaces the seeded `once` default on get, and a malformed
# value is rejected before it persists. The retired outline `qgate` run-at-all
# set path has no branch here — it was removed from the outline defaults entirely.


def test_plan_phase_3_outline_q_gate_validation_set_get_roundtrip(plan_context):
    """`plan phase-3-outline set/get --field q_gate_validation` round-trips a valid value."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_plan(
        Namespace(sub_noun='phase-3-outline', verb='set', field='q_gate_validation', value='once')
    )
    assert set_result['status'] == 'success'
    assert set_result['field'] == 'q_gate_validation'
    assert set_result['value'] == 'once'

    get_result = cmd_plan(
        Namespace(sub_noun='phase-3-outline', verb='get', field='q_gate_validation')
    )
    assert get_result['status'] == 'success'
    assert get_result['value'] == 'once'


def test_plan_phase_4_plan_q_gate_validation_set_get_roundtrip(plan_context):
    """`plan phase-4-plan set/get --field q_gate_validation` round-trips a valid value."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_plan(
        Namespace(sub_noun='phase-4-plan', verb='set', field='q_gate_validation', value='off')
    )
    assert set_result['status'] == 'success'
    assert set_result['value'] == 'off'

    get_result = cmd_plan(
        Namespace(sub_noun='phase-4-plan', verb='get', field='q_gate_validation')
    )
    assert get_result['status'] == 'success'
    assert get_result['value'] == 'off'


def test_plan_q_gate_validation_get_returns_once_default(plan_context):
    """A fresh config lacking q_gate_validation surfaces the seeded 'once' default via get."""
    create_marshal_json(plan_context.fixture_dir)

    get_result = cmd_plan(
        Namespace(sub_noun='phase-4-plan', verb='get', field='q_gate_validation')
    )

    assert get_result['status'] == 'success'
    assert get_result['value'] == 'once'


def test_plan_q_gate_validation_set_rejects_invalid_value(plan_context):
    """A malformed q_gate_validation value is rejected at the set boundary, naming the field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(sub_noun='phase-3-outline', verb='set', field='q_gate_validation', value='sometimes')
    )

    assert result['status'] == 'error'
    # the validator error message names the offending dotted field path
    assert 'q_gate_validation' in result['error']


# =============================================================================
# project set field-name whitelist (this plan, D1)
# =============================================================================
#
# `cmd_project`'s set branch rejects any field not in DEFAULT_PROJECT with
# error_type='unknown_field' before persisting, making set symmetric with the
# get branch's field_not_found handling. A typo'd or retired key (e.g. a dead
# lane knob like use_merge_queue) is rejected rather than silently written to
# marshal.json where no reader would ever consult it. The four known
# DEFAULT_PROJECT fields must still set successfully.


def test_project_set_rejects_unknown_field(plan_context):
    """`project set --field use_merge_queue` is rejected with error_type='unknown_field'."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_project(Namespace(verb='set', field='use_merge_queue', value='true'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'unknown_field'
    assert 'use_merge_queue' in result['error']


def test_project_set_unknown_field_not_persisted(plan_context):
    """A rejected unknown field is never written to marshal.json — a follow-up get is field_not_found."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_project(Namespace(verb='set', field='use_merge_queue', value='true'))
    assert set_result['status'] == 'error'

    # The dead key must not have been persisted: get resolves neither the stored
    # project config nor DEFAULT_PROJECT, so it surfaces field_not_found.
    get_result = cmd_project(Namespace(verb='get', field='use_merge_queue'))
    assert get_result['status'] == 'error'
    assert get_result['error_type'] == 'field_not_found'


def test_project_set_default_base_branch_succeeds(plan_context):
    """The known `default_base_branch` field still sets and round-trips."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_project(Namespace(verb='set', field='default_base_branch', value='develop'))
    assert set_result['status'] == 'success'
    assert set_result['value'] == 'develop'

    get_result = cmd_project(Namespace(verb='get', field='default_base_branch'))
    assert get_result['status'] == 'success'
    assert get_result['value'] == 'develop'


def test_project_set_working_prefixes_succeeds(plan_context):
    """The known list-valued `working_prefixes` field still sets and round-trips."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_project(
        Namespace(verb='set', field='working_prefixes', value='["feature/", "fix/"]')
    )
    assert set_result['status'] == 'success'
    assert set_result['value'] == ['feature/', 'fix/']

    get_result = cmd_project(Namespace(verb='get', field='working_prefixes'))
    assert get_result['status'] == 'success'
    assert get_result['value'] == ['feature/', 'fix/']


def test_project_set_pr_strategy_succeeds(plan_context):
    """The known `pr_strategy` field still sets and round-trips."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_project(Namespace(verb='set', field='pr_strategy', value='distinct'))
    assert set_result['status'] == 'success'
    assert set_result['value'] == 'distinct'

    get_result = cmd_project(Namespace(verb='get', field='pr_strategy'))
    assert get_result['status'] == 'success'
    assert get_result['value'] == 'distinct'


def test_project_set_pr_compact_max_changed_files_succeeds(plan_context):
    """The known `pr_compact_max_changed_files` field still sets and round-trips."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_project(
        Namespace(verb='set', field='pr_compact_max_changed_files', value='200')
    )
    assert set_result['status'] == 'success'
    assert set_result['value'] == 200

    get_result = cmd_project(Namespace(verb='get', field='pr_compact_max_changed_files'))
    assert get_result['status'] == 'success'
    assert get_result['value'] == 200


# =============================================================================
# Main
# =============================================================================
