#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Pre-archive foreign-PR landing gate for the phase-6-finalize dispatcher.

A *foreign* task's change lands in a DIFFERENT repository than the one being
planned, so its done-ness cannot be read from the host plan's own PR — nothing
carries that commit into review or merge. Done-ness measured at the commit
therefore reports a foreign task ``done`` even when its change sits on a branch
in another repo with **no PR anywhere**. This gate is the enforcement point that
closes that gap: run BEFORE ``archive-plan``, it refuses to archive while any
foreign deliverable's change is ``pushed_no_pr`` — committed and pushed to a
branch that no PR carries.

The gate is a consumer of two deterministic signals, never of artifact prose:

* the ``foreign`` column on ``manage-solution-outline list-deliverables`` — the
  population it iterates (a change outside the project root), so a coverage
  decision never silently pools host paths with foreign ones; and
* the ``ci pr landing-state`` verb — the per-repository done-ness discriminator
  (``merged`` / ``pr_open`` / ``pushed_no_pr`` / ``unpushed``).

Return shape (CLI emits TOON; programmatic callers consume the dict directly)::

    status: clear | blocked | error
    plan_id: <id>
    foreign_deliverable_count: <int>
    repos[N]{repo_root,landing_state,deliverables}: ...   # one row per foreign repo
    blocking[M]{repo_root,deliverables}: ...              # the pushed_no_pr rows (blocked only)
    unresolved[K]{path,reason}: ...                       # foreign paths whose repo could not be resolved

Outcome semantics:

* ``clear`` — no foreign deliverable is ``pushed_no_pr``. Archive may proceed.
  This includes the common case of zero foreign deliverables.
* ``blocked`` — at least one foreign deliverable's repository is ``pushed_no_pr``.
  The dispatcher MUST NOT archive; it surfaces ``blocking[]`` (the offending
  repos and the deliverables that named them) so the operator opens the missing
  PR(s). ``blocked`` is a first-class, distinguishable state — not ``done`` and
  not a crash — exactly as the plan requires.
* ``error`` — the gate could not evaluate, or could not READ the evidence for at
  least one foreign deliverable: the solution outline could not be listed, the
  project root could not be resolved, a foreign repository root could not be
  resolved, or its landing state came back unreadable / outside the declared
  ``LANDING_STATES`` model. Fails CLOSED — a gate that cannot see the evidence
  must not certify the population clean. The ``unresolved[]`` list names every
  such item.

An ``error`` outcome stops the archive exactly as ``blocked`` does; the two
differ only in why. The gate CLEARS only when it has POSITIVELY read a landing
state in the declared model for every foreign deliverable's repository and none
is ``pushed_no_pr`` — never on an absence of evidence.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py \\
      plan-marshall:phase-6-finalize:foreign_pr_gate check --plan-id {plan_id}

Subprocess seams (``_list_deliverables``, ``_resolve_repo_root``,
``_resolve_landing_state``) are split out so the orchestration body is testable
without a live solution outline, a live foreign checkout, or a live CI provider.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from ci_base import LANDING_STATES
from file_ops import cwd_checkout_root, get_executor_path
from toon_parser import parse_toon, serialize_toon

#: The landing state the gate refuses to archive on. Named once, here, so the
#: refusal condition and its documentation cannot drift apart.
BLOCKING_LANDING_STATE = 'pushed_no_pr'

#: Executor notations for the two signals the gate consumes.
_SOLUTION_OUTLINE_NOTATION = 'plan-marshall:manage-solution-outline:manage-solution-outline'
_CI_NOTATION = 'plan-marshall:tools-integration-ci:ci'


# ---------------------------------------------------------------------------
# Subprocess seams (overridable in tests)
# ---------------------------------------------------------------------------


def _list_deliverables(plan_id: str) -> dict:
    """Return the parsed ``manage-solution-outline list-deliverables`` TOON.

    Consumes the deliverables — including the ``foreign`` column this gate
    iterates — through the executor proxy so the gate reads the SAME structured
    signal every other consumer does, never a re-parse of the outline markdown.
    Returns the parsed dict verbatim; the caller inspects ``status``.
    """
    executor = get_executor_path()
    cmd = [
        sys.executable,
        str(executor),
        _SOLUTION_OUTLINE_NOTATION,
        'list-deliverables',
        '--plan-id',
        plan_id,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    stdout = completed.stdout or ''
    if not stdout.strip():
        return {
            'status': 'error',
            'error': (
                f'list-deliverables produced no output (exit_code={completed.returncode}): '
                f'{completed.stderr.strip() or "no stderr"}'
            ),
        }
    try:
        return parse_toon(stdout)
    except Exception as exc:  # pragma: no cover — defensive only
        return {'status': 'error', 'error': f'list-deliverables output not parseable as TOON: {exc}'}


def _resolve_repo_root(path: str) -> str | None:
    """Return the git toplevel that contains ``path``, or None when unresolvable.

    ``path`` is a foreign (outside-the-project-root) affected-file path; its
    repository root is the git toplevel of the directory it lives in. Returns
    None when that directory is absent or not inside a git checkout — the foreign
    tree may simply not exist in the session running the gate, which is reported
    (``unresolved[]``) rather than treated as a landing verdict.
    """
    directory = os.path.dirname(path) or path
    if not os.path.isdir(directory):
        return None
    completed = subprocess.run(
        ['git', '-C', directory, 'rev-parse', '--show-toplevel'],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    root = completed.stdout.strip()
    return root or None


def _resolve_landing_state(repo_root: str) -> dict:
    """Return the parsed ``ci pr landing-state --project-dir {repo_root}`` TOON.

    Routes the landing-state verb at the foreign repository's checkout via the
    router-level ``--project-dir`` flag, so the verb answers "did THIS
    repository's change land?" for the foreign tree. Returns the parsed dict
    verbatim; the caller reads ``landing_state``.
    """
    executor = get_executor_path()
    cmd = [
        sys.executable,
        str(executor),
        _CI_NOTATION,
        '--project-dir',
        repo_root,
        'pr',
        'landing-state',
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    stdout = completed.stdout or ''
    if not stdout.strip():
        return {
            'status': 'error',
            'error': (
                f'landing-state produced no output (exit_code={completed.returncode}): '
                f'{completed.stderr.strip() or "no stderr"}'
            ),
        }
    try:
        return parse_toon(stdout)
    except Exception as exc:  # pragma: no cover — defensive only
        return {'status': 'error', 'error': f'landing-state output not parseable as TOON: {exc}'}


# ---------------------------------------------------------------------------
# Foreign-path extraction (pure)
# ---------------------------------------------------------------------------


def _foreign_paths_by_deliverable(deliverables: list[dict]) -> list[tuple[int, list[str]]]:
    """Extract ``(deliverable_number, [foreign_path, ...])`` for foreign deliverables.

    Reads the ``foreign`` flags stamped by ``list-deliverables``: a deliverable
    contributes when its roll-up ``foreign`` is true, and only its entries whose
    own ``foreign`` flag is true are collected. Deliverables with no foreign
    entry are dropped. Pure — no I/O — so the population logic is unit-testable
    against a fixture deliverable list.
    """
    result: list[tuple[int, list[str]]] = []
    for deliverable in deliverables:
        if not isinstance(deliverable, dict) or not deliverable.get('foreign'):
            continue
        # All THREE declaration fields — a survey-scope deliverable declares
        # `Files expected to mutate:` instead of `Affected files:`, and its
        # foreign paths must reach this gate like any other. Reading one field
        # made the gate's population a strict subset of the declared surface.
        seen: set[str] = set()
        paths = []
        for field in ('affected_files', 'mutation_scope', 'survey_scope'):
            for entry in deliverable.get(field, []) or []:
                if not isinstance(entry, dict) or not entry.get('foreign'):
                    continue
                path = str(entry.get('path') or '')
                # Deduplicated rather than assumed disjoint. The survey-scope
                # convention requires the two lists to share no path, but that
                # is an AUTHORING rule no check enforces, so a doubly-declared
                # path would otherwise be named twice in the operator's
                # blocking message.
                if path and path not in seen:
                    seen.add(path)
                    paths.append(path)
        if paths:
            result.append((int(deliverable.get('number', 0)), paths))
    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check(
    plan_id: str,
    *,
    deliverables_loader=None,
    root_resolver=None,
    landing_resolver=None,
) -> dict:
    """Evaluate the pre-archive foreign-PR landing gate for ``plan_id``.

    Args:
        plan_id: Plan identifier — used to list the solution outline's
            deliverables.
        deliverables_loader: Optional test seam in place of
            :func:`_list_deliverables`. Signature: ``(plan_id) -> dict``.
        root_resolver: Optional test seam in place of :func:`_resolve_repo_root`.
            Signature: ``(path) -> str | None``.
        landing_resolver: Optional test seam in place of
            :func:`_resolve_landing_state`. Signature: ``(repo_root) -> dict``.

    Returns:
        The gate result dict (see the module docstring for the shape and the
        ``clear`` / ``blocked`` / ``error`` semantics).
    """
    load = deliverables_loader or _list_deliverables
    resolve_root = root_resolver or _resolve_repo_root
    resolve_landing = landing_resolver or _resolve_landing_state

    # The project root is the substrate the foreign classification rests on. When
    # it cannot be resolved, the advisory `foreign` column fails open (stamps
    # every path host), which would let the gate see zero foreign deliverables and
    # clear on absent evidence. Fail closed here so an unresolvable root can never
    # produce a false clear.
    try:
        project_root = cwd_checkout_root()
    except Exception as exc:  # noqa: BLE001 — any resolution failure fails the gate closed
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'project_root_unresolvable',
            'message': f'Could not resolve the project root for foreign classification: {exc}',
        }

    listed = load(plan_id)
    if not isinstance(listed, dict) or listed.get('status') != 'success':
        message = (listed or {}).get('error') or (listed or {}).get('message') or 'list-deliverables did not succeed'
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'deliverables_unavailable',
            'message': str(message),
        }

    foreign = _foreign_paths_by_deliverable(listed.get('deliverables', []))
    if not foreign:
        return {
            'status': 'clear',
            'plan_id': plan_id,
            'project_root': project_root,
            'foreign_deliverable_count': 0,
            'repos': [],
        }

    # Map each foreign repository root to the deliverables that named it, so a
    # repo is resolved (and landing-state polled) once even when several
    # deliverables target it. Deterministic order: first appearance wins.
    root_to_deliverables: dict[str, set[int]] = {}
    root_order: list[str] = []
    unresolved: list[dict] = []
    for number, paths in foreign:
        for path in paths:
            root = resolve_root(path)
            if root is None:
                unresolved.append({'path': path, 'reason': 'repository root not resolvable (foreign tree absent?)'})
                continue
            if root not in root_to_deliverables:
                root_to_deliverables[root] = set()
                root_order.append(root)
            root_to_deliverables[root].add(number)

    repos: list[dict] = []
    blocking: list[dict] = []
    for root in root_order:
        deliverable_numbers = sorted(root_to_deliverables[root])
        landing = resolve_landing(root)
        state = landing.get('landing_state') if isinstance(landing, dict) else None
        if state not in LANDING_STATES:
            # Unreadable, absent, or outside the declared model. Fail closed: an
            # unread or unknown landing state cannot certify the change landed, so
            # it is surfaced as unresolved rather than silently cleared. Validating
            # against LANDING_STATES (not a bare truthiness check) is what refuses
            # an unknown-but-truthy state instead of admitting it.
            reason = (
                (landing or {}).get('error')
                or (landing or {}).get('message')
                or f'landing-state returned {state!r}, not one of {list(LANDING_STATES)}'
            )
            unresolved.append({'path': root, 'reason': f'landing-state unresolved: {reason}'})
            continue
        row = {'repo_root': root, 'landing_state': state, 'deliverables': deliverable_numbers}
        repos.append(row)
        if state == BLOCKING_LANDING_STATE:
            blocking.append({'repo_root': root, 'deliverables': deliverable_numbers})

    # Precedence: a pushed_no_pr block is the loudest; otherwise ANY unresolved
    # item fails the gate closed (indeterminate is not clear); only a
    # fully-read, nothing-blocking population clears.
    if blocking:
        status = 'blocked'
    elif unresolved:
        status = 'error'
    else:
        status = 'clear'

    result: dict = {
        'status': status,
        'plan_id': plan_id,
        'project_root': project_root,
        'foreign_deliverable_count': len(foreign),
        'repos': repos,
    }
    if blocking:
        result['blocking'] = blocking
        result['message'] = (
            f'{len(blocking)} foreign repository/ies are {BLOCKING_LANDING_STATE} — a change is '
            'committed and pushed to a branch that no pull request carries. Open the missing PR(s) '
            'in the foreign repository/ies before archiving; done-ness is measured at the PR, not '
            'the commit.'
        )
    if unresolved:
        result['unresolved'] = unresolved
    if status == 'error':
        result['error'] = 'foreign_landing_indeterminate'
        result.setdefault(
            'message',
            f'{len(unresolved)} foreign repository/ies could not be evaluated (root unresolvable or '
            'landing state unreadable/unknown); refusing to archive on absent evidence. Resolve every '
            'item in unresolved[] before archiving.',
        )
    return result


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`check` — emits TOON.

    Exit code: 0 for a decided verdict the dispatcher reads from ``status``
    (``clear`` or ``blocked``); 1 for ``error`` so a caller relying only on the
    exit code stops rather than proceeding to archive on an un-evaluable gate.
    """
    result = check(args.plan_id)
    print(serialize_toon(result))
    return 1 if result.get('status') == 'error' else 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``check`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Refuse to archive a plan while any foreign deliverable is '
            'pushed_no_pr — a change committed and pushed to a branch that no '
            'pull request carries. Run before archive-plan.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)
    check_parser = sub.add_parser('check', help='Evaluate the pre-archive foreign-PR landing gate', allow_abbrev=False)
    check_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    check_parser.set_defaults(func=cmd_check)
    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'BLOCKING_LANDING_STATE',
    'check',
]
