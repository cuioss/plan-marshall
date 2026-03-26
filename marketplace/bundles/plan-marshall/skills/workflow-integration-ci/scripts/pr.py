#!/usr/bin/env python3
"""
PR workflow operations - fetch comments and triage them (provider-agnostic).

Uses tools-integration-ci ci router for provider abstraction.

Usage:
    pr.py fetch-comments [--pr <number>] [--unresolved-only]
    pr.py triage --comment <json>
    pr.py --help

Subcommands:
    fetch-comments    Fetch PR review comments (GitHub or GitLab via ci router)
    triage           Triage a single PR review comment

Examples:
    # Fetch comments for current branch's PR
    pr.py fetch-comments

    # Fetch comments for specific PR
    pr.py fetch-comments --pr 123

    # Triage a single comment
    pr.py triage --comment '{"id":"C1","body":"Please fix this","path":"src/Main.java","line":42}'
"""

import argparse
import json
import re
import subprocess
import sys
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]

# ============================================================================
# TRIAGE CONFIGURATION
# ============================================================================

# Patterns for classification
PATTERNS: dict[str, Any] = {
    'code_change': {
        'high': [
            r'security',
            r'vulnerability',
            r'injection',
            r'xss',
            r'csrf',
            r'bug',
            r'error',
            r'fix',
            r'broken',
            r'crash',
            r'null pointer',
            r'memory leak',
        ],
        'medium': [
            r'please\s+(?:add|remove|change|fix|update)',
            r'should\s+(?:be|have|use)',
            r'missing',
            r'incorrect',
            r'wrong',
        ],
        'low': [r'rename', r'variable name', r'naming', r'typo', r'spelling', r'formatting', r'style'],
    },
    'explain': [r'why', r'explain', r'reasoning', r'rationale', r'how does', r'what is', r'can you clarify', r'\?'],
    'ignore': [r'^lgtm', r'^approved', r'looks good', r'^nice', r'^thanks', r'\[bot\]', r'^nit:', r'^nitpick:'],
}


# ============================================================================
# FETCH-COMMENTS SUBCOMMAND (Provider-Agnostic via ci router)
# ============================================================================

# CI router command prefix — the ci.py router reads ci.provider from marshal.json
# and delegates to the correct provider script (github.py or gitlab.py)
CI_ROUTER = 'python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci'


def run_command(cmd: str, extra_args: list[str] | None = None) -> tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, return code."""
    full_cmd = cmd
    if extra_args:
        full_cmd = f'{cmd} {" ".join(extra_args)}'

    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return '', 'Command timed out', 124
    except Exception as e:
        return '', str(e), 1


def get_current_pr_number() -> int | None:
    """Get PR number for current branch via ci router."""
    stdout, stderr, returncode = run_command(f'{CI_ROUTER} pr view')
    if returncode != 0:
        return None

    # Parse pr_number from TOON output
    for line in stdout.split('\n'):
        if line.startswith('pr_number:'):
            try:
                return int(line.split(':', 1)[1].strip())
            except ValueError:
                return None

    return None


def parse_toon_comments(toon_output: str) -> list[dict[str, Any]]:
    """Parse TOON format comment output from tools-integration-ci.

    Uses the TOON table header to map columns dynamically, so this parser
    handles any column order and additional fields (e.g. thread_id).
    """
    comments: list[dict[str, Any]] = []
    lines = toon_output.strip().split('\n')

    in_comments_table = False
    fields: list[str] = []
    for line in lines:
        # Detect start of comments table: comments[N]{field1,field2,...}:
        if line.startswith('comments['):
            in_comments_table = True
            # Extract field names from header
            brace_start = line.find('{')
            brace_end = line.find('}')
            if brace_start != -1 and brace_end != -1:
                fields = line[brace_start + 1 : brace_end].split(',')
            continue

        # Skip non-table lines or empty lines
        if not in_comments_table or not line.strip():
            continue

        # Strip leading whitespace (TOON table rows are indented with 2 spaces)
        stripped = line.strip()

        # Stop at next section (non-indented line that looks like a key: value)
        if not line[0].isspace() and ':' in stripped:
            break

        # Parse tab-separated comment row using header fields
        parts = stripped.split('\t')
        if fields and len(parts) >= len(fields):
            row = dict(zip(fields, parts, strict=False))
            # Normalize known fields
            comment: dict[str, Any] = {
                'id': row.get('id', ''),
                'author': row.get('author', ''),
                'body': row.get('body', ''),
                'path': row.get('path') if row.get('path') != '-' else None,
                'line': int(row['line']) if row.get('line', '-') not in ('-', '') and row['line'].isdigit() else None,
                'resolved': row.get('resolved', 'false').lower() == 'true',
                'created_at': row.get('created_at'),
            }
            # Include thread_id if present
            if 'thread_id' in row:
                comment['thread_id'] = row['thread_id']
            comments.append(comment)

    return comments


def fetch_comments(pr_number: int, unresolved_only: bool = False) -> dict[str, Any]:
    """Fetch review comments for a PR using tools-integration-ci ci router."""
    pr_comments_cmd = f'{CI_ROUTER} pr comments'

    # Build command with arguments
    extra_args = ['--pr-number', str(pr_number)]
    if unresolved_only:
        extra_args.append('--unresolved-only')

    stdout, stderr, code = run_command(pr_comments_cmd, extra_args)

    if code != 0:
        return {'error': f'Failed to fetch PR comments: {stderr}', 'status': 'failure'}

    # Parse TOON output
    comments = parse_toon_comments(stdout)

    # Extract metadata from TOON header
    provider = 'unknown'
    total = len(comments)
    unresolved = sum(1 for c in comments if not c.get('resolved', False))

    for line in stdout.split('\n'):
        if line.startswith('provider:'):
            provider = line.split(':', 1)[1].strip()
        elif line.startswith('total:'):
            try:
                total = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith('unresolved:'):
            try:
                unresolved = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass

    return {
        'pr_number': pr_number,
        'provider': provider,
        'comments': comments,
        'total_comments': total,
        'unresolved_count': unresolved,
        'status': 'success',
    }


def cmd_fetch_comments(args):
    """Handle fetch-comments subcommand."""
    # Determine PR number
    pr_number = args.pr
    if not pr_number:
        pr_number = get_current_pr_number()
        if not pr_number:
            print(
                serialize_toon(
                    {'error': 'No PR found for current branch. Use --pr to specify.', 'status': 'failure'}
                )
            )
            return 1

    result = fetch_comments(pr_number, getattr(args, 'unresolved_only', False))
    print(serialize_toon(result))

    return 0 if result.get('status') == 'success' else 1


# ============================================================================
# TRIAGE SUBCOMMAND
# ============================================================================


def classify_comment(body: str) -> tuple[str, str, str]:
    """Classify comment and determine action and priority."""
    body_lower = body.lower()

    # Check for ignore patterns first
    for pattern in PATTERNS['ignore']:
        if re.search(pattern, body_lower):
            return 'ignore', 'none', 'Automated or acknowledgment comment'

    # Check for code change patterns with priority
    for priority in ['high', 'medium', 'low']:
        for pattern in PATTERNS['code_change'][priority]:
            if re.search(pattern, body_lower):
                return 'code_change', priority, f'Matches {priority} priority pattern: {pattern}'

    # Check for explanation patterns
    for pattern in PATTERNS['explain']:
        if re.search(pattern, body_lower):
            return 'explain', 'low', 'Question or clarification request'

    # Default to code_change with low priority if none match
    if len(body) > 50:  # Substantial comment likely needs attention
        return 'code_change', 'low', 'Substantial review comment requires attention'

    return 'ignore', 'none', 'Brief comment with no actionable content'


def suggest_implementation(action: str, body: str, path: str | None, line: int | None) -> str | None:
    """Generate implementation suggestion based on action type."""
    if action == 'ignore':
        return None

    if action == 'explain':
        return f'Reply to comment at {path}:{line} with explanation of design decision'

    # For code_change, try to extract specific action
    body_lower = body.lower()

    if 'add' in body_lower:
        return f'Add requested code/functionality at {path}:{line}'
    elif 'remove' in body_lower or 'delete' in body_lower:
        return f'Remove indicated code at {path}:{line}'
    elif 'rename' in body_lower:
        return f'Rename as suggested at {path}:{line}'
    elif 'fix' in body_lower:
        return f'Fix the issue indicated at {path}:{line}'
    else:
        return f'Review and address comment at {path}:{line}'


def triage_comment(comment: dict) -> dict:
    """Triage a single comment and return decision."""
    comment_id = comment.get('id', 'unknown')
    body = comment.get('body', '')
    path = comment.get('path')
    line = comment.get('line')
    author = comment.get('author', 'unknown')

    if not body:
        return {
            'comment_id': comment_id,
            'action': 'ignore',
            'reason': 'Empty comment body',
            'priority': 'none',
            'suggested_implementation': None,
            'status': 'success',
        }

    action, priority, reason = classify_comment(body)
    suggestion = suggest_implementation(action, body, path, line)

    return {
        'comment_id': comment_id,
        'author': author,
        'action': action,
        'reason': reason,
        'priority': priority,
        'location': f'{path}:{line}' if path and line else None,
        'suggested_implementation': suggestion,
        'status': 'success',
    }


def cmd_triage(args):
    """Handle triage subcommand."""
    try:
        comment = json.loads(args.comment)
    except json.JSONDecodeError as e:
        print(serialize_toon({'error': f'Invalid JSON input: {e}', 'status': 'failure'}))
        return 1

    result = triage_comment(comment)
    print(serialize_toon(result))

    return 0 if result.get('status') == 'success' else 1


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='PR workflow operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pr.py fetch-comments --pr 123
  pr.py triage --comment '{"id":"C1","body":"Please fix this"}'
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # fetch-comments subcommand
    fetch_parser = subparsers.add_parser('fetch-comments', help='Fetch PR review comments (GitHub/GitLab)')
    fetch_parser.add_argument('--pr', type=int, help="PR number (default: current branch's PR)")
    fetch_parser.add_argument('--unresolved-only', action='store_true', help='Only return unresolved comments')
    fetch_parser.set_defaults(func=cmd_fetch_comments)

    # triage subcommand
    triage_parser = subparsers.add_parser('triage', help='Triage a single PR review comment')
    triage_parser.add_argument('--comment', required=True, help='JSON string with comment data')
    triage_parser.set_defaults(func=cmd_triage)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
