#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-bundle extension skill-profile composition tests.

One parametrized module pins the skill-profile invariant for every bundle
extension that declares one: the profile key is present on the domain, and
(where the profile carries defaults) it resolves the bundle's focused skill.
Adding a bundle adds a row to :data:`_PROFILE_ROWS`, not a new module.

The module is cross-bundle by definition, so it lives under ``test/marketplace/``
rather than any single ``test/<bundle>/plan-marshall-plugin/`` directory — which
also puts it back inside mypy's scope (``test/*/plan-marshall-plugin/`` is
excluded because a hyphenated directory is not a valid package name).

Tier 2 (direct import): each bundle's ``extension.py`` is loaded by explicit
file path via ``importlib.util.spec_from_file_location``, because every bundle
ships that same module basename.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import pytest

from conftest import MARKETPLACE_ROOT

# (bundle, domain_key, profile, expected_skill). ``expected_skill`` is None for
# a profile that is declared as a resolution alias and carries no defaults of
# its own — pm-documents' ``implementation`` profile folds in the core doc
# skills via ``_build_applicable_result``'s core-merge instead.
_PROFILE_ROWS: tuple[tuple[str, str, str, str | None], ...] = (
    ('pm-dev-python', 'python', 'security', 'pm-dev-python:python-security'),
    ('pm-dev-java', 'java', 'security', 'pm-dev-java:java-security'),
    ('pm-dev-java-cui', 'java-cui', 'security', 'pm-dev-java-cui:cui-http'),
    ('pm-dev-oci', 'oci-containers', 'security', 'pm-dev-oci:oci-security'),
    ('pm-dev-frontend', 'javascript', 'security', 'pm-dev-frontend:javascript-security'),
    ('pm-plugin-development', 'plan-marshall-plugin-dev', 'security', 'pm-plugin-development:plugin-security'),
    ('pm-documents', 'documentation', 'implementation', None),
)

_SKILL_BEARING_ROWS = tuple(row for row in _PROFILE_ROWS if row[3] is not None)

# pm-documents behavioural expectations (the documentation-module skill alias).
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


def _load_extension(bundle: str) -> Any:
    """Load ``<bundle>``'s plan-marshall-plugin extension and return an instance."""
    extension_path = MARKETPLACE_ROOT / bundle / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    module_name = f'extension_{bundle.replace("-", "_")}'
    spec = importlib.util.spec_from_file_location(module_name, extension_path)
    assert spec is not None and spec.loader is not None, f'no import spec for {extension_path}'
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _domain(bundle: str, domain_key: str) -> dict:
    """Return the named domain entry from ``<bundle>``'s get_skill_domains()."""
    domains = _load_extension(bundle).get_skill_domains()
    return next(d for d in domains if d['domain']['key'] == domain_key)


def _profile_defaults(bundle: str, domain_key: str, profile: str) -> list[str]:
    """Return the default skill identifiers declared by ``profile``."""
    entries = _domain(bundle, domain_key)['profiles'][profile]['defaults']
    return [entry['skill'] for entry in entries]


@pytest.mark.parametrize('bundle,domain_key,profile,expected_skill', _PROFILE_ROWS)
def test_profile_is_declared(bundle, domain_key, profile, expected_skill):
    """Each bundle's domain declares the profile key its consumers look up."""
    # Act
    profiles = _domain(bundle, domain_key)['profiles']

    # Assert
    assert profile in profiles, f'{bundle}:{domain_key} must declare the {profile!r} profile'


@pytest.mark.parametrize('bundle,domain_key,profile,expected_skill', _SKILL_BEARING_ROWS)
def test_profile_resolves_focused_skill(bundle, domain_key, profile, expected_skill):
    """The profile resolves the bundle's focused skill (and is therefore non-empty)."""
    # Act
    defaults = _profile_defaults(bundle, domain_key, profile)

    # Assert
    assert expected_skill in defaults, f'{bundle} {profile} profile must resolve {expected_skill}'


# =============================================================================
# pm-documents documentation-module skill alias (behaviour beyond the table)
#
# phase-4-plan's closed task-profile enum ({implementation, module_testing,
# verification}) looks up skills_by_profile.implementation for every
# deliverable, so a documentation module whose extension declares only core and
# documentation profiles resolves an EMPTY skill set for doc tasks (lesson
# 2026-07-16-17-011 gap 1). The alias folds the core doc skills into
# skills_by_profile.implementation via _build_applicable_result's core-merge.
# =============================================================================


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


def test_documents_resolves_nonempty_implementation_skills():
    """A documentation module resolves a non-empty skills_by_profile['implementation']."""
    # Arrange
    ext = _load_extension('pm-documents')

    # Act
    result = ext.applies_to_module(_documentation_module_data())

    # Assert
    assert result['applicable'] is True
    implementation = result['skills_by_profile'].get('implementation')
    assert implementation is not None
    assert _skill_names(implementation['defaults']) == CORE_DOC_SKILLS
    assert implementation['optionals'] == []


def test_documents_documentation_profile_unchanged():
    """The existing documentation profile output is unchanged by the alias."""
    # Arrange
    ext = _load_extension('pm-documents')

    # Act
    result = ext.applies_to_module(_documentation_module_data())

    # Assert
    documentation = result['skills_by_profile'].get('documentation')
    assert documentation is not None
    assert _skill_names(documentation['defaults']) == CORE_DOC_SKILLS
    assert _skill_names(documentation['optionals']) == DOCUMENTATION_OPTIONAL_SKILLS


def test_documents_not_applicable_without_doc_signals():
    """A module with no documentation signal stays not-applicable (no skill leak)."""
    # Arrange
    ext = _load_extension('pm-documents')
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


def test_documents_respects_active_profiles_filter():
    """An explicit active_profiles filter still gates the implementation alias."""
    # Arrange
    ext = _load_extension('pm-documents')

    # Act
    result = ext.applies_to_module(_documentation_module_data(), active_profiles={'documentation'})

    # Assert
    assert 'implementation' not in result['skills_by_profile']
    assert 'documentation' in result['skills_by_profile']
