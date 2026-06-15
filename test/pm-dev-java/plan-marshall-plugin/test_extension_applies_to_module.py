#!/usr/bin/env python3
"""Tests for the pm-dev-java extension's applies_to_module() conditional defaults.

Guards the dependency-driven promotion/demotion of java-cdi and java-lombok
between a profile's defaults and optionals lists. When a CDI dependency is
present the java-cdi skill must be promoted from optionals to defaults; when
absent it must remain (or be demoted back to) optionals. The same conditional
applies to java-lombok with a Lombok dependency.

Tier 2 (direct import): loads the bundle extension.py and inspects the
applies_to_module() return value directly.
"""

import importlib.util

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import MARKETPLACE_ROOT


def _load_extension():
    """Load the pm-dev-java bundle extension.py and return an Extension instance."""
    extension_path = MARKETPLACE_ROOT / 'pm-dev-java' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_dev_java', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _module_data(dependencies):
    """Build a minimal Maven module_data carrying the given dependency strings."""
    return {
        'name': 'sample-module',
        'build_systems': ['maven'],
        'dependencies': dependencies,
    }


def _skill_in(entries, marker):
    """True iff any entry's 'skill' value contains marker."""
    return any(isinstance(e, dict) and marker in e.get('skill', '') for e in entries)


def test_java_cdi_promoted_to_defaults_when_cdi_dep_present():
    """With a CDI dependency present, java-cdi is a default for implementation."""
    # Arrange
    extension = _load_extension()
    module_data = _module_data(['jakarta.enterprise.cdi-api:4.0.1'])

    # Act
    result = extension.applies_to_module(module_data)

    # Assert
    impl = result['skills_by_profile']['implementation']
    assert _skill_in(impl['defaults'], 'java-cdi')
    assert not _skill_in(impl['optionals'], 'java-cdi')


def test_java_cdi_remains_optional_when_cdi_dep_absent():
    """With no CDI dependency, java-cdi stays optional for implementation (no regression)."""
    # Arrange
    extension = _load_extension()
    module_data = _module_data(['org.apache.commons:commons-lang3:3.14.0'])

    # Act
    result = extension.applies_to_module(module_data)

    # Assert
    impl = result['skills_by_profile']['implementation']
    assert _skill_in(impl['optionals'], 'java-cdi')
    assert not _skill_in(impl['defaults'], 'java-cdi')


def test_java_lombok_promoted_to_defaults_when_lombok_dep_present():
    """With a Lombok dependency present, java-lombok is promoted to defaults.

    java-lombok is declared in the bundle's ``core`` optionals, which
    _build_applicable_result merges into every applicable profile; assert
    against the ``implementation`` profile that carries the merged entry.
    """
    # Arrange
    extension = _load_extension()
    module_data = _module_data(['org.projectlombok:lombok:1.18.30'])

    # Act
    result = extension.applies_to_module(module_data)

    # Assert
    impl = result['skills_by_profile']['implementation']
    assert _skill_in(impl['defaults'], 'java-lombok')
    assert not _skill_in(impl['optionals'], 'java-lombok')


def test_java_lombok_remains_optional_when_lombok_dep_absent():
    """With no Lombok dependency, java-lombok stays optional (no regression)."""
    # Arrange
    extension = _load_extension()
    module_data = _module_data(['org.apache.commons:commons-lang3:3.14.0'])

    # Act
    result = extension.applies_to_module(module_data)

    # Assert
    impl = result['skills_by_profile']['implementation']
    assert _skill_in(impl['optionals'], 'java-lombok')
    assert not _skill_in(impl['defaults'], 'java-lombok')
