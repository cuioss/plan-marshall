#!/usr/bin/env python3
"""Tests for extension.py implementations across domain bundles.

Tests that each extension:
1. Implements all required functions correctly
2. Returns properly structured data from get_skill_domains()
3. Returns valid command mappings
4. References skills that actually exist
5. Covers required canonical commands (for build bundles)

These are behavioral tests, not just structural validation.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner, PROJECT_ROOT, MARKETPLACE_ROOT

# Required canonical commands in discover_modules() output
# NOTE: Commands are now part of module discovery output, not separate mappings
REQUIRED_CANONICAL_COMMANDS = ['module-tests', 'verify']

# Valid domain profile categories
VALID_PROFILE_CATEGORIES = ['core', 'implementation', 'module_testing', 'integration_testing', 'quality', 'documentation']


def load_extension(bundle_name: str):
    """Load an extension.py module and return Extension instance."""

    extension_path = MARKETPLACE_ROOT / bundle_name / 'skills' / 'plan-marshall-plugin' / 'extension.py'

    if not extension_path.exists():
        raise FileNotFoundError(f"Extension not found: {extension_path}")

    spec = importlib.util.spec_from_file_location(f"extension_{bundle_name}", extension_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Return Extension instance (clean slate - no backward compat functions)
    if hasattr(module, 'Extension'):
        return module.Extension()

    raise ValueError(f"No Extension class found in {bundle_name}")


def skill_exists(skill_ref: str) -> bool:
    """Check if a skill reference (bundle:skill) exists."""
    if ':' not in skill_ref:
        return False

    bundle, skill = skill_ref.split(':', 1)
    skill_path = MARKETPLACE_ROOT / bundle / 'skills' / skill

    # Check for SKILL.md (primary) or at least skill directory
    return skill_path.is_dir() and (
        (skill_path / 'SKILL.md').exists() or
        len(list(skill_path.glob('*.md'))) > 0 or
        len(list(skill_path.glob('scripts/*.py'))) > 0
    )


def create_test_project(build_system: str) -> Path:
    """Create a temporary test project for a given build system."""
    temp_dir = Path(tempfile.mkdtemp())

    if build_system == 'maven':
        (temp_dir / 'pom.xml').write_text('<project></project>')
    elif build_system == 'gradle':
        (temp_dir / 'build.gradle').write_text('plugins { id "java" }')
    elif build_system == 'npm':
        (temp_dir / 'package.json').write_text('{"name": "test", "version": "1.0.0"}')
    elif build_system == 'documentation':
        (temp_dir / 'doc').mkdir()
    elif build_system == 'requirements':
        (temp_dir / 'doc' / 'spec').mkdir(parents=True)
        (temp_dir / 'doc' / 'spec' / 'Requirements.adoc').write_text('= Requirements\n')
    elif build_system == 'plugin-dev':
        (temp_dir / 'marketplace' / 'bundles').mkdir(parents=True)

    return temp_dir


def cleanup_test_project(temp_dir: Path):
    """Clean up temporary test project."""
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# Validation Functions
# =============================================================================

def validate_skill_domains_structure(domains: dict, bundle_name: str) -> list:
    """Validate the structure of get_skill_domains() return value."""
    issues = []

    # Must have 'domain' key
    if 'domain' not in domains:
        issues.append(f"{bundle_name}: get_skill_domains() missing 'domain' key")
        return issues

    domain = domains['domain']

    # Domain must have key and name
    if not isinstance(domain, dict):
        issues.append(f"{bundle_name}: domain must be a dict, got {type(domain)}")
        return issues

    if 'key' not in domain:
        issues.append(f"{bundle_name}: domain missing 'key'")
    elif not isinstance(domain['key'], str) or not domain['key']:
        issues.append(f"{bundle_name}: domain.key must be non-empty string")

    if 'name' not in domain:
        issues.append(f"{bundle_name}: domain missing 'name'")
    elif not isinstance(domain['name'], str) or not domain['name']:
        issues.append(f"{bundle_name}: domain.name must be non-empty string")

    # Must have 'profiles' key
    if 'profiles' not in domains:
        issues.append(f"{bundle_name}: get_skill_domains() missing 'profiles' key")
        return issues

    profiles = domains['profiles']

    if not isinstance(profiles, dict):
        issues.append(f"{bundle_name}: profiles must be a dict, got {type(profiles)}")
        return issues

    # Validate each profile category
    for category, config in profiles.items():
        if category not in VALID_PROFILE_CATEGORIES:
            issues.append(f"{bundle_name}: unknown profile category '{category}'")
            continue

        if not isinstance(config, dict):
            issues.append(f"{bundle_name}: profiles.{category} must be a dict")
            continue

        # Must have defaults and optionals
        if 'defaults' not in config:
            issues.append(f"{bundle_name}: profiles.{category} missing 'defaults'")
        elif not isinstance(config['defaults'], list):
            issues.append(f"{bundle_name}: profiles.{category}.defaults must be a list")

        if 'optionals' not in config:
            issues.append(f"{bundle_name}: profiles.{category} missing 'optionals'")
        elif not isinstance(config['optionals'], list):
            issues.append(f"{bundle_name}: profiles.{category}.optionals must be a list")

    return issues


def validate_skill_references(domains: dict, bundle_name: str) -> list:
    """Validate that all skill references in profiles actually exist."""
    issues = []

    profiles = domains.get('profiles', {})

    for category, config in profiles.items():
        if not isinstance(config, dict):
            continue

        # Check defaults
        for skill_ref in config.get('defaults', []):
            if not skill_exists(skill_ref):
                issues.append(f"{bundle_name}: skill reference '{skill_ref}' in profiles.{category}.defaults does not exist")

        # Check optionals
        for skill_ref in config.get('optionals', []):
            if not skill_exists(skill_ref):
                issues.append(f"{bundle_name}: skill reference '{skill_ref}' in profiles.{category}.optionals does not exist")

    return issues


def validate_triage_outline_references(module, bundle_name: str) -> list:
    """Validate that provides_triage() and provides_outline() return valid refs."""
    issues = []

    if hasattr(module, 'provides_triage'):
        triage = module.provides_triage()
        if triage is not None:
            if not isinstance(triage, str):
                issues.append(f"{bundle_name}: provides_triage() must return str or None")
            elif not skill_exists(triage):
                issues.append(f"{bundle_name}: triage skill '{triage}' does not exist")

    if hasattr(module, 'provides_outline'):
        outline = module.provides_outline()
        if outline is not None:
            if not isinstance(outline, str):
                issues.append(f"{bundle_name}: provides_outline() must return str or None")
            elif not skill_exists(outline):
                issues.append(f"{bundle_name}: outline skill '{outline}' does not exist")

    return issues


# =============================================================================
# pm-dev-java Extension Tests
# =============================================================================

def test_java_extension_skill_domains_structure():
    """Test pm-dev-java get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-java')
    domains = ext.get_skill_domains()

    issues = validate_skill_domains_structure(domains, 'pm-dev-java')
    assert not issues, f"Structure issues: {issues}"

    # Verify domain key
    assert domains['domain']['key'] == 'java', "Domain key should be 'java'"


def test_java_extension_skill_references_exist():
    """Test pm-dev-java skill references point to existing skills."""
    ext = load_extension('pm-dev-java')
    domains = ext.get_skill_domains()

    issues = validate_skill_references(domains, 'pm-dev-java')
    assert not issues, f"Missing skills: {issues}"


def test_java_extension_triage_reference():
    """Test pm-dev-java provides_triage returns valid reference."""
    ext = load_extension('pm-dev-java')
    issues = validate_triage_outline_references(ext, 'pm-dev-java')
    assert not issues, f"Reference issues: {issues}"


# =============================================================================
# pm-dev-frontend Extension Tests
# =============================================================================

def test_frontend_extension_skill_domains_structure():
    """Test pm-dev-frontend get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-frontend')
    domains = ext.get_skill_domains()

    issues = validate_skill_domains_structure(domains, 'pm-dev-frontend')
    assert not issues, f"Structure issues: {issues}"

    # Verify domain key
    assert domains['domain']['key'] == 'javascript', "Domain key should be 'javascript'"


def test_frontend_extension_skill_references_exist():
    """Test pm-dev-frontend skill references point to existing skills."""
    ext = load_extension('pm-dev-frontend')
    domains = ext.get_skill_domains()

    issues = validate_skill_references(domains, 'pm-dev-frontend')
    assert not issues, f"Missing skills: {issues}"


def test_frontend_extension_triage_reference():
    """Test pm-dev-frontend provides_triage returns valid reference."""
    ext = load_extension('pm-dev-frontend')
    issues = validate_triage_outline_references(ext, 'pm-dev-frontend')
    assert not issues, f"Reference issues: {issues}"


# =============================================================================
# pm-plugin-development Extension Tests
# =============================================================================

def test_plugin_dev_extension_skill_domains_structure():
    """Test pm-plugin-development get_skill_domains returns valid structure."""
    ext = load_extension('pm-plugin-development')
    domains = ext.get_skill_domains()

    issues = validate_skill_domains_structure(domains, 'pm-plugin-development')
    assert not issues, f"Structure issues: {issues}"

    # Verify domain key
    assert domains['domain']['key'] == 'plan-marshall-plugin-dev', "Domain key should be 'plan-marshall-plugin-dev'"


def test_plugin_dev_extension_skill_references_exist():
    """Test pm-plugin-development skill references point to existing skills."""
    ext = load_extension('pm-plugin-development')
    domains = ext.get_skill_domains()

    issues = validate_skill_references(domains, 'pm-plugin-development')
    assert not issues, f"Missing skills: {issues}"


def test_plugin_dev_extension_triage_reference():
    """Test pm-plugin-development provides_triage returns valid reference."""
    ext = load_extension('pm-plugin-development')
    issues = validate_triage_outline_references(ext, 'pm-plugin-development')
    assert not issues, f"Reference issues: {issues}"


# =============================================================================
# pm-requirements Extension Tests
# =============================================================================

def test_requirements_extension_skill_domains_structure():
    """Test pm-requirements get_skill_domains returns valid structure."""
    ext = load_extension('pm-requirements')
    domains = ext.get_skill_domains()

    issues = validate_skill_domains_structure(domains, 'pm-requirements')
    assert not issues, f"Structure issues: {issues}"

    # Verify domain key
    assert domains['domain']['key'] == 'requirements', "Domain key should be 'requirements'"


def test_requirements_extension_skill_references_exist():
    """Test pm-requirements skill references point to existing skills."""
    ext = load_extension('pm-requirements')
    domains = ext.get_skill_domains()

    issues = validate_skill_references(domains, 'pm-requirements')
    assert not issues, f"Missing skills: {issues}"


# =============================================================================
# pm-documents Extension Tests
# =============================================================================

def test_documents_extension_skill_domains_structure():
    """Test pm-documents get_skill_domains returns valid structure."""
    ext = load_extension('pm-documents')
    domains = ext.get_skill_domains()

    issues = validate_skill_domains_structure(domains, 'pm-documents')
    assert not issues, f"Structure issues: {issues}"

    # Verify domain key
    assert domains['domain']['key'] == 'documentation', "Domain key should be 'documentation'"


def test_documents_extension_skill_references_exist():
    """Test pm-documents skill references point to existing skills."""
    ext = load_extension('pm-documents')
    domains = ext.get_skill_domains()

    issues = validate_skill_references(domains, 'pm-documents')
    assert not issues, f"Missing skills: {issues}"


# =============================================================================
# pm-dev-java-cui Extension Tests
# =============================================================================

def test_java_cui_extension_skill_domains_structure():
    """Test pm-dev-java-cui get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-java-cui')
    domains = ext.get_skill_domains()

    issues = validate_skill_domains_structure(domains, 'pm-dev-java-cui')
    assert not issues, f"Structure issues: {issues}"

    # Verify domain key
    assert domains['domain']['key'] == 'java-cui', "Domain key should be 'java-cui'"


def test_java_cui_extension_skill_references_exist():
    """Test pm-dev-java-cui skill references point to existing skills."""
    ext = load_extension('pm-dev-java-cui')
    domains = ext.get_skill_domains()

    issues = validate_skill_references(domains, 'pm-dev-java-cui')
    assert not issues, f"Missing skills: {issues}"


# =============================================================================
# Triage/Outline Reference Tests
# =============================================================================

def test_requirements_extension_triage_reference():
    """Test pm-requirements provides_triage returns valid reference."""
    ext = load_extension('pm-requirements')
    issues = validate_triage_outline_references(ext, 'pm-requirements')
    assert not issues, f"Reference issues: {issues}"


def test_documents_extension_triage_reference():
    """Test pm-documents provides_triage returns valid reference."""
    ext = load_extension('pm-documents')
    issues = validate_triage_outline_references(ext, 'pm-documents')
    assert not issues, f"Reference issues: {issues}"


def test_plugin_dev_extension_outline_reference():
    """Test pm-plugin-development provides_outline returns valid reference."""
    ext = load_extension('pm-plugin-development')

    outline = ext.provides_outline()
    assert outline is not None, "Should provide outline skill"
    assert skill_exists(outline), f"Outline skill '{outline}' should exist"


def test_documents_extension_outline_reference():
    """Test pm-documents provides_outline returns valid reference."""
    ext = load_extension('pm-documents')

    outline = ext.provides_outline()
    assert outline is not None, "Should provide outline skill"
    assert skill_exists(outline), f"Outline skill '{outline}' should exist"


# =============================================================================
# Cross-Bundle Validation Tests
# =============================================================================

def test_all_extensions_have_unique_domain_keys():
    """Test that all extensions have unique domain keys."""
    bundles = ['pm-dev-java', 'pm-dev-java-cui', 'pm-dev-frontend', 'pm-plugin-development', 'pm-requirements', 'pm-documents']
    domain_keys = {}

    for bundle in bundles:
        try:
            ext = load_extension(bundle)
            domains = ext.get_skill_domains()
            key = domains['domain']['key']

            if key in domain_keys:
                raise AssertionError(f"Duplicate domain key '{key}' in {bundle} and {domain_keys[key]}")

            domain_keys[key] = bundle
        except FileNotFoundError:
            pass  # Skip bundles without extensions

    assert len(domain_keys) == 6, f"Should have 6 unique domain keys, got {len(domain_keys)}"


def test_all_extensions_have_required_functions():
    """Test that all extensions implement required functions."""
    bundles = ['pm-dev-java', 'pm-dev-java-cui', 'pm-dev-frontend', 'pm-plugin-development', 'pm-requirements', 'pm-documents']
    # Only get_skill_domains is required (abstract method)
    required = ['get_skill_domains']

    for bundle in bundles:
        try:
            ext = load_extension(bundle)

            for func_name in required:
                assert hasattr(ext, func_name), f"{bundle}: missing required function {func_name}"
                assert callable(getattr(ext, func_name)), f"{bundle}: {func_name} is not callable"
        except FileNotFoundError:
            raise AssertionError(f"{bundle}: extension.py not found")


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # pm-dev-java tests
        test_java_extension_skill_domains_structure,
        test_java_extension_skill_references_exist,
        test_java_extension_triage_reference,
        # pm-dev-frontend tests
        test_frontend_extension_skill_domains_structure,
        test_frontend_extension_skill_references_exist,
        test_frontend_extension_triage_reference,
        # pm-plugin-development tests
        test_plugin_dev_extension_skill_domains_structure,
        test_plugin_dev_extension_skill_references_exist,
        test_plugin_dev_extension_triage_reference,
        test_plugin_dev_extension_outline_reference,
        # pm-requirements tests
        test_requirements_extension_skill_domains_structure,
        test_requirements_extension_skill_references_exist,
        test_requirements_extension_triage_reference,
        # pm-documents tests
        test_documents_extension_skill_domains_structure,
        test_documents_extension_skill_references_exist,
        test_documents_extension_triage_reference,
        test_documents_extension_outline_reference,
        # pm-dev-java-cui tests
        test_java_cui_extension_skill_domains_structure,
        test_java_cui_extension_skill_references_exist,
        # Cross-bundle tests
        test_all_extensions_have_unique_domain_keys,
        test_all_extensions_have_required_functions,
    ])
    sys.exit(runner.run())
