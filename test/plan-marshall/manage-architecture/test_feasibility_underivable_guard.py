#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Negative-control test for the refine feasibility underivable guard (D3).

The refine phase's feasibility check reasons over ``architecture graph`` output to
validate dependency direction. That reasoning CANNOT fire at zero edges — an
edgeless graph carries no dependency-direction signal. The guard the deliverable
adds is: before treating an empty graph as a clean dependency-direction pass, read
``resolver_count`` to tell the two empties apart.

``resolver_count: 0`` (no resolver ran) means UNDERIVABLE — the empty edge set is
an absence of capability, and a consumer must NOT record a clean pass.
``resolver_count: N`` with empty edges means N resolvers ran and found nothing — a
real answer, and a clean pass is correct.

This is the negative control from the plan's Verification section: a zero-edge
graph produced by "no resolver" must be DISTINGUISHABLE from a zero-edge graph
produced by "a resolver found nothing", asserted by a consumer that applies the
documented guard and classifies the two oppositely — so it CANNOT silently pass on
emptiness.
"""

import tempfile

import extension_discovery

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
get_module_graph = _cmd_client.get_module_graph


class _StubResolver:
    """A derivation resolver returning canned ``(edges, notes)``."""

    def __init__(self, resolver_id: str, edges=None):
        self.resolver_id = resolver_id
        self._edges = edges or []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return self._edges, []


def _register(monkeypatch, *resolvers: _StubResolver) -> None:
    records = [
        {'origin': f'stub-{r.resolver_id}', 'id': r.resolver_id, 'module': r} for r in resolvers
    ]
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


def _seed(tmpdir: str, names: list[str]) -> None:
    save_project_meta(
        {
            'name': 'feasibility-fixture',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in names},
        },
        tmpdir,
    )
    for name in names:
        save_module_derived(
            name,
            {
                'name': name,
                'paths': {'module': name},
                'dependencies': ['org.example:external:compile'],
                'commands': {},
            },
            tmpdir,
        )


def _dependency_direction_derivable(graph_result: dict) -> bool:
    """The documented refine guard, modelled as the consumer applies it.

    Dependency-direction reasoning is derivable iff a resolver ran — otherwise the
    empty edge set is UNDERIVABLE, not a clean pass. This mirrors the instruction
    in phase-2-refine's Feasibility Check: the check a consumer performs BEFORE
    reading the edges.
    """
    return bool(graph_result['resolver_count'] > 0)


def test_zero_resolver_graph_is_underivable_not_a_clean_pass(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, ['api', 'core', 'app'])
        # No resolver registered → the underivable case.
        monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])

        graph = get_module_graph(tmpdir)

        assert graph['edges'] == []
        assert graph['resolver_count'] == 0
        # The guard refuses to treat this empty graph as a clean pass.
        assert _dependency_direction_derivable(graph) is False


def test_resolver_present_empty_graph_is_a_genuine_pass(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(tmpdir, ['api', 'core', 'app'])
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        graph = get_module_graph(tmpdir)

        # Same empty edge set — but a resolver ran, so the guard permits a pass.
        assert graph['edges'] == []
        assert graph['resolver_count'] == 1
        assert _dependency_direction_derivable(graph) is True


def test_the_two_empty_graphs_are_classified_oppositely(monkeypatch):
    """The core negative control: identical empty edges, opposite guard verdicts.

    A consumer that ignored ``resolver_count`` would silently pass BOTH as clean —
    exactly the vacuous-consumer failure this deliverable closes.
    """
    with tempfile.TemporaryDirectory() as underivable, tempfile.TemporaryDirectory() as derived_nothing:
        _seed(underivable, ['api', 'core'])
        _seed(derived_nothing, ['api', 'core'])

        monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])
        empty_no_resolver = get_module_graph(underivable)

        _register(monkeypatch, _StubResolver('maven', edges=[]))
        empty_with_resolver = get_module_graph(derived_nothing)

        # Byte-identical empty edge sets ...
        assert empty_no_resolver['edges'] == empty_with_resolver['edges'] == []
        # ... classified oppositely, so the consumer cannot silently pass emptiness.
        assert _dependency_direction_derivable(empty_no_resolver) is False
        assert _dependency_direction_derivable(empty_with_resolver) is True
