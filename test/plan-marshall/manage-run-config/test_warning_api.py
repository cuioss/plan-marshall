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

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PLAN_DIR_NAME, PlanContext, get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-run-config', 'run_config.py')


# =============================================================================
# Warning Add Tests
# =============================================================================


def test_warning_add_creates_entry():
    """Test warning add creates entry in run-configuration.json."""
    with PlanContext() as ctx:
        # First init the config
        run_script(SCRIPT_PATH, 'init')

        # Add a warning pattern
        result = run_script(
            SCRIPT_PATH,
            'warning',
            'add',
            '--category',
            'transitive_dependency',
            '--pattern',
            'uses commons-logging via spring-core',
        )

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert data['success'] is True, 'Should return success'
        assert data['action'] == 'added', "Action should be 'added'"

        # Verify in config file
        config_path = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
        config = json.loads(config_path.read_text())
        warnings = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'uses commons-logging via spring-core' in warnings, f'Pattern should be in config: {warnings}'


def test_warning_add_skips_duplicate():
    """Test warning add skips duplicate pattern."""
    with PlanContext() as _:
        run_script(SCRIPT_PATH, 'init')

        # Add same pattern twice
        run_script(
            SCRIPT_PATH, 'warning', 'add', '--category', 'transitive_dependency', '--pattern', 'duplicate pattern'
        )
        result = run_script(
            SCRIPT_PATH, 'warning', 'add', '--category', 'transitive_dependency', '--pattern', 'duplicate pattern'
        )

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert data['action'] == 'skipped', 'Should skip duplicate'


def test_warning_add_invalid_category():
    """Test warning add rejects invalid category."""
    with PlanContext() as _:
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH, 'warning', 'add', '--category', 'invalid_category', '--pattern', 'some pattern'
        )

        # argparse should reject invalid category
        assert result.returncode != 0, 'Should reject invalid category'


# =============================================================================
# Warning List Tests
# =============================================================================


def test_warning_list_all_categories():
    """Test warning list returns all categories."""
    with PlanContext() as _:
        run_script(SCRIPT_PATH, 'init')

        # Add patterns to different categories
        run_script(SCRIPT_PATH, 'warning', 'add', '--category', 'transitive_dependency', '--pattern', 'pattern1')
        run_script(SCRIPT_PATH, 'warning', 'add', '--category', 'plugin_compatibility', '--pattern', 'pattern2')

        result = run_script(SCRIPT_PATH, 'warning', 'list')

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert 'categories' in data, 'Should return categories'
        assert 'transitive_dependency' in data['categories'], 'Should have transitive_dependency'
        assert 'plugin_compatibility' in data['categories'], 'Should have plugin_compatibility'


def test_warning_list_single_category():
    """Test warning list with --category filter."""
    with PlanContext() as _:
        run_script(SCRIPT_PATH, 'init')

        run_script(
            SCRIPT_PATH, 'warning', 'add', '--category', 'transitive_dependency', '--pattern', 'filtered pattern'
        )

        result = run_script(SCRIPT_PATH, 'warning', 'list', '--category', 'transitive_dependency')

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert 'patterns' in data, 'Should return patterns'
        assert 'filtered pattern' in data['patterns'], f'Should contain the pattern: {data["patterns"]}'


def test_warning_list_empty():
    """Test warning list on empty config."""
    with PlanContext() as _:
        run_script(SCRIPT_PATH, 'init')

        result = run_script(SCRIPT_PATH, 'warning', 'list')

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert data['success'] is True, 'Should succeed with empty list'


# =============================================================================
# Warning Remove Tests
# =============================================================================


def test_warning_remove_existing():
    """Test warning remove removes existing pattern."""
    with PlanContext() as ctx:
        run_script(SCRIPT_PATH, 'init')

        # Add then remove
        run_script(SCRIPT_PATH, 'warning', 'add', '--category', 'transitive_dependency', '--pattern', 'to be removed')
        result = run_script(
            SCRIPT_PATH, 'warning', 'remove', '--category', 'transitive_dependency', '--pattern', 'to be removed'
        )

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert data['action'] == 'removed', "Action should be 'removed'"

        # Verify removed from config
        config_path = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
        config = json.loads(config_path.read_text())
        warnings = config['maven']['acceptable_warnings']['transitive_dependency']
        assert 'to be removed' not in warnings, 'Pattern should be removed'


def test_warning_remove_nonexistent():
    """Test warning remove skips non-existent pattern."""
    with PlanContext() as _:
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH, 'warning', 'remove', '--category', 'transitive_dependency', '--pattern', 'nonexistent'
        )

        assert result.returncode == 0, f'Should succeed: {result.stderr}'
        data = result.json()
        assert data['action'] == 'skipped', 'Should skip nonexistent'


# =============================================================================
# Build System Parameter Tests
# =============================================================================


def test_warning_add_with_build_system():
    """Test warning add with --build-system parameter."""
    with PlanContext() as ctx:
        run_script(SCRIPT_PATH, 'init')

        result = run_script(
            SCRIPT_PATH,
            'warning',
            'add',
            '--category',
            'transitive_dependency',
            '--pattern',
            'npm warning',
            '--build-system',
            'npm',
        )

        assert result.returncode == 0, f'Should succeed: {result.stderr}'

        # Verify in npm section, not maven
        config_path = ctx.fixture_dir / PLAN_DIR_NAME / 'run-configuration.json'
        config = json.loads(config_path.read_text())
        npm_warnings = config.get('npm', {}).get('acceptable_warnings', {}).get('transitive_dependency', [])
        assert 'npm warning' in npm_warnings, f'Should be in npm section: {config}'


# =============================================================================
# Main
# =============================================================================
