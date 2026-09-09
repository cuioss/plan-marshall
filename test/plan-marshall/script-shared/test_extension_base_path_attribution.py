#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Axis-D ``PathAttributionBase`` contract in ``extension_base``.

Covers the four concerns the path-attribution extension point rests on:

1. **Safe defaults** — ``path_attributor_id()`` returns ``''`` and
   ``claim_paths()`` returns ``([], [])``, so a subclass that overrides nothing
   is a valid no-claim attributor and the ABC declares no abstract method.
2. **Subclass override** — a subclass supplying both methods is accepted and its
   values ride through unchanged.
3. **The disjointness invariant** — ``PathAttributionBase`` is absent from
   ``ExtensionBase.__mro__``, ``BuildExtensionBase.__mro__`` AND
   ``DerivationResolverBase.__mro__``, and none of those three ABCs appears in
   ``PathAttributionBase.__mro__``. This is the structural property the mechanism
   choice rests on: the legitimate implementor population straddles Axis-A and
   Axis-B, so a face on either one would be unreachable from the other, and
   Axis-D must be a sibling ABC opted into by multiple inheritance. The Axis-C
   half of the assertion matters independently — path attribution answers a
   different question from edge derivation and must not become a face on it.
4. **Multiple-inheritance opt-in** — a class inheriting ``ExtensionBase`` *or*
   ``BuildExtensionBase`` together with ``PathAttributionBase`` satisfies
   ``isinstance`` for both, which is the shape ``plan-marshall-plugin`` uses to
   claim ``.claude/skills`` and ``.plan``.

The discovery collector and the claim merge are covered separately in
test_path_attribution_discovery.py and test_path_attribution_merge.py — this
module covers only the ABC's own method contract and the hierarchy invariant.
"""

import pytest
from extension_base import (
    BuildExtensionBase,
    DerivationResolverBase,
    ExtensionBase,
    PathAttributionBase,
)


class _DefaultAttributor(PathAttributionBase):
    """PathAttributionBase subclass that overrides nothing — a no-claim attributor."""


class _OverridingAttributor(PathAttributionBase):
    """PathAttributionBase subclass that supplies both Axis-D methods."""

    def path_attributor_id(self) -> str:
        return 'fixture'

    def claim_paths(self) -> tuple[list[tuple[str, str]], list[str]]:
        return [('.plan', 'plan-marshall')], ['suppressed claim on contested prefix doc/']


class _BuildAndAttributor(BuildExtensionBase, PathAttributionBase):
    """The multiple-inheritance opt-in shape a build skill would use."""

    def path_attributor_id(self) -> str:
        return 'fixture-build'


# --- 1. Safe defaults -------------------------------------------------------


def test_path_attributor_id_defaults_to_empty_string():
    # Arrange
    attributor = _DefaultAttributor()

    # Act
    attributor_id = attributor.path_attributor_id()

    # Assert
    assert attributor_id == ''


def test_claim_paths_defaults_to_empty_claims_and_notes():
    # Arrange
    attributor = _DefaultAttributor()

    # Act
    claims, notes = attributor.claim_paths()

    # Assert
    assert claims == []
    assert notes == []


def test_path_attribution_base_declares_no_abstract_method():
    # Arrange / Act
    abstract_methods = PathAttributionBase.__abstractmethods__

    # Assert — every Axis-D method carries a default, matching its sibling anchors
    assert abstract_methods == frozenset()


def test_path_attribution_base_is_directly_instantiable():
    # Arrange / Act — no abstract method means the ABC itself instantiates
    attributor = PathAttributionBase()

    # Assert
    assert attributor.path_attributor_id() == ''
    assert attributor.claim_paths() == ([], [])


# --- 2. Subclass override ---------------------------------------------------


def test_subclass_overriding_both_methods_is_accepted():
    # Arrange
    attributor = _OverridingAttributor()

    # Act
    attributor_id = attributor.path_attributor_id()
    claims, notes = attributor.claim_paths()

    # Assert
    assert attributor_id == 'fixture'
    assert claims == [('.plan', 'plan-marshall')]
    assert notes == ['suppressed claim on contested prefix doc/']


def test_claim_paths_takes_no_arguments_so_the_attributor_stays_pure():
    # Arrange — a claim is declared from static knowledge, never derived from a
    # tree scan, so the hook is handed nothing to scan.
    attributor = _OverridingAttributor()

    # Act
    claims, _ = attributor.claim_paths()

    # Assert
    assert claims == [('.plan', 'plan-marshall')]


# --- 3. The disjointness invariant -----------------------------------------


#: ``(candidate, the hierarchy it must NOT appear in)`` — Axis-D against each of
#: the three existing ABCs, in both directions. The Axis-C rows matter
#: independently of the Axis-A/B ones: "which module owns this path" is a
#: different question from "which modules depend on which", and bolting one onto
#: the other would give a single ABC two unrelated contracts.
_DISJOINT_HIERARCHY_PAIRS = [
    (PathAttributionBase, ExtensionBase),
    (PathAttributionBase, BuildExtensionBase),
    (PathAttributionBase, DerivationResolverBase),
    (ExtensionBase, PathAttributionBase),
    (BuildExtensionBase, PathAttributionBase),
    (DerivationResolverBase, PathAttributionBase),
]

_DISJOINT_HIERARCHY_IDS = [
    'axis-d-is-not-a-face-on-axis-a',
    'axis-d-is-not-a-face-on-axis-b',
    'axis-d-is-not-a-face-on-axis-c',
    'axis-d-does-not-inherit-axis-a',
    'axis-d-does-not-inherit-axis-b',
    'axis-d-does-not-inherit-axis-c',
]


@pytest.mark.parametrize('candidate,hierarchy', _DISJOINT_HIERARCHY_PAIRS, ids=_DISJOINT_HIERARCHY_IDS)
def test_axis_d_is_disjoint_from_every_other_abc(candidate, hierarchy):
    assert candidate not in hierarchy.__mro__


# --- 4. Multiple-inheritance opt-in ---------------------------------------


def test_multiple_inheritance_satisfies_isinstance_for_both_abcs():
    # Arrange
    extension = _BuildAndAttributor()

    # Act / Assert
    assert isinstance(extension, BuildExtensionBase)
    assert isinstance(extension, PathAttributionBase)


def test_multiple_inheritance_preserves_both_contracts():
    # Arrange
    extension = _BuildAndAttributor()

    # Act
    attributor_id = extension.path_attributor_id()
    claims, notes = extension.claim_paths()
    globs = extension.classify_globs()

    # Assert — the Axis-D override applies and the inherited Axis-B default survives
    assert attributor_id == 'fixture-build'
    assert (claims, notes) == ([], [])
    assert globs == []


def test_multiple_inheritance_from_axis_a_side_is_also_valid():
    # Arrange — the shape plan-marshall-plugin uses for its two shipped claims
    class _DomainAndAttributor(ExtensionBase, PathAttributionBase):
        def get_skill_domains(self) -> list[dict]:
            return [
                {
                    'domain': {'key': 'fixture', 'name': 'Fixture', 'description': 'Test only'},
                    'profiles': {
                        'core': {'defaults': [], 'optionals': []},
                        'implementation': {'defaults': [], 'optionals': []},
                        'module_testing': {'defaults': [], 'optionals': []},
                        'quality': {'defaults': [], 'optionals': []},
                    },
                }
            ]

        def path_attributor_id(self) -> str:
            return 'fixture-domain'

    extension = _DomainAndAttributor()

    # Act / Assert
    assert isinstance(extension, ExtensionBase)
    assert isinstance(extension, PathAttributionBase)
    assert extension.path_attributor_id() == 'fixture-domain'


def test_axis_c_and_axis_d_coexist_on_one_implementor():
    # Arrange — nothing stops a single extension from opting into both sibling
    # axes; the two contracts are independent, not alternatives.
    class _ResolverAndAttributor(BuildExtensionBase, DerivationResolverBase, PathAttributionBase):
        def derivation_resolver_id(self) -> str:
            return 'fixture-edges'

        def path_attributor_id(self) -> str:
            return 'fixture-paths'

    extension = _ResolverAndAttributor()

    # Act / Assert
    assert isinstance(extension, DerivationResolverBase)
    assert isinstance(extension, PathAttributionBase)
    assert extension.derivation_resolver_id() == 'fixture-edges'
    assert extension.path_attributor_id() == 'fixture-paths'
