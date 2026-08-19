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

These two are the gate-relative edges. A SECOND family is artifact-level: a step declares
``reads: [X]`` for the run artifacts it consumes and ``destroys: [X]`` for those it
renders unavailable to later steps, and pairing the two derives a **read-before-destroy**
edge — the defect a bare integer cannot express, since a step legally numbered after a
``destroys`` step still reads a destroyed input.

That family used to be empty, and this module asserted its emptiness as the honest
statement of the floor. It is no longer empty, so the assertion has been re-measured into
the derivation itself. One half of it remains below the floor and is still stated as such:
there is **no** producer-side marker, so read-BEFORE-produce is not derivable —
``reads: [metrics]`` is paired against ``record-metrics`` only by a human reading the
prose.

A THIRD, non-gate-relative edge family is derived at the end of this module: a
**named-step adjacency** that no marker expresses, because its producer→consumer relation
is a data dependency between three specific steps rather than a property either of them
declares. ``project:finalize-step-era-stamp-fill`` resolves the ``PR-PENDING`` era-stamp
sentinel to the real PR number, so it can only run once ``default:create-pr`` has produced
that number, and it must run before ``default:ci-verify`` validates the tree that carries
the correction. That is an ordering obligation stated in prose in the step's own doc and,
until this module derived it, asserted nowhere.

The population is DERIVED from discovery, never hardcoded — a step added later is
covered automatically — and this module deliberately asserts **no cardinality literal**:
a hardcoded count is precisely the drift shape this plan removes. The cardinality is
instead pinned to its own derivation (edges == the marker-carrying step count), and the
coverage is asserted to be a strict FLOOR (marker-carrying steps are a proper subset of
all finalize steps, and the producer-side vocabulary is empty).

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

#: The artifact-level data-edge vocabulary. ``reads`` names the artifacts a step
#: consumes; ``destroys`` names the artifacts it renders unavailable to every later
#: step. Contract: extension-api/standards/finalize-step-order-bands.md
#: § "`reads` and `destroys`".
_READS_MARKER = 'reads'
_DESTROYS_MARKER = 'destroys'

#: Consumer-side markers that still do NOT exist in the vocabulary. ``reads`` was
#: removed from this list when the first steps declared it — the honest widening the
#: floor assertion was written to force. The remaining names are the spellings a
#: future plan might introduce; if one lands, the floor widens again and this list is
#: what a maintainer updates.
_ABSENT_CONSUMER_MARKERS = ('consumes', 'reads_artifacts', 'consumes_artifacts')


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


def test_no_other_consumer_side_marker_spelling_has_appeared():
    """The consumer side is spelled ``reads`` and nothing else.

    ``reads`` used to be on this list, and the floor this module measured was
    gate-relative BECAUSE the artifact-level consumer vocabulary was empty. Steps now
    declare it, so the floor has widened and the artifact-edge assertions below are what
    measure the widened part. What this test still guards is that a SECOND spelling has
    not appeared alongside it — two names for the consumer side would split the
    derivation, and the half spelled the other way would be silently unchecked.
    """
    declarers = []
    for record in _finalize_records():
        doc_path = Path(record['path'])
        fields = extension_discovery._read_frontmatter_fields(doc_path, _ABSENT_CONSUMER_MARKERS)
        present = [key for key in _ABSENT_CONSUMER_MARKERS if key in fields]
        if present:
            declarers.append(f"{record.get('name')}: {present}")
    assert not declarers, (
        'A finalize step declared a consumer-side marker under a spelling other than '
        f'`{_READS_MARKER}`. Two names for one concept split the derivation below, so '
        'either rename the declaration or fold the new spelling into the artifact-edge '
        f'derivation: {declarers}'
    )


def _artifact_lists(doc_path: Path, key: str) -> list[str]:
    """One step's declared artifact tokens for ``key``, normalized to a list."""
    fields = extension_discovery._read_frontmatter_fields(doc_path, (key,))
    value = fields.get(key)
    if not value:
        return []
    return [str(item) for item in (value if isinstance(value, list) else [value])]


def derive_artifact_edges() -> list[dict]:
    """Derive read-before-destroy edges from the ``reads`` / ``destroys`` vocabulary.

    For every artifact token a step declares under ``reads``, pair it with each step
    that declares the same token under ``destroys``. The edge asserts the reader runs
    strictly BEFORE the destroyer: a step legally numbered after a ``destroys`` step
    still reads a destroyed input, which is precisely the defect a bare integer cannot
    express.

    This is the artifact-level data edge the gate-relative derivation above cannot see —
    it is not a marker on the merge gate, it is a dependency between two named steps
    mediated by a shared artifact token.
    """
    reads: list[tuple[str, int, str]] = []
    destroys: list[tuple[str, int, str]] = []
    for record in _finalize_records():
        name, order = record.get('name'), record.get('order')
        if not isinstance(order, int):
            continue
        doc_path = Path(record['path'])
        for artifact in _artifact_lists(doc_path, _READS_MARKER):
            reads.append((str(name), order, artifact))
        for artifact in _artifact_lists(doc_path, _DESTROYS_MARKER):
            destroys.append((str(name), order, artifact))

    return [
        {
            'reader': r_name,
            'reader_order': r_order,
            'destroyer': d_name,
            'destroyer_order': d_order,
            'artifact': artifact,
        }
        for r_name, r_order, artifact in reads
        for d_name, d_order, d_artifact in destroys
        if d_artifact == artifact
    ]


def test_artifact_edge_set_is_derived_and_non_empty():
    """The artifact-edge derivation resolves something, so the gate below is not vacuous."""
    assert derive_artifact_edges(), (
        f'No finalize step pairs a `{_READS_MARKER}` token with a matching '
        f'`{_DESTROYS_MARKER}` token, so the read-before-destroy assertion below has '
        f'nothing to check. Either no step declares an artifact dependency, or every '
        f'declared `{_READS_MARKER}` token names an artifact nothing destroys.'
    )


def test_every_reader_runs_before_the_step_that_destroys_what_it_reads():
    """GATE: a step never reads an artifact a lower-ordered step has destroyed."""
    offenders = [
        f"{e['reader']} (order {e['reader_order']}) reads {e['artifact']!r}, which "
        f"{e['destroyer']} (order {e['destroyer_order']}) destroys"
        for e in derive_artifact_edges()
        if e['reader_order'] >= e['destroyer_order']
    ]
    assert not offenders, (
        'These steps are ordered at or after the step that destroys an artifact they '
        f'declare they read, so the input is gone by the time they run: {offenders}'
    )


def test_every_declared_read_token_is_a_known_artifact():
    """A `reads` token must name an artifact the vocabulary knows.

    The vocabulary is small and shared on purpose: a producer's output and a consumer's
    ``reads`` have to refer to the SAME token or the pairing above silently finds no
    edge — a typo would make the read-before-destroy gate vacuous for that step while
    every assertion stayed green.
    """
    known = {artifact for _n, _o, artifact in [
        (r.get('name'), r.get('order'), a)
        for r in _finalize_records()
        for a in _artifact_lists(Path(r['path']), _DESTROYS_MARKER)
    ]} | {'metrics'}

    offenders = []
    for record in _finalize_records():
        for artifact in _artifact_lists(Path(record['path']), _READS_MARKER):
            if artifact not in known:
                offenders.append(f"{record.get('name')}: {artifact!r}")

    assert not offenders, (
        f'These steps declare a `{_READS_MARKER}` token that matches no `'
        f'{_DESTROYS_MARKER}` declaration and is not a known produced artifact, so the '
        f'read-before-destroy pairing finds no edge for them and the gate is vacuous '
        f'there. Known tokens: {sorted(known)}. Offenders: {offenders}'
    )


def test_the_producer_side_is_still_undeclared_below_the_floor():
    """No step declares which artifact it PRODUCES — that half stays below the floor.

    ``reads`` and ``destroys`` make read-after-destroy checkable. Read-BEFORE-produce is
    not: there is no ``produces`` marker, so ``reads: [metrics]`` is paired against
    ``record-metrics`` only by a human reading the prose. Stating that plainly is what
    keeps this module's coverage claim honest rather than implying the artifact-level
    derivation is now complete.
    """
    declarers = []
    for record in _finalize_records():
        fields = extension_discovery._read_frontmatter_fields(
            Path(record['path']), ('produces', 'emits', 'produces_artifacts')
        )
        if fields:
            declarers.append(f"{record.get('name')}: {sorted(fields)}")
    assert not declarers, (
        'A finalize step declared a producer-side artifact marker. The read-before-produce '
        'direction is now derivable and this module should derive it rather than reporting '
        f'it as below the floor: {declarers}'
    )


# ---------------------------------------------------------------------------
# The named-step adjacency edge — a data dependency no marker expresses
# ---------------------------------------------------------------------------

#: The era-stamp adjacency's three steps, in the order they must run. The obligation is
#: stated in ``.claude/skills/finalize-step-era-stamp-fill/SKILL.md``: the step resolves
#: the ``PR-PENDING`` sentinel to the real PR number, so it needs the PR ``create-pr``
#: opens, and the correction must be on the branch before ``ci-verify`` reads it.
_PR_PRODUCER = 'default:create-pr'
_ERA_STAMP_STEP = 'project:finalize-step-era-stamp-fill'
_CI_CONSUMER = 'default:ci-verify'


def _order_of(step_name: str) -> int:
    """Read one discovered step's ``order`` off the registry, never a literal."""
    for record in _finalize_records():
        if record.get('name') == step_name:
            order = record.get('order')
            assert isinstance(order, int), (
                f'{step_name} was discovered but its frontmatter ``order`` is '
                f'{order!r}, not an int, so no ordering assertion can read it.'
            )
            return order
    raise AssertionError(
        f'{step_name} is not among the discovered {_EXT_POINT} implementors, so the '
        f'era-stamp adjacency assertion has nothing to read and would pass vacuously.'
    )


def test_era_stamp_fill_runs_between_pr_creation_and_ci_verification():
    """The era-stamp step's order lies STRICTLY between create-pr's and ci-verify's.

    ``project:finalize-step-era-stamp-fill`` rewrites the ``PR-PENDING`` era-stamp
    sentinel to this plan's real PR number and pushes the correction onto the feature
    branch. Both bounds are load-bearing and neither is expressed by any frontmatter
    marker:

    - **After ``default:create-pr``** — the PR number does not exist until the PR is
      opened, so an earlier order leaves the step with nothing but a guess, which is the
      guessed-number defect the sentinel was introduced to remove.
    - **Before ``default:ci-verify``** — the rewritten ``audit.py`` and its test mirror
      must be on the branch before CI reads the tree, or CI verifies a tree the merge
      will not contain.

    Every order is READ from discovery, so moving any of the three steps moves the
    obligation with it and no literal here goes stale.
    """
    pr_order = _order_of(_PR_PRODUCER)
    era_order = _order_of(_ERA_STAMP_STEP)
    ci_order = _order_of(_CI_CONSUMER)

    assert pr_order < era_order < ci_order, (
        f'{_ERA_STAMP_STEP} (order {era_order}) must run strictly after '
        f'{_PR_PRODUCER} (order {pr_order}) — the PR number it resolves the PR-PENDING '
        f'sentinel to does not exist before then — and strictly before {_CI_CONSUMER} '
        f'(order {ci_order}), so the rewritten era stamp is on the branch CI reads.'
    )
