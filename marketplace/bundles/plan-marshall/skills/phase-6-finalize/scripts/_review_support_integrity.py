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
  added to another) IS caught, by matching per test identity.

The branch is read as ONE test set rather than one path at a time:

* a moved, renamed or split test file is not a lost assertion — the changed set
  pairs each deleted test path with the test paths the branch added or renamed, so
  an assertion that travelled with the file is still accounted for;
* the pre-image is read at ``git merge-base {base} HEAD``, the same tree the
  three-dot changed set describes, so an assertion the base branch gained after
  the branch point is never reported as removed;
* a test is named by an identity that does not depend on its file path —
  ``class::function`` for Python (``async def`` and indented methods included),
  the quoted name for a JS/TS ``it``/``test``/``describe``, and one entry per
  CLASS header for a file whose test headers neither arm parses — so a test that
  moved to another file is still the same test;
* the after-image is the working tree's text, falling back to ``HEAD:{path}``: an
  uncommitted removal is still graded, never hidden by the commit boundary;
* a plan with ``use_worktree: false`` is graded against the main checkout's diff
  to the base instead of being skipped as ``worktree_unresolved``; the evidence
  root the check chose is reported on the payload.

A loss is reported in exactly three cases, with the per-path report as the unit of
the finding row: the set total drops, a named test disappears from every
after-file, or one test's count drops while that test still exists.

Importable as ``from _review_support_integrity import ...`` by ``review_support.py``.
Every verb emits TOON and exits 0 on every outcome; an input that cannot be read is
``status: error`` with a named ``error``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from _criteria_snapshot import plan_uses_worktree
from _references_core import read_references, resolve_base_ref, resolve_live_worktree
from file_ops import cwd_checkout_root

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

#: A Python test-function header. ``async def`` is included (a coroutine test is a
#: test), and so is an indented ``def`` — a method declared inside a class. The
#: class it belongs to is tracked separately so the identity is ``Class::method``.
_TEST_DEF_RE = re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(')
#: A Python class header, the scope half of a method's identity.
_CLASS_DEF_RE = re.compile(r'^(\s*)class\s+(\w+)\s*[\(:]')
#: A class header in a language whose modifiers precede the keyword (``public
#: class``, ``open class``, ``abstract class``). Used only as the FALLBACK identity
#: for a file that declares no Python ``def`` and no JS/TS test call — the arm that
#: gives a non-Python test class an identity at all, so its removal can be declared
#: and accepted instead of being an identity-less row nobody can decide.
_ANY_CLASS_RE = re.compile(
    r'^\s*(?:(?:public|private|protected|abstract|final|static|open|sealed|internal|data)\s+)*class\s+(\w+)'
)
#: A JS/TS ``it``/``test``/``describe`` call. Its quoted name is the identity.
_JS_TEST_RE = re.compile(r'^\s*(?:it|test|describe)\s*\(\s*[\'"]([^\'"]+)[\'"]')


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


def main_checkout_root() -> Path | None:
    """The main checkout root, or ``None`` when it cannot be resolved.

    Module-level so a caller (and a test) can substitute it: it is the evidence
    root for a plan that runs WITHOUT a worktree, and a plan that cannot resolve
    one has no tree to grade, which must stay visible rather than become a pass.
    """
    try:
        root = Path(cwd_checkout_root())
    except Exception:
        return None
    return root if root.is_dir() else None


def changed_statuses(worktree: Path, base_ref: str) -> list[tuple[str, str, str | None]]:
    """Return ``(code, path, old_path)`` for the three-dot ``{base_ref}...HEAD`` diff.

    Renames are DETECTED (not suppressed): a renamed file is one delete plus one
    add, and the pair is what lets the caller account for assertions that
    travelled with the file. ``old_path`` is set only for a rename/copy source.
    Raises on git failure, exactly like :func:`changed_files`.
    """
    proc = _git(worktree, ['diff', '--name-status', '--find-renames', f'{base_ref}...HEAD'])
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr)
    entries: list[tuple[str, str, str | None]] = []
    for line in proc.stdout.splitlines():
        parts = [part for part in line.split('\t') if part]
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[1]
        if status[:1] in ('R', 'C') and len(parts) >= 3:
            entries.append((status[:1], parts[2], path))
        else:
            entries.append((status[:1], path, None))
    return entries


def changed_files(worktree: Path, base_ref: str) -> list[str]:
    """Return every changed path of ``{base_ref}...HEAD``, both sides of a rename.

    Renames are no longer suppressed: a moved test file appears as its old path
    (deleted side) and its new path (added side), so both are visible to the
    caller that pairs them. May raise on git failure.
    """
    paths: list[str] = []
    for _code, path, old_path in changed_statuses(worktree, base_ref):
        for candidate in (old_path, path):
            if candidate and candidate not in paths:
                paths.append(candidate)
    return paths


def merge_base(worktree: Path, base_ref: str) -> str | None:
    """Resolve ``git merge-base {base_ref} HEAD``, or ``None`` when it cannot be read.

    The pre-image must be read from the SAME tree the changed set describes. The
    three-dot diff already compares against the merge base, so reading the
    pre-image at the base ref's own tip compared two different trees: an
    assertion the base branch gained after the branch point then read as one the
    branch removed.
    """
    proc = _git(worktree, ['merge-base', base_ref, 'HEAD'])
    if proc.returncode != 0:
        return None
    resolved = proc.stdout.strip()
    return resolved or None


def _show(worktree: Path, rev: str, path: str) -> str | None:
    """Return the file's content at ``rev``, or ``None`` when it did not exist."""
    proc = _git(worktree, ['show', f'{rev}:{path}'])
    return proc.stdout if proc.returncode == 0 else None


def _after_image(root: Path, path: str) -> str | None:
    """Return the branch's text for ``path``: the working tree, else ``HEAD``.

    The working tree first is the behaviour this check already had, and it is the
    fail-closed direction: a test edited but not yet committed is still graded, so
    an uncommitted removal cannot hide behind the commit boundary. ``HEAD`` is the
    fallback for a path the working tree no longer carries.
    """
    target = root / path
    try:
        if target.is_file():
            return target.read_text(encoding='utf-8')
    except OSError:
        pass
    return _show(root, 'HEAD', path)


def _pre_image(worktree: Path, base_ref: str, path: str) -> str | None:
    """Return the file's content at ``merge-base {base_ref} HEAD``, or ``None``.

    ``base_ref`` is expected to be an already-resolved commit-ish; the merge base
    is resolved here so a caller passing a branch name still reads the tree the
    changed set was taken from. A base with no merge base (an unrelated history)
    falls back to the ref itself, which is the only tree available.
    """
    base = merge_base(worktree, base_ref) or base_ref
    return _show(worktree, base, path)


def is_test_path(path: str) -> bool:
    """Whether a path is a test surface by the repository's own naming conventions."""
    return any(indicator in path for indicator in TEST_PATH_INDICATORS)


def _count(text: str, patterns: tuple[re.Pattern[str], ...] = ASSERTION_PATTERNS) -> int:
    return sum(len(pattern.findall(text)) for pattern in patterns)


def _markers(text: str) -> set[str]:
    return {marker for marker in SKIP_MARKERS if marker in text}


def _function_assertion_counts(text: str) -> dict[str, int]:
    """Count assertion constructs per test identity, in the whole file.

    The identity does NOT depend on the file path: ``Class::method`` for a method
    declared inside a Python class, the bare function name for a top-level one, and
    the quoted name for a JS/TS ``it``/``test``/``describe``. ``async def`` counts as
    a test, and an indented ``def`` is the method arm of the class identity.

    A file that declares none of those — a test class in a language whose headers
    the two arms do not parse — falls back to its CLASS headers as the identity, one
    entry per class. That fallback is what keeps such a removal decidable: a row
    with no identity can be neither declared nor accepted.

    A file-level count misses an assertion removed from one test and added to
    another — the file total is unchanged — while the per-identity counts still
    show the loss.
    """
    spans = _identity_spans(text)
    if not spans:
        spans = _class_spans(text)
    counts: dict[str, int] = {}
    for index, (start, name) in enumerate(spans):
        end = spans[index + 1][0] if index + 1 < len(spans) else len(text)
        counts[name] = counts.get(name, 0) + _count(text[start:end])
    return counts


def _identity_spans(text: str) -> list[tuple[int, str]]:
    """The Python/JS test-function identities, in document order."""
    spans: list[tuple[int, str]] = []
    class_stack: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.strip():
            indent = len(line) - len(line.lstrip())
            while class_stack and class_stack[-1][0] >= indent:
                class_stack.pop()
            match = _TEST_DEF_RE.match(line)
            if match:
                prefix = f'{class_stack[-1][1]}::' if class_stack else ''
                spans.append((offset, prefix + match.group(1)))
            else:
                class_match = _CLASS_DEF_RE.match(line)
                if class_match:
                    class_stack.append((indent, class_match.group(2)))
                js_match = _JS_TEST_RE.match(line)
                if js_match:
                    spans.append((offset, js_match.group(1)))
        offset += len(line)
    return spans


def _class_spans(text: str) -> list[tuple[int, str]]:
    """The fallback identities: one per class header, in document order."""
    spans: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        match = _ANY_CLASS_RE.match(line)
        if match:
            spans.append((offset, match.group(1)))
        offset += len(line)
    return spans


def _normalized_body(text: str) -> str:
    """A whitespace-normalized body, so a pure move compares equal."""
    return '\n'.join(line.rstrip() for line in text.strip().splitlines())


def _evidence_root(plan_id: str) -> tuple[Path | None, str | None]:
    """Resolve the tree the branch diff is read from, and name the choice.

    A worktree-bound plan is graded against its worktree. A plan that runs WITHOUT
    a worktree (``use_worktree: false``) is graded against the main checkout — the
    tree the finalize contract assigns it — so it is graded rather than skipped as
    ``worktree_unresolved``. A plan that DECLARED a materialized worktree which
    does not resolve now returns ``None``: grading it against another tree would
    compare two heads.
    """
    try:
        worktree = resolve_live_worktree(plan_id)
    except Exception:
        worktree = None
    if worktree is not None:
        resolved = Path(worktree)
        return (resolved, 'worktree') if resolved.is_dir() else (None, None)
    if plan_uses_worktree(plan_id):
        return None, None
    root = main_checkout_root()
    return (root, 'main_checkout') if root is not None else (None, None)


def _row(path: str, removed: int, removed_tests: list[dict[str, Any]], detail: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        'path': path,
        'kind': 'assertion_removed',
        'removed_assertions': removed,
        'removed_tests': removed_tests,
        'detail': detail,
    }
    names = [entry['identity'] for entry in removed_tests]
    if names:
        row['weakened_functions'] = names
    return row


def compute_test_integrity(plan_id: str, base_ref: str | None = None) -> dict[str, Any]:
    """Report every changed test whose assertions were removed or filtered.

    One finding per weakened test file:

    * ``assertion_removed`` — a loss in one of the three cases: the changed test
      set's assertion total drops, a named test disappears from every after-file,
      or one test's count drops while that test still exists (including the net
      count evasion and a deleted test whose assertions were added to another test
      in the same file).
    * ``test_filtered`` — the branch adds a skip/xfail marker the pre-image did
      not carry.

    A file the branch ADDS is not reported: removing an assertion means removing
    one that existed before the change. The comparator reads the whole changed
    test set, so a moved / renamed / split file is not a loss, and reads the
    pre-image at the merge base, so an assertion the base branch gained later is
    not reported. It does NOT catch a RELAXED assertion that keeps the count
    (`assert x == 5` rewritten to `assert x is not None`), which stays the
    author's reading of the change rather than this verb's count.
    """
    root, evidence_kind = _evidence_root(plan_id)
    if root is None:
        if plan_uses_worktree(plan_id):
            return _error(plan_id, 'worktree_unresolved', 'no worktree is materialized for the plan')
        return _error(plan_id, 'evidence_root_unresolved', 'no tree could be resolved to grade the branch diff')
    refs = read_references(plan_id)
    resolved_base = resolve_base_ref(base_ref, refs if isinstance(refs, dict) else {}, root)
    try:
        entries = changed_statuses(root, resolved_base)
    except (subprocess.SubprocessError, OSError) as exc:
        return _error(plan_id, 'diff_unavailable', f'{resolved_base}...HEAD could not be read: {exc}')
    base_tree = merge_base(root, resolved_base) or resolved_base

    before: dict[str, str] = {}
    after: dict[str, str] = {}
    renamed_from: dict[str, str] = {}
    for code, path, old_path in entries:
        if code in ('R', 'C'):
            if old_path and is_test_path(old_path):
                text = _show(root, base_tree, old_path)
                if text is not None:
                    before[old_path] = text
            if is_test_path(path):
                text = _after_image(root, path)
                if text is not None:
                    after[path] = text
                    if old_path:
                        renamed_from[path] = old_path
        elif code == 'D':
            if is_test_path(path):
                text = _show(root, base_tree, path)
                if text is not None:
                    before[path] = text
        elif code == 'A':
            if is_test_path(path):
                text = _after_image(root, path)
                if text is not None:
                    after[path] = text
        elif is_test_path(path):
            pre = _pre_image(root, resolved_base, path)
            post = _after_image(root, path)
            if pre is not None:
                before[path] = pre
            if post is not None:
                after[path] = post

    after_identities: dict[str, int] = {}
    for text in after.values():
        for identity, count in _function_assertion_counts(text).items():
            after_identities[identity] = after_identities.get(identity, 0) + count

    findings: list[dict[str, Any]] = []
    for path, pre in before.items():
        before_fns = _function_assertion_counts(pre)
        before_file = _count(pre)
        post = after.get(path)
        if post is None:
            missing = {identity: count for identity, count in before_fns.items() if identity not in after_identities}
            if missing:
                findings.append(
                    _row(
                        path,
                        sum(missing.values()),
                        [
                            {'identity': identity, 'assertions_removed': count}
                            for identity, count in sorted(missing.items())
                        ],
                        f'{sum(missing.values())} assertion(s) of {", ".join(sorted(missing))} are gone from '
                        f'every file the branch carries',
                    )
                )
                continue
            # No identity could be extracted (a non-Python test class): fall back to
            # the file's own count, unless the same body simply moved.
            if not before_fns and before_file and not _content_survives(pre, after):
                findings.append(
                    _row(
                        path,
                        before_file,
                        [],
                        f'{before_file} assertion(s) present at {base_tree} are gone from the file',
                    )
                )
            continue

        after_fns = _function_assertion_counts(post)
        file_loss = before_file - _count(post)
        drops = {
            identity: count - after_fns[identity]
            for identity, count in before_fns.items()
            if identity in after_fns and after_fns[identity] < count
        }
        missing = {
            identity: count
            for identity, count in before_fns.items()
            if identity not in after_fns and identity not in after_identities
        }
        identity_loss = sum(drops.values()) + sum(missing.values())
        removed = max(0, max(file_loss, identity_loss))
        if removed:
            removed_tests = [
                {'identity': identity, 'assertions_removed': count}
                for identity, count in sorted({**drops, **missing}.items())
            ]
            detail = f'{removed} assertion(s) present at {base_tree} are gone from the file'
            names = sorted({**drops, **missing})
            if names:
                detail = f'{removed} assertion(s) present at {base_tree} are gone from {", ".join(names)}'
                if file_loss <= 0:
                    detail += ', while the file total is not reduced by the same amount'
            findings.append(_row(path, removed, removed_tests, detail))

    # Case 1: the total across the whole changed test set dropped. This is the
    # last-net guard — a genuine loss the per-identity pass could not explain (a
    # language whose test headers are not parsed) is still reported, never dropped.
    before_total = sum(_count(text) for text in before.values())
    after_total = sum(_count(text) for text in after.values())
    explained = sum(finding['removed_assertions'] for finding in findings)
    if after_total < before_total and before_total - after_total > explained:
        holders = sorted(before.items(), key=lambda item: -_count(item[1]))
        if holders:
            path, text = holders[0]
            findings.append(
                _row(
                    path,
                    before_total - after_total - explained,
                    [],
                    f'the changed test set holds {before_total - after_total} assertion(s) fewer than at {base_tree}',
                )
            )

    for path, post in after.items():
        # A marker is only "added by the branch" against a pre-image. An ADDED test
        # file has none (the branch created it, so it filtered nothing), and a
        # RENAMED file's pre-image lives under the old path. Comparing an added file
        # against '' reported every new skipped test as filtered, which the retired
        # check never did.
        pre_path = path if path in before else renamed_from.get(path)
        if pre_path is None:
            continue
        pre = before.get(pre_path, '')
        added_markers = sorted(_markers(post) - _markers(pre))
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
        'merge_base': base_tree,
        'evidence_root': evidence_kind,
        'finding_count': len(findings),
        'findings': findings,
    }


def _content_survives(pre: str, after: dict[str, str]) -> bool:
    """Whether a body the branch deleted reappears verbatim in an after-file."""
    wanted = _normalized_body(pre)
    return any(_normalized_body(text) == wanted for text in after.values())


__all__ = [
    'ASSERTION_PATTERNS',
    'SKIP_MARKERS',
    'TEST_PATH_INDICATORS',
    'changed_files',
    'changed_statuses',
    'compute_test_integrity',
    'is_test_path',
    'main_checkout_root',
    'merge_base',
]
