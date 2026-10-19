#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-dev-java extension's applies_to_module() conditional defaults.

Guards the dependency-driven promotion/demotion of java-cdi and java-lombok
between a profile's defaults and optionals lists. When a CDI dependency is
present the java-cdi skill must be promoted from optionals to defaults; when
absent it must remain (or be demoted back to) optionals. The same conditional
applies to java-lombok with a Lombok dependency.

Tier 2 (direct import): loads the bundle extension.py and inspects the
applies_to_module() return value directly.
"""

# Import shared infrastructure (conftest.py sets up PYTHONPATH for extension_base).
from conftest import load_skill_module


def _load_extension():
    """Load the pm-dev-java bundle extension.py and return an Extension instance."""
    module = load_skill_module('pm-dev-java', 'plan-marshall-plugin', 'extension.py', 'extension_pm_dev_java')
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


def _declared_module_data(declared):
    """Build a cheap-crawl module dict carrying only ``declared_dependencies``."""
    return {
        'name': 'sample-module',
        'build_systems': ['maven'],
        'dependencies': [],
        'declared_dependencies': declared,
    }


def test_qualifies_optional_rejects_cdi_dependent_skills_without_cdi():
    """Without a CDI dependency none of the CDI-dependent optionals qualify."""
    extension = _load_extension()
    module_data = _declared_module_data([{'group_id': 'org.apache.commons', 'artifact_id': 'commons-lang3'}])

    for skill in (
        'pm-dev-java:java-cdi',
        'pm-dev-java:java-quarkus',
        'pm-dev-java:junit-weld-testing',
    ):
        assert extension.qualifies_optional('implementation', skill, module_data) is False, skill


def test_qualifies_optional_admits_cdi_skills_from_declared_dependency_objects():
    """A declared ``jakarta.enterprise`` dependency object qualifies java-cdi."""
    extension = _load_extension()
    module_data = _declared_module_data(
        [{'group_id': 'jakarta.enterprise', 'artifact_id': 'jakarta.enterprise.cdi-api'}]
    )

    assert extension.qualifies_optional('implementation', 'pm-dev-java:java-cdi', module_data) is True


def test_qualifies_optional_admits_module_agnostic_optionals():
    """An optional with no module-level signal stays applicable."""
    extension = _load_extension()
    module_data = _declared_module_data([])

    assert extension.qualifies_optional('implementation', 'pm-dev-java:java-maintenance', module_data) is True


def test_qualifies_optional_treats_quarkus_arc_as_a_cdi_signal():
    """io.quarkus:quarkus-arc is a CDI implementation and qualifies java-cdi."""
    extension = _load_extension()
    module_data = _declared_module_data([{'group_id': 'io.quarkus', 'artifact_id': 'quarkus-arc'}])

    assert extension.qualifies_optional('implementation', 'pm-dev-java:java-cdi', module_data) is True


def test_cdi_gated_set_is_declared_on_the_skill_entries():
    """The gated set is carried by declaration markers, not a hand-maintained name list."""
    extension = _load_extension()
    requirements = {
        entry['skill']: entry.get('requires')
        for domain_info in extension.get_skill_domains()
        for profile_data in domain_info['profiles'].values()
        for entry in profile_data.get('defaults', []) + profile_data.get('optionals', [])
        if isinstance(entry, dict)
    }

    assert requirements['pm-dev-java:java-cdi'] == 'cdi'
    assert requirements['pm-dev-java:java-quarkus'] == 'cdi'
    assert requirements['pm-dev-java:junit-weld-testing'] == 'cdi'
    assert requirements['pm-dev-java:java-lombok'] == 'lombok'
    assert requirements.get('pm-dev-java:java-maintenance') is None
