#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _marshalld_scheduler (slots, round-robin fairness, idempotent attach)."""

from __future__ import annotations

import sys

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _build_server_protocol as proto  # noqa: E402
import _marshalld_scheduler as scheduler_mod  # noqa: E402


def _spec(notation: str, *, plan_id: str = 'p', tree: str = '/tree') -> proto.JobSpec:
    executor = f'{tree}/.plan/execute-script.py'
    return proto.make_job_spec(['python3', executor, notation], tree, tree, plan_id)


def test_idempotent_submit_attaches():
    sched = scheduler_mod.Scheduler(max_slots=5)
    spec = _spec('a:b:c')

    first = sched.submit(spec, '/proj')
    second = sched.submit(spec, '/proj')

    assert first.attached is False
    assert second.attached is True
    assert second.job_id == first.job_id
    assert sched.queued_count == 1  # not double-enqueued


def test_distinct_submits_get_distinct_ids():
    sched = scheduler_mod.Scheduler(max_slots=5)

    a = sched.submit(_spec('a:b:c'), '/proj')
    b = sched.submit(_spec('d:e:f'), '/proj')

    assert a.job_id != b.job_id
    assert sched.queued_count == 2


def test_max_slots_bounds_admission():
    sched = scheduler_mod.Scheduler(max_slots=2)
    for notation in ('a:1:x', 'b:1:x', 'c:1:x'):
        sched.submit(_spec(notation), '/proj')

    first = sched.admit_next()
    second = sched.admit_next()
    third = sched.admit_next()

    assert first is not None and second is not None
    assert third is None  # no slot free
    assert sched.running_count == 2


def test_complete_frees_slot_and_fingerprint():
    sched = scheduler_mod.Scheduler(max_slots=1)
    spec = _spec('a:b:c')
    result = sched.submit(spec, '/proj')
    entry = sched.admit_next()
    assert entry is not None

    assert sched.has_job(spec.fingerprint)  # in flight before completion

    sched.complete(entry.job_id)

    assert sched.running_count == 0
    assert not sched.has_job(spec.fingerprint)  # fingerprint freed
    # After completion an identical resubmit is a NEW job (fingerprint freed).
    resubmit = sched.submit(spec, '/proj')
    assert resubmit.attached is False
    assert resubmit.job_id != result.job_id


def test_round_robin_fairness_across_projects():
    sched = scheduler_mod.Scheduler(max_slots=10)
    # Two jobs for A, one for B, submitted A, A, B.
    sched.submit(_spec('a:1:x', tree='/A'), '/A')
    sched.submit(_spec('a:2:x', tree='/A'), '/A')
    sched.submit(_spec('b:1:x', tree='/B'), '/B')

    first = sched.admit_next()
    second = sched.admit_next()
    third = sched.admit_next()

    assert first is not None and second is not None and third is not None
    projects = [first.project_root, second.project_root, third.project_root]
    # Round-robin: A then B then A — B is not starved behind both A jobs.
    assert projects == ['/A', '/B', '/A']


def test_available_slots_reporting():
    sched = scheduler_mod.Scheduler(max_slots=3)
    assert sched.available_slots() == 3
    sched.submit(_spec('a:b:c'), '/proj')
    sched.admit_next()
    assert sched.available_slots() == 2


def test_resolve_max_slots_defaults_and_overrides():
    assert scheduler_mod.resolve_max_slots(None) == scheduler_mod.DEFAULT_MAX_SLOTS
    assert scheduler_mod.resolve_max_slots({}) == scheduler_mod.DEFAULT_MAX_SLOTS
    assert scheduler_mod.resolve_max_slots({'build': {'queue': {'max_slots': 7}}}) == 7
    # Non-positive / non-int / bool degrade to the default.
    assert scheduler_mod.resolve_max_slots({'build': {'queue': {'max_slots': 0}}}) == scheduler_mod.DEFAULT_MAX_SLOTS
    assert scheduler_mod.resolve_max_slots({'build': {'queue': {'max_slots': True}}}) == scheduler_mod.DEFAULT_MAX_SLOTS


def test_admit_next_empty_returns_none():
    sched = scheduler_mod.Scheduler(max_slots=2)
    assert sched.admit_next() is None
