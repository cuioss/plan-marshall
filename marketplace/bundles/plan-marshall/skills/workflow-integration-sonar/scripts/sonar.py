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

import sys

from triage_helpers import (  # type: ignore[import-not-found]
    calculate_priority,
    cmd_triage_batch_handler,
    cmd_triage_single,
    create_workflow_cli,
    is_test_file,
    load_skill_config,
    safe_main,
)

# ============================================================================
# TRIAGE CONFIGURATION (loaded from sonar-rules.json)
# ============================================================================

_RULES_CONFIG = load_skill_config(__file__, 'sonar-rules.json')

SUPPRESSABLE_RULES: dict[str, str] = _RULES_CONFIG.get('suppressable_rules', {})

# Severity to priority mapping — externalized to sonar-rules.json for consistency
# with the data-driven pattern used by all workflow scripts.
SEVERITY_PRIORITY: dict[str, str] = _RULES_CONFIG['severity_priority']

# Type to priority boost — includes SECURITY_HOTSPOT (Sonar's 4th issue type).
# Values are index offsets in PRIORITY_LEVELS: +1 promotes, -1 demotes.
TYPE_BOOST: dict[str, int] = _RULES_CONFIG['type_boost']

# Issue types that must always be fixed — loaded from sonar-rules.json.
_ALWAYS_FIX_TYPES: dict[str, str] = _RULES_CONFIG.get('always_fix_types', {})


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


_SUPPRESSION_SYNTAX: dict[str, str] = _RULES_CONFIG.get(
    'suppression_syntax',
    {
        'python': '# NOSONAR {rule} - {reason}',
        'default': '// NOSONAR {rule} - {reason}',
    },
)


def get_suppression_string(rule: str, reason: str, file: str = '') -> str:
    """Generate suppression string for the issue using language-appropriate comment syntax.

    Language detection order: file extension → rule prefix → default (//).
    Syntax templates are loaded from ``standards/sonar-rules.json`` suppression_syntax.
    """
    # Detect language from file extension or rule prefix
    lang = None
    if file.endswith('.py') or rule.startswith('python:'):
        lang = 'python'
    template = _SUPPRESSION_SYNTAX.get(
        lang or 'default', _SUPPRESSION_SYNTAX.get('default', '// NOSONAR {rule} - {reason}')
    )
    return template.format(rule=rule, reason=reason)


def calculate_sonar_priority(severity: str, issue_type: str) -> str:
    """Calculate priority based on Sonar severity and issue type.

    Delegates to shared ``calculate_priority`` from triage_helpers with
    a severity-to-base mapping and type-based boost.
    """
    base_priority = SEVERITY_PRIORITY.get(severity, 'low')
    boost = TYPE_BOOST.get(issue_type, 0)
    return calculate_priority(base_priority, boost)


def should_suppress(rule: str, file: str, issue_type: str) -> tuple[bool, str | None]:
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

    # Issue types that must always be fixed (loaded from sonar-rules.json)
    if issue_type in _ALWAYS_FIX_TYPES:
        priority = 'critical' if severity == 'BLOCKER' else 'high'
        return {
            'issue_key': key,
            'action': 'fix',
            'reason': _ALWAYS_FIX_TYPES[issue_type],
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
            'suppression_string': get_suppression_string(rule, suppress_reason or '', file),
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
    parser = create_workflow_cli(
        description='Sonar workflow operations',
        epilog="""
Examples:
  sonar.py triage --issue '{"key":"ISSUE-1","rule":"java:S1234"}'
  sonar.py triage-batch --issues '[{"key":"I1","rule":"java:S1234"}, ...]'
""",
        subcommands=[
            {
                'name': 'triage',
                'help': 'Triage a single Sonar issue',
                'handler': cmd_triage,
                'args': [{'flags': ['--issue'], 'required': True, 'help': 'JSON string with issue data'}],
            },
            {
                'name': 'triage-batch',
                'help': 'Triage multiple Sonar issues at once',
                'handler': cmd_triage_batch,
                'args': [{'flags': ['--issues'], 'required': True, 'help': 'JSON array of issue objects'}],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon  # type: ignore[import-not-found]

    return _output_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
