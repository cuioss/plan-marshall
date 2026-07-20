#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the marshalld central interaction-audit log.

Two surfaces are exercised:

* ``InteractionAudit.record`` / ``read_all`` / ``gc`` in isolation — one record
  per call, attribution + timestamp stamped, secrets never written, and GC
  pruning only records past the retention window. The whole store is isolated by
  pointing ``PLAN_MARSHALL_HOME`` at a per-test tmp dir before construction.
* ``Daemon.handle_request`` writes exactly one attributed record per dispatched
  ``ping`` / ``submit`` / ``wait`` request, deriving ``project_root`` / ``plan_id``
  / ``job_id`` from the request where present and empty when absent.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
if str(_DAEMON_DIR) not in sys.path:
    sys.path.insert(0, str(_DAEMON_DIR))

import _marshalld_audit as audit_mod  # noqa: E402
import marshalld  # noqa: E402
from _build_server_protocol import JobSpec  # noqa: E402
from _marshalld_journal import Journal  # noqa: E402
from _marshalld_scheduler import Scheduler  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


# =============================================================================
# InteractionAudit — record / read_all
# =============================================================================


def test_record_appends_exactly_one_line_per_call(home):
    audit = audit_mod.InteractionAudit()

    audit.record('ping', '', '', '', 'ok')
    assert len(audit.read_all()) == 1

    audit.record('submit', '/proj', 'p1', 'JOB-1', 'queued')
    assert len(audit.read_all()) == 2


def test_record_stamps_attribution_and_timestamp(home):
    audit = audit_mod.InteractionAudit()

    record = audit.record('submit', '/proj', 'p1', 'JOB-1', 'queued')

    stored = audit.read_all()[-1]
    assert stored == record
    assert stored['op'] == 'submit'
    assert stored['project_root'] == '/proj'
    assert stored['plan_id'] == 'p1'
    assert stored['job_id'] == 'JOB-1'
    assert stored['outcome'] == 'queued'
    assert stored['timestamp']  # a non-empty ISO stamp


def test_record_keeps_non_secret_extra_and_drops_none(home):
    audit = audit_mod.InteractionAudit()

    audit.record('submit', '/proj', 'p1', '', 'refused', reason='not_registered', dropped=None)

    stored = audit.read_all()[-1]
    assert stored['reason'] == 'not_registered'
    assert 'dropped' not in stored


def test_record_never_writes_secret_bearing_fields(home):
    audit = audit_mod.InteractionAudit()

    audit.record('submit', '/proj', 'p1', 'JOB-1', 'queued')

    stored = audit.read_all()[-1]
    # The record schema is fixed — no spec/command/env/argv ever leaks in.
    assert set(stored) == {'op', 'project_root', 'plan_id', 'job_id', 'outcome', 'timestamp'}
    assert 'command' not in stored
    assert 'spec' not in stored
    assert 'env' not in stored


@pytest.mark.parametrize('forbidden_key', ['command', 'args', 'argv', 'spec', 'env', 'cwd', 'exec_path', 'project_path'])
def test_record_rejects_forbidden_secret_shaped_extra_key(home, forbidden_key):
    """Fail-loud backstop (defense-in-depth): a secret-shaped ``extra`` key must
    raise immediately rather than ever reach the on-disk audit trail, even from
    a future caller that violates the secrets-discipline contract."""
    audit = audit_mod.InteractionAudit()

    with pytest.raises(ValueError, match=forbidden_key):
        audit.record('submit', '/proj', 'p1', 'JOB-1', 'queued', **{forbidden_key: 'secret-value'})

    assert audit.read_all() == []


def test_read_all_on_absent_log_is_empty(home):
    audit = audit_mod.InteractionAudit()

    assert audit.read_all() == []


def test_read_all_on_non_utf8_corrupt_log_fails_closed(home):
    """A non-UTF-8-corrupted log must degrade to an empty list, never raise.

    ``read_all`` is the single read choke point for both ``gc`` (daemon startup)
    and the operator ``logs`` verb; a ``UnicodeDecodeError`` (not an ``OSError``
    subclass) leaking out would crash the daemon at startup.
    """
    audit = audit_mod.InteractionAudit()
    audit.record('ping', '', '', '', 'ok')  # materialise the log + parent dir
    # Overwrite with bytes that are not valid UTF-8.
    audit.path.write_bytes(b'\xff\xfe not valid utf-8 \x80\x81')

    assert audit.read_all() == []


def test_gc_on_corrupt_log_does_not_crash(home):
    """gc() runs at daemon startup — a corrupt log must not abort it.

    Regression guard for the unguarded-boundary defect: gc() -> read_all() ->
    read_text() would raise UnicodeDecodeError on a corrupt log and crash
    Daemon.serve() before the daemon could accept any request.
    """
    audit = audit_mod.InteractionAudit()
    audit.record('ping', '', '', '', 'ok')
    audit.path.write_bytes(b'\xff\xfe\x00 corrupt \x80')

    # Must not raise; a corrupt log yields no parseable records to prune.
    assert audit.gc() == 0


def test_read_records_or_none_distinguishes_unreadable_from_empty(home):
    """read_records_or_none() returns None only for a present-but-unreadable log.

    Absent and present-and-readable-but-empty both return [] (indistinguishable to
    the operator verb's log_absent/empty handling); a non-UTF-8-corrupt present log
    returns None so the logs verb can report log_unreadable. This is the three-state
    contract read_all() collapses to [] for its crash-safe callers.
    """
    audit = audit_mod.InteractionAudit()

    # Absent → [] (not None).
    assert audit.read_records_or_none() == []

    # Present, readable, non-empty → the parsed records.
    audit.record('ping', '', '', '', 'ok')
    assert audit.read_records_or_none() == audit.read_all()
    assert len(audit.read_records_or_none()) == 1

    # Present but corrupt (non-UTF-8) → None (the distinguishable unreadable state).
    audit.path.write_bytes(b'\xff\xfe corrupt \x80')
    assert audit.read_records_or_none() is None
    # read_all() still collapses that None to [] for gc()/daemon-startup safety.
    assert audit.read_all() == []


# =============================================================================
# InteractionAudit — gc (bounded retention)
# =============================================================================


def test_gc_on_absent_log_returns_zero(home):
    audit = audit_mod.InteractionAudit()

    assert audit.gc() == 0


def test_gc_removes_only_records_past_the_window(home, monkeypatch):
    audit = audit_mod.InteractionAudit(retention_seconds=100)

    # An old record, stamped far in the past.
    monkeypatch.setattr(audit_mod, 'now_utc_iso', lambda: '2000-01-01T00:00:00Z')
    audit.record('ping', '', '', '', 'ok')
    # A fresh record, stamped far in the future.
    monkeypatch.setattr(audit_mod, 'now_utc_iso', lambda: '2100-01-01T00:00:00Z')
    audit.record('submit', '/proj', 'p1', 'JOB-NEW', 'queued')

    # GC as-of one second after the fresh record's stamp: the old record is well
    # past the 100s window, the fresh one is inside it.
    now_epoch = datetime(2100, 1, 1, 0, 0, 1, tzinfo=UTC).timestamp()
    removed = audit.gc(now=now_epoch)

    assert removed == 1
    remaining = audit.read_all()
    assert len(remaining) == 1
    assert remaining[0]['job_id'] == 'JOB-NEW'


def test_gc_keeps_all_records_within_the_window(home):
    audit = audit_mod.InteractionAudit(retention_seconds=3600)
    audit.record('ping', '', '', '', 'ok')
    audit.record('ping', '', '', '', 'ok')

    # GC now — both records were just written, so none is past the window.
    removed = audit.gc()

    assert removed == 0
    assert len(audit.read_all()) == 2


def test_now_utc_iso_round_trips_through_parse_iso_epoch():
    """Guard the (convention-only) format contract between the writer and GC parser.

    Every other GC test mocks ``now_utc_iso`` to a hand-crafted string, so none
    proves the REAL, unmocked ``file_ops.now_utc_iso()`` output actually parses
    back through ``_parse_iso_epoch``. If that contract ever broke, ``_is_expired``
    would silently read ``None`` for every timestamp and ``gc()`` would degrade to
    "never prunes anything" — a silent failure this one unmocked assertion catches.
    """
    assert audit_mod._parse_iso_epoch(audit_mod.now_utc_iso()) is not None


def test_record_preserved_across_gc_rewrite_is_still_readable(home):
    audit = audit_mod.InteractionAudit(retention_seconds=3600)
    audit.record('submit', '/proj', 'p1', 'JOB-KEEP', 'queued')

    audit.gc()

    stored = audit.read_all()
    assert len(stored) == 1
    assert stored[0]['job_id'] == 'JOB-KEEP'


# =============================================================================
# Daemon dispatch — one attributed record per request
# =============================================================================


def _daemon(tmp_path, audit) -> marshalld.Daemon:
    return marshalld.Daemon(
        scheduler=Scheduler(max_slots=1),
        journal=Journal(),
        interaction_audit=audit,
        log_dir=tmp_path / 'job-logs',
    )


def test_handle_request_writes_one_record_per_ping_and_wait(home, tmp_path):
    audit = audit_mod.InteractionAudit()
    daemon = _daemon(tmp_path, audit)

    async def _drive() -> None:
        await daemon.handle_request({'op': 'ping'})
        await daemon.handle_request({'op': 'wait', 'job_id': 'J', 'bound': 0})

    asyncio.run(_drive())

    records = audit.read_all()
    assert [r['op'] for r in records] == ['ping', 'wait']
    # ping carries no attribution; wait carries only the requested job_id.
    assert records[0]['project_root'] == ''
    assert records[0]['plan_id'] == ''
    assert records[0]['job_id'] == ''
    assert records[0]['outcome'] == 'ok'
    assert records[1]['job_id'] == 'J'


def test_handle_request_submit_records_project_attribution(home, tmp_path):
    audit = audit_mod.InteractionAudit()
    daemon = _daemon(tmp_path, audit)
    spec = JobSpec(
        command=[sys.executable, '-c', 'pass'],
        exec_path=str(tmp_path),
        project_path=str(tmp_path),
        plan_id='p1',
        fingerprint='fp',
    )

    async def _drive():
        return await daemon.handle_request({'op': 'submit', 'job': spec.to_dict()})

    response = asyncio.run(_drive())

    records = audit.read_all()
    assert len(records) == 1
    record = records[0]
    assert record['op'] == 'submit'
    assert record['plan_id'] == 'p1'
    assert record['project_root']  # canonicalised project path — non-empty
    assert record['outcome'] == response['status']
    # Secrets discipline: the raw command argv never appears anywhere in the record.
    assert 'command' not in record
    assert 'spec' not in record
    assert sys.executable not in json.dumps(record)


def test_handle_request_unknown_op_is_still_audited(home, tmp_path):
    audit = audit_mod.InteractionAudit()
    daemon = _daemon(tmp_path, audit)

    async def _drive() -> None:
        await daemon.handle_request({'op': 'bogus'})

    asyncio.run(_drive())

    records = audit.read_all()
    assert len(records) == 1
    assert records[0]['op'] == 'bogus'
    assert records[0]['outcome'] == 'error'


def test_audit_interaction_swallows_attribution_failure(home, tmp_path, monkeypatch):
    """Attribution DERIVATION failure must never abort request handling.

    ``_audit_attribution`` calls ``canonicalize_root`` (``Path.resolve()``), which
    can raise ``OSError`` on a symlink loop / resolution failure. That derivation
    runs inside the best-effort guard, so a raise there is swallowed exactly like a
    ``record()`` disk failure — the daemon's "a disk failure must never abort
    request handling" contract covers the whole audit path, not just the write.
    """
    audit = audit_mod.InteractionAudit()
    daemon = _daemon(tmp_path, audit)

    def _boom(_op, _request):
        raise OSError('resolution failure (e.g. symlink loop)')

    monkeypatch.setattr(daemon, '_audit_attribution', _boom)

    # Must NOT raise — the guard now covers attribution derivation, not just record().
    daemon._audit_interaction('submit', {'op': 'submit'}, {'status': 'queued'})

    # The aborted derivation wrote no record (clean best-effort skip).
    assert audit.read_all() == []
