#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Read-only compute-footprint query for manage-references.

Derives the plan's actual footprint live from the worktree git state — the
union of the three-dot ``{base_ref}...HEAD`` diff and the porcelain working-tree
state — without consulting any persisted ledger. The footprint is computed
on-demand from the worktree, which is the single source of truth.

This handler is read-only with respect to ``references.json``: it never mutates
it. It reads ``references.json`` only to resolve ``base_branch`` for the diff
range. The one opt-in write it performs is ``--files-out``, which writes the
computed list to a caller-named file and nothing else — the faithful hand-off
for a consumer that takes the footprint as a file rather than as a
hand-composed command-line string.

Resolution rule:
    files = sorted live footprint set

Where ``live`` is the union of:
    - ``git -C {worktree_path} diff --name-only {base_ref}...HEAD``
    - parsed paths from ``git -C {worktree_path} status --porcelain``
"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from _references_core import (
    _ref_resolves_in_worktree,
    _run_git,
    compute_plan_branch_diff,
    get_references_path,
    read_references,
    resolve_base_ref,
    write_references,
)
from input_validation import require_valid_plan_id


def cmd_compute_footprint(args: argparse.Namespace) -> dict:
    """Return the live plan-branch-only footprint set.

    Read-only — never writes references.json.
    """
    require_valid_plan_id(args)

    worktree = Path(args.worktree_path)
    if not worktree.exists() or not worktree.is_dir():
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'worktree_not_found',
            'message': f'Worktree path does not exist or is not a directory: {args.worktree_path}',
        }

    refs = read_references(args.plan_id)
    if not refs:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'references_not_found',
            'message': 'references.json not found',
        }

    rev_parse = _run_git(worktree, ['rev-parse', '--git-dir'])
    if rev_parse.returncode != 0:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'not_a_git_worktree',
            'message': f'Path is not inside a git worktree: {args.worktree_path}',
        }

    base_ref = resolve_base_ref(getattr(args, 'base_ref', None), refs, worktree)
    explicit = getattr(args, 'base_ref', None)
    if explicit is not None and str(explicit).strip():
        base_ref_source = 'explicit'
    elif base_ref.startswith('origin/') or base_ref.startswith('refs/remotes/origin/'):
        base_ref_source = 'upstream'
    else:
        base_ref_source = 'fallback'
    if not _ref_resolves_in_worktree(worktree, base_ref):
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'git_error',
            'message': f'Unresolvable base ref {base_ref!r} in worktree {worktree} (source={base_ref_source})',
            'base_ref': base_ref,
            'base_ref_source': base_ref_source,
        }
    try:
        live_set = compute_plan_branch_diff(worktree, base_ref)
    except subprocess.CalledProcessError as exc:
        return {
            'status': 'error',
            'plan_id': args.plan_id,
            'error': 'git_error',
            'message': f'Failed to compute plan branch diff: {exc}',
        }
    files = sorted(live_set)

    payload = {
        'status': 'success',
        'plan_id': args.plan_id,
        'base_ref': base_ref,
        'base_ref_source': base_ref_source,
        'files': files,
        'live_count': len(files),
    }

    files_out = getattr(args, 'files_out', None)
    if files_out:
        try:
            out_path = _write_footprint_files(args.plan_id, files_out, files)
        except ValueError as exc:
            # A refused destination is not a write failure: it is a request this
            # verb declines. It gets its own code so a caller can tell "you
            # asked for something I will not do" from "the disk said no".
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'files_out_refused',
                'message': str(exc),
            }
        except OSError as exc:
            return {
                'status': 'error',
                'plan_id': args.plan_id,
                'error': 'files_out_unwritable',
                'message': f'Failed to write the footprint to {files_out}: {exc}',
            }
        payload['files_out'] = str(out_path)
        payload['files_out_count'] = len(files)

    return payload


def _write_footprint_files(plan_id: str, files_out: str, files: list[str]) -> Path:
    """Write the footprint list to ``files_out`` atomically, refusing the plan record.

    Three properties, each closing a distinct way this write could betray its
    stated contract:

    * **It never replaces the plan record.** ``compute-footprint`` is read-only
      with respect to ``references.json``, and a caller naming that path as the
      export target would silently break the promise — the footprint would
      overwrite the plan's own state. The destination is compared against the
      real references path by *resolved* identity, not by string, so a
      differently-spelled or symlinked path is caught too.
    * **It is atomic.** The bytes go to a temporary sibling that is renamed into
      place, so a reader never observes a truncated list. A directly-written
      file that failed partway is still *readable* — and a partial footprint
      derives a narrower bundle set that reads as a clean gate, which is the
      false green this hand-off exists to eliminate. A same-directory temp keeps
      the rename on one filesystem, so it is a rename and not an interruptible
      copy.
    * **It creates the parent directory**, so the documented
      ``.plan/temp/{plan_id}-footprint.txt`` form needs no separate step.

    Args:
        plan_id: Owning plan id, used to resolve the references path to refuse.
        files_out: Caller-named destination path.
        files: The computed footprint, already sorted.

    Returns:
        The destination path that was written.

    Raises:
        ValueError: The destination resolves to the plan's ``references.json``.
        OSError: The destination could not be created or written.
    """
    out_path = Path(files_out).expanduser()
    if out_path.resolve() == get_references_path(plan_id).resolve():
        raise ValueError(
            f'Refusing to write the footprint over the plan record: {out_path} is '
            f"this plan's references.json. compute-footprint is read-only with "
            f'respect to it; choose a different --files-out path.'
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=out_path.parent,
        prefix=f'.{out_path.name}.',
        suffix='.tmp',
        delete=False,
    ) as handle:
        handle.write(''.join(f'{path}\n' for path in files))
        handle.flush()
        os.fsync(handle.fileno())
        tmp_path = Path(handle.name)
    try:
        os.replace(tmp_path, out_path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise
    return out_path


def cmd_capture_footprint(args: argparse.Namespace) -> dict:
    """Persist the realized plan footprint into references.json — deterministically.

    ``compute-footprint`` derives the live footprint from the worktree but never
    records it. That is the read-time-from-a-mutable-substrate defect the plan
    (R3) exists to close: once ``default:branch-cleanup`` removes the worktree the
    diff was computed against, an ARCHIVED-plan resolver has nothing live to read,
    and for a plan created after the change-ledger was removed the legacy
    ``references.modified_files`` key is absent too — so the archived footprint
    resolves to UNRESOLVED permanently.

    This verb is the **capture-while-true** side effect: it computes the identical
    live footprint and WRITES it under ``references.realized_footprint`` while the
    worktree still exists and the diff is still accurate. A later resolver prefers
    that recorded set over any re-derivation. ``default:branch-cleanup`` calls this
    once, before it removes the worktree.

    Idempotent: re-running overwrites the key with the current worktree state. The
    write reuses ``compute_plan_branch_diff`` through :func:`cmd_compute_footprint`,
    so the recorded set is byte-identical to what ``compute-footprint`` would
    return at the same instant — there is no second footprint definition to drift.
    """
    computed = cmd_compute_footprint(args)
    if computed.get('status') != 'success':
        # Propagate the compute error verbatim (worktree missing, not-a-git-worktree,
        # references-not-found, git-error) — the caller records nothing on failure and
        # the resolver falls to its next tier, never a fabricated empty capture.
        return computed

    files = computed['files']
    refs = read_references(args.plan_id)
    refs['realized_footprint'] = files
    write_references(args.plan_id, refs)

    return {
        'status': 'success',
        'plan_id': args.plan_id,
        'base_ref': computed['base_ref'],
        'base_ref_source': computed.get('base_ref_source', 'unknown'),
        'files': files,
        'realized_footprint_count': len(files),
        'persisted': True,
    }
