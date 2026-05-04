"""Cleanup command handlers for manage-run-config.

Handles: cleanup, cleanup-status

Reads retention settings directly from marshal.json rather than
calling manage-config via subprocess — intentional optimization
to avoid process overhead for a frequently-called internal module.
"""

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

# Direct imports - PYTHONPATH set by executor
from constants import DIR_ARCHIVED, DIR_LOGS  # type: ignore[import-not-found]
from file_ops import (  # type: ignore[import-not-found]
    get_base_dir,
    get_marshal_path,
    get_temp_dir,
    output_toon,
)

# Configuration — delegate to file_ops for consistent path resolution.
# PLAN_BASE_DIR holds runtime state (logs/, archived-plans/) in
# the per-project global plan-marshall directory. temp/ stays project-local
# under the tracked config dir (.plan/), and marshal.json is also tracked.
PLAN_BASE_DIR = get_base_dir()
MARSHAL_JSON = get_marshal_path()
TEMP_DIR = get_temp_dir()


@dataclass
class CleanupStats:
    """Statistics from cleanup operations."""

    temp_files: int = 0
    temp_bytes: int = 0
    logs_deleted: int = 0
    logs_bytes: int = 0
    archived_plans_deleted: int = 0
    archived_plans_bytes: int = 0


def get_retention_settings() -> dict | None:
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

    retention: dict = config['system']['retention']
    return retention


def get_path_age_days(path: Path) -> float:
    """Get age of a file or directory in days based on modification time."""
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) / 86400
    except OSError:
        return 0


# Aliases for backward compatibility
get_dir_age_days = get_path_age_days
get_file_age_days = get_path_age_days


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
        if get_file_age_days(log_file) > max_age_days:
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

        if get_dir_age_days(plan_dir) > max_age_days:
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


def get_status() -> dict | None:
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
            if get_file_age_days(f) > retention['logs_days']:
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
                if get_dir_age_days(d) > retention['archived_plans_days']:
                    archived_old += 1
                    try:
                        for f in d.rglob('*'):
                            if f.is_file():
                                archived_old_bytes += f.stat().st_size
                    except OSError:
                        pass

    return {
        'retention': retention,
        'temp': {'files': temp_files, 'bytes': temp_bytes},
        'logs': {'total': logs_total, 'old': logs_old, 'old_bytes': logs_old_bytes},
        'archived_plans': {'total': archived_total, 'old': archived_old, 'old_bytes': archived_old_bytes},
    }


def cmd_clean(args) -> dict | None:
    """Execute cleanup based on retention settings."""
    retention = get_retention_settings()
    if retention is None:
        return None
    target = args.target
    dry_run = args.dry_run

    stats = CleanupStats()

    # Clean temp
    if target in ('all', 'temp') and retention.get('temp_on_maintenance', True):
        files, bytes_freed = clean_temp(dry_run)
        stats.temp_files = files
        stats.temp_bytes = bytes_freed

    # Clean logs
    if target in ('all', 'logs'):
        deleted, bytes_freed = clean_logs(retention['logs_days'], dry_run)
        stats.logs_deleted = deleted
        stats.logs_bytes = bytes_freed

    # Clean archived plans
    if target in ('all', 'archived-plans'):
        deleted, bytes_freed = clean_archived_plans(retention['archived_plans_days'], dry_run)
        stats.archived_plans_deleted = deleted
        stats.archived_plans_bytes = bytes_freed

    # Output
    status = 'dry_run' if dry_run else 'success'
    total_bytes = stats.temp_bytes + stats.logs_bytes + stats.archived_plans_bytes

    return {
        'status': status,
        'target': target,
        'temp_files': stats.temp_files,
        'temp_bytes': stats.temp_bytes,
        'logs_deleted': stats.logs_deleted,
        'logs_bytes': stats.logs_bytes,
        'archived_plans_deleted': stats.archived_plans_deleted,
        'archived_plans_bytes': stats.archived_plans_bytes,
        'total_bytes_freed': total_bytes,
    }


def cmd_status(args) -> dict | None:
    """Show cleanup status."""
    status = get_status()
    if status is None:
        return None

    return {
        'status': 'ok',
        'retention_logs_days': status['retention']['logs_days'],
        'retention_archived_plans_days': status['retention']['archived_plans_days'],
        'retention_temp_on_maintenance': status['retention']['temp_on_maintenance'],
        'temp_files': status['temp']['files'],
        'temp_bytes': status['temp']['bytes'],
        'logs_total': status['logs']['total'],
        'logs_old': status['logs']['old'],
        'logs_old_bytes': status['logs']['old_bytes'],
        'archived_plans_total': status['archived_plans']['total'],
        'archived_plans_old': status['archived_plans']['old'],
        'archived_plans_old_bytes': status['archived_plans']['old_bytes'],
    }
