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

**The tree passed to ``--project-dir`` is the MAIN CHECKOUT, not the plan's
worktree.** Every ``post_run_review: true`` step is ordered after
``default:branch-cleanup`` (70), which merges and then REMOVES the worktree, so
by the time this guard runs the worktree path no longer exists on disk. A
``git -C`` against it fails outright and returns ``status: error`` with
``clean: true`` — and because the caller records nothing on the error branch,
aiming this guard at the worktree would make its whole ``clean: false`` arm
unreachable: a guard that can never fire. The main checkout is also the right
tree on the merits, since that is where a post-run step's stray tracked write
actually lands, on the merged base branch.

Three design decisions this seam settles. They are stated here for the
implementer and restated for the caller in ``phase-6-finalize/SKILL.md`` item 5f
sub-item (0), which marks them "do NOT re-derive them" — the point is that no
caller derives them afresh, not that only one document carries them:

1. **Scope — the post-run band only.** The guard is consulted only for a step
   declaring ``post_run_review: true``. Before the merge gate an uncommitted
   tracked edit is still pushable, so the defect this detects is reachable only
   after the gate. Broadening the check to every step would fire on the normal
   pre-gate working state.
2. **Path predicate — dirty AND tracked; ``.plan/`` exempt ONLY when untracked.**
   Every finalize step legitimately writes plan STATE under ``.plan/`` (status,
   logs, findings, metrics), and those writes are *untracked* — but a number of
   files under ``.plan/`` ARE git-tracked (``marshal.json``, every
   ``project-architecture/**/enriched.json`` descriptor). ``--untracked-files=no``
   drops the untracked plan state (git itself excludes it), and the shared
   ``.plan/`` exemption
   (:func:`_plan_state_exemption.partition_plan_state_exemption`) is keyed on
   git TRACKEDNESS rather than on the path prefix: a *tracked* ``.plan/`` file
   left dirty after the merge gate is an unpushable tracked edit and is reported
   like any other tracked source. Exempting the whole ``.plan/`` prefix — the
   earlier behaviour — hid exactly those tracked writes (an architecture-enrich
   write is the recurring case), which is the defect this guard now closes. The
   SAME shared predicate backs the layer-D main-checkout drift capture in
   ``plan-marshall/scripts/_invariants.py`` so the two guards cannot diverge.
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
    project_dir: <the tree that was actually observed>
    clean: true|false
    considered_paths[N]: [<every dirty tracked path observed, pre-exemption>]
    exempted_paths[N]: [<untracked .plan/ paths dropped as plan state>]
    offending_paths[N]: [<dirty tracked source, tracked .plan/ files included>]

``considered_paths`` is the population the verdict was drawn from, so a
``clean: true`` that names the paths it examined is distinguishable from a
looked-at-nothing pass. ``exempted_paths`` names what was dropped and (by the
predicate) why: an untracked ``.plan/`` plan-state write. ``project_dir`` is
echoed because WHICH tree was observed is the one fact that distinguishes a real
``clean: true`` from the vacuous one a worktree-aimed run would produce; without
it a log line cannot tell the two apart.

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
      --project-dir "<main checkout root>"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _plan_state_exemption import partition_plan_state_exemption
from toon_parser import serialize_toon

#: Porcelain status letters that introduce a second (original) path field in
#: ``-z`` output: rename and copy. Both sides are reported, because either one
#: being a tracked source path means the step moved tracked source.
_TWO_PATH_STATUSES: frozenset[str] = frozenset({'R', 'C'})

#: Seconds allowed for the single ``git status`` observation.
_GIT_TIMEOUT_SECONDS: int = 60


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


def _observe_dirty_source(
    project_dir: Path,
) -> tuple[bool, list[str], list[str], list[str], str | None]:
    """Observe real working-tree state and split it via the shared exemption.

    Runs the single tracked-only ``git status`` observation against
    ``project_dir``, decodes it, and applies the shared trackedness-based
    ``.plan/`` exemption
    (:func:`_plan_state_exemption.partition_plan_state_exemption`). Because the
    observation is ``--untracked-files=no``, git has already dropped every
    untracked path, so the exemption's untracked-``.plan/`` arm normally finds
    nothing here — its job at this site is to KEEP the tracked ``.plan/`` files
    the old prefix filter wrongly dropped.

    Args:
        project_dir: Working tree to observe. The predicate is general, but the
            documented caller (item 5f sub-item (0)) must pass the MAIN
            CHECKOUT — see the module docstring for why the worktree is wrong.

    Returns:
        A ``(clean, offenders, exempted, considered, error)`` tuple.
        ``considered`` is every dirty tracked path observed (the population the
        verdict is drawn from); ``exempted`` is the untracked ``.plan/`` subset
        dropped as plan state; ``offenders`` is the retained dirty-source set
        (tracked ``.plan/`` files included). ``clean`` is ``True`` when
        ``offenders`` is empty. On a git failure ``error`` carries the detail and
        ``clean`` is ``True`` with empty lists — an unusable observation never
        manufactures an offender.
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
        return True, [], [], [], f'git status failed: {exc}'

    if completed.returncode != 0:
        detail = completed.stderr.strip() or f'git exited {completed.returncode}'
        return True, [], [], [], f'git status failed: {detail}'

    considered = sorted(set(parse_porcelain_z(completed.stdout)))
    offenders, exempted = partition_plan_state_exemption(considered, project_dir)
    return not offenders, offenders, exempted, considered, None


def check_tracked_source(project_dir: Path) -> tuple[bool, list[str], str | None]:
    """Programmatic 3-tuple view of :func:`_observe_dirty_source`.

    Returns ``(clean, offending_paths, error)`` — the back-compatible shape the
    item-5f caller and the ordering guard consume. The examined population
    (``considered`` / ``exempted``) rides the CLI TOON payload instead; see
    :func:`cmd_check`.
    """
    clean, offenders, _exempted, _considered, error = _observe_dirty_source(project_dir)
    return clean, offenders, error


def cmd_check(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`_observe_dirty_source` — emits TOON, returns 0."""
    project_dir = Path(args.project_dir).expanduser()
    clean, offenders, exempted, considered, error = _observe_dirty_source(project_dir)

    payload: dict[str, object] = {
        'status': 'error' if error else 'success',
        'step_id': args.step_id,
        'project_dir': str(project_dir),
        'clean': clean,
        'considered_paths': considered,
        'exempted_paths': exempted,
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
            'Report dirty TRACKED paths (source, or a tracked .plan/ config/'
            'descriptor) left behind by a post_run_review finalize step. The '
            '.plan/ exemption is keyed on git trackedness, not the path prefix. '
            'Advisory and non-blocking — the verdict rides the TOON payload and '
            'the exit code is always 0.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    check_parser = sub.add_parser(
        'check',
        help='Observe a working tree for dirty tracked source (tracked .plan/ files included)',
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
        required=True,
        dest='project_dir',
        help=(
            'MAIN CHECKOUT to observe. Required, with no default: every '
            'post_run_review step runs after branch-cleanup has removed the '
            "plan's worktree, so defaulting to the cwd would silently observe "
            'a deleted tree and make the check vacuous. See the module '
            'docstring.'
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


__all__ = ['check_tracked_source', 'parse_porcelain_z']
