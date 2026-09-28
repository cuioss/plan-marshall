# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared orchestrator ledger worktree substrate.

With the repository-wide ``orchestrator.use_worktree`` knob on, the orchestrator
ledger store (``.plan/orchestrator/**`` and ``.plan/archived-orchestrators/**``)
lives inside ONE fixed, main-anchored git worktree at
``<main>/.plan/local/worktrees/_orchestrator`` on the long-lived branch
``chore/orchestrator-ledger``. This module owns that tree's location, the knob
read, the ledger drift detector behind the cutover guard, and the idempotent
first-use creation. It is a library module with no CLI entry point.

Import surface is deliberately stdlib plus ``marketplace_paths`` only, so the
module stays importable on the bootstrap path where only ``script-shared``,
``ref-toon-format`` and ``tools-file-ops`` are on ``sys.path``.

The module never removes a worktree, never resets or rebases it, and never
commits: an existing tree is reused exactly as found, and landing its changes on
the base branch is not this module's concern.

Every refusal raises :class:`OrchestratorStoreUnavailable`, one typed error
carrying a machine-readable ``code`` and structured ``fields``:

- ``ledger_cutover_refused`` — the switch-on drift check found uncommitted or
  unlanded ledger paths (``dirty_paths``) on the main checkout.
- ``ledger_drift_unevaluable`` — git could not answer the drift question; a check
  that could not run is never reported as clean.
- ``base_ref_unresolvable`` — ``origin/{base}`` could not be fetched or resolved.
- ``orchestrator_worktree_create_failed`` — the main checkout could not be
  resolved, or ``git worktree add`` failed and no valid worktree exists after it.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from marketplace_paths import (
    ORCHESTRATOR_WORKTREE_KEY,
    PLAN_DIR_NAME,
    WORKTREES_DIRNAME,
    base_dir_override_active,
    main_checkout_root,
    resolve_main_anchored_path,
)

# The long-lived branch the shared ledger worktree checks out. ``chore/`` because
# ledger landings are maintenance, and the working-branch prefix set is closed.
ORCHESTRATOR_WORKTREE_BRANCH = 'chore/orchestrator-ledger'

# The two repo-relative ledger store roots, spelled once. Both the drift
# detector's pathspecs and every consumer that needs to name the ledger surface
# read this tuple.
LEDGER_PATHSPECS = ('.plan/orchestrator', '.plan/archived-orchestrators')

_DEFAULT_BASE_BRANCH = 'main'
_GIT_TIMEOUT_SECONDS = 120


class OrchestratorStoreUnavailable(Exception):
    """The orchestrator store cannot be resolved; carries ``code`` and ``fields``.

    The base is ``Exception`` DIRECTLY — never ``RuntimeError``, ``ValueError`` or
    ``OSError``. The store consumers carry broad ``except RuntimeError`` handlers
    that convert a failure into a different verdict (not-found, fail-open empty,
    silent drop); a subclass of any of those bases would be intercepted by them
    before the refusal reaches the caller that must render it.
    """

    def __init__(self, code: str, message: str, **fields: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields


def orchestrator_worktree_path() -> Path:
    """Return the shared ledger worktree's location, main-anchored.

    ``resolve_main_anchored_path(WORKTREES_DIRNAME) / ORCHESTRATOR_WORKTREE_KEY``:
    the same path from the main checkout and from every plan worktree, because a
    cwd-relative worktree root resolves inside a plan's own worktree and would
    address a different, empty tree.

    Raises:
        RuntimeError: when git cannot resolve the main checkout (not a repo and no
            base-dir override set).
    """
    return resolve_main_anchored_path(WORKTREES_DIRNAME) / ORCHESTRATOR_WORKTREE_KEY


def orchestrator_knob_config_path() -> Path | None:
    """Return the ONE ``marshal.json`` the knob is read from and may be written to.

    That is the MAIN checkout's ``marshal.json`` — or, while a base-dir override
    is active, the override directory's ``marshal.json`` (the override stands in
    for main). Anchoring on main makes every checkout, main and every plan
    worktree alike, agree on the knob.

    Returns:
        The main-anchored ``marshal.json`` path, or ``None`` when no main anchor
        resolves (not inside a git repository and no override set).
    """
    if base_dir_override_active():
        return resolve_main_anchored_path('marshal.json')
    try:
        root = main_checkout_root()
    except RuntimeError:
        return None
    return root / PLAN_DIR_NAME / 'marshal.json'


def _read_knob_config() -> dict[str, Any]:
    """Read the main-anchored ``marshal.json``; absent or unreadable reads as empty."""
    path = orchestrator_knob_config_path()
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def orchestrator_use_worktree() -> bool:
    """Return the effective ``orchestrator.use_worktree`` value.

    Strict bool: only a literal JSON ``true`` turns the knob on. An absent key, an
    absent or unreadable ``marshal.json``, a non-bool value, and an unresolvable
    main anchor all read as ``False``.
    """
    orchestrator = _read_knob_config().get('orchestrator')
    if not isinstance(orchestrator, dict):
        return False
    return orchestrator.get('use_worktree') is True


def _default_base_branch() -> str:
    """Return ``project.default_base_branch`` from the main-anchored config, else ``main``."""
    project = _read_knob_config().get('project')
    if isinstance(project, dict):
        value = project.get('default_base_branch')
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _DEFAULT_BASE_BRANCH


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C {cwd} {args}``; a missing binary or a timeout reads as a failed run."""
    cmd = ['git', '-C', str(cwd), *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=_GIT_TIMEOUT_SECONDS)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(cmd, 1, '', str(exc))


def _porcelain_paths(output: str) -> list[str]:
    """Extract every path from ``git status --porcelain=v1 -z`` output.

    A rename or copy entry is followed by its source path as a separate record;
    both sides are ledger drift, so both are returned.
    """
    paths: list[str] = []
    records = output.split('\0')
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        status, path = record[:2], record[3:]
        paths.append(path)
        if status[0] in 'RC' and index < len(records) and records[index]:
            paths.append(records[index])
            index += 1
    return paths


def detect_ledger_drift(checkout_root: Path, base_ref: str) -> list[str]:
    """Return every ledger path that would be stranded by leaving ``checkout_root``.

    A ledger path is drift when it is uncommitted or untracked in the checkout
    (``git status --porcelain`` over :data:`LEDGER_PATHSPECS`), or committed but
    not on ``base_ref`` (``git log {base_ref}..HEAD --name-only`` over the same
    pathspecs). Paths outside the ledger store are never reported.

    Args:
        checkout_root: Root of the checkout to inspect.
        base_ref: The ref a committed ledger path must be reachable from to count
            as landed (e.g. ``origin/main``).

    Returns:
        The sorted, de-duplicated repo-relative drift paths; empty when clean.

    Raises:
        OrchestratorStoreUnavailable: code ``ledger_drift_unevaluable`` when git
            cannot answer either question.
    """
    status = _git(checkout_root, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', *LEDGER_PATHSPECS)
    if status.returncode != 0:
        raise OrchestratorStoreUnavailable(
            'ledger_drift_unevaluable',
            f'cannot read the ledger working-tree state of {checkout_root}: {status.stderr.strip()}',
            checkout=str(checkout_root),
            base_ref=base_ref,
            stderr=status.stderr.strip(),
        )
    log = _git(checkout_root, 'log', f'{base_ref}..HEAD', '--name-only', '--pretty=format:', '--', *LEDGER_PATHSPECS)
    if log.returncode != 0:
        raise OrchestratorStoreUnavailable(
            'ledger_drift_unevaluable',
            f'cannot compare the ledger history of {checkout_root} against {base_ref}: {log.stderr.strip()}',
            checkout=str(checkout_root),
            base_ref=base_ref,
            stderr=log.stderr.strip(),
        )
    drift = set(_porcelain_paths(status.stdout))
    drift.update(line.strip() for line in log.stdout.splitlines() if line.strip())
    return sorted(drift)


def _registered_worktree_branch(main_root: Path, path: Path) -> str | None:
    """Return the branch a registered worktree at ``path`` has checked out.

    Returns ``None`` when no worktree is registered at ``path``, and ``''`` for a
    registered worktree on a detached HEAD.
    """
    listing = _git(main_root, 'worktree', 'list', '--porcelain')
    if listing.returncode != 0:
        return None
    target = path.resolve()
    current: Path | None = None
    branch = ''
    for line in [*listing.stdout.splitlines(), '']:
        if line.startswith('worktree '):
            current = Path(line[len('worktree ') :]).resolve()
            branch = ''
        elif line.startswith('branch '):
            branch = line[len('branch ') :].removeprefix('refs/heads/')
        elif not line and current is not None:
            if current == target:
                return branch
            current = None
    return None


def ensure_orchestrator_worktree() -> Path:
    """Return the shared ledger worktree, creating it on first use.

    An existing registered worktree at :func:`orchestrator_worktree_path` is
    returned unchanged — no reset, no rebase, no pull. Otherwise the tree is
    created off ``origin/{base}`` (``{base}`` is ``project.default_base_branch``,
    default ``main``):

    1. ``git fetch origin {base}``, then verify ``origin/{base}`` resolves. The
       fetch runs first so the drift check below compares against the base as it
       stands on the remote, not a stale local copy of it.
    2. The switch-on drift check (:func:`detect_ledger_drift`) against the main
       checkout — refused with ``ledger_cutover_refused`` naming every path, so a
       hand-edited ``marshal.json`` cannot bypass the cutover guard.
    3. ``git worktree add``: an existing local ``chore/orchestrator-ledger`` branch
       is reused; otherwise it is created with ``-b`` from ``origin/{base}``.
    4. On a failed add, the post-add re-check: two sessions can race to first
       use, and ``git worktree add`` is the atomic primitive that lets only one
       win. When the path is now a registered worktree on the ledger branch, the
       loser returns it as success; only a failure that leaves no valid worktree
       is reported.

    Returns:
        The worktree root path.

    Raises:
        OrchestratorStoreUnavailable: ``ledger_cutover_refused`` (with
            ``dirty_paths``), ``ledger_drift_unevaluable``,
            ``base_ref_unresolvable`` or ``orchestrator_worktree_create_failed``;
            the git-backed codes carry git's ``stderr``.
    """
    try:
        path = orchestrator_worktree_path()
        main_root = main_checkout_root()
    except RuntimeError as exc:
        raise OrchestratorStoreUnavailable(
            'orchestrator_worktree_create_failed',
            f'cannot resolve the main checkout for the orchestrator ledger worktree: {exc}',
            branch=ORCHESTRATOR_WORKTREE_BRANCH,
        ) from exc

    if _registered_worktree_branch(main_root, path) is not None:
        return path

    base = _default_base_branch()
    base_ref = f'origin/{base}'
    probe = _git(main_root, 'fetch', 'origin', base)
    if probe.returncode == 0:
        probe = _git(main_root, 'rev-parse', '--verify', '--quiet', f'refs/remotes/{base_ref}^{{commit}}')
    if probe.returncode != 0:
        stderr = probe.stderr.strip()
        raise OrchestratorStoreUnavailable(
            'base_ref_unresolvable',
            f'cannot resolve {base_ref} to create the orchestrator ledger worktree: {stderr}',
            base_ref=base_ref,
            worktree_path=str(path),
            branch=ORCHESTRATOR_WORKTREE_BRANCH,
            stderr=stderr,
        )

    dirty_paths = detect_ledger_drift(main_root, base_ref)
    if dirty_paths:
        raise OrchestratorStoreUnavailable(
            'ledger_cutover_refused',
            f'the main checkout holds {len(dirty_paths)} uncommitted or unlanded ledger path(s); '
            'land or discard them before the ledger moves into the shared worktree',
            dirty_paths=dirty_paths,
            worktree_path=str(path),
            branch=ORCHESTRATOR_WORKTREE_BRANCH,
        )

    branch_exists = _git(main_root, 'rev-parse', '--verify', '--quiet', f'refs/heads/{ORCHESTRATOR_WORKTREE_BRANCH}')
    if branch_exists.returncode == 0:
        add = _git(main_root, 'worktree', 'add', str(path), ORCHESTRATOR_WORKTREE_BRANCH)
    else:
        add = _git(main_root, 'worktree', 'add', '--no-track', '-b', ORCHESTRATOR_WORKTREE_BRANCH, str(path), base_ref)
    if add.returncode == 0:
        return path

    if _registered_worktree_branch(main_root, path) == ORCHESTRATOR_WORKTREE_BRANCH:
        return path
    raise OrchestratorStoreUnavailable(
        'orchestrator_worktree_create_failed',
        f'git worktree add failed for {path}: {add.stderr.strip()}',
        worktree_path=str(path),
        branch=ORCHESTRATOR_WORKTREE_BRANCH,
        stderr=add.stderr.strip(),
    )
