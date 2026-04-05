#!/usr/bin/env python3
"""
Git workflow operations - format commits and analyze diffs.

Usage:
    git_workflow.py format-commit --type <type> --subject <subject> [options]
    git_workflow.py analyze-diff --file <diff-file>
    git_workflow.py detect-artifacts [--root <dir>]
    git_workflow.py --help

Subcommands:
    format-commit      Format commit message following conventional commits
    analyze-diff       Analyze diff file to suggest commit message
    detect-artifacts   Scan for committable artifacts (build outputs, temp files)

Examples:
    # Format a commit message
    git_workflow.py format-commit --type feat --scope auth --subject "add login flow"

    # Analyze a diff for commit suggestions
    git_workflow.py analyze-diff --file changes.diff

    # Detect artifacts before committing
    git_workflow.py detect-artifacts --root /path/to/repo
"""

import fnmatch
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    create_workflow_cli,
    is_test_file,
    load_skill_config,
    make_error,
    safe_main,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

_COMMIT_CONFIG = load_skill_config(__file__, 'git-commit-config.json')
VALID_TYPES: list[str] = _COMMIT_CONFIG['valid_types']
_IMPERATIVE_ALLOWLIST: set[str] = set(_COMMIT_CONFIG.get('imperative_allowlist', []))
_SUBJECT_MAX_LENGTH: int = _COMMIT_CONFIG.get('subject_max_length', 72)
_SUBJECT_WARN_LENGTH: int = _COMMIT_CONFIG.get('subject_warn_length', 50)
_MONOREPO_ROOTS: set[str] = set(
    _COMMIT_CONFIG.get(
        'monorepo_roots',
        [
            'packages',
            'modules',
            'apps',
            'libs',
            'services',
        ],
    )
)

_ARTIFACT_CONFIG = load_skill_config(__file__, 'artifact-patterns.json')


# ============================================================================
# VALIDATION
# ============================================================================


def validate_subject(subject: str) -> dict:
    """Validate commit subject."""
    warnings = []
    valid = True

    if not subject:
        return {'valid': False, 'warnings': ['Subject is required']}

    # Check length (thresholds from git-commit-config.json)
    if len(subject) > _SUBJECT_WARN_LENGTH:
        warnings.append(f'Subject exceeds {_SUBJECT_WARN_LENGTH} chars ({len(subject)} chars)')
    if len(subject) > _SUBJECT_MAX_LENGTH:
        valid = False
        warnings.append(f'Subject must not exceed {_SUBJECT_MAX_LENGTH} chars')

    # Check imperative mood (basic check with false-positive allow-list
    # loaded from git-commit-config.json)
    first_word = subject.split()[0].lower() if subject.split() else ''
    if first_word not in _IMPERATIVE_ALLOWLIST:
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
            stripped = paragraph.lstrip()
            indent = paragraph[: len(paragraph) - len(stripped)]
            effective_width = width - len(indent)
            if effective_width < 20:
                lines.append(paragraph)
                continue
            wrapped = textwrap.fill(
                stripped,
                width=effective_width,
                initial_indent='',
                subsequent_indent='',
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.extend(indent + line for line in wrapped.split('\n'))
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
    # Validate scope doesn't contain parentheses (would break header format)
    if scope and ('(' in scope or ')' in scope):
        scope = scope.replace('(', '').replace(')', '')

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


def validate_header_length(commit_type: str, scope: str | None, subject: str, breaking: str | None) -> dict:
    """Validate total header length (type + scope + subject)."""
    warnings = []
    breaking_indicator = '!' if breaking else ''
    if scope:
        header = f'{commit_type}({scope}){breaking_indicator}: {subject}'
    else:
        header = f'{commit_type}{breaking_indicator}: {subject}'
    if len(header) > 72:
        warnings.append(f'Header exceeds 72 chars ({len(header)} chars) — consider shorter scope or subject')
    return {'valid': len(header) <= 72, 'warnings': warnings}


def cmd_format_commit(args):
    """Handle format-commit subcommand."""
    # Validate inputs
    type_validation = validate_type(args.commit_type)
    subject_validation = validate_subject(args.subject)
    header_validation = validate_header_length(args.commit_type, args.scope, args.subject, args.breaking)

    all_warnings = type_validation['warnings'] + subject_validation['warnings'] + header_validation['warnings']
    is_valid = type_validation['valid'] and subject_validation['valid'] and header_validation['valid']

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
        'status': 'success' if is_valid else 'error',
    }

    return result


# ============================================================================
# ANALYZE-DIFF SUBCOMMAND
# ============================================================================


def analyze_diff(diff_content: str) -> dict:
    """Analyze diff content to suggest commit parameters."""
    detected_changes: list[str] = []
    suggestions: dict[str, Any] = {
        'type': 'chore',
        'scope': None,
        'detected_changes': detected_changes,
    }

    # Detect file types changed
    files_changed = re.findall(r'^diff --git a/(.+?) b/', diff_content, re.MULTILINE)

    if not files_changed:
        return suggestions

    # Analyze file paths — support Maven, Python, JS, and generic layouts
    src_files = [
        f
        for f in files_changed
        if '/src/' in f or f.startswith('src/') or f.endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))
    ]
    test_files = [f for f in files_changed if is_test_file(f)]
    doc_files = [f for f in files_changed if f.endswith(('.md', '.adoc', '.txt', '.rst'))]
    ci_files = [
        f
        for f in files_changed
        if f.startswith('.github/')
        or f.startswith('.gitlab-ci')
        or f.startswith('.circleci/')
        or f in ('Jenkinsfile', '.travis.yml', 'azure-pipelines.yml')
        or '/ci/' in f
    ]

    # Detect scope from common path — try multiple project layouts
    if src_files:
        paths = [f.split('/') for f in src_files]
        scope_found = False
        # Monorepo prefixes loaded from git-commit-config.json
        for path in paths:
            if scope_found:
                break
            # Monorepo: packages/<name>/src/... or modules/<name>/...
            if len(path) > 1 and path[0] in _MONOREPO_ROOTS:
                suggestions['scope'] = path[1]
                scope_found = True
            # Maven/Gradle: src/main/java/<package>/...
            elif 'main' in path:
                idx = path.index('main')
                if idx + 2 < len(path):
                    suggestions['scope'] = path[idx + 2]
                    scope_found = True
            # Python: <package>/*.py or src/<package>/*.py
            # Only check the last component (file name) to avoid matching
            # directory names like something.py/
            elif path[-1].endswith('.py'):
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

    # Detect type — count content lines only (exclude diff headers like +++ and ---)
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
    if re.search(bug_pattern, diff_headers, re.IGNORECASE) or re.search(bug_pattern, comment_lines, re.IGNORECASE):
        suggestions['type'] = 'fix'
        detected_changes.append('Bug fix patterns detected in diff context')

    # Performance improvement indicators — check comments for perf keywords
    elif (
        re.search(
            r'\b(perf(?:ormance)?|optimi[zs]e|benchmark|latency|throughput|cache|memoize)\b',
            comment_lines,
            re.IGNORECASE,
        )
        and src_files
    ):
        suggestions['type'] = 'perf'
        detected_changes.append('Performance improvement patterns detected in diff context')

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
        return make_error(f'File not found: {args.file}', code=ErrorCode.NOT_FOUND)

    diff_content = path.read_text()
    suggestions = analyze_diff(diff_content)

    return {'mode': 'analysis', 'suggestions': suggestions, 'status': 'success'}


# ============================================================================
# DETECT-ARTIFACTS SUBCOMMAND
# ============================================================================

# Artifact patterns loaded from standards/artifact-patterns.json
SAFE_ARTIFACT_PATTERNS: list[str] = _ARTIFACT_CONFIG.get('safe_patterns', [])
UNCERTAIN_ARTIFACT_PATTERNS: list[str] = _ARTIFACT_CONFIG.get('uncertain_patterns', [])


def get_gitignored_files(root: Path) -> set[str]:
    """Return set of relative paths that are gitignored under root.

    Uses `git check-ignore` to respect .gitignore rules. Returns empty set
    if not inside a git repo or git is unavailable.
    """
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--others', '--ignored', '--exclude-standard'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(root),
        )
        if result.returncode != 0:
            return set()
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
        return set()


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    """Compile glob-style patterns into regex for single-pass matching.

    Uses ``fnmatch.translate()`` for simple glob patterns and placeholder-based
    conversion for ``**`` recursive directory patterns (which fnmatch does not
    support).
    """
    compiled = []
    for pattern in patterns:
        if '**' in pattern:
            # fnmatch doesn't support **; convert manually using placeholders
            # to prevent double-replacement (e.g., * inside (.*/)?).
            regex = pattern.replace('.', r'\.')
            regex = regex.replace('**/', '\x00DIR\x00')
            regex = regex.replace('**', '\x00STAR\x00')
            regex = regex.replace('*', '[^/]*')
            regex = regex.replace('\x00DIR\x00', '(.*/)?')
            regex = regex.replace('\x00STAR\x00', '.*')
            compiled.append(re.compile(f'^{regex}$'))
        else:
            compiled.append(re.compile(fnmatch.translate(pattern)))
    return compiled


_SAFE_REGEXES = _compile_patterns(SAFE_ARTIFACT_PATTERNS)
_UNCERTAIN_REGEXES = _compile_patterns(UNCERTAIN_ARTIFACT_PATTERNS)


# Directories to skip entirely during traversal — large and never useful to scan.
# Only directories that are NEVER artifact-matched themselves. Directories
# like __pycache__, .eggs, .next must NOT be skipped since they match
# safe/uncertain artifact patterns.
_SKIP_DIRS = set(_ARTIFACT_CONFIG.get('skip_dirs', ['.git', 'node_modules']))


def scan_artifacts(root: Path, respect_gitignore: bool = True) -> dict:
    """Scan directory for committable artifacts.

    Returns dict with 'safe' (auto-deletable) and 'uncertain' (needs confirmation) lists.
    Files already covered by .gitignore are excluded by default since they
    cannot be accidentally committed.

    Uses a single directory traversal with compiled regex patterns instead
    of multiple Path.glob() calls, improving performance on large repos.
    Skips known large directories (node_modules, .git, etc.) early to avoid
    unnecessary traversal.
    """
    ignored = get_gitignored_files(root) if respect_gitignore else set()

    safe: list[str] = []
    uncertain: list[str] = []

    root_str = str(root)
    for dirpath_str, dirnames, filenames in os.walk(root_str):
        # Prune directories we never need to descend into
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

        for filename in filenames:
            rel = os.path.relpath(os.path.join(dirpath_str, filename), root_str)
            if rel in ignored:
                continue

            # Check safe patterns first
            if any(rx.match(rel) for rx in _SAFE_REGEXES):
                safe.append(rel)
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
        return make_error(f'Directory not found: {root}', code=ErrorCode.NOT_FOUND)

    result = scan_artifacts(root, respect_gitignore=not args.no_gitignore)
    result['root'] = str(root)
    result['status'] = 'success'
    return result


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    parser = create_workflow_cli(
        description='Git workflow operations',
        epilog="""
Examples:
  git_workflow.py format-commit --type feat --scope auth --subject "add login"
  git_workflow.py analyze-diff --file changes.diff
  git_workflow.py detect-artifacts --root /path/to/repo
""",
        subcommands=[
            {
                'name': 'format-commit',
                'help': 'Format commit message following conventional commits',
                'handler': cmd_format_commit,
                'args': [
                    {
                        'flags': ['--type'],
                        'dest': 'commit_type',
                        'required': True,
                        'choices': VALID_TYPES,
                        'help': 'Commit type',
                    },
                    {'flags': ['--scope'], 'help': 'Commit scope'},
                    {'flags': ['--subject'], 'required': True, 'help': 'Commit subject'},
                    {'flags': ['--body'], 'help': 'Commit body'},
                    {'flags': ['--breaking'], 'help': 'Breaking change description'},
                    {'flags': ['--footer'], 'help': 'Additional footer'},
                ],
            },
            {
                'name': 'analyze-diff',
                'help': 'Analyze diff file to suggest commit message',
                'handler': cmd_analyze_diff,
                'args': [{'flags': ['--file'], 'required': True, 'help': 'Diff file to analyze'}],
            },
            {
                'name': 'detect-artifacts',
                'help': 'Scan for committable artifacts',
                'handler': cmd_detect_artifacts,
                'args': [
                    {'flags': ['--root'], 'help': 'Root directory to scan (default: cwd)'},
                    {
                        'flags': ['--no-gitignore'],
                        'action': 'store_true',
                        'help': 'Include gitignored files in results',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon  # type: ignore[import-not-found]

    return _output_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
