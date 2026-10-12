#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-merge findings gate that owns the merge dispatch for ``default:branch-cleanup``.

The pre-merge blocking-findings gate used to be an instruction: run
``phase_handshake findings-check``, parse its ``status``, and only then issue the
merge verb. Neither merge verb required that call, so a skipped or misread check
still merged — and the later archive refusal then stranded a plan whose change
was already on the base branch.

This script turns the instruction into a mechanism. It is the ONLY merge-shaped
dispatch ``branch-cleanup`` issues: it evaluates the blocking-findings invariant
for phase ``6-finalize`` and issues the routed merge verb only when that
evaluation proved the store clean. The merge is therefore unreachable without
the check having run and passed.

* **One verdict vocabulary.** The verdict comes from
  ``_handshake_commands.cmd_findings_check`` called in-process — the very handler
  behind ``phase_handshake findings-check`` — so this gate and that verb cannot
  disagree about what a pending actionable finding is, nor about the fail-closed
  ``query_failed`` reading of an unevaluable count. Like that verb, the gate
  writes no handshake row.
* **The CI merge verbs stay plan-agnostic.** ``ci pr safe-merge`` and
  ``ci pr merge-queue`` carry no plan state; ``--plan-id`` is consumed here, for
  the findings check alone, and is never forwarded to the CI router.

Return shape (CLI emits TOON; programmatic callers consume the dict directly):

* the gate refused — ``status: error`` carrying the findings verdict verbatim
  (``error: blocking_findings_present`` with ``blocking_count`` /
  ``blocking_types`` / ``per_type``, ``error: query_failed``, or any other
  refusal the verdict source returns) plus ``dispatched: false``. The merge
  runner was never invoked;
* the gate passed — the routed verb's payload verbatim plus
  ``findings_gate: clean`` and ``dispatched: true``. Branch on the verb's own
  ``status`` from here, exactly as on a direct verb call.

A malformed invocation (an unknown ``--route``, a ``safe-merge`` route without
``--strategy``, or a safe-merge-only flag on the ``merge-queue`` route) is refused
before the findings check runs, also with ``dispatched: false``. Every such
refusal carries ``refusal_category: invocation`` (:data:`REFUSAL_CATEGORY_FIELD` /
:data:`INVOCATION_REFUSAL`), whatever its ``error`` code, so a caller tells an
invocation refusal (the findings store was never read) from a store-verdict
refusal by that one field instead of by enumerating error codes. A store-verdict
refusal and a dispatched payload never carry the field.

Exit code is ``0`` on every outcome above; the verdict travels in the TOON.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py plan-marshall:phase-6-finalize:pre_merge_gate \\
      merge --plan-id {plan_id} --pr-number {pr_number} --route {route} \\
      --project-dir {worktree_path} [--strategy S] [--delete-branch] [--admin-merge-on-stuck-state]

The findings check and the merge runner are injectable seams so the go/no-go
logic is testable without a findings store, an executor, or a CI provider.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from _handshake_commands import cmd_findings_check
from file_ops import get_executor_path
from toon_parser import parse_toon, serialize_toon

#: The phase whose blocking-findings invariant gates the merge.
FINDINGS_PHASE = '6-finalize'

#: The closed set of merge verbs this gate may dispatch, as ``--route`` values.
#: ``ci pr merge`` and ``ci pr auto-merge`` are deliberately absent: they are not
#: reachable from ``branch-cleanup`` under any condition.
ROUTES: tuple[str, ...] = ('safe-merge', 'merge-queue')

#: The ``--strategy`` values ``ci pr safe-merge`` accepts.
STRATEGIES: tuple[str, ...] = ('squash', 'merge', 'rebase')

#: The payload field that marks a refusal by its category rather than its code.
REFUSAL_CATEGORY_FIELD = 'refusal_category'

#: The :data:`REFUSAL_CATEGORY_FIELD` value every invocation refusal carries — the
#: invocation was malformed and was refused before the findings store was read.
INVOCATION_REFUSAL = 'invocation'

_CI_NOTATION = 'plan-marshall:tools-integration-ci:ci'

FindingsCheck = Callable[[str], dict[str, Any]]
MergeRunner = Callable[[list[str]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Seams (overridable in tests)
# ---------------------------------------------------------------------------


def _check_findings(plan_id: str) -> dict[str, Any]:
    """Evaluate the blocking-findings invariant for :data:`FINDINGS_PHASE`.

    Calls the ``phase_handshake findings-check`` handler in-process, so the
    verdict vocabulary is that verb's own.
    """
    return cmd_findings_check(argparse.Namespace(plan_id=plan_id, phase=FINDINGS_PHASE))


def _run_ci(ci_args: list[str]) -> dict[str, Any]:
    """Run ``ci`` with ``ci_args`` through the executor and return its parsed TOON.

    No subprocess timeout is applied: ``pr safe-merge`` bounds its own readiness
    poll (``--poll-timeout``), and ``pr merge-queue`` returns once the enqueue is
    issued. A verb that produced no output is reported as an error payload rather
    than as a merge outcome.
    """
    executor = get_executor_path()
    completed = subprocess.run(
        [sys.executable, str(executor), _CI_NOTATION, *ci_args],
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = completed.stdout or ''
    if not stdout.strip():
        return {
            'status': 'error',
            'error': 'merge_verb_no_output',
            'message': (
                f'ci {" ".join(ci_args)} produced no output (exit_code={completed.returncode}): '
                f'{completed.stderr.strip() or "no stderr"}'
            ),
        }
    try:
        return parse_toon(stdout)
    except Exception as exc:  # pragma: no cover — defensive only
        return {
            'status': 'error',
            'error': 'merge_verb_unparseable',
            'message': f'ci {" ".join(ci_args)} output not parseable as TOON: {exc}',
        }


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def build_merge_args(
    route: str,
    *,
    project_dir: str,
    pr_number: int,
    strategy: str | None = None,
    delete_branch: bool = False,
    admin_merge_on_stuck_state: bool = False,
) -> list[str]:
    """Return the ``ci`` argument vector for ``route``.

    ``--project-dir`` is the router-level flag and precedes the ``pr`` verb.
    The safe-merge pass-through flags are forwarded on the ``safe-merge`` route
    only; the ``merge-queue`` enqueue takes the PR number alone.
    """
    args = ['--project-dir', project_dir, 'pr', route, '--pr-number', str(pr_number)]
    if route == 'safe-merge':
        args += ['--strategy', str(strategy)]
        if delete_branch:
            args.append('--delete-branch')
        if admin_merge_on_stuck_state:
            args.append('--admin-merge-on-stuck-state')
    return args


def _invocation_refusal(
    plan_id: str,
    route: str,
    *,
    strategy: str | None,
    delete_branch: bool,
    admin_merge_on_stuck_state: bool,
) -> dict[str, Any] | None:
    """Refuse an invocation whose flags do not fit its route, before any check runs.

    Every refusal is built by one constructor that stamps
    ``refusal_category: invocation``, so any refusal code this function gains
    carries the category without its consumers having to name the new code.
    """

    def _refuse(error: str, message: str) -> dict[str, Any]:
        return {
            'status': 'error',
            'error': error,
            REFUSAL_CATEGORY_FIELD: INVOCATION_REFUSAL,
            'plan_id': plan_id,
            'route': route,
            'dispatched': False,
            'message': message,
        }

    if route not in ROUTES:
        return _refuse('unknown_route', f'--route must be one of {list(ROUTES)}, got {route!r}')
    if route == 'safe-merge' and not strategy:
        return _refuse(
            'strategy_required',
            'the safe-merge route requires --strategy; nothing was checked and nothing was merged',
        )
    if route == 'merge-queue' and (strategy or delete_branch or admin_merge_on_stuck_state):
        return _refuse(
            'flag_not_applicable_to_route',
            '--strategy, --delete-branch and --admin-merge-on-stuck-state apply to the safe-merge '
            'route only; the merge-queue enqueue takes the PR number alone and the platform owns '
            'the merge method and the head-branch deletion. Nothing was checked and nothing was merged',
        )
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def merge(
    plan_id: str,
    *,
    route: str,
    pr_number: int,
    project_dir: str,
    strategy: str | None = None,
    delete_branch: bool = False,
    admin_merge_on_stuck_state: bool = False,
    findings_check: FindingsCheck | None = None,
    merge_runner: MergeRunner | None = None,
) -> dict[str, Any]:
    """Issue the routed merge verb only when the findings store is proven clean.

    Args:
        plan_id: Plan whose ``6-finalize`` findings store is evaluated. Not
            forwarded to the CI router.
        route: ``safe-merge`` or ``merge-queue`` (see :data:`ROUTES`).
        pr_number: PR to merge or enqueue.
        project_dir: Working tree the ``ci`` router binds to.
        strategy: ``safe-merge`` strategy; required on that route only.
        delete_branch: ``safe-merge`` pass-through.
        admin_merge_on_stuck_state: ``safe-merge`` pass-through.
        findings_check: Optional seam in place of :func:`_check_findings`.
            Signature: ``(plan_id) -> dict``.
        merge_runner: Optional seam in place of :func:`_run_ci`. Signature:
            ``(ci_args) -> dict``.

    Returns:
        The refusal payload plus ``dispatched: false``, or the routed verb's
        payload plus ``findings_gate: clean`` and ``dispatched: true``.
    """
    refusal = _invocation_refusal(
        plan_id,
        route,
        strategy=strategy,
        delete_branch=delete_branch,
        admin_merge_on_stuck_state=admin_merge_on_stuck_state,
    )
    if refusal is not None:
        return refusal

    verdict = (findings_check or _check_findings)(plan_id)
    if verdict.get('status') != 'success':
        # blocking_findings_present, query_failed, or any other refusal the
        # verdict source returns: the payload travels verbatim, nothing merges.
        # The invocation category is never forwarded — the store WAS read here.
        store_refusal = {k: v for k, v in verdict.items() if k != REFUSAL_CATEGORY_FIELD}
        return {**store_refusal, 'dispatched': False}
    if verdict.get('blocking_count') != 0:
        # A success envelope that does not carry a measured zero is not a clean
        # store. Fail closed rather than read an absent count as zero.
        return {
            'status': 'error',
            'error': 'findings_verdict_unrecognised',
            'plan_id': plan_id,
            'phase': FINDINGS_PHASE,
            'blocking_count': verdict.get('blocking_count'),
            'dispatched': False,
            'message': (
                'findings-check returned status: success without blocking_count: 0, so the store '
                'was not proven clean; refusing to merge'
            ),
        }

    ci_args = build_merge_args(
        route,
        project_dir=project_dir,
        pr_number=pr_number,
        strategy=strategy,
        delete_branch=delete_branch,
        admin_merge_on_stuck_state=admin_merge_on_stuck_state,
    )
    payload = (merge_runner or _run_ci)(ci_args)
    return {**payload, 'findings_gate': 'clean', 'dispatched': True}


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_merge(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`merge` — emits TOON and exits 0 on every outcome."""
    result = merge(
        args.plan_id,
        route=args.route,
        pr_number=args.pr_number,
        project_dir=args.project_dir,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
        admin_merge_on_stuck_state=args.admin_merge_on_stuck_state,
    )
    print(serialize_toon(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``merge`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Evaluate the 6-finalize blocking-findings invariant and, only on a clean '
            'store, issue the routed merge verb (ci pr safe-merge or ci pr merge-queue).'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)
    merge_parser = sub.add_parser(
        'merge',
        help='Gate the merge dispatch on a clean pre-merge findings store',
        allow_abbrev=False,
    )
    merge_parser.add_argument('--plan-id', required=True, dest='plan_id', help='Plan identifier')
    merge_parser.add_argument('--pr-number', required=True, type=int, dest='pr_number', help='PR number')
    merge_parser.add_argument(
        '--route',
        required=True,
        choices=ROUTES,
        help='Merge verb to dispatch on a clean store: safe-merge (immediate) or merge-queue (enqueue)',
    )
    merge_parser.add_argument(
        '--project-dir',
        required=True,
        dest='project_dir',
        help='Working tree the ci router binds to (forwarded as the router-level --project-dir)',
    )
    merge_parser.add_argument(
        '--strategy',
        choices=STRATEGIES,
        default=None,
        help='safe-merge route only (required there): merge strategy forwarded to ci pr safe-merge',
    )
    merge_parser.add_argument(
        '--delete-branch',
        action='store_true',
        dest='delete_branch',
        help='safe-merge route only: forwarded to ci pr safe-merge',
    )
    merge_parser.add_argument(
        '--admin-merge-on-stuck-state',
        action='store_true',
        dest='admin_merge_on_stuck_state',
        help='safe-merge route only: forwarded to ci pr safe-merge',
    )
    merge_parser.set_defaults(func=cmd_merge)
    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'FINDINGS_PHASE',
    'INVOCATION_REFUSAL',
    'REFUSAL_CATEGORY_FIELD',
    'ROUTES',
    'STRATEGIES',
    'build_merge_args',
    'merge',
]
