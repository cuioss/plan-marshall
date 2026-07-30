#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Axis-C ``DerivationResolverBase`` contract in ``extension_base``.

Covers the four concerns the module-edge derivation extension point rests on:

1. **Safe defaults** — ``derivation_resolver_id()`` returns ``''`` and
   ``derive_edges()`` returns ``([], [])``, so a subclass that overrides nothing
   is a valid no-edge resolver and the ABC declares no abstract method.
2. **Subclass override** — a subclass supplying both methods is accepted and its
   values ride through unchanged.
3. **The disjointness invariant** — ``DerivationResolverBase`` is absent from
   ``ExtensionBase.__mro__`` and from ``BuildExtensionBase.__mro__``, and neither
   of those ABCs appears in ``DerivationResolverBase.__mro__``. This is the
   structural property the whole mechanism choice rests on: because Axis-A and
   Axis-B are disjoint hierarchies, a resolver face on either one would be
   unreachable from the other, so Axis-C must be a sibling ABC opted into by
   multiple inheritance.
4. **Multiple-inheritance opt-in** — a class inheriting ``BuildExtensionBase``
   *and* ``DerivationResolverBase`` satisfies ``isinstance`` for both, which is
   the shape ``build-maven`` uses to provide the Maven coordinate join.

The discovery collector and the edge merge are covered separately in
test_derivation_resolver_discovery.py and test_derivation_merge.py — this module
covers only the ABC's own method contract and the hierarchy invariant.
"""

from extension_base import (
    BuildExtensionBase,
    DerivationResolverBase,
    ExtensionBase,
)

_EMPTY_MAP: dict = {}


class _DefaultResolver(DerivationResolverBase):
    """DerivationResolverBase subclass that overrides nothing — a no-edge resolver."""


class _OverridingResolver(DerivationResolverBase):
    """DerivationResolverBase subclass that supplies both Axis-C methods."""

    def derivation_resolver_id(self) -> str:
        return 'fixture'

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        return [('core', 'util')], ['suppressed edge for ambiguous key g:a']


class _BuildAndResolver(BuildExtensionBase, DerivationResolverBase):
    """The multiple-inheritance opt-in shape a build skill uses (cf. build-maven)."""

    def derivation_resolver_id(self) -> str:
        return 'fixture-build'


# --- 1. Safe defaults -------------------------------------------------------


def test_derivation_resolver_id_defaults_to_empty_string():
    # Arrange
    resolver = _DefaultResolver()

    # Act
    resolver_id = resolver.derivation_resolver_id()

    # Assert
    assert resolver_id == ''


def test_derive_edges_defaults_to_empty_edges_and_notes():
    # Arrange
    resolver = _DefaultResolver()

    # Act
    edges, notes = resolver.derive_edges(_EMPTY_MAP, _EMPTY_MAP)

    # Assert
    assert edges == []
    assert notes == []


def test_derivation_resolver_base_declares_no_abstract_method():
    # Arrange / Act
    abstract_methods = DerivationResolverBase.__abstractmethods__

    # Assert — every Axis-C method carries a default, matching BuildExtensionBase
    assert abstract_methods == frozenset()


def test_derivation_resolver_base_is_directly_instantiable():
    # Arrange / Act — no abstract method means the ABC itself instantiates
    resolver = DerivationResolverBase()

    # Assert
    assert resolver.derivation_resolver_id() == ''
    assert resolver.derive_edges(_EMPTY_MAP, _EMPTY_MAP) == ([], [])


# --- 2. Subclass override ---------------------------------------------------


def test_subclass_overriding_both_methods_is_accepted():
    # Arrange
    resolver = _OverridingResolver()

    # Act
    resolver_id = resolver.derivation_resolver_id()
    edges, notes = resolver.derive_edges(_EMPTY_MAP, _EMPTY_MAP)

    # Assert
    assert resolver_id == 'fixture'
    assert edges == [('core', 'util')]
    assert notes == ['suppressed edge for ambiguous key g:a']


def test_derive_edges_receives_both_module_maps():
    # Arrange
    seen: list[tuple[dict, dict]] = []

    class _RecordingResolver(DerivationResolverBase):
        def derive_edges(
            self,
            derived_by_name: dict,
            enriched_by_name: dict,
        ) -> tuple[list[tuple[str, str]], list[str]]:
            seen.append((derived_by_name, enriched_by_name))
            return [], []

    derived = {'core': {'metadata': {}}}
    enriched = {'core': {'purpose': 'test'}}

    # Act
    _RecordingResolver().derive_edges(derived, enriched)

    # Assert — both pre-loaded maps reach the resolver; it re-derives nothing
    assert seen == [(derived, enriched)]


# --- 3. The disjointness invariant -----------------------------------------


def test_derivation_resolver_base_absent_from_extension_base_mro():
    # Assert — Axis-C is NOT a face on Axis-A
    assert DerivationResolverBase not in ExtensionBase.__mro__


def test_derivation_resolver_base_absent_from_build_extension_base_mro():
    # Assert — Axis-C is NOT a face on Axis-B
    assert DerivationResolverBase not in BuildExtensionBase.__mro__


def test_derivation_resolver_base_inherits_neither_existing_abc():
    # Arrange / Act
    mro = DerivationResolverBase.__mro__

    # Assert — inherited by neither, and inherits from neither
    assert ExtensionBase not in mro
    assert BuildExtensionBase not in mro


def test_axis_a_and_axis_b_hierarchies_are_themselves_disjoint():
    # Assert — the premise the mechanism choice rests on: a face on either ABC
    # would be structurally unreachable from the other
    assert BuildExtensionBase not in ExtensionBase.__mro__
    assert ExtensionBase not in BuildExtensionBase.__mro__


# --- 4. Multiple-inheritance opt-in ---------------------------------------


def test_multiple_inheritance_satisfies_isinstance_for_both_abcs():
    # Arrange
    extension = _BuildAndResolver()

    # Act / Assert
    assert isinstance(extension, BuildExtensionBase)
    assert isinstance(extension, DerivationResolverBase)


def test_multiple_inheritance_preserves_both_contracts():
    # Arrange
    extension = _BuildAndResolver()

    # Act
    resolver_id = extension.derivation_resolver_id()
    edges, notes = extension.derive_edges(_EMPTY_MAP, _EMPTY_MAP)
    globs = extension.classify_globs()

    # Assert — the Axis-C override applies and the inherited Axis-B default survives
    assert resolver_id == 'fixture-build'
    assert (edges, notes) == ([], [])
    assert globs == []


def test_multiple_inheritance_from_axis_a_side_is_also_valid():
    # Arrange — a language/content domain bundle may opt in from the Axis-A side
    class _DomainAndResolver(ExtensionBase, DerivationResolverBase):
        def get_skill_domains(self) -> list[dict]:
            return [{
                'domain': {'key': 'fixture', 'name': 'Fixture', 'description': 'Test only'},
                'profiles': {
                    'core': {'defaults': [], 'optionals': []},
                    'implementation': {'defaults': [], 'optionals': []},
                    'module_testing': {'defaults': [], 'optionals': []},
                    'quality': {'defaults': [], 'optionals': []},
                },
            }]

        def derivation_resolver_id(self) -> str:
            return 'fixture-domain'

    extension = _DomainAndResolver()

    # Act / Assert
    assert isinstance(extension, ExtensionBase)
    assert isinstance(extension, DerivationResolverBase)
    assert extension.derivation_resolver_id() == 'fixture-domain'
