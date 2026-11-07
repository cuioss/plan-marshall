#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for _marshalld_scheduler (slots, round-robin fairness, idempotent attach)."""

from __future__ import annotations

import asyncio
import json
import os
import time
from types import SimpleNamespace

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
    # Distinct directories, because the cap is what this test bounds: one
    # directory can never hold two jobs however many slots are free (D1).
    for index, notation in enumerate(('a:1:x', 'b:1:x', 'c:1:x')):
        sched.submit(_spec(notation, tree=f'/dir-{index}'), '/proj')

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
    #
    # The two A jobs live in DISTINCT directories (their own trees) while sharing
    # one registered project root: a project's fairness slot is not a directory,
    # and D1 never runs two jobs of ONE directory at once — so two jobs that
    # shared a directory could not both be admitted, and the rotation this test
    # pins would be unobservable rather than merely changed.
    sched.submit(_spec('a:1:x', tree='/A/worktree-1'), '/A')
    sched.submit(_spec('a:2:x', tree='/A/worktree-2'), '/A')
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
    for index, notation in enumerate(('a:1:x', 'b:1:x', 'c:1:x')):
        sched.submit(_spec(notation, tree=f'/dir-{index}'), '/proj')
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
    for index, notation in enumerate(('a:1:x', 'b:1:x', 'c:1:x')):
        sched.submit(_spec(notation, tree=f'/dir-{index}'), '/proj')
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


# =============================================================================
# One build per project directory (PLAN-LB-108 D1)
# =============================================================================
# Two builds of one worktree write the same `target/`, so the daemon admits at
# most one job per DIRECTORY at a time — the directory, never the registry
# fairness key (which is the main checkout, shared by every worktree). These
# tests drive the real Scheduler; nothing here stubs admission.


def _dir_spec(notation: str, directory: str) -> proto.JobSpec:
    """Build a spec whose own directory (``project_path``) is ``directory``."""
    return _spec(notation, tree=directory)


def test_admit_next_admits_one_job_per_directory_and_never_the_second():
    """W1's second job waits while W1's first runs; W2's job is admitted.

    The three assertions are one claim each: W1's second job is NEVER the
    second admission (the defect), W2's job is not held up behind it (no
    head-of-line blocking), and the second W1 job runs only once the first
    completes (the release is what admits it).
    """
    sched = scheduler_mod.Scheduler(max_slots=2)
    a = sched.submit(_dir_spec('a:1:module-tests', '/W1'), '/proj', directory='/W1')
    b = sched.submit(_dir_spec('b:1:integration-tests', '/W1'), '/proj', directory='/W1')
    c = sched.submit(_dir_spec('c:1:module-tests', '/W2'), '/proj', directory='/W2')

    first = sched.admit_next()
    second = sched.admit_next()

    assert first is not None and first.job_id == a.job_id
    assert second is not None and second.job_id == c.job_id, 'W1 must not run a second job while its first runs'
    assert sched.admit_next() is None, 'the two slots are spent on two directories'

    sched.complete(a.job_id)
    third = sched.admit_next()

    assert third is not None and third.job_id == b.job_id, 'B is admitted only after complete(A)'


def test_admit_next_keeps_fifo_order_within_one_directory():
    """W1's queue is served in submit order, and a blocked W1 head does not
    reorder the two W1 jobs behind each other."""
    sched = scheduler_mod.Scheduler(max_slots=2)
    a = sched.submit(_dir_spec('a:1:x', '/W1'), '/proj', directory='/W1')
    b = sched.submit(_dir_spec('b:1:x', '/W1'), '/proj', directory='/W1')
    d = sched.submit(_dir_spec('d:1:x', '/W1'), '/proj', directory='/W1')

    assert sched.admit_next().job_id == a.job_id
    sched.complete(a.job_id)
    assert sched.admit_next().job_id == b.job_id
    sched.complete(b.job_id)
    assert sched.admit_next().job_id == d.job_id


def test_a_directory_held_in_process_is_not_admitted_until_it_releases():
    """A live in-process holder keeps a daemon job for the same directory queued.

    Admitting it would spend a machine-global slot on a child that would then
    wait on the directory anyway (the lock order is directory first, then slot).
    """
    sched = scheduler_mod.Scheduler(max_slots=2)
    a = sched.submit(_dir_spec('a:1:x', '/W1'), '/proj', directory='/W1')

    assert sched.admit_next(busy_directories={'/W1'}) is None

    admitted = sched.admit_next(busy_directories=set())

    assert admitted is not None and admitted.job_id == a.job_id


def test_running_in_directory_names_the_job_the_next_submit_would_wait_on():
    """``queued_behind`` needs the id of the job running in the same directory."""
    sched = scheduler_mod.Scheduler(max_slots=2)
    a = sched.submit(_dir_spec('a:1:x', '/W1'), '/proj', directory='/W1')
    sched.submit(_dir_spec('b:1:x', '/W2'), '/proj', directory='/W2')
    sched.admit_next()

    assert sched.running_in_directory('/W1') == a.job_id
    assert sched.running_in_directory('/W2') == ''


def test_a_holder_identity_cannot_inject_a_toon_key(tmp_path, monkeypatch):
    """The daemon sanitises a foreign holder identity before reporting it.

    `waiting_on` interpolates a plan id read from the machine-global queue — text
    another checkout's build wrote. A newline would split the identity across lines
    in the TOON payload, where it is reparsed as a sibling key.
    """
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    daemon = _daemon(tmp_path)
    monkeypatch.setattr(
        daemon,
        '_held_directories',
        lambda: {'/W1': {'plan_id': 'evil\nstatus: success', 'pid': 42, 'command': 'x'}},
    )

    identity = daemon._waiting_on('/W1')

    assert '\n' not in identity
    assert 'evil' in identity  # the fact is still reported, just on one line


# -- daemon level ------------------------------------------------------------


class _StubVerifier:
    """Accept every submit and report one canonical root (the fairness key)."""


def _install_stub_verifier(monkeypatch, canonical_root: str = '/proj') -> None:
    import marshalld

    outcome = SimpleNamespace(accepted=True, record={'canonical_root': canonical_root})
    monkeypatch.setattr(marshalld, 'read_registry', lambda: {})
    monkeypatch.setattr(marshalld, 'verify_submit', lambda *_a, **_k: outcome)


def _stub_run_job(monkeypatch, gate):
    """Install a ``run_job`` that blocks until ``gate`` is set, then succeeds."""
    import marshalld

    seen: list[str] = []

    async def fake_run_job(command, project_path, **_kwargs):
        seen.append(project_path)
        await gate.wait()
        return {'status': 'success', 'exit_code': 0, 'duration_seconds': 1, 'log_file': ''}

    monkeypatch.setattr(marshalld, 'run_job', fake_run_job)
    return seen


def _daemon(tmp_path, max_slots: int = 2):
    import marshalld
    from _marshalld_journal import Journal

    return marshalld.Daemon(
        scheduler=scheduler_mod.Scheduler(max_slots=max_slots),
        journal=Journal(),
        log_dir=tmp_path / 'job-logs',
    )


def _write_directory_holders(home, holders: dict) -> None:
    """Stage the machine-global queue file's in-process-holder map."""
    path = home / 'build-queue.json'
    path.write_text(json.dumps({'directory_locks': holders}), encoding='utf-8')


def test_handle_request_keeps_a_second_job_for_one_directory_queued(tmp_path, monkeypatch):
    """B's journal status stays ``queued`` while A of the same directory runs."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    _install_stub_verifier(monkeypatch)
    gate = asyncio.Event()

    async def scenario():
        seen = _stub_run_job(monkeypatch, gate)
        daemon = _daemon(tmp_path)
        w1 = str(tmp_path / 'W1')
        a = await daemon.handle_request({'op': 'submit', 'job': _dir_spec('a:1:x', w1).to_dict()})
        b = await daemon.handle_request({'op': 'submit', 'job': _dir_spec('b:1:x', w1).to_dict()})

        await asyncio.sleep(0)  # let A's execution task start and block on the gate
        assert daemon._journal.get(a['job_id'])['status'] == 'running'
        assert daemon._journal.get(b['job_id'])['status'] == 'queued', 'B must wait for its directory'
        assert seen == [w1], 'only A ran'

        gate.set()
        for _ in range(50):
            await asyncio.sleep(0)
            if str((daemon._journal.get(b['job_id']) or {}).get('status', '')) == 'success':
                break
        assert daemon._journal.get(b['job_id'])['status'] == 'success'

    asyncio.run(scenario())


def test_handle_request_keeps_a_job_queued_while_an_in_process_holder_is_live(tmp_path, monkeypatch):
    """A live in-process holder on W1 keeps a W1 job queued; its release admits it.

    The release arrives through the daemon's next ``wait`` — the daemon has no
    timer, and a queued client is always waiting, so admission is re-evaluated
    there rather than on a poll loop the daemon does not run.
    """
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    _install_stub_verifier(monkeypatch)

    async def scenario():
        gate = asyncio.Event()
        _stub_run_job(monkeypatch, gate)
        daemon = _daemon(tmp_path)
        w1 = str(tmp_path / 'W1')
        _write_directory_holders(
            tmp_path,
            {
                str((tmp_path / 'W1').resolve()): {
                    'plan_id': 'another-lane-build',
                    'command': 'module-tests',
                    'pid': os.getpid(),
                    'acquired_at': time.time(),
                }
            },
        )

        a = await daemon.handle_request({'op': 'submit', 'job': _dir_spec('a:1:x', w1).to_dict()})

        await asyncio.sleep(0)
        assert daemon._journal.get(a['job_id'])['status'] == 'queued'

        _write_directory_holders(tmp_path, {})
        await daemon.handle_request({'op': 'wait', 'job_id': a['job_id'], 'bound': 0})

        assert daemon._journal.get(a['job_id'])['status'] == 'running'
        gate.set()
        for _ in range(50):
            await asyncio.sleep(0)
            if str((daemon._journal.get(a['job_id']) or {}).get('status', '')) == 'success':
                break
        assert daemon._journal.get(a['job_id'])['status'] == 'success'

    asyncio.run(scenario())
