#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared reader for the machine-global per-directory build lock.

The per-directory build lock is a record inside the machine-global
``build-queue.json`` (see ``manage-locks/build_queue``): which build is writing
which project directory right now. TWO very different processes must answer
"is this directory held, and by something alive?" from it:

* the build wrapper, which takes and releases the lock
  (``_build_queue_slot.directory_lock`` → ``build_queue.run_directory_acquire``),
  and
* the ``marshalld`` daemon, which consults it at admission so it never spends a
  machine slot on a child that would then wait for the directory.

Two copies of the field names and the liveness rule is one copy too many: a
change to either would silently desynchronise admission from the lock — the
daemon admitting a job for a directory the wrapper considers held, or the
wrapper waiting on a directory the daemon considers free. This module is the ONE
implementation both import.

It is a pure reader plus a liveness predicate: no writes, no I/O beyond reading
a state file the caller hands in. Liveness is by PID — a plan-less lane build
(``NO_PLAN``) has no plan directory, so a plan-anchored check would declare a
running build dead.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DIRECTORY_LOCKS_FIELD = 'directory_locks'
"""Top-level ``build-queue.json`` field: ``{canonical_directory: holder record}``.

A holder record is ``{plan_id, command, pid, acquired_at, ticket}``.
"""

DIRECTORY_WAITERS_FIELD = 'directory_waiters'
"""Top-level ``build-queue.json`` field: the FIFO list of builds waiting for a directory.

A waiter record is ``{directory, ticket, plan_id, command, pid, ts}``.
"""


def is_zombie(pid: Any) -> bool:
    """Return whether ``pid`` is an unreaped zombie (Linux ``/proc``), else False.

    ``os.kill(pid, 0)`` SUCCEEDS for a process that has exited but has not been
    reaped by its parent, and a build child the daemon killed can stay unreaped for
    a while. Counting that as a live holder would block its directory for as long
    as the corpse lives. Where ``/proc`` is unavailable (macOS) there is no portable
    probe and the caller's signal test alone decides.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        stat = Path(f'/proc/{pid}/stat').read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False
    # Field 3 is the process state; the comm field (2) may contain spaces and
    # parentheses, so the state is read after the LAST ')' of the comm field.
    _, _, tail = stat.rpartition(')')
    state = tail.strip().split(' ', 1)[0] if tail.strip() else ''
    return state == 'Z'


def pid_alive(pid: Any) -> bool:
    """Return whether ``pid`` names a live, non-zombie process.

    Never guesses and never raises:

    * a malformed pid is NOT alive — a corrupt record must be reclaimable rather
      than wedging a directory forever;
    * ``ProcessLookupError`` means gone;
    * ``PermissionError`` means the process exists (another user owns it);
    * any OTHER errno (``ENOSYS`` under a seccomp filter, ``EINVAL``, …) means the
      probe could not answer, and it fails toward ALIVE: letting a second build
      into a directory a live build may be writing is the hazard this lock exists
      to prevent, whereas a stale record has an explicit escape
      (``build_queue directory clear``).
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return not is_zombie(pid)
    except OSError:
        return True
    return not is_zombie(pid)


def directory_locks(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the directory-holder map, dropping records that are not mappings."""
    raw = state.get(DIRECTORY_LOCKS_FIELD)
    if not isinstance(raw, dict):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def directory_waiters(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the FIFO waiter list, dropping records missing a ticket or directory.

    The admission scan keys on both, so a record missing either would raise inside
    the read-modify-write and take every acquire down with it. Junk is DROPPED, in
    the same fail-open-to-reclaim direction the dead-holder prune takes.
    """
    raw = state.get(DIRECTORY_WAITERS_FIELD)
    if not isinstance(raw, list):
        return []
    return [
        entry
        for entry in raw
        if isinstance(entry, dict) and isinstance(entry.get('ticket'), str) and isinstance(entry.get('directory'), str)
    ]


def held_directories(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return ``{directory: holder}`` for the directories a LIVE holder occupies.

    The single answer to "which directories are held right now", shared by the
    daemon's admission check and by anything else that must not enter a held
    directory. A record whose pid is gone (or is an unreaped zombie) is not held.
    """
    return {directory: holder for directory, holder in directory_locks(state).items() if pid_alive(holder.get('pid'))}
