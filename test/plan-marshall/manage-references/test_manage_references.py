#!/usr/bin/env python3
"""Tests for manage-references.py script.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.
"""

from argparse import Namespace
from pathlib import Path

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-references', 'manage-references.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime)
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-references'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_crud = _load_module('_refs_cmd_crud', '_references_crud.py')
_list = _load_module('_refs_cmd_list', '_cmd_list.py')
_ctx = _load_module('_refs_cmd_context', '_cmd_context.py')

cmd_create, cmd_get, cmd_read, cmd_set = _crud.cmd_create, _crud.cmd_get, _crud.cmd_read, _crud.cmd_set
cmd_add_file, cmd_add_list, cmd_remove_file, cmd_set_list = (
    _list.cmd_add_file,
    _list.cmd_add_list,
    _list.cmd_remove_file,
    _list.cmd_set_list,
)
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


def _add_file_ns(plan_id='test-plan', file='src/Main.java'):
    """Build Namespace for cmd_add_file."""
    return Namespace(plan_id=plan_id, file=file)


def _remove_file_ns(plan_id='test-plan', file='src/Main.java'):
    """Build Namespace for cmd_remove_file."""
    return Namespace(plan_id=plan_id, file=file)


def _add_list_ns(plan_id='test-plan', field='affected_files', values='file1.md,file2.md'):
    """Build Namespace for cmd_add_list."""
    return Namespace(plan_id=plan_id, field=field, values=values)


def _set_list_ns(plan_id='test-plan', field='affected_files', values='file1.md,file2.md'):
    """Build Namespace for cmd_set_list."""
    return Namespace(plan_id=plan_id, field=field, values=values)


def _get_context_ns(plan_id='test-plan', include_files=False):
    """Build Namespace for cmd_get_context."""
    return Namespace(plan_id=plan_id, include_files=include_files)


# =============================================================================
# Test: Create Command
# =============================================================================


def test_create_references():
    """Test creating references.json."""
    with PlanContext():
        result = cmd_create(_create_ns())
        assert result['status'] == 'success'
        assert result['created'] is True


def test_create_with_issue_url():
    """Test creating references with issue URL."""
    with PlanContext():
        result = cmd_create(_create_ns(issue_url='https://github.com/org/repo/issues/123'))
        assert result['status'] == 'success'
        assert 'issue_url' in result['fields']


# =============================================================================
# Test: Read Command
# =============================================================================


def test_read_references():
    """Test reading references.json."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_read(_read_ns())
        assert result['status'] == 'success'


# =============================================================================
# Test: Get/Set Commands
# =============================================================================


def test_get_field():
    """Test getting a specific field."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_get(_get_ns(field='branch'))
        assert result['value'] == 'feature/test'


def test_set_field():
    """Test setting a specific field."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_set(_set_ns(field='branch', value='feature/new-branch'))
        assert result['value'] == 'feature/new-branch'


# =============================================================================
# Test: Add/Remove File Commands
# =============================================================================


def test_add_file():
    """Test adding a file to modified_files."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_add_file(_add_file_ns(file='src/Main.java'))
        assert result['added'] == 'src/Main.java'
        assert result['total'] == 1


# =============================================================================
# Test: Get Context
# =============================================================================


def test_get_context():
    """Test get-context returns all relevant references in one call."""
    with PlanContext():
        cmd_create(
            _create_ns(
                issue_url='https://github.com/org/repo/issues/123',
                build_system='maven',
            )
        )
        cmd_add_file(_add_file_ns(file='src/Main.java'))
        cmd_add_file(_add_file_ns(file='src/Test.java'))

        result = cmd_get_context(_get_context_ns())
        assert result['status'] == 'success'
        # Should have branch info
        assert result['branch'] == 'feature/test'
        assert result['base_branch'] == 'main'
        # Should have issue URL
        assert result['issue_url'] == 'https://github.com/org/repo/issues/123'
        # Should have build system
        assert result['build_system'] == 'maven'
        # Should have file counts
        assert result['modified_files_count'] == 2


def test_get_context_empty():
    """Test get-context with minimal references."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_get_context(_get_context_ns())
        assert result['modified_files_count'] == 0


def test_get_context_not_found():
    """Test get-context returns None for missing plan (TOON error already output)."""
    with PlanContext():
        result = cmd_get_context(_get_context_ns(plan_id='nonexistent'))
        assert result is None


# =============================================================================
# Test: Add List Command
# =============================================================================


def test_add_list_new_field():
    """Test adding multiple values to a new list field."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_add_list(_add_list_ns(values='file1.md,file2.md,file3.md'))
        assert result['status'] == 'success'
        assert result['field'] == 'affected_files'
        assert result['added_count'] == 3
        assert result['total'] == 3


def test_add_list_existing_field():
    """Test adding values to an existing list field."""
    with PlanContext():
        cmd_create(_create_ns())
        cmd_add_list(_add_list_ns(values='file1.md,file2.md'))
        result = cmd_add_list(_add_list_ns(values='file3.md,file4.md'))
        assert result['added_count'] == 2
        assert result['total'] == 4


def test_add_list_no_duplicates():
    """Test that add-list skips duplicate values."""
    with PlanContext():
        cmd_create(_create_ns())
        cmd_add_list(_add_list_ns(values='file1.md,file2.md'))
        result = cmd_add_list(_add_list_ns(values='file1.md,file3.md'))
        assert result['added_count'] == 1  # Only file3.md is new
        assert result['total'] == 3


# =============================================================================
# Test: Set List Command
# =============================================================================


def test_set_list_comma_separated():
    """Test set-list with comma-separated values."""
    with PlanContext():
        cmd_create(_create_ns())
        result = cmd_set_list(_set_list_ns(values='file1.md,file2.md,file3.md'))
        assert result['status'] == 'success'
        assert result['field'] == 'affected_files'
        assert result['count'] == 3


def test_set_list_replaces_existing():
    """Test that set-list replaces existing list (not appends)."""
    with PlanContext():
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


def test_set_list_empty_clears():
    """Test that set-list with empty values clears the list."""
    with PlanContext():
        cmd_create(_create_ns())
        cmd_add_list(_add_list_ns(values='file1.md,file2.md'))
        # Set to empty
        result = cmd_set_list(_set_list_ns(values=''))
        assert result['count'] == 0


def test_set_list_nonexistent_plan():
    """Test set-list returns None for non-existent plan (TOON error already output)."""
    with PlanContext():
        result = cmd_set_list(_set_list_ns(plan_id='nonexistent'))
        assert result is None


def test_set_list_returns_previous_count():
    """Test that set-list returns the previous count when replacing."""
    with PlanContext():
        cmd_create(_create_ns())
        cmd_add_list(_add_list_ns(values='old1.md,old2.md,old3.md'))
        result = cmd_set_list(_set_list_ns(values='new1.md,new2.md'))
        assert result['previous_count'] == 3
        assert result['count'] == 2


# =============================================================================
# Test: Create with --domains Parameter
# =============================================================================


def test_create_with_single_domain():
    """Test creating references with single domain."""
    with PlanContext():
        result = cmd_create(_create_ns(domains='java'))
        assert result['status'] == 'success'
        assert 'domains' in result['fields']

        # Verify domains stored correctly
        get_result = cmd_get(_get_ns(field='domains'))
        assert get_result['value'] == ['java']


def test_create_with_multiple_domains():
    """Test creating references with multiple domains."""
    with PlanContext():
        cmd_create(_create_ns(domains='java,documentation'))

        # Verify domains stored correctly
        get_result = cmd_get(_get_ns(field='domains'))
        assert 'java' in get_result['value']
        assert 'documentation' in get_result['value']
        assert len(get_result['value']) == 2


def test_create_without_domains():
    """Test creating references without domains (domains not set)."""
    with PlanContext():
        cmd_create(_create_ns())

        # Domains should not be in fields - get returns error
        get_result = cmd_get(_get_ns(field='domains'))
        assert get_result['status'] == 'error'


def test_create_with_domains_and_issue_url():
    """Test creating references with both domains and issue URL."""
    with PlanContext():
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


def test_cli_create_roundtrip():
    """CLI create + get roundtrip verifies end-to-end plumbing."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    with PlanContext():
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
# Regression Tests: Not-found conditions exit 0 with TOON error
# =============================================================================


def test_cli_get_not_found_exits_zero():
    """Regression: get with missing references.json exits 0 with TOON error output."""
    with PlanContext():
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'nonexistent', '--field', 'branch')
        assert result.success, f'Should exit 0, got: {result.stderr}'
        assert 'status: error' in result.stdout
        assert 'file_not_found' in result.stdout


def test_cli_read_not_found_exits_zero(tmp_path, monkeypatch):
    """Regression: read with missing references.json exits 0 with TOON error output.

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
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


def test_cli_get_context_not_found_exits_zero(tmp_path, monkeypatch):
    """Regression: get-context with missing references.json exits 0 with TOON error output.

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
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout
