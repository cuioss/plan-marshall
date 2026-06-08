#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Whole-tree completeness gate surfacer for the phase-6-finalize dispatcher.

Backs the ``default:finalize-step-whole-tree-gate`` finalize step (see
``phase-6-finalize/standards/finalize-step-whole-tree-gate.md``). The gate is
the NOT-diff-scoped complement to the diff-scoped finalize gates: where the
simplify / self-review passes reason about the plan's own change surface, this
surfacer sweeps the ENTIRE ``marketplace/`` tree for survivors of deletions the
plan was meant to make, and compares the request's enumerated mandate against
the diff's touched files.

This script is the deterministic surfacing half of the step. It emits two
candidate lists; the LLM cognitive pass in the step body classifies each
``survivors[]`` row as a genuine omission vs a legitimate retained reference,
and each ``mandate_gaps[]`` row as a real gap vs a satisfied-by-another-path
item. The script makes no FAIL/PASS judgement itself — it only surfaces.

Two checks:

1. **Whole-tree survivor sweep** — for each identifier the plan DELETED
   (extracted from removed lines of the ``{base}...HEAD`` diff), grep the
   entire ``marketplace/`` tree (NOT the diff, NOT only touched skills) with
   word-boundary anchoring and report every surviving reference as a
   ``survivors[]{file,line,identifier}`` row. The sweep excludes
   ``.plan/archived-plans/**``, ``__pycache__`` byte-compiled output, and
   vendored snapshot directories.
2. **Intent-vs-diff scope check** — extract the request's enumerated mandate
   targets (named files / symbols / contracts in ``request.md``) and flag any
   that have zero representation in the diff's touched files as a
   ``mandate_gaps[]`` row.

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

The script is stdlib-only and registered through the marketplace executor; it
is invoked via ``python3 .plan/execute-script.py
plan-marshall:phase-6-finalize:whole_tree_gate scan --plan-id {plan_id}``. The
executor injects ``PYTHONPATH`` for ``toon_parser``, ``file_ops``, and
``input_validation`` so no in-script ``sys.path`` manipulation is required.

Subprocess seams (``_run_git_diff``, ``_run_git_diff_names``) and the
worktree-root / request-text resolvers are split out so the orchestration body
is testable without a live git worktree.
"""

from __future__ import annotations

import argparse
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


def extract_deleted_identifiers(diff_text: str) -> list[str]:
    """Extract the symbol-like identifiers removed by the diff.

    Scans removed lines (unified-diff lines beginning with a single ``-`` that
    are NOT the ``---`` file header) and collects code-symbol identifiers of
    meaningful length, dropping language keywords and ubiquitous stopwords. The
    result is sorted and de-duplicated so the sweep is deterministic.

    A removed line that also appears as an added line (a pure move/rename) still
    contributes its identifiers — the survivor sweep will simply find the moved
    reference and the cognitive pass classifies it as a legitimate retention.
    """
    identifiers: set[str] = set()
    for raw in diff_text.splitlines():
        if not raw.startswith('-'):
            continue
        if raw.startswith('---'):
            # Unified-diff old-file header, not a content removal.
            continue
        removed = raw[1:]
        for match in _IDENTIFIER_RE.finditer(removed):
            token = match.group(1)
            if len(token) < _MIN_IDENTIFIER_LEN:
                continue
            if token in _IDENTIFIER_STOPWORDS:
                continue
            identifiers.add(token)
    return sorted(identifiers)


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
    for path in sweep_root.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix not in _SWEEP_SUFFIXES:
            continue
        if any(part in _EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        yield path


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
    survivors: list[dict] = []
    for path in _iter_sweep_files(sweep_root):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        rel = _repo_relative(path, worktree_root)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for ident, pattern in patterns.items():
                if pattern.search(line):
                    survivors.append(
                        {'file': rel, 'line': line_no, 'identifier': ident}
                    )
    survivors.sort(key=lambda row: (row['file'], row['line'], row['identifier']))
    return survivors


def _repo_relative(path: Path, root: Path) -> str:
    """Render ``path`` relative to ``root`` with forward slashes."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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
) -> dict:
    """Surface whole-tree survivors and intent-vs-diff mandate gaps.

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

    return {
        'status': 'success',
        'plan_id': plan_id,
        'base_ref': resolved_base,
        'deleted_identifier_count': len(deleted_identifiers),
        'survivors': survivors,
        'survivor_count': len(survivors),
        'mandate_gaps': [{'mandate_item': item} for item in mandate_gaps],
        'mandate_gap_count': len(mandate_gaps),
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
    'extract_deleted_identifiers',
    'extract_mandate_items',
    'sweep_survivors',
]
