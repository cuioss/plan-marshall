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
import re
import subprocess
import sys
from typing import Any

from toon_parser import parse_toon, parse_toon_table, serialize_toon  # type: ignore[import-not-found]
from triage_helpers import cmd_triage_batch_handler, cmd_triage_single  # type: ignore[import-not-found]

# ============================================================================
# TRIAGE CONFIGURATION
# ============================================================================

# Patterns for classification
PATTERNS: dict[str, Any] = {
    'code_change': {
        'high': [
            r'\bsecurity\b',
            r'\bvulnerability\b',
            r'\binjection\b',
            r'\bxss\b',
            r'\bcsrf\b',
            r'\bbug\b',
            r'\berror\b',
            r'\bfix\b',
            r'\bbroken\b',
            r'\bcrash\b',
            r'\bnull pointer\b',
            r'\bmemory leak\b',
        ],
        'medium': [
            r'please\s+(?:add|remove|change|fix|update)\b',
            r'should\s+(?:be|have|use)\b',
            r'\bmissing\b',
            r'\bincorrect\b',
            r'\bwrong\b',
        ],
        'low': [r'\brenam(?:e|ing)\b', r'\bvariable name\b', r'\bnaming\b', r'\btypo\b', r'\bspelling\b', r'\bformatting\b', r'\bstyle\b', r'^nit:', r'^nitpick:'],
    },
    'explain': [r'\bwhy\b', r'\bexplain\b', r'\breasoning\b', r'\brationale\b', r'\bhow does\b', r'\bwhat is\b', r'\bcan you clarify\b'],
    'ignore': [r'^lgtm', r'^approved', r'\blooks good\b', r'^nice\b', r'^thanks\b', r'\[bot\]'],
}


# ============================================================================
# FETCH-COMMENTS SUBCOMMAND (Provider-Agnostic via ci router)
# ============================================================================

# CI router command prefix — the ci.py router reads ci.provider from marshal.json
# and delegates to the correct provider script (github.py or gitlab.py).
#
# NOTE: run_command() shells out to the CI router directly instead of going through
# the executor. This is intentional — fetch-comments runs as a subprocess of the
# executor itself, so re-entering the executor would create circular invocations.
CI_ROUTER = 'python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci'


def run_command(cmd: str, extra_args: list[str] | None = None) -> tuple[str, str, int]:
    """Run a shell command and return stdout, stderr, return code."""
    full_cmd = cmd
    if extra_args:
        full_cmd = f'{cmd} {" ".join(extra_args)}'

    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=120)
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


def parse_comments_output(stdout: str, pr_number: int) -> dict[str, Any]:
    """Parse TOON output from CI router into structured comment data.

    Separated from fetch_comments() for testability.
    """
    parsed = parse_toon(stdout)
    comments = parse_toon_table(stdout, 'comments', null_markers={'-'})

    provider = parsed.get('provider', 'unknown')
    total = parsed.get('total', len(comments))
    unresolved = parsed.get('unresolved', sum(1 for c in comments if not c.get('resolved', False)))

    return {
        'pr_number': pr_number,
        'provider': provider,
        'comments': comments,
        'total_comments': total,
        'unresolved_count': unresolved,
        'status': 'success',
    }


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

    return parse_comments_output(stdout, pr_number)


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
    """Classify comment and determine action and priority.

    Priority order: ignore → code_change → explain → default.
    Code change is checked before explain so that actionable requests
    like "Can you fix X?" are classified as code changes, not questions.
    """
    body_lower = body.lower()

    # Check for ignore patterns first
    for pattern in PATTERNS['ignore']:
        if re.search(pattern, body_lower):
            return 'ignore', 'none', 'Automated or acknowledgment comment'

    # Check for code change patterns first — actionable requests take
    # priority over questions. "Can you fix X?" is a code_change, not explain.
    for priority in ['high', 'medium', 'low']:
        for pattern in PATTERNS['code_change'][priority]:
            if re.search(pattern, body_lower):
                return 'code_change', priority, f'Matches {priority} priority pattern: {pattern}'

    # Check for explanation patterns — only after ruling out code_change,
    # so "Why did you fix it this way?" is correctly classified as explain
    # rather than matching "fix" as code_change first (handled above) or
    # matching "?" and missing code_change intent.
    for pattern in PATTERNS['explain']:
        if re.search(pattern, body_lower):
            return 'explain', 'low', 'Question or clarification request'

    # Standalone question mark — comment is a question but doesn't match
    # explicit explain keywords. Check after code_change and explain patterns.
    if '?' in body_lower:
        return 'explain', 'low', 'Question or clarification request'

    # Default: review comment without clear action signal
    if len(body) > 100:
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
    return cmd_triage_single(args.comment, triage_comment)


def cmd_triage_batch(args):
    """Handle triage-batch subcommand — triage multiple comments at once."""
    return cmd_triage_batch_handler(args.comments, triage_comment, ['code_change', 'explain', 'ignore'])


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

    # triage-batch subcommand
    batch_parser = subparsers.add_parser('triage-batch', help='Triage multiple PR review comments at once')
    batch_parser.add_argument('--comments', required=True, help='JSON array of comment objects')
    batch_parser.set_defaults(func=cmd_triage_batch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
