#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-55 D4 — a grant exists only for the option the operator selected, and the
operator's CodeRabbit policy is written down where consumers read it.

Two of the deliverable's mechanisms are pinned here:

* ``merge-authorization grant`` refuses an answer that is not the override option's
  label (PLAN-LB-47 minted ``barrier-ask-override`` from the free text "try now",
  with a reason the operator never gave);
* the operator's review policy — CodeRabbit mandatory, 90-minute windows, ten of
  them, close-and-reopen on silence, never demoted to ``optional_bots`` — is present
  in ``coderabbit.md``, so a consumer reads it instead of re-deriving it.
"""

from __future__ import annotations

import argparse

import pytest

from conftest import get_skill_dir, load_script_module

merges = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_merge_authorization.py', '_lb55_merge_authorization'
)
lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb55_grant_lifecycle')

HEAD = 'a' * 40
OVERRIDE_LABEL = 'Merge anyway (record reason)'


def _grant(plan_id: str, **overrides) -> dict | None:
    lifecycle.cmd_create(
        argparse.Namespace(
            plan_id=plan_id,
            title='LB-55 Grant Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    values = {
        'plan_id': plan_id,
        'kind': 'barrier-ask-override',
        'head': HEAD,
        'gap_class': 'review-barrier-gap',
        'granted_over': '2 unhandled, unproven_bots=cuioss-review-bot',
        'reason': 'accepted the gap',
        'operator_answer': None,
        'override_label': None,
    }
    values.update(overrides)
    return merges.cmd_merge_authorization_grant(argparse.Namespace(**values))


def test_free_text_is_not_a_grant(plan_context):
    """``try now`` is not the override option, so no authorization is minted."""
    result = _grant(
        'lb55-grant-free-text',
        operator_answer='try now',
        override_label=OVERRIDE_LABEL,
    )

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'operator_answer_not_the_override_option'
    assert result['operator_answer'] == 'try now'


def test_the_override_option_is_accepted_and_recorded_verbatim(plan_context):
    """⛔ MATCHED CONTROL — the option label itself is the grant."""
    result = _grant(
        'lb55-grant-label',
        operator_answer=OVERRIDE_LABEL,
        override_label=OVERRIDE_LABEL,
    )

    assert result is not None
    assert result['status'] == 'success', f'the selected option must grant, got {result!r}'
    assert result['kind'] == 'barrier-ask-override'


def test_an_answer_without_an_option_label_refuses(plan_context):
    """An answer nothing can be compared against proves nothing."""
    result = _grant('lb55-grant-half', operator_answer='try now')

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'operator_answer_incomplete'


def test_a_grant_without_an_answer_keeps_its_legacy_shape(plan_context):
    """The check is opt-in at the call site: no answer supplied, no answer compared."""
    result = _grant('lb55-grant-plain')

    assert result is not None
    assert result['status'] == 'success'


def test_the_operator_review_policy_is_in_the_coderabbit_standard():
    """The policy is documented where consumers read it — never re-derived."""
    text = (get_skill_dir('plan-marshall', 'automatic-review') / 'standards' / 'coderabbit.md').read_text(
        encoding='utf-8'
    )

    assert '## Operator review policy' in text
    assert 'mandatory' in text.lower()
    assert '90 minutes' in text
    assert '10 windows' in text
    assert 'optional_bots' in text, 'the policy must say what it forbids: demotion of a required bot'
    assert 'Close the PR **unmerged**' in text
