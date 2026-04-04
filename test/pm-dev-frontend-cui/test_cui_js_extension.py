#!/usr/bin/env python3
"""Tests for pm-dev-frontend-cui extension.py.

Verifies the Extension class API contract:
- get_skill_domains(): correct domain key, name, description, profile structure
- applies_to_module(): applicable for npm+maven, not applicable for npm-only or maven-only
- config_defaults(): sets expected Maven profile mappings
- additive_to: 'javascript'
"""

import importlib.util
import json
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT

# =============================================================================
# Extension Loader
# =============================================================================


def load_frontend_cui_extension():
    """Load pm-dev-frontend-cui extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-frontend-cui' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    assert extension_path.exists(), f'Extension not found: {extension_path}'

    spec = importlib.util.spec_from_file_location('extension_pm_dev_frontend_cui', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    assert hasattr(module, 'Extension'), 'Extension class not found in extension.py'
    return module.Extension()


# =============================================================================
# Module data helpers
# =============================================================================


def _npm_maven_module_data(**extra) -> dict:
    """Sample module with both npm and maven (CUI JS dual build system)."""
    data = {
        'name': 'cui-frontend',
        'build_systems': ['npm', 'maven'],
        'paths': {'module': 'cui-frontend', 'sources': ['src'], 'tests': ['test']},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {'source_files': 20, 'test_files': 8},
    }
    data.update(extra)
    return data


def _npm_only_module_data() -> dict:
    """Sample module with only npm (no maven)."""
    return {
        'name': 'pure-frontend',
        'build_systems': ['npm'],
        'paths': {'module': 'pure-frontend', 'sources': ['src'], 'tests': ['test']},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {'source_files': 10, 'test_files': 3},
    }


def _maven_only_module_data() -> dict:
    """Sample module with only maven (no npm)."""
    return {
        'name': 'java-module',
        'build_systems': ['maven'],
        'paths': {'module': 'core', 'sources': ['src/main/java'], 'tests': ['src/test/java']},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'commands': {},
        'stats': {'source_files': 30, 'test_files': 15},
    }


def _empty_module_data() -> dict:
    """Module with no build systems."""
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


# =============================================================================
# get_skill_domains() tests
# =============================================================================


def test_get_skill_domains_returns_list():
    """get_skill_domains() returns a non-empty list."""
    ext = load_frontend_cui_extension()
    domains = ext.get_skill_domains()
    assert isinstance(domains, list), 'get_skill_domains() must return a list'
    assert len(domains) == 1, 'pm-dev-frontend-cui provides exactly one domain'


def test_get_skill_domains_domain_key():
    """get_skill_domains() returns domain key 'javascript-cui'."""
    ext = load_frontend_cui_extension()
    domain = ext.get_skill_domains()[0]['domain']
    assert domain['key'] == 'javascript-cui', f"Domain key should be 'javascript-cui', got '{domain['key']}'"


def test_get_skill_domains_domain_name():
    """get_skill_domains() returns a non-empty domain name."""
    ext = load_frontend_cui_extension()
    domain = ext.get_skill_domains()[0]['domain']
    assert isinstance(domain['name'], str) and domain['name'], 'Domain name must be non-empty string'


def test_get_skill_domains_domain_description():
    """get_skill_domains() returns a non-empty domain description."""
    ext = load_frontend_cui_extension()
    domain = ext.get_skill_domains()[0]['domain']
    assert isinstance(domain.get('description'), str) and domain['description'], (
        'Domain description must be non-empty string'
    )


def test_get_skill_domains_has_profiles():
    """get_skill_domains() includes 'profiles' key."""
    ext = load_frontend_cui_extension()
    item = ext.get_skill_domains()[0]
    assert 'profiles' in item, "get_skill_domains() item must have 'profiles' key"


def test_get_skill_domains_core_profile_has_cui_javascript_project():
    """core.defaults includes pm-dev-frontend-cui:cui-javascript-project."""
    ext = load_frontend_cui_extension()
    profiles = ext.get_skill_domains()[0]['profiles']
    core_defaults = profiles.get('core', {}).get('defaults', [])

    # Extract skill refs from dict or string entries
    skill_refs = []
    for entry in core_defaults:
        if isinstance(entry, dict):
            skill_refs.append(entry.get('skill', ''))
        else:
            skill_refs.append(entry)

    assert 'pm-dev-frontend-cui:cui-javascript-project' in skill_refs, (
        "core.defaults must include 'pm-dev-frontend-cui:cui-javascript-project'"
    )


def test_get_skill_domains_profile_structure():
    """All profiles have 'defaults' and 'optionals' lists."""
    ext = load_frontend_cui_extension()
    profiles = ext.get_skill_domains()[0]['profiles']

    for category, config in profiles.items():
        assert isinstance(config, dict), f'profiles.{category} must be a dict'
        assert 'defaults' in config, f'profiles.{category} missing defaults'
        assert 'optionals' in config, f'profiles.{category} missing optionals'
        assert isinstance(config['defaults'], list), f'profiles.{category}.defaults must be list'
        assert isinstance(config['optionals'], list), f'profiles.{category}.optionals must be list'


def test_get_skill_domains_cui_javascript_project_skill_exists():
    """The cui-javascript-project skill referenced in core.defaults actually exists."""
    skill_path = MARKETPLACE_ROOT / 'pm-dev-frontend-cui' / 'skills' / 'cui-javascript-project'
    assert skill_path.is_dir(), f'Skill directory not found: {skill_path}'
    has_content = (
        (skill_path / 'SKILL.md').exists()
        or len(list(skill_path.glob('*.md'))) > 0
        or len(list(skill_path.glob('scripts/*.py'))) > 0
    )
    assert has_content, f'Skill directory exists but has no content: {skill_path}'


# =============================================================================
# applies_to_module() tests
# =============================================================================


def test_applies_to_module_npm_and_maven_is_applicable():
    """applies_to_module() returns applicable=True for modules with both npm and maven."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_maven_module_data())
    assert result['applicable'] is True, 'npm+maven module should be applicable'


def test_applies_to_module_npm_and_maven_confidence_high():
    """applies_to_module() returns confidence=high for npm+maven module."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_maven_module_data())
    assert result['confidence'] == 'high', f"Expected confidence='high', got '{result['confidence']}'"


def test_applies_to_module_npm_only_not_applicable():
    """applies_to_module() returns applicable=False for npm-only module (no maven)."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_only_module_data())
    assert result['applicable'] is False, 'npm-only module should not be applicable'


def test_applies_to_module_maven_only_not_applicable():
    """applies_to_module() returns applicable=False for maven-only module (no npm)."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_maven_only_module_data())
    assert result['applicable'] is False, 'maven-only module should not be applicable'


def test_applies_to_module_empty_not_applicable():
    """applies_to_module() returns applicable=False for module with no build systems."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_empty_module_data())
    assert result['applicable'] is False, 'empty module should not be applicable'


def test_applies_to_module_additive_to_javascript():
    """applies_to_module() returns additive_to='javascript' for applicable modules."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_maven_module_data())
    assert result['additive_to'] == 'javascript', f"Expected additive_to='javascript', got '{result['additive_to']}'"


def test_applies_to_module_not_applicable_additive_to_none():
    """applies_to_module() returns additive_to=None when not applicable."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_only_module_data())
    assert result['additive_to'] is None, 'Not-applicable result should have additive_to=None'


def test_applies_to_module_result_has_required_keys():
    """applies_to_module() result always has all required keys."""
    required_keys = ['applicable', 'confidence', 'signals', 'additive_to', 'skills_by_profile']
    ext = load_frontend_cui_extension()

    for module_data in [_npm_maven_module_data(), _npm_only_module_data(), _empty_module_data()]:
        result = ext.applies_to_module(module_data)
        for key in required_keys:
            assert key in result, f"applies_to_module() missing key '{key}'"


def test_applies_to_module_with_cui_deps_signals():
    """applies_to_module() detects de.cuioss dependencies as additional signal."""
    ext = load_frontend_cui_extension()
    module_data = _npm_maven_module_data(dependencies=['de.cuioss.portal:portal-common:compile'])
    result = ext.applies_to_module(module_data)
    assert result['applicable'] is True
    signals_str = ' '.join(result['signals'])
    assert 'de.cuioss' in signals_str, 'CUI dependency signal should be present'


def test_applies_to_module_with_frontend_maven_plugin_signal():
    """applies_to_module() detects frontend-maven-plugin as canonical signal."""
    ext = load_frontend_cui_extension()
    module_data = _npm_maven_module_data(dependencies=['com.github.eirslett:frontend-maven-plugin:1.12.1'])
    result = ext.applies_to_module(module_data)
    assert result['applicable'] is True
    signals_str = ' '.join(result['signals'])
    assert 'frontend-maven-plugin' in signals_str, 'frontend-maven-plugin signal should be present'


def test_applies_to_module_accepts_active_profiles():
    """applies_to_module() accepts active_profiles parameter without error."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_maven_module_data(), active_profiles={'implementation', 'core'})
    assert 'applicable' in result, 'Result must have applicable key'


def test_applies_to_module_skills_by_profile_populated():
    """applies_to_module() populates skills_by_profile for applicable module."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_maven_module_data())
    assert result['applicable'] is True
    assert isinstance(result['skills_by_profile'], dict), 'skills_by_profile must be a dict'


# =============================================================================
# config_defaults() tests
# =============================================================================


def test_config_defaults_sets_profiles_map():
    """config_defaults() sets build.maven.profiles.map.canonical in extension_defaults."""
    ext = load_frontend_cui_extension()

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_dir = Path(tmpdir) / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({}), encoding='utf-8')

        ext.config_defaults(tmpdir)

        config = json.loads(marshal_path.read_text(encoding='utf-8'))
        ext_defaults = config.get('extension_defaults', {})

        assert 'build.maven.profiles.map.canonical' in ext_defaults, (
            'config_defaults() must set build.maven.profiles.map.canonical'
        )
        profiles_map = ext_defaults['build.maven.profiles.map.canonical']
        assert 'pre-commit' in profiles_map, f"profiles.map.canonical should contain 'pre-commit', got: {profiles_map}"
        assert 'coverage' in profiles_map, f"profiles.map.canonical should contain 'coverage', got: {profiles_map}"


def test_config_defaults_sets_profiles_skip():
    """config_defaults() sets build.maven.profiles.skip in extension_defaults."""
    ext = load_frontend_cui_extension()

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_dir = Path(tmpdir) / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        marshal_path.write_text(json.dumps({}), encoding='utf-8')

        ext.config_defaults(tmpdir)

        config = json.loads(marshal_path.read_text(encoding='utf-8'))
        ext_defaults = config.get('extension_defaults', {})

        assert 'build.maven.profiles.skip' in ext_defaults, 'config_defaults() must set build.maven.profiles.skip'
        skip_val = ext_defaults['build.maven.profiles.skip']
        assert skip_val, 'profiles.skip value must be non-empty'


def test_config_defaults_write_once_semantics():
    """config_defaults() does not overwrite existing extension_defaults values."""
    ext = load_frontend_cui_extension()

    with tempfile.TemporaryDirectory() as tmpdir:
        plan_dir = Path(tmpdir) / '.plan'
        plan_dir.mkdir()
        marshal_path = plan_dir / 'marshal.json'
        pre_existing = 'my-custom-mapping'
        marshal_path.write_text(
            json.dumps({'extension_defaults': {'build.maven.profiles.map.canonical': pre_existing}}),
            encoding='utf-8',
        )

        ext.config_defaults(tmpdir)

        config = json.loads(marshal_path.read_text(encoding='utf-8'))
        ext_defaults = config.get('extension_defaults', {})

        # write-once semantics: pre-existing value must not be overwritten
        assert ext_defaults.get('build.maven.profiles.map.canonical') == pre_existing, (
            'config_defaults() must not overwrite pre-existing extension_defaults values'
        )


# =============================================================================
# additive_to contract
# =============================================================================


def test_additive_to_javascript_when_applicable():
    """Extension is additive to 'javascript' domain, not standalone."""
    ext = load_frontend_cui_extension()
    result = ext.applies_to_module(_npm_maven_module_data())
    assert result['additive_to'] == 'javascript', "pm-dev-frontend-cui must be additive to 'javascript'"


if __name__ == '__main__':
    import traceback

    tests = [
        test_get_skill_domains_returns_list,
        test_get_skill_domains_domain_key,
        test_get_skill_domains_domain_name,
        test_get_skill_domains_domain_description,
        test_get_skill_domains_has_profiles,
        test_get_skill_domains_core_profile_has_cui_javascript_project,
        test_get_skill_domains_profile_structure,
        test_get_skill_domains_cui_javascript_project_skill_exists,
        test_applies_to_module_npm_and_maven_is_applicable,
        test_applies_to_module_npm_and_maven_confidence_high,
        test_applies_to_module_npm_only_not_applicable,
        test_applies_to_module_maven_only_not_applicable,
        test_applies_to_module_empty_not_applicable,
        test_applies_to_module_additive_to_javascript,
        test_applies_to_module_not_applicable_additive_to_none,
        test_applies_to_module_result_has_required_keys,
        test_applies_to_module_with_cui_deps_signals,
        test_applies_to_module_with_frontend_maven_plugin_signal,
        test_applies_to_module_accepts_active_profiles,
        test_applies_to_module_skills_by_profile_populated,
        test_config_defaults_sets_profiles_map,
        test_config_defaults_sets_profiles_skip,
        test_config_defaults_write_once_semantics,
        test_additive_to_javascript_when_applicable,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f'FAILED: {test.__name__}')
            traceback.print_exc()
            print()

    print(f'\nResults: {passed} passed, {failed} failed')
    import sys

    sys.exit(0 if failed == 0 else 1)
