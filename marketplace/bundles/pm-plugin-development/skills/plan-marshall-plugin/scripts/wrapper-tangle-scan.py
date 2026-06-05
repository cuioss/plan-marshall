#!/usr/bin/env python3
"""Retrospective aspect: scan plan-marshall CI-wrapper sources for tangle leaks.

This is the ``plan-marshall-plugin-dev`` domain retrospective aspect contributed
via the ``provides_retrospective_aspects()`` extension point
(see ``extension-api/standards/ext-point-retrospective.md``). It is the former
**Surface C** of the generic ``plan-marshall:plan-retrospective:direct-gh-glab-usage``
aspect — moved here because scanning plan-marshall's own CI-abstraction sources
is only meaningful for plans authored against the ``plan-marshall-plugin-dev``
domain. Surfaces A (plan logs) and B (plan diff) remain in the generic,
domain-invariant aspect.

What it detects:
    CI wrapper source files (``tools-integration-ci`` and
    ``workflow-integration-{github,gitlab}``) — subprocess / ``run_gh`` /
    ``run_glab`` args that tangle the ``gh``/``glab`` CLI with a local-git
    mutation (``checkout``, ``branch -d``, ``branch -D``, ``--delete-branch``,
    ``--remove-source-branch``).

Exit code always 0 (findings are carried in the TOON output). This matches the
convention in the generic retrospective aspects: the retrospective compiler
consumes fragments regardless of whether individual aspects found issues.

Usage:
    python3 wrapper-tangle-scan.py run --plan-id EXAMPLE-PLAN --mode live
    python3 wrapper-tangle-scan.py run --archived-plan-path /abs --mode archived
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from file_ops import base_path, output_toon, safe_main  # type: ignore[import-not-found]
from input_validation import (  # type: ignore[import-not-found]
    add_plan_id_arg,
    parse_args_with_toon_errors,
)

# Maximum length of ``snippet`` field per finding. Keeps the TOON fragment
# readable; full lines are available via file+line in the source.
_SNIPPET_MAX = 200

# Source-file invocation pattern: matches ``gh`` or ``glab`` only when
# followed by a space, a quote, or a period — the shapes that represent
# actual CLI invocations or module access. ``github_*`` identifiers and
# docstrings like "see gh doc" are excluded by the flanking rules.
_SOURCE_INVOKE_RE = re.compile(r"""(?<![\w-])(gh|glab)(?=[\s'"\.])""")

# Local-git mutation tokens for the wrapper-tangle heuristic. A subprocess
# args list that contains BOTH a CLI name (gh/glab) AND one of these tokens
# in the same call is flagged as a wrapper tangle.
#
# Self-contained tokens are matched as anchored patterns so prefix collisions
# (e.g. ``branch_delete`` for ``checkout``-like names, ``--delete-branch-me``
# for the long flags) cannot trigger a false positive.
_MUTATION_TOKEN_PATTERNS = (
    re.compile(r'\bcheckout\b'),
    re.compile(r'(?<![\w-])--delete-branch(?![\w-])'),
    re.compile(r'(?<![\w-])--remove-source-branch(?![\w-])'),
)

# Tokeniser for the ``branch -d`` / ``branch -D`` pair: split on whitespace,
# brackets, parens, commas, and quotes so both shell-style strings
# (``'git branch -d foo'``) and Python list-style args
# (``['git', 'branch', '-d', 'foo']``) decompose to the same token stream.
_TOKEN_SPLIT_RE = re.compile(r"[\s()\[\],'\"]+")

# Wrapper-tangle scan scope. Paths are relative to the repository root and
# are resolved against the current working directory at scan time (tests
# override ``cwd`` via the ``--project-root`` override flag).
_WRAPPER_DIRS = (
    'marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts',
    'marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts',
    'marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts',
)


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory for ``mode``.

    The wrapper-tangle scan is a static source scan that does not read the plan
    directory, but the resolution is retained for parity with the generic
    aspects and to validate the mode/flag combination fail-loud.
    """
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def trim_snippet(line: str) -> str:
    """Trim ``line`` to the per-finding snippet contract.

    The TOON consumer expects a single-line snippet no longer than
    ``_SNIPPET_MAX`` chars. Trailing whitespace (including the trailing
    newline from splitlines-preserving readers) is stripped.
    """
    stripped = line.rstrip('\n').rstrip('\r').rstrip()
    if len(stripped) <= _SNIPPET_MAX:
        return stripped
    return stripped[: _SNIPPET_MAX - 3] + '...'


def is_comment_or_blank(line: str) -> bool:
    """True when ``line`` is whitespace-only or starts with a ``#`` comment."""
    stripped = line.strip()
    return not stripped or stripped.startswith('#')


def _iter_python_files(roots: tuple[str, ...], project_root: Path) -> list[Path]:
    """Enumerate ``*.py`` files under ``roots`` (relative to ``project_root``)."""
    files: list[Path] = []
    for rel in roots:
        scan_dir = project_root / rel
        if not scan_dir.exists():
            continue
        files.extend(sorted(p for p in scan_dir.rglob('*.py') if p.is_file()))
    return files


def _line_is_in_docstring(lines: list[str], index: int) -> bool:
    """Return True when ``lines[index]`` is inside a triple-quoted string.

    Simple state machine: walks the file from the top, toggling the
    in-docstring flag whenever an unescaped triple-quote token opens or
    closes a block. A single-line triple-quoted string (open and close on
    the same line) leaves the flag unchanged because both tokens are on
    the same line and the odd-count check below resolves to ``False``.

    Good enough for the commentary-filter contract: false negatives here
    would only suppress findings we actually wanted, and false positives
    would only hide documentation examples — both benign given how rarely
    the wrapper sources use triple-quoted strings around live CLI calls.
    """
    in_block = False
    token: str | None = None
    double = '"' * 3
    single = "'" * 3
    for i, raw in enumerate(lines):
        if i == index:
            return in_block
        # Count unescaped triple-quote occurrences on the line.
        # Order matters: prefer the active token when one is open.
        for candidate in (double, single):
            if token == candidate:
                # Closing token must match the opener. An odd count on
                # the line toggles the flag.
                if candidate in raw and raw.count(candidate) % 2 == 1:
                    in_block = False
                    token = None
                continue
            if token is None and candidate in raw:
                if raw.count(candidate) % 2 == 1:
                    in_block = True
                    token = candidate
    return in_block


def _line_tangles_git(line: str) -> bool:
    """True when ``line`` carries a local-git mutation token.

    Self-contained tokens (``checkout``, ``--delete-branch``,
    ``--remove-source-branch``) are matched with anchored regexes that
    refuse adjacent word characters or hyphens, so prefix collisions like
    ``branch_delete`` or ``--delete-branch-me`` cannot trigger a false
    positive.

    The ``branch -d`` / ``branch -D`` pair is recognised by tokenising on
    whitespace, brackets, parens, commas and quotes, then looking for a
    ``branch`` token immediately followed by ``-d`` or ``-D``. This shape
    captures both shell-style strings (``'git branch -d foo'``) and
    Python list-style args (``['git', 'branch', '-d', 'foo']``) without
    flagging unrelated identifiers like ``branch_delete``.
    """
    if any(pattern.search(line) for pattern in _MUTATION_TOKEN_PATTERNS):
        return True
    tokens = [tok for tok in _TOKEN_SPLIT_RE.split(line) if tok]
    for idx, tok in enumerate(tokens):
        if tok == 'branch' and idx + 1 < len(tokens) and tokens[idx + 1] in ('-d', '-D'):
            return True
    return False


def _scan_wrappers_for_tangle(project_root: Path) -> list[dict[str, Any]]:
    """Scan CI wrapper sources for tangled gh/glab + git calls.

    Heuristic: a wrapper-level CLI invocation is flagged when its argument
    list contains both the CLI name (``gh``/``glab``) and any of the
    mutation tokens. Call sites are anchored on either ``subprocess.``
    (raw subprocess use) or the project's ``run_gh(`` / ``run_glab(``
    wrappers, which are the standard entry points inside the CI
    abstraction — missing them would let an abstraction leak slip
    through entirely. In practice the args list can span several lines, so
    the scan looks at a rolling window of up to 8 lines starting at each
    call site — enough to cover realistic multi-line args literals without
    pulling in unrelated code.
    """
    findings: list[dict[str, Any]] = []
    subprocess_call_re = re.compile(r'\bsubprocess\.')
    wrapper_call_re = re.compile(r'\b(run_gh|run_glab)\(')
    for py_path in _iter_python_files(_WRAPPER_DIRS, project_root):
        try:
            text = py_path.read_text(encoding='utf-8')
        except OSError:
            continue
        lines = text.splitlines()
        rel = str(py_path.relative_to(project_root))
        for idx, line in enumerate(lines):
            if is_comment_or_blank(line):
                continue
            if _line_is_in_docstring(lines, idx):
                continue
            is_subprocess_site = bool(subprocess_call_re.search(line))
            is_wrapper_site = bool(wrapper_call_re.search(line))
            if not (is_subprocess_site or is_wrapper_site):
                continue
            # Collect a small window for multi-line calls. 8 lines is
            # empirically enough for wrapper call sites in the bundle.
            window_end = min(idx + 8, len(lines))
            window = lines[idx:window_end]
            window_text = '\n'.join(window)
            # ``run_gh(`` / ``run_glab(`` calls have the CLI name implicit
            # in the wrapper itself — there is no need for an additional
            # ``gh``/``glab`` literal in the args window. ``subprocess.``
            # call sites still require the literal CLI name to ensure we
            # only flag genuine CLI invocations.
            has_cli = is_wrapper_site or bool(_SOURCE_INVOKE_RE.search(window_text))
            if not has_cli:
                continue
            if not any(_line_tangles_git(w) for w in window):
                continue
            findings.append(
                {
                    'surface': 'wrapper_tangle',
                    'file': rel,
                    'line': idx + 1,
                    'snippet': trim_snippet(line),
                    'category': 'wrapper_tangle',
                    'severity': 'error',
                }
            )
    return findings


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    # Resolve the plan dir to validate the mode/flag combination fail-loud,
    # even though the static source scan itself does not read it.
    resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()

    findings = _scan_wrappers_for_tangle(project_root)

    return {
        'status': 'success',
        'aspect': 'wrapper-tangle',
        'domain': 'plan-marshall-plugin-dev',
        'plan_id': args.plan_id or Path(args.archived_plan_path or '').name,
        'counts': {
            'total': len(findings),
            'by_surface': {'wrapper_tangle': len(findings)},
        },
        'findings': findings,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Scan plan-marshall CI-wrapper sources for tangled gh/glab + local-git mutations',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help='Scan CI-wrapper sources for wrapper tangles',
        allow_abbrev=False,
    )
    add_plan_id_arg(run_parser, required=False)
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.add_argument(
        '--project-root',
        help='Repository root for the wrapper scan. Defaults to the current working directory.',
    )
    # Accepted for parity with other scripts that forward --audit-plan-id;
    # audit logging is handled by the executor, so the flag is a passthrough here.
    run_parser.add_argument(
        '--audit-plan-id',
        help='Plan identifier for executor-level audit logging (passthrough)',
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()  # type: ignore[no-untyped-call]
