#!/usr/bin/env python3
"""Tests for the plan-marshall-plugin extension's provides_recipes().

Guards the registration of built-in recipes returned by the plan-marshall
bundle's Extension. The recipes are the static list literal that
manage-config list-recipes / resolve-recipe discover at runtime.

Tier 2 (direct import): loads the bundle extension.py and inspects the
provides_recipes() return value directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, get_script_path, run_script

_MANAGE_CONFIG = get_script_path('plan-marshall', 'manage-config', 'manage-config.py')

# Required ext-point-recipe fields every recipe dict must carry.
REQUIRED_RECIPE_FIELDS = {
    'key',
    'name',
    'description',
    'skill',
    'default_change_type',
    'scope',
}


def _load_extension():
    """Load the plan-marshall bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_plan_marshall', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _recipe_by_key(recipes, key):
    """Return the single recipe dict with the given key, or None."""
    matches = [r for r in recipes if r.get('key') == key]
    return matches[0] if matches else None


def test_provides_recipes_returns_list():
    """provides_recipes() returns a non-empty list of dicts."""
    recipes = _load_extension().provides_recipes()
    assert isinstance(recipes, list)
    assert recipes, 'provides_recipes() must not be empty'
    assert all(isinstance(r, dict) for r in recipes)


def test_provides_recipes_includes_marshal_json_config_audit():
    """The marshal-json-config-audit recipe is registered with all required fields."""
    recipes = _load_extension().provides_recipes()
    recipe = _recipe_by_key(recipes, 'marshal-json-config-audit')
    assert recipe is not None, 'marshal-json-config-audit recipe must be registered'
    assert REQUIRED_RECIPE_FIELDS.issubset(recipe.keys())


def test_marshal_json_config_audit_field_values():
    """The marshal-json-config-audit recipe carries the expected field values."""
    recipes = _load_extension().provides_recipes()
    recipe = _recipe_by_key(recipes, 'marshal-json-config-audit')
    assert recipe is not None
    assert recipe['skill'] == 'plan-marshall:recipe-marshal-json-config-audit'
    assert recipe['default_change_type'] == 'tech_debt'
    assert recipe['scope'] == 'module'
    assert recipe['coverage_gathering'] == 'none'


def test_refactor_to_profile_standards_still_registered():
    """The pre-existing recipe is not regressed by the new registration."""
    recipes = _load_extension().provides_recipes()
    recipe = _recipe_by_key(recipes, 'refactor-to-profile-standards')
    assert recipe is not None, 'refactor-to-profile-standards recipe must remain registered'
    assert recipe['skill'] == 'plan-marshall:recipe-refactor-to-profile-standards'


def test_discoverable_via_list_recipes(plan_context):
    """The recipe surfaces through the manage-config list-recipes discovery path."""
    result = run_script(_MANAGE_CONFIG, 'list-recipes')
    assert result.success, f'list-recipes should succeed: {result.stderr}'
    assert 'marshal-json-config-audit' in result.stdout
    assert 'plan-marshall:recipe-marshal-json-config-audit' in result.stdout
