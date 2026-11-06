#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""One integrity gate for the finalize review — internal module, not an entry point.

Answers a question that belongs to a computation rather than the reviewer's prose,
and which fails open if left to reading:

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
* the after-image is the working tree's text, falling back to ``HEAD:{path}``, for
  a path the branch has COMMITTED a change to: a further uncommitted edit there is
  still graded;
* a plan with ``use_worktree: false`` is graded against the main checkout's diff
  to the base when that checkout carries the plan's work (its HEAD is not the base
  tip and its tree is clean), and refused as ``evidence_root_unresolved``
  otherwise; the evidence root the check chose is reported on the payload.

A loss is reported in exactly four cases: the set total drops, a named test disappears from every after-file, one test's count drops while that test still exists, or a surviving path's own total drops and no identity accounts for it. The per-path report is the unit of the finding row. A deleted test identity is a MOVE only when its assertion CONTENT reappears in an after-file: a bare name there proves nothing, so a same-named test in another changed file cannot absorb a loss, while a function moved with its assertions is not a loss. Both key the accepted set by what the entry NAMES: a test identity plus its removed count, a filter's marker set plus the identity of each marked test, or a path-level row kind (mixed residual / file total / set total) plus its count. A declaration without a count decides a removal only, never a drop of a surviving test.

Importable as ``from _review_support_integrity import ...`` by ``review_support.py``.
Every verb emits TOON and exits 0 on every outcome; an input that cannot be read is
``status: error`` with a named ``error``.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
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
#: A JS/TS ``it``/``test``/``describe`` call, INCLUDING the skip forms. The skip
#: form replaces the header rather than decorating it (``it.skip('x', ...)`), so the
#: pattern must match it: otherwise the filtered test has no identity, reads as a
#: named test that vanished, and its marker is never compared.
_JS_TEST_RE = re.compile(r'^\s*(?:it|test|describe|xit|xdescribe)(?:\.skip)?\s*\(\s*[\'"]([^\'"]+)[\'"]')

#: Three-quote delimiters, so a string body that starts a line at column 0 is not
#: mistaken for a new top-level statement.
_TRIPLE_QUOTES = ("'''", '"""')


def _significant_lines(text: str):
    """Yield ``(offset, line, significant)`` for every line of ``text``.

    A blank line, a comment-only line and every line inside a triple-quoted string
    are not significant for SCOPE tracking: a column-0 comment or a dedented
    string body inside a class does not close the class, so the methods after it
    keep their ``Class::`` prefix.
    """
    in_string: str | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        significant = True
        if in_string is not None:
            significant = False
            if in_string in line:
                in_string = None
        elif not stripped or stripped.startswith('#'):
            significant = False
        else:
            for quote in _TRIPLE_QUOTES:
                index = line.find(quote)
                if index >= 0:
                    if line.find(quote, index + len(quote)) < 0:
                        in_string = quote
                    break
        yield offset, line, significant
        offset += len(line)


class _GitFailure(Exception):
    """A git call whose failure does not mean "the object is absent"."""


def _error(plan_id: str, error: str, message: str) -> dict[str, Any]:
    return {'status': 'error', 'plan_id': plan_id, 'error': error, 'message': message}


def _git(worktree: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one git command with paths emitted literally (never C-quoted).

    ``core.quotePath=false`` is passed so a non-ASCII path comes back as the bytes
    the tree holds rather than as an escaped string the caller then fails to match.
    A timeout surfaces as :class:`_GitFailure` instead of escaping as a
    ``subprocess.TimeoutExpired`` traceback, so the caller can report a named
    state.
    """
    try:
        return subprocess.run(
            ['git', '-c', 'core.quotePath=false', '-C', str(worktree), *args],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise _GitFailure(f'git {args[0] if args else ""} timed out') from exc
    except OSError as exc:
        raise _GitFailure(f'git could not be run: {exc}') from exc


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


def changed_statuses(worktree: Path, base_ref: str, head_ref: str = 'HEAD') -> list[tuple[str, str, str | None]]:
    """Return ``(code, path, old_path)`` for the three-dot ``{base_ref}...{head_ref}`` diff.

    Renames are DETECTED (not suppressed): a renamed file is one delete plus one
    add, and the pair is what lets the caller account for assertions that
    travelled with the file. ``old_path`` is set only for a rename/copy source.
    Raises on git failure, exactly like :func:`changed_files`.
    """
    proc = _git(worktree, ['diff', '--name-status', '--find-renames', '-z', f'{base_ref}...{head_ref}'])
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr)
    # NUL-delimited records: `status\0path\0` for one path, `status\0old\0new\0` for a
    # rename/copy. Reading them NUL-wise keeps a path containing `"`, `\`, TAB or LF
    # literal; the line-oriented form C-quotes those and the quoted string then names
    # no file in the tree.
    tokens = proc.stdout.split('\0')
    entries: list[tuple[str, str, str | None]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        if not status:
            index += 1
            continue
        if status[:1] in ('R', 'C'):
            if index + 2 >= len(tokens):
                break
            entries.append((status[:1], tokens[index + 2], tokens[index + 1]))
            index += 3
        else:
            if index + 1 >= len(tokens):
                break
            entries.append((status[:1], tokens[index + 1], None))
            index += 2
    return entries


def changed_files(worktree: Path, base_ref: str) -> list[str]:
    """Return every changed path of ``{base_ref}...HEAD``, both sides of a rename.

    Renames are detected: a moved test file appears as its old path
    (deleted side) and its new path (added side), so both are visible to the
    caller that pairs them. May raise on git failure.
    """
    paths: list[str] = []
    for _code, path, old_path in changed_statuses(worktree, base_ref):
        for candidate in (old_path, path):
            if candidate and candidate not in paths:
                paths.append(candidate)
    return paths


def merge_base(worktree: Path, base_ref: str, head_ref: str = 'HEAD') -> str | None:
    """Resolve ``git merge-base {base_ref} {head_ref}``, or ``None`` when it cannot be read.

    The pre-image must be read from the SAME tree the changed set describes. The
    three-dot diff already compares against the merge base, so reading the
    pre-image at the base ref's own tip compared two different trees: an
    assertion the base branch gained after the branch point then read as one the
    branch removed.
    """
    proc = _git(worktree, ['merge-base', base_ref, head_ref])
    if proc.returncode != 0:
        return None
    resolved = proc.stdout.strip()
    return resolved or None


#: ``git show`` failures that mean the PATH is genuinely absent from the revision,
#: as opposed to a call that failed for another reason (a bad revision, permissions, a
#: corrupt object store, a killed process). Only the former is "did not exist": a
#: missing REVISION is a failed read, and reading it as an absent file would drop a
#: deleted test's pre-image and count its loss nowhere.
_ABSENT_PATTERNS = (
    'does not exist in',
    'exists on disk, but not in',
)


def _show(worktree: Path, rev: str, path: str) -> str | None:
    """Return the file's content at ``rev``, or ``None`` when it did not exist.

    A non-zero exit is only read as "the path did not exist" when git says so.
    Any other failure raises :class:`_GitFailure`, because reading a failed
    ``git show`` as an absent file would drop a deleted test's pre-image and
    count its loss nowhere.
    """
    proc = _git(worktree, ['show', f'{rev}:{path}'])
    if proc.returncode == 0:
        return proc.stdout
    message = f'{proc.stderr or ""}{proc.stdout or ""}'
    if any(pattern in message for pattern in _ABSENT_PATTERNS):
        return None
    raise _GitFailure(f'git show {rev}:{path} failed: {message.strip() or proc.returncode}')


def _after_image(root: Path, path: str, head_ref: str | None = None) -> str | None:
    """Return the branch's text for ``path``: the working tree, else ``HEAD``.

    When ``head_ref`` names a commit, the committed tree at that commit is read
    instead of the working tree, so a close pins the rows to the head the finding
    was validated at.

    Without ``head_ref``, the working tree is read first. That is fail-closed when
    a further *removal* is still uncommitted: it is graded. It does NOT guarantee
    the converse — a removal the branch COMMITTED and someone restored only in the
    working tree reads as not removed here. The changed SET is the committed
    three-dot diff, so a path the branch never committed is not read at all.

    ``HEAD`` is the fallback for a path the working tree no longer carries.
    """
    if head_ref is not None:
        return _show(root, head_ref, path)
    target = root / path
    try:
        if target.is_file():
            return target.read_text(encoding='utf-8')
    except OSError:
        pass
    return _show(root, 'HEAD', path)


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
    entry per class. That fallback is what keeps such a removal decidable under an
    identity; a row with NO identity at all is acceptable by its explicit path-level
    key, so no row is unacceptable by construction.

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


def _identity_bodies(text: str) -> dict[str, str]:
    """The whitespace-normalized BODY of every UNIQUE test identity.

    The body runs from the identity's own header to the next identity's header, so a
    move is proven by the test's assertion content rather than by its name. Two
    different tests that share a name therefore carry different bodies, and a bare
    name in another file proves nothing. An identity that occurs MORE THAN ONCE in
    one file is omitted: its count is a sum no single body can prove, so crediting a
    move would over-credit it — the identity then survives nothing and its loss is
    reported, the fail-closed direction.
    """
    spans = _identity_spans(text) or _class_spans(text)
    bodies: dict[str, str] = {}
    repeated: set[str] = set()
    for index, (start, name) in enumerate(spans):
        if name in bodies:
            repeated.add(name)
        end = spans[index + 1][0] if index + 1 < len(spans) else len(text)
        bodies[name] = _normalized_body(text[start:end])
    for name in repeated:
        bodies.pop(name, None)
    return bodies


def _assertion_lines(text: str) -> list[str]:
    """The stripped assertion-bearing LINES of a body — the fingerprint a move is proven by."""
    return [line.strip() for line in text.splitlines() if any(pattern.search(line) for pattern in ASSERTION_PATTERNS)]


def _identity_spans(text: str) -> list[tuple[int, str]]:
    """The Python/JS test-function identities, in document order.

    The class scope is a stack of ``(indent, full_path)``. A class is popped only
    by a significant line at or below its own indent, so a column-0 comment or a
    dedented string body inside the class body does not end it. A nested class
    keeps its full path (``A.Inner``), so ``A.Inner::m`` and ``B.Inner::m`` are
    distinct identities.
    """
    spans: list[tuple[int, str]] = []
    class_stack: list[tuple[int, str]] = []
    for offset, line, significant in _significant_lines(text):
        if not significant:
            continue
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
                parent = f'{class_stack[-1][1]}.' if class_stack else ''
                class_stack.append((indent, parent + class_match.group(2)))
            js_match = _JS_TEST_RE.match(line)
            if js_match:
                spans.append((offset, js_match.group(1)))
    return spans


def _class_spans(text: str) -> list[tuple[int, str]]:
    """The fallback identities: one per class header, in document order.

    A nested class keeps its full path, so two ``Inner`` classes declared under
    different outer classes do not collide.
    """
    spans: list[tuple[int, str]] = []
    stack: list[tuple[int, str]] = []
    for offset, line, significant in _significant_lines(text):
        if not significant:
            continue
        match = _ANY_CLASS_RE.match(line)
        if not match:
            continue
        indent = len(line) - len(line.lstrip())
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = f'{stack[-1][1]}.' if stack else ''
        stack.append((indent, parent + match.group(1)))
        spans.append((offset, stack[-1][1]))
    return spans


def _normalized_body(text: str) -> str:
    """A whitespace-normalized body, so a pure move compares equal."""
    return '\n'.join(line.rstrip() for line in text.strip().splitlines())


def _rev_parse(root: Path, ref: str) -> str | None:
    """Resolve a ref to a commit id, or ``None`` when it cannot be read."""
    proc = _git(root, ['rev-parse', '--verify', f'{ref}^{{commit}}'])
    if proc.returncode != 0:
        return None
    resolved = proc.stdout.strip()
    return resolved or None


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Whether ``ancestor`` is an ancestor of (or equal to) ``descendant``.

    ``git merge-base --is-ancestor`` uses exit 1 for "no" and any other non-zero exit
    for "the question could not be asked" (a missing object, a corrupt repository).
    Reading every non-zero exit as "not an ancestor" turned a failed read into a
    positive claim that the checkout sat at or behind its base, so the third state is
    raised as :class:`_GitFailure` and reported as ``test_integrity_not_run``.
    """
    proc = _git(root, ['merge-base', '--is-ancestor', ancestor, descendant])
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    message = f'{proc.stderr or ""}{proc.stdout or ""}'.strip()
    raise _GitFailure(f'git merge-base --is-ancestor failed: {message or proc.returncode}')


def _current_branch(root: Path) -> str | None:
    """The branch the checkout has checked out, or ``None`` for a detached HEAD."""
    proc = _git(root, ['symbolic-ref', '--quiet', '--short', 'HEAD'])
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def _tree_is_dirty(root: Path) -> bool:
    """Whether the checkout carries uncommitted changes.

    A ``git status`` that cannot be read is a FAILED check, not a clean tree: the
    caller must report a named state rather than grade a tree it could not inspect.
    """
    proc = _git(root, ['status', '--porcelain'])
    if proc.returncode != 0:
        raise _GitFailure('git status failed')
    return bool(proc.stdout.strip())


def _evidence_root(plan_id: str) -> tuple[Path | None, str | None]:
    """Resolve the tree the branch diff is read from, and name the choice.

    A worktree-bound plan is graded against its worktree. A plan that runs WITHOUT
    a worktree (``use_worktree: false``) is graded against the main checkout — the
    tree the finalize contract assigns it — but only when that checkout is actually
    carrying the plan's work: it must be CLEAN, its HEAD must not sit at or behind the
    base ref, and when the plan record carries a branch (``references.branch``) its
    checked-out branch must be that branch. Otherwise the grade is refused as
    ``evidence_root_unresolved`` rather than passed on an empty diff (the base-branch
    case), on another plan's branch, or on unrelated uncommitted text (the dirty
    case). A plan that DECLARED a materialized worktree which does not resolve now
    returns ``None``: grading it against another tree would compare two heads.

    ``review_support._evidence_root`` resolves the citation-check root for the same
    two tree kinds; this one adds the fail-closed head, branch and dirty checks a diff
    grade needs.
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
    if root is None:
        return None, None
    refs = read_references(plan_id)
    base_ref = resolve_base_ref(None, refs if isinstance(refs, dict) else {}, root)
    # Compare COMMITS, not branch spellings: ``resolve_base_ref`` returns
    # ``origin/<base>`` when that remote-tracking ref resolves, while HEAD's local
    # name is ``<base>``. A detached HEAD is covered too.
    head_sha = _rev_parse(root, 'HEAD')
    base_sha = _rev_parse(root, base_ref)
    head_is_behind_or_at_base = (
        head_sha is not None and base_sha is not None and (head_sha == base_sha or _is_ancestor(root, 'HEAD', base_ref))
    )
    if head_is_behind_or_at_base:
        # HEAD at OR BEHIND the base ref makes the three-dot diff empty: grading it
        # would report success with zero rows, i.e. a pass, for work not checked
        # out. (A stale local main behind origin/main is the same false pass.)
        return None, 'main_checkout_on_base_branch'
    recorded_branch = str(refs.get('branch') or '').strip() if isinstance(refs, dict) else ''
    if recorded_branch and _current_branch(root) != recorded_branch:
        # The plan record names the branch its work lives on; a checkout of another
        # plan's branch would grade a different change and report this plan clean.
        return None, 'main_checkout_other_branch'
    if _tree_is_dirty(root):
        # A dirty checkout feeds unrelated uncommitted text into the after-image.
        return None, 'main_checkout_dirty'
    return root, 'main_checkout'


def _row(
    path: str,
    removed: int,
    removed_tests: list[dict[str, Any]],
    detail: str,
    acceptance_kind: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        'path': path,
        'kind': 'assertion_removed',
        'removed_assertions': removed,
        'removed_tests': removed_tests,
        'detail': detail,
    }
    if acceptance_kind is not None:
        # Which ROW KIND a path-level acceptance must name. A residual entry, a
        # file total and a set total are three different claims; one key must not
        # stand for another even when the counts coincide.
        row['acceptance_kind'] = acceptance_kind
    names = [entry['identity'] for entry in removed_tests]
    if names:
        row['weakened_functions'] = names
    return row


def compute_test_integrity(plan_id: str, base_ref: str | None = None, head_ref: str | None = None) -> dict[str, Any]:
    """Report every changed test whose assertions were removed or filtered.

    One finding per weakened test file:

    * ``assertion_removed`` — a loss in one of four cases: the changed test set's
      assertion total drops; a named test disappears from every after-file; one
      test's count drops while that test still exists (including the net count
      evasion and a deleted test whose assertions were added to another test in
      the same file); or a surviving path's own total drops and no identity
      accounts for the drop.
    * ``test_filtered`` — the branch adds a skip/xfail marker the pre-image did
      not carry.

    The survival comparison is decided per IDENTITY against a CONTENT match: the
    removed identity's body must reappear in an after-file. A bare name there proves
    nothing — a same-named test with different assertions cannot absorb a loss — while
    a function moved with its assertions is not a loss.

    A file the branch ADDS is not reported: removing an assertion means removing
    one that existed before the change. The comparator reads the whole changed
    test set, so a moved / renamed / split file is not a loss, and reads the
    pre-image at the merge base, so an assertion the base branch gained later is
    not reported. It does NOT catch a RELAXED assertion that keeps the count
    (`assert x == 5` rewritten to `assert x is not None`), which stays the
    author's reading of the change rather than this verb's count.
    """
    try:
        root, evidence_kind = _evidence_root(plan_id)
        if root is None:
            if plan_uses_worktree(plan_id):
                return _error(plan_id, 'worktree_unresolved', 'no worktree is materialized for the plan')
            return _error(
                plan_id,
                'evidence_root_unresolved',
                f'the main checkout cannot grade the branch diff: {evidence_kind or "no checkout"}',
            )
        return _grade_test_integrity(plan_id, root, evidence_kind, base_ref, head_ref)
    except (_GitFailure, UnicodeDecodeError) as exc:
        return _error(plan_id, 'test_integrity_not_run', str(exc))


def _grade_test_integrity(
    plan_id: str, root: Path, evidence_kind: str | None, base_ref: str | None, head_ref: str | None = None
) -> dict[str, Any]:
    """Grade the tree once the evidence root and its git calls are known to work.

    ``head_ref`` pins the read to a commit (the head a finding was validated at);
    without it the committed ``HEAD`` and the working tree are read.
    """
    head = head_ref or 'HEAD'
    refs = read_references(plan_id)
    resolved_base = resolve_base_ref(base_ref, refs if isinstance(refs, dict) else {}, root)
    # Resolve the merge base BEFORE the diff: on unrelated histories the three-dot
    # diff fails with "no merge base", which would otherwise be reported as
    # diff_unavailable and hide the named state this check promises.
    base_tree = merge_base(root, resolved_base, head)
    if base_tree is None:
        return _error(
            plan_id,
            'merge_base_unresolved',
            f'no merge base exists for {resolved_base} and {head}, so the pre-image cannot be read',
        )
    try:
        entries = changed_statuses(root, resolved_base, head)
    except (subprocess.SubprocessError, OSError) as exc:
        return _error(plan_id, 'diff_unavailable', f'{resolved_base}...{head} could not be read: {exc}')

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
                text = _after_image(root, path, head_ref)
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
                text = _after_image(root, path, head_ref)
                if text is not None:
                    after[path] = text
        elif is_test_path(path):
            pre = _show(root, base_tree, path)
            post = _after_image(root, path, head_ref)
            if pre is not None:
                before[path] = pre
            if post is not None:
                after[path] = post

    before_fns_by_path = {path: _function_assertion_counts(text) for path, text in before.items()}
    after_fns_by_path = {path: _function_assertion_counts(text) for path, text in after.items()}
    before_bodies_by_path = {path: _identity_bodies(text) for path, text in before.items()}
    after_bodies: dict[str, set[str]] = {}
    for text in after.values():
        for identity, body in _identity_bodies(text).items():
            after_bodies.setdefault(identity, set()).add(body)

    def _surviving_assertions(path: str, identity: str, count: int) -> int:
        """How many of ``identity``'s assertions a MOVE proves survived, in ``count``'s unit.

        A move is proven by content, never by a bare name: the after-file must carry
        the before body's assertion lines as EXCESS over what another before-file
        already carried for the same identity. A full superset is a full move (the
        test moved, possibly strengthened); a body wholly contained in the before is a
        weakened move and survives by that body's own count. Anything else — an
        unrelated test that merely shares the name, even one that shares a line —
        survives nothing.
        """
        before_lines = Counter(_assertion_lines(before_bodies_by_path[path].get(identity, '')))
        if not before_lines:
            return 0
        carried: Counter[str] = Counter()
        for other, bodies in before_bodies_by_path.items():
            if other == path:
                continue
            carried += Counter(_assertion_lines(bodies.get(identity, '')))
        best = 0
        for body in after_bodies.get(identity, set()):
            excess = Counter(_assertion_lines(body)) - carried
            if not excess:
                continue
            if not (before_lines - excess):
                return count
            if not (excess - before_lines):
                best = max(best, min(count, sum(_count(line) * n for line, n in excess.items())))
        return best

    findings: list[dict[str, Any]] = []
    moved_by_path: dict[str, int] = {}
    for path, pre in before.items():
        before_fns = before_fns_by_path[path]
        before_file = _count(pre)
        post = after.get(path)
        if post is None:
            # A deleted test identity is a MOVE only to the extent its assertion
            # lines reappear elsewhere; a bare name there proves nothing.
            missing: dict[str, int] = {}
            kinds: dict[str, str] = {}
            for identity, count in before_fns.items():
                surviving = _surviving_assertions(path, identity, count)
                moved_by_path[path] = moved_by_path.get(path, 0) + surviving
                lost = count - surviving
                if lost > 0:
                    missing[identity] = lost
                    # A count-less declaration decides a whole REMOVAL only; an
                    # identity whose content is only partly elsewhere is a DROP.
                    kinds[identity] = 'removed' if surviving == 0 else 'dropped'
            if missing:
                findings.append(
                    _row(
                        path,
                        sum(missing.values()),
                        [
                            {'identity': identity, 'assertions_removed': count, 'kind': kinds[identity]}
                            for identity, count in sorted(missing.items())
                        ],
                        f'{sum(missing.values())} assertion(s) of {", ".join(sorted(missing))} are gone from '
                        f'every file the branch carries',
                    )
                )
                continue
            # No identity at all could be extracted — neither a test function nor a
            # class header: fall back to the file's own count, unless the same body
            # simply moved. The row carries a path-level key, so a close can accept it.
            if not before_fns and before_file and not _content_survives(pre, after):
                findings.append(
                    _row(
                        path,
                        before_file,
                        [],
                        f'{before_file} assertion(s) present at {base_tree} are gone from the file',
                        acceptance_kind='file_total',
                    )
                )
            continue

        after_fns = after_fns_by_path[path]
        file_loss = before_file - _count(post)
        drops = {
            identity: count - after_fns[identity]
            for identity, count in before_fns.items()
            if identity in after_fns and after_fns[identity] < count
        }
        missing = {}
        missing_kinds: dict[str, str] = {}
        carried_away = 0
        for identity, count in before_fns.items():
            if identity in after_fns:
                continue
            # Same rule as the deleted-file arm: only assertion CONTENT that really
            # reappears counts, so a same-named test in another file absorbs nothing.
            surviving = _surviving_assertions(path, identity, count)
            carried_away += min(count, surviving)
            lost = count - surviving
            if lost > 0:
                missing[identity] = lost
                missing_kinds[identity] = 'removed' if surviving == 0 else 'dropped'
        identity_loss = sum(drops.values()) + sum(missing.values())
        moved_by_path[path] = moved_by_path.get(path, 0) + carried_away
        # A surviving path's own total is only reported when NO identity accounts
        # for the drop: a function moved to another file is not a loss.
        residual = file_loss - identity_loss - carried_away
        removed = identity_loss + max(0, residual)
        if removed:
            removed_tests = [
                {
                    'identity': identity,
                    'assertions_removed': count,
                    'kind': 'dropped' if identity in drops else missing_kinds[identity],
                }
                for identity, count in sorted({**drops, **missing}.items())
            ]
            detail = f'{removed} assertion(s) present at {base_tree} are gone from the file'
            names = sorted({**drops, **missing})
            if names:
                detail = f'{removed} assertion(s) present at {base_tree} are gone from {", ".join(names)}'
                if file_loss <= 0:
                    detail += ', while the file total is not reduced by the same amount'
            findings.append(
                _row(
                    path,
                    removed,
                    removed_tests,
                    detail,
                    acceptance_kind='mixed_residual' if removed_tests else 'file_total',
                )
            )

    # Case 1: the total across the whole changed test set dropped. This is the
    # last-net guard — a genuine loss the per-identity pass could not explain (a
    # language whose test headers are not parsed) is still reported, never dropped.
    # The row is attributed to the file whose loss no identity explains, not to the
    # file with the largest raw drop, and carries the path key so a close can accept it.
    before_total = sum(_count(text) for text in before.values())
    after_total = sum(_count(text) for text in after.values())
    explained = sum(finding['removed_assertions'] for finding in findings)
    if after_total < before_total and before_total - after_total > explained:
        # Attribute the leftover to the file whose own loss is NOT explained by an
        # identity row, never to the file with the largest raw drop: a larger drop
        # that identities already account for is not where the unexplained loss sits.
        reported_by_path: dict[str, int] = {}
        for finding in findings:
            reported_by_path[finding['path']] = reported_by_path.get(finding['path'], 0) + int(
                finding.get('removed_assertions') or 0
            )
        raw_losses = {path: _count(text) - _count(after.get(path, '')) for path, text in before.items()}
        unexplained = [
            (raw - moved_by_path.get(path, 0) - reported_by_path.get(path, 0), path)
            for path, raw in raw_losses.items()
            if raw > 0
        ]
        positive_unexplained = [entry for entry in unexplained if entry[0] > 0]
        if positive_unexplained:
            _loss, path = max(positive_unexplained)
        else:
            positive = [(raw - moved_by_path.get(path, 0), path) for path, raw in raw_losses.items() if raw > 0]
            if positive:
                _loss, path = max(positive)
            else:
                holders = sorted(before.items(), key=lambda item: -_count(item[1]))
                if not holders:
                    return _payload(plan_id, resolved_base, base_tree, evidence_kind, findings)
                path = holders[0][0]
        findings.append(
            _row(
                path,
                before_total - after_total - explained,
                [],
                f'the changed test set holds {before_total - after_total} assertion(s) fewer than at {base_tree}',
                acceptance_kind='set_total',
            )
        )

    for path, post in after.items():
        # A marker is only "added by the branch" against a pre-image, and the
        # comparison is per TEST IDENTITY, not per file: a marker that travelled
        # with one test must not mask a marker the branch added to another in the
        # same file or in a sibling half of a split. A RENAMED file's pre-image
        # lives under the old path; an ADDED file is paired with the deleted body it
        # came from; a genuinely new file has no pre-image and is skipped, so a new
        # skipped test is never read as a filter.
        pre_path = path if path in before else renamed_from.get(path)
        if pre_path is not None:
            pre = before.get(pre_path, '')
        else:
            pre = _moved_pre_image(post, before, after)
            if pre is None:
                continue
        units = _added_marker_units(post, pre)
        if units:
            added_markers = sorted({marker for markers in units.values() for marker in markers})
            marked_tests = sorted(identity for identity in units if identity)
            row: dict[str, Any] = {
                'path': path,
                'kind': 'test_filtered',
                'markers': added_markers,
                'detail': f'the branch adds {", ".join(added_markers)}: the test no longer runs',
            }
            if marked_tests:
                # WHAT the acceptance covers: the identity of each marked test, so a
                # later skip of a further test in the same file is a new row.
                row['marked_tests'] = marked_tests
            findings.append(row)

    return _payload(plan_id, resolved_base, base_tree, evidence_kind, findings)


def _payload(
    plan_id: str, resolved_base: str, base_tree: str, evidence_kind: str | None, findings: list[dict[str, Any]]
) -> dict[str, Any]:
    """The success payload, so every exit names the same fields."""
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


def _without_markers(text: str) -> str:
    """A body with its skip/xfail markers removed, so a move still compares equal."""
    stripped = text
    for marker in SKIP_MARKERS:
        stripped = stripped.replace(marker, '')
    return _normalized_body(stripped)


def _moved_pre_image(post: str, before: dict[str, str], after: dict[str, str]) -> str | None:
    """The deleted body an ADDED file logically came from, or ``None``.

    A split (one file deleted, two added) carries its tests into files that did not
    exist, so an added path has no same-path pre-image. Two pairings recover it, best
    first:

    * exact — the added body equals a DELETED body once markers are stripped (a
      move that stayed whole);
    * identity — the added file shares at least one test identity with a DELETED
      file, and the deleted file with the LARGEST overlap wins (so an unrelated
      deletion cannot win by document order).

    Pairing is by identity, deliberately: a same-named class moved to another
    package is the same test under the identity rule, and a marker it gained during
    the move is reported. A file that shares no identity with any deletion —
    including a genuinely new test whose identities appear nowhere in the pre-image
    — is left unpaired, and its markers are not read as filters.
    """
    wanted = _without_markers(post)
    for path, text in before.items():
        if path in after:
            continue
        if _without_markers(text) == wanted:
            return text
    added_identities = set(_function_assertion_counts(post))
    if not added_identities:
        return None
    best: tuple[int, str] | None = None
    for path, text in before.items():
        if path in after:
            continue
        shared = len(added_identities & set(_function_assertion_counts(text)))
        if shared and (best is None or shared > best[0]):
            best = (shared, text)
    return best[1] if best is not None else None


def _identity_markers(text: str) -> dict[str, set[str]]:
    """The skip markers attributed to each test identity.

    A marker on a header line (an indented ``it.skip(...)``) belongs to THAT test;
    any other marker is attributed to the next test header at or after it, because a
    decorator sits on the line ABOVE the ``def`` it filters and so falls outside the
    function's own span. That attribution is what lets a marker on one test be told
    from a marker on another in the same file. A file with no test identity yields a
    single ``''`` entry carrying the whole file's markers, which is the file-level
    comparison that applies to a language with no headers at all.
    """
    spans = _identity_spans(text) or _class_spans(text)
    if not spans:
        return {'': _markers(text)}
    markers: dict[str, set[str]] = {name: set() for _, name in spans}
    for marker in SKIP_MARKERS:
        cursor = 0
        while True:
            position = text.find(marker, cursor)
            if position < 0:
                break
            # A marker that sits on a test header line (an indented ``it.skip(``)
            # belongs to THAT test; the previous rule attributed it to the next
            # span, because the header's offset is the line start below the marker.
            line_start = text.rfind('\n', 0, position) + 1
            owner = next((name for offset, name in spans if offset == line_start), None)
            if owner is None:
                owner = next((name for offset, name in spans if offset >= position), spans[-1][1])
            markers[owner].add(marker)
            cursor = position + len(marker)
    return markers


def _added_marker_units(post: str, pre: str) -> dict[str, set[str]]:
    """The markers the branch ADDED, keyed by the test identity that gained them.

    An identity present only after the change is a new test: it has no pre-image to
    compare against, so its markers are not read as additions. When EITHER side
    carries no test identity at all — a language the header arms do not parse — the
    comparison falls back to the whole file, which is the only granularity available
    and the pre-existing behaviour. The returned map is what lets a filter acceptance
    name the identity of each marked test rather than only the marker kind.
    """
    after_markers = _identity_markers(post)
    before_markers = _identity_markers(pre)
    if set(after_markers) == {''} or set(before_markers) == {''}:
        added = _markers(post) - _markers(pre)
        return {'': added} if added else {}
    units: dict[str, set[str]] = {}
    for identity, markers in after_markers.items():
        if identity not in before_markers:
            continue
        added = markers - before_markers[identity]
        if added:
            units[identity] = added
    return units


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
