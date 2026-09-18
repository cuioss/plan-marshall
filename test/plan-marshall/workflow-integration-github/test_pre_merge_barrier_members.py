# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fixture-accurate provider tests for barrier member coverage.

The barrier re-runs the ``github_pr fetch_findings`` producer immediately before
merge/enqueue and then queries pending ``pr-comment`` findings; any pending
finding blocks the merge. These tests exercise the member-coverage producer
properties end-to-end against the REAL findings store (isolated via the autouse
``plan_context`` PLAN_BASE_DIR sandbox), monkeypatching only the GitHub provider
surface (``check_auth``, ``fetch_pr_comments_data``, ``fetch_pr_head_sha``):

    - absent-required-bot blocks the merge though no comment is pending.
    - optional-bot silence does not block the merge.
    - the swept members cover the taxonomy's blocking set, including the
      structural member, with an explicit reason for every unproducible one.
    - widened-member parity — the two taxonomy members that refine ``absent``
      (``participated_stale`` and ``not_triggered``) gate the merge EXACTLY as
      ``absent`` does, compared against the ``absent`` verdict for the SAME
      scenario with a matched ``participated`` negative control.

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


def _state_of(verdict, bot):
    """Return the single taxonomy member ``verdict`` assigned to ``bot``."""
    return {row['bot_kind']: row['state'] for row in verdict['bot_states']}[bot]


def _barrier_projection(verdict, pending):
    """Project a verdict onto the fields the barrier's merge decision rests on.

    Deliberately EXCLUDES ``bot_states``: its ``state`` differs by construction,
    since naming the member is the entire point of the widened taxonomy, so
    including it would compare the one field that MUST differ and could never
    assert parity. The exclusion is safe precisely because the caller pins the
    member separately — the projection asserts the verdicts agree, the member
    assertions assert the scenarios genuinely differed.
    """
    return {
        'participation_complete': verdict['participation_complete'],
        'unproven_bots': verdict['unproven_bots'],
        'pending_bots': verdict['pending_bots'],
        'proves': verdict['proves'],
        # Predicate 1 ∧ Predicate 2, composed as the barrier composes them: any
        # pending comment blocks, and an unproven required bot blocks independently.
        'merge_allowed': verdict['participation_complete'] and not pending,
    }


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


def test_absent_required_bot_blocks_merge_though_no_comment_is_pending(plan_context, monkeypatch):
    """A required bot that never reviewed blocks the merge.

    The comment predicate is satisfied (every fetched comment triaged, zero
    pending), so on the pending count alone the barrier would proceed to merge.
    The participation predicate must independently refuse, because `cuioss-review-bot`
    published nothing at all and its silence is indistinguishable from a clean
    review to any count of comments.
    """
    plan_id = 'barrier-absent-required-bot'

    _patch_provider(monkeypatch, _CODERABBIT_ONLY)
    result = _run_fetch(206, plan_id)
    assert result['status'] == 'success'
    # `cuioss-review-bot` is not in the observed participation set — it never published.
    assert 'cuioss-review-bot' not in {row['bot_kind'] for row in result['participated_bots']}

    # Triage handles every comment that exists: predicate 1 is CLEAN.
    _resolve_all_pending(plan_id)
    assert _pending(plan_id) == []

    # Predicate 2 refuses anyway — this is the whole point of the second predicate.
    verdict = _completeness(
        plan_id,
        _participation_csv(result),
        required=['cuioss-review-bot'],
        optional=['coderabbit'],
    )
    assert verdict['participation_complete'] is False
    assert verdict['unproven_bots'] == ['cuioss-review-bot']
    assert {r['bot_kind']: r['state'] for r in verdict['bot_states']}['cuioss-review-bot'] == 'absent'
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
        optional=['cuioss-review-bot', 'sourcery'],
    )
    assert verdict['participation_complete'] is True
    # The silent optional bots are still REPORTED — accepted, never hidden.
    assert 'cuioss-review-bot' in verdict['unproven_bots']
    assert 'sourcery' in verdict['unproven_bots']


def test_the_swept_members_cover_the_taxonomys_blocking_set():
    """⛔ Totality: every blocking member is swept, or excluded WITH a reason.

    This is the assertion that makes the sweep above self-maintaining. The
    population is the classifier's own ``_UNPROVEN_STATES`` — the states that leave
    a required bot's participation unproven — so a member added to the taxonomy
    lands in neither the observation map nor the unproducible set and fails HERE,
    naming itself, instead of silently going unswept.

    Asserted non-empty first: an empty blocking set would make the equality below
    compare two empty sets and pass while sweeping nothing.
    """
    blocking = set(review_completeness._UNPROVEN_STATES)
    assert blocking, 'the taxonomy declares no blocking member; the sweep would be vacuous'
    assert _MEMBER_OBSERVATIONS, 'no member is swept; the parametrisation would be empty'

    covered = set(_MEMBER_OBSERVATIONS)
    excluded = set(_UNPRODUCIBLE_MEMBERS)

    assert not (covered & excluded), f'these members are both swept and excluded: {sorted(covered & excluded)}'
    assert covered | excluded == blocking, (
        'the swept members no longer partition the taxonomy blocking set.\n'
        f'  blocking but neither swept nor excluded: {sorted(blocking - covered - excluded)}\n'
        f'  swept or excluded but not blocking:      {sorted((covered | excluded) - blocking)}\n'
        'Add an observation to _MEMBER_OBSERVATIONS, or an explicit reason to '
        '_UNPRODUCIBLE_MEMBERS.'
    )


def test_the_structural_member_is_actually_swept():
    """The member the previous hand-list omitted is in the swept set, by name.

    A totality assertion alone would also pass with ``refused_structural`` sitting
    in the unproducible set, which is precisely how the omission would survive its
    own fix.
    """
    assert review_completeness.STATE_REFUSED_STRUCTURAL in _MEMBER_OBSERVATIONS
    assert review_completeness.STATE_REFUSED_STRUCTURAL not in _UNPRODUCIBLE_MEMBERS


@pytest.mark.parametrize(
    ('member', 'observation'),
    [pytest.param(member, observation, id=member) for member, observation in sorted(_MEMBER_OBSERVATIONS.items())],
)
def test_widened_member_gates_byte_identically_to_absent(member, observation, plan_context, monkeypatch):
    """A widened member's merge verdict equals ``absent``'s, and the check can fail.

    One scenario is built once — CodeRabbit reviewed, the required ``cuioss-review-bot`` did
    not, triage cleared every comment that exists — so Predicate 1 is clean and the
    merge decision rests entirely on Predicate 2. The predicate is then run against
    that same store three ways: with no further observation (``absent``), with the
    widened member's observation, and with ``cuioss-review-bot`` proven as a participant.

    Three assertions carry the property, and each answers a different way the test
    could pass while proving nothing:

    * the member assertions prove the observation LANDED. Without them the parity
      would hold just as well when the observation was ignored and both runs
      classified ``cuioss-review-bot`` ``absent`` — an equality that passes for the wrong
      reason, which is exactly how a mis-keyed observation set would slip through.
    * the projection equality is the property itself: no merge verdict moves.
    * the ``participated`` control proves the comparison CAN fail, so the equality
      is a property of the widened members rather than of a projection too coarse
      to distinguish any two verdicts at all.
    """
    plan_id = _parity_plan_id(member)

    _patch_provider(monkeypatch, _CODERABBIT_ONLY)
    result = _run_fetch(210, plan_id)
    assert result['status'] == 'success'
    _resolve_all_pending(plan_id)
    pending = _pending(plan_id)
    assert pending == []

    participated_csv = _participation_csv(result)
    required = ['cuioss-review-bot']
    optional = ['coderabbit']

    absent_verdict = _completeness(plan_id, participated_csv, required, optional)
    widened_verdict = _completeness(plan_id, participated_csv, required, optional, **observation)

    # The scenarios genuinely differ upstream of the projection.
    assert _state_of(absent_verdict, 'cuioss-review-bot') == review_completeness.STATE_ABSENT
    assert _state_of(widened_verdict, 'cuioss-review-bot') == member

    # THE property: the barrier cannot tell the two apart.
    assert _barrier_projection(widened_verdict, pending) == _barrier_projection(absent_verdict, pending)

    # Matched negative control, same store and same required set: a proven
    # participant's verdict MUST differ. The evidence kind comes from the registry
    # rather than a literal, so the control cannot rot into an inadmissible pair
    # that is silently dropped — which would make it pass by failing to prove
    # participation at all.
    evidence_kind = review_completeness.bot_registry.participation_evidence('cuioss-review-bot')[0]
    participated_verdict = _completeness(
        plan_id, f'{participated_csv},cuioss-review-bot:{evidence_kind}', required, optional
    )

    assert _state_of(participated_verdict, 'cuioss-review-bot') != review_completeness.STATE_ABSENT
    assert _barrier_projection(participated_verdict, pending) != _barrier_projection(absent_verdict, pending)
