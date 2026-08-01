#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end proof that the graph family answers from derived edges.

Runs the whole shipped pipeline against the plan-marshall marketplace itself —
real module discovery, real resolver discovery over both hierarchies, and the
real core merge — so the claim under test is "the graph is non-vacuous for this
project", not "the seam would work if something fed it".

The pipeline exercised here is:

``discover_plugin_modules()`` (materializes ``component_refs``)
→ ``discover_derivation_resolvers()`` (spans Axis-A and Axis-B)
→ ``merge_resolver_edges()`` (validates, unions, stamps provenance)

**The gate is asserted as a separately-failing precondition.**
``discover_plugin_modules()`` early-returns ``[]`` for any tree that is not the
plan-marshall marketplace, and every downstream assertion here would then pass
vacuously over an empty map. :func:`test_gate_precondition_marketplace_is_plan_marshall`
and :func:`test_gate_precondition_discovery_returns_modules` fail with their own
distinct messages so a broken gate is never reported as a broken graph.

The collapse property (one edge, two producers) is asserted twice on purpose:
once over the live tree, and once over a controlled module map driven through
the SAME two real resolvers and the SAME real merge. The live assertion proves
the property holds for this project; the controlled one proves the mechanism
itself, independent of whatever the tree happens to contain.
"""

from pathlib import Path

import plugin_discover
from plugin_discover import _is_plan_marshall_marketplace, discover_plugin_modules

from conftest import load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

_discovery = load_script_module(
    'plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_graph_e2e'
)
_merge = load_script_module(
    'plan-marshall', 'extension-api', '_derivation_merge.py', 'derivation_merge_graph_e2e'
)

EXPECTED_RESOLVER_IDS = ['markdown', 'maven', 'python']
"""The shipped resolver roster: one Axis-B implementor and two Axis-A ones."""

AXIS_B_RESOLVER_IDS = {'maven'}
AXIS_A_RESOLVER_IDS = {'markdown', 'python'}


# =============================================================================
# Cached pipeline — discovery walks the whole bundle tree, so it runs once
# =============================================================================

_PIPELINE: dict = {}


def _pipeline() -> dict:
    """Run the real pipeline once and memoize its result for this module."""
    if not _PIPELINE:
        modules = discover_plugin_modules(str(PROJECT_ROOT))
        derived_by_name = {module['name']: module for module in modules}
        resolvers = _discovery.discover_derivation_resolvers()
        edges, reports = _merge.merge_resolver_edges(resolvers, derived_by_name, {})
        _PIPELINE.update(
            modules=modules,
            derived_by_name=derived_by_name,
            resolvers=resolvers,
            edges=edges,
            reports=reports,
        )
    return _PIPELINE


def _producers_sets(edges: list[dict]) -> list[list[str]]:
    """Project the merged edges onto their producer lists."""
    return [edge['producers'] for edge in edges]


# =============================================================================
# Gate preconditions — each fails with its own distinct message
# =============================================================================


def test_gate_precondition_marketplace_is_plan_marshall():
    """GATE: the tree under test is the plan-marshall marketplace.

    discover_plugin_modules() early-returns [] for any other tree, which would
    make every downstream assertion in this module pass over an empty map.
    """
    assert _is_plan_marshall_marketplace(str(PROJECT_ROOT)), (
        f'GATE FAILED: {PROJECT_ROOT} is not the plan-marshall marketplace '
        '(marketplace/.claude-plugin/marketplace.json name != "plan-marshall"). '
        'Every graph assertion in this module would pass vacuously.'
    )


def test_gate_precondition_discovery_returns_modules():
    """GATE: discovery yields a non-zero module count.

    A zero-module map would satisfy "no edges" trivially, so the module count is
    checked on its own before any edge claim is made.
    """
    modules = _pipeline()['modules']

    assert len(modules) > 0, (
        'GATE FAILED: discover_plugin_modules() returned zero modules for '
        f'{PROJECT_ROOT}. No edge assertion below carries meaning.'
    )


def test_gate_precondition_modules_carry_component_refs():
    """GATE: at least one module carries a non-empty component_refs field.

    The resolvers join over this field, so an empty field set across every
    module would make a zero-edge graph a materialization failure rather than a
    real answer.
    """
    derived_by_name = _pipeline()['derived_by_name']

    populated = [name for name, data in derived_by_name.items() if data.get('component_refs')]

    assert populated, (
        'GATE FAILED: no discovered module carries a populated component_refs '
        'field, so both resolvers would have nothing to join over.'
    )


# =============================================================================
# The resolver roster — three resolvers spanning both hierarchies
# =============================================================================


def test_three_resolvers_are_discovered():
    """The shipped roster is exactly markdown, maven, and python."""
    resolvers = _pipeline()['resolvers']

    assert sorted(record['id'] for record in resolvers) == EXPECTED_RESOLVER_IDS


def test_resolver_count_is_three():
    """resolver_count is the anti-vacuity numerator carried on every response."""
    assert len(_pipeline()['resolvers']) == 3


def test_every_resolver_reports_ok():
    """No resolver errored — an errored one would contribute zero edges silently."""
    reports = _pipeline()['reports']

    assert [report['status'] for report in reports] == ['ok'] * len(reports)


def test_resolver_set_spans_both_hierarchies():
    """The merged set covers Axis-A and Axis-B implementors.

    Scanning only one discovery path would silently hide every resolver on the
    other side, so the roster is asserted to straddle both.
    """
    ids = {record['id'] for record in _pipeline()['resolvers']}

    assert ids & AXIS_B_RESOLVER_IDS, 'no Axis-B (build-hierarchy) resolver in the roster'
    assert ids & AXIS_A_RESOLVER_IDS, 'no Axis-A (domain-hierarchy) resolver in the roster'


# =============================================================================
# The graph is non-empty and provenance-carrying
# =============================================================================


def test_impact_edge_set_is_non_empty():
    """The graph family answers from real derived edges, not an empty substrate."""
    assert _pipeline()['edges'], 'the merged edge set is empty for the plan-marshall marketplace'


def test_every_edge_carries_a_non_empty_producer_list():
    """No edge in any response is producer-less."""
    for edge in _pipeline()['edges']:
        assert edge['producers'], f'edge {edge["from"]} -> {edge["to"]} carries no producers'


def test_at_least_one_edge_is_produced_by_markdown_alone():
    """The markdown resolver contributes edges no other resolver found."""
    assert ['markdown'] in _producers_sets(_pipeline()['edges'])


def test_python_resolver_contributes_edges_to_the_graph():
    """The python resolver's id appears among the producers of real edges.

    Note the asymmetry with markdown above: on this tree the python resolver
    never produces an edge ALONE. Every module pair its import join derives is
    also derived by the markdown join, because a bundle whose Python imports a
    plan-marshall module invariably references that bundle in markdown too. Its
    contribution is therefore real but fully corroborated, and per-edge
    provenance is the only thing that makes it visible at all.
    """
    contributing = [edge for edge in _pipeline()['edges'] if 'python' in edge['producers']]

    assert contributing, 'the python resolver contributed no edge to the merged graph'


def test_python_resolver_reports_a_non_zero_edge_count():
    """The resolver's own report shows it derived edges, independent of collapse.

    edge_count is counted BEFORE the producer union, so it stays honest even
    when every one of this resolver's pairs is corroborated by a sibling and
    therefore invisible as an exclusively-python edge.
    """
    python_report = next(report for report in _pipeline()['reports'] if report['id'] == 'python')

    assert python_report['edge_count'] > 0


def test_every_python_edge_on_this_tree_is_corroborated_by_markdown():
    """Pins the subsumption above as a fact rather than leaving it implicit.

    If a future change made the python resolver derive a pair markdown cannot
    see, this test fails and the exclusively-python case becomes assertable —
    which is a finding, not a regression.
    """
    python_edges = [edge for edge in _pipeline()['edges'] if 'python' in edge['producers']]

    assert python_edges
    assert all(edge['producers'] == ['markdown', 'python'] for edge in python_edges)


def test_corroborated_edge_collapses_to_one_edge_with_both_producers():
    """A pair both Axis-A resolvers derive is ONE edge naming both, sorted.

    Two resolvers deriving the same module pair have not disagreed — they have
    independently corroborated — so the union collapses them and the edge keeps
    both producer ids.
    """
    edges = _pipeline()['edges']

    corroborated = [edge for edge in edges if edge['producers'] == ['markdown', 'python']]

    assert corroborated, (
        'no edge was derived by BOTH the markdown and python resolvers, so the '
        'producer-union collapse is not exercised against the live tree'
    )
    for edge in corroborated:
        assert edge['producers'] == sorted(edge['producers'])


def test_no_edge_is_a_self_edge():
    """The merge drops self-loops, which would corrupt traversal."""
    for edge in _pipeline()['edges']:
        assert edge['from'] != edge['to']


def test_both_endpoints_of_every_edge_are_known_modules():
    """A resolver cannot invent a node — endpoints are validated against discovery."""
    known = set(_pipeline()['derived_by_name'])

    for edge in _pipeline()['edges']:
        assert edge['from'] in known
        assert edge['to'] in known


# =============================================================================
# Byte-stability
# =============================================================================


def test_edge_list_is_byte_stable_across_two_runs():
    """Two independent merges over the same input produce identical output."""
    derived_by_name = _pipeline()['derived_by_name']
    resolvers = _pipeline()['resolvers']

    first, _ = _merge.merge_resolver_edges(resolvers, derived_by_name, {})
    second, _ = _merge.merge_resolver_edges(resolvers, derived_by_name, {})

    assert first == second


def test_edge_list_is_sorted_by_endpoint_pair():
    """Sorted output is what makes the byte-stability above meaningful."""
    edges = _pipeline()['edges']

    assert edges == sorted(edges, key=lambda edge: (edge['from'], edge['to']))


def test_component_refs_materialization_is_deterministic():
    """Re-running discovery yields an identical component_refs field."""
    first = _pipeline()['derived_by_name']
    second = {
        module['name']: module for module in discover_plugin_modules(str(PROJECT_ROOT))
    }

    assert {name: data['component_refs'] for name, data in first.items()} == {
        name: data['component_refs'] for name, data in second.items()
    }


# =============================================================================
# The anti-vacuity discriminator, asserted directly
# =============================================================================


def test_zero_resolvers_and_zero_findings_are_distinguishable():
    """`resolver_count: 0` and `resolver_count: N, edges: []` are different answers.

    The two states MUST be distinguishable without inspecting the edge list:
    the first is an absence of capability, the second a real, positive "N
    resolvers ran and found nothing".
    """
    derived_by_name = _pipeline()['derived_by_name']
    resolvers = _pipeline()['resolvers']

    no_resolver_edges, no_resolver_reports = _merge.merge_resolver_edges([], derived_by_name, {})
    ran_edges, ran_reports = _merge.merge_resolver_edges(resolvers, {}, {})

    # No resolver ran: empty report list is the discriminator.
    assert no_resolver_edges == []
    assert no_resolver_reports == []

    # N resolvers ran over an empty module map and legitimately found nothing.
    assert ran_edges == []
    assert len(ran_reports) == 3
    assert len(ran_reports) != len(no_resolver_reports)


def test_a_ran_and_found_nothing_response_still_names_its_resolvers():
    """The positive-zero answer carries the roster that produced it."""
    _edges, reports = _merge.merge_resolver_edges(_pipeline()['resolvers'], {}, {})

    assert sorted(report['id'] for report in reports) == EXPECTED_RESOLVER_IDS


# =============================================================================
# The collapse mechanism, proven independently of the live tree's contents
# =============================================================================


def test_collapse_mechanism_holds_over_a_controlled_module_map():
    """The same real resolvers and real merge collapse a corroborated pair.

    The live-tree assertion above proves the property holds for THIS project;
    this one proves the mechanism, so a tree that stopped containing a
    corroborated pair would not be mistaken for a broken union.
    """
    derived_by_name = {
        'alpha': {
            'component_refs': [
                {'target_bundle': 'beta', 'dep_type': 'skill', 'resolved': True},
                {'target_bundle': 'beta', 'dep_type': 'import', 'resolved': True},
            ]
        },
        'beta': {'component_refs': []},
    }
    resolvers = [
        record for record in _pipeline()['resolvers'] if record['id'] in AXIS_A_RESOLVER_IDS
    ]

    edges, reports = _merge.merge_resolver_edges(resolvers, derived_by_name, {})

    assert edges == [{'from': 'alpha', 'to': 'beta', 'producers': ['markdown', 'python']}]
    assert [report['edge_count'] for report in reports] == [1, 1]


def test_plugin_discover_exposes_the_materialization_helper():
    """The pipeline's first stage is a named, directly-testable seam."""
    assert callable(plugin_discover.build_component_refs)
