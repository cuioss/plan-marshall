#!/usr/bin/env python3
"""
Shared helpers for workflow scripts (pr.py, sonar.py, git-workflow.py).

Provides:
- Triage command handlers (single-item and batch) for JSON→TOON workflows
- safe_main wrapper for consistent error handling across all workflow scripts
- Error code taxonomy for cross-skill error propagation
- Priority calculation utility for severity/boost workflows

Usage:
    from triage_helpers import cmd_triage_single, cmd_triage_batch_handler, safe_main
    from triage_helpers import ErrorCode, make_error, calculate_priority
"""

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]


# ============================================================================
# ERROR CODE TAXONOMY
# ============================================================================


class ErrorCode:
    """Standardized error codes for cross-skill error propagation.

    Used by workflow skills (pr-doctor, integration-ci, integration-sonar,
    integration-git) to enable consistent error routing across orchestration
    layers without string matching on error messages.
    """

    PROVIDER_NOT_CONFIGURED = 'PROVIDER_NOT_CONFIGURED'
    MCP_UNAVAILABLE = 'MCP_UNAVAILABLE'
    TIMEOUT = 'TIMEOUT'
    INVALID_INPUT = 'INVALID_INPUT'
    NOT_FOUND = 'NOT_FOUND'
    AUTH_FAILURE = 'AUTH_FAILURE'
    BUILD_FAILURE = 'BUILD_FAILURE'
    PARSE_ERROR = 'PARSE_ERROR'


def make_error(message: str, *, code: str | None = None, **extra: Any) -> dict[str, Any]:
    """Create a standardized error payload for TOON output.

    All workflow scripts should use this for error responses to ensure
    a consistent contract: ``{'error': message, 'status': 'failure', ...}``.

    Args:
        message: Human-readable error description.
        code: Optional error code from ``ErrorCode`` for programmatic routing.
        **extra: Additional context fields (e.g., file, category).

    Returns:
        Dict ready for ``serialize_toon()``.
    """
    result: dict[str, Any] = {'error': message, 'status': 'failure'}
    if code:
        result['error_code'] = code
    result.update(extra)
    return result


def safe_main(main_fn: Callable[[], int]) -> int:
    """Wrap a script's main() to catch unhandled exceptions and emit TOON failure.

    Ensures all workflow scripts produce structured TOON output even on
    unexpected errors, instead of raw tracebacks.

    Usage::

        if __name__ == '__main__':
            sys.exit(safe_main(main))
    """
    try:
        return main_fn()
    except SystemExit as e:
        # Let argparse --help / missing-arg exits pass through
        raise e
    except Exception as e:
        print(serialize_toon(make_error(f'Unexpected error: {e}')))
        return 1


# ============================================================================
# JSON ARGUMENT PARSING
# ============================================================================


def parse_json_arg(raw: str, field_name: str) -> tuple[Any, int]:
    """Parse a JSON string from a CLI argument.

    Eliminates the duplicated try/except json.loads pattern across workflow
    scripts (pr_doctor.py, permission_web.py, etc.).

    Args:
        raw: Raw JSON string from argparse.
        field_name: Argument name for error messages (e.g., '--issues').

    Returns:
        Tuple of (parsed_value, return_code). On success, return_code is 0.
        On failure, the error TOON is already printed and return_code is 1;
        the caller should ``return 1`` immediately.
    """
    try:
        return json.loads(raw), 0
    except json.JSONDecodeError as e:
        print(serialize_toon(make_error(
            f'Invalid {field_name} JSON: {e}', code=ErrorCode.INVALID_INPUT,
        )))
        return None, 1


# ============================================================================
# CONFIG FILE LOADING
# ============================================================================


def load_config_file(path: Path, description: str = 'config') -> dict[str, Any]:
    """Load a JSON config file with standardized error handling.

    Returns the parsed dict on success, or an empty dict on failure.
    Warnings are printed to stderr so callers can proceed with defaults.

    Args:
        path: Path to the JSON config file.
        description: Human-readable description for error messages.

    Returns:
        Parsed dict, or empty dict if loading failed.
    """
    try:
        with open(path) as f:
            result: dict[str, Any] = json.load(f)
            return result
    except (OSError, json.JSONDecodeError) as e:
        print(f'WARNING: Failed to load {description} ({path}): {e}', file=sys.stderr)
        return {}


# ============================================================================
# PRIORITY CALCULATION
# ============================================================================

# Canonical priority levels used across all workflow scripts.
PRIORITY_LEVELS = ('low', 'medium', 'high', 'critical')
_PRIORITY_INDEX = {level: i for i, level in enumerate(PRIORITY_LEVELS)}


def calculate_priority(base_priority: str, boost: int = 0) -> str:
    """Calculate final priority by applying a boost to a base level.

    Shared by sonar.py (severity + type boost) and pr_doctor.py (category
    aggregation). Clamps the result to the valid priority range.

    Args:
        base_priority: Starting priority ('low', 'medium', 'high', 'critical').
        boost: Integer offset (+1 = escalate, -1 = de-escalate).

    Returns:
        Adjusted priority string, clamped to valid range.
    """
    current_idx = _PRIORITY_INDEX.get(base_priority, 0)
    new_idx = max(0, min(len(PRIORITY_LEVELS) - 1, current_idx + boost))
    return PRIORITY_LEVELS[new_idx]


# ============================================================================
# TRIAGE COMMAND HANDLERS
# ============================================================================


def cmd_triage_single(json_str: str, triage_fn: Callable[[dict], dict]) -> int:
    """Standard single-item triage command handler.

    Parses JSON string, calls triage_fn, prints TOON result.

    Args:
        json_str: JSON string representing a single item (comment, issue, etc.)
        triage_fn: Function that takes a dict and returns a triage result dict

    Returns:
        0 on success, 1 on failure
    """
    try:
        item = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(serialize_toon(make_error(f'Invalid JSON input: {e}')))
        return 1

    result = triage_fn(item)
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


def cmd_triage_batch_handler(
    json_str: str,
    triage_fn: Callable[[dict], dict],
    action_categories: list[str],
) -> int:
    """Standard batch triage command handler.

    Parses JSON array, triages each item, prints TOON with summary counts.

    Args:
        json_str: JSON string representing an array of items
        triage_fn: Function that takes a dict and returns a triage result dict
        action_categories: List of action names to count in summary
            (e.g., ['code_change', 'explain', 'ignore'] or ['fix', 'suppress'])

    Returns:
        0 on success, 1 on failure
    """
    try:
        items = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(serialize_toon(make_error(f'Invalid JSON input: {e}')))
        return 1

    if not isinstance(items, list):
        print(serialize_toon(make_error('Input must be a JSON array')))
        return 1

    results = [triage_fn(item) for item in items]
    summary: dict[str, Any] = {'total': len(results)}
    for category in action_categories:
        summary[category] = sum(1 for r in results if r['action'] == category)

    print(serialize_toon({'results': results, 'summary': summary, 'status': 'success'}))
    return 0
