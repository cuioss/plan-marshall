#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the markdown derivation resolver (Axis-C) on pm-plugin-development.

The resolver is a **pure join** over the ``component_refs`` field
``discover_plugin_modules`` materializes, so these tests hand it module maps
directly rather than discovering a fixture tree: the input shape IS the contract,
and building it by hand keeps each suppression rule pinned in isolation.

Covered:

- The provenance id is ``markdown`` and both hierarchies' ``isinstance`` hold.
- Only the four markdown reference kinds contribute; ``import`` is ignored and,
  being out of scope rather than suppressed, produces no note.
- Unresolved targets, unknown endpoints, and self-edges are each suppressed AND
  reported, in aggregated form rather than one note per dropped reference.
- ``derive_edges`` reads no file and spawns no subprocess — the Axis-C purity
  contract, asserted by making both operations fatal for the duration of the call.
"""

import builtins
import importlib.util
import subprocess
from pathlib import Path

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
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_extension_module = _load_plugin_extension()
Extension = _extension_module.Extension


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


def test_all_four_markdown_dep_types_contribute():
    """script, skill, path and implements each yield an edge."""
    derived = {
        'alpha': _module(
            [
                _ref('beta', 'script'),
                _ref('beta', 'skill'),
                _ref('beta', 'path'),
                _ref('beta', 'implements'),
            ]
        ),
        'beta': _module([]),
    }

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert notes == []


def test_each_markdown_dep_type_contributes_on_its_own():
    """No single markdown dep_type depends on another being present."""
    for dep_type in ('script', 'skill', 'path', 'implements'):
        derived = {'alpha': _module([_ref('beta', dep_type)]), 'beta': _module([])}

        edges, notes = _derive(derived)

        assert edges == [('alpha', 'beta')], f'{dep_type} produced no edge'
        assert notes == []


def test_import_entries_are_ignored_without_a_note():
    """import belongs to the sibling python resolver, so it is out of scope.

    Out of scope is not the same as suppressed: an ignored import must NOT
    appear in notes[], or every report would claim a suppression that the
    python resolver is in fact handling.
    """
    derived = {'alpha': _module([_ref('beta', 'import')]), 'beta': _module([])}

    edges, notes = _derive(derived)

    assert edges == []
    assert notes == []


def test_import_entry_does_not_suppress_a_sibling_markdown_edge():
    """An ignored import leaves the same module's markdown edges intact."""
    derived = {
        'alpha': _module([_ref('beta', 'import'), _ref('beta', 'skill')]),
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
    """The sample is capped, and the omitted remainder is counted, not hidden."""
    unresolved = [_ref(f'ghost-{index}', 'skill', resolved=False) for index in range(5)]
    derived = {'alpha': _module(unresolved)}

    _edges, notes = _derive(derived)

    note = notes[0]
    assert f'(+{5 - NOTE_SAMPLE_LIMIT} more)' in note


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
    """Four reference kinds naming one target collapse to a single edge."""
    derived = {
        'alpha': _module(
            [_ref('beta', kind) for kind in ('script', 'skill', 'path', 'implements')]
        ),
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
