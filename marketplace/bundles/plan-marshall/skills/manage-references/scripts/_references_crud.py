#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CRUD command handlers for manage-references.

Handles: create, read, get, set, sync-affected-files
"""

import argparse

from _plan_parsing import declared_paths_by_intent, declared_paths_population
from _references_core import (
    get_references_path,
    read_references,
    require_references,
    write_references,
)
from constants import FILE_SOLUTION_OUTLINE
from file_ops import get_plan_dir
from input_validation import require_valid_plan_id

#: The references key holding the plan's DECLARED footprint — the paths the
#: outline says the plan expects to touch. Distinct from ``realized_footprint``,
#: which records what the worktree actually touched.
_AFFECTED_FILES_FIELD = 'affected_files'


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


def cmd_sync_affected_files(args: argparse.Namespace) -> dict:
    """Re-derive ``references.affected_files`` from the outline's structured data.

    The declared footprint is DERIVED, not composed. Every path comes from
    ``_plan_parsing.declared_paths_by_intent``, which walks all three declaration
    headings across every deliverable — so a survey-scope deliverable's
    ``Files expected to mutate:`` paths reach the key for the first time, and no
    reader has to scrape outline prose into a CSV to produce it.

    The write is a **set union** over the existing value, which is what makes the
    verb safe to re-run at every point a later consumer depends on the value being
    current (before the manifest is composed, and again on the finalize loop-back).
    A path recorded by an earlier run survives a later one, a path that appeared
    after the outline was first read is added, and a repeat run with no new paths
    changes nothing. Ordering is stable: already-recorded paths keep their position
    and newly derived ones are appended in sorted order, so the key does not churn
    between runs that derived the same set.

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

    declared: set[str] = set()
    for paths in declared_paths_by_intent(content).values():
        declared |= paths

    refs = read_references(args.plan_id)
    existing = refs.get(_AFFECTED_FILES_FIELD)
    if existing is None:
        existing = []
    elif not isinstance(existing, list):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'field': _AFFECTED_FILES_FIELD,
            'error': 'not_a_list',
            'message': f"Field '{_AFFECTED_FILES_FIELD}' is not a list",
        }

    recorded = [str(value) for value in existing]
    known = set(recorded)
    added = sorted(declared - known)
    refs[_AFFECTED_FILES_FIELD] = recorded + added
    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'field': _AFFECTED_FILES_FIELD,
        'added_count': len(added),
        # Derived paths the key ALREADY carried. Reported alongside ``added_count``
        # so a zero-add run states whether it derived nothing or re-derived what
        # was already there.
        'unchanged_count': len(declared & known),
        'total': len(refs[_AFFECTED_FILES_FIELD]),
        'declared_count': len(declared),
        'added': added,
        **population,
    }
