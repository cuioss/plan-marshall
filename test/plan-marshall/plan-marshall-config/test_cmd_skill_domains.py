#!/usr/bin/env python3
"""Tests for skill-domains commands in plan-marshall-config.

Tests skill-domains, resolve-domain-skills, get-workflow-skills commands
including nested structure variants and edge cases.
"""

import json
import sys
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script, TestRunner, PlanTestContext
from test_helpers import SCRIPT_PATH, create_marshal_json, create_nested_marshal_json


# =============================================================================
# skill-domains Basic Tests (Flat Structure)
# =============================================================================

def test_skill_domains_list():
    """Test skill-domains list."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'list')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'success' in result.stdout.lower()
        assert 'java' in result.stdout


def test_skill_domains_get():
    """Test skill-domains get."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-dev-java:java-core' in result.stdout


def test_skill_domains_get_defaults():
    """Test skill-domains get-defaults."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-defaults', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-dev-java:java-core' in result.stdout


def test_skill_domains_get_optionals():
    """Test skill-domains get-optionals."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-optionals', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-dev-java:java-cdi' in result.stdout


def test_skill_domains_unknown_domain():
    """Test skill-domains get with unknown domain returns error."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'unknown')

        assert 'error' in result.stdout.lower(), "Should report error"
        assert 'unknown' in result.stdout.lower()


def test_skill_domains_add():
    """Test skill-domains add."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'add',
            '--domain', 'python',
            '--defaults', 'pm-dev-python:cui-python-core'
        )

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify added
        verify = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'python')
        assert 'pm-dev-python:cui-python-core' in verify.stdout


def test_skill_domains_validate():
    """Test skill-domains validate."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        # Valid skill
        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate',
            '--domain', 'java',
            '--skill', 'pm-dev-java:java-core'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()


def test_skill_domains_validate_returns_location():
    """Test skill-domains validate returns in_defaults or in_optionals."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        # Skill in defaults
        result_defaults = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate',
            '--domain', 'java',
            '--skill', 'pm-dev-java:java-core'
        )

        assert result_defaults.success, f"Should succeed: {result_defaults.stderr}"
        assert 'in_defaults' in result_defaults.stdout.lower()

        # Skill in optionals
        result_optionals = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate',
            '--domain', 'java',
            '--skill', 'pm-dev-java:java-cdi'
        )

        assert result_optionals.success, f"Should succeed: {result_optionals.stderr}"
        assert 'in_optionals' in result_optionals.stdout.lower()


def test_skill_domains_validate_invalid_skill():
    """Test skill-domains validate with invalid skill returns false."""
    with PlanTestContext() as ctx:
        create_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate',
            '--domain', 'java',
            '--skill', 'pm-dev-java:invalid-skill'
        )

        assert result.success, f"Should succeed even if invalid: {result.stderr}"
        assert 'false' in result.stdout.lower()


# =============================================================================
# skill-domains Nested Structure Tests
# =============================================================================

def test_skill_domains_get_nested_structure():
    """Test skill-domains get returns nested structure for domains with profiles."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        # Should include core block
        assert 'core' in result.stdout
        # Should include implementation block
        assert 'implementation' in result.stdout
        # Should include testing block
        assert 'testing' in result.stdout


def test_skill_domains_get_defaults_nested():
    """Test skill-domains get-defaults returns core.defaults for nested structure."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-defaults', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        # Should return core.defaults
        assert 'pm-dev-java:java-core' in result.stdout


def test_skill_domains_get_optionals_nested():
    """Test skill-domains get-optionals returns core.optionals for nested structure."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-optionals', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        # Should return core.optionals
        assert 'pm-dev-java:java-null-safety' in result.stdout
        assert 'pm-dev-java:java-lombok' in result.stdout


def test_skill_domains_validate_nested():
    """Test skill-domains validate works with nested structure."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        # Validate skill in core.defaults
        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate',
            '--domain', 'java',
            '--skill', 'pm-dev-java:java-core'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()


def test_skill_domains_validate_nested_profile_skill():
    """Test skill-domains validate finds skills in profile blocks."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        # Validate skill in testing.defaults (junit-core)
        result = run_script(
            SCRIPT_PATH, 'skill-domains', 'validate',
            '--domain', 'java',
            '--skill', 'pm-dev-java:junit-core'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'true' in result.stdout.lower() or 'valid' in result.stdout.lower()
        assert 'in_defaults' in result.stdout.lower()


def test_skill_domains_get_system_has_workflow_skills():
    """Test skill-domains get returns system domain with workflow_skills."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'system')

        assert result.success, f"Should succeed: {result.stderr}"
        # System domain has defaults
        assert 'defaults' in result.stdout
        assert 'plan-marshall:general-development-rules' in result.stdout
        # System domain now HAS workflow_skills (5-phase model)
        assert 'workflow_skills' in result.stdout


# =============================================================================
# skill-domains detect Tests
# =============================================================================

def test_skill_domains_detect_runs():
    """Test skill-domains detect command runs successfully."""
    with PlanTestContext() as ctx:
        # Create minimal marshal.json
        config = {
            "skill_domains": {
                "system": {
                    "defaults": ["plan-marshall:general-development-rules"],
                    "optionals": []
                }
            },
            "modules": {},
            "build_systems": [],
            "system": {"retention": {}},
            "plan": {"defaults": {}}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'success' in result.stdout.lower()
        assert 'detected' in result.stdout.lower()


def test_skill_domains_detect_no_overwrite():
    """Test skill-domains detect does not overwrite existing domains."""
    with PlanTestContext() as ctx:
        # Create marshal.json with custom java domain
        config = {
            "skill_domains": {
                "system": {"defaults": [], "optionals": []},
                "java": {
                    "core": {"defaults": ["custom:skill"], "optionals": []}
                }
            },
            "modules": {},
            "build_systems": [],
            "system": {"retention": {}},
            "plan": {"defaults": {}}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'skill-domains', 'detect')

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify existing java domain was NOT overwritten (even if java was detected)
        verify = run_script(SCRIPT_PATH, 'skill-domains', 'get', '--domain', 'java')
        assert 'custom:skill' in verify.stdout


# =============================================================================
# resolve-domain-skills Tests
# =============================================================================

def test_resolve_domain_skills_java_implementation():
    """Test resolve-domain-skills for java + implementation profile."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'resolve-domain-skills',
            '--domain', 'java',
            '--profile', 'implementation'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        # Should include core defaults (java-core)
        assert 'pm-dev-java:java-core' in result.stdout
        # Should include implementation optionals (java-cdi, java-maintenance)
        assert 'pm-dev-java:java-cdi' in result.stdout
        # Should NOT include testing defaults (junit-core)
        assert 'pm-dev-java:junit-core' not in result.stdout


def test_resolve_domain_skills_java_testing():
    """Test resolve-domain-skills for java + testing profile."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'resolve-domain-skills',
            '--domain', 'java',
            '--profile', 'testing'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        # Should include core defaults (java-core)
        assert 'pm-dev-java:java-core' in result.stdout
        # Should include testing defaults (junit-core)
        assert 'pm-dev-java:junit-core' in result.stdout
        # Should include testing optionals (junit-integration)
        assert 'pm-dev-java:junit-integration' in result.stdout
        # Should NOT include implementation optionals (java-cdi)
        assert 'pm-dev-java:java-cdi' not in result.stdout


def test_resolve_domain_skills_javascript_implementation():
    """Test resolve-domain-skills for javascript + implementation profile."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'resolve-domain-skills',
            '--domain', 'javascript',
            '--profile', 'implementation'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        # Should include core defaults (cui-javascript)
        assert 'pm-dev-frontend:cui-javascript' in result.stdout
        # Should include implementation optionals
        assert 'pm-dev-frontend:cui-javascript-linting' in result.stdout


def test_resolve_domain_skills_unknown_domain():
    """Test resolve-domain-skills with unknown domain returns error."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'resolve-domain-skills',
            '--domain', 'unknown',
            '--profile', 'implementation'
        )

        assert 'error' in result.stdout.lower(), "Should report error"
        assert 'unknown' in result.stdout.lower()


def test_resolve_domain_skills_unknown_profile():
    """Test resolve-domain-skills with unknown profile returns error."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'resolve-domain-skills',
            '--domain', 'java',
            '--profile', 'invalid-profile'
        )

        assert 'error' in result.stdout.lower(), "Should report error"
        assert 'profile' in result.stdout.lower()


def test_resolve_domain_skills_java_quality():
    """Test resolve-domain-skills for java + quality profile (finalize phase)."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(
            SCRIPT_PATH, 'resolve-domain-skills',
            '--domain', 'java',
            '--profile', 'quality'
        )

        assert result.success, f"Should succeed: {result.stderr}"
        # Should include core defaults (java-core)
        assert 'pm-dev-java:java-core' in result.stdout
        # Should include quality defaults (javadoc)
        assert 'pm-dev-java:javadoc' in result.stdout


# =============================================================================
# get-workflow-skills Tests (5-Phase Model)
# =============================================================================

def test_get_workflow_skills():
    """Test get-workflow-skills returns all 5-phase workflow skill references."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-workflow-skills')

        assert result.success, f"Should succeed: {result.stderr}"
        # Verify all 5 phases are returned
        assert '1-init' in result.stdout
        assert '2-outline' in result.stdout
        assert '3-plan' in result.stdout
        assert '4-execute' in result.stdout
        assert '5-finalize' in result.stdout
        # Verify skill references
        assert 'pm-workflow:phase-1-init' in result.stdout
        assert 'pm-workflow:phase-2-outline' in result.stdout
        assert 'pm-workflow:phase-3-plan' in result.stdout


def test_get_workflow_skills_output_format():
    """Test get-workflow-skills returns all 5 workflow skill references."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-workflow-skills')

        assert result.success, f"Should succeed: {result.stderr}"
        # Verify all 5 workflow skills are returned
        assert 'pm-workflow:phase-4-execute' in result.stdout
        assert 'pm-workflow:phase-5-finalize' in result.stdout


# =============================================================================
# resolve-workflow-skill Tests (5-Phase Model - Always uses system domain)
# =============================================================================

def test_resolve_workflow_skill_init():
    """Test resolve-workflow-skill for 1-init phase returns system workflow skill."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill', '--phase', '1-init')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-workflow:phase-1-init' in result.stdout
        assert 'phase' in result.stdout
        assert 'workflow_skill' in result.stdout


def test_resolve_workflow_skill_outline():
    """Test resolve-workflow-skill for 2-outline phase returns system workflow skill."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill', '--phase', '2-outline')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-workflow:phase-2-outline' in result.stdout


def test_resolve_workflow_skill_plan():
    """Test resolve-workflow-skill for 3-plan phase returns system workflow skill."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill', '--phase', '3-plan')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-workflow:phase-3-plan' in result.stdout


def test_resolve_workflow_skill_execute():
    """Test resolve-workflow-skill for 4-execute phase returns system workflow skill."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill', '--phase', '4-execute')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-workflow:phase-4-execute' in result.stdout


def test_resolve_workflow_skill_finalize():
    """Test resolve-workflow-skill for 5-finalize phase returns system workflow skill."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill', '--phase', '5-finalize')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-workflow:phase-5-finalize' in result.stdout


def test_resolve_workflow_skill_no_system_domain():
    """Test resolve-workflow-skill returns error when system domain is missing."""
    with PlanTestContext() as ctx:
        # Create marshal.json WITHOUT system domain
        config = {
            "skill_domains": {
                "java": {"core": {"defaults": [], "optionals": []}}
            },
            "modules": {},
            "build_systems": [],
            "system": {"retention": {}},
            "plan": {"defaults": {}}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill', '--phase', 'outline')

        assert 'error' in result.stdout.lower(), "Should report error"
        assert 'system' in result.stdout.lower()


# =============================================================================
# resolve-workflow-skill-extension Tests
# =============================================================================

def test_resolve_workflow_skill_extension_java_outline():
    """Test resolve-workflow-skill-extension returns outline extension for java."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill-extension',
            '--domain', 'java', '--type', 'outline')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-dev-java:java-outline-ext' in result.stdout
        assert 'domain' in result.stdout
        assert 'type' in result.stdout
        assert 'extension' in result.stdout


def test_resolve_workflow_skill_extension_java_triage():
    """Test resolve-workflow-skill-extension returns triage extension for java."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill-extension',
            '--domain', 'java', '--type', 'triage')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-dev-java:java-triage' in result.stdout


def test_resolve_workflow_skill_extension_javascript_outline():
    """Test resolve-workflow-skill-extension returns outline extension for javascript."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill-extension',
            '--domain', 'javascript', '--type', 'outline')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-dev-frontend:js-outline-ext' in result.stdout


def test_resolve_workflow_skill_extension_missing_type():
    """Test resolve-workflow-skill-extension returns null for missing extension type."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        # javascript has no triage extension
        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill-extension',
            '--domain', 'javascript', '--type', 'triage')

        assert result.success, f"Should succeed: {result.stderr}"
        # Should return null for extension, not error
        assert 'null' in result.stdout.lower() or 'none' in result.stdout.lower()


def test_resolve_workflow_skill_extension_unknown_domain():
    """Test resolve-workflow-skill-extension returns null for unknown domain (not error)."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill-extension',
            '--domain', 'unknown', '--type', 'outline')

        assert result.success, f"Should succeed (returns null, not error): {result.stderr}"
        # Should return null for extension, not error
        assert 'null' in result.stdout.lower() or 'none' in result.stdout.lower()


def test_resolve_workflow_skill_extension_plugin_dev():
    """Test resolve-workflow-skill-extension returns extensions for plugin-dev domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'resolve-workflow-skill-extension',
            '--domain', 'plan-marshall-plugin-dev', '--type', 'outline')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'pm-plugin-development:plugin-outline-ext' in result.stdout


# =============================================================================
# get-extensions / set-extensions Tests
# =============================================================================

def test_get_extensions_java():
    """Test get-extensions returns extensions for java domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-extensions', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'extensions' in result.stdout
        assert 'outline' in result.stdout
        assert 'triage' in result.stdout


def test_get_extensions_unknown_domain():
    """Test get-extensions returns error for unknown domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-extensions', '--domain', 'unknown')

        assert 'error' in result.stdout.lower(), "Should report error"


def test_set_extensions():
    """Test set-extensions adds extension to domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'set-extensions',
            '--domain', 'java', '--type', 'triage', '--skill', 'pm-dev-java:new-triage')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'triage' in result.stdout
        assert 'pm-dev-java:new-triage' in result.stdout


# =============================================================================
# get-available / configure Tests
# =============================================================================

def test_get_available_uses_discovery():
    """Test get-available uses discovery for domains (no longer tied to build system)."""
    with PlanTestContext() as ctx:
        # Create marshal.json - build_systems no longer affect get-available
        config = {
            "skill_domains": {"system": {"defaults": []}},
            "modules": {},
            "build_systems": [{"system": "maven", "skill": "plan-marshall:build-operations"}],
            "system": {"retention": {}},
            "plan": {"defaults": {}}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'skill-domains', 'get-available')

        assert result.success, f"Should succeed: {result.stderr}"
        # Returns discovered_domains from bundle manifests
        assert 'discovered_domains' in result.stdout


def test_configure_domains():
    """Test configure adds system domain and selected domains."""
    with PlanTestContext() as ctx:
        config = {
            "skill_domains": {},
            "modules": {},
            "build_systems": [],
            "system": {"retention": {}},
            "plan": {"defaults": {}}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'skill-domains', 'configure', '--domains', 'java,javascript')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'system_domain' in result.stdout
        assert 'configured' in result.stdout

        # Verify marshal.json was updated
        updated = json.loads(marshal_path.read_text())
        assert 'system' in updated['skill_domains'], "System domain should be added"
        assert 'java' in updated['skill_domains'], "Java domain should be added"
        assert 'javascript' in updated['skill_domains'], "JavaScript domain should be added"
        assert 'workflow_skills' in updated['skill_domains']['system'], "System should have workflow_skills"


def test_configure_always_adds_system():
    """Test configure always adds system domain even with empty selection."""
    with PlanTestContext() as ctx:
        config = {
            "skill_domains": {},
            "modules": {},
            "build_systems": [],
            "system": {"retention": {}},
            "plan": {"defaults": {}}
        }
        marshal_path = ctx.fixture_dir / 'marshal.json'
        marshal_path.write_text(json.dumps(config, indent=2))

        result = run_script(SCRIPT_PATH, 'skill-domains', 'configure', '--domains', '')

        assert result.success, f"Should succeed: {result.stderr}"

        # Verify system domain was added
        updated = json.loads(marshal_path.read_text())
        assert 'system' in updated['skill_domains'], "System domain should always be added"


# =============================================================================
# set with --profile Tests
# =============================================================================

def test_set_with_profile():
    """Test set with --profile updates specific profile."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'skill-domains', 'set',
            '--domain', 'java', '--profile', 'quality',
            '--defaults', 'pm-dev-java:new-skill')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'quality' in result.stdout


# =============================================================================
# get-skills-by-profile Tests
# =============================================================================

def test_get_skills_by_profile_java():
    """Test get-skills-by-profile returns profile-keyed skills for java domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-skills-by-profile', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        # Should have skills_by_profile structure
        assert 'skills_by_profile' in result.stdout
        # Should have all profiles
        assert 'implementation' in result.stdout
        assert 'unit-testing' in result.stdout
        assert 'integration-testing' in result.stdout
        assert 'benchmark-testing' in result.stdout


def test_get_skills_by_profile_includes_core_skills():
    """Test get-skills-by-profile includes core skills in all profiles."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-skills-by-profile', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        # Core skill should appear in output (java-core is in core.defaults)
        assert 'pm-dev-java:java-core' in result.stdout


def test_get_skills_by_profile_includes_profile_skills():
    """Test get-skills-by-profile includes profile-specific skills."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-skills-by-profile', '--domain', 'java')

        assert result.success, f"Should succeed: {result.stderr}"
        # Testing profile skill should appear (junit-core is in testing.defaults)
        assert 'pm-dev-java:junit-core' in result.stdout


def test_get_skills_by_profile_javascript():
    """Test get-skills-by-profile works for javascript domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-skills-by-profile', '--domain', 'javascript')

        assert result.success, f"Should succeed: {result.stderr}"
        assert 'skills_by_profile' in result.stdout
        # Core js skill should be present
        assert 'pm-dev-frontend:cui-javascript' in result.stdout


def test_get_skills_by_profile_unknown_domain():
    """Test get-skills-by-profile returns error for unknown domain."""
    with PlanTestContext() as ctx:
        create_nested_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-skills-by-profile', '--domain', 'unknown')

        assert 'error' in result.stdout.lower(), "Should report error"
        assert 'unknown' in result.stdout.lower()


def test_get_skills_by_profile_flat_domain_error():
    """Test get-skills-by-profile returns error for flat structure domain."""
    with PlanTestContext() as ctx:
        # Create marshal.json with flat structure
        create_marshal_json(ctx.fixture_dir)

        result = run_script(SCRIPT_PATH, 'get-skills-by-profile', '--domain', 'java')

        assert 'error' in result.stdout.lower(), "Should report error for flat domain"
        assert 'profile' in result.stdout.lower() or 'flat' in result.stdout.lower()


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Basic skill-domains tests (flat structure)
        test_skill_domains_list,
        test_skill_domains_get,
        test_skill_domains_get_defaults,
        test_skill_domains_get_optionals,
        test_skill_domains_unknown_domain,
        test_skill_domains_add,
        test_skill_domains_validate,
        test_skill_domains_validate_returns_location,
        test_skill_domains_validate_invalid_skill,
        # Nested structure tests
        test_skill_domains_get_nested_structure,
        test_skill_domains_get_defaults_nested,
        test_skill_domains_get_optionals_nested,
        test_skill_domains_validate_nested,
        test_skill_domains_validate_nested_profile_skill,
        test_skill_domains_get_system_has_workflow_skills,
        # Detect tests
        test_skill_domains_detect_runs,
        test_skill_domains_detect_no_overwrite,
        # resolve-domain-skills tests
        test_resolve_domain_skills_java_implementation,
        test_resolve_domain_skills_java_testing,
        test_resolve_domain_skills_javascript_implementation,
        test_resolve_domain_skills_unknown_domain,
        test_resolve_domain_skills_unknown_profile,
        test_resolve_domain_skills_java_quality,
        # get-workflow-skills tests
        test_get_workflow_skills,
        test_get_workflow_skills_output_format,
        # resolve-workflow-skill tests (5-phase model)
        test_resolve_workflow_skill_init,
        test_resolve_workflow_skill_outline,
        test_resolve_workflow_skill_plan,
        test_resolve_workflow_skill_execute,
        test_resolve_workflow_skill_finalize,
        test_resolve_workflow_skill_no_system_domain,
        # resolve-workflow-skill-extension tests
        test_resolve_workflow_skill_extension_java_outline,
        test_resolve_workflow_skill_extension_java_triage,
        test_resolve_workflow_skill_extension_javascript_outline,
        test_resolve_workflow_skill_extension_missing_type,
        test_resolve_workflow_skill_extension_unknown_domain,
        test_resolve_workflow_skill_extension_plugin_dev,
        # get-extensions / set-extensions tests
        test_get_extensions_java,
        test_get_extensions_unknown_domain,
        test_set_extensions,
        # get-available / configure tests
        test_get_available_uses_discovery,
        test_configure_domains,
        test_configure_always_adds_system,
        # set with --profile tests
        test_set_with_profile,
        # get-skills-by-profile tests
        test_get_skills_by_profile_java,
        test_get_skills_by_profile_includes_core_skills,
        test_get_skills_by_profile_includes_profile_skills,
        test_get_skills_by_profile_javascript,
        test_get_skills_by_profile_unknown_domain,
        test_get_skills_by_profile_flat_domain_error,
    ])
    sys.exit(runner.run())
