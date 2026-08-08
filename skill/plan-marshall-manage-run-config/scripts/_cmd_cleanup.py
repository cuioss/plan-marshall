# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cleanup command handlers for manage-run-config.

Handles: cleanup, cleanup-status

Reads retention settings directly from marshal.json rather than
calling manage-config via subprocess — intentional optimization
to avoid process overhead for a frequently-called internal module.
"""

import argparse
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Direct imports - PYTHONPATH set by executor
from _config_defaults import DEFAULT_SYSTEM_RETENTION
from constants import (
    CI_BODIES_DIRNAME,
    CLEANUP_TARGET_ALL,
    CLEANUP_TARGET_ARCHIVED_PLANS,
    CLEANUP_TARGET_BUILD_RESULTS,
    CLEANUP_TARGET_LOGS,
    CLEANUP_TARGET_NO_PLAN_BODIES,
    CLEANUP_TARGET_TEMP,
    DIR_ARCHIVED,
    DIR_LOGS,
    DIR_PLANS,
    DIR_WORK,
    FILE_STATUS,
)
from file_ops import (
    get_base_dir,
    get_build_results_dir,
    get_marshal_path,
    get_temp_dir,
    output_toon,
)
from marketplace_paths import NO_PLAN_SENTINEL

# Configuration — delegate to file_ops for consistent path resolution.
# PLAN_BASE_DIR holds runtime state (logs/, archived-plans/) in
# the per-project global plan-marshall directory. temp/ stays project-local
# under the tracked config dir (.plan/), and marshal.json is also tracked.
PLAN_BASE_DIR = get_base_dir()
MARSHAL_JSON = get_marshal_path()
TEMP_DIR = get_temp_dir()

# `CI_BODIES_DIRNAME` (the `<plan>/work/ci-bodies/` directory half, whose layout
# `tools-integration-ci.get_body_path` owns) and `CLEANUP_TARGETS` (the closed
# `cleanup --target` set `cmd_clean` dispatches on and `run_config.py` turns into
# its argparse `choices`) are both declared in `constants` and imported above —
# one declaration each, so neither can drift from its second consumer.


@dataclass
class CleanupStats:
    """Statistics from cleanup operations."""

    temp_files: int = 0
    temp_bytes: int = 0
    logs_deleted: int = 0
    logs_bytes: int = 0
    archived_plans_deleted: int = 0
    archived_plans_bytes: int = 0
    no_plan_bodies_deleted: int = 0
    no_plan_bodies_bytes: int = 0
    build_results_deleted: int = 0
    build_results_bytes: int = 0


def get_retention_settings() -> dict[str, Any] | None:
    """
    Get retention settings from marshal.json.

    Returns:
        dict with retention settings, or None if not found (TOON error already output).
    """
    if not MARSHAL_JSON.exists():
        output_toon(
            {
                'status': 'error',
                'error': 'file_not_found',
                'message': 'marshal.json not found. Run command /marshall-steward first',
            }
        )
        return None

    try:
        config = json.loads(MARSHAL_JSON.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        output_toon({'status': 'error', 'error': 'invalid_json', 'message': f'Invalid marshal.json: {e}'})
        return None

    if 'system' not in config or 'retention' not in config['system']:
        output_toon(
            {
                'status': 'error',
                'error': 'missing_config',
                'message': 'system.retention not configured. Run command /marshall-steward first',
            }
        )
        return None

    persisted: dict[str, Any] = config['system']['retention']
    retention: dict[str, Any] = dict(persisted)
    # Backfill retention keys the persisted marshal.json predates. A project
    # whose config was written before a key joined DEFAULT_SYSTEM_RETENTION —
    # and which has not re-run `manage-config sync-defaults` since — carries no
    # entry for it, so the direct indexing below (and in cmd_status / cmd_clean)
    # would raise an unhandled KeyError instead of producing a structured TOON
    # result. Defaults come from DEFAULT_SYSTEM_RETENTION so this normalization
    # cannot drift from the canonical values.
    for key, default in DEFAULT_SYSTEM_RETENTION.items():
        retention.setdefault(key, default)
    # Build results live and die with the plan artifact they belong to, so an
    # ABSENT `build_results_days` tracks the project's *effective*
    # `archived_plans_days` — a project that lengthened plan archival lengthens
    # build-result retention in lock-step, instead of silently falling back to
    # the shipped default the loop above just seeded. Membership is tested
    # against the RAW persisted mapping, not against `retention`, because the
    # loop above has already seeded a value there for every default key. An
    # explicitly configured `build_results_days` therefore always wins.
    if 'build_results_days' not in persisted:
        retention['build_results_days'] = retention['archived_plans_days']
    return retention


def get_path_age_days(path: Path) -> float:
    """Get age of a file or directory in days based on modification time."""
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) / 86400
    except OSError:
        return 0


def clean_temp(dry_run: bool = False) -> tuple[int, int]:
    """
    Clean .plan/temp directory.

    Returns:
        (files_deleted, bytes_freed)
    """
    temp_dir = TEMP_DIR
    if not temp_dir.exists():
        return 0, 0

    file_count = 0
    total_bytes = 0

    for item in temp_dir.rglob('*'):
        if item.is_file():
            file_count += 1
            try:
                total_bytes += item.stat().st_size
            except OSError:
                pass

    if dry_run:
        return file_count, total_bytes

    # Remove all contents but keep the directory
    for item in temp_dir.iterdir():
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except OSError:
            pass

    return file_count, total_bytes


def clean_logs(max_age_days: int, dry_run: bool = False) -> tuple[int, int]:
    """
    Clean old log files from .plan/logs.

    Returns:
        (files_deleted, bytes_freed)
    """
    logs_dir = PLAN_BASE_DIR / DIR_LOGS
    if not logs_dir.exists():
        return 0, 0

    deleted = 0
    total_bytes = 0

    for log_file in logs_dir.glob('*.log'):
        if get_path_age_days(log_file) > max_age_days:
            try:
                size = log_file.stat().st_size
                if not dry_run:
                    log_file.unlink()
                deleted += 1
                total_bytes += size
            except OSError:
                pass

    return deleted, total_bytes


def clean_archived_plans(max_age_days: int, dry_run: bool = False) -> tuple[int, int]:
    """
    Clean old archived plan directories from .plan/archived-plans.

    Returns:
        (dirs_deleted, bytes_freed)
    """
    archived_dir = PLAN_BASE_DIR / DIR_ARCHIVED
    if not archived_dir.exists():
        return 0, 0

    deleted = 0
    total_bytes = 0

    for plan_dir in archived_dir.iterdir():
        if not plan_dir.is_dir():
            continue

        if get_path_age_days(plan_dir) > max_age_days:
            # Calculate size
            dir_size = 0
            try:
                for f in plan_dir.rglob('*'):
                    if f.is_file():
                        dir_size += f.stat().st_size
            except OSError:
                pass

            if not dry_run:
                try:
                    shutil.rmtree(plan_dir)
                except OSError:
                    continue

            deleted += 1
            total_bytes += dir_size

    return deleted, total_bytes


def get_no_plan_bodies_dir() -> Path:
    """Return the sentinel plan's prepared-CI-body directory.

    ``{base}/plans/NO_PLAN/work/ci-bodies``. Derived from ``PLAN_BASE_DIR`` for
    the same reason its three sibling targets are: this module resolves every
    cleanable location from that one root, so the whole cleanup surface stays
    patchable at a single seam. The result is path-identical to
    ``file_ops.get_plan_dir(NO_PLAN_SENTINEL) / 'work' / 'ci-bodies'`` because
    ``get_plan_dir`` joins the same ``get_base_dir()`` root — a parity the test
    suite asserts directly, so this local derivation can never silently drift
    away from the resolver that produces the files.
    """
    return PLAN_BASE_DIR / DIR_PLANS / NO_PLAN_SENTINEL / DIR_WORK / CI_BODIES_DIRNAME


def clean_no_plan_bodies(max_age_days: int, dry_run: bool = False) -> tuple[int, int]:
    """Clean aged prepared-body files from the plan-less sentinel directory.

    The sentinel (``NO_PLAN``) is a SHARED, PERMANENT directory: unlike a real
    plan it is never archived, so the body files plan-less callers prepare
    under it accumulate with nothing to age them out. This target is that
    missing lifecycle.

    Only the ``*.md`` body FILES are removed. The sentinel directory itself,
    its ``work/`` subtree, and its ``status.json`` marker are NEVER deleted —
    removing ``status.json`` would make ``resolve_plan_context`` treat the
    sentinel as not-found and break every plan-less ``prepare_body`` caller
    until the next materialization. A missing sentinel directory is a clean
    ``(0, 0)`` no-op, never an error: a project where no plan-less body was
    ever prepared simply has nothing to clean.

    Returns:
        (files_deleted, bytes_freed)
    """
    bodies_dir = get_no_plan_bodies_dir()
    if not bodies_dir.exists():
        return 0, 0

    deleted = 0
    total_bytes = 0

    for body_file in bodies_dir.glob('*.md'):
        if get_path_age_days(body_file) > max_age_days:
            try:
                size = body_file.stat().st_size
                if not dry_run:
                    body_file.unlink()
                deleted += 1
                total_bytes += size
            except OSError:
                pass

    return deleted, total_bytes


def plan_is_live(plan_dir: Path) -> bool:
    """Return whether a plan directory belongs to a LIVE plan.

    A plan is live for as long as its directory carries a readable
    ``status.json``. That marker — not directory presence — is what the rest of
    the system already treats as "this plan exists and is being managed":
    ``file_ops.require_plan_exists`` guards on it, ``manage-status list`` skips
    directories without it, and ``manage-status list-orphans`` defines an orphan
    as exactly its absence. A finished plan does not linger here at all — the
    finalize ``archive-plan`` step MOVES it to ``archived-plans/``, where
    ``archived_plans_days`` ages the whole directory (build results included).

    The ``NO_PLAN`` sentinel also carries a ``status.json`` marker and would
    therefore read as live, which is why the enumeration below carves it out by
    id rather than by this predicate: the sentinel is never archived, so nothing
    would ever age its build results.
    """
    return (plan_dir / FILE_STATUS).is_file()


def cleanable_build_results_dirs() -> list[tuple[str, Path]]:
    """Return ``(plan_id, build_results_dir)`` for every NON-live results tree.

    The plan set is ENUMERATED FROM THE PLAN STORE, never from a hand-written
    list, so a newly created plan is covered without an edit here. Each entry's
    path comes from :func:`file_ops.get_build_results_dir` — the single owner of
    the build-results path — so this cleanup surface cannot drift away from the
    resolver the build wrappers actually write through.

    Two populations survive the filter:

    * A plan directory whose ``status.json`` is absent (see :func:`plan_is_live`)
      — a leftover the plan lifecycle no longer tracks.
    * The ``NO_PLAN`` sentinel, unconditionally. It is shared and permanent —
      never archived, exactly the condition that made the ``no-plan-bodies``
      target necessary — so an age threshold is the only lifecycle its build
      results can have. It is appended rather than discovered because its
      results are main-anchored (``get_build_results_dir`` resolves the sentinel
      through the main checkout), so a caller pinned to a worktree would
      otherwise never see it.

    A live plan appears in NEITHER the cleanup nor the ``cleanup-status``
    population: its build results are not merely spared deletion, they are never
    counted as reclaimable.
    """
    cleanable: list[tuple[str, Path]] = []

    plans_dir = PLAN_BASE_DIR / DIR_PLANS
    if plans_dir.is_dir():
        for plan_dir in sorted(plans_dir.iterdir()):
            if not plan_dir.is_dir() or plan_dir.name == NO_PLAN_SENTINEL:
                continue
            if plan_is_live(plan_dir):
                continue
            cleanable.append((plan_dir.name, get_build_results_dir(plan_dir.name)))

    cleanable.append((NO_PLAN_SENTINEL, get_build_results_dir(NO_PLAN_SENTINEL)))
    return cleanable


def build_result_files(results_dir: Path) -> list[Path]:
    """Return every regular file under one plan's build-results tree.

    A missing tree is an empty list, never an error: a plan that never ran a
    build simply has nothing to clean.
    """
    if not results_dir.is_dir():
        return []
    try:
        return [path for path in results_dir.rglob('*') if path.is_file()]
    except OSError:
        return []


def clean_build_results(max_age_days: int, dry_run: bool = False) -> tuple[int, int]:
    """Clean aged build-result files from every non-live plan's results tree.

    Only the result FILES are removed; the ``build-results`` directories
    themselves are left in place, matching the file-scoped shape of
    :func:`clean_logs` and :func:`clean_no_plan_bodies`.

    Returns:
        (files_deleted, bytes_freed)
    """
    deleted = 0
    total_bytes = 0

    for _plan_id, results_dir in cleanable_build_results_dirs():
        for result_file in build_result_files(results_dir):
            if get_path_age_days(result_file) <= max_age_days:
                continue
            try:
                size = result_file.stat().st_size
                if not dry_run:
                    result_file.unlink()
                deleted += 1
                total_bytes += size
            except OSError:
                pass

    return deleted, total_bytes


def get_status() -> dict[str, Any] | None:
    """
    Get status of all cleanable directories.

    Returns:
        dict with counts and sizes for each target, or None if config missing.
    """
    retention = get_retention_settings()
    if retention is None:
        return None

    # Temp stats
    temp_dir = TEMP_DIR
    temp_files = 0
    temp_bytes = 0
    if temp_dir.exists():
        for item in temp_dir.rglob('*'):
            if item.is_file():
                temp_files += 1
                try:
                    temp_bytes += item.stat().st_size
                except OSError:
                    pass

    # Logs stats
    logs_dir = PLAN_BASE_DIR / DIR_LOGS
    logs_total = 0
    logs_old = 0
    logs_old_bytes = 0
    if logs_dir.exists():
        for f in logs_dir.glob('*.log'):
            logs_total += 1
            if get_path_age_days(f) > retention['logs_days']:
                logs_old += 1
                try:
                    logs_old_bytes += f.stat().st_size
                except OSError:
                    pass

    # Archived plans stats
    archived_dir = PLAN_BASE_DIR / DIR_ARCHIVED
    archived_total = 0
    archived_old = 0
    archived_old_bytes = 0
    if archived_dir.exists():
        for d in archived_dir.iterdir():
            if d.is_dir():
                archived_total += 1
                if get_path_age_days(d) > retention['archived_plans_days']:
                    archived_old += 1
                    try:
                        for f in d.rglob('*'):
                            if f.is_file():
                                archived_old_bytes += f.stat().st_size
                    except OSError:
                        pass

    # Sentinel prepared-body stats
    bodies_dir = get_no_plan_bodies_dir()
    no_plan_bodies_total = 0
    no_plan_bodies_old = 0
    no_plan_bodies_old_bytes = 0
    if bodies_dir.exists():
        for f in bodies_dir.glob('*.md'):
            no_plan_bodies_total += 1
            if get_path_age_days(f) > retention['no_plan_body_days']:
                no_plan_bodies_old += 1
                try:
                    no_plan_bodies_old_bytes += f.stat().st_size
                except OSError:
                    pass

    # Build-results stats. The population is the CLEANABLE one — non-live plans
    # plus the sentinel — so `total` and `old` stand in the same relation here as
    # they do for logs (candidate population vs its aged subset). A live plan's
    # results are absent from BOTH counts: they are never offered as
    # safe-to-delete on this surface, not merely excluded from `old`.
    build_results_total = 0
    build_results_old = 0
    build_results_old_bytes = 0
    for _plan_id, results_dir in cleanable_build_results_dirs():
        for result_file in build_result_files(results_dir):
            build_results_total += 1
            if get_path_age_days(result_file) > retention['build_results_days']:
                build_results_old += 1
                try:
                    build_results_old_bytes += result_file.stat().st_size
                except OSError:
                    pass

    return {
        'retention': retention,
        'temp': {'files': temp_files, 'bytes': temp_bytes},
        'logs': {'total': logs_total, 'old': logs_old, 'old_bytes': logs_old_bytes},
        'archived_plans': {'total': archived_total, 'old': archived_old, 'old_bytes': archived_old_bytes},
        'no_plan_bodies': {
            'total': no_plan_bodies_total,
            'old': no_plan_bodies_old,
            'old_bytes': no_plan_bodies_old_bytes,
        },
        'build_results': {
            'total': build_results_total,
            'old': build_results_old,
            'old_bytes': build_results_old_bytes,
        },
    }


def cmd_clean(args: argparse.Namespace) -> dict[str, Any] | None:
    """Execute cleanup based on retention settings."""
    retention = get_retention_settings()
    if retention is None:
        return None
    target = args.target
    dry_run = args.dry_run

    stats = CleanupStats()

    # Clean temp
    if target in (CLEANUP_TARGET_ALL, CLEANUP_TARGET_TEMP) and retention.get('temp_on_maintenance', True):
        files, bytes_freed = clean_temp(dry_run)
        stats.temp_files = files
        stats.temp_bytes = bytes_freed

    # Clean logs
    if target in (CLEANUP_TARGET_ALL, CLEANUP_TARGET_LOGS):
        deleted, bytes_freed = clean_logs(retention['logs_days'], dry_run)
        stats.logs_deleted = deleted
        stats.logs_bytes = bytes_freed

    # Clean archived plans
    if target in (CLEANUP_TARGET_ALL, CLEANUP_TARGET_ARCHIVED_PLANS):
        deleted, bytes_freed = clean_archived_plans(retention['archived_plans_days'], dry_run)
        stats.archived_plans_deleted = deleted
        stats.archived_plans_bytes = bytes_freed

    # Clean aged prepared-body files under the plan-less sentinel
    if target in (CLEANUP_TARGET_ALL, CLEANUP_TARGET_NO_PLAN_BODIES):
        deleted, bytes_freed = clean_no_plan_bodies(retention['no_plan_body_days'], dry_run)
        stats.no_plan_bodies_deleted = deleted
        stats.no_plan_bodies_bytes = bytes_freed

    # Clean aged build results, skipping every LIVE plan's tree entirely
    if target in (CLEANUP_TARGET_ALL, CLEANUP_TARGET_BUILD_RESULTS):
        deleted, bytes_freed = clean_build_results(retention['build_results_days'], dry_run)
        stats.build_results_deleted = deleted
        stats.build_results_bytes = bytes_freed

    # Output
    status = 'dry_run' if dry_run else 'success'
    total_bytes = (
        stats.temp_bytes
        + stats.logs_bytes
        + stats.archived_plans_bytes
        + stats.no_plan_bodies_bytes
        + stats.build_results_bytes
    )

    return {
        'status': status,
        'target': target,
        'temp_files': stats.temp_files,
        'temp_bytes': stats.temp_bytes,
        'logs_deleted': stats.logs_deleted,
        'logs_bytes': stats.logs_bytes,
        'archived_plans_deleted': stats.archived_plans_deleted,
        'archived_plans_bytes': stats.archived_plans_bytes,
        'no_plan_bodies_deleted': stats.no_plan_bodies_deleted,
        'no_plan_bodies_bytes': stats.no_plan_bodies_bytes,
        'build_results_deleted': stats.build_results_deleted,
        'build_results_bytes': stats.build_results_bytes,
        'total_bytes_freed': total_bytes,
    }


def cmd_status(args: argparse.Namespace) -> dict[str, Any] | None:
    """Show cleanup status."""
    del args  # unused — fixed-shape verb
    status = get_status()
    if status is None:
        return None

    return {
        'status': 'ok',
        'retention_logs_days': status['retention']['logs_days'],
        'retention_archived_plans_days': status['retention']['archived_plans_days'],
        'retention_temp_on_maintenance': status['retention']['temp_on_maintenance'],
        'retention_no_plan_body_days': status['retention']['no_plan_body_days'],
        'retention_build_results_days': status['retention']['build_results_days'],
        'temp_files': status['temp']['files'],
        'temp_bytes': status['temp']['bytes'],
        'logs_total': status['logs']['total'],
        'logs_old': status['logs']['old'],
        'logs_old_bytes': status['logs']['old_bytes'],
        'archived_plans_total': status['archived_plans']['total'],
        'archived_plans_old': status['archived_plans']['old'],
        'archived_plans_old_bytes': status['archived_plans']['old_bytes'],
        'no_plan_bodies_total': status['no_plan_bodies']['total'],
        'no_plan_bodies_old': status['no_plan_bodies']['old'],
        'no_plan_bodies_old_bytes': status['no_plan_bodies']['old_bytes'],
        'build_results_total': status['build_results']['total'],
        'build_results_old': status['build_results']['old'],
        'build_results_old_bytes': status['build_results']['old_bytes'],
    }
