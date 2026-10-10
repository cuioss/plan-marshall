# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``workflow-integration-github`` subtree's fixtures helper.

Home of the **currency-subject bot population** — the bots whose participation
credit is currency-tested because they re-review by editing one persistent
comment in place (``bot_registry.participation_requires_update``). Every module
in this subtree that parametrizes over that population imports it from here by
bare name, so exactly ONE definition of it exists in the test tree.

Re-deriving the population in a consuming module — or hand-listing its members —
is the hand-maintained-roster defect this module exists to close: a bot that
newly opts into ``participation_requires_update`` must inherit every case
parametrized over the population rather than silently escaping it.

Its COMPLEMENT — :data:`CURRENCY_BLIND_BOTS`, the append-per-review bots — is derived
here too, from the same registry read, so the partition cannot drift apart or overlap.

Both populations are guarded NON-EMPTY at import (:func:`guard_non_empty`) and their
sizes are published as :data:`CURRENCY_SUBJECT_BOT_COUNT` and
:data:`CURRENCY_BLIND_BOT_COUNT`. A parametrize over an empty tuple produces a skip
rather than a failure, so an unguarded empty population would let a whole sweep report
clean while covering nothing.

A second partition lives here for the same reason — the **evidence content gate**
(``bot_registry.participation_evidence_marker``). Every declared ``(bot_kind, shape)``
evidence pairing is either GATED on a content marker (:data:`MARKER_GATED_EVIDENCE`)
or credited on the shape alone (:data:`UNGATED_EVIDENCE`). Both halves are derived from
one registry read, guarded non-empty, and sized, so a marker newly declared by a bot
moves its pairing from one half to the other with no test edit.

It is also the home of the **CodeRabbit quota-notice bodies** that state a reset time
in the review-summary wording ("Next included review available in N minutes"), each
paired with the reset time it states and that time in seconds, and of the matched
body that states none. They are literals rather than registry-derived because they
are the observed notice text the registry's extraction patterns must read.

And of the **CodeRabbit acknowledgment replies** — the command replies that only
confirm ``@coderabbitai review`` was received (:data:`CODERABBIT_ACKNOWLEDGMENTS`) —
each carrying the PROVENANCE of its wording, beside the matched bodies that are not
acknowledgments: a genuine short review comment from the same bot, and a human
comment that quotes an acknowledgment.

And of the **CodeRabbit "nothing new to review" replies**
(:data:`CODERABBIT_NO_UNREVIEWED_COMMIT_REPLIES`) — the refusals whose condition is
``no_unreviewed_commit`` — each carrying the provenance of its wording, beside the
matched command reply that is a rate limit (:data:`CODERABBIT_RATE_LIMITED_COMMAND_REPLY`).
"""

from __future__ import annotations

import bot_registry


class VacuousPopulationError(AssertionError):
    """A derived population is empty, so every verdict over it is vacuous."""


def guard_non_empty[T](population: tuple[T, ...], name: str, derivation: str) -> tuple[T, ...]:
    """Return ``population``, or raise when it is empty.

    Generic over the member type, so a population of ``(bot_kind, shape)`` pairs is
    guarded exactly as a population of bot kinds is.

    Args:
        population: The derived population.
        name: The population's published name, for the failure message.
        derivation: How the population was derived, so a failure names the
            source to investigate rather than only the empty result.

    Returns:
        The population unchanged, when it carries at least one member.

    Raises:
        VacuousPopulationError: when ``population`` is empty.
    """
    if not population:
        raise VacuousPopulationError(
            f'{name} is empty — derived from {derivation}. Every test parametrized '
            f'over it would skip rather than fail, reporting clean while covering nothing.'
        )
    return population


#: Bots whose participation credit is currency-tested, derived from the registry.
CURRENCY_SUBJECT_BOTS: tuple[str, ...] = guard_non_empty(
    tuple(bot for bot in bot_registry.bot_kinds() if bot_registry.participation_requires_update(bot)),
    'CURRENCY_SUBJECT_BOTS',
    'bot_registry.bot_kinds() filtered by bot_registry.participation_requires_update',
)

#: The published size of the currency-subject bot population.
CURRENCY_SUBJECT_BOT_COUNT: int = len(CURRENCY_SUBJECT_BOTS)

#: Bots whose participation credit is NOT currency-tested — the complement, derived from
#: the same registry read so the two populations cannot drift apart or overlap. These are
#: the append-per-review bots: they publish a NEW comment per review, so the producer
#: credits them on the presence of a declared ``participation_evidence`` publish shape and
#: compares no commit.
#:
#: The complement lives here rather than in a consuming module for the same reason the
#: subject population does: derived in two places is hand-maintained in two places. It is
#: guarded non-empty because the behaviour it parametrizes — the accepted, bounded
#: currency-blind gap recorded in ``automatic-review/standards/bot-participation-contract.md``
#: — would otherwise be asserted over nothing.
CURRENCY_BLIND_BOTS: tuple[str, ...] = guard_non_empty(
    tuple(bot for bot in bot_registry.bot_kinds() if not bot_registry.participation_requires_update(bot)),
    'CURRENCY_BLIND_BOTS',
    'bot_registry.bot_kinds() filtered by NOT bot_registry.participation_requires_update',
)

#: The published size of the currency-blind bot population.
CURRENCY_BLIND_BOT_COUNT: int = len(CURRENCY_BLIND_BOTS)

#: Every declared ``(bot_kind, shape)`` evidence pairing, in registry order — the
#: population the content-gate partition below splits.
_DECLARED_EVIDENCE: tuple[tuple[str, str], ...] = tuple(
    (bot, shape) for bot in bot_registry.bot_kinds() for shape in bot_registry.participation_evidence(bot)
)

#: ``(bot_kind, shape, marker)`` for every declared evidence shape the bot GATES on a
#: content marker: a comment in that shape credits only when its body carries ``marker``.
MARKER_GATED_EVIDENCE: tuple[tuple[str, str, str], ...] = guard_non_empty(
    tuple(
        (bot, shape, marker)
        for bot, shape in _DECLARED_EVIDENCE
        if (marker := bot_registry.participation_evidence_marker(bot, shape))
    ),
    'MARKER_GATED_EVIDENCE',
    'declared (bot_kind, shape) evidence pairings with a bot_registry.participation_evidence_marker',
)

#: The published size of the marker-gated evidence population.
MARKER_GATED_EVIDENCE_COUNT: int = len(MARKER_GATED_EVIDENCE)

#: ``(bot_kind, shape)`` for every declared evidence shape with NO content marker — the
#: FAIL-OPEN half, credited on the shape alone exactly as before the gate existed. The
#: complement of :data:`MARKER_GATED_EVIDENCE` over the same registry read.
UNGATED_EVIDENCE: tuple[tuple[str, str], ...] = guard_non_empty(
    tuple(
        (bot, shape) for bot, shape in _DECLARED_EVIDENCE if not bot_registry.participation_evidence_marker(bot, shape)
    ),
    'UNGATED_EVIDENCE',
    'declared (bot_kind, shape) evidence pairings with no bot_registry.participation_evidence_marker',
)

#: The published size of the ungated evidence population.
UNGATED_EVIDENCE_COUNT: int = len(UNGATED_EVIDENCE)

#: The bot the quota-notice bodies below belong to.
QUOTA_NOTICE_BOT_KIND = 'coderabbit'

#: ``(body, stated reset time, that time in seconds)`` for CodeRabbit's review-summary
#: quota notice. Every body carries the bot's declared ``Review limit reached`` wording
#: and states its reset time as "Next included review available in ...": in minutes, in
#: hours, and in the two compound forms.
CODERABBIT_NEXT_REVIEW_NOTICES: tuple[tuple[str, str, int], ...] = guard_non_empty(
    (
        (
            '> [!WARNING] > ## Review limit reached > '
            'You have reached your review limit. Next included review available in 38 minutes.',
            '38 minutes',
            2280,
        ),
        (
            '> [!WARNING] > ## Review limit reached > '
            'You have reached your review limit. Next included review available in 2 hours.',
            '2 hours',
            7200,
        ),
        (
            '> [!WARNING] > ## Review limit reached > '
            'You have reached your review limit. Next included review available in 12 minutes and 30 seconds.',
            '12 minutes and 30 seconds',
            750,
        ),
        (
            '> [!WARNING] > ## Review limit reached > '
            'You have reached your review limit. Next included review available in 1 hour and 5 minutes.',
            '1 hour and 5 minutes',
            3900,
        ),
    ),
    'CODERABBIT_NEXT_REVIEW_NOTICES',
    'the literal notice bodies declared in _github_pr_fixtures',
)

#: The published size of the stated-reset-time notice population.
CODERABBIT_NEXT_REVIEW_NOTICE_COUNT: int = len(CODERABBIT_NEXT_REVIEW_NOTICES)

#: The matched body: the same declared wording, stating NO reset time at all.
CODERABBIT_NOTICE_STATING_NO_RESET_TIME = (
    '> [!WARNING] > ## Review limit reached > '
    'You have reached your review limit for the current billing cycle. '
    'Reviews will resume once the limit resets.'
)

#: The bot the acknowledgment bodies below belong to, and the login it comments under.
ACKNOWLEDGMENT_BOT_KIND = 'coderabbit'
ACKNOWLEDGMENT_BOT_LOGIN = 'coderabbitai'

#: Provenance of an acknowledgment fixture's WORDING. ``observed`` — the statement was
#: read off a live command reply. ``constructed`` — the statement is the reported
#: wording and has NOT been read off a live comment: CodeRabbit edits the one reply in
#: place, so the earlier wording is gone by the time the reply is read.
ACKNOWLEDGMENT_OBSERVED = 'observed'
ACKNOWLEDGMENT_CONSTRUCTED = 'constructed'


def _command_reply(statement: str) -> str:
    """Wrap ``statement`` in the disclosure CodeRabbit's command replies arrive in.

    The ``Action performed`` summary and the one-line statement are the parts that
    carry meaning; the line breaks around them are this builder's own, which is why
    the recogniser under test collapses whitespace before it compares.
    """
    return f'<details>\n<summary>✅ Action performed</summary>\n\n{statement}\n\n</details>'


#: ``(case id, body, provenance)`` for each CodeRabbit acknowledgment reply.
#:
#: ``Review finished.`` is OBSERVED: it was read off the command replies on
#: ``cuioss/plan-marshall#1654``, inside the ``Action performed`` disclosure.
#: ``Review triggered.`` is CONSTRUCTED: those replies had already been edited to their
#: final wording when they were read, so this body has never been seen on a live
#: comment. A case that passes only on the constructed body proves the declared literal
#: is honoured, not that CodeRabbit posts it.
CODERABBIT_ACKNOWLEDGMENTS: tuple[tuple[str, str, str], ...] = guard_non_empty(
    (
        ('review-finished', _command_reply('Review finished.'), ACKNOWLEDGMENT_OBSERVED),
        ('review-triggered', _command_reply('Review triggered.'), ACKNOWLEDGMENT_CONSTRUCTED),
    ),
    'CODERABBIT_ACKNOWLEDGMENTS',
    'the literal acknowledgment bodies declared in _github_pr_fixtures',
)

#: The published size of the acknowledgment population.
CODERABBIT_ACKNOWLEDGMENT_COUNT: int = len(CODERABBIT_ACKNOWLEDGMENTS)

#: NEGATIVE control, same bot: a genuine review comment as short as an acknowledgment.
#: It carries a code anchor and neither acknowledgment statement, so it is feedback
#: about the code — matched as the bot's answer, and filed as a finding.
CODERABBIT_GENUINE_SHORT_REVIEW_COMMENT = 'Guard the bound at `src/idx.py:12` before indexing.'

#: NEGATIVE control, other author: a HUMAN comment quoting an acknowledgment statement.
#: The class is scoped to the bot that declared the literal, so the quotation does not
#: make this an acknowledgment.
HUMAN_COMMENT_QUOTING_AN_ACKNOWLEDGMENT = (
    'CodeRabbit replied "Review finished." but the retry loop at `src/idx.py:12` '
    'still spins forever when the backoff cap is zero.'
)

#: The bot the "nothing new to review" bodies below belong to, and its login.
NO_UNREVIEWED_COMMIT_BOT_KIND = 'coderabbit'
NO_UNREVIEWED_COMMIT_BOT_LOGIN = 'coderabbitai'


def _declined_command_reply(statement: str) -> str:
    """Wrap ``statement`` in the disclosure CodeRabbit's DECLINED command replies arrive in.

    The same disclosure as :func:`_command_reply`, under the ``Action not completed``
    summary, followed by the note CodeRabbit appends to every such reply.
    """
    return (
        '<details>\n<summary>⚠️ Action not completed</summary>\n\n'
        f'{statement}\n\n'
        '> Note: CodeRabbit is an incremental review system and does not re-review already '
        'reviewed commits. This command is applicable only when automatic reviews are paused.\n\n'
        '</details>'
    )


#: ``(case id, body, provenance)`` for each CodeRabbit reply saying nothing new is left
#: to review. Provenance uses the acknowledgment vocabulary above.
#:
#: ``Already reviewed the last commit`` is OBSERVED: it was read off a command reply on
#: ``cuioss/plan-marshall#1654``. ``No new commits to review`` is CONSTRUCTED: it is the
#: reported wording of the skip notice and has not been read off a live comment.
CODERABBIT_NO_UNREVIEWED_COMMIT_REPLIES: tuple[tuple[str, str, str], ...] = guard_non_empty(
    (
        (
            'already-reviewed',
            _declined_command_reply(
                'Already reviewed the last commit. '
                'Use @coderabbitai full review to rerun a review of the entire changeset.'
            ),
            ACKNOWLEDGMENT_OBSERVED,
        ),
        (
            'no-new-commits',
            '> [!IMPORTANT]\n> ## Review skipped\n>\n> No new commits to review.',
            ACKNOWLEDGMENT_CONSTRUCTED,
        ),
    ),
    'CODERABBIT_NO_UNREVIEWED_COMMIT_REPLIES',
    'the literal no-new-commit bodies declared in _github_pr_fixtures',
)

#: The published size of the no-new-commit reply population.
CODERABBIT_NO_UNREVIEWED_COMMIT_REPLY_COUNT: int = len(CODERABBIT_NO_UNREVIEWED_COMMIT_REPLIES)

#: The matched body: a declined command reply from the same bot, in the same disclosure,
#: that IS a limit. Its condition is ``rate_limited``.
CODERABBIT_RATE_LIMITED_COMMAND_REPLY = _declined_command_reply('Review rate limited.')
