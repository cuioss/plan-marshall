# SPDX-License-Identifier: FSL-1.1-ALv2
"""Two-state ``--plan-id`` / ``--project-dir`` resolution helper.

Every Bucket B (worktree-scoped) script that historically accepted
``--project-dir`` must also accept ``--plan-id`` and auto-resolve the
worktree path. This module implements the canonical routing contract so
consumer scripts share a single implementation instead of one copy each.

The worktree face itself is NOT resolved here — it is delegated to
``file_ops.resolve_plan_context``, which owns the single
``manage-status get-worktree-path`` invocation in the codebase. This
module is the argv/flag layer on top of that resolver.

Two-state contract (per script):

* ``--plan-id X`` AND ``--project-dir Y`` — error
  ``mutually_exclusive_args``. The caller must pick exactly one routing
  source.
* ``--plan-id X`` only — resolve via ``manage-status get-worktree-path``.
  When ``use_worktree`` is true, return the persisted ``worktree_path``.
  When ``use_worktree`` is false (or metadata absent), fall back to the
  plan root resolved cwd-relatively (the nearest ancestor of cwd
  containing ``.plan/local``; ADR-002 uniform cwd rule).
* ``--plan-id NO_PLAN`` — the plan-less sentinel is NOT a routing source.
  It resolves exactly like the neither-flag branch (the main-checkout
  root, with no ``get-worktree-path`` lookup) and it is not counted as
  "supplied" for the mutual-exclusion check, so
  ``--plan-id NO_PLAN --project-dir Y`` stays legal and yields ``Y``.
  This is what keeps the sentinel a routing/ledger VALUE rather than a
  plan-directory selector.
* ``--project-dir Y`` only — return ``Y`` verbatim. Legacy / escape
  hatch — preserved for callers that need an explicit path (test
  fixtures, ad-hoc invocations from outside any plan).
* Neither — return the main-checkout root.

All branches return an absolute filesystem path (string). Callers should
use the return value as the working tree root for subprocesses, file
reads, and project-relative path resolution.

See ``plan-marshall:tools-script-executor/standards/cwd-policy.md`` for
the authoritative Bucket A/B split and the rationale for explicit
routing in worktree-isolated plans.
"""

from __future__ import annotations

import json
import os
import sys

from file_ops import (
    WorktreeResolutionError,
    cwd_checkout_root,
    resolve_plan_context,
)
from marketplace_paths import names_real_plan


class MutuallyExclusiveArgsError(ValueError):
    """Raised when a caller supplies both ``--plan-id`` and ``--project-dir``.

    The two flags are routing sources; supplying both creates ambiguity
    about which path wins. Scripts should catch this and emit a TOON
    ``status: error`` / ``error: mutually_exclusive_args`` payload rather
    than letting the exception propagate.
    """


def resolve_project_dir(
    plan_id: str | None,
    project_dir: str | None,
    *,
    default: str | None = None,
) -> str:
    """Resolve the working-tree root from (``plan_id``, ``project_dir``).

    Implements the four-state contract documented at module top.

    Args:
        plan_id: Optional plan identifier. When set to a REAL plan id the
            worktree path is looked up via ``manage-status
            get-worktree-path``. The ``NO_PLAN`` sentinel is treated as
            absent — it is not a routing source, so it neither triggers
            the lookup nor participates in the mutual-exclusion check.
        project_dir: Optional explicit project directory override.
            Returned verbatim when set (and ``plan_id`` is not a real
            plan id).
        default: Sentinel used by argparse to detect "user did not pass
            ``--project-dir``". When ``project_dir`` equals ``default``,
            the value is treated as absent. Pass the same default the
            argparse parser uses (typically ``'.'``) so the
            both-supplied error only fires when the caller explicitly
            opted into both flags.

    Returns:
        Absolute path string for the resolved project root.

    Raises:
        MutuallyExclusiveArgsError: when both ``plan_id`` and a
            non-default ``project_dir`` are set.
        WorktreeResolutionError: when ``plan_id`` resolution fails
            (manage-status error, missing worktree metadata, etc.).
    """
    project_dir_supplied = project_dir is not None and project_dir != default
    # The sentinel is excluded HERE rather than only inside the branch below:
    # counting it as "supplied" would (a) make ``--plan-id NO_PLAN
    # --project-dir Y`` a spurious mutual-exclusion error and (b) hand the
    # sentinel to the worktree resolver as if it named a plan.
    plan_id_supplied = names_real_plan(plan_id)

    if plan_id_supplied and project_dir_supplied:
        raise MutuallyExclusiveArgsError(
            "Both --plan-id and --project-dir were supplied. Pick exactly one: "
            '--plan-id auto-resolves the worktree path; --project-dir is the explicit override.'
        )

    if plan_id_supplied:
        assert plan_id is not None  # for mypy
        # Delegate the worktree face to the consolidated resolver so
        # ``manage-status get-worktree-path`` is invoked from exactly one
        # place. ``ensure=False`` keeps this a routing lookup: resolving a
        # working tree must not materialize or existence-check the plan.
        return resolve_plan_context(plan_id, ensure=False).worktree_path

    if project_dir_supplied:
        assert project_dir is not None  # for mypy
        return os.path.abspath(project_dir)

    return cwd_checkout_root()


def add_plan_id_arg(parser, *, help_text: str | None = None) -> None:
    """Attach the standard ``--plan-id`` argument to a parser.

    Pairs with ``--project-dir`` to expose the two-state contract on
    every Bucket B script. Default is ``None`` so callers can detect
    whether the flag was explicitly supplied.

    Args:
        parser: ``argparse.ArgumentParser`` or subparser to extend.
        help_text: Optional override for the flag's help string.
    """
    parser.add_argument(
        '--plan-id',
        dest='plan_id',
        default=None,
        help=help_text
        or (
            'Plan identifier — when set, the project directory is resolved via '
            'manage-status get-worktree-path. Mutually exclusive with --project-dir.'
        ),
    )


def resolve_from_args(args, *, default: str = '.') -> str:
    """Convenience wrapper: resolve from an argparse Namespace.

    Reads ``args.plan_id`` and ``args.project_dir`` (both optional) and
    returns the resolved absolute path. Use when the namespace already
    carries both attributes; pass the same ``default`` the parser used
    so the both-supplied check only fires for explicit double-routing.
    """
    plan_id = getattr(args, 'plan_id', None)
    project_dir = getattr(args, 'project_dir', None)
    return resolve_project_dir(plan_id, project_dir, default=default)


def extract_plan_id(argv: list[str]) -> tuple[str | None, list[str]]:
    """Strip an optional top-level ``--plan-id ID`` flag from *argv*.

    Mirrors :func:`ci_base.extract_project_dir` so the CI router and
    provider front-ends can pre-parse ``--plan-id`` without forcing
    every downstream argparse layer to know about the flag.

    Returns:
        ``(plan_id_or_none, remaining_argv)``. Supports both
        ``--plan-id ID`` and ``--plan-id=ID`` forms. Only the first
        occurrence is consumed.
    """
    plan_id: str | None = None
    out: list[str] = []
    consumed = False
    i = 0
    while i < len(argv):
        token = argv[i]
        if not consumed and token == '--plan-id':
            if i + 1 >= len(argv):
                print('Error: --plan-id requires an ID argument', file=sys.stderr)
                sys.exit(2)
            plan_id = argv[i + 1]
            consumed = True
            i += 2
            continue
        if not consumed and token.startswith('--plan-id='):
            plan_id = token.split('=', 1)[1]
            if not plan_id:
                print('Error: --plan-id requires a non-empty ID', file=sys.stderr)
                sys.exit(2)
            consumed = True
            i += 1
            continue
        out.append(token)
        i += 1
    return plan_id, out


def emit_mutually_exclusive_error(plan_id: str | None, project_dir: str | None) -> dict:
    """Build the canonical TOON-friendly error payload for the both-supplied case.

    Centralised so every consumer emits the same shape regardless of
    whether it speaks TOON, JSON, or a mixed format. Callers are
    responsible for serialising and printing.
    """
    # The values are echoed back to make debugging easier without
    # disclosing anything sensitive (plan ids are not secrets).
    return {
        'status': 'error',
        'error': 'mutually_exclusive_args',
        'message': (
            "--plan-id and --project-dir are mutually exclusive. "
            'Pick one: --plan-id auto-resolves via manage-status; --project-dir is the explicit override.'
        ),
        'plan_id': plan_id,
        'project_dir': project_dir,
    }


def emit_worktree_error(plan_id: str, exc: WorktreeResolutionError) -> dict:
    """Build the canonical error payload for ``--plan-id`` resolution failures."""
    return {
        'status': 'error',
        'error': 'worktree_resolution_failed',
        'message': str(exc),
        'plan_id': plan_id,
    }


# Re-export json for callers that need to serialise the error payloads
# without pulling in another import. Kept at module bottom so the
# import-graph stays clean.
__all__ = [
    'MutuallyExclusiveArgsError',
    'WorktreeResolutionError',
    'add_plan_id_arg',
    'emit_mutually_exclusive_error',
    'emit_worktree_error',
    'extract_plan_id',
    'resolve_from_args',
    'resolve_project_dir',
]

# Ensure ``json`` is imported eagerly so callers using the helper from a
# constrained PYTHONPATH do not need a separate import line. The symbol
# is intentionally not part of ``__all__`` — re-exporting it would
# muddle the public surface.
_ = json
