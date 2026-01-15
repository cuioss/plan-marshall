#!/usr/bin/env python3
"""
Cleanup .plan directory based on retention settings from marshal.json.

Consolidates cleanup for temp, logs, archived-plans, and memory directories.

Usage:
    python3 cleanup-plan-directory.py clean [--dry-run] [--target TARGET]
    python3 cleanup-plan-directory.py status

Subcommands:
    clean     Clean directories based on retention settings
    status    Show cleanup status and what would be cleaned

Options:
    --dry-run          Show what would be deleted without deleting
    --target TARGET    Clean specific target only (temp|logs|archived-plans|memory|all)

Retention settings (from marshal.json):
    logs_days: 1              # Delete logs older than N days
    archived_plans_days: 5    # Delete archived plans older than N days
    memory_days: 5            # Delete memory files older than N days
    temp_on_maintenance: true # Clean temp directory on maintenance

Output (TOON format):
    status	success
    temp_files	5
    temp_bytes	1024
    logs_deleted	3
    archived_plans_deleted	2
    memory_files_deleted	10
"""

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Direct import - PYTHONPATH set by executor
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# Configuration
PLAN_BASE_DIR = Path(os.environ.get('PLAN_BASE_DIR', '.plan'))
MARSHAL_JSON = PLAN_BASE_DIR / 'marshal.json'


@dataclass
class CleanupStats:
    """Statistics from cleanup operations."""

    temp_files: int = 0
    temp_bytes: int = 0
    logs_deleted: int = 0
    logs_bytes: int = 0
    archived_plans_deleted: int = 0
    archived_plans_bytes: int = 0
    memory_files_deleted: int = 0
    memory_bytes: int = 0


def get_retention_settings() -> dict:
    """
    Get retention settings from marshal.json.

    Returns:
        dict with retention settings

    Raises:
        SystemExit: If marshal.json doesn't exist or has no retention config
    """
    if not MARSHAL_JSON.exists():
        print(
            serialize_toon({'status': 'error', 'error': 'marshal.json not found. Run command /marshall-steward first'})
        )
        sys.exit(1)

    try:
        config = json.loads(MARSHAL_JSON.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(serialize_toon({'status': 'error', 'error': f'Invalid marshal.json: {e}'}))
        sys.exit(1)

    if 'system' not in config or 'retention' not in config['system']:
        print(
            serialize_toon(
                {'status': 'error', 'error': 'system.retention not configured. Run command /marshall-steward first'}
            )
        )
        sys.exit(1)

    retention: dict = config['system']['retention']
    return retention


def get_dir_age_days(path: Path) -> float:
    """Get age of directory in days based on modification time."""
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) / 86400
    except OSError:
        return 0


def get_file_age_days(path: Path) -> float:
    """Get age of file in days based on modification time."""
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
    temp_dir = PLAN_BASE_DIR / 'temp'
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
    logs_dir = PLAN_BASE_DIR / 'logs'
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
    archived_dir = PLAN_BASE_DIR / 'archived-plans'
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


def clean_memory(max_age_days: int, dry_run: bool = False) -> tuple[int, int]:
    """
    Clean old memory files from .plan/memory.

    Returns:
        (files_deleted, bytes_freed)
    """
    memory_dir = PLAN_BASE_DIR / 'memory'
    if not memory_dir.exists():
        return 0, 0

    deleted = 0
    total_bytes = 0

    # Clean all files recursively (handoffs, etc.)
    for item in memory_dir.rglob('*'):
        if not item.is_file():
            continue

        if get_file_age_days(item) > max_age_days:
            try:
                size = item.stat().st_size
                if not dry_run:
                    item.unlink()
                deleted += 1
                total_bytes += size
            except OSError:
                pass

    # Clean empty subdirectories
    if not dry_run:
        for subdir in memory_dir.iterdir():
            if subdir.is_dir():
                try:
                    # Only remove if empty
                    if not any(subdir.iterdir()):
                        subdir.rmdir()
                except OSError:
                    pass

    return deleted, total_bytes


def get_status() -> dict:
    """
    Get status of all cleanable directories.

    Returns:
        dict with counts and sizes for each target
    """
    retention = get_retention_settings()

    # Temp stats
    temp_dir = PLAN_BASE_DIR / 'temp'
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
    logs_dir = PLAN_BASE_DIR / 'logs'
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
    archived_dir = PLAN_BASE_DIR / 'archived-plans'
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

    # Memory stats
    memory_dir = PLAN_BASE_DIR / 'memory'
    memory_total = 0
    memory_old = 0
    memory_old_bytes = 0
    if memory_dir.exists():
        for f in memory_dir.rglob('*'):
            if f.is_file():
                memory_total += 1
                if get_file_age_days(f) > retention['memory_days']:
                    memory_old += 1
                    try:
                        memory_old_bytes += f.stat().st_size
                    except OSError:
                        pass

    return {
        'retention': retention,
        'temp': {'files': temp_files, 'bytes': temp_bytes},
        'logs': {'total': logs_total, 'old': logs_old, 'old_bytes': logs_old_bytes},
        'archived_plans': {'total': archived_total, 'old': archived_old, 'old_bytes': archived_old_bytes},
        'memory': {'total': memory_total, 'old': memory_old, 'old_bytes': memory_old_bytes},
    }


def cmd_clean(args) -> int:
    """Execute cleanup based on retention settings."""
    retention = get_retention_settings()
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

    # Clean memory
    if target in ('all', 'memory'):
        deleted, bytes_freed = clean_memory(retention['memory_days'], dry_run)
        stats.memory_files_deleted = deleted
        stats.memory_bytes = bytes_freed

    # Output
    status = 'dry_run' if dry_run else 'success'
    total_bytes = stats.temp_bytes + stats.logs_bytes + stats.archived_plans_bytes + stats.memory_bytes

    result = {
        'status': status,
        'target': target,
        'temp_files': stats.temp_files,
        'temp_bytes': stats.temp_bytes,
        'logs_deleted': stats.logs_deleted,
        'logs_bytes': stats.logs_bytes,
        'archived_plans_deleted': stats.archived_plans_deleted,
        'archived_plans_bytes': stats.archived_plans_bytes,
        'memory_files_deleted': stats.memory_files_deleted,
        'memory_bytes': stats.memory_bytes,
        'total_bytes_freed': total_bytes,
    }

    print(serialize_toon(result))
    return 0


def cmd_status(args) -> int:
    """Show cleanup status."""
    status = get_status()

    result = {
        'status': 'ok',
        'retention_logs_days': status['retention']['logs_days'],
        'retention_archived_plans_days': status['retention']['archived_plans_days'],
        'retention_memory_days': status['retention']['memory_days'],
        'retention_temp_on_maintenance': status['retention']['temp_on_maintenance'],
        'temp_files': status['temp']['files'],
        'temp_bytes': status['temp']['bytes'],
        'logs_total': status['logs']['total'],
        'logs_old': status['logs']['old'],
        'logs_old_bytes': status['logs']['old_bytes'],
        'archived_plans_total': status['archived_plans']['total'],
        'archived_plans_old': status['archived_plans']['old'],
        'archived_plans_old_bytes': status['archived_plans']['old_bytes'],
        'memory_total': status['memory']['total'],
        'memory_old': status['memory']['old'],
        'memory_old_bytes': status['memory']['old_bytes'],
    }

    print(serialize_toon(result))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Cleanup .plan directory based on retention settings')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # clean subcommand
    clean_parser = subparsers.add_parser('clean', help='Clean directories based on retention')
    clean_parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    clean_parser.add_argument(
        '--target',
        choices=['all', 'temp', 'logs', 'archived-plans', 'memory'],
        default='all',
        help='Clean specific target only (default: all)',
    )
    clean_parser.set_defaults(func=cmd_clean)

    # status subcommand
    status_parser = subparsers.add_parser('status', help='Show cleanup status')
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()
    func_result: int = args.func(args)
    return func_result


if __name__ == '__main__':
    sys.exit(main())
