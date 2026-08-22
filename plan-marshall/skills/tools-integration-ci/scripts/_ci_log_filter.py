#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Error-extraction filtering for downloaded CI failure logs.

Two public helpers consumed by the CI provider scripts after a raw failing-job
log has been downloaded:

- ``filter_log(raw_log, error_style)`` — produce a filtered error-extraction
  variant of a raw CI log. The default ``generic`` mode applies a context-window
  heuristic (lines matching ERROR/FAIL/Exception/Traceback plus N surrounding
  context lines, overlapping windows collapsed with an elision marker). The
  ``maven`` / ``gradle`` / ``npm`` modes route through the shared build parsers
  (``_build_parser_registry`` + the per-system ``parse_log``) and fall back to
  the generic heuristic when no structured errors are found.
- ``slugify_check_name(name)`` — derive a collision-free per-check file-name
  stem from a CI check name.

The filter heuristic specification is the central standard; see
``marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/api-contract.md``
(CI Failure Log Download & Filtering). That document is authoritative — this
module implements it and must not be treated as the specification.

The module is dependency-light: the generic path is pure stdlib. The build-parser
routing is imported lazily so that ``import _ci_log_filter`` never requires the
build script directories to be on ``sys.path`` unless a structured ``error_style``
is actually requested.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

# Symmetric before/after context-line count for the generic heuristic.
CONTEXT_LINES = 3

# Marker emitted between non-adjacent kept windows.
ELISION_MARKER = '...'

# Fallback stem when slugify_check_name receives input with no usable characters.
SLUG_FALLBACK = 'check'

# Generic error-line heuristic: matches the central-standard markers.
_GENERIC_ERROR_RE = re.compile(r'ERROR|FAIL|Exception|Traceback', re.IGNORECASE)

# Build systems that route through the shared structured build parsers.
_STRUCTURED_STYLES = ('maven', 'gradle', 'npm')

# Per-style sibling skill that exposes parse_log(log_file).
_STYLE_TO_PARSE_MODULE = {
    'maven': ('build-maven', '_maven_cmd_parse'),
    'gradle': ('build-gradle', '_gradle_cmd_parse'),
    'npm': ('build-npm', '_npm_parse_errors'),
}


def slugify_check_name(name: str) -> str:
    """Derive a collision-free, file-name-safe stem from a CI check name.

    Lowercases the input, replaces every run of non-alphanumeric characters with
    a single ``-``, and trims leading/trailing ``-``. Empty or all-separator
    input falls back to a stable token so the result is always a usable stem.

    Args:
        name: The CI check name (e.g. ``"verify / verify"``).

    Returns:
        A lowercase slug containing only ``[a-z0-9-]`` with no leading, trailing,
        or repeated ``-``. Returns ``SLUG_FALLBACK`` when the input has no usable
        characters.

    Example:
        >>> slugify_check_name("verify / verify")
        'verify-verify'
        >>> slugify_check_name("Build (3.12)")
        'build-3-12'
        >>> slugify_check_name("///")
        'check'
    """
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
    slug = slug.strip('-')
    return slug or SLUG_FALLBACK


def filter_log(raw_log: str, error_style: str = 'generic') -> str:
    """Produce a filtered error-extraction variant of a raw CI log.

    Args:
        raw_log: Full raw log content of a failing CI job.
        error_style: One of ``maven``, ``gradle``, ``npm``, or ``generic``
            (default). Structured styles route through the shared build parsers
            and fall back to the generic heuristic when no structured errors are
            found; any unrecognized value is treated as ``generic``.

    Returns:
        The filtered log text. For the generic heuristic this is the kept
        error-context windows joined with elision markers; for structured styles
        it is a rendered list of the parsed build issues.
    """
    if error_style in _STRUCTURED_STYLES:
        structured = _filter_structured(raw_log, error_style)
        if structured is not None:
            return structured
    return _filter_generic(raw_log)


def _filter_generic(raw_log: str) -> str:
    """Extract error lines plus surrounding context from a raw log.

    Matches each line against the generic error heuristic, keeps a window of
    ``CONTEXT_LINES`` lines on each side, collapses overlapping windows, and
    joins non-adjacent windows with ``ELISION_MARKER``. When no line matches,
    falls back to the trailing ``CONTEXT_LINES`` lines so triage always has
    content.

    Args:
        raw_log: Full raw log content.

    Returns:
        The filtered log text.
    """
    lines = raw_log.splitlines()
    if not lines:
        return ''

    match_indices = [i for i, line in enumerate(lines) if _GENERIC_ERROR_RE.search(line)]

    if not match_indices:
        tail = lines[-CONTEXT_LINES:]
        return '\n'.join(tail)

    windows = _merge_windows(match_indices, len(lines))
    return _render_windows(lines, windows)


def _merge_windows(match_indices: list[int], line_count: int) -> list[tuple[int, int]]:
    """Build merged [start, end) context windows around matched line indices.

    Each match contributes a window of ``CONTEXT_LINES`` lines on each side,
    clamped to ``[0, line_count)``. Overlapping or adjacent windows are merged.

    Args:
        match_indices: Sorted indices of lines that matched the error heuristic.
        line_count: Total number of lines in the log.

    Returns:
        A list of non-overlapping ``(start, end)`` half-open index ranges in
        ascending order.
    """
    windows: list[tuple[int, int]] = []
    for idx in match_indices:
        start = max(0, idx - CONTEXT_LINES)
        end = min(line_count, idx + CONTEXT_LINES + 1)
        if windows and start <= windows[-1][1]:
            prev_start, prev_end = windows[-1]
            windows[-1] = (prev_start, max(prev_end, end))
        else:
            windows.append((start, end))
    return windows


def _render_windows(lines: list[str], windows: list[tuple[int, int]]) -> str:
    """Render merged windows into filtered text with elision markers.

    Args:
        lines: The full list of log lines.
        windows: Ascending, non-overlapping ``(start, end)`` ranges.

    Returns:
        The kept lines, with ``ELISION_MARKER`` inserted between non-adjacent
        windows (and at the head/tail when content was elided there).
    """
    out: list[str] = []
    prev_end = 0
    for start, end in windows:
        if start > prev_end:
            out.append(ELISION_MARKER)
        out.extend(lines[start:end])
        prev_end = end
    if prev_end < len(lines):
        out.append(ELISION_MARKER)
    return '\n'.join(out)


def _filter_structured(raw_log: str, error_style: str) -> str | None:
    """Route a raw log through the shared build parser for ``error_style``.

    Writes the raw log to a temp file (the build parsers read from a path),
    invokes the per-system ``parse_log``, and renders the parsed error issues
    into filtered text.

    Args:
        raw_log: Full raw log content.
        error_style: A structured style (``maven`` / ``gradle`` / ``npm``).

    Returns:
        The rendered structured-error text, or ``None`` when the build parser
        is unavailable or produced no error issues (signalling the caller to
        fall back to the generic heuristic).
    """
    parse_log = _load_parse_log(error_style)
    if parse_log is None:
        return None

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False, encoding='utf-8') as handle:
            temp_path = handle.name
            handle.write(raw_log)
        issues, _test_summary, _build_status = parse_log(temp_path)
    except (OSError, ValueError, KeyError, IndexError, AttributeError, TypeError):
        return None
    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)

    error_issues = [issue for issue in issues if getattr(issue, 'severity', None) == 'error']
    if not error_issues:
        return None

    return _render_issues(error_issues)


def _render_issues(issues: list[object]) -> str:
    """Render parsed build issues into filtered text.

    Args:
        issues: Parsed build ``Issue`` objects (error severity).

    Returns:
        One line per issue in ``file:line: message`` form, with ``file`` /
        ``line`` omitted when not available, followed by any stack trace.
    """
    out: list[str] = []
    for issue in issues:
        file = getattr(issue, 'file', None)
        line = getattr(issue, 'line', None)
        message = getattr(issue, 'message', '')
        prefix = ''
        if file:
            prefix = f'{file}:{line}: ' if line is not None else f'{file}: '
        out.append(f'{prefix}{message}')
        stack_trace = getattr(issue, 'stack_trace', None)
        if stack_trace:
            out.append(stack_trace)
    return '\n'.join(out)


def _load_parse_log(error_style: str):
    """Lazily import the per-system ``parse_log`` for a structured style.

    Adds the build skill script directories to ``sys.path`` on first use so the
    generic path remains pure stdlib and importable without the build parsers
    being present.

    Args:
        error_style: A structured style (``maven`` / ``gradle`` / ``npm``).

    Returns:
        The ``parse_log`` callable, or ``None`` when the build parser modules
        cannot be imported in the current environment.
    """
    skill, module_name = _STYLE_TO_PARSE_MODULE[error_style]
    _ensure_build_parser_paths(skill)
    try:
        module = __import__(module_name)
    except ImportError:
        return None
    return getattr(module, 'parse_log', None)


def _ensure_build_parser_paths(skill: str) -> None:
    """Add the build skill + shared build script directories to ``sys.path``.

    Navigates from this file (``tools-integration-ci/scripts/``) up to the
    ``skills/`` directory and adds the per-system build skill's ``scripts``
    directory plus the shared ``script-shared/scripts/build`` directory that the
    build parsers depend on.

    Args:
        skill: The build skill directory name (e.g. ``build-maven``).
    """
    scripts_dir = Path(__file__).resolve().parent
    skills_dir = scripts_dir.parent.parent
    candidate_dirs = [
        skills_dir / skill / 'scripts',
        skills_dir / 'script-shared' / 'scripts' / 'build',
        skills_dir / 'tools-file-ops' / 'scripts',
    ]
    for directory in candidate_dirs:
        directory_str = str(directory)
        if directory.is_dir() and directory_str not in sys.path:
            sys.path.insert(0, directory_str)
