#!/usr/bin/env python3
"""Deterministic candidate surfacing for the pre-submission-self-review finalize step.

Reads the worktree's diff against the base branch, scans added lines in modified
files, and emits four candidate lists (regexes, user-facing strings, markdown
sections, symmetric-pair functions) as TOON for the LLM cognitive review pass to
consume.

Storage: stateless — reads the worktree diff and the plan's references.modified_files.
Output: TOON to stdout.

Usage:
    python3 self_review.py surface --plan-id my-plan --project-dir /path/to/worktree
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from file_ops import (  # type: ignore[import-not-found]
    output_toon,
    output_toon_error,
    safe_main,
)
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    require_valid_plan_id,
)
from toon_parser import parse_toon  # type: ignore[import-not-found]

# =============================================================================
# Detection regexes
# =============================================================================

# Added-line marker (stripped before content scanning)
_ADDED_LINE = re.compile(r'^\+(?!\+\+)(.*)$')

# Diff hunk header (records the post-image starting line number)
_HUNK_HEADER = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')

# Diff file header (records the post-image path)
_FILE_HEADER = re.compile(r'^\+\+\+ b/(.+)$')

# Regex/glob detection
_RE_CALL = re.compile(
    r"\bre\.(?:compile|match|search|findall|sub|fullmatch|finditer)"
    r"\s*\(\s*(?:r|f|rf|fr)?(['\"])(.+?)\1"
)
# fnmatch's pattern is the SECOND positional arg (path is first); accept any
# string literal inside the call's argument list — first quoted run wins.
_FNMATCH_CALL = re.compile(
    r"\bfnmatch\.(?:fnmatch|filter)\s*\([^)]*?(['\"])([^'\"]*)\1"
)
_RAW_REGEX_LITERAL = re.compile(r"\br(['\"])([^'\"]*[\^$.*+?\[\](){}|\\][^'\"]*)\1")

# User-facing string detection
_DEF_OR_CLASS = re.compile(r'^\s*(def|class)\s+\w+')
_TRIPLE_QUOTE = re.compile(r"""^\s*(['"]{3})(.*)$""")
_PRINT_CALL = re.compile(r"\bprint\s*\(\s*(?:r|f|rf|fr)?(['\"])(.*?)\1")
_ARGPARSE_FIELD = re.compile(
    r"\b(description|help|epilog)\s*=\s*(?:r|f|rf|fr)?(['\"])(.*?)\2"
)
_RAISE_MESSAGE = re.compile(
    r"\braise\s+\w+(?:Error|Exception)\s*\(\s*(?:r|f|rf|fr)?(['\"])(.*?)\1"
)
_MD_HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
_MD_BULLET = re.compile(r'^\s*[-*]\s+(.+?)\s*$')

# Symmetric-pair detection
_DEF_NAME = re.compile(r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')
_PAIR_TOKENS: list[tuple[str, str]] = [
    ('save', 'load'),
    ('init', 'restore'),
    ('push', 'pop'),
    ('acquire', 'release'),
    ('open', 'close'),
    ('start', 'stop'),
]


# =============================================================================
# Helpers
# =============================================================================


def _truncate(text: str, limit: int) -> str:
    """Truncate text to limit characters, adding ellipsis when shortened."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + '...'


def _run_git(project_dir: Path, *args: str) -> tuple[int, str, str]:
    """Run a git command via ``git -C {project_dir} ...`` and return (returncode, stdout, stderr)."""
    cmd = ['git', '-C', str(project_dir), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode, proc.stdout, proc.stderr


def _resolve_modified_files(plan_id: str) -> list[str]:
    """Read references.modified_files for the plan via parse_toon on manage-references output."""
    cmd = [
        sys.executable,
        '.plan/execute-script.py',
        'plan-marshall:manage-references:manage-references',
        'list',
        'get',
        '--plan-id',
        plan_id,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    if proc.returncode != 0:
        return []
    parsed = parse_toon(proc.stdout)
    if parsed.get('status') != 'success':
        return []
    files = parsed.get('modified_files', [])
    if isinstance(files, list):
        return [str(p) for p in files if p]
    return []


def _verify_base_branch(project_dir: Path, base_branch: str) -> bool:
    """Return True if the base branch ref resolves inside the project dir."""
    rc, _, _ = _run_git(project_dir, 'rev-parse', '--verify', base_branch)
    return rc == 0


def _diff_hunks(project_dir: Path, base_branch: str) -> str:
    """Return the post-image diff of the working tree against base_branch.

    Uses ``git diff {base_branch}`` (NOT ``base_branch...HEAD``) because
    ``pre-submission-self-review`` runs BEFORE ``commit-push`` — the changes
    under review are typically uncommitted and would not appear in a
    HEAD-anchored diff. Working-tree diff captures both staged and unstaged
    changes against the base branch's HEAD, which is the correct review
    surface for the pre-submission step.
    """
    rc, out, _ = _run_git(project_dir, 'diff', '--unified=3', base_branch)
    if rc != 0:
        return ''
    return out


def _read_post_image(project_dir: Path, repo_relative_path: str) -> list[str]:
    """Return the worktree's current contents of repo_relative_path as a list of lines."""
    full = project_dir / repo_relative_path
    if not full.is_file():
        return []
    try:
        return full.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# Diff parsing
# =============================================================================


def _iter_added_lines(diff_text: str) -> list[tuple[str, int, str]]:
    """Yield ``(file_path, post_image_line_no, content)`` for each added line in the diff."""
    out: list[tuple[str, int, str]] = []
    current_file: str | None = None
    post_line = 0
    for raw in diff_text.splitlines():
        m_file = _FILE_HEADER.match(raw)
        if m_file is not None:
            current_file = m_file.group(1)
            post_line = 0
            continue
        m_hunk = _HUNK_HEADER.match(raw)
        if m_hunk is not None:
            post_line = int(m_hunk.group(1))
            continue
        if current_file is None:
            continue
        if raw.startswith('+++') or raw.startswith('---'):
            continue
        if raw.startswith('+'):
            content = raw[1:]
            out.append((current_file, post_line, content))
            post_line += 1
            continue
        if raw.startswith('-'):
            continue
        if raw.startswith(' '):
            post_line += 1
            continue
        if raw.startswith('\\'):
            continue
    return out


# =============================================================================
# Detectors
# =============================================================================


def _detect_regexes(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for path, lineno, content in added:
        if not (path.endswith('.py') or path.endswith('.md')):
            continue
        for m in _RE_CALL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
        for m in _FNMATCH_CALL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
        for m in _RAW_REGEX_LITERAL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
    return out


def _detect_user_facing_strings(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prev_def_or_class = False
    for path, lineno, content in added:
        if path.endswith('.md'):
            m_h = _MD_HEADING.match(content)
            if m_h is not None:
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'markdown_heading',
                        'text': _truncate(m_h.group(2), 200),
                    }
                )
                prev_def_or_class = False
                continue
            m_b = _MD_BULLET.match(content)
            if m_b is not None:
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'markdown_bullet',
                        'text': _truncate(m_b.group(1), 200),
                    }
                )
                prev_def_or_class = False
                continue
            prev_def_or_class = False
            continue
        if not path.endswith('.py'):
            prev_def_or_class = False
            continue
        if _DEF_OR_CLASS.match(content):
            prev_def_or_class = True
            continue
        if prev_def_or_class:
            m_t = _TRIPLE_QUOTE.match(content)
            if m_t is not None:
                tail = m_t.group(2)
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'docstring',
                        'text': _truncate(tail, 200),
                    }
                )
                prev_def_or_class = False
                continue
        prev_def_or_class = False
        for m in _PRINT_CALL.finditer(content):
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': 'print',
                    'text': _truncate(m.group(2), 200),
                }
            )
        for m in _ARGPARSE_FIELD.finditer(content):
            field = m.group(1)
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': f'argparse_{field}',
                    'text': _truncate(m.group(3), 200),
                }
            )
        for m in _RAISE_MESSAGE.finditer(content):
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': 'raise_message',
                    'text': _truncate(m.group(2), 200),
                }
            )
    return out


def _detect_markdown_sections(
    added: list[tuple[str, int, str]], project_dir: Path
) -> list[dict[str, Any]]:
    """Emit one entry per added/edited heading, with sibling list (peer headings under same parent)."""
    md_files: dict[str, set[int]] = {}
    for path, lineno, content in added:
        if not path.endswith('.md'):
            continue
        if _MD_HEADING.match(content) is None:
            continue
        md_files.setdefault(path, set()).add(lineno)

    out: list[dict[str, Any]] = []
    for md_path, edited_lines in md_files.items():
        post_image = _read_post_image(project_dir, md_path)
        # Build a list of (line_no, depth, heading, parent_path) for every heading in the file.
        headings: list[dict[str, Any]] = []
        ancestor_stack: list[tuple[int, str]] = []  # (depth, heading)
        for idx, line in enumerate(post_image, start=1):
            m = _MD_HEADING.match(line)
            if m is None:
                continue
            depth = len(m.group(1))
            text = m.group(2)
            while ancestor_stack and ancestor_stack[-1][0] >= depth:
                ancestor_stack.pop()
            parent = ancestor_stack[-1][1] if ancestor_stack else ''
            headings.append(
                {'line': idx, 'depth': depth, 'heading': text, 'parent': parent}
            )
            ancestor_stack.append((depth, text))
        # For each edited heading, gather siblings under same parent at same depth.
        for h in headings:
            if h['line'] not in edited_lines:
                continue
            siblings = [
                other['heading']
                for other in headings
                if other is not h
                and other['depth'] == h['depth']
                and other['parent'] == h['parent']
            ]
            out.append(
                {
                    'file': md_path,
                    'line': h['line'],
                    'heading': _truncate(h['heading'], 120),
                    'siblings': '; '.join(_truncate(s, 80) for s in siblings),
                }
            )
    return out


def _detect_symmetric_pairs(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _DEF_NAME.match(content)
        if m is None:
            continue
        name = m.group(1)
        parts = name.split('_')
        partner_name: str | None = None
        for tok_a, tok_b in _PAIR_TOKENS:
            if tok_a in parts:
                idx = parts.index(tok_a)
                swapped = list(parts)
                swapped[idx] = tok_b
                partner_name = '_'.join(swapped)
                break
            if tok_b in parts:
                idx = parts.index(tok_b)
                swapped = list(parts)
                swapped[idx] = tok_a
                partner_name = '_'.join(swapped)
                break
        if partner_name is None:
            continue
        out.append(
            {
                'file': path,
                'line': lineno,
                'name': name,
                'partner': partner_name,
            }
        )
    return out


# =============================================================================
# Subcommand: surface
# =============================================================================


def _cmd_surface(args: argparse.Namespace) -> int:
    plan_id = require_valid_plan_id(args)
    project_dir = Path(args.project_dir).resolve()
    base_branch = args.base_branch or 'main'

    if not project_dir.is_dir():
        output_toon_error(
            'project_dir_invalid',
            f'project-dir does not exist or is not a directory: {project_dir}',
        )
        return 1

    rc_check, _, stderr_check = _run_git(project_dir, 'rev-parse', '--git-dir')
    if rc_check != 0:
        output_toon_error(
            'git_unavailable',
            f'git -C {project_dir} rev-parse failed: {stderr_check.strip()}',
        )
        return 1

    if not _verify_base_branch(project_dir, base_branch):
        output_toon_error(
            'base_branch_not_found',
            f'base branch {base_branch!r} does not resolve inside {project_dir}',
        )
        return 1

    modified_files = _resolve_modified_files(plan_id)

    diff_text = _diff_hunks(project_dir, base_branch)
    added = _iter_added_lines(diff_text)

    if modified_files:
        allowed = set(modified_files)
        added = [(p, ln, c) for (p, ln, c) in added if p in allowed]

    regexes = _detect_regexes(added)
    user_facing = _detect_user_facing_strings(added)
    md_sections = _detect_markdown_sections(added, project_dir)
    sym_pairs = _detect_symmetric_pairs(added)

    output = {
        'status': 'success',
        'plan_id': plan_id,
        'project_dir': str(project_dir),
        'base_branch': base_branch,
        'counts': {
            'regexes': len(regexes),
            'user_facing_strings': len(user_facing),
            'markdown_sections': len(md_sections),
            'symmetric_pairs': len(sym_pairs),
            'total': len(regexes) + len(user_facing) + len(md_sections) + len(sym_pairs),
        },
        'regexes': regexes,
        'user_facing_strings': user_facing,
        'markdown_sections': md_sections,
        'symmetric_pairs': sym_pairs,
    }
    output_toon(output)
    return 0


# =============================================================================
# CLI
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Surface candidate lists for pre-submission self-review.',
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_surface = sub.add_parser(
        'surface',
        help='Emit the four candidate lists from the worktree diff as TOON.',
        allow_abbrev=False,
    )
    add_plan_id_arg(p_surface)
    p_surface.add_argument(
        '--project-dir',
        required=True,
        help='Absolute path to the active git worktree (Bucket B).',
    )
    p_surface.add_argument(
        '--base-branch',
        default='main',
        help='Base branch for diff computation (default: main).',
    )
    p_surface.set_defaults(func=_cmd_surface)
    return parser


@safe_main
def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    main()
