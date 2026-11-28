#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Landing the shared orchestrator ledger worktree onto the base branch.

Backs ``orchestrator.py``'s ``land`` verb group. With ``orchestrator.use_worktree``
on, the ledger lives in ONE long-lived worktree on ``chore/orchestrator-ledger``
that every session writes to and nothing ever recreates. Landing it is therefore
not "commit, open a PR, delete the branch": the tree keeps receiving writes while
its PR is in the merge queue, and after the PR lands the SAME tree must continue
on top of the new base. This module owns the four deterministic steps of that
cycle; the PR, CI, review and merge-queue steps between them belong to the
``land`` workflow and the CI abstraction.

* ``status`` — read-only report of where the tree stands in the cycle.
* ``snapshot [--extend]`` — commit the ledger paths, push the commit to the
  remote head branch WITHOUT force, and record the pushed commit.
* ``bind --pr-number N`` — record which PR carries the in-flight land.
* ``resync --pr-number N --merge-commit-sha SHA`` — after the PR landed, verify
  the landed content, replay everything written since the snapshot onto the new
  base, and close the cycle.

**State lives in two local-only refs**, never in a file: the pushed marker
:data:`PUSHED_MARKER_REF` names the commit the in-flight land pushed, and the PR
binding ``refs/plan-marshall/ledger-land/pr/{N}`` names the PR that carries it
(same SHA; at most one exists). Neither ref is ever pushed. A land is *in flight*
exactly while the marker exists.

**What this module never does.** No hard reset, no stash drop, no removal of the
tree, and no forced push other than the one lease-guarded delete of the landed
remote head branch. A rebase that cannot complete is aborted and the tree is left
exactly where it was.

Every verb refuses with ``land_requires_use_worktree`` while the knob is off and
resolves the tree through :func:`orchestrator_worktree.ensure_orchestrator_worktree`,
whose typed :class:`~orchestrator_worktree.OrchestratorStoreUnavailable` refusals
propagate to ``safe_main`` and render under their own codes. Git is always
targeted as ``git -C {store_checkout}``.

**Concurrency (TOCTOU / check-then-act).** Every check-then-act over the two refs
and the commit runs inside :func:`_land_guard` — :func:`_locks_core.held_guard`
on one main-anchored guard file — with the check re-read inside the guard. The
guard is reclaimed after a bounded age, so network round-trips (push, fetch,
ls-remote) always run OUTSIDE it, and the git calls made inside it share one
deadline that ends before that age. The mitigation menu lives in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.
"""

from __future__ import annotations

import argparse
import functools
import re
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from _locks_core import _GUARD_STALE_SECONDS, held_guard
from marketplace_paths import main_checkout_root, resolve_main_anchored_path
from orchestrator_worktree import (
    LEDGER_PATHSPECS,
    ORCHESTRATOR_WORKTREE_BRANCH,
    default_base_branch,
    ensure_orchestrator_worktree,
    orchestrator_use_worktree,
)
from run_config import read_commit_trailer

#: The local-only ref naming the commit the in-flight land pushed.
PUSHED_MARKER_REF = 'refs/plan-marshall/ledger-land/pushed'

#: Prefix of the local-only PR binding ref; the PR number is the last component.
BINDING_REF_PREFIX = 'refs/plan-marshall/ledger-land/pr/'

#: The remote head branch a land pushes to and a resync deletes.
REMOTE_HEAD_REF = f'refs/heads/{ORCHESTRATOR_WORKTREE_BRANCH}'

#: The main-anchored guard file every land critical section holds.
LAND_GUARD_FILE = 'orchestrator-land.lock'

#: The tri-state value of a read that could not be completed.
UNKNOWN = 'unknown'

#: Body sections of a composed land, in render order, keyed by the first path
#: component (or exact file name) below the epic directory.
_CATEGORY_ORDER = ('queue rows', 'plan specs', 'anchor/header', 'landings', 'inbox', 'other')
_CATEGORY_BY_DIR = {'queue': 'queue rows', 'plans': 'plan specs', 'landings': 'landings', 'inbox': 'inbox'}
_HEADER_FILES = frozenset({'status.json', 'resume_anchor.md'})

#: Bound of one git call made OUTSIDE the land guard.
_GIT_TIMEOUT_SECONDS = 120

#: Wall-clock budget shared by every git call of one guarded section, and the
#: further allowance for aborting a replay that ran into it. Their sum is below
#: the age at which the next acquirer reclaims the guard.
_GUARD_WORK_SECONDS = _GUARD_STALE_SECONDS / 2
_GUARD_ABORT_SECONDS = _GUARD_STALE_SECONDS / 4

_SHA_RE = re.compile(r'^[0-9a-f]{7,64}$')


class _GuardClock:
    """The deadline of the guarded section this process is in; ``None`` outside one."""

    deadline: float | None = None


# --- git plumbing -------------------------------------------------------------


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C {cwd} {args}``; a missing binary or a timeout reads as a failed run.

    Inside :func:`_land_guard` the call is bounded by what is left of the
    section's deadline instead, and running into it raises ``TimeoutError``.
    """
    cmd = ['git', '-C', str(cwd), *args]
    guarded = _GuardClock.deadline is not None
    timeout = _GuardClock.deadline - time.monotonic() if _GuardClock.deadline is not None else _GIT_TIMEOUT_SECONDS
    out_of_budget = f'the guarded land section ran out of its time budget at `git {args[0]}`'
    if timeout <= 0:
        raise TimeoutError(out_of_budget)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(cmd, 1, '', str(exc))
    except subprocess.TimeoutExpired as exc:
        if guarded:
            raise TimeoutError(out_of_budget) from exc
        return subprocess.CompletedProcess(cmd, 1, '', str(exc))


@contextmanager
def _land_guard() -> Iterator[None]:
    """Hold the land guard for a ``with`` block whose git calls share one deadline.

    The deadline keeps the whole block shorter than the age at which the next
    acquirer reclaims the guard. A git call that runs into it is killed and
    raises ``TimeoutError``; the guard is released either way.
    """
    with held_guard(_guard_path()):
        _GuardClock.deadline = time.monotonic() + _GUARD_WORK_SECONDS
        try:
            yield
        finally:
            _GuardClock.deadline = None


def _error(code: str, message: str, **fields: Any) -> dict[str, Any]:
    return {'status': 'error', 'error': code, 'message': message, **fields}


def _rev(checkout: Path, rev: str) -> str | None:
    """Resolve ``rev`` to a commit SHA, or ``None`` when it does not resolve."""
    result = _git(checkout, 'rev-parse', '--verify', '--quiet', f'{rev}^{{commit}}')
    sha = result.stdout.strip()
    return sha if result.returncode == 0 and sha else None


def _is_ancestor(checkout: Path, ancestor: str, descendant: str) -> bool | None:
    """Return whether ``ancestor`` is contained in ``descendant``; ``None`` when git cannot say."""
    result = _git(checkout, 'merge-base', '--is-ancestor', ancestor, descendant)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    return None


def _commit_count(checkout: Path, revision_range: str) -> int | None:
    """Count the commits in ``revision_range``; ``None`` when the range does not resolve."""
    result = _git(checkout, 'rev-list', '--count', revision_range)
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _name_list(checkout: Path, *args: str) -> list[str] | None:
    """Run a name-listing git query; ``None`` when the call fails."""
    result = _git(checkout, *args)
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line.strip()]


def _pending_ledger_paths(checkout: Path) -> list[str] | None:
    """Return every uncommitted or untracked ledger path; ``None`` when git cannot say.

    Rename detection is switched off so every ``-z`` record is one ``XY path``
    entry and both sides of a move are reported as their own paths.
    """
    result = _git(
        checkout,
        '-c',
        'status.renames=false',
        'status',
        '--porcelain=v1',
        '-z',
        '--untracked-files=all',
        '--',
        *LEDGER_PATHSPECS,
    )
    if result.returncode != 0:
        return None
    return sorted(record[3:] for record in result.stdout.split('\0') if len(record) > 3)


def _binding_prs(checkout: Path) -> list[int]:
    """Return the PR numbers that currently carry a binding ref, ascending."""
    refs = _name_list(checkout, 'for-each-ref', '--format=%(refname)', BINDING_REF_PREFIX) or []
    numbers = []
    for ref in refs:
        suffix = ref.strip()[len(BINDING_REF_PREFIX) :]
        if suffix.isdigit():
            numbers.append(int(suffix))
    return sorted(numbers)


def _remote_head(checkout: Path) -> tuple[str, str | None]:
    """Read the remote head branch: ``(present|absent|unknown, sha)``.

    A failed ``git ls-remote`` is ``unknown`` — never ``absent``: a remote that
    could not be asked has not said the branch is gone.
    """
    result = _git(checkout, 'ls-remote', '--heads', 'origin', REMOTE_HEAD_REF)
    if result.returncode != 0:
        return UNKNOWN, None
    for line in result.stdout.splitlines():
        sha, _, ref = line.partition('\t')
        if ref.strip() == REMOTE_HEAD_REF and sha.strip():
            return 'present', sha.strip()
    return 'absent', None


def _remote_contained(checkout: Path, remote_state: str, remote_sha: str | None) -> bool | str:
    """Whether every commit on the remote head branch is contained in local ``HEAD``.

    ``True`` for an absent remote branch (it holds no commit the local branch
    lacks — read ``remote_branch`` beside it to tell that case from a contained
    present branch), ``unknown`` when the remote could not be read, and ``False``
    when the remote commit is not in the local object store at all.
    """
    if remote_state == UNKNOWN:
        return UNKNOWN
    if remote_state == 'absent' or remote_sha is None:
        return True
    if _rev(checkout, remote_sha) is None:
        return False
    contained = _is_ancestor(checkout, remote_sha, 'HEAD')
    return UNKNOWN if contained is None else contained


def _guard_path() -> Path:
    return resolve_main_anchored_path(LAND_GUARD_FILE)


def _land_verb(
    body: Callable[[Path, argparse.Namespace], dict[str, Any]],
) -> Callable[[argparse.Namespace], dict[str, Any]]:
    """Wrap a land handler body with the knob refusal and the tree resolution.

    The knob-off refusal is returned before the tree is touched. The tree is
    resolved through ``ensure_orchestrator_worktree``; its typed refusals are NOT
    caught here — they reach ``safe_main`` and render under their own codes. A
    guard that could not be acquired, or a guarded section that ran out of its
    time budget, is an operation failure, not a crash.
    """

    @functools.wraps(body)
    def handler(args: argparse.Namespace) -> dict[str, Any]:
        if not orchestrator_use_worktree():
            return _error(
                'land_requires_use_worktree',
                'orchestrator land needs the shared ledger worktree; orchestrator.use_worktree is off, '
                'so the ledger lives on the main checkout and lands with the plan that changed it',
            )
        checkout = ensure_orchestrator_worktree()
        try:
            return body(checkout, args)
        except TimeoutError as exc:
            return _error('land_guard_timeout', str(exc), store_checkout=str(checkout))

    return handler


# --- status -------------------------------------------------------------------


@_land_verb
def cmd_land_status(checkout: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Report where the shared ledger worktree stands in the land cycle (read-only)."""
    del args  # fixed-shape verb
    base = default_base_branch()
    branch = _git(checkout, 'rev-parse', '--abbrev-ref', 'HEAD')
    marker = _rev(checkout, PUSHED_MARKER_REF)
    bound = _binding_prs(checkout)
    pending = _pending_ledger_paths(checkout)
    unpushed = _commit_count(checkout, f'{marker}..HEAD' if marker else f'origin/{base}..HEAD')
    remote_state, remote_sha = _remote_head(checkout)

    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'land_status',
        'store_checkout': str(checkout),
        'branch': branch.stdout.strip() if branch.returncode == 0 else UNKNOWN,
        'base_branch': base,
        'pending_paths': UNKNOWN if pending is None else pending,
        'pending_count': UNKNOWN if pending is None else len(pending),
        'unpushed_commits': UNKNOWN if unpushed is None else unpushed,
        'pushed_marker': marker,
        'bound_pr': bound[0] if len(bound) == 1 else None,
        'remote_branch': remote_state,
        'remote_branch_contained': _remote_contained(checkout, remote_state, remote_sha),
    }
    if len(bound) > 1:
        result['bound_pr_conflict'] = bound
    return result


# --- snapshot -----------------------------------------------------------------


def _stage_ledger(checkout: Path) -> subprocess.CompletedProcess[str] | None:
    """``git add -A`` every ledger root that exists or is tracked; return a failed run, else ``None``.

    A root that is neither on disk nor tracked is skipped: ``git add`` rejects a
    pathspec that matches nothing, and such a root has nothing to stage.
    """
    for spec in LEDGER_PATHSPECS:
        tracked = _name_list(checkout, 'ls-files', '--', spec)
        if not (checkout / spec).exists() and not tracked:
            continue
        added = _git(checkout, 'add', '-A', '--', spec)
        if added.returncode != 0:
            return added
    return None


def _commit_staged_ledger(checkout: Path) -> dict[str, Any] | int:
    """Commit the staged ledger paths; return the committed path count or an error payload."""
    staged = _name_list(checkout, 'diff', '--cached', '--name-only', '--no-renames', '--', *LEDGER_PATHSPECS)
    if staged is None:
        return _error('ledger_commit_failed', 'cannot read the staged ledger paths', store_checkout=str(checkout))
    if not staged:
        return 0
    specs = [spec for spec in LEDGER_PATHSPECS if any(path.startswith(f'{spec}/') for path in staged)]
    subject = f'chore(orchestrator): snapshot ledger ({len(staged)} path{"" if len(staged) == 1 else "s"})'
    commit = _git(checkout, 'commit', '-m', subject, '-m', read_commit_trailer()['trailer'], '--', *specs)
    if commit.returncode != 0:
        return _error(
            'ledger_commit_failed',
            'git commit of the staged ledger paths failed',
            store_checkout=str(checkout),
            stderr=commit.stderr.strip() or commit.stdout.strip(),
        )
    return len(staged)


def _categorize(path: str) -> tuple[str, str]:
    """Map a ledger path to ``(epic, category)``.

    The epic is the directory directly below a ledger root; an archived epic is
    labelled as such. A path directly inside a ledger root belongs to no epic.
    """
    for spec in LEDGER_PATHSPECS:
        if not path.startswith(f'{spec}/'):
            continue
        parts = path[len(spec) + 1 :].split('/')
        if len(parts) < 2:
            return '(store root)', 'other'
        epic = parts[0] if spec == LEDGER_PATHSPECS[0] else f'{parts[0]} (archived)'
        if len(parts) == 2:
            return epic, 'anchor/header' if parts[1] in _HEADER_FILES else 'other'
        return epic, _CATEGORY_BY_DIR.get(parts[1], 'other')
    return '(store root)', 'other'


def compose_land_message(name_status: list[tuple[str, str]]) -> tuple[str, str]:
    """Compose the PR title and body for a land from its ``(status, path)`` rows.

    The body groups the changed ledger paths per epic, and within an epic per
    category in :data:`_CATEGORY_ORDER`. It carries no attribution footer.
    """
    grouped: dict[str, dict[str, list[str]]] = {}
    for status, path in name_status:
        epic, category = _categorize(path)
        grouped.setdefault(epic, {}).setdefault(category, []).append(f'{status} {path}')

    epics = sorted(grouped)
    total = len(name_status)
    paths = f'{total} path{"" if total == 1 else "s"}'
    if len(epics) == 1:
        title = f'chore(orchestrator-ledger): land {epics[0]} ledger ({paths})'
    else:
        title = f'chore(orchestrator-ledger): land ledger for {len(epics)} epics ({paths})'

    lines = ['## Summary', '', f'Lands {paths} of orchestrator ledger state across {len(epics)} epic(s).', '']
    for epic in epics:
        lines.append(f'## {epic}')
        lines.append('')
        for category in _CATEGORY_ORDER:
            rows = grouped[epic].get(category)
            if not rows:
                continue
            lines.append(f'**{category}** ({len(rows)})')
            lines.append('')
            lines.extend(f'- `{row}`' for row in sorted(rows))
            lines.append('')
    return title, '\n'.join(lines).rstrip() + '\n'


def _land_name_status(checkout: Path, base: str, head: str) -> list[tuple[str, str]] | None:
    """Ledger ``(status, path)`` rows the land carries relative to its fork point from the base."""
    rows = _name_list(
        checkout, 'diff', '--name-status', '--no-renames', f'origin/{base}...{head}', '--', *LEDGER_PATHSPECS
    )
    if rows is None:
        return None
    parsed = []
    for row in rows:
        status, _, path = row.partition('\t')
        if path:
            parsed.append((status.strip(), path.strip()))
    return parsed


@_land_verb
def cmd_land_snapshot(checkout: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Commit the ledger paths, push them without force, and record the pushed commit."""
    extend = args.extend
    base = default_base_branch()

    with _land_guard():
        marker = _rev(checkout, PUSHED_MARKER_REF)
        if marker and not extend:
            in_flight_prs = _binding_prs(checkout)
            return {
                'status': 'success',
                'operation': 'land_snapshot',
                'outcome': 'in_flight',
                'pushed_marker': marker,
                'bound_pr': in_flight_prs[0] if in_flight_prs else None,
            }
        failed_add = _stage_ledger(checkout)
        if failed_add is not None:
            return _error(
                'ledger_commit_failed',
                'git add of the ledger paths failed',
                store_checkout=str(checkout),
                stderr=failed_add.stderr.strip(),
            )
        committed = _commit_staged_ledger(checkout)
        if isinstance(committed, dict):
            return committed
        head = _rev(checkout, 'HEAD')
        if head is None:
            return _error(
                'ledger_commit_failed', 'cannot resolve HEAD of the ledger worktree', store_checkout=str(checkout)
            )
        unpushed = _commit_count(checkout, f'{marker}..HEAD' if marker else f'origin/{base}..HEAD')
        # An unresolvable range is NOT a measured zero: only a counted 0 is "nothing".
        if not extend and committed == 0 and unpushed == 0:
            return {
                'status': 'success',
                'operation': 'land_snapshot',
                'outcome': 'nothing_to_land',
                'head_sha': head,
            }

    # The push is a network round-trip: outside the guard, and never forced.
    push = _git(checkout, 'push', 'origin', f'{head}:{REMOTE_HEAD_REF}')
    if push.returncode != 0:
        remote_state, remote_sha = _remote_head(checkout)
        return _error(
            'ledger_push_rejected',
            f'the push of {head} to {ORCHESTRATOR_WORKTREE_BRANCH} was rejected; '
            'the commit is kept and no land is recorded',
            head_sha=head,
            committed_paths=committed,
            remote_branch=remote_state,
            remote_branch_contained=_remote_contained(checkout, remote_state, remote_sha),
            stderr=push.stderr.strip(),
        )

    with _land_guard():
        current = _rev(checkout, PUSHED_MARKER_REF)
        # Never move the marker backwards: a concurrent --extend may already have
        # recorded a later push that contains this one.
        if current is None or current == head or _is_ancestor(checkout, head, current) is not True:
            current = head
            recorded = _git(checkout, 'update-ref', PUSHED_MARKER_REF, head)
            if recorded.returncode != 0:
                return _error(
                    'land_ref_write_failed',
                    f'{head} was pushed but the pushed marker could not be recorded',
                    head_sha=head,
                    stderr=recorded.stderr.strip(),
                )
        bound = _binding_prs(checkout)
        for pr in bound:
            _git(checkout, 'update-ref', f'{BINDING_REF_PREFIX}{pr}', current)

    name_status = _land_name_status(checkout, base, head)
    title, body = compose_land_message(name_status or [])
    return {
        'status': 'success',
        'operation': 'land_snapshot',
        'outcome': 'pushed',
        'head_sha': head,
        'pushed_marker': current,
        'committed_paths': committed,
        'bound_pr': bound[0] if bound else None,
        'land_paths': UNKNOWN if name_status is None else len(name_status),
        'title': title,
        'body': body,
    }


# --- bind ---------------------------------------------------------------------


@_land_verb
def cmd_land_bind(checkout: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Point the PR binding ref at the pushed marker; idempotent."""
    pr_number = args.pr_number
    target = f'{BINDING_REF_PREFIX}{pr_number}'
    with _land_guard():
        marker = _rev(checkout, PUSHED_MARKER_REF)
        if marker is None:
            return _no_land_in_flight(pr_number)
        for other in _binding_prs(checkout):
            if other != pr_number:
                _git(checkout, 'update-ref', '-d', f'{BINDING_REF_PREFIX}{other}')
        bound = _git(checkout, 'update-ref', target, marker)
        if bound.returncode != 0:
            return _error(
                'land_ref_write_failed',
                f'the binding ref for PR {pr_number} could not be written',
                pr_number=pr_number,
                stderr=bound.stderr.strip(),
            )
    return {
        'status': 'success',
        'operation': 'land_bind',
        'outcome': 'bound',
        'pr_number': pr_number,
        'pushed_marker': marker,
    }


def _no_land_in_flight(pr_number: int) -> dict[str, Any]:
    return _error(
        'no_land_in_flight',
        'no pushed marker exists, so no land is in flight; run `land snapshot` first',
        pr_number=pr_number,
    )


# --- resync -------------------------------------------------------------------


def _mismatched_land_paths(checkout: Path, marker: str, merge_sha: str) -> dict[str, Any] | list[str]:
    """Return the ledger paths the land changed whose content at ``merge_sha`` differs from the marker.

    The land's own change set is measured from the marker's fork point off the
    merge commit's FIRST PARENT — the base as it stood when the land merged — so
    the set is the same under a squash, a rebase and a true merge. Measuring from
    the merge commit itself would make a true merge's set empty and the check
    vacuous.
    """
    fork = _git(checkout, 'merge-base', marker, f'{merge_sha}^')
    fork_sha = fork.stdout.strip()
    if fork.returncode != 0 or not fork_sha:
        return _error(
            'resync_content_unevaluable',
            f'cannot find where the land forked from the base below {merge_sha}',
            merge_commit_sha=merge_sha,
            pushed_marker=marker,
            stderr=fork.stderr.strip(),
        )
    changed = _name_list(checkout, 'diff', '--name-only', '--no-renames', fork_sha, marker, '--', *LEDGER_PATHSPECS)
    if changed is None:
        return _error(
            'resync_content_unevaluable',
            'cannot enumerate the ledger paths the land changed',
            merge_commit_sha=merge_sha,
            pushed_marker=marker,
        )
    if not changed:
        return []
    differing = _name_list(checkout, 'diff', '--name-only', '--no-renames', marker, merge_sha, '--', *changed)
    if differing is None:
        return _error(
            'resync_content_unevaluable',
            f'cannot compare the landed ledger content at {merge_sha} against the pushed marker',
            merge_commit_sha=merge_sha,
            pushed_marker=marker,
        )
    return sorted(differing)


def _fast_forward_main(base: str) -> str:
    """Fast-forward the primary checkout's base branch to ``origin/{base}``: ``done`` or ``failed``.

    Never forced and never a reason to stop the resync: the ledger tree is
    resynced regardless, and a primary checkout that could not move is reported.
    """
    try:
        main_root = main_checkout_root()
    except RuntimeError:
        return 'failed'
    current = _git(main_root, 'rev-parse', '--abbrev-ref', 'HEAD')
    if current.returncode != 0:
        return 'failed'
    if current.stdout.strip() == base:
        moved = _git(main_root, 'merge', '--ff-only', f'origin/{base}')
    else:
        # Not checked out there: move the branch ref itself; a non-fast-forward is refused by git.
        moved = _git(main_root, 'fetch', '.', f'refs/remotes/origin/{base}:refs/heads/{base}')
    return 'done' if moved.returncode == 0 else 'failed'


def _delete_landed_remote_branch(checkout: Path, marker: str) -> str:
    """Delete the landed remote head branch, only while it still sits at ``marker``.

    Returns ``deleted``, ``already_absent``, ``kept_diverged`` (the remote branch
    moved past the landed commit, so it holds work that has not landed) or
    ``failed``. The delete is lease-guarded on the marker, so a branch that moved
    between the read and the push is still kept.
    """
    remote_state, remote_sha = _remote_head(checkout)
    if remote_state == UNKNOWN:
        return 'failed'
    if remote_state == 'absent':
        return 'already_absent'
    if remote_sha != marker:
        return 'kept_diverged'
    push = _git(checkout, 'push', f'--force-with-lease={REMOTE_HEAD_REF}:{marker}', 'origin', f':{REMOTE_HEAD_REF}')
    if push.returncode == 0:
        return 'deleted'
    return 'kept_diverged' if 'stale info' in push.stderr else 'failed'


def _replay_onto(checkout: Path, base_ref: str, marker: str) -> subprocess.CompletedProcess[str]:
    """Rebase everything after ``marker`` onto ``base_ref``; running out of the guard budget is a failed run."""
    try:
        return _git(checkout, 'rebase', '--autostash', '--onto', base_ref, marker)
    except TimeoutError as exc:
        return subprocess.CompletedProcess([], 1, '', str(exc))


def _abort_replay(checkout: Path) -> None:
    """Abort a failed replay on the abort allowance, so one that spent the work budget is still undone."""
    _GuardClock.deadline = max(_GuardClock.deadline or 0.0, time.monotonic() + _GUARD_ABORT_SECONDS)
    _git(checkout, 'rebase', '--abort')


def _delete_land_refs(checkout: Path) -> None:
    for pr in _binding_prs(checkout):
        _git(checkout, 'update-ref', '-d', f'{BINDING_REF_PREFIX}{pr}')
    _git(checkout, 'update-ref', '-d', PUSHED_MARKER_REF)


@_land_verb
def cmd_land_resync(checkout: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Replay the ledger tree onto the base the land merged into and close the cycle."""
    pr_number = args.pr_number
    merge_sha = args.merge_commit_sha.strip().lower()
    base = default_base_branch()
    base_ref = f'origin/{base}'

    marker = _rev(checkout, PUSHED_MARKER_REF)
    if marker is None:
        return _no_land_in_flight(pr_number)
    if not _SHA_RE.match(merge_sha):
        return _error(
            'invalid_merge_commit_sha',
            '--merge-commit-sha must be a hexadecimal commit SHA',
            pr_number=pr_number,
            merge_commit_sha=merge_sha,
        )

    fetch = _git(checkout, 'fetch', 'origin', base)
    if fetch.returncode != 0:
        return _error(
            'base_fetch_failed',
            f'cannot fetch {base_ref}, so the landed commit cannot be checked against the base',
            pr_number=pr_number,
            base_branch=base,
            stderr=fetch.stderr.strip(),
        )
    if _rev(checkout, merge_sha) is None or _is_ancestor(checkout, merge_sha, base_ref) is not True:
        return _error(
            'merge_commit_not_on_base',
            f'{merge_sha} is not a commit on {base_ref}; the land has not reached the base under that SHA',
            pr_number=pr_number,
            merge_commit_sha=merge_sha,
            base_branch=base,
        )
    mismatched = _mismatched_land_paths(checkout, marker, merge_sha)
    if isinstance(mismatched, dict):
        return {**mismatched, 'pr_number': pr_number}
    if mismatched:
        return _error(
            'resync_content_mismatch',
            f'{len(mismatched)} ledger path(s) the land changed differ at {merge_sha} from the pushed marker; '
            'the tree is left untouched',
            pr_number=pr_number,
            merge_commit_sha=merge_sha,
            pushed_marker=marker,
            mismatched_paths=mismatched,
        )

    # Network and primary-checkout steps: outside the guard, and never fatal.
    main_fast_forward = _fast_forward_main(base)
    remote_branch_cleanup = _delete_landed_remote_branch(checkout, marker)

    try:
        with _land_guard():
            marker_now = _rev(checkout, PUSHED_MARKER_REF)
            if marker_now is None:
                return _no_land_in_flight(pr_number)
            pre_rebase = _rev(checkout, 'HEAD')
            replayed = _commit_count(checkout, f'{marker_now}..HEAD')
            carried = _git(checkout, 'status', '--porcelain=v1', '--untracked-files=no')
            carried_uncommitted = bool(carried.stdout.strip()) if carried.returncode == 0 else UNKNOWN
            # A HEAD that no longer contains the marker was already replayed onto the
            # base by an earlier resync that stopped before closing the cycle.
            already_resynced = _is_ancestor(checkout, marker_now, 'HEAD') is False
            if already_resynced:
                replayed = 0
            else:
                rebase = _replay_onto(checkout, base_ref, marker_now)
                if rebase.returncode != 0:
                    _abort_replay(checkout)
                    return _error(
                        'resync_conflict',
                        'the ledger tree could not be replayed onto the base; '
                        'the rebase was aborted and both land refs are kept',
                        pr_number=pr_number,
                        merge_commit_sha=merge_sha,
                        pushed_marker=marker_now,
                        pre_rebase_sha=pre_rebase,
                        head_restored=_rev(checkout, 'HEAD') == pre_rebase,
                        main_fast_forward=main_fast_forward,
                        remote_branch_cleanup=remote_branch_cleanup,
                        stderr=rebase.stderr.strip() or rebase.stdout.strip(),
                    )
            _delete_land_refs(checkout)
    except TimeoutError as exc:
        return _error(
            'land_guard_timeout',
            str(exc),
            store_checkout=str(checkout),
            pr_number=pr_number,
            main_fast_forward=main_fast_forward,
            remote_branch_cleanup=remote_branch_cleanup,
        )

    return {
        'status': 'success',
        'operation': 'land_resync',
        'outcome': 'resynced',
        'pr_number': pr_number,
        'merge_commit_sha': merge_sha,
        'head_sha': _rev(checkout, 'HEAD'),
        'already_resynced': already_resynced,
        'replayed_commits': UNKNOWN if replayed is None else replayed,
        'carried_uncommitted': carried_uncommitted,
        'main_fast_forward': main_fast_forward,
        'remote_branch_cleanup': remote_branch_cleanup,
    }
