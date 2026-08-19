#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge-authorization subcommand of manage-status."""


from _merge_authorization_fixtures import (
    BARRIER_GAP,
    HEAD_A,
    HEAD_B,
    MERGE_ACTION_GAP,
    _check_args,
    _grant_args,
    _make_plan,
    _verdict_for,
    cmd_merge_authorization_check,
    cmd_merge_authorization_grant,
    read_status,
)

# =============================================================================
# grant — persistence and the overwrite-is-the-re-seek contract
# =============================================================================


def test_grant_persists_head_bound_record(plan_context):
    """grant writes {head, gap_class, granted_over, reason, granted_at} under the kind key."""
    plan_id = 'merge-auth-grant'
    _make_plan(plan_id)

    result = cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))

    assert result['status'] == 'success'
    assert result['kind'] == 'barrier-ask-override'
    assert result['head'] == HEAD_A
    assert result['gap_class'] == BARRIER_GAP
    assert result['granted_at']
    assert 'previous_head' not in result

    persisted = read_status(plan_id)['metadata']['merge_authorizations']['barrier-ask-override']
    assert persisted['head'] == HEAD_A
    assert persisted['gap_class'] == BARRIER_GAP
    assert set(persisted) == {'head', 'gap_class', 'granted_over', 'reason', 'granted_at'}


def test_record_round_trips_granted_over_and_reason(plan_context):
    """granted_over and reason survive persistence verbatim.

    ``granted_over`` is what the authorization was granted OVER, so a later
    reader can re-evaluate the ruling against a later delta. A lossy round-trip
    would silently destroy that comparison.
    """
    plan_id = 'merge-auth-roundtrip'
    _make_plan(plan_id)
    gap = '3 unhandled, unproven_bots=pr-agent,sourcery'
    reason = "operator: docs-only delta, bots are rate-limited until tomorrow"

    cmd_merge_authorization_grant(
        _grant_args(plan_id, 'barrier-ask-override', HEAD_A, granted_over=gap, reason=reason)
    )

    persisted = read_status(plan_id)['metadata']['merge_authorizations']['barrier-ask-override']
    assert persisted['granted_over'] == gap
    assert persisted['reason'] == reason

    checked = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A))
    assert checked['records'][0]['granted_over'] == gap
    assert checked['records'][0]['reason'] == reason


def test_regrant_at_new_head_overwrites_the_record(plan_context):
    """A re-grant replaces the record rather than accumulating a second one.

    The overwrite IS the sanctioned re-seek — which is why the verb pair carries
    no revoke verb.
    """
    plan_id = 'merge-auth-overwrite'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))

    result = cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_B))

    assert result['head'] == HEAD_B
    assert result['previous_head'] == HEAD_A

    authorizations = read_status(plan_id)['metadata']['merge_authorizations']
    assert list(authorizations) == ['barrier-ask-override']
    assert authorizations['barrier-ask-override']['head'] == HEAD_B


# =============================================================================
# check — the lapse rule (D5a) and the re-seek (D5b)
# =============================================================================


def test_check_lapses_when_head_advances(plan_context):
    """The lapse rule: an authorization granted at HEAD A does not authorize HEAD B.

    A ruling made over one tree must not be recalled to merge a different one.
    """
    plan_id = 'merge-auth-lapse'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_B))

    assert result['status'] == 'success'
    assert result['any_authorized'] is False
    assert result['lapsed_kinds'] == ['barrier-ask-override']
    assert result['authorized_kinds'] == []
    assert _verdict_for(result, 'barrier-ask-override') == 'lapsed'


def test_regrant_at_new_head_reauthorizes(plan_context):
    """The re-grant rule: a re-seek at the advanced HEAD restores authorization.

    The escape hatch is BOUND, not removed — proving the lapse rule does not
    simply delete the operator's ability to proceed.
    """
    plan_id = 'merge-auth-reseek'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))
    cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_B))

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_B))

    assert result['any_authorized'] is True
    assert result['authorized_kinds'] == ['barrier-ask-override']
    assert result['lapsed_kinds'] == []
    assert _verdict_for(result, 'barrier-ask-override') == 'valid'


def test_check_at_the_granting_head_is_valid(plan_context):
    """An authorization checked at the HEAD it was granted against is valid.

    The matched positive control for the lapse rule: without this, a check that
    returned ``lapsed`` unconditionally would satisfy the lapse test while
    re-prompting the operator on every ordinary merge.
    """
    plan_id = 'merge-auth-same-head'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(
        _grant_args(plan_id, 'pre-merge-consent', HEAD_A, gap_class=MERGE_ACTION_GAP)
    )

    result = cmd_merge_authorization_check(
        _check_args(plan_id, HEAD_A, gap_class=MERGE_ACTION_GAP)
    )

    assert result['any_authorized'] is True
    assert result['any_admissible'] is True
    assert _verdict_for(result, 'pre-merge-consent') == 'valid'


# =============================================================================
# check — fail-closed defaults
# =============================================================================


def test_empty_store_is_fail_closed(plan_context):
    """No records at all yields any_authorized: false with both lists empty.

    ``absent`` is never collapsed into ``valid``: a plan that never granted
    anything must not read as authorized.
    """
    plan_id = 'merge-auth-empty'
    _make_plan(plan_id)

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A))

    assert result['status'] == 'success'
    assert result['any_authorized'] is False
    assert result['any_admissible'] is False
    assert result['authorized_kinds'] == []
    assert result['lapsed_kinds'] == []
    assert result['admissible_kinds'] == []
    assert result['inadmissible_kinds'] == []
    assert result['records'] == []
