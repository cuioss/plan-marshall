#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Thin scaffolding script for the marshall-orchestrator skill.

Deliberately lean, per the orchestrator's lean posture: everything that
requires judgement stays LLM-workflow; this script owns four deterministic
operations against the main-anchored orchestrator store
(``.plan/local/orchestrator/{slug}/``, resolved via
``file_ops.get_store_dir('orchestrator', slug)``):

- ``scaffold --slug S`` — create the epic directory tree (idempotent).
- ``queue --slug S [--transition PLAN-NN --status X | --set-row PLAN-NN
  --field F --value V]`` — a three-way surface over the plan queue in
  ``status.json``: read the whole queue, transition one plan's ``status``,
  or set one result field (:data:`PLAN_ROW_FIELDS`) of one plan row. Both
  write forms mutate the located row inside the shared ``rmw_json``
  critical section, so no unsynchronised whole-array rewrite remains.
- ``resume-summary --slug S`` — generate the "START HERE" block from
  ``status.json`` (the machine authority) for the LLM to paste into
  ``epic.md`` between the generated-block markers.
- ``archive --slug S`` — relocate a *closed* epic tree to
  ``.plan/local/archived-orchestrators/{slug}/`` (a mechanical, post-close
  directory move that requires no judgement; refuses a non-closed epic).

The ``kind=orchestrator`` ``status.json`` schema is owned by
``manage-status/standards/status-lifecycle.md``; ``status.json`` is created
via ``manage-status create --store orchestrator``, never by this script.
No implementation-side capability (no build/CI/source verbs) exists here.
"""

import argparse
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _locks_core import rmw_json
from file_ops import (
    get_archived_orchestrator_dir,
    get_store_dir,
    now_utc_iso,
    output_toon,
    read_json,
    safe_main,
)
from input_validation import validate_plan_id

ORCHESTRATOR_STORE = 'orchestrator'

# Epic subdirectories per the layout contract in
# persona-marshall-orchestrator/standards/orchestration-model.md.
EPIC_SUBDIRS = ('workstreams', 'plans', 'landings', 'logs')

FILE_STATUS = 'status.json'

# The per-row RESULT fields ``queue --set-row`` may write. Deliberately narrow:
# ``status`` stays exclusive to ``--transition`` (a status change and a landing
# stamp are independent events), and ``id``/``slug``/``workstream`` are row
# identity, not result, so they are seeded by ``decompose`` and never patched.
PLAN_ROW_FIELDS = frozenset({'plan_marshall_plan_id', 'pr', 'landing'})


def _error(slug: str, error: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build the standard TOON error envelope for this script."""
    result: dict[str, Any] = {
        'status': 'error',
        'slug': slug,
        'store': ORCHESTRATOR_STORE,
        'error': error,
        'message': message,
    }
    result.update(extra)
    return result


def _validate_slug(slug: str) -> str | None:
    """Validate the epic slug (kebab-case, same shape as a plan id).

    Returns an error message string when invalid, ``None`` when valid.
    The validation is load-bearing: the slug becomes a directory name under
    the orchestrator store, so a malformed value (path separators, ``..``)
    must never reach ``get_store_dir``.
    """
    try:
        validate_plan_id(slug)
    except ValueError as exc:
        return str(exc)
    return None


def _epic_root(slug: str, allow_archived: bool = False) -> Path:
    """Resolve the epic's store root directory.

    ``allow_archived`` threads straight into
    :func:`file_ops.get_store_dir`'s read-fallback: when ``True`` and the active
    ``orchestrator/{slug}`` tree is absent, the archived home
    ``archived-orchestrators/{slug}`` is resolved instead (when it exists).
    READ verbs pass ``True``; ``scaffold``, ``queue --transition``, and the
    ``archive`` source resolution stay strict (default ``False``) so a frozen
    archived epic is never mutated at the active path.
    """
    return get_store_dir(ORCHESTRATOR_STORE, slug, allow_archived=allow_archived)


def _read_status(slug: str, allow_archived: bool = False) -> dict[str, Any]:
    """Read the epic's status.json (empty dict when absent or malformed).

    ``read_json`` degrades a missing/unreadable/unparseable file to ``{}``, but
    a status.json whose top-level JSON is valid-but-non-dict (an array, a bare
    string, ``null``) would otherwise reach ``dict(...)`` and raise. Fall back
    to ``{}`` on any non-dict parse so callers always receive a dict.

    ``allow_archived`` threads into :func:`_epic_root` so READ verbs resolve an
    archived epic transparently when its active tree is absent.
    """
    data = read_json(_epic_root(slug, allow_archived=allow_archived) / FILE_STATUS)
    if not isinstance(data, dict):
        return {}
    return dict(data)


def _set_row_field(row: dict[str, Any], field: str, value: str) -> dict[str, Any]:
    """Set one field of a plan row, returning the previous and new values."""
    previous = row.get(field, '')
    row[field] = value
    return {'previous': previous, 'new': value}


def _mutate_plan_row(
    slug: str, plan_id: str, apply: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any]:
    """Apply ``apply`` to one ``plans[]`` row inside a serialized critical section.

    The single write path for the plan queue: both ``--transition`` and
    ``--set-row`` route through here, so no unsynchronised read-modify-write of
    ``plans[]`` remains. The mutation runs against the FRESH in-lock state via
    the shared ``O_EXCL``-guarded :func:`_locks_core.rmw_json` — the same
    critical section ``manage-status update-field`` uses for this very document
    — so a concurrent orchestrator session stamping a DIFFERENT row (or a
    different field of the same row) cannot be clobbered by a last-writer-wins
    over a stale read. ``updated`` is re-stamped only when a row was located.

    Returns a dict carrying either ``result`` (the value ``apply`` returned for
    the located row) or ``available_plans`` (every queued plan id) when
    ``plan_id`` is absent from the queue.
    """
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        plans = state.get('plans', [])
        for row in plans:
            if row.get('id') == plan_id:
                outcome['result'] = apply(row)
                state['updated'] = now_utc_iso()
                return state
        outcome['available_plans'] = [row.get('id', '') for row in plans]
        return state

    rmw_json(_epic_root(slug) / FILE_STATUS, _mutate)
    return outcome


def cmd_scaffold(args: argparse.Namespace) -> dict[str, Any]:
    """Create the ``.plan/local/orchestrator/{slug}/`` directory tree.

    Idempotent: existing directories are left untouched, re-running against
    an already-scaffolded epic succeeds and reports ``already_existed: true``.
    Does NOT create ``status.json`` — that is
    ``manage-status create --store orchestrator``'s job.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    root = _epic_root(args.slug)
    already_existed = root.is_dir()
    root.mkdir(parents=True, exist_ok=True)
    for sub in EPIC_SUBDIRS:
        (root / sub).mkdir(exist_ok=True)
    return {
        'status': 'success',
        'operation': 'scaffold',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'root': str(root),
        'already_existed': already_existed,
        'directories': list(EPIC_SUBDIRS),
    }


def cmd_queue(args: argparse.Namespace) -> dict[str, Any]:
    """Read the plan queue, transition one plan's status, or set one row field.

    Three-way surface over ``status.json``'s ``plans[]``:

    - **read** (no write flags): returns ``phase``, ``resume_anchor``, and the
      full ``plans[]`` queue.
    - **transition** (``--transition PLAN-NN --status X``): sets that plan's
      ``status``. The status vocabulary is owned by the orchestrator workflows;
      the script stores the supplied value verbatim.
    - **set-row** (``--set-row PLAN-NN --field F --value V``): sets one result
      field of that plan's row, where ``F`` is one of :data:`PLAN_ROW_FIELDS`.
      This is the sanctioned way to stamp a landing (``pr``, ``landing``,
      ``plan_marshall_plan_id``) without re-serializing the whole array.

    The two write forms are mutually exclusive, each triple/pair must be
    supplied complete, and both mutate the located row through
    :func:`_mutate_plan_row`'s critical section.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    set_row_args = (args.set_row, args.field, args.value)
    transition_args = (args.transition, args.status)
    set_row_given = any(arg is not None for arg in set_row_args)
    transition_given = any(arg is not None for arg in transition_args)
    if set_row_given and transition_given:
        return _error(
            args.slug,
            'wrong_parameters',
            '--set-row/--field/--value are mutually exclusive with --transition/--status',
        )
    if set_row_given and not all(arg is not None for arg in set_row_args):
        return _error(
            args.slug,
            'wrong_parameters',
            '--set-row, --field and --value must be supplied together',
        )
    if (args.transition is None) != (args.status is None):
        return _error(
            args.slug,
            'wrong_parameters',
            '--transition and --status must be supplied together',
        )
    if set_row_given and args.field not in PLAN_ROW_FIELDS:
        return _error(
            args.slug,
            'invalid_field',
            f'--field must be one of {sorted(PLAN_ROW_FIELDS)}, got: {args.field}',
        )
    # Read-path resolves an archived epic transparently; both write-paths stay
    # strict so an archived epic is never mutated at the active path.
    is_read = not set_row_given and not transition_given
    status_doc = _read_status(args.slug, allow_archived=is_read)
    if not status_doc:
        return _error(
            args.slug, 'file_not_found', 'status.json not found in orchestrator store'
        )
    if is_read:
        return {
            'status': 'success',
            'operation': 'queue',
            'slug': args.slug,
            'store': ORCHESTRATOR_STORE,
            'phase': status_doc.get('phase', ''),
            'resume_anchor': status_doc.get('resume_anchor', ''),
            'plans': status_doc.get('plans', []),
        }
    plan_id = args.set_row if set_row_given else args.transition
    field = args.field if set_row_given else 'status'
    value = args.value if set_row_given else args.status
    outcome = _mutate_plan_row(
        args.slug, plan_id, lambda row: _set_row_field(row, field, value)
    )
    if 'result' not in outcome:
        return _error(
            args.slug,
            'plan_not_found',
            f'plan {plan_id!r} not found in the queue',
            available_plans=outcome['available_plans'],
        )
    result = outcome['result']
    if set_row_given:
        return {
            'status': 'success',
            'operation': 'queue-set-row',
            'slug': args.slug,
            'store': ORCHESTRATOR_STORE,
            'plan': plan_id,
            'field': field,
            'previous_value': result['previous'],
            'new_value': result['new'],
        }
    return {
        'status': 'success',
        'operation': 'queue-transition',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'plan': plan_id,
        'previous_status': result['previous'],
        'new_status': result['new'],
    }


def _format_plan_line(plan: dict[str, Any]) -> str:
    """Render one plan as a summary line, appending the non-empty link fields."""
    parts = [f'{plan.get("id", "?")} ({plan.get("workstream", "?")})']
    if plan.get('plan_marshall_plan_id'):
        parts.append(f'plan={plan["plan_marshall_plan_id"]}')
    if plan.get('pr'):
        parts.append(f'PR {plan["pr"]}')
    if plan.get('landing'):
        parts.append(f'landing={plan["landing"]}')
    return ' — '.join(parts)


def _build_summary(status_doc: dict[str, Any]) -> str:
    """Build the START-HERE markdown block, derived purely from status.json.

    Renders the resume anchor, the epic phase, the running/parked plans, the
    staged queue (in ``plans[]`` order), and a residual per-status listing for
    every other status value — so no plan is ever invisible in the summary.
    """
    plans = status_doc.get('plans', [])
    lines = [
        f'**Resume anchor**: {status_doc.get("resume_anchor") or "(not set)"}',
        f'**Phase**: {status_doc.get("phase", "")}',
    ]
    running = [p for p in plans if p.get('status') == 'running']
    parked = [p for p in plans if p.get('status') == 'parked']
    staged = [p for p in plans if p.get('status') == 'staged']
    other = [p for p in plans if p.get('status') not in ('running', 'parked', 'staged')]
    for label, group in (('Running', running), ('Parked', parked)):
        if group:
            lines.append(f'**{label}**:')
            lines.extend(f'- {_format_plan_line(plan)}' for plan in group)
    lines.append('**Queue** (staged, in order):')
    if staged:
        lines.extend(
            f'{position}. {_format_plan_line(plan)}'
            for position, plan in enumerate(staged, start=1)
        )
    else:
        lines.append('- (empty)')
    for plan in other:
        lines.append(f'- {_format_plan_line(plan)} — status: {plan.get("status", "")}')
    return '\n'.join(lines)


def cmd_resume_summary(args: argparse.Namespace) -> dict[str, Any]:
    """Generate the START-HERE block from status.json.

    The returned ``summary`` field is the markdown block the LLM pastes
    verbatim between the ``BEGIN/END GENERATED: resume-summary`` markers in
    ``epic.md``. It is derived purely from ``status.json`` — the machine
    authority — never from the prose already in ``epic.md``.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    status_doc = _read_status(args.slug, allow_archived=True)
    if not status_doc:
        return _error(
            args.slug, 'file_not_found', 'status.json not found in orchestrator store'
        )
    return {
        'status': 'success',
        'operation': 'resume-summary',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'summary': _build_summary(status_doc),
    }


def cmd_archive(args: argparse.Namespace) -> dict[str, Any]:
    """Relocate a *closed* epic tree to ``archived-orchestrators/{slug}/``.

    A mechanical, post-close directory move (the fourth deterministic
    operation this script owns) — never a judgement call. Order of checks:

    - source absent, dest present → idempotent success (``already_archived``).
    - source absent, dest absent → ``error: not_found``.
    - source present, epic phase is not ``closed`` → ``error: not_closed`` with
      an actionable message; NO move is performed.
    - source present AND dest present → ``error: archive_conflict`` (never
      clobber the frozen audit record).
    - otherwise → create the archived parent and ``shutil.move`` the tree,
      returning ``archived_to``.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    source = _epic_root(args.slug)
    dest = get_archived_orchestrator_dir(args.slug)
    if not source.exists():
        if dest.exists():
            return {
                'status': 'success',
                'operation': 'archive',
                'slug': args.slug,
                'store': ORCHESTRATOR_STORE,
                'already_archived': True,
                'archived_to': str(dest),
            }
        return _error(
            args.slug,
            'not_found',
            f'epic {args.slug!r} has no active or archived tree to archive',
        )
    phase = _read_status(args.slug).get('phase', '')
    if phase != 'closed':
        return _error(
            args.slug,
            'not_closed',
            f'epic {args.slug} is phase={phase}; run close first, then archive',
            phase=phase,
        )
    if dest.exists():
        return _error(
            args.slug,
            'archive_conflict',
            f'epic {args.slug!r} already has an archived tree at {dest}; '
            'refusing to clobber the audit record',
            archived_to=str(dest),
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {
        'status': 'success',
        'operation': 'archive',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'already_archived': False,
        'archived_to': str(dest),
    }


def _add_slug_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--slug', required=True, help='Epic slug (kebab-case)')


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='orchestrator',
        description=(
            'Thin scaffolding for marshall-orchestrator epics: scaffold the '
            'epic tree, read/transition/stamp the plan queue, generate the '
            'START-HERE resume summary.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    scaffold = subparsers.add_parser(
        'scaffold',
        help='Create the .plan/local/orchestrator/{slug}/ directory tree (idempotent).',
        allow_abbrev=False,
    )
    _add_slug_arg(scaffold)
    scaffold.set_defaults(handler=cmd_scaffold)

    queue = subparsers.add_parser(
        'queue',
        help=(
            'Read the plan queue from status.json, transition one plan status, '
            'or set one plan row field.'
        ),
        allow_abbrev=False,
    )
    _add_slug_arg(queue)
    queue.add_argument(
        '--transition',
        default=None,
        metavar='PLAN-NN',
        help='Plan id to transition (requires --status).',
    )
    queue.add_argument(
        '--status',
        default=None,
        metavar='STATUS',
        help='New status value for the plan named by --transition.',
    )
    queue.add_argument(
        '--set-row',
        default=None,
        metavar='PLAN-NN',
        help=(
            'Plan id whose row field to set (requires --field and --value; '
            'mutually exclusive with --transition/--status).'
        ),
    )
    queue.add_argument(
        '--field',
        default=None,
        metavar='FIELD',
        help=f'Row field to set: one of {sorted(PLAN_ROW_FIELDS)} (requires --set-row).',
    )
    queue.add_argument(
        '--value',
        default=None,
        metavar='VALUE',
        help='New value for the field named by --field (requires --set-row).',
    )
    queue.set_defaults(handler=cmd_queue)

    resume = subparsers.add_parser(
        'resume-summary',
        help='Generate the START-HERE block from status.json (paste into epic.md).',
        allow_abbrev=False,
    )
    _add_slug_arg(resume)
    resume.set_defaults(handler=cmd_resume_summary)

    archive = subparsers.add_parser(
        'archive',
        help='Relocate a closed epic tree to archived-orchestrators/{slug}/ (post-close, mechanical).',
        allow_abbrev=False,
    )
    _add_slug_arg(archive)
    archive.set_defaults(handler=cmd_archive)

    return parser


@safe_main
def main() -> int:
    args = _build_arg_parser().parse_args()
    output_toon(args.handler(args))
    return 0


if __name__ == '__main__':
    main()
