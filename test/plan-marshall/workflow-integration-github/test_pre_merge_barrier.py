#!/usr/bin/env python3
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
        never covered (the plan-marshall#1067 shape), and a re-grant at the new
        HEAD restores it, so the escape hatch is BOUND rather than removed.

Per lesson 2026-07-09-14-001 the provider response is built from a real fixture
shape (mirroring ``test_github_pr.py``), so a green fixture cannot diverge from
production provider behaviour.
"""

import argparse

from conftest import load_script_module

github_pr = load_script_module('plan-marshall', 'workflow-integration-github', 'github_pr.py', 'github_pr')
_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

query_findings = _findings_core.query_findings
query_qgate_findings = _findings_core.query_qgate_findings
resolve_finding = _findings_core.resolve_finding


# Initial bot-review comment set fetched during the automatic-review pass —
# coderabbit (thread-bearing inline) + sourcery (thread_id-less review_body).
# Bodies are substantive so neither is dropped by the ``_is_obvious_noise``
# pre-filter.
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

# A late review comment that lands AFTER the automatic-review pass marked the
# step done — a distinct ``comment_id`` from a bot author, so it is genuinely new
# and must not be deduped against the already-stored comments.
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
        f
        for f in query_findings(plan_id, finding_type='pr-comment')['findings']
        if f.get('resolution') == 'pending'
    ]


def _resolve_all_pending(plan_id):
    """Simulate the triage pass resolving every fetched comment (bot handled)."""
    for f in query_findings(plan_id, finding_type='pr-comment')['findings']:
        if f.get('resolution') == 'pending':
            resolve_finding(plan_id, f['hash_id'], 'fixed')


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


# A batched disposition comment as ``post_responses`` actually posts it: a NEW
# PR-level comment authored by the repo-owner account, carrying kind
# ``issue_comment`` and a NEW comment_id each turn. The body is rendered by the
# PRODUCTION emitter rather than a hand-written literal, so a future rename of the
# heading cannot leave these barrier tests green while reopening the loop.
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
        _self_response_comment(f'self-{i}', anchor=f'c{i}')
        for i in range(github_pr._SELF_RESPONSE_LOOP_BOUND)
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


# --- Predicate 2: required-bot participation ---------------------------------
#
# The barrier's comment predicate asks whether every comment that EXISTS has been
# handled. It is structurally blind to an absence: a required bot that never
# reviewed publishes nothing, files no finding, and so contributes zero pending
# comments — identical, to a pending count, to a bot that reviewed and was
# triaged clean. The participation predicate is the complement, and these tests
# pin the distinction the merge gate depends on.

review_completeness = load_script_module(
    'plan-marshall', 'automatic-review', 'review_completeness.py', 'review_completeness'
)


# Only CodeRabbit speaks. `pr-agent` — the required bot — never publishes, which
# is the plan-marshall#1045 shape: the fix commit was reviewed by CodeRabbit and
# never by the required bot, yet nothing downstream blocked the merge.
_CODERABBIT_ONLY = [_INITIAL_COMMENTS[0]]


def _participation_csv(fetch_result):
    """Render ``fetch_findings``'s participation rows as the barrier's CSV argument.

    The producer emits ``[{bot_kind, evidence_kind}, ...]``; the predicate's CLI
    takes ``bot_kind:evidence_kind`` pairs. The barrier crosses exactly this seam,
    so the tests cross it too rather than hand-building an already-parsed map.
    """
    return ','.join(
        f'{row["bot_kind"]}:{row["evidence_kind"]}' for row in fetch_result['participated_bots']
    )


def _completeness(plan_id, participated_csv, required, optional):
    return review_completeness.check_completeness(
        plan_id,
        required_bots=required,
        optional_bots=optional,
        participated_bots=review_completeness.parse_participation(participated_csv),
    )


def test_absent_required_bot_blocks_merge_though_no_comment_is_pending(plan_context, monkeypatch):
    """A required bot that never reviewed must block the merge — plan-marshall#1045.

    The comment predicate is satisfied (every fetched comment triaged, zero
    pending), so on the pending count alone the barrier would proceed to merge.
    The participation predicate must independently refuse, because `pr-agent`
    published nothing at all and its silence is indistinguishable from a clean
    review to any count of comments.
    """
    plan_id = 'barrier-absent-required-bot'

    _patch_provider(monkeypatch, _CODERABBIT_ONLY)
    result = _run_fetch(206, plan_id)
    assert result['status'] == 'success'
    # `pr-agent` is not in the observed participation set — it never published.
    assert 'pr-agent' not in {row['bot_kind'] for row in result['participated_bots']}

    # Triage handles every comment that exists: predicate 1 is CLEAN.
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    # Predicate 2 refuses anyway — this is the whole point of the second predicate.
    verdict = _completeness(
        plan_id,
        _participation_csv(result),
        required=['pr-agent'],
        optional=['coderabbit'],
    )
    assert verdict['participation_complete'] is False
    assert verdict['unproven_bots'] == ['pr-agent']
    assert {r['bot_kind']: r['state'] for r in verdict['bot_states']}['pr-agent'] == 'absent'
    # The ceiling travels with the verdict: a satisfied quorum is never a quality claim.
    assert verdict['proves'] == 'participation_only'


def test_optional_bot_silence_does_not_block_merge(plan_context, monkeypatch):
    """Silence from an OPTIONAL bot is the configured way to accept non-participation.

    This is the counter-case that keeps the predicate from being a blanket
    "every configured bot must speak" rule: a bot on a hard quota that will not
    clear inside the plan's lifetime belongs in `optional_bots`, and moving it
    there is the sanctioned alternative to a force-done that would accept every
    bot's silence at once.
    """
    plan_id = 'barrier-optional-silence'

    _patch_provider(monkeypatch, _CODERABBIT_ONLY)
    result = _run_fetch(207, plan_id)
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    verdict = _completeness(
        plan_id,
        _participation_csv(result),
        required=['coderabbit'],
        optional=['pr-agent', 'sourcery'],
    )
    assert verdict['participation_complete'] is True
    # The silent optional bots are still REPORTED — accepted, never hidden.
    assert 'pr-agent' in verdict['unproven_bots']
    assert 'sourcery' in verdict['unproven_bots']


# --- Authorization binding: the stale-override refusal ------------------------
#
# Predicate 2 reporting `participation_complete: false` is what the barrier calls
# a REPORTED GAP. The barrier may proceed past a reported gap only on an operator
# authorization that is valid at the HEAD it is about to merge — never on a
# decision-log entry recalled from an earlier pass, which is precisely how
# plan-marshall#1067 merged five unreviewed production commits.

_merge_auth = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_merge_authorization.py', '_barrier_merge_auth_cmd'
)
_lifecycle = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_barrier_merge_auth_lifecycle'
)

#: The docs-only tree the operator actually inspected when they ruled.
_DOCS_ONLY_HEAD = 'd0c50n1ya1b2c3d4e5f60718293a4b5c6d7e8f90'
#: The post-rebase tree carrying production commits the ruling never covered.
_REBASED_HEAD = '76c7200b6f1e2d3c4b5a69788796a5b4c3d2e1f0'


def _make_plan(plan_id):
    """Create the plan status.json the merge-authorization store lives in."""
    _lifecycle.cmd_create(
        argparse.Namespace(
            plan_id=plan_id,
            title='Pre-merge barrier authorization test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
            store='plans',
            use_worktree=False,
        )
    )


def _grant(plan_id, kind, head, granted_over, reason):
    return _merge_auth.cmd_merge_authorization_grant(
        argparse.Namespace(
            plan_id=plan_id, kind=kind, head=head, granted_over=granted_over, reason=reason
        )
    )


def _authorization_check(plan_id, head):
    return _merge_auth.cmd_merge_authorization_check(
        argparse.Namespace(plan_id=plan_id, head=head)
    )


def test_stale_override_does_not_satisfy_barrier_after_head_advances(plan_context, monkeypatch):
    """The plan-marshall#1067 shape, end to end.

    An operator rules "merge anyway" over a docs-only delta at HEAD A. A rebase
    then advances the branch to HEAD B carrying production commits, and the
    required bot has NOT reviewed B — so Predicate 2 reports a gap and the
    barrier is on an authorizable blocked path. At that point the ONLY admissible
    evidence is an authorization valid at B: the ruling made over A must read as
    LAPSED, leaving the barrier with nothing to proceed on.

    The second half proves the hatch was bound rather than removed — re-seeking
    at B re-authorizes, so the operator is never locked out, only re-asked about
    a tree they have actually seen.
    """
    plan_id = 'barrier-stale-override'
    _make_plan(plan_id)

    # The operator rules over the docs-only tree, naming what they saw.
    _grant(
        plan_id,
        'barrier-ask-override',
        _DOCS_ONLY_HEAD,
        granted_over='0 unhandled, docs-only delta, unproven_bots=pr-agent',
        reason='operator: docs-only change, proceeding without the pr-agent review',
    )

    # The rebase lands production commits and the required bot has not reviewed
    # them — Predicate 2 reports the gap the barrier must not proceed past.
    _patch_provider(monkeypatch, _CODERABBIT_ONLY)
    result = _run_fetch(208, plan_id)
    assert result['status'] == 'success'
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    verdict = _completeness(
        plan_id,
        _participation_csv(result),
        required=['pr-agent'],
        optional=['coderabbit'],
    )
    assert verdict['participation_complete'] is False
    assert verdict['unproven_bots'] == ['pr-agent']

    # THE property: the ruling made over HEAD A is not evidence at HEAD B.
    stale = _authorization_check(plan_id, _REBASED_HEAD)
    assert stale['any_authorized'] is False
    assert 'barrier-ask-override' in stale['lapsed_kinds']
    assert stale['authorized_kinds'] == []

    # The hatch is BOUND, not removed: re-seeking at the tree that will actually
    # be merged restores authorization.
    _grant(
        plan_id,
        'barrier-ask-override',
        _REBASED_HEAD,
        granted_over='0 unhandled, unproven_bots=pr-agent',
        reason='operator: re-asked after the rebase, accepting the gap on this tree',
    )

    reseeked = _authorization_check(plan_id, _REBASED_HEAD)
    assert reseeked['any_authorized'] is True
    assert reseeked['authorized_kinds'] == ['barrier-ask-override']
    assert reseeked['lapsed_kinds'] == []
