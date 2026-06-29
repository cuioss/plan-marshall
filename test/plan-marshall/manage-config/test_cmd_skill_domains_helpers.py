#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the pure helper functions in ``_cmd_skill_domains.py``.

The existing ``test_cmd_skill_domains.py`` suite drives the ``cmd_skill_domains``
verb dispatcher and the verify-step discovery, but the skill-entry extraction
helpers (``_extract_skill_name`` / ``_extract_skill_description`` /
``_extract_skill_names`` / ``_build_skill_dict_with_descriptions``) and the
bundle-config conversion/loading helpers
(``convert_extension_to_domain_config`` / ``load_profiles_from_bundle`` /
``load_domain_config_from_bundle``) have no direct coverage. These tests
exercise their real input -> output contracts (string vs dict entries, embedded
vs fetched descriptions, present vs absent extension functions, unknown
bundle/domain fallbacks).
"""

from conftest import load_script_module

# Loaded under a unique module name to avoid clashing with the canonical
# ``_cmd_skill_domains`` module other test files register.
_sd = load_script_module('plan-marshall', 'manage-config', '_cmd_skill_domains.py', 'cmd_skill_domains_helpers_under_test')


# =============================================================================
# _extract_skill_name
# =============================================================================


def test_extract_skill_name_from_string_returns_verbatim():
    """A plain-string skill entry is returned unchanged."""
    assert _sd._extract_skill_name('pm-dev-java:java-core') == 'pm-dev-java:java-core'


def test_extract_skill_name_from_dict_returns_skill_field():
    """A dict entry yields its ``skill`` field."""
    assert _sd._extract_skill_name({'skill': 'pm-dev-java:javadoc', 'description': 'd'}) == 'pm-dev-java:javadoc'


def test_extract_skill_name_from_dict_without_skill_returns_empty():
    """A dict entry lacking a ``skill`` field yields the empty string."""
    assert _sd._extract_skill_name({'description': 'orphan'}) == ''


# =============================================================================
# _extract_skill_description
# =============================================================================


def test_extract_skill_description_from_dict_returns_description():
    """A dict entry yields its ``description`` field."""
    assert _sd._extract_skill_description({'skill': 's', 'description': 'the desc'}) == 'the desc'


def test_extract_skill_description_from_dict_without_description_returns_empty():
    """A dict entry lacking a ``description`` field yields the empty string."""
    assert _sd._extract_skill_description({'skill': 's'}) == ''


def test_extract_skill_description_from_string_returns_empty():
    """A plain-string entry carries no description."""
    assert _sd._extract_skill_description('pm-dev-java:java-core') == ''


# =============================================================================
# _extract_skill_names
# =============================================================================


def test_extract_skill_names_mixed_entries():
    """A mixed list of string and dict entries yields the list of skill names in order."""
    entries = ['a:one', {'skill': 'b:two', 'description': 'd'}, {'description': 'orphan'}]

    assert _sd._extract_skill_names(entries) == ['a:one', 'b:two', '']


# =============================================================================
# _build_skill_dict_with_descriptions
# =============================================================================


def test_build_skill_dict_uses_embedded_descriptions():
    """Entries with embedded descriptions are mapped name -> description without SKILL.md lookup."""
    entries = [
        {'skill': 'pm-dev-java:java-core', 'description': 'core patterns'},
        {'skill': 'pm-dev-java:javadoc', 'description': 'javadoc rules'},
    ]

    result = _sd._build_skill_dict_with_descriptions(entries)

    assert result == {
        'pm-dev-java:java-core': 'core patterns',
        'pm-dev-java:javadoc': 'javadoc rules',
    }


def test_build_skill_dict_skips_entries_without_skill_name():
    """Entries with no resolvable skill name are dropped from the mapping."""
    entries = [{'skill': 'x:y', 'description': 'kept'}, {'description': 'no skill key'}]

    result = _sd._build_skill_dict_with_descriptions(entries)

    assert result == {'x:y': 'kept'}


def test_build_skill_dict_falls_back_to_notation_for_unknown_string_entry():
    """A bare-string entry with no resolvable SKILL.md falls back to the notation as its description."""
    result = _sd._build_skill_dict_with_descriptions(['zzz:not-a-real-skill'])

    # get_skill_description returns the notation itself when the SKILL.md cannot
    # be resolved, so the entry maps to its own notation.
    assert result == {'zzz:not-a-real-skill': 'zzz:not-a-real-skill'}


# =============================================================================
# convert_extension_to_domain_config
# =============================================================================


class _FakeFullModule:
    """Fake extension module exposing both outline and triage providers."""

    def provides_outline_skill(self):
        return 'pm-dev-java:ext-outline-java'

    def provides_triage(self):
        return 'pm-dev-java:ext-triage-java'


class _FakeEmptyProvidersModule:
    """Fake extension module whose providers return None (registered but empty)."""

    def provides_outline_skill(self):
        return None

    def provides_triage(self):
        return None


class _FakeNoProvidersModule:
    """Fake extension module that declares no provider functions at all."""


def test_convert_extension_to_domain_config_full_providers():
    """Both providers populate outline_skill and the triage workflow extension."""
    config = _sd.convert_extension_to_domain_config(_FakeFullModule(), {}, 'pm-dev-java')

    assert config['bundle'] == 'pm-dev-java'
    assert config['outline_skill'] == 'pm-dev-java:ext-outline-java'
    assert config['workflow_skill_extensions'] == {'triage': 'pm-dev-java:ext-triage-java'}


def test_convert_extension_to_domain_config_empty_providers_emits_bundle_only():
    """Providers returning None contribute neither outline_skill nor extensions."""
    config = _sd.convert_extension_to_domain_config(_FakeEmptyProvidersModule(), {}, 'pm-dev-java')

    assert config == {'bundle': 'pm-dev-java'}


def test_convert_extension_to_domain_config_no_provider_functions():
    """A module with no provider functions yields just the bundle reference."""
    config = _sd.convert_extension_to_domain_config(_FakeNoProvidersModule(), {}, 'some-bundle')

    assert config == {'bundle': 'some-bundle'}


# =============================================================================
# load_profiles_from_bundle / load_domain_config_from_bundle
# =============================================================================


def test_load_profiles_from_bundle_matches_real_bundle():
    """A real bundle/domain pair returns its profiles block including the core profile."""
    result = _sd.load_profiles_from_bundle('pm-dev-java', 'java')

    assert 'profiles' in result
    assert 'core' in result['profiles']


def test_load_profiles_from_bundle_unknown_bundle_returns_empty():
    """An unknown bundle name resolves to an empty profiles block."""
    result = _sd.load_profiles_from_bundle('no-such-bundle-xyz', 'java')

    assert result == {'profiles': {}}


def test_load_domain_config_from_bundle_unknown_domain_returns_none():
    """An unknown domain key resolves to None (no extension claims it)."""
    assert _sd.load_domain_config_from_bundle('no-such-domain-xyz') is None
