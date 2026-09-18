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


review_completeness = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)
_CODERABBIT_ONLY = [_INITIAL_COMMENTS[0]]


def _participation_csv(fetch_result):
    """Render ``fetch_findings``'s participation rows as the barrier's CSV argument.

    The producer emits ``[{bot_kind, evidence_kind}, ...]``; the predicate's CLI
    takes ``bot_kind:evidence_kind`` pairs. The barrier crosses exactly this seam,
    so the tests cross it too rather than hand-building an already-parsed map.
    """
    return ','.join(f'{row["bot_kind"]}:{row["evidence_kind"]}' for row in fetch_result['participated_bots'])


def _completeness(plan_id, participated_csv, required, optional, **observation):
    """Run the participation predicate as the barrier does.

    ``observation`` forwards any further observation set the barrier may supply
    (``stale_participation_bots``, ``not_triggered``, …) straight through to
    ``check_completeness``, so a scenario differs from its baseline by exactly the
    one observation under test and nothing else.
    """
    return review_completeness.check_completeness(
        plan_id,
        required_bots=required,
        optional_bots=optional,
        participated_bots=review_completeness.parse_participation(participated_csv),
        **observation,
    )


_merge_auth = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_merge_authorization.py', '_barrier_merge_auth_cmd'
)
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_barrier_merge_auth_lifecycle')
_DOCS_ONLY_HEAD = 'd0c50n1ya1b2c3d4e5f60718293a4b5c6d7e8f90'
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


_BARRIER_GAP = 'review-barrier-gap'
_MERGE_ACTION_GAP = 'merge-action'


def _grant(plan_id, kind, head, gap_class, granted_over, reason):
    return _merge_auth.cmd_merge_authorization_grant(
        argparse.Namespace(
            plan_id=plan_id,
            kind=kind,
            head=head,
            gap_class=gap_class,
            granted_over=granted_over,
            reason=reason,
        )
    )


def _authorization_check(plan_id, head):
    """Check as the barrier does — always against the gap class IT reports."""
    return _merge_auth.cmd_merge_authorization_check(
        argparse.Namespace(plan_id=plan_id, head=head, gap_class=_BARRIER_GAP)
    )


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


def test_stale_override_does_not_satisfy_barrier_after_head_advances(plan_context, monkeypatch):
    """A stale override does not satisfy the barrier once HEAD advances.

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
        gap_class=_BARRIER_GAP,
        granted_over='0 unhandled, docs-only delta, unproven_bots=cuioss-review-bot',
        reason='operator: docs-only change, proceeding without the cuioss-review-bot review',
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
        required=['cuioss-review-bot'],
        optional=['coderabbit'],
    )
    assert verdict['participation_complete'] is False
    assert verdict['unproven_bots'] == ['cuioss-review-bot']

    # THE property: the ruling made over HEAD A is not evidence at HEAD B.
    stale = _authorization_check(plan_id, _REBASED_HEAD)
    assert stale['any_authorized'] is False
    assert stale['any_admissible'] is False
    assert 'barrier-ask-override' in stale['lapsed_kinds']
    assert stale['authorized_kinds'] == []

    # The hatch is BOUND, not removed: re-seeking at the tree that will actually
    # be merged restores authorization.
    _grant(
        plan_id,
        'barrier-ask-override',
        _REBASED_HEAD,
        gap_class=_BARRIER_GAP,
        granted_over='0 unhandled, unproven_bots=cuioss-review-bot',
        reason='operator: re-asked after the rebase, accepting the gap on this tree',
    )

    reseeked = _authorization_check(plan_id, _REBASED_HEAD)
    assert reseeked['any_authorized'] is True
    assert reseeked['any_admissible'] is True
    assert reseeked['authorized_kinds'] == ['barrier-ask-override']
    assert reseeked['admissible_kinds'] == ['barrier-ask-override']
    assert reseeked['lapsed_kinds'] == []


def test_consent_over_a_different_gap_at_the_same_head_does_not_satisfy_barrier(plan_context, monkeypatch):
    """The CROSS-KIND case: same HEAD, valid authorization, still inadmissible.

    HEAD-binding alone does not make the barrier safe. On the default interactive
    path the Pre-Merge Confirmation Gate grants ``pre-merge-consent`` at the LIVE
    HEAD on every "Yes, merge", and this barrier fires immediately afterwards with
    no rebase between them — so a barrier that routed on ``any_authorized`` alone
    would find a valid record on EVERY interactive merge and skip its own
    disposition universally. A routine merge confirmation, given before the
    operator was ever shown the participation gap, would authorize past it.

    The two asserts that carry the property are deliberately adjacent: the consent
    is ``valid`` at this HEAD (so the old routing WOULD have bypassed), and it is
    NOT ``admissible`` here (so the new routing does not). Admissibility is
    per-gap, not merely per-HEAD.

    The second half is the matched positive control at the SAME HEAD, so the
    refusal cannot be passing because nothing is ever admissible: the barrier's
    own ``barrier-ask-override``, granted over the gap the barrier actually
    reported, does satisfy it.
    """
    plan_id = 'barrier-cross-kind'
    _make_plan(plan_id)

    # The required bot never reviewed this HEAD — the barrier reports the gap.
    _patch_provider(monkeypatch, _CODERABBIT_ONLY)
    result = _run_fetch(209, plan_id)
    assert result['status'] == 'success'
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    verdict = _completeness(
        plan_id,
        _participation_csv(result),
        required=['cuioss-review-bot'],
        optional=['coderabbit'],
    )
    assert verdict['participation_complete'] is False

    # The Pre-Merge Confirmation Gate's consent, granted at the very HEAD the
    # barrier is about to gate — over the MERGE ACTION, not over this gap.
    _grant(
        plan_id,
        'pre-merge-consent',
        _REBASED_HEAD,
        gap_class=_MERGE_ACTION_GAP,
        granted_over='operator confirmed merge of PR #209 at this HEAD',
        reason="operator selected 'Yes, merge' at the Pre-Merge Confirmation Gate",
    )

    checked = _authorization_check(plan_id, _REBASED_HEAD)

    # HEAD-valid — this is exactly what `any_authorized` alone would have read as
    # authorization, and why HEAD-binding on its own is not sufficient.
    assert checked['any_authorized'] is True
    assert checked['authorized_kinds'] == ['pre-merge-consent']
    # ...yet inadmissible HERE, because it was granted over a different gap.
    assert checked['any_admissible'] is False
    assert checked['admissible_kinds'] == []
    assert checked['inadmissible_kinds'] == ['pre-merge-consent']

    # Matched positive control at the SAME HEAD: the barrier's own override,
    # granted over the gap the barrier reported, IS admissible.
    _grant(
        plan_id,
        'barrier-ask-override',
        _REBASED_HEAD,
        gap_class=_BARRIER_GAP,
        granted_over='0 unhandled, unproven_bots=cuioss-review-bot',
        reason='operator: accepting the participation gap on this tree',
    )

    reseeked = _authorization_check(plan_id, _REBASED_HEAD)
    assert reseeked['any_admissible'] is True
    assert reseeked['admissible_kinds'] == ['barrier-ask-override']
    # The consent is still reported — never hidden, just not admissible here.
    assert reseeked['inadmissible_kinds'] == ['pre-merge-consent']
