#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the cost-field write-back added to manage-tasks `update`.

TASK-14 added the only persistence path for the T-shirt cost mechanism: three
optional flags on the ``update`` subcommand — ``--cost-size`` /
``--predicted-cost-tokens`` / ``--envelope-id`` — that persist
``cost_size`` / ``predicted_cost_tokens`` / ``envelope_id`` onto the
``TASK-NNN.json`` record (the pure compute verbs ``derive-cost-size`` /
``pack-envelopes`` stay side-effect-free). This module pins the write-back:

* the round-trip — values written via ``update`` surface back via ``next``
  (and via the ``update`` result echo);
* partial writes — one field at a time, leaving the others untouched;
* idempotent re-write — writing the same values again is a no-op for the record;
* validation rejection — negative ``predicted_cost_tokens``, an out-of-band
  ``cost_size``, and a non-positive ``envelope_id`` each yield a status: error
  result without mutating the record.

Tier 2 (direct import via ``_helpers``) tests exercise the ``cmd_update`` /
``cmd_next`` round-trip with the ``plan_context`` PLAN_BASE_DIR sandbox; Tier 3
subprocess tests exercise the CLI plumbing (flag acceptance, the status: error
TOON on validation rejection, and the argparse type rejection on a
non-integer token count). The sibling ``test_tasks_cost.py`` mirrors the same
Tier-2/Tier-3 split for the pure deriver.
"""

import pytest

from conftest import get_script_path, run_script

from _helpers import (
    _next_ns,
    _update_ns,
    add_basic_task,
    cmd_next,
    cmd_update,
)

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')


# =============================================================================
# Tier 2 — write-back round-trip (cmd_update -> cmd_next / cmd_read)
# =============================================================================


def test_update_persists_all_cost_fields_surfaced_via_next(plan_context):
    """All three cost fields written via update surface back via next."""
    add_basic_task(plan_id='wb-all', title='Sized task', deliverable=1)

    update = cmd_update(
        _update_ns(
            plan_id='wb-all',
            number=1,
            cost_size='M',
            predicted_cost_tokens=60000,
            envelope_id=2,
        )
    )
    assert update['status'] == 'success'

    result = cmd_next(_next_ns(plan_id='wb-all'))

    assert result['status'] == 'success'
    assert result['next']['cost_size'] == 'M'
    assert result['next']['predicted_cost_tokens'] == 60000
    assert result['next']['envelope_id'] == 2


def test_update_echoes_persisted_cost_fields(plan_context):
    """The update result echoes the persisted cost fields."""
    add_basic_task(plan_id='wb-echo', title='Sized task', deliverable=1)

    update = cmd_update(
        _update_ns(
            plan_id='wb-echo',
            number=1,
            cost_size='L',
            predicted_cost_tokens=130000,
            envelope_id=3,
        )
    )

    assert update['status'] == 'success'
    assert update['task']['cost_size'] == 'L'
    assert update['task']['predicted_cost_tokens'] == 130000
    assert update['task']['envelope_id'] == 3


def test_update_persisted_cost_fields_survive_reload(plan_context):
    """Persisted cost fields are durable — a fresh next (re-read from disk) returns them.

    ``cmd_next`` re-parses the TASK-NNN.json from disk on each call, so a
    success TOON from a fresh ``next`` after the ``update`` write proves the
    values were persisted to the record (not merely echoed by the writer). The
    ``next`` surface is the documented read path for these fields — TASK-3/14
    deliberately scoped the cost read surface to ``next``, so the round-trip is
    asserted through ``next`` rather than ``read``.
    """
    add_basic_task(plan_id='wb-reload', title='Sized task', deliverable=1)
    cmd_update(
        _update_ns(
            plan_id='wb-reload',
            number=1,
            cost_size='XL',
            predicted_cost_tokens=260000,
            envelope_id=1,
        )
    )

    result = cmd_next(_next_ns(plan_id='wb-reload'))

    assert result['status'] == 'success'
    assert result['next']['cost_size'] == 'XL'
    assert result['next']['predicted_cost_tokens'] == 260000
    assert result['next']['envelope_id'] == 1


def test_update_accepts_zero_predicted_cost_tokens(plan_context):
    """Zero is a valid (non-negative) predicted_cost_tokens value."""
    add_basic_task(plan_id='wb-zero', title='Sized task', deliverable=1)

    update = cmd_update(_update_ns(plan_id='wb-zero', number=1, predicted_cost_tokens=0))

    assert update['status'] == 'success'
    result = cmd_next(_next_ns(plan_id='wb-zero'))
    assert result['next']['predicted_cost_tokens'] == 0


@pytest.mark.parametrize('size', ['XS', 'S', 'M', 'L', 'XL', 'XXL'])
def test_update_accepts_each_valid_cost_size(plan_context, size):
    """Every valid T-shirt size band (six-size scale) is accepted and persisted."""
    plan_id = f'wb-size-{size}'
    add_basic_task(plan_id=plan_id, title='Sized task', deliverable=1)

    update = cmd_update(_update_ns(plan_id=plan_id, number=1, cost_size=size))

    assert update['status'] == 'success'
    result = cmd_next(_next_ns(plan_id=plan_id))
    assert result['next']['cost_size'] == size


# =============================================================================
# Tier 2 — partial writes (one field at a time leaves the others untouched)
# =============================================================================


def test_update_cost_size_only_leaves_other_fields_absent(plan_context):
    """Writing only cost_size leaves predicted_cost_tokens / envelope_id null."""
    add_basic_task(plan_id='wb-part-size', title='Sized task', deliverable=1)

    cmd_update(_update_ns(plan_id='wb-part-size', number=1, cost_size='S'))

    result = cmd_next(_next_ns(plan_id='wb-part-size'))
    assert result['next']['cost_size'] == 'S'
    assert result['next']['predicted_cost_tokens'] is None
    assert result['next']['envelope_id'] is None


def test_update_tokens_only_leaves_other_fields_absent(plan_context):
    """Writing only predicted_cost_tokens leaves cost_size / envelope_id null."""
    add_basic_task(plan_id='wb-part-tok', title='Sized task', deliverable=1)

    cmd_update(_update_ns(plan_id='wb-part-tok', number=1, predicted_cost_tokens=25000))

    result = cmd_next(_next_ns(plan_id='wb-part-tok'))
    assert result['next']['predicted_cost_tokens'] == 25000
    assert result['next']['cost_size'] is None
    assert result['next']['envelope_id'] is None


def test_update_envelope_only_leaves_other_fields_absent(plan_context):
    """Writing only envelope_id leaves cost_size / predicted_cost_tokens null."""
    add_basic_task(plan_id='wb-part-env', title='Sized task', deliverable=1)

    cmd_update(_update_ns(plan_id='wb-part-env', number=1, envelope_id=4))

    result = cmd_next(_next_ns(plan_id='wb-part-env'))
    assert result['next']['envelope_id'] == 4
    assert result['next']['cost_size'] is None
    assert result['next']['predicted_cost_tokens'] is None


def test_update_second_field_preserves_first(plan_context):
    """A later single-field write does not clobber an earlier-written field."""
    add_basic_task(plan_id='wb-accum', title='Sized task', deliverable=1)

    cmd_update(_update_ns(plan_id='wb-accum', number=1, cost_size='M'))
    cmd_update(_update_ns(plan_id='wb-accum', number=1, predicted_cost_tokens=60000))

    result = cmd_next(_next_ns(plan_id='wb-accum'))
    assert result['next']['cost_size'] == 'M'
    assert result['next']['predicted_cost_tokens'] == 60000


def test_update_without_cost_flags_does_not_touch_persisted_costs(plan_context):
    """An unrelated update (title) leaves previously-persisted cost fields intact."""
    add_basic_task(plan_id='wb-untouched', title='Sized task', deliverable=1)
    cmd_update(
        _update_ns(
            plan_id='wb-untouched',
            number=1,
            cost_size='L',
            predicted_cost_tokens=130000,
            envelope_id=2,
        )
    )

    cmd_update(_update_ns(plan_id='wb-untouched', number=1, title='Renamed task'))

    result = cmd_next(_next_ns(plan_id='wb-untouched'))
    assert result['next']['task_title'] == 'Renamed task'
    assert result['next']['cost_size'] == 'L'
    assert result['next']['predicted_cost_tokens'] == 130000
    assert result['next']['envelope_id'] == 2


# =============================================================================
# Tier 2 — idempotent re-write
# =============================================================================


def test_update_idempotent_rewrite_same_values(plan_context):
    """Re-writing the identical cost values is a no-op for the record."""
    add_basic_task(plan_id='wb-idem', title='Sized task', deliverable=1)
    first = cmd_update(
        _update_ns(
            plan_id='wb-idem',
            number=1,
            cost_size='M',
            predicted_cost_tokens=60000,
            envelope_id=2,
        )
    )
    second = cmd_update(
        _update_ns(
            plan_id='wb-idem',
            number=1,
            cost_size='M',
            predicted_cost_tokens=60000,
            envelope_id=2,
        )
    )

    assert first['status'] == 'success'
    assert second['status'] == 'success'
    assert first['task']['cost_size'] == second['task']['cost_size']
    assert first['task']['predicted_cost_tokens'] == second['task']['predicted_cost_tokens']
    assert first['task']['envelope_id'] == second['task']['envelope_id']

    result = cmd_next(_next_ns(plan_id='wb-idem'))
    assert result['next']['cost_size'] == 'M'
    assert result['next']['predicted_cost_tokens'] == 60000
    assert result['next']['envelope_id'] == 2


def test_update_rewrite_overwrites_with_new_values(plan_context):
    """A second write with different values overwrites the first."""
    add_basic_task(plan_id='wb-overwrite', title='Sized task', deliverable=1)
    cmd_update(
        _update_ns(
            plan_id='wb-overwrite',
            number=1,
            cost_size='S',
            predicted_cost_tokens=25000,
            envelope_id=1,
        )
    )
    cmd_update(
        _update_ns(
            plan_id='wb-overwrite',
            number=1,
            cost_size='XL',
            predicted_cost_tokens=260000,
            envelope_id=5,
        )
    )

    result = cmd_next(_next_ns(plan_id='wb-overwrite'))
    assert result['next']['cost_size'] == 'XL'
    assert result['next']['predicted_cost_tokens'] == 260000
    assert result['next']['envelope_id'] == 5


# =============================================================================
# Tier 2 — validation rejection (status: error, record left unchanged)
# =============================================================================


def test_update_rejects_negative_predicted_cost_tokens(plan_context):
    """A negative predicted_cost_tokens yields a status: error result."""
    add_basic_task(plan_id='wb-neg-tok', title='Sized task', deliverable=1)

    update = cmd_update(_update_ns(plan_id='wb-neg-tok', number=1, predicted_cost_tokens=-1))

    assert update['status'] == 'error'
    assert 'predicted-cost-tokens' in update['message']


def test_update_rejects_invalid_cost_size(plan_context):
    """An out-of-band cost_size yields a status: error result.

    XXL is a VALID size under the six-size scale, so the rejection case uses a
    genuinely out-of-enum label (XXXL).
    """
    add_basic_task(plan_id='wb-bad-size', title='Sized task', deliverable=1)

    update = cmd_update(_update_ns(plan_id='wb-bad-size', number=1, cost_size='XXXL'))

    assert update['status'] == 'error'
    assert 'cost-size' in update['message']


def test_update_rejects_non_positive_envelope_id(plan_context):
    """A non-positive (0) envelope_id yields a status: error result."""
    add_basic_task(plan_id='wb-zero-env', title='Sized task', deliverable=1)

    update = cmd_update(_update_ns(plan_id='wb-zero-env', number=1, envelope_id=0))

    assert update['status'] == 'error'
    assert 'envelope-id' in update['message']


def test_update_rejected_negative_tokens_leaves_record_unchanged(plan_context):
    """A rejected write does not mutate the previously-persisted value."""
    add_basic_task(plan_id='wb-reject-stable', title='Sized task', deliverable=1)
    cmd_update(_update_ns(plan_id='wb-reject-stable', number=1, predicted_cost_tokens=60000))

    rejected = cmd_update(_update_ns(plan_id='wb-reject-stable', number=1, predicted_cost_tokens=-5))
    assert rejected['status'] == 'error'

    result = cmd_next(_next_ns(plan_id='wb-reject-stable'))
    assert result['next']['predicted_cost_tokens'] == 60000


# =============================================================================
# Tier 3 — CLI plumbing (subprocess via run_script)
#
# The semantic-validation rejections (invalid cost_size, negative tokens,
# non-positive envelope_id) are covered by the Tier-2 cmd_update tests above:
# cmd_update looks up the task file FIRST and only validates the cost fields on
# a found task, so a plan-less subprocess invocation would return a "not found"
# error rather than the cost-field guard. The Tier-3 tests below cover the
# layer that DOES fire before any handler — argparse type coercion (the
# `type=int` declarations on --predicted-cost-tokens / --envelope-id) — which
# rejects a non-integer value with exit 2 independent of any on-disk task.
# =============================================================================


def test_cli_update_non_integer_predicted_cost_tokens_exits_2():
    """A non-integer --predicted-cost-tokens is an argparse type rejection (exit 2)."""
    result = run_script(
        SCRIPT_PATH,
        'update',
        '--plan-id', 'wb-cli-missing',
        '--task-number', '1',
        '--predicted-cost-tokens', 'lots',
    )

    assert result.returncode == 2


def test_cli_update_non_integer_envelope_id_exits_2():
    """A non-integer --envelope-id is an argparse type rejection (exit 2)."""
    result = run_script(
        SCRIPT_PATH,
        'update',
        '--plan-id', 'wb-cli-missing',
        '--task-number', '1',
        '--envelope-id', 'two',
    )

    assert result.returncode == 2
