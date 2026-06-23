#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unified change-ledger CLI — the first-class worktree-sha + append + query API.

Notation: ``plan-marshall:manage-change-ledger:manage-change-ledger``

This standalone script is the executor-callable surface over the one append-only
change-ledger (``.plan/work/change-ledger.jsonl``) and its ``worktree_sha``
primitive. It exposes three verbs on the shared deterministic core
(``_ledger_core.py``) and the shared hash helper (``worktree_sha.py``):

  * ``worktree-sha`` — the FIRST-CLASS reusable freshness API. Computes the
    current working-tree currency hash for ``--worktree-root`` (defaults to cwd)
    via the single shared ``compute_worktree_sha`` helper. Any caller anywhere a
    freshness question arises asks "what is the current worktree state hash"
    through this verb, without re-implementing the hash or reaching into a
    private gate helper.
  * ``append`` — the SOLE write path. ``--kind {build|change}`` selects the
    entry shape; the verb stamps ``kind``, ``worktree_sha``, ``timestamp_iso``
    and the kind-specific fields via the core constructors, then appends exactly
    one JSONL line (pure-append). For ``change`` entries, ``--commit-sha`` and
    ``--changed-paths`` are stored VERBATIM — the verb does NOT compute changed
    paths (git-sourcing is the caller's contract).
  * ``query`` — read the ledger (optional ``--kind`` / ``--exit-code`` filters),
    printing the matching entries as TOON. For inspection and tests; the
    freshness gate imports ``read_entries`` directly rather than shelling here.

The ledger resolves under the tracked-config dir (``get_tracked_config_dir()``),
NOT plan-scoped, so plan-less orchestrator builds are covered. ``compute_worktree_sha``
lives once in ``script-shared`` and is the sole implementation imported by this
verb, the executor ``kind=build`` writer, and the gate.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from typing import Any

from _ledger_core import (  # type: ignore[import-not-found]
    KIND_BUILD,
    KIND_CHANGE,
    append_entry,
    build_record,
    change_record,
    read_entries,
    resolve_ledger_path,
)
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    create_workflow_cli,
    make_error,
    print_toon,
    safe_main,
)
from worktree_sha import compute_worktree_sha  # type: ignore[import-not-found]


def _split_changed_paths(raw: str | None) -> list[str]:
    """Split a comma-separated ``--changed-paths`` value into a clean list.

    Empty / whitespace-only segments are dropped; surrounding whitespace is
    trimmed. The verb stores the result verbatim (the caller already git-sourced
    the paths).
    """
    if not raw:
        return []
    return [seg.strip() for seg in raw.split(',') if seg.strip()]


def run_worktree_sha(args: Namespace) -> dict[str, Any]:
    """``worktree-sha`` — print the current working-tree currency hash."""
    worktree_root = args.worktree_root or '.'
    sha = compute_worktree_sha(worktree_root)
    if sha is None:
        return make_error(
            f'cannot resolve HEAD in {worktree_root}; working-tree sha is undefined',
            code='head_unresolvable',
            worktree_root=str(worktree_root),
        )
    return {
        'status': 'success',
        'worktree_sha': sha,
        'worktree_root': str(worktree_root),
    }


def run_append(args: Namespace) -> dict[str, Any]:
    """``append`` — append one ``kind=build`` or ``kind=change`` ledger entry."""
    worktree_root = args.worktree_root or '.'
    worktree_sha = args.worktree_sha if args.worktree_sha else compute_worktree_sha(worktree_root)

    if args.kind == KIND_BUILD:
        if not args.notation:
            return make_error(
                '--notation is required for --kind build',
                code=ErrorCode.INVALID_INPUT,
            )
        if args.exit_code is None:
            return make_error(
                '--exit-code is required for --kind build',
                code=ErrorCode.INVALID_INPUT,
            )
        record = build_record(
            notation=args.notation,
            plan_id=args.plan_id,
            args=args.args,
            exit_code=args.exit_code,
            worktree_sha=worktree_sha,
            log_file=args.log_file,
        )
    else:  # KIND_CHANGE
        deliverable_id = args.deliverable_id or args.task_id
        if not deliverable_id:
            return make_error(
                'one of --deliverable-id / --task-id is required for --kind change',
                code=ErrorCode.INVALID_INPUT,
            )
        if not args.commit_sha:
            return make_error(
                '--commit-sha is required for --kind change',
                code=ErrorCode.INVALID_INPUT,
            )
        record = change_record(
            deliverable_id=deliverable_id,
            worktree_sha=worktree_sha,
            commit_sha=args.commit_sha,
            changed_paths=_split_changed_paths(args.changed_paths),
        )

    append_entry(record)
    return {
        'status': 'success',
        'kind': args.kind,
        'worktree_sha': worktree_sha,
        'ledger_path': str(resolve_ledger_path()),
    }


def run_query(args: Namespace) -> dict[str, Any]:
    """``query`` — read the ledger with optional ``--kind`` / ``--exit-code`` filters."""
    entries = read_entries()
    if args.kind:
        entries = [e for e in entries if e.get('kind') == args.kind]
    if args.exit_code is not None:
        entries = [e for e in entries if e.get('exit_code') == args.exit_code]
    return {
        'status': 'success',
        'count': len(entries),
        'ledger_path': str(resolve_ledger_path()),
        'entries': entries,
    }


def main() -> int:
    """Entry point — ``worktree-sha`` / ``append`` / ``query`` verbs."""
    parser = create_workflow_cli(
        description='Unified change-ledger: first-class worktree-sha API + append + query',
        epilog="""
Examples:
  manage-change-ledger.py worktree-sha [--worktree-root PATH]
  manage-change-ledger.py append --kind build --notation NOTATION --exit-code 0 [--plan-id ID] [--log-file PATH]
  manage-change-ledger.py append --kind change --deliverable-id 2 --commit-sha SHA --changed-paths a,b,c
  manage-change-ledger.py query [--kind build|change] [--exit-code 0]
""",
        subcommands=[
            {
                'name': 'worktree-sha',
                'help': 'Print the current working-tree currency hash (first-class freshness API)',
                'handler': run_worktree_sha,
                'args': [
                    {
                        'flags': ['--worktree-root'],
                        'dest': 'worktree_root',
                        'help': 'Working-tree root to hash (default: cwd)',
                    },
                ],
            },
            {
                'name': 'append',
                'help': 'Append one kind=build or kind=change ledger entry (pure-append)',
                'handler': run_append,
                'args': [
                    {
                        'flags': ['--kind'],
                        'dest': 'kind',
                        'required': True,
                        'choices': [KIND_BUILD, KIND_CHANGE],
                        'help': 'Entry discriminator: build (executor) or change (phase-5)',
                    },
                    {
                        'flags': ['--worktree-root'],
                        'dest': 'worktree_root',
                        'help': 'Working-tree root to hash when --worktree-sha is omitted (default: cwd)',
                    },
                    {
                        'flags': ['--worktree-sha'],
                        'dest': 'worktree_sha',
                        'help': 'Pre-computed worktree_sha (skips recomputation when the caller already has it)',
                    },
                    {
                        'flags': ['--notation'],
                        'dest': 'notation',
                        'help': 'build: the build-class notation that was dispatched',
                    },
                    {
                        'flags': ['--plan-id'],
                        'dest': 'plan_id',
                        'help': 'build: the plan_id (nullable — omit for an orchestrator global-tier build)',
                    },
                    {
                        'flags': ['--args'],
                        'dest': 'args',
                        'help': 'build: the dispatched command args (free-form)',
                    },
                    {
                        'flags': ['--exit-code'],
                        'dest': 'exit_code',
                        'type': int,
                        'help': 'build: the build exit code (recorded even when non-zero)',
                    },
                    {
                        'flags': ['--log-file'],
                        'dest': 'log_file',
                        'help': 'build: the build log path',
                    },
                    {
                        'flags': ['--deliverable-id'],
                        'dest': 'deliverable_id',
                        'help': 'change: the completed deliverable id',
                    },
                    {
                        'flags': ['--task-id'],
                        'dest': 'task_id',
                        'help': 'change: the completed task id (alternative to --deliverable-id)',
                    },
                    {
                        'flags': ['--commit-sha'],
                        'dest': 'commit_sha',
                        'help': 'change: the git commit sha the deliverable produced',
                    },
                    {
                        'flags': ['--changed-paths'],
                        'dest': 'changed_paths',
                        'help': 'change: comma-separated git-sourced changed paths (stored verbatim)',
                    },
                ],
            },
            {
                'name': 'query',
                'help': 'Read the ledger with optional --kind / --exit-code filters',
                'handler': run_query,
                'args': [
                    {
                        'flags': ['--kind'],
                        'dest': 'kind',
                        'choices': [KIND_BUILD, KIND_CHANGE],
                        'help': 'Filter to entries of this kind',
                    },
                    {
                        'flags': ['--exit-code'],
                        'dest': 'exit_code',
                        'type': int,
                        'help': 'Filter to entries with this exit_code',
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    return print_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
