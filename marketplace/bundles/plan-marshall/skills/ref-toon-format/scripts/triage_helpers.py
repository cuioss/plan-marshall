#!/usr/bin/env python3
"""
Shared helpers for workflow scripts in plan-marshall bundle.

Provides:
- ``print_toon`` / ``print_error`` — output helpers replacing repetitive print+serialize+return patterns
- ``safe_main`` — wrapper for consistent error handling across all workflow scripts
- ``ErrorCode`` / ``make_error`` — error code taxonomy for cross-skill error propagation
- ``load_skill_config`` — standardized config loading from skill standards directories
- ``create_workflow_cli`` — argparse boilerplate reduction for subcommand-based scripts
- ``cmd_triage_single`` / ``cmd_triage_batch_handler`` — triage command handlers for JSON→TOON workflows
- ``calculate_priority`` — priority calculation utility for severity/boost workflows (used by sonar.py)
- ``is_test_file`` — test file detection across languages (used by sonar.py, git_workflow.py)

Usage:
    from triage_helpers import print_toon, print_error, safe_main, create_workflow_cli
    from triage_helpers import ErrorCode, make_error, load_skill_config
"""

import argparse
import json
import re
import sys
import traceback as tb_module
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from toon_parser import serialize_toon  # type: ignore[import-not-found]

__all__ = [
    # Error handling
    'ErrorCode', 'make_error',
    # Output helpers
    'print_toon', 'print_error',
    # Main wrapper
    'safe_main',
    # JSON/config loading
    'parse_json_arg', 'load_config_file', 'load_skill_config',
    # CLI construction
    'create_workflow_cli',
    # Priority
    'calculate_priority', 'PRIORITY_LEVELS',
    # Test detection
    'is_test_file',
    # Triage handlers
    'cmd_triage_single', 'cmd_triage_batch_handler',
    # Type definitions
    'TriageResult',
    # Regex compilation
    'compile_patterns_from_config',
]


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================


class TriageResult(TypedDict, total=False):
    """Expected return shape for triage callback functions.

    Used by ``cmd_triage_single`` and ``cmd_triage_batch_handler`` callbacks.
    The ``action`` and ``status`` fields are required; all others are optional
    and vary by domain (CI comments, Sonar issues, etc.).
    """

    action: str       # Required: 'code_change', 'explain', 'ignore', 'fix', 'suppress'
    status: str       # Required: 'success' or 'error'
    reason: str
    priority: str
    suggested_implementation: str | None
    suppression_string: str | None


# ============================================================================
# ERROR CODE TAXONOMY
# ============================================================================


class ErrorCode:
    """Standardized error codes for cross-skill error propagation.

    Used by workflow skills (pr-doctor, integration-ci, integration-sonar,
    integration-git, permission-web) to enable consistent error routing across
    orchestration layers without string matching on error messages.

    Semantic guidelines:
    - ``NOT_FOUND``: A requested resource (file, PR, directory) does not exist.
    - ``INVALID_INPUT``: Input data has the wrong shape or type (not a parsing failure).
    - ``PARSE_ERROR``: JSON/TOON/config parsing failed (malformed syntax).
    - ``FETCH_FAILURE``: A configured provider returned an error during data retrieval.
    - ``PROVIDER_NOT_CONFIGURED``: No CI/MCP provider is set up at all.
    """

    PROVIDER_NOT_CONFIGURED = 'PROVIDER_NOT_CONFIGURED'
    FETCH_FAILURE = 'FETCH_FAILURE'
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
    a consistent contract: ``{'error': message, 'status': 'error', ...}``.

    Args:
        message: Human-readable error description.
        code: Optional error code from ``ErrorCode`` for programmatic routing.
        **extra: Additional context fields (e.g., file, category).

    Returns:
        Dict ready for ``serialize_toon()``.
    """
    result: dict[str, Any] = {'error': message, 'status': 'error'}
    if code:
        result['error_code'] = code
    result.update(extra)
    return result


# ============================================================================
# OUTPUT HELPERS
# ============================================================================


def print_toon(result: dict[str, Any]) -> int:
    """Serialize a result dict to TOON, print it, and return an exit code.

    Returns 0 if ``result['status'] == 'success'``, 1 otherwise.
    Replaces the repetitive ``print(serialize_toon(result)); return 0/1`` pattern.
    """
    print(serialize_toon(result))
    return 0 if result.get('status') == 'success' else 1


def print_error(message: str, *, code: str | None = None, **extra: Any) -> int:
    """Shortcut: create an error payload, print it as TOON, and return 1.

    Replaces the triple: ``print(serialize_toon(make_error(...))); return 1``.
    """
    return print_toon(make_error(message, code=code, **extra))


def safe_main(main_fn: Callable[[], int]) -> int:
    """Wrap a script's main() to catch unhandled exceptions and emit TOON failure.

    Ensures all workflow scripts produce structured TOON output even on
    unexpected errors, instead of raw tracebacks. The full traceback is
    included in the TOON payload for debugging.

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
        print(serialize_toon(make_error(
            f'Unexpected error: {e}',
            traceback=tb_module.format_exc(),
        )))
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


def load_skill_config(script_file: str, config_name: str) -> dict[str, Any]:
    """Load a JSON config from the skill's standards directory.

    Computes the standard path: ``<script_dir>/../standards/<config_name>``
    and delegates to ``load_config_file``. All workflow scripts follow this
    directory convention.

    Args:
        script_file: The ``__file__`` of the calling script.
        config_name: Config filename (e.g., 'sonar-rules.json').

    Returns:
        Parsed dict, or empty dict if loading failed.
    """
    config_path = Path(script_file).parent.parent / 'standards' / config_name
    return load_config_file(config_path, config_name)


# ============================================================================
# PRIORITY CALCULATION
# ============================================================================

# Canonical priority levels used across all workflow scripts.
PRIORITY_LEVELS = ('low', 'medium', 'high', 'critical')
_PRIORITY_INDEX = {level: i for i, level in enumerate(PRIORITY_LEVELS)}


def calculate_priority(base_priority: str, boost: int = 0) -> str:
    """Calculate final priority by applying a boost to a base level.

    Primary consumer: ``sonar.py`` (severity + type boost via
    ``calculate_sonar_priority``). Available for other workflow scripts
    that need priority escalation/de-escalation arithmetic.

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
# TEST FILE DETECTION
# ============================================================================

# Consolidated test-file detection patterns. Covers Java, Python, JavaScript/TypeScript,
# Go, and generic test directory conventions.
# Consumers: sonar.py (suppression rules for test files), git_workflow.py (diff analysis).
_TEST_DIR_SEGMENTS = ('/test/', '/tests/', '/__tests__/')
_TEST_SUFFIXES = (
    'Test.java', 'Tests.java', 'IT.java',           # Java (JUnit)
    '.test.js', '.test.ts', '.test.jsx', '.test.tsx',  # JS/TS (Jest/Vitest)
    '.spec.js', '.spec.ts', '.spec.jsx', '.spec.tsx',  # JS/TS (Jasmine/Mocha)
    '_test.go',                                        # Go
    '_test.py',                                        # Python (pytest)
)
_TEST_PREFIXES = ('test_',)  # Python test files (test_foo.py)
_TEST_DIR_PREFIXES = ('test/', 'tests/')  # Top-level test directories


def is_test_file(file_path: str) -> bool:
    """Determine whether a file path refers to a test file.

    Checks directory segments, file suffixes, and file prefixes against
    known test conventions across Java, Python, JavaScript/TypeScript, and Go.
    """
    if any(seg in file_path for seg in _TEST_DIR_SEGMENTS):
        return True
    if any(file_path.endswith(suffix) for suffix in _TEST_SUFFIXES):
        return True
    # Check filename (last path component) for prefix patterns
    filename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path
    if any(filename.startswith(prefix) for prefix in _TEST_PREFIXES):
        return True
    # Top-level test directories
    if any(file_path.startswith(prefix) for prefix in _TEST_DIR_PREFIXES):
        return True
    return False


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
        return print_error(f'Invalid JSON input: {e}')

    result = triage_fn(item)
    return print_toon(result)


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
        return print_error(f'Invalid JSON input: {e}')

    if not isinstance(items, list):
        return print_error('Input must be a JSON array')

    results: list[dict[str, Any]] = []
    failed = 0
    for item in items:
        try:
            results.append(triage_fn(item))
        except Exception as e:
            failed += 1
            item_id = item.get('id', item.get('key', 'unknown')) if isinstance(item, dict) else 'unknown'
            results.append({
                'item_id': item_id,
                'action': 'error',
                'reason': f'Triage failed: {e}',
                'status': 'error',
            })

    summary: dict[str, Any] = {'total': len(results), 'failed': failed}
    for category in action_categories:
        summary[category] = sum(1 for r in results if r.get('action') == category)

    return print_toon({'results': results, 'summary': summary, 'status': 'success'})


# ============================================================================
# REGEX COMPILATION FROM CONFIG
# ============================================================================


def compile_patterns_from_config(
    patterns: list[str],
    source_label: str = 'config',
) -> list[re.Pattern]:
    """Pre-compile regex patterns from a JSON config list.

    Shared by workflow scripts that load regex patterns from standards/*.json
    files (pr.py from comment-patterns.json, permission_web.py from
    domain-lists.json). Centralizes error handling and warning output.

    Args:
        patterns: List of regex pattern strings.
        source_label: Human-readable label for warning messages
            (e.g., 'comment-patterns.json [code_change][high]').

    Returns:
        List of compiled regex Pattern objects. Invalid patterns are skipped
        with a stderr warning.
    """
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error as e:
            print(f'WARNING: Invalid regex in {source_label}: {p} — {e}', file=sys.stderr)
    return compiled


# ============================================================================
# CLI CONSTRUCTION
# ============================================================================


def create_workflow_cli(
    description: str,
    epilog: str,
    subcommands: list[dict[str, Any]],
) -> argparse.ArgumentParser:
    """Create a standardized argparse parser for workflow scripts.

    Reduces the ~20-line boilerplate that every workflow script duplicates:
    ArgumentParser → add_subparsers → per-subcommand setup → set_defaults(func=...).

    Args:
        description: Parser description.
        epilog: Examples text for --help output.
        subcommands: List of dicts, each with:
            - ``name`` (str): Subcommand name (e.g., 'triage').
            - ``help`` (str): Subcommand help text.
            - ``handler`` (Callable): Function to call for this subcommand.
            - ``args`` (list[dict]): Argument definitions, each with:
                - ``flags`` (list[str]): Argument flags (e.g., ['--issue']).
                - Plus any kwargs for ``add_argument`` (type, required, help, etc.).

    Returns:
        Configured ArgumentParser. Call ``parser.parse_args()`` then ``args.func(args)``.

    Example::

        parser = create_workflow_cli(
            description='Sonar workflow operations',
            epilog='  sonar.py triage --issue ...',
            subcommands=[{
                'name': 'triage',
                'help': 'Triage a single Sonar issue',
                'handler': cmd_triage,
                'args': [{'flags': ['--issue'], 'required': True, 'help': 'JSON issue data'}],
            }],
        )
        args = parser.parse_args()
        return args.func(args)
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true', default=False,
        help='Enable verbose output for debugging',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    for cmd in subcommands:
        sub = subparsers.add_parser(cmd['name'], help=cmd['help'])
        for arg_def in cmd.get('args', []):
            flags = arg_def['flags']
            kwargs = {k: v for k, v in arg_def.items() if k != 'flags'}
            sub.add_argument(*flags, **kwargs)
        sub.set_defaults(func=cmd['handler'])

    return parser
