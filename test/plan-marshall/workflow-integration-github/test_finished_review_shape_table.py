# SPDX-License-Identifier: FSL-1.1-ALv2
"""One shape table, one verdict: the three finished-review sites agree.

The done rule asks one question — is a FINISHED review on record — and three sites
answer it: the producer's ``finished_review_bots[]`` build, the post chokepoint
(``github_re_review._qualifying_review_on_record``) and the runbook lane's
``review-gate --required-reviewer`` check. Before this table they each read a
different predicate, so a formal review with an empty commit was a review for the
chokepoint and not for the producer.

Every artifact below is driven through ALL THREE sites and asserted to one verdict.
The second half pins the consequence: for one bot and one history, the chokepoint's
"done" and ``trigger-bot``'s trigger list are never both true, and
``request_fresh_review``'s refusal follows the chokepoint.
"""

from __future__ import annotations

import argparse

import github_pr
import github_re_review
import pytest

from conftest import load_script_module

lane = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'runbook_lane_shape_table_mod')
rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_PR = 147
_HEAD = 'a' * 40
_OTHER = 'b' * 40
_LOGIN = 'coderabbitai'
_BOT = 'coderabbit'

_MARKER_WITH_COMMIT = (
    f'<!-- final_review_risk_coverage:{{"sourceCommitId":"{_HEAD}","coveredCommitId":"{_HEAD}","kind":"reviewed"}} -->'
)
_MARKER_WITHOUT_COMMIT = '<!-- final_review_risk_coverage:{"kind":"reviewed"} -->'
_IN_PROGRESS_MARKER = '<!-- final_review_risk_coverage:{"coveredCommitId":"' + _HEAD + '","kind":"in_progress"} -->'
_REFUSAL = '> [!WARNING]\n> ## Review limit reached\n> Please wait 12 minutes before requesting another review.'
_WALKTHROUGH = '## Walkthrough\n\nsome prose before the review completes'

#: label -> (kind, body, commit_id, the one verdict every site must reach).
_SHAPES: dict[str, tuple[str, str, str, bool]] = {
    'formal review with a commit': ('review_body', 'No actionable comments were generated', _HEAD, True),
    'formal review without a commit': ('review_body', 'No actionable comments were generated', '', False),
    'marker with a commit': ('issue_comment', _MARKER_WITH_COMMIT, '', True),
    'marker without a commit': ('issue_comment', _MARKER_WITHOUT_COMMIT, '', False),
    'refusal with a marker': ('review_body', _REFUSAL + '\n' + _MARKER_WITH_COMMIT, '', True),
    'refusal without a marker': ('review_body', _REFUSAL, '', False),
    'in-progress summary': ('issue_comment', _IN_PROGRESS_MARKER, '', False),
    'walkthrough': ('issue_comment', _WALKTHROUGH, '', False),
}


def _comment(kind: str, body: str, *, commit_id: str = '') -> dict:
    return {
        'id': 'c-1',
        'kind': kind,
        'author': _LOGIN,
        'thread_id': '',
        'body': body,
        'path': '',
        'line': 0,
        'resolved': False,
        'created_at': '2026-01-01T00:00:00Z',
        'updated_at': '2026-01-01T00:05:00Z',
        'commit_id': commit_id,
        'reply_to_id': '',
        'thread_reply': False,
    }


def _stub(monkeypatch, comments: list[dict]) -> None:
    """Stub the provider surface the producer, the chokepoint and the post read."""
    monkeypatch.setattr(github_re_review, 'read_bot_in_progress', lambda _pr_number, _bot_kind: False)
    monkeypatch.setattr(
        github_re_review,
        'read_rate_window',
        lambda *_a, **_kw: {'status': 'free', 'expired': True, 'holder': '', 'seconds_remaining': 0.0},
    )
    for module in (github_pr, github_re_review):
        monkeypatch.setattr(module._github, 'check_auth', lambda: (True, ''))
        monkeypatch.setattr(module._github, 'fetch_pr_head_sha', lambda _pr_number: _HEAD)
        monkeypatch.setattr(module._github, 'fetch_pr_head_committed_at', lambda _pr_number: '')
        monkeypatch.setattr(module._github, 'post_pr_comment', lambda *_a, **_kw: {'status': 'success'})
        monkeypatch.setattr(
            module._github,
            'fetch_pr_comments_data',
            lambda _pr_number, unresolved_only=False: {
                'status': 'success',
                'provider': 'github',
                'complete': True,
                'comments': list(comments),
                'total': len(comments),
                'unresolved': 0,
            },
        )
        monkeypatch.setattr(
            module._github,
            'fetch_pr_reviews_with_commits',
            lambda _pr_number: {'status': 'success', 'reviews': []},
        )


def _producer(plan_context, monkeypatch, comments: list[dict]) -> set[str]:
    _stub(monkeypatch, comments)
    plan_id = 'shape-table-producer'
    plan_context.plan_dir_for(plan_id)
    result = github_pr.cmd_fetch_findings(argparse.Namespace(pr_number=_PR, plan_id=plan_id))
    assert result['status'] == 'success', result
    return {str(row['bot_kind']) for row in result.get('finished_review_bots') or []}


@pytest.mark.parametrize('label', sorted(_SHAPES))
def test_every_site_reaches_one_verdict_per_artifact(plan_context, monkeypatch, label: str) -> None:
    """The shape table: producer, chokepoint and lane agree on every artifact."""
    kind, body, commit_id, expected = _SHAPES[label]
    comments = [_comment(kind, body, commit_id=commit_id)]

    assert (_BOT in _producer(plan_context, monkeypatch, comments)) is expected
    assert github_re_review._qualifying_review_on_record(_PR, _BOT) is expected
    assert (lane._required_reviewers_without_a_review(comments, [_BOT]) == []) is expected


@pytest.mark.parametrize('label', sorted(_SHAPES))
def test_the_chokepoint_and_trigger_bot_never_both_hold(plan_context, monkeypatch, label: str) -> None:
    """A bot the chokepoint calls done is never the bot ``trigger-bot`` lists.

    ``trigger-bot`` removes a flagged bot only when the producer reports a finished
    review, so a chokepoint that reads a wider predicate strands the pull request:
    the post is refused as ``review_on_record_done`` while the trigger list still
    names the bot.
    """
    kind, body, commit_id, _expected = _SHAPES[label]
    comments = [_comment(kind, body, commit_id=commit_id)]
    finished = _producer(plan_context, monkeypatch, comments)

    done = github_re_review._qualifying_review_on_record(_PR, _BOT) is True
    strategy = github_re_review.resolve_strategy(_BOT)
    assert strategy is not None, f'{_BOT} resolves no strategy'
    refused = strategy.request_fresh_review(_PR, '2026-01-01T00:00:00Z')
    trigger = rc.list_bots_for_trigger([_BOT], [], [_BOT], finished_review_bots=list(finished))

    assert (refused.get('status') == 'refused') is done
    assert not (done and _BOT in trigger['trigger_bots']), f'{label} is stranded: refused and triggered'
