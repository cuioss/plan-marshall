#!/usr/bin/env python3
"""
Git workflow operations - format commits and analyze diffs.

Usage:
    git-workflow.py format-commit --type <type> --subject <subject> [options]
    git-workflow.py analyze-diff --file <diff-file>
    git-workflow.py --help

Subcommands:
    format-commit    Format commit message following conventional commits
    analyze-diff     Analyze diff file to suggest commit message

Examples:
    # Format a commit message
    git-workflow.py format-commit --type feat --scope auth --subject "add login flow"

    # Analyze a diff for commit suggestions
    git-workflow.py analyze-diff --file changes.diff
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]

# ============================================================================
# CONFIGURATION
# ============================================================================

VALID_TYPES = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore']
TYPE_PRIORITY = {t: i for i, t in enumerate(VALID_TYPES)}


# ============================================================================
# VALIDATION
# ============================================================================


def validate_subject(subject: str) -> dict:
    """Validate commit subject."""
    warnings = []
    valid = True

    if not subject:
        return {'valid': False, 'warnings': ['Subject is required']}

    # Check length
    if len(subject) > 50:
        warnings.append(f'Subject exceeds 50 chars ({len(subject)} chars)')
    if len(subject) > 72:
        valid = False
        warnings.append('Subject must not exceed 72 chars')

    # Check imperative mood (basic check)
    past_tense_endings = ['ed', 'ing']
    first_word = subject.split()[0].lower() if subject.split() else ''
    if any(first_word.endswith(e) for e in past_tense_endings):
        warnings.append("Subject should use imperative mood (e.g., 'add' not 'added')")

    # Check case
    if subject[0].isupper():
        warnings.append('Subject should start with lowercase')

    # Check period
    if subject.endswith('.'):
        warnings.append('Subject should not end with period')

    return {'valid': valid, 'warnings': warnings}


def validate_type(commit_type: str) -> dict:
    """Validate commit type."""
    if commit_type not in VALID_TYPES:
        return {'valid': False, 'warnings': [f"Invalid type '{commit_type}'. Valid types: {', '.join(VALID_TYPES)}"]}
    return {'valid': True, 'warnings': []}


# ============================================================================
# FORMATTING
# ============================================================================


def wrap_text(text: str, width: int) -> str:
    """Wrap text at specified width."""
    lines = []
    for paragraph in text.split('\n'):
        if len(paragraph) <= width:
            lines.append(paragraph)
        else:
            words = paragraph.split()
            current_line = []
            current_length = 0
            for word in words:
                if current_length + len(word) + 1 <= width:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            if current_line:
                lines.append(' '.join(current_line))
    return '\n'.join(lines)


def format_message(
    commit_type: str,
    scope: str,
    subject: str,
    body: str | None = None,
    breaking: str | None = None,
    footer: str | None = None,
) -> str:
    """Format complete commit message."""
    # Header
    breaking_indicator = '!' if breaking else ''
    if scope:
        header = f'{commit_type}({scope}){breaking_indicator}: {subject}'
    else:
        header = f'{commit_type}{breaking_indicator}: {subject}'

    # Build message parts
    parts = [header]

    if body:
        parts.append('')  # Blank line
        # Wrap body at 72 chars
        wrapped_body = wrap_text(body, 72)
        parts.append(wrapped_body)

    if breaking or footer:
        parts.append('')  # Blank line
        if breaking:
            parts.append(f'BREAKING CHANGE: {breaking}')
        if footer:
            parts.append(footer)

    # Add Claude footer
    parts.append('')
    parts.append('🤖 Generated with [Claude Code](https://claude.com/claude-code)')
    parts.append('')
    parts.append('Co-Authored-By: Claude <noreply@anthropic.com>')

    return '\n'.join(parts)


# ============================================================================
# FORMAT-COMMIT SUBCOMMAND
# ============================================================================


def cmd_format_commit(args):
    """Handle format-commit subcommand."""
    # Validate inputs
    type_validation = validate_type(args.commit_type)
    subject_validation = validate_subject(args.subject)

    all_warnings = type_validation['warnings'] + subject_validation['warnings']
    is_valid = type_validation['valid'] and subject_validation['valid']

    # Format message
    formatted = format_message(args.commit_type, args.scope, args.subject, args.body, args.breaking, args.footer)

    result = {
        'type': args.commit_type,
        'scope': args.scope,
        'subject': args.subject,
        'body': args.body,
        'breaking': args.breaking,
        'footer': args.footer,
        'formatted_message': formatted,
        'validation': {'valid': is_valid, 'warnings': all_warnings},
        'status': 'success',
    }

    print(serialize_toon(result))
    return 0 if is_valid else 1


# ============================================================================
# ANALYZE-DIFF SUBCOMMAND
# ============================================================================


def analyze_diff(diff_content: str) -> dict:
    """Analyze diff content to suggest commit parameters."""
    detected_changes: list[str] = []
    suggestions: dict[str, Any] = {
        'type': 'chore',
        'scope': None,
        'subject': None,
        'detected_changes': detected_changes,
    }

    # Detect file types changed
    files_changed = re.findall(r'^diff --git a/(.+?) b/', diff_content, re.MULTILINE)

    if not files_changed:
        return suggestions

    # Analyze file paths
    src_files = [f for f in files_changed if '/src/' in f]
    test_files = [f for f in files_changed if '/test/' in f or 'Test' in f]
    doc_files = [f for f in files_changed if f.endswith(('.md', '.adoc', '.txt'))]

    # Detect scope from common path
    if src_files:
        paths = [f.split('/') for f in src_files]
        # Find common component
        for path in paths:
            if 'main' in path:
                idx = path.index('main')
                if idx + 2 < len(path):
                    suggestions['scope'] = path[idx + 2]
                    break

    # Detect type
    additions = len(re.findall(r'^\+[^+]', diff_content, re.MULTILINE))
    deletions = len(re.findall(r'^-[^-]', diff_content, re.MULTILINE))

    # Bug fix indicators
    if re.search(r'(fix|bug|error|null|exception)', diff_content, re.IGNORECASE):
        suggestions['type'] = 'fix'
        detected_changes.append('Bug fix patterns detected')

    # Feature indicators
    elif additions > deletions * 2 and src_files:
        suggestions['type'] = 'feat'
        detected_changes.append('Significant new code added')

    # Test changes
    elif test_files and not src_files:
        suggestions['type'] = 'test'
        detected_changes.append('Test files modified')

    # Documentation
    elif doc_files and not src_files:
        suggestions['type'] = 'docs'
        detected_changes.append('Documentation modified')

    # Refactoring
    elif abs(additions - deletions) < min(additions, deletions) * 0.3:
        suggestions['type'] = 'refactor'
        detected_changes.append('Similar additions/deletions suggests refactoring')

    suggestions['files_changed'] = files_changed[:10]  # Limit to 10

    return suggestions


def cmd_analyze_diff(args):
    """Handle analyze-diff subcommand."""
    path = Path(args.file)
    if not path.exists():
        print(serialize_toon({'error': f'File not found: {args.file}', 'status': 'failure'}))
        return 1

    diff_content = path.read_text()
    suggestions = analyze_diff(diff_content)

    print(serialize_toon({'mode': 'analysis', 'suggestions': suggestions, 'status': 'success'}))
    return 0


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Git workflow operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  git-workflow.py format-commit --type feat --scope auth --subject "add login"
  git-workflow.py analyze-diff --file changes.diff
""",
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # format-commit subcommand
    format_parser = subparsers.add_parser('format-commit', help='Format commit message following conventional commits')
    format_parser.add_argument('--type', dest='commit_type', required=True, choices=VALID_TYPES, help='Commit type')
    format_parser.add_argument('--scope', help='Commit scope')
    format_parser.add_argument('--subject', required=True, help='Commit subject')
    format_parser.add_argument('--body', help='Commit body')
    format_parser.add_argument('--breaking', help='Breaking change description')
    format_parser.add_argument('--footer', help='Additional footer')
    format_parser.set_defaults(func=cmd_format_commit)

    # analyze-diff subcommand
    analyze_parser = subparsers.add_parser('analyze-diff', help='Analyze diff file to suggest commit message')
    analyze_parser.add_argument('--file', required=True, help='Diff file to analyze')
    analyze_parser.set_defaults(func=cmd_analyze_diff)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
