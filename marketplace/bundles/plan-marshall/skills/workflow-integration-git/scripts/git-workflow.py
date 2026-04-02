#!/usr/bin/env python3
"""
Git workflow operations - format commits and analyze diffs.

Usage:
    git-workflow.py format-commit --type <type> --subject <subject> [options]
    git-workflow.py analyze-diff --file <diff-file>
    git-workflow.py detect-artifacts [--root <dir>]
    git-workflow.py --help

Subcommands:
    format-commit      Format commit message following conventional commits
    analyze-diff       Analyze diff file to suggest commit message
    detect-artifacts   Scan for committable artifacts (build outputs, temp files)

Examples:
    # Format a commit message
    git-workflow.py format-commit --type feat --scope auth --subject "add login flow"

    # Analyze a diff for commit suggestions
    git-workflow.py analyze-diff --file changes.diff

    # Detect artifacts before committing
    git-workflow.py detect-artifacts --root /path/to/repo
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from toon_parser import serialize_toon  # type: ignore[import-not-found]
from triage_helpers import ErrorCode, make_error, safe_main  # type: ignore[import-not-found]

# ============================================================================
# CONFIGURATION
# ============================================================================

VALID_TYPES = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore', 'ci']
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

    # Check imperative mood (basic check with false-positive allow-list)
    first_word = subject.split()[0].lower() if subject.split() else ''
    # Words ending in -ed/-ing that are NOT past tense/gerund forms
    imperative_allowlist = {
        'red', 'bed', 'shed', 'led', 'fed', 'sled', 'med', 'wed',
        'string', 'ring', 'bring', 'king', 'swing', 'thing', 'spring', 'ping',
        'caching', 'hashing', 'nothing', 'everything', 'something',
        'mixed', 'embed', 'spread', 'thread', 'overhead',
    }
    if first_word not in imperative_allowlist:
        if first_word.endswith('ed') and len(first_word) > 2:
            warnings.append("Subject should use imperative mood (e.g., 'add' not 'added')")
        elif first_word.endswith('ing') and len(first_word) > 3:
            warnings.append("Subject should use imperative mood (e.g., 'add' not 'adding')")

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
    """Wrap text at specified width, preserving leading indentation."""
    lines = []
    for paragraph in text.split('\n'):
        if len(paragraph) <= width:
            lines.append(paragraph)
        else:
            # Preserve leading whitespace (for bullet lists, indented blocks)
            stripped = paragraph.lstrip()
            indent = paragraph[: len(paragraph) - len(stripped)]
            effective_width = width - len(indent)
            if effective_width < 20:
                # Indent too deep to wrap meaningfully — keep as-is
                lines.append(paragraph)
                continue
            words = stripped.split()
            current_line: list[str] = []
            current_length = 0
            for word in words:
                if current_length + len(word) + 1 <= effective_width:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    lines.append(indent + ' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            if current_line:
                lines.append(indent + ' '.join(current_line))
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

    # Co-Authored-By is NOT appended here — the caller (workflow Step 5
    # or git commit command) adds it so the footer matches the project's
    # configured format (see CLAUDE.md) and isn't duplicated.

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

    # Analyze file paths — support Maven, Python, JS, and generic layouts
    src_files = [
        f for f in files_changed
        if '/src/' in f or f.startswith('src/') or f.endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))
    ]
    test_files = [
        f
        for f in files_changed
        if '/test/' in f or '/tests/' in f or '/__tests__/' in f or 'Test' in f
        or f.startswith('test_') or f.startswith('test/') or f.startswith('tests/')
    ]
    doc_files = [f for f in files_changed if f.endswith(('.md', '.adoc', '.txt', '.rst'))]
    ci_files = [
        f
        for f in files_changed
        if f.startswith('.github/') or f.startswith('.gitlab-ci') or f.startswith('.circleci/')
        or f in ('Jenkinsfile', '.travis.yml', 'azure-pipelines.yml')
        or '/ci/' in f
    ]

    # Detect scope from common path — try multiple project layouts
    if src_files:
        paths = [f.split('/') for f in src_files]
        scope_found = False
        # Monorepo prefixes: packages/<name>/..., modules/<name>/..., apps/<name>/...
        monorepo_roots = {'packages', 'modules', 'apps', 'libs', 'services'}
        for path in paths:
            if scope_found:
                break
            # Monorepo: packages/<name>/src/... or modules/<name>/...
            if len(path) > 1 and path[0] in monorepo_roots:
                suggestions['scope'] = path[1]
                scope_found = True
            # Maven/Gradle: src/main/java/<package>/...
            elif 'main' in path:
                idx = path.index('main')
                if idx + 2 < len(path):
                    suggestions['scope'] = path[idx + 2]
                    scope_found = True
            # Python: <package>/*.py or src/<package>/*.py
            elif any(p.endswith('.py') for p in path):
                # Use first directory component (or second if src/)
                start = 1 if path[0] == 'src' else 0
                if start < len(path) - 1:
                    suggestions['scope'] = path[start]
                    scope_found = True
            # JS/TS: src/<component>/*.{js,ts,jsx,tsx}
            elif path[0] == 'src' and len(path) > 2:
                suggestions['scope'] = path[1]
                scope_found = True
            # Generic: use top-level directory
            elif len(path) > 1:
                suggestions['scope'] = path[0]
                scope_found = True

    # Detect type
    additions = len(re.findall(r'^\+[^+]', diff_content, re.MULTILINE))
    deletions = len(re.findall(r'^-[^-]', diff_content, re.MULTILINE))

    # Bug fix indicators — check diff metadata, comments, and added/removed lines.
    # Use word boundaries to avoid matching identifiers like errorHandler, fixedWidth.
    bug_pattern = r'\b(fix(?:es|ed)?|bug|bugfix)\b'
    # Primary: diff metadata lines (high confidence)
    diff_headers = '\n'.join(
        line for line in diff_content.split('\n') if line.startswith(('@@', '---', '+++', 'diff '))
    )
    # Secondary: comment lines in added/removed code (medium confidence)
    comment_lines = '\n'.join(
        line
        for line in diff_content.split('\n')
        if (line.startswith('+') or line.startswith('-'))
        and ('// ' in line or '# ' in line or '/* ' in line or '* ' in line)
    )
    if re.search(bug_pattern, diff_headers, re.IGNORECASE) or re.search(
        bug_pattern, comment_lines, re.IGNORECASE
    ):
        suggestions['type'] = 'fix'
        detected_changes.append('Bug fix patterns detected in diff context')

    # CI configuration changes
    elif ci_files and not src_files:
        suggestions['type'] = 'ci'
        detected_changes.append('CI configuration files modified')

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

    # Refactoring — when additions and deletions are roughly balanced (within 30%
    # of the smaller count), the change is likely restructuring existing code rather
    # than adding or removing functionality. The 0.3 threshold was chosen empirically:
    # pure renames have 0% delta, real refactors rarely exceed 30%, while features
    # typically add 2x+ more lines than they remove.
    elif abs(additions - deletions) < min(additions, deletions) * 0.3:
        suggestions['type'] = 'refactor'
        detected_changes.append('Similar additions/deletions suggests refactoring')

    # Fallback scope: if no scope found from src_files, use top-level directory
    # of first changed file (when it has a directory component)
    if suggestions['scope'] is None and files_changed:
        parts = files_changed[0].split('/')
        if len(parts) > 1:
            suggestions['scope'] = parts[0]

    suggestions['files_changed'] = files_changed[:10]  # Limit to 10

    return suggestions


def cmd_analyze_diff(args):
    """Handle analyze-diff subcommand."""
    path = Path(args.file)
    if not path.exists():
        print(serialize_toon(make_error(f'File not found: {args.file}', code=ErrorCode.NOT_FOUND)))
        return 1

    diff_content = path.read_text()
    suggestions = analyze_diff(diff_content)

    print(serialize_toon({'mode': 'analysis', 'suggestions': suggestions, 'status': 'success'}))
    return 0


# ============================================================================
# DETECT-ARTIFACTS SUBCOMMAND
# ============================================================================

# Patterns that are always safe to delete (never belong in a commit)
SAFE_ARTIFACT_PATTERNS = [
    # Java
    '**/*.class',
    # Python
    '**/*.pyc',
    '**/__pycache__/**',
    '**/*.egg-info/**',
    '**/.eggs/**',
    # Node.js / TypeScript
    '**/*.tsbuildinfo',
    # General temp/backup
    '**/*.temp',
    '**/*.backup',
    '**/*.backup*',
    '**/*.orig',
    # OS artifacts
    '**/.DS_Store',
    # Plan temp (explicitly temporary)
    '.plan/temp/**',
]

# Patterns that require user confirmation before deletion
UNCERTAIN_ARTIFACT_PATTERNS = [
    'target/**',
    'build/**',
    'dist/**',
    '.next/**',
    'node_modules/**',
]


def get_gitignored_files(root: Path) -> set[str]:
    """Return set of relative paths that are gitignored under root.

    Uses `git check-ignore` to respect .gitignore rules. Returns empty set
    if not inside a git repo or git is unavailable.
    """
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--others', '--ignored', '--exclude-standard'],
            capture_output=True, text=True, timeout=30, cwd=str(root),
        )
        if result.returncode != 0:
            return set()
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
        return set()


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    """Compile glob-style patterns into regex for single-pass matching."""
    compiled = []
    for pattern in patterns:
        # Convert glob to regex: ** → .*, * → [^/]*, . → \.
        # Use placeholder to prevent ** → .* → .[^/]* double-replacement
        regex = pattern.replace('.', r'\.')
        regex = regex.replace('**/', '(.+/)?')
        regex = regex.replace('**', '\x00STAR\x00')
        regex = regex.replace('*', '[^/]*')
        regex = regex.replace('\x00STAR\x00', '.*')
        compiled.append(re.compile(f'^{regex}$'))
    return compiled


_SAFE_REGEXES = _compile_patterns(SAFE_ARTIFACT_PATTERNS)
_UNCERTAIN_REGEXES = _compile_patterns(UNCERTAIN_ARTIFACT_PATTERNS)


def scan_artifacts(root: Path, respect_gitignore: bool = True) -> dict:
    """Scan directory for committable artifacts.

    Returns dict with 'safe' (auto-deletable) and 'uncertain' (needs confirmation) lists.
    Files already covered by .gitignore are excluded by default since they
    cannot be accidentally committed.

    Uses a single directory traversal with compiled regex patterns instead
    of multiple Path.glob() calls, improving performance on large repos.
    """
    ignored = get_gitignored_files(root) if respect_gitignore else set()

    safe: list[str] = []
    uncertain: list[str] = []
    safe_set: set[str] = set()

    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if rel in ignored:
            continue

        # Check safe patterns first
        if any(rx.match(rel) for rx in _SAFE_REGEXES):
            safe.append(rel)
            safe_set.add(rel)
        elif any(rx.match(rel) for rx in _UNCERTAIN_REGEXES):
            uncertain.append(rel)

    return {
        'safe': sorted(safe),
        'uncertain': sorted(uncertain),
        'total': len(safe) + len(uncertain),
    }


def cmd_detect_artifacts(args):
    """Handle detect-artifacts subcommand."""
    root = Path(args.root) if args.root else Path.cwd()

    if not root.is_dir():
        print(serialize_toon(make_error(f'Directory not found: {root}', code=ErrorCode.NOT_FOUND)))
        return 1

    result = scan_artifacts(root, respect_gitignore=not args.no_gitignore)
    result['root'] = str(root)
    result['status'] = 'success'
    print(serialize_toon(result))
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
  git-workflow.py detect-artifacts --root /path/to/repo
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

    # detect-artifacts subcommand
    artifacts_parser = subparsers.add_parser('detect-artifacts', help='Scan for committable artifacts')
    artifacts_parser.add_argument('--root', help='Root directory to scan (default: cwd)')
    artifacts_parser.add_argument('--no-gitignore', action='store_true', help='Include gitignored files in results')
    artifacts_parser.set_defaults(func=cmd_detect_artifacts)

    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(safe_main(main))
