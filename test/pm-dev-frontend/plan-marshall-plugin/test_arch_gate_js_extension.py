#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-frontend extension's arch-gate declaration.

Pins provides_arch_gate() to the dependency-cruiser single-field descriptor so
the javascript domain's arch-gate verify-step append fires. Tier 2 (direct
import): loads the bundle extension.py and inspects provides_arch_gate() directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT


def _load_extension():
    """Load the pm-dev-frontend bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-frontend' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_dev_frontend', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def test_provides_arch_gate_returns_descriptor():
    """The javascript extension declares a non-None arch-gate descriptor."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert descriptor is not None, 'javascript domain must declare an arch-gate tool'
    assert isinstance(descriptor, dict)


def test_provides_arch_gate_names_dependency_cruiser():
    """The arch-gate descriptor names dependency-cruiser as the native tool."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert descriptor['tool'] == 'dependency-cruiser'


def test_provides_arch_gate_is_single_field():
    """The descriptor is single-field — only 'tool', no execution_mode variant."""
    # Act
    descriptor = _load_extension().provides_arch_gate()

    # Assert
    assert set(descriptor.keys()) == {'tool'}, 'descriptor carries only the tool name'


# =============================================================================
# get_skill_domains
# =============================================================================


def test_get_skill_domains_declares_the_javascript_domain():
    """The extension declares exactly one domain keyed ``javascript`` with the
    four skill-loading profiles."""
    domains = _load_extension().get_skill_domains()

    assert isinstance(domains, list)
    assert len(domains) == 1
    assert domains[0]['domain']['key'] == 'javascript'
    profiles = domains[0]['profiles']
    assert {'core', 'implementation', 'module_testing', 'security'} <= set(profiles)


def test_get_skill_domains_profiles_declare_their_package_sources():
    """The implementation profile reads production packages, module_testing reads
    test packages — the package_source discriminator that drives optional-skill
    activation."""
    profiles = _load_extension().get_skill_domains()[0]['profiles']

    assert profiles['implementation']['package_source'] == 'packages'
    assert profiles['module_testing']['package_source'] == 'test_packages'


def test_get_skill_domains_security_profile_defaults_to_javascript_security():
    """The security profile ships the javascript-security skill as a default."""
    security_defaults = _load_extension().get_skill_domains()[0]['profiles']['security']['defaults']

    assert any(entry['skill'] == 'pm-dev-frontend:javascript-security' for entry in security_defaults)


# =============================================================================
# applies_to_module
# =============================================================================


def test_applies_to_module_is_not_applicable_without_npm():
    """A module not built by npm is not a javascript module."""
    result = _load_extension().applies_to_module(
        {'build_systems': ['maven'], 'packages': {}, 'test_packages': {}}
    )

    assert result['applicable'] is False
    assert result['confidence'] == 'none'
    assert result['additive_to'] is None


def test_applies_to_module_is_applicable_for_an_npm_module():
    """An npm module is a javascript module, surfaced with its build-system signal."""
    result = _load_extension().applies_to_module(
        {'build_systems': ['npm'], 'packages': {}, 'test_packages': {}}
    )

    assert result['applicable'] is True
    assert 'build_systems=npm' in result['signals']


# =============================================================================
# provides_triage
# =============================================================================


def test_provides_triage_points_at_the_js_triage_skill():
    """The javascript domain delegates finding triage to ext-triage-js."""
    assert _load_extension().provides_triage() == 'pm-dev-frontend:ext-triage-js'
