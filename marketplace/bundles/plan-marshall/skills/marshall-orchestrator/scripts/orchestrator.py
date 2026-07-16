#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Thin scaffolding script for the marshall-orchestrator skill.

Deliberately lean, per the orchestrator's lean posture: everything that
requires judgement stays LLM-workflow; this script owns exactly three
deterministic operations against the main-anchored orchestrator store
(``.plan/local/orchestrator/{slug}/``, resolved via
``file_ops.get_store_dir('orchestrator', slug)``):

- ``scaffold --slug S`` — create the epic directory tree (idempotent).
- ``queue --slug S [--transition PLAN-NN --status X]`` — read the plan
  queue from ``status.json``, or transition one plan's status.
- ``resume-summary --slug S`` — generate the "START HERE" block from
  ``status.json`` (the machine authority) for the LLM to paste into
  ``epic.md`` between the generated-block markers.

The ``kind=orchestrator`` ``status.json`` schema is owned by
``manage-status/standards/status-lifecycle.md``; ``status.json`` is created
via ``manage-status create --store orchestrator``, never by this script.
No implementation-side capability (no build/CI/source verbs) exists here.
"""

import argparse
from pathlib import Path
from typing import Any

from file_ops import (
    get_store_dir,
    now_utc_iso,
    output_toon,
    read_json,
    safe_main,
    write_json,
)
from input_validation import validate_plan_id

ORCHESTRATOR_STORE = 'orchestrator'

# Epic subdirectories per the layout contract in
# persona-marshall-orchestrator/standards/orchestration-model.md.
EPIC_SUBDIRS = ('workstreams', 'plans', 'landings', 'logs')

FILE_STATUS = 'status.json'


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


def _epic_root(slug: str) -> Path:
    """Resolve the epic's store root directory."""
    return get_store_dir(ORCHESTRATOR_STORE, slug)


def _read_status(slug: str) -> dict[str, Any]:
    """Read the epic's status.json (empty dict when absent)."""
    return dict(read_json(_epic_root(slug) / FILE_STATUS))


def _write_status(slug: str, status: dict[str, Any]) -> None:
    """Write the epic's status.json, stamping ``updated``."""
    status['updated'] = now_utc_iso()
    write_json(_epic_root(slug) / FILE_STATUS, status)


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
    """Read the plan queue, or transition one plan's status.

    Without ``--transition``: returns ``phase``, ``resume_anchor``, and the
    full ``plans[]`` queue from ``status.json``. With ``--transition PLAN-NN
    --status X``: sets that plan's ``status`` field and writes the document
    back. The status vocabulary is owned by the orchestrator workflows; the
    script stores the supplied value verbatim.
    """
    invalid = _validate_slug(args.slug)
    if invalid:
        return _error(args.slug, 'invalid_slug', invalid)
    if (args.transition is None) != (args.status is None):
        return _error(
            args.slug,
            'wrong_parameters',
            '--transition and --status must be supplied together',
        )
    status_doc = _read_status(args.slug)
    if not status_doc:
        return _error(
            args.slug, 'file_not_found', 'status.json not found in orchestrator store'
        )
    plans = status_doc.get('plans', [])
    if args.transition is None:
        return {
            'status': 'success',
            'operation': 'queue',
            'slug': args.slug,
            'store': ORCHESTRATOR_STORE,
            'phase': status_doc.get('phase', ''),
            'resume_anchor': status_doc.get('resume_anchor', ''),
            'plans': plans,
        }
    for plan in plans:
        if plan.get('id') == args.transition:
            previous = plan.get('status', '')
            plan['status'] = args.status
            _write_status(args.slug, status_doc)
            return {
                'status': 'success',
                'operation': 'queue-transition',
                'slug': args.slug,
                'store': ORCHESTRATOR_STORE,
                'plan': args.transition,
                'previous_status': previous,
                'new_status': args.status,
            }
    return _error(
        args.slug,
        'plan_not_found',
        f'plan {args.transition!r} not found in the queue',
        available_plans=[plan.get('id', '') for plan in plans],
    )


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
    status_doc = _read_status(args.slug)
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


def _add_slug_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--slug', required=True, help='Epic slug (kebab-case)')


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='orchestrator',
        description=(
            'Thin scaffolding for marshall-orchestrator epics: scaffold the '
            'epic tree, read/transition the plan queue, generate the '
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
        help='Read the plan queue from status.json, or transition one plan status.',
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
    queue.set_defaults(handler=cmd_queue)

    resume = subparsers.add_parser(
        'resume-summary',
        help='Generate the START-HERE block from status.json (paste into epic.md).',
        allow_abbrev=False,
    )
    _add_slug_arg(resume)
    resume.set_defaults(handler=cmd_resume_summary)

    return parser


@safe_main
def main() -> int:
    args = _build_arg_parser().parse_args()
    output_toon(args.handler(args))
    return 0


if __name__ == '__main__':
    main()
