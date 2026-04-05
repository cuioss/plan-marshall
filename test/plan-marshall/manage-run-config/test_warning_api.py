#!/usr/bin/env python3
"""Tests for warning API in run_config.py.

Tests:
- warning add - adds pattern to acceptable list
- warning list - lists accepted warning patterns
- warning remove - removes pattern from acceptable list
- Filtering behavior (actionable mode filters accepted warnings)
- Structured mode shows all with [accepted] markers
"""

import json
from argparse import Namespace

# Direct import - no hyphens in filename
import run_config

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, get_script_path, run_script

cmd_init = run_config.cmd_init
cmd_warning_add = run_config.cmd_warning_add
cmd_warning_list = run_config.cmd_warning_list
cmd_warning_remove = run_config.cmd_warning_remove

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


# =============================================================================
# Warning Add Tests
# =============================================================================


def test_warning_add_creates_entry():
    """Test warning add creates entry in run-configuration.json."""
    with PlanContext() as ctx:
        # First init the config
        cmd_init(Namespace(force=False))

        # Add a warning pattern
        result = cmd_warning_add(
            Namespace(category='transitive_dependency', pattern='uses commons-logging via spring-core',
                      build_system='maven')
        )

        assert result['status'] == 'success', 'Should return success'
        assert result['action'] == 'added', "Action should be 'added'"

        # Verify in config file
        config_path = ctx.fixture_dir / 'run-configuration.json'
        config = json.loads(config_path.read_text())
        warnings = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'uses commons-logging via spring-core' in warnings, f'Pattern should be in config: {warnings}'


def test_warning_add_skips_duplicate():
    """Test warning add skips duplicate pattern."""
    with PlanContext() as _:
        cmd_init(Namespace(force=False))

        # Add same pattern twice
        cmd_warning_add(
            Namespace(category='transitive_dependency', pattern='duplicate pattern', build_system='maven')
        )
        result = cmd_warning_add(
            Namespace(category='transitive_dependency', pattern='duplicate pattern', build_system='maven')
        )

        assert result['status'] == 'success'
        assert result['action'] == 'skipped', 'Should skip duplicate'


def test_warning_add_invalid_category():
    """Test warning add rejects invalid category."""
    with PlanContext() as _:
        cmd_init(Namespace(force=False))

        result = cmd_warning_add(
            Namespace(category='invalid_category', pattern='some pattern', build_system='maven')
        )

        # cmd_warning_add returns error dict for invalid category
        assert result['status'] == 'error', 'Should reject invalid category'


# =============================================================================
# Warning List Tests
# =============================================================================


def test_warning_list_all_categories():
    """Test warning list returns all categories."""
    with PlanContext() as _:
        cmd_init(Namespace(force=False))

        # Add patterns to different categories
        cmd_warning_add(Namespace(category='transitive_dependency', pattern='pattern1', build_system='maven'))
        cmd_warning_add(Namespace(category='plugin_compatibility', pattern='pattern2', build_system='maven'))

        result = cmd_warning_list(Namespace(category=None, build_system='maven'))

        assert result['status'] == 'success'
        assert 'categories' in result, 'Should return categories'
        assert 'transitive_dependency' in result['categories'], 'Should have transitive_dependency'
        assert 'plugin_compatibility' in result['categories'], 'Should have plugin_compatibility'


def test_warning_list_single_category():
    """Test warning list with --category filter."""
    with PlanContext() as _:
        cmd_init(Namespace(force=False))

        cmd_warning_add(
            Namespace(category='transitive_dependency', pattern='filtered pattern', build_system='maven')
        )

        result = cmd_warning_list(Namespace(category='transitive_dependency', build_system='maven'))

        assert result['status'] == 'success'
        assert 'patterns' in result, 'Should return patterns'
        assert 'filtered pattern' in result['patterns'], f'Should contain the pattern: {result["patterns"]}'


def test_warning_list_empty():
    """Test warning list on empty config."""
    with PlanContext() as _:
        cmd_init(Namespace(force=False))

        result = cmd_warning_list(Namespace(category=None, build_system='maven'))

        assert result['status'] == 'success', 'Should succeed with empty list'


# =============================================================================
# Warning Remove Tests
# =============================================================================


def test_warning_remove_existing():
    """Test warning remove removes existing pattern."""
    with PlanContext() as ctx:
        cmd_init(Namespace(force=False))

        # Add then remove
        cmd_warning_add(
            Namespace(category='transitive_dependency', pattern='to be removed', build_system='maven')
        )
        result = cmd_warning_remove(
            Namespace(category='transitive_dependency', pattern='to be removed', build_system='maven')
        )

        assert result['status'] == 'success'
        assert result['action'] == 'removed', "Action should be 'removed'"

        # Verify removed from config
        config_path = ctx.fixture_dir / 'run-configuration.json'
        config = json.loads(config_path.read_text())
        warnings = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'to be removed' not in warnings, 'Pattern should be removed'


def test_warning_remove_nonexistent():
    """Test warning remove skips non-existent pattern."""
    with PlanContext() as _:
        cmd_init(Namespace(force=False))

        result = cmd_warning_remove(
            Namespace(category='transitive_dependency', pattern='nonexistent', build_system='maven')
        )

        assert result['status'] == 'success'
        assert result['action'] == 'skipped', 'Should skip nonexistent'


# =============================================================================
# Build System Parameter Tests
# =============================================================================


def test_warning_add_with_build_system():
    """Test warning add with --build-system parameter."""
    with PlanContext() as ctx:
        cmd_init(Namespace(force=False))

        result = cmd_warning_add(
            Namespace(category='transitive_dependency', pattern='npm warning', build_system='npm')
        )

        assert result['status'] == 'success'

        # Verify in npm section, not maven
        config_path = ctx.fixture_dir / 'run-configuration.json'
        config = json.loads(config_path.read_text())
        npm_warnings = config.get('npm', {}).get('acceptable_warnings', {}).get('transitive_dependency', [])
        assert 'npm warning' in npm_warnings, f'Should be in npm section: {config}'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_warning_add_invalid_category():
    """Test warning add rejects invalid category via argparse."""
    with PlanContext():
        cmd_init(Namespace(force=False))
        result = run_script(SCRIPT_PATH, 'warning', 'add', '--category', 'invalid_category', '--pattern', 'test')
        assert result.returncode != 0, 'Should reject invalid category'


def test_cli_warning_help():
    """Test warning subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'warning', '--help')
    assert result.success
    assert 'add' in result.stdout
    assert 'list' in result.stdout
    assert 'remove' in result.stdout
