#!/usr/bin/env python3
"""Tests for manage-config.py script.

Note: workflow_skills are resolved from marshal.json via plan-marshall-config,
not stored in config.toon.
"""

import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, get_script_path, PlanContext

# Get script path
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-config', 'manage-config.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]


# Alias for backward compatibility
TestContext = PlanContext


# =============================================================================
# Test: Create Command
# =============================================================================

def test_create_config_single_domain():
    """Test creating a config file with single domain (java)."""
    with TestContext(plan_id='config-single'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-single',
            '--domains', 'java'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['config']['domains'] == ['java']
        # workflow_skills not in config.toon anymore
        assert 'workflow_skills' not in data['config']


def test_create_config_multiple_domains():
    """Test creating a config file with multiple domains."""
    with TestContext(plan_id='config-multi-domain'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-multi-domain',
            '--domains', 'java,javascript'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'java' in data['config']['domains']
        assert 'javascript' in data['config']['domains']


def test_create_config_plugin_domain():
    """Test creating a config file with plan-marshall-plugin-dev domain."""
    with TestContext(plan_id='config-plugin'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-plugin',
            '--domains', 'plan-marshall-plugin-dev'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['config']['domains'] == ['plan-marshall-plugin-dev']


def test_create_config_with_all_options():
    """Test creating a config file with all optional parameters."""
    with TestContext(plan_id='config-full-opts'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-full-opts',
            '--domains', 'java',
            '--commit-strategy', 'per_plan',
            '--create-pr', 'false',
            '--verification-required', 'true',
            '--verification-command', '/pm-dev-builder:builder-build-and-fix',
            '--branch-strategy', 'direct'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['config']['commit_strategy'] == 'per_plan'
        assert data['config']['create_pr'] == False
        assert data['config']['verification_required'] == True
        assert data['config']['verification_command'] == '/pm-dev-builder:builder-build-and-fix'
        assert data['config']['branch_strategy'] == 'direct'


def test_create_config_invalid_domain():
    """Test that invalid domain format fails."""
    with TestContext(plan_id='config-invalid-domain'):
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-invalid-domain',
            '--domains', 'Java'  # Must be lowercase
        )
        assert not result.success, "Expected failure for invalid domain format"
        data = parse_toon(result.stdout)
        assert data['error'] == 'invalid_domain'


# =============================================================================
# Test: Get-Domains Subcommand
# =============================================================================

def test_get_domains_single():
    """Test getting domains array with single domain."""
    with TestContext(plan_id='config-gd-single'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-gd-single',
            '--domains', 'java'
        )
        result = run_script(SCRIPT_PATH, 'get-domains',
            '--plan-id', 'config-gd-single'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['domains'] == ['java']
        assert data['count'] == 1


def test_get_domains_multiple():
    """Test getting domains array with multiple domains."""
    with TestContext(plan_id='config-gd-multi'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-gd-multi',
            '--domains', 'java,javascript'
        )
        result = run_script(SCRIPT_PATH, 'get-domains',
            '--plan-id', 'config-gd-multi'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['count'] == 2
        assert 'java' in data['domains']
        assert 'javascript' in data['domains']


def test_get_domains_not_found():
    """Test get-domains with missing plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get-domains',
            '--plan-id', 'nonexistent'
        )
        assert not result.success, "Expected failure for missing plan"
        data = parse_toon(result.stdout)
        assert data['error'] == 'file_not_found'


# =============================================================================
# Test: Get/Set/Read Operations (Basic Functionality)
# =============================================================================

def test_set_and_get_field():
    """Test setting and getting a config field."""
    with TestContext(plan_id='config-getset'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-getset',
            '--domains', 'java'
        )
        # Set a field
        set_result = run_script(SCRIPT_PATH, 'set',
            '--plan-id', 'config-getset',
            '--field', 'commit_strategy',
            '--value', 'per_plan'
        )
        assert set_result.success, f"Set failed: {set_result.stderr}"

        # Get the field
        get_result = run_script(SCRIPT_PATH, 'get',
            '--plan-id', 'config-getset',
            '--field', 'commit_strategy'
        )
        assert get_result.success, f"Get failed: {get_result.stderr}"
        data = parse_toon(get_result.stdout)
        assert data['value'] == 'per_plan'


def test_read_config():
    """Test reading entire config."""
    with TestContext(plan_id='config-read'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-read',
            '--domains', 'java'
        )
        result = run_script(SCRIPT_PATH, 'read',
            '--plan-id', 'config-read'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert 'config' in data
        assert data['config']['domains'] == ['java']


def test_set_invalid_commit_strategy():
    """Test that setting invalid commit_strategy fails."""
    with TestContext(plan_id='config-invalid-commit'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-invalid-commit',
            '--domains', 'java'
        )
        result = run_script(SCRIPT_PATH, 'set',
            '--plan-id', 'config-invalid-commit',
            '--field', 'commit_strategy',
            '--value', 'invalid_value'
        )
        assert not result.success, "Expected failure for invalid commit_strategy"
        data = parse_toon(result.stdout)
        assert data['error'] == 'invalid_value'
        assert 'valid_values' in data


def test_get_domains_array():
    """Test getting domains array via get command."""
    with TestContext(plan_id='config-get-domains'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-get-domains',
            '--domains', 'java'
        )
        result = run_script(SCRIPT_PATH, 'get',
            '--plan-id', 'config-get-domains',
            '--field', 'domains'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['value'] == ['java']


# =============================================================================
# Test: Get Multi
# =============================================================================

def test_get_multi_fields():
    """Test getting multiple fields in one call."""
    with TestContext(plan_id='config-multi'):
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-multi',
            '--domains', 'java',
            '--commit-strategy', 'per_plan',
            '--branch-strategy', 'direct'
        )
        result = run_script(SCRIPT_PATH, 'get-multi',
            '--plan-id', 'config-multi',
            '--fields', 'commit_strategy,branch_strategy'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['commit_strategy'] == 'per_plan'
        assert data['branch_strategy'] == 'direct'


def test_get_multi_not_found():
    """Test get-multi with missing plan."""
    with TestContext():
        result = run_script(SCRIPT_PATH, 'get-multi',
            '--plan-id', 'nonexistent',
            '--fields', 'commit_strategy'
        )
        assert not result.success, "Expected failure for missing plan"


# =============================================================================
# Test: File Already Exists
# =============================================================================

def test_create_config_already_exists():
    """Test that create fails when config already exists without --force."""
    with TestContext(plan_id='config-exists'):
        # First create
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-exists',
            '--domains', 'java'
        )
        # Second create without --force should fail
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-exists',
            '--domains', 'javascript'
        )
        assert not result.success, "Expected failure when file exists"
        data = parse_toon(result.stdout)
        assert data['error'] == 'file_exists'


def test_create_config_force_overwrite():
    """Test that create with --force overwrites existing config."""
    with TestContext(plan_id='config-force'):
        # First create with java
        run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-force',
            '--domains', 'java'
        )
        # Second create with javascript and --force
        result = run_script(SCRIPT_PATH, 'create',
            '--plan-id', 'config-force',
            '--domains', 'javascript',
            '--force'
        )
        assert result.success, f"Script failed: {result.stderr}"
        data = parse_toon(result.stdout)
        assert data['config']['domains'] == ['javascript']
