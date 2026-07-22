#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-java-cui extension's domain-verb declaration.

Pins provides_domain_verb() to the marker-detect descriptor so the java-cui
domain's marker gate resolves. Tier 2 (direct import): loads the bundle
extension.py and inspects provides_domain_verb() directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT


def _load_extension():
    """Load the pm-dev-java-cui bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-java-cui' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_dev_java_cui', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def test_provides_domain_verb_returns_descriptor():
    """The java-cui extension declares a non-None domain-verb descriptor."""
    # Act
    descriptor = _load_extension().provides_domain_verb()

    # Assert
    assert descriptor is not None, 'java-cui domain must declare its marker-detect verb'
    assert isinstance(descriptor, dict)


def test_provides_domain_verb_names_marker_detect():
    """The descriptor's verb type is the marker-detect capability key."""
    # Act
    descriptor = _load_extension().provides_domain_verb()

    # Assert
    assert descriptor['verb'] == 'marker-detect'


def test_provides_domain_verb_carries_exactly_verb_and_notation():
    """The descriptor is the two-field {verb, notation} shape from the contract."""
    # Act
    descriptor = _load_extension().provides_domain_verb()

    # Assert
    assert set(descriptor.keys()) == {'verb', 'notation'}


def test_provides_domain_verb_notation_points_at_this_bundle():
    """The notation resolves within pm-dev-java-cui, not the core bundle."""
    # Act
    notation = _load_extension().provides_domain_verb()['notation']

    # Assert
    assert notation == 'pm-dev-java-cui:search-markers'


def test_declared_notation_resolves_to_a_registered_script():
    """The declared notation's skill exists on disk and carries its entry-point script."""
    # Arrange
    notation = _load_extension().provides_domain_verb()['notation']
    bundle, skill = notation.split(':', 1)

    # Act
    skill_dir = MARKETPLACE_ROOT / bundle / 'skills' / skill
    script_path = skill_dir / 'scripts' / 'search_markers.py'

    # Assert
    assert skill_dir.is_dir(), f'Declared verb skill directory missing: {skill_dir}'
    assert (skill_dir / 'SKILL.md').is_file(), f'Declared verb skill has no SKILL.md: {skill_dir}'
    assert script_path.is_file(), f'Declared verb has no entry-point script: {script_path}'


def test_declared_skill_is_registered_in_plugin_json():
    """The declared verb's skill is registered in the bundle's plugin.json."""
    # Arrange
    import json

    notation = _load_extension().provides_domain_verb()['notation']
    bundle, skill = notation.split(':', 1)
    plugin_json = MARKETPLACE_ROOT / bundle / '.claude-plugin' / 'plugin.json'

    # Act
    skills = json.loads(plugin_json.read_text(encoding='utf-8'))['skills']

    # Assert
    assert f'./skills/{skill}' in skills, f'{skill} is not registered in {plugin_json}'
