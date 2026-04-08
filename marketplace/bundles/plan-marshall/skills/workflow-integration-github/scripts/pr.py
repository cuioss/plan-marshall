#!/usr/bin/env python3
"""
GitHub PR workflow operations - fetch comments and triage them.

Uses github.py directly for GitHub operations (no provider detection needed).

Usage:
    pr.py fetch-comments [--pr <number>] [--unresolved-only]
    pr.py triage --comment <json> [--context <code>]
    pr.py triage-batch --comments <json-array>
    pr.py --help

Subcommands:
    fetch-comments    Fetch PR review comments (GitHub or GitLab via ci router)
    triage           Triage a single PR review comment
    triage-batch     Triage multiple PR review comments at once

Examples:
    # Fetch comments for current branch's PR
    pr.py fetch-comments

    # Fetch comments for specific PR
    pr.py fetch-comments --pr 123

    # Triage a single comment
    pr.py triage --comment '{"id":"C1","body":"Please fix this","path":"src/Main.java","line":42}'

    # Batch triage multiple comments
    pr.py triage-batch --comments '[{"id":"C1","body":"Fix this"},{"id":"C2","body":"LGTM"}]'
"""

import json
import re
import sys
from typing import Any

import github as _github  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    cmd_triage_batch_handler,
    cmd_triage_single,
    compile_patterns_from_config,
    create_workflow_cli,
    load_skill_config,
    make_error,
    parse_json_arg,
    safe_main,
)

# ============================================================================
# TRIAGE CONFIGURATION (loaded from comment-patterns.json)
# ============================================================================

PATTERNS: dict[str, Any] = load_skill_config(__file__, 'comment-patterns.json')

# Configurable thresholds (from comment-patterns.json or defaults)
_THRESHOLDS = PATTERNS.get('thresholds', {})
SUBSTANTIAL_COMMENT_LENGTH: int = _THRESHOLDS.get('substantial_comment_length', 100)
CONTEXT_MATCH_MIN_LENGTH: int = _THRESHOLDS.get('context_match_min_length', 20)

# Pre-compile regex patterns at load time to catch malformed patterns early
# and avoid repeated compilation per classify_comment() call.
_COMPILED_PATTERNS: dict[str, dict[str, list[re.Pattern]]] = {}
for _category in ('code_change', 'explain', 'ignore'):
    _COMPILED_PATTERNS[_category] = {}
    for _priority, _pattern_list in PATTERNS.get(_category, {}).items():
        _COMPILED_PATTERNS[_category][_priority] = compile_patterns_from_config(
            _pattern_list,
            f'comment-patterns.json [{_category}][{_priority}]',
        )


# ============================================================================
# FETCH-COMMENTS SUBCOMMAND (Provider-Agnostic via direct import)
# ============================================================================

def get_current_pr_number() -> int | None:
    """Get PR number for current branch via GitHub's view_pr_data()."""
    result = _github.view_pr_data()
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
    """Fetch review comments for a PR via GitHub's fetch_pr_comments_data()."""

    result = _github.fetch_pr_comments_data(pr_number, unresolved_only)

    if result.get('status') != 'success':
        return make_error(result.get('error', 'Failed to fetch PR comments'), code=ErrorCode.FETCH_FAILURE)

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
            return make_error('No PR found for current branch. Use --pr to specify.', code=ErrorCode.NOT_FOUND)

    result = fetch_comments(pr_number, getattr(args, 'unresolved_only', False))
    return result


# ============================================================================
# TRIAGE SUBCOMMAND
# ============================================================================


CAMEL_CASE_MIN_LENGTH: int = _THRESHOLDS.get('camel_case_min_length', 4)

# Pre-compiled verb patterns for suggest_implementation() — avoids
# re-compiling regex on every call. Checked in specificity order.
_VERB_PATTERNS: list[tuple[list[re.Pattern], str]] = [
    ([re.compile(rf'\b{v}\b') for v in verbs], suggestion)
    for verbs, suggestion in [
        (['rename', 'refactor'], 'Rename/refactor as suggested'),
        (['remove', 'delete', 'drop'], 'Remove indicated code'),
        (['fix', 'resolve', 'correct'], 'Fix the issue indicated'),
        (['add', 'include', 'create'], 'Add requested code/functionality'),
        (['replace', 'swap', 'change', 'update'], 'Update code as requested'),
        (['move', 'extract', 'split'], 'Restructure code as suggested'),
    ]
]


def _looks_like_identifier(w: str) -> bool:
    """Check if a word looks like a code identifier.

    Matches words with underscores, dots, parens, or camelCase
    (mixed upper/lower within a word, configurable min length).
    """
    clean = w.rstrip('.,;:)')
    if '_' in clean or '.' in clean or '(' in clean:
        return True
    # camelCase: has both upper and lower, at least CAMEL_CASE_MIN_LENGTH chars
    if len(clean) >= CAMEL_CASE_MIN_LENGTH and any(c.isupper() for c in clean[1:]) and any(c.islower() for c in clean):
        return True
    return False


def classify_comment(body: str, context: str | None = None) -> dict[str, str]:
    """Classify comment and determine action and priority.

    Returns dict with 'action', 'priority', and 'reason' keys.

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
        for compiled in _COMPILED_PATTERNS['code_change'].get(priority, []):
            if compiled.search(body_lower):
                return {
                    'action': 'code_change',
                    'priority': priority,
                    'reason': f'Matches {priority} priority pattern: {compiled.pattern}',
                }

    # Check for ignore patterns AFTER code_change — pure acknowledgments
    # with no actionable content.
    for priority, compiled_list in _COMPILED_PATTERNS['ignore'].items():
        for compiled in compiled_list:
            if compiled.search(body_lower):
                return {'action': 'ignore', 'priority': priority, 'reason': 'Automated or acknowledgment comment'}

    # Check for explanation patterns — only after ruling out code_change,
    # so "Why did you fix it this way?" is correctly classified as explain
    # rather than matching "fix" as code_change first (handled above) or
    # matching "?" and missing code_change intent.
    for priority, compiled_list in _COMPILED_PATTERNS['explain'].items():
        for compiled in compiled_list:
            if compiled.search(body_lower):
                return {'action': 'explain', 'priority': priority, 'reason': 'Question or clarification request'}

    # Standalone question mark — comment is a question but doesn't match
    # explicit explain keywords. Check after code_change and explain patterns.
    if '?' in body_lower:
        return {'action': 'explain', 'priority': 'low', 'reason': 'Question or clarification request'}

    # Context-aware classification: if code context is provided and the
    # comment references specific code patterns, boost to code_change
    if context and len(body) > CONTEXT_MATCH_MIN_LENGTH:
        # Comment mentions something visible in the code context —
        # likely a targeted review comment that needs action
        context_lower = context.lower()
        code_refs = [w for w in body.split() if _looks_like_identifier(w)]
        if any(ref.lower().rstrip('.,;:)') in context_lower for ref in code_refs):
            return {
                'action': 'code_change',
                'priority': 'medium',
                'reason': 'Comment references code identifiers visible in context',
            }

    # Default: review comment without clear action signal.
    # Longer comments (>100 chars) likely contain substantive feedback that
    # warrants attention even without keyword matches. Short comments without
    # recognizable patterns are typically drive-by acknowledgments.
    if len(body) > SUBSTANTIAL_COMMENT_LENGTH:
        return {
            'action': 'code_change',
            'priority': 'low',
            'reason': f'Substantial review comment (>{SUBSTANTIAL_COMMENT_LENGTH} chars) requires attention',
        }

    return {'action': 'ignore', 'priority': 'low', 'reason': 'Brief comment with no actionable content'}


def suggest_implementation(action: str, body: str, path: str | None, line: int | None) -> str | None:
    """Generate implementation suggestion based on action type.

    For code_change actions, extracts the most specific verb from the comment
    body to produce a targeted suggestion. Falls back to a generic review
    prompt when no verb is detected.
    """
    if action == 'ignore':
        return None

    location = f'{path}:{line}' if path and line is not None else (path or 'unspecified location')

    if action == 'explain':
        return f'Reply to comment at {location} with explanation of design decision'

    # For code_change, extract the most specific action verb from the body.
    # Uses word boundary matching to avoid false positives (e.g., "prefix" matching "fix").
    # Checked in specificity order: targeted verbs first, then generic ones.
    # Patterns are pre-compiled at module level (_VERB_PATTERNS) for performance.
    body_lower = body.lower()
    for compiled_patterns, suggestion in _VERB_PATTERNS:
        if any(p.search(body_lower) for p in compiled_patterns):
            return f'{suggestion} at {location}'

    return f'Review and address comment at {location}'


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
            'priority': 'low',
            'suggested_implementation': None,
            'status': 'success',
        }

    classification = classify_comment(body, context=context)
    action = classification['action']
    priority = classification['priority']
    reason = classification['reason']
    suggestion = suggest_implementation(action, body, path, line)

    return {
        'comment_id': comment_id,
        'author': author,
        'action': action,
        'reason': reason,
        'priority': priority,
        'location': f'{path}:{line}' if path and line is not None else None,
        'suggested_implementation': suggestion,
        'status': 'success',
    }


def cmd_triage(args):
    """Handle triage subcommand."""
    # Inject CLI --context into the comment JSON if provided
    if getattr(args, 'context', None):
        comment, rc = parse_json_arg(args.comment, '--comment')
        if not rc and isinstance(comment, dict):
            comment['context'] = args.context
            return cmd_triage_single(json.dumps(comment), triage_comment)
        # On parse failure, fall through to cmd_triage_single which reports the error
    return cmd_triage_single(args.comment, triage_comment)


def cmd_triage_batch(args):
    """Handle triage-batch subcommand — triage multiple comments at once."""
    return cmd_triage_batch_handler(args.comments, triage_comment, ['code_change', 'explain', 'ignore'])


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = create_workflow_cli(
        description='PR workflow operations',
        epilog="""
Examples:
  pr.py fetch-comments --pr 123
  pr.py triage --comment '{"id":"C1","body":"Please fix this"}'
""",
        subcommands=[
            {
                'name': 'fetch-comments',
                'help': 'Fetch PR review comments (GitHub/GitLab)',
                'handler': cmd_fetch_comments,
                'args': [
                    {'flags': ['--pr'], 'type': int, 'help': "PR number (default: current branch's PR)"},
                    {'flags': ['--unresolved-only'], 'action': 'store_true', 'help': 'Only return unresolved comments'},
                ],
            },
            {
                'name': 'triage',
                'help': 'Triage a single PR review comment',
                'handler': cmd_triage,
                'args': [
                    {'flags': ['--comment'], 'required': True, 'help': 'JSON string with comment data'},
                    {'flags': ['--context'], 'help': 'Surrounding code context for better classification'},
                ],
            },
            {
                'name': 'triage-batch',
                'help': 'Triage multiple PR review comments at once',
                'handler': cmd_triage_batch,
                'args': [{'flags': ['--comments'], 'required': True, 'help': 'JSON array of comment objects'}],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon  # type: ignore[import-not-found]

    return _output_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
