#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Whole-tree completeness gate surfacer for the phase-6-finalize dispatcher.

Backs the ``default:finalize-step-whole-tree-gate`` finalize step (see
``phase-6-finalize/standards/finalize-step-whole-tree-gate.md``). The gate is
the NOT-diff-scoped complement to the diff-scoped finalize gates: where the
simplify / self-review passes reason about the plan's own change surface, this
surfacer sweeps the ENTIRE ``marketplace/`` tree for survivors of deletions the
plan was meant to make, compares the request's enumerated mandate against the
diff's touched files, AND runs two whole-tree facet checks each gated on the
plan's changed set intersecting the corresponding trigger glob.

This script is the deterministic surfacing half of the step. It emits the
candidate lists; the LLM cognitive pass in the step body classifies each
``survivors[]`` row as a genuine omission vs a legitimate retained reference,
and each ``mandate_gaps[]`` row as a real gap vs a satisfied-by-another-path
item. The script makes no FAIL/PASS judgement itself — it only surfaces. The
facet checks (2–4 below) carry their own structured findings into the return
TOON for the same cognitive pass to classify; the surfacer never converts a
facet finding into a verdict.

Surfacing checks:

1. **Whole-tree survivor sweep** (always runs) — for each identifier the plan
   DELETED (extracted from removed lines of the ``{base}...HEAD`` diff), grep
   the entire ``marketplace/`` tree (NOT the diff, NOT only touched skills)
   with word-boundary anchoring and report every surviving reference as a
   ``survivors[]{file,line,identifier}`` row. The sweep excludes
   ``.plan/archived-plans/**``, ``__pycache__`` byte-compiled output, and
   vendored snapshot directories.
2. **Intent-vs-diff scope check** (always runs) — extract the request's
   enumerated mandate targets (named files / symbols / contracts in
   ``request.md``) and flag any that have zero representation in the diff's
   touched files as a ``mandate_gaps[]`` row.

Facet checks (each conditional on the plan's changed set hitting its trigger;
see ``manage-execution-manifest/standards/decision-rules.md`` § Pre-Filter:
``whole_tree_gate_inactive`` for the per-category trigger globs — this script
mirrors those two categories and does NOT redefine the activation predicate):

* **F1 — marketplace-wide static-analysis sweep** (doctor trigger) — when the
  changed set touches a plugin-doctor / plan-doctor analyzer or rule script,
  run the marketplace-wide ``plugin-doctor quality-gate`` over the full
  ``marketplace/`` tree (NOT the build-map-scoped subset) so a rule change that
  breaks an untouched component surfaces before the push.
* **F2 — whole-tree grep-sweep guard re-run** (sweep-test trigger) — when the
  changed set touches a whole-tree grep-sweep guard test, re-run the
  ``whole_tree_sweep``-marked guard tests with the full tree as scan root.

Return shape (CLI emits this as TOON; programmatic callers consume the dict
directly)::

    status: success | error
    plan_id: <plan id>
    base_ref: <resolved base ref>
    deleted_identifier_count: <int>
    survivors[N]{file,line,identifier}: ...   # whole-tree survivors
    mandate_gaps[M]{mandate_item}: ...        # request mandate items absent from the diff
    survivor_count: <int>
    mandate_gap_count: <int>
    facets:
      doctor:     {triggered, ran, passed, finding_count, summary}
      sweep_test: {triggered, ran, passed, summary}

The script is stdlib-only and registered through the marketplace executor; it
is invoked via ``python3 .plan/execute-script.py
plan-marshall:phase-6-finalize:whole_tree_gate scan --plan-id {plan_id}``. The
executor injects ``PYTHONPATH`` for ``toon_parser``, ``file_ops``, and
``input_validation`` so no in-script ``sys.path`` manipulation is required.

Subprocess seams (``_run_git_diff``, ``_run_git_diff_names``,
``_run_doctor_quality_gate``, ``_run_sweep_tests``) and the worktree-root /
request-text resolvers are split out so the orchestration body is testable
without a live git worktree, live doctor run, or live pytest run.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

from file_ops import get_plan_dir, get_base_dir  # type: ignore[import-not-found]
from input_validation import require_valid_plan_id  # type: ignore[import-not-found]
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The subtree the whole-tree survivor sweep greps. The gate is deliberately
#: marketplace-scoped — survivors of a deleted marketplace symbol that linger
#: in test fixtures or generated output are not the gate's concern.
_SWEEP_SUBDIR: str = 'marketplace'

#: Directory names excluded from the sweep. ``.plan`` is excluded so the
#: archived-plan corpus (``.plan/archived-plans/**``) and any plan-scoped state
#: never produce phantom survivors; ``__pycache__`` excludes byte-compiled
#: output; ``node_modules``/``target``/``dist`` exclude vendored or generated
#: snapshots.
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {'.plan', '__pycache__', 'node_modules', 'target', 'dist', '.git'}
)

#: File suffixes the sweep reads. Restricting to text-bearing source/doc
#: suffixes avoids grepping binary blobs and keeps the sweep deterministic.
_SWEEP_SUFFIXES: frozenset[str] = frozenset(
    {'.py', '.md', '.json', '.adoc', '.toon', '.txt', '.yml', '.yaml', '.sh'}
)

#: Identifiers shorter than this are too common to anchor a meaningful sweep
#: (every ``id``, ``os``, ``re`` would explode the survivor list with noise).
_MIN_IDENTIFIER_LEN: int = 4

#: Per-token tree-wide occurrence ceiling for the survivor sweep. A genuine
#: deleted symbol surviving somewhere in the tree resolves at a handful of call
#: sites; a candidate that matches more locations than this is overwhelmingly an
#: ordinary prose word (e.g. a dashed compound like ``plan-marshall`` that passes
#: ``_IDENTIFIER_RE`` yet recurs in narrative throughout the tree), not a removed
#: identifier. Such candidates are dropped from ``survivors[]`` entirely — the
#: surfacer's no-verdict contract is preserved: a dropped candidate simply does
#: not appear, it is never converted into a finding. The ceiling is deliberately
#: generous so a legitimate widely-referenced symbol is not silently discarded.
_MAX_TREE_OCCURRENCES: int = 50

#: Generic single-word tokens that are never meaningful deletion targets even
#: when they pass the length filter — language keywords and ubiquitous names.
_IDENTIFIER_STOPWORDS: frozenset[str] = frozenset(
    {
        'self', 'None', 'True', 'False', 'return', 'import', 'from', 'class',
        'else', 'elif', 'pass', 'with', 'args', 'data', 'name', 'path',
        'this', 'that', 'when', 'then', 'will', 'must', 'each', 'have',
        'into', 'such', 'only', 'both', 'used', 'uses', 'plan', 'file',
        'step', 'type', 'list', 'dict', 'text', 'line', 'code', 'test',
    }
)

#: Matches code-symbol identifiers in a removed diff line: snake_case,
#: camelCase, PascalCase, and dotted/dashed compound names of meaningful
#: length. Word-boundary anchored.
_IDENTIFIER_RE = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]{2,}(?:[.-][A-Za-z0-9_]+)*)\b')

#: Matches a repo-relative file path token inside request prose (a path with a
#: known source/doc suffix). Used by the mandate extractor.
_PATH_RE = re.compile(
    r'\b([A-Za-z0-9_./-]+\.(?:py|md|adoc|json|toon|yml|yaml|sh))\b'
)

# ---------------------------------------------------------------------------
# Whole-tree facet triggers
# ---------------------------------------------------------------------------
#
# Each facet check (F1 doctor / F2 sweep-test) fires only when the plan's
# changed set intersects the matching trigger-glob category. These two
# categories MIRROR ``_WHOLE_TREE_INVARIANT_TRIGGER_GLOBS`` in
# ``manage-execution-manifest.py`` (the single source of the activation
# predicate the composer uses to keep this step in the manifest). They are
# repeated here — not imported — because the executor runs this script with a
# PYTHONPATH that does not include the manifest skill's scripts dir, and the
# per-facet RUN decision is a finer split (one category per facet) than the
# composer's coarse "any-trigger-hit ⇒ keep the gate" predicate. The literal
# patterns are kept byte-identical to the manifest constant; decision-rules.md
# § Pre-Filter: ``whole_tree_gate_inactive`` is the single doc home for the
# per-category rationale, cross-referenced from the gate-body doc.

#: F1 doctor trigger — a changed plugin-doctor / plan-doctor analyzer or rule
#: re-classifies the whole marketplace, so the marketplace-wide doctor pass
#: must re-run over the full tree.
_DOCTOR_TRIGGER_GLOBS: tuple[str, ...] = (
    'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**/*.py',
    'marketplace/bundles/plan-marshall/skills/plan-doctor/**/*.py',
)

#: F2 sweep-test trigger — a changed whole-tree grep-sweep guard test must be
#: re-run with the full ``marketplace/`` scan root rather than module-scoped.
_SWEEP_TEST_TRIGGER_GLOBS: tuple[str, ...] = (
    'test/plan-marshall/**/test_*sweep*.py',
    'test/marketplace/**/test_*sweep*.py',
)

#: Executor notation of the marketplace-wide static-analysis quality gate the
#: F1 facet invokes as a subprocess.
_DOCTOR_NOTATION: str = 'pm-plugin-development:plugin-doctor:doctor-marketplace'

#: The pytest marker the F2 facet selects (``-m whole_tree_sweep``). Registered
#: in ``pyproject.toml`` ``[tool.pytest.ini_options] markers``.
_SWEEP_TEST_MARKER: str = 'whole_tree_sweep'

#: Per-facet wall-clock ceilings (seconds) for the subprocess seams. The doctor
#: pass and the marked sweep tests are both bounded, fast invariant checks; the
#: ceilings exist only to fail loud rather than hang the finalize gate.
_DOCTOR_TIMEOUT_S: int = 300
_SWEEP_TEST_TIMEOUT_S: int = 300


def _changed_set_hits(changed_paths: list[str], globs: tuple[str, ...]) -> bool:
    """Return True when any changed path matches any glob in ``globs``.

    Mirrors the manifest composer's glob-match style: each repo-relative
    changed path is tested against every glob via :func:`fnmatch.fnmatch`; the
    first match short-circuits. An empty ``changed_paths`` (a plan whose sources
    lie outside the trigger surface, or the pre-diff shape) yields False so the
    facet does not fire.
    """
    for path in changed_paths:
        for pattern in globs:
            if fnmatch.fnmatch(path, pattern):
                return True
    return False


# ---------------------------------------------------------------------------
# Subprocess seams (overridable in tests)
# ---------------------------------------------------------------------------


def _run_git_diff(worktree: Path, base_ref: str) -> str:
    """Return the unified ``{base_ref}...HEAD`` diff text.

    Raises:
        RuntimeError: ``git diff`` exited non-zero. The message carries the
            captured stderr so the dispatcher can surface the reason.
    """
    completed = subprocess.run(
        ['git', '-C', str(worktree), 'diff', f'{base_ref}...HEAD'],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git diff {base_ref}...HEAD failed in {str(worktree)!r}: "
            f"{completed.stderr.strip() or 'no stderr'}"
        )
    return completed.stdout


def _run_git_diff_names(worktree: Path, base_ref: str) -> list[str]:
    """Return the ``{base_ref}...HEAD`` changed-file path list.

    Raises:
        RuntimeError: ``git diff --name-only`` exited non-zero.
    """
    completed = subprocess.run(
        ['git', '-C', str(worktree), 'diff', '--name-only', f'{base_ref}...HEAD'],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git diff --name-only {base_ref}...HEAD failed in "
            f"{str(worktree)!r}: {completed.stderr.strip() or 'no stderr'}"
        )
    return [line for line in completed.stdout.splitlines() if line]


def _run_doctor_quality_gate(worktree: Path) -> dict:
    """Run the marketplace-wide ``plugin-doctor quality-gate`` (F1 facet).

    Invokes the doctor's ``quality-gate`` subcommand over the full
    ``marketplace/`` tree (no ``--paths`` filter, so the scope is whole-tree)
    via the executor, captures its exit code and stdout, and returns a small
    structured dict the facet driver folds into the return TOON. The doctor
    exits non-zero when it finds violations — that is a SURFACED finding, not an
    infrastructure error, so a non-zero exit does NOT raise.

    Returns a dict ``{passed: bool, finding_count: int, summary: str}``.
    ``finding_count`` counts ``finding`` / ``error`` markers in the doctor's
    stdout (best-effort; the cognitive pass reads the full ``summary``).

    Raises:
        RuntimeError: the doctor could not be invoked at all — the executor is
            missing, or the run exceeded :data:`_DOCTOR_TIMEOUT_S`. An un-run
            facet is indistinguishable from a passed one, so the caller must
            surface the reason rather than silently treat it as clean.
    """
    cmd = [
        sys.executable,
        '.plan/execute-script.py',
        _DOCTOR_NOTATION,
        'quality-gate',
        '--marketplace-root',
        'marketplace',
    ]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(worktree),
            capture_output=True,
            text=True,
            check=False,
            timeout=_DOCTOR_TIMEOUT_S,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f'plugin-doctor quality-gate could not be invoked in {str(worktree)!r}: {exc}'
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f'plugin-doctor quality-gate timed out after {_DOCTOR_TIMEOUT_S}s '
            f'in {str(worktree)!r}'
        ) from exc

    stdout = completed.stdout or ''
    passed = completed.returncode == 0
    finding_count = sum(
        stdout.count(token) for token in ('finding', 'error', 'ERROR')
    )
    if passed:
        summary = 'marketplace-wide static-analysis sweep passed: zero findings'
    else:
        summary = (
            'marketplace-wide static-analysis sweep reported findings '
            f'(exit {completed.returncode}); see stdout:\n{stdout.strip()}'
        )
    return {'passed': passed, 'finding_count': finding_count, 'summary': summary}


def _run_sweep_tests(worktree: Path) -> dict:
    """Re-run the ``whole_tree_sweep``-marked guard tests (F2 facet).

    Invokes pytest with ``-m whole_tree_sweep`` from the worktree root, so the
    marked guard tests run with the full ``marketplace/`` tree as scan root
    rather than the module-scoped subset phase-5 task verification uses. A pytest
    exit code of 5 (``no tests collected``) is treated as a PASS — a plan that
    touches a sweep-test file but whose tree carries no ``whole_tree_sweep``
    marker has nothing to re-run, and that is not a failure.

    Returns a dict ``{passed: bool, summary: str}``. A non-zero exit other than
    5 is a surfaced test failure, NOT an infrastructure error, so it does not
    raise.

    Raises:
        RuntimeError: pytest could not be invoked at all, or the run exceeded
            :data:`_SWEEP_TEST_TIMEOUT_S`.
    """
    cmd = [
        sys.executable,
        '-m',
        'pytest',
        '-m',
        _SWEEP_TEST_MARKER,
        '-q',
    ]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(worktree),
            capture_output=True,
            text=True,
            check=False,
            timeout=_SWEEP_TEST_TIMEOUT_S,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f'pytest -m {_SWEEP_TEST_MARKER} could not be invoked in {str(worktree)!r}: {exc}'
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f'pytest -m {_SWEEP_TEST_MARKER} timed out after '
            f'{_SWEEP_TEST_TIMEOUT_S}s in {str(worktree)!r}'
        ) from exc

    stdout = completed.stdout or ''
    # pytest exit code 5 == no tests collected (the marker matched nothing).
    passed = completed.returncode in (0, 5)
    if completed.returncode == 0:
        summary = f'whole-tree grep-sweep guard tests passed (-m {_SWEEP_TEST_MARKER})'
    elif completed.returncode == 5:
        summary = (
            f'no {_SWEEP_TEST_MARKER}-marked guard tests collected — nothing to re-run'
        )
    else:
        summary = (
            f'whole-tree grep-sweep guard tests failed (-m {_SWEEP_TEST_MARKER}, '
            f'exit {completed.returncode}); see stdout:\n{stdout.strip()}'
        )
    return {'passed': passed, 'summary': summary}


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def _resolve_worktree_root(explicit: str | None) -> Path:
    """Resolve the worktree root where ``marketplace/`` lives.

    Under the cwd-pinned model (ADR-002) the script runs with cwd pinned to the
    worktree, so the worktree root is the parent of ``.plan`` — i.e. two levels
    above ``get_base_dir()`` (``<root>/.plan/local``). An explicit override is
    honoured first so tests can point the sweep at an isolated fixture tree.

    Raises:
        RuntimeError: when no base dir resolves and no override was supplied.
    """
    if explicit is not None:
        val = explicit.strip()
        if val:
            return Path(val)
    # get_base_dir() -> <root>/.plan/local ; the worktree root is its grandparent.
    return get_base_dir().parent.parent


def _read_base_ref(plan_id: str) -> str:
    """Resolve the diff base ref from ``references.json``, falling back to main.

    Read-only. Returns ``references.base_branch`` when present and non-empty,
    otherwise the literal ``main``.
    """
    refs_path = get_plan_dir(plan_id) / 'references.json'
    try:
        import json

        refs = json.loads(refs_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'main'
    if isinstance(refs, dict):
        base = refs.get('base_branch')
        if isinstance(base, str) and base.strip():
            return base.strip()
    return 'main'


def _read_request_text(plan_id: str) -> str:
    """Return the plan's ``request.md`` text, or an empty string when absent."""
    request_path = get_plan_dir(plan_id) / 'request.md'
    try:
        return request_path.read_text(encoding='utf-8')
    except OSError:
        return ''


# ---------------------------------------------------------------------------
# Diff parsing
# ---------------------------------------------------------------------------


def _line_identifiers(line: str) -> set[str]:
    """Return the code-symbol identifiers on a single diff line.

    Applies the coarse first pass — ``_IDENTIFIER_RE`` shape, the
    ``_MIN_IDENTIFIER_LEN`` length floor, and the ``_IDENTIFIER_STOPWORDS`` set —
    so a token that survives this filter on a removed line is comparable against
    the same filter on an added/context line.
    """
    tokens: set[str] = set()
    for match in _IDENTIFIER_RE.finditer(line):
        token = match.group(1)
        if len(token) < _MIN_IDENTIFIER_LEN:
            continue
        if token in _IDENTIFIER_STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def extract_deleted_identifiers(diff_text: str) -> list[str]:
    """Extract the symbol-like identifiers genuinely removed by the diff.

    Scans removed lines (unified-diff lines beginning with a single ``-`` that
    are NOT the ``---`` file header) and collects code-symbol identifiers of
    meaningful length, dropping language keywords and ubiquitous stopwords (the
    coarse first pass: ``_IDENTIFIER_RE`` + ``_MIN_IDENTIFIER_LEN`` +
    ``_IDENTIFIER_STOPWORDS``). The result is sorted and de-duplicated so the
    sweep is deterministic.

    On top of the coarse pass, a token that also appears on an added (``+``) or
    context (unchanged) line of the same diff is dropped — it was not actually
    deleted, only moved or surrounded by retained text. This drop reverses the
    older keep-moved-tokens behaviour: keeping them flooded the survivor sweep
    with dashed-compound prose tokens (e.g. ``plan-marshall``) that pass
    ``_IDENTIFIER_RE`` yet recur unchanged throughout the tree. Subtracting the
    added/context token set is the cheap in-diff signal that a candidate is not
    a genuine removal.
    """
    removed_tokens: set[str] = set()
    retained_tokens: set[str] = set()
    for raw in diff_text.splitlines():
        if raw.startswith('---') or raw.startswith('+++'):
            # Unified-diff file headers, not content lines.
            continue
        if raw.startswith('@@') or raw.startswith('diff '):
            # Hunk header / diff-command line — carries no content tokens.
            continue
        if raw.startswith('-'):
            removed_tokens |= _line_identifiers(raw[1:])
        elif raw.startswith('+'):
            retained_tokens |= _line_identifiers(raw[1:])
        elif raw.startswith(' '):
            # Context (unchanged) line: the leading space is stripped; the
            # surrounding retained content is treated as a retained token source.
            retained_tokens |= _line_identifiers(raw[1:])
        else:
            # git metadata lines (index, old/new/deleted/new-file mode,
            # rename/copy from/to, similarity index, "Binary files", the
            # "\ No newline at end of file" marker, etc.) carry no content
            # tokens — skip so they never pollute retained_tokens.
            continue
    return sorted(removed_tokens - retained_tokens)


def extract_mandate_items(request_text: str, changed_files: list[str]) -> list[str]:
    """Extract request mandate items absent from the diff's touched files.

    A "mandate item" is a repo-relative file path the request prose names as a
    deletion / edit target (e.g. ``_plan_parsing.py``, an explicit
    ``marketplace/.../SKILL.md`` path). For each named path, the item is a gap
    when no changed file ends with that path token (suffix match tolerates the
    request naming a basename where the diff carries the full repo-relative
    path). De-duplicated and sorted.

    The check is intentionally conservative: it only flags paths the request
    explicitly names, never inferring intent, so the cognitive pass starts from
    a small high-signal candidate list rather than a noisy one.
    """
    named_paths: set[str] = set()
    for match in _PATH_RE.finditer(request_text):
        named_paths.add(match.group(1))

    gaps: list[str] = []
    for named in sorted(named_paths):
        if not _path_represented(named, changed_files):
            gaps.append(named)
    return gaps


def _path_represented(named: str, changed_files: list[str]) -> bool:
    """Return True when a changed file matches the named mandate path.

    Matches by suffix so a request that names a basename
    (``_plan_parsing.py``) is satisfied by a diff that carries the full
    repo-relative path (``marketplace/.../_plan_parsing.py``), and a request
    that names a full path is satisfied by an exact entry.
    """
    named_norm = named.strip('/')
    for changed in changed_files:
        if changed == named_norm:
            return True
        if changed.endswith('/' + named_norm):
            return True
        # Request named a full repo-relative path; diff carries the same.
        if named_norm.endswith('/' + changed):
            return True
    return False


# ---------------------------------------------------------------------------
# Whole-tree sweep
# ---------------------------------------------------------------------------


def _iter_sweep_files(sweep_root: Path):
    """Yield every text-bearing file under ``sweep_root`` not in an excluded dir."""
    if not sweep_root.is_dir():
        return
    try:
        for path in sweep_root.iterdir():
            if path.is_dir():
                if path.name not in _EXCLUDED_DIR_NAMES:
                    yield from _iter_sweep_files(path)
            elif path.is_file():
                if path.suffix in _SWEEP_SUFFIXES:
                    yield path
    except OSError:
        pass


def sweep_survivors(
    worktree_root: Path,
    deleted_identifiers: list[str],
) -> list[dict]:
    """Grep ``{worktree_root}/marketplace`` for surviving deleted identifiers.

    Returns one ``{file, line, identifier}`` row per surviving reference, with
    ``file`` rendered repo-relative to ``worktree_root`` and ``line`` the
    1-based line number. Word-boundary anchored per identifier so a deleted
    ``foo`` does not match ``foobar``. Rows are sorted by (file, line,
    identifier) for deterministic output.

    A per-token tree-occurrence ceiling (:data:`_MAX_TREE_OCCURRENCES`) drops any
    candidate whose tree-wide match count exceeds the ceiling: a "deleted
    identifier" matching dozens of locations is overwhelmingly an ordinary prose
    word, not a removed symbol. Dropped candidates simply do not appear in the
    returned rows — the surfacer's no-verdict contract is preserved.
    """
    if not deleted_identifiers:
        return []

    # One compiled word-boundary pattern per identifier, keyed by identifier so
    # the survivor row can name which deleted symbol it matched.
    patterns = {
        ident: re.compile(r'\b' + re.escape(ident) + r'\b')
        for ident in deleted_identifiers
    }

    sweep_root = worktree_root / _SWEEP_SUBDIR
    rows_by_ident: dict[str, list[dict]] = {ident: [] for ident in deleted_identifiers}
    for path in _iter_sweep_files(sweep_root):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        rel = _repo_relative(path, worktree_root)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for ident, pattern in patterns.items():
                if pattern.search(line):
                    rows_by_ident[ident].append(
                        {'file': rel, 'line': line_no, 'identifier': ident}
                    )

    # Per-token occurrence ceiling: a candidate matching more than the ceiling is
    # prose, not a removed symbol — drop all its rows.
    survivors: list[dict] = []
    for ident_rows in rows_by_ident.values():
        if len(ident_rows) > _MAX_TREE_OCCURRENCES:
            continue
        survivors.extend(ident_rows)
    survivors.sort(key=lambda row: (row['file'], row['line'], row['identifier']))
    return survivors


def _repo_relative(path: Path, root: Path) -> str:
    """Render ``path`` relative to ``root`` with forward slashes."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# Facet orchestration
# ---------------------------------------------------------------------------


def run_facets(
    worktree_root: Path,
    changed_files: list[str],
    *,
    doctor_runner=None,
    sweep_runner=None,
) -> dict:
    """Run the two whole-tree facet checks, each gated on its trigger.

    For each facet (F1 doctor / F2 sweep-test), the facet fires only when
    ``changed_files`` intersects the matching trigger-glob category. A facet
    that does not fire returns ``{triggered: False, ran: False, passed: True,
    ...}`` — an untriggered facet is vacuously clean and contributes no
    finding. A facet that fires runs its (overridable) seam and folds the
    structured result in.

    The surfacer makes NO verdict: ``passed: False`` on a facet is a SURFACED
    finding for the cognitive pass to classify, exactly like a ``survivors[]``
    row. An infrastructure failure inside a seam (raised ``RuntimeError``) is
    captured as ``ran: False, passed: False`` with an ``error`` key, so an
    un-run facet is never silently treated as clean.

    Args:
        worktree_root: Worktree root where ``marketplace/`` lives.
        changed_files: The plan's ``{base}...HEAD`` changed-file path list.
        doctor_runner: Optional seam in place of :func:`_run_doctor_quality_gate`.
        sweep_runner: Optional seam in place of :func:`_run_sweep_tests`.

    Returns:
        A dict ``{doctor: {...}, sweep_test: {...}}``.
    """
    doctor_fn = doctor_runner or _run_doctor_quality_gate
    sweep_fn = sweep_runner or _run_sweep_tests

    facets: dict[str, dict] = {}

    # F1 — marketplace-wide static-analysis sweep (doctor trigger).
    if _changed_set_hits(changed_files, _DOCTOR_TRIGGER_GLOBS):
        try:
            res = doctor_fn(worktree_root)
            facets['doctor'] = {
                'triggered': True,
                'ran': True,
                'passed': bool(res.get('passed')),
                'finding_count': int(res.get('finding_count', 0)),
                'summary': str(res.get('summary', '')),
            }
        except RuntimeError as exc:
            facets['doctor'] = {
                'triggered': True,
                'ran': False,
                'passed': False,
                'finding_count': 0,
                'summary': '',
                'error': str(exc),
            }
    else:
        facets['doctor'] = {
            'triggered': False,
            'ran': False,
            'passed': True,
            'finding_count': 0,
            'summary': 'doctor facet not triggered (changed set hit no doctor trigger glob)',
        }

    # F2 — whole-tree grep-sweep guard re-run (sweep-test trigger).
    if _changed_set_hits(changed_files, _SWEEP_TEST_TRIGGER_GLOBS):
        try:
            res = sweep_fn(worktree_root)
            facets['sweep_test'] = {
                'triggered': True,
                'ran': True,
                'passed': bool(res.get('passed')),
                'summary': str(res.get('summary', '')),
            }
        except RuntimeError as exc:
            facets['sweep_test'] = {
                'triggered': True,
                'ran': False,
                'passed': False,
                'summary': '',
                'error': str(exc),
            }
    else:
        facets['sweep_test'] = {
            'triggered': False,
            'ran': False,
            'passed': True,
            'summary': 'sweep-test facet not triggered (changed set hit no sweep-test trigger glob)',
        }

    return facets


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan(
    plan_id: str,
    *,
    worktree_path: str | None = None,
    base_ref: str | None = None,
    diff_runner=None,
    diff_names_runner=None,
    doctor_runner=None,
    sweep_runner=None,
) -> dict:
    """Surface whole-tree survivors, mandate gaps, and the two facet checks.

    Args:
        plan_id: Plan identifier — locates ``references.json`` / ``request.md``.
        worktree_path: Worktree root override (where ``marketplace/`` lives).
            When ``None``, resolved from the pinned cwd via ``get_base_dir``.
        base_ref: Diff base ref override. When ``None``, resolved from
            ``references.base_branch`` (falling back to ``main``).
        diff_runner: Optional test seam in place of :func:`_run_git_diff`.
            Signature ``(worktree: Path, base_ref: str) -> str``.
        diff_names_runner: Optional test seam in place of
            :func:`_run_git_diff_names`. Signature
            ``(worktree: Path, base_ref: str) -> list[str]``.
        doctor_runner: Optional facet seam in place of
            :func:`_run_doctor_quality_gate`.
        sweep_runner: Optional facet seam in place of :func:`_run_sweep_tests`.

    Returns:
        The dict matching the return contract in the module docstring.
    """
    diff_fn = diff_runner or _run_git_diff
    names_fn = diff_names_runner or _run_git_diff_names

    worktree_root = _resolve_worktree_root(worktree_path)
    resolved_base = base_ref.strip() if base_ref and base_ref.strip() else _read_base_ref(plan_id)

    diff_text = diff_fn(worktree_root, resolved_base)
    changed_files = names_fn(worktree_root, resolved_base)

    deleted_identifiers = extract_deleted_identifiers(diff_text)
    survivors = sweep_survivors(worktree_root, deleted_identifiers)

    request_text = _read_request_text(plan_id)
    mandate_gaps = extract_mandate_items(request_text, changed_files)

    facets = run_facets(
        worktree_root,
        changed_files,
        doctor_runner=doctor_runner,
        sweep_runner=sweep_runner,
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'base_ref': resolved_base,
        'deleted_identifier_count': len(deleted_identifiers),
        'survivors': survivors,
        'survivor_count': len(survivors),
        'mandate_gaps': [{'mandate_item': item} for item in mandate_gaps],
        'mandate_gap_count': len(mandate_gaps),
        'facets': facets,
    }


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_scan(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`scan` — emits TOON, returns exit 0 on success."""
    plan_id = require_valid_plan_id(args)
    try:
        result = scan(
            plan_id,
            worktree_path=getattr(args, 'worktree_path', None),
            base_ref=getattr(args, 'base_ref', None),
        )
    except RuntimeError as exc:
        print(serialize_toon({'status': 'error', 'plan_id': plan_id, 'error': str(exc)}))
        return 1
    print(serialize_toon(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``scan`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Whole-tree completeness gate surfacer. Greps the entire '
            'marketplace tree for surviving references to symbols the plan '
            'deleted and flags request-mandate items absent from the diff. '
            'Consumed by the phase-6-finalize whole-tree-gate step body.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    scan_parser = sub.add_parser(
        'scan',
        help='Surface whole-tree survivors and intent-vs-diff mandate gaps',
        allow_abbrev=False,
    )
    scan_parser.add_argument(
        '--plan-id',
        required=True,
        dest='plan_id',
        help='Plan identifier (locates references.json and request.md)',
    )
    scan_parser.add_argument(
        '--worktree-path',
        default=None,
        dest='worktree_path',
        help=(
            'Worktree root override (where marketplace/ lives). When omitted, '
            'resolved from the pinned cwd.'
        ),
    )
    scan_parser.add_argument(
        '--base-ref',
        default=None,
        dest='base_ref',
        help=(
            'Diff base ref override. When omitted, resolved from '
            'references.base_branch, falling back to main.'
        ),
    )
    scan_parser.set_defaults(func=cmd_scan)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'scan',
    'run_facets',
    'extract_deleted_identifiers',
    'extract_mandate_items',
    'sweep_survivors',
]
