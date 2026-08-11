#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""D1 — derive the finalize-step producer→consumer ORDERING edges from the declared
markers, publish the edge cardinality, and state the enumeration coverage as a FLOOR.

The plan's root observation is that a finalize step's ``order:`` determines what it can
*see*, yet the producer→consumer dependency the ordering must satisfy is declared only
partially. This module DERIVES the edge set that IS declarable from step frontmatter and
makes its coverage honest:

- A ``mutates_source: true`` step must run BEFORE the merge gate (its edit is only
  pushable while the branch is open) — a derived edge ``step → gate``.
- A ``post_run_review: true`` step must run AFTER the merge gate (its evidence is only
  produced at/after that gate) — a derived edge ``gate → step``.

These two are the gate-relative producer→consumer edges the CURRENT frontmatter
vocabulary expresses. The CONSUMER side of an artifact-level *data* edge — WHICH
artifact a step READS — has **no** frontmatter marker at all, so a data dependency like
R1 (``lessons-housekeeping`` reads the retrospective's report) or R2 (the retrospective
reads the closed metrics accumulator) is **below this floor** and invisible to any
frontmatter derivation. That undeclared-edge gap is the defect the plan addresses; this
module measures the floor honestly rather than asserting a coverage it does not have.

The population is DERIVED from discovery, never hardcoded — a step added later is
covered automatically — and this module deliberately asserts **no cardinality literal**:
a hardcoded count is precisely the drift shape this plan removes. The cardinality is
instead pinned to its own derivation (edges == the marker-carrying step count), and the
coverage is asserted to be a strict FLOOR (marker-carrying steps are a proper subset of
all finalize steps, and the consumer-side vocabulary is empty).

D5 note: this test IS the derivation-level observation the plan requires — it runs
inside the normal ``./pw verify`` gate, so it is observable from inside a run even
though the run's own frozen manifest executes the OLD order.
"""

from __future__ import annotations

from pathlib import Path

import extension_discovery
from extension_discovery import find_implementors

#: The canonical ext-point whose implementors are the finalize steps.
_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'

#: The merge gate. Its order is the ordering threshold, read off discovery.
_MERGE_GATE = 'default:branch-cleanup'

#: The two markers that express a gate-relative producer→consumer ordering edge.
_BEFORE_GATE_MARKER = 'mutates_source'  # true ⇒ step must run BEFORE the gate
_AFTER_GATE_MARKER = 'post_run_review'  # true ⇒ step must run AFTER the gate

#: Consumer-side artifact-read markers that DO NOT exist in the vocabulary. The floor
#: assertion proves the derivation cannot see an artifact-level data edge because no
#: step declares which artifact it reads. If a future plan introduces one of these, the
#: floor widens and this list is what a maintainer updates.
_ABSENT_CONSUMER_MARKERS = ('reads', 'consumes', 'reads_artifacts', 'consumes_artifacts')


def _declares_true(doc_path: Path, key: str) -> bool:
    """Read one boolean fact off a discovered step doc via the registry's own parser."""
    fields = extension_discovery._read_frontmatter_fields(doc_path, (key,))
    return bool(fields.get(key, False))


def _finalize_records() -> list[dict]:
    return list(find_implementors(_EXT_POINT))


def _merge_gate_order() -> int | None:
    for record in _finalize_records():
        if record.get('name') == _MERGE_GATE:
            order = record.get('order')
            return order if isinstance(order, int) else None
    return None


def derive_ordering_edges() -> list[dict]:
    """Derive the gate-relative producer→consumer ordering edges from step frontmatter.

    Each edge is ``{producer, producer_order, consumer, consumer_order, marker}``. A
    ``mutates_source: true`` step contributes ``step → gate``; a ``post_run_review: true``
    step contributes ``gate → step``. The gate itself contributes no edge.
    """
    gate_order = _merge_gate_order()
    edges: list[dict] = []
    for record in _finalize_records():
        name = record.get('name')
        order = record.get('order')
        if name == _MERGE_GATE or not isinstance(order, int) or gate_order is None:
            continue
        doc_path = Path(record['path'])
        if _declares_true(doc_path, _BEFORE_GATE_MARKER):
            edges.append({
                'producer': name,
                'producer_order': order,
                'consumer': _MERGE_GATE,
                'consumer_order': gate_order,
                'marker': _BEFORE_GATE_MARKER,
            })
        if _declares_true(doc_path, _AFTER_GATE_MARKER):
            edges.append({
                'producer': _MERGE_GATE,
                'producer_order': gate_order,
                'consumer': name,
                'consumer_order': order,
                'marker': _AFTER_GATE_MARKER,
            })
    return edges


def _marker_carrying_step_count() -> int:
    """Count finalize steps (excluding the gate) carrying at least one edge marker."""
    count = 0
    for record in _finalize_records():
        if record.get('name') == _MERGE_GATE:
            continue
        doc_path = Path(record['path'])
        if _declares_true(doc_path, _BEFORE_GATE_MARKER) or _declares_true(
            doc_path, _AFTER_GATE_MARKER
        ):
            count += 1
    return count


def test_merge_gate_is_discoverable():
    """The ordering threshold is READ from discovery, so the edge derivation is non-vacuous."""
    assert _merge_gate_order() is not None, (
        f'{_MERGE_GATE} was not found among the discovered {_EXT_POINT} implementors, '
        'so no merge-gate order could be resolved and every derived edge would be '
        'vacuous.'
    )


def test_edge_set_is_derived_and_non_empty():
    """The derivation resolves a non-empty edge set — every later assertion depends on it."""
    edges = derive_ordering_edges()
    assert edges, (
        'The gate-relative ordering-edge derivation returned an EMPTY set. Either no '
        f'finalize step declares {_BEFORE_GATE_MARKER}: true or {_AFTER_GATE_MARKER}: '
        f'true, or find_implementors({_EXT_POINT!r}) discovered no step docs.'
    )


def test_every_derived_edge_is_order_satisfied():
    """GATE: every derived producer→consumer edge runs producer-before-consumer.

    A ``mutates_source: true`` step ordered at/after the gate, or a
    ``post_run_review: true`` step ordered at/before it, is a violated edge — the exact
    ordering defect the plan's derivation exists to surface. The threshold is READ from
    the discovered gate record, so moving the gate moves the obligation with it, and the
    population is the DERIVED set, so a step added later is covered with no edit here.
    """
    offenders = [
        f"{e['producer']} (order {e['producer_order']}) → {e['consumer']} "
        f"(order {e['consumer_order']}) [{e['marker']}]"
        for e in derive_ordering_edges()
        if e['producer_order'] >= e['consumer_order']
    ]
    assert not offenders, (
        'These derived producer→consumer ordering edges are violated (producer is not '
        f'strictly before consumer): {offenders}'
    )


def test_edge_cardinality_equals_its_own_derivation_no_literal():
    """The edge cardinality is pinned to its derivation, never to a hardcoded count.

    Every marker-carrying step contributes exactly one gate edge (the two markers are
    mutually exclusive, so a step carries at most one), so the edge count MUST equal the
    marker-carrying step count. Asserting that equality — rather than a literal — is what
    keeps this a derivation instead of a drift-prone tally.
    """
    edges = derive_ordering_edges()
    assert len(edges) == _marker_carrying_step_count(), (
        f'Derived edge count ({len(edges)}) disagrees with the marker-carrying step '
        f'count ({_marker_carrying_step_count()}). Because mutates_source and '
        'post_run_review are mutually exclusive, each marker-carrying step contributes '
        'exactly one gate edge, so the two counts must match.'
    )


def test_coverage_is_a_floor_marker_carrying_steps_are_a_proper_subset():
    """The enumeration coverage is a FLOOR: not every finalize step carries an edge marker.

    Most finalize steps (push, create-pr, ci-verify, …) declare neither marker, so the
    derived edge set covers only a subset of the pipeline. Stating coverage as a floor —
    marker-carrying steps ⊊ all finalize steps — is the plan's D1 requirement.
    """
    total = len([r for r in _finalize_records() if r.get('name') != _MERGE_GATE])
    covered = _marker_carrying_step_count()
    assert total > 0, 'No finalize steps were discovered.'
    assert 0 < covered < total, (
        f'Expected the marker-carrying steps ({covered}) to be a PROPER, non-empty subset '
        f'of all finalize steps ({total}) — a coverage FLOOR. A full or empty coverage '
        'would mean the derivation is not measuring a floor at all.'
    )


def test_consumer_side_data_edges_are_undeclared_below_the_floor():
    """No finalize step declares WHICH artifact it reads — the consumer side is undeclared.

    This is the mechanical statement of the plan's root defect: the derivation can only
    see gate-relative edges because the artifact-level *consumer* vocabulary is empty. A
    data dependency like R1/R2 therefore sits BELOW this floor. If a future plan adds a
    ``reads``/``consumes`` marker, this test fails and the floor is re-measured — the
    honest way to widen coverage.
    """
    declarers = []
    for record in _finalize_records():
        doc_path = Path(record['path'])
        fields = extension_discovery._read_frontmatter_fields(doc_path, _ABSENT_CONSUMER_MARKERS)
        present = [key for key in _ABSENT_CONSUMER_MARKERS if key in fields]
        if present:
            declarers.append(f"{record.get('name')}: {present}")
    assert not declarers, (
        'A finalize step declared a consumer-side artifact-read marker, which would widen '
        'the derivation past the gate-relative floor this test measures. Re-measure the '
        f'floor and update _ABSENT_CONSUMER_MARKERS: {declarers}'
    )
