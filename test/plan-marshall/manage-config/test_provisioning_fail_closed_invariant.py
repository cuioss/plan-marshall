#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Structural fail-closed provisioning-write invariant test (ADR-009).

Enumerates the provisioning-write handlers and asserts each one FAILS CLOSED on
an unknown / out-of-schema field: it returns ``status: error`` (never
``status: success``) rather than silently persisting a value no reader would
ever consult. A new provisioning-write handler that skips the shared
fail-closed guard (``_config_core.reject_unknown_provisioning_field``) is caught
by the enumeration below.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

# conftest.py sets up PYTHONPATH; test_helpers seeds marshal.json fixtures.
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


_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_system = _cmd_system_plan.cmd_system
cmd_project = _cmd_system_plan.cmd_project
# Reached through the loaded module's own namespace so the guard and whitelists
# are the exact instances the handlers use (no separate module copy).
reject_unknown_provisioning_field = _cmd_system_plan.reject_unknown_provisioning_field
DEFAULT_PROJECT = _cmd_system_plan.DEFAULT_PROJECT
DEFAULT_SYSTEM_RETENTION = _cmd_system_plan.DEFAULT_SYSTEM_RETENTION


# The enumerated provisioning-write handlers. Each entry pairs a callable that
# performs an UNKNOWN-field write with one that performs a KNOWN-field write. A
# new provisioning-write handler must be added here AND route through the shared
# fail-closed guard, or the unknown-field assertion below fails loudly.
def _unknown_retention_write():
    return cmd_system(Namespace(sub_noun='retention', verb='set', field='not_a_real_retention_key', value='7'))


def _known_retention_write():
    return cmd_system(Namespace(sub_noun='retention', verb='set', field='logs_days', value='7'))


def _unknown_project_write():
    return cmd_project(Namespace(verb='set', field='not_a_real_project_key', value='x'))


def _known_project_write():
    return cmd_project(Namespace(verb='set', field='default_base_branch', value='main'))


_PROVISIONING_WRITE_HANDLERS = [
    ('system.retention set', _unknown_retention_write, _known_retention_write),
    ('project set', _unknown_project_write, _known_project_write),
]


def test_every_provisioning_write_handler_fails_closed_on_unknown_field(plan_context):
    """STRUCTURAL: every enumerated provisioning-write handler refuses an unknown
    field with ``status: error`` (never a vacuous ``status: success``)."""
    for label, unknown_write, _known in _PROVISIONING_WRITE_HANDLERS:
        create_marshal_json(plan_context.fixture_dir)
        result = unknown_write()
        assert result['status'] == 'error', f'{label} must fail closed on an unknown field, got {result}'
        assert result.get('error_type') == 'unknown_field', (
            f'{label} must report error_type=unknown_field, got {result}'
        )


def test_every_provisioning_write_handler_accepts_a_known_field(plan_context):
    """The guard does not over-reject: a KNOWN field still writes successfully."""
    for label, _unknown, known_write in _PROVISIONING_WRITE_HANDLERS:
        create_marshal_json(plan_context.fixture_dir)
        result = known_write()
        assert result['status'] == 'success', f'{label} must accept a known field, got {result}'


def test_shared_guard_rejects_unknown_and_passes_known():
    """The single fail-closed encoding: ``reject_unknown_provisioning_field``
    returns an error_exit dict for an unknown field and ``None`` for a known one."""
    rejection = reject_unknown_provisioning_field('nope', DEFAULT_PROJECT, 'project')
    assert rejection is not None
    assert rejection['status'] == 'error'
    assert rejection['error_type'] == 'unknown_field'

    assert reject_unknown_provisioning_field('default_base_branch', DEFAULT_PROJECT, 'project') is None
    assert reject_unknown_provisioning_field('logs_days', DEFAULT_SYSTEM_RETENTION, 'system.retention') is None


def test_seeded_silent_success_write_is_caught(plan_context):
    """The invariant fails loudly against a seeded silent-success write: a pre-guard
    unknown-field write would have returned ``status: success``; the guard converts
    it into a fail-closed ``error``, proving the guard is the active gate."""
    create_marshal_json(plan_context.fixture_dir)
    result = cmd_system(Namespace(sub_noun='retention', verb='set', field='typo_key', value='1'))
    assert result['status'] == 'error'
    assert result.get('error_type') == 'unknown_field'
