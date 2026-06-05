#!/usr/bin/env python3
"""Detect direct ``gh``/``glab`` usage across the two generic retrospective surfaces.

The CI integration abstraction (``plan-marshall:tools-integration-ci:ci``)
is the sanctioned entry point for GitHub/GitLab operations. Direct CLI
invocation is a hard-rule violation. This aspect surfaces every leak so
the retrospective report carries concrete evidence.

Surfaces scanned (domain-invariant — run for every plan, regardless of domain):
- (A) ``logs/work.log`` and ``logs/script-execution.log`` — runtime leaks.
- (B) ``git diff {base}...HEAD`` added lines — code-level leaks introduced
      by the plan.

The former Surface C (CI-wrapper source scan for tangled gh/glab + local-git
mutations) is a meta-only check that scans plan-marshall's own CI-abstraction
sources. It moved to the ``plan-marshall-plugin-dev`` domain retrospective
aspect (``pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan``),
contributed via the ``provides_retrospective_aspects()`` extension point — see
``extension-api/standards/ext-point-retrospective.md``. Surface C runs only for
plans authored against the ``plan-marshall-plugin-dev`` domain; Surfaces A+B
here remain domain-invariant.

Exit code always 0 (findings are carried in the TOON output). This
matches the convention in ``analyze-logs.py`` and
``check-artifact-consistency.py``: the retrospective compiler consumes
fragments regardless of whether individual aspects found issues.

Usage:
    python3 direct-gh-glab-usage.py run --plan-id EXAMPLE-PLAN --mode live
    python3 direct-gh-glab-usage.py run --archived-plan-path /abs --mode archived
"""

from __future__ import annotations

import argparse
import re
import subprocess
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

# Log lines are matched with word-boundary-aware patterns so ``github.com``
# and similar substrings never trigger a false match. ``gh.`` (attribute
# access on a module named ``gh``) is the third distinct form we care about,
# matching the task's detection spec.
_LOG_RE = re.compile(r'(?:(?<![\w-])gh(?:\s|\.)|(?<![\w-])glab\s)')

# Source-file invocation pattern: matches ``gh`` or ``glab`` only when
# followed by a space, a quote, or a period — the shapes that represent
# actual CLI invocations or module access. ``github_*`` identifiers and
# docstrings like "see gh doc" are excluded by the flanking rules.
_SOURCE_INVOKE_RE = re.compile(r"""(?<![\w-])(gh|glab)(?=[\s'"\.])""")

# Diff scanner targets added lines in Python files. Removing / context lines
# are ignored because we only care about what the plan introduced.
_DIFF_ADD_RE = re.compile(r'^\+(?!\+)')


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory for ``mode``."""
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
    """True when ``line`` is whitespace-only or starts with a ``#`` comment.

    Used by the diff scanner to skip commentary. Log scanners do NOT
    apply this filter — log lines are never commented-out source.
    """
    stripped = line.strip()
    return not stripped or stripped.startswith('#')


def _scan_logs_for_leaks(plan_dir: Path) -> list[dict[str, Any]]:
    """Surface A: scan plan log files for gh/glab invocations.

    Returns one finding per matched line. Missing log files are silently
    skipped — the log-analysis aspect already surfaces missing log files,
    so duplicating that warning here would double-report.
    """
    findings: list[dict[str, Any]] = []
    logs_dir = plan_dir / 'logs'
    targets = ('work.log', 'script-execution.log')
    for target in targets:
        log_path = logs_dir / target
        if not log_path.exists():
            continue
        try:
            text = log_path.read_text(encoding='utf-8')
        except OSError:
            continue
        # Relative path used for the finding file field so archived-mode
        # fragments are portable between reviewer checkouts.
        rel_path = f'logs/{target}'
        for idx, line in enumerate(text.splitlines(), start=1):
            if not _LOG_RE.search(line):
                continue
            findings.append(
                {
                    'surface': 'log_leak',
                    'file': rel_path,
                    'line': idx,
                    'snippet': trim_snippet(line),
                    'category': 'log_leak',
                    'severity': 'error',
                }
            )
    return findings


def _git_diff_added_lines(base: str, project_root: Path) -> list[tuple[str, int, str]]:
    """Return ``(file, line_number, line_text)`` tuples for diff-added lines.

    ``line_number`` is the new-file 1-based line index. Binary files and
    files whose extension is not ``.py`` are skipped; diff headers are
    parsed for ``+++ b/<path>`` and hunk ``@@ -x,y +line,z @@`` markers.
    Failure to run ``git`` (missing binary, non-repo cwd) returns an empty
    list without raising — the aspect then reports zero diff findings.
    """
    try:
        proc = subprocess.run(
            ['git', '-C', str(project_root), 'diff', '--unified=0', f'{base}...HEAD'],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []

    out: list[tuple[str, int, str]] = []
    current_file: str | None = None
    next_line_no: int | None = None
    hunk_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')
    for raw in proc.stdout.splitlines():
        if raw.startswith('+++ b/'):
            current_file = raw[6:]
            next_line_no = None
            continue
        if raw.startswith('--- '):
            continue
        if raw.startswith('@@'):
            m = hunk_re.match(raw)
            if m and current_file is not None:
                next_line_no = int(m.group(1))
            continue
        if not current_file or next_line_no is None:
            continue
        if raw.startswith('+') and not raw.startswith('+++'):
            out.append((current_file, next_line_no, raw[1:]))
            next_line_no += 1
    return out


def _scan_diff_for_leaks(base: str, project_root: Path) -> list[dict[str, Any]]:
    """Surface B: scan ``git diff {base}...HEAD`` for added gh/glab calls."""
    findings: list[dict[str, Any]] = []
    for file_path, line_no, line_text in _git_diff_added_lines(base, project_root):
        # Scope to Python files — docstrings/markdown are not source code
        # for this aspect's purposes (see references/direct-gh-glab-usage.md).
        if not file_path.endswith('.py'):
            continue
        if is_comment_or_blank(line_text):
            continue
        if not _SOURCE_INVOKE_RE.search(line_text):
            continue
        findings.append(
            {
                'surface': 'diff_leak',
                'file': file_path,
                'line': line_no,
                'snippet': trim_snippet(f'+{line_text}'),
                'category': 'diff_leak',
                'severity': 'error',
            }
        )
    return findings


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
    base = args.base or 'main'

    findings: list[dict[str, Any]] = []
    findings.extend(_scan_logs_for_leaks(plan_dir))
    findings.extend(_scan_diff_for_leaks(base, project_root))

    counts_by_surface = {
        'log_leak': sum(1 for f in findings if f['surface'] == 'log_leak'),
        'diff_leak': sum(1 for f in findings if f['surface'] == 'diff_leak'),
    }

    return {
        'status': 'success',
        'aspect': 'direct-gh-glab-usage',
        'plan_id': args.plan_id or Path(args.archived_plan_path or '').name,
        'counts': {
            'total': len(findings),
            'by_surface': counts_by_surface,
        },
        'findings': findings,
    }


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Detect direct gh/glab CLI usage across plan logs and diff',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help='Scan plan logs and diff for direct gh/glab usage',
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
        '--base',
        default='main',
        help='Base ref for git diff scan (default: main)',
    )
    run_parser.add_argument(
        '--project-root',
        help='Repository root for the diff scan. Defaults to the current working directory.',
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
