#!/usr/bin/env python3
"""
PR Doctor utilities - handoff parsing and diagnostic report generation.

Usage:
    pr_doctor.py parse-handoff --handoff <json>
    pr_doctor.py --help

Subcommands:
    parse-handoff    Parse and validate handoff JSON, merge with explicit params

Examples:
    # Parse a handoff structure
    pr_doctor.py parse-handoff --handoff '{"artifacts":{"pr_number":123},"decisions":{"auto_fix":true}}'

    # Parse with explicit overrides
    pr_doctor.py parse-handoff --handoff '{"artifacts":{"pr_number":123}}' --pr 456 --checks build
"""

import argparse
import json
import sys
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]
from triage_helpers import make_error, safe_main  # type: ignore[import-not-found]

# ============================================================================
# HANDOFF SCHEMA
# ============================================================================

VALID_CHECKS = {'build', 'reviews', 'sonar', 'all'}
DEFAULT_MAX_FIX_ATTEMPTS = 3


def validate_handoff(handoff: dict) -> list[str]:
    """Validate handoff JSON structure. Returns list of warnings (empty = valid)."""
    warnings = []

    # Check top-level structure
    valid_keys = {'artifacts', 'decisions', 'constraints'}
    unknown_keys = set(handoff.keys()) - valid_keys
    if unknown_keys:
        warnings.append(f'Unknown top-level keys: {", ".join(sorted(unknown_keys))}')

    # Validate artifacts
    artifacts = handoff.get('artifacts', {})
    if not isinstance(artifacts, dict):
        warnings.append('artifacts must be a dict')
    else:
        if 'pr_number' in artifacts:
            pr = artifacts['pr_number']
            if not isinstance(pr, int) or pr <= 0:
                warnings.append(f'artifacts.pr_number must be a positive integer, got: {pr}')

    # Validate decisions
    decisions = handoff.get('decisions', {})
    if not isinstance(decisions, dict):
        warnings.append('decisions must be a dict')
    else:
        if 'checks' in decisions:
            checks = decisions['checks']
            if checks not in VALID_CHECKS:
                warnings.append(f'decisions.checks must be one of {VALID_CHECKS}, got: {checks}')
        if 'auto_fix' in decisions and not isinstance(decisions['auto_fix'], bool):
            warnings.append(f'decisions.auto_fix must be bool, got: {type(decisions["auto_fix"]).__name__}')

    # Validate constraints
    constraints = handoff.get('constraints', {})
    if not isinstance(constraints, dict):
        warnings.append('constraints must be a dict')
    else:
        if 'max_fix_attempts' in constraints:
            mfa = constraints['max_fix_attempts']
            if not isinstance(mfa, int) or mfa <= 0:
                warnings.append(f'constraints.max_fix_attempts must be a positive integer, got: {mfa}')
        if 'protected_files' in constraints:
            pf = constraints['protected_files']
            if not isinstance(pf, list) or not all(isinstance(f, str) for f in pf):
                warnings.append('constraints.protected_files must be a list of strings')

    return warnings


def merge_handoff_with_params(
    handoff: dict,
    pr: int | None = None,
    checks: str | None = None,
    auto_fix: bool | None = None,
    max_fix_attempts: int | None = None,
) -> dict[str, Any]:
    """Merge handoff structure with explicit parameters. Explicit params take precedence."""
    artifacts = handoff.get('artifacts', {})
    decisions = handoff.get('decisions', {})
    constraints = handoff.get('constraints', {})

    result: dict[str, Any] = {
        'pr_number': pr if pr is not None else artifacts.get('pr_number'),
        'branch': artifacts.get('branch'),
        'commit_hash': artifacts.get('commit_hash'),
        'plan_id': artifacts.get('plan_id'),
        'checks': checks if checks is not None else decisions.get('checks', 'all'),
        'auto_fix': auto_fix if auto_fix is not None else decisions.get('auto_fix', False),
        'wait': decisions.get('wait', True),
        'skip_sonar': decisions.get('skip_sonar', False),
        'max_fix_attempts': (
            max_fix_attempts if max_fix_attempts is not None
            else constraints.get('max_fix_attempts', DEFAULT_MAX_FIX_ATTEMPTS)
        ),
        'protected_files': constraints.get('protected_files', []),
    }

    return result


# ============================================================================
# TRACK-ATTEMPT SUBCOMMAND
# ============================================================================


# In-memory attempt counters per category (reset per script invocation).
# The caller passes the current count; the script returns whether to continue.
def check_attempt(category: str, current: int, max_attempts: int) -> dict[str, Any]:
    """Check whether a fix attempt should proceed or stop.

    Args:
        category: Fix category (build, reviews, sonar).
        current: Current attempt number (0-based, pre-increment).
        max_attempts: Maximum allowed attempts.

    Returns:
        Dict with 'proceed' bool, 'attempt' (1-based), and 'remaining'.
    """
    attempt = current + 1
    proceed = attempt <= max_attempts
    return {
        'category': category,
        'attempt': attempt,
        'max_attempts': max_attempts,
        'remaining': max(0, max_attempts - attempt),
        'proceed': proceed,
        'reason': 'within limit' if proceed else f'reached max {max_attempts} attempts for {category}',
        'status': 'success',
    }


def cmd_track_attempt(args):
    """Handle track-attempt subcommand."""
    result = check_attempt(args.category, args.current, args.max_attempts)
    print(serialize_toon(result))
    return 0


# ============================================================================
# PARSE-HANDOFF SUBCOMMAND
# ============================================================================


def cmd_parse_handoff(args):
    """Handle parse-handoff subcommand."""
    try:
        handoff = json.loads(args.handoff)
    except json.JSONDecodeError as e:
        print(serialize_toon(make_error(f'Invalid JSON input: {e}')))
        return 1

    if not isinstance(handoff, dict):
        print(serialize_toon(make_error('Handoff must be a JSON object')))
        return 1

    # Validate
    warnings = validate_handoff(handoff)

    # Merge with explicit params
    merged = merge_handoff_with_params(
        handoff,
        pr=args.pr,
        checks=args.checks,
        auto_fix=args.auto_fix,
        max_fix_attempts=args.max_fix_attempts,
    )

    result: dict[str, Any] = {
        'merged': merged,
        'validation': {
            'valid': len(warnings) == 0,
            'warnings': warnings,
        },
        'status': 'success',
    }

    print(serialize_toon(result))
    return 0


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='PR Doctor utilities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pr_doctor.py parse-handoff --handoff '{"artifacts":{"pr_number":123}}'
  pr_doctor.py parse-handoff --handoff '{"artifacts":{"pr_number":123}}' --pr 456
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # track-attempt subcommand
    attempt_parser = subparsers.add_parser('track-attempt', help='Check if a fix attempt should proceed')
    attempt_parser.add_argument('--category', required=True, choices=['build', 'reviews', 'sonar'], help='Fix category')
    attempt_parser.add_argument('--current', type=int, required=True, help='Current attempt count (0-based)')
    attempt_parser.add_argument('--max-attempts', type=int, default=DEFAULT_MAX_FIX_ATTEMPTS, help='Maximum attempts')
    attempt_parser.set_defaults(func=cmd_track_attempt)

    # parse-handoff subcommand
    handoff_parser = subparsers.add_parser('parse-handoff', help='Parse and validate handoff JSON')
    handoff_parser.add_argument('--handoff', required=True, help='Handoff JSON string')
    handoff_parser.add_argument('--pr', type=int, help='Override PR number')
    handoff_parser.add_argument('--checks', choices=['build', 'reviews', 'sonar', 'all'], help='Override checks')
    handoff_parser.add_argument('--auto-fix', nargs='?', const=True, default=None, type=lambda v: v.lower() in ('true', '1', 'yes') if isinstance(v, str) else bool(v), help='Override auto-fix (flag or true/false)')
    handoff_parser.add_argument('--max-fix-attempts', type=int, help='Override max fix attempts')
    handoff_parser.set_defaults(func=cmd_parse_handoff)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
