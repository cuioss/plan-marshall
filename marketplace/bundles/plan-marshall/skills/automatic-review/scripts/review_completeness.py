#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Step-done PARTICIPATION predicate for the ``plan-marshall:automatic-review`` guard.

Deterministic, no-LLM helper the ``automatic-review`` "Mark Step Complete" guard
consults BEFORE the terminal-clean ``mark-step-done``. It answers one question
against the per-plan ``pr-comment`` findings store: is every REQUIRED review bot
accounted for — meaning each required bot is a PROVEN participant AND has no
unresolved (``pending``) finding left?

**The verdict proves PARTICIPATION only — never review QUALITY.**
``participation_complete: true`` means every required bot was observed
publishing a review artifact against this diff and its findings are triaged. It
does NOT mean the diff was reviewed well, or reviewed meaningfully at all. A bot
can publish a valid participation artifact and still miss every real defect: on
#1027 PR-Agent posted its Guide — valid participation — while reporting "no
major issues" on a diff in which CodeRabbit found two Major defects. **A
satisfied quorum is not a reviewed diff**, and no caller may render it as one.
Every field this module returns is named and documented against that ceiling.

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
``participation_complete``: its silence is not a failure, so it can never hold
the step open. Optional bots are still classified and reported for visibility —
the guard shows what the optional reviewers did — but their membership in
``pending_bots`` / ``unproven_bots`` is informational and contributes nothing to
``participation_complete``. See
``automatic-review/standards/bot-participation-contract.md`` for the
required-vs-optional semantics.

Two independent incompleteness classes are surfaced separately so the guard can
name the offending bots:

- ``unproven_bots`` — bots that produced NO ``pr-comment`` finding at all AND
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

Every required bot is classified into exactly one **state**. Nine of the ten are
the closed non-participation taxonomy owned by
``standards/bot-participation-contract.md`` (``absent``, ``in_progress``,
``refused_awaitable``, ``refused_hard``, ``refused_unknown``,
``participated_but_empty``, ``participated_stale``, ``declined``,
``not_triggered``); the tenth, ``participated``, is its complement — the bot
delivered a usable review — and is not a non-participation. The refusal states are
split ONE-TO-ONE by the refusing bot's registry three-valued ``rate_limit_class``
(``awaitable_window`` -> ``refused_awaitable``, ``hard_quota`` -> ``refused_hard``,
``unknown`` -> ``refused_unknown``), so no bot-name literal appears here and no
class value is collapsed into another. ``refused_unknown`` is its OWN member rather
than being folded into ``refused_hard``: a declared *we-do-not-know* is not a
positive *hard quota* finding, and rendering it as one steered an operator toward
"waiting is futile, force it" for a refusal shape that had simply never been
observed.

``participation_complete`` is TRIAGE-STATE AWARE (``triage_ran``):

- ``triage_ran == False`` (the default — the FIND-only automatic-review step,
  BEFORE the dispatcher-owned unified triage runs): a ``pending`` finding is the
  EXPECTED awaiting-triage state and does NOT count as incompleteness, so
  ``participation_complete`` is false only when a REQUIRED bot produced NO
  finding. This is what stops the guard manufacturing a loop-back on findings
  that are pending only because triage has not run yet.
- ``triage_ran == True`` (triage has run): a still-``pending`` finding on a
  REQUIRED bot IS a real incompleteness and blocks alongside an unproven
  required bot.

``pending_bots`` and ``unproven_bots`` are emitted for visibility in BOTH modes
and span required ∪ optional; only the REQUIRED subset contributes to
``participation_complete``, and only ``pending``'s contribution additionally
depends on ``triage_ran``. The predicate fails closed over the required set: a
plan with no findings yet reports every required bot as ``absent`` and
``participation_complete: false`` in both modes, so the guard never marks the
step done on an empty store. An EMPTY ``required_bots`` is a valid configured
state — the quorum is vacuously satisfied and ``participation_complete`` is
``true``.

Usage:
    review_completeness.py check --plan-id <id> [--required-bots [<csv>]] [--optional-bots [<csv>]] [--participated-bots [<csv>]] [--in-progress-bots [<csv>]] [--refused-bots [<csv>]] [--stale-participation-bots [<csv>]] [--declined-bots [<csv>]] [--not-triggered] [--triage-ran]
    review_completeness.py deficit --plan-id <id> [--required-bots [<csv>]] [--optional-bots [<csv>]] [--participated-bots [<csv>]] [--in-progress-bots [<csv>]] [--refused-bots [<csv>]] [--stale-participation-bots [<csv>]] [--declined-bots [<csv>]] [--not-triggered] [--min-deficit <n>]
    review_completeness.py --help

Every list flag above takes an OPTIONAL value: it may be supplied bare (the flag
with no value at all), which reads exactly the same as omitting it — the empty
list. A caller that interpolates an empty variable into the command line
therefore produces the empty-list reading rather than an argparse rejection. The
relaxation is a parser-robustness change ONLY: an empty required-bots list is
still the vacuously-satisfied quorum, and no empty list ever launders an
unproven bot into a pass.

The list flags split into two FORMS, and a token forwarded to the wrong form is a
loud caller error rather than a silent misparse. The two EVIDENCE-TYPED (pair-form)
flags — ``--participated-bots`` and ``--stale-participation-bots`` — take
``bot_kind:evidence_kind`` pairs, the exact shape ``github_pr fetch_findings`` emits
in ``participated_bots[]`` and ``stale_participation_bots[]``, so the producer's
output forwards to each verbatim. The remaining list flags are bare-form
(``bot_kind`` tokens only). A bare kind on a pair-form flag, or a pair on a
bare-form flag, is REJECTED as a malformed caller error (``status: error``,
non-zero exit, no ``participation_complete`` field — read as an UNKNOWN verdict):
a dropped bare kind would resolve to ``absent`` (a blocking member) and a misread
pair would match no configured bot, both manufacturing a confident verdict over a
misparsed population. An empty value is the empty list, never a malformed token.

Subcommands:
    check    Report whether every REQUIRED bot's PARTICIPATION is proven and triaged.
    deficit  Report whether a REQUIRED reviewer under-produced against a real
             baseline — a REVIEWER-QUALITY signal, never a merge verdict.

Return TOON shape (check):
    status: success
    participation_complete: true|false
    proves: participation_only
    review_state_summary: <compact reviewer-state distribution>   # emitted only when non-empty
    pending_bots[N]:                     # emitted only when non-empty
      - bot
    unproven_bots[N]:                    # emitted only when non-empty
      - bot
    bot_states[N]{bot_kind,state}: ...   # one row per required ∪ optional bot

Return TOON shape (deficit):
    status: success
    verdict: deficit|clean|unassessable
    proves: reviewer_quality_only
    gates_merge: false
    baseline_max: <int>
    baseline_reviewers[N]: ...           # emitted only when non-empty
    required_reviewed[N]: ...            # emitted only when non-empty
    deficit_reviewers[N]{bot_kind,findings,deficit}: ...   # emitted only when non-empty
    reviewers[N]{bot_kind,reviewed,finding_count,state}: ...  # the published population
"""

from __future__ import annotations

import argparse
import sys

import bot_registry
from _findings_core import query_findings

# The state every classified bot resolves to. Nine members are the closed
# NON-participation taxonomy owned by
# ``standards/bot-participation-contract.md``; ``participated`` is its complement
# (the bot delivered a usable review) and is deliberately NOT a tenth member of
# that taxonomy — it is the success case the taxonomy exists to distinguish from.
STATE_ABSENT = 'absent'
STATE_IN_PROGRESS = 'in_progress'
STATE_REFUSED_AWAITABLE = 'refused_awaitable'
STATE_REFUSED_HARD = 'refused_hard'
# The refusing bot's registry ``rate_limit_class`` declared ``unknown`` (or a value
# that is neither ``awaitable_window`` nor ``hard_quota``): the bot published a
# refusal, but its refusal shape has never been observed, so whether the window
# reopens is genuinely not known. Its OWN member rather than a fold into
# ``refused_hard`` — a binary ``== 'awaitable_window'`` test over the three-valued
# field rendered this declared ignorance as a positive hard-quota finding.
STATE_REFUSED_UNKNOWN = 'refused_unknown'
STATE_PARTICIPATED_BUT_EMPTY = 'participated_but_empty'
# Never the bare ``stale``: the state is a PARTICIPATION that went stale, and the
# short name loses the distinction from a bot that never published at all.
STATE_PARTICIPATED_STALE = 'participated_stale'
# The bot was asked to review the merge candidate (a re-review was triggered) and
# answered WITHOUT producing a review of it — an incremental-review DECLINE: a
# comment carrying no reviewed-commit SHA (``head_sha_verified: false``) rather than
# a review of this HEAD. Distinct from ``participated_stale`` (a review that exists
# but predates the merge candidate) and from the refusal members (an explicit
# rate-limit / quota / size notice): the bot engaged but declined this commit, so
# re-triggering it produces another decline rather than a review.
STATE_DECLINED = 'declined'
# A REFINEMENT of ``absent``, not a sibling of it: the bot published nothing AND
# nothing could have been published, because no pull_request-event run exists for
# the PR at all. It is PR-wide rather than per-bot — the same condition holds for
# every bot on the PR — which is why its input is a single bool rather than an
# observation set keyed by bot.
STATE_NOT_TRIGGERED = 'not_triggered'
STATE_PARTICIPATED = 'participated'

# The states that leave a REQUIRED bot's participation unproven. A required bot in
# any of these holds the step open; ``participated_but_empty`` and ``participated``
# are both accounted-for outcomes and never block. ``participated_stale`` DOES
# block — the bot published against an earlier HEAD, so nothing has reviewed the
# current diff — but its remedy is a re-review trigger, not the non-participation
# escalation ``absent`` calls for.
_UNPROVEN_STATES = frozenset(
    {
        STATE_ABSENT,
        STATE_IN_PROGRESS,
        STATE_REFUSED_AWAITABLE,
        STATE_REFUSED_HARD,
        STATE_REFUSED_UNKNOWN,
        STATE_PARTICIPATED_STALE,
        STATE_DECLINED,
        STATE_NOT_TRIGGERED,
    }
)

# The states that mean a reviewer REVIEWED THE DIFF AT ALL — the reviewed-at-all
# predicate the counting rule and the deficit signal (below) both read. Both are a
# proven publish shape against the merge candidate: ``participated`` filed at least
# one finding, ``participated_but_empty`` reviewed and found nothing. Every other
# state is a non-review (a refusal, an absence, a stale or in-flight publish), so it
# can be neither a deficit baseline nor a meaningful finding count.
_REVIEWED_STATES = frozenset({STATE_PARTICIPATED, STATE_PARTICIPATED_BUT_EMPTY})

# Deficit-signal verdicts (D2). A REVIEWER-QUALITY observation about a required
# reviewer's YIELD, never a merge verdict and never a participation verdict.
DEFICIT_DEFICIT = 'deficit'            # a required reviewer under-produced vs a baseline
DEFICIT_CLEAN = 'clean'                # a baseline exists and no required reviewer under-produced
DEFICIT_UNASSESSABLE = 'unassessable'  # no baseline reviewer reviewed the diff — evidence neither way

# The compact display buckets for the reviewer-state distribution, in canonical
# render order. Each maps one-or-more taxonomy states to a short human label, so a
# reader of ``display_detail`` can tell *reviewed-and-clean* from *nobody-reviewed*
# at a glance — the distinction a bare comment count collapses. Grouped so the label
# answers the reader's question ("did anyone review?") rather than exposing every
# internal state name; the three refusal members share one ``refused`` bucket.
_STATE_SUMMARY_BUCKETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('reviewed', (STATE_PARTICIPATED,)),
    ('empty', (STATE_PARTICIPATED_BUT_EMPTY,)),
    ('refused', (STATE_REFUSED_AWAITABLE, STATE_REFUSED_HARD, STATE_REFUSED_UNKNOWN)),
    ('stale', (STATE_PARTICIPATED_STALE,)),
    ('declined', (STATE_DECLINED,)),
    ('in-progress', (STATE_IN_PROGRESS,)),
    ('not-triggered', (STATE_NOT_TRIGGERED,)),
    ('absent', (STATE_ABSENT,)),
)


class MalformedBotFlag(ValueError):
    """A bot-list flag received a token whose SHAPE does not match the flag's form.

    The flag set is split by form. The pair-form flags (``--participated-bots`` and
    ``--stale-participation-bots``, both fed the producer's
    ``bot_kind:evidence_kind`` records) require every token to be a pair; a bare
    ``bot_kind`` is malformed. The bare-form flags (``--required-bots`` /
    ``--optional-bots`` / ``--in-progress-bots`` / ``--refused-bots`` /
    ``--declined-bots``) require every token to be a bare ``bot_kind``; a
    ``bot_kind:evidence_kind`` pair is malformed.

    A malformed token is REJECTED loudly rather than silently reinterpreted. Both
    misparses are polarity-selecting: a bare kind dropped from the pair-form parse
    resolves to ``absent`` (a blocking member), manufacturing a confident false merge
    block against a bot the caller believed participated; a pair fed to a bare-form
    flag becomes a one-off "bot" named ``bot_kind:evidence_kind`` that matches no
    configured bot and vanishes, while the real bot still resolves to ``absent``.
    Raising instead makes the form mismatch a visible caller error the CLI renders as
    ``status: error`` with a non-zero exit and no ``participation_complete`` field.
    """


def parse_participation(raw: str | None, flag: str = '--participated-bots') -> dict[str, str]:
    """Parse a ``bot_kind:evidence_kind`` CSV into a bot -> evidence-kind map.

    Only pairs whose ``evidence_kind`` is one of the publish shapes the bot's
    registry record declares in ``participation_evidence`` are admitted; a
    well-formed pair whose evidence kind is NOT a declared publish shape is dropped.
    This is where the diff-derived-evidence rule is ENFORCED rather than merely
    asserted: the admissible vocabulary is closed to publish shapes, so a
    body-derived signal — anything a reviewer could have produced by reading the PR
    description alone — carries no admissible evidence kind and cannot be laundered
    in as participation.

    A token that is NOT a ``bot_kind:evidence_kind`` pair — a bare ``bot_kind`` with
    no colon, or a pair with an empty side — is a SHAPE violation and is REJECTED
    with :class:`MalformedBotFlag`, never silently dropped. That silent drop is
    precisely the polarity-selecting misparse this rejection closes: the bot would
    fall through to ``absent`` (a blocking member) and manufacture a confident false
    merge block against a bot the caller meant to record as a participant. The
    rejection is the SHAPE check ONLY — a well-formed pair whose evidence kind is
    inadmissible is a semantic non-match, not a caller error, and stays a silent drop
    (the diff-derived-evidence rule above). An empty token (the bare-flag /
    trailing-comma empty-list form) is skipped, not rejected.

    A bot whose registry record declares no evidence shape can never match any
    admissible pair, which is the fail-closed default.
    """
    proven: dict[str, str] = {}
    for entry in (raw or '').split(','):
        entry = entry.strip()
        if not entry:
            continue
        bot_kind, sep, evidence_kind = entry.partition(':')
        bot_kind = bot_kind.strip()
        evidence_kind = evidence_kind.strip()
        if not sep or not bot_kind or not evidence_kind:
            raise MalformedBotFlag(
                f'{flag} expects bot_kind:evidence_kind pairs but received the token '
                f'{entry!r}, which is not a pair. A bare bot_kind neither proves '
                f'participation nor is a valid absence: silently dropping it would '
                f'resolve the bot to absent (a blocking state) and manufacture a false '
                f'merge block, so it is rejected as a caller error.'
            )
        if evidence_kind in bot_registry.participation_evidence(bot_kind):
            proven[bot_kind] = evidence_kind
    return proven


def _refusal_state(rate_limit_class: str) -> str:
    """Map a bot's three-valued ``rate_limit_class`` to its refusal STATE, one-to-one.

    The mapping is total and injective over the three declared classes, so no value
    is collapsed into another:

    - ``awaitable_window`` -> ``refused_awaitable`` — the window reopens on its own.
    - ``hard_quota``       -> ``refused_hard`` — a budget that does not usefully reopen.
    - ``unknown`` / anything else -> ``refused_unknown`` — the registry declares
      ignorance, so whether waiting helps is genuinely not known.

    ``unknown`` resolves to its own member, never to ``refused_hard``. A binary
    ``== 'awaitable_window'`` test over the three-valued field mapped everything that
    was not awaitable — ``hard_quota`` and ``unknown`` alike — into ``refused_hard``,
    rendering a declared *we-do-not-know* as a positive *hard quota* finding. Any
    value that is neither of the first two, INCLUDING a malformed or absent one,
    resolves fail-closed to ``refused_unknown`` rather than being asserted as a hard
    quota the registry never declared.
    """
    if rate_limit_class == 'awaitable_window':
        return STATE_REFUSED_AWAITABLE
    if rate_limit_class == 'hard_quota':
        return STATE_REFUSED_HARD
    return STATE_REFUSED_UNKNOWN


def classify_bot(
    bot: str,
    proven_participants: dict[str, str],
    has_findings: bool,
    in_progress: set[str],
    refused: set[str],
    stale_participants: set[str] | None = None,
    not_triggered: bool = False,
    declined: set[str] | None = None,
) -> str:
    """Return the single state ``bot`` resolves to.

    The branches are evaluated in evidence-strength order, so exactly one state is
    assigned. Proven participation is checked FIRST because it is positive,
    diff-derived evidence the bot actually reviewed — it outranks the awaiting and
    refusal signals, which are both statements about the absence of a review. The
    same ordering logic settles the refusal-outranks-stale edge: a bot that has a
    stale publish AND a refusal is classified refused, because the refusal is the
    NEWER and more actionable signal — it names a reason the bot will not review now,
    whereas a stale publish only says the last review predates this HEAD, and the two
    call for different remedies (wait out or accept the refusal vs re-trigger).

    - **``participated``** — proven participant that filed at least one finding.
    - **``participated_but_empty``** — proven participant that filed none. It did
      its pass and had nothing actionable to say; accounted-for, never a failure.
    - **``refused_awaitable`` / ``refused_hard`` / ``refused_unknown``** — the bot
      published a refusal. Which member is decided ONE-TO-ONE by its registry
      three-valued ``rate_limit_class`` (:func:`_refusal_state`): ``awaitable_window``
      reopens on its own, ``hard_quota`` does not, and ``unknown`` is a declared
      ignorance that is neither — never collapsed into ``refused_hard``. No bot-name
      literal.
    - **``declined``** — the bot was asked to review the merge candidate and answered
      without producing a review of it (an incremental-review decline: a comment
      carrying no reviewed-commit SHA). Checked after the refusal branches — a refusal
      is the more specific "will not review now" signal — and before ``participated_stale``,
      because a decline says the bot answered *this* re-review request without
      reviewing, which is a fresher and more actionable signal than a review that
      merely predates this HEAD. Unproven and blocking, but the remedy is to accept the
      decline, not to re-trigger a bot that already declined this commit.
    - **``participated_stale``** — the bot published in a declared evidence shape,
      but the currency test failed: the comment was reviewed against a commit that is
      not the merge candidate and was not edited in place since, so the review it
      proves predates this HEAD. Unproven and therefore blocking, but the remedy is to
      re-trigger a re-review — the opposite of ``absent``, where there is no review to
      refresh.
    - **``in_progress``** — the bot's review is still running.
    - **``not_triggered``** — PR-wide: no ``pull_request``-event workflow run exists
      for this PR at all, so NO bot could have published and this bot's silence
      says nothing about this bot. A refinement of ``absent`` rather than a sibling
      — hence the last branch before it — whose remedy is to trigger the review
      rather than to escalate a reviewer that was asked and did not answer.
    - **``absent``** — no evidence of any kind. The fail-closed default, which is
      also where a bot declaring NO evidence shape necessarily lands, since it can
      never be proven a participant.
    """
    if bot in proven_participants:
        return STATE_PARTICIPATED if has_findings else STATE_PARTICIPATED_BUT_EMPTY
    if bot in refused:
        return _refusal_state(bot_registry.rate_limit_class(bot))
    if bot in (declined or set()):
        return STATE_DECLINED
    if bot in (stale_participants or set()):
        return STATE_PARTICIPATED_STALE
    if bot in in_progress:
        return STATE_IN_PROGRESS
    # Last branch before the fallthrough: every earlier state is POSITIVE evidence
    # about this specific bot, and a PR-wide "nothing ran" must never override an
    # observation that something did. Placing it here means no existing verdict
    # moves — only what would otherwise have been ``absent`` is refined.
    if not_triggered:
        return STATE_NOT_TRIGGERED
    return STATE_ABSENT


def compose_review_state_summary(bot_states: list[dict]) -> str:
    """Render the reviewer-state distribution as a compact one-line summary (D3).

    Turns the ``bot_states`` classification into a short, comma-separated tally of
    the non-zero buckets in :data:`_STATE_SUMMARY_BUCKETS` — ``"3 refused"``,
    ``"1 reviewed, 2 empty"``, ``"2 empty, 1 refused"`` — so a reader of
    ``display_detail`` can tell *reviewed-and-clean* from *nobody-reviewed*, which a
    bare ``N comment(s) found`` cannot. ``"0 comment(s) found"`` is the identical
    string for a clean 27-file review and for a run where no reviewer produced any
    content; appended, ``"3 empty"`` versus ``"3 refused"`` separates them.

    Returns ``''`` when ``bot_states`` is empty. An empty roster (no required and no
    optional bot) has nothing to distribute, and inventing a bucket there would be a
    claim about reviewers that were never configured — the empty string is the honest
    value, and the caller simply appends nothing.
    """
    counts: dict[str, int] = {}
    for record in bot_states:
        state = record.get('state', '')
        counts[state] = counts.get(state, 0) + 1
    parts: list[str] = []
    for label, states in _STATE_SUMMARY_BUCKETS:
        total = sum(counts.get(s, 0) for s in states)
        if total:
            parts.append(f'{total} {label}')
    return ', '.join(parts)


def assess_deficit(
    reviewers: list[dict],
    required_bots: list[str] | set[str],
    min_deficit: int = 1,
) -> dict:
    """Report whether a REQUIRED reviewer under-produced against a real baseline (D2).

    This is an OBSERVABILITY signal about reviewer QUALITY — a bug report about the
    reviewer, never a merge verdict and never a participation verdict. It gates
    nothing: a reviewer that produced a result satisfies participation and the merge
    decision regardless of what this reports, so the envelope carries
    ``proves: reviewer_quality_only`` and ``gates_merge: false`` in as many words.
    Turning it into a gate would block a merge on a third party's output.

    Args:
        reviewers: one record per reviewer, ``{bot_kind, reviewed: bool,
            finding_count: int}``. ``reviewed`` is the reviewed-at-all predicate (a
            proven publish shape against the merge candidate — the
            :data:`_REVIEWED_STATES` membership); ``finding_count`` is the number of
            filed ``pr-comment`` findings attributed to the reviewer. It is the FILED
            count, never a raw comment count: the producer already collapsed noise,
            refusals and duplicates, and one reviewer's findings can arrive across
            several review bodies, so counting bodies or raw comments is wrong in both
            directions.
        required_bots: the bot kinds designated ``required``; a reviewer NOT in this
            set is an optional / baseline reviewer.
        min_deficit: the smallest baseline-minus-required gap that counts as a
            deficit (default 1 — a required reviewer that reviewed yet produced
            strictly fewer findings than a baseline reviewer that reviewed the same
            diff).

    Returns:
        A dict carrying ``verdict`` (:data:`DEFICIT_DEFICIT` / :data:`DEFICIT_CLEAN`
        / :data:`DEFICIT_UNASSESSABLE`), the non-gating disclaimers, and the
        populations every figure was computed over — ``baseline_reviewers`` (the
        non-required reviewers that reviewed), ``baseline_max`` (the highest baseline
        finding count), ``required_reviewed`` (the required reviewers that reviewed),
        and ``deficit_reviewers`` (one ``{bot_kind, findings, deficit}`` record per
        under-producing required reviewer).

    Verdict rules — the baseline is what makes a deficit assessable:

    - **unassessable** — NO non-required reviewer reviewed the diff, so there is no
      baseline to compare against and the run is evidence neither way. A required
      reviewer that produced nothing on a diff nothing else reviewed is not proof of
      under-production. This is the companion of the ``0 : 0`` guard: when every
      other reviewer refused, nothing reviewed the diff besides the required bot.
    - **clean** — a baseline exists AND no required reviewer that reviewed produced
      at least ``min_deficit`` fewer findings than the baseline's best. ``0 : 0``
      against a real baseline (a baseline reviewer reviewed and found nothing; the
      required reviewer found nothing) lands here, never in ``deficit``.
    - **deficit** — a baseline exists AND at least one required reviewer that
      reviewed produced at least ``min_deficit`` fewer findings than the baseline's
      best. Reported as a reviewer-quality bug about that required reviewer.
    """
    required_set = set(required_bots)
    baseline = [
        r for r in reviewers
        if r.get('bot_kind') not in required_set and r.get('reviewed')
    ]
    baseline_max = max((int(r.get('finding_count') or 0) for r in baseline), default=0)
    required_reviewed = [
        r for r in reviewers
        if r.get('bot_kind') in required_set and r.get('reviewed')
    ]

    deficit_reviewers: list[dict] = []
    if not baseline:
        verdict = DEFICIT_UNASSESSABLE
    else:
        for r in required_reviewed:
            count = int(r.get('finding_count') or 0)
            gap = baseline_max - count
            if gap >= min_deficit:
                deficit_reviewers.append(
                    {'bot_kind': r.get('bot_kind'), 'findings': count, 'deficit': gap}
                )
        verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN

    return {
        'status': 'success',
        'verdict': verdict,
        # Machine-readable restatement of the ceiling: this signal is about reviewer
        # quality and moves no gate. A consumer cannot read it as a merge verdict
        # without ignoring a field that says otherwise.
        'proves': 'reviewer_quality_only',
        'gates_merge': False,
        'baseline_reviewers': sorted(str(r.get('bot_kind') or '') for r in baseline),
        'baseline_max': baseline_max,
        'required_reviewed': sorted(str(r.get('bot_kind') or '') for r in required_reviewed),
        'deficit_reviewers': deficit_reviewers,
    }


def check_completeness(
    plan_id: str,
    required_bots: list[str],
    optional_bots: list[str] | None = None,
    triage_ran: bool = False,
    participated_bots: dict[str, str] | None = None,
    in_progress_bots: list[str] | None = None,
    refused_bots: list[str] | None = None,
    stale_participation_bots: list[str] | None = None,
    declined_bots: list[str] | None = None,
    not_triggered: bool = False,
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
        stale_participation_bots:
                           Bots whose observed comment matched a declared
                           ``participation_evidence`` publish shape but failed the
                           ``participation_requires_update`` currency test, as
                           reported by ``github_pr fetch_findings``'s
                           ``stale_participation_bots[]``. They resolve to
                           ``participated_stale`` — unproven and blocking, but whose
                           remedy is a re-review trigger rather than the
                           non-participation escalation ``absent`` calls for. The
                           producer already subtracted the proven set, so a bot with
                           one stale and one fresh comment never arrives here.
        declined_bots:     Bots that were asked to review the merge candidate (a
                           re-review was triggered) and answered WITHOUT producing a
                           review of it — an incremental-review decline, observed as a
                           re-review ``matched: true`` with ``head_sha_verified:
                           false``. They resolve to ``declined`` — unproven and
                           blocking exactly as ``participated_stale`` is, but whose
                           remedy is to accept the decline, since re-triggering a bot
                           that already declined this commit produces another decline.
                           Distinct from ``refused_bots`` (an explicit rate-limit /
                           quota / size notice) and from ``stale_participation_bots``
                           (a review that exists but predates the merge candidate).
        not_triggered:     PR-WIDE observable: ``True`` when no
                           ``pull_request``-event workflow run exists for this PR,
                           as reported by ``github_pr pull_request_runs`` /
                           ``ci checks pull-request-runs``. A single bool rather
                           than a per-bot set, because the condition holds for
                           every bot at once. It refines what would otherwise be
                           ``absent`` and overrides no positive observation.

    Returns:
        Dict with the TOON-serialisable fields ``status``,
        ``participation_complete``, ``proves`` (always ``participation_only`` — the
        machine-readable form of the ceiling), ``pending_bots``, ``unproven_bots``,
        and ``bot_states`` (one ``{bot_kind, state}`` record per classified bot).

        ``bot_states`` spans required ∪ optional and assigns exactly one state per
        bot. ``unproven_bots`` is the subset whose state leaves participation
        unproven — the members of ``_UNPROVEN_STATES`` (``absent`` /
        ``in_progress`` / any of the three refusal members / ``participated_stale`` /
        ``declined`` / ``not_triggered``);
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
    stale = set(stale_participation_bots or [])
    declined = set(declined_bots or [])
    required_set = set(required_bots)
    # Required first, then the optional bots not already listed as required, so
    # the reported lists read in a stable, caller-meaningful order.
    classified = list(required_bots) + [b for b in (optional_bots or []) if b not in required_set]

    bot_states: list[dict[str, str]] = []
    pending_bots: list[str] = []
    unproven_bots: list[str] = []
    for bot in classified:
        bot_findings = [f for f in findings if f.get('bot_kind') == bot]
        state = classify_bot(
            bot, proven, bool(bot_findings), in_progress, refused, stale, not_triggered, declined
        )
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
        # The reviewer-state distribution as a compact one-line summary (D3), so a
        # ``display_detail`` reader can tell reviewed-and-clean from nobody-reviewed.
        # ``''`` for an empty roster — nothing to distribute.
        'review_state_summary': compose_review_state_summary(bot_states),
    }


def check_deficit(
    plan_id: str,
    required_bots: list[str],
    optional_bots: list[str] | None = None,
    participated_bots: dict[str, str] | None = None,
    in_progress_bots: list[str] | None = None,
    refused_bots: list[str] | None = None,
    stale_participation_bots: list[str] | None = None,
    declined_bots: list[str] | None = None,
    not_triggered: bool = False,
    min_deficit: int = 1,
) -> dict:
    """Classify each bot, count its FILED findings, and assess the deficit signal (D2).

    Reads the plan's ``pr-comment`` findings store to derive, per classified bot, its
    filed finding count and its reviewed-at-all predicate (the classification state
    is in :data:`_REVIEWED_STATES`), then hands the per-reviewer population to
    :func:`assess_deficit`. Takes the SAME observation inputs as
    :func:`check_completeness`, so the automatic-review step forwards the sets it has
    already gathered.

    On a findings-store load failure returns the ``load_failure`` error branch —
    identical to :func:`check_completeness` — so a crashed read is an UNKNOWN verdict
    rather than a false clean.
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
    stale = set(stale_participation_bots or [])
    declined = set(declined_bots or [])
    required_set = set(required_bots)
    classified = list(required_bots) + [b for b in (optional_bots or []) if b not in required_set]

    reviewers: list[dict] = []
    for bot in classified:
        bot_findings = [f for f in findings if f.get('bot_kind') == bot]
        state = classify_bot(
            bot, proven, bool(bot_findings), in_progress, refused, stale, not_triggered, declined
        )
        reviewers.append(
            {
                'bot_kind': bot,
                'reviewed': state in _REVIEWED_STATES,
                'finding_count': len(bot_findings),
                'state': state,
            }
        )

    result = assess_deficit(reviewers, required_bots, min_deficit=min_deficit)
    # Publish the per-reviewer population the verdict was computed over, so no figure
    # is a rate whose denominator is invisible — the defect this deliverable is about.
    result['reviewers'] = reviewers
    return result


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
    summary = payload.get('review_state_summary', '')
    if summary:
        print(f'review_state_summary: {summary}')
    pending = payload['pending_bots']
    if pending:
        print(f'pending_bots[{len(pending)}]:')
        for bot in pending:
            print(f'  - {bot}')
    unproven = payload['unproven_bots']
    if unproven:
        print(f'unproven_bots[{len(unproven)}]:')
        for bot in unproven:
            print(f'  - {bot}')
    states = payload['bot_states']
    if states:
        print(f'bot_states[{len(states)}]{{bot_kind,state}}:')
        for record in states:
            print(f'  {record["bot_kind"]},{record["state"]}')


def _emit_deficit_toon(payload: dict) -> None:
    """Print the deficit-signal TOON block.

    The ``gates_merge: false`` line is emitted verbatim so a reader — or a cold read
    of the rendered output — sees in as many words that this signal moves no gate.
    """
    print(f'status: {payload.get("status", "success")}')
    if payload.get('status') == 'error':
        print(f'error: {payload.get("error", "unknown")}')
        if 'detail' in payload:
            print(f'detail: {payload["detail"]}')
        return
    print(f'verdict: {payload["verdict"]}')
    print(f'proves: {payload["proves"]}')
    print('gates_merge: ' + ('true' if payload['gates_merge'] else 'false'))
    print(f'baseline_max: {payload["baseline_max"]}')
    baseline = payload['baseline_reviewers']
    if baseline:
        print(f'baseline_reviewers[{len(baseline)}]:')
        for bot in baseline:
            print(f'  - {bot}')
    required_reviewed = payload['required_reviewed']
    if required_reviewed:
        print(f'required_reviewed[{len(required_reviewed)}]:')
        for bot in required_reviewed:
            print(f'  - {bot}')
    deficits = payload['deficit_reviewers']
    if deficits:
        print(f'deficit_reviewers[{len(deficits)}]{{bot_kind,findings,deficit}}:')
        for record in deficits:
            print(f'  {record["bot_kind"]},{record["findings"]},{record["deficit"]}')
    reviewers = payload.get('reviewers') or []
    if reviewers:
        print(f'reviewers[{len(reviewers)}]{{bot_kind,reviewed,finding_count,state}}:')
        for record in reviewers:
            reviewed = 'true' if record['reviewed'] else 'false'
            print(f'  {record["bot_kind"]},{reviewed},{record["finding_count"]},{record["state"]}')


def _split_bots(raw: str | None, flag: str = 'a bare-form bot flag') -> list[str]:
    """Split a bare-form ``bot_kind`` list into its non-empty members.

    Absent, empty, and whitespace-only values all read as the empty list, so the
    bare-flag, omitted-flag, and explicitly-empty forms agree without a caller-side
    emptiness check.

    A ``bot_kind:evidence_kind`` PAIR token is a SHAPE violation for a bare-form flag
    and is REJECTED with :class:`MalformedBotFlag`. Fed a pair, a bare-form flag would
    read it as a bot literally named ``bot_kind:evidence_kind``, which matches no
    configured bot and vanishes silently while the real bot resolves to ``absent`` —
    the same polarity-selecting misparse the pair-form flags reject in the other
    direction. Rejecting it keeps the flag SET internally consistent: a token
    forwarded to the wrong flag form fails loudly instead of being reinterpreted into
    a blocking verdict nobody computed.
    """
    bots: list[str] = []
    for entry in (raw or '').split(','):
        entry = entry.strip()
        if not entry:
            continue
        if ':' in entry:
            raise MalformedBotFlag(
                f'{flag} expects bare bot_kind tokens but received the pair-shaped '
                f'token {entry!r}. A bot_kind:evidence_kind pair belongs on a pair-form '
                f'flag (--participated-bots / --stale-participation-bots); fed to a '
                f'bare-form flag it would be read as a bot named {entry!r} and silently '
                f'match nothing.'
            )
        bots.append(entry)
    return bots


def _parse_bot_observations(args: argparse.Namespace) -> dict:
    """Parse the shared bot-observation flags into the classifier's input sets.

    Both the ``check`` and ``deficit`` subcommands classify each bot from the same
    observation flags, so the parse-by-FORM logic lives here once. The two pair-form
    flags — ``--participated-bots`` and ``--stale-participation-bots``, both fed the
    producer's ``{bot_kind, evidence_kind}`` records verbatim — go through
    :func:`parse_participation`; the bare-form flags through :func:`_split_bots`.

    Raises :class:`MalformedBotFlag` when a token's shape does not match its flag's
    form; each command renders that as a structured ``status: error`` UNKNOWN verdict
    with a NON-ZERO exit and no verdict field, never a false pass and never a false
    block.
    """
    return {
        'required_bots': _split_bots(args.required_bots, '--required-bots'),
        'optional_bots': _split_bots(args.optional_bots, '--optional-bots'),
        'participated_bots': parse_participation(args.participated_bots, '--participated-bots'),
        'in_progress_bots': _split_bots(args.in_progress_bots, '--in-progress-bots'),
        'refused_bots': _split_bots(args.refused_bots, '--refused-bots'),
        # --stale-participation-bots is EVIDENCE-TYPED like --participated-bots: it is
        # fed the producer's stale_participation_bots[] pair records verbatim, so it
        # takes the same pair form and the classifier reads only the bot_kinds.
        'stale_participation_bots': list(
            parse_participation(args.stale_participation_bots, '--stale-participation-bots')
        ),
        'declined_bots': _split_bots(args.declined_bots, '--declined-bots'),
    }


def cmd_check(args: argparse.Namespace) -> int:
    """Run the completeness predicate and emit the summary TOON to stdout.

    The bot-list flags are parsed by FORM (see :func:`_parse_bot_observations`)
    before the predicate runs. A token whose shape does not match its flag's form is
    a :class:`MalformedBotFlag` caller error, rendered as a structured ``status:
    error`` with a NON-ZERO exit and NO ``participation_complete`` field, so the
    caller reads it as an UNKNOWN verdict (never a false pass and never a false
    block) — the same shape the load-failure branch and the doc's UNKNOWN-verdict
    handling already expect.
    """
    try:
        obs = _parse_bot_observations(args)
    except MalformedBotFlag as exc:
        _emit_toon({'status': 'error', 'error': 'malformed_bot_flag', 'detail': str(exc)})
        return 1
    payload = check_completeness(
        args.plan_id,
        obs['required_bots'],
        optional_bots=obs['optional_bots'],
        triage_ran=args.triage_ran,
        participated_bots=obs['participated_bots'],
        in_progress_bots=obs['in_progress_bots'],
        refused_bots=obs['refused_bots'],
        stale_participation_bots=obs['stale_participation_bots'],
        declined_bots=obs['declined_bots'],
        not_triggered=args.not_triggered,
    )
    _emit_toon(payload)
    return 0 if payload.get('status') == 'success' else 1


def cmd_deficit(args: argparse.Namespace) -> int:
    """Run the deficit signal and emit its TOON to stdout.

    A REVIEWER-QUALITY observation, never a merge verdict — the emitted envelope
    carries ``gates_merge: false``. Shares the observation-flag parsing with
    ``check``; a :class:`MalformedBotFlag` is an UNKNOWN verdict exactly as there.
    """
    try:
        obs = _parse_bot_observations(args)
    except MalformedBotFlag as exc:
        _emit_deficit_toon({'status': 'error', 'error': 'malformed_bot_flag', 'detail': str(exc)})
        return 1
    payload = check_deficit(
        args.plan_id,
        obs['required_bots'],
        optional_bots=obs['optional_bots'],
        participated_bots=obs['participated_bots'],
        in_progress_bots=obs['in_progress_bots'],
        refused_bots=obs['refused_bots'],
        stale_participation_bots=obs['stale_participation_bots'],
        declined_bots=obs['declined_bots'],
        not_triggered=args.not_triggered,
        min_deficit=args.min_deficit,
    )
    _emit_deficit_toon(payload)
    return 0 if payload.get('status') == 'success' else 1


def _add_bot_observation_flags(sub: argparse.ArgumentParser) -> None:
    """Add the observation flags shared by the ``check`` and ``deficit`` subcommands.

    ``--plan-id`` plus the six list flags and the PR-wide ``--not-triggered`` bool —
    the classifier's whole input surface. Factored so the two subcommands cannot
    drift in flag name, ``nargs``, or ``const`` (a drift would silently change how an
    empty list parses on one command but not the other).
    """
    sub.add_argument('--plan-id', required=True)
    sub.add_argument(
        '--required-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated review-bot kinds whose participation is REQUIRED. For '
            'check these and only these form the completeness quorum; for deficit '
            'they are the reviewers whose YIELD is compared against the baseline. An '
            'empty list is a valid configured state. May be supplied bare (no value), '
            'which reads as the empty list.'
        ),
    )
    sub.add_argument(
        '--optional-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated review-bot kinds whose participation is OPTIONAL. '
            'Classified and reported for visibility but NEVER gating; for deficit they '
            'are candidate baseline reviewers. May be supplied bare (no value), which '
            'reads as the empty list.'
        ),
    )
    sub.add_argument(
        '--participated-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated EVIDENCE-TYPED participation pairs, each '
            'bot_kind:evidence_kind, as reported by github_pr fetch_findings. A '
            "pair is admitted only when evidence_kind is one of that bot's "
            'declared participation_evidence publish shapes; a bare bot_kind with '
            'no evidence_kind is rejected, because unqualified presence does not '
            'prove a bot reviewed this diff. This proves PARTICIPATION only, never '
            'review quality. May be supplied bare (no value), which reads as the '
            'empty list — zero proven participants, never a pass.'
        ),
    )
    sub.add_argument(
        '--in-progress-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated review-bot kinds whose review was still running '
            '(completion check not yet terminal) when the poll budget expired. '
            'A required bot here is classified in_progress and blocks. May be '
            'supplied bare (no value), which reads as the empty list.'
        ),
    )
    sub.add_argument(
        '--refused-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated review-bot kinds observed publishing a refusal '
            'notice. Supply only the observation — the refusal is split ONE-TO-ONE '
            "into refused_awaitable / refused_hard / refused_unknown from each bot's "
            'registry three-valued rate_limit_class, never by the caller. May be '
            'supplied bare (no value), which reads as the empty list.'
        ),
    )
    sub.add_argument(
        '--stale-participation-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated bot_kind:evidence_kind pairs — the SAME evidence-typed '
            'form as --participated-bots, and the exact shape github_pr '
            "fetch_findings emits in stale_participation_bots[], so the producer's "
            'output forwards here verbatim. Each names a bot whose observed comment '
            'matched a declared participation_evidence publish shape but failed the '
            'participation_requires_update currency test; the classifier reads only '
            'the bot_kind. A required bot here is classified participated_stale and '
            'blocks — it published against an earlier HEAD, so nothing has reviewed '
            'the current diff — but the remedy is a re-review trigger, not the '
            'non-participation escalation absent calls for. A bare bot_kind with no '
            'evidence_kind is rejected as malformed (a bare token belongs on a '
            'bare-form flag). May be supplied bare (no value), which reads as the '
            'empty list.'
        ),
    )
    sub.add_argument(
        '--declined-bots',
        nargs='?',
        const='',
        default='',
        help=(
            'Comma-separated review-bot kinds that were asked to review the merge '
            'candidate (a re-review was triggered) and answered WITHOUT producing a '
            'review of it — an incremental-review decline (re-review matched: true '
            'with head_sha_verified: false). A required bot here is classified '
            'declined and blocks — it engaged but did not review this commit — but '
            'the remedy is to accept the decline, not to re-trigger a bot that '
            'already declined. Distinct from --refused-bots (an explicit rate-limit / '
            'quota / size notice) and --stale-participation-bots (a review that '
            'exists but predates the merge candidate). May be supplied bare (no '
            'value), which reads as the empty list.'
        ),
    )
    sub.add_argument(
        '--not-triggered',
        action='store_true',
        default=False,
        help=(
            'PR-WIDE: pass when no pull_request-event workflow run exists for this '
            'PR, as reported by github_pr pull_request_runs / ci checks '
            'pull-request-runs. Every required bot then resolves not_triggered '
            'instead of absent — still blocking, but the remedy is to trigger the '
            'review rather than escalate a reviewer that was asked and stayed '
            'silent. A store_true bool, not a bot list: the condition holds for '
            'every bot at once. Omit it whenever a pull_request run exists, '
            'INCLUDING one that concluded skipped — a skipped run was still '
            'triggered.'
        ),
    )


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
    _add_bot_observation_flags(check_parser)
    check_parser.add_argument(
        '--triage-ran',
        action='store_true',
        default=False,
        help=(
            'Whether the dispatcher-owned unified triage has already run. Omit '
            '(the FIND-only default) so a pending finding does NOT block '
            'completeness — only unproven REQUIRED bots gate the mark-done. Pass '
            'it once triage has run so a still-pending required finding blocks as '
            'a real incompleteness.'
        ),
    )
    check_parser.set_defaults(func=cmd_check)

    deficit_parser = subparsers.add_parser(
        'deficit',
        help=(
            'Report whether a REQUIRED reviewer under-produced against a real '
            'baseline — a reviewer-quality signal, never a merge verdict'
        ),
        allow_abbrev=False,
    )
    _add_bot_observation_flags(deficit_parser)
    deficit_parser.add_argument(
        '--min-deficit',
        type=int,
        default=1,
        help=(
            'The smallest baseline-minus-required finding-count gap that counts as a '
            'deficit (default 1). A required reviewer that reviewed the diff yet '
            'produced at least this many fewer findings than the best baseline '
            'reviewer is reported. The signal fires only when a baseline exists (some '
            'non-required reviewer reviewed the same diff) and never on 0 : 0 against '
            'a real baseline; with no baseline the verdict is unassessable, never a '
            'deficit. This gates no merge.'
        ),
    )
    deficit_parser.set_defaults(func=cmd_deficit)

    args = parser.parse_args(argv)
    rc: int = args.func(args)
    return rc


if __name__ == '__main__':
    sys.exit(main())
