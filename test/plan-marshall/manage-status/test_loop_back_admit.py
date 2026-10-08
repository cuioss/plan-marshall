#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``loop-back admit`` verb of manage-status.

The verb budgets finalize loop-back rounds per requesting source, so the
properties pinned here are the ones that make the budget per-source rather than
shared:

* a source is admitted round by round up to its ceiling, and each admission
  persists its own increment;
* a refusal returns the same fields as an admission and writes nothing;
* one source spending every round it holds leaves a different source at round 1;
* the retired scalar ``loop_back_iteration`` is attributed to no source;
* a store the verb cannot interpret is an error, never an empty budget.

Each test uses its own ``plan_id`` so no test reads another's status document.
"""

from argparse import Namespace
from typing import Any, cast

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_loop_back_admit_lifecycle')
_loop_back = load_script_module('plan-marshall', 'manage-status', '_cmd_loop_back.py', '_loop_back_admit_cmd')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_loop_back_admit_status_core')

cmd_create = _lifecycle.cmd_create
cmd_loop_back_admit = _loop_back.cmd_loop_back_admit
read_status = _status_core.read_status
write_status = _status_core.write_status

_SELF_REVIEW = 'default:pre-submission-self-review'
_AUTOMATIC_REVIEW = 'plan-marshall:automatic-review'
_MAX_ITERATIONS = 3


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Loop-back Admit Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _admit(plan_id: str, source: str, ceiling: int = _MAX_ITERATIONS) -> dict[str, Any]:
    result = cmd_loop_back_admit(Namespace(plan_id=plan_id, source=source, ceiling=ceiling))
    assert result is not None
    return cast(dict[str, Any], result)


def _seed_metadata(plan_id: str, **fields: object) -> None:
    """Write metadata fields straight into the status document."""
    status = read_status(plan_id)
    status.setdefault('metadata', {}).update(fields)
    write_status(plan_id, status)


def _spend_all_rounds(plan_id: str, source: str) -> None:
    for _ in range(_MAX_ITERATIONS):
        assert _admit(plan_id, source)['admitted'] is True


def test_a_source_is_admitted_for_every_round_up_to_its_ceiling(plan_context):
    """Each of the ``max_iterations`` rounds is admitted and persisted in turn."""
    plan_id = 'loop-back-admit-rounds'
    _make_plan(plan_id)

    for expected_round in range(1, _MAX_ITERATIONS + 1):
        result = _admit(plan_id, _SELF_REVIEW)

        assert result['status'] == 'success'
        assert result['admitted'] is True
        assert result['source'] == _SELF_REVIEW
        assert result['iteration'] == expected_round
        assert result['effective_ceiling'] == _MAX_ITERATIONS
        assert result['ceiling'] == _MAX_ITERATIONS
        assert result['granted'] == 0
        # The increment is persisted by the admitting call itself.
        assert read_status(plan_id)['metadata']['loop_back_budgets'][_SELF_REVIEW] == {
            'spent': expected_round,
            'granted': 0,
        }


def test_a_further_round_is_refused_and_leaves_the_store_unchanged(plan_context):
    """Past the ceiling the verb refuses, reports the same fields, and writes nothing."""
    plan_id = 'loop-back-admit-refusal'
    _make_plan(plan_id)
    _spend_all_rounds(plan_id, _SELF_REVIEW)
    before = read_status(plan_id)

    result = _admit(plan_id, _SELF_REVIEW)

    assert result['status'] == 'success'
    assert result['admitted'] is False
    assert result['source'] == _SELF_REVIEW
    # The round that was requested and not given.
    assert result['iteration'] == _MAX_ITERATIONS + 1
    assert result['effective_ceiling'] == _MAX_ITERATIONS
    assert result['ceiling'] == _MAX_ITERATIONS
    assert result['granted'] == 0
    # The whole document, its ``updated`` stamp included, is as it was.
    assert read_status(plan_id) == before


def test_one_source_spending_its_rounds_does_not_starve_another(plan_context):
    """A different source is admitted at round 1 after the first is exhausted."""
    plan_id = 'loop-back-admit-two-sources'
    _make_plan(plan_id)
    _spend_all_rounds(plan_id, _SELF_REVIEW)
    assert _admit(plan_id, _SELF_REVIEW)['admitted'] is False

    result = _admit(plan_id, _AUTOMATIC_REVIEW)

    assert result['admitted'] is True
    assert result['source'] == _AUTOMATIC_REVIEW
    assert result['iteration'] == 1
    budgets = read_status(plan_id)['metadata']['loop_back_budgets']
    assert budgets == {
        _SELF_REVIEW: {'spent': _MAX_ITERATIONS, 'granted': 0},
        _AUTOMATIC_REVIEW: {'spent': 1, 'granted': 0},
    }


def test_a_legacy_scalar_count_is_attributed_to_no_source(plan_context):
    """A status still carrying ``loop_back_iteration`` admits each source from zero."""
    plan_id = 'loop-back-admit-legacy-scalar'
    _make_plan(plan_id)
    # A scalar already at the ceiling: read as a shared count it would refuse everyone.
    _seed_metadata(plan_id, loop_back_iteration=_MAX_ITERATIONS)

    for source in (_SELF_REVIEW, _AUTOMATIC_REVIEW):
        result = _admit(plan_id, source)

        assert result['admitted'] is True
        assert result['iteration'] == 1

    metadata = read_status(plan_id)['metadata']
    assert metadata['loop_back_budgets'] == {
        _SELF_REVIEW: {'spent': 1, 'granted': 0},
        _AUTOMATIC_REVIEW: {'spent': 1, 'granted': 0},
    }
    # The scalar is neither read nor rewritten.
    assert metadata['loop_back_iteration'] == _MAX_ITERATIONS


def test_granted_rounds_raise_the_effective_ceiling(plan_context):
    """``granted`` on a source's record extends that source's ceiling."""
    plan_id = 'loop-back-admit-granted'
    _make_plan(plan_id)
    _seed_metadata(plan_id, loop_back_budgets={_SELF_REVIEW: {'spent': _MAX_ITERATIONS, 'granted': 1}})

    admitted = _admit(plan_id, _SELF_REVIEW)
    refused = _admit(plan_id, _SELF_REVIEW)

    assert admitted['admitted'] is True
    assert admitted['iteration'] == _MAX_ITERATIONS + 1
    assert admitted['effective_ceiling'] == _MAX_ITERATIONS + 1
    assert admitted['granted'] == 1
    assert refused['admitted'] is False
    assert refused['iteration'] == _MAX_ITERATIONS + 2
    # The admission keeps the granted count it found.
    assert read_status(plan_id)['metadata']['loop_back_budgets'][_SELF_REVIEW] == {
        'spent': _MAX_ITERATIONS + 1,
        'granted': 1,
    }


def test_an_uninterpretable_store_is_an_error_not_an_empty_budget(plan_context):
    """A malformed record is reported and left alone rather than read as zero spent."""
    plan_id = 'loop-back-admit-malformed'
    _make_plan(plan_id)
    _seed_metadata(plan_id, loop_back_budgets={_SELF_REVIEW: {'spent': 'three', 'granted': 0}})
    before = read_status(plan_id)

    result = _admit(plan_id, _SELF_REVIEW)

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_budget_store'
    assert result['source'] == _SELF_REVIEW
    assert 'admitted' not in result
    assert read_status(plan_id) == before


def test_a_negative_ceiling_is_rejected_before_any_write(plan_context):
    """A ceiling below zero is an invalid argument and admits nothing."""
    plan_id = 'loop-back-admit-negative-ceiling'
    _make_plan(plan_id)
    before = read_status(plan_id)

    result = _admit(plan_id, _SELF_REVIEW, ceiling=-1)

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'
    assert read_status(plan_id) == before
