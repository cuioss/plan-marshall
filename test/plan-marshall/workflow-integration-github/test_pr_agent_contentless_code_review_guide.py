# SPDX-License-Identifier: FSL-1.1-ALv2
"""PR-Agent's SECOND persistent comment — the code-review pass's ``## PR Code Review Guide``.

The reviewer runs up to two passes, each publishing its own persistent
``issue_comment``: the security pass's ``## PR Reviewer Guide 🔍`` and, where a
repository opts in, the code-review pass's ``## PR Code Review Guide 🧭``. Both are
rendered by PR-Agent's own renderer, so they share one body layout. The registry
therefore names both headings in ``contentless_review_headings`` — an alternation
on top of the ``contentless_review_markers`` conjunction — and these arms pin that
the one rule covers both comments:

1. **Predicate arms** — ``_is_contentless_boilerplate`` drops the clean
   code-review Guide and keeps every deviating shape, including the clean rows
   under NO declared heading (the negative control proving the heading condition
   is live rather than vacuous).
2. **Producer arms** — ``cmd_fetch_findings`` drops a clean code-review Guide
   while still crediting participation, and files a code-review Guide that
   carries a finding byte-identical.
3. **Two-comment arms** — both Guides on one PR: each is judged on its own body,
   and the currency test credits the bot when either Guide is current.

The mirror arms for the security Guide live in
``test_pr_agent_contentless_guide_interaction_core.py`` / ``_guide.py``. Every
body comes from ``test/_shared/_pr_agent_guide_bodies.py``.
"""

from __future__ import annotations

import argparse

import pytest
from _pr_agent_guide_bodies import (
    CODE_REVIEW_CLEAN_GUIDE,
    CODE_REVIEW_GUIDE_DOCS_ONLY,
    CODE_REVIEW_GUIDE_HEADING,
    CODE_REVIEW_GUIDE_WITH_FINDING,
    GUIDE_HEADING,
    GUIDE_WITH_FINDING,
    OBSERVED_CLEAN_GUIDE,
    UNHEADED_CLEAN_TABLE,
)

from conftest import load_script_module

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')
query_findings = _findings_core.query_findings

_BOT = 'cuioss-review-bot'
_CREDITED = {'bot_kind': _BOT, 'evidence_kind': 'issue_comment'}
_CREATED_AT = '2026-07-30T09:00:00Z'
_EDITED_AT = '2026-07-30T11:30:00Z'
_HEAD_A = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
_HEAD_B = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'


def _guide_comment(body, comment_id, *, created_at=None, updated_at=None):
    """A ``cuioss-review-bot`` issue_comment carrying ``body``."""
    comment = {
        'id': comment_id,
        'author': _BOT,
        'thread_id': '',
        'kind': 'issue_comment',
        'body': body,
        'resolved': False,
    }
    if created_at is not None:
        comment['created_at'] = created_at
    if updated_at is not None:
        comment['updated_at'] = updated_at
    return comment


def _patch_provider(monkeypatch, comments, head_sha='deadbeef'):
    """Monkeypatch only the GitHub provider surface — the findings store stays real."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_committed_at', lambda pr_number: '')
    monkeypatch.setattr(
        github_pr._github,
        'fetch_pr_comments_data',
        lambda pr_number, unresolved_only=False: {
            'status': 'success',
            'provider': 'github',
            'comments': list(comments),
            'total': len(comments),
            'unresolved': len(comments),
        },
    )
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: head_sha)


def _run_fetch(pr_number, plan_id):
    """Run the producer's FIND verb against ``plan_id``, with its plan directory present."""
    from file_ops import get_base_dir  # local import: resolved per call, after the sandbox fixture

    (get_base_dir() / 'plans' / plan_id).mkdir(parents=True, exist_ok=True)
    return github_pr.cmd_fetch_findings(argparse.Namespace(pr_number=pr_number, plan_id=plan_id))


def _stored_bodies(plan_id):
    findings = query_findings(plan_id, finding_type='pr-comment')['findings']
    return [(f.get('raw_input') or {}).get('body', '') for f in findings]


# =============================================================================
# 1. Predicate arms
# =============================================================================


def test_code_review_guide_differs_from_the_observed_body_only_by_its_heading():
    """The code-review fixture is the observed clean body re-headed, nothing else.

    The code-review pass re-heads PR-Agent's own rendering, so the only difference
    between the two clean Guides is the heading. Pinning that keeps the code-review
    arms exercising the observed markup rather than a shape invented here.
    """
    assert CODE_REVIEW_CLEAN_GUIDE == OBSERVED_CLEAN_GUIDE.replace(GUIDE_HEADING, CODE_REVIEW_GUIDE_HEADING, 1)
    assert GUIDE_HEADING not in CODE_REVIEW_CLEAN_GUIDE


def test_clean_code_review_guide_is_contentless():
    """Positive control: the clean code-review Guide satisfies the same rule as the security one."""
    assert github_pr._is_contentless_boilerplate(OBSERVED_CLEAN_GUIDE, _BOT) is True
    assert github_pr._is_contentless_boilerplate(CODE_REVIEW_CLEAN_GUIDE, _BOT) is True


@pytest.mark.parametrize(
    'body',
    [CODE_REVIEW_GUIDE_WITH_FINDING, CODE_REVIEW_GUIDE_DOCS_ONLY, UNHEADED_CLEAN_TABLE],
    ids=['with-finding', 'docs-only', 'no-declared-heading'],
)
def test_deviating_code_review_shapes_are_not_contentless(body):
    """Negative controls: each deviation from the clean shape keeps the comment.

    ``no-declared-heading`` is the one that proves the heading alternation is a
    real condition: every conjunction marker is present and nothing actionable
    is, so only the absent heading keeps it from being dropped.
    """
    assert github_pr._is_contentless_boilerplate(body, _BOT) is False


def test_an_empty_heading_list_adds_no_condition(monkeypatch):
    """A bot declaring no headings is judged by its conjunction alone.

    The fail-open half of the alternation's contract: an absent field must leave
    every bot that has not declared it exactly where it was, so the unheaded clean
    table — kept above only by the heading condition — is dropped once the bot
    declares no heading at all.
    """
    monkeypatch.setattr(github_pr.bot_registry, 'contentless_review_headings', lambda bot_kind: [])
    assert github_pr._is_contentless_boilerplate(UNHEADED_CLEAN_TABLE, _BOT) is True


def test_headings_never_open_the_layer_on_their_own(monkeypatch):
    """With no conjunction markers the layer stays off, whatever headings are declared."""
    monkeypatch.setattr(github_pr.bot_registry, 'contentless_review_markers', lambda bot_kind: [])
    assert github_pr._is_contentless_boilerplate(CODE_REVIEW_CLEAN_GUIDE, _BOT) is False


# =============================================================================
# 2. Producer arms
# =============================================================================


def test_clean_code_review_guide_is_dropped_but_still_credits_participation(plan_context, monkeypatch):
    """A clean code-review Guide files no finding, and the bot is still a proven participant."""
    plan_id = 'cuioss-review-bot-code-review-clean-dropped'
    _patch_provider(monkeypatch, [_guide_comment(CODE_REVIEW_CLEAN_GUIDE, 'code-review-1')])

    result = _run_fetch(1301, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 0
    assert result['count_skipped_noise'] == 1
    assert result['count_skipped_refusal'] == 0
    assert result['producer_mismatch_hash_id'] is None
    assert _CREDITED in result['participated_bots']
    assert _stored_bodies(plan_id) == []


def test_code_review_guide_with_a_finding_is_stored_byte_identical(plan_context, monkeypatch):
    """One ``<details>`` finding vetoes the drop under the code-review heading too."""
    plan_id = 'cuioss-review-bot-code-review-with-finding'
    _patch_provider(monkeypatch, [_guide_comment(CODE_REVIEW_GUIDE_WITH_FINDING, 'code-review-1')])

    result = _run_fetch(1302, plan_id)

    assert result['status'] == 'success'
    assert result['count_stored'] == 1
    assert result['count_skipped_noise'] == 0
    assert _stored_bodies(plan_id) == [CODE_REVIEW_GUIDE_WITH_FINDING]


# =============================================================================
# 3. Two-comment arms
# =============================================================================


def test_both_clean_guides_on_one_pr_are_each_dropped(plan_context, monkeypatch):
    """Two clean Guides are two drops — neither is mistaken for the other's duplicate."""
    plan_id = 'cuioss-review-bot-two-clean-guides'
    _patch_provider(
        monkeypatch,
        [
            _guide_comment(OBSERVED_CLEAN_GUIDE, 'security-1'),
            _guide_comment(CODE_REVIEW_CLEAN_GUIDE, 'code-review-1'),
        ],
    )

    result = _run_fetch(1303, plan_id)

    assert result['count_stored'] == 0
    assert result['count_skipped_noise'] == 2
    assert result['participated_bots'] == [_CREDITED]


def test_each_guide_is_judged_on_its_own_body(plan_context, monkeypatch):
    """A clean security Guide beside a finding-bearing code-review Guide files exactly the latter.

    And the mirror: the code-review Guide's clean shape must not drop a security
    Guide that carries a finding. Each body is judged alone.
    """
    security_with_finding = GUIDE_WITH_FINDING
    plan_id = 'cuioss-review-bot-guides-judged-alone'
    _patch_provider(
        monkeypatch,
        [
            _guide_comment(OBSERVED_CLEAN_GUIDE, 'security-1'),
            _guide_comment(CODE_REVIEW_GUIDE_WITH_FINDING, 'code-review-1'),
        ],
    )
    first = _run_fetch(1304, plan_id)
    assert first['count_stored'] == 1
    assert _stored_bodies(plan_id) == [CODE_REVIEW_GUIDE_WITH_FINDING]

    mirror_plan = 'cuioss-review-bot-guides-judged-alone-mirror'
    _patch_provider(
        monkeypatch,
        [
            _guide_comment(security_with_finding, 'security-1'),
            _guide_comment(CODE_REVIEW_CLEAN_GUIDE, 'code-review-1'),
        ],
    )
    mirror = _run_fetch(1305, mirror_plan)
    assert mirror['count_stored'] == 1
    assert _stored_bodies(mirror_plan) == [security_with_finding]


def test_one_current_guide_credits_the_bot_after_head_advances(plan_context, monkeypatch):
    """Each Guide clears the currency test on its own row; one current Guide is enough.

    Both Guides are credited at ``_HEAD_A``. After the merge candidate advances to
    ``_HEAD_B`` only the code-review Guide is edited in place. The untouched security
    Guide proves nothing about ``_HEAD_B``, but the edited one does — so the bot is
    credited, not reported stale. The matched control is the next case.
    """
    plan_id = 'cuioss-review-bot-two-guides-one-current'
    security = _guide_comment(OBSERVED_CLEAN_GUIDE, 'security-1', created_at=_CREATED_AT, updated_at=_CREATED_AT)
    code_review = _guide_comment(
        CODE_REVIEW_CLEAN_GUIDE, 'code-review-1', created_at=_CREATED_AT, updated_at=_CREATED_AT
    )
    _patch_provider(monkeypatch, [security, code_review], head_sha=_HEAD_A)
    first = _run_fetch(1306, plan_id)
    assert first['participated_bots'] == [_CREDITED]

    edited = dict(code_review, updated_at=_EDITED_AT)
    _patch_provider(monkeypatch, [security, edited], head_sha=_HEAD_B)
    second = _run_fetch(1306, plan_id)

    assert second['participated_bots'] == [_CREDITED]
    assert second['stale_participation_bots'] == []


def test_two_untouched_guides_go_stale_once_head_advances(plan_context, monkeypatch):
    """Matched control: when NEITHER Guide moves past the advance, the bot is stale."""
    plan_id = 'cuioss-review-bot-two-guides-both-stale'
    security = _guide_comment(OBSERVED_CLEAN_GUIDE, 'security-1', created_at=_CREATED_AT, updated_at=_CREATED_AT)
    code_review = _guide_comment(
        CODE_REVIEW_CLEAN_GUIDE, 'code-review-1', created_at=_CREATED_AT, updated_at=_CREATED_AT
    )
    _patch_provider(monkeypatch, [security, code_review], head_sha=_HEAD_A)
    first = _run_fetch(1307, plan_id)
    assert first['participated_bots'] == [_CREDITED]

    _patch_provider(monkeypatch, [security, code_review], head_sha=_HEAD_B)
    second = _run_fetch(1307, plan_id)

    assert second['participated_bots'] == []
    assert second['stale_participation_bots'] == [_CREDITED]
