#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge-authorization subcommand of manage-status.

The verb pair binds every merge-gate authorization to TWO things: the HEAD it was
granted against, and the gap class it was granted over. The cases below pin the
properties the pre-merge barrier relies on:

- (a) an authorization LAPSES when HEAD advances past the tree it was granted
  over — the plan-marshall#1067 shape;
- (b) a re-grant at the new HEAD re-authorizes, so the escape hatch is BOUND
  rather than removed;
- (c) a ruling granted over a DIFFERENT gap at the SAME HEAD is ``valid`` but NOT
  ``admissible``, so HEAD-binding alone can never be read as authorization —
  several kinds (``pre-merge-consent`` above all) are granted at sites that run
  before a gate, at the same HEAD, over a different gap;
- the empty store is FAIL-CLOSED (``absent`` is never collapsed into ``valid``);
- admissibility narrows the ROUTING, never the REPORT — an inadmissible record is
  still reported, never filtered away;
- ``check`` accepts no ``--kind`` filter, so one valid authorization can never
  mask a lapsed sibling.
"""

from argparse import Namespace

from conftest import get_script_path, load_script_module, run_script

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_merge_auth_lifecycle')
_merge_auth = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_merge_authorization.py', '_merge_auth_cmd'
)
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_merge_auth_core')

cmd_create = _lifecycle.cmd_create
cmd_merge_authorization_grant = _merge_auth.cmd_merge_authorization_grant
cmd_merge_authorization_check = _merge_auth.cmd_merge_authorization_check
read_status = _status_core.read_status
write_status = _status_core.write_status

HEAD_A = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'
HEAD_B = '76c7200b6f1e2d3c4b5a69788796a5b4c3d2e1f0'

#: The gap class the pre-merge review barrier reports and checks for.
BARRIER_GAP = 'review-barrier-gap'
#: A DIFFERENT gap class, granted by a gate that runs earlier at the same HEAD.
MERGE_ACTION_GAP = 'merge-action'


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Merge Authorization Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
            store='plans',
            use_worktree=False,
        )
    )


def _grant_args(
    plan_id: str,
    kind: str,
    head: str,
    gap_class: str = BARRIER_GAP,
    granted_over: str = '2 unhandled, unproven_bots=pr-agent',
    reason: str = 'operator accepted the gap',
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        kind=kind,
        head=head,
        gap_class=gap_class,
        granted_over=granted_over,
        reason=reason,
    )


def _check_args(plan_id: str, head: str, gap_class: str = BARRIER_GAP) -> Namespace:
    return Namespace(plan_id=plan_id, head=head, gap_class=gap_class)


def _record_for(result: dict, kind: str) -> dict | None:
    """Return the per-record entry for ``kind``, or None when absent."""
    records: list[dict] = result['records']
    for record in records:
        if record['kind'] == kind:
            return record
    return None


def _verdict_for(result: dict, kind: str) -> str | None:
    """Return the per-record verdict for ``kind``, or None when absent."""
    record = _record_for(result, kind)
    return None if record is None else str(record['verdict'])


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
    """D5(a): an authorization granted at HEAD A does not authorize HEAD B.

    This is the plan-marshall#1067 shape: a ruling made over one tree must not
    be recalled to merge a different one.
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
    """D5(b): the re-seek at the advanced HEAD restores authorization.

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

    The negative control for the lapse rule: without this, a check that returned
    ``lapsed`` unconditionally would satisfy the lapse test while re-prompting
    the operator on every ordinary merge.
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
# check — the single-question contract, pinned at the CLI boundary
# =============================================================================


def _manage_status_script():
    return get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


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
