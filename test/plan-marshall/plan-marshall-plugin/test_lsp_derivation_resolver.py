#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``lsp`` derivation resolver hosted on the plan-marshall bundle.

Tier 2 (direct import): loads the plan-marshall bundle extension.py and drives
``derive_edges()`` against synthetic ``derived_by_name`` maps.

The resolver's host is ``plan-marshall``'s own domain extension, which already
carries Axis-A (skill domains, discovery) and Axis-D (path attribution). Axis-C
rides alongside them by multiple inheritance, so two properties matter here that
did not on a bundle whose ONLY substance was the resolver: the pre-existing
Axis-A face must be undisturbed by the addition, and the resolver must still be
DISCOVERED — the ``isinstance(module, DerivationResolverBase)`` filter is what
admits it, and a class that merely answers ``derivation_resolver_id()`` must not
be admitted. The discovery test below is therefore paired with a matched
negative control that differs from its positive twin by exactly one base class.

The load-bearing assertions about ``derive_edges`` are the ones about a harvest
that did NOT run. A resolver that reported ``edge_count: 0`` with an empty
``notes[]`` after its server failed to start would be indistinguishable from one
that ran and legitimately found nothing — the confident empty answer this
substrate exists to eliminate.
"""


from extension_base import DerivationResolverBase, ExtensionBase

from conftest import load_script_module, load_skill_module

HARVEST_RAN = {'ran': True, 'reason': '', 'notes': []}

_discovery = load_script_module(
    'plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_lsp_resolver'
)


def _load_extension():
    """Load the plan-marshall bundle extension.py and return an Extension.

    Every domain bundle ships an ``extension.py`` sharing the module basename
    ``extension``, so a distinct ``module_name`` is passed to avoid the
    cross-bundle ``import extension`` collision.
    """
    module = load_skill_module(
        'plan-marshall', 'plan-marshall-plugin', 'extension.py', 'extension_plan_marshall_lsp'
    )
    return module.Extension()


def _module(refs, harvest=None):
    """Build a minimal derived-module dict carrying refs and a harvest record."""
    return {'component_refs': refs, 'lsp_harvest': harvest if harvest is not None else dict(HARVEST_RAN)}


def _ref(target, dep_type='lsp', resolved=True):
    return {'target_bundle': target, 'dep_type': dep_type, 'resolved': resolved}


def test_resolver_id_is_lsp():
    """The provenance id is the stable string stamped onto every edge."""
    assert _load_extension().derivation_resolver_id() == 'lsp'


def test_host_still_declares_only_the_general_dev_domain():
    """Adding Axis-C must leave the host's pre-existing Axis-A face untouched.

    The retired bundle asserted ``get_skill_domains() == []`` here, which was
    true only of a bundle whose whole substance was the resolver. The resolver's
    new host is a real domain extension, so the property worth pinning is the
    opposite one: the domain list is exactly what it was before the fold, and
    multiple inheritance did not disturb it.
    """
    assert [entry['domain']['key'] for entry in _load_extension().get_skill_domains()] == [
        'general-dev'
    ]


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


def test_project_with_no_harvest_record_anywhere_says_so():
    """The silent-zero this resolver must never produce, in its widest form.

    In a project whose modules are discovered by an extension that does not
    materialize the harvest field, NO module carries a record. Returning a bare
    empty edge list there would hand every consumer project a confident
    `status: ok, edge_count: 0` that is really "no harvest happened here".
    """
    # Arrange — modules exist, but none carries a harvest record.
    derived = {'alpha': {'component_refs': []}, 'beta': {'component_refs': []}}

    # Act
    edges, notes = _load_extension().derive_edges(derived, {})

    # Assert
    assert edges == []
    assert len(notes) == 1
    assert notes[0].startswith('harvest-did-not-run:')


def test_empty_module_map_reports_nothing():
    """No modules at all is core's null case, not a harvest failure to report."""
    # Act
    edges, notes = _load_extension().derive_edges({}, {})

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


def test_host_ships_no_configuration_mechanism_for_the_harvest():
    """D4's ⛔: no parallel config surface.

    The harvest is switched on solely by the shared machine-local
    `language_servers` binding that `plan-marshall:lsp-client` already reads. A
    second key naming the same server for the same language would be exactly the
    parallel store that surface exists to prevent, so the resolver's host must
    not override `config_defaults` at all.
    """
    # Arrange / Act
    extension_type = type(_load_extension())

    # Assert — the inherited no-op, not an override of its own.
    assert extension_type.config_defaults is ExtensionBase.config_defaults


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

    extension = _load_extension()
    monkeypatch.setattr(subprocess, 'Popen', _fail)
    monkeypatch.setattr(subprocess, 'run', _fail)
    monkeypatch.setattr('builtins.open', _fail)
    derived = {'alpha': _module([_ref('beta')]), 'beta': _module([])}

    # Act
    edges, _notes = extension.derive_edges(derived, {})

    # Assert
    assert edges == [('alpha', 'beta')]


# =============================================================================
# Discovery — the resolver is reachable, with a matched negative control
# =============================================================================
#
# ``discover_derivation_resolvers()`` admits a module by
# ``isinstance(module, DerivationResolverBase)``, NOT by whether it answers
# ``derivation_resolver_id()``. The two stubs below are identical in every
# respect except that base class, so the pair exercises the filter in BOTH
# directions: the positive is admitted, and the negative — which would pass any
# duck-typed check — is rejected. Without the negative, the positive could pass
# against an implementation that never filtered at all.


class _AxisCOptIn(ExtensionBase, DerivationResolverBase):
    """Positive control: an Extension-shaped class that DOES opt into Axis-C."""

    def get_skill_domains(self) -> list[dict]:
        return []

    def derivation_resolver_id(self) -> str:
        return 'lsp-control'


class _AxisCLookalike(ExtensionBase):
    """Negative control: the same shape MINUS ``DerivationResolverBase``.

    It still answers ``derivation_resolver_id()`` with the same id, so nothing
    but the missing base distinguishes it from the positive control above.
    """

    def get_skill_domains(self) -> list[dict]:
        return []

    def derivation_resolver_id(self) -> str:
        return 'lsp-control'


def _patch_domain_extensions(monkeypatch, *modules):
    """Point both discovery collectors at the given in-process domain stubs."""
    monkeypatch.setattr(
        _discovery,
        'discover_all_extensions',
        lambda: [
            {'bundle': f'bundle-{i}', 'path': '', 'module': m} for i, m in enumerate(modules)
        ],
    )
    monkeypatch.setattr(_discovery, 'discover_build_extensions', lambda: [])


def test_isinstance_filter_admits_an_axis_c_opt_in(monkeypatch):
    """The positive direction: subclassing DerivationResolverBase gets you discovered."""
    # Arrange
    _patch_domain_extensions(monkeypatch, _AxisCOptIn())

    # Act
    resolvers = _discovery.discover_derivation_resolvers()

    # Assert
    assert [rec['id'] for rec in resolvers] == ['lsp-control']


def test_isinstance_filter_rejects_the_same_shape_without_the_base(monkeypatch):
    """The failing direction of the same control — answering the method is not enough.

    This is what makes the positive assertion above non-vacuous: a discovery
    implementation that admitted anything exposing ``derivation_resolver_id()``
    would pass that test and fail this one.
    """
    # Arrange
    _patch_domain_extensions(monkeypatch, _AxisCLookalike())

    # Act
    resolvers = _discovery.discover_derivation_resolvers()

    # Assert
    assert resolvers == []


def test_lsp_resolver_is_discovered_from_the_plan_marshall_bundle():
    """Live tree: the ``lsp`` resolver is surfaced, and plan-marshall hosts it.

    The fold's central regression. Discovery is unconditional — it applies no
    domain filter — so the only thing that can make this fail is the resolver no
    longer being reachable from the bundle that now owns it.
    """
    # Act
    records = _discovery.discover_derivation_resolvers()

    # Assert
    by_id = {rec['id']: rec for rec in records}
    assert 'lsp' in by_id, f'the lsp resolver was not discovered; got {sorted(by_id)}'
    assert by_id['lsp']['origin'] == 'plan-marshall'
