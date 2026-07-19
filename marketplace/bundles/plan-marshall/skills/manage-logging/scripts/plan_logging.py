#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Unified logging module for script execution, work progress, and decision tracking.

Provides:
- Script execution logging (automatic via executor)
- Work progress logging (semantic entries for artifacts, progress, etc.)
- Decision logging (dedicated log for decision entries)

Log file locations:
- Plan-scoped (store='plans'): .plan/local/plans/{plan_id}/logs/{script-execution,work,decision}.log
- Orchestrator-scoped (store='orchestrator'): .plan/local/orchestrator/{slug}/logs/{decision,work}.log
  (main-anchored via get_store_dir, resolving cross-session regardless of caller cwd)
- Global fallback: .plan/logs/{type}-YYYY-MM-DD.log

Configuration via environment variables:
- PLAN_BASE_DIR: Base directory for .plan structure (default: .plan)
- LOG_MAX_OUTPUT: Max chars to capture from stdout/stderr (default: 2000)
- LOG_RETENTION_DAYS: Days to keep global logs (default: 7)
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

from constants import (
    DIR_LOGS,
    DIR_PLANS,
    HASH_ID_LENGTH,
    VALID_LOG_LEVELS,
    VALID_LOG_TYPES,
    VALID_WORK_CATEGORIES,
)
from file_ops import get_base_dir, get_store_dir, now_utc_iso
from input_validation import is_valid_plan_id

# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_ENABLED = True

# Store names accepted by the store-aware logging API. 'plans' is the default
# (existing plan-scoped behavior, byte-identical); 'orchestrator' routes to the
# main-anchored orchestrator tree via file_ops.get_store_dir.
VALID_STORES = ('plans', 'orchestrator')


def get_plan_base_dir() -> Path:
    """Get base directory for plan structure."""
    return get_base_dir()


def get_max_output() -> int:
    """Get max chars to capture from stdout/stderr."""
    return int(os.environ.get('LOG_MAX_OUTPUT', '2000'))


def get_retention_days() -> int:
    """Get days to keep global logs."""
    return int(os.environ.get('LOG_RETENTION_DAYS', '7'))


def get_global_log_dir() -> Path:
    """Get global log directory."""
    return get_plan_base_dir() / DIR_LOGS


def get_plans_dir() -> Path:
    """Get plans directory."""
    return get_plan_base_dir() / DIR_PLANS


# =============================================================================
# UTILITIES
# =============================================================================


def format_timestamp() -> str:
    """Get current time in ISO 8601 UTC format."""
    return now_utc_iso()


def compute_entry_hash(message: str) -> str:
    """Compute 6-digit hash from message content."""
    return hashlib.sha256(message.encode()).hexdigest()[:HASH_ID_LENGTH]


def format_log_entry(level: str, message: str, **fields: Any) -> str:
    """
    Format a standard log entry with auto-generated hash.

    Args:
        level: Log level (INFO, WARNING, ERROR)
        message: Primary message
        **fields: Additional fields to include as indented lines

    Returns:
        Formatted log entry: [{timestamp}] [{level}] [{hash}] {message}
    """
    timestamp = format_timestamp()
    hash_id = compute_entry_hash(message)
    lines = [f'[{timestamp}] [{level}] [{hash_id}] {message}']

    for key, value in fields.items():
        if value is not None and value != '':
            lines.append(f'  {key}: {value}')

    return '\n'.join(lines) + '\n'


def extract_plan_id(args: list[str]) -> str | None:
    """Extract --plan-id value from argument list."""
    for i, arg in enumerate(args):
        if arg == '--plan-id' and i + 1 < len(args):
            plan_id: str = args[i + 1]
            return plan_id
        if arg.startswith('--plan-id='):
            plan_id_value: str = arg.split('=', 1)[1]
            return plan_id_value
    return None


# =============================================================================
# PATH RESOLUTION
# =============================================================================


def get_log_path(plan_id: str | None, log_type: str = 'script', store: str = 'plans') -> Path:
    """
    Get path to log file.

    Log-directory resolution routes through file_ops.get_store_dir — the one
    parameterized store-root mechanism. ``store='plans'`` (default) preserves
    the existing plan-scoped behavior byte-identically; ``store='orchestrator'``
    resolves the main-anchored orchestrator tree
    (``.plan/local/orchestrator/{entry_id}/logs/``) regardless of caller cwd,
    transparently falling back to the archived tree for a closed-and-relocated
    epic (see the inline rationale at the resolution call below).

    Args:
        plan_id: Entry identifier — a plan id (store='plans') or an epic slug
            (store='orchestrator'). None for global.
        log_type: 'script', 'work', or 'decision'
        store: Store name — 'plans' (default) or 'orchestrator'

    Returns:
        Path to log file in logs/ subdirectory

    Raises:
        ValueError: when ``store`` is not one of :data:`VALID_STORES`. The guard
            closes the silent fall-through where any string other than
            ``'orchestrator'`` slipped past to the plans/global branch.
    """
    if store not in VALID_STORES:
        raise ValueError(
            f'unknown store {store!r}: expected one of {list(VALID_STORES)}'
        )

    log_type = log_type.lower()

    # Map log type to filename
    if log_type == 'work':
        filename = 'work.log'
    elif log_type == 'decision':
        filename = 'decision.log'
    else:
        filename = 'script-execution.log'

    if plan_id and store == 'orchestrator':
        # Orchestrator entries have no status.json sentinel contract — the
        # slug tree is scaffolded by marshall-orchestrator before logging, and
        # the store is main-anchored, so no plans-style orphan-slot hazard.
        #
        # Resolve with allow_archived=True: appending an audit-trail log entry
        # is a continuation of the record, NOT a status.json business-state
        # mutation, so it follows the same read-fallback transparency the
        # manage-status READ verbs use for an archived epic — never a strict
        # write-refusal. Without the fallback, a decision/work write against an
        # archived-only epic would scaffold an EMPTY active orchestrator/{slug}/
        # tree, and that resurrected active dir makes a repeated `archive`
        # request's source.exists() probe misreport the epic as not-yet-archived
        # (falling into not_closed instead of the idempotent already_archived
        # path). The fallback resolves the archived logs/ tree when only it
        # exists, the active tree when both exist (active wins), and names the
        # active tree when neither exists (brand-new epic before scaffold).
        return get_store_dir('orchestrator', plan_id, allow_archived=True) / 'logs' / filename

    if plan_id:
        plan_dir = get_store_dir('plans', plan_id)
        # Treat the slot as plan-scoped ONLY when it is an INITIALIZED plan dir:
        # the directory exists AND carries the status.json sentinel. A bare
        # existence test would extend a status.json-less orphan slot (e.g. a
        # metrics-created work/ half that mis-resolved to main while the
        # authoritative plan dir is worktree-resident). The inline sentinel check
        # keeps logging non-raising and silent-fallback — it never errors a caller.
        if (plan_dir / 'status.json').is_file():
            # Plan-scoped logs go in logs/ subdirectory
            return plan_dir / 'logs' / filename

    # Global fallback with date suffix
    global_log_dir = get_global_log_dir()
    global_log_dir.mkdir(parents=True, exist_ok=True)

    if log_type == 'work':
        return global_log_dir / f'work-{date.today()}.log'
    elif log_type == 'decision':
        return global_log_dir / f'decision-{date.today()}.log'

    return global_log_dir / f'script-execution-{date.today()}.log'


# =============================================================================
# UNIFIED LOG ENTRY (SIMPLIFIED API)
# =============================================================================

VALID_TYPES = VALID_LOG_TYPES
VALID_LEVELS = VALID_LOG_LEVELS


def log_entry(log_type: str, plan_id: str | None, level: str, message: str, store: str = 'plans') -> None:
    """
    Write log entry to appropriate log file.

    Args:
        log_type: 'script' or 'work'
        plan_id: Plan identifier, or None for no plan context (global fallback)
        level: INFO, WARNING, ERROR
        message: Log message
        store: Store name — 'plans' (default) or 'orchestrator'
    """
    if not LOG_ENABLED:
        return

    log_type_lower = log_type.lower()
    level = level.upper()

    try:
        log_file = get_log_path(plan_id, log_type_lower, store=store)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        entry = format_log_entry(level, message)

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

    except Exception:  # noqa: BLE001 — logging is best-effort, never raises into a caller
        pass  # Silent failure for logging


# =============================================================================
# SCRIPT EXECUTION LOGGING
# =============================================================================


def log_script_execution(
    notation: str, subcommand: str, args: list, exit_code: int, duration: float, stdout: str = '', stderr: str = ''
) -> None:
    """
    Log script execution to script-execution.log.

    Args:
        notation: Script notation (bundle:skill:script)
        subcommand: Script subcommand
        args: Full argument list
        exit_code: Process exit code
        duration: Execution time in seconds
        stdout: Captured stdout
        stderr: Captured stderr
    """
    if not LOG_ENABLED:
        return

    try:
        plan_id = extract_plan_id(args)
        log_file = get_log_path(plan_id, 'script')

        message = f'{notation} {subcommand} ({duration:.2f}s)'

        if exit_code == 0:
            entry = format_log_entry('INFO', message)
        else:
            max_output = get_max_output()
            entry = format_log_entry(
                'ERROR',
                message,
                exit_code=exit_code,
                args=' '.join(args),
                stdout=stdout[:max_output].replace('\n', ' ')[:500] if stdout else None,
                stderr=stderr[:max_output].replace('\n', ' ')[:500] if stderr else None,
            )

        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

    except Exception:  # noqa: BLE001 — logging is best-effort, never raises into a caller
        pass  # Silent failure for logging


def cleanup_old_script_logs(max_age_days: int | None = None) -> int:
    """
    Delete global script logs older than max_age_days.

    Args:
        max_age_days: Days to keep (default from LOG_RETENTION_DAYS)

    Returns:
        Count of deleted files
    """
    if max_age_days is None:
        max_age_days = get_retention_days()

    deleted = 0
    cutoff = time.time() - (max_age_days * 86400)

    global_log_dir = get_global_log_dir()
    if not global_log_dir.exists():
        return 0

    for log_file in global_log_dir.glob('script-execution-*.log'):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                deleted += 1
        except OSError:
            pass

    return deleted


# =============================================================================
# WORK LOGGING
# =============================================================================

VALID_CATEGORIES = VALID_WORK_CATEGORIES


def log_work(plan_id: str, category: str, message: str, phase: str, detail: str | None = None) -> dict[str, Any]:
    """
    Add entry to work.log.

    Args:
        plan_id: Plan identifier (kebab-case)
        category: Entry category (ARTIFACT, PROGRESS, ERROR, OUTCOME, FINDING)
        message: Summary text
        phase: Current workflow phase
        detail: Additional context (optional)

    Returns:
        Result dict with status and entry info

    Note:
        For decision logging, use log_decision() instead which writes to decision.log.
    """
    if not is_valid_plan_id(plan_id):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }

    category = category.upper()
    if category not in VALID_CATEGORIES:
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_category',
            'message': f"Invalid category '{category}'. Valid: {', '.join(VALID_CATEGORIES)}",
        }

    try:
        log_file = get_log_path(plan_id, 'work')
        log_file.parent.mkdir(parents=True, exist_ok=True)

        level = 'ERROR' if category == 'ERROR' else 'INFO'
        # Include category in message for work logs (DECISION, ARTIFACT, etc.)
        formatted_message = f'[{category}] {message}'
        entry = format_log_entry(level, formatted_message, phase=phase, detail=detail)

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

        # Count entries
        total_entries = _count_entries(log_file)

        result = {
            'status': 'success',
            'plan_id': plan_id,
            'category': category,
            'phase': phase,
            'timestamp': format_timestamp(),
            'message': message,
            'total_entries': total_entries,
        }
        if detail:
            result['detail'] = detail

        return result

    except OSError as e:
        return {'status': 'error', 'plan_id': plan_id, 'error': 'write_failed', 'message': str(e)}


def read_work_log(plan_id: str, phase: str | None = None, store: str = 'plans') -> dict[str, Any]:
    """
    Read work log entries.

    Args:
        plan_id: Plan identifier
        phase: Filter by phase (optional)
        store: Store name — 'plans' (default) or 'orchestrator'

    Returns:
        Result dict with entries
    """
    if not is_valid_plan_id(plan_id):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }

    try:
        log_file = get_log_path(plan_id, 'work', store=store)

        if not log_file.exists():
            return {'status': 'success', 'plan_id': plan_id, 'total_entries': 0, 'entries': []}

        entries = _parse_log_file(log_file)

        # Filter by phase if specified
        if phase:
            entries = [e for e in entries if e.get('phase') == phase]

        return {'status': 'success', 'plan_id': plan_id, 'total_entries': len(entries), 'entries': entries}

    except OSError as e:
        return {'status': 'error', 'plan_id': plan_id, 'error': 'read_failed', 'message': str(e)}


def list_recent_work(plan_id: str, limit: int = 10, store: str = 'plans') -> dict[str, Any]:
    """
    List most recent work log entries.

    Args:
        plan_id: Plan identifier
        limit: Maximum entries to return
        store: Store name — 'plans' (default) or 'orchestrator'

    Returns:
        Result dict with entries
    """
    result = read_work_log(plan_id, store=store)

    if result['status'] != 'success':
        return result

    total = result['total_entries']
    entries = result['entries'][-limit:]  # Get most recent

    return {
        'status': 'success',
        'plan_id': plan_id,
        'total_entries': total,
        'showing': len(entries),
        'entries': entries,
    }


# =============================================================================
# DECISION LOGGING
# =============================================================================


def log_separator(log_type: str, plan_id: str, store: str = 'plans') -> None:
    """
    Append a blank line to the specified log file for visual separation.

    Args:
        log_type: 'work' or 'decision'
        plan_id: Plan identifier
        store: Store name — 'plans' (default) or 'orchestrator'
    """
    try:
        log_file = get_log_path(plan_id, log_type, store=store)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('\n')

    except Exception:  # noqa: BLE001 — logging is best-effort, never raises into a caller
        pass  # Silent failure for logging


def log_decision(plan_id: str, message: str, phase: str, detail: str | None = None) -> dict[str, Any]:
    """
    Add entry to decision.log.

    Args:
        plan_id: Plan identifier (kebab-case)
        message: Decision message (should NOT include [DECISION] prefix)
        phase: Current workflow phase
        detail: Additional context (optional)

    Returns:
        Result dict with status and entry info
    """
    if not is_valid_plan_id(plan_id):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }

    try:
        log_file = get_log_path(plan_id, 'decision')
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Decision entries use INFO level, no category prefix (file is the category)
        entry = format_log_entry('INFO', message, phase=phase, detail=detail)

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

        # Count entries
        total_entries = _count_entries(log_file)

        result = {
            'status': 'success',
            'plan_id': plan_id,
            'log_type': 'decision',
            'phase': phase,
            'timestamp': format_timestamp(),
            'message': message,
            'total_entries': total_entries,
        }
        if detail:
            result['detail'] = detail

        return result

    except OSError as e:
        return {'status': 'error', 'plan_id': plan_id, 'error': 'write_failed', 'message': str(e)}


def read_decision_log(plan_id: str, phase: str | None = None, store: str = 'plans') -> dict[str, Any]:
    """
    Read decision log entries.

    Args:
        plan_id: Plan identifier
        phase: Filter by phase (optional)
        store: Store name — 'plans' (default) or 'orchestrator'

    Returns:
        Result dict with entries
    """
    if not is_valid_plan_id(plan_id):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }

    try:
        log_file = get_log_path(plan_id, 'decision', store=store)

        if not log_file.exists():
            return {'status': 'success', 'plan_id': plan_id, 'total_entries': 0, 'entries': []}

        entries = _parse_log_file(log_file)

        # Filter by phase if specified
        if phase:
            entries = [e for e in entries if e.get('phase') == phase]

        return {'status': 'success', 'plan_id': plan_id, 'total_entries': len(entries), 'entries': entries}

    except OSError as e:
        return {'status': 'error', 'plan_id': plan_id, 'error': 'read_failed', 'message': str(e)}


# =============================================================================
# PARSING HELPERS
# =============================================================================

# New format: [timestamp] [level] [hash] message
# Hash is always present as 6 hex chars
HEADER_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] '
    r'\[(\w+)\] '
    r'\[([a-f0-9]{6})\] '
    r'(.+)$',
    re.MULTILINE,
)
FIELD_PATTERN = re.compile(r'^  (\w+): (.+)$', re.MULTILINE)


def _parse_log_file(log_file: Path) -> list[dict[str, str]]:
    """Parse log file into list of entry dicts."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    content = log_file.read_text(encoding='utf-8')
    for line in content.split('\n'):
        header_match = HEADER_PATTERN.match(line)
        if header_match:
            if current:
                entries.append(current)
            current = {
                'timestamp': header_match.group(1),
                'level': header_match.group(2),
                'hash_id': header_match.group(3),
                'message': header_match.group(4),
            }
        elif current:
            field_match = FIELD_PATTERN.match(line)
            if field_match:
                current[field_match.group(1)] = field_match.group(2)

    if current:
        entries.append(current)

    return entries


def _count_entries(log_file: Path) -> int:
    """Count entries in log file."""
    if not log_file.exists():
        return 0
    content = log_file.read_text(encoding='utf-8')
    return len(HEADER_PATTERN.findall(content))


# =============================================================================
# MODULE SELF-TEST
# =============================================================================

if __name__ == '__main__':
    print('plan_logging.py - Unified Logging Module')
    print('=' * 50)
    print(f'\nPlan Base Directory: {get_plan_base_dir()}')
    print(f'Max Output Capture: {get_max_output()}')
    print(f'Retention Days: {get_retention_days()}')
    print('\nLog locations (plan-scoped, store=plans):')
    print('  .plan/local/plans/{plan_id}/logs/script-execution.log')
    print('  .plan/local/plans/{plan_id}/logs/work.log')
    print('  .plan/local/plans/{plan_id}/logs/decision.log')
    print('\nLog locations (orchestrator-scoped, store=orchestrator):')
    print('  .plan/local/orchestrator/{slug}/logs/work.log')
    print('  .plan/local/orchestrator/{slug}/logs/decision.log')
    print('\nAvailable functions:')
    print('- format_timestamp() -> str')
    print('- format_log_entry(level, message, **fields) -> str')
    print('- extract_plan_id(args) -> str | None')
    print('- get_log_path(plan_id, log_type) -> Path')
    print('- log_script_execution(...)')
    print('- cleanup_old_script_logs(max_age_days) -> int')
    print('- log_work(plan_id, category, message, phase, detail) -> dict')
    print('- read_work_log(plan_id, phase) -> dict')
    print('- list_recent_work(plan_id, limit) -> dict')
    print('- log_decision(plan_id, message, phase, detail) -> dict')
    print('- read_decision_log(plan_id, phase) -> dict')
