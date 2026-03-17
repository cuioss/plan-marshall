#!/usr/bin/env python3
"""Tests for list-recipes and resolve-recipe commands in manage-config.

Recipes are discovered at runtime from extensions (provides_recipes())
and project recipe-* skills. These tests verify the runtime discovery
by calling list-recipes and resolve-recipe against live extensions.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from test_helpers import SCRIPT_PATH

from conftest import PlanContext, run_script

# =============================================================================
# list-recipes Tests (runtime discovery)
# =============================================================================


def test_list_recipes_returns_success():
    """Test list-recipes returns success status."""
    with PlanContext(plan_id='recipe-list'):
        result = run_script(SCRIPT_PATH, 'list-recipes')
        assert result.success, f'Should succeed: {result.stderr}'
        assert 'success' in result.stdout.lower()


def test_list_recipes_includes_project_recipe():
    """Test list-recipes discovers project recipe-* skills."""
    with PlanContext(plan_id='recipe-project'):
        result = run_script(SCRIPT_PATH, 'list-recipes')
        assert result.success, f'Should succeed: {result.stderr}'
        # Project has .claude/skills/recipe-plugin-compliance
        assert 'plugin-compliance' in result.stdout


def test_list_recipes_includes_domain():
    """Test list-recipes includes domain key in recipe entries."""
    with PlanContext(plan_id='recipe-domain'):
        result = run_script(SCRIPT_PATH, 'list-recipes')
        assert result.success, f'Should succeed: {result.stderr}'
        assert 'plan-marshall-plugin-dev' in result.stdout


# =============================================================================
# resolve-recipe Tests (runtime discovery)
# =============================================================================


def test_resolve_recipe_found():
    """Test resolve-recipe returns recipe metadata for project recipe."""
    with PlanContext(plan_id='recipe-resolve'):
        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'plugin-compliance')
        assert result.success, f'Should succeed: {result.stderr}'
        assert 'plugin-compliance' in result.stdout
        assert 'project:recipe-plugin-compliance' in result.stdout
        assert 'plan-marshall-plugin-dev' in result.stdout


def test_resolve_recipe_returns_profile():
    """Test resolve-recipe returns profile from project recipe metadata."""
    with PlanContext(plan_id='recipe-profile'):
        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'plugin-compliance')
        assert result.success, f'Should succeed: {result.stderr}'
        assert 'implementation' in result.stdout


def test_resolve_recipe_not_found():
    """Test resolve-recipe returns error for unknown recipe."""
    with PlanContext(plan_id='recipe-notfound'):
        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'nonexistent-recipe')
        assert not result.success or 'error' in result.stdout.lower(), 'Should report error'
