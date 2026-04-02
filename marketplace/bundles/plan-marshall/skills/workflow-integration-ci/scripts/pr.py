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
import sys
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    cmd_triage_batch_handler,
    cmd_triage_single,
    make_error,
    safe_main,
)

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
# FETCH-COMMENTS SUBCOMMAND (Provider-Agnostic via direct import)
# ============================================================================

# Provider resolution — imports ci.py's get_provider() to determine which
# provider module to use, then imports the data-returning functions directly.
# This avoids the previous subprocess chain (executor → pr.py → executor → ci.py)
# while maintaining provider abstraction.


def _get_provider_module():
    """Resolve the CI provider and return the provider module.

    Returns the provider module (github or gitlab), or None if not configured.

    Contract: The returned module must expose these functions:
    - view_pr_data() -> dict with 'status', 'pr_number' keys
    - fetch_pr_comments_data(pr_number: int, unresolved_only: bool) -> dict with 'status', 'comments', 'total', 'unresolved' keys
    If tools-integration-ci refactors these, pr.py must be updated in lockstep.
    """
    try:
        from ci import get_provider  # type: ignore[import-not-found]
    except ImportError as e:
        print(f'WARNING: Cannot import ci module from tools-integration-ci: {e}', file=sys.stderr)
        return None

    provider = get_provider()
    try:
        if provider == 'github':
            import github as mod  # type: ignore[import-not-found]
        elif provider == 'gitlab':
            import gitlab as mod  # type: ignore[import-not-found]
        else:
            return None
    except ImportError as e:
        print(f'WARNING: Cannot import {provider} module from tools-integration-ci: {e}', file=sys.stderr)
        return None

    # Validate contract: ensure required functions exist
    for fn_name in ('view_pr_data', 'fetch_pr_comments_data'):
        if not hasattr(mod, fn_name):
            print(f'WARNING: {provider} module missing required function {fn_name}', file=sys.stderr)
            return None

    return mod


def get_current_pr_number() -> int | None:
    """Get PR number for current branch via provider's view_pr_data()."""
    mod = _get_provider_module()
    if not mod:
        return None

    result = mod.view_pr_data()
    if result.get('status') != 'success':
        return None

    pr_number = result.get('pr_number')
    if pr_number is None or pr_number == 'unknown':
        return None
    try:
        return int(pr_number)
    except (ValueError, TypeError):
        return None


def fetch_comments(pr_number: int, unresolved_only: bool = False) -> dict[str, Any]:
    """Fetch review comments for a PR via provider's fetch_pr_comments_data()."""
    mod = _get_provider_module()
    if not mod:
        return make_error('CI provider not configured. Run /marshall-steward first.', code=ErrorCode.PROVIDER_NOT_CONFIGURED)

    result = mod.fetch_pr_comments_data(pr_number, unresolved_only)

    if result.get('status') != 'success':
        return make_error(result.get('error', 'Failed to fetch PR comments'))

    # Transform provider result into pr.py's expected format
    return {
        'pr_number': pr_number,
        'provider': result.get('provider', 'unknown'),
        'comments': result.get('comments', []),
        'total_comments': result.get('total', 0),
        'unresolved_count': result.get('unresolved', 0),
        'status': 'success',
    }


def cmd_fetch_comments(args):
    """Handle fetch-comments subcommand."""
    # Determine PR number
    pr_number = args.pr
    if not pr_number:
        pr_number = get_current_pr_number()
        if not pr_number:
            print(serialize_toon(make_error('No PR found for current branch. Use --pr to specify.', code=ErrorCode.NOT_FOUND)))
            return 1

    result = fetch_comments(pr_number, getattr(args, 'unresolved_only', False))
    print(serialize_toon(result))

    return 0 if result.get('status') == 'success' else 1


# ============================================================================
# TRIAGE SUBCOMMAND
# ============================================================================


def classify_comment(body: str, context: str | None = None) -> tuple[str, str, str]:
    """Classify comment and determine action and priority.

    Priority order: code_change(high) → code_change(medium/low) → ignore → explain → default.
    High-priority code changes (security, bugs) always win. Then actionable
    requests. Ignore patterns are checked after code_change so that comments
    like "LGTM, but please fix the typo" are classified as code_change, not
    swallowed by the ignore match on "lgtm".

    Args:
        body: Comment body text.
        context: Optional surrounding code context for better classification.
            When provided, helps disambiguate comments that reference code patterns.
    """
    body_lower = body.lower()

    # Check for code change patterns FIRST — actionable requests take
    # priority over ignore/explain. This ensures "LGTM, but please fix
    # the typo" is classified as code_change, not swallowed by ignore.
    for priority in ['high', 'medium', 'low']:
        for pattern in PATTERNS['code_change'][priority]:
            if re.search(pattern, body_lower):
                return 'code_change', priority, f'Matches {priority} priority pattern: {pattern}'

    # Check for ignore patterns AFTER code_change — pure acknowledgments
    # with no actionable content.
    for pattern in PATTERNS['ignore']:
        if re.search(pattern, body_lower):
            return 'ignore', 'none', 'Automated or acknowledgment comment'

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

    # Context-aware classification: if code context is provided and the
    # comment references specific code patterns, boost to code_change
    if context and len(body) > 20:
        # Comment mentions something visible in the code context —
        # likely a targeted review comment that needs action
        context_lower = context.lower()
        # Extract potential identifiers: words with underscores, dots, parens,
        # or camelCase (mixed upper/lower within a word)
        def _looks_like_identifier(w: str) -> bool:
            clean = w.rstrip('.,;:)')
            if '_' in clean or '.' in clean or '(' in clean:
                return True
            # camelCase: has both upper and lower, at least 4 chars
            if len(clean) >= 4 and any(c.isupper() for c in clean[1:]) and any(c.islower() for c in clean):
                return True
            return False

        code_refs = [w for w in body.split() if _looks_like_identifier(w)]
        if any(ref.lower().rstrip('.,;:)') in context_lower for ref in code_refs):
            return 'code_change', 'medium', 'Comment references code identifiers visible in context'

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
    context = comment.get('context')

    if not body:
        return {
            'comment_id': comment_id,
            'action': 'ignore',
            'reason': 'Empty comment body',
            'priority': 'none',
            'suggested_implementation': None,
            'status': 'success',
        }

    action, priority, reason = classify_comment(body, context=context)
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
    # Inject CLI --context into the comment JSON if provided
    if getattr(args, 'context', None):
        try:
            comment = json.loads(args.comment)
            comment['context'] = args.context
            return cmd_triage_single(json.dumps(comment), triage_comment)
        except json.JSONDecodeError:
            pass  # Let cmd_triage_single handle the error
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
    triage_parser.add_argument('--context', help='Surrounding code context for better classification')
    triage_parser.set_defaults(func=cmd_triage)

    # triage-batch subcommand
    batch_parser = subparsers.add_parser('triage-batch', help='Triage multiple PR review comments at once')
    batch_parser.add_argument('--comments', required=True, help='JSON array of comment objects')
    batch_parser.set_defaults(func=cmd_triage_batch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
