#!/usr/bin/env python3
"""
Shared helpers for workflow scripts (pr.py, sonar.py, git-workflow.py).

Provides:
- Triage command handlers (single-item and batch) for JSON→TOON workflows
- safe_main wrapper for consistent error handling across all workflow scripts

Usage:
    from triage_helpers import cmd_triage_single, cmd_triage_batch_handler, safe_main
"""

import json
from collections.abc import Callable
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]


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
        print(serialize_toon({'error': f'Unexpected error: {e}', 'status': 'failure'}))
        return 1


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
        print(serialize_toon({'error': f'Invalid JSON input: {e}', 'status': 'failure'}))
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
        print(serialize_toon({'error': f'Invalid JSON input: {e}', 'status': 'failure'}))
        return 1

    if not isinstance(items, list):
        print(serialize_toon({'error': 'Input must be a JSON array', 'status': 'failure'}))
        return 1

    results = [triage_fn(item) for item in items]
    summary: dict[str, Any] = {'total': len(results)}
    for category in action_categories:
        summary[category] = sum(1 for r in results if r['action'] == category)

    print(serialize_toon({'results': results, 'summary': summary, 'status': 'success'}))
    return 0
