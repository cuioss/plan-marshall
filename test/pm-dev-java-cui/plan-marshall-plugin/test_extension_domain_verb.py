#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-java-cui extension's domain-verb declaration.

Pins provides_domain_verb() to the list-shaped multi-verb contract: the java-cui
domain owns two OpenRewrite finding signals, ``marker-detect`` (search-markers,
tree-scan) and ``rewrite-log-parse`` (parse-rewrite-log, log-parse). Tier 2
(direct import): loads the bundle extension.py and inspects
provides_domain_verb() directly.
"""

import importlib.util
import tempfile

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT

#: The two verbs the java-cui domain declares, keyed by verb type. Each entry is
#: {verb_type: notation}; the parse test derives the expected script filename by
#: converting the skill name's hyphens to underscores.
EXPECTED_VERBS = {
    'marker-detect': 'pm-dev-java-cui:search-markers',
    'rewrite-log-parse': 'pm-dev-java-cui:parse-rewrite-log',
}


def _load_extension():
    """Load the pm-dev-java-cui bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-java-cui' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_dev_java_cui', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _descriptors_by_verb() -> dict:
    """Return the declared descriptors keyed by verb type."""
    descriptors = _load_extension().provides_domain_verb()
    return {d['verb']: d for d in descriptors}


def test_provides_domain_verb_returns_a_non_empty_list():
    """The java-cui extension declares a non-None list of domain-verb descriptors."""
    # Act
    descriptors = _load_extension().provides_domain_verb()

    # Assert
    assert descriptors is not None, 'java-cui domain must declare its domain verbs'
    assert isinstance(descriptors, list)
    assert descriptors, 'the list must not be empty'


def test_list_declares_both_expected_verbs():
    """The list declares exactly the marker-detect and rewrite-log-parse verbs."""
    # Act
    by_verb = _descriptors_by_verb()

    # Assert
    assert set(by_verb.keys()) == set(EXPECTED_VERBS.keys())


def test_marker_detect_resolution_is_unbroken():
    """marker-detect (Signal A) is still declared with its original notation."""
    # Act
    by_verb = _descriptors_by_verb()

    # Assert
    assert by_verb['marker-detect']['notation'] == EXPECTED_VERBS['marker-detect']


def test_rewrite_log_parse_is_declared():
    """rewrite-log-parse (Signal B) is declared with its parser notation."""
    # Act
    by_verb = _descriptors_by_verb()

    # Assert
    assert by_verb['rewrite-log-parse']['notation'] == EXPECTED_VERBS['rewrite-log-parse']


def test_each_descriptor_carries_exactly_verb_and_notation():
    """Every descriptor is the two-field {verb, notation} shape from the contract."""
    # Act
    descriptors = _load_extension().provides_domain_verb()

    # Assert
    for descriptor in descriptors:
        assert set(descriptor.keys()) == {'verb', 'notation'}


def test_every_notation_points_at_this_bundle():
    """Every declared notation resolves within pm-dev-java-cui, not the core bundle."""
    # Act
    descriptors = _load_extension().provides_domain_verb()

    # Assert
    for descriptor in descriptors:
        assert descriptor['notation'].startswith('pm-dev-java-cui:')


def test_every_declared_notation_resolves_to_a_registered_script():
    """Each declared notation's skill exists on disk and carries its entry-point script."""
    # Arrange
    descriptors = _load_extension().provides_domain_verb()

    # Act / Assert
    for descriptor in descriptors:
        bundle, skill = descriptor['notation'].split(':', 1)
        skill_dir = MARKETPLACE_ROOT / bundle / 'skills' / skill
        # The entry-point script name is the skill name with hyphens as underscores.
        script_path = skill_dir / 'scripts' / f'{skill.replace("-", "_")}.py'

        assert skill_dir.is_dir(), f'Declared verb skill directory missing: {skill_dir}'
        assert (skill_dir / 'SKILL.md').is_file(), f'Declared verb skill has no SKILL.md: {skill_dir}'
        assert script_path.is_file(), f'Declared verb has no entry-point script: {script_path}'


def test_every_declared_skill_is_registered_in_plugin_json():
    """Each declared verb's skill is registered in the bundle's plugin.json."""
    # Arrange
    import json

    descriptors = _load_extension().provides_domain_verb()

    # Act / Assert
    for descriptor in descriptors:
        bundle, skill = descriptor['notation'].split(':', 1)
        plugin_json = MARKETPLACE_ROOT / bundle / '.claude-plugin' / 'plugin.json'
        skills = json.loads(plugin_json.read_text(encoding='utf-8'))['skills']
        assert f'./skills/{skill}' in skills, f'{skill} is not registered in {plugin_json}'


# =============================================================================
# get_skill_domains
# =============================================================================


def test_get_skill_domains_declares_the_java_cui_domain():
    """The extension declares exactly one domain keyed ``java-cui`` with profiles."""
    domains = _load_extension().get_skill_domains()

    assert isinstance(domains, list)
    assert len(domains) == 1
    assert domains[0]['domain']['key'] == 'java-cui'
    assert 'profiles' in domains[0]


def test_get_skill_domains_security_profile_defaults_to_cui_http():
    """The security profile ships cui-http as a request-sanitization default."""
    domains = _load_extension().get_skill_domains()

    security_defaults = domains[0]['profiles']['security']['defaults']
    assert any(entry['skill'] == 'pm-dev-java-cui:cui-http' for entry in security_defaults)


# =============================================================================
# applies_to_module
# =============================================================================


def test_applies_to_module_is_not_applicable_for_a_non_jvm_build():
    """A module built by neither Maven nor Gradle is not a java-cui module."""
    result = _load_extension().applies_to_module(
        {'build_systems': ['npm'], 'dependencies': [], 'packages': {}}
    )

    assert result['applicable'] is False
    assert result['confidence'] == 'none'
    assert result['additive_to'] is None


def test_applies_to_module_is_additive_to_java_for_a_maven_module():
    """A Maven module is a java-cui module, additive to the base java domain."""
    result = _load_extension().applies_to_module(
        {'build_systems': ['maven'], 'dependencies': [], 'packages': {}}
    )

    assert result['applicable'] is True
    assert result['additive_to'] == 'java'
    assert any('build_systems=maven' in signal for signal in result['signals'])


def test_applies_to_module_records_a_cui_dependency_signal():
    """A de.cuioss dependency is surfaced as an additional applicability signal."""
    module_data = {
        'build_systems': ['gradle'],
        'dependencies': ['de.cuioss:cui-core:1.0', 'org.other:lib:2.0'],
        'packages': {},
    }

    result = _load_extension().applies_to_module(module_data)

    assert result['applicable'] is True
    assert any('de.cuioss' in signal for signal in result['signals'])


# =============================================================================
# provides_recipes
# =============================================================================


def test_provides_recipes_returns_the_cui_logging_enforce_recipe():
    """The extension advertises the codebase-wide CUI logging-enforcement recipe."""
    recipes = _load_extension().provides_recipes()

    enforce = next(r for r in recipes if r['key'] == 'cui-logging-enforce')
    assert enforce['skill'] == 'pm-dev-java-cui:recipe-cui-logging-enforce'
    assert enforce['scope'] == 'codebase_wide'
    assert enforce['default_change_type'] == 'tech_debt'


# =============================================================================
# config_defaults (write-once Maven profile defaults)
# =============================================================================


def test_config_defaults_writes_cui_profile_map_and_skip_list():
    """config_defaults seeds the CUI canonical profile map and skip list."""
    from _config_core import ext_defaults_get

    with tempfile.TemporaryDirectory() as project_root:
        _load_extension().config_defaults(project_root)

        profile_map = ext_defaults_get('build.maven.profiles.map.canonical', project_root)
        skip = ext_defaults_get('build.maven.profiles.skip', project_root)

        assert profile_map is not None
        assert 'pre-commit:quality-gate' in profile_map
        assert skip is not None
        assert 'release' in skip


def test_config_defaults_is_write_once_and_preserves_existing_values():
    """config_defaults uses write-once semantics — a pre-existing canonical map
    is preserved, never overwritten."""
    from _config_core import ext_defaults_get, ext_defaults_set

    with tempfile.TemporaryDirectory() as project_root:
        ext_defaults_set('build.maven.profiles.map.canonical', 'custom:mapping', project_root)

        _load_extension().config_defaults(project_root)

        assert ext_defaults_get('build.maven.profiles.map.canonical', project_root) == 'custom:mapping'
