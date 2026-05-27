#!/usr/bin/env python3
"""Tests for list-recipes and resolve-recipe commands in manage-config.

Recipes are discovered at runtime from extensions (provides_recipes())
and project recipe-* skills. These tests verify the runtime discovery
by calling list-recipes and resolve-recipe against live extensions.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH

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


_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')

cmd_list_recipes = _cmd_skill_resolution.cmd_list_recipes
cmd_resolve_recipe = _cmd_skill_resolution.cmd_resolve_recipe

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402

# =============================================================================
# list-recipes Tests (Tier 2 - direct import)
# =============================================================================


def test_list_recipes_returns_success(plan_context):
    """Test list-recipes returns success status."""
    result = cmd_list_recipes(Namespace())
    assert result['status'] == 'success'
    assert 'recipes' in result
    assert 'count' in result


def test_list_recipes_includes_project_recipe(plan_context):
    """Test list-recipes discovers project recipe-* skills."""
    result = cmd_list_recipes(Namespace())
    assert result['status'] == 'success'
    # Project has .claude/skills/recipe-plugin-compliance
    recipes_str = str(result['recipes'])
    assert 'plugin-compliance' in recipes_str


def test_list_recipes_includes_domain(plan_context):
    """Test list-recipes includes domain key in recipe entries."""
    result = cmd_list_recipes(Namespace())
    assert result['status'] == 'success'
    recipes_str = str(result['recipes'])
    assert 'plan-marshall-plugin-dev' in recipes_str


# =============================================================================
# resolve-recipe Tests (Tier 2 - direct import)
# =============================================================================


def test_resolve_recipe_found(plan_context):
    """Test resolve-recipe returns recipe metadata for project recipe."""
    result = cmd_resolve_recipe(Namespace(recipe='plugin-compliance'))
    assert result['status'] == 'success'
    assert result['recipe_key'] == 'plugin-compliance'
    assert 'project:recipe-plugin-compliance' in result['recipe_skill']
    assert result['domain'] == 'plan-marshall-plugin-dev'


def test_resolve_recipe_returns_profile(plan_context):
    """Test resolve-recipe returns profile from project recipe metadata."""
    result = cmd_resolve_recipe(Namespace(recipe='plugin-compliance'))
    assert result['status'] == 'success'
    assert result['profile'] == 'implementation'


def test_resolve_recipe_not_found(plan_context):
    """Test resolve-recipe returns error for unknown recipe."""
    result = cmd_resolve_recipe(Namespace(recipe='nonexistent-recipe'))
    assert result['status'] == 'error'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_list_recipes(plan_context):
    """Test CLI plumbing: list-recipes outputs TOON."""
    result = run_script(SCRIPT_PATH, 'list-recipes')
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'success' in result.stdout.lower()


def test_cli_resolve_recipe(plan_context):
    """Test CLI plumbing: resolve-recipe outputs TOON."""
    result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'plugin-compliance')
    assert result.success, f'Should succeed: {result.stderr}'
    assert 'plugin-compliance' in result.stdout
