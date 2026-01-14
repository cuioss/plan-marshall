#!/usr/bin/env python3
"""
Sonar workflow operations - fetch issues and triage them.

Usage:
    sonar.py fetch --project <key> [options]
    sonar.py triage --issue <json>
    sonar.py --help

Subcommands:
    fetch       Fetch Sonar issues for a PR or project
    triage      Triage a single Sonar issue

Examples:
    # Fetch issues for a project
    sonar.py fetch --project myproject --pr 123 --severities BLOCKER,CRITICAL

    # Triage a single issue
    sonar.py triage --issue '{"key":"ISSUE-1","rule":"java:S1234",...}'
"""

import argparse
import json
import sys
from typing import Any

# ============================================================================
# TRIAGE CONFIGURATION
# ============================================================================

# Rules that are typically suppressable (false positives or intentional)
SUPPRESSABLE_RULES = {
    'java:S1135': 'TODO comments - tracked in issue management',
    'java:S1068': 'Unused fields - may be for reflection/serialization',
    'java:S1172': 'Unused parameters - may be for API compatibility',
    'java:S106': 'System.out - acceptable in CLI/test code',
    'java:S2139': 'Logger vs exception - design decision',
}

# Severity to priority mapping
SEVERITY_PRIORITY = {'BLOCKER': 'critical', 'CRITICAL': 'high', 'MAJOR': 'medium', 'MINOR': 'low', 'INFO': 'low'}

# Type to priority boost
TYPE_BOOST = {
    'VULNERABILITY': 1,  # Boost priority
    'BUG': 0,
    'CODE_SMELL': -1,  # Lower priority
}


# ============================================================================
# FETCH SUBCOMMAND
# ============================================================================


def generate_mcp_instruction(project: str, pr: str | None = None, severities: str | None = None) -> dict[str, Any]:
    """Generate MCP tool invocation instruction for Claude."""
    parameters: dict[str, Any] = {'projects': [project]}
    instruction: dict[str, Any] = {'tool': 'mcp__sonarqube__search_sonar_issues_in_projects', 'parameters': parameters}

    if pr:
        parameters['pullRequestId'] = pr

    if severities:
        parameters['severities'] = severities

    return instruction


def create_fetch_output(
    project: str, pr: str | None = None, severities: str | None = None, types: str | None = None
) -> dict:
    """Create output structure showing expected format for fetch."""
    return {
        'project_key': project,
        'pull_request_id': pr,
        'issues': [
            {
                'key': 'EXAMPLE-001',
                'type': 'BUG',
                'severity': 'MAJOR',
                'file': 'src/main/java/Example.java',
                'line': 42,
                'rule': 'java:S1234',
                'message': 'Example issue message',
                '_note': 'This is sample structure - actual issues from MCP tool',
            }
        ],
        'statistics': {'total_issues_fetched': 0, 'issues_after_filtering': 0, 'by_severity': {}, 'by_type': {}},
        'mcp_instruction': generate_mcp_instruction(project, pr, severities),
        'status': 'instruction_generated',
    }


def cmd_fetch(args):
    """Handle fetch subcommand - fetch Sonar issues for a PR."""
    result = create_fetch_output(args.project, args.pr, args.severities, args.types)
    print(json.dumps(result, indent=2))
    return 0


# ============================================================================
# TRIAGE SUBCOMMAND
# ============================================================================


def get_fix_suggestion(rule: str, message: str, file: str, line: int) -> str:
    """Generate fix suggestion based on rule."""
    suggestions = {
        'java:S2095': 'Wrap resource in try-with-resources block',
        'java:S1192': 'Extract duplicated string to constant',
        'java:S3649': 'Use parameterized query instead of string concatenation',
        'java:S1068': 'Remove unused field or add @SuppressWarnings with reason',
        'java:S1135': 'Complete TODO or track in issue management system',
        'java:S106': 'Replace System.out with CuiLogger',
        'java:S1481': 'Remove unused local variable',
        'java:S1854': 'Remove useless assignment',
        'java:S1144': 'Remove unused private method',
    }

    rule_id = rule.split(':')[-1] if ':' in rule else rule
    full_rule = f'java:{rule_id}' if not rule.startswith('java:') else rule

    suggestion = suggestions.get(full_rule, f'Review and fix: {message}')
    return f'{suggestion} at {file}:{line}'


def get_suppression_string(rule: str, reason: str) -> str:
    """Generate suppression string for the issue."""
    return f'// NOSONAR {rule} - {reason}'


def calculate_priority(severity: str, issue_type: str) -> str:
    """Calculate priority based on severity and type."""
    base_priority = SEVERITY_PRIORITY.get(severity, 'low')
    boost = TYPE_BOOST.get(issue_type, 0)

    priority_levels = ['low', 'medium', 'high', 'critical']
    current_idx = priority_levels.index(base_priority)
    new_idx = max(0, min(len(priority_levels) - 1, current_idx + boost))

    return priority_levels[new_idx]


def should_suppress(rule: str, file: str, issue_type: str) -> tuple:
    """Determine if issue should be suppressed."""
    # Check suppressable rules
    if rule in SUPPRESSABLE_RULES:
        return True, SUPPRESSABLE_RULES[rule]

    # Test files often have acceptable exceptions
    if '/test/' in file or 'Test.java' in file:
        if rule in ['java:S106', 'java:S2699']:
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

    # Check if should suppress
    suppress, suppress_reason = should_suppress(rule, file, issue_type)

    if suppress:
        return {
            'issue_key': key,
            'action': 'suppress',
            'reason': suppress_reason,
            'priority': 'low',
            'suggested_implementation': None,
            'suppression_string': get_suppression_string(rule, suppress_reason),
            'status': 'success',
        }

    # Calculate priority and suggest fix
    priority = calculate_priority(severity, issue_type)
    fix_suggestion = get_fix_suggestion(rule, message, file, line)

    return {
        'issue_key': key,
        'action': 'fix',
        'reason': f'{issue_type} with {severity} severity should be fixed',
        'priority': priority,
        'suggested_implementation': fix_suggestion,
        'suppression_string': None,
        'command_to_use': '/java-implement-code' if file.endswith('.java') else None,
        'status': 'success',
    }


def cmd_triage(args):
    """Handle triage subcommand - triage a single Sonar issue."""
    try:
        issue = json.loads(args.issue)
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON input: {e}', 'status': 'failure'}, indent=2))
        return 1

    result = triage_issue(issue)
    print(json.dumps(result, indent=2))

    return 0 if result.get('status') == 'success' else 1


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
  sonar.py fetch --project myproject --pr 123
  sonar.py triage --issue '{"key":"ISSUE-1","rule":"java:S1234"}'
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # fetch subcommand
    fetch_parser = subparsers.add_parser('fetch', help='Fetch Sonar issues for a PR or project')
    fetch_parser.add_argument('--project', required=True, help='SonarQube project key')
    fetch_parser.add_argument('--pr', help='Pull request ID')
    fetch_parser.add_argument(
        '--severities', help='Filter by severities (comma-separated: BLOCKER,CRITICAL,MAJOR,MINOR,INFO)'
    )
    fetch_parser.add_argument('--types', help='Filter by types (comma-separated: BUG,CODE_SMELL,VULNERABILITY)')
    fetch_parser.set_defaults(func=cmd_fetch)

    # triage subcommand
    triage_parser = subparsers.add_parser('triage', help='Triage a single Sonar issue')
    triage_parser.add_argument('--issue', required=True, help='JSON string with issue data')
    triage_parser.set_defaults(func=cmd_triage)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
