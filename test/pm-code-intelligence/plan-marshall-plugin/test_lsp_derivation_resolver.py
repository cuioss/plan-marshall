#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-code-intelligence ``lsp`` derivation resolver.

Tier 2 (direct import): loads the bundle extension.py and drives
``derive_edges()`` against synthetic ``derived_by_name`` maps.

The load-bearing assertions here are the ones about a harvest that did NOT run.
A resolver that reported ``edge_count: 0`` with an empty ``notes[]`` after its
server failed to start would be indistinguishable from one that ran and
legitimately found nothing — the confident empty answer this substrate exists to
eliminate.
"""

import importlib.util
import sys
import types

from conftest import MARKETPLACE_ROOT

HARVEST_RAN = {'ran': True, 'reason': '', 'notes': []}


def _load_extension():
    """Load the pm-code-intelligence bundle extension.py and return an Extension."""
    extension_path = MARKETPLACE_ROOT / 'pm-code-intelligence' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
    spec = importlib.util.spec_from_file_location('extension_pm_code_intelligence', extension_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Extension()


def _module(refs, harvest=None):
    """Build a minimal derived-module dict carrying refs and a harvest record."""
    return {'component_refs': refs, 'lsp_harvest': harvest if harvest is not None else dict(HARVEST_RAN)}


def _ref(target, dep_type='lsp', resolved=True):
    return {'target_bundle': target, 'dep_type': dep_type, 'resolved': resolved}


def test_resolver_id_is_lsp():
    """The provenance id is the stable string stamped onto every edge."""
    assert _load_extension().derivation_resolver_id() == 'lsp'


def test_registers_no_skill_domain():
    """The bundle contributes an edge set, not skills."""
    assert _load_extension().get_skill_domains() == []


def test_derives_edge_from_lsp_reference():
    """A resolved lsp reference between two known modules becomes an edge."""
    # Arrange
    derived = {'alpha': _module([_ref('beta')]), 'beta': _module([])}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == [('alpha', 'beta')]
    assert notes == []


def test_ignores_reference_kinds_owned_by_sibling_resolvers():
    """Non-lsp dep types are out of scope, so they yield no edge AND no note."""
    # Arrange — the four kinds owned by the markdown/python/documentation joins.
    refs = [_ref('beta', dep_type=kind) for kind in ('import', 'script', 'skill', 'path')]
    derived = {'alpha': _module(refs), 'beta': _module([])}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert — silence here is correct: out-of-scope is not suppression.
    assert edges == []
    assert notes == []


def test_unknown_endpoint_is_suppressed_and_reported():
    """A target naming no known module yields no edge and an aggregated note."""
    # Arrange
    derived = {'alpha': _module([_ref('ghost')])}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert any(note.startswith('unknown-endpoint:') for note in notes)


def test_unresolved_target_is_suppressed_and_reported():
    """An unresolved reference yields no edge and an aggregated note."""
    # Arrange
    derived = {'alpha': _module([_ref('beta', resolved=False)]), 'beta': _module([])}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert any(note.startswith('unresolved-target:') for note in notes)


def test_self_edge_is_suppressed_and_reported():
    """A module referencing itself yields no edge and an aggregated note."""
    # Arrange
    derived = {'alpha': _module([_ref('alpha')])}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert any(note.startswith('self-edge:') for note in notes)


def test_harvest_that_did_not_run_is_reported_not_silent():
    """A failed harvest produces a stated reason, never a bare zero-edge success.

    This is the provenance contract's whole point: zero edges because the server
    never started must not read like zero edges because the workspace has none.
    """
    # Arrange
    failed = {'ran': False, 'reason': 'server-absent: pyright-langserver is not on PATH', 'notes': []}
    derived = {'alpha': _module([], harvest=failed)}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert notes == ['harvest-did-not-run: server-absent: pyright-langserver is not on PATH']


def test_harvest_failure_note_is_emitted_once_across_modules():
    """The workspace-wide record rides every module but is reported once."""
    # Arrange
    failed = {'ran': False, 'reason': 'server-timeout: budget exceeded', 'notes': []}
    derived = {name: _module([], harvest=failed) for name in ('alpha', 'beta', 'gamma')}

    # Act
    _edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert notes == ['harvest-did-not-run: server-timeout: budget exceeded']


def test_successful_harvest_with_no_references_reports_no_failure_note():
    """A harvest that ran and found nothing is a real answer, not a failure."""
    # Arrange
    derived = {'alpha': _module([])}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert not any(note.startswith('harvest-did-not-run:') for note in notes)


def test_harvest_notes_propagate_from_the_engine():
    """Suppressions the discovery-time lift recorded reach the resolver report."""
    # Arrange
    harvest = {'ran': True, 'reason': '', 'notes': ['unattributable-endpoint: 2 suppressed [a -> b]']}
    derived = {'alpha': _module([], harvest=harvest)}

    # Act
    _edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert 'unattributable-endpoint: 2 suppressed [a -> b]' in notes


def test_module_without_harvest_record_contributes_nothing():
    """A module discovered by another extension carries no record and is skipped."""
    # Arrange
    derived = {'alpha': {'component_refs': []}}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert notes == []


def test_edges_are_sorted_and_deduplicated():
    """Byte-stable output: duplicates collapse and order is deterministic."""
    # Arrange
    derived = {
        'zeta': _module([_ref('alpha'), _ref('alpha')]),
        'alpha': _module([_ref('beta')]),
        'beta': _module([]),
    }

    # Act
    edges, _notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == [('alpha', 'beta'), ('zeta', 'alpha')]


def test_config_defaults_seed_the_harvest_off(monkeypatch):
    """The harvest is opt-IN: the shipped default must be disabled.

    It boots a language server and indexes the workspace — a cost every crawl
    would otherwise pay whether or not the project wants symbol-derived edges.
    """
    # Arrange — a stand-in for the shared config surface, recording what is set.
    written = {}
    fake = types.ModuleType('_config_core')
    fake.ext_defaults_set_default = lambda key, value, _root: written.setdefault(key, value)
    monkeypatch.setitem(sys.modules, '_config_core', fake)

    # Act
    _load_extension().config_defaults('/tmp/project')

    # Assert
    assert written['pm_code_intelligence.lsp.enabled'] == 'false'


def test_config_defaults_use_the_shared_surface_not_a_parallel_mechanism(monkeypatch):
    """Every setting is an ordinary extension default, written through the helper."""
    # Arrange
    written = {}
    fake = types.ModuleType('_config_core')
    fake.ext_defaults_set_default = lambda key, value, _root: written.setdefault(key, value)
    monkeypatch.setitem(sys.modules, '_config_core', fake)

    # Act
    _load_extension().config_defaults('/tmp/project')

    # Assert — namespaced keys only; no file of the bundle's own is written.
    assert set(written) == {
        'pm_code_intelligence.lsp.enabled',
        'pm_code_intelligence.lsp.python.server',
        'pm_code_intelligence.lsp.timeout_seconds',
    }


def test_config_defaults_is_a_noop_without_the_config_surface(monkeypatch):
    """An uninitialized project must not fail extension loading."""
    # Arrange
    monkeypatch.setitem(sys.modules, '_config_core', None)

    # Act / Assert — the guarded import degrades to doing nothing.
    _load_extension().config_defaults('/tmp/project')


def test_derive_edges_runs_no_subprocess_and_touches_no_disk(monkeypatch):
    """The Axis-C purity contract, asserted rather than assumed.

    The harvest is a discovery-time engine precisely so this method stays pure;
    a regression that reached for a server here would reintroduce the whole-index
    cost on every graph query.
    """
    # Arrange
    import subprocess

    def _fail(*_args, **_kwargs):
        raise AssertionError('derive_edges must not run a subprocess or read the filesystem')

    monkeypatch.setattr(subprocess, 'Popen', _fail)
    monkeypatch.setattr(subprocess, 'run', _fail)
    monkeypatch.setattr('builtins.open', _fail)
    derived = {'alpha': _module([_ref('beta')]), 'beta': _module([])}

    # Act
    edges, _notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == [('alpha', 'beta')]
