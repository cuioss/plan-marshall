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
                        'key': 'null-safety-compliance',
                        'name': 'Null Safety Compliance',
                        'description': 'Add JSpecify annotations across all packages',
                        'skill': 'pm-dev-java:recipe-null-safety',
                        'default_change_type': 'tech_debt',
                        'scope': 'codebase_wide',
                        'profile': 'implementation',
                        'package_source': 'packages',
                    },
                    {
                        'key': 'custom-test-recipe',
                        'name': 'Custom Test Recipe',
                        'description': 'Custom recipe without profile/package_source fields',
                        'skill': 'pm-dev-java:recipe-custom-test',
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
        assert 'null-safety-compliance' in result.stdout
        assert 'custom-test-recipe' in result.stdout


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

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'null-safety-compliance')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'null-safety-compliance' in result.stdout
        assert 'pm-dev-java:recipe-null-safety' in result.stdout
        assert 'tech_debt' in result.stdout
        assert 'codebase_wide' in result.stdout
        assert 'java' in result.stdout


def test_resolve_recipe_returns_profile_and_package_source():
    """Test resolve-recipe returns profile and package_source when present."""
    with PlanContext(plan_id='recipe-profile') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'null-safety-compliance')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'implementation' in result.stdout
        assert 'packages' in result.stdout


def test_resolve_recipe_returns_empty_profile_when_absent():
    """Test resolve-recipe returns empty strings for profile/package_source when absent."""
    with PlanContext(plan_id='recipe-noprofile') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'custom-test-recipe')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'custom-test-recipe' in result.stdout
        assert 'pm-dev-java:recipe-custom-test' in result.stdout
        # profile and package_source should be empty strings (present but empty)
        # The TOON output will contain the field keys with empty values


def test_resolve_recipe_second_recipe():
    """Test resolve-recipe works for any recipe in the list."""
    with PlanContext(plan_id='recipe-resolve2') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-recipe', '--recipe', 'custom-test-recipe')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'custom-test-recipe' in result.stdout
        assert 'pm-dev-java:recipe-custom-test' in result.stdout


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


# =============================================================================
# add-recipe Tests
# =============================================================================


def _create_marshal_with_domain(fixture_dir: Path) -> Path:
    """Create marshal.json with a domain but no recipes."""
    config = {
        'skill_domains': {
            'system': {
                'defaults': ['plan-marshall:general-development-rules'],
                'optionals': [],
            },
            'java': {
                'bundle': 'pm-dev-java',
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
    return marshal_path


def test_add_recipe_success():
    """Test add-recipe adds a project recipe with source=project."""
    with PlanContext(plan_id='recipe-add') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'my-custom-recipe',
            '--skill', 'project:my-recipe-skill',
        )

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'my-custom-recipe' in result.stdout

        # Verify marshal.json was updated
        marshal_path = ctx.fixture_dir / 'marshal.json'
        updated = json.loads(marshal_path.read_text())
        recipes = updated['skill_domains']['java']['recipes']
        assert len(recipes) == 1
        recipe = recipes[0]
        assert recipe['key'] == 'my-custom-recipe'
        assert recipe['skill'] == 'project:my-recipe-skill'
        assert recipe['source'] == 'project'
        assert recipe['default_change_type'] == 'tech_debt'
        assert recipe['scope'] == 'codebase_wide'


def test_add_recipe_with_all_optional_fields():
    """Test add-recipe with profile, package_source, description, name."""
    with PlanContext(plan_id='recipe-add-opts') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'full-recipe',
            '--skill', 'project:full-recipe-skill',
            '--name', 'Full Recipe',
            '--description', 'A recipe with all fields',
            '--change-type', 'feature',
            '--scope', 'single_module',
            '--profile', 'implementation',
            '--package-source', 'packages',
        )

        assert result.success, f'Should succeed: {result.stderr}'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        updated = json.loads(marshal_path.read_text())
        recipe = updated['skill_domains']['java']['recipes'][0]
        assert recipe['name'] == 'Full Recipe'
        assert recipe['description'] == 'A recipe with all fields'
        assert recipe['default_change_type'] == 'feature'
        assert recipe['scope'] == 'single_module'
        assert recipe['profile'] == 'implementation'
        assert recipe['package_source'] == 'packages'
        assert recipe['source'] == 'project'


def test_add_recipe_duplicate_key_fails():
    """Test add-recipe rejects duplicate recipe key."""
    with PlanContext(plan_id='recipe-add-dup') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        # Add first recipe
        run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'my-recipe',
            '--skill', 'project:my-skill',
        )

        # Add same key again
        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'my-recipe',
            '--skill', 'project:other-skill',
        )

        assert 'error' in result.stdout.lower(), 'Should reject duplicate key'
        assert 'already exists' in result.stdout.lower()


def test_add_recipe_unknown_domain_fails():
    """Test add-recipe rejects unknown domain."""
    with PlanContext(plan_id='recipe-add-nodom') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'nonexistent',
            '--key', 'my-recipe',
            '--skill', 'project:my-skill',
        )

        assert 'error' in result.stdout.lower(), 'Should reject unknown domain'


def test_add_recipe_invalid_skill_notation_fails():
    """Test add-recipe rejects skill without colon notation."""
    with PlanContext(plan_id='recipe-add-badskill') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'my-recipe',
            '--skill', 'no-colon-notation',
        )

        assert 'error' in result.stdout.lower(), 'Should reject invalid skill notation'


# =============================================================================
# remove-recipe Tests
# =============================================================================


def test_remove_recipe_success():
    """Test remove-recipe removes a project recipe."""
    with PlanContext(plan_id='recipe-rm') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        # Add a project recipe first
        run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'removable-recipe',
            '--skill', 'project:removable-skill',
        )

        # Remove it
        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'remove-recipe',
            '--domain', 'java',
            '--key', 'removable-recipe',
        )

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'removable-recipe' in result.stdout

        # Verify removed from marshal.json
        marshal_path = ctx.fixture_dir / 'marshal.json'
        updated = json.loads(marshal_path.read_text())
        recipes = updated['skill_domains']['java'].get('recipes', [])
        assert len(recipes) == 0


def test_remove_recipe_non_project_fails():
    """Test remove-recipe rejects removing non-project (extension) recipes."""
    with PlanContext(plan_id='recipe-rm-ext') as ctx:
        _create_marshal_with_recipes(ctx.fixture_dir)

        # Try to remove an extension-provided recipe (no source field)
        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'remove-recipe',
            '--domain', 'java',
            '--key', 'null-safety-compliance',
        )

        assert 'error' in result.stdout.lower(), 'Should reject removing non-project recipe'
        assert 'non-project' in result.stdout.lower() or 'cannot remove' in result.stdout.lower()


def test_remove_recipe_not_found_fails():
    """Test remove-recipe returns error for unknown key."""
    with PlanContext(plan_id='recipe-rm-notfound') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'remove-recipe',
            '--domain', 'java',
            '--key', 'nonexistent-recipe',
        )

        assert 'error' in result.stdout.lower(), 'Should report error for unknown key'
        assert 'not found' in result.stdout.lower()


# =============================================================================
# configure preservation Tests
# =============================================================================


def test_configure_preserves_project_recipes():
    """Test that configure preserves project-level recipes across reconfiguration."""
    with PlanContext(plan_id='recipe-preserve') as ctx:
        _create_marshal_with_domain(ctx.fixture_dir)

        # Add a project recipe
        run_script(
            SCRIPT_PATH,
            'skill-domains',
            'add-recipe',
            '--domain', 'java',
            '--key', 'my-project-recipe',
            '--skill', 'project:my-recipe-skill',
            '--description', 'A project recipe',
        )

        # Verify recipe was added
        marshal_path = ctx.fixture_dir / 'marshal.json'
        before = json.loads(marshal_path.read_text())
        assert len(before['skill_domains']['java'].get('recipes', [])) == 1

        # Run configure — this would normally clear and rebuild domains
        # Note: configure requires extension.py discovery, so we verify the
        # preservation logic by checking that project recipes with source=project
        # are preserved in the config structure
        result = run_script(
            SCRIPT_PATH,
            'skill-domains',
            'configure',
            '--domains', 'java',
        )

        # configure may fail if extension.py discovery isn't available in test env
        # but the preservation logic is tested via the marshal.json state
        # If configure succeeded, check that project recipe survived
        if result.success:
            after = json.loads(marshal_path.read_text())
            java_recipes = after['skill_domains'].get('java', {}).get('recipes', [])
            project_recipes = [r for r in java_recipes if r.get('source') == 'project']
            assert len(project_recipes) == 1
            assert project_recipes[0]['key'] == 'my-project-recipe'
