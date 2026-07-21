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
  all AND are not accounted-for as *settled*. A bot whose review is still
  genuinely awaited (nothing posted, review window still open) leaves no finding,
  so the store is silent on it and it blocks.
- ``pending_bots`` — enabled bots that DID produce a finding but still carry at
  least one ``resolution == 'pending'`` finding (fetched, not yet triaged).

Settled-bots accounting: a bot with ZERO stored findings has NOT necessarily gone
un-heard. A bot is *settled* — accounted for despite filing no actionable
finding — when EITHER it posted at least one comment (even if every comment was
noise-filtered away, so ``count_stored`` is 0) OR its review window has closed
(its completion check reached a terminal state, or it is a no-completion-check
bot whose buffer wait already elapsed). The caller passes such bots via
``settled_bots``; a settled bot with no stored finding is accounted-for, not an
incompleteness. Only a still-awaited bot with nothing posted and an open review
window blocks. This stops the guard manufacturing an infinite loop-back for a bot
whose review landed as pure noise or whose review was skipped/declined.

``complete`` is TRIAGE-STATE AWARE (``triage_ran``):

- ``triage_ran == False`` (the default — the FIND-only automatic-review step,
  BEFORE the dispatcher-owned unified triage runs): a ``pending`` finding is the
  EXPECTED awaiting-triage state and does NOT count as incompleteness, so
  ``complete = not unfetched_bots`` — only an enabled bot that produced NO
  finding blocks. This is what stops the guard manufacturing a loop-back on
  findings that are pending only because triage has not run yet.
- ``triage_ran == True`` (triage has run): a still-``pending`` finding IS a real
  incompleteness, so ``complete = not pending_bots and not unfetched_bots`` —
  today's behavior.

``pending_bots`` and ``unfetched_bots`` are emitted for visibility in BOTH
modes; only their contribution to ``complete`` changes with ``triage_ran``. The
predicate fails closed: a plan with no findings yet reports every enabled bot as
unfetched and ``complete: false`` in both modes, so the guard never marks the
step done on an empty store.

Usage:
    review_completeness.py check --plan-id <id> --enabled-bots <csv> [--settled-bots <csv>] [--triage-ran]
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


def check_completeness(
    plan_id: str,
    enabled_bots: list[str],
    triage_ran: bool = False,
    settled_bots: list[str] | None = None,
) -> dict:
    """Classify each enabled bot against the plan's ``pr-comment`` findings store.

    Args:
        plan_id:       Plan identifier (used to resolve the findings store).
        enabled_bots:  The bot kinds this step drives, in caller order. An empty
                       list is a valid degenerate input (no bots to await →
                       ``complete: true``).
        triage_ran:    Whether the dispatcher-owned unified triage has already
                       run. ``False`` (default — the FIND-only step) treats a
                       ``pending`` finding as the expected awaiting-triage state
                       that does NOT block completeness (only unfetched bots
                       block). ``True`` treats a still-``pending`` finding as a
                       real incompleteness (both pending and unfetched block).
        settled_bots:  Bots the caller has established are accounted-for despite
                       filing no actionable finding — a bot is settled when it
                       posted at least one comment (even if every comment was
                       noise-filtered, so it stored zero findings) OR its review
                       window has closed (completion check terminal, or a
                       no-completion-check bot whose buffer wait elapsed). A
                       settled bot with no stored finding is NOT reported as
                       ``unfetched``; only a still-awaited bot (nothing posted,
                       review window open) with no stored finding blocks. ``None``
                       (default) means no settled signal — behaves as before.

    Returns:
        Dict with the TOON-serialisable summary fields ``status``, ``complete``,
        ``pending_bots``, and ``unfetched_bots``. Per-bot membership is
        mutually exclusive: a bot with no finding that is not settled is
        ``unfetched``; a bot with a finding but an unresolved one is ``pending``;
        a bot whose findings are all resolved, or a bot with no finding that IS
        settled, is complete and appears in neither list. ``pending_bots`` and
        ``unfetched_bots`` are reported for visibility regardless of
        ``triage_ran``; only whether ``pending_bots`` contributes to ``complete``
        depends on it.

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

    settled = set(settled_bots or [])
    pending_bots: list[str] = []
    unfetched_bots: list[str] = []
    for bot in enabled_bots:
        bot_findings = [f for f in findings if f.get('bot_kind') == bot]
        if not bot_findings and bot not in settled:
            # No stored finding AND not accounted-for as settled — still
            # genuinely awaited (nothing posted, review window open). A settled
            # bot with zero findings (posted all-noise, or its review
            # window closed) is accounted-for and does NOT block.
            unfetched_bots.append(bot)
            continue
        if any(f.get('resolution') == 'pending' for f in bot_findings):
            pending_bots.append(bot)

    # Triage-state-aware completeness. Before triage runs (``triage_ran`` False,
    # the FIND-only step) a pending finding is the expected awaiting-triage state
    # and must NOT block — only unfetched enabled bots gate the mark-done. After
    # triage runs, a still-pending finding is a real incompleteness and blocks.
    if triage_ran:
        complete = not pending_bots and not unfetched_bots
    else:
        complete = not unfetched_bots
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
    settled_bots: list[str] = []
    if args.settled_bots:
        settled_bots = [b.strip() for b in args.settled_bots.split(',') if b.strip()]
    payload = check_completeness(
        args.plan_id, enabled_bots, triage_ran=args.triage_ran, settled_bots=settled_bots
    )
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
    check_parser.add_argument(
        '--settled-bots',
        default='',
        help=(
            'Comma-separated list of review-bot kinds the caller has established '
            'are accounted-for despite filing no actionable finding — a bot that '
            'posted a comment (even if all-noise) OR whose review window has '
            'closed (completion check terminal, or a no-completion-check bot whose '
            'buffer wait elapsed). A settled bot with zero stored findings is NOT '
            'reported as unfetched; only a still-awaited bot with nothing posted '
            'blocks.'
        ),
    )
    check_parser.add_argument(
        '--triage-ran',
        action='store_true',
        default=False,
        help=(
            'Whether the dispatcher-owned unified triage has already run. Omit '
            '(the FIND-only default) so a pending finding does NOT block '
            'completeness — only unfetched enabled bots gate the mark-done. Pass '
            'it once triage has run so a still-pending finding blocks as a real '
            'incompleteness.'
        ),
    )
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
