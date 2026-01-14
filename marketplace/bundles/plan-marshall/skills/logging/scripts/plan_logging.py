#!/usr/bin/env python3
"""
Unified logging module for script execution and work progress tracking.

Provides:
- Script execution logging (automatic via executor)
- Work progress logging (semantic entries for decisions, artifacts, etc.)

Configuration via environment variables:
- PLAN_BASE_DIR: Base directory for .plan structure (default: .plan)
- LOG_MAX_OUTPUT: Max chars to capture from stdout/stderr (default: 2000)
- LOG_RETENTION_DAYS: Days to keep global logs (default: 7)
"""

import os
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

LOG_ENABLED = True


def get_plan_base_dir() -> Path:
    """Get base directory for plan structure."""
    return Path(os.environ.get('PLAN_BASE_DIR', '.plan'))


def get_max_output() -> int:
    """Get max chars to capture from stdout/stderr."""
    return int(os.environ.get('LOG_MAX_OUTPUT', '2000'))


def get_retention_days() -> int:
    """Get days to keep global logs."""
    return int(os.environ.get('LOG_RETENTION_DAYS', '7'))


def get_global_log_dir() -> Path:
    """Get global log directory."""
    return get_plan_base_dir() / 'logs'


def get_plans_dir() -> Path:
    """Get plans directory."""
    return get_plan_base_dir() / 'plans'


# =============================================================================
# UTILITIES
# =============================================================================


def format_timestamp() -> str:
    """Get current time in ISO 8601 UTC format."""
    return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def format_log_entry(level: str, message: str, **fields) -> str:
    """
    Format a standard log entry.

    Args:
        level: Log level (INFO, WARN, ERROR)
        message: Primary message
        **fields: Additional fields to include as indented lines

    Returns:
        Formatted log entry string with trailing newline
    """
    timestamp = format_timestamp()
    lines = [f'[{timestamp}] [{level}] {message}']

    for key, value in fields.items():
        if value is not None and value != '':
            lines.append(f'  {key}: {value}')

    return '\n'.join(lines) + '\n'


def extract_plan_id(args: list) -> str | None:
    """Extract --plan-id value from argument list."""
    for i, arg in enumerate(args):
        if arg == '--plan-id' and i + 1 < len(args):
            plan_id: str = args[i + 1]
            return plan_id
        if arg.startswith('--plan-id='):
            plan_id_value: str = arg.split('=', 1)[1]
            return plan_id_value
    return None


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan_id is kebab-case with no special characters."""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', plan_id))


# =============================================================================
# PATH RESOLUTION
# =============================================================================


def get_log_path(plan_id: str | None, log_type: str = 'script') -> Path:
    """
    Get path to log file.

    Args:
        plan_id: Plan identifier (None for global)
        log_type: 'script' or 'work'

    Returns:
        Path to log file (script-execution.log or work.log)
    """
    log_type = log_type.lower()
    filename = 'work.log' if log_type == 'work' else 'script-execution.log'

    if plan_id:
        plan_dir = get_plans_dir() / plan_id
        if plan_dir.exists():
            return plan_dir / filename

    # Global fallback for both script and work logs
    global_log_dir = get_global_log_dir()
    global_log_dir.mkdir(parents=True, exist_ok=True)

    if log_type == 'work':
        return global_log_dir / f'work-{date.today()}.log'

    return global_log_dir / f'script-execution-{date.today()}.log'


# =============================================================================
# UNIFIED LOG ENTRY (SIMPLIFIED API)
# =============================================================================

VALID_TYPES = ('script', 'work')
VALID_LEVELS = ('INFO', 'WARN', 'ERROR')


def log_entry(log_type: str, plan_id: str, level: str, message: str) -> None:
    """
    Write log entry to appropriate log file.

    Args:
        log_type: 'script' or 'work'
        plan_id: Plan identifier
        level: INFO, WARN, ERROR
        message: Log message
    """
    if not LOG_ENABLED:
        return

    log_type_lower = log_type.lower()
    level = level.upper()

    try:
        log_file = get_log_path(plan_id, log_type_lower)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        entry = format_log_entry(level, message)

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

    except Exception:
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

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

    except Exception:
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
        except Exception:
            pass

    return deleted


# =============================================================================
# WORK LOGGING
# =============================================================================

VALID_CATEGORIES = ['DECISION', 'ARTIFACT', 'PROGRESS', 'ERROR', 'OUTCOME', 'FINDING']


def log_work(plan_id: str, category: str, message: str, phase: str, detail: str | None = None) -> dict:
    """
    Add entry to work.log.

    Args:
        plan_id: Plan identifier (kebab-case)
        category: Entry category (DECISION, ARTIFACT, PROGRESS, ERROR, OUTCOME, FINDING)
        message: Summary text
        phase: Current workflow phase
        detail: Additional context (optional)

    Returns:
        Result dict with status and entry info
    """
    if not validate_plan_id(plan_id):
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

    except Exception as e:
        return {'status': 'error', 'plan_id': plan_id, 'error': 'write_failed', 'message': str(e)}


def read_work_log(plan_id: str, phase: str | None = None) -> dict:
    """
    Read work log entries.

    Args:
        plan_id: Plan identifier
        phase: Filter by phase (optional)

    Returns:
        Result dict with entries
    """
    if not validate_plan_id(plan_id):
        return {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'invalid_plan_id',
            'message': f'Invalid plan_id format: {plan_id}',
        }

    try:
        log_file = get_log_path(plan_id, 'work')

        if not log_file.exists():
            return {'status': 'success', 'plan_id': plan_id, 'total_entries': 0, 'entries': []}

        entries = _parse_log_file(log_file)

        # Filter by phase if specified
        if phase:
            entries = [e for e in entries if e.get('phase') == phase]

        return {'status': 'success', 'plan_id': plan_id, 'total_entries': len(entries), 'entries': entries}

    except Exception as e:
        return {'status': 'error', 'plan_id': plan_id, 'error': 'read_failed', 'message': str(e)}


def list_recent_work(plan_id: str, limit: int = 10) -> dict:
    """
    List most recent work log entries.

    Args:
        plan_id: Plan identifier
        limit: Maximum entries to return

    Returns:
        Result dict with entries
    """
    result = read_work_log(plan_id)

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
# PARSING HELPERS
# =============================================================================

# Matches both old format [timestamp] [level] [category] message
# and new format [timestamp] [level] message (with optional [CATEGORY] in message)
HEADER_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] '
    r'\[(\w+)\] (?:\[(\w+)\] )?(.+)$',
    re.MULTILINE,
)
FIELD_PATTERN = re.compile(r'^  (\w+): (.+)$', re.MULTILINE)


def _parse_log_file(log_file: Path) -> list:
    """Parse log file into list of entry dicts."""
    entries = []
    current = None

    content = log_file.read_text(encoding='utf-8')
    for line in content.split('\n'):
        header_match = HEADER_PATTERN.match(line)
        if header_match:
            if current:
                entries.append(current)
            current = {
                'timestamp': header_match.group(1),
                'level': header_match.group(2),
                'category': header_match.group(3),
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
    print('\nAvailable functions:')
    print('- format_timestamp() -> str')
    print('- format_log_entry(level, category, message, **fields) -> str')
    print('- extract_plan_id(args) -> str | None')
    print('- get_log_path(plan_id, log_type) -> Path')
    print('- log_script_execution(...)')
    print('- cleanup_old_script_logs(max_age_days) -> int')
    print('- log_work(plan_id, category, message, phase, detail) -> dict')
    print('- read_work_log(plan_id, phase) -> dict')
    print('- list_recent_work(plan_id, limit) -> dict')
