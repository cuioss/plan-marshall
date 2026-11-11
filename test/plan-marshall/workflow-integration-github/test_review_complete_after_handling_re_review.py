# SPDX-License-Identifier: FSL-1.1-ALv2
"""One handled review completes a bot that declares ``review_complete_after_handling``.

The review-allowance economy is spent only after a review exists. This module pins
both halves of that rule at the two places a request can originate:

- ``request_fresh_review`` — the one post chokepoint — refuses a flagged bot whose
  qualifying review is already on record on this pull request, and posts nothing; a
  pull request with no qualifying review is triggered exactly as before, and so is
  every bot without the flag.
- ``resolve_recovery_action`` — the refusal derivation — settles a flagged bot with
  a credited or stale review instead of returning the trigger arm, while leaving
  every other bot's derivation unchanged.

A qualifying review is the producer's own admitted evidence: a comment in one of the
bot's declared ``participation_evidence`` publish shapes, carrying that shape's
declared content marker where one is declared. A walkthrough posted before a review
completes carries no declared marker and is not admitted; a refusal, an acknowledgment
and a skip notice are not declared publish shapes at all. Those are the shapes that
must keep the first trigger reachable.
"""

from __future__ import annotations

import bot_registry
import github_re_review
import pytest

_EARLIER = 'a' * 40
_PR = 142
_PUSH_TIME = '2026-01-01T00:00:00Z'

#: A finished review's summary comment, in the marker the producer's one parser reads.
_COVERAGE_BODY = (
    '<!-- final_review_risk_coverage:'
    f'{{"sourceCommitId":"{_EARLIER}","coveredCommitId":"{_EARLIER}","kind":"reviewed"}} -->'
)
_REFUSAL_BODY = '> [!WARNING] > ## Review limit reached > Please wait 12 minutes before requesting another review.'
_ACKNOWLEDGMENT_BODY = 'Review triggered'
_SKIP_BODY = '## Review skipped\n\nDraft pull request.'


def _history(monkeypatch, comments, *, status: str = 'success', complete: bool = True) -> None:
    """Serve ``comments`` as the pull request's history the done read consumes."""
    monkeypatch.setattr(
        github_re_review._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {
            'status': status,
            'complete': complete,
            'comments': list(comments),
        },
    )


def _record_posts(monkeypatch) -> list[tuple]:
    """Replace ``post_pr_comment`` with a recorder; return the list it appends to."""
    posted: list[tuple] = []

    def fake_post(pr_number, body):
        posted.append((pr_number, body))
        return {'status': 'success', 'operation': 'post_pr_comment', 'pr_number': pr_number}

    monkeypatch.setattr(github_re_review._github, 'post_pr_comment', fake_post)
    return posted


def _free_window(monkeypatch) -> None:
    """Hold the rate-window read at NO STORED RECORD, so the window never refuses."""
    monkeypatch.setattr(
        github_re_review,
        'read_rate_window',
        lambda *_a, **_kw: {'status': 'free', 'expired': True, 'holder': '', 'seconds_remaining': 0.0},
    )


def _comment(kind: str, body: str, *, author: str = 'coderabbitai', commit_id: str = '') -> dict:
    return {
        'kind': kind,
        'author': author,
        'body': body,
        'commit_id': commit_id,
        'created_at': '2026-01-01T00:00:00Z',
    }


def _request(bot_kind: str, monkeypatch) -> dict:
    _free_window(monkeypatch)
    return github_re_review.resolve_strategy(bot_kind).request_fresh_review(_PR, _PUSH_TIME)


# ---------------------------------------------------------------------------
# The registry declaration
# ---------------------------------------------------------------------------


def test_coderabbit_declares_the_flag_and_no_other_bot_does():
    """The done rule is registry data: one bot opts in, everything else is unchanged."""
    assert bot_registry.review_complete_after_handling('coderabbit') is True
    others = [bot for bot in bot_registry.bot_kinds() if bot != 'coderabbit']
    assert others, 'the registry declares no other bot — the negative half would be vacuous'
    assert [bot for bot in others if bot_registry.review_complete_after_handling(bot)] == []


def test_an_unregistered_bot_declares_no_done_rule():
    """Fail-closed: an unknown token is never granted the economy."""
    assert bot_registry.review_complete_after_handling('not-a-registered-bot') is False


# ---------------------------------------------------------------------------
# request_fresh_review — the one post chokepoint
# ---------------------------------------------------------------------------


def test_a_marker_bearing_finished_review_refuses_the_trigger(monkeypatch):
    """⛔ The load-bearing case: the review is on record, so no comment reaches the PR."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('issue_comment', _COVERAGE_BODY)])

    result = _request('coderabbit', monkeypatch)

    assert posted == [], 'a trigger was posted although the qualifying review is on record'
    assert result['status'] == 'refused'
    assert result['reason'] == 'review_on_record_done'
    assert result['bot_kind'] == 'coderabbit'
    assert result['escalated'] is False


def test_a_formal_review_record_refuses_the_trigger(monkeypatch):
    """A review record is admitted evidence whatever commit it names — the head is not asked."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('review_body', 'findings here', commit_id='')])

    result = _request('coderabbit', monkeypatch)

    assert posted == []
    assert result['status'] == 'refused'
    assert result['reason'] == 'review_on_record_done'


def test_the_escalated_command_is_refused_too(monkeypatch):
    """Done stops BOTH commands: the escalated one spends a review as well."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('issue_comment', _COVERAGE_BODY)])
    _free_window(monkeypatch)

    result = github_re_review.resolve_strategy('coderabbit').request_fresh_review(_PR, _PUSH_TIME, escalated=True)

    assert posted == []
    assert result['status'] == 'refused'
    assert result['reason'] == 'review_on_record_done'
    assert result['escalated'] is True


def test_a_pull_request_with_no_review_is_triggered_once(monkeypatch):
    """MATCHED CONTROL — the same bot, the same read, no review on record: it posts.

    Without this a refusal here would be equally consistent with a verb that never
    posts for this bot at all.
    """
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [])

    result = _request('coderabbit', monkeypatch)

    assert result['status'] == 'success'
    assert posted == [(_PR, '@coderabbitai review')]


@pytest.mark.parametrize(
    ('case_id', 'body'),
    [
        ('refusal', _REFUSAL_BODY),
        ('acknowledgment', _ACKNOWLEDGMENT_BODY),
        ('skip_notice', _SKIP_BODY),
    ],
)
def test_a_non_review_shape_is_not_a_review_on_record(case_id, body, monkeypatch):
    """A refusal, an acknowledgment or a skip notice is not done.

    None is a declared ``participation_evidence`` publish shape, so none is admitted
    evidence — precisely the shapes that must keep the FIRST trigger reachable on a
    pull request whose only bot output is one of them.
    """
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('issue_comment', body)])

    result = _request('coderabbit', monkeypatch)

    assert result['status'] == 'success', case_id
    assert posted == [(_PR, '@coderabbitai review')], case_id


def test_an_unflagged_bot_is_never_refused_by_the_done_rule(monkeypatch):
    """MATCHED CONTROL — a bot without the flag posts even beside a qualifying review."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('issue_comment', _COVERAGE_BODY)])

    result = _request('sourcery', monkeypatch)

    assert result['status'] == 'success'
    assert posted == [(_PR, '@sourcery-ai review')]


def test_an_unreadable_history_permits_the_post(monkeypatch):
    """A failed read is not evidence of a review on record; refusing would be fail-worse.

    The same direction the rate-window guard takes: a read that could not be performed
    must not take the whole re-review path down, a far larger failure than the one
    redundant comment it would prevent.
    """
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [], status='error')

    result = _request('coderabbit', monkeypatch)

    assert result['status'] == 'success'
    assert posted == [(_PR, '@coderabbitai review')]


def test_a_capped_history_is_not_read_as_no_review(monkeypatch):
    """A partial fetch may hide the review, so it permits the post like a failed read."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [], complete=False)

    result = _request('coderabbit', monkeypatch)

    assert result['status'] == 'success'
    assert posted == [(_PR, '@coderabbitai review')]


def test_a_marker_without_a_commit_is_still_admitted_evidence(monkeypatch):
    """The marker is the producer's admission test; the head is never asked at this site.

    A marker naming no commit is not HEAD-BOUND evidence — it cannot credit a review of
    the current tree — but it IS an admitted review artifact, which is the only question
    the done rule asks before suppressing a request.
    """
    posted = _record_posts(monkeypatch)
    _history(
        monkeypatch,
        [_comment('issue_comment', '<!-- final_review_risk_coverage:{"kind":"reviewed"} -->')],
    )

    result = _request('coderabbit', monkeypatch)

    assert posted == []
    assert result['status'] == 'refused'


def test_a_summary_without_a_declared_marker_is_not_a_review(monkeypatch):
    """A pre-review walkthrough carries no declared marker, so it credits nothing."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('issue_comment', '## Walkthrough\n\nsome prose')])

    result = _request('coderabbit', monkeypatch)

    assert result['status'] == 'success'
    assert posted == [(_PR, '@coderabbitai review')]


def test_the_retired_review_wrapper_is_still_admitted_evidence(monkeypatch):
    """Both declared markers are the producer's admission test, so both suppress a request."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('issue_comment', '<!-- recent_review_start -->\nNo findings.')])

    result = _request('coderabbit', monkeypatch)

    assert posted == []
    assert result['status'] == 'refused'


def test_an_inline_comment_proves_a_review(monkeypatch):
    """An inline comment is published BY a review, so it is evidence one happened."""
    posted = _record_posts(monkeypatch)
    _history(monkeypatch, [_comment('inline', 'a line comment', commit_id='')])

    result = _request('coderabbit', monkeypatch)

    assert posted == []
    assert result['status'] == 'refused'
    assert result['reason'] == 'review_on_record_done'


def test_a_bot_with_a_review_on_record_settles_a_no_unreviewed_commit_reply():
    """The done arm is the same under the bot's 'nothing new to review' reply."""
    verdict = github_re_review.resolve_recovery_action(
        'coderabbit',
        condition=github_re_review.REFUSAL_CONDITION_NO_UNREVIEWED_COMMIT,
        review_on_record='stale',
        pending_findings=0,
    )

    assert verdict['action'] == 'accept_review_on_record'
    assert verdict['reason'] == 'review_on_record_done'


# ---------------------------------------------------------------------------
# resolve_recovery_action — the refusal derivation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('review_on_record', ['credited', 'stale'])
def test_a_flagged_bot_with_a_review_on_record_settles_without_posting(review_on_record):
    """The elapsed window settles on the recorded review instead of re-triggering it."""
    verdict = github_re_review.resolve_recovery_action(
        'coderabbit',
        cause='quota',
        review_on_record=review_on_record,
        pending_findings=0,
        window_expired=True,
        attempts_remaining=5,
    )

    assert verdict['action'] == 'accept_review_on_record'
    assert verdict['reason'] == 'review_on_record_done'


def test_a_flagged_bot_with_pending_findings_routes_to_triage():
    """Handling is not removed: pending findings are triaged, never re-requested."""
    verdict = github_re_review.resolve_recovery_action(
        'coderabbit',
        cause='quota',
        review_on_record='stale',
        pending_findings=2,
        window_expired=True,
        attempts_remaining=5,
    )

    assert verdict['action'] == 'await_triage'
    assert verdict['reason'] == 'review_on_record_done_findings_pending'


def test_a_flagged_bot_with_an_unobserved_findings_state_is_unmeasured():
    """Fail-closed: an observation nobody made is not a done verdict."""
    verdict = github_re_review.resolve_recovery_action(
        'coderabbit',
        cause='quota',
        review_on_record='credited',
        pending_findings=None,
        window_expired=True,
        attempts_remaining=5,
    )

    assert verdict['action'] == 'unmeasured'
    assert verdict['reason'] == 'no_findings_observation'


def test_a_flagged_bot_with_no_review_still_follows_the_quota_policy():
    """MATCHED CONTROL — no review on record leaves today's dispatch unchanged."""
    verdict = github_re_review.resolve_recovery_action(
        'coderabbit',
        cause='quota',
        review_on_record='absent',
        pending_findings=0,
        window_expired=True,
        attempts_remaining=5,
    )

    assert verdict['action'] == 'close_and_reopen'
    assert verdict['reason'] == 'claim_window_elapsed'


def test_an_unflagged_bot_never_takes_the_done_arm():
    """MATCHED CONTROL — the same review observation, no flag: today's derivation stands."""
    verdict = github_re_review.resolve_recovery_action(
        'sourcery',
        cause='quota',
        review_on_record='stale',
        pending_findings=0,
        window_expired=True,
        attempts_remaining=5,
    )

    assert verdict['action'] != 'accept_review_on_record'
    assert verdict['reason'] != 'review_on_record_done'
    # sourcery declares hard_quota, so its refusal escalates rather than awaiting —
    # the point here is only that the done branch did not claim it.
    assert verdict['action'] == 'escalate_not_awaitable'
