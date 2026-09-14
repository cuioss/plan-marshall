#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the Axis-C ``DerivationResolverBase`` contract in ``extension_base``.

Covers the five concerns the module-edge derivation extension point rests on:

1. **Safe defaults** — ``derivation_resolver_id()`` returns ``''``,
   ``derive_edges()`` returns ``([], [])``, and ``derivation_file_patterns()``
   returns ``[]``, so a subclass that overrides nothing is a valid no-edge
   resolver and the ABC declares no abstract method. The pattern default is
   load-bearing rather than incidental: it is what lets a third-party resolver
   stay valid without declaring a file domain, and the menu reports it as *not
   declared* rather than as "derives from no files".
2. **Subclass override** — a subclass supplying all three methods is accepted
   and its values ride through unchanged.
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
5. **The aggregated-note populations** — ``_aggregate_notes`` reports the summed
   ``occurrences`` (source REFERENCES) while sampling over distinct CANDIDATES,
   so neither number is published under the other's name.

The discovery collector and the edge merge are covered separately in
test_derivation_resolver_discovery.py and test_derivation_merge.py — this module
covers only the ABC's own method contract and the hierarchy invariant.
"""

import pytest
from extension_base import (
    NOTE_SAMPLE_LIMIT,
    BuildExtensionBase,
    DerivationResolverBase,
    ExtensionBase,
)

_EMPTY_MAP: dict = {}


class _DefaultResolver(DerivationResolverBase):
    """DerivationResolverBase subclass that overrides nothing — a no-edge resolver."""


class _OverridingResolver(DerivationResolverBase):
    """DerivationResolverBase subclass that supplies all three Axis-C methods."""

    def derivation_resolver_id(self) -> str:
        return 'fixture'

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        return [('core', 'util')], ['suppressed edge for ambiguous key g:a']

    def derivation_file_patterns(self) -> list[str]:
        return ['**/*.fixture']


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
    assert resolver.derivation_file_patterns() == []


# --- 2. Subclass override ---------------------------------------------------


def test_subclass_overriding_every_method_is_accepted():
    # Arrange
    resolver = _OverridingResolver()

    # Act
    resolver_id = resolver.derivation_resolver_id()
    edges, notes = resolver.derive_edges(_EMPTY_MAP, _EMPTY_MAP)

    # Assert
    assert resolver_id == 'fixture'
    assert edges == [('core', 'util')]
    assert notes == ['suppressed edge for ambiguous key g:a']
    assert resolver.derivation_file_patterns() == ['**/*.fixture']


def test_declared_file_patterns_default_to_empty():
    """The ABC default asserts nothing about a resolver's file domain.

    ``[]`` is *not declared*, never "derives from no files" — the null-on-absent
    contract every face of this API shares. Pinned at the ABC because it is the
    documented default a third-party resolver relies on, and no other test
    exercises the ABC's own implementation.
    """
    assert _DefaultResolver().derivation_file_patterns() == []


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


#: ``(candidate, the hierarchy it must NOT appear in)`` — the full pairwise
#: matrix over the three ABCs. The premise the mechanism choice rests on is that
#: NO pair is related in either direction: a face declared on any one of them
#: would be structurally unreachable from the other two, which is why Axis-C is a
#: sibling ABC opted into by multiple inheritance rather than a method on either
#: existing base.
_DISJOINT_HIERARCHY_PAIRS = [
    (DerivationResolverBase, ExtensionBase),
    (DerivationResolverBase, BuildExtensionBase),
    (ExtensionBase, DerivationResolverBase),
    (BuildExtensionBase, DerivationResolverBase),
    (BuildExtensionBase, ExtensionBase),
    (ExtensionBase, BuildExtensionBase),
]

_DISJOINT_HIERARCHY_IDS = [
    'axis-c-is-not-a-face-on-axis-a',
    'axis-c-is-not-a-face-on-axis-b',
    'axis-c-does-not-inherit-axis-a',
    'axis-c-does-not-inherit-axis-b',
    'axis-b-is-not-a-face-on-axis-a',
    'axis-a-is-not-a-face-on-axis-b',
]


@pytest.mark.parametrize('candidate,hierarchy', _DISJOINT_HIERARCHY_PAIRS, ids=_DISJOINT_HIERARCHY_IDS)
def test_the_three_abc_hierarchies_are_pairwise_disjoint(candidate, hierarchy):
    assert candidate not in hierarchy.__mro__


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

        def derivation_resolver_id(self) -> str:
            return 'fixture-domain'

    extension = _DomainAndResolver()

    # Act / Assert
    assert isinstance(extension, ExtensionBase)
    assert isinstance(extension, DerivationResolverBase)
    assert extension.derivation_resolver_id() == 'fixture-domain'


# --- 5. The aggregated-note populations -------------------------------------
#
# A ``component_refs`` element is deduplicated on its
# ``(target_bundle, dep_type, resolved)`` triple, so ONE candidate can stand for
# many source references. The note reports the summed ``occurrences`` under the
# name "reference(s)"; the sample and its ``(+N more)`` suffix stay over the
# distinct candidates a sample is actually drawn from. Counting candidates and
# labelling the result "reference(s)" is the defect this split closes.

_AGGREGATE = DerivationResolverBase._aggregate_notes


def _reference_total(note: str) -> int:
    """Read the ``N`` out of ``'{category}: N reference(s) suppressed - ...'``."""
    return int(note.split(': ', 1)[1].split(' reference(s)', 1)[0])


def test_note_reports_summed_occurrences_not_the_candidate_count():
    """Several references collapsing onto ONE triple report the reference total.

    The population the schema documents is *source references*, and the whole
    point of ``occurrences`` is that the element count no longer measures it.
    """
    # Arrange — one deduplicated candidate standing for five source references
    suppressed = {'unresolved-target': [('documentation -> plan-marshall [path]', 5)]}

    # Act
    notes = _AGGREGATE(suppressed)

    # Assert — five references, reported from a single candidate
    assert _reference_total(notes[0]) == 5
    assert notes[0].endswith('sample: documentation -> plan-marshall [path]')


def test_bare_descriptions_each_count_as_one_reference():
    """The negative control: a materializer that omits ``occurrences``.

    The documented default is ``1``, so an omitting materializer renders exactly
    as it did before the field existed — the reference total equals the candidate
    count, which is the ONLY case in which the two populations coincide.
    """
    # Arrange — five bare candidates, no multiplicity carried
    suppressed = {'unresolved-target': [f'a -> b{i} [path]' for i in range(5)]}

    # Act
    notes = _AGGREGATE(suppressed)

    # Assert — same total as the pair form above, reached the other way
    assert _reference_total(notes[0]) == 5


def test_sample_and_overflow_stay_over_distinct_candidates():
    """``(+N more)`` counts CANDIDATES beyond the sample cap, never references.

    The suffix qualifies the sample, and a sample is drawn from candidates — so a
    single high-multiplicity candidate must not inflate it.
    """
    # Arrange — one candidate carrying 99 references, well over the sample cap
    suppressed = {'self-edge': [('a -> a [path]', 99)]}

    # Act
    notes = _AGGREGATE(suppressed)

    # Assert — 99 references, but one candidate, so nothing overflows the sample
    assert _reference_total(notes[0]) == 99
    assert 'more)' not in notes[0]


def test_overflow_counts_candidates_beyond_the_sample_cap():
    # Arrange — one more candidate than the cap admits, each a single reference
    candidates = [f'a -> b{i} [path]' for i in range(NOTE_SAMPLE_LIMIT + 2)]

    # Act
    notes = _AGGREGATE({'self-edge': candidates})

    # Assert — the two beyond the cap are counted, not hidden
    assert notes[0].endswith('(+2 more)')


def test_mixed_bare_and_pair_entries_sum_together():
    # Arrange — a materializer that populates the field for only some elements
    suppressed = {'unknown-endpoint': ['a -> b [path]', ('a -> c [path]', 4)]}

    # Act
    notes = _AGGREGATE(suppressed)

    # Assert — 1 (defaulted) + 4 (carried)
    assert _reference_total(notes[0]) == 5


@pytest.mark.parametrize('occurrences', [0, -3, None, 'many', 1.5], ids=['zero', 'negative', 'none', 'text', 'float'])
def test_unusable_occurrences_floors_to_one(occurrences):
    """A suppressed candidate always stands for at least the reference that produced it.

    Contributing ``0`` would under-report a suppression the Axis-C contract
    requires be visible, so the floor is fail-closed rather than permissive.
    """
    # Arrange / Act
    notes = _AGGREGATE({'self-edge': [('a -> a [path]', occurrences)]})

    # Assert
    assert _reference_total(notes[0]) == 1


def test_empty_category_emits_no_note():
    # Arrange — seeding every recognised category is how a caller fixes note order
    suppressed: dict = {'unresolved-target': [], 'self-edge': [('a -> a [path]', 2)]}

    # Act
    notes = _AGGREGATE(suppressed)

    # Assert — only the non-empty category renders
    assert len(notes) == 1
    assert notes[0].startswith('self-edge: 2 reference(s)')
