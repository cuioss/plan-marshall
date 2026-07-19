#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Central append-only interaction-audit log for the marshalld build server.

The interaction audit is the daemon's per-request accountability trail: every
request the daemon dispatches (``ping`` / ``submit`` / ``wait``) appends exactly
one attributed record to a single central JSON-lines log under the machine-global
``~/.plan-marshall/marshalld/interaction-audit.log``. It is a *sibling* of the
job :mod:`_marshalld_journal` (which keeps raw specs/results/ETA keyed by
``job_id``), not a replacement — the two answer different questions:

* the JOURNAL answers "what is the state / result of job X?" (keyed by ``job_id``);
* the AUDIT answers "who asked the daemon to do what, and how did it turn out?"
  (one uniform record per request, including the ``ping`` and ``refused`` /
  ``degraded`` interactions that carry no ``job_id`` and so cannot be keyed under
  the journal at all).

Each record stamps ``op`` / ``project_root`` / ``plan_id`` / ``job_id`` /
``outcome`` / ``timestamp`` (plus non-secret extras like ``reason``). The
``project_root`` field is the per-project attribution the operator ``logs`` read
verb filters on to derive a project-scoped view. Retention is bounded and GC'd on
every daemon start, mirroring the journal's S6 model.

Secrets discipline: a record NEVER carries ``spec.command`` (the raw argv), the
process env, exec/project paths beyond the canonical ``project_root``, or any
other spec field that may carry secrets.

Usage:
    from _marshalld_audit import InteractionAudit

    audit = InteractionAudit()                 # resolves ~/.plan-marshall/marshalld/
    audit.record('submit', '/proj', 'p1', 'JOB-1', 'queued')
    audit.record('submit', '/proj', 'p1', '', 'refused', reason='not_registered')
    records = audit.read_all()                  # every stored record (newest last)
    removed = audit.gc()                        # count of expired records pruned
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from file_ops import atomic_write_file, now_utc_iso
from marketplace_paths import ensure_home_root, home_root

_AUDIT_FILENAME = 'interaction-audit.log'
_DIR_MODE = 0o700
_FILE_MODE = 0o600

DEFAULT_AUDIT_RETENTION_SECONDS = 7 * 24 * 3600
"""Default interaction-audit retention window in seconds (7 days).

Parallel to :data:`_marshalld_journal.DEFAULT_RETENTION_SECONDS`: a bounded
window after which a record is GC'd on daemon start. The audit trail is kept
longer than the journal's terminal-result window because it is an
accountability record, not live job state.
"""

# The ISO-8601 UTC form produced by ``now_utc_iso`` (no fractional seconds), used
# to parse a record's ``timestamp`` back to epoch for the GC age comparison.
_TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def _parse_iso_epoch(timestamp: Any) -> float | None:
    """Parse an ISO-8601 UTC ``timestamp`` string back to epoch seconds.

    Args:
        timestamp: The record's ``timestamp`` field.

    Returns:
        Epoch seconds, or ``None`` when the value is missing or unparseable (an
        unparseable record is kept by GC, never silently dropped).
    """
    if not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.strptime(timestamp, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None
    return parsed.timestamp()


class InteractionAudit:
    """Central append-only interaction-audit log under the marshalld home.

    The instance resolves its path once at construction from ``home_root()``
    (honouring ``PLAN_MARSHALL_HOME``), so a test can isolate the whole audit log
    by pointing that env var at a tmp dir before constructing.
    """

    def __init__(self, retention_seconds: int = DEFAULT_AUDIT_RETENTION_SECONDS) -> None:
        """Initialise the interaction audit.

        Args:
            retention_seconds: Retention window in seconds; records older than
                this are pruned by :meth:`gc`.
        """
        self._retention_seconds = retention_seconds
        self._path = home_root() / 'marshalld' / _AUDIT_FILENAME

    @property
    def path(self) -> Path:
        """Return the interaction-audit log path."""
        return self._path

    # -- directory / file mode --------------------------------------------

    def _ensure_dir(self) -> None:
        """Create the ``0o700`` marshalld dir the audit log lives in (idempotent)."""
        ensure_home_root()
        directory = self._path.parent
        directory.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
        if (directory.stat().st_mode & 0o777) != _DIR_MODE:
            os.chmod(directory, _DIR_MODE)

    def _chmod_file(self) -> None:
        """Force the audit log to ``0o600`` (matching the lifecycle-audit idiom)."""
        if self._path.exists() and (self._path.stat().st_mode & 0o777) != _FILE_MODE:
            os.chmod(self._path, _FILE_MODE)

    # -- record / read / gc -----------------------------------------------

    def record(
        self,
        op: str,
        project_root: str,
        plan_id: str,
        job_id: str,
        outcome: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Append exactly one attributed interaction record.

        Args:
            op: The dispatched op (``ping`` / ``submit`` / ``wait``).
            project_root: The canonical project root, or ``''`` when absent
                (e.g. a ``ping`` or a ``wait`` that carries no spec).
            plan_id: The submitting plan id, or ``''`` when absent.
            job_id: The daemon-assigned job id, or ``''`` when absent.
            outcome: The response outcome (the response ``status``).
            **extra: Non-secret extra fields to record (e.g. ``reason``). A
                ``None`` value is dropped. NEVER pass secret-bearing spec fields.

        Returns:
            The stored record dict.
        """
        self._ensure_dir()
        record: dict[str, Any] = {
            'op': op,
            'project_root': project_root,
            'plan_id': plan_id,
            'job_id': job_id,
            'outcome': outcome,
            'timestamp': now_utc_iso(),
        }
        for key, value in extra.items():
            if value is not None:
                record[key] = value
        with open(self._path, 'a', encoding='utf-8') as handle:
            handle.write(json.dumps(record) + '\n')
        self._chmod_file()
        return record

    def read_all(self) -> list[dict[str, Any]]:
        """Return every stored record in append order (oldest first).

        A malformed line is skipped rather than aborting the read. A corrupted or
        unreadable log file fails closed to an empty list rather than raising: the
        read must never abort its callers, because ``gc()`` runs at daemon startup
        (``Daemon.serve``) — mirroring the sibling ``rotate_log`` best-effort
        startup guard. Callers that need to distinguish "present but unreadable"
        from "absent or empty" (the operator ``logs`` verb, for its
        ``log_unreadable`` reason) use :meth:`read_records_or_none` instead.

        Returns:
            The list of record dicts (empty when the log is absent, unreadable, or
            corrupted).
        """
        records = self.read_records_or_none()
        return [] if records is None else records

    def read_records_or_none(self) -> list[dict[str, Any]] | None:
        """Parse all records, distinguishing an unreadable log from an empty one.

        Returns ``[]`` when the log is absent or present-and-readable-but-empty,
        the parsed record list when present and readable, and ``None`` when the
        log is present but unreadable/corrupt (an ``OSError`` — permission/IO — or
        a ``UnicodeDecodeError``, which is NOT an ``OSError`` subclass, from a
        non-UTF-8-corrupted file). This is the single read+parse choke point:
        :meth:`read_all` collapses the ``None`` to ``[]`` for its crash-safe
        callers (``gc`` at daemon startup), while the operator ``logs`` verb keys
        its ``log_unreadable`` reason off the ``None``.

        Returns:
            The record list, or ``None`` when the present log could not be read.
        """
        if not self._path.exists():
            return []
        try:
            raw = self._path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            return None
        records: list[dict[str, Any]] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                records.append(data)
        return records

    def gc(self, now: float | None = None) -> int:
        """Prune records older than the retention window, rewriting atomically.

        A record whose ``timestamp`` cannot be parsed is kept (never silently
        dropped). The log is only rewritten when at least one record is pruned.

        Args:
            now: Current epoch seconds; defaults to :func:`time.time`.

        Returns:
            The number of records removed.
        """
        if not self._path.exists():
            return 0
        current = time.time() if now is None else now
        records = self.read_all()
        kept = [record for record in records if not self._is_expired(record, current)]
        removed = len(records) - len(kept)
        if removed:
            self._ensure_dir()
            payload = ''.join(json.dumps(record) + '\n' for record in kept)
            atomic_write_file(self._path, payload)
            self._chmod_file()
        return removed

    def _is_expired(self, record: dict[str, Any], current: float) -> bool:
        """Return whether ``record`` is past the retention window at ``current``."""
        epoch = _parse_iso_epoch(record.get('timestamp'))
        if epoch is None:
            return False
        return (current - epoch) > self._retention_seconds
