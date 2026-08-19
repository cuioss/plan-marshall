#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge-authorization subcommand of manage-status.

The verb pair binds every merge-gate authorization to TWO things: the HEAD it was
granted against, and the gap class it was granted over. The cases below pin the
properties the pre-merge barrier relies on:

- (a) an authorization LAPSES when HEAD advances past the tree it was granted
  over;
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

from conftest import get_script_path, load_script_module

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
# check — the single-question contract, pinned at the CLI boundary
# =============================================================================


def _manage_status_script():
    return get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
