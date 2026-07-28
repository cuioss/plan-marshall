#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Step-done PARTICIPATION predicate for the ``plan-marshall:automatic-review`` guard.

Deterministic, no-LLM helper the ``automatic-review`` "Mark Step Complete" guard
consults BEFORE the terminal-clean ``mark-step-done``. It answers one question
against the per-plan ``pr-comment`` findings store: is every REQUIRED review bot
accounted for — meaning each required bot is a PROVEN participant AND has no
unresolved (``pending``) finding left?

**The verdict proves PARTICIPATION only — never review QUALITY.** ``complete:
true`` means every required bot was observed publishing a review artifact against
this diff and its findings are triaged. It does NOT mean the diff was reviewed
well, or reviewed meaningfully at all. A bot can publish a valid participation
artifact and still miss every real defect: on #1027 PR-Agent posted its Guide —
valid participation — while reporting "no major issues" on a diff in which
CodeRabbit found two Major defects. **A satisfied quorum is not a reviewed diff**,
and no caller may render it as one. Every field this module returns is named and
documented against that ceiling.

Participation is EVIDENCE-TYPED, not presence-typed. The caller supplies
``participated_bots`` as ``bot_kind:evidence_kind`` pairs produced by
``github_pr fetch_findings``; a bot counts as a proven participant only when its
``evidence_kind`` is one of the publish shapes its registry record declares in
``participation_evidence``. The admissible vocabulary is CLOSED to publish shapes,
and that closure is the structural guard behind the **diff-derived-evidence rule**:
a publish shape is an artifact the bot produced against the diff, whereas a
body-derived signal — anything a reviewer could have produced by reading the PR
description alone, including the Intent section the PR body carries — has no
publish shape and therefore no admissible evidence kind. It can never discharge a
review obligation. A bot declaring no evidence shape resolves FAIL-CLOSED: it can
never be proven a participant.

**The quorum is over ``required_bots`` ONLY.** An optional bot never gates
``complete``: its silence is not a failure, so it can never hold the step open.
Optional bots are still classified and reported for visibility — the guard shows
what the optional reviewers did — but their membership in ``pending_bots`` /
``unfetched_bots`` is informational and contributes nothing to ``complete``. See
``automatic-review/standards/bot-participation-contract.md`` for the
required-vs-optional semantics.

Two independent incompleteness classes are surfaced separately so the guard can
name the offending bots:

- ``unfetched_bots`` — bots that produced NO ``pr-comment`` finding at all AND
  are not accounted-for as *settled*. A bot whose review is still genuinely
  awaited (nothing posted, review window still open) leaves no finding, so the
  store is silent on it. Only a REQUIRED entry here blocks.
- ``pending_bots`` — bots that DID produce a finding but still carry at least one
  ``resolution == 'pending'`` finding (fetched, not yet triaged). Only a REQUIRED
  entry here blocks, and only once triage has run.

Participation accounting: a bot with ZERO stored findings has NOT necessarily gone
un-heard. A proven participant that filed no actionable finding reviewed the diff
and had nothing to say — ``participated_but_empty``, an accounted-for outcome, not
an incompleteness. This stops the guard manufacturing an infinite loop-back for a
bot whose review landed as pure noise.

Every required bot is classified into exactly one **state**. Five of the six are
the closed non-participation taxonomy owned by
``standards/bot-participation-contract.md`` (``absent``, ``in_progress``,
``refused_awaitable``, ``refused_hard``, ``participated_but_empty``); the sixth,
``participated``, is its complement — the bot delivered a usable review — and is
not a non-participation. The refusal states are split by the refusing bot's
registry ``rate_limit_class``, so no bot-name literal appears here.

``complete`` is TRIAGE-STATE AWARE (``triage_ran``):

- ``triage_ran == False`` (the default — the FIND-only automatic-review step,
  BEFORE the dispatcher-owned unified triage runs): a ``pending`` finding is the
  EXPECTED awaiting-triage state and does NOT count as incompleteness, so
  ``complete`` is false only when a REQUIRED bot produced NO finding. This is what
  stops the guard manufacturing a loop-back on findings that are pending only
  because triage has not run yet.
- ``triage_ran == True`` (triage has run): a still-``pending`` finding on a
  REQUIRED bot IS a real incompleteness and blocks alongside an unfetched
  required bot.

``pending_bots`` and ``unfetched_bots`` are emitted for visibility in BOTH modes
and span required ∪ optional; only the REQUIRED subset contributes to
``complete``, and only ``pending``'s contribution additionally depends on
``triage_ran``. The predicate fails closed over the required set: a plan with no
findings yet reports every required bot as unfetched and ``complete: false`` in
both modes, so the guard never marks the step done on an empty store. An EMPTY
``required_bots`` is a valid configured state — the quorum is vacuously satisfied
and ``complete`` is true.

Usage:
    review_completeness.py check --plan-id <id> --required-bots <csv> [--optional-bots <csv>] [--participated-bots <csv>] [--in-progress-bots <csv>] [--refused-bots <csv>] [--triage-ran]
    review_completeness.py --help

Subcommands:
    check  Report whether every REQUIRED bot's PARTICIPATION is proven and triaged.

Return TOON shape:
    status: success
    participation_complete: true|false
    proves: participation_only
    pending_bots[N]: [bot, ...]          # emitted only when non-empty
    unproven_bots[N]: [bot, ...]         # emitted only when non-empty
    bot_states[N]{bot_kind,state}: ...   # one row per required ∪ optional bot
"""

from __future__ import annotations

import argparse
import sys

import bot_registry
from _findings_core import query_findings

# The state every classified bot resolves to. Five members are the closed
# NON-participation taxonomy owned by
# ``standards/bot-participation-contract.md``; ``participated`` is its complement
# (the bot delivered a usable review) and is deliberately NOT a sixth member of
# that taxonomy — it is the success case the taxonomy exists to distinguish from.
STATE_ABSENT = 'absent'
STATE_IN_PROGRESS = 'in_progress'
STATE_REFUSED_AWAITABLE = 'refused_awaitable'
STATE_REFUSED_HARD = 'refused_hard'
STATE_PARTICIPATED_BUT_EMPTY = 'participated_but_empty'
STATE_PARTICIPATED = 'participated'

# The states that leave a REQUIRED bot's participation unproven. A required bot in
# any of these holds the step open; ``participated_but_empty`` and ``participated``
# are both accounted-for outcomes and never block.
_UNPROVEN_STATES = frozenset(
    {STATE_ABSENT, STATE_IN_PROGRESS, STATE_REFUSED_AWAITABLE, STATE_REFUSED_HARD}
)


def parse_participation(raw: str | None) -> dict[str, str]:
    """Parse the ``bot_kind:evidence_kind`` CSV into a bot -> evidence-kind map.

    Only pairs whose ``evidence_kind`` is one of the publish shapes the bot's
    registry record declares in ``participation_evidence`` are admitted; anything
    else is dropped. This is where the diff-derived-evidence rule is ENFORCED
    rather than merely asserted: the admissible vocabulary is closed to publish
    shapes, so a body-derived signal — anything a reviewer could have produced by
    reading the PR description alone — carries no admissible evidence kind and
    cannot be laundered in as participation.

    A bare ``bot_kind`` with no ``:evidence_kind`` is dropped for the same reason:
    unqualified presence is exactly the claim this module stopped accepting. A bot
    whose registry record declares no evidence shape can never match, which is the
    fail-closed default.
    """
    proven: dict[str, str] = {}
    for entry in (raw or '').split(','):
        bot_kind, _, evidence_kind = entry.strip().partition(':')
        bot_kind = bot_kind.strip()
        evidence_kind = evidence_kind.strip()
        if not bot_kind or not evidence_kind:
            continue
        if evidence_kind in bot_registry.participation_evidence(bot_kind):
            proven[bot_kind] = evidence_kind
    return proven


def classify_bot(
    bot: str,
    proven_participants: dict[str, str],
    has_findings: bool,
    in_progress: set[str],
    refused: set[str],
) -> str:
    """Return the single state ``bot`` resolves to.

    The branches are evaluated in evidence-strength order, so exactly one state is
    assigned. Proven participation is checked FIRST because it is positive,
    diff-derived evidence the bot actually reviewed — it outranks the awaiting and
    refusal signals, which are both statements about the absence of a review.

    - **``participated``** — proven participant that filed at least one finding.
    - **``participated_but_empty``** — proven participant that filed none. It did
      its pass and had nothing actionable to say; accounted-for, never a failure.
    - **``refused_awaitable`` / ``refused_hard``** — the bot published a refusal.
      Which member is decided by its registry ``rate_limit_class``: a window that
      reopens on its own is awaitable, anything else is not. No bot-name literal.
    - **``in_progress``** — the bot's review is still running.
    - **``absent``** — no evidence of any kind. The fail-closed default, which is
      also where a bot declaring NO evidence shape necessarily lands, since it can
      never be proven a participant.
    """
    if bot in proven_participants:
        return STATE_PARTICIPATED if has_findings else STATE_PARTICIPATED_BUT_EMPTY
    if bot in refused:
        awaitable = bot_registry.rate_limit_class(bot) == 'awaitable_window'
        return STATE_REFUSED_AWAITABLE if awaitable else STATE_REFUSED_HARD
    if bot in in_progress:
        return STATE_IN_PROGRESS
    return STATE_ABSENT


def check_completeness(
    plan_id: str,
    required_bots: list[str],
    optional_bots: list[str] | None = None,
    triage_ran: bool = False,
    participated_bots: dict[str, str] | None = None,
    in_progress_bots: list[str] | None = None,
    refused_bots: list[str] | None = None,
) -> dict:
    """Classify each bot's PARTICIPATION against the plan's ``pr-comment`` findings store.

    This proves participation, never review quality — see the module docstring.

    Args:
        plan_id:           Plan identifier (used to resolve the findings store).
        required_bots:     The bot kinds whose participation is REQUIRED, in
                           caller order. These — and only these — form the quorum.
                           An empty list is a valid configured state (nothing to
                           await → ``participation_complete: true``).
        optional_bots:     The bot kinds whose participation is OPTIONAL. They are
                           classified and reported for visibility but NEVER gate
                           the verdict — an optional bot's silence is not a
                           failure. ``None`` (default) means none.
        triage_ran:        Whether the dispatcher-owned unified triage has already
                           run. ``False`` (default — the FIND-only step) treats a
                           ``pending`` finding as the expected awaiting-triage
                           state that does NOT block (only unproven bots block).
                           ``True`` treats a still-``pending`` finding as a real
                           incompleteness.
        participated_bots: The EVIDENCE-TYPED participation map (``bot_kind`` ->
                           ``evidence_kind``) from ``github_pr fetch_findings``,
                           already filtered to admissible publish shapes by
                           :func:`parse_participation`. Unqualified presence is
                           NOT accepted — only a declared publish shape proves
                           participation, which is what keeps a body-derived
                           signal from discharging a review obligation.
        in_progress_bots:  Bots whose review is still running (completion check
                           not yet terminal) when the poll budget expired.
        refused_bots:      Bots observed publishing a refusal notice. The refusal
                           STATE is split by each bot's registry
                           ``rate_limit_class``; the caller supplies only the
                           observation, never the classification.

    Returns:
        Dict with the TOON-serialisable fields ``status``,
        ``participation_complete``, ``proves`` (always ``participation_only`` — the
        machine-readable form of the ceiling), ``pending_bots``, ``unproven_bots``,
        and ``bot_states`` (one ``{bot_kind, state}`` record per classified bot).

        ``bot_states`` spans required ∪ optional and assigns exactly one state per
        bot. ``unproven_bots`` is the subset whose state leaves participation
        unproven (``absent`` / ``in_progress`` / either refusal member);
        ``pending_bots`` is the subset carrying an untriaged finding. Both span
        required ∪ optional for visibility, but only the REQUIRED subset gates
        ``participation_complete``, and only ``pending``'s contribution
        additionally depends on ``triage_ran``.

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

    proven = dict(participated_bots or {})
    in_progress = set(in_progress_bots or [])
    refused = set(refused_bots or [])
    required_set = set(required_bots)
    # Required first, then the optional bots not already listed as required, so
    # the reported lists read in a stable, caller-meaningful order.
    classified = list(required_bots) + [b for b in (optional_bots or []) if b not in required_set]

    bot_states: list[dict[str, str]] = []
    pending_bots: list[str] = []
    unproven_bots: list[str] = []
    for bot in classified:
        bot_findings = [f for f in findings if f.get('bot_kind') == bot]
        state = classify_bot(bot, proven, bool(bot_findings), in_progress, refused)
        bot_states.append({'bot_kind': bot, 'state': state})
        if state in _UNPROVEN_STATES:
            unproven_bots.append(bot)
            continue
        if any(f.get('resolution') == 'pending' for f in bot_findings):
            pending_bots.append(bot)

    # The quorum is over the REQUIRED set only — an optional bot appears in the
    # reported lists for visibility but never gates the mark-done, because its
    # silence is not a failure.
    required_unproven = [b for b in unproven_bots if b in required_set]
    required_pending = [b for b in pending_bots if b in required_set]

    # Triage-state-aware verdict. Before triage runs (``triage_ran`` False, the
    # FIND-only step) a pending finding is the expected awaiting-triage state and
    # must NOT block — only unproven REQUIRED bots gate the mark-done. After triage
    # runs, a still-pending required finding is a real incompleteness.
    if triage_ran:
        participation_complete = not required_pending and not required_unproven
    else:
        participation_complete = not required_unproven
    return {
        'status': 'success',
        'participation_complete': participation_complete,
        # Machine-readable restatement of the ceiling, so a consumer cannot read
        # this envelope as a statement about review quality without ignoring a
        # field that says otherwise in as many words.
        'proves': 'participation_only',
        'pending_bots': pending_bots,
        'unproven_bots': unproven_bots,
        'bot_states': bot_states,
    }


def _emit_toon(payload: dict) -> None:
    """Print a minimal TOON block matching the documented contract."""
    print(f'status: {payload.get("status", "success")}')
    if payload.get('status') == 'error':
        print(f'error: {payload.get("error", "unknown")}')
        if 'detail' in payload:
            print(f'detail: {payload["detail"]}')
        return
    print('participation_complete: ' + ('true' if payload['participation_complete'] else 'false'))
    print(f'proves: {payload["proves"]}')
    pending = payload['pending_bots']
    if pending:
        print(f'pending_bots[{len(pending)}]: {pending}')
    unproven = payload['unproven_bots']
    if unproven:
        print(f'unproven_bots[{len(unproven)}]: {unproven}')
    states = payload['bot_states']
    if states:
        print(f'bot_states[{len(states)}]{{bot_kind,state}}:')
        for record in states:
            print(f'  {record["bot_kind"]},{record["state"]}')


def cmd_check(args: argparse.Namespace) -> int:
    """Run the completeness predicate and emit the summary TOON to stdout."""
    required_bots: list[str] = []
    if args.required_bots:
        required_bots = [b.strip() for b in args.required_bots.split(',') if b.strip()]
    optional_bots: list[str] = []
    if args.optional_bots:
        optional_bots = [b.strip() for b in args.optional_bots.split(',') if b.strip()]
    in_progress_bots: list[str] = []
    if args.in_progress_bots:
        in_progress_bots = [b.strip() for b in args.in_progress_bots.split(',') if b.strip()]
    refused_bots: list[str] = []
    if args.refused_bots:
        refused_bots = [b.strip() for b in args.refused_bots.split(',') if b.strip()]
    payload = check_completeness(
        args.plan_id,
        required_bots,
        optional_bots=optional_bots,
        triage_ran=args.triage_ran,
        participated_bots=parse_participation(args.participated_bots),
        in_progress_bots=in_progress_bots,
        refused_bots=refused_bots,
    )
    _emit_toon(payload)
    return 0 if payload.get('status') == 'success' else 1


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=(
            'Step-done PARTICIPATION predicate for automatic-review. Proves that '
            'every required bot published a review artifact against this diff — '
            'never that the diff was reviewed well.'
        ),
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    check_parser = subparsers.add_parser(
        'check',
        help="Report whether every REQUIRED bot's participation is proven and triaged",
        allow_abbrev=False,
    )
    check_parser.add_argument('--plan-id', required=True)
    check_parser.add_argument(
        '--required-bots',
        default='',
        help=(
            'Comma-separated review-bot kinds whose participation is REQUIRED. '
            'These and only these form the completeness quorum — a required '
            "bot's silence blocks the mark-done. An empty list is a valid "
            'configured state (quorum vacuously satisfied).'
        ),
    )
    check_parser.add_argument(
        '--optional-bots',
        default='',
        help=(
            'Comma-separated review-bot kinds whose participation is OPTIONAL. '
            'Classified and reported for visibility but NEVER gating: an optional '
            "bot's silence is not a failure and never blocks the mark-done."
        ),
    )
    check_parser.add_argument(
        '--participated-bots',
        default='',
        help=(
            'Comma-separated EVIDENCE-TYPED participation pairs, each '
            'bot_kind:evidence_kind, as reported by github_pr fetch_findings. A '
            "pair is admitted only when evidence_kind is one of that bot's "
            'declared participation_evidence publish shapes; a bare bot_kind with '
            'no evidence_kind is rejected, because unqualified presence does not '
            'prove a bot reviewed this diff. This proves PARTICIPATION only, never '
            'review quality.'
        ),
    )
    check_parser.add_argument(
        '--in-progress-bots',
        default='',
        help=(
            'Comma-separated review-bot kinds whose review was still running '
            '(completion check not yet terminal) when the poll budget expired. '
            'A required bot here is classified in_progress and blocks.'
        ),
    )
    check_parser.add_argument(
        '--refused-bots',
        default='',
        help=(
            'Comma-separated review-bot kinds observed publishing a refusal '
            'notice. Supply only the observation — the refusal is split into '
            "refused_awaitable / refused_hard from each bot's registry "
            'rate_limit_class, never by the caller.'
        ),
    )
    check_parser.add_argument(
        '--triage-ran',
        action='store_true',
        default=False,
        help=(
            'Whether the dispatcher-owned unified triage has already run. Omit '
            '(the FIND-only default) so a pending finding does NOT block '
            'completeness — only unfetched REQUIRED bots gate the mark-done. Pass '
            'it once triage has run so a still-pending required finding blocks as '
            'a real incompleteness.'
        ),
    )
    check_parser.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
