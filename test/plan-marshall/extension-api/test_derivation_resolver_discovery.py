#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``extension_discovery.discover_derivation_resolvers()`` (Axis-C).

Loaded in-process via ``load_script_module`` (real filename → coverage counts).

The collector under test spans BOTH existing discovery paths —
``discover_all_extensions()`` (Axis-A) and ``discover_build_extensions()``
(Axis-B) — because a resolver opts in by multiple inheritance from either
hierarchy. Both collectors are monkeypatched to in-process stubs so the tests are
deterministic and carry no dependency on the live marketplace tree.

Covered:

- Zero registered resolvers returns an empty list (the null-on-absent outcome).
- A resolver from the BUILD hierarchy and one from the DOMAIN hierarchy are
  BOTH discovered — the property that makes spanning both paths load-bearing.
- Results are sorted by resolver id for deterministic downstream ordering.
- A resolver whose id accessor raises is skipped rather than crashing discovery.
- A resolver reporting an empty id is skipped (a producer-less edge is never
  emitted).
"""

from extension_base import (
    BuildExtensionBase,
    DerivationResolverBase,
    ExtensionBase,
)

from conftest import load_script_module

_disc = load_script_module(
    'plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_derivation'
)


# =============================================================================
# Stub resolvers — one per opt-in hierarchy
# =============================================================================


class _BuildSideResolver(BuildExtensionBase, DerivationResolverBase):
    """Axis-B opt-in: the shape build-maven uses."""

    def __init__(self, resolver_id: str = 'maven'):
        self._id = resolver_id

    def derivation_resolver_id(self) -> str:
        return self._id


class _DomainSideResolver(ExtensionBase, DerivationResolverBase):
    """Axis-A opt-in: the shape a future markdown/python resolver would use."""

    def __init__(self, resolver_id: str = 'markdown'):
        self._id = resolver_id

    def get_skill_domains(self) -> list[dict]:
        return []

    def derivation_resolver_id(self) -> str:
        return self._id


class _RaisingResolver(BuildExtensionBase, DerivationResolverBase):
    """A resolver whose id accessor raises — must be skipped, not fatal."""

    def derivation_resolver_id(self) -> str:
        raise RuntimeError('boom-resolver-id')


class _EmptyIdResolver(BuildExtensionBase, DerivationResolverBase):
    """A resolver that cannot identify itself — skipped to preserve provenance."""

    def derivation_resolver_id(self) -> str:
        return ''


class _PlainBuildExtension(BuildExtensionBase):
    """A build extension that does NOT opt into Axis-C — must be filtered out."""


class _PlainDomainExtension(ExtensionBase):
    """A domain extension that does NOT opt into Axis-C — must be filtered out."""

    def get_skill_domains(self) -> list[dict]:
        return []


def _patch_collectors(monkeypatch, *, domain_modules=(), build_modules=()):
    """Point both discovery collectors at in-process stub module lists."""
    monkeypatch.setattr(
        _disc,
        'discover_all_extensions',
        lambda: [{'bundle': f'bundle-{i}', 'path': '', 'module': m} for i, m in enumerate(domain_modules)],
    )
    monkeypatch.setattr(
        _disc,
        'discover_build_extensions',
        lambda: [{'skill': f'build-{i}', 'path': '', 'module': m} for i, m in enumerate(build_modules)],
    )


# =============================================================================
# Null-on-absent
# =============================================================================


def test_zero_registered_resolvers_returns_empty_list(monkeypatch):
    # Arrange
    _patch_collectors(monkeypatch)

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert — absence of capability, not an error
    assert resolvers == []


def test_non_resolver_extensions_are_filtered_out(monkeypatch):
    # Arrange — registered extensions that do not subclass DerivationResolverBase
    _patch_collectors(
        monkeypatch,
        domain_modules=(_PlainDomainExtension(),),
        build_modules=(_PlainBuildExtension(),),
    )

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert
    assert resolvers == []


# =============================================================================
# Both hierarchies are spanned
# =============================================================================


def test_resolvers_from_both_hierarchies_are_discovered(monkeypatch):
    # Arrange — one Axis-A opt-in, one Axis-B opt-in
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideResolver('markdown'),),
        build_modules=(_BuildSideResolver('maven'),),
    )

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert — scanning only one path would hide one of these
    assert [rec['id'] for rec in resolvers] == ['markdown', 'maven']


def test_record_carries_origin_and_module(monkeypatch):
    # Arrange
    resolver = _BuildSideResolver('maven')
    _patch_collectors(monkeypatch, build_modules=(resolver,))

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert
    assert len(resolvers) == 1
    assert resolvers[0] == {'origin': 'build-0', 'id': 'maven', 'module': resolver}


def test_build_hierarchy_resolver_is_discovered_alone(monkeypatch):
    # Arrange — no Axis-A resolvers at all
    _patch_collectors(monkeypatch, build_modules=(_BuildSideResolver('maven'),))

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert
    assert [rec['id'] for rec in resolvers] == ['maven']


def test_domain_hierarchy_resolver_is_discovered_alone(monkeypatch):
    # Arrange — no Axis-B resolvers at all
    _patch_collectors(monkeypatch, domain_modules=(_DomainSideResolver('markdown'),))

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert
    assert [rec['id'] for rec in resolvers] == ['markdown']


# =============================================================================
# Deterministic ordering
# =============================================================================


def test_results_are_sorted_by_resolver_id(monkeypatch):
    # Arrange — supplied deliberately out of alphabetical order, across both paths
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideResolver('zeta'), _DomainSideResolver('alpha')),
        build_modules=(_BuildSideResolver('mu'),),
    )

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert
    assert [rec['id'] for rec in resolvers] == ['alpha', 'mu', 'zeta']


# =============================================================================
# Guarded-call skip paths
# =============================================================================


def test_resolver_whose_id_accessor_raises_is_skipped(monkeypatch):
    # Arrange — a raising resolver alongside a healthy sibling
    _patch_collectors(
        monkeypatch,
        build_modules=(_RaisingResolver(), _BuildSideResolver('maven')),
    )

    # Act — discovery must not crash
    resolvers = _disc.discover_derivation_resolvers()

    # Assert — the broken resolver is dropped, the sibling survives
    assert [rec['id'] for rec in resolvers] == ['maven']


def test_resolver_with_empty_id_is_skipped(monkeypatch):
    # Arrange
    _patch_collectors(
        monkeypatch,
        build_modules=(_EmptyIdResolver(), _BuildSideResolver('maven')),
    )

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert — an unidentifiable resolver would produce producer-less edges
    assert [rec['id'] for rec in resolvers] == ['maven']


def test_all_resolvers_unidentifiable_yields_empty_list(monkeypatch):
    # Arrange
    _patch_collectors(monkeypatch, build_modules=(_EmptyIdResolver(), _RaisingResolver()))

    # Act
    resolvers = _disc.discover_derivation_resolvers()

    # Assert
    assert resolvers == []
