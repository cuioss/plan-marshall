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
# check — the single-question contract, pinned at the CLI boundary
# =============================================================================

def test_check_cli_accepts_the_documented_form(plan_context):
    """Positive control: the documented `check --plan-id --head --gap-class` form works.

    Without this, the rejection tests below could pass for an unrelated reason
    (a broken subparser registration rejects every invocation equally).
    """
    plan_id = 'merge-auth-cli-ok'
    _make_plan(plan_id)

    result = run_script(
        _manage_status_script(),
        'merge-authorization',
        'check',
        '--plan-id',
        plan_id,
        '--head',
        HEAD_A,
        '--gap-class',
        BARRIER_GAP,
    )

    assert result.returncode == 0, result.stderr
    assert 'any_admissible' in result.stdout


def test_check_cli_rejects_a_kind_filter(plan_context):
    """`check` takes NO --kind flag, and the parser enforces it.

    A per-kind check would let one valid authorization mask a lapsed sibling, so
    the single-question contract is pinned at the argparse boundary rather than
    left to convention.
    """
    plan_id = 'merge-auth-cli-kind'
    _make_plan(plan_id)

    result = run_script(
        _manage_status_script(),
        'merge-authorization',
        'check',
        '--plan-id',
        plan_id,
        '--head',
        HEAD_A,
        '--gap-class',
        BARRIER_GAP,
        '--kind',
        'barrier-ask-override',
    )

    assert result.returncode == 2
    assert 'unrecognized arguments: --kind' in result.stderr


def test_check_cli_requires_the_gap_class(plan_context):
    """`check` without --gap-class is an argparse rejection, not a HEAD-only check.

    Making the flag REQUIRED rather than optional is what forecloses the
    fail-open fallback: an optional flag would let a caller (or a later doc edit)
    silently drop back to routing on HEAD-validity alone, which reads as
    authorized on essentially every interactive merge.
    """
    plan_id = 'merge-auth-cli-no-gap'
    _make_plan(plan_id)

    result = run_script(
        _manage_status_script(),
        'merge-authorization',
        'check',
        '--plan-id',
        plan_id,
        '--head',
        HEAD_A,
    )

    assert result.returncode == 2
    assert '--gap-class' in result.stderr


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


def test_malformed_record_is_lapsed_not_valid(plan_context):
    """A structurally-unusable record resolves to lapsed, never to valid.

    There is no catch-all branch admitting an unrecognized shape to the
    authorized set — the fail-open direction the barrier cannot tolerate.
    """
    plan_id = 'merge-auth-malformed'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['merge_authorizations'] = {'barrier-ask-override': 'granted'}
    write_status(plan_id, status)

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A))

    assert result['any_authorized'] is False
    assert result['any_admissible'] is False
    assert result['lapsed_kinds'] == ['barrier-ask-override']
    assert _verdict_for(result, 'barrier-ask-override') == 'lapsed'


def test_one_valid_authorization_does_not_mask_a_lapsed_sibling(plan_context):
    """Every record is reported, so a lapsed kind stays visible beside a valid one.

    The aggregate lists are what make the single-question contract auditable: a
    caller that only saw ``any_authorized`` would lose the lapsed sibling, which
    is exactly what a per-kind filter would cause. Admissibility does not change
    that: the valid-but-other-gap consent is reported in BOTH ``authorized_kinds``
    and ``inadmissible_kinds`` rather than filtered away, so the routing narrows
    while the report does not.
    """
    plan_id = 'merge-auth-mixed'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(
        _grant_args(plan_id, 'pre-merge-consent', HEAD_B, gap_class=MERGE_ACTION_GAP)
    )
    cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_B))

    assert result['authorized_kinds'] == ['pre-merge-consent']
    assert result['lapsed_kinds'] == ['barrier-ask-override']
    assert result['admissible_kinds'] == []
    assert result['inadmissible_kinds'] == ['pre-merge-consent']
    assert _verdict_for(result, 'barrier-ask-override') == 'lapsed'
    assert _verdict_for(result, 'pre-merge-consent') == 'valid'


# =============================================================================
# check — admissibility: the gap class, not just the HEAD
# =============================================================================


def test_valid_record_over_a_different_gap_is_not_admissible(plan_context):
    """A ruling granted over a DIFFERENT gap at the SAME HEAD does not authorize.

    This is the second half of the binding, and it is not redundant with the
    lapse rule: ``pre-merge-consent`` is granted by the Pre-Merge Confirmation
    Gate at the very HEAD the review barrier then gates, with no rebase in
    between. HEAD-binding alone therefore reads as authorization on essentially
    every interactive merge — a routine "Yes, merge" would authorize past a
    participation gap the operator was never shown.

    The record is ``valid`` (that part is honest — it IS bound to this tree) and
    simultaneously NOT ``admissible`` here. Both asserts are load-bearing: the
    first is what makes the second non-vacuous.
    """
    plan_id = 'merge-auth-cross-gap'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(
        _grant_args(plan_id, 'pre-merge-consent', HEAD_A, gap_class=MERGE_ACTION_GAP)
    )

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A, gap_class=BARRIER_GAP))

    assert result['any_authorized'] is True
    assert result['authorized_kinds'] == ['pre-merge-consent']
    assert result['any_admissible'] is False
    assert result['admissible_kinds'] == []
    assert result['inadmissible_kinds'] == ['pre-merge-consent']
    assert _record_for(result, 'pre-merge-consent')['admissible'] is False


def test_matching_gap_class_at_the_granting_head_is_admissible(plan_context):
    """The matched positive control: right HEAD AND right gap class admits.

    Without this, ``test_valid_record_over_a_different_gap_is_not_admissible``
    would be satisfied by an implementation that returned ``admissible: false``
    unconditionally — which would wedge the barrier shut rather than bind it.
    """
    plan_id = 'merge-auth-matching-gap'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(
        _grant_args(plan_id, 'barrier-ask-override', HEAD_A, gap_class=BARRIER_GAP)
    )

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A, gap_class=BARRIER_GAP))

    assert result['any_admissible'] is True
    assert result['admissible_kinds'] == ['barrier-ask-override']
    assert result['inadmissible_kinds'] == []
    assert _record_for(result, 'barrier-ask-override')['admissible'] is True


def test_matching_gap_class_at_a_superseded_head_is_not_admissible(plan_context):
    """The other half of the conjunction: right gap class, wrong HEAD, refused.

    Together with the two cases above this pins admissibility as an AND of two
    independent conditions rather than either one alone — a record can fail on
    the HEAD, on the class, or on both.
    """
    plan_id = 'merge-auth-matching-gap-stale'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(
        _grant_args(plan_id, 'barrier-ask-override', HEAD_A, gap_class=BARRIER_GAP)
    )

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_B, gap_class=BARRIER_GAP))

    assert result['any_admissible'] is False
    assert result['admissible_kinds'] == []
    assert result['lapsed_kinds'] == ['barrier-ask-override']
    assert _record_for(result, 'barrier-ask-override')['admissible'] is False
