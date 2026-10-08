#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the outcome transitions mark-step-done records without ``--force``.

A retried or re-fired step changes its recorded outcome on its ordinary path,
so those writes are legal unforced: ``failed`` to any outcome, ``loop_back`` to
any outcome, ``done`` to ``failed`` and ``done`` to ``loop_back``. A pair
outside that set still returns ``conflict`` and writes nothing.

The sections, in order:

* Legal transitions without --force
* Negative control: a pair outside the table
"""

import json

import pytest
from _mark_step_done_fixtures import _args, _make_plan, cmd_mark_step_done, read_status

_PHASE = '1-init'
_STEP = 'step-a'


def _mark(plan_id: str, outcome: str, detail: str, force: bool = False):
    """Record ``outcome`` on the shared step, supplying the target a loop_back needs."""
    return cmd_mark_step_done(
        _args(
            plan_id,
            _PHASE,
            _STEP,
            outcome,
            force=force,
            display_detail=detail,
            loop_back_target='6-finalize' if outcome == 'loop_back' else None,
        )
    )


def _stored_entry(plan_id: str) -> dict:
    entry: dict = read_status(plan_id)['metadata']['phase_steps'][_PHASE][_STEP]
    return entry


# =============================================================================
# Legal transitions without --force
# =============================================================================


def test_mark_step_failed_to_done_without_force(plan_context):
    """A failed step that is retried green records `done` with no --force."""
    # Arrange
    plan_id = 'retry-failed-to-done'
    _make_plan(plan_id)
    _mark(plan_id, 'failed', 'timeout')

    # Act
    result = _mark(plan_id, 'done', 'retry green')

    # Assert
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['outcome'] == 'done'
    assert result['previous_outcome'] == 'failed'
    assert _stored_entry(plan_id) == {
        'outcome': 'done',
        'display_detail': 'retry green',
        'firing_count': 2,
        'prior_firings': [{'outcome': 'failed'}],
    }


@pytest.mark.parametrize(
    ('recorded', 'requested'),
    [
        ('loop_back', 'done'),
        ('failed', 'skipped'),
        ('failed', 'loop_back'),
        ('done', 'failed'),
        ('done', 'loop_back'),
    ],
)
def test_mark_step_legal_transition_without_force(plan_context, recorded, requested):
    """Each remaining table pair is recorded unforced and joins the firing trail."""
    # Arrange
    plan_id = f'retry-{recorded}-to-{requested}'.replace('_', '-')
    _make_plan(plan_id)
    _mark(plan_id, recorded, 'first firing')

    # Act
    result = _mark(plan_id, requested, 'second firing')

    # Assert
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['outcome'] == requested
    assert result['previous_outcome'] == recorded

    entry = _stored_entry(plan_id)
    assert entry['outcome'] == requested
    assert entry['display_detail'] == 'second firing'
    assert entry['firing_count'] == 2
    assert [firing['outcome'] for firing in entry['prior_firings']] == [recorded]


# =============================================================================
# Negative control: a pair outside the table
# =============================================================================


def test_mark_step_skipped_to_done_without_force_is_conflict(plan_context):
    """`skipped` to `done` is outside the table: conflict, and nothing is written."""
    # Arrange
    plan_id = 'retry-skipped-to-done'
    _make_plan(plan_id)
    _mark(plan_id, 'skipped', 'not applicable')
    stored_before = json.dumps(read_status(plan_id), sort_keys=True)

    # Act
    result = _mark(plan_id, 'done', 'late run')

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'conflict'
    assert result['existing_outcome'] == 'skipped'
    assert result['requested_outcome'] == 'done'
    assert json.dumps(read_status(plan_id), sort_keys=True) == stored_before
