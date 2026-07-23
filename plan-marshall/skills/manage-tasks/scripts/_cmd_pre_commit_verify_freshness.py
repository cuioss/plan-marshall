#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-commit verify-freshness command handler for manage-tasks.py.

Closes the necessary-vs-sufficient gap between ``loop-exit-guard``
(queue-empty proof) and the pre-push state (worktree-actually-verified
proof). The command answers a single deterministic question:

    Does the unified change-ledger contain a ``kind=build`` entry with
    ``status == 'success'`` whose ``worktree_sha`` equals the CURRENT
    working-tree currency hash?

That question is only worth asking when a build was necessary in the first
place. Build necessity is NOT re-derived here: the gate consults the single
build/no-build authority (``extension_base.should_execute_build``, the
``manage-config build-decision`` verb) with NO canonical command — it asks the
plan-wide "does anything in this footprint need a build?" question and MUST NOT
pick a representative command. A ``not_necessary`` verdict returns ``fresh``
carrying the verdict's own ``reason`` verbatim, so the gate never invents a
reason vocabulary of its own; a ``build`` verdict falls through to the ledger
scan below unchanged. See ADR-004 § "Amendment: ``build-decision`` is the sole
build/no-build authority".

A ``kind=build`` entry is stamped by the executor dispatch boundary after every
build-class invocation, carrying the truthful build ``status`` (``success`` /
``error`` / ``timeout`` / ``killed``) and the working-tree ``worktree_sha``
captured at build time. The gate recomputes the current working-tree sha and
looks for a matching successful build entry. Matching on ``status`` rather than
``exit_code`` is load-bearing: the build wrapper exits 0 on timeout (the
outcome is modeled in its stdout TOON, not the exit code), so an ``exit_code``
predicate would launder a build that never finished into a false ``fresh``.
A row lacking ``status`` never matches — the gate fails closed to ``stale``.
The query is build-tool-agnostic and tier-agnostic: it filters on ``kind``,
``status`` and ``worktree_sha`` only — never ``notation`` or ``plan_id`` — so a
Maven/Gradle/npm build, or an orchestrator-driven global-tier build with
``plan_id: null``, satisfies the gate exactly as a plan-scoped pyproject build
does.

The primitive is the *working-tree* currency, NOT the committed ``HEAD``. This
is a pre-commit gate: at gate time the plan's edits are still uncommitted, so a
``git rev-parse HEAD`` primitive would match trivially regardless of any
uncommitted change between build and gate (a false-positive ``fresh``). The
working-tree sha folds in the staged + unstaged + untracked-not-ignored state,
so an uncommitted edit after a clean-tree build changes the sha and the gate
correctly reports ``stale``.

Outcomes:

- ``fresh`` (+ the verdict's ``reason``) — the build-decision verdict is
                     ``not_necessary``: no build was ever required for this
                     footprint, so no ``kind=build`` entry could legally exist
                     and none is demanded. The short-circuit fires BEFORE the
                     ledger scan and forwards the authority's own reason text.
- ``fresh``        — a ``kind=build`` entry with ``status == 'success'`` and a
                     matching ``worktree_sha`` exists; a successful build has
                     been observed against the current on-disk state, so the
                     gate is permitted to pass.
- ``stale``        — the ledger has entries but none is a successful build
                     against the current working-tree sha; the worktree has been
                     mutated since the last observed build, so the gate MUST fail
                     closed.
- ``undecidable``  — no positive freshness proof can be established. Two
                     sub-reasons: ``no_registry`` (the ledger file is absent or
                     empty) and ``head_unresolvable`` (the working-tree sha
                     cannot be computed — a non-git directory or a repo with no
                     commit). The gate MUST fail closed in both cases.

The full failure-mode contract — including the ``--force`` orchestrator
escape and the cross-references to phase-5-execute Step 12a and
phase-6-finalize ``push`` — is documented in
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness".
"""

from pathlib import Path

from _ledger_core import (
    KIND_BUILD,
    read_entries,
    resolve_ledger_path,
)
from _tasks_core import get_plan_dir
from constants import FILE_STATUS
from file_ops import read_json
from worktree_sha import compute_worktree_sha


def _read_status_metadata(plan_id: str) -> dict:
    """Read ``status.json`` for the plan and return its ``metadata`` dict.

    Reads the plan-scoped status file directly via ``file_ops.read_json``
    rather than dispatching through ``manage-status`` to keep this command
    inside the manage-tasks sys.path island. Returns an empty dict on any
    read/parse error so the caller can degrade to the cwd fallback.
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.is_file():
        return {}
    try:
        status = read_json(status_path)
    except Exception:  # noqa: BLE001 — degrade to empty metadata on any error
        return {}
    if not isinstance(status, dict):
        return {}
    metadata = status.get('metadata', {})
    if not isinstance(metadata, dict):
        return {}
    return metadata


def _resolve_worktree_root(plan_id: str) -> Path:
    """Resolve the worktree root for the plan.

    Reads ``status.metadata.worktree_path`` and falls back to the current
    working directory when no worktree is materialised. The fallback is
    intentional: a plan that runs against the main checkout still needs a
    freshness gate, and the main checkout is reachable from cwd.
    """
    metadata = _read_status_metadata(plan_id)
    worktree_path = metadata.get('worktree_path', '')
    if isinstance(worktree_path, str) and worktree_path:
        candidate = Path(worktree_path)
        if candidate.is_dir():
            return candidate
    return Path.cwd()


def _build_necessity_verdict(plan_id: str) -> dict:
    """Return the COMMAND-FREE build-necessity verdict for ``plan_id``.

    Delegates to the single authority with ``canonical_command=None``: this gate
    asks whether ANY build was needed for the plan's live footprint, which is a
    plan-wide question, so it passes no command and MUST NOT choose a
    representative one. The returned dict carries ``decision`` and — on
    ``not_necessary`` — the authority's own ``reason``, which the caller forwards
    verbatim rather than inventing an exemption vocabulary.

    The import is in-function so this command module keeps no hard top-level
    dependency on another skill's scripts dir (the same discipline the
    ``manage-config`` build-decision wrapper uses). A verdict that cannot be
    obtained degrades to ``build``, which routes the caller into the ledger scan
    — the fail-closed direction.
    """
    try:
        from extension_base import should_execute_build

        verdict = should_execute_build(None, plan_id)
    except Exception:  # noqa: BLE001 — an unobtainable verdict must fail closed
        return {'decision': 'build'}
    if not isinstance(verdict, dict):
        return {'decision': 'build'}
    return verdict


def cmd_pre_commit_verify_freshness(args) -> dict:
    """Handle ``pre-commit-verify-freshness`` subcommand.

    See module docstring for the contract; the algorithm is laid out in
    deliverable 4 of the plan ``solution_outline.md``.
    """
    plan_id: str = args.plan_id

    # Build-necessity short-circuit: when the single authority rules that this
    # footprint needs no build, no kind=build ledger entry could ever legally be
    # stamped for it, so demanding one is an impossible demand rather than a
    # gate. Exempt BEFORE the ledger scan and forward the verdict's own reason.
    verdict = _build_necessity_verdict(plan_id)
    if verdict.get('decision') == 'not_necessary':
        return {
            'status': 'fresh',
            'plan_id': plan_id,
            'reason': verdict.get('reason', ''),
            'message': (
                'build-decision ruled a build not_necessary for this footprint, so no '
                'kind=build entry can exist and none is required. Gate permitted without '
                'a ledger scan.'
            ),
        }

    worktree_root = _resolve_worktree_root(plan_id)
    current_sha = compute_worktree_sha(worktree_root)

    if current_sha is None:
        return {
            'status': 'undecidable',
            'plan_id': plan_id,
            'reason': 'head_unresolvable',
            'worktree_root': str(worktree_root),
            'message': (
                f'Working-tree currency hash is undefined for {worktree_root} '
                f'(HEAD unresolvable — non-git directory or a repo with no '
                f'commit). No positive freshness proof exists; gate MUST fail '
                f'closed.'
            ),
        }

    ledger_path = resolve_ledger_path()
    entries = read_entries(ledger_path)

    if not entries:
        return {
            'status': 'undecidable',
            'plan_id': plan_id,
            'reason': 'no_registry',
            'worktree_sha': current_sha,
            'worktree_root': str(worktree_root),
            'ledger_path': str(ledger_path),
            'message': (
                f'Change-ledger is absent or empty ({ledger_path}). No '
                f'kind=build entry exists to prove freshness; gate MUST fail '
                f'closed.'
            ),
        }

    # Scan for any successful build entry stamped against the current
    # working-tree sha. The query filters on kind, status and worktree_sha
    # only — never notation or plan_id — so it is build-tool-agnostic and
    # tier-agnostic. Requiring status == 'success' (not exit_code == 0) is
    # what closes the false-fresh hole: a timed-out build exits 0 but stamps
    # status: timeout, and a row lacking status never matches (fail-closed).
    for entry in entries:
        if (
            entry.get('kind') == KIND_BUILD
            and entry.get('status') == 'success'
            and entry.get('worktree_sha') == current_sha
        ):
            return {
                'status': 'fresh',
                'plan_id': plan_id,
                'worktree_sha': current_sha,
                'matched_notation': entry.get('notation', ''),
                'timestamp_iso': entry.get('timestamp_iso', ''),
                'worktree_root': str(worktree_root),
                'ledger_path': str(ledger_path),
                'message': (
                    f'A successful kind=build entry matches the current '
                    f'working-tree sha ({current_sha}). Gate permitted.'
                ),
            }

    return {
        'status': 'stale',
        'plan_id': plan_id,
        'worktree_sha': current_sha,
        'worktree_root': str(worktree_root),
        'ledger_path': str(ledger_path),
        'message': (
            f'No successful kind=build entry matches the current working-tree '
            f'sha ({current_sha}); the worktree has been mutated since the last '
            f'observed build. Gate MUST fail closed; re-dispatch a build before '
            f'retrying.'
        ),
    }
