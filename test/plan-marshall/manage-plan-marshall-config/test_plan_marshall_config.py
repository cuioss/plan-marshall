#!/usr/bin/env python3
"""Integration tests for plan-marshall-config.py script.

Happy-path tests verifying the monolithic CLI API.
Detailed variant and corner case tests are in:
- test_cmd_init.py
- test_cmd_skill_domains.py
- test_cmd_system_plan.py
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import SCRIPT_PATH, create_marshal_json, create_nested_marshal_json, create_run_config

from conftest import PlanContext, run_script

# =============================================================================
# Happy-Path Integration Tests
# =============================================================================


def test_init_creates_marshal_json():
    """Test init creates marshal.json with defaults."""
    with PlanContext() as ctx:
        result = run_script(SCRIPT_PATH, 'init')

        assert result.success, f'Init should succeed: {result.stderr}'
        assert 'success' in result.stdout.lower()

        marshal_path = ctx.fixture_dir / 'marshal.json'
        assert marshal_path.exists(), 'marshal.json should be created'


def test_skill_domains_list():
    """Test skill-domains list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'list')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'java' in result.stdout


def test_skill_domains_get():
    """Test skill-domains get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'pm-dev-java:java-create' in result.stdout


def test_system_retention_get():
    """Test system retention get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'system', 'retention', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'logs_days' in result.stdout


def test_plan_defaults_list():
    """Test plan defaults list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'plan', 'defaults', 'list')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'commit_strategy' in result.stdout


def test_resolve_domain_skills():
    """Test resolve-domain-skills command."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-domain-skills', '--domain', 'java', '--profile', 'implementation')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'pm-dev-java:java-create' in result.stdout


def test_get_workflow_skills():
    """Test get-workflow-skills command (5-phase model)."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-workflow-skills')

        assert result.success, f'Should succeed: {result.stderr}'
        # Verify 5-phase model output
        assert 'outline' in result.stdout
        assert 'pm-workflow:phase-2-outline' in result.stdout


def test_error_without_marshal_json():
    """Test operations fail gracefully without marshal.json."""
    with PlanContext():
        # Don't create marshal.json

        result = run_script(SCRIPT_PATH, 'skill-domains', 'list')

        assert 'error' in result.stdout.lower(), 'Should report error'


def test_help_output():
    """Test --help outputs usage information."""
    result = run_script(SCRIPT_PATH, '--help')

    assert result.success, 'Help should succeed'
    assert 'skill-domains' in result.stdout
    assert 'ci' in result.stdout


def test_ci_get():
    """Test ci get returns full CI config."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ci', 'get')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'github' in result.stdout
        assert 'repo_url' in result.stdout


def test_ci_get_provider():
    """Test ci get-provider returns provider info."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ci', 'get-provider')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'github' in result.stdout


def test_ci_get_tools():
    """Test ci get-tools returns authenticated tools from run-configuration.json."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        create_run_config(ctx.fixture_dir)  # Tools are stored in run-configuration.json

        result = run_script(SCRIPT_PATH, 'ci', 'get-tools')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'git' in result.stdout
        assert 'gh' in result.stdout


def test_ci_set_provider():
    """Test ci set-provider updates provider."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'ci', 'set-provider', '--provider', 'gitlab', '--repo-url', 'https://gitlab.com/test/repo'
        )

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'gitlab' in result.stdout


def test_ci_set_tools():
    """Test ci set-tools updates authenticated tools."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ci', 'set-tools', '--tools', 'git,glab,python3')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'glab' in result.stdout


# =============================================================================
# Extension Defaults Tests
# =============================================================================


def test_ext_defaults_set_adds_value():
    """Test ext-defaults set adds a value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'test.key', '--value', 'test-value')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'success' in result.stdout
        assert 'test.key' in result.stdout


def test_ext_defaults_set_updates_existing():
    """Test ext-defaults set overwrites existing value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        # Set initial value
        run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'test.key', '--value', 'initial')

        # Update value
        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'test.key', '--value', 'updated')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'updated' in result.stdout


def test_ext_defaults_set_json_array():
    """Test ext-defaults set with JSON array value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'test.array', '--value', '["a","b","c"]')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'success' in result.stdout


def test_ext_defaults_set_json_object():
    """Test ext-defaults set with JSON object value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'test.obj', '--value', '{"nested": true}')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'success' in result.stdout


def test_ext_defaults_set_plain_string():
    """Test ext-defaults set with plain string (not JSON)."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'test.str', '--value', 'hello-world')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'hello-world' in result.stdout


def test_ext_defaults_get_existing():
    """Test ext-defaults get retrieves existing value."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'my.key', '--value', 'my-value')

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'get', '--key', 'my.key')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'my-value' in result.stdout


def test_ext_defaults_get_nonexistent():
    """Test ext-defaults get returns not_found for missing key."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'get', '--key', 'nonexistent')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'not_found' in result.stdout


def test_ext_defaults_set_default_adds_new():
    """Test ext-defaults set-default adds value when key doesn't exist."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set-default', '--key', 'new.key', '--value', 'new-value')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'success' in result.stdout
        assert 'new-value' in result.stdout


def test_ext_defaults_set_default_skips_existing():
    """Test ext-defaults set-default skips when key exists."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'existing.key', '--value', 'original')

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'set-default', '--key', 'existing.key', '--value', 'new')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'skipped' in result.stdout
        assert 'key_exists' in result.stdout


def test_ext_defaults_list_all():
    """Test ext-defaults list shows all values."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'key1', '--value', 'value1')
        run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'key2', '--value', 'value2')

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'list')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'key1' in result.stdout
        assert 'key2' in result.stdout


def test_ext_defaults_list_empty():
    """Test ext-defaults list with no values."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'list')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'count' in result.stdout


def test_ext_defaults_remove_existing():
    """Test ext-defaults remove deletes existing key."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        run_script(SCRIPT_PATH, 'ext-defaults', 'set', '--key', 'to.remove', '--value', 'value')

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'remove', '--key', 'to.remove')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'removed' in result.stdout


def test_ext_defaults_remove_nonexistent_skips():
    """Test ext-defaults remove skips non-existent key."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'ext-defaults', 'remove', '--key', 'nonexistent')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'skipped' in result.stdout


def test_ext_defaults_help():
    """Test ext-defaults --help shows usage."""
    result = run_script(SCRIPT_PATH, 'ext-defaults', '--help')

    assert result.success, 'Help should succeed'
    assert 'get' in result.stdout
    assert 'set' in result.stdout
    assert 'set-default' in result.stdout


# =============================================================================
# Main
# =============================================================================
