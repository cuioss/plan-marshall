#!/usr/bin/env python3
"""Tests for skill-domains commands in manage-config.

Tests skill-domains, resolve-domain-skills commands
including nested structure variants and edge cases.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH, create_marshal_json, create_nested_marshal_json, patch_config_paths

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')
_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')

cmd_list_verify_steps = _cmd_skill_domains.cmd_list_verify_steps
cmd_skill_domains = _cmd_skill_domains.cmd_skill_domains
cmd_get_skills_by_profile = _cmd_skill_resolution.cmd_get_skills_by_profile
cmd_list_finalize_steps = _cmd_skill_resolution.cmd_list_finalize_steps
cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills
cmd_resolve_workflow_skill_extension = _cmd_skill_resolution.cmd_resolve_workflow_skill_extension

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import PlanContext, run_script  # noqa: E402

# =============================================================================
# skill-domains Basic Tests (Flat Structure) - Tier 2
# =============================================================================


def test_skill_domains_list():
    """Test skill-domains list."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='list'))

        assert result['status'] == 'success'
        assert 'java' in result['domains']


def test_skill_domains_get():
    """Test skill-domains get."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get', domain='java'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:java-core' in result['defaults']


def test_skill_domains_get_defaults():
    """Test skill-domains get-defaults."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-defaults', domain='java'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:java-core' in result['defaults']


def test_skill_domains_get_optionals():
    """Test skill-domains get-optionals."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-optionals', domain='java'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:java-cdi' in result['optionals']


def test_skill_domains_unknown_domain():
    """Test skill-domains get with unknown domain returns error."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get', domain='unknown'))

        assert result['status'] == 'error'
        assert 'unknown' in result['error'].lower()


def test_skill_domains_add():
    """Test skill-domains add."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='add',
            domain='python',
            defaults='pm-dev-python:cui-python-core',
            optionals=None,
        ))

        assert result['status'] == 'success'

        # Verify added
        verify = cmd_skill_domains(Namespace(verb='get', domain='python'))
        assert 'pm-dev-python:cui-python-core' in verify['defaults']


def test_skill_domains_validate():
    """Test skill-domains validate."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='validate',
            domain='java',
            skill='pm-dev-java:java-core',
        ))

        assert result['status'] == 'success'
        assert result['valid'] is True


def test_skill_domains_validate_returns_location():
    """Test skill-domains validate returns in_defaults or in_optionals."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        # Skill in defaults
        result_defaults = cmd_skill_domains(Namespace(
            verb='validate', domain='java', skill='pm-dev-java:java-core',
        ))
        assert result_defaults['in_defaults'] is True

        # Skill in optionals
        result_optionals = cmd_skill_domains(Namespace(
            verb='validate', domain='java', skill='pm-dev-java:java-cdi',
        ))
        assert result_optionals['in_optionals'] is True


def test_skill_domains_validate_invalid_skill():
    """Test skill-domains validate with invalid skill returns false."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='validate', domain='java', skill='pm-dev-java:invalid-skill',
        ))

        assert result['status'] == 'success'
        assert result['valid'] is False


# =============================================================================
# skill-domains Nested Structure Tests (Tier 2)
# =============================================================================


def test_skill_domains_get_nested_structure():
    """Test skill-domains get returns nested structure for domains with bundle reference."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get', domain='java'))

        assert result['status'] == 'success'
        assert 'bundle' in result
        assert result['bundle'] == 'pm-dev-java'
        assert 'workflow_skill_extensions' in result


def test_skill_domains_get_defaults_nested():
    """Test skill-domains get-defaults loads core.defaults from extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-defaults', domain='java'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        assert 'pm-dev-java:java-core' in defaults_str


def test_skill_domains_get_optionals_nested():
    """Test skill-domains get-optionals loads core.optionals from extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-optionals', domain='java'))

        assert result['status'] == 'success'
        optionals_str = str(result['optionals'])
        assert 'pm-dev-java:java-null-safety' in optionals_str
        assert 'pm-dev-java:java-lombok' in optionals_str


def test_skill_domains_validate_nested():
    """Test skill-domains validate loads profiles from extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate', '--domain', 'java', '--skill', 'pm-dev-java:java-core'
        )
        assert result.success, f'Should succeed: {result.stderr}'
        assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()


def test_skill_domains_validate_nested_profile_skill():
    """Test skill-domains validate finds skills in profile blocks loaded from extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate', '--domain', 'java', '--skill', 'pm-dev-java:junit-core'
        )
        assert result.success, f'Should succeed: {result.stderr}'
        assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()
        assert 'in_defaults' in result.stdout.lower()


def test_skill_domains_get_system_has_task_executors():
    """Test skill-domains get returns system domain with task_executors."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get', domain='system'))

        assert result['status'] == 'success'
        assert 'defaults' in result
        assert 'plan-marshall:general-development-rules' in result['defaults']
        assert 'task_executors' in result


# =============================================================================
# skill-domains detect Tests (Tier 2)
# =============================================================================


def test_skill_domains_detect_runs():
    """Test skill-domains detect command runs successfully."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {'system': {'defaults': ['plan-marshall:dev-general-practices'], 'optionals': []}},
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='detect'))

        assert result['status'] == 'success'
        assert 'detected' in result


def test_skill_domains_detect_no_overwrite():
    """Test skill-domains detect does not overwrite existing domains."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {
                'system': {'defaults': [], 'optionals': []},
                'java': {
                    'bundle': 'custom-java-bundle',
                    'workflow_skill_extensions': {'outline': 'custom:outline-skill'},
                },
            },
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='detect'))

        assert result['status'] == 'success'

        # Verify existing java domain was NOT overwritten
        verify = cmd_skill_domains(Namespace(verb='get', domain='java'))
        assert verify['bundle'] == 'custom-java-bundle'


# =============================================================================
# resolve-domain-skills Tests (Tier 2)
# =============================================================================


def test_resolve_domain_skills_java_implementation():
    """Test resolve-domain-skills for java + implementation profile."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        assert 'pm-dev-java:java-core' in defaults_str
        optionals_str = str(result['optionals'])
        assert 'pm-dev-java:java-cdi' in optionals_str
        # Should NOT include testing defaults
        assert 'pm-dev-java:junit-core' not in defaults_str


def test_resolve_domain_skills_java_testing():
    """Test resolve-domain-skills for java + module_testing profile."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='module_testing'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        optionals_str = str(result['optionals'])
        assert 'pm-dev-java:java-core' in defaults_str
        assert 'pm-dev-java:junit-core' in defaults_str
        assert 'pm-dev-java:junit-integration' in optionals_str
        # Should NOT include implementation optionals
        assert 'pm-dev-java:java-cdi' not in optionals_str


def test_resolve_domain_skills_javascript_implementation():
    """Test resolve-domain-skills for javascript + implementation profile."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='javascript', profile='implementation'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        optionals_str = str(result['optionals'])
        assert 'pm-dev-frontend:javascript' in defaults_str
        assert 'pm-dev-frontend:lint-config' in optionals_str


def test_resolve_domain_skills_unknown_domain():
    """Test resolve-domain-skills with unknown domain returns error."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='unknown', profile='implementation'))

        assert result['status'] == 'error'
        assert 'unknown' in result['error'].lower()


def test_resolve_domain_skills_unknown_profile():
    """Test resolve-domain-skills with unknown profile returns error."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='invalid-profile'))

        assert result['status'] == 'error'
        assert 'profile' in result['error'].lower()


def test_resolve_domain_skills_java_quality():
    """Test resolve-domain-skills for java + quality profile (finalize phase)."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_domain_skills(Namespace(domain='java', profile='quality'))

        assert result['status'] == 'success'
        defaults_str = str(result['defaults'])
        assert 'pm-dev-java:java-core' in defaults_str
        assert 'pm-dev-java:javadoc' in defaults_str


# =============================================================================
# resolve-workflow-skill-extension Tests (Tier 2)
# =============================================================================


def test_resolve_workflow_skill_extension_java_outline():
    """Test resolve-workflow-skill-extension returns outline extension for java."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='java', type='outline'))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-dev-java:ext-outline-java'
        assert result['domain'] == 'java'
        assert result['type'] == 'outline'


def test_resolve_workflow_skill_extension_java_triage():
    """Test resolve-workflow-skill-extension returns triage extension for java."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='java', type='triage'))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-dev-java:ext-triage-java'


def test_resolve_workflow_skill_extension_javascript_outline():
    """Test resolve-workflow-skill-extension returns outline extension for javascript."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='javascript', type='outline'))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-dev-frontend:ext-outline-frontend'


def test_resolve_workflow_skill_extension_missing_type():
    """Test resolve-workflow-skill-extension returns null for missing extension type."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='javascript', type='triage'))

        assert result['status'] == 'success'
        assert result['extension'] is None


def test_resolve_workflow_skill_extension_unknown_domain():
    """Test resolve-workflow-skill-extension returns null for unknown domain (not error)."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(domain='unknown', type='outline'))

        assert result['status'] == 'success'
        assert result['extension'] is None


def test_resolve_workflow_skill_extension_plugin_dev():
    """Test resolve-workflow-skill-extension returns extensions for plugin-dev domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_resolve_workflow_skill_extension(Namespace(
            domain='plan-marshall-plugin-dev', type='outline',
        ))

        assert result['status'] == 'success'
        assert result['extension'] == 'pm-plugin-development:ext-outline-workflow'


# =============================================================================
# get-extensions / set-extensions Tests (Tier 2)
# =============================================================================


def test_get_extensions_java():
    """Test get-extensions returns extensions for java domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-extensions', domain='java'))

        assert result['status'] == 'success'
        assert 'extensions' in result
        assert 'outline' in result['extensions']
        assert 'triage' in result['extensions']


def test_get_extensions_unknown_domain():
    """Test get-extensions returns error for unknown domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-extensions', domain='unknown'))

        assert result['status'] == 'error'


def test_set_extensions():
    """Test set-extensions adds extension to domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='set-extensions',
            domain='java',
            type='triage',
            skill='pm-dev-java:new-triage',
        ))

        assert result['status'] == 'success'
        assert result['type'] == 'triage'
        assert result['skill'] == 'pm-dev-java:new-triage'


# =============================================================================
# get-available / configure Tests (Tier 2)
# =============================================================================


def test_get_available_uses_discovery():
    """Test get-available uses discovery for domains."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {'system': {'defaults': []}},
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-available'))

        assert result['status'] == 'success'
        assert 'discovered_domains' in result


def test_configure_domains():
    """Test configure adds system domain and selected domains."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {},
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='configure', domains='java,javascript'))

        assert result['status'] == 'success'
        assert 'system_domain' in result

        # Verify marshal.json was updated
        updated = json.loads(marshal_path.read_text())
        assert 'system' in updated['skill_domains']
        assert 'java' in updated['skill_domains']
        assert 'javascript' in updated['skill_domains']


def test_configure_always_adds_system():
    """Test configure always adds system domain even with empty selection."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {},
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='configure', domains=''))

        assert result['status'] == 'success'

        updated = json.loads(marshal_path.read_text())
        assert 'system' in updated['skill_domains']


# =============================================================================
# set with --profile Tests (Tier 2)
# =============================================================================


def test_set_with_profile_returns_error():
    """Test set with --profile returns error since profiles are in extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='set',
            domain='java',
            profile='quality',
            defaults='pm-dev-java:new-skill',
            optionals=None,
        ))

        assert result['status'] == 'error'


# =============================================================================
# get-skills-by-profile Tests (Tier 2)
# =============================================================================


def test_get_skills_by_profile_java():
    """Test get-skills-by-profile loads profile-keyed skills from extension.py."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        assert 'skills_by_profile' in result
        assert 'implementation' in result['skills_by_profile']
        assert 'module_testing' in result['skills_by_profile']
        # integration_testing should NOT appear as standalone profile for java
        assert 'integration_testing' not in result['skills_by_profile']


def test_get_skills_by_profile_includes_core_skills():
    """Test get-skills-by-profile includes core skills in all profiles."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        # Core skill should appear in every profile
        for profile_skills in result['skills_by_profile'].values():
            assert 'pm-dev-java:java-core' in profile_skills


def test_get_skills_by_profile_includes_profile_skills():
    """Test get-skills-by-profile includes profile-specific skills."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        assert 'pm-dev-java:junit-core' in result['skills_by_profile']['module_testing']


def test_get_skills_by_profile_javascript():
    """Test get-skills-by-profile works for javascript domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='javascript'))

        assert result['status'] == 'success'
        assert 'skills_by_profile' in result
        all_skills = str(result['skills_by_profile'])
        assert 'pm-dev-frontend:javascript' in all_skills


def test_get_skills_by_profile_unknown_domain():
    """Test get-skills-by-profile returns error for unknown domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='unknown'))

        assert result['status'] == 'error'
        assert 'unknown' in result['error'].lower()


def test_get_skills_by_profile_flat_domain_fallback():
    """Test get-skills-by-profile returns core skills for flat structure domain (no bundle)."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_get_skills_by_profile(Namespace(domain='java'))

        assert result['status'] == 'success'
        assert 'skills_by_profile' in result


# =============================================================================
# Tests for verbs that work without skill_domains (Tier 2)
# =============================================================================


def test_get_available_works_without_skill_domains():
    """Test get-available works without skill_domains being configured."""
    with PlanContext() as ctx:
        config = {
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get-available'))

        assert result['status'] == 'success'
        assert 'discovered_domains' in result


def test_configure_works_without_skill_domains():
    """Test configure works without skill_domains being configured."""
    with PlanContext() as ctx:
        config = {
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

        assert result['status'] == 'success'
        assert 'system_domain' in result

        updated = json.loads(marshal_path.read_text())
        assert 'skill_domains' in updated
        assert 'system' in updated['skill_domains']
        assert 'java' in updated['skill_domains']


def test_list_requires_skill_domains():
    """Test list verb requires skill_domains to be configured."""
    with PlanContext() as ctx:
        config = {
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='list'))

        assert result['status'] == 'error'
        assert 'skill_domains not configured' in result['error']


# =============================================================================
# Project Skills Tests (Tier 2)
# =============================================================================


def test_discover_project_discovers_skills():
    """Test discover-project finds skills in .claude/skills/.

    This test scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        # Create .claude/skills/ with a test skill (relative to cwd)
        skills_dir = Path('.claude/skills/test-skill')
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skills_dir / 'SKILL.md'
        skill_md.write_text('---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\n')

        try:
            result = run_script(SCRIPT_PATH, 'skill-domains', 'discover-project')

            assert result.success, f'Should succeed: {result.stderr}'
            assert 'project:test-skill' in result.stdout
        finally:
            skill_md.unlink()
            skills_dir.rmdir()


def test_discover_project_returns_structured_output():
    """Test discover-project returns TOON output with status, count, and skills fields."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'discover-project')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'count: ' in result.stdout


def test_attach_project_to_domain():
    """Test attach-project adds project skills to a domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='attach-project',
            domain='java',
            skills='project:my-custom-skill',
        ))

        assert result['status'] == 'success'
        assert 'project:my-custom-skill' in result['project_skills']

        # Verify marshal.json was updated
        marshal_path = ctx.fixture_dir / 'marshal.json'
        updated = json.loads(marshal_path.read_text())
        assert 'project:my-custom-skill' in updated['skill_domains']['java']['project_skills']


def test_attach_project_to_system_domain():
    """Test attach-project works with system domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='attach-project',
            domain='system',
            skills='project:cross-domain-skill',
        ))

        assert result['status'] == 'success'

        marshal_path = ctx.fixture_dir / 'marshal.json'
        updated = json.loads(marshal_path.read_text())
        assert 'project:cross-domain-skill' in updated['skill_domains']['system']['project_skills']


def test_attach_project_rejects_invalid_notation():
    """Test attach-project rejects skills not starting with project:."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='attach-project',
            domain='java',
            skills='pm-dev-java:invalid-notation',
        ))

        assert result['status'] == 'error'


def test_attach_project_rejects_unknown_domain():
    """Test attach-project rejects unknown domain."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(
            verb='attach-project',
            domain='nonexistent',
            skills='project:some-skill',
        ))

        assert result['status'] == 'error'


def test_attach_project_no_duplicates():
    """Test attach-project does not add duplicate skills."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        # Attach first time
        cmd_skill_domains(Namespace(verb='attach-project', domain='java', skills='project:my-skill'))

        # Attach same skill again
        cmd_skill_domains(Namespace(verb='attach-project', domain='java', skills='project:my-skill'))

        # Verify no duplicate
        marshal_path = ctx.fixture_dir / 'marshal.json'
        updated = json.loads(marshal_path.read_text())
        project_skills = updated['skill_domains']['java']['project_skills']
        assert project_skills.count('project:my-skill') == 1


def test_configure_preserves_project_skills():
    """Test configure preserves existing project_skills when reconfiguring domains."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {
                'system': {
                    'defaults': ['plan-marshall:dev-general-practices'],
                    'project_skills': ['project:system-skill'],
                    'task_executors': {'implementation': 'plan-marshall:task-implementation'},
                },
                'java': {
                    'bundle': 'pm-dev-java',
                    'project_skills': ['project:java-helper'],
                    'workflow_skill_extensions': {'triage': 'pm-dev-java:ext-triage-java'},
                },
            },
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

        assert result['status'] == 'success'

        updated = json.loads(marshal_path.read_text())
        assert 'project:system-skill' in updated['skill_domains']['system']['project_skills']
        assert 'project:java-helper' in updated['skill_domains']['java']['project_skills']


def test_configure_drops_project_skills_for_removed_domains():
    """Test configure drops project_skills for domains that are no longer selected."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {
                'system': {'defaults': [], 'task_executors': {}},
                'java': {'bundle': 'pm-dev-java', 'project_skills': ['project:java-helper']},
                'javascript': {'bundle': 'pm-dev-frontend', 'project_skills': ['project:js-helper']},
            },
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='configure', domains='java'))

        assert result['status'] == 'success'

        updated = json.loads(marshal_path.read_text())
        assert 'project:java-helper' in updated['skill_domains']['java'].get('project_skills', [])
        assert 'javascript' not in updated['skill_domains']


def test_get_nested_includes_project_skills():
    """Test skill-domains get includes project_skills in output for nested domains."""
    with PlanContext() as ctx:
        config = {
            'skill_domains': {
                'system': {
                    'defaults': ['plan-marshall:dev-general-practices'],
                    'project_skills': ['project:my-tool'],
                    'task_executors': {},
                },
            },
            'system': {'retention': {}},
            'plan': {
                'phase-1-init': {'branch_strategy': 'direct'},
                'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
                'phase-5-execute': {
                    'commit_strategy': 'per_deliverable',
                    'verification_max_iterations': 5,
                    'steps': ['default:quality_check', 'default:build_verify'],
                },
                'phase-6-finalize': {
                    'max_iterations': 3,
                    'review_bot_buffer_seconds': 300,
                    'steps': [
                        'default:commit-push',
                        'default:create-pr',
                        'default:automated-review',
                        'default:sonar-roundtrip',
                        'default:knowledge-capture',
                        'default:lessons-capture',
                        'default:branch-cleanup',
                        'default:archive-plan',
                    ],
                },
            },
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))
        patch_config_paths(ctx.fixture_dir)

        result = cmd_skill_domains(Namespace(verb='get', domain='system'))

        assert result['status'] == 'success'
        assert 'project_skills' in result
        assert 'project:my-tool' in result['project_skills']


# =============================================================================
# list-finalize-steps Tests (Tier 2)
# =============================================================================


def test_list_finalize_steps_returns_built_in():
    """Test list-finalize-steps returns built-in steps with default: prefix."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_list_finalize_steps(Namespace())

        assert result['status'] == 'success'
        step_names = [s['name'] for s in result['steps']]
        assert 'default:commit-push' in step_names
        assert 'default:create-pr' in step_names
        assert 'default:archive-plan' in step_names
        assert 'default:branch-cleanup' in step_names


def test_list_finalize_steps_count():
    """Test list-finalize-steps returns correct count for built-in steps."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_list_finalize_steps(Namespace())

        assert result['status'] == 'success'
        assert result['count'] >= 7


def test_list_finalize_steps_discovers_project_skills():
    """Test list-finalize-steps discovers project-local finalize-step-* skills.

    Scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        skill_dir = ctx.fixture_dir / '.claude' / 'skills' / 'finalize-step-hello-world'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            '---\nname: finalize-step-hello-world\ndescription: Hello World\n---\n\n# Hello World\n'
        )

        result = run_script(SCRIPT_PATH, 'list-finalize-steps', cwd=ctx.fixture_dir)

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'project:finalize-step-hello-world' in result.stdout
        assert 'Hello World' in result.stdout


# =============================================================================
# list-verify-steps Tests (Tier 2)
# =============================================================================


def test_list_verify_steps_returns_built_in():
    """Test list-verify-steps returns built-in steps with default: prefix."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)
        patch_config_paths(ctx.fixture_dir)

        result = cmd_list_verify_steps(Namespace())

        assert result['status'] == 'success'
        step_names = [s['name'] for s in result['steps']]
        assert 'default:quality_check' in step_names
        assert 'default:build_verify' in step_names


def test_list_verify_steps_discovers_project_skills():
    """Test list-verify-steps discovers project-local verify-step-* skills.

    Scans .claude/skills/ relative to cwd, so keep as subprocess.
    """
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        skill_dir = ctx.fixture_dir / '.claude' / 'skills' / 'verify-step-hello-world'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            '---\nname: verify-step-hello-world\ndescription: Hello World\n---\n\n# Hello World\n'
        )

        result = run_script(SCRIPT_PATH, 'list-verify-steps', cwd=ctx.fixture_dir)

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'project:verify-step-hello-world' in result.stdout
        assert 'Hello World' in result.stdout


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_skill_domains_list():
    """Test CLI plumbing: skill-domains list outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'list')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'java' in result.stdout


def test_cli_skill_domains_get():
    """Test CLI plumbing: skill-domains get outputs TOON."""
    with PlanContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'pm-dev-java:java-core' in result.stdout


def test_cli_resolve_domain_skills():
    """Test CLI plumbing: resolve-domain-skills outputs TOON."""
    with PlanContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-domain-skills', '--domain', 'java', '--profile', 'implementation')

        assert result.success, f'Should succeed: {result.stderr}'
        assert 'pm-dev-java:java-core' in result.stdout


# =============================================================================
# Main
# =============================================================================
