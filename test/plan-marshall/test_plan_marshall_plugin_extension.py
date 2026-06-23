#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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


def test_refactor_to_profile_standards_still_registered():
    """The pre-existing recipe is not regressed by the new registration."""
    recipes = _load_extension().provides_recipes()
    recipe = _recipe_by_key(recipes, 'refactor-to-profile-standards')
    assert recipe is not None, 'refactor-to-profile-standards recipe must remain registered'
    assert recipe['skill'] == 'plan-marshall:recipe-refactor-to-profile-standards'


def test_code_review_recipe_registered():
    """recipe-code-review is registered with the expected ext-point-recipe fields."""
    recipes = _load_extension().provides_recipes()
    recipe = _recipe_by_key(recipes, 'code-review')
    assert recipe is not None, 'code-review recipe must be registered'
    assert recipe['skill'] == 'plan-marshall:recipe-code-review'
    assert recipe['default_change_type'] == 'feature'
    assert recipe['scope'] == 'module'
    # All required ext-point-recipe dict keys are present.
    assert {'key', 'name', 'description', 'skill', 'default_change_type', 'scope'} <= recipe.keys()


def test_security_audit_recipe_registered():
    """recipe-security-audit is registered with the expected ext-point-recipe fields."""
    recipes = _load_extension().provides_recipes()
    recipe = _recipe_by_key(recipes, 'security-audit')
    assert recipe is not None, 'security-audit recipe must be registered'
    assert recipe['skill'] == 'plan-marshall:recipe-security-audit'
    assert recipe['default_change_type'] == 'feature'
    assert recipe['scope'] == 'module'
    assert {'key', 'name', 'description', 'skill', 'default_change_type', 'scope'} <= recipe.keys()


def test_discoverable_via_list_recipes(plan_context):
    """The recipe surfaces through list-recipes as a project-local recipe.

    After relocation to .claude/skills/, the recipe is no longer a bundle
    recipe; it is discovered by the project-local scanner. The discovery path
    parses the relocated SKILL.md's `recipe_domain` row end-to-end, so this
    test also proves that row is present and not silently skipped. The recipe
    must surface with the `project:` skill notation and `source: project`
    (NOT the bundle `plan-marshall:` notation).
    """
    result = run_script(_MANAGE_CONFIG, 'list-recipes')
    assert result.success, f'list-recipes should succeed: {result.stderr}'
    data = result.toon()
    recipes = data.get('recipes', [])
    recipe = _recipe_by_key(recipes, 'marshal-json-config-audit')
    assert recipe is not None, 'marshal-json-config-audit must be discovered as a project-local recipe'
    assert recipe['skill'] == 'project:recipe-marshal-json-config-audit'
    assert recipe['source'] == 'project'
