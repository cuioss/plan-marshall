#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Runtime tracked-source guard for the finalize ``post_run_review`` band.

A ``post_run_review`` step runs AFTER the merge gate, so a tracked-source write
one of its branches makes lands as an uncommitted diff with no remaining push
path. The ordering guard in
``test/plan-marshall/phase-6-finalize/test_post_run_review_ordering.py`` proves
only that such a step DECLARES ``mutates_source: false``; it observes no
worktree state, so a branch that violates its own declaration is undetectable
from the declaration alone. This seam is the runtime observation that closes
that gap — item 5f of ``phase-6-finalize/SKILL.md`` calls it once per post-run
band step return.

Three design decisions this seam settles, each stated once here so no caller
re-derives them:

1. **Scope — the post-run band only.** The guard is consulted only for a step
   declaring ``post_run_review: true``. Before the merge gate an uncommitted
   tracked edit is still pushable, so the defect this detects is reachable only
   after the gate. Broadening the check to every step would fire on the normal
   pre-gate working state.
2. **Path predicate — dirty AND tracked AND outside ``.plan/``.** Every finalize
   step legitimately writes under ``.plan/`` (status, logs, findings, metrics),
   so a bare non-empty ``git status --porcelain`` test would fire on every
   post-run step. The predicate is therefore two filters composed:
   ``--untracked-files=no`` (git itself drops untracked paths, so a new,
   unstaged file is not an offender) plus an explicit ``.plan/`` prefix
   exclusion. What survives both is a dirty TRACKED source path.
3. **Failure action — loud, legible, NON-blocking.** ``phase-6-finalize``
   documents the post-run band as advisory and never blocking, so a hard failure
   would contradict it. This script therefore NEVER fails: ``clean: false`` is a
   reported verdict, not an error, and the exit code is ``0`` on every path. The
   caller's obligation is a WARNING work-log line naming the offending paths and
   the writing step, plus a recorded finding — see item 5f.

Return shape (CLI emits TOON; programmatic callers consume
:func:`check_tracked_source` directly)::

    status: success
    step_id: <the step whose return triggered the check>
    clean: true|false
    offending_paths[N]: [<dirty tracked paths outside .plan/>]

``clean: true`` with an empty ``offending_paths[]`` is the expected outcome. A
git failure (the directory is not a repository, git is unavailable) returns
``status: error`` with ``clean: true`` and an ``error`` field — the guard is
advisory, so an unusable observation must not manufacture an offender, and the
zero exit keeps the caller's non-blocking contract intact.

The script is registered through ``generate_executor.py`` and consumed via the
executor proxy::

    python3 .plan/execute-script.py \
      plan-marshall:phase-6-finalize:post_run_source_guard check \
      --step-id "<finalize step id>" \
      --project-dir "<worktree or main-checkout root>"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from toon_parser import serialize_toon

#: Path prefixes whose dirty entries are NEVER offenders. Every finalize step
#: writes plan state under ``.plan/``; those writes are the normal mode of
#: operation, not an unpushable source edit.
_EXCLUDED_PREFIXES: tuple[str, ...] = ('.plan/',)

#: Porcelain status letters that introduce a second (original) path field in
#: ``-z`` output: rename and copy. Both sides are reported, because either one
#: being a tracked source path means the step moved tracked source.
_TWO_PATH_STATUSES: frozenset[str] = frozenset({'R', 'C'})

#: Seconds allowed for the single ``git status`` observation.
_GIT_TIMEOUT_SECONDS: int = 60


def _is_excluded(path: str) -> bool:
    """Whether a repo-relative path falls under an excluded prefix."""
    return any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


def parse_porcelain_z(payload: str) -> list[str]:
    """Extract the dirty paths from ``git status --porcelain -z`` output.

    The ``-z`` form is used rather than the default line form because it emits
    paths verbatim (no shell-style quoting or escaping), so a path containing a
    space, a quote, or a non-ASCII byte parses identically to a plain one.

    Args:
        payload: Raw stdout of ``git status --porcelain -z …``. Each record is
            ``XY<space><path>\\0``; a rename/copy record is followed by one
            additional ``<original-path>\\0`` field.

    Returns:
        Every path named by the payload, in payload order, with both sides of a
        rename/copy record included. Deduplication and prefix filtering are the
        caller's concern — this function only decodes.
    """
    fields = [field for field in payload.split('\0') if field]
    paths: list[str] = []
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if len(record) < 4:
            # Not a well-formed ``XY<space><path>`` record — skip it rather
            # than guessing at a path that would become a phantom offender.
            continue
        status, path = record[:2], record[3:]
        paths.append(path)
        if _TWO_PATH_STATUSES & set(status):
            if index < len(fields):
                paths.append(fields[index])
                index += 1
    return paths


def filter_tracked_source(paths: list[str]) -> list[str]:
    """Reduce decoded porcelain paths to the offending tracked-source set.

    Args:
        paths: Repo-relative paths decoded from a tracked-only porcelain run.

    Returns:
        The sorted, de-duplicated subset that lies outside every excluded
        prefix. Empty means the step left no unpushable tracked edit.
    """
    return sorted({path for path in paths if path and not _is_excluded(path)})


def check_tracked_source(project_dir: Path) -> tuple[bool, list[str], str | None]:
    """Observe real worktree state and report dirty tracked source paths.

    Runs the single tracked-only ``git status`` observation against
    ``project_dir`` and applies the two-filter path predicate documented in the
    module docstring.

    Args:
        project_dir: Worktree root (or main checkout) to observe.

    Returns:
        A ``(clean, offending_paths, error)`` triple. ``clean`` is ``True`` when
        no dirty tracked path outside ``.plan/`` was observed. ``error`` is
        ``None`` on a successful observation and carries the git failure detail
        otherwise, in which case ``clean`` is ``True`` and ``offending_paths``
        is empty — an unusable observation never manufactures an offender.
    """
    try:
        completed = subprocess.run(
            [
                'git',
                '-C',
                str(project_dir),
                'status',
                '--porcelain',
                '-z',
                '--untracked-files=no',
            ],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return True, [], f'git status failed: {exc}'

    if completed.returncode != 0:
        detail = completed.stderr.strip() or f'git exited {completed.returncode}'
        return True, [], f'git status failed: {detail}'

    offenders = filter_tracked_source(parse_porcelain_z(completed.stdout))
    return not offenders, offenders, None


def cmd_check(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`check_tracked_source` — emits TOON, returns 0."""
    project_dir = Path(args.project_dir).expanduser()
    clean, offenders, error = check_tracked_source(project_dir)

    payload: dict[str, object] = {
        'status': 'error' if error else 'success',
        'step_id': args.step_id,
        'project_dir': str(project_dir),
        'clean': clean,
        'offending_paths': offenders,
    }
    if error:
        payload['error'] = error
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``check`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Report dirty TRACKED source paths outside .plan/ left behind by a '
            'post_run_review finalize step. Advisory and non-blocking — the '
            'verdict rides the TOON payload and the exit code is always 0.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    check_parser = sub.add_parser(
        'check',
        help='Observe the worktree for dirty tracked source outside .plan/',
        allow_abbrev=False,
    )
    check_parser.add_argument(
        '--step-id',
        required=True,
        dest='step_id',
        help='Finalize step id whose return triggered the check (echoed back).',
    )
    check_parser.add_argument(
        '--project-dir',
        default='.',
        dest='project_dir',
        help=(
            'Worktree root (or main checkout) to observe. Defaults to the '
            'current working directory, which phase-5+ pins to the active '
            'worktree.'
        ),
    )
    check_parser.set_defaults(func=cmd_check)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = ['check_tracked_source', 'filter_tracked_source', 'parse_porcelain_z']
