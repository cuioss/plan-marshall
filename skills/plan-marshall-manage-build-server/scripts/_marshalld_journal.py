#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""On-disk journal for the marshalld build server (S6 retention + restart replay).

The journal is the daemon's durable memory: it persists every job's spec and
terminal result, plus per-command ETA history, under the machine-global
``~/.plan-marshall/marshalld/journal/`` directory. It gives the build server two
properties the request demands:

* **Bounded retention (S6)** — a terminal result is readable for a bounded
  window (default 3600 s) after completion, then garbage-collected; a ``wait``
  after expiry returns ``not_found`` rather than an unbounded-growth journal.
* **Restart survival** — on daemon restart the journal REPLAYS: terminal
  results survive (still readable), but any job that was ``queued`` / ``running``
  when the daemon died is marked ``killed`` — its child process died with the
  supervisor and must never be silently resumed or reported as still running.

Each job is one JSON file (``{job_id}.json``); ETA history is a single
``eta-history.json`` mapping a command key to a bounded list of recent
durations. All state is stdlib-JSON — no database, no LLM in the loop.

Usage:
    from _marshalld_journal import Journal

    journal = Journal()          # resolves ~/.plan-marshall/marshalld/journal/
    journal.record_spec(job_id, spec_dict)
    journal.record_status(job_id, 'running')
    journal.record_result(job_id, result_payload)   # terminal
    entry = journal.get(job_id)  # None once GC'd past retention
    journal.record_duration('maven:verify', 42.0)
    eta = journal.estimate_eta('maven:verify')
    killed = journal.replay_on_restart()   # job_ids forced to killed
    removed = journal.gc()                  # expired terminal job_ids removed
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from file_ops import atomic_write_file, now_utc_iso, read_json
from marketplace_paths import ensure_home_root, home_root

# Terminal statuses mirror the wire vocabulary in _build_server_protocol. They
# are duplicated as a small literal set here (rather than imported) so the
# journal has no hard import dependency on the protocol module's constants — the
# journal only ever compares status strings.
_TERMINAL = frozenset({'success', 'failure', 'timeout', 'killed'})
_STATUS_KILLED = 'killed'

_JOURNAL_SUBDIR = 'journal'
_ETA_FILENAME = 'eta-history.json'
_DIR_MODE = 0o700
_FILE_MODE = 0o600

DEFAULT_RETENTION_SECONDS = 3600
"""Default terminal-result retention window (S6)."""

DEFAULT_ETA_SAMPLES = 20
"""Number of recent durations retained per command key for ETA estimation."""


class Journal:
    """Durable job/result/ETA store under the machine-global marshalld home.

    The instance resolves its directory once at construction from
    ``home_root()`` (honouring ``PLAN_MARSHALL_HOME``), so a test can isolate the
    whole journal by pointing that env var at a tmp dir before constructing.
    """

    def __init__(
        self,
        retention_seconds: int = DEFAULT_RETENTION_SECONDS,
        eta_samples: int = DEFAULT_ETA_SAMPLES,
    ) -> None:
        """Initialise the journal.

        Args:
            retention_seconds: Terminal-result retention window in seconds.
            eta_samples: Number of recent durations kept per command key.
        """
        self._retention_seconds = retention_seconds
        self._eta_samples = eta_samples
        self._dir = home_root() / 'marshalld' / _JOURNAL_SUBDIR

    # -- directory / paths -------------------------------------------------

    @property
    def directory(self) -> Path:
        """Return the journal directory path."""
        return self._dir

    def ensure_dir(self) -> Path:
        """Create the journal directory ``0o700`` (idempotent) and return it."""
        ensure_home_root()
        self._dir.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
        if (self._dir.stat().st_mode & 0o777) != _DIR_MODE:
            os.chmod(self._dir, _DIR_MODE)
        return self._dir

    def _job_path(self, job_id: str) -> Path:
        return self._dir / f'{job_id}.json'

    def _eta_path(self) -> Path:
        return self._dir / _ETA_FILENAME

    # -- job records -------------------------------------------------------

    def _write_entry(self, entry: dict[str, Any]) -> None:
        self.ensure_dir()
        path = self._job_path(entry['job_id'])
        atomic_write_file(path, json.dumps(entry, indent=2))
        if (path.stat().st_mode & 0o777) != _FILE_MODE:
            os.chmod(path, _FILE_MODE)

    def record_spec(self, job_id: str, spec: dict[str, Any], status: str = 'queued') -> dict[str, Any]:
        """Persist a new job's spec, creating its journal entry.

        Args:
            job_id: The job identifier (unique per submit).
            spec: The job spec dict (:meth:`JobSpec.to_dict`).
            status: Initial status (default ``queued``).

        Returns:
            The stored journal entry.
        """
        now = time.time()
        entry = {
            'job_id': job_id,
            'spec': spec,
            'status': status,
            'result': None,
            'created_at': now_utc_iso(),
            'created_epoch': now,
            'updated_epoch': now,
        }
        self._write_entry(entry)
        return entry

    def record_status(self, job_id: str, status: str) -> dict[str, Any] | None:
        """Update a job's non-terminal status (e.g. ``queued`` → ``running``).

        Args:
            job_id: The job identifier.
            status: The new status.

        Returns:
            The updated entry, or ``None`` when the job is unknown.
        """
        entry = self.get(job_id)
        if entry is None:
            return None
        entry['status'] = status
        entry['updated_epoch'] = time.time()
        self._write_entry(entry)
        return entry

    def record_result(self, job_id: str, result: dict[str, Any]) -> dict[str, Any] | None:
        """Persist a job's terminal result and terminal status.

        The terminal status is taken from ``result['status']`` when present,
        which the supervisor already renders in the wire vocabulary
        (``success|failure|timeout|killed``).

        Args:
            job_id: The job identifier.
            result: The terminal status payload.

        Returns:
            The updated entry, or ``None`` when the job is unknown.
        """
        entry = self.get(job_id)
        if entry is None:
            return None
        entry['result'] = result
        entry['status'] = result.get('status', 'success')
        entry['updated_epoch'] = time.time()
        self._write_entry(entry)
        return entry

    def get(self, job_id: str) -> dict[str, Any] | None:
        """Return a job's journal entry, or ``None`` when absent / GC'd.

        Args:
            job_id: The job identifier.

        Returns:
            The stored entry dict, or ``None``.
        """
        path = self._job_path(job_id)
        if not path.exists():
            return None
        data = read_json(path, default=None)
        return data if isinstance(data, dict) else None

    def _iter_entries(self) -> list[dict[str, Any]]:
        if not self._dir.is_dir():
            return []
        entries: list[dict[str, Any]] = []
        for path in self._dir.glob('*.json'):
            if path.name == _ETA_FILENAME:
                continue
            data = read_json(path, default=None)
            if isinstance(data, dict) and 'job_id' in data:
                entries.append(data)
        return entries

    # -- restart replay / GC ----------------------------------------------

    def replay_on_restart(self) -> list[str]:
        """Mark every non-terminal job ``killed`` (restart replay).

        A job left ``queued`` / ``running`` when the daemon died lost its child
        with the supervisor — it is transitioned to ``killed`` (its own terminal
        state), NEVER silently resumed. Terminal results are untouched.

        Returns:
            The job ids that were transitioned to ``killed``.
        """
        killed: list[str] = []
        for entry in self._iter_entries():
            if entry.get('status') not in _TERMINAL:
                entry['status'] = _STATUS_KILLED
                if not isinstance(entry.get('result'), dict):
                    entry['result'] = {'status': _STATUS_KILLED}
                else:
                    entry['result']['status'] = _STATUS_KILLED
                entry['updated_epoch'] = time.time()
                self._write_entry(entry)
                killed.append(entry['job_id'])
        return killed

    def gc(self, now: float | None = None) -> list[str]:
        """Remove terminal job entries older than the retention window.

        Only terminal entries are eligible: a ``queued`` / ``running`` job is
        never GC'd out from under a live wait. After removal a ``get`` /
        ``wait`` for that id returns ``None`` (the daemon renders ``not_found``).

        Args:
            now: Current epoch seconds; defaults to :func:`time.time`.

        Returns:
            The job ids that were removed.
        """
        current = time.time() if now is None else now
        removed: list[str] = []
        for entry in self._iter_entries():
            if entry.get('status') not in _TERMINAL:
                continue
            updated = entry.get('updated_epoch', 0.0)
            if current - float(updated) > self._retention_seconds:
                self._job_path(entry['job_id']).unlink(missing_ok=True)
                removed.append(entry['job_id'])
        return removed

    # -- ETA history -------------------------------------------------------

    def record_duration(self, command_key: str, seconds: float) -> None:
        """Append a completed run's duration to a command key's ETA history.

        The history is bounded to the most recent :data:`DEFAULT_ETA_SAMPLES`
        durations per key, so the file stays small and the estimate tracks
        recent behaviour rather than the all-time average.

        Args:
            command_key: The command identity (e.g. ``maven:verify``).
            seconds: The observed wall-clock duration.
        """
        self.ensure_dir()
        history = self._read_eta_history()
        samples = history.get(command_key, [])
        samples.append(float(seconds))
        history[command_key] = samples[-self._eta_samples :]
        path = self._eta_path()
        atomic_write_file(path, json.dumps(history, indent=2))
        if (path.stat().st_mode & 0o777) != _FILE_MODE:
            os.chmod(path, _FILE_MODE)

    def estimate_eta(self, command_key: str) -> float | None:
        """Estimate a command's ETA as the mean of its recent durations.

        Args:
            command_key: The command identity.

        Returns:
            The mean recent duration in seconds, or ``None`` when the key has no
            recorded history.
        """
        samples = self._read_eta_history().get(command_key, [])
        if not samples:
            return None
        return sum(samples) / len(samples)

    def _read_eta_history(self) -> dict[str, list[float]]:
        data = read_json(self._eta_path(), default={})
        if not isinstance(data, dict):
            return {}
        cleaned: dict[str, list[float]] = {}
        for key, samples in data.items():
            if isinstance(samples, list):
                cleaned[key] = [float(s) for s in samples if isinstance(s, (int, float))]
        return cleaned
