#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Private helper owning the N-resolver edge merge for the Axis-C seam.

Core owns the merge, the provenance, and the traversal; it owns none of the
derivation. This module is that merge: it calls each discovered
``DerivationResolverBase`` implementor, validates and unions the edge sets, and
returns both the merged edges and a per-resolver report.

The union needs no conflict rule because none is expressible: an edge is an
unweighted ``(from, to)`` boolean, so union is idempotent and commutative. A pair
produced by more than one resolver has not created a disagreement — the resolvers
have independently corroborated — so the duplicates collapse to ONE edge carrying
every contributing resolver's id, which is exactly what the provenance contract
needs.

See ``extension-api/standards/ext-point-derivation-resolver.md`` for the complete
four-face contract, the N-resolver union semantics, and the anti-vacuity
provenance property this merge implements.
"""

from typing import Any

from plan_logging import log_entry

_STATUS_OK = 'ok'
_STATUS_ERROR = 'error'

#: Prefix marking a note the MERGE appended, distinguishing it from the notes the
#: resolver itself returned. Without the prefix a reader of the report cannot tell
#: whether the resolver suppressed the edge deliberately or the merge discarded it.
_MERGE_NOTE_PREFIX = 'merge: '


def _coerce_pair(candidate: Any) -> tuple[str, str] | None:
    """Return ``candidate`` as a ``(from, to)`` string pair, or ``None``.

    A resolver is an extension-contributed implementor, so its return value is
    validated rather than trusted: a pair that is not a two-element sequence of
    strings is dropped instead of propagating a malformed edge into the graph.
    """
    if isinstance(candidate, str) or not isinstance(candidate, (tuple, list)):
        return None
    if len(candidate) != 2:
        return None
    source, target = candidate
    if not isinstance(source, str) or not isinstance(target, str):
        return None
    return source, target


def _coerce_notes(candidate: Any) -> list[str]:
    """Return ``candidate`` as a list of note strings.

    ``notes[]`` is the required channel for any condition that suppressed an
    edge, so a malformed notes value is normalized rather than dropped silently:
    a bare string becomes a one-element list, and non-string items are rendered
    via ``str`` so the condition still reaches the report.
    """
    if candidate is None:
        return []
    if isinstance(candidate, str):
        return [candidate]
    if isinstance(candidate, (tuple, list)):
        return [item if isinstance(item, str) else str(item) for item in candidate]
    return [str(candidate)]


def merge_resolver_edges(
    resolvers: list[dict[str, Any]],
    derived_by_name: dict,
    enriched_by_name: dict,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge every resolver's edge set into one provenance-carrying edge list.

    Calls each resolver's ``derive_edges``, unpacking the ``(edges, notes)``
    return and carrying that resolver's ``notes`` onto its report. Each candidate
    pair must survive three validity filters before it is unioned:

    1. **The pair must be well-formed** — a candidate that is not a two-element
       sequence of strings is dropped rather than propagated into the graph.
    2. **Both endpoints must be known module names** — a pair naming a module
       absent from ``derived_by_name`` is dropped, so a resolver cannot invent a
       node.
    3. **Self-edges are dropped** — a module does not depend on itself, and a
       self-loop would corrupt traversal.

    **Every merge-side drop appends its own note.** The three filters above are
    the merge suppressing an edge, so each one records why, prefixed with
    ``merge:`` to keep it distinguishable from the notes the resolver itself
    returned. Without that, a resolver whose every candidate the merge discarded
    would report ``status: ok``, ``edge_count: 0`` and an empty ``notes`` list —
    a confident-looking zero indistinguishable from "ran and legitimately found
    nothing", which is exactly the vacuity this extension point exists to
    eliminate (see the contract's § "Suppression must be reported, never silent").

    Surviving pairs are unioned keyed on ``(from, to)``. A pair produced by more
    than one resolver collapses to ONE edge whose ``producers[]`` is the sorted
    list of contributing resolver ids.

    A resolver that raises reports ``status: error`` with ``edge_count: 0`` and
    contributes no edges; its siblings still contribute. An errored resolver
    never aborts the merge — a single broken implementor must not blank the graph.

    Zero resolvers is a first-class, non-error outcome: the return is
    ``([], [])``, never an exception and never a fabricated edge. The caller
    distinguishes "no resolver ran" from "N resolvers ran and found nothing" by
    the length of the returned report list.

    Args:
        resolvers: Discovered resolver records from
            ``extension_discovery.discover_derivation_resolvers()`` — each a
            ``{origin, id, module}`` dict.
        derived_by_name: Module name → derived data. Its keys are the authoritative
            known-module set both endpoints of every edge are validated against.
        enriched_by_name: Module name → enriched (LLM-curated) overlay data,
            passed through to each resolver unchanged.

    Returns:
        A ``(edges, resolver_reports)`` tuple. ``edges`` is a list of
        ``{'from': str, 'to': str, 'producers': list[str]}`` dicts sorted by
        ``(from, to)`` for byte-stable output. ``resolver_reports`` is one
        ``{'id', 'edge_count', 'status', 'notes'}`` dict per resolver, in the
        order the resolvers were supplied.
    """
    known_modules = set(derived_by_name)
    # Keyed on (from, to); value is the set of contributing resolver ids.
    producers_by_pair: dict[tuple[str, str], set[str]] = {}
    reports: list[dict[str, Any]] = []

    for record in resolvers:
        resolver_id = record.get('id', '')

        # The module lookup and the hook call share one guarded block: a record
        # missing its ``module`` key is as much a broken-implementor condition as
        # a raising ``derive_edges``, and both resolve to the same error report
        # rather than aborting the merge.
        try:
            raw_edges, raw_notes = record['module'].derive_edges(derived_by_name, enriched_by_name)
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] derive_edges() failed for derivation resolver {resolver_id}: {e}',
            )
            reports.append(
                {
                    'id': resolver_id,
                    'edge_count': 0,
                    'status': _STATUS_ERROR,
                    'notes': [f'derive_edges() raised: {e}'],
                }
            )
            continue

        notes = _coerce_notes(raw_notes)
        contributed: set[tuple[str, str]] = set()
        for candidate in raw_edges or []:
            pair = _coerce_pair(candidate)
            if pair is None:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped malformed candidate {candidate!r} — '
                    f'not a two-element pair of module-name strings'
                )
                continue
            source, target = pair
            if source == target:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped self-edge ({source} -> {target}) — '
                    f'a module does not depend on itself'
                )
                continue
            unknown = [name for name in (source, target) if name not in known_modules]
            if unknown:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped edge ({source} -> {target}) — '
                    f'unknown module endpoint(s): {", ".join(unknown)}'
                )
                continue
            contributed.add(pair)
            producers_by_pair.setdefault(pair, set()).add(resolver_id)

        reports.append(
            {
                'id': resolver_id,
                'edge_count': len(contributed),
                'status': _STATUS_OK,
                'notes': notes,
            }
        )

    edges = [
        {'from': source, 'to': target, 'producers': sorted(producers_by_pair[(source, target)])}
        for source, target in sorted(producers_by_pair)
    ]
    return edges, reports
