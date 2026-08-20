#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge-authorization subcommand of manage-status."""


from _merge_authorization_fixtures import (
    BARRIER_GAP,
    HEAD_A,
    HEAD_B,
    _check_args,
    _grant_args,
    _make_plan,
    _manage_status_script,
    _record_for,
    _verdict_for,
    cmd_merge_authorization_check,
    cmd_merge_authorization_grant,
    read_status,
    write_status,
)

from conftest import run_script

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


# =============================================================================
# check — the single-question contract, pinned at the CLI boundary
# =============================================================================

def test_grant_cli_requires_the_gap_class(plan_context):
    """`grant` without --gap-class is an argparse rejection.

    A grant site that omitted the class would persist an unlabelled ruling. The
    parser refuses it at the boundary, so the classless record the fail-closed
    read handles can only ever arrive from a legacy or hand-edited status file.
    """
    plan_id = 'merge-auth-cli-grant-no-gap'
    _make_plan(plan_id)

    result = run_script(
        _manage_status_script(),
        'merge-authorization',
        'grant',
        '--plan-id',
        plan_id,
        '--kind',
        'barrier-ask-override',
        '--head',
        HEAD_A,
        '--granted-over',
        '2 unhandled',
        '--reason',
        'operator accepted the gap',
    )

    assert result.returncode == 2
    assert '--gap-class' in result.stderr


# =============================================================================
# grant — persistence and the overwrite-is-the-re-seek contract
# =============================================================================

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


# =============================================================================
# check — admissibility: the gap class, not just the HEAD
# =============================================================================

def test_record_without_a_gap_class_matches_no_class(plan_context):
    """A record carrying no ``gap_class`` is never admissible — no wildcard.

    A legacy or hand-edited record with the field absent must fail closed rather
    than matching every class, which is the fail-open direction: an unlabelled
    ruling would authorize past every gate at once.
    """
    plan_id = 'merge-auth-classless'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['merge_authorizations'] = {
        'barrier-ask-override': {
            'head': HEAD_A,
            'granted_over': '2 unhandled',
            'reason': 'legacy record written before the gap class existed',
            'granted_at': '2026-01-15T14:30:00Z',
        }
    }
    write_status(plan_id, status)

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A, gap_class=BARRIER_GAP))

    # Still HEAD-valid and still reported — nothing is hidden...
    assert result['any_authorized'] is True
    assert result['authorized_kinds'] == ['barrier-ask-override']
    # ...but an unlabelled ruling authorizes nothing.
    assert result['any_admissible'] is False
    assert result['inadmissible_kinds'] == ['barrier-ask-override']
    assert _record_for(result, 'barrier-ask-override')['gap_class'] is None


# =============================================================================
# grant — persistence and the overwrite-is-the-re-seek contract
# =============================================================================

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
