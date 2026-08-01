#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the markdown derivation resolver (Axis-C) on pm-plugin-development.

The resolver is a **pure join** over the ``component_refs`` field
``discover_plugin_modules`` materializes, so these tests hand it module maps
directly rather than discovering a fixture tree: the input shape IS the contract,
and building it by hand keeps each suppression rule pinned in isolation.

Covered:

- The provenance id is ``markdown`` and both hierarchies' ``isinstance`` hold.
- Only the reference kinds this resolver declares contribute; every other
  ``DependencyType`` kind is ignored and, being out of scope rather than
  suppressed, produces no note. Both swept populations are derived from the
  enum and the resolver's own declaration, never hand-listed.
- Unresolved targets, unknown endpoints, and self-edges are each suppressed AND
  reported, in aggregated form rather than one note per dropped reference.
- ``derive_edges`` reads no file and spawns no subprocess — the Axis-C purity
  contract, asserted by making both operations fatal for the duration of the call.
"""

import builtins
import importlib.util
import subprocess
from pathlib import Path

from _dep_detection import DependencyType
from extension_base import NOTE_SAMPLE_LIMIT, DerivationResolverBase, ExtensionBase

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

EXTENSION_FILE = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plan-marshall-plugin'
    / 'extension.py'
)


def _load_plugin_extension():
    """Load the pm-plugin-development Extension by explicit file path.

    Every domain bundle ships an ``extension.py`` sharing the module basename
    ``extension``; loading via ``spec_from_file_location`` against the explicit
    path avoids the cross-bundle ``import extension`` collision.
    """
    spec = importlib.util.spec_from_file_location('plugin_dev_extension', EXTENSION_FILE)
    assert spec is not None and spec.loader is not None, f'no import spec for {EXTENSION_FILE}'
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_extension_module = _load_plugin_extension()
Extension = _extension_module.Extension

ALL_DEP_TYPES = frozenset(member.value for member in DependencyType)
"""Every dependency kind the authoritative :class:`DependencyType` enum declares."""

MARKDOWN_DEP_TYPES = tuple(sorted(_extension_module.MARKDOWN_DEP_TYPES))
"""The reference kinds this resolver owns, read from the resolver's own declaration."""

NON_MARKDOWN_DEP_TYPES = tuple(sorted(ALL_DEP_TYPES - set(MARKDOWN_DEP_TYPES)))
"""Every remaining enum kind — the sweep that must stay out of scope.

Both populations are derived rather than hand-listed so a sixth
``DependencyType`` lands in one of the two sweeps automatically. A restated
tuple keeps every sweep green while the new kind goes untested and the
markdown-vs-import resolver split goes unverified for it.
"""

NOTE_OVERFLOW = 2
"""How far the overflow fixture below exceeds the note's sample cap.

Both ends of the overflow assertion derive from ``NOTE_SAMPLE_LIMIT``: a fixture
sized to a literal 5 stops exercising the overflow branch at all once the cap
reaches 5, and then fails with an opaque substring mismatch rather than naming
the cause.
"""

OVERFLOW_SAMPLE_SIZE = NOTE_SAMPLE_LIMIT + NOTE_OVERFLOW
"""Fixture size that provably overflows the note's sample cap at any cap value."""


# =============================================================================
# Input builders
# =============================================================================


def _ref(target_bundle: str, dep_type: str, resolved: bool = True) -> dict:
    """Build one materialized component reference."""
    return {'target_bundle': target_bundle, 'dep_type': dep_type, 'resolved': resolved}


def _module(refs: list[dict] | None = None) -> dict:
    """Build one derived-module entry, optionally carrying component_refs."""
    data: dict = {'build_systems': ['marshall-plugin']}
    if refs is not None:
        data['component_refs'] = refs
    return data


def _derive(derived_by_name: dict) -> tuple[list[tuple[str, str]], list[str]]:
    """Run the resolver over a derived map with an empty enriched overlay."""
    return Extension().derive_edges(derived_by_name, {})


def _note_for(notes: list[str], category: str) -> str:
    """Return the single note for ``category``, asserting exactly one exists."""
    matching = [note for note in notes if note.startswith(f'{category}:')]
    assert len(matching) == 1, f'expected exactly one {category} note, got {matching}'
    return matching[0]


# =============================================================================
# Identity and hierarchy opt-in
# =============================================================================


def test_resolver_id_is_markdown():
    """The stable provenance id names this resolver on every edge it produces."""
    assert Extension().derivation_resolver_id() == 'markdown'


def test_extension_opts_into_both_hierarchies():
    """Axis-A and Axis-C are both satisfied by the same Extension instance."""
    extension = Extension()

    assert isinstance(extension, ExtensionBase)
    assert isinstance(extension, DerivationResolverBase)


# =============================================================================
# Dep-type scoping
# =============================================================================


def test_the_dep_type_populations_are_non_vacuous_and_enum_derived():
    """Anchor for every sweep below: neither population may be empty or invented.

    Each sweep iterates one of the two populations, so an empty one would let
    its sweep pass while asserting nothing, and a kind this resolver declares
    that the authoritative enum does not know would be swept as if it were real.
    The union check pins the split itself: every enum kind is either owned by
    this resolver or swept as out of scope — never silently absent from both.
    """
    assert MARKDOWN_DEP_TYPES
    assert NON_MARKDOWN_DEP_TYPES
    assert set(MARKDOWN_DEP_TYPES) <= ALL_DEP_TYPES
    assert set(MARKDOWN_DEP_TYPES) | set(NON_MARKDOWN_DEP_TYPES) == ALL_DEP_TYPES


def test_all_markdown_dep_types_contribute():
    """Every reference kind this resolver owns yields an edge."""
    derived = {
        'alpha': _module([_ref('beta', dep_type) for dep_type in MARKDOWN_DEP_TYPES]),
        'beta': _module([]),
    }

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert notes == []


def test_each_markdown_dep_type_contributes_on_its_own():
    """No single markdown dep_type depends on another being present."""
    for dep_type in MARKDOWN_DEP_TYPES:
        derived = {'alpha': _module([_ref('beta', dep_type)]), 'beta': _module([])}

        edges, notes = _derive(derived)

        assert edges == [('alpha', 'beta')], f'{dep_type} produced no edge'
        assert notes == []


def test_non_markdown_dep_types_are_ignored_without_a_note():
    """Every kind outside this resolver's set belongs to a sibling, so it is out of scope.

    Out of scope is not the same as suppressed: an ignored reference must NOT
    appear in notes[], or every report would claim a suppression that the
    python resolver is in fact handling. The population is derived, so a sixth
    ``DependencyType`` lands in this sweep instead of going untested.
    """
    for dep_type in NON_MARKDOWN_DEP_TYPES:
        derived = {'alpha': _module([_ref('beta', dep_type)]), 'beta': _module([])}

        assert _derive(derived) == ([], []), f'{dep_type} leaked into the markdown resolver'


def test_out_of_scope_entry_does_not_suppress_a_sibling_markdown_edge():
    """An ignored out-of-scope reference leaves the same module's markdown edges intact."""
    derived = {
        'alpha': _module(
            [_ref('beta', NON_MARKDOWN_DEP_TYPES[0]), _ref('beta', MARKDOWN_DEP_TYPES[0])]
        ),
        'beta': _module([]),
    }

    edges, _notes = _derive(derived)

    assert edges == [('alpha', 'beta')]


# =============================================================================
# Suppression: unresolved target
# =============================================================================


def test_unresolved_reference_is_suppressed_and_reported():
    """A reference whose target does not exist yields no edge but a note."""
    derived = {'alpha': _module([_ref('gamma', 'skill', resolved=False)]), 'beta': _module([])}

    edges, notes = _derive(derived)

    assert edges == []
    note = _note_for(notes, 'unresolved-target')
    assert '1 reference(s) suppressed' in note
    assert 'alpha -> gamma [skill]' in note


# =============================================================================
# Suppression: unknown endpoint
# =============================================================================


def test_reference_to_unknown_module_is_suppressed_and_reported():
    """A resolved reference naming no known module yields no edge but a note."""
    derived = {'alpha': _module([_ref('delta', 'script')])}

    edges, notes = _derive(derived)

    assert edges == []
    note = _note_for(notes, 'unknown-endpoint')
    assert '1 reference(s) suppressed' in note
    assert 'alpha -> delta [script]' in note


# =============================================================================
# Suppression: self-edge
# =============================================================================


def test_self_edge_is_excluded_and_reported():
    """A bundle referencing itself is dropped by the resolver, not just the merge.

    Dropping it here is what keeps this resolver's own edge_count honest: the
    core merge also drops self-edges, so a resolver that emitted them would
    report more edges than the graph ever receives.
    """
    derived = {'alpha': _module([_ref('alpha', 'skill')])}

    edges, notes = _derive(derived)

    assert edges == []
    note = _note_for(notes, 'self-edge')
    assert '1 reference(s) suppressed' in note
    assert 'alpha -> alpha [skill]' in note


def test_self_edge_does_not_suppress_a_real_edge_from_the_same_module():
    """A self-reference and a cross-bundle reference are judged independently."""
    derived = {
        'alpha': _module([_ref('alpha', 'skill'), _ref('beta', 'skill')]),
        'beta': _module([]),
    }

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert _note_for(notes, 'self-edge')


# =============================================================================
# Notes are aggregated, never per-reference
# =============================================================================


def test_many_suppressed_references_collapse_into_one_note_per_category():
    """One note per category with the full count — never one note per drop.

    merge_resolver_edges appends one note per dropped candidate, so a
    per-reference note here would make the per-resolver report unreadable.
    """
    unresolved = [_ref(f'ghost-{index}', 'skill', resolved=False) for index in range(5)]
    derived = {'alpha': _module(unresolved)}

    edges, notes = _derive(derived)

    assert edges == []
    assert len(notes) == 1
    note = notes[0]
    assert note.startswith('unresolved-target: 5 reference(s) suppressed')


def test_aggregated_note_bounds_its_sample_and_reports_the_overflow():
    """The sample is capped, and the omitted remainder is counted, not hidden.

    Both the fixture size and the expected remainder derive from
    ``NOTE_SAMPLE_LIMIT``, so the test keeps exercising the overflow branch at
    any cap value instead of quietly ceasing to reach it.
    """
    unresolved = [
        _ref(f'ghost-{index}', 'skill', resolved=False) for index in range(OVERFLOW_SAMPLE_SIZE)
    ]
    derived = {'alpha': _module(unresolved)}

    _edges, notes = _derive(derived)

    note = notes[0]
    assert f'{OVERFLOW_SAMPLE_SIZE} reference(s) suppressed' in note
    assert f'(+{NOTE_OVERFLOW} more)' in note


def test_all_three_categories_report_side_by_side():
    """Each suppression category contributes its own aggregated note."""
    derived = {
        'alpha': _module(
            [
                _ref('ghost', 'skill', resolved=False),
                _ref('delta', 'script'),
                _ref('alpha', 'path'),
            ]
        )
    }

    edges, notes = _derive(derived)

    assert edges == []
    assert len(notes) == 3
    assert _note_for(notes, 'unresolved-target')
    assert _note_for(notes, 'unknown-endpoint')
    assert _note_for(notes, 'self-edge')


# =============================================================================
# Edge-set shape
# =============================================================================


def test_no_cross_bundle_references_yields_empty_edges_and_notes():
    """A bundle set with nothing to say returns the null-on-absent pair."""
    derived = {'alpha': _module([]), 'beta': _module([])}

    assert _derive(derived) == ([], [])


def test_modules_without_component_refs_contribute_nothing():
    """Modules discovered by another extension carry no component_refs."""
    derived = {'alpha': _module(), 'beta': _module()}

    assert _derive(derived) == ([], [])


def test_edges_are_deduplicated_across_dep_types():
    """Every owned reference kind naming one target collapses to a single edge."""
    derived = {
        'alpha': _module([_ref('beta', kind) for kind in MARKDOWN_DEP_TYPES]),
        'beta': _module([]),
    }

    edges, _notes = _derive(derived)

    assert edges == [('alpha', 'beta')]


def test_edges_are_sorted():
    """Edges come back in sorted order for byte-stable output."""
    derived = {
        'zeta': _module([_ref('alpha', 'skill')]),
        'alpha': _module([_ref('mu', 'skill')]),
        'mu': _module([_ref('zeta', 'skill')]),
    }

    edges, _notes = _derive(derived)

    assert edges == [('alpha', 'mu'), ('mu', 'zeta'), ('zeta', 'alpha')]
    assert edges == sorted(edges)


# =============================================================================
# Axis-C purity: no file I/O, no subprocess
# =============================================================================


def test_derive_edges_reads_no_file_and_spawns_no_subprocess(monkeypatch):
    """The purity contract, asserted by making both operations fatal.

    A resolver is a pure function of its arguments — the filesystem-reading
    detection engine runs at discovery time instead. Monkeypatching both sinks
    to raise catches a regression that reintroduced a read at derive time.
    """

    def _forbidden(*_args, **_kwargs):
        raise AssertionError('derive_edges must not touch the filesystem or spawn a subprocess')

    monkeypatch.setattr(builtins, 'open', _forbidden)
    monkeypatch.setattr(Path, 'read_text', _forbidden)
    monkeypatch.setattr(subprocess, 'run', _forbidden)
    monkeypatch.setattr(subprocess, 'Popen', _forbidden)

    derived = {
        'alpha': _module([_ref('beta', 'skill'), _ref('ghost', 'script', resolved=False)]),
        'beta': _module([]),
    }

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert len(notes) == 1
