#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Job scheduler for the marshalld build server (slots, fairness, idempotency).

The scheduler decides WHICH accepted job runs NEXT and enforces three
properties the request demands:

* **Bounded concurrency** — at most ``max_slots`` jobs run at once. The cap is
  the MACHINE-GLOBAL ``build.queue.max_slots`` (default
  :data:`_machine_config.DEFAULT_MAX_SLOTS`, the machine-CPU cap), resolved by
  :func:`_machine_config.resolve_max_slots` from ``machine-config.json`` — it is
  NOT a per-repository ``marshal.json`` key, because the daemon serves every
  registered project on the host and one shared slot budget cannot take a
  different value per project. This is the daemon-side admission count; the
  actual cross-process slot is coordinated against the single machine-global
  ``build-queue.json`` by the build-execute routing seam (D5), which owns the
  shared reader/writer. The scheduler tracks the daemon's own admitted set so it
  never oversubscribes the budget it holds. The cap is re-pointable while the
  scheduler is live (:meth:`Scheduler.set_max_slots`), because the daemon
  re-resolves the machine-global value on every submit — an operator's ``config
  set`` therefore takes effect without restarting a daemon that may be serving
  other projects' builds. A re-point governs future ADMISSION only and never
  evicts a running job.
* **Per-project round-robin fairness** — when several projects contend for the
  slot budget, admission rotates across projects rather than draining one
  project's queue before serving another. Within a project, order is FIFO.
* **Idempotent submit** — an identical concurrent submit (same
  ``plan_id + notation + args + tree`` fingerprint) ATTACHES to the existing
  in-flight job and returns its id, instead of double-running the build.

The scheduler is a pure in-memory data structure with no I/O, so its fairness
and idempotency are fully unit-testable without a daemon, a socket, or a real
subprocess.

Usage:
    from _marshalld_scheduler import Scheduler

    scheduler = Scheduler(max_slots=5)
    result = scheduler.submit(job_spec, project_root)
    if result.attached:
        ...  # identical in-flight job — reuse result.job_id
    entry = scheduler.admit_next()   # None when no slot / no queued job
    scheduler.complete(entry.job_id)
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from _machine_config import DEFAULT_MAX_SLOTS


@dataclass
class JobEntry:
    """A scheduled job's bookkeeping record.

    Attributes:
        job_id: Unique per submit (a fresh uuid; identical resubmits attach to
            the original id instead of minting a new one).
        fingerprint: The idempotent-submit fingerprint.
        project_root: The registered canonical root (the fairness key).
        plan_id: The submitting plan id.
        spec: The job spec dict.
    """

    job_id: str
    fingerprint: str
    project_root: str
    plan_id: str
    spec: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubmitResult:
    """Outcome of :meth:`Scheduler.submit`.

    Attributes:
        job_id: The job id to wait on (a fresh id, or the attached-to id).
        attached: ``True`` when an identical in-flight job already existed and
            this submit attached to it instead of enqueuing a new job.
    """

    job_id: str
    attached: bool


class Scheduler:
    """In-memory admission scheduler with fairness and idempotent attach."""

    def __init__(self, max_slots: int = DEFAULT_MAX_SLOTS) -> None:
        """Initialise the scheduler.

        Args:
            max_slots: Maximum concurrently-running jobs (>= 1).
        """
        # Through set_max_slots() so the >= 1 floor is applied in exactly ONE
        # place: the cap arrives here at startup and there on every re-resolve,
        # and two copies of the clamp are two chances for the doors to disagree
        # about what the lowest legal cap is.
        self._max_slots = 1
        self.set_max_slots(max_slots)
        self._queues: dict[str, deque[JobEntry]] = {}
        self._order: list[str] = []
        self._rotation = 0
        self._running: dict[str, JobEntry] = {}
        self._by_fingerprint: dict[str, str] = {}

    # -- introspection -----------------------------------------------------

    @property
    def max_slots(self) -> int:
        """Return the concurrency cap."""
        return self._max_slots

    @property
    def running_count(self) -> int:
        """Return the number of currently-running jobs."""
        return len(self._running)

    @property
    def queued_count(self) -> int:
        """Return the total number of queued (not-yet-admitted) jobs."""
        return sum(len(q) for q in self._queues.values())

    def available_slots(self) -> int:
        """Return how many more jobs may be admitted right now."""
        return max(0, self._max_slots - len(self._running))

    def has_job(self, fingerprint: str) -> bool:
        """Return whether a job with ``fingerprint`` is queued or running."""
        return fingerprint in self._by_fingerprint

    # -- mutation ----------------------------------------------------------

    def set_max_slots(self, max_slots: int) -> int:
        """Re-point the concurrency cap at a newly-resolved value.

        The cap is machine-global state an operator can change under a running
        daemon (``manage_build_server config set``), and the daemon re-resolves it
        per submit — so the scheduler must be able to take a new cap without being
        rebuilt, which would discard its queues, its running set, and the
        idempotency fingerprints of jobs already in flight.

        Applies to ADMISSION only, never retroactively to running jobs. LOWERING
        the cap below the current running count therefore does not cancel or evict
        anything: :meth:`available_slots` already floors at ``0``, so the
        scheduler simply admits nothing new until enough jobs complete to bring
        the running count back under the new cap. Killing a build an operator
        never asked to kill would be a far worse answer to "the cap went down"
        than waiting is.

        Args:
            max_slots: The newly-resolved cap. Clamped to ``>= 1`` on the same
                floor the constructor applies — one shared clamp, so a caller
                cannot reach a zero cap through this door that the constructor
                would have rejected, and a cap of ``0`` can never wedge the
                daemon into admitting nothing forever.

        Returns:
            The cap now in effect (post-clamp), so a caller reports what was
            applied rather than what it asked for.
        """
        self._max_slots = max(1, int(max_slots))
        return self._max_slots

    def submit(self, job_spec: Any, project_root: str) -> SubmitResult:
        """Enqueue a job, or attach to an identical in-flight one.

        Args:
            job_spec: A :class:`_build_server_protocol.JobSpec` (needs
                ``fingerprint``, ``plan_id``, and a ``to_dict`` method).
            project_root: The registered canonical root (fairness key).

        Returns:
            A :class:`SubmitResult`; ``attached=True`` when an identical job was
            already in flight.
        """
        fingerprint = getattr(job_spec, 'fingerprint', '') or ''
        if fingerprint and fingerprint in self._by_fingerprint:
            return SubmitResult(job_id=self._by_fingerprint[fingerprint], attached=True)

        job_id = uuid.uuid4().hex
        spec_dict = job_spec.to_dict() if hasattr(job_spec, 'to_dict') else dict(job_spec)
        entry = JobEntry(
            job_id=job_id,
            fingerprint=fingerprint,
            project_root=project_root,
            plan_id=getattr(job_spec, 'plan_id', '') or '',
            spec=spec_dict,
        )
        if project_root not in self._queues:
            self._queues[project_root] = deque()
            self._order.append(project_root)
        self._queues[project_root].append(entry)
        if fingerprint:
            self._by_fingerprint[fingerprint] = job_id
        return SubmitResult(job_id=job_id, attached=False)

    def admit_next(self) -> JobEntry | None:
        """Admit and return the next job under fairness, or ``None``.

        Returns ``None`` when no slot is free or no job is queued. Selection
        rotates across projects (round-robin), FIFO within a project.
        """
        if self.available_slots() == 0 or not self._order:
            return None

        count = len(self._order)
        for offset in range(count):
            idx = (self._rotation + offset) % count
            project = self._order[idx]
            queue = self._queues.get(project)
            if queue:
                entry = queue.popleft()
                # Advance rotation PAST the served project so the next admit
                # starts at the following project (true round-robin).
                self._rotation = (idx + 1) % count
                self._running[entry.job_id] = entry
                return entry
        return None

    def complete(self, job_id: str) -> JobEntry | None:
        """Mark a running job finished, freeing its slot and fingerprint.

        Args:
            job_id: The job id that finished.

        Returns:
            The completed entry, or ``None`` when the id was not running.
        """
        entry = self._running.pop(job_id, None)
        if entry is None:
            return None
        if entry.fingerprint and self._by_fingerprint.get(entry.fingerprint) == job_id:
            del self._by_fingerprint[entry.fingerprint]
        return entry
