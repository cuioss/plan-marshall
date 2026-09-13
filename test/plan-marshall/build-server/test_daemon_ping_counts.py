#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D1: the daemon's ping handshake carries the scheduler's in-flight / queued counts.

The reconcile reads daemon idleness from the daemon's OWN scheduler count rather
than inferring it — so the ping response must expose ``in_flight`` (running jobs)
and ``queued`` (admitted-but-not-yet-running jobs). Adding these to ping stays
backward-compatible: the client handshake reads only ``status`` and ``version``.

This suite owns the ping payload's SHAPE. Later extensions add keys to the same
response — D3 adds the build-slot cap (``max_slots`` / ``max_slots_source``) — and
every such extension has to be ADDITIVE: a new key that displaced or shadowed a
count would put the reconcile back to inferring idleness, which is the one
outcome the counts exist to prevent. The coexistence assertion below is what
makes that additivity a pinned contract rather than an accident of field order.
What the cap fields MEAN — their source partition, and the per-submit re-resolve
that keeps them current — is owned by ``test_daemon_max_slots_resolution.py``; it
is deliberately not re-asserted here.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

# PLAIN import, deliberately: the build-server suites annotate against
# ``marshalld.Daemon``, and only a plain import gives mypy the real module — the
# shared loader returns ``Any``, which turns every such annotation into an
# undefined name. The name is bound the same way in every suite, so no loaded copy
# is ever published beside the plainly-imported one.
import marshalld
import pytest
from _build_server_protocol import JobSpec
from _marshalld_journal import Journal
from _marshalld_scheduler import Scheduler


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return tmp_path


def _stage_machine_cap(home: Path, value: int) -> None:
    """Stage ``value`` as the machine-global build-slot cap under ``home``.

    The cap the daemon REPORTS comes from its own resolution of the
    machine-global ``machine-config.json``, so a test that asserts on the
    reported cap has to stage it here — sizing the :class:`Scheduler` stages the
    admission cap and nothing else. The cap's semantics (the source partition,
    the per-submit re-resolve) stay owned by
    ``test_daemon_max_slots_resolution.py``; this helper exists only to give the
    shape assertion below a cap value it can tell apart from the counts.
    """
    path = home / 'marshalld' / 'machine-config.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'version': 1, 'build': {'queue': {'max_slots': value}}}), encoding='utf-8')


def _spec(fingerprint: str) -> JobSpec:
    return JobSpec(
        command=['python3', 'x'],
        exec_path='/t',
        project_path='/t',
        plan_id='p',
        fingerprint=fingerprint,
    )


def test_ping_reports_zero_counts_on_an_idle_daemon(home, tmp_path):
    daemon = marshalld.Daemon(
        scheduler=Scheduler(max_slots=2),
        journal=Journal(),
        log_dir=tmp_path / 'job-logs',
    )

    response = asyncio.run(daemon.handle_request({'op': 'ping'}))

    assert response['status'] == 'ok'
    assert response['version'] == marshalld.VERSION
    assert response['in_flight'] == 0
    assert response['queued'] == 0


def test_ping_reflects_running_and_queued_jobs(home, tmp_path):
    # max_slots=1: admit one job (running=1), leave two queued.
    scheduler = Scheduler(max_slots=1)
    scheduler.submit(_spec('FP-A'), 'root')
    scheduler.submit(_spec('FP-B'), 'root')
    scheduler.submit(_spec('FP-C'), 'root')
    admitted = scheduler.admit_next()
    assert admitted is not None  # one slot filled → running_count == 1
    daemon = marshalld.Daemon(scheduler=scheduler, journal=Journal(), log_dir=tmp_path / 'job-logs')

    response = asyncio.run(daemon.handle_request({'op': 'ping'}))

    assert response['in_flight'] == 1
    assert response['queued'] == 2


def test_ping_carries_the_cap_fields_without_displacing_the_counts(home, tmp_path):
    # The additivity contract. Once the cap fields joined this payload, the two
    # counts must still be reported AND must still carry their own values — a new
    # small integer sitting beside two existing small integers is exactly the
    # shape in which a key swap goes unnoticed.
    #
    # The three numbers are therefore deliberately pairwise DISTINCT (cap 4,
    # running 1, queued 5): with a cap of 1 the cap and the in-flight count would
    # coincide, and an implementation that wrote a count into the cap key would
    # satisfy every assertion below. 5 is doubly unavailable as the cap here — it
    # is this test's queued count AND it is ``DEFAULT_MAX_SLOTS``, so a cap of 5
    # would both collide with a count and be reachable by pure degradation.
    #
    # The cap is therefore staged in the MACHINE-GLOBAL config, which is where the
    # daemon resolves the value it reports. Sizing only the ``Scheduler`` does not
    # stage it at all: ``ping`` reports the daemon's OWN resolution, never the
    # scheduler's constructor argument — deliberately so, since a cap sourced from
    # the scheduler could not distinguish a configured cap from a degraded one.
    # Left unstaged, the constructor's own resolution reaches the default, and the
    # reported cap lands exactly on the queued count's value.
    _stage_machine_cap(home, 4)
    scheduler = Scheduler(max_slots=4)
    for index in range(6):
        scheduler.submit(_spec(f'FP-{index}'), 'root')
    assert scheduler.admit_next() is not None  # exactly one slot filled
    daemon = marshalld.Daemon(scheduler=scheduler, journal=Journal(), log_dir=tmp_path / 'job-logs')

    response = asyncio.run(daemon.handle_request({'op': 'ping'}))

    # The pre-existing keys, unchanged.
    assert response['status'] == 'ok'
    assert response['version'] == marshalld.VERSION
    assert response['in_flight'] == 1
    assert response['queued'] == 5
    # The added keys, present alongside them and holding the cap — not a count.
    assert response['max_slots'] == 4
    assert response['max_slots_source']
