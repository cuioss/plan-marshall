#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-references.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')


_crud = load_script_module('plan-marshall', 'manage-references', '_references_crud.py', '_refs_cmd_crud')
_list = load_script_module('plan-marshall', 'manage-references', '_cmd_list.py', '_refs_cmd_list')
_ctx = load_script_module('plan-marshall', 'manage-references', '_cmd_context.py', '_refs_cmd_context')
_core = load_script_module('plan-marshall', 'manage-references', '_references_core.py', '_refs_core')

require_references = _core.require_references
get_references_path = _core.get_references_path

cmd_create, cmd_get, cmd_read, cmd_set = _crud.cmd_create, _crud.cmd_get, _crud.cmd_read, _crud.cmd_set
cmd_add_list, cmd_set_list = _list.cmd_add_list, _list.cmd_set_list
cmd_get_context = _ctx.cmd_get_context


# =============================================================================
# Namespace Helpers
# =============================================================================


def _create_ns(plan_id='test-plan', branch='feature/test', issue_url=None, build_system=None, domains=None):
    """Build Namespace for cmd_create."""
    return Namespace(plan_id=plan_id, branch=branch, issue_url=issue_url, build_system=build_system, domains=domains)


def _read_ns(plan_id='test-plan'):
    """Build Namespace for cmd_read."""
    return Namespace(plan_id=plan_id)


def _get_ns(plan_id='test-plan', field='branch'):
    """Build Namespace for cmd_get."""
    return Namespace(plan_id=plan_id, field=field)


def _set_ns(plan_id='test-plan', field='branch', value='feature/new-branch'):
    """Build Namespace for cmd_set."""
    return Namespace(plan_id=plan_id, field=field, value=value)


def _add_list_ns(plan_id='test-plan', field='affected_files', values='file1.md,file2.md'):
    """Build Namespace for cmd_add_list."""
    return Namespace(plan_id=plan_id, field=field, values=values)


def _set_list_ns(plan_id='test-plan', field='affected_files', values='file1.md,file2.md'):
    """Build Namespace for cmd_set_list."""
    return Namespace(plan_id=plan_id, field=field, values=values)


def _get_context_ns(plan_id='test-plan'):
    """Build Namespace for cmd_get_context."""
    return Namespace(plan_id=plan_id)


# =============================================================================
# Test: Create Command
# =============================================================================


def test_create_references(plan_context):
    """Test creating references.json."""
    result = cmd_create(_create_ns())
    assert result['status'] == 'success'
    assert result['created'] is True


def test_create_with_issue_url(plan_context):
    """Test creating references with issue URL."""
    result = cmd_create(_create_ns(issue_url='https://github.com/org/repo/issues/123'))
    assert result['status'] == 'success'
    assert 'issue_url' in result['fields']


# =============================================================================
# Test: Read Command
# =============================================================================


def test_read_references(plan_context):
    """Test reading references.json."""
    cmd_create(_create_ns())
    result = cmd_read(_read_ns())
    assert result['status'] == 'success'


# =============================================================================
# Test: Get/Set Commands
# =============================================================================


def test_get_field(plan_context):
    """Test getting a specific field."""
    cmd_create(_create_ns())
    result = cmd_get(_get_ns(field='branch'))
    assert result['value'] == 'feature/test'


def test_set_field(plan_context):
    """Test setting a specific field."""
    cmd_create(_create_ns())
    result = cmd_set(_set_ns(field='branch', value='feature/new-branch'))
    assert result['value'] == 'feature/new-branch'


# =============================================================================
# Test: Create omits the modified_files ledger
# =============================================================================


def test_create_omits_modified_files(plan_context):
    """A fresh references.json must NOT carry a modified_files key.

    The footprint ledger was deleted — references.json no longer seeds
    ``modified_files`` at create; the footprint is derived on-demand via
    ``compute-footprint``.
    """
    cmd_create(_create_ns())
    refs = require_references('test-plan')
    assert isinstance(refs, dict)
    assert 'modified_files' not in refs, (
        f'create seeded a modified_files key: {refs!r}. The ledger was removed '
        f'— create must persist only branch/base_branch (+ optional fields).'
    )


# =============================================================================
# Test: Get Context
# =============================================================================


def test_get_context(plan_context):
    """Test get-context returns all relevant references in one call."""
    cmd_create(
        _create_ns(
            issue_url='https://github.com/org/repo/issues/123',
            build_system='maven',
        )
    )

    result = cmd_get_context(_get_context_ns())
    assert result['status'] == 'success'
    # Should have branch info
    assert result['branch'] == 'feature/test'
    assert result['base_branch'] == 'main'
    # Should have issue URL
    assert result['issue_url'] == 'https://github.com/org/repo/issues/123'
    # Should have build system
    assert result['build_system'] == 'maven'
    # The footprint ledger is gone — get-context no longer reports a count.
    assert 'modified_files_count' not in result
    assert 'modified_files' not in result


def test_get_context_omits_modified_files(plan_context):
    """get-context with minimal references omits all modified_files surface."""
    cmd_create(_create_ns())
    result = cmd_get_context(_get_context_ns())
    assert result['status'] == 'success'
    assert 'modified_files_count' not in result
    assert 'modified_files' not in result


def test_get_context_not_found(plan_context):
    """get-context returns an error dict for a missing plan (caller propagates to dispatcher)."""
    result = cmd_get_context(_get_context_ns(plan_id='nonexistent'))
    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'
    assert result['plan_id'] == 'nonexistent'


# =============================================================================
# Test: Add List Command
# =============================================================================


def test_add_list_new_field(plan_context):
    """Test adding multiple values to a new list field."""
    cmd_create(_create_ns())
    result = cmd_add_list(_add_list_ns(values='file1.md,file2.md,file3.md'))
    assert result['status'] == 'success'
    assert result['field'] == 'affected_files'
    assert result['added_count'] == 3
    assert result['total'] == 3


def test_add_list_existing_field(plan_context):
    """Test adding values to an existing list field."""
    cmd_create(_create_ns())
    cmd_add_list(_add_list_ns(values='file1.md,file2.md'))
    result = cmd_add_list(_add_list_ns(values='file3.md,file4.md'))
    assert result['added_count'] == 2
    assert result['total'] == 4


def test_add_list_no_duplicates(plan_context):
    """Test that add-list skips duplicate values."""
    cmd_create(_create_ns())
    cmd_add_list(_add_list_ns(values='file1.md,file2.md'))
    result = cmd_add_list(_add_list_ns(values='file1.md,file3.md'))
    assert result['added_count'] == 1  # Only file3.md is new
    assert result['total'] == 3


# =============================================================================
# Test: Set List Command
# =============================================================================


def test_set_list_comma_separated(plan_context):
    """Test set-list with comma-separated values."""
    cmd_create(_create_ns())
    result = cmd_set_list(_set_list_ns(values='file1.md,file2.md,file3.md'))
    assert result['status'] == 'success'
    assert result['field'] == 'affected_files'
    assert result['count'] == 3


def test_set_list_replaces_existing(plan_context):
    """Test that set-list replaces existing list (not appends)."""
    cmd_create(_create_ns())
    # First add some files
    cmd_add_list(_add_list_ns(values='old1.md,old2.md,old3.md'))
    # Now set-list should REPLACE, not append
    result = cmd_set_list(_set_list_ns(values='new1.md,new2.md'))
    assert result['count'] == 2  # Only the new files, not 5

    # Verify by reading the field
    get_result = cmd_get(_get_ns(field='affected_files'))
    assert len(get_result['value']) == 2
    assert 'new1.md' in get_result['value']
    assert 'new2.md' in get_result['value']
    assert 'old1.md' not in get_result['value']


def test_set_list_empty_clears(plan_context):
    """Test that set-list with empty values clears the list."""
    cmd_create(_create_ns())
    cmd_add_list(_add_list_ns(values='file1.md,file2.md'))
    # Set to empty
    result = cmd_set_list(_set_list_ns(values=''))
    assert result['count'] == 0


def test_set_list_nonexistent_plan(plan_context):
    """set-list returns an error dict for a missing plan (caller propagates to dispatcher)."""
    result = cmd_set_list(_set_list_ns(plan_id='nonexistent'))
    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'
    assert result['plan_id'] == 'nonexistent'


def test_set_list_returns_previous_count(plan_context):
    """Test that set-list returns the previous count when replacing."""
    cmd_create(_create_ns())
    cmd_add_list(_add_list_ns(values='old1.md,old2.md,old3.md'))
    result = cmd_set_list(_set_list_ns(values='new1.md,new2.md'))
    assert result['previous_count'] == 3
    assert result['count'] == 2


# =============================================================================
# Test: Create with --domains Parameter
# =============================================================================


def test_create_with_single_domain(plan_context):
    """Test creating references with single domain."""
    result = cmd_create(_create_ns(domains='java'))
    assert result['status'] == 'success'
    assert 'domains' in result['fields']

    # Verify domains stored correctly
    get_result = cmd_get(_get_ns(field='domains'))
    assert get_result['value'] == ['java']


def test_create_with_multiple_domains(plan_context):
    """Test creating references with multiple domains."""
    cmd_create(_create_ns(domains='java,documentation'))

    # Verify domains stored correctly
    get_result = cmd_get(_get_ns(field='domains'))
    assert 'java' in get_result['value']
    assert 'documentation' in get_result['value']
    assert len(get_result['value']) == 2


def test_create_without_domains(plan_context):
    """Test creating references without domains (domains not set)."""
    cmd_create(_create_ns())

    # Domains should not be in fields - get returns error
    get_result = cmd_get(_get_ns(field='domains'))
    assert get_result['status'] == 'error'


def test_create_with_domains_and_issue_url(plan_context):
    """Test creating references with both domains and issue URL."""
    result = cmd_create(
        _create_ns(
            domains='java',
            issue_url='https://github.com/org/repo/issues/42',
        )
    )
    assert 'domains' in result['fields']
    assert 'issue_url' in result['fields']


# =============================================================================
# Subprocess tests (CLI plumbing - Tier 3)
# =============================================================================


def test_cli_missing_subcommand_exits_2():
    """Missing subcommand exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 2


def test_cli_help_exits_0():
    """--help exits with code 0."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.returncode == 0
    assert 'manage references' in result.stdout.lower()


def test_cli_create_roundtrip(plan_context):
    """CLI create + get roundtrip verifies end-to-end plumbing."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    create_result = run_script(
        SCRIPT_PATH,
        'create',
        '--plan-id',
        'test-plan',
        '--branch',
        'feature/test',
    )
    assert create_result.success, f'Script failed: {create_result.stderr}'
    data = parse_toon(create_result.stdout)
    assert data['status'] == 'success'

    get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--field', 'branch')
    assert get_result.success, f'Script failed: {get_result.stderr}'
    get_data = parse_toon(get_result.stdout)
    assert get_data['value'] == 'feature/test'


# =============================================================================
# Regression Tests: Not-found conditions exit 0 with TOON status:error
#
# Operation failures (file not found, validation failure) are NOT script
# crashes — the script ran successfully, only the operation failed. Per the
# output contract (pm-plugin-development:plugin-script-architecture →
# output-contract.md), these exit 0 and carry the verdict in the TOON
# ``status: error`` payload on stdout. Callers branch on ``status``, never on
# the process exit code. Exit 1 is reserved for genuine script crashes
# (uncaught exceptions surfaced by ``safe_main``); exit 2 for argparse.
# =============================================================================


def test_cli_get_not_found_exits_zero_with_toon_error(plan_context):
    """get with missing references.json exits 0 with TOON status:error output."""
    result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'nonexistent', '--field', 'branch')
    assert result.success, f'Operation failures exit 0, stderr: {result.stderr}'
    assert result.returncode == 0
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


def test_cli_read_not_found_exits_zero_with_toon_error(tmp_path, monkeypatch):
    """read with missing references.json exits 0 with TOON status:error output.

    PlanContext pins PLAN_BASE_DIR to its fixture_dir, but the spawned
    subprocess can still write to ``~/.plan-marshall-credentials`` during
    provider initialization. Redirect HOME and CREDENTIALS_DIR as well so
    nothing leaks into the real host paths.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))
    monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'nonexistent')
    assert result.success, f'Operation failures exit 0, stderr: {result.stderr}'
    assert result.returncode == 0
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


def test_cli_get_context_not_found_exits_zero_with_toon_error(tmp_path, monkeypatch):
    """get-context with missing references.json exits 0 with TOON status:error output.

    PlanContext pins PLAN_BASE_DIR to its fixture_dir, but the spawned
    subprocess can still write to ``~/.plan-marshall-credentials`` during
    provider initialization. Redirect HOME and CREDENTIALS_DIR as well so
    nothing leaks into the real host paths.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))
    monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')
    result = run_script(SCRIPT_PATH, 'get-context', '--plan-id', 'nonexistent')
    assert result.success, f'Operation failures exit 0, stderr: {result.stderr}'
    assert result.returncode == 0
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


def test_cli_set_list_not_found_exits_zero_with_toon_error(tmp_path, monkeypatch):
    """set-list with missing references.json exits 0 with TOON status:error output."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))
    monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')
    result = run_script(
        SCRIPT_PATH,
        'set-list',
        '--plan-id',
        'nonexistent',
        '--field',
        'domains',
        '--values',
        'foo,bar',
    )
    assert result.success, f'Operation failures exit 0, stderr: {result.stderr}'
    assert result.returncode == 0
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


# =============================================================================
# Exhaustive coverage: every operation-failure path emits (exit_code == 0)
# AND (status: error) TOON. Subcommands that touch require_references() must
# propagate the file-not-found dict so the dispatcher emits the TOON error
# payload while exiting 0; argparse rejections surface as exit_code == 2 via
# parse_args_with_toon_errors (a separate, genuine-usage-error path).
# =============================================================================


_FILE_NOT_FOUND_INVOCATIONS = [
    ('get', ['get', '--plan-id', 'nonexistent', '--field', 'branch']),
    ('read', ['read', '--plan-id', 'nonexistent']),
    ('get-context', ['get-context', '--plan-id', 'nonexistent']),
    ('set-list', ['set-list', '--plan-id', 'nonexistent', '--field', 'domains', '--values', 'a']),
]


def test_cli_every_file_not_found_path_exits_zero_with_toon_error(tmp_path, monkeypatch):
    """Every require_references() consumer surfaces exit_code == 0 + status: error TOON.

    This is the exhaustive coverage gate: any subcommand that reads
    references.json via ``require_references()`` MUST propagate the
    file-not-found error dict so the main dispatcher emits the TOON
    ``status: error`` payload and exits 0 (operation failure, not a script
    crash). A future caller added without the
    ``if refs.get('status') == 'error': return refs`` propagation guard — or
    one that regresses the dispatcher back to exit 1 on error — fails this
    test.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))
    monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')

    failures: list[str] = []
    for label, argv in _FILE_NOT_FOUND_INVOCATIONS:
        result = run_script(SCRIPT_PATH, *argv)
        if result.returncode != 0:
            failures.append(
                f'{label}: exit_code={result.returncode} (expected 0 for operation failure); '
                f'stdout={result.stdout!r}'
            )
            continue
        if 'status: error' not in result.stdout:
            failures.append(f'{label}: missing "status: error" in stdout; stdout={result.stdout!r}')
        if 'file_not_found' not in result.stdout:
            failures.append(f'{label}: missing "file_not_found" in stdout; stdout={result.stdout!r}')

    assert not failures, 'File-not-found exit-code regressions:\n' + '\n'.join(failures)


# =============================================================================
# Test: require_references rejects non-dict top-level JSON values
# =============================================================================
# Regression coverage for the gemini-code-assist review on PR #426:
# require_references() must raise ValueError when references.json exists but
# its top-level JSON value is not a JSON object. Without the isinstance check,
# non-dict values (list, string, number, bool, null) silently pass through
# the `if not refs:` truthiness gate and trigger AttributeError downstream
# when callers invoke ``.get()`` on the parsed value.


def _write_raw_references(plan_id: str, payload: str) -> None:
    """Write raw JSON text to references.json for a plan, bypassing schema."""
    refs_path = get_references_path(plan_id)
    refs_path.parent.mkdir(parents=True, exist_ok=True)
    refs_path.write_text(payload, encoding='utf-8')


@pytest.mark.parametrize(
    ('payload', 'expected_type_name'),
    [
        ('[1, 2, 3]', 'list'),
        ('"a string"', 'str'),
        ('42', 'int'),
        ('3.14', 'float'),
        ('true', 'bool'),
    ],
)
def test_require_references_raises_on_non_dict_json(plan_context, payload, expected_type_name):
    """Truthy non-dict top-level JSON values raise a clear ValueError.

    Covers list, string, integer, float, and boolean payloads. JSON ``null``
    is falsy and therefore caught earlier by the ``if not refs:`` gate (see
    ``test_require_references_treats_null_as_file_not_found`` below), so it
    is intentionally absent from this parametrization.
    """
    plan_id = plan_context.plan_id
    _write_raw_references(plan_id, payload)

    with pytest.raises(ValueError, match='invalid format') as excinfo:
        require_references(plan_id)

    message = str(excinfo.value)
    assert expected_type_name in message
    assert plan_id in message


def test_require_references_treats_null_as_file_not_found(plan_context):
    """JSON ``null`` is falsy and falls through the not-found gate.

    ``read_json`` returns ``None`` for a file whose top-level value is ``null``,
    which means ``if not refs:`` triggers BEFORE the isinstance check. Surface
    the existing file_not_found error envelope rather than a ValueError.
    """
    plan_id = plan_context.plan_id
    _write_raw_references(plan_id, 'null')

    result = require_references(plan_id)

    assert isinstance(result, dict)
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


def test_require_references_accepts_dict_payload(plan_context):
    """Sanity check: a valid JSON object payload still returns the dict."""
    plan_id = plan_context.plan_id
    _write_raw_references(plan_id, '{"branch": "feature/test"}')

    result = require_references(plan_id)

    assert isinstance(result, dict)
    assert result['branch'] == 'feature/test'


def test_require_references_returns_error_dict_when_missing(plan_context):
    """Sanity check: a missing references.json still returns the file_not_found
    error dict — the new isinstance guard does NOT change the not-found path.
    """
    result = require_references('nonexistent-plan')

    assert isinstance(result, dict)
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'
    assert result['plan_id'] == 'nonexistent-plan'


def test_require_references_returns_error_dict_on_empty_object(plan_context):
    """An empty JSON object ``{}`` is falsy and still maps to file_not_found
    via the existing ``if not refs:`` check (unchanged by this fix).
    """
    plan_id = plan_context.plan_id
    _write_raw_references(plan_id, '{}')

    result = require_references(plan_id)

    assert isinstance(result, dict)
    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'


def _seed_non_dict_references(tmp_path, monkeypatch, payload):
    """Seed a references.json with a non-dict top-level JSON value and run read.

    Returns the CompletedProcess from the ``read`` subprocess invocation.
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('PLAN_MARSHALL_CREDENTIALS_DIR', str(tmp_path / 'creds'))
    monkeypatch.setattr('_providers_core.CREDENTIALS_DIR', tmp_path / 'creds')

    plan_id = 'corrupt-plan'
    refs_path = tmp_path / 'plans' / plan_id / 'references.json'
    refs_path.parent.mkdir(parents=True, exist_ok=True)
    refs_path.write_text(payload, encoding='utf-8')

    # Sanity check: the file is parseable JSON but NOT a dict.
    parsed = json.loads(refs_path.read_text())
    assert not isinstance(parsed, dict)

    return run_script(SCRIPT_PATH, 'read', '--plan-id', plan_id)


@pytest.mark.parametrize(
    'payload',
    [
        '[1, 2, 3]',
        '"a string"',
        '42',
        'true',
    ],
)
def test_cli_truthy_non_dict_references_crashes_nonzero_exit(payload, tmp_path, monkeypatch):
    """A *truthy* non-dict references payload raises ValueError → exit 1.

    ``require_references()`` only reaches its ``isinstance`` guard when the
    parsed value is truthy (a non-empty list/string, a non-zero number, or
    ``true``). The raised ValueError bypasses the TOON error envelope and
    crashes via ``safe_main`` with a non-zero exit code — corrupt-file states
    that are *truthy* must NOT exit 0.
    """
    result = _seed_non_dict_references(tmp_path, monkeypatch, payload)
    assert result.returncode == 1, (
        f'Expected exit 1 (ValueError crash) for truthy non-dict references '
        f'payload {payload!r}; '
        f'stdout={result.stdout!r} stderr={result.stderr!r}'
    )


@pytest.mark.parametrize(
    'payload',
    [
        'null',
        'false',
        '0',
        '[]',
        '""',
    ],
)
def test_cli_falsy_non_dict_references_is_operation_failure_exit0(payload, tmp_path, monkeypatch):
    """A *falsy* non-dict references payload is a contract-correct exit-0 failure.

    ``require_references()`` returns ``None`` from ``read_references`` for any
    falsy parsed value (``null``, ``false``, ``0``, ``[]``, ``""``), so the
    ``if not refs:`` branch fires *before* the ``isinstance`` guard and returns
    the structured ``file_not_found`` operation-error dict. Per the
    operation-failure contract, the dispatcher emits ``status: error`` on
    stdout and exits 0 — the script ran successfully, only the operation failed.
    """
    result = _seed_non_dict_references(tmp_path, monkeypatch, payload)
    assert result.returncode == 0, (
        f'Expected exit 0 (operation failure) for falsy non-dict references '
        f'payload {payload!r}; '
        f'stdout={result.stdout!r} stderr={result.stderr!r}'
    )
    assert 'status: error' in result.stdout, (
        f'Expected structured error TOON on stdout for payload {payload!r}; '
        f'stdout={result.stdout!r}'
    )
    assert 'file_not_found' in result.stdout, (
        f'Expected file_not_found error on stdout for payload {payload!r}; '
        f'stdout={result.stdout!r}'
    )


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the module docstring's
    storage line must spell the references location as ``.plan/local/plans/`` —
    the legacy bare ``.plan/plans/`` form is incorrect since runtime state moved
    under ``.plan/local``.
    """
    import re

    source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'
