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
import shutil
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT

# Required canonical commands in discover_modules() output
# NOTE: Commands are now part of module discovery output, not separate mappings
REQUIRED_CANONICAL_COMMANDS = ['module-tests', 'verify']

# Valid domain profile categories
VALID_PROFILE_CATEGORIES = [
    'core',
    'implementation',
    'module_testing',
    'integration_testing',
    'quality',
    'documentation',
]


def load_extension(bundle_name: str):
    """Load an extension.py module and return Extension instance."""

    extension_path = MARKETPLACE_ROOT / bundle_name / 'skills' / 'plan-marshall-plugin' / 'extension.py'

    if not extension_path.exists():
        raise FileNotFoundError(f'Extension not found: {extension_path}')

    spec = importlib.util.spec_from_file_location(f'extension_{bundle_name}', extension_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load module from {extension_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Return Extension instance
    if hasattr(module, 'Extension'):
        return module.Extension()

    raise ValueError(f'No Extension class found in {bundle_name}')


def skill_exists(skill_ref: str) -> bool:
    """Check if a skill reference (bundle:skill) exists."""
    if ':' not in skill_ref:
        return False

    bundle, skill = skill_ref.split(':', 1)
    skill_path = MARKETPLACE_ROOT / bundle / 'skills' / skill

    # Check for SKILL.md (primary) or at least skill directory
    return skill_path.is_dir() and (
        (skill_path / 'SKILL.md').exists()
        or len(list(skill_path.glob('*.md'))) > 0
        or len(list(skill_path.glob('scripts/*.py'))) > 0
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
        issues.append(f'{bundle_name}: domain must be a dict, got {type(domain)}')
        return issues

    if 'key' not in domain:
        issues.append(f"{bundle_name}: domain missing 'key'")
    elif not isinstance(domain['key'], str) or not domain['key']:
        issues.append(f'{bundle_name}: domain.key must be non-empty string')

    if 'name' not in domain:
        issues.append(f"{bundle_name}: domain missing 'name'")
    elif not isinstance(domain['name'], str) or not domain['name']:
        issues.append(f'{bundle_name}: domain.name must be non-empty string')

    # Must have 'profiles' key
    if 'profiles' not in domains:
        issues.append(f"{bundle_name}: get_skill_domains() missing 'profiles' key")
        return issues

    profiles = domains['profiles']

    if not isinstance(profiles, dict):
        issues.append(f'{bundle_name}: profiles must be a dict, got {type(profiles)}')
        return issues

    # Validate each profile category
    for category, config in profiles.items():
        if category not in VALID_PROFILE_CATEGORIES:
            issues.append(f"{bundle_name}: unknown profile category '{category}'")
            continue

        if not isinstance(config, dict):
            issues.append(f'{bundle_name}: profiles.{category} must be a dict')
            continue

        # Must have defaults and optionals
        if 'defaults' not in config:
            issues.append(f"{bundle_name}: profiles.{category} missing 'defaults'")
        elif not isinstance(config['defaults'], list):
            issues.append(f'{bundle_name}: profiles.{category}.defaults must be a list')

        if 'optionals' not in config:
            issues.append(f"{bundle_name}: profiles.{category} missing 'optionals'")
        elif not isinstance(config['optionals'], list):
            issues.append(f'{bundle_name}: profiles.{category}.optionals must be a list')

    return issues


def _extract_skill_ref(entry) -> str:
    """Extract skill reference from an entry (string or dict).

    Handles both legacy string format and new dict format:
    - String: "pm-dev-java:java-core"
    - Dict: {"skill": "pm-dev-java:java-core", "description": "..."}
    """
    if isinstance(entry, dict):
        return entry.get('skill', '')
    return entry


def validate_skill_references(domains: dict, bundle_name: str) -> list:
    """Validate that all skill references in profiles actually exist."""
    issues = []

    profiles = domains.get('profiles', {})

    for category, config in profiles.items():
        if not isinstance(config, dict):
            continue

        # Check defaults
        for entry in config.get('defaults', []):
            skill_ref = _extract_skill_ref(entry)
            if not skill_exists(skill_ref):
                issues.append(
                    f"{bundle_name}: skill reference '{skill_ref}' in profiles.{category}.defaults does not exist"
                )

        # Check optionals
        for entry in config.get('optionals', []):
            skill_ref = _extract_skill_ref(entry)
            if not skill_exists(skill_ref):
                issues.append(
                    f"{bundle_name}: skill reference '{skill_ref}' in profiles.{category}.optionals does not exist"
                )

    return issues


def agent_exists(agent_ref: str) -> bool:
    """Check if an agent reference (bundle:agent) exists."""
    if ':' not in agent_ref:
        return False

    bundle, agent = agent_ref.split(':', 1)
    agent_path = MARKETPLACE_ROOT / bundle / 'agents' / f'{agent}.md'

    return agent_path.is_file()


def validate_triage_and_outline_skill(module, bundle_name: str) -> list:
    """Validate that provides_triage() and provides_outline_skill() return valid refs."""
    issues = []

    if hasattr(module, 'provides_triage'):
        triage = module.provides_triage()
        if triage is not None:
            if not isinstance(triage, str):
                issues.append(f'{bundle_name}: provides_triage() must return str or None')
            elif not skill_exists(triage):
                issues.append(f"{bundle_name}: triage skill '{triage}' does not exist")

    if hasattr(module, 'provides_outline_skill'):
        outline_skill = module.provides_outline_skill()
        if outline_skill is not None:
            if not isinstance(outline_skill, str):
                issues.append(f'{bundle_name}: provides_outline_skill() must return str or None')
            elif not skill_exists(outline_skill):
                issues.append(f"{bundle_name}: outline skill '{outline_skill}' does not exist")

    return issues


# =============================================================================
# pm-dev-java Extension Tests
# =============================================================================


def test_java_extension_skill_domains_structure():
    """Test pm-dev-java get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-java')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-dev-java')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'java', "Domain key should be 'java'"


def test_java_extension_skill_references_exist():
    """Test pm-dev-java skill references point to existing skills."""
    ext = load_extension('pm-dev-java')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-dev-java')
    assert not issues, f'Missing skills: {issues}'


def test_java_extension_triage_reference():
    """Test pm-dev-java provides_triage returns valid reference."""
    ext = load_extension('pm-dev-java')
    issues = validate_triage_and_outline_skill(ext, 'pm-dev-java')
    assert not issues, f'Reference issues: {issues}'


# =============================================================================
# pm-dev-frontend Extension Tests
# =============================================================================


def test_frontend_extension_skill_domains_structure():
    """Test pm-dev-frontend get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-frontend')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-dev-frontend')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'javascript', "Domain key should be 'javascript'"


def test_frontend_extension_skill_references_exist():
    """Test pm-dev-frontend skill references point to existing skills."""
    ext = load_extension('pm-dev-frontend')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-dev-frontend')
    assert not issues, f'Missing skills: {issues}'


def test_frontend_extension_triage_reference():
    """Test pm-dev-frontend provides_triage returns valid reference."""
    ext = load_extension('pm-dev-frontend')
    issues = validate_triage_and_outline_skill(ext, 'pm-dev-frontend')
    assert not issues, f'Reference issues: {issues}'


# =============================================================================
# pm-plugin-development Extension Tests
# =============================================================================


def test_plugin_dev_extension_skill_domains_structure():
    """Test pm-plugin-development get_skill_domains returns valid structure."""
    ext = load_extension('pm-plugin-development')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-plugin-development')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'plan-marshall-plugin-dev', "Domain key should be 'plan-marshall-plugin-dev'"


def test_plugin_dev_extension_skill_references_exist():
    """Test pm-plugin-development skill references point to existing skills."""
    ext = load_extension('pm-plugin-development')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-plugin-development')
    assert not issues, f'Missing skills: {issues}'


def test_plugin_dev_extension_triage_reference():
    """Test pm-plugin-development provides_triage returns valid reference."""
    ext = load_extension('pm-plugin-development')
    issues = validate_triage_and_outline_skill(ext, 'pm-plugin-development')
    assert not issues, f'Reference issues: {issues}'


# =============================================================================
# pm-requirements Extension Tests
# =============================================================================


def test_requirements_extension_skill_domains_structure():
    """Test pm-requirements get_skill_domains returns valid structure."""
    ext = load_extension('pm-requirements')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-requirements')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'requirements', "Domain key should be 'requirements'"


def test_requirements_extension_skill_references_exist():
    """Test pm-requirements skill references point to existing skills."""
    ext = load_extension('pm-requirements')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-requirements')
    assert not issues, f'Missing skills: {issues}'


# =============================================================================
# pm-documents Extension Tests
# =============================================================================


def test_documents_extension_skill_domains_structure():
    """Test pm-documents get_skill_domains returns valid structure."""
    ext = load_extension('pm-documents')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-documents')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'documentation', "Domain key should be 'documentation'"


def test_documents_extension_skill_references_exist():
    """Test pm-documents skill references point to existing skills."""
    ext = load_extension('pm-documents')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-documents')
    assert not issues, f'Missing skills: {issues}'


# =============================================================================
# pm-dev-java-cui Extension Tests
# =============================================================================


def test_java_cui_extension_skill_domains_structure():
    """Test pm-dev-java-cui get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-java-cui')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-dev-java-cui')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'java-cui', "Domain key should be 'java-cui'"


def test_java_cui_extension_skill_references_exist():
    """Test pm-dev-java-cui skill references point to existing skills."""
    ext = load_extension('pm-dev-java-cui')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-dev-java-cui')
    assert not issues, f'Missing skills: {issues}'


# =============================================================================
# pm-dev-frontend-cui Extension Tests
# =============================================================================


def test_frontend_cui_extension_skill_domains_structure():
    """Test pm-dev-frontend-cui get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-frontend-cui')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-dev-frontend-cui')
    assert not issues, f'Structure issues: {issues}'

    # Verify domain key
    assert domains['domain']['key'] == 'javascript-cui', "Domain key should be 'javascript-cui'"


def test_frontend_cui_extension_skill_references_exist():
    """Test pm-dev-frontend-cui skill references point to existing skills."""
    ext = load_extension('pm-dev-frontend-cui')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-dev-frontend-cui')
    assert not issues, f'Missing skills: {issues}'


# =============================================================================
# Triage/Outline Reference Tests
# =============================================================================


def test_requirements_extension_triage_reference():
    """Test pm-requirements provides_triage returns valid reference."""
    ext = load_extension('pm-requirements')
    issues = validate_triage_and_outline_skill(ext, 'pm-requirements')
    assert not issues, f'Reference issues: {issues}'


def test_documents_extension_triage_reference():
    """Test pm-documents provides_triage returns valid reference."""
    ext = load_extension('pm-documents')
    issues = validate_triage_and_outline_skill(ext, 'pm-documents')
    assert not issues, f'Reference issues: {issues}'


def test_plugin_dev_extension_outline_skill_reference():
    """Test pm-plugin-development provides_outline_skill returns valid reference."""
    ext = load_extension('pm-plugin-development')

    outline_skill = ext.provides_outline_skill()
    assert outline_skill is not None, 'Should provide outline_skill'
    assert isinstance(outline_skill, str), 'Should return a string'
    assert skill_exists(outline_skill), f"Outline skill '{outline_skill}' should exist"


def test_documents_extension_no_outline_skill():
    """Test pm-documents does not provide outline_skill (uses generic)."""
    ext = load_extension('pm-documents')

    # pm-documents uses generic phase-3-outline standards, so should return None
    outline_skill = ext.provides_outline_skill()
    assert outline_skill is None, 'pm-documents should not provide domain-specific outline_skill'


# =============================================================================
# applies_to_module() Tests
# =============================================================================


def _maven_module_data() -> dict:
    """Sample maven module data."""
    return {
        'name': 'core',
        'build_systems': ['maven'],
        'paths': {'module': 'core', 'sources': ['src/main/java'], 'tests': ['src/test/java']},
        'metadata': {},
        'packages': {},
        'dependencies': ['jakarta.enterprise.cdi-api:jakarta.enterprise:compile'],
        'commands': {},
        'stats': {'source_files': 10, 'test_files': 5},
    }


def _npm_module_data() -> dict:
    """Sample npm module data."""
    return {
        'name': 'frontend',
        'build_systems': ['npm'],
        'paths': {'module': 'frontend', 'sources': ['src'], 'tests': ['test']},
        'metadata': {},
        'packages': {},
        'dependencies': ['lit:compile'],
        'commands': {},
        'stats': {'source_files': 20, 'test_files': 8},
    }


def _empty_module_data() -> dict:
    """Sample module with no signals."""
    return {
        'name': 'empty',
        'build_systems': [],
        'paths': {'module': '.', 'sources': [], 'tests': []},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {},
    }


def _plugin_module_data() -> dict:
    """Sample marketplace plugin module data."""
    return {
        'name': 'pm-dev-java',
        'build_systems': ['marshall-plugin'],
        'paths': {'module': 'marketplace/bundles/pm-dev-java', 'sources': [], 'tests': []},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {},
    }


def _python_module_data() -> dict:
    """Sample python module data."""
    return {
        'name': 'python-project',
        'build_systems': ['python'],
        'paths': {'module': '.', 'sources': ['src'], 'tests': ['test']},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {'source_files': 15, 'test_files': 10},
    }


def _doc_module_data() -> dict:
    """Sample documentation module data."""
    return {
        'name': 'documentation',
        'build_systems': ['documentation'],
        'paths': {'module': 'doc', 'sources': ['doc'], 'tests': []},
        'metadata': {'description': 'Project documentation'},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {},
    }


def test_java_applies_to_maven_module():
    """Java ext: maven module -> applicable (high)."""
    ext = load_extension('pm-dev-java')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is True
    assert result['confidence'] == 'high'
    assert result['additive_to'] is None
    assert len(result['skills_by_profile']) > 0


def test_java_not_applicable_to_npm_module():
    """Java ext: npm module -> not applicable."""
    ext = load_extension('pm-dev-java')
    result = ext.applies_to_module(_npm_module_data())
    assert result['applicable'] is False


def test_frontend_applies_to_npm_module():
    """Frontend ext: npm module -> applicable (high)."""
    ext = load_extension('pm-dev-frontend')
    result = ext.applies_to_module(_npm_module_data())
    assert result['applicable'] is True
    assert result['confidence'] == 'high'


def test_frontend_not_applicable_to_maven_module():
    """Frontend ext: maven module -> not applicable."""
    ext = load_extension('pm-dev-frontend')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is False


def test_java_cui_applies_to_maven_with_additive():
    """Java-CUI ext: maven module -> applicable with additive_to='java'."""
    ext = load_extension('pm-dev-java-cui')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is True
    assert result['additive_to'] == 'java'


def test_java_cui_not_applicable_to_npm():
    """Java-CUI ext: npm module -> not applicable."""
    ext = load_extension('pm-dev-java-cui')
    result = ext.applies_to_module(_npm_module_data())
    assert result['applicable'] is False


def test_general_dev_applies_to_code_modules():
    """General-dev: code modules -> applicable."""
    ext = load_extension('plan-marshall')
    assert ext.applies_to_module(_maven_module_data())['applicable'] is True
    assert ext.applies_to_module(_npm_module_data())['applicable'] is True
    assert ext.applies_to_module(_python_module_data())['applicable'] is True
    result = ext.applies_to_module(_maven_module_data())
    assert result['confidence'] == 'high'


def test_general_dev_not_applicable_to_non_code_modules():
    """General-dev: doc/plugin/empty modules -> not applicable."""
    ext = load_extension('plan-marshall')
    assert ext.applies_to_module(_doc_module_data())['applicable'] is False
    assert ext.applies_to_module(_plugin_module_data())['applicable'] is False
    assert ext.applies_to_module(_empty_module_data())['applicable'] is False


def test_plan_marshall_get_skill_domains_multi():
    """plan-marshall provides both build and general-dev domains."""
    ext = load_extension('plan-marshall')
    all_domains = ext.get_skill_domains()

    assert len(all_domains) == 2
    keys = {d['domain']['key'] for d in all_domains}
    assert 'build' in keys
    assert 'general-dev' in keys


def test_plugin_dev_applies_to_marketplace_module():
    """Plugin-dev ext: marketplace module -> applicable."""
    ext = load_extension('pm-plugin-development')
    result = ext.applies_to_module(_plugin_module_data())
    assert result['applicable'] is True


def test_plugin_dev_not_applicable_to_plain_module():
    """Plugin-dev ext: plain module -> not applicable."""
    ext = load_extension('pm-plugin-development')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is False


def test_documents_only_documentation_profile():
    """pm-documents should only define core and documentation profiles."""
    ext = load_extension('pm-documents')
    domains = ext.get_skill_domains()[0]
    assert set(domains['profiles'].keys()) == {'core', 'documentation'}


def test_documents_applies_to_doc_module():
    """Documents ext: module with doc/ -> applicable."""
    ext = load_extension('pm-documents')
    result = ext.applies_to_module(_doc_module_data())
    assert result['applicable'] is True


def test_documents_not_applicable_to_maven_module():
    """Documents ext: plain maven module without doc -> not applicable."""
    ext = load_extension('pm-documents')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is False


def test_requirements_not_applicable():
    """Requirements ext: not applicable (default behavior)."""
    ext = load_extension('pm-requirements')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is False


def test_applies_to_module_result_structure():
    """All applies_to_module results have required keys."""
    required_keys = ['applicable', 'confidence', 'signals', 'additive_to', 'skills_by_profile']
    bundles = [
        'pm-dev-java',
        'pm-dev-frontend',
        'pm-dev-java-cui',
        'pm-dev-frontend-cui',
        'plan-marshall',
        'pm-plugin-development',
        'pm-documents',
        'pm-requirements',
    ]

    for bundle in bundles:
        ext = load_extension(bundle)
        result = ext.applies_to_module(_maven_module_data())
        for key in required_keys:
            assert key in result, f'{bundle}: applies_to_module missing key {key}'


# =============================================================================
# Profile Applicability Tests (signal detection + active_profiles)
# =============================================================================


def _maven_it_module_data() -> dict:
    """Maven module with integration test signals."""
    return {
        'name': 'integration-tests',
        'build_systems': ['maven'],
        'paths': {'module': 'integration-tests', 'sources': ['src/main/java'], 'tests': ['src/test/java']},
        'metadata': {'profiles': ['integration-test']},
        'packages': {},
        'dependencies': ['org.testcontainers:testcontainers:test'],
        'commands': {},
        'stats': {'source_files': 2, 'test_files': 10},
    }


def test_java_detect_applicable_profiles_with_it_signals():
    """Java ext: module with IT signals adds integration_testing to applicable set.

    Note: pm-dev-java doesn't define an integration_testing profile in get_skill_domains(),
    so the signal detection adds it to the applicable set but _build_applicable_result
    will skip it since it's not in profiles. This is correct behavior — the detection
    layer says "this profile WOULD apply" but it only takes effect if defined.
    """
    ext = load_extension('pm-dev-java')
    profiles = ext.get_skill_domains()[0]['profiles']
    detected = ext._detect_applicable_profiles(profiles, _maven_it_module_data())
    assert detected is not None
    # IT signals detected, so integration_testing is in the applicable set
    # (even though pm-dev-java doesn't define this profile, the signal is still detected)
    assert 'implementation' in detected
    assert 'module_testing' in detected
    assert 'quality' in detected


def test_java_detect_applicable_profiles_without_it_signals():
    """Java ext: plain module without IT signals excludes integration_testing."""
    ext = load_extension('pm-dev-java')
    profiles = ext.get_skill_domains()[0]['profiles']
    detected = ext._detect_applicable_profiles(profiles, _maven_module_data())
    assert detected is not None
    assert 'integration_testing' not in detected
    assert 'implementation' in detected


def test_java_detect_applicable_profiles_none_module():
    """Java ext: None module_data returns None (no filtering)."""
    ext = load_extension('pm-dev-java')
    profiles = ext.get_skill_domains()[0]['profiles']
    detected = ext._detect_applicable_profiles(profiles, None)
    assert detected is None


def test_java_applies_to_module_with_active_profiles():
    """Java ext: active_profiles filters output profiles."""
    ext = load_extension('pm-dev-java')
    result = ext.applies_to_module(
        _maven_module_data(),
        active_profiles={'implementation', 'quality'},
    )
    assert result['applicable'] is True
    assert 'implementation' in result['skills_by_profile']
    assert 'quality' in result['skills_by_profile']
    assert 'module_testing' not in result['skills_by_profile']


def test_java_applies_to_module_signal_detection_filters_it():
    """Java ext: signal detection excludes integration_testing for non-IT module."""
    ext = load_extension('pm-dev-java')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is True
    assert 'integration_testing' not in result['skills_by_profile']


def test_java_applies_to_module_signal_detection_it_module():
    """Java ext: IT module is applicable with standard profiles.

    pm-dev-java doesn't define an integration_testing profile (IT skills
    are optionals within module_testing), so signal detection doesn't
    add a new profile — it just correctly identifies the module as applicable.
    """
    ext = load_extension('pm-dev-java')
    result = ext.applies_to_module(_maven_it_module_data())
    assert result['applicable'] is True
    assert 'implementation' in result['skills_by_profile']
    assert 'module_testing' in result['skills_by_profile']


def test_general_dev_with_active_profiles():
    """General-dev ext: active_profiles filters output profiles."""
    ext = load_extension('plan-marshall')
    result = ext.applies_to_module(
        _maven_module_data(),
        active_profiles={'implementation'},
    )
    assert result['applicable'] is True
    assert 'implementation' in result['skills_by_profile']
    assert 'module_testing' not in result['skills_by_profile']


def test_frontend_with_active_profiles():
    """Frontend ext: active_profiles filters output profiles."""
    ext = load_extension('pm-dev-frontend')
    result = ext.applies_to_module(
        _npm_module_data(),
        active_profiles={'implementation', 'module_testing'},
    )
    assert result['applicable'] is True
    assert 'implementation' in result['skills_by_profile']
    assert 'module_testing' in result['skills_by_profile']
    assert 'quality' not in result['skills_by_profile']


def test_all_extensions_accept_active_profiles():
    """All extensions accept active_profiles parameter without error."""
    bundles_and_data = [
        ('pm-dev-java', _maven_module_data()),
        ('pm-dev-java-cui', _maven_module_data()),
        ('pm-dev-frontend', _npm_module_data()),
        ('pm-dev-frontend-cui', _npm_module_data()),
        ('pm-dev-python', _python_module_data()),
        ('pm-dev-oci', _empty_module_data()),
        ('pm-documents', _doc_module_data()),
        ('pm-plugin-development', _plugin_module_data()),
        ('plan-marshall', _maven_module_data()),
    ]
    for bundle, data in bundles_and_data:
        ext = load_extension(bundle)
        # Should not raise
        result = ext.applies_to_module(data, active_profiles={'implementation'})
        assert 'applicable' in result, f'{bundle}: missing applicable key'


# =============================================================================
# pm-dev-oci Extension Tests
# =============================================================================


def _docker_module_data(sources: list[str] | None = None) -> dict:
    """Sample module with container config files."""
    return {
        'name': 'app',
        'build_systems': ['maven'],
        'paths': {
            'module': '.',
            'sources': sources if sources is not None else ['Dockerfile', 'src/main/java'],
            'tests': [],
        },
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {},
    }


def test_oci_extension_skill_domains_structure():
    """Test pm-dev-oci get_skill_domains returns valid structure."""
    ext = load_extension('pm-dev-oci')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_domains_structure(domains, 'pm-dev-oci')
    assert not issues, f'Structure issues: {issues}'

    assert domains['domain']['key'] == 'oci-containers', "Domain key should be 'oci-containers'"


def test_oci_extension_skill_references_exist():
    """Test pm-dev-oci skill references point to existing skills."""
    ext = load_extension('pm-dev-oci')
    domains = ext.get_skill_domains()[0]

    issues = validate_skill_references(domains, 'pm-dev-oci')
    assert not issues, f'Missing skills: {issues}'


def test_oci_extension_triage_reference():
    """Test pm-dev-oci provides_triage returns valid reference."""
    ext = load_extension('pm-dev-oci')
    issues = validate_triage_and_outline_skill(ext, 'pm-dev-oci')
    assert not issues, f'Reference issues: {issues}'


def test_oci_applies_to_dockerfile_module():
    """OCI ext: module with Dockerfile -> applicable (high)."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data())
    assert result['applicable'] is True
    assert result['confidence'] == 'high'
    assert any('Dockerfile' in s for s in result['signals'])


def test_oci_applies_to_containerfile_module():
    """OCI ext: module with Containerfile -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['Containerfile']))
    assert result['applicable'] is True


def test_oci_applies_to_compose_module():
    """OCI ext: module with compose.yml -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['compose.yml']))
    assert result['applicable'] is True


def test_oci_applies_to_dockerignore():
    """OCI ext: module with .dockerignore -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['.dockerignore']))
    assert result['applicable'] is True


def test_oci_applies_to_containerignore():
    """OCI ext: module with .containerignore -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['.containerignore']))
    assert result['applicable'] is True


def test_oci_applies_to_hadolint_config():
    """OCI ext: module with .hadolint.yaml -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['.hadolint.yaml']))
    assert result['applicable'] is True


def test_oci_applies_to_trivyignore():
    """OCI ext: module with .trivyignore -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['.trivyignore']))
    assert result['applicable'] is True


def test_oci_applies_to_docker_directory():
    """OCI ext: module with docker/ directory path -> applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_docker_module_data(sources=['docker/Dockerfile']))
    assert result['applicable'] is True


def test_oci_applies_to_container_metadata():
    """OCI ext: module with container metadata -> applicable."""
    ext = load_extension('pm-dev-oci')
    data = _docker_module_data(sources=['src/main/java'])
    data['metadata']['packaging'] = 'docker'
    result = ext.applies_to_module(data)
    assert result['applicable'] is True


def test_oci_not_applicable_to_plain_module():
    """OCI ext: plain module without container signals -> not applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_maven_module_data())
    assert result['applicable'] is False


def test_oci_not_applicable_to_empty_module():
    """OCI ext: empty module -> not applicable."""
    ext = load_extension('pm-dev-oci')
    result = ext.applies_to_module(_empty_module_data())
    assert result['applicable'] is False


# =============================================================================
# Cross-Bundle Validation Tests
# =============================================================================


def test_all_extensions_have_unique_domain_keys():
    """Test that all extensions have unique domain keys."""
    bundles = [
        'pm-dev-java',
        'pm-dev-java-cui',
        'pm-dev-frontend',
        'pm-dev-frontend-cui',
        'pm-dev-python',
        'pm-dev-oci',
        'pm-plugin-development',
        'pm-requirements',
        'pm-documents',
        'plan-marshall',
    ]
    domain_keys = {}

    for bundle in bundles:
        try:
            ext = load_extension(bundle)
            all_domains = ext.get_skill_domains()
            for domains in all_domains:
                key = domains['domain']['key']
                if key in domain_keys:
                    raise AssertionError(f"Duplicate domain key '{key}' in {bundle} and {domain_keys[key]}")
                domain_keys[key] = bundle
        except FileNotFoundError:
            pass  # Skip bundles without extensions

    assert len(domain_keys) == 11, (
        f'Should have 11 unique domain keys, got {len(domain_keys)}: {sorted(domain_keys.keys())}'
    )


def test_all_extensions_have_required_functions():
    """Test that all extensions implement required functions."""
    bundles = [
        'pm-dev-java',
        'pm-dev-java-cui',
        'pm-dev-frontend',
        'pm-dev-frontend-cui',
        'pm-dev-python',
        'pm-dev-oci',
        'pm-plugin-development',
        'pm-requirements',
        'pm-documents',
        'plan-marshall',
    ]
    # Only get_skill_domains is required (abstract method)
    required = ['get_skill_domains']

    for bundle in bundles:
        try:
            ext = load_extension(bundle)

            for func_name in required:
                assert hasattr(ext, func_name), f'{bundle}: missing required function {func_name}'
                assert callable(getattr(ext, func_name)), f'{bundle}: {func_name} is not callable'
        except FileNotFoundError as err:
            raise AssertionError(f'{bundle}: extension.py not found') from err


# =============================================================================
# Main
# =============================================================================
