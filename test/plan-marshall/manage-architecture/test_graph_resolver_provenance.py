#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the graph family's delegation to the Axis-C resolver seam.

The graph / path / neighbors / impact verbs no longer derive edges themselves —
they delegate to the registered ``DerivationResolverBase`` implementors and carry
the merged result's provenance on every response. These tests pin the seam and the
**anti-vacuity property** it exists to buy:

``resolver_count: 0`` with an empty result means NO RESOLVER RAN (an absence of
capability), while ``resolver_count: N`` with an empty result means N RESOLVERS
RAN AND FOUND NOTHING (a real, positive answer). The two states must be
distinguishable without inspecting the edge list.

Resolvers are injected by monkeypatching ``extension_discovery`` — the seam's
deferred ``from extension_discovery import discover_derivation_resolvers`` does a
fresh attribute lookup on the module at every call, so patching the module
attribute is sufficient and no real bundle needs to ship a resolver.

Fixture modules deliberately carry NO ``internal_dependencies`` (so the declared
precedence branches do not shadow the resolver) and a NON-EMPTY ``dependencies``
list (so the lazy Maven enrichment short-circuits and no subprocess runs).
"""

import tempfile

import extension_discovery
import pytest

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived

get_module_graph = _cmd_client.get_module_graph
get_module_path = _cmd_client.get_module_path
get_module_neighbors = _cmd_client.get_module_neighbors
get_module_impact = _cmd_client.get_module_impact
render_overview = _cmd_client.render_overview
render_module_markdown = _cmd_client.render_module_markdown


# =============================================================================
# Fixtures
# =============================================================================


def _seed(tmpdir: str, modules: dict[str, dict]) -> None:
    save_project_meta(
        {
            'name': 'resolver-fixture',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        save_module_derived(name, data, tmpdir)


def _module(name: str, **extra) -> dict:
    """A module with no declared internal_dependencies and non-empty dependencies."""
    data = {
        'name': name,
        'paths': {'module': name},
        # Non-empty so ``_enriched_dependencies`` short-circuits (no Maven run).
        'dependencies': ['org.example:external:compile'],
        'commands': {},
    }
    data.update(extra)
    return data


def _create_triple(tmpdir: str) -> None:
    """Three modules with NO declared edges — every edge must come from a resolver."""
    _seed(tmpdir, {'api': _module('api'), 'core': _module('core'), 'app': _module('app')})


def _create_sibling_pair(tmpdir: str) -> None:
    """A virtual-sibling pair, so the post-resolution augmentation is exercised."""
    _seed(
        tmpdir,
        {
            'web-maven': _module(
                'web-maven',
                virtual_module={
                    'physical_path': 'web',
                    'technology': 'maven',
                    'sibling_modules': ['web-npm'],
                },
            ),
            'web-npm': _module(
                'web-npm',
                virtual_module={
                    'physical_path': 'web',
                    'technology': 'npm',
                    'sibling_modules': ['web-maven'],
                },
            ),
        },
    )


class _StubResolver:
    """A resolver returning canned ``(edges, notes)``."""

    def __init__(self, resolver_id: str, edges=None, notes=None):
        self.resolver_id = resolver_id
        self._edges = edges or []
        self._notes = notes or []

    def derivation_resolver_id(self) -> str:
        return self.resolver_id

    def derive_edges(self, derived_by_name, enriched_by_name):
        return self._edges, self._notes


def _register(monkeypatch, *resolvers: _StubResolver) -> None:
    """Point the discovery seam at the supplied stub resolvers."""
    records = [
        {'origin': f'stub-{r.resolver_id}', 'id': r.resolver_id, 'module': r} for r in resolvers
    ]
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)


@pytest.fixture
def no_resolvers(monkeypatch):
    """The zero-registered-resolver state."""
    monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: [])


# =============================================================================
# 1. Zero resolvers registered — resolver_count 0 + empty result
# =============================================================================


def test_graph_with_zero_resolvers_reports_zero_count_and_no_edges(no_resolvers):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)

        result = get_module_graph(tmpdir)

        assert result['resolver_count'] == 0
        assert result['resolvers'] == []
        assert result['edges'] == []
        assert result['graph']['edge_count'] == 0


def test_path_with_zero_resolvers_reports_zero_count_and_no_path(no_resolvers):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)

        path, resolvers = get_module_path('app', 'api', tmpdir)

        assert path is None
        assert resolvers == []


def test_neighbors_with_zero_resolvers_reports_zero_count_and_lone_module(no_resolvers):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)

        neighbors, resolvers = get_module_neighbors('app', 2, tmpdir)

        assert neighbors == ['app']
        assert resolvers == []


def test_impact_with_zero_resolvers_reports_zero_count_and_empty_impact(no_resolvers):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)

        impact, resolvers = get_module_impact('api', tmpdir)

        assert impact == []
        assert resolvers == []


# =============================================================================
# 2. One resolver that finds nothing — resolver_count 1 + empty result
# =============================================================================


def test_graph_with_one_empty_resolver_is_distinguishable_from_zero(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        result = get_module_graph(tmpdir)

        # Same empty edge set as the zero-resolver case — but a DIFFERENT,
        # positive meaning, and the response says so.
        assert result['edges'] == []
        assert result['resolver_count'] == 1
        assert result['resolvers'] == [
            {'id': 'maven', 'edge_count': 0, 'status': 'ok', 'notes': []}
        ]


def test_path_with_one_empty_resolver_is_distinguishable_from_zero(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        path, resolvers = get_module_path('app', 'api', tmpdir)

        assert path is None
        assert len(resolvers) == 1
        assert resolvers[0]['id'] == 'maven'


def test_neighbors_with_one_empty_resolver_is_distinguishable_from_zero(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        neighbors, resolvers = get_module_neighbors('app', 2, tmpdir)

        assert neighbors == ['app']
        assert len(resolvers) == 1


def test_impact_with_one_empty_resolver_is_distinguishable_from_zero(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        impact, resolvers = get_module_impact('api', tmpdir)

        assert impact == []
        assert len(resolvers) == 1


def test_resolver_notes_ride_onto_the_graph_response(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(
            monkeypatch,
            _StubResolver('maven', edges=[], notes=['ambiguous coordinate g:a']),
        )

        result = get_module_graph(tmpdir)

        # A suppressed edge is reported, never dropped silently.
        assert result['resolvers'][0]['notes'] == ['ambiguous coordinate g:a']
        assert result['resolvers'][0]['status'] == 'ok'


# =============================================================================
# 3. N resolvers — union, and a shared edge carries both producers
# =============================================================================


def test_two_resolvers_union_their_edge_sets(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(
            monkeypatch,
            _StubResolver('maven', edges=[('app', 'core')]),
            _StubResolver('python', edges=[('core', 'api')]),
        )

        result = get_module_graph(tmpdir)

        # Emitted edges run dependency → dependent.
        emitted = {(e['from'], e['to']) for e in result['edges']}
        assert emitted == {('core', 'app'), ('api', 'core')}
        assert result['resolver_count'] == 2


def test_shared_edge_collapses_to_one_edge_with_both_producers(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(
            monkeypatch,
            _StubResolver('python', edges=[('app', 'core')]),
            _StubResolver('maven', edges=[('app', 'core')]),
        )

        result = get_module_graph(tmpdir)

        # ONE edge, not two — corroboration, not conflict.
        assert len(result['edges']) == 1
        assert result['edges'][0]['from'] == 'core'
        assert result['edges'][0]['to'] == 'app'
        assert result['edges'][0]['producers'] == ['maven', 'python']


def test_errored_resolver_reports_error_while_sibling_contributes(monkeypatch):
    class _Raising:
        def derivation_resolver_id(self) -> str:
            return 'broken'

        def derive_edges(self, derived_by_name, enriched_by_name):
            raise RuntimeError('boom')

    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        records = [
            {'origin': 'stub-broken', 'id': 'broken', 'module': _Raising()},
            {'origin': 'stub-maven', 'id': 'maven', 'module': _StubResolver('maven', edges=[('app', 'core')])},
        ]
        monkeypatch.setattr(extension_discovery, 'discover_derivation_resolvers', lambda: records)

        result = get_module_graph(tmpdir)

        assert len(result['edges']) == 1
        by_id = {rec['id']: rec for rec in result['resolvers']}
        assert by_id['broken']['status'] == 'error'
        assert by_id['broken']['edge_count'] == 0
        assert by_id['maven']['status'] == 'ok'


# =============================================================================
# 4. Traversals compute over the merged edge set
# =============================================================================


def test_path_traverses_the_merged_edge_set(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        # Each hop comes from a DIFFERENT resolver — the path only exists in the union.
        _register(
            monkeypatch,
            _StubResolver('maven', edges=[('app', 'core')]),
            _StubResolver('python', edges=[('core', 'api')]),
        )

        path, resolvers = get_module_path('app', 'api', tmpdir)

        assert path == ['app', 'core', 'api']
        assert len(resolvers) == 2


def test_neighbors_traverses_the_merged_edge_set(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(
            monkeypatch,
            _StubResolver('maven', edges=[('app', 'core')]),
            _StubResolver('python', edges=[('core', 'api')]),
        )

        neighbors, _ = get_module_neighbors('app', 2, tmpdir)

        assert neighbors == ['api', 'app', 'core']


def test_impact_traverses_the_merged_edge_set(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(
            monkeypatch,
            _StubResolver('maven', edges=[('app', 'core')]),
            _StubResolver('python', edges=[('core', 'api')]),
        )

        impact, _ = get_module_impact('api', tmpdir)

        assert impact == ['app', 'core']


# =============================================================================
# 5. Every edge carries a non-empty producers[]
# =============================================================================


def test_every_resolver_derived_edge_carries_its_producer(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[('app', 'core'), ('core', 'api')]))

        result = get_module_graph(tmpdir)

        assert result['edges']
        for edge in result['edges']:
            assert edge['producers'] == ['maven']


def test_sibling_cross_link_edges_are_stamped_not_producerless(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_sibling_pair(tmpdir)
        # No resolver derives the sibling pair — core's augmentation adds it.
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        result = get_module_graph(tmpdir)

        assert result['edges'], 'sibling augmentation must still produce edges'
        for edge in result['edges']:
            assert edge['producers'] == ['sibling-cross-link']


def test_no_edge_in_any_response_is_producerless(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_sibling_pair(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[('web-maven', 'web-npm')]))

        result = get_module_graph(tmpdir)

        for edge in result['edges']:
            assert edge['producers'], f'producer-less edge: {edge}'


def test_declared_internal_dependencies_are_stamped_declared(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed(
            tmpdir,
            {
                'api': _module('api', internal_dependencies=[]),
                'core': _module('core', internal_dependencies=['api']),
            },
        )
        _register(monkeypatch, _StubResolver('maven', edges=[]))

        result = get_module_graph(tmpdir)

        assert len(result['edges']) == 1
        assert result['edges'][0]['producers'] == ['declared']


# =============================================================================
# 6. overview renders the provenance footer
# =============================================================================


def test_overview_renders_provenance_footer_naming_resolvers(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(
            monkeypatch,
            _StubResolver('maven', edges=[('app', 'core')]),
            _StubResolver('python', edges=[]),
        )

        rendered = render_overview(tmpdir, budget=500)

        assert '## Adjacency' in rendered
        assert 'Edge provenance: derived by 2 resolver(s) — maven, python.' in rendered


def test_overview_provenance_footer_states_when_no_resolver_registered(no_resolvers):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)

        rendered = render_overview(tmpdir, budget=500)

        assert 'no derivation resolver is registered' in rendered


# =============================================================================
# 7. render_module_markdown — the fifth call site, with AND without deps
# =============================================================================


def test_module_markdown_renders_resolver_derived_dependencies(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        _register(monkeypatch, _StubResolver('maven', edges=[('app', 'core')]))

        rendered = render_module_markdown('app', tmpdir, budget=500)

        assert '## Internal Dependencies' in rendered
        assert '- core' in rendered
        assert 'Edge provenance: derived by 1 resolver(s) — maven.' in rendered


def test_module_markdown_renders_provenance_line_even_without_dependencies(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)
        # 'api' is derived as a dependency of nothing — it has no outgoing edges.
        _register(monkeypatch, _StubResolver('maven', edges=[('app', 'core')]))

        rendered = render_module_markdown('api', tmpdir, budget=500)

        # The section AND its provenance line render — this is exactly the case an
        # unqualified empty list would misrepresent as a positive finding.
        assert '## Internal Dependencies' in rendered
        assert 'Edge provenance: derived by 1 resolver(s) — maven.' in rendered


def test_module_markdown_provenance_line_states_when_no_resolver_registered(no_resolvers):
    with tempfile.TemporaryDirectory() as tmpdir:
        _create_triple(tmpdir)

        rendered = render_module_markdown('app', tmpdir, budget=500)

        assert '## Internal Dependencies' in rendered
        assert 'no derivation resolver is registered' in rendered
