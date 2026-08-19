#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-interface.py script.

Tier 2 (direct import) tests with 2 subprocess CLI plumbing tests retained.
"""

from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, parse_ns, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('pm-documents', 'manage-interface', 'manage-interface.py')

# Tier 2 direct imports - load hyphenated module via the conftest helper
_mod = load_script_module('pm-documents', 'manage-interface', 'manage-interface.py', 'manage_interface')

cmd_list = _mod.cmd_list

# Argument namespaces come from the script's OWN parser, so each carries every
# default the real CLI applies — a hand-built Namespace carries only the keys its
# author remembered. Parsed once at module scope: parse_ns re-executes the script
# module on every call.
_CREATE_NS = parse_ns(
    'pm-documents', 'manage-interface', 'manage-interface.py',
    'create', '--title', 'placeholder', '--type', 'REST_API', register=False,
)
_LIST_NS = parse_ns(
    'pm-documents', 'manage-interface', 'manage-interface.py',
    'list', register=False,
)
_DELETE_NS = parse_ns(
    'pm-documents', 'manage-interface', 'manage-interface.py',
    'delete', '--number', '1', '--force', register=False,
)
_READ_NS = parse_ns(
    'pm-documents', 'manage-interface', 'manage-interface.py',
    'read', '--number', '1', register=False,
)
_NEXT_NUMBER_NS = parse_ns(
    'pm-documents', 'manage-interface', 'manage-interface.py',
    'next-number', register=False,
)


def _ns(template: Namespace, **overrides) -> Namespace:
    """A parser-produced namespace with this test's values overlaid."""
    return Namespace(**{**vars(template), **overrides})
cmd_create = _mod.cmd_create
cmd_read = _mod.cmd_read
cmd_update = _mod.cmd_update
cmd_delete = _mod.cmd_delete
cmd_next_number = _mod.cmd_next_number

VALID_INTERFACE_TYPES = ['REST_API', 'Event', 'gRPC', 'Database', 'File', 'Other']


@pytest.fixture
def interface_dir(tmp_path, monkeypatch):
    """Provide an isolated ``doc/interfaces`` tree and chdir into its root.

    ``manage-interface`` resolves ``doc/interfaces`` relative to cwd, so each
    test runs against a fresh sandbox. The autouse ``_restore_cwd`` fixture
    restores the working directory after the test.
    """
    interfaces = tmp_path / 'doc' / 'interfaces'
    interfaces.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return interfaces


def test_next_number_returns_one_for_empty_dir(interface_dir):
    result = cmd_next_number(_ns(_NEXT_NUMBER_NS, command='next-number'))

    assert result['status'] == 'success'
    assert result['next_number'] == 1


def test_create_interface_writes_numbered_file(interface_dir):
    result = cmd_create(_ns(_CREATE_NS, command='create', title='User Service API', type='REST_API'))

    assert result['status'] == 'success'
    assert result['number'] == 1

    created_file = interface_dir / '001-User_Service_API.adoc'
    assert created_file.exists()
    content = created_file.read_text()
    assert 'INTER-001' in content
    assert 'User Service API' in content
    assert 'REST_API' in content


def test_create_multiple_interfaces_increments_number(interface_dir):
    cmd_create(_ns(_CREATE_NS, command='create', title='First', type='REST_API'))
    cmd_create(_ns(_CREATE_NS, command='create', title='Second', type='Event'))

    result = cmd_create(_ns(_CREATE_NS, command='create', title='Third', type='gRPC'))

    assert result['number'] == 3


def test_list_returns_all_interfaces(interface_dir):
    cmd_create(_ns(_CREATE_NS, command='create', title='API One', type='REST_API'))
    cmd_create(_ns(_CREATE_NS, command='create', title='API Two', type='Event'))

    result = cmd_list(_ns(_LIST_NS, command='list', type=None))

    assert result['status'] == 'success'
    assert result['count'] == 2


def test_list_filters_by_type(interface_dir):
    cmd_create(_ns(_CREATE_NS, command='create', title='REST One', type='REST_API'))
    cmd_create(_ns(_CREATE_NS, command='create', title='Event One', type='Event'))
    cmd_create(_ns(_CREATE_NS, command='create', title='REST Two', type='REST_API'))

    result = cmd_list(_ns(_LIST_NS, command='list', type='REST_API'))

    assert result['status'] == 'success'
    assert result['count'] == 2


def test_read_returns_interface_content(interface_dir):
    cmd_create(_ns(_CREATE_NS, command='create', title='Test Read', type='Database'))

    result = cmd_read(_ns(_READ_NS, command='read', number=1))

    assert result['status'] == 'success'
    assert 'Test Read' in result['content']


def test_read_missing_interface_reports_not_found(interface_dir):
    result = cmd_read(_ns(_READ_NS, command='read', number=999))

    assert result['status'] == 'error'
    assert 'not found' in result['message'].lower()


def test_delete_without_force_is_rejected(interface_dir):
    cmd_create(_ns(_CREATE_NS, command='create', title='Delete Test', type='File'))

    result = cmd_delete(_ns(_DELETE_NS, command='delete', number=1, force=False))

    assert result['status'] == 'error'
    assert '--force' in result['message']


def test_delete_with_force_removes_file(interface_dir):
    cmd_create(_ns(_CREATE_NS, command='create', title='Delete Me', type='Other'))

    result = cmd_delete(_ns(_DELETE_NS, command='delete', number=1, force=True))

    assert result['deleted']
    assert list(interface_dir.glob('001-*.adoc')) == []


@pytest.mark.parametrize('interface_type', VALID_INTERFACE_TYPES)
def test_create_accepts_valid_type(interface_dir, interface_type):
    result = cmd_create(_ns(_CREATE_NS, command='create', title=f'Test {interface_type}', type=interface_type))

    assert result['status'] == 'success'


def test_create_sanitizes_special_characters_in_filename(interface_dir):
    result = cmd_create(_ns(_CREATE_NS, command='create', title='API/Service with Special!', type='REST_API'))

    assert result['status'] == 'success'
    filename = Path(result['path']).name
    assert '/' not in filename
    assert '!' not in filename


# Tier 3: Subprocess CLI plumbing tests (retained)


def test_cli_create_requires_type(tmp_path):
    result = run_script(SCRIPT_PATH, 'create', '--title', 'Some Interface', cwd=tmp_path)

    assert result.returncode != 0
    assert '--type' in result.stderr


def test_cli_rejects_invalid_interface_type(tmp_path):
    result = run_script(SCRIPT_PATH, 'create', '--title', 'Bad Interface', '--type', 'INVALID', cwd=tmp_path)

    assert result.returncode != 0


def test_cli_create_then_list(tmp_path):
    create_result = run_script(SCRIPT_PATH, 'create', '--title', 'CLI Test', '--type', 'REST_API', cwd=tmp_path)

    assert create_result.returncode == 0
    assert 'success' in create_result.stdout

    list_result = run_script(SCRIPT_PATH, 'list', cwd=tmp_path)

    assert list_result.returncode == 0
    assert 'success' in list_result.stdout
