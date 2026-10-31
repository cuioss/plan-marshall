#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""One integrity gate for the finalize review — internal module, not an entry point.

Answers a question the review used to answer in prose, and which was observed fail
open on real runs:

* :func:`compute_test_integrity` — every pre-existing test whose assertions the
  branch removed or filtered. pm-mcp-core PLAN-41 filtered an assertion and
  PLAN-44 reshaped a test-catalog entry to stay green; a review that compares only
  the tests the branch ADDS never sees it. A relaxed assertion that keeps its
  assertion count is not caught by the count and stays the review author's reading
  of the change; a net-count evasion (one assertion removed from a test and one
  added to another) IS caught, by matching per test function.

Imported as ``from _review_support_integrity import ...`` by ``review_support.py``.
Every verb emits TOON and exits 0 on every outcome; an input that cannot be read is
``status: error`` with a named ``error``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from _references_core import read_references, resolve_base_ref, resolve_live_worktree

#: Substrings that make a changed path a test surface.
TEST_PATH_INDICATORS = ('test/', 'tests/', 'test_', '_test.', '.test.', '.spec.', 'spec/', 'Test.', 'IT.')

#: One assertion-bearing construct per supported language family.
ASSERTION_PATTERNS = (
    re.compile(r'(?<![\w.])assert\b'),
    re.compile(r'\.assert[A-Z]\w*'),
    re.compile(r'\bassert[A-Z]\w*\('),
    re.compile(r'\bexpect\s*\('),
    re.compile(r'\bAssertions\.\w+\('),
    re.compile(r'\.should\b'),
    re.compile(r'\bfail\s*\('),
)

#: Constructs that FILTER a test rather than asserting in it.
SKIP_MARKERS = (
    'pytest.mark.skip',
    'pytest.mark.xfail',
    'it.skip',
    'describe.skip',
    'test.skip',
    'xit(',
    'xdescribe(',
    '@Disabled',
    '@Ignore',
    'unittest.skip',
)


def _error(plan_id: str, error: str, message: str) -> dict[str, Any]:
    return {'status': 'error', 'plan_id': plan_id, 'error': error, 'message': message}


def _git(worktree: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', '-C', str(worktree), *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def changed_files(worktree: Path, base_ref: str) -> list[str]:
    """Return the three-dot ``{base_ref}...HEAD`` changed paths (may raise on git failure)."""
    proc = _git(worktree, ['diff', '--name-only', '--no-renames', f'{base_ref}...HEAD'])
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _pre_image(worktree: Path, base_ref: str, path: str) -> str | None:
    """Return the file's content at ``base_ref``, or ``None`` when it did not exist."""
    proc = _git(worktree, ['show', f'{base_ref}:{path}'])
    return proc.stdout if proc.returncode == 0 else None


def is_test_path(path: str) -> bool:
    """Whether a path is a test surface by the repository's own naming conventions."""
    return any(indicator in path for indicator in TEST_PATH_INDICATORS)


def _count(text: str, patterns: tuple[re.Pattern[str], ...]) -> int:
    return sum(len(pattern.findall(text)) for pattern in patterns)


def _markers(text: str) -> set[str]:
    return {marker for marker in SKIP_MARKERS if marker in text}


#: A test-function header: a TOP-LEVEL Python ``def`` or an ``it``/``test``/
#: ``describe`` call. The Python arm is anchored at column 0 so a nested helper is
#: not read as its own function (its assertions stay in the enclosing test), and a
#: method indented inside a class is not mistaken for a top-level test. Counts are
#: per function, which is what closes net-count evasion.
_FUNCTION_HEADER_RE = re.compile(r'(?m)^def\s+(\w+)|^[ \t]*(?:it|test|describe)\s*\(\s*[\'"]([^\'"]+)[\'"]')


def _function_assertion_counts(text: str) -> dict[str, int]:
    """Count assertion constructs per test function, keyed by function name.

    Splits ``text`` on test-function headers and counts only the assertions inside
    each function's own body. A file-level count misses an assertion removed from
    one test and added to another — the file total is unchanged — while the
    per-function counts still show the loss.
    """
    spans = [(match.start(), match.group(1) or match.group(2) or '') for match in _FUNCTION_HEADER_RE.finditer(text)]
    counts: dict[str, int] = {}
    for index, (start, name) in enumerate(spans):
        end = spans[index + 1][0] if index + 1 < len(spans) else len(text)
        counts[name] = counts.get(name, 0) + _count(text[start:end], ASSERTION_PATTERNS)
    return counts


def compute_test_integrity(plan_id: str, base_ref: str | None = None) -> dict[str, Any]:
    """Report every changed test whose assertions were removed or filtered.

    One finding per weakened test file:

    * ``assertion_removed`` — an assertion the base tree held is gone, either from
      the FILE total or from one test function whose count dropped while another
      function's count rose (net-count evasion).
    * ``test_filtered`` — the branch adds a skip/xfail marker the base tree did
      not carry.

    A file the branch ADDS is not reported: removing an assertion means removing
    one that existed before the change. The comparator counts assertion constructs
    both per file and per test function — the per-function leg is what catches a
    net-zero file whose loss moved from one test to another — not a diff-line
    heuristic. It does NOT catch a RELAXED assertion that keeps the count
    (`assert x == 5` rewritten to `assert x is not None`), which stays the author's
    reading of the change rather than this verb's count.
    """
    worktree = resolve_live_worktree(plan_id)
    if worktree is None:
        return _error(plan_id, 'worktree_unresolved', 'no worktree is materialized for the plan')
    refs = read_references(plan_id)
    resolved_base = resolve_base_ref(base_ref, refs if isinstance(refs, dict) else {}, worktree)
    try:
        paths = changed_files(worktree, resolved_base)
    except (subprocess.SubprocessError, OSError) as exc:
        return _error(plan_id, 'diff_unavailable', f'{resolved_base}...HEAD could not be read: {exc}')

    findings: list[dict[str, Any]] = []
    for path in paths:
        if not is_test_path(path):
            continue
        before = _pre_image(worktree, resolved_base, path)
        if before is None:
            continue
        target = worktree / path
        if not target.exists():
            # The branch DELETED an existing test: every assertion it held is gone.
            after = ''
        else:
            try:
                after = target.read_text(encoding='utf-8')
            except OSError:
                continue
        file_loss = _count(before, ASSERTION_PATTERNS) - _count(after, ASSERTION_PATTERNS)
        before_fns = _function_assertion_counts(before)
        after_fns = _function_assertion_counts(after)
        # A function present in BOTH trees whose count dropped. A function absent
        # from the after tree is a rename or a deletion, not a per-function loss —
        # counting it would report a renamed test as weakened — so those are left to
        # the file-level count.
        weakened_functions = sorted(
            name for name, count in before_fns.items() if name in after_fns and after_fns[name] < count
        )
        per_function_removed = sum(
            max(0, count - after_fns[name]) for name, count in before_fns.items() if name in after_fns
        )
        removed = max(max(0, file_loss), per_function_removed)
        added_markers = sorted(_markers(after) - _markers(before))
        if removed:
            finding: dict[str, Any] = {
                'path': path,
                'kind': 'assertion_removed',
                'removed_assertions': removed,
                'detail': f'{removed} assertion(s) present at {resolved_base} are gone from the file',
            }
            if weakened_functions:
                finding['weakened_functions'] = weakened_functions
                if per_function_removed > max(0, file_loss):
                    finding['detail'] = (
                        f'{removed} assertion(s) present at {resolved_base} are gone from '
                        f'{", ".join(weakened_functions)}, while the file total is not reduced by the same amount'
                    )
            findings.append(finding)
        if added_markers:
            findings.append(
                {
                    'path': path,
                    'kind': 'test_filtered',
                    'markers': added_markers,
                    'detail': f'the branch adds {", ".join(added_markers)}: the test no longer runs',
                }
            )
    return {
        'status': 'success',
        'plan_id': plan_id,
        'base_ref': resolved_base,
        'finding_count': len(findings),
        'findings': findings,
    }


__all__ = [
    'ASSERTION_PATTERNS',
    'SKIP_MARKERS',
    'TEST_PATH_INDICATORS',
    'changed_files',
    'compute_test_integrity',
    'is_test_path',
]
