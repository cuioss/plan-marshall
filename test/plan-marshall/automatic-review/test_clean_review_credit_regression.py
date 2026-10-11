#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression for the participation-to-disclosure path, from the reader's angle.

The co-located unit suites pin each seam in isolation: the producer's evidence content
gate (``test_github_pr.py``), the classifier's clean-review member
(``test_review_completeness.py``), and the re-review envelope's body-derived
``head_sha_verified`` (``test_re_review_strategy.py``). This module pins their
COMPOSITION, which is where a fail-open gate and a body-derived verdict can silently
cancel out while every seam still passes on its own.

Every scenario drives the REAL producer (``github_pr.cmd_fetch_findings``) and, where
the path has one, the REAL re-review await (``github_re_review.await_fresh_review``),
then feeds their outputs to the REAL classifier (``review_completeness.check_completeness``)
exactly as the ``automatic-review`` step body forwards them. Only the GitHub provider
surface is stubbed. The assertions are on what a reader of the finished step sees —
the bot's taxonomy member, the quorum verdict, and the ``review_state_summary`` line —
never on an internal call.

1. **A walkthrough alone does not satisfy the quorum.** CodeRabbit's pre-review
   walkthrough ``issue_comment`` is the same publish shape as its verdict; credited on
   shape alone it satisfied the quorum for a review that had not happened.
2. **A marker-bearing clean review resolves ``participated_but_empty`` and renders
   ``empty``.** Every comment of a clean review is dropped as noise, so the credit is
   the only thing between it and ``absent``.
3. **A republished summary is no re-review answer.** It carries no verdict marker, so
   the matcher's marker gate leaves the wait unmatched, no decline is recorded, and the
   bot stays ``absent``.
4. **A verdict naming the awaited HEAD does not resolve ``declined``; one naming
   another commit does.** Before the comment arm read its body, every comment match
   published ``head_sha_verified: false`` and the step recorded a decline the bot never
   made — the blocking member whose remedy is to accept it rather than re-trigger.
"""

from __future__ import annotations

import argparse

import bot_registry
import github_re_review
import pytest

from conftest import load_script_module

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py')
rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_BOT = 'coderabbit'
_LOGIN = 'coderabbitai'
_PR_NUMBER = 1500

#: The merge candidate, a real 40-hex SHA so the body-derived verdict can extract it.
_HEAD_SHA = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'
_HEAD_SHA_URL = f'https://github.com/cuioss/plan-marshall/commit/{_HEAD_SHA}'

#: A different full commit — the reference a verdict for some other commit carries.
_OTHER_SHA = '0f1e2d3c4b5a69788796a5b4c3d2e1f098765432'

#: The re-review trigger time; every comment below is edited in place after it.
_TRIGGER = '2026-01-01T00:02:00Z'

#: CodeRabbit's walkthrough / summary ``issue_comment`` — posted before any review
#: completes. It carries none of CodeRabbit's verdict marker.
_WALKTHROUGH = (
    '<!-- This is an auto-generated comment: summarize by coderabbit.ai --> '
    '## Walkthrough The change gates participation credit on a per-shape content marker.'
)

#: The same summary republished in place after the re-review, now naming the commit it
#: reviewed — still a summary, so still carrying no verdict marker.
_REPUBLISHED_SUMMARY = f'{_WALKTHROUGH} (Review updated until commit [{_HEAD_SHA[:7]}]({_HEAD_SHA_URL}))'

#: A clean review verdict. The marker is READ from the registry rather than restated,
#: so this body tracks the declaration the producer gates on.
_CLEAN_VERDICT = (
    f'{bot_registry.participation_evidence_marker(_BOT, "issue_comment")} '
    'No actionable comments were generated in the recent review.'
)


def _comment(comment_id, body):
    """One CodeRabbit ``issue_comment``, created before the trigger and edited after it."""
    return {
        'id': comment_id,
        'kind': 'issue_comment',
        'author': _LOGIN,
        'thread_id': '',
        'body': body,
        'path': '',
        'line': 0,
        'resolved': False,
        'created_at': '2026-01-01T00:00:00Z',
        'updated_at': '2026-01-01T00:05:00Z',
    }


def _stub_provider(monkeypatch, comments):
    """Stub the GitHub provider surface the producer AND the re-review await reach.

    The await consults the bot's completion check-run whenever a poll would end on a
    match; that read is held at NOT OBSERVED RUNNING, so no scenario reaches ``gh``
    and none depends on whether a real PR's check happens to be running.
    """
    monkeypatch.setattr(github_re_review, 'read_bot_in_progress', lambda _pr_number, _bot_kind: False)
    for module in (github_pr, github_re_review):
        monkeypatch.setattr(module._github, 'check_auth', lambda: (True, ''))
        monkeypatch.setattr(module._github, 'fetch_pr_head_sha', lambda pr_number: _HEAD_SHA)
        monkeypatch.setattr(module._github, 'fetch_pr_head_committed_at', lambda pr_number: '')
        monkeypatch.setattr(
            module._github,
            'fetch_pr_comments_data',
            lambda pr_number, unresolved_only=False: {
                'status': 'success',
                'provider': 'github',
                'comments': list(comments),
                'total': len(comments),
                'unresolved': len(comments),
            },
        )
        monkeypatch.setattr(
            module._github,
            'fetch_pr_reviews_with_commits',
            lambda pr_number: {'status': 'success', 'reviews': []},
        )


def _find(plan_context, plan_id):
    """The step's FIND stage: the producer files findings and reports participation."""
    plan_context.plan_dir_for(plan_id)
    result = github_pr.cmd_fetch_findings(argparse.Namespace(pr_number=_PR_NUMBER, plan_id=plan_id))
    assert result['status'] == 'success', result
    return result


def _participation_flag(find_result):
    """``participated_bots[]`` rendered as the step forwards it to the classifier."""
    return ','.join(f'{row["bot_kind"]}:{row["evidence_kind"]}' for row in find_result['participated_bots'])


def _classify(plan_id, find_result, declined_bots=None):
    """The step-done participation guard over CodeRabbit as the only required bot."""
    return rc.check_completeness(
        plan_id,
        [_BOT],
        participated_bots=rc.parse_participation(_participation_flag(find_result)),
        declined_bots=declined_bots or [],
    )


def _state_of(result, bot):
    return next(row['state'] for row in result['bot_states'] if row['bot_kind'] == bot)


def test_a_walkthrough_alone_does_not_satisfy_the_quorum(plan_context, monkeypatch):
    """Scenario 1 — the pre-review walkthrough is not a review, so the quorum stays open.

    Fails when the evidence content gate is reverted: the walkthrough is CodeRabbit's
    declared ``issue_comment`` shape, so on shape alone it is credited, the bot
    resolves ``participated_but_empty``, and the step reads as reviewed-and-clean on a
    PR nobody reviewed.
    """
    plan_id = 'crr-walkthrough-only'
    _stub_provider(monkeypatch, [_comment('cr-walkthrough', _WALKTHROUGH)])

    result = _classify(plan_id, _find(plan_context, plan_id))

    assert result['participation_complete'] is False
    assert _state_of(result, _BOT) == rc.STATE_ABSENT
    assert result['review_state_summary'] == '1 absent'


def test_a_marker_bearing_clean_review_resolves_empty(plan_context, monkeypatch):
    """Scenario 2 — a clean review is an accounted-for success, rendered as ``empty``.

    The verdict comment is dropped as noise, so nothing is filed; the credit the
    producer grants before the noise filter is the only thing that keeps the bot off
    ``absent``. It must land on ``participated_but_empty`` — never ``absent``, which
    holds a clean PR open, and never ``participated``, which claims findings that do
    not exist.
    """
    plan_id = 'crr-clean-review'
    _stub_provider(monkeypatch, [_comment('cr-verdict', _CLEAN_VERDICT)])

    find_result = _find(plan_context, plan_id)
    result = _classify(plan_id, find_result)

    assert find_result['count_stored'] == 0
    assert result['participation_complete'] is True
    assert _state_of(result, _BOT) == rc.STATE_PARTICIPATED_BUT_EMPTY
    assert result['review_state_summary'] == '1 empty'


def _re_review():
    """The re-review await for the merge candidate.

    Every scenario's comment post-dates the trigger, so a matching poll completes at
    once; an unmatched await is bounded by its one-second budget.
    """
    strategy = github_re_review.resolve_strategy(_BOT)
    envelope = strategy.await_fresh_review(_PR_NUMBER, _HEAD_SHA, _TRIGGER, bot_kind=_BOT, timeout=1, interval=0)
    assert envelope['status'] == 'success', envelope
    return envelope


def _declined_after_re_review(envelope):
    """The step's documented decline rule: an answer that verified no HEAD is a decline."""
    return [_BOT] if envelope['matched'] and not envelope['head_sha_verified'] else []


def test_a_republished_summary_is_no_answer_and_records_no_decline(plan_context, monkeypatch):
    """Scenario 3 — a summary naming the head is no re-review answer, so nothing is declined.

    The comment is a republished SUMMARY: it carries no verdict marker, so the producer
    credits nothing for it, and the re-review matcher — which applies the same marker
    gate — does not take it as the answer either. The await ends unmatched, the step
    forwards no decline, and the bot stays ``absent``: still awaiting its verdict, and
    still re-triggerable.

    Fails when the matcher's marker gate is reverted: the summary then ends the wait
    as a match, the step reads a verdict off a review that never finished, and a body
    naming no commit would be forwarded as a decline the bot never made.
    """
    plan_id = 'crr-republished-summary'
    _stub_provider(monkeypatch, [_comment('cr-summary', _REPUBLISHED_SUMMARY)])

    envelope = _re_review()
    result = _classify(plan_id, _find(plan_context, plan_id), declined_bots=_declined_after_re_review(envelope))

    assert envelope['matched'] is False
    assert envelope['refusal_detected'] is False
    assert _declined_after_re_review(envelope) == []
    assert _state_of(result, _BOT) == rc.STATE_ABSENT
    assert result['review_state_summary'] == '1 absent'


def _verdict_naming(reference):
    """A marker-bearing CodeRabbit verdict, republished in place, naming ``reference``."""
    return f'{_CLEAN_VERDICT} (Review updated until commit {reference})' if reference else _CLEAN_VERDICT


def test_a_verdict_naming_the_head_is_not_a_decline(plan_context, monkeypatch):
    """Scenario 3b — the verdict named the commit it reviewed, so the step records no decline.

    Fails when the body-derived verdict is reverted: the comment arm then publishes
    ``head_sha_verified: false`` for this comment, the step forwards CodeRabbit in
    ``--declined-bots``, and the bot resolves ``declined`` — whose remedy is to accept
    the decline rather than re-trigger a reviewer that did review this HEAD.
    """
    plan_id = 'crr-verdict-names-head'
    _stub_provider(monkeypatch, [_comment('cr-verdict', _verdict_naming(f'[{_HEAD_SHA[:7]}]({_HEAD_SHA_URL})'))])

    envelope = _re_review()
    result = _classify(plan_id, _find(plan_context, plan_id), declined_bots=_declined_after_re_review(envelope))

    assert envelope['matched'] is True
    assert envelope['head_sha_verified'] is True
    assert _state_of(result, _BOT) != rc.STATE_DECLINED


def test_a_verdict_naming_another_commit_is_still_a_decline(plan_context, monkeypatch):
    """⛔ MATCHED NEGATIVE CONTROL for scenario 3b — the same verdict naming another commit declines.

    Same builder, same timestamps, same producer run; only the commit the body names
    differs. The bot answered with a finished verdict for a commit that is not the
    merge candidate, so the step records the decline, the producer credits nothing for
    this HEAD, and the bot resolves ``declined``. Without this control, scenario 3b
    would pass just as well against a verdict that never declines anything.
    """
    plan_id = 'crr-verdict-other-commit'
    _stub_provider(monkeypatch, [_comment('cr-verdict', _verdict_naming(_OTHER_SHA))])

    envelope = _re_review()
    result = _classify(plan_id, _find(plan_context, plan_id), declined_bots=_declined_after_re_review(envelope))

    assert envelope['matched'] is True
    assert envelope['head_sha_verified'] is False
    assert _state_of(result, _BOT) == rc.STATE_DECLINED
    assert result['participation_complete'] is False


@pytest.mark.parametrize(
    'reference',
    [
        pytest.param('', id='names-no-commit'),
        pytest.param(f'[{_HEAD_SHA[:7]}]', id='names-only-an-abbreviation'),
    ],
)
def test_a_verdict_naming_no_head_is_recorded_as_a_decline(plan_context, monkeypatch, reference):
    """The step forwards a decline for a finished verdict that names no full HEAD.

    The matcher's verdict is what the step reads, so the decline is recorded here
    whatever the producer concluded. The classifier then ranks the producer's own
    credit above it: a verdict naming no commit is credited on its first observation at
    a resolvable merge candidate, and proven participation outranks a decline by design
    (``review_completeness.classify_bot``), so the bot resolves as reviewed-and-clean
    rather than ``declined``.
    """
    plan_id = f'crr-verdict-{"abbrev" if reference else "no-commit"}'
    _stub_provider(monkeypatch, [_comment('cr-verdict', _verdict_naming(reference))])

    envelope = _re_review()
    declined = _declined_after_re_review(envelope)
    result = _classify(plan_id, _find(plan_context, plan_id), declined_bots=declined)

    assert envelope['matched'] is True
    assert envelope['head_sha_verified'] is False
    assert declined == [_BOT]
    assert _state_of(result, _BOT) == rc.STATE_PARTICIPATED_BUT_EMPTY
