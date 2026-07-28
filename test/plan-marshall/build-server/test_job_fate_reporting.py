#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Behavioural coverage for the daemon's job-fate reporting.

The operator log must answer "what happened to THIS job?". Before this feature a
``submit`` row carried ``outcome`` = the *response* status, which is always
``queued`` — so a job that completed and a job that was abandoned rendered
identically, forever. These tests pin the behaviour that closes that gap.

Four groups:

1. **Discrimination** — a completed job and an abandoned job, driven through the
   REAL terminalization seams (``Daemon._execute`` after ``journal.record_result``
   and ``Daemon.serve`` over ``journal.replay_on_restart``), render differently in
   the operator ``logs`` view. Those seams also emit exactly ONE fate record per
   terminalization: an already-terminalized job is never admitted — and so never
   re-executed — a second time.
2. **Unknown fate** — a fate the daemon cannot substantiate renders ``unknown``,
   never a terminal value and never ``queued``; covered over the
   died-without-restart path and the GC'd-journal-entry path.
3. **Secrets discipline** — no record produced by the fate write path carries the
   raw command argv, the interpreter path, or any exec/project path beyond the
   canonical ``project_root``; the ``_FORBIDDEN_EXTRA_KEYS`` backstop still raises.
4. **Best-effort writes** — a disk or attribution failure on a fate-bearing write
   is swallowed and aborts neither request handling nor daemon startup.

The machine-global home is isolated via ``PLAN_MARSHALL_HOME`` under ``tmp_path``
exactly as the sibling suites do. The daemon seams are driven synchronously and
``run_job`` is stubbed, mirroring the ``_daemon_submit`` idiom documented in
``test_interaction_audit_correlation.py`` — ``asyncio.run`` over a real in-flight
subprocess transport hangs at loop close on some asyncio versions.
"""

from __future__ import annotations

import asyncio
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
if str(_DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(_DAEMON_DIR))

import _marshalld_audit as audit_mod  # noqa: E402
import manage_build_server as mbs  # noqa: E402
import marshalld  # noqa: E402
from _build_server_protocol import JobSpec, status_payload  # noqa: E402
from _marshalld_journal import Journal  # noqa: E402
from _marshalld_scheduler import Scheduler  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


@pytest.fixture
def project(home: Path) -> Path:
    """A distinct project root the logs verb can scope to."""
    root = home / 'proj'
    root.mkdir()
    return root


def _daemon(tmp_path, audit, journal) -> marshalld.Daemon:
    return marshalld.Daemon(
        scheduler=Scheduler(max_slots=1),
        journal=journal,
        interaction_audit=audit,
        log_dir=tmp_path / 'job-logs',
    )


def _spec(project_root: Path) -> JobSpec:
    return JobSpec(
        command=[sys.executable, str(project_root / '.plan' / 'execute-script.py'), 'a:b:c', 'run'],
        exec_path=str(project_root),
        project_path=str(project_root),
        plan_id='p1',
        fingerprint='fp',
    )


def _submit(daemon: marshalld.Daemon, spec: JobSpec) -> str:
    """Drive the submit seam synchronously — assign a job_id, journal it, audit it."""
    request = {'op': 'submit', 'job': spec.to_dict()}
    result = daemon._scheduler.submit(spec, 'root')  # enqueue only — no admit, no subprocess
    daemon._journal.record_spec(result.job_id, spec.to_dict())
    response = {'status': 'queued', 'job_id': result.job_id, 'attached': result.attached}
    daemon._audit_interaction('submit', request, response)
    return result.job_id


def _stub_run_job(monkeypatch, payload: dict) -> None:
    """Replace the supervisor's ``run_job`` with a coroutine returning ``payload``."""

    async def _fake_run_job(*_args, **_kwargs):
        return payload

    monkeypatch.setattr(marshalld, 'run_job', _fake_run_job)


def _terminalize(daemon, job_id: str, spec: JobSpec, payload: dict, monkeypatch) -> None:
    """Drive the REAL ``_execute`` terminalization seam with ``run_job`` stubbed.

    The job is ADMITTED through the scheduler first, exactly as ``_admit_ready``
    does in production — a job only ever reaches ``_execute`` after admission.
    Driving ``_execute`` on a still-queued job would leave the scheduler's
    ``complete()`` tail a no-op (freeing neither the slot nor the idempotency
    fingerprint) and leave the job's own stale queue entry behind for the tail's
    ``_admit_ready()`` to pick up.
    """
    admitted = daemon._scheduler.admit_next()
    assert admitted is not None and admitted.job_id == job_id
    daemon._journal.record_status(job_id, 'running')

    _stub_run_job(monkeypatch, payload)
    asyncio.run(daemon._execute(job_id, spec.to_dict()))


class _StartupReached(Exception):
    """Sentinel raised from a stubbed ``start_unix_server`` to mark bind-time."""


def _serve_until_bind(daemon, monkeypatch) -> None:
    """Run ``serve()`` through replay + fate emission, stopping at the socket bind."""

    async def _sentinel(*_args, **_kwargs):
        raise _StartupReached

    monkeypatch.setattr(marshalld.asyncio, 'start_unix_server', _sentinel)
    with pytest.raises(_StartupReached):
        asyncio.run(daemon.serve())


def _logs(project_root: Path) -> list[dict]:
    records: list[dict] = mbs.run_logs(Namespace(root=str(project_root), limit=None))['records']
    return records


def _fate_by_job(records: list[dict]) -> dict[str, str]:
    return {
        record['job_id']: record['fate']
        for record in records
        if record['kind'] == audit_mod.KIND_INTERACTION
    }


# =============================================================================
# 1. Discrimination — a completed job and an abandoned job must differ
# =============================================================================


def test_completed_and_abandoned_jobs_render_differently(project, tmp_path, monkeypatch):
    """The fail-first test: today's defect renders BOTH as `outcome: queued`.

    A job that ran to completion and a job the daemon abandoned (its supervisor
    died, so restart replay forced it to `killed`) must be distinguishable in the
    operator view. Both are driven through the real terminalization seams.
    """
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)

    # Job A completes through _execute -> record_result -> fate emission.
    done_id = _submit(daemon, spec)
    _terminalize(
        daemon,
        done_id,
        spec,
        status_payload('success', duration_seconds=1, log_file=str(tmp_path / 'a.log')),
        monkeypatch,
    )

    # Job B is left in flight and the daemon restarts: replay forces it to
    # `killed` and serve() emits that fate.
    lost_id = _submit(daemon, spec)
    journal.record_status(lost_id, 'running')
    _serve_until_bind(daemon, monkeypatch)

    fates = _fate_by_job(_logs(project))

    assert fates[done_id] == 'success'
    assert fates[lost_id] == 'killed'
    # The whole point: they are no longer indistinguishable.
    assert fates[done_id] != fates[lost_id]


def test_request_status_stays_truthful_about_the_request(project, tmp_path, monkeypatch):
    """Carrying a fate must not corrupt the request-scoped status.

    The submit really WAS answered `queued`; the fix adds a fate column, it does
    not rewrite history on the request column.
    """
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)

    job_id = _submit(daemon, spec)
    _terminalize(
        daemon,
        job_id,
        spec,
        status_payload('failure', duration_seconds=1, log_file=str(tmp_path / 'a.log')),
        monkeypatch,
    )

    row = next(r for r in _logs(project) if r['kind'] == audit_mod.KIND_INTERACTION)
    assert row['request_status'] == 'queued'
    assert row['fate'] == 'failure'


def test_terminalized_job_is_never_admitted_again(project, tmp_path, monkeypatch):
    """One terminalization emits exactly ONE fate record — structurally.

    ``_execute``'s tail re-enters ``_admit_ready()``. If an admission ever hands
    back a job that has ALREADY terminalized, the daemon would re-run the build,
    clobber the terminal journal status back to ``running``, and append a SECOND
    ``kind=job_fate`` record for a single terminalization. The admission must be
    released instead — freeing both the slot and the idempotency fingerprint.
    """
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)
    _stub_run_job(monkeypatch, status_payload('success', duration_seconds=1, log_file='x'))

    # A job that terminalized while its own entry is still sitting in the queue.
    job_id = _submit(daemon, spec)
    journal.record_result(job_id, status_payload('success', duration_seconds=1, log_file='x'))
    daemon._audit_job_fate(job_id, 'success', spec.to_dict())

    async def _drive():
        daemon._admit_ready()

    asyncio.run(_drive())

    fate_records = [r for r in audit.read_all() if r.get('kind') == audit_mod.KIND_JOB_FATE]
    assert [r['job_id'] for r in fate_records] == [job_id]
    assert daemon._tasks == {}  # no second execution was ever started
    assert journal.get(job_id)['status'] == 'success'  # terminal status not clobbered
    # The stale admission was released, not left holding the slot or the fingerprint.
    assert daemon._scheduler.queued_count == 0
    assert daemon._scheduler.running_count == 0
    assert not daemon._scheduler.has_job(spec.fingerprint)


# =============================================================================
# 2. Unknown fate — never a terminal value, never queued
# =============================================================================


def test_daemon_died_without_restart_renders_unknown(project, tmp_path):
    """No replay ran, so the on-disk entry is frozen non-terminal.

    The child died with the supervisor, so reporting the job as in-flight would be
    false — and `queued` would be the original defect. It renders `unknown`.
    """
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)

    job_id = _submit(daemon, spec)
    journal.record_status(job_id, 'running')  # frozen here — the daemon never came back

    fates = _fate_by_job(_logs(project))

    assert fates[job_id] == 'unknown'
    assert fates[job_id] not in {'success', 'failure', 'timeout', 'killed'}
    assert fates[job_id] != 'queued'


def test_gcd_journal_entry_renders_unknown(project, tmp_path):
    """The audit row outlives the journal entry (7 days vs 3600 s).

    Once the journal entry is GC'd there is nothing left to join against, so the
    fate is undeterminable and renders `unknown` rather than a fabricated value.
    """
    audit = audit_mod.InteractionAudit()
    journal = Journal(retention_seconds=0)
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)

    job_id = _submit(daemon, spec)
    journal.record_result(job_id, status_payload('success', duration_seconds=1, log_file='x'))
    # Age every terminal entry past the (zero-length) retention window.
    assert journal.gc(now=journal.get(job_id)['updated_epoch'] + 10) == [job_id]
    assert journal.get(job_id) is None

    # The interaction row survives; with no emitted fate record it renders unknown.
    audit_only = [
        record
        for record in audit.read_all()
        if record.get('kind') == audit_mod.KIND_JOB_FATE
    ]
    assert audit_only == []
    assert _fate_by_job(_logs(project))[job_id] == 'unknown'


@pytest.mark.parametrize('claimed', ['queued', 'running', '', 'bogus'])
def test_writer_refuses_to_claim_a_non_terminal_fate(home, claimed):
    """A fate outside the terminal vocabulary is stored as `unknown`.

    The daemon never claims a fate it cannot substantiate, and never records the
    request-scoped `queued` as though it were an outcome.
    """
    audit = audit_mod.InteractionAudit()

    stored = audit.record_job_fate('JOB-1', claimed)

    assert stored['fate'] == audit_mod.FATE_UNKNOWN
    assert audit.read_all()[-1]['fate'] == audit_mod.FATE_UNKNOWN


@pytest.mark.parametrize('terminal', ['success', 'failure', 'timeout', 'killed'])
def test_writer_stores_every_real_terminal_fate_verbatim(home, terminal):
    """Each of the four real terminal states round-trips unchanged.

    Guards the negative test above from degenerating into "everything is unknown".
    """
    audit = audit_mod.InteractionAudit()

    assert audit.record_job_fate('JOB-1', terminal)['fate'] == terminal


# =============================================================================
# 3. Secrets discipline on the fate write path
# =============================================================================


def test_fate_record_carries_no_secret_bearing_field(project, tmp_path, monkeypatch):
    """The fate write derives attribution from the spec without copying secrets."""
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)

    job_id = _submit(daemon, spec)
    _terminalize(
        daemon,
        job_id,
        spec,
        status_payload('success', duration_seconds=1, log_file=str(tmp_path / 'a.log')),
        monkeypatch,
    )

    fate_records = [r for r in audit.read_all() if r.get('kind') == audit_mod.KIND_JOB_FATE]
    assert len(fate_records) == 1
    record = fate_records[0]
    blob = json.dumps(record)

    assert set(record) == {'kind', 'job_id', 'fate', 'project_root', 'plan_id', 'timestamp'}
    assert sys.executable not in blob
    assert str(project / '.plan' / 'execute-script.py') not in blob
    assert 'command' not in record
    assert 'exec_path' not in record
    assert 'env' not in record
    # Only the canonical project_root survives as attribution.
    assert record['project_root'] == mbs.canonicalize_root(str(project))
    assert record['plan_id'] == 'p1'


@pytest.mark.parametrize(
    'forbidden_key',
    ['command', 'args', 'argv', 'spec', 'env', 'cwd', 'exec_path', 'project_path'],
)
def test_record_job_fate_rejects_forbidden_secret_shaped_extra_key(home, forbidden_key):
    """The `_FORBIDDEN_EXTRA_KEYS` backstop guards the NEW write path too."""
    audit = audit_mod.InteractionAudit()

    with pytest.raises(ValueError, match=forbidden_key):
        audit.record_job_fate('JOB-1', 'success', '/proj', 'p1', **{forbidden_key: 'secret-value'})

    assert audit.read_all() == []


# =============================================================================
# 4. Best-effort writes — never abort request handling or daemon startup
# =============================================================================


def test_fate_write_disk_failure_does_not_abort_execution(project, tmp_path, monkeypatch):
    """A disk failure on the fate write must not break job terminalization."""
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    spec = _spec(project)
    job_id = _submit(daemon, spec)

    def _boom(**_kwargs):
        raise OSError('audit log write failure')

    monkeypatch.setattr(audit, 'record_job_fate', _boom)

    # Must NOT raise — and the journal result must still be recorded.
    _terminalize(
        daemon,
        job_id,
        spec,
        status_payload('success', duration_seconds=1, log_file=str(tmp_path / 'a.log')),
        monkeypatch,
    )

    assert journal.get(job_id)['status'] == 'success'


def test_fate_write_attribution_failure_is_swallowed(home, tmp_path, monkeypatch):
    """Attribution derivation (``canonicalize_root``) can raise — it is guarded."""
    audit = audit_mod.InteractionAudit()
    daemon = _daemon(tmp_path, audit, Journal())

    def _boom(_path):
        raise OSError('resolution failure (e.g. symlink loop)')

    monkeypatch.setattr(marshalld, 'canonicalize_root', _boom)

    # Must NOT raise; the aborted derivation writes no record (clean best-effort skip).
    daemon._audit_job_fate('JOB-1', 'success', {'project_path': '/proj', 'plan_id': 'p1'})

    assert audit.read_all() == []


def test_fate_write_failure_does_not_abort_daemon_startup(home, tmp_path, monkeypatch):
    """A replay-path fate-write failure must never stop the daemon from binding."""
    audit = audit_mod.InteractionAudit()
    journal = Journal()
    daemon = _daemon(tmp_path, audit, journal)
    journal.record_spec('JOB-STUCK', _spec(Path(home)).to_dict(), status='running')

    def _boom(**_kwargs):
        raise OSError('audit log write failure')

    monkeypatch.setattr(audit, 'record_job_fate', _boom)

    # The bind sentinel — NOT the OSError — must escape.
    _serve_until_bind(daemon, monkeypatch)

    # Replay still did its job: the stuck entry was forced to its real terminal state.
    assert journal.get('JOB-STUCK')['status'] == 'killed'
