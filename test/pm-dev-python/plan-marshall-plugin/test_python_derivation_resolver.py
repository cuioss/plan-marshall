#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the python-import derivation resolver (Axis-C) on pm-dev-python.

The resolver is a **pure join** over the ``component_refs`` field module
discovery materializes, so these tests hand it module maps directly rather than
discovering a fixture tree: the input shape IS the contract, and building it by
hand keeps each suppression rule pinned in isolation.

Covered:

- The provenance id is ``python`` and both hierarchies' ``isinstance`` hold.
- Only ``import`` entries contribute; the four markdown reference kinds are
  ignored and, being out of scope rather than suppressed, produce no note.
- Unresolved targets, unknown endpoints, and self-edges are each suppressed AND
  reported, in aggregated form rather than one note per dropped reference.
- ``derive_edges`` reads no file and spawns no subprocess.
- The pre-existing Axis-A faces still behave as they did before the Axis-C
  addition — multiple inheritance must not disturb them.
- **Registration is unconditional**: the resolver is discovered even for a
  project the python domain does not apply to. ``applies_to_module()`` gates
  skill loading, not resolver registration, and the two are independent.
"""

import builtins
import importlib.util
import subprocess
from pathlib import Path

from extension_base import NOTE_SAMPLE_LIMIT, DerivationResolverBase, ExtensionBase

from conftest import MARKETPLACE_ROOT, load_script_module

EXTENSION_FILE = MARKETPLACE_ROOT / 'pm-dev-python' / 'skills' / 'plan-marshall-plugin' / 'extension.py'


def _load_extension_module():
    """Load the pm-dev-python bundle extension.py by explicit file path.

    Every domain bundle ships an ``extension.py`` sharing the module basename
    ``extension``; loading via ``spec_from_file_location`` against the explicit
    path avoids the cross-bundle ``import extension`` collision.
    """
    spec = importlib.util.spec_from_file_location('extension_pm_dev_python_resolver', EXTENSION_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_extension_module = _load_extension_module()
Extension = _extension_module.Extension

_discovery = load_script_module(
    'plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_python_resolver'
)

MARKDOWN_DEP_TYPES = ('script', 'skill', 'path', 'implements')


# =============================================================================
# Input builders
# =============================================================================


def _ref(target_bundle: str, dep_type: str = 'import', resolved: bool = True) -> dict:
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


def test_resolver_id_is_python():
    """The stable provenance id names this resolver on every edge it produces."""
    assert Extension().derivation_resolver_id() == 'python'


def test_extension_opts_into_both_hierarchies():
    """Axis-A and Axis-C are both satisfied by the same Extension instance."""
    extension = Extension()

    assert isinstance(extension, ExtensionBase)
    assert isinstance(extension, DerivationResolverBase)


# =============================================================================
# Dep-type scoping
# =============================================================================


def test_import_entries_contribute_edges():
    """An import reference between two known bundles yields an edge."""
    derived = {'alpha': _module([_ref('beta')]), 'beta': _module([])}

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert notes == []


def test_markdown_dep_types_are_ignored_without_a_note():
    """The four markdown kinds belong to the sibling markdown resolver.

    Out of scope is not the same as suppressed: an ignored markdown reference
    must NOT appear in notes[], or every report would claim a suppression that
    the markdown resolver is in fact handling.
    """
    derived = {
        'alpha': _module([_ref('beta', dep_type) for dep_type in MARKDOWN_DEP_TYPES]),
        'beta': _module([]),
    }

    edges, notes = _derive(derived)

    assert edges == []
    assert notes == []


def test_each_markdown_dep_type_is_ignored_on_its_own():
    """No single markdown kind leaks an edge into the python resolver."""
    for dep_type in MARKDOWN_DEP_TYPES:
        derived = {'alpha': _module([_ref('beta', dep_type)]), 'beta': _module([])}

        assert _derive(derived) == ([], []), f'{dep_type} leaked into the python resolver'


def test_markdown_entry_does_not_suppress_a_sibling_import_edge():
    """An ignored markdown reference leaves the same module's import edges intact."""
    derived = {
        'alpha': _module([_ref('beta', 'skill'), _ref('beta', 'import')]),
        'beta': _module([]),
    }

    edges, _notes = _derive(derived)

    assert edges == [('alpha', 'beta')]


# =============================================================================
# Suppression
# =============================================================================


def test_unresolved_import_is_suppressed_and_reported():
    """An import whose target does not exist yields no edge but a note."""
    derived = {'alpha': _module([_ref('ghost', resolved=False)]), 'beta': _module([])}

    edges, notes = _derive(derived)

    assert edges == []
    note = _note_for(notes, 'unresolved-target')
    assert '1 reference(s) suppressed' in note
    assert 'alpha -> ghost [import]' in note


def test_import_to_unknown_module_is_suppressed_and_reported():
    """A resolved import naming no known module yields no edge but a note."""
    derived = {'alpha': _module([_ref('delta')])}

    edges, notes = _derive(derived)

    assert edges == []
    note = _note_for(notes, 'unknown-endpoint')
    assert '1 reference(s) suppressed' in note
    assert 'alpha -> delta [import]' in note


def test_self_edge_is_excluded_and_reported():
    """A bundle importing itself is dropped by the resolver, not just the merge.

    Dropping it here is what keeps this resolver's own edge_count honest: the
    core merge also drops self-edges, so a resolver that emitted them would
    report more edges than the graph ever receives.
    """
    derived = {'alpha': _module([_ref('alpha')])}

    edges, notes = _derive(derived)

    assert edges == []
    note = _note_for(notes, 'self-edge')
    assert 'alpha -> alpha [import]' in note


def test_self_edge_does_not_suppress_a_real_edge_from_the_same_module():
    """A self-import and a cross-bundle import are judged independently."""
    derived = {'alpha': _module([_ref('alpha'), _ref('beta')]), 'beta': _module([])}

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert _note_for(notes, 'self-edge')


# =============================================================================
# Notes are aggregated, never per-reference
# =============================================================================


def test_many_suppressed_imports_collapse_into_one_note_per_category():
    """One note per category with the full count — never one note per drop."""
    unresolved = [_ref(f'ghost-{index}', resolved=False) for index in range(5)]
    derived = {'alpha': _module(unresolved)}

    edges, notes = _derive(derived)

    assert edges == []
    assert len(notes) == 1
    assert notes[0].startswith('unresolved-target: 5 reference(s) suppressed')


def test_aggregated_note_bounds_its_sample_and_reports_the_overflow():
    """The sample is capped, and the omitted remainder is counted, not hidden."""
    unresolved = [_ref(f'ghost-{index}', resolved=False) for index in range(5)]
    derived = {'alpha': _module(unresolved)}

    _edges, notes = _derive(derived)

    assert f'(+{5 - NOTE_SAMPLE_LIMIT} more)' in notes[0]


def test_all_three_categories_report_side_by_side():
    """Each suppression category contributes its own aggregated note."""
    derived = {
        'alpha': _module([_ref('ghost', resolved=False), _ref('delta'), _ref('alpha')])
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


def test_no_import_references_yields_empty_edges_and_notes():
    """A bundle set with nothing to say returns the null-on-absent pair."""
    derived = {'alpha': _module([]), 'beta': _module([])}

    assert _derive(derived) == ([], [])


def test_modules_without_component_refs_contribute_nothing():
    """Modules discovered by another extension carry no component_refs."""
    derived = {'alpha': _module(), 'beta': _module()}

    assert _derive(derived) == ([], [])


def test_repeated_import_references_collapse_to_one_edge():
    """Duplicate references to one target yield a single edge."""
    derived = {'alpha': _module([_ref('beta'), _ref('beta')]), 'beta': _module([])}

    edges, _notes = _derive(derived)

    assert edges == [('alpha', 'beta')]


def test_edges_are_sorted():
    """Edges come back in sorted order for byte-stable output."""
    derived = {
        'zeta': _module([_ref('alpha')]),
        'alpha': _module([_ref('mu')]),
        'mu': _module([_ref('zeta')]),
    }

    edges, _notes = _derive(derived)

    assert edges == [('alpha', 'mu'), ('mu', 'zeta'), ('zeta', 'alpha')]
    assert edges == sorted(edges)


# =============================================================================
# Axis-C purity: no file I/O, no subprocess
# =============================================================================


def test_derive_edges_reads_no_file_and_spawns_no_subprocess(monkeypatch):
    """The purity contract, asserted by making both operations fatal."""

    def _forbidden(*_args, **_kwargs):
        raise AssertionError('derive_edges must not touch the filesystem or spawn a subprocess')

    monkeypatch.setattr(builtins, 'open', _forbidden)
    monkeypatch.setattr(Path, 'read_text', _forbidden)
    monkeypatch.setattr(subprocess, 'run', _forbidden)
    monkeypatch.setattr(subprocess, 'Popen', _forbidden)

    derived = {
        'alpha': _module([_ref('beta'), _ref('ghost', resolved=False)]),
        'beta': _module([]),
    }

    edges, notes = _derive(derived)

    assert edges == [('alpha', 'beta')]
    assert len(notes) == 1


# =============================================================================
# Axis-A regression — multiple inheritance must not disturb the existing faces
# =============================================================================


def test_get_skill_domains_still_declares_the_python_domain():
    """The Axis-A domain declaration is unchanged by the Axis-C addition."""
    domains = Extension().get_skill_domains()

    assert [entry['domain']['key'] for entry in domains] == ['python']


def test_applies_to_module_still_detects_a_python_module():
    """A python build system still yields a high-confidence applicable verdict."""
    verdict = Extension().applies_to_module({'build_systems': ['python'], 'paths': {}})

    assert verdict['applicable'] is True
    assert verdict['confidence'] == 'high'


def test_applies_to_module_still_rejects_a_non_python_module():
    """A module with no Python signal is still reported as not applicable."""
    verdict = Extension().applies_to_module({'build_systems': ['maven'], 'paths': {'sources': ['src/main']}})

    assert verdict['applicable'] is False
    assert verdict['confidence'] == 'none'


def test_provides_triage_is_unchanged():
    """The triage binding survives the Axis-C addition."""
    assert Extension().provides_triage() == 'pm-dev-python:ext-triage-python'


def test_provides_arch_gate_is_unchanged():
    """The arch-gate binding survives the Axis-C addition."""
    assert Extension().provides_arch_gate() == {'tool': 'import-linter'}


# =============================================================================
# Registration is unconditional — applicability does not gate discovery
# =============================================================================

NON_PYTHON_MODULE = {'build_systems': ['maven'], 'paths': {'sources': ['src/main'], 'tests': ['src/test']}}
"""A module the python domain explicitly does not apply to."""


def test_the_fixture_module_is_genuinely_not_applicable():
    """Anchor for the next test: without this, that test could pass vacuously."""
    verdict = Extension().applies_to_module(NON_PYTHON_MODULE)

    assert verdict['applicable'] is False


def test_resolver_is_discovered_even_when_the_domain_does_not_apply(monkeypatch):
    """Registration is discovered off the unfiltered extension path.

    ``discover_derivation_resolvers()`` iterates ``discover_all_extensions()``,
    which returns every extension regardless of project applicability — the
    applicability-filtered variant is not on this path. So a project the python
    domain does not apply to still gets this resolver's edges.
    """
    extension = Extension()
    assert extension.applies_to_module(NON_PYTHON_MODULE)['applicable'] is False

    monkeypatch.setattr(
        _discovery,
        'discover_all_extensions',
        lambda: [{'bundle': 'pm-dev-python', 'path': '', 'module': extension}],
    )
    monkeypatch.setattr(_discovery, 'discover_build_extensions', lambda: [])

    resolvers = _discovery.discover_derivation_resolvers()

    assert [record['id'] for record in resolvers] == ['python']


def test_discovery_does_not_consult_applies_to_module(monkeypatch):
    """The collector never calls the applicability face at all.

    Making applies_to_module fatal proves independence positively, rather than
    inferring it from a discovery result that happened to come out right.
    """
    extension = Extension()

    def _forbidden(*_args, **_kwargs):
        raise AssertionError('resolver discovery must not consult applies_to_module')

    monkeypatch.setattr(extension, 'applies_to_module', _forbidden)
    monkeypatch.setattr(
        _discovery,
        'discover_all_extensions',
        lambda: [{'bundle': 'pm-dev-python', 'path': '', 'module': extension}],
    )
    monkeypatch.setattr(_discovery, 'discover_build_extensions', lambda: [])

    resolvers = _discovery.discover_derivation_resolvers()

    assert [record['id'] for record in resolvers] == ['python']
