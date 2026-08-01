#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``extension_discovery.discover_path_attributors()`` (Axis-D).

Loaded in-process via ``load_script_module`` (real filename → coverage counts).

The collector under test spans BOTH existing discovery paths —
``discover_all_extensions()`` (Axis-A) and ``discover_build_extensions()``
(Axis-B) — because an attributor opts in by multiple inheritance from either
hierarchy. Both collectors are monkeypatched to in-process stubs so the tests are
deterministic and carry no dependency on the live marketplace tree.

Covered:

- Zero registered attributors returns an empty list (the null-on-absent outcome).
- An attributor from the BUILD hierarchy and one from the DOMAIN hierarchy are
  BOTH discovered — the span-both-paths invariant, and the one a future
  maintainer can silently break by scanning only the collector their own
  implementor happens to live behind.
- Results are sorted by attributor id for deterministic downstream ordering.
- The four skip conditions: an id accessor that raises, a non-string id, an
  empty/whitespace id, and an id already claimed by another attributor.
"""

from extension_base import (
    BuildExtensionBase,
    ExtensionBase,
    PathAttributionBase,
)

from conftest import load_script_module

_disc = load_script_module(
    'plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_path_attribution'
)


# =============================================================================
# Stub attributors — one per opt-in hierarchy
# =============================================================================


class _BuildSideAttributor(BuildExtensionBase, PathAttributionBase):
    """Axis-B opt-in: a build skill claiming its own production tree."""

    def __init__(self, attributor_id: str = 'pyproject'):
        self._id = attributor_id

    def path_attributor_id(self) -> str:
        return self._id


class _DomainSideAttributor(ExtensionBase, PathAttributionBase):
    """Axis-A opt-in: the shape plan-marshall-plugin uses."""

    def __init__(self, attributor_id: str = 'plan-marshall'):
        self._id = attributor_id

    def get_skill_domains(self) -> list[dict]:
        return []

    def path_attributor_id(self) -> str:
        return self._id


class _RaisingAttributor(BuildExtensionBase, PathAttributionBase):
    """An attributor whose id accessor raises — must be skipped, not fatal."""

    def path_attributor_id(self) -> str:
        raise RuntimeError('boom-path-attributor-id')


class _EmptyIdAttributor(BuildExtensionBase, PathAttributionBase):
    """An attributor that cannot identify itself — skipped to preserve provenance."""

    def path_attributor_id(self) -> str:
        return ''


class _NonStringIdAttributor(BuildExtensionBase, PathAttributionBase):
    """An attributor whose id is truthy but not a string — skipped before the sort."""

    def __init__(self, attributor_id=1):
        self._id = attributor_id

    def path_attributor_id(self):
        return self._id


class _PlainBuildExtension(BuildExtensionBase):
    """A build extension that does NOT opt into Axis-D — must be filtered out."""


class _PlainDomainExtension(ExtensionBase):
    """A domain extension that does NOT opt into Axis-D — must be filtered out."""

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


def test_zero_registered_attributors_returns_empty_list(monkeypatch):
    # Arrange
    _patch_collectors(monkeypatch)

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — absence of capability, not an error
    assert attributors == []


def test_non_attributor_extensions_are_filtered_out(monkeypatch):
    # Arrange — registered extensions that do not subclass PathAttributionBase
    _patch_collectors(
        monkeypatch,
        domain_modules=(_PlainDomainExtension(),),
        build_modules=(_PlainBuildExtension(),),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert attributors == []


# =============================================================================
# Both hierarchies are spanned — the span-both-paths invariant
# =============================================================================


def test_attributors_from_both_hierarchies_are_discovered(monkeypatch):
    # Arrange — one Axis-A opt-in, one Axis-B opt-in
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('plan-marshall'),),
        build_modules=(_BuildSideAttributor('pyproject'),),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — scanning only one path would hide one of these
    assert [rec['id'] for rec in attributors] == ['plan-marshall', 'pyproject']


def test_record_carries_origin_and_module(monkeypatch):
    # Arrange
    attributor = _BuildSideAttributor('pyproject')
    _patch_collectors(monkeypatch, build_modules=(attributor,))

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert len(attributors) == 1
    assert attributors[0] == {'origin': 'build-0', 'id': 'pyproject', 'module': attributor}


def test_build_hierarchy_attributor_is_discovered_alone(monkeypatch):
    # Arrange — no Axis-A attributors at all
    _patch_collectors(monkeypatch, build_modules=(_BuildSideAttributor('pyproject'),))

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert [rec['id'] for rec in attributors] == ['pyproject']


def test_domain_hierarchy_attributor_is_discovered_alone(monkeypatch):
    # Arrange — no Axis-B attributors at all
    _patch_collectors(monkeypatch, domain_modules=(_DomainSideAttributor('plan-marshall'),))

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert [rec['id'] for rec in attributors] == ['plan-marshall']


# =============================================================================
# Deterministic ordering
# =============================================================================


def test_results_are_sorted_by_attributor_id(monkeypatch):
    # Arrange — supplied deliberately out of alphabetical order, across both paths
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('zeta'), _DomainSideAttributor('alpha')),
        build_modules=(_BuildSideAttributor('mu'),),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert [rec['id'] for rec in attributors] == ['alpha', 'mu', 'zeta']


# =============================================================================
# Skip condition 1 — the id accessor raises
# =============================================================================


def test_attributor_whose_id_accessor_raises_is_skipped(monkeypatch):
    # Arrange — a raising attributor alongside a healthy sibling
    _patch_collectors(
        monkeypatch,
        build_modules=(_RaisingAttributor(), _BuildSideAttributor('pyproject')),
    )

    # Act — discovery must not crash
    attributors = _disc.discover_path_attributors()

    # Assert — the broken attributor is dropped, the sibling survives
    assert [rec['id'] for rec in attributors] == ['pyproject']


# =============================================================================
# Skip condition 2 — an empty or whitespace-only id
# =============================================================================


def test_attributor_with_empty_id_is_skipped(monkeypatch):
    # Arrange
    _patch_collectors(
        monkeypatch,
        build_modules=(_EmptyIdAttributor(), _BuildSideAttributor('pyproject')),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — an unidentifiable attributor would produce producer-less claims
    assert [rec['id'] for rec in attributors] == ['pyproject']


def test_attributor_with_whitespace_only_id_is_skipped(monkeypatch):
    # Arrange — truthy, but carries no identity
    _patch_collectors(
        monkeypatch,
        build_modules=(_BuildSideAttributor('   '), _BuildSideAttributor('pyproject')),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert [rec['id'] for rec in attributors] == ['pyproject']


def test_attributor_id_is_normalized_by_stripping_surrounding_whitespace(monkeypatch):
    # Arrange
    _patch_collectors(monkeypatch, build_modules=(_BuildSideAttributor('  pyproject  '),))

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — the stored id is the normalized form, not the raw return
    assert [rec['id'] for rec in attributors] == ['pyproject']


def test_all_attributors_unidentifiable_yields_empty_list(monkeypatch):
    # Arrange
    _patch_collectors(monkeypatch, build_modules=(_EmptyIdAttributor(), _RaisingAttributor()))

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert attributors == []


# =============================================================================
# Skip condition 3 — a truthy NON-STRING id would raise on the mixed-type sort
# =============================================================================


def test_attributor_with_non_string_id_is_skipped(monkeypatch):
    # Arrange — the int 1 passes a falsiness check but is not a usable producer id
    _patch_collectors(
        monkeypatch,
        build_modules=(_NonStringIdAttributor(1), _BuildSideAttributor('pyproject')),
    )

    # Act — discovery must neither admit it nor raise while sorting
    attributors = _disc.discover_path_attributors()

    # Assert
    assert [rec['id'] for rec in attributors] == ['pyproject']


def test_non_string_id_does_not_break_the_sort_of_surviving_attributors(monkeypatch):
    # Arrange — a mixed-type id alongside two healthy attributors out of order
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('zeta'),),
        build_modules=(_NonStringIdAttributor(1), _BuildSideAttributor('alpha')),
    )

    # Act — the pre-sort rejection is what keeps this from raising TypeError
    attributors = _disc.discover_path_attributors()

    # Assert
    assert [rec['id'] for rec in attributors] == ['alpha', 'zeta']


# =============================================================================
# Skip condition 4 — a duplicate id would collapse two producer identities
# =============================================================================


def test_duplicate_attributor_id_from_two_origins_is_skipped(monkeypatch):
    # Arrange — an Axis-A and an Axis-B attributor both claiming 'plan-marshall'
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('plan-marshall'),),
        build_modules=(_BuildSideAttributor('plan-marshall'),),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — exactly one survives; the id never maps to two producers
    assert [rec['id'] for rec in attributors] == ['plan-marshall']
    assert len(attributors) == 1


def test_duplicate_attributor_id_keeps_the_first_claimant(monkeypatch):
    # Arrange — the Axis-A path is scanned first, so its claimant wins
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('plan-marshall'),),
        build_modules=(_BuildSideAttributor('plan-marshall'),),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert
    assert attributors[0]['origin'] == 'bundle-0'


def test_duplicate_id_does_not_suppress_a_distinct_sibling(monkeypatch):
    # Arrange — a colliding pair plus one attributor with its own id
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('plan-marshall'),),
        build_modules=(_BuildSideAttributor('plan-marshall'), _BuildSideAttributor('gradle')),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — only the duplicate is dropped
    assert [rec['id'] for rec in attributors] == ['gradle', 'plan-marshall']


def test_id_collision_is_detected_after_whitespace_normalization(monkeypatch):
    # Arrange — the two ids differ only by surrounding whitespace
    _patch_collectors(
        monkeypatch,
        domain_modules=(_DomainSideAttributor('plan-marshall'),),
        build_modules=(_BuildSideAttributor(' plan-marshall '),),
    )

    # Act
    attributors = _disc.discover_path_attributors()

    # Assert — normalization happens before the uniqueness check
    assert len(attributors) == 1
