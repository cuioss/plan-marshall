# SPDX-License-Identifier: FSL-1.1-ALv2
"""The done rule's one question has one reader.

The done rule rests on a single question — is a FINISHED review on record — and the
producer, the post chokepoint and the runbook lane must answer it the same way. This
module pins the producer and the chokepoint against the SAME artifacts, so a formal
review cannot be a review at one site and not at another.

The artifacts below are the cases the three sites must agree on:

* a formal ``review_body`` with and without the commit it reviewed;
* a marker-bearing ``issue_comment`` that names a covered commit;
* a refusal-shaped body beside a readable finished marker;
* a body only the ENUMERATIVE refusal arm reads as a refusal, which the producer's
  own ``_is_refusal_notice`` does not read;
* a pre-review walkthrough.
"""

from __future__ import annotations

import argparse

import _github_pr
import github_pr
import github_re_review
import pytest

_PR = 147
_HEAD = 'a' * 40
_LOGIN = 'coderabbitai'

_REFUSAL = '> [!WARNING]\n> ## Review limit reached\n> Please wait 12 minutes before requesting another review.'
#: The registry arm's phrase in another letter case and with no notice presentation:
#: the structural arm needs a notice SHAPE as well as the limit statement, so only the
#: registry arm can read this body.
_REFUSAL_CASE_VARIANT = 'REVIEW LIMIT REACHED'
#: Short, anchor-less, and matched by NO pre-noise-filter refusal arm — the one body
#: the enumerative arm exists for. The arm is inert at its shipped (unmeasured)
#: threshold, so the test below supplies a measured bound.
_ENUMERATIVE_REFUSAL = 'Please resubmit this pull request later.'
_MARKER = (
    f'<!-- final_review_risk_coverage:{{"sourceCommitId":"{_HEAD}","coveredCommitId":"{_HEAD}","kind":"reviewed"}} -->'
)
#: A readable, finished marker that names NO commit — a claim nobody can place.
_MARKER_WITHOUT_COMMIT = '<!-- final_review_risk_coverage:{"kind":"reviewed"} -->'
_WALKTHROUGH = '## Walkthrough\n\nsome prose before the review completes'


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
    """Stub the provider surface the producer and the chokepoint both read."""
    monkeypatch.setattr(github_re_review, 'read_bot_in_progress', lambda _pr_number, _bot_kind: False)
    for module in (github_pr, github_re_review):
        monkeypatch.setattr(module._github, 'check_auth', lambda: (True, ''))
        monkeypatch.setattr(module._github, 'fetch_pr_head_sha', lambda _pr_number: _HEAD)
        monkeypatch.setattr(module._github, 'fetch_pr_head_committed_at', lambda _pr_number: '')
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


def _producer_finished_bots(plan_context, monkeypatch, comments: list[dict]) -> set[str]:
    """Drive the producer's ``finished_review_bots[]`` build over ``comments``."""
    _stub(monkeypatch, comments)
    plan_id = 'one-reader-producer'
    plan_context.plan_dir_for(plan_id)
    result = github_pr.cmd_fetch_findings(argparse.Namespace(pr_number=_PR, plan_id=plan_id))
    assert result['status'] == 'success', result
    return {str(row['bot_kind']) for row in result.get('finished_review_bots') or []}


def _chokepoint(monkeypatch, comments: list[dict]) -> bool | None:
    """Ask the post chokepoint's finished-review read over ``comments``."""
    _stub(monkeypatch, comments)
    return github_re_review._qualifying_review_on_record(_PR, 'coderabbit')


def test_the_chokepoint_refuses_an_empty_commit_review_body(plan_context, monkeypatch) -> None:
    """⛔ The empty-commit formal review proves no head, so it is no finished review.

    Both sites ask ``is_finished_review``, so the record the producer leaves out of
    ``finished_review_bots`` is the record the chokepoint does not refuse the trigger
    for.
    """
    comments = [_comment('review_body', 'No actionable comments were generated', commit_id='')]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == set()
    assert _chokepoint(monkeypatch, comments) is False


def test_the_chokepoint_and_the_producer_admit_a_review_body_with_a_commit(plan_context, monkeypatch) -> None:
    """HOLDS AT THE BASE: the commit a formal review names is the artifact."""
    comments = [_comment('review_body', 'No actionable comments were generated', commit_id=_HEAD)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == {'coderabbit'}
    assert _chokepoint(monkeypatch, comments) is True


def test_the_chokepoint_and_the_producer_admit_a_marker_bearing_issue_comment(plan_context, monkeypatch) -> None:
    """HOLDS AT THE BASE: a readable kind=reviewed marker naming a commit is a review."""
    comments = [_comment('issue_comment', _MARKER)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == {'coderabbit'}
    assert _chokepoint(monkeypatch, comments) is True


def test_the_chokepoint_and_the_producer_admit_a_refusal_beside_a_finished_marker(plan_context, monkeypatch) -> None:
    """HOLDS AT THE BASE: CodeRabbit keeps a later limit notice beside its verdict."""
    comments = [_comment('review_body', _REFUSAL + '\n' + _MARKER, commit_id='')]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == {'coderabbit'}
    assert _chokepoint(monkeypatch, comments) is True


def test_the_chokepoint_and_the_producer_agree_on_an_enumerative_refusal(plan_context, monkeypatch) -> None:
    """⛔ A body only the ENUMERATIVE arm reads is not a refusal for this question.

    The enumerative arm answers "is this not review feedback" at a different pipeline
    position, and ``_is_refusal_notice`` covers only the arms answerable before the
    producer's noise filter. Both sites read that boolean, so a formal review naming a
    commit is a finished review whatever the enumerative arm says.
    """
    monkeypatch.setattr(_github_pr, 'UNRECOGNISED_REFUSAL_MAX_CHARS', 200)
    assert _github_pr._is_unrecognised_refusal(_ENUMERATIVE_REFUSAL, 'coderabbit') is True
    assert _github_pr._is_refusal_notice(_ENUMERATIVE_REFUSAL, 'coderabbit') is False
    comments = [_comment('review_body', _ENUMERATIVE_REFUSAL, commit_id=_HEAD)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == {'coderabbit'}
    assert _chokepoint(monkeypatch, comments) is True


@pytest.mark.parametrize(
    ('body', 'commit_id'),
    [
        (_WALKTHROUGH, ''),
        ('## Review skipped\n\nDraft pull request.', ''),
    ],
)
def test_the_chokepoint_and_the_producer_agree_on_a_non_review(plan_context, monkeypatch, body, commit_id) -> None:
    """MATCHED CONTROL — neither site admits an artifact that is not a review."""
    comments = [_comment('issue_comment', body, commit_id=commit_id)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == set()
    assert _chokepoint(monkeypatch, comments) is False


def test_a_case_variant_refusal_is_a_refusal_at_both_sites(plan_context, monkeypatch) -> None:
    """⛔ The registry arm matches case-insensitively.

    A bot that answers a quota question in capitals has still declined. A
    case-sensitive match files that body as review feedback, so a review body naming a
    commit counts as a finished review nobody received.
    """
    assert _github_pr._is_rate_limit_notice(_REFUSAL_CASE_VARIANT) is False, (
        'the structural arm must not reach this body, or the case does not decide it'
    )
    comments = [_comment('review_body', _REFUSAL_CASE_VARIANT, commit_id=_HEAD)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == set()
    assert _chokepoint(monkeypatch, comments) is False


def test_a_commit_less_marker_does_not_lift_a_refusal(plan_context, monkeypatch) -> None:
    """⛔ The refusal exemption is a marker NAMING A COMMIT, never merely `reviewed`.

    A `kind: reviewed` marker naming no commit claims a review of some unknowable
    head, so beside a refusal it leaves the refusal standing.
    """
    comments = [_comment('review_body', _REFUSAL + '\n' + _MARKER_WITHOUT_COMMIT, commit_id=_HEAD)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == set()
    assert _chokepoint(monkeypatch, comments) is False


@pytest.mark.parametrize(
    ('covered', 'expected'),
    [
        ('a' * 40, True),
        ('cf28a05db', True),
        ('pending', False),
        ('n/a', False),
        ('', False),
    ],
)
def test_the_commit_a_marker_names_must_be_a_commit_id(covered: str, expected: bool) -> None:
    """⛔ A placeholder in the covered field is not a commit, so it is not a review.

    The marker field is dedicated to the commit a review covered, so an all-hex value
    in it IS a commit however abbreviated; a word that is not hex names no commit at
    all. Before this test, a refusal body beside ``coveredCommitId: "pending"`` was
    exempt from the refusal exclusion at all three finished-review sites.
    """
    body = f'<!-- final_review_risk_coverage:{{"coveredCommitId":"{covered}","kind":"reviewed"}} -->'

    assert _github_pr.review_coverage_names_commit(body) is expected


def test_a_refusal_naming_a_commit_and_no_marker_is_not_a_finished_review(plan_context, monkeypatch) -> None:
    """HOLDS AT THE BASE: the commit a refusal names is the head it DECLINED."""
    comments = [_comment('review_body', _REFUSAL, commit_id=_HEAD)]

    assert _producer_finished_bots(plan_context, monkeypatch, comments) == set()
    assert _chokepoint(monkeypatch, comments) is False
