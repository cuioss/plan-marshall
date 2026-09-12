#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _marshalld_scheduler (slots, round-robin fairness, idempotent attach)."""

from __future__ import annotations

import _build_server_protocol as proto
import _machine_config
import _marshalld_scheduler as scheduler_mod


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


def test_default_max_slots_agrees_with_the_shared_machine_global_default():
    """The scheduler admits against the shared default, not a local copy.

    Cap RESOLUTION is no longer this module's job — that contract lives in
    ``test_machine_config.py``. What remains a scheduler contract is that its
    constructor default is the same value the fallback queue falls back to, so
    the daemon and the in-process path cannot disagree about what
    "unconfigured" means while sharing one slot budget.

    This pins the VALUE agreement. That the default is DEFINED in only one
    place is a source-level property, checked by the deliverable's zero-hit
    sweep for the removed per-consumer constants rather than at runtime.
    """
    assert scheduler_mod.DEFAULT_MAX_SLOTS == _machine_config.DEFAULT_MAX_SLOTS
    assert scheduler_mod.Scheduler().max_slots == _machine_config.DEFAULT_MAX_SLOTS


def test_scheduler_exposes_no_config_resolver_of_its_own():
    """Cap resolution was removed from the scheduler, not merely bypassed.

    The scheduler is a pure in-memory structure with no I/O; a resolver
    reappearing here would be a second place the cap could be read from.
    """
    assert not hasattr(scheduler_mod, 'resolve_max_slots')


def test_admit_next_empty_returns_none():
    sched = scheduler_mod.Scheduler(max_slots=2)
    assert sched.admit_next() is None


# =============================================================================
# set_max_slots — re-pointing a live cap
# =============================================================================
# The cap is machine-global state an operator can change under a running daemon,
# and the daemon re-resolves it per submit. The scheduler therefore has to take a
# new cap in place: rebuilding it would discard its queues, its running set, and
# the idempotency fingerprints of jobs already in flight. These tests pin the
# in-place semantics; the daemon-level integration (that a live `config set`
# reaches this setter on the next submit) is owned by
# ``test_daemon_max_slots_resolution.py``.


def test_set_max_slots_raises_the_admission_bound():
    sched = scheduler_mod.Scheduler(max_slots=1)
    for notation in ('a:1:x', 'b:1:x', 'c:1:x'):
        sched.submit(_spec(notation), '/proj')
    assert sched.admit_next() is not None
    assert sched.admit_next() is None  # the cap of 1 is what blocks here

    sched.set_max_slots(3)

    # The previously-blocked jobs become admissible — the same call that was
    # refused above now succeeds, which is what makes the refusal above the
    # matched control for this claim rather than an unrelated assertion.
    assert sched.admit_next() is not None
    assert sched.admit_next() is not None
    assert sched.running_count == 3


def test_set_max_slots_returns_the_cap_actually_applied():
    sched = scheduler_mod.Scheduler(max_slots=2)

    # A caller reports what was applied, not what it asked for — so the return is
    # the post-clamp value. Both a passed-through value and a clamped one are
    # checked, since a setter that returned its argument unchanged would satisfy
    # the first alone.
    assert sched.set_max_slots(6) == 6
    assert sched.max_slots == 6
    assert sched.set_max_slots(0) == 1
    assert sched.max_slots == 1


def test_set_max_slots_applies_the_same_floor_as_the_constructor():
    """One clamp, reached through both doors.

    A cap of ``0`` would wedge the daemon into admitting nothing forever, so
    neither door may accept one. The pair is asserted together because a floor
    applied in two places is two chances for the doors to disagree about what the
    lowest legal cap is — and the constructor now reaches the floor by delegating
    to this setter, which is the property under test.
    """
    assert scheduler_mod.Scheduler(max_slots=0).max_slots == 1
    assert scheduler_mod.Scheduler(max_slots=-4).max_slots == 1

    sched = scheduler_mod.Scheduler(max_slots=5)
    sched.set_max_slots(0)
    assert sched.max_slots == 1
    sched.set_max_slots(-4)
    assert sched.max_slots == 1


def test_lowering_the_cap_never_evicts_a_running_job():
    """A cap that went down is a reason to admit nothing, not to kill anything.

    Killing a build an operator never asked to kill would be a far worse answer
    than waiting, so the new cap governs ADMISSION only. The running set is
    asserted intact and the admission door asserted shut in the same test,
    because either half alone is satisfiable by an implementation that got the
    other half wrong.
    """
    sched = scheduler_mod.Scheduler(max_slots=3)
    for notation in ('a:1:x', 'b:1:x', 'c:1:x'):
        sched.submit(_spec(notation), '/proj')
    first = sched.admit_next()
    second = sched.admit_next()
    assert first is not None and second is not None
    assert sched.running_count == 2

    sched.set_max_slots(1)

    # Nothing was evicted: both jobs are still running, over the new cap.
    assert sched.running_count == 2
    assert sched.max_slots == 1
    # And nothing new is admitted — available_slots floors at 0 rather than
    # going negative, so the third job simply waits.
    assert sched.available_slots() == 0
    assert sched.admit_next() is None
    assert sched.queued_count == 1

    # Once enough jobs complete to bring the running count under the new cap,
    # admission resumes on its own — no intervention, and no lost job.
    sched.complete(first.job_id)
    sched.complete(second.job_id)
    assert sched.available_slots() == 1
    assert sched.admit_next() is not None


def test_set_max_slots_preserves_queues_running_jobs_and_fingerprints():
    """Re-pointing is in place — the reason this is a setter, not a rebuild.

    A rebuilt scheduler would silently double-run every in-flight job (its
    fingerprints gone, so an identical resubmit would no longer attach) and lose
    every queued one. All three pieces of state are asserted across the
    re-point.
    """
    sched = scheduler_mod.Scheduler(max_slots=2)
    running_spec = _spec('a:1:x')
    queued_spec = _spec('b:1:x')
    running_submit = sched.submit(running_spec, '/proj')
    queued_submit = sched.submit(queued_spec, '/proj')
    admitted = sched.admit_next()
    assert admitted is not None

    sched.set_max_slots(7)

    assert sched.running_count == 1
    assert sched.queued_count == 1
    # The idempotency fingerprints survive, so an identical resubmit still
    # attaches instead of minting a second run of the same build.
    assert sched.has_job(running_spec.fingerprint)
    assert sched.has_job(queued_spec.fingerprint)
    assert sched.submit(running_spec, '/proj').job_id == running_submit.job_id
    assert sched.submit(queued_spec, '/proj').job_id == queued_submit.job_id
