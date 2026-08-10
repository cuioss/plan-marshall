#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the run_config ``language-server`` verbs (the lsp-client config surface).

The ``language_servers`` section lives in the machine-local run-configuration
store — the shared configuration surface the lsp-client reads. These cover the
set/get/list/remove round-trip, the disabled flag, and command validation.
"""

import argparse

import run_config

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


def _set(**kwargs) -> argparse.Namespace:
    defaults = {'language': 'python', 'command': '["srv", "--stdio"]', 'language_id': None, 'disabled': False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cli_set_succeeds(plan_context):
    result = run_script(
        SCRIPT_PATH, 'language-server', 'set',
        '--language', 'python', '--command', '["pyright-langserver", "--stdio"]', '--language-id', 'python',
    )
    assert result.success, result.stderr
    data = result.toon()
    assert data.get('status') == 'success'
    assert data.get('action') == 'set'
    assert data.get('language') == 'python'


def test_set_get_round_trip(plan_context):
    run_config.cmd_language_server_set(_set(language_id='python'))
    got = run_config.cmd_language_server_get(argparse.Namespace(language='python'))
    assert got['status'] == 'success'
    assert got['configured'] is True
    assert got['enabled'] is True
    assert got['command'] == ['srv', '--stdio']
    assert got['language_id'] == 'python'


def test_get_not_configured(plan_context):
    got = run_config.cmd_language_server_get(argparse.Namespace(language='ruby'))
    assert got['status'] == 'success'
    assert got['configured'] is False


def test_disabled_flag_persists(plan_context):
    run_config.cmd_language_server_set(_set(disabled=True))
    got = run_config.cmd_language_server_get(argparse.Namespace(language='python'))
    assert got['configured'] is True
    assert got['enabled'] is False


def test_language_id_defaults_to_language(plan_context):
    run_config.cmd_language_server_set(_set(language='python', language_id=None))
    got = run_config.cmd_language_server_get(argparse.Namespace(language='python'))
    assert got['language_id'] == 'python'


def test_list_and_remove(plan_context):
    run_config.cmd_language_server_set(_set(language='python'))
    run_config.cmd_language_server_set(_set(language='typescript', command='["tsserver"]'))
    listed = run_config.cmd_language_server_list(argparse.Namespace())
    assert listed['languages'] == ['python', 'typescript']
    assert listed['count'] == 2

    removed = run_config.cmd_language_server_remove(argparse.Namespace(language='python'))
    assert removed['action'] == 'removed'
    assert run_config.cmd_language_server_list(argparse.Namespace())['languages'] == ['typescript']

    skipped = run_config.cmd_language_server_remove(argparse.Namespace(language='python'))
    assert skipped['action'] == 'skipped'


def test_set_rejects_non_json_command(plan_context):
    result = run_config.cmd_language_server_set(_set(command='not-json'))
    assert result['status'] == 'error'


def test_set_rejects_non_list_command(plan_context):
    assert run_config.cmd_language_server_set(_set(command='{"a": 1}'))['status'] == 'error'
    assert run_config.cmd_language_server_set(_set(command='[]'))['status'] == 'error'
    assert run_config.cmd_language_server_set(_set(command='[1, 2]'))['status'] == 'error'
