#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge-authorization subcommand of manage-status.

The verb pair binds every merge-gate authorization to the HEAD it was granted
against. The cases below pin the four properties the pre-merge barrier relies
on:

- (a) an authorization LAPSES when HEAD advances past the tree it was granted
  over — the plan-marshall#1067 shape;
- (b) a re-grant at the new HEAD re-authorizes, so the escape hatch is BOUND
  rather than removed;
- the empty store is FAIL-CLOSED (``absent`` is never collapsed into ``valid``);
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
    granted_over: str = '2 unhandled, unproven_bots=pr-agent',
    reason: str = 'operator accepted the gap',
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        kind=kind,
        head=head,
        granted_over=granted_over,
        reason=reason,
    )


def _check_args(plan_id: str, head: str) -> Namespace:
    return Namespace(plan_id=plan_id, head=head)


def _verdict_for(result: dict, kind: str) -> str | None:
    """Return the per-record verdict for ``kind``, or None when absent."""
    for record in result['records']:
        if record['kind'] == kind:
            return str(record['verdict'])
    return None


# =============================================================================
# grant — persistence and the overwrite-is-the-re-seek contract
# =============================================================================


def test_grant_persists_head_bound_record(plan_context):
    """grant writes {head, granted_over, reason, granted_at} under the kind key."""
    plan_id = 'merge-auth-grant'
    _make_plan(plan_id)

    result = cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))

    assert result['status'] == 'success'
    assert result['kind'] == 'barrier-ask-override'
    assert result['head'] == HEAD_A
    assert result['granted_at']
    assert 'previous_head' not in result

    persisted = read_status(plan_id)['metadata']['merge_authorizations']['barrier-ask-override']
    assert persisted['head'] == HEAD_A
    assert set(persisted) == {'head', 'granted_over', 'reason', 'granted_at'}


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
    cmd_merge_authorization_grant(_grant_args(plan_id, 'pre-merge-consent', HEAD_A))

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_A))

    assert result['any_authorized'] is True
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
    assert result['authorized_kinds'] == []
    assert result['lapsed_kinds'] == []
    assert result['records'] == []
    assert all(record['verdict'] != 'valid' for record in result['records'])


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
    assert result['lapsed_kinds'] == ['barrier-ask-override']
    assert _verdict_for(result, 'barrier-ask-override') == 'lapsed'


def test_one_valid_authorization_does_not_mask_a_lapsed_sibling(plan_context):
    """Every record is reported, so a lapsed kind stays visible beside a valid one.

    The aggregate lists are what make the single-question contract auditable: a
    caller that only saw ``any_authorized`` would lose the lapsed sibling, which
    is exactly what a per-kind filter would cause.
    """
    plan_id = 'merge-auth-mixed'
    _make_plan(plan_id)
    cmd_merge_authorization_grant(_grant_args(plan_id, 'pre-merge-consent', HEAD_B))
    cmd_merge_authorization_grant(_grant_args(plan_id, 'barrier-ask-override', HEAD_A))

    result = cmd_merge_authorization_check(_check_args(plan_id, HEAD_B))

    assert result['authorized_kinds'] == ['pre-merge-consent']
    assert result['lapsed_kinds'] == ['barrier-ask-override']
    assert _verdict_for(result, 'barrier-ask-override') == 'lapsed'
    assert _verdict_for(result, 'pre-merge-consent') == 'valid'


# =============================================================================
# check — the single-question contract, pinned at the CLI boundary
# =============================================================================


def _manage_status_script():
    return get_script_path('plan-marshall', 'manage-status', 'manage-status.py')


def test_check_cli_accepts_the_documented_form(plan_context):
    """Positive control: the documented `check --plan-id --head` form is accepted.

    Without this, the rejection test below could pass for an unrelated reason
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
    )

    assert result.returncode == 0, result.stderr
    assert 'any_authorized' in result.stdout


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
        '--kind',
        'barrier-ask-override',
    )

    assert result.returncode == 2
    assert 'unrecognized arguments: --kind' in result.stderr
