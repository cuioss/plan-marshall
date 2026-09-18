# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fixture-accurate provider tests for the D1 pre-merge comment-completeness barrier.

The barrier re-runs the ``github_pr fetch_findings`` producer immediately before
merge/enqueue and then queries pending ``pr-comment`` findings; any pending
finding blocks the merge. These tests exercise the two barrier-critical producer
properties end-to-end against the REAL findings store (isolated via the autouse
``plan_context`` PLAN_BASE_DIR sandbox), monkeypatching only the GitHub provider
surface (``check_auth``, ``fetch_pr_comments_data``, ``fetch_pr_head_sha``):

    (a) late-comment-after-triage — a comment posted after the prior fetch is
        filed as a NEW pending pr-comment finding on the re-fetch (the
        ``(bot_kind, comment_id)`` dedup does not suppress a genuinely-new
        comment), so the barrier's pending query is non-empty and blocks.
    (b) clean-path — a re-fetch whose comments were all already stored files
        zero new findings, so the barrier query is empty and the merge proceeds.
    (c) termination — once triage's own batched response comment is the only new
        comment on the PR, the re-fetch excludes it, the barrier's pending query
        stays EMPTY and the merge proceeds. Before the self-response exclusion
        this reply was filed as a fresh pending finding, so the barrier blocked,
        triage responded again, and the cycle never terminated.
    (d) guard trips and reports — at ``_SELF_RESPONSE_LOOP_BOUND`` CONSECUTIVE
        self-authored responses (the current cycle's unbroken run, not the PR's
        lifetime total) the producer REPORTS exhaustion as a
        ``(self-response-loop)`` Q-Gate finding instead of passing silently.
    (e) stale-override refusal — an operator authorization granted at one HEAD
        does NOT authorize a merge at a later HEAD carrying commits the ruling
        never covered, and a re-grant at the new HEAD restores it, so the
        escape hatch is BOUND rather than removed.
    (f) cross-kind refusal — an authorization granted over a DIFFERENT gap at the
        SAME HEAD (the ``pre-merge-consent`` the Pre-Merge Confirmation Gate
        grants moments earlier) does NOT satisfy this barrier, while the
        barrier's own ``barrier-ask-override`` at that same HEAD does.
        HEAD-binding alone is not sufficient: admissibility is per-gap.
    (g) widened-member parity — the two taxonomy members that refine ``absent``
        (``participated_stale`` and ``not_triggered``) gate the merge EXACTLY as
        ``absent`` does. The barrier-relevant projection of the verdict is compared
        against the ``absent`` verdict for the SAME scenario rather than against a
        transcribed expectation, with a matched ``participated`` negative control
        proving the comparison can fail.

The provider response is built from a real fixture shape (mirroring
``test_github_pr.py``), so a green fixture cannot diverge from production
provider behaviour.
"""

import argparse

import pytest

from conftest import load_script_module

PLAN_IDS: tuple[str, ...] = (
    'barrier-absent-required-bot',
    'barrier-clean-path',
    'barrier-cross-kind',
    'barrier-late-comment',
    'barrier-optional-silence',
    'barrier-self-response-bound',
    'barrier-self-response-terminates',
    'barrier-stale-override',
)
github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')
query_findings = _findings_core.query_findings
query_qgate_findings = _findings_core.query_qgate_findings
resolve_finding = _findings_core.resolve_finding
_INITIAL_COMMENTS = [
    {
        'id': 'c1',
        'author': 'coderabbitai',
        'thread_id': 'PRRT_1',
        'kind': 'inline',
        'body': 'Consider handling the None case here before dereferencing.',
        'path': 'src/a.py',
        'line': 10,
        'resolved': False,
    },
    {
        'id': 'c2',
        'author': 'sourcery-ai',
        'thread_id': '',
        'kind': 'review_body',
        'body': 'Overall the change reads well but this helper should be extracted.',
        'resolved': False,
    },
]
_LATE_COMMENT = {
    'id': 'c-late',
    'author': 'coderabbitai',
    'thread_id': 'PRRT_9',
    'kind': 'inline',
    'body': 'This newly-pushed branch introduces an off-by-one in the loop bound.',
    'path': 'src/c.py',
    'line': 42,
    'resolved': False,
}


def _patch_provider(monkeypatch, comments):
    """Monkeypatch the GitHub provider surface ``github_pr`` reaches through ``_github``."""
    monkeypatch.setattr(github_pr._github, 'check_auth', lambda: (True, ''))
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
    monkeypatch.setattr(github_pr._github, 'fetch_pr_head_sha', lambda pr_number: 'deadbeef')


def _run_fetch(pr_number, plan_id):
    args = argparse.Namespace(pr_number=pr_number, plan_id=plan_id)
    return github_pr.cmd_fetch_findings(args)


def _pending(plan_id):
    """The pending pr-comment findings — the exact set the barrier query returns."""
    return [
        f for f in query_findings(plan_id, finding_type='pr-comment')['findings'] if f.get('resolution') == 'pending'
    ]


def _resolve_all_pending(plan_id):
    """Simulate the triage pass resolving every fetched comment (bot handled)."""
    for f in query_findings(plan_id, finding_type='pr-comment')['findings']:
        if f.get('resolution') == 'pending':
            resolve_finding(plan_id, f['hash_id'], 'fixed')


def _self_response_comment(comment_id, anchor='c1'):
    return {
        'id': comment_id,
        'author': 'oliver',
        'thread_id': '',
        'kind': 'issue_comment',
        'body': github_pr._build_batched_response_body(
            [(anchor, 'Fixed — the None case is now guarded before the dereference.')]
        ),
        'resolved': False,
    }


review_completeness = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)
_CODERABBIT_ONLY = [_INITIAL_COMMENTS[0]]
_merge_auth = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_merge_authorization.py', '_barrier_merge_auth_cmd'
)
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_barrier_merge_auth_lifecycle')
_DOCS_ONLY_HEAD = 'd0c50n1ya1b2c3d4e5f60718293a4b5c6d7e8f90'
_REBASED_HEAD = '76c7200b6f1e2d3c4b5a69788796a5b4c3d2e1f0'
_BARRIER_GAP = 'review-barrier-gap'
_MERGE_ACTION_GAP = 'merge-action'
_MEMBER_OBSERVATIONS = {
    review_completeness.STATE_PARTICIPATED_STALE: {'stale_participation_bots': ['cuioss-review-bot']},
    review_completeness.STATE_NOT_TRIGGERED: {'not_triggered': True},
    review_completeness.STATE_DECLINED: {'declined_bots': ['cuioss-review-bot']},
    review_completeness.STATE_IN_PROGRESS: {'in_progress_bots': ['cuioss-review-bot']},
    # cuioss-review-bot's registry rate_limit_class is ``unknown``, so a bare refusal from it
    # resolves to the declared-ignorance member.
    review_completeness.STATE_REFUSED_UNKNOWN: {'refused_bots': ['cuioss-review-bot']},
    # ...and the same refusal with an observed SIZE cause resolves structurally,
    # because the cause axis dominates the class axis.
    review_completeness.STATE_REFUSED_STRUCTURAL: {
        'refused_bots': ['cuioss-review-bot'],
        'refused_causes': {'cuioss-review-bot': 'size'},
    },
}


def _parity_plan_id(member):
    """The plan id the parity case for ``member`` files its findings against."""
    return f'barrier-parity-{member.replace("_", "-")}'


PLAN_IDS += tuple(_parity_plan_id(member) for member in _MEMBER_OBSERVATIONS)
_UNPRODUCIBLE_MEMBERS = {
    review_completeness.STATE_ABSENT: (
        'the BASELINE every widened member is compared against, not a widened member itself'
    ),
    review_completeness.STATE_REFUSED_AWAITABLE: (
        'requires a refusing bot whose registry rate_limit_class is awaitable_window; '
        'the required bot in this scenario (cuioss-review-bot) declares unknown'
    ),
    review_completeness.STATE_REFUSED_HARD: (
        'requires a refusing bot whose registry rate_limit_class is hard_quota; '
        'the required bot in this scenario (cuioss-review-bot) declares unknown'
    ),
    review_completeness.STATE_UNREGISTERED_KIND: (
        'decided from the CONFIGURATION, not from an observation: it requires the '
        'required token to be absent from bot_registry.bot_kinds(), which no entry in '
        '_MEMBER_OBSERVATIONS can produce because those are predicate observations and '
        "this is a registry fact. Producing it would mean swapping the scenario's "
        'required bot for an unregistered token — and that changes the bot whose state '
        'the parity compares, so the absent baseline and the widened run would name '
        'DIFFERENT bots in unproven_bots and the projection could never be equal. The '
        'parity this sweep asserts is therefore not statable for this member here; the '
        'barrier-relevant property (it blocks exactly as absent does) is covered by its '
        'membership in _UNPROVEN_STATES, asserted in test_structural_refusal.py'
    ),
}


def test_late_comment_after_triage_surfaces_pending_finding(plan_context, monkeypatch):
    """A comment posted after triage is re-fetched as a NEW pending finding.

    The initial pass fetches and triages (resolves) the bot comments; a late
    comment then lands. The barrier's re-fetch files ONLY the genuinely-new
    comment as a fresh pending finding (the already-stored resolved comments
    dedupe on ``(bot_kind, comment_id)``), so the barrier's pending query is
    non-empty and the merge is blocked.
    """
    plan_id = 'barrier-late-comment'

    _patch_provider(monkeypatch, _INITIAL_COMMENTS)
    first = _run_fetch(202, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == len(_INITIAL_COMMENTS)

    # Triage handled every comment — the store has no pending findings left.
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    # A late comment lands; the barrier re-fetches with it now present.
    _patch_provider(monkeypatch, [*_INITIAL_COMMENTS, _LATE_COMMENT])
    second = _run_fetch(202, plan_id)
    assert second['status'] == 'success'
    # Only the genuinely-new comment is stored; the already-stored ones dedupe.
    assert second['count_stored'] == 1
    assert second['count_skipped_duplicate'] == len(_INITIAL_COMMENTS)
    assert second['producer_mismatch_hash_id'] is None

    # The barrier's pending query is now non-empty — exactly the late comment.
    pending = _pending(plan_id)
    assert len(pending) == 1
    assert 'comment_id: c-late' in (pending[0].get('detail') or '')


def test_clean_path_no_new_comments_leaves_barrier_empty(plan_context, monkeypatch):
    """A re-fetch with no new comments files zero findings — the barrier passes.

    Every comment was already stored and resolved during the automatic-review
    pass; the barrier's re-fetch dedupes all of them, adds zero dispatches, and
    the pending query stays empty so the merge proceeds.
    """
    plan_id = 'barrier-clean-path'

    _patch_provider(monkeypatch, _INITIAL_COMMENTS)
    first = _run_fetch(203, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == len(_INITIAL_COMMENTS)

    _resolve_all_pending(plan_id)

    # Barrier re-fetch: identical comments, all already stored.
    second = _run_fetch(203, plan_id)
    assert second['status'] == 'success'
    assert second['count_stored'] == 0
    assert second['count_skipped_duplicate'] == len(_INITIAL_COMMENTS)
    assert second['producer_mismatch_hash_id'] is None

    # Barrier query empty → merge proceeds.
    assert _pending(plan_id) == []


def test_self_response_after_triage_leaves_barrier_empty(plan_context, monkeypatch):
    """The loop TERMINATES: our own reply does not re-block the barrier.

    This is the end-to-end property the fix exists for. Triage resolves the bot
    comments and transmits its dispositions as one batched PR-level comment; the
    barrier then re-fetches with that comment now present on the PR. The comment
    is unresolved, is not a refusal, matches no ``ignore`` regex, and carries a
    comment_id the ``(bot_kind, comment_id)`` dedup has never seen — so before the
    self-response exclusion it was filed as a fresh PENDING finding and the
    barrier blocked forever. The pending query must now be empty.
    """
    plan_id = 'barrier-self-response-terminates'

    _patch_provider(monkeypatch, _INITIAL_COMMENTS)
    first = _run_fetch(204, plan_id)
    assert first['status'] == 'success'
    assert first['count_stored'] == len(_INITIAL_COMMENTS)

    # Triage resolves every comment and transmits its dispositions.
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    # The transmitted batched response is now a comment on the PR; the barrier
    # re-fetches with it present.
    _patch_provider(monkeypatch, [*_INITIAL_COMMENTS, _self_response_comment('self-1')])
    second = _run_fetch(204, plan_id)
    assert second['status'] == 'success'
    # Nothing new is filed: the originals dedupe, our own reply is excluded.
    assert second['count_stored'] == 0
    assert second['count_skipped_duplicate'] == len(_INITIAL_COMMENTS)
    assert second['count_skipped_self_response'] == 1
    assert second['producer_mismatch_hash_id'] is None

    # THE property: the barrier's pending query is empty → the merge proceeds.
    assert _pending(plan_id) == []


def test_self_response_loop_bound_reports_qgate_finding(plan_context, monkeypatch):
    """At the bound the guard REPORTS exhaustion — it never passes silently.

    The exclusion filter cannot be complete: a thread-bearing disposition whose
    resolve-thread failed leaves an unresolved reply carrying arbitrary
    ``resolution_detail`` text and no transmission shape at all, so that residue
    is unkeyable by construction and only a bound can terminate it. When the
    CONSECUTIVE self-responses of the current cycle reach
    ``_SELF_RESPONSE_LOOP_BOUND`` — as they do here, where nothing but our own
    replies is on the PR — the producer files a ``(self-response-loop)`` Q-Gate
    finding, which is what turns exhaustion into a reported coverage gap requiring
    an operator decision rather than a silent pass.
    """
    plan_id = 'barrier-self-response-bound'
    accumulated = [
        _self_response_comment(f'self-{i}', anchor=f'c{i}') for i in range(github_pr._SELF_RESPONSE_LOOP_BOUND)
    ]
    _patch_provider(monkeypatch, accumulated)

    result = _run_fetch(205, plan_id)
    # The fetch itself succeeded — the loop report travels as its own field.
    assert result['status'] == 'success'
    assert result['count_skipped_self_response'] == github_pr._SELF_RESPONSE_LOOP_BOUND
    assert result['self_response_loop_detected'] is True

    # The barrier is not blocked by a pr-comment finding...
    assert _pending(plan_id) == []
    # ...but the exhaustion IS filed and retrievable, so it cannot pass unnoticed.
    qgate = query_qgate_findings(plan_id, '5-execute')['findings']
    loop_findings = [f for f in qgate if f.get('title', '').startswith('(self-response-loop)')]
    assert len(loop_findings) == 1
    assert loop_findings[0]['resolution'] == 'pending'
    assert loop_findings[0]['hash_id'] == result['self_response_loop_hash_id']
