#!/usr/bin/env python3
"""Tests for list-recipes and resolve-recipe commands in plan-marshall-config.

Tests recipe listing, resolution, and edge cases.
"""

import json
from pathlib import Path

from test_helpers import SCRIPT_PATH

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script


def _create_marshal_with_recipes(fixture_dir: Path) -> Path:
    """Create marshal.json with recipe entries in skill_domains."""
    config = {
        'skill_domains': {
            'system': {
                'defaults': ['plan-marshall:general-development-rules'],
                'optionals': [],
            },
            'java': {
                'bundle': 'pm-dev-java',
                'recipes': [
                    {
                        'key': 'refactor-to-standards',
                        'name': 'Refactor to Implementation Standards',
                        'description': 'Refactor production code to comply with java-core standards',
                        'skill': 'pm-dev-java:recipe-refactor-to-standards',
                        'default_change_type': 'tech_debt',
                        'scope': 'codebase_wide',
                    },
                    {
                        'key': 'refactor-to-test-standards',
                        'name': 'Refactor to Test Standards',
                        'description': 'Refactor test code to comply with junit-core standards',
                        'skill': 'pm-dev-java:recipe-refactor-to-test-standards',
                        'default_change_type': 'tech_debt',
                        'scope': 'codebase_wide',
                    },
                ],
                'workflow_skill_extensions': {
                    'triage': 'pm-dev-java:ext-triage-java',
                },
            },
        },
        'system': {
            'retention': {'logs_days': 1, 'archived_plans_days': 5, 'memory_days': 5, 'temp_on_maintenance': True}
        },
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95},
            'phase-5-execute': {
                'commit_strategy': 'per_deliverable',
                'verification_max_iterations': 5,
                'verification_1_quality_check': True,
                'verification_2_build_verify': True,
                'verification_domain_steps': {},
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                '1_commit_push': True,
                '2_create_pr': True,
                '3_automated_review': True,
                '4_sonar_roundtrip': True,
                '5_knowledge_capture': True,
                '6_lessons_capture': True,
            },
        },
        'ci': {'repo_url': 'https://github.com/test/repo', 'provider': 'github'},
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))

    # Also create raw-project-data.json (required by some commands)
    raw_data = {
        'project': {'name': 'test-project'},
        'modules': [
            {'name': 'my-core', 'path': 'my-core', 'parent': None, 'build_systems': ['maven'], 'packaging': 'jar'},
        ],
    }
    raw_data_path = fixture_dir / 'raw-project-data.json'
    raw_data_path.write_text(json.dumps(raw_data, indent=2))

    return marshal_path


# =============================================================================
# list-recipes Tests
# =============================================================================


def test_list_recipes_with_recipes():
    """Test list-recipes returns all recipes from configured domains."""
    with PlanContext(plan_id='recipe-list') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'list-recipes')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'success' in result.stdout.lower()
        assert 'refactor-to-standards' in result.stdout
        assert 'refactor-to-test-standards' in result.stdout


def test_list_recipes_count():
    """Test list-recipes returns correct count."""
    with PlanContext(plan_id='recipe-count') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'list-recipes')

        assert result.success, f'Should succeed: {result.stderr}'
        # Count should be 2 (both Java recipes)
        assert '2' in result.stdout


def test_list_recipes_no_recipes():
    """Test list-recipes when no domains have recipes."""
    with PlanContext(plan_id='recipe-empty') as ctx:
        config = {
            'skill_domains': {
                'system': {'defaults': [], 'optionals': []},
                'java': {'bundle': 'pm-dev-java'},
            },
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {},
                'phase-2-refine': {},
                'phase-5-execute': {'verification_domain_steps': {}},
                'phase-6-finalize': {},
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'list-recipes')

        assert result.success, f'Should succeed: {result.stderr}'
        assert '0' in result.stdout


def test_list_recipes_includes_domain():
    """Test list-recipes includes domain key in recipe entries."""
    with PlanContext(plan_id='recipe-domain') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'list-recipes')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'java' in result.stdout


# =============================================================================
# resolve-recipe Tests
# =============================================================================


def test_resolve_recipe_found():
    """Test resolve-recipe returns recipe metadata when found."""
    with PlanContext(plan_id='recipe-resolve') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'refactor-to-standards')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'refactor-to-standards' in result.stdout
        assert 'pm-dev-java:recipe-refactor-to-standards' in result.stdout
        assert 'tech_debt' in result.stdout
        assert 'codebase_wide' in result.stdout
        assert 'java' in result.stdout


def test_resolve_recipe_second_recipe():
    """Test resolve-recipe works for any recipe in the list."""
    with PlanContext(plan_id='recipe-resolve2') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'refactor-to-test-standards')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'refactor-to-test-standards' in result.stdout
        assert 'pm-dev-java:recipe-refactor-to-test-standards' in result.stdout


def test_resolve_recipe_not_found():
    """Test resolve-recipe returns error for unknown recipe."""
    with PlanContext(plan_id='recipe-notfound') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'nonexistent-recipe')

        assert not result.success or 'error' in result.stdout.lower(), 'Should report error'
        assert 'nonexistent-recipe' in result.stdout.lower() or 'not found' in result.stdout.lower()


def test_resolve_recipe_no_recipes_configured():
    """Test resolve-recipe returns error when no recipes exist."""
    with PlanContext(plan_id='recipe-noconfig') as ctx:
        config = {
            'skill_domains': {
                'system': {'defaults': [], 'optionals': []},
            },
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {},
                'phase-2-refine': {},
                'phase-5-execute': {'verification_domain_steps': {}},
                'phase-6-finalize': {},
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'refactor-to-standards')

        assert not result.success or 'error' in result.stdout.lower() or 'not found' in result.stdout.lower()
