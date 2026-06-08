#!/usr/bin/env python3
"""Pre-commit verify-freshness command handler for manage-tasks.py.

Closes the necessary-vs-sufficient gap between ``loop-exit-guard``
(queue-empty proof) and the pre-commit-push state (worktree-actually-verified
proof). The command answers a single deterministic question:

    Is the most recent ``plan-marshall:build-pyproject:pyproject_build run``
    line in ``script-execution.log`` newer than the most recent file-content
    mtime in the worktree?

Three possible outcomes:

- ``fresh``        — build log entry post-dates the newest worktree mtime;
                     a fresh ``verify`` has been observed against the current
                     on-disk state, so the gate is permitted to pass.
- ``stale``        — newest worktree mtime post-dates the most recent build
                     log entry; the worktree has been mutated since the last
                     observed verify, so the gate MUST fail closed.
- ``undecidable``  — either no matching INFO log line exists, or the worktree
                     mtime cannot be resolved; the gate MUST fail closed
                     because no positive freshness proof exists.

The full failure-mode contract — including the ``--force`` orchestrator
escape and the cross-references to phase-5-execute Step 12a and
phase-6-finalize ``commit-push`` — is documented in
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness".
"""

import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from _references_core import (  # type: ignore[import-not-found]
    compute_plan_branch_diff,
    resolve_base_ref,
)
from _tasks_core import get_plan_dir  # type: ignore[import-not-found]
from constants import FILE_REFERENCES, FILE_STATUS  # type: ignore[import-not-found]
from file_ops import read_json  # type: ignore[import-not-found]

# Build-run log line shape (script-execution.log):
#   [2026-05-24T20:56:42Z] [INFO] [abc123] plan-marshall:build-pyproject:pyproject_build run (12.3s)
# We match only INFO entries — ERROR entries indicate the run failed, which
# does NOT count as a successful verify observation. The substring
# ``plan-marshall:build-pyproject:pyproject_build run`` is matched literally;
# the trailing ``(N.NNs)`` duration block is optional in the regex so future
# log-format additions do not silently break the match.
_BUILD_LINE_RE = re.compile(
    r'^\[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]'
    r'\s+\[INFO\]'
    r'\s+\[[0-9a-f]+\]'
    r'\s+plan-marshall:build-pyproject:pyproject_build\s+run\b'
)

# Directories skipped during the worktree-root fallback walk. The set mirrors
# the project's gitignore conventions: build outputs (``target``, ``build``),
# tooling caches (``__pycache__``, ``node_modules``, ``.venv``), git metadata
# (``.git``), plan-marshall runtime state (``.plan``). Any other dotted
# directory is also skipped (see ``_skip_dir`` below).
_SKIP_DIR_NAMES = frozenset(
    {'.git', '.plan', 'node_modules', '__pycache__', '.venv', 'target', 'build'}
)


def _skip_dir(name: str) -> bool:
    """Return True when a directory name should be skipped by the rglob walk."""
    if name in _SKIP_DIR_NAMES:
        return True
    return name.startswith('.')


def _resolve_log_path(plan_id: str) -> Path:
    """Resolve the plan-scoped script-execution.log path.

    Mirrors the resolution used by ``manage-logging:plan_logging.get_log_path``
    for the plan-scoped branch (the global-fallback branch is intentionally
    NOT consulted — the freshness gate is a plan-scoped invariant and a
    missing plan-scoped log file is itself a signal that no build has been
    observed against this plan).
    """
    return get_plan_dir(plan_id) / 'logs' / 'script-execution.log'


def _scan_latest_build_ts(log_path: Path) -> tuple[datetime | None, str | None]:
    """Scan the log from tail-end for the most recent matching INFO entry.

    Returns ``(timestamp, iso_string)`` for the latest match, or
    ``(None, None)`` when no matching line exists (or the log file itself is
    missing). Reads the entire file because plan-scoped logs are bounded by
    plan lifetime and tail-scanning would require a backwards-line iterator
    that is not worth the complexity here.
    """
    if not log_path.is_file():
        return (None, None)

    latest_ts: datetime | None = None
    latest_iso: str | None = None
    try:
        with log_path.open(encoding='utf-8', errors='replace') as f:
            for line in f:
                match = _BUILD_LINE_RE.match(line)
                if not match:
                    continue
                iso = match.group('ts')
                try:
                    ts = datetime.strptime(iso, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)
                except ValueError:
                    continue
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts
                    latest_iso = iso
    except OSError:
        return (None, None)

    return (latest_ts, latest_iso)


def _max_mtime_from_paths(paths: list[Path]) -> tuple[float | None, Path | None]:
    """Compute the maximum mtime across a list of paths that exist on disk.

    Missing paths are silently skipped — the caller decides what to do if all
    candidates are missing. Returns ``(max_epoch_seconds, newest_path)`` or
    ``(None, None)`` when no candidate exists.
    """
    max_mtime: float | None = None
    newest_path: Path | None = None
    for path in paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        if max_mtime is None or stat.st_mtime > max_mtime:
            max_mtime = stat.st_mtime
            newest_path = path
    return (max_mtime, newest_path)


def _walk_worktree_for_max_mtime(worktree_root: Path) -> tuple[float | None, Path | None]:
    """Walk the worktree root and return the newest file's mtime + path.

    Skips the directories named in ``_SKIP_DIR_NAMES`` (and any other dotted
    directory). The walk is implemented manually via ``Path.iterdir`` so we
    can prune skipped subtrees at descent time rather than filtering after
    a full ``rglob('*')`` materialisation.
    """
    max_mtime: float | None = None
    newest_path: Path | None = None
    stack: list[Path] = [worktree_root]

    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir():
                    if _skip_dir(entry.name):
                        continue
                    stack.append(entry)
                    continue
                stat = entry.stat()
            except OSError:
                continue
            if max_mtime is None or stat.st_mtime > max_mtime:
                max_mtime = stat.st_mtime
                newest_path = entry

    return (max_mtime, newest_path)


def _read_status_metadata(plan_id: str) -> dict:
    """Read ``status.json`` for the plan and return its ``metadata`` dict.

    Reads the plan-scoped status file directly via ``file_ops.read_json``
    rather than dispatching through ``manage-status`` to keep this command
    inside the manage-tasks sys.path island. Returns an empty dict on any
    read/parse error so the caller can degrade to the cwd fallback.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.is_file():
        return {}
    try:
        status = read_json(status_path)
    except Exception:  # noqa: BLE001 — degrade to empty metadata on any error
        return {}
    if not isinstance(status, dict):
        return {}
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return {}
    return metadata


def _resolve_worktree_root(plan_id: str) -> Path:
    """Resolve the worktree root for the plan.

    Reads ``status.metadata.worktree_path`` and falls back to the current
    working directory when no worktree is materialised. The fallback is
    intentional: a plan that runs against the main checkout still needs a
    freshness gate, and the main checkout is reachable from cwd.
    """
    metadata = _read_status_metadata(plan_id)
    worktree_path = metadata.get('worktree_path', '')
    if isinstance(worktree_path, str) and worktree_path:
        candidate = Path(worktree_path)
        if candidate.is_dir():
            return candidate
    return Path.cwd()


def _resolve_footprint(plan_id: str, worktree_root: Path) -> list[str]:
    """Derive the live plan footprint as the mtime-candidate scope.

    Reads ``references.json`` only to resolve the base ref, then computes the
    footprint live from the worktree via ``compute_plan_branch_diff``
    (``{base}...HEAD`` ∪ porcelain). Returns repo-relative paths.

    Returns an empty list on any failure — missing references.json, a worktree
    that is not a git tree (archived plan), or a git error — so callers fall
    back to the worktree-root walk exactly as before. Absolute paths and
    ``.``/``..`` traversal entries are filtered out for safety.
    """
    refs_path = get_plan_dir(plan_id) / FILE_REFERENCES
    refs: dict = {}
    if refs_path.is_file():
        try:
            loaded = read_json(refs_path)
        except Exception:  # noqa: BLE001 — degrade to empty refs on any error
            loaded = None
        if isinstance(loaded, dict):
            refs = loaded
    base_ref = resolve_base_ref(None, refs)
    try:
        footprint = compute_plan_branch_diff(worktree_root, base_ref)
    except subprocess.CalledProcessError:
        return []
    return [
        entry
        for entry in footprint
        if entry
        and not Path(entry).is_absolute()
        and '..' not in Path(entry).parts
        and '.' not in Path(entry).parts
    ]


def _iso_from_epoch(epoch: float) -> str:
    """Format a POSIX epoch as an ISO-8601 UTC string with Z suffix."""
    return datetime.fromtimestamp(epoch, tz=UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def cmd_pre_commit_verify_freshness(args) -> dict:
    """Handle ``pre-commit-verify-freshness`` subcommand.

    See module docstring for the contract; the algorithm is laid out in
    deliverable 1 of the plan ``solution_outline.md``.
    """
    plan_id: str = args.plan_id

    log_path = _resolve_log_path(plan_id)
    t_build_dt, t_build_iso = _scan_latest_build_ts(log_path)

    if t_build_dt is None:
        return {
            'status': 'undecidable',
            'plan_id': plan_id,
            'reason': 'no_build_log_entry',
            'log_path': str(log_path),
            'message': (
                f'script-execution.log contains no INFO entry matching '
                f'"plan-marshall:build-pyproject:pyproject_build run" '
                f'(searched: {log_path}). No positive freshness proof exists; '
                f'gate MUST fail closed.'
            ),
        }

    worktree_root = _resolve_worktree_root(plan_id)
    footprint = _resolve_footprint(plan_id, worktree_root)

    # Resolve mtime candidates: the live footprint first (precise scope), then
    # fall back to a full worktree walk when the footprint is empty or every
    # entry is missing on disk.
    candidate_paths: list[Path] = []
    for rel in footprint:
        # Footprint entries are repo-relative; resolve against the worktree
        # root so a plan that runs in an isolated worktree walks the correct
        # tree.
        candidate_paths.append(worktree_root / rel)

    t_worktree_epoch: float | None = None
    newest_path: Path | None = None
    if candidate_paths:
        t_worktree_epoch, newest_path = _max_mtime_from_paths(candidate_paths)

    if t_worktree_epoch is None:
        t_worktree_epoch, newest_path = _walk_worktree_for_max_mtime(worktree_root)

    if t_worktree_epoch is None:
        return {
            'status': 'undecidable',
            'plan_id': plan_id,
            'reason': 'worktree_mtime_unresolvable',
            'worktree_root': str(worktree_root),
            't_build_iso': t_build_iso,
            'message': (
                f'Worktree root {worktree_root} produced no candidate files '
                f'after pruning skip-list directories. No mtime baseline '
                f'available; gate MUST fail closed.'
            ),
        }

    t_build_epoch = t_build_dt.timestamp()
    t_worktree_iso = _iso_from_epoch(t_worktree_epoch)

    if t_build_epoch < t_worktree_epoch:
        return {
            'status': 'stale',
            'plan_id': plan_id,
            't_build_iso': t_build_iso,
            't_worktree_iso': t_worktree_iso,
            'newest_mtime_path': str(newest_path) if newest_path else '',
            'worktree_root': str(worktree_root),
            'message': (
                f'Worktree mutated since the most recent verify run '
                f'(build={t_build_iso}, worktree={t_worktree_iso}, '
                f'newest_path={newest_path}). Gate MUST fail closed; '
                f're-dispatch verify before retrying.'
            ),
        }

    return {
        'status': 'fresh',
        'plan_id': plan_id,
        't_build_iso': t_build_iso,
        't_worktree_iso': t_worktree_iso,
        'newest_mtime_path': str(newest_path) if newest_path else '',
        'worktree_root': str(worktree_root),
        'message': (
            f'Latest verify run ({t_build_iso}) post-dates the newest '
            f'worktree mtime ({t_worktree_iso}). Gate permitted.'
        ),
    }
