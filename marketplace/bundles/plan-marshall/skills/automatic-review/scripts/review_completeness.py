#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Step-done completeness predicate for the ``plan-marshall:automatic-review`` guard.

Deterministic, no-LLM helper the ``automatic-review`` "Mark Step Complete" guard
consults BEFORE the terminal-clean ``mark-step-done``. It answers one question
against the per-plan ``pr-comment`` findings store: is every enabled review bot
accounted for — meaning each enabled bot both produced at least one fetched
finding AND has no unresolved (``pending``) finding left?

Two independent incompleteness classes are surfaced separately so the guard can
name the offending bots:

- ``unfetched_bots`` — enabled bots that produced NO ``pr-comment`` finding at
  all. A bot whose review was never fetched (posted after the wait step moved on,
  or awaited but never surfaced) leaves no finding, so the store is silent on it.
- ``pending_bots`` — enabled bots that DID produce a finding but still carry at
  least one ``resolution == 'pending'`` finding (fetched, not yet triaged).

``complete`` is ``true`` only when BOTH lists are empty. The predicate fails
closed: a plan with no findings yet reports every enabled bot as unfetched and
``complete: false``, so the guard never marks the step done on an empty store.

Usage:
    review_completeness.py check --plan-id <id> --enabled-bots <csv>
    review_completeness.py --help

Subcommands:
    check  Report whether every enabled bot is fetched-and-resolved for the plan.

Return TOON shape:
    status: success
    complete: true|false
    pending_bots[N]: [bot, ...]      # emitted only when non-empty
    unfetched_bots[N]: [bot, ...]    # emitted only when non-empty
"""

from __future__ import annotations

import argparse
import sys

from _findings_core import query_findings


def check_completeness(plan_id: str, enabled_bots: list[str]) -> dict:
    """Classify each enabled bot against the plan's ``pr-comment`` findings store.

    Args:
        plan_id:       Plan identifier (used to resolve the findings store).
        enabled_bots:  The bot kinds this step drives, in caller order. An empty
                       list is a valid degenerate input (no bots to await →
                       ``complete: true``).

    Returns:
        Dict with the TOON-serialisable summary fields ``status``, ``complete``,
        ``pending_bots``, and ``unfetched_bots``. Per-bot membership is
        mutually exclusive: a bot with no finding is ``unfetched``; a bot with a
        finding but an unresolved one is ``pending``; a bot whose findings are
        all resolved is complete and appears in neither list.

        On a findings-store load failure (corrupt or inaccessible store JSON)
        returns the ``_emit_toon`` error-branch payload
        ``{'status': 'error', 'error': 'load_failure', 'detail': ...}`` instead
        of raising, so the caller renders a structured error and exits non-zero.
    """
    try:
        findings = query_findings(plan_id, finding_type='pr-comment')['findings']
    except (OSError, ValueError) as e:
        return {
            'status': 'error',
            'error': 'load_failure',
            'detail': f'Failed to load findings store: {e}',
        }

    pending_bots: list[str] = []
    unfetched_bots: list[str] = []
    for bot in enabled_bots:
        bot_findings = [f for f in findings if f.get('bot_kind') == bot]
        if not bot_findings:
            unfetched_bots.append(bot)
            continue
        if any(f.get('resolution') == 'pending' for f in bot_findings):
            pending_bots.append(bot)

    complete = not pending_bots and not unfetched_bots
    return {
        'status': 'success',
        'complete': complete,
        'pending_bots': pending_bots,
        'unfetched_bots': unfetched_bots,
    }


def _emit_toon(payload: dict) -> None:
    """Print a minimal TOON block matching the documented contract."""
    print(f'status: {payload.get("status", "success")}')
    if payload.get('status') == 'error':
        print(f'error: {payload.get("error", "unknown")}')
        if 'detail' in payload:
            print(f'detail: {payload["detail"]}')
        return
    print('complete: ' + ('true' if payload['complete'] else 'false'))
    pending = payload['pending_bots']
    if pending:
        print(f'pending_bots[{len(pending)}]: {pending}')
    unfetched = payload['unfetched_bots']
    if unfetched:
        print(f'unfetched_bots[{len(unfetched)}]: {unfetched}')


def cmd_check(args: argparse.Namespace) -> int:
    """Run the completeness predicate and emit the summary TOON to stdout."""
    enabled_bots: list[str] = []
    if args.enabled_bots:
        enabled_bots = [b.strip() for b in args.enabled_bots.split(',') if b.strip()]
    payload = check_completeness(args.plan_id, enabled_bots)
    _emit_toon(payload)
    return 0 if payload.get('status') == 'success' else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description='Step-done completeness predicate for automatic-review.',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    check_parser = subparsers.add_parser(
        'check',
        help='Report whether every enabled bot is fetched-and-resolved',
        allow_abbrev=False,
    )
    check_parser.add_argument('--plan-id', required=True)
    check_parser.add_argument(
        '--enabled-bots',
        default='',
        help='Comma-separated list of enabled review-bot kinds',
    )
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
