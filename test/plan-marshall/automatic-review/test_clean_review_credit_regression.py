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
3. **A republished comment naming the awaited HEAD does not resolve ``declined``.**
   Before the comment arm read its body, every comment match published
   ``head_sha_verified: false`` and the step recorded a decline the bot never made —
   the blocking member whose remedy is to accept it rather than re-trigger.
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
    """Stub the GitHub provider surface the producer AND the re-review await reach."""
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

    Every scenario's comment post-dates the trigger, so the first poll completes and
    the real poll loop never sleeps.
    """
    strategy = github_re_review.resolve_strategy(_BOT)
    envelope = strategy.await_fresh_review(_PR_NUMBER, _HEAD_SHA, _TRIGGER, bot_kind=_BOT, timeout=1, interval=0)
    assert envelope['status'] == 'success', envelope
    return envelope


def _declined_after_re_review(envelope):
    """The step's documented decline rule: an answer that verified no HEAD is a decline."""
    return [_BOT] if envelope['matched'] and not envelope['head_sha_verified'] else []


def test_a_republished_comment_naming_the_head_is_not_a_decline(plan_context, monkeypatch):
    """Scenario 3 — the bot named the commit it reviewed, so the step records no decline.

    Fails when the body-derived verdict is reverted: the comment arm then publishes
    ``head_sha_verified: false`` for this comment, the step forwards CodeRabbit in
    ``--declined-bots``, and the bot resolves ``declined`` — whose remedy is to accept
    the decline rather than re-trigger a reviewer that did review this HEAD.

    The comment is a republished SUMMARY, so it carries no verdict marker and the
    producer credits nothing for it; the bot therefore stays ``absent`` — still
    awaiting its verdict, and still re-triggerable — rather than ``declined``.
    """
    plan_id = 'crr-republished-names-head'
    _stub_provider(monkeypatch, [_comment('cr-summary', _REPUBLISHED_SUMMARY)])

    envelope = _re_review()
    result = _classify(plan_id, _find(plan_context, plan_id), declined_bots=_declined_after_re_review(envelope))

    assert envelope['matched'] is True
    assert _state_of(result, _BOT) != rc.STATE_DECLINED
    assert _state_of(result, _BOT) == rc.STATE_ABSENT
    assert result['review_state_summary'] == '1 absent'


@pytest.mark.parametrize(
    'reference',
    [
        pytest.param('', id='names-no-commit'),
        pytest.param(f'[{_HEAD_SHA[:7]}]', id='names-only-an-abbreviation'),
    ],
)
def test_a_republished_comment_not_naming_the_head_is_still_a_decline(plan_context, monkeypatch, reference):
    """⛔ MATCHED NEGATIVE CONTROL for scenario 3 — the same comment without the HEAD declines.

    Same builder, same timestamps, same producer run; only the body's reference to the
    merge candidate is gone. The bot answered without naming this HEAD, so the step
    records the decline and the bot resolves ``declined``. Without this control,
    scenario 3 would pass just as well against a verdict that never declines anything.
    """
    plan_id = f'crr-republished-{"abbrev" if reference else "no-commit"}'
    body = f'{_WALKTHROUGH} (Review updated until commit {reference})' if reference else _WALKTHROUGH
    _stub_provider(monkeypatch, [_comment('cr-summary', body)])

    envelope = _re_review()
    result = _classify(plan_id, _find(plan_context, plan_id), declined_bots=_declined_after_re_review(envelope))

    assert envelope['matched'] is True
    assert _state_of(result, _BOT) == rc.STATE_DECLINED
    assert result['participation_complete'] is False
