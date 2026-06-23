#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pre-commit verify-freshness command handler for manage-tasks.py.

Closes the necessary-vs-sufficient gap between ``loop-exit-guard``
(queue-empty proof) and the pre-push state (worktree-actually-verified
proof). The command answers a single deterministic question:

    Does the unified change-ledger contain a ``kind=build`` entry with
    ``exit_code == 0`` whose ``worktree_sha`` equals the CURRENT working-tree
    currency hash?

A ``kind=build`` entry is stamped by the executor dispatch boundary after every
build-class invocation, carrying the working-tree ``worktree_sha`` captured at
build time. The gate recomputes the current working-tree sha and looks for a
matching successful build entry. The query is build-tool-agnostic and
tier-agnostic: it filters on ``kind``, ``exit_code`` and ``worktree_sha`` only —
never ``notation`` or ``plan_id`` — so a Maven/Gradle/npm build, or an
orchestrator-driven global-tier build with ``plan_id: null``, satisfies the gate
exactly as a plan-scoped pyproject build does.

The primitive is the *working-tree* currency, NOT the committed ``HEAD``. This
is a pre-commit gate: at gate time the plan's edits are still uncommitted, so a
``git rev-parse HEAD`` primitive would match trivially regardless of any
uncommitted change between build and gate (a false-positive ``fresh``). The
working-tree sha folds in the staged + unstaged + untracked-not-ignored state,
so an uncommitted edit after a clean-tree build changes the sha and the gate
correctly reports ``stale``.

Outcomes:

- ``fresh`` / ``documentation_only`` — a documentation-only plan composes an
                     empty ``phase_5.verification_steps`` in its
                     ``execution.toon`` manifest, so it legitimately runs no
                     build and therefore stamps no ``kind=build`` ledger entry.
                     The gate short-circuits to ``status: fresh`` with
                     ``reason: documentation_only`` BEFORE the ledger scan: a
                     plan with no build step needs no freshness proof. This
                     branch fires only when the manifest is present AND its
                     ``phase_5.verification_steps`` list is empty; an absent
                     manifest or a non-empty step list falls through to the
                     ledger scan below.
- ``fresh`` / ``lint_only`` — a lint-only plan composes a non-empty
                     ``phase_5.verification_steps`` whose every entry is a
                     structural-lint (``quality-gate``) step and none is a
                     build/test step. Structural lint never stamps a
                     ``kind=build`` ledger entry, so — exactly like a
                     documentation-only plan — the plan legitimately runs no
                     build and needs no freshness proof. The gate short-circuits
                     to ``status: fresh`` with ``reason: lint_only`` BEFORE the
                     ledger scan. The predicate classifies each step by the
                     trailing ``:``-segment of its ID (so ``verify:quality-gate``
                     and ``default:verify:quality-gate`` both resolve to
                     ``quality-gate``) and fires only when the list is non-empty,
                     every step resolves to ``quality-gate``, and NO step
                     resolves to a build/test role (``module-tests``,
                     ``coverage``, or the bare ``verify`` alias). Any build/test
                     step in the list disables the exemption and the plan falls
                     through to the ledger scan below.
- ``fresh``        — a ``kind=build`` entry with ``exit_code == 0`` and a
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

from _ledger_core import (  # type: ignore[import-not-found]
    KIND_BUILD,
    read_entries,
    resolve_ledger_path,
)
from _tasks_core import get_plan_dir  # type: ignore[import-not-found]
from constants import FILE_STATUS  # type: ignore[import-not-found]
from file_ops import read_json  # type: ignore[import-not-found]
from toon_parser import parse_toon  # type: ignore[import-not-found]
from worktree_sha import compute_worktree_sha  # type: ignore[import-not-found]

# The per-plan execution manifest lives alongside status.json at
# .plan/local/plans/{plan_id}/execution.toon. Its name is owned by
# manage-execution-manifest (MANIFEST_FILENAME); duplicated here as a literal
# to keep this command inside the manage-tasks sys.path island.
_MANIFEST_FILENAME = 'execution.toon'

# Structural-lint role(s) — the phase-5 verification roles that run static
# analysis only and never stamp a kind=build ledger entry. Classified by the
# trailing ':'-segment of a step ID, so 'verify:quality-gate' and
# 'default:verify:quality-gate' both resolve to 'quality-gate'. A step whose
# role is NOT in this set (e.g. 'module-tests', 'coverage', or the bare
# 'verify' alias) is a build/test step and disables the lint-only exemption.
_LINT_ONLY_ROLES = frozenset({'quality-gate'})


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


def _is_documentation_only(plan_id: str) -> bool:
    """Return True when the plan's execution manifest declares no phase-5 build.

    A documentation-only plan composes an empty ``phase_5.verification_steps``
    list in its ``execution.toon`` manifest and therefore never stamps a
    ``kind=build`` ledger entry. The freshness gate must exempt such plans
    rather than fail closed on the missing build proof.

    Reads ``execution.toon`` via ``_read_verification_steps`` (the shared
    plan-dir resolution + TOON parse inside the manage-tasks sys.path island).
    Returns ``False`` (no exemption — fall through to the ledger scan) when the
    manifest is absent, unreadable, or when ``phase_5.verification_steps`` is
    present and non-empty. Returns ``True`` only when the manifest parses AND
    its ``phase_5.verification_steps`` is an empty list.
    """
    verification_steps = _read_verification_steps(plan_id)
    return verification_steps is not None and len(verification_steps) == 0


def _read_verification_steps(plan_id: str) -> list | None:
    """Return the plan's ``phase_5.verification_steps`` list, or ``None``.

    Reads ``execution.toon`` directly via the same plan-dir resolution
    ``_is_documentation_only`` uses, parsing TOON to stay inside the
    manage-tasks sys.path island. Returns ``None`` (signalling no usable
    manifest) when the manifest is absent, unreadable, malformed, or when
    ``phase_5.verification_steps`` is not a list. Returns the list verbatim
    otherwise (which MAY be empty).
    """
    manifest_path = get_plan_dir(plan_id) / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None
    try:
        manifest = parse_toon(manifest_path.read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001 — degrade to no-manifest on any parse error
        return None
    if not isinstance(manifest, dict):
        return None
    phase_5 = manifest.get('phase_5', {})
    if not isinstance(phase_5, dict):
        return None
    verification_steps = phase_5.get('verification_steps', None)
    if not isinstance(verification_steps, list):
        return None
    return verification_steps


def _is_lint_only(plan_id: str) -> bool:
    """Return True when every phase-5 step is structural lint and none builds.

    A lint-only plan composes a non-empty ``phase_5.verification_steps`` whose
    every entry resolves to a structural-lint role (``quality-gate``) and none
    resolves to a build/test role. Structural lint never stamps a
    ``kind=build`` ledger entry, so — like a documentation-only plan — such a
    plan legitimately runs no build and needs no freshness proof.

    Step IDs are role-suffixed and optionally ``default:``-prefixed, e.g.
    ``verify:quality-gate`` and ``default:verify:quality-gate`` both resolve to
    ``quality-gate`` via the trailing ``:``-segment. A bare step ID with no
    ``:`` resolves to itself.

    Mirrors ``_is_documentation_only``'s manifest-read discipline: reads
    ``execution.toon`` inside the manage-tasks sys.path island and degrades to
    ``False`` (no exemption — fall through to the ledger scan) on any
    parse/shape error. Returns ``True`` only when the step list is non-empty,
    every step's role is in ``_LINT_ONLY_ROLES``, and no step carries a
    build/test role. Any non-lint step (``module-tests``, ``coverage``, the
    bare ``verify`` alias) disables the exemption.
    """
    verification_steps = _read_verification_steps(plan_id)
    if not verification_steps:
        return False
    return all(
        isinstance(step, str) and step.rsplit(':', 1)[-1] in _LINT_ONLY_ROLES
        for step in verification_steps
    )


def cmd_pre_commit_verify_freshness(args) -> dict:
    """Handle ``pre-commit-verify-freshness`` subcommand.

    See module docstring for the contract; the algorithm is laid out in
    deliverable 4 of the plan ``solution_outline.md``.
    """
    plan_id: str = args.plan_id

    # Documentation-only short-circuit: a docs-only plan composes an empty
    # phase_5.verification_steps and therefore never stamps a kind=build ledger
    # entry. It needs no freshness proof, so exempt it BEFORE the ledger scan
    # rather than fail closed on the missing build. Fires only when the manifest
    # is present AND phase_5.verification_steps is empty; an absent manifest or a
    # non-empty step list falls through to the ledger scan unchanged.
    if _is_documentation_only(plan_id):
        return {
            'status': 'fresh',
            'plan_id': plan_id,
            'reason': 'documentation_only',
            'message': (
                'Plan composes an empty phase_5.verification_steps '
                '(documentation-only); no build step runs, so no freshness '
                'proof is required. Gate permitted without a ledger scan.'
            ),
        }

    # Lint-only short-circuit: a plan whose phase_5.verification_steps are all
    # structural-lint (quality-gate) steps runs no build and therefore stamps no
    # kind=build ledger entry — exactly like a documentation-only plan. Exempt it
    # BEFORE the ledger scan with reason: lint_only. Fires only when the list is
    # non-empty and every step is a quality-gate step; any build/test step
    # (module-tests, coverage, the bare verify alias) disables the exemption and
    # falls through to the ledger scan below.
    if _is_lint_only(plan_id):
        return {
            'status': 'fresh',
            'plan_id': plan_id,
            'reason': 'lint_only',
            'message': (
                'Plan composes a phase_5.verification_steps of structural lint '
                '(quality-gate) only; no build step runs, so no freshness proof '
                'is required. Gate permitted without a ledger scan.'
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
    # working-tree sha. The query filters on kind, exit_code and worktree_sha
    # only — never notation or plan_id — so it is build-tool-agnostic and
    # tier-agnostic.
    for entry in entries:
        if (
            entry.get('kind') == KIND_BUILD
            and entry.get('exit_code') == 0
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
