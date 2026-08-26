#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CRUD command handlers for manage-references.

Handles: create, read, get, set, sync-affected-files
"""

import argparse

from _plan_parsing import INTENT_UNANNOTATED, declared_paths_by_intent, declared_paths_population
from _references_core import (
    get_references_path,
    read_references,
    require_references,
    write_references,
)
from constants import FILE_SOLUTION_OUTLINE, STEP_INTENT_READ, VALID_STEP_INTENTS
from file_ops import get_plan_dir
from input_validation import require_valid_plan_id

#: The references key holding the plan's DECLARED footprint — the paths the
#: outline says the plan expects to MODIFY. Distinct from ``realized_footprint``,
#: which records what the worktree actually touched, and — since the intent
#: partition below — distinct from the plan's whole declared surface: a path the
#: plan only READS is declared, but is not an expected modification and does not
#: belong here.
_AFFECTED_FILES_FIELD = 'affected_files'

#: The references key holding the READ-intent half of the declared surface.
#:
#: The partition's carry side. Read-intent paths are excluded from
#: ``affected_files`` because that key means "expected modification", and a
#: read-only path counted there caps every recall figure derived from it below
#: threshold by construction — the denominator gains a member the numerator can
#: never contain, since the footprint is a diff and a file the plan only read can
#: never appear in one. They are kept HERE rather than dropped so the declaration
#: survives: a reader can still tell a genuinely small declared surface from a
#: filtered one, which a silent exclusion would destroy.
_READ_INTENT_FILES_FIELD = 'read_intent_files'

#: The declared intents that denote a MODIFICATION, and therefore partition into
#: ``affected_files``.
#:
#: :data:`_plan_parsing.INTENT_UNANNOTATED` is a member deliberately. A bullet
#: under a modification heading that carries no ``(intent)`` marker stated no
#: intent at all, and the two available readings are not symmetric: counting it
#: as a modification over-states the expected write-set by one path, while
#: counting it as a read SUBTRACTS it from every change footprint derived
#: downstream and manufactures a vacuously small denominator. The over-stating
#: direction is the safe one, so an unmarked declaration is never quieter than a
#: marked one. Its count is published separately (``unannotated_count``) so the
#: assumption stays visible rather than being folded silently into the total.
#:
#: A marker-less bullet under ``Files to survey`` never reaches this set: that
#: heading is analysis-only by definition, so ``_plan_parsing`` resolves its
#: unmarked bullets to :data:`constants.STEP_INTENT_READ` at parse time.
#:
#: DERIVED by subtraction from the closed enum rather than enumerated as
#: literals, so the two sides of the partition cannot drift apart. A fifth intent
#: added to :data:`constants.VALID_STEP_INTENTS` is a modification here by
#: construction — the direction that over-states rather than silently drops a
#: path — instead of falling into neither half and vanishing from both keys.
#: ``declared_paths_by_intent`` guarantees the same closed key set, so this
#: subtraction and that mapping enumerate the same intents.
_MUTATION_INTENTS = frozenset(set(VALID_STEP_INTENTS) - {STEP_INTENT_READ} | {INTENT_UNANNOTATED})


def cmd_create(args: argparse.Namespace) -> dict:
    """Create references.json with basic fields."""
    require_valid_plan_id(args)

    path = get_references_path(args.plan_id)
    if path.exists():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'already_exists',
            'message': 'references.json already exists',
        }

    # Build base references
    refs = {'branch': args.branch, 'base_branch': 'main'}

    # Add optional fields
    if args.issue_url:
        refs['issue_url'] = args.issue_url
    if args.build_system:
        refs['build_system'] = args.build_system
    if args.domains:
        refs['domains'] = [d.strip() for d in args.domains.split(',') if d.strip()]

    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'file': 'references.json',
        'created': True,
        'fields': list(refs.keys()),
    }


def cmd_read(args: argparse.Namespace) -> dict:
    """Read entire references.json."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)
    if refs.get('status') == 'error':
        return refs

    # Summarize lists
    summary = {}
    for key, value in refs.items():
        if isinstance(value, list):
            summary[key] = f'{len(value)} items'
        else:
            summary[key] = value

    return {'status': 'success', 'plan_id': args.plan_id, 'references': summary}


def cmd_get(args: argparse.Namespace) -> dict:
    """Get a specific field value."""
    require_valid_plan_id(args)

    refs = require_references(args.plan_id)
    if refs.get('status') == 'error':
        return refs

    value = refs.get(args.field)
    if value is None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'field': args.field,
            'error': 'field_not_found',
            'message': f"Field '{args.field}' not found",
        }

    return {'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': value}


def cmd_set(args: argparse.Namespace) -> dict:
    """Set a specific field value."""
    require_valid_plan_id(args)

    refs = read_references(args.plan_id)
    previous = refs.get(args.field)
    refs[args.field] = args.value
    write_references(args.plan_id, refs)

    result = {'status': 'success', 'plan_id': args.plan_id, 'field': args.field, 'value': args.value}
    if previous is not None:
        result['previous'] = previous
    return result


def _read_outline(plan_id: str) -> tuple[str | None, dict]:
    """Read the plan's solution outline, or return the refusal that explains why not.

    Returns ``(content, error)`` where exactly one member is populated. The error
    branch is a refusal, never an empty-string content: a caller handed empty text
    would derive an empty declared set and report it as a measurement, which is
    precisely the false-zero this verb exists to remove.
    """
    outline_path = get_plan_dir(plan_id) / FILE_SOLUTION_OUTLINE
    if not outline_path.exists():
        return None, {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'outline_not_found',
            'message': f'{FILE_SOLUTION_OUTLINE} not found — nothing to derive the declared footprint from',
        }
    try:
        return outline_path.read_text(encoding='utf-8'), {}
    except OSError as exc:
        return None, {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'outline_unreadable',
            'message': f'{FILE_SOLUTION_OUTLINE} could not be read: {exc}',
        }


def _union_into(refs: dict, field: str, derived: set[str]) -> tuple[list[str], list[str], dict]:
    """Union ``derived`` into ``refs[field]``, preserving the recorded order.

    Returns ``(recorded, added, error)``. ``error`` is populated — and the other
    two are empty — only when the existing value is present but not a list, which
    is a corrupt-state refusal rather than something to overwrite silently.

    Ordering is stable by construction: already-recorded paths keep their
    position and newly derived ones are appended in sorted order, so a re-run
    that derived the same set leaves the key byte-identical and the file does not
    churn between runs.
    """
    existing = refs.get(field)
    if existing is None:
        existing = []
    elif not isinstance(existing, list):
        return [], [], {
            'status': 'error',
            'field': field,
            'error': 'not_a_list',
            'message': f"Field '{field}' is not a list",
        }

    recorded = [str(value) for value in existing]
    added = sorted(derived - set(recorded))
    refs[field] = recorded + added
    return recorded, added, {}


def cmd_sync_affected_files(args: argparse.Namespace) -> dict:
    """Re-derive the plan's declared footprint, PARTITIONED BY INTENT.

    The declared footprint is DERIVED, not composed. Every path comes from
    ``_plan_parsing.declared_paths_by_intent``, which walks all three declaration
    headings across every deliverable — so a survey-scope deliverable's
    ``Files expected to mutate:`` paths reach the keys, and no reader has to
    scrape outline prose into a CSV to produce them.

    **The partition.** The derived paths are split by the intent they were
    declared with and written to two keys, not one:

    * ``affected_files`` — the MUTATION half (:data:`_MUTATION_INTENTS`): every
      declared write, delete, and unannotated-under-a-modification-heading path.
      This key means "expected modification", and it is what every downstream
      recall figure uses as its denominator.
    * ``read_intent_files`` — the READ half: paths a deliverable declared it
      would only consult.

    Keeping a read-intent path out of ``affected_files`` is the point. The
    realized footprint is a diff, so a file the plan merely read can never appear
    in it; counted as an expected modification it is a denominator member the
    numerator cannot ever contain, and it caps every derived recall below
    threshold no matter how completely the plan executed. Excluding it silently
    would trade that error for a worse one — an unexplained small set — so the
    path is CARRIED in the sibling key rather than dropped, and the counts below
    make the split legible.

    **The two halves are disjoint, and mutation wins.** A path declared a write
    by one deliverable and a read by another is an expected modification: the
    write declaration is the load-bearing one, and honouring the read instead
    would subtract a genuinely-changing file from the footprint. Such a path is
    therefore reported under ``affected_files`` only, and the number of read
    declarations reclassified this way is published as
    ``read_reclassified_count`` so the subtraction is visible rather than
    silently shrinking ``read_intent_count``. Disjointness is what lets
    ``mutation_count + read_intent_count`` reconstruct the distinct declared-path
    total exactly.

    Both writes are **set unions** over the existing values, which is what makes
    the verb safe to re-run at every point a later consumer depends on the value
    being current (before the manifest is composed, and again on the finalize
    loop-back). A path recorded by an earlier run survives a later one, a path
    that appeared after the outline was first read is added, and a repeat run
    with no new paths changes nothing.

    Refuses rather than reporting a clean zero when it could not derive anything:
    a missing or unreadable outline, and an outline whose Deliverables section
    yielded no deliverable blocks at all, are ``status: error`` — an empty
    derivation from an unread outline is indistinguishable from a plan that
    declared nothing, and only the first is a failure of this verb.
    """
    require_valid_plan_id(args)

    content, read_error = _read_outline(args.plan_id)
    if content is None:
        return read_error

    population = declared_paths_population(content)
    if population['deliverables_scanned'] == 0:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'no_deliverables_parsed',
            'message': (
                'No deliverable blocks were parsed from the outline — the declared '
                'footprint was not derived. Nothing was written.'
            ),
            **population,
        }

    by_intent = declared_paths_by_intent(content)

    mutation: set[str] = set()
    for intent in _MUTATION_INTENTS:
        mutation |= by_intent.get(intent, set())

    declared_read = by_intent.get(STEP_INTENT_READ, set())
    # Mutation wins the overlap — see the disjointness paragraph in the docstring.
    read_intent = declared_read - mutation
    unannotated = by_intent.get(INTENT_UNANNOTATED, set())

    refs = read_references(args.plan_id)

    mutation_recorded, mutation_added, error = _union_into(refs, _AFFECTED_FILES_FIELD, mutation)
    if error:
        return {'plan_id': args.plan_id, **error}

    read_recorded, read_added, error = _union_into(refs, _READ_INTENT_FILES_FIELD, read_intent)
    if error:
        return {'plan_id': args.plan_id, **error}

    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'field': _AFFECTED_FILES_FIELD,
        'added_count': len(mutation_added),
        # Derived paths the key ALREADY carried. Reported alongside ``added_count``
        # so a zero-add run states whether it derived nothing or re-derived what
        # was already there.
        'unchanged_count': len(mutation & set(mutation_recorded)),
        'total': len(refs[_AFFECTED_FILES_FIELD]),
        'added': mutation_added,
        # ---- the partition, and the populations behind it -------------------
        # Published so a FILTERED set is never mistaken for a SMALL one: the
        # three counts together state how large the declared surface was and
        # which way each path was routed. `mutation_count + read_intent_count`
        # reconstructs `declared_count` exactly (the halves are disjoint);
        # `unannotated_count` is a SUB-count of `mutation_count`, naming how much
        # of the mutation half got there by the unmarked-bullet default rather
        # than by an explicit marker.
        'mutation_count': len(mutation),
        'read_intent_count': len(read_intent),
        'unannotated_count': len(unannotated),
        'read_reclassified_count': len(declared_read & mutation),
        'declared_count': len(mutation) + len(read_intent),
        'read_intent_field': _READ_INTENT_FILES_FIELD,
        'read_intent_added_count': len(read_added),
        'read_intent_total': len(refs[_READ_INTENT_FILES_FIELD]),
        'read_intent_added': read_added,
        **population,
    }
