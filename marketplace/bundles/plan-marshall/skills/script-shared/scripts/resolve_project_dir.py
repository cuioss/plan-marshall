"""Two-state ``--plan-id`` / ``--project-dir`` resolution helper.

Every Bucket B (worktree-scoped) script that historically accepted
``--project-dir`` must also accept ``--plan-id`` and auto-resolve the
worktree path through ``manage-status get-worktree-path``. This module
implements the canonical contract so the 27 consumer scripts share a
single implementation instead of 27 copies.

Two-state contract (per script):

* ``--plan-id X`` AND ``--project-dir Y`` — error
  ``mutually_exclusive_args``. The caller must pick exactly one routing
  source.
* ``--plan-id X`` only — resolve via ``manage-status get-worktree-path``.
  When ``use_worktree`` is true, return the persisted ``worktree_path``.
  When ``use_worktree`` is false (or metadata absent), fall back to the
  plan root resolved cwd-relatively (the nearest ancestor of cwd
  containing ``.plan/local``; ADR-002 uniform cwd rule).
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
import subprocess
import sys
from pathlib import Path

from file_ops import get_executor_path  # type: ignore[import-not-found]
from marketplace_paths import _find_plan_root_from_cwd  # type: ignore[import-not-found]


class MutuallyExclusiveArgsError(ValueError):
    """Raised when a caller supplies both ``--plan-id`` and ``--project-dir``.

    The two flags are routing sources; supplying both creates ambiguity
    about which path wins. Scripts should catch this and emit a TOON
    ``status: error`` / ``error: mutually_exclusive_args`` payload rather
    than letting the exception propagate.
    """


class WorktreeResolutionError(RuntimeError):
    """Raised when ``--plan-id`` resolution fails.

    Indicates that ``manage-status get-worktree-path`` returned an error
    payload (e.g., ``worktree_unresolved``) — the metadata is corrupt or
    the plan was created without seeding worktree state. The caller
    should surface the underlying message verbatim.
    """


def _executor_path() -> Path:
    """Locate ``.plan/execute-script.py`` relative to the main checkout.

    Delegates to ``file_ops.get_executor_path()``, which resolves the executor
    cwd-relatively via the uniform cwd rule (ADR-002) — worktree-resident during
    phase-5+, main during the finalize regenerate-on-main path.
    """
    try:
        return get_executor_path()
    except RuntimeError as exc:
        raise WorktreeResolutionError(
            'Cannot locate executor — not inside a git checkout. '
            "Pass --project-dir explicitly or run from a checkout that contains '.plan/execute-script.py'."
        ) from exc


def _query_worktree_path(plan_id: str) -> tuple[bool, str]:
    """Return ``(use_worktree, worktree_path)`` for a plan id.

    Spawns ``manage-status get-worktree-path`` and parses its TOON output
    via the lightweight ``json``-style fallback below. The
    ``manage-status`` script is Bucket A (cwd-agnostic), so executor
    invocation works from any worktree.

    Raises:
        WorktreeResolutionError: when the script returns a non-success
            status or stdout cannot be parsed.
    """
    executor = _executor_path()
    cmd = [
        sys.executable,
        str(executor),
        'plan-marshall:manage-status:manage-status',
        'get-worktree-path',
        '--plan-id',
        plan_id,
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise WorktreeResolutionError(
            f"Failed to invoke manage-status get-worktree-path for plan_id='{plan_id}': {exc}"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or '').strip()
        raise WorktreeResolutionError(
            f"manage-status get-worktree-path failed (exit {completed.returncode}) for plan_id='{plan_id}': {stderr}"
        )

    use_worktree, worktree_path = _parse_get_worktree_path_output(completed.stdout)
    return use_worktree, worktree_path


def _parse_get_worktree_path_output(stdout: str) -> tuple[bool, str]:
    """Parse the TOON payload produced by manage-status get-worktree-path.

    The output is a flat key/value document with the shape::

        status: success
        plan_id: X
        use_worktree: false
        worktree_path: ""

    Rather than pulling in the full ``toon_parser`` (which would create a
    cycle for the foundational helper), we walk the lines manually — the
    payload is shallow and the contract is owned by ``_status_query.py``.
    """
    use_worktree = False
    worktree_path = ''
    saw_status_success = False
    error_field: str | None = None
    message_field: str | None = None
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if key == 'status' and value == 'success':
            saw_status_success = True
        elif key == 'use_worktree':
            use_worktree = value.lower() == 'true'
        elif key == 'worktree_path':
            worktree_path = value
        elif key == 'error':
            error_field = value
        elif key == 'message':
            message_field = value
    if not saw_status_success:
        raise WorktreeResolutionError(
            f"manage-status get-worktree-path returned non-success: error='{error_field}' message='{message_field}'"
        )
    return use_worktree, worktree_path


def _main_checkout_root() -> str:
    """Return the checkout root as an absolute path string.

    Used as the fallback when neither ``--plan-id`` nor ``--project-dir``
    is supplied (or when ``--plan-id`` resolves to ``use_worktree=false``).
    Resolved cwd-relatively via the uniform cwd rule (ADR-002): the nearest
    ancestor of cwd containing ``.plan/local``.
    """
    root = _find_plan_root_from_cwd()
    if root is None:
        # Last-ditch fallback: caller is operating outside any resolvable
        # plan root (rare; usually a test fixture). Use cwd so the historical
        # behaviour of ``--project-dir=.`` is preserved.
        return os.path.abspath(os.getcwd())
    return str(root)


def resolve_project_dir(
    plan_id: str | None,
    project_dir: str | None,
    *,
    default: str | None = None,
) -> str:
    """Resolve the working-tree root from (``plan_id``, ``project_dir``).

    Implements the four-state contract documented at module top.

    Args:
        plan_id: Optional plan identifier. When set, the worktree path
            is looked up via ``manage-status get-worktree-path``.
        project_dir: Optional explicit project directory override.
            Returned verbatim when set (and ``plan_id`` is not).
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
    plan_id_supplied = bool(plan_id)

    if plan_id_supplied and project_dir_supplied:
        raise MutuallyExclusiveArgsError(
            "Both --plan-id and --project-dir were supplied. Pick exactly one: "
            '--plan-id auto-resolves the worktree path; --project-dir is the explicit override.'
        )

    if plan_id_supplied:
        assert plan_id is not None  # for mypy
        use_worktree, worktree_path = _query_worktree_path(plan_id)
        if use_worktree:
            if not worktree_path:
                raise WorktreeResolutionError(
                    f"Plan '{plan_id}' reports use_worktree=true but worktree_path is empty."
                )
            return os.path.abspath(worktree_path)
        return _main_checkout_root()

    if project_dir_supplied:
        assert project_dir is not None  # for mypy
        return os.path.abspath(project_dir)

    return _main_checkout_root()


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
