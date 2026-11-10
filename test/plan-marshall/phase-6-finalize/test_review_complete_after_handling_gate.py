# SPDX-License-Identifier: FSL-1.1-ALv2
"""The merge gate accepts a done review without a review of the current head.

``pre_merge_gate`` decides the merge, and the participation question it asks is the
predicate's own — it re-runs ``review_completeness check`` over the producer's
observations rather than forming a second verdict. So the done rule reaches the
merge through that one predicate: a required bot declaring
``review_complete_after_handling`` whose qualifying review is on an earlier head
resolves ``participated``, participation is PROVEN, and no
``review-barrier-gap`` authorization is consulted at all.

This module drives the production verdict function with the production classifier,
so the case fails at the base commit (where the same observation classifies
``participated_stale`` and the gate refuses with ``merge_participation_unproven``).
"""

from __future__ import annotations

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', register=False)
rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_PLAN_ID = 'lb142-merge-gate'
_PR = 142


def _real_participation(plan_id, required_bots, stale_bots):
    """The predicate's own answer, reshaped to the verdict ``_check_participation`` returns."""

    def _check(_plan, _pr, _project_dir):
        checked = rc.check_completeness(
            plan_id,
            required_bots,
            triage_ran=True,
            stale_participation_bots=stale_bots,
            pr_number=_PR,
        )
        if checked['status'] != 'success':
            return {'status': 'error', 'error': 'predicate_unreadable', 'roster_read': True}
        return {
            'status': 'success',
            'participation_complete': checked['participation_complete'] is True,
            'roster_read': True,
            'required_bots': list(required_bots),
            'optional_bots': [],
            'unproven_bots': list(checked.get('unproven_bots') or []),
            'bot_states': list(checked.get('bot_states') or []),
            'proves': checked.get('proves'),
            'store_scope': checked.get('store_scope'),
        }

    return _check


class _AuthorizationRecorder:
    """A seam that records whether the gate reached for a merge authorization."""

    def __init__(self, verdict: dict) -> None:
        self.verdict = verdict
        self.calls: list[tuple] = []

    def __call__(self, plan_id, head):
        self.calls.append((plan_id, head))
        return dict(self.verdict)


def test_a_done_flagged_review_is_admitted_without_any_authorization(plan_context):
    """The whole condition: stale report, no pending finding, no grant, merge allowed."""
    plan_context.plan_dir_for(_PLAN_ID)
    authorization = _AuthorizationRecorder({'status': 'success', 'any_admissible': False, 'admissible_kinds': []})

    verdict = gate._participation_verdict(
        _PLAN_ID,
        _PR,
        '.',
        head='b' * 40,
        participation_check=_real_participation(_PLAN_ID, ['coderabbit'], ['coderabbit']),
        authorization_check=authorization,
    )

    assert verdict['allowed'] is True
    assert verdict['participation_complete'] is True
    assert verdict['authorization_kind'] is None
    assert authorization.calls == [], 'a proven participant must not need an authorization lookup'
    assert verdict['bot_states'] == [{'bot_kind': 'coderabbit', 'state': 'participated_but_empty'}]


def test_a_pending_finding_keeps_the_same_review_refused(plan_context):
    """MATCHED CONTROL — the same bot and observation, one pending finding: refused."""
    import _findings_core as fc

    plan_context.plan_dir_for(_PLAN_ID)
    result = fc.add_finding(
        _PLAN_ID,
        'pr-comment',
        title=f'PR #{_PR} inline comment by coderabbit',
        detail=f'pr_number: {_PR}\nkind: inline\nauthor: coderabbit\nthread_id: t\ncomment_id: c\n',
        bot_kind='coderabbit',
        kind='inline',
        author='coderabbitai',
        reviewed_commit_sha='a' * 40,
    )
    assert result['status'] == 'success', result
    authorization = _AuthorizationRecorder({'status': 'success', 'any_admissible': False, 'admissible_kinds': []})

    verdict = gate._participation_verdict(
        _PLAN_ID,
        _PR,
        '.',
        head='b' * 40,
        participation_check=_real_participation(_PLAN_ID, ['coderabbit'], ['coderabbit']),
        authorization_check=authorization,
    )

    assert verdict['allowed'] is False
    assert verdict['code'] == 'participation_unproven'
    assert authorization.calls != [], 'a known gap consults the authorization seam'


def test_an_unflagged_stale_review_is_still_refused(plan_context):
    """MATCHED CONTROL — the same fixture for a bot without the flag keeps today's refusal."""
    plan_context.plan_dir_for(_PLAN_ID)
    authorization = _AuthorizationRecorder({'status': 'success', 'any_admissible': False, 'admissible_kinds': []})

    verdict = gate._participation_verdict(
        _PLAN_ID,
        _PR,
        '.',
        head='b' * 40,
        participation_check=_real_participation(_PLAN_ID, ['sourcery'], ['sourcery']),
        authorization_check=authorization,
    )

    assert verdict['allowed'] is False
    assert verdict['unproven_bots'] == ['sourcery']
