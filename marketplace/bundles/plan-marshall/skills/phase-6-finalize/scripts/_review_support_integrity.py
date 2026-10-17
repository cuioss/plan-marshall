#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Two integrity gates for the finalize review — internal module, not an entry point.

Both answer a question the review used to answer in prose, and both were
observed fail open on real runs:

* :func:`compute_test_integrity` — every pre-existing test whose assertions the
  branch removed or filtered. pm-mcp-core PLAN-41 filtered an assertion and
  PLAN-44 reshaped a test-catalog entry to stay green; a review that compares
  only the tests the branch ADDS never sees it. A relaxed assertion that keeps
  its assertion count is not caught by the count and stays the review author's
  reading of the change.
* :func:`record_verify_first` / :func:`check_verify_first` — a verify-first gate's
  evidence must predate the action it gates. PLAN-LB-40 logged its nine-consumer
  gate as passed before running it, committed the gated change at 20:15 and ran
  the real check at 20:47.

Imported as ``from _review_support_integrity import ...`` by ``review_support.py``.
Every verb emits TOON and exits 0 on every outcome; an input that cannot be read
is ``status: error`` with a named ``error``.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _references_core import read_references, resolve_base_ref, resolve_live_worktree
from file_ops import base_path

#: Plan-relative path of the verify-first evidence ledger.
VERIFY_FIRST_FILE = 'work/verify-first.jsonl'

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
    proc = _git(worktree, ['diff', '--name-only', f'{base_ref}...HEAD'])
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


def compute_test_integrity(plan_id: str, base_ref: str | None = None) -> dict[str, Any]:
    """Report every changed test whose assertions were removed or filtered.

    One finding per weakened test file:

    * ``assertion_removed`` — the branch leaves fewer assertion constructs in the
      file than the base tree had.
    * ``test_filtered`` — the branch adds a skip/xfail marker the base tree did
      not carry.

    A file the branch ADDS is not reported: removing an assertion means removing
    one that existed before the change. The comparator is the COUNT of assertion
    constructs, not a diff-line heuristic, so it catches a removed assertion and a
    dropped negative case; it does NOT catch a RELAXED assertion that keeps the
    count (`assert x == 5` rewritten to `assert x is not None`), which stays the
    author's reading of the change rather than this verb's count.
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
        try:
            after = target.read_text(encoding='utf-8')
        except OSError:
            continue
        removed = max(0, _count(before, ASSERTION_PATTERNS) - _count(after, ASSERTION_PATTERNS))
        added_markers = sorted(_markers(after) - _markers(before))
        if removed:
            findings.append(
                {
                    'path': path,
                    'kind': 'assertion_removed',
                    'removed_assertions': removed,
                    'detail': f'{removed} assertion(s) present at {resolved_base} are gone from the file',
                }
            )
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


def record_verify_first(plan_id: str, gate: str, evidence: str) -> dict[str, Any]:
    """Append one verify-first evidence record, stamped with the moment it is written.

    The timestamp is derived here and never accepted as an argument: a caller-
    supplied one could always be back-dated to satisfy the check it exists for.
    """
    if not str(gate or '').strip() or not str(evidence or '').strip():
        return _error(plan_id, 'invalid_arguments', 'a verify-first record needs a gate and its evidence')
    path = base_path('plans', plan_id, VERIFY_FIRST_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'gate': gate,
        'evidence': evidence,
        'recorded_at': datetime.now(UTC).isoformat(),
    }
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, sort_keys=True) + '\n')
    return {
        'status': 'success',
        'plan_id': plan_id,
        'file': VERIFY_FIRST_FILE,
        'gate': gate,
        'recorded_at': record['recorded_at'],
    }


def _records(plan_id: str) -> list[dict[str, Any]]:
    """Read every verify-first record; an unreadable line is skipped, not guessed at."""
    path = base_path('plans', plan_id, VERIFY_FIRST_FILE)
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _commit_time(worktree: Path, commit: str) -> datetime | None:
    proc = _git(worktree, ['show', '-s', '--format=%cI', commit])
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def check_verify_first(plan_id: str, gate: str, commit: str) -> dict[str, Any]:
    """Refuse when a verify-first gate's evidence does not predate ``commit``.

    The gate passed before the action it gates exactly when each of its recorded
    evidence entries was written strictly before the gated commit. A gate with NO
    record has no evidence that predates the commit, and a record written at or
    after the commit is evidence gathered after the fact — both are refusals, and
    both are what PLAN-LB-40's faked nine-consumer gate looks like from here.
    """
    worktree = resolve_live_worktree(plan_id)
    if worktree is None:
        return _error(plan_id, 'worktree_unresolved', 'no worktree is materialized for the plan')
    when = _commit_time(worktree, commit)
    if when is None:
        return _error(plan_id, 'unknown_commit', f'{commit!r} does not resolve in the worktree')
    matching = [row for row in _records(plan_id) if str(row.get('gate')) == gate]
    if not matching:
        return _error(
            plan_id,
            'verify_first_evidence_missing',
            f'gate {gate!r} has no recorded evidence, so nothing predates {commit}',
        )
    postdating = [
        {'evidence': str(row.get('evidence', '')), 'recorded_at': str(row.get('recorded_at', ''))}
        for row in matching
        if _after(row.get('recorded_at'), when)
    ]
    if postdating:
        return {
            **_error(
                plan_id,
                'verify_first_evidence_postdates_commit',
                f'gate {gate!r} has evidence recorded at or after {commit}: the check ran after the action it gates',
            ),
            'commit': commit,
            'commit_time': when.isoformat(),
            'postdating': postdating,
        }
    return {
        'status': 'success',
        'plan_id': plan_id,
        'gate': gate,
        'commit': commit,
        'commit_time': when.isoformat(),
        'records': len(matching),
    }


def _after(recorded_at: Any, commit_time: datetime) -> bool:
    """Whether a record's timestamp is at or after the commit time.

    An unparseable timestamp is treated as postdating: a record whose age cannot
    be established is not evidence that it came first.
    """
    try:
        parsed = datetime.fromisoformat(str(recorded_at))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed >= commit_time


__all__ = [
    'ASSERTION_PATTERNS',
    'SKIP_MARKERS',
    'TEST_PATH_INDICATORS',
    'VERIFY_FIRST_FILE',
    'changed_files',
    'check_verify_first',
    'compute_test_integrity',
    'is_test_path',
    'record_verify_first',
]
