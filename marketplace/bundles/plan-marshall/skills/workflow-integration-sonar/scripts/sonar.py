#!/usr/bin/env python3
"""
Sonar workflow operations - triage issues for fix or suppress.

Usage:
    sonar.py triage --issue <json>
    sonar.py triage-batch --issues <json-array>
    sonar.py --help

Subcommands:
    triage         Triage a single Sonar issue
    triage-batch   Triage multiple Sonar issues at once

Examples:
    # Triage a single issue
    sonar.py triage --issue '{"key":"ISSUE-1","rule":"java:S1234",...}'

    # Triage multiple issues at once
    sonar.py triage-batch --issues '[{"key":"I1","rule":"java:S1234",...}, ...]'
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    calculate_priority,
    cmd_triage_batch_handler,
    cmd_triage_single,
    is_test_file,
    load_config_file,
    safe_main,
)


# ============================================================================
# TRIAGE CONFIGURATION (loaded from sonar-rules.json)
# ============================================================================

_RULES_FILE = Path(__file__).parent.parent / 'standards' / 'sonar-rules.json'


_RULES_CONFIG = load_config_file(_RULES_FILE, 'sonar-rules.json')

SUPPRESSABLE_RULES: dict[str, str] = _RULES_CONFIG.get('suppressable_rules', {})

# Severity to priority mapping
SEVERITY_PRIORITY = {'BLOCKER': 'critical', 'CRITICAL': 'high', 'MAJOR': 'medium', 'MINOR': 'low', 'INFO': 'low'}

# Type to priority boost — includes SECURITY_HOTSPOT (Sonar's 4th issue type)
TYPE_BOOST = {
    'VULNERABILITY': 1,  # Boost priority
    'SECURITY_HOTSPOT': 1,  # Boost priority — requires review
    'BUG': 0,
    'CODE_SMELL': -1,  # Lower priority
}


# ============================================================================
# TRIAGE SUBCOMMAND
# ============================================================================


_FIX_SUGGESTIONS: dict[str, str] = _RULES_CONFIG.get('fix_suggestions', {})
_TEST_ACCEPTABLE_RULES: set[str] = set(_RULES_CONFIG.get('test_acceptable_rules', []))


def get_fix_suggestion(rule: str, message: str, file: str, line: int) -> str:
    """Generate fix suggestion based on rule.

    Supports Java, JavaScript/TypeScript, and Python rules. Rule-to-suggestion
    mappings are loaded from ``standards/sonar-rules.json``. Falls back to
    the Sonar issue message for unrecognized rules.
    """
    suggestion = _FIX_SUGGESTIONS.get(rule, f'Review and fix: {message}')
    return f'{suggestion} at {file}:{line}'


def get_suppression_string(rule: str, reason: str, file: str = '') -> str:
    """Generate suppression string for the issue using language-appropriate comment syntax."""
    if file.endswith('.py') or rule.startswith('python:'):
        return f'# NOSONAR {rule} - {reason}'
    return f'// NOSONAR {rule} - {reason}'


def calculate_sonar_priority(severity: str, issue_type: str) -> str:
    """Calculate priority based on Sonar severity and issue type.

    Delegates to shared ``calculate_priority`` from triage_helpers with
    a severity-to-base mapping and type-based boost.
    """
    base_priority = SEVERITY_PRIORITY.get(severity, 'low')
    boost = TYPE_BOOST.get(issue_type, 0)
    return calculate_priority(base_priority, boost)


def should_suppress(rule: str, file: str, issue_type: str) -> tuple:
    """Determine if issue should be suppressed."""
    # Check suppressable rules
    if rule in SUPPRESSABLE_RULES:
        return True, SUPPRESSABLE_RULES[rule]

    # Test files often have acceptable exceptions — detect across languages
    if is_test_file(file):
        # Console/stdout usage and missing assertions are acceptable in tests
        if rule in _TEST_ACCEPTABLE_RULES:
            return True, 'Test code - acceptable pattern'

    return False, None


def triage_issue(issue: dict) -> dict:
    """Triage a single issue and return decision."""
    key = issue.get('key', 'unknown')
    issue_type = issue.get('type', 'CODE_SMELL')
    severity = issue.get('severity', 'MAJOR')
    file = issue.get('file', 'unknown')
    line = issue.get('line', 0)
    rule = issue.get('rule', 'unknown')
    message = issue.get('message', '')

    # Security hotspots and vulnerabilities must always be fixed
    if issue_type in ('VULNERABILITY', 'SECURITY_HOTSPOT'):
        priority = 'critical' if severity == 'BLOCKER' else 'high'
        return {
            'issue_key': key,
            'action': 'fix',
            'reason': f'{issue_type} must always be fixed',
            'priority': priority,
            'suggested_implementation': get_fix_suggestion(rule, message, file, line),
            'suppression_string': None,
            'status': 'success',
        }

    # Check if should suppress
    suppress, suppress_reason = should_suppress(rule, file, issue_type)

    if suppress:
        return {
            'issue_key': key,
            'action': 'suppress',
            'reason': suppress_reason,
            'priority': 'low',
            'suggested_implementation': None,
            'suppression_string': get_suppression_string(rule, suppress_reason, file),
            'status': 'success',
        }

    # Calculate priority and suggest fix
    priority = calculate_sonar_priority(severity, issue_type)
    fix_suggestion = get_fix_suggestion(rule, message, file, line)

    return {
        'issue_key': key,
        'action': 'fix',
        'reason': f'{issue_type} with {severity} severity should be fixed',
        'priority': priority,
        'suggested_implementation': fix_suggestion,
        'suppression_string': None,
        'status': 'success',
    }


def cmd_triage(args):
    """Handle triage subcommand - triage a single Sonar issue."""
    return cmd_triage_single(args.issue, triage_issue)


def cmd_triage_batch(args):
    """Handle triage-batch subcommand — triage multiple issues at once."""
    return cmd_triage_batch_handler(args.issues, triage_issue, ['fix', 'suppress'])


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sonar workflow operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sonar.py triage --issue '{"key":"ISSUE-1","rule":"java:S1234"}'
  sonar.py triage-batch --issues '[{"key":"I1","rule":"java:S1234"}, ...]'
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # triage subcommand
    triage_parser = subparsers.add_parser('triage', help='Triage a single Sonar issue')
    triage_parser.add_argument('--issue', required=True, help='JSON string with issue data')
    triage_parser.set_defaults(func=cmd_triage)

    # triage-batch subcommand
    batch_parser = subparsers.add_parser('triage-batch', help='Triage multiple Sonar issues at once')
    batch_parser.add_argument('--issues', required=True, help='JSON array of issue objects')
    batch_parser.set_defaults(func=cmd_triage_batch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
