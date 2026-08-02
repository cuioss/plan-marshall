#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end proof that the graph family answers from derived edges.

Runs the whole shipped pipeline against the plan-marshall marketplace itself —
real module discovery, real resolver discovery over both hierarchies, the real
core merge, AND the real consumer that turns merged edges into a graph — so the
claim under test is "the graph is non-vacuous for this project", not "the seam
would work if something fed it".

The pipeline exercised here is:

``discover_plugin_modules()`` (materializes ``component_refs``)
→ ``discover_derivation_resolvers()`` (spans Axis-A and Axis-B)
→ ``merge_resolver_edges()`` (validates, unions, stamps provenance)
→ ``get_module_graph()`` (applies declared-vs-derived precedence, then layers)

**The last stage is load-bearing, not decorative.** Stopping at
``merge_resolver_edges`` proved only that edges were PRODUCED. The declared-wins
precedence branch in ``get_module_graph`` runs AFTER the merge and can discard
every one of them, which is exactly what shipped: an empty
``internal_dependencies`` stub read as a declaration, so all 29 merged edges were
thrown away while each resolver still reported ``status: ok`` with a positive
``edge_count``. A merge-level assertion is structurally incapable of seeing that.
The enriched overlay below therefore carries the empty-list declaration
``architecture init`` seeds into every module, so the discarding condition exists
in the fixture rather than being excluded by an empty ``{}``.

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
_cmd_client = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client.py', 'cmd_client_graph_e2e'
)

EXPECTED_RESOLVER_IDS = ['markdown', 'maven', 'python']
"""The shipped resolver roster: one Axis-B implementor and two Axis-A ones.

This literal is the module's SINGLE executable pin, and it is deliberate. It is
consumed only by :func:`test_the_expected_resolver_roster_is_discovered` (which
asserts it against ``discover_derivation_resolvers()``) and by that assertion's
own count companion. Every other site that needs the roster derives it from the
discovery stage instead, so adding a resolver to the registry fails the pin —
the one place a human is meant to look — rather than silently leaving a copy of
the roster stale somewhere downstream. Deriving the pin too would make the whole
module vacuous: a registry that discovered nothing would satisfy a fully-derived
assertion set.
"""

# The axis-membership sets stay hand-written on purpose. Unlike the roster, axis
# membership is not carried on the discovered record — it is a class-hierarchy
# property (an Axis-B resolver is a BuildExtensionBase implementor), so deriving
# these would require isinstance checks against the build hierarchy. That is a
# materially larger refactor than the roster-duplication these constants sit
# next to, so they remain literals and are asserted as membership, not equality.
AXIS_B_RESOLVER_IDS = {'maven'}
AXIS_A_RESOLVER_IDS = {'markdown', 'python'}


# =============================================================================
# Cached pipeline — discovery walks the whole bundle tree, so it runs once
# =============================================================================

_PIPELINE: dict = {}


def _init_seeded_overlay(derived_by_name: dict) -> dict[str, dict]:
    """The enriched overlay ``architecture init`` seeds for every module.

    ``init`` writes ``"internal_dependencies": []`` into every module's
    enriched.json, so this IS the real overlay shape a live project carries. It
    is reproduced here rather than read off disk so the discarding condition is
    present deterministically — an overlay loaded from a tree whose
    ``.plan/architecture`` happens to be unmaterialized would collapse back to
    the ``{}`` blind spot this test exists to remove.
    """
    return {name: {'internal_dependencies': []} for name in derived_by_name}


def _pipeline() -> dict:
    """Run the real pipeline once and memoize its result for this module."""
    if not _PIPELINE:
        modules = discover_plugin_modules(str(PROJECT_ROOT))
        derived_by_name = {module['name']: module for module in modules}
        enriched_by_name = _init_seeded_overlay(derived_by_name)
        resolvers = _discovery.discover_derivation_resolvers()
        edges, reports = _merge.merge_resolver_edges(resolvers, derived_by_name, enriched_by_name)
        graph = _cmd_client.get_module_graph(
            str(PROJECT_ROOT),
            derived_by_name=derived_by_name,
            enriched_by_name=enriched_by_name,
        )
        _PIPELINE.update(
            modules=modules,
            derived_by_name=derived_by_name,
            enriched_by_name=enriched_by_name,
            resolvers=resolvers,
            edges=edges,
            reports=reports,
            graph=graph,
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
# The resolver roster — the shipped resolvers, spanning both hierarchies
# =============================================================================


def test_the_expected_resolver_roster_is_discovered():
    """The shipped roster is exactly the hand-written ``EXPECTED_RESOLVER_IDS`` pin."""
    resolvers = _pipeline()['resolvers']

    assert sorted(record['id'] for record in resolvers) == EXPECTED_RESOLVER_IDS


def test_resolver_count_matches_the_expected_roster():
    """resolver_count is the anti-vacuity numerator carried on every response.

    The expected size comes from ``EXPECTED_RESOLVER_IDS`` — the roster pinned
    and asserted above — rather than from a second literal that would have to be
    remembered and updated alongside it.
    """
    assert len(_pipeline()['resolvers']) == len(EXPECTED_RESOLVER_IDS)


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
# The MERGED GRAPH is non-empty — asserted at the consumer, past the discard site
# =============================================================================
#
# Every assertion in this block reads get_module_graph's output, so it covers the
# declared-vs-derived precedence branch in _build_deps_and_producers — the site
# that discards a module's resolver-derived edges. A merge-level assertion runs
# BEFORE that branch and cannot observe it.


def test_module_graph_edge_count_is_non_empty():
    """The graph the CLI answers from is non-empty, not merely the merge's output.

    This is the claim the merge-level check could not make: the edges must
    SURVIVE ``get_module_graph``'s declared-wins precedence branch, not just be
    produced by the resolvers.
    """
    graph = _pipeline()['graph']

    assert graph['graph']['edge_count'] > 0, (
        'get_module_graph returned zero edges for the plan-marshall marketplace — '
        'the resolvers produced edges and the consumer discarded them'
    )
    assert graph['edges'], 'the graph carries an edge_count but an empty edges list'


def test_empty_enriched_declaration_does_not_blank_the_graph():
    """The precise condition that shipped green: every module carries an empty
    ``internal_dependencies`` in its enriched overlay — the stub ``architecture
    init`` seeds — and the graph must STILL carry its resolver-derived edges.

    An empty container declares nothing, so it cannot suppress a derived edge.
    Before the meaning-guard fix this exact overlay reduced ``edge_count`` to 0.
    """
    pipeline = _pipeline()

    assert all(
        overlay['internal_dependencies'] == []
        for overlay in pipeline['enriched_by_name'].values()
    ), 'fixture drift: the overlay no longer carries the empty-declaration condition'
    assert pipeline['graph']['graph']['edge_count'] > 0


def test_at_least_one_graph_edge_is_stamped_by_a_resolver_not_declared():
    """At least one surviving edge carries resolver provenance, so the merged
    graph is not composed purely of declarations the precedence branch stamped.

    Deliberately existential, not universal: a declared edge and a cross-link
    edge are both legitimate members of the merged graph, so requiring EVERY
    edge to be resolver-stamped would assert something the contract does not
    promise. The claim that bites is that the resolver contribution survives
    the merge at all — which is exactly what the empty-declaration defect
    reduced to zero.

    The ids the producers are matched against come from the discovery stage,
    not from the roster literal: this assertion is about resolver provenance
    surviving the consumer, so it must follow whatever the registry actually
    yields rather than carry a second copy of the pin.
    """
    pipeline = _pipeline()
    resolver_ids = {record['id'] for record in pipeline['resolvers']}

    resolver_stamped = [
        edge for edge in pipeline['graph']['edges'] if set(edge['producers']) & resolver_ids
    ]

    assert resolver_stamped, (
        'no edge in the merged graph is stamped by a resolver — every surviving '
        'edge came from a declaration or a cross-link'
    )


def test_graph_response_names_the_resolvers_that_ran():
    """The anti-vacuity numerator rides all the way to the consumer's response.

    Both sides are derived rather than pinned, and the claim survives that:
    the expected ids come from the pipeline's ``discover_derivation_resolvers()``
    stage while the observed ids come from the independent ``get_module_graph()``
    call, so this remains a genuine cross-stage agreement check instead of a
    second copy of the roster literal.
    """
    pipeline = _pipeline()
    discovered_ids = sorted(record['id'] for record in pipeline['resolvers'])
    graph = pipeline['graph']

    assert graph['resolver_count'] == len(discovered_ids)
    assert sorted(report['id'] for report in graph['resolvers']) == discovered_ids


def test_merge_stage_produces_edges():
    """The MERGE stage produces edges — a strictly weaker claim than the graph
    assertions above, kept because it localises a failure to the producing stage
    rather than to the consumer."""
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
    enriched_by_name = _pipeline()['enriched_by_name']
    resolvers = _pipeline()['resolvers']

    first, _ = _merge.merge_resolver_edges(resolvers, derived_by_name, enriched_by_name)
    second, _ = _merge.merge_resolver_edges(resolvers, derived_by_name, enriched_by_name)

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
    assert len(ran_reports) == len(EXPECTED_RESOLVER_IDS)
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
