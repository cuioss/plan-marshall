#!/usr/bin/env python3
"""
Git workflow operations - format commits, analyze diffs, manage worktrees.

Usage:
    git_workflow.py format-commit --type <type> --subject <subject> [options]
    git_workflow.py analyze-diff --worktree-path <worktree-path> [--cached]
    git_workflow.py detect-artifacts [--root <dir>]
    git_workflow.py worktree-path --plan-id <plan-id>
    git_workflow.py worktree-create --plan-id <plan-id> --branch <branch> [--base <ref>]
    git_workflow.py worktree-remove --plan-id <plan-id> [--force]
    git_workflow.py worktree-list
    git_workflow.py worktree-rebase-to --plan-id <plan-id> --base <branch>
    git_workflow.py --help

Subcommands:
    format-commit      Format commit message following conventional commits
    analyze-diff       Capture and analyze the worktree diff to suggest a commit message
    detect-artifacts   Scan for committable artifacts (build outputs, temp files)
    worktree-path      Resolve the persisted worktree path for a plan
    worktree-create    Create a worktree + feature branch + .plan symlink for a plan
    worktree-remove    Remove a worktree (worktree first, then branch ref)
    worktree-list      Enumerate plans whose status.json declares a worktree
    worktree-rebase-to Rebase the worktree's branch onto --base, dispatching
                       on the eight documented worktree states

Examples:
    # Format a commit message
    git_workflow.py format-commit --type feat --scope auth --subject "add login flow"

    # Analyze a worktree diff for commit suggestions
    git_workflow.py analyze-diff --worktree-path /path/to/worktree [--cached]

    # Detect artifacts before committing
    git_workflow.py detect-artifacts --root /path/to/repo

    # Worktree CRUD verbs
    git_workflow.py worktree-path --plan-id my-plan
    git_workflow.py worktree-create --plan-id my-plan --branch feature/my-plan
    git_workflow.py worktree-remove --plan-id my-plan
    git_workflow.py worktree-list
    git_workflow.py worktree-rebase-to --plan-id my-plan --base main
"""

import fnmatch
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from _cmd_baseline_reconcile import cmd_baseline_reconcile
from file_ops import get_worktree_root  # type: ignore[import-not-found]
from git_provider import run_git  # type: ignore[import-not-found]
from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]
from toon_parser import parse_toon, parse_toon_table  # type: ignore[import-not-found]
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
    """Handle analyze-diff subcommand.

    Captures the worktree diff in-process via ``git -C {worktree_path} diff
    [--cached]`` and feeds the captured stdout to ``analyze_diff()``. The
    caller no longer needs to materialize a temp file.
    """
    worktree_path = Path(args.worktree_path)
    if not worktree_path.is_dir():
        return make_error(f'Worktree path not found: {args.worktree_path}', code=ErrorCode.NOT_FOUND)

    cmd = ['git', '-C', str(worktree_path), 'diff']
    if args.cached:
        cmd.append('--cached')

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
    except subprocess.CalledProcessError as exc:
        return make_error(
            f'git diff failed (exit {exc.returncode}): {exc.stderr.strip()}',
            code=ErrorCode.UNKNOWN,
        )
    except subprocess.TimeoutExpired:
        return make_error('git diff timed out after 30 seconds', code=ErrorCode.UNKNOWN)
    except FileNotFoundError:
        return make_error('git executable not found on PATH', code=ErrorCode.UNKNOWN)

    suggestions = analyze_diff(result.stdout)

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


def get_tracked_files(root: Path) -> set[str]:
    """Return set of paths (relative to ``root``) that are tracked by git.

    Uses ``git ls-files --cached`` with ``cwd=root`` so results are
    relative to ``root`` — matching the ``rel`` computation in
    ``scan_artifacts`` even when ``root`` is a subdirectory of a repo.
    Returns empty set if not inside a git repo or git is unavailable.
    Tracked files must never be classified as ``safe`` artifacts — even
    if a filename matches a safe glob, a tracked entry may be a committed
    fixture that the developer intends to keep.
    """
    try:
        result = subprocess.run(
            ['git', 'ls-files', '--cached'],
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

    Tracked files are never reported as ``safe`` — even when a filename
    matches a safe glob, a tracked entry may be an intentional fixture
    (e.g., a committed ``*.log`` used by a test). Matching tracked files
    are routed to ``uncertain`` so the caller can confirm before any
    deletion.
    """
    ignored = get_gitignored_files(root) if respect_gitignore else set()
    tracked = get_tracked_files(root)

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

            # Check safe patterns first, but demote tracked files to
            # 'uncertain' so committed fixtures are never auto-deleted.
            if any(rx.match(rel) for rx in _SAFE_REGEXES):
                if rel in tracked:
                    uncertain.append(rel)
                else:
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
# WORKTREE SUBCOMMANDS
# ============================================================================
#
# Two-state contract per §9 of the solution outline:
#   • ``--plan-id X`` is REQUIRED — every worktree subcommand operates on
#     a worktree, so a plan id is non-negotiable.
#   • Path resolution for ``worktree-path``/``worktree-remove``/``worktree-list``
#     reads ``status.metadata.worktree_path`` via ``manage-status get-worktree-path``.
#   • ``worktree-create`` computes the path from
#     ``get_worktree_root() / plan_id`` (the only verb that materializes a
#     new worktree on disk), runs ``git worktree add``, then writes
#     ``metadata.worktree_path`` / ``worktree_branch`` / ``use_worktree``
#     via ``manage-status metadata --set`` so subsequent verbs can
#     resolve the path through the canonical channel.

_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

_BOOTSTRAP_TIMEOUT_SECONDS = 120

#: Gitignored subpaths under ``.plan/`` that must be shared across
#: worktrees by symlinking into the main checkout. Everything else under
#: ``.plan/`` is tracked and materialized natively by ``git worktree add``.
_SHARED_PLAN_SUBPATHS: tuple[tuple[str, bool], ...] = (
    ('local', True),
    ('execute-script.py', False),
)


def _executor_path() -> Path | None:
    """Locate the ``.plan/execute-script.py`` executor relative to the main checkout.

    Returns ``None`` when the main checkout cannot be resolved (no git
    repo) or the executor file is absent (fresh repo, before
    ``/marshall-steward`` regeneration).
    """
    root = git_main_checkout_root()
    if root is None:
        return None
    candidate = root / _PLAN_DIR_NAME / 'execute-script.py'
    return candidate if candidate.exists() else None


def _manage_status_call(
    subcommand: str,
    *extra_args: str,
    timeout: int = 30,
) -> tuple[int, str, str]:
    """Invoke ``plan-marshall:manage-status:manage_status`` via the executor.

    Returns ``(returncode, stdout, stderr)`` (raw, not stripped). When the
    executor cannot be located, returns ``(127, '', '<reason>')`` so the
    caller can surface a clean TOON error rather than crashing.
    """
    executor = _executor_path()
    if executor is None:
        return 127, '', 'plan-marshall executor not available (.plan/execute-script.py missing)'
    try:
        result = subprocess.run(
            [
                'python3',
                str(executor),
                'plan-marshall:manage-status:manage_status',
                subcommand,
                *extra_args,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return 127, '', 'python3 executable not found on PATH'
    except subprocess.TimeoutExpired:
        return 124, '', f'manage-status {subcommand} timed out after {timeout} seconds'
    return result.returncode, result.stdout, result.stderr


def _read_metadata_field(plan_id: str, field: str) -> str:
    """Best-effort read of ``status.metadata.<field>`` via manage-status.

    Returns the string value when the field is present, or ``''`` when
    the call fails, the field is absent, or parsing the TOON output
    raises. Used by branch-name lookups during ``worktree-remove`` and
    ``worktree-list`` where missing metadata is a soft signal, not a
    hard error.
    """
    rc, stdout, _stderr = _manage_status_call(
        'metadata', '--plan-id', plan_id, '--get', '--field', field
    )
    if rc != 0:
        return ''
    try:
        parsed = parse_toon(stdout)
    except Exception:  # noqa: BLE001 — defensive against TOON drift
        return ''
    if parsed.get('status') != 'success':
        return ''
    value = parsed.get('value')
    return str(value) if value is not None else ''


def _resolve_worktree_path_for_plan(plan_id: str) -> tuple[Path | None, dict | None]:
    """Resolve ``status.metadata.worktree_path`` for ``plan_id``.

    Returns ``(path, None)`` on success, ``(None, error_dict)`` on
    failure. The error dict is a fully-formed TOON-shaped payload ready
    to return from a subcommand handler.
    """
    rc, stdout, stderr = _manage_status_call('get-worktree-path', '--plan-id', plan_id)
    if rc != 0:
        return None, {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'plan_resolution_failed',
            'message': (stderr or stdout).strip()
            or 'manage-status get-worktree-path failed',
        }

    try:
        parsed = parse_toon(stdout)
    except Exception as exc:  # noqa: BLE001 — defensive against TOON drift
        return None, {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'plan_resolution_failed',
            'message': f'failed to parse manage-status output: {exc}',
        }

    if parsed.get('status') == 'error' or parsed.get('error'):
        return None, {
            'status': 'error',
            'plan_id': plan_id,
            'error': parsed.get('error') or 'plan_resolution_failed',
            'message': parsed.get('message') or 'manage-status reported an error',
        }

    use_worktree = bool(parsed.get('use_worktree'))
    worktree_path_value = parsed.get('worktree_path') or ''

    if not use_worktree or not worktree_path_value:
        return None, {
            'status': 'error',
            'plan_id': plan_id,
            'error': 'plan_resolution_failed',
            'message': (
                'No worktree configured for this plan — '
                'status.metadata.use_worktree is false or worktree_path is unset'
            ),
        }

    return Path(str(worktree_path_value)), None


def _detect_pw_wrapper(worktree: Path) -> Path | None:
    """Locate a pyprojectx wrapper in the worktree, preferring Unix `pw`."""
    for name in ('pw', 'pw.bat', 'pwx'):
        candidate = worktree / name
        if candidate.exists():
            return candidate
    return None


def _bootstrap_pyprojectx(worktree: Path) -> tuple[str, str]:
    """Best-effort pre-bootstrap of pyprojectx in a freshly-created worktree.

    Runs ``./pw --version`` so pyprojectx populates ``.pyprojectx`` while ``uv``
    is still on PATH. Returns ``(status, detail)`` where status is
    ``ok``, ``skipped``, or ``warning``. The caller treats this strictly as
    advisory — failures never fail ``cmd_worktree_create``.
    """
    wrapper = _detect_pw_wrapper(worktree)
    if wrapper is None:
        return 'skipped', 'no pw wrapper found in worktree'
    try:
        result = subprocess.run(
            [str(wrapper), '--version'],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=_BOOTSTRAP_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 'warning', f'bootstrap invocation failed: {exc}'
    if result.returncode != 0:
        stderr_tail = (result.stderr or '').strip().splitlines()[-1:]
        detail = stderr_tail[0] if stderr_tail else f'exit {result.returncode}'
        return 'warning', detail
    return 'ok', ''


def _ensure_worktree_plan_symlinks(worktree: Path) -> tuple[bool, str]:
    """Link gitignored ``.plan/`` subpaths into the main checkout.

    The worktree's ``.plan`` directory itself is left alone —
    ``git worktree add`` already materializes any tracked content there.
    Only the entries listed in :data:`_SHARED_PLAN_SUBPATHS` are linked
    to the main checkout so runtime state and the executor stay in sync
    across worktrees.

    For each shared subpath:
    - If it already exists as a symlink pointing at the expected target,
      skip it.
    - If it exists as a stale symlink, replace it.
    - If it exists as a real file or directory, refuse with an error
      that names the specific offending subpath.
    - If it is missing, create the symlink.

    Returns ``(success, error_message)``.
    """
    main_root = git_main_checkout_root()
    if main_root is None:
        return False, 'cannot resolve main git checkout root for .plan symlinks'

    plan_dir = worktree / _PLAN_DIR_NAME
    # Ensure .plan exists as a real directory. git worktree add creates
    # it when tracked content lives there; fall back to mkdir otherwise.
    plan_dir.mkdir(parents=True, exist_ok=True)

    for subpath, is_dir in _SHARED_PLAN_SUBPATHS:
        target = (main_root / _PLAN_DIR_NAME / subpath).resolve()
        link_path = plan_dir / subpath
        rel_display = f'{_PLAN_DIR_NAME}/{subpath}'

        if link_path.is_symlink():
            try:
                if link_path.resolve() == target:
                    continue
            except OSError:
                pass
            link_path.unlink()
        elif link_path.exists():
            kind = 'directory' if link_path.is_dir() else 'file'
            return False, (
                f'{link_path} exists as a real {kind}; refusing to replace '
                f'{rel_display} with symlink. Remove it manually or inspect '
                'for user data.'
            )

        # Use a relative symlink so the worktree stays portable.
        rel_target = os.path.relpath(target, link_path.parent)
        try:
            os.symlink(rel_target, link_path, target_is_directory=is_dir)
        except OSError as exc:
            return False, f'failed to create {rel_display} symlink: {exc}'
    return True, ''


def cmd_worktree_path(args):
    """Resolve the persisted worktree path for a plan.

    Two-state contract: ``--plan-id`` is required; resolution goes
    through ``manage-status get-worktree-path``.
    """
    path, error = _resolve_worktree_path_for_plan(args.plan_id)
    if error is not None:
        return error

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'worktree_path': str(path),
        'exists': path.is_dir(),
    }


def cmd_worktree_create(args):
    """Create a worktree + feature branch + .plan symlinks for ``--plan-id``.

    Path is computed from ``get_worktree_root() / plan_id`` — the only
    verb that materializes a new worktree on disk. After ``git worktree
    add`` succeeds, project state is bookkept by writing
    ``metadata.use_worktree``/``worktree_path``/``worktree_branch`` via
    ``manage-status metadata --set`` so subsequent verbs can resolve the
    path through the canonical channel.
    """
    try:
        target = get_worktree_root() / args.plan_id
    except RuntimeError as exc:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_resolution_failed',
            'message': str(exc),
        }

    if target.exists():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'worktree_exists',
            'message': f'Worktree already exists: {target}',
            'worktree_path': str(target),
        }
    target.parent.mkdir(parents=True, exist_ok=True)

    main_root = git_main_checkout_root()
    if main_root is None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_resolution_failed',
            'message': 'cannot resolve main git checkout root for git worktree add',
        }

    git_args = ['-C', str(main_root), 'worktree', 'add']
    if args.base:
        git_args += ['-b', args.branch, str(target), args.base]
    else:
        git_args += ['-b', args.branch, str(target)]
    rc, _stdout, stderr = run_git(git_args)
    if rc != 0:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'worktree_add_failed',
            'message': f'git worktree add failed: {stderr}',
            'branch': args.branch,
        }

    ok, link_err = _ensure_worktree_plan_symlinks(target)
    if not ok:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_symlink_failed',
            'message': f'Worktree created but .plan symlinks failed: {link_err}',
            'worktree_path': str(target),
        }

    bootstrap_status, bootstrap_detail = _bootstrap_pyprojectx(target)

    # Project-state bookkeeping: persist the resolved path/branch via
    # manage-status so subsequent verbs can resolve through the canonical
    # channel. The ``use_worktree`` field is a string here (manage-status
    # metadata --set stores values as strings); ``cmd_get_worktree_path``
    # treats the literal ``true`` as truthy so the round-trip is intact.
    bookkeeping_warnings: list[str] = []
    for field, value in (
        ('use_worktree', 'true'),
        ('worktree_path', str(target)),
        ('worktree_branch', args.branch),
    ):
        rc, _out, err = _manage_status_call(
            'metadata',
            '--plan-id',
            args.plan_id,
            '--set',
            '--field',
            field,
            '--value',
            value,
        )
        if rc != 0:
            bookkeeping_warnings.append(
                f'manage-status metadata --set --field {field}: {err.strip() or "non-zero exit"}'
            )

    payload: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'worktree_path': str(target),
        'branch': args.branch,
        'plan_symlink': str(target / _PLAN_DIR_NAME),
        'bootstrap': bootstrap_status,
    }
    if bootstrap_status == 'warning':
        payload['bootstrap_warning'] = bootstrap_detail
    if bookkeeping_warnings:
        # Surface bookkeeping problems without failing the command — the
        # worktree itself is on disk; status metadata can be fixed later.
        payload['bookkeeping_warnings'] = bookkeeping_warnings
    return payload


def cmd_worktree_remove(args):
    """Remove a worktree (worktree first, then branch ref).

    Order matters: ``git worktree remove`` refuses to drop a branch ref
    that is still checked out. We remove the worktree first, then delete
    the branch ref so the cleanup is symmetric with ``cmd_worktree_create``.
    """
    target, error = _resolve_worktree_path_for_plan(args.plan_id)
    if error is not None:
        return error

    main_root = git_main_checkout_root()
    if main_root is None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_resolution_failed',
            'message': 'cannot resolve main git checkout root for git worktree remove',
        }

    if not target.exists():
        return {
            'status': 'success',
            'plan_id': args.plan_id,
            'worktree_path': str(target),
            'action': 'noop',
            'message': 'Worktree does not exist',
        }

    # Step 1: remove the worktree itself.
    git_args = ['-C', str(main_root), 'worktree', 'remove', str(target)]
    if args.force:
        git_args.append('--force')
    rc, _out, err = run_git(git_args)
    if rc != 0:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'worktree_remove_failed',
            'message': f'git worktree remove failed: {err}',
            'worktree_path': str(target),
            'hint': 'Pass --force only after verifying the worktree is clean.',
        }

    # Step 2: delete the branch ref. Read the branch from status metadata
    # (canonical source) and best-effort delete. Failure to delete the
    # branch is reported but does not fail the command — the worktree is
    # already gone and branch cleanup is recoverable.
    branch_warning: str | None = None
    branch_name = _read_metadata_field(args.plan_id, 'worktree_branch')
    if branch_name:
        rc, _out, err = run_git(['-C', str(main_root), 'branch', '-D', branch_name])
        if rc != 0:
            branch_warning = f'branch ref {branch_name} not deleted: {err}'

    payload: dict[str, Any] = {
        'status': 'success',
        'plan_id': args.plan_id,
        'worktree_path': str(target),
        'action': 'removed',
    }
    if branch_name:
        payload['branch'] = branch_name
    if branch_warning:
        payload['branch_warning'] = branch_warning
    return payload


def _detect_worktree_state(
    worktree: Path,
    base: str,
    main_root: Path,
) -> tuple[str, dict[str, Any]]:
    """Inspect the worktree and return ``(state, evidence)``.

    State is one of the eight documented worktree-state labels:

    - ``missing-target`` — the worktree directory does not exist on disk.
    - ``missing-base``  — the ``base`` ref cannot be resolved in the
      shared object database.
    - ``detached``      — HEAD is detached (no current branch).
    - ``dirty``         — the worktree has uncommitted changes
      (staged, unstaged, or untracked).
    - ``ahead``         — the branch has commits the base does not
      contain (and the base has none the branch lacks).
    - ``behind``        — the base has commits the branch does not
      contain (and the branch has none the base lacks).
    - ``clean``         — the branch and base point at the same commit
      (or a divergence with both ahead/behind counts zero).
    - The eighth label, ``conflict``, is determined by the rebase
      attempt itself, not this function.

    ``evidence`` carries supplementary fields the dispatcher echoes back
    in the TOON output (e.g., ``head_branch``, ``ahead``, ``behind``).
    """
    if not worktree.is_dir():
        return 'missing-target', {'worktree_path': str(worktree)}

    rc, _out, err = run_git(['-C', str(main_root), 'rev-parse', '--verify', f'{base}^{{commit}}'])
    if rc != 0:
        return 'missing-base', {'base': base, 'message': err.strip() or 'base ref not found'}

    rc, head_branch_out, _err = run_git(
        ['-C', str(worktree), 'symbolic-ref', '--quiet', '--short', 'HEAD']
    )
    if rc != 0:
        return 'detached', {'message': 'HEAD is detached; rebase requires a checked-out branch'}
    head_branch = head_branch_out.strip()

    rc, status_out, _err = run_git(['-C', str(worktree), 'status', '--porcelain'])
    if rc == 0 and status_out.strip():
        return 'dirty', {
            'head_branch': head_branch,
            'message': 'worktree has uncommitted changes; stash, commit, or discard first',
        }

    # Compute ahead/behind counts relative to the resolved base commit.
    rc, counts_out, _err = run_git(
        ['-C', str(worktree), 'rev-list', '--left-right', '--count', f'{base}...HEAD']
    )
    ahead = behind = 0
    if rc == 0 and counts_out.strip():
        parts = counts_out.split()
        if len(parts) >= 2:
            try:
                behind = int(parts[0])
                ahead = int(parts[1])
            except ValueError:
                behind = ahead = 0

    evidence: dict[str, Any] = {
        'head_branch': head_branch,
        'ahead': ahead,
        'behind': behind,
    }

    if ahead > 0 and behind == 0:
        return 'ahead', evidence
    if behind > 0 and ahead == 0:
        return 'behind', evidence
    if ahead == 0 and behind == 0:
        return 'clean', evidence
    # Diverged — both ahead and behind. Treat as ``ahead`` for dispatch
    # since the rebase needs to relocate the local commits onto base.
    return 'ahead', evidence


def cmd_worktree_rebase_to(args):
    """Rebase the worktree's branch onto ``--base``.

    Detects the current state per :func:`_detect_worktree_state`,
    dispatches the rebase accordingly, and returns a TOON payload with
    ``status`` (``success``, ``error``, ``conflict``) and ``state`` (one
    of the eight documented labels). On conflict, the rebase is left in
    progress with conflict markers so the caller can inspect or abort.
    All git invocations use ``git -C {worktree_path}``; no working
    directory is implicitly assumed.
    """
    target, error = _resolve_worktree_path_for_plan(args.plan_id)
    if error is not None:
        return error

    main_root = git_main_checkout_root()
    if main_root is None:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'plan_resolution_failed',
            'state': 'missing-target',
            'message': 'cannot resolve main git checkout root for rebase',
        }

    state, evidence = _detect_worktree_state(target, args.base, main_root)

    base_payload: dict[str, Any] = {
        'plan_id': args.plan_id,
        'worktree_path': str(target),
        'base': args.base,
        'state': state,
    }
    base_payload.update(evidence)

    # Reject states that require user action without touching git.
    if state == 'missing-target':
        return {
            **base_payload,
            'status': 'error',
            'error': 'missing_target',
            'message': f'worktree path does not exist: {target}',
        }
    if state == 'missing-base':
        return {
            **base_payload,
            'status': 'error',
            'error': 'missing_base',
            'message': f'base ref not found: {args.base}',
        }
    if state == 'detached':
        return {
            **base_payload,
            'status': 'error',
            'error': 'detached_head',
            'message': 'HEAD is detached; rebase requires a checked-out branch',
        }
    if state == 'dirty':
        return {
            **base_payload,
            'status': 'error',
            'error': 'dirty_worktree',
            'message': (
                'worktree has uncommitted changes; stash, commit, '
                'or discard before rebasing'
            ),
        }

    # ``clean`` — already up-to-date relative to base. No-op rebase.
    if state == 'clean':
        return {
            **base_payload,
            'status': 'success',
            'action': 'noop',
            'message': 'branch is already at base; no rebase needed',
        }

    # ``ahead`` and ``behind`` both attempt a rebase. The detected state
    # is preserved in the response so callers can distinguish.
    rc, _stdout, stderr = run_git(['-C', str(target), 'rebase', args.base])
    if rc == 0:
        return {
            **base_payload,
            'status': 'success',
            'action': 'rebased',
            'message': f'rebased {evidence.get("head_branch", "HEAD")} onto {args.base}',
        }

    # Non-zero exit means rebase produced conflicts (or another git
    # error). Inspect for an in-progress rebase to surface the conflict
    # state cleanly. Conflict markers are intentionally left in place
    # so the caller can resolve manually.
    rebase_state_dir = target / '.git' / 'rebase-merge'
    rebase_apply_dir = target / '.git' / 'rebase-apply'
    in_progress = rebase_state_dir.exists() or rebase_apply_dir.exists()

    if in_progress:
        # Enumerate conflicting paths via ``git diff --name-only --diff-filter=U``.
        rc_d, conflicts_out, _err = run_git(
            ['-C', str(target), 'diff', '--name-only', '--diff-filter=U']
        )
        conflicts = (
            [line for line in conflicts_out.splitlines() if line.strip()]
            if rc_d == 0
            else []
        )
        return {
            **base_payload,
            'status': 'conflict',
            'state': 'conflict',
            'error': 'rebase_conflict',
            'conflicts': conflicts,
            'message': (
                f'rebase produced conflicts ({len(conflicts)} file(s)); '
                'resolve and run `git rebase --continue` or `git rebase --abort`'
            ),
        }

    # Rebase failed for another reason (e.g., invalid args). Surface git's stderr.
    return {
        **base_payload,
        'status': 'error',
        'error': 'rebase_failed',
        'message': f'git rebase failed: {stderr.strip() or "non-zero exit"}',
    }


def cmd_worktree_list(_args):
    """Enumerate plans whose status.json declares a worktree.

    Reads from ``manage-status list`` and filters on
    ``metadata.use_worktree == true`` by calling
    ``manage-status get-worktree-path`` per plan. Plans without a
    configured worktree are silently skipped.
    """
    rc, stdout, stderr = _manage_status_call('list')
    if rc != 0:
        return {
            'status': 'error',
            'error': 'plan_resolution_failed',
            'message': (stderr or stdout).strip() or 'manage-status list failed',
        }

    rows = parse_toon_table(stdout, 'plans')
    plan_ids = [str(row.get('id')) for row in rows if row.get('id')]

    worktrees: list[dict[str, str]] = []
    for plan_id in plan_ids:
        path, error = _resolve_worktree_path_for_plan(plan_id)
        if error is not None or path is None:
            continue
        worktrees.append(
            {
                'plan_id': plan_id,
                'path': str(path),
                'branch': _read_metadata_field(plan_id, 'worktree_branch'),
            }
        )

    try:
        worktrees_root = str(get_worktree_root())
    except RuntimeError:
        worktrees_root = ''

    return {
        'status': 'success',
        'worktrees_root': worktrees_root,
        'count': len(worktrees),
        'worktrees': worktrees,
    }


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
  git_workflow.py analyze-diff --worktree-path /path/to/worktree [--cached]
  git_workflow.py detect-artifacts --root /path/to/repo
  git_workflow.py worktree-path --plan-id my-plan
  git_workflow.py worktree-create --plan-id my-plan --branch feature/my-plan
  git_workflow.py worktree-remove --plan-id my-plan [--force]
  git_workflow.py worktree-list
  git_workflow.py worktree-rebase-to --plan-id my-plan --base main
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
                'help': 'Capture and analyze the worktree diff to suggest a commit message',
                'handler': cmd_analyze_diff,
                'args': [
                    {
                        'flags': ['--worktree-path'],
                        'required': True,
                        'help': 'Worktree path to capture diff from',
                    },
                    {
                        'flags': ['--cached'],
                        'action': 'store_true',
                        'help': 'Use staged diff (git diff --cached) instead of unstaged',
                    },
                ],
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
            {
                'name': 'worktree-path',
                'help': 'Resolve the persisted worktree path for a plan',
                'handler': cmd_worktree_path,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory — worktree subcommands operate on a worktree)',
                    },
                ],
            },
            {
                'name': 'worktree-create',
                'help': 'Create a worktree + feature branch + .plan symlink for a plan',
                'handler': cmd_worktree_create,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory)',
                    },
                    {
                        'flags': ['--branch'],
                        'required': True,
                        'help': 'Feature branch name to create',
                    },
                    {
                        'flags': ['--base'],
                        'help': 'Base ref for the new branch (default: current HEAD)',
                    },
                ],
            },
            {
                'name': 'worktree-remove',
                'help': 'Remove a worktree (worktree first, then branch ref)',
                'handler': cmd_worktree_remove,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory)',
                    },
                    {
                        'flags': ['--force'],
                        'action': 'store_true',
                        'help': 'Force removal (use only if worktree is clean)',
                    },
                ],
            },
            {
                'name': 'worktree-list',
                'help': 'Enumerate plans whose status.json declares a worktree',
                'handler': cmd_worktree_list,
                'args': [],
            },
            {
                'name': 'worktree-rebase-to',
                'help': "Rebase the worktree's branch onto --base, dispatching on the eight documented worktree states",
                'handler': cmd_worktree_rebase_to,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory — resolves the worktree path via manage-status)',
                    },
                    {
                        'flags': ['--base'],
                        'required': True,
                        'help': 'Base ref to rebase onto (e.g., main, origin/main)',
                    },
                ],
            },
            {
                'name': 'baseline-reconcile',
                'help': (
                    'Mechanical baseline reconciliation for phase-2-refine Step 3d '
                    '(fetch + diff + merge-tree conflict detection; no LLM dispatch)'
                ),
                'handler': cmd_baseline_reconcile,
                'args': [
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'required': True,
                        'help': 'Plan identifier (mandatory — resolves worktree path and base branch)',
                    },
                    {
                        'flags': ['--base-branch'],
                        'dest': 'base_branch',
                        'help': (
                            'Optional override for the upstream base branch. '
                            'Default reads from plan config phase-2-refine.base_branch, '
                            'falling back to main.'
                        ),
                    },
                    {
                        'flags': ['--worktree-path'],
                        'dest': 'worktree_path',
                        'help': (
                            'Optional override for the worktree path. Default reads '
                            'metadata.worktree_path from status.json.'
                        ),
                    },
                    {
                        'flags': ['--skip-fetch'],
                        'dest': 'skip_fetch',
                        'action': 'store_true',
                        'help': (
                            'Skip the git fetch origin {base_branch} round-trip. '
                            'Use in tests with seeded local refs; the environment '
                            'variable PLAN_MARSHALL_SKIP_FETCH=1 has the same effect.'
                        ),
                    },
                    {
                        'flags': ['--no-emit'],
                        'dest': 'no_emit',
                        'action': 'store_true',
                        'help': (
                            'Run the checks and return the result TOON without writing '
                            'any Q-Gate findings (dry-run).'
                        ),
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
