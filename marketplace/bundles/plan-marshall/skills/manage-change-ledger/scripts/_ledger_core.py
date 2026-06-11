#!/usr/bin/env python3
"""Deterministic core for the unified change-ledger primitive.

Notation: imported as a module (PYTHONPATH) — ``from _ledger_core import
append_entry, read_entries, build_record, change_record, resolve_ledger_path``.
NOT an executor entry point.

This module is the single read/write/construct surface for the one append-only
change-ledger (``.plan/work/change-ledger.jsonl``). The ledger is the unified
``worktree_sha``-stamped record of working-tree transitions; it subsumes the
former "build-registry" idea entirely (there is NO separate ``builds.jsonl``).
Both writers — the executor dispatch-boundary ``kind=build`` writer and the
phase-5 ``kind=change`` writer — and both readers — the ``query`` verb and the
``pre-commit-verify-freshness`` gate — go through this core so entries are
shaped identically and parsed identically.

**Tracked-config-dir resolution, NOT plan-scoped.** The ledger resolves via
:func:`file_ops.get_tracked_config_dir` (modeled on ``manage-locks``), so it
serves plan-less orchestrator builds (a ``kind=build`` entry with ``plan_id:
null``) just as well as plan-scoped task builds.

**Pure-append concurrency.** :func:`append_entry` writes exactly one
``json.dumps(record) + '\\n'`` line per call with a single ``open(..., 'a')``.
On the small per-record size this is atomic enough for a POSIX append, and
:func:`read_entries` tolerates (skips) malformed lines, so no lock is
introduced. The shape is deliberately pure-append — no read-modify-write, no
find-and-update — so no check-then-act window exists and the cooperative-lock
class does not apply. (See the TOCTOU / check-then-act mitigation menu in
``dev-general-code-quality/standards/code-organization.md`` — the pure-append
shape avoids the window entirely.)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from file_ops import get_tracked_config_dir, now_utc_iso  # type: ignore[import-not-found]

KIND_BUILD = 'build'
KIND_CHANGE = 'change'


def resolve_ledger_path() -> Path:
    """Resolve the single change-ledger path under the tracked-config dir.

    ``<tracked-config-dir>/work/change-ledger.jsonl``. NOT plan-scoped — one
    ledger per repository working tree, covering plan-less orchestrator builds.
    """
    return get_tracked_config_dir() / 'work' / 'change-ledger.jsonl'


def append_entry(record: dict[str, Any], path: Path | None = None) -> None:
    """Append exactly one JSONL line for ``record``. Pure-append.

    Creates the ``work/`` parent directory if absent, then writes one
    ``json.dumps(record) + '\\n'`` line with a single ``open(path, 'a')``. No
    read-modify-write, no in-place mutation.
    """
    ledger_path = path if path is not None else resolve_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + '\n'
    with open(ledger_path, 'a', encoding='utf-8') as handle:
        handle.write(line)


def read_entries(path: Path | None = None) -> list[dict[str, Any]]:
    """Read the change-ledger JSONL file, skipping malformed lines.

    Returns the parsed entries in file order, or ``[]`` when the ledger is
    absent. This is the library reader the gate imports directly rather than
    shelling out to the ``query`` verb.
    """
    ledger_path = path if path is not None else resolve_ledger_path()
    if not ledger_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with open(ledger_path, encoding='utf-8') as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    entries.append(parsed)
    except OSError:
        pass
    return entries


def build_record(
    *,
    notation: str,
    plan_id: str | None,
    args: str | None,
    exit_code: int,
    worktree_sha: str | None,
    log_file: str | None,
    timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct a ``kind=build`` ledger record.

    Written by the executor dispatch boundary after every build-class
    invocation. Carries the build outcome (``exit_code``, recorded even when
    non-zero — the gate filters on it) stamped against the working-tree
    ``worktree_sha`` at capture time. A build is NOT a commit, so this record
    does NOT carry ``commit_sha`` or ``changed_paths``.
    """
    return {
        'kind': KIND_BUILD,
        'notation': notation,
        'plan_id': plan_id,
        'args': args,
        'exit_code': exit_code,
        'worktree_sha': worktree_sha,
        'log_file': log_file,
        'timestamp_iso': timestamp_iso if timestamp_iso is not None else now_utc_iso(),
    }


def change_record(
    *,
    deliverable_id: str,
    worktree_sha: str | None,
    commit_sha: str,
    changed_paths: list[str],
    timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct a ``kind=change`` ledger record.

    Written by the phase-5 execute loop after each deliverable completes and
    commits. ``commit_sha`` and ``changed_paths`` are git-sourced by the caller
    (from ``git diff-tree`` against the just-produced commit) — this constructor
    stores the caller-supplied list VERBATIM; it does NOT compute or re-derive
    changed paths. Self-computed / ``affected_files``-snapshotted paths are
    PROHIBITED at the call site.
    """
    return {
        'kind': KIND_CHANGE,
        'deliverable_id': deliverable_id,
        'commit_sha': commit_sha,
        'changed_paths': list(changed_paths),
        'worktree_sha': worktree_sha,
        'timestamp_iso': timestamp_iso if timestamp_iso is not None else now_utc_iso(),
    }
