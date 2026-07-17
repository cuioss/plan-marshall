#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-documents Extension (documentation domain, Axis-A skill loading).

Covers the documentation-module skill alias: phase-4-plan's closed task-profile
enum (``{implementation, module_testing, verification}``) looks up
``skills_by_profile.implementation`` for every deliverable, so a documentation
module whose extension declares only ``core`` and ``documentation`` profiles
resolves an EMPTY skill set for doc tasks (lesson ``2026-07-16-17-011`` gap 1:
~39 AsciiDoc files shipped with no documentation-authoring skill). The fix
declares an ``implementation`` profile on the pm-documents domain so the core
doc skills fold into ``skills_by_profile.implementation`` via
``_build_applicable_result``'s core-merge.

The extension module lives under the skill's ``scripts``-adjacent directory and
shares the module basename ``extension`` with every other bundle's extension,
so the class is loaded via ``importlib.util.spec_from_file_location`` against
the explicit file path to avoid the cross-skill module-name collision.
"""

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
EXTENSION_FILE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-documents'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)

CORE_DOC_SKILLS = {
    'pm-documents:ref-asciidoc',
    'pm-documents:ref-documentation',
    'pm-documents:ref-narrative-styles',
    'pm-documents:ref-svg-diagrams',
}

DOCUMENTATION_OPTIONAL_SKILLS = {
    'plan-marshall:manage-adr',
    'pm-documents:manage-interface',
}


def _load_documents_extension():
    """Load the pm-documents Extension class by explicit file path."""
    spec = importlib.util.spec_from_file_location(
        'pm_documents_extension', EXTENSION_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EXTENSION_MODULE = _load_documents_extension()
Extension = _EXTENSION_MODULE.Extension


def _documentation_module_data() -> dict:
    """A documentation-module shape as produced by discover_modules()."""
    return {
        'name': 'documentation',
        'paths': {'module': 'doc'},
        'build_systems': ['documentation'],
        'metadata': {'description': 'Project documentation'},
    }


def _skill_names(entries: list[dict]) -> set[str]:
    return {entry['skill'] for entry in entries}


def test_get_skill_domains_declares_implementation_profile():
    """The domain declares an implementation profile key (the durable alias)."""
    # Arrange
    ext = Extension()

    # Act
    domains = ext.get_skill_domains()

    # Assert
    profiles = domains[0]['profiles']
    assert 'implementation' in profiles


def test_applies_to_module_resolves_nonempty_implementation_skills():
    """A documentation module resolves a non-empty skills_by_profile['implementation'].

    Reproduces lesson 2026-07-16-17-011 gap 1: before the fix, the extension
    declared only core+documentation profiles, so the implementation lookup
    phase-4-plan performs found nothing and doc tasks shipped with an empty
    skill set.
    """
    # Arrange
    ext = Extension()
    module_data = _documentation_module_data()

    # Act
    result = ext.applies_to_module(module_data)

    # Assert
    assert result['applicable'] is True
    implementation = result['skills_by_profile'].get('implementation')
    assert implementation is not None
    defaults = _skill_names(implementation['defaults'])
    assert defaults == CORE_DOC_SKILLS
    assert implementation['optionals'] == []


def test_applies_to_module_documentation_profile_unchanged():
    """The existing documentation profile output is unchanged by the alias."""
    # Arrange
    ext = Extension()
    module_data = _documentation_module_data()

    # Act
    result = ext.applies_to_module(module_data)

    # Assert
    documentation = result['skills_by_profile'].get('documentation')
    assert documentation is not None
    assert _skill_names(documentation['defaults']) == CORE_DOC_SKILLS
    assert _skill_names(documentation['optionals']) == DOCUMENTATION_OPTIONAL_SKILLS


def test_applies_to_module_not_applicable_without_doc_signals():
    """A module with no documentation signal stays not-applicable (no skill leak)."""
    # Arrange
    ext = Extension()
    module_data = {
        'name': 'backend',
        'paths': {'module': 'backend', 'sources': ['backend/src']},
        'build_systems': ['maven'],
    }

    # Act
    result = ext.applies_to_module(module_data)

    # Assert
    assert result['applicable'] is False
    assert result['skills_by_profile'] == {}


def test_applies_to_module_respects_active_profiles_filter():
    """An explicit active_profiles filter still gates the implementation alias."""
    # Arrange
    ext = Extension()
    module_data = _documentation_module_data()

    # Act
    result = ext.applies_to_module(module_data, active_profiles={'documentation'})

    # Assert
    assert 'implementation' not in result['skills_by_profile']
    assert 'documentation' in result['skills_by_profile']
