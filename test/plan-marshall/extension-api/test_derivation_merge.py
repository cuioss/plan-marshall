#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_derivation_merge.merge_resolver_edges()`` — the N-resolver union.

Loaded in-process via ``load_script_module`` (real filename → coverage counts).

The merge owns the provenance half of the Axis-C contract: core merges and stamps
producers, resolvers derive. The properties pinned here:

- Single-resolver passthrough.
- Two resolvers producing DISJOINT edges union to the sum.
- Two resolvers producing the SAME pair collapse to ONE edge with two sorted
  producers. This is the duplicate-**identity** case that stands in for the
  refuted conflict rule: the resolvers have corroborated, not disagreed, so no
  conflict resolution is expressible or needed.
- Self-edges and unknown-endpoint edges are dropped (a resolver cannot invent a
  node, and a module does not depend on itself).
- A raising resolver reports ``status: error`` with ``edge_count: 0`` while its
  siblings still contribute — one broken implementor never blanks the graph.
- A resolver emitting ``notes[]`` has them preserved on its report while
  ``status`` stays ``ok``; a resolver emitting none reports ``notes: []``.
- **Every merge-side drop is reported.** The three validity filters are core
  suppressing an edge, so each appends a ``merge:``-prefixed note to that
  resolver's report. The headline property: a resolver whose every candidate the
  merge discarded must NOT report ``status: ok`` / ``edge_count: 0`` /
  ``notes: []`` — that confident-looking zero is indistinguishable from "ran and
  legitimately found nothing", and is the vacuity the contract forbids.
- Edge ordering is deterministic across runs (sorted by ``(from, to)``).

Note on notes ordering: the implementation contract carries a resolver's
``notes`` onto its report **unchanged**, preserving the resolver's own intended
ordering rather than re-sorting it. The assertions below pin that unchanged
passthrough.
"""

from typing import Any

from conftest import load_script_module

_merge = load_script_module(
    'plan-marshall', 'extension-api', '_derivation_merge.py', 'derivation_merge'
)

# The known-module universe every test validates edge endpoints against.
_DERIVED: dict[str, dict] = {'core': {}, 'util': {}, 'api': {}}
_ENRICHED: dict = {}


class _StubResolver:
    """A resolver returning canned ``(edges, notes)``, or raising on demand."""

    def __init__(self, edges=None, notes=None, raises: bool = False):
        self._edges = edges if edges is not None else []
        self._notes = notes if notes is not None else []
        self._raises = raises
        self.calls: list[tuple[dict, dict]] = []

    def derive_edges(self, derived_by_name: dict, enriched_by_name: dict):
        self.calls.append((derived_by_name, enriched_by_name))
        if self._raises:
            raise RuntimeError('boom-derive-edges')
        return self._edges, self._notes


def _record(resolver_id: str, resolver: Any) -> dict[str, Any]:
    """Build a discovery-shaped ``{origin, id, module}`` record."""
    return {'origin': f'origin-{resolver_id}', 'id': resolver_id, 'module': resolver}


def _merge_with(*pairs: tuple[str, Any]):
    """Run the merge over ``(resolver_id, resolver)`` pairs."""
    records = [_record(rid, res) for rid, res in pairs]
    return _merge.merge_resolver_edges(records, _DERIVED, _ENRICHED)


# =============================================================================
# Null-on-absent
# =============================================================================


def test_zero_resolvers_returns_empty_edges_and_empty_reports():
    # Act
    edges, reports = _merge.merge_resolver_edges([], _DERIVED, _ENRICHED)

    # Assert — resolver_count 0 is distinguishable from "ran and found nothing"
    assert edges == []
    assert reports == []


def test_resolver_returning_no_edges_still_reports_ok():
    # Arrange
    resolver = _StubResolver(edges=[])

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert — N resolvers ran and found nothing: a real, positive answer
    assert edges == []
    assert reports == [{'id': 'maven', 'edge_count': 0, 'status': 'ok', 'notes': []}]


# =============================================================================
# Single-resolver passthrough
# =============================================================================


def test_single_resolver_passthrough():
    # Arrange
    resolver = _StubResolver(edges=[('core', 'util')])

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]
    assert reports == [{'id': 'maven', 'edge_count': 1, 'status': 'ok', 'notes': []}]


def test_resolver_receives_both_prelaoded_maps():
    # Arrange
    resolver = _StubResolver()

    # Act
    _merge_with(('maven', resolver))

    # Assert — the resolver is a pure function of its arguments
    assert resolver.calls == [(_DERIVED, _ENRICHED)]


# =============================================================================
# N-resolver union
# =============================================================================


def test_disjoint_edges_from_two_resolvers_union_to_the_sum():
    # Arrange
    a = _StubResolver(edges=[('core', 'util')])
    b = _StubResolver(edges=[('api', 'core')])

    # Act
    edges, reports = _merge_with(('maven', a), ('python', b))

    # Assert — union, sorted by (from, to)
    assert edges == [
        {'from': 'api', 'to': 'core', 'producers': ['python']},
        {'from': 'core', 'to': 'util', 'producers': ['maven']},
    ]
    assert [rec['edge_count'] for rec in reports] == [1, 1]


def test_same_pair_from_two_resolvers_collapses_to_one_edge_with_two_producers():
    # Arrange — the duplicate-IDENTITY case: corroboration, not conflict
    a = _StubResolver(edges=[('core', 'util')])
    b = _StubResolver(edges=[('core', 'util')])

    # Act — supplied markdown-then-maven so the producer sort is observable
    edges, reports = _merge_with(('markdown', a), ('maven', b))

    # Assert — ONE edge, both producers, sorted
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['markdown', 'maven']}]
    # Both resolvers are credited with having contributed the pair
    assert [rec['edge_count'] for rec in reports] == [1, 1]


def test_producers_are_sorted_regardless_of_resolver_order():
    # Arrange — supplied in reverse alphabetical order
    a = _StubResolver(edges=[('core', 'util')])
    b = _StubResolver(edges=[('core', 'util')])

    # Act
    edges, _ = _merge_with(('zeta', a), ('alpha', b))

    # Assert
    assert edges[0]['producers'] == ['alpha', 'zeta']


def test_duplicate_pair_within_one_resolver_counts_once():
    # Arrange — a resolver emitting the same pair twice
    resolver = _StubResolver(edges=[('core', 'util'), ('core', 'util')])

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert — union is idempotent
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]
    assert reports[0]['edge_count'] == 1


# =============================================================================
# Validity filters
# =============================================================================


def test_self_edges_are_dropped():
    # Arrange
    resolver = _StubResolver(edges=[('core', 'core'), ('core', 'util')])

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]
    assert reports[0]['edge_count'] == 1


def test_edges_with_unknown_endpoints_are_dropped():
    # Arrange — 'ghost' is absent from the known-module universe
    resolver = _StubResolver(
        edges=[('core', 'ghost'), ('ghost', 'core'), ('core', 'util')]
    )

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert — a resolver cannot invent a node
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]
    assert reports[0]['edge_count'] == 1


def test_malformed_pairs_are_dropped():
    # Arrange — wrong arity, wrong types, and a bare string
    resolver = _StubResolver(
        edges=[('core',), ('core', 'util', 'extra'), (1, 2), 'core-util', ('core', 'util')]
    )

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]
    assert reports[0]['edge_count'] == 1


def test_list_shaped_pairs_are_accepted():
    # Arrange — a resolver returning lists rather than tuples
    resolver = _StubResolver(edges=[['core', 'util']])

    # Act
    edges, _ = _merge_with(('maven', resolver))

    # Assert
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]


# =============================================================================
# Error isolation
# =============================================================================


def test_raising_resolver_reports_error_while_siblings_contribute():
    # Arrange
    broken = _StubResolver(raises=True)
    healthy = _StubResolver(edges=[('core', 'util')])

    # Act
    edges, reports = _merge_with(('broken', broken), ('maven', healthy))

    # Assert — the merge is never aborted by one broken implementor
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]

    broken_report = next(rec for rec in reports if rec['id'] == 'broken')
    assert broken_report['status'] == 'error'
    assert broken_report['edge_count'] == 0
    assert broken_report['notes'] != []

    maven_report = next(rec for rec in reports if rec['id'] == 'maven')
    assert maven_report['status'] == 'ok'
    assert maven_report['edge_count'] == 1


def test_errored_resolver_contributes_no_producers():
    # Arrange
    broken = _StubResolver(raises=True)

    # Act
    edges, _ = _merge_with(('broken', broken))

    # Assert
    assert edges == []


def test_record_missing_its_module_is_reported_as_error():
    # Arrange — a malformed discovery record
    records: list[dict[str, Any]] = [{'origin': 'x', 'id': 'broken'}]

    # Act
    edges, reports = _merge.merge_resolver_edges(records, _DERIVED, _ENRICHED)

    # Assert — same error report shape, merge still returns
    assert edges == []
    assert reports[0]['id'] == 'broken'
    assert reports[0]['status'] == 'error'
    assert reports[0]['edge_count'] == 0


# =============================================================================
# Suppression reporting (notes[])
# =============================================================================


def test_notes_are_preserved_on_the_report_with_status_ok():
    # Arrange — the ambiguous-coordinate case: an edge suppressed, and reported
    notes = ['ambiguous coordinate g:a claimed by core and util', 'unresolvable ref x']
    resolver = _StubResolver(edges=[('core', 'util')], notes=notes)

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert — suppression is visible, and a suppressed edge is not an error
    assert reports == [
        {'id': 'maven', 'edge_count': 1, 'status': 'ok', 'notes': notes}
    ]
    assert edges == [{'from': 'core', 'to': 'util', 'producers': ['maven']}]


def test_notes_are_carried_unchanged_not_resorted():
    # Arrange — deliberately non-alphabetical, to pin passthrough over re-sorting
    notes = ['zeta condition', 'alpha condition']
    resolver = _StubResolver(notes=notes)

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — the resolver's own ordering survives
    assert reports[0]['notes'] == ['zeta condition', 'alpha condition']


def test_resolver_emitting_no_notes_reports_empty_list():
    # Arrange
    resolver = _StubResolver(edges=[('core', 'util')])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — shape-identical to a resolver that cannot emit notes
    assert reports[0]['notes'] == []


def test_notes_emitted_by_a_zero_edge_resolver_are_still_reported():
    # Arrange — every candidate edge suppressed
    resolver = _StubResolver(edges=[], notes=['all coordinates ambiguous'])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — the condition must be visible even with zero edges
    assert reports[0]['edge_count'] == 0
    assert reports[0]['status'] == 'ok'
    assert reports[0]['notes'] == ['all coordinates ambiguous']


def test_bare_string_notes_value_is_normalized_to_a_list():
    # Arrange
    resolver = _StubResolver(notes='single condition')

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert
    assert reports[0]['notes'] == ['single condition']


# =============================================================================
# Merge-side suppression reporting — core's own drops must be legible
# =============================================================================


def _merge_notes(report: dict) -> list[str]:
    """Return only the notes the MERGE appended, not the resolver's own."""
    return [note for note in report['notes'] if note.startswith('merge: ')]


def test_dropped_self_edge_is_reported_in_notes():
    # Arrange
    resolver = _StubResolver(edges=[('core', 'core')])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — the drop is visible, and names the edge that was dropped
    notes = _merge_notes(reports[0])
    assert len(notes) == 1
    assert 'self-edge' in notes[0]
    assert 'core' in notes[0]


def test_dropped_unknown_endpoint_edge_is_reported_in_notes():
    # Arrange — 'ghost' is absent from the known-module universe
    resolver = _StubResolver(edges=[('core', 'ghost')])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — the note names the endpoint that was not known
    notes = _merge_notes(reports[0])
    assert len(notes) == 1
    assert 'ghost' in notes[0]


def test_note_for_unknown_endpoints_names_both_when_both_are_unknown():
    # Arrange
    resolver = _StubResolver(edges=[('ghost', 'phantom')])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert
    note = _merge_notes(reports[0])[0]
    assert 'ghost' in note
    assert 'phantom' in note


def test_dropped_malformed_pair_is_reported_in_notes():
    # Arrange — wrong arity, wrong types, and a bare string
    resolver = _StubResolver(edges=[('core',), (1, 2), 'core-util'])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — one note per discarded candidate
    assert len(_merge_notes(reports[0])) == 3


def test_resolver_whose_every_edge_was_dropped_does_not_report_a_silent_zero():
    # Arrange — the headline vacuity case: candidates produced, all discarded
    resolver = _StubResolver(edges=[('core', 'core'), ('core', 'ghost'), ('bad',)])

    # Act
    edges, reports = _merge_with(('maven', resolver))

    # Assert — a zero edge_count is only trustworthy when the drops are legible
    assert edges == []
    assert reports[0]['edge_count'] == 0
    assert reports[0]['status'] == 'ok'
    assert reports[0]['notes'] != []
    assert len(_merge_notes(reports[0])) == 3


def test_merge_notes_are_distinguishable_from_the_resolvers_own_notes():
    # Arrange — the resolver reports one condition; the merge drops one edge
    resolver = _StubResolver(
        edges=[('core', 'core'), ('core', 'util')],
        notes=['ambiguous coordinate g:a claimed by core and util'],
    )

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — both channels survive, and the prefix separates them
    all_notes = reports[0]['notes']
    assert all_notes[0] == 'ambiguous coordinate g:a claimed by core and util'
    assert len(_merge_notes(reports[0])) == 1
    assert len(all_notes) == 2


def test_clean_merge_appends_no_merge_notes():
    # Arrange — every candidate is valid
    resolver = _StubResolver(edges=[('core', 'util'), ('api', 'core')])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — the drop channel stays silent when nothing was dropped
    assert reports[0]['notes'] == []


def test_merge_notes_are_attributed_to_the_resolver_that_produced_the_candidate():
    # Arrange — only one of two resolvers emits a droppable candidate
    dropper = _StubResolver(edges=[('core', 'ghost')])
    clean = _StubResolver(edges=[('core', 'util')])

    # Act
    _, reports = _merge_with(('maven', dropper), ('python', clean))

    # Assert — the note rides the offending resolver's report, not its sibling's
    by_id = {rec['id']: rec for rec in reports}
    assert len(_merge_notes(by_id['maven'])) == 1
    assert by_id['python']['notes'] == []


def test_dropped_candidates_do_not_inflate_edge_count():
    # Arrange — one valid edge among three dropped candidates
    resolver = _StubResolver(edges=[('core', 'core'), ('core', 'ghost'), ('core', 'util')])

    # Act
    _, reports = _merge_with(('maven', resolver))

    # Assert — edge_count still counts only what survived
    assert reports[0]['edge_count'] == 1
    assert len(_merge_notes(reports[0])) == 2


# =============================================================================
# Determinism
# =============================================================================


def test_edge_ordering_is_deterministic_across_runs():
    # Arrange — supplied in a scrambled order
    scrambled = [('core', 'util'), ('api', 'core'), ('util', 'api'), ('api', 'util')]
    expected = [
        ('api', 'core'),
        ('api', 'util'),
        ('core', 'util'),
        ('util', 'api'),
    ]

    # Act — two independent merges over the same input
    first, _ = _merge_with(('maven', _StubResolver(edges=list(scrambled))))
    second, _ = _merge_with(('maven', _StubResolver(edges=list(reversed(scrambled)))))

    # Assert — byte-stable output, independent of resolver emission order
    assert [(e['from'], e['to']) for e in first] == expected
    assert first == second


def test_reports_follow_the_supplied_resolver_order():
    # Arrange
    a = _StubResolver(edges=[('core', 'util')])
    b = _StubResolver(edges=[('api', 'core')])

    # Act
    _, reports = _merge_with(('zeta', a), ('alpha', b))

    # Assert — reports mirror the (already id-sorted) discovery order handed in
    assert [rec['id'] for rec in reports] == ['zeta', 'alpha']
