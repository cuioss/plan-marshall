#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pre-merge gate's refusal category.

``branch-cleanup`` tells an invocation refusal (the call was malformed, the
findings store was never read) from a store-verdict refusal by ONE field,
``refusal_category: invocation``, instead of by enumerating error codes. That
only works when the field is total over one side and absent from the other:

* every invocation-refusal path carries it, whatever its ``error`` code;
* no store-verdict refusal carries it — not even one whose verdict source
  supplied the field — and neither does a dispatched payload.
"""

from typing import Any

import pytest

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', 'pre_merge_gate')

# The route-parametrized tests bind gate.ROUTES; an empty route set would turn
# every case into a silent skip, so pin it non-empty at collection time.
assert len(gate.ROUTES) >= 1, 'pre_merge_gate.ROUTES is empty; the route-parametrized tests would vanish'

_PLAN_ID = 'pre-merge-gate-category-plan'
_CLEAN_VERDICT = {'status': 'success', 'plan_id': _PLAN_ID, 'phase': '6-finalize', 'blocking_count': 0}


def _merge(route: str, verdict: dict[str, Any], **flags: Any) -> tuple[dict[str, Any], list[str], list[list[str]]]:
    checks: list[str] = []
    runs: list[list[str]] = []

    def findings_check(plan_id: str) -> dict[str, Any]:
        checks.append(plan_id)
        return dict(verdict)

    def merge_runner(ci_args: list[str]) -> dict[str, Any]:
        runs.append(list(ci_args))
        return {'status': 'success', 'merged': True}

    result = gate.merge(
        _PLAN_ID,
        route=route,
        pr_number=42,
        project_dir='/abs/worktree',
        findings_check=findings_check,
        merge_runner=merge_runner,
        **flags,
    )
    return result, checks, runs


def test_category_constants_are_exported() -> None:
    assert gate.REFUSAL_CATEGORY_FIELD == 'refusal_category'
    assert gate.INVOCATION_REFUSAL == 'invocation'
    assert {'REFUSAL_CATEGORY_FIELD', 'INVOCATION_REFUSAL'} <= set(gate.__all__)


_INVOCATION_REFUSALS = [
    pytest.param('not-a-route', {}, 'unknown_route', id='unknown-route'),
    pytest.param('safe-merge', {}, 'strategy_required', id='strategy-required'),
    pytest.param('merge-queue', {'strategy': 'squash'}, 'flag_not_applicable_to_route', id='mq-strategy'),
    pytest.param('merge-queue', {'delete_branch': True}, 'flag_not_applicable_to_route', id='mq-delete-branch'),
    pytest.param(
        'merge-queue', {'admin_merge_on_stuck_state': True}, 'flag_not_applicable_to_route', id='mq-admin-merge'
    ),
]


@pytest.mark.parametrize(('route', 'flags', 'error'), _INVOCATION_REFUSALS)
def test_every_invocation_refusal_carries_the_invocation_category(
    route: str, flags: dict[str, Any], error: str
) -> None:
    result, checks, runs = _merge(route, _CLEAN_VERDICT, **flags)

    assert result['error'] == error, result
    assert result[gate.REFUSAL_CATEGORY_FIELD] == gate.INVOCATION_REFUSAL, result
    assert result['dispatched'] is False, result
    # Non-vacuity: the refusal really fired before the store was read.
    assert checks == [], 'an invocation refusal read the findings store'
    assert runs == []


_STORE_VERDICTS = [
    pytest.param(
        {'status': 'error', 'error': 'blocking_findings_present', 'blocking_count': 1, 'per_type': {'x': 1}},
        'blocking_findings_present',
        id='blocking',
    ),
    pytest.param({'status': 'error', 'error': 'query_failed'}, 'query_failed', id='query-failed'),
    pytest.param({'status': 'success', 'plan_id': _PLAN_ID}, 'findings_verdict_unrecognised', id='unrecognised'),
    pytest.param({'status': 'error', 'error': 'some_future_refusal'}, 'some_future_refusal', id='pass-through'),
    pytest.param(
        {'status': 'error', 'error': 'query_failed', 'refusal_category': 'invocation'},
        'query_failed',
        id='source-supplied-category-is-dropped',
    ),
]


@pytest.mark.parametrize('route', gate.ROUTES)
@pytest.mark.parametrize(('verdict', 'error'), _STORE_VERDICTS)
def test_store_verdict_refusals_never_carry_the_category(route: str, verdict: dict[str, Any], error: str) -> None:
    flags = {'strategy': 'squash'} if route == 'safe-merge' else {}

    result, checks, runs = _merge(route, verdict, **flags)

    assert result['error'] == error, result
    assert gate.REFUSAL_CATEGORY_FIELD not in result, result
    assert result['dispatched'] is False, result
    # Non-vacuity: these refusals come from the store, which was read.
    assert checks == [_PLAN_ID]
    assert runs == []


@pytest.mark.parametrize('route', gate.ROUTES)
def test_dispatched_payload_never_carries_the_category(route: str) -> None:
    flags = {'strategy': 'squash'} if route == 'safe-merge' else {}

    result, _checks, runs = _merge(route, _CLEAN_VERDICT, **flags)

    assert result['dispatched'] is True, result
    assert len(runs) == 1
    assert gate.REFUSAL_CATEGORY_FIELD not in result, result
