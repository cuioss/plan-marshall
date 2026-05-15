#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""CI-completion precondition resolver for the phase-6-finalize dispatcher.

This helper backs the ``requires: [ci-complete]`` frontmatter declaration on
consumer finalize steps (``automated-review``, ``sonar-roundtrip``). Before
the dispatcher invokes any step that declares the precondition, it calls
:func:`resolve` here; the resolver consults a per-HEAD cache and, on miss,
runs the bounded ``ci wait`` polling primitive inline.

Return shape (CLI emits this as TOON; programmatic callers consume the dict
directly)::

    status: satisfied | wait_succeeded | wait_failed
    head_sha: <40-char hex SHA>
    ci_final_status: success | failure | timeout | null

Outcome semantics:

* ``satisfied`` — the cache for the current HEAD already records a
  ``success`` outcome from a prior call in the same dispatcher pass. No CI
  poll is issued. ``ci_final_status`` is ``success``.
* ``wait_succeeded`` — the cache was missing (or stale relative to HEAD); a
  fresh ``ci wait`` returned ``final_status: success``. The cache is
  populated with the live HEAD SHA. ``ci_final_status`` is ``success``.
* ``wait_failed`` — the cache was missing (or stale); a fresh ``ci wait``
  returned ``final_status: failure`` OR ``status: timeout``. No cache entry
  is written (re-entry will re-poll). ``ci_final_status`` carries either
  ``failure`` or ``timeout`` so the caller can surface the reason in the
  consumer step's ``display_detail``.

The script is intentionally a private helper (underscore prefix) — it is
invoked inline by the markdown dispatcher in
``phase-6-finalize/SKILL.md`` Step 3 ("Precondition resolution" block) and
is NOT exposed as a marketplace notation. The dispatcher bears
responsibility for mapping ``wait_failed`` to the consumer step's outcome
record (``failed`` with ``display_detail "ci_failure (precondition)"``);
this script never calls ``mark-step-done`` directly because the
precondition is not itself a finalize step.

Cache lifecycle:

* Storage: ``.plan/plans/{plan_id}/work/ci-precondition-cache.toon``.
* Key: the 40-character HEAD SHA captured via
  ``git -C {worktree_path} rev-parse HEAD`` at the start of each resolve
  call.
* Invalidation: implicit. When a loop-back commit advances HEAD, the next
  resolve call sees a fresh SHA, the cache's stored SHA no longer matches,
  and the resolver re-runs ``ci wait`` against the new tree.
* Failure: no cache entry is written on ``wait_failed``, so a re-entry
  always polls again — the failure state does not stick.

Subprocess seams (``_run_git_rev_parse_head``, ``_run_ci_wait``) are split
out to keep the orchestration body easy to test without a live git
worktree or live CI provider.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Resolve the marketplace_paths + toon_parser modules without committing
# this helper to the global executor (it is a private dispatcher-side
# helper, not a registered notation). The path manipulation mirrors the
# pattern used by other underscore-prefixed marketplace scripts.
_SCRIPTS_DIR = Path(__file__).parent
_SCRIPT_SHARED = _SCRIPTS_DIR.parent.parent.parent / 'script-shared' / 'scripts'
_REF_TOON = _SCRIPTS_DIR.parent.parent.parent / 'ref-toon-format' / 'scripts'
for _candidate in (_SCRIPT_SHARED, _REF_TOON):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default ``ci wait --timeout`` ceiling — 600 s (10 minutes). Most CI
#: runs complete inside 60-180 s; the larger ceiling is defensive against
#: cold-start queues. The host platform's per-call Bash ceiling is set to
#: match this value plus a small buffer (see ``_run_ci_wait`` below) so
#: the script-side ceiling is the binding one.
DEFAULT_CI_WAIT_TIMEOUT_SECONDS: int = 600

#: Cache file path relative to the plan directory.
_CACHE_RELATIVE_PATH: str = 'work/ci-precondition-cache.toon'

#: The CI-wait notation routed through the executor proxy.
_CI_WAIT_NOTATION: str = 'plan-marshall:tools-integration-ci:ci'


# ---------------------------------------------------------------------------
# Subprocess seams (overridable in tests)
# ---------------------------------------------------------------------------


def _run_git_rev_parse_head(worktree_path: str) -> str:
    """Return the worktree's current HEAD SHA via ``git rev-parse HEAD``.

    Raises:
        RuntimeError: ``git rev-parse`` exited non-zero. The exception
            message carries the captured stderr so the dispatcher can
            surface the reason.
    """
    completed = subprocess.run(
        ['git', '-C', worktree_path, 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git rev-parse HEAD failed in {worktree_path!r}: "
            f"{completed.stderr.strip() or 'no stderr'}"
        )
    sha = completed.stdout.strip()
    if not sha:
        raise RuntimeError(
            f"git rev-parse HEAD returned empty output in {worktree_path!r}"
        )
    return sha


def _run_ci_wait(
    plan_id: str,
    pr_number: int,
    timeout_seconds: int,
    worktree_path: str,
) -> dict:
    """Invoke ``ci wait`` via the executor proxy and parse the TOON result.

    Returns the parsed TOON dict verbatim. Callers inspect
    ``final_status`` (on success) or ``status``/``error`` (on timeout) to
    decide the outcome.

    The host platform's per-call ceiling is wider than ``timeout_seconds``
    because ``ci wait`` enforces its own internal poll loop. We invoke
    with ``--plan-id`` so the executor's two-state contract resolves the
    worktree path itself; passing both ``--plan-id`` and
    ``--project-dir`` would trigger ``mutually_exclusive_args``.
    """
    executor = Path(_SCRIPTS_DIR).parents[4] / '.plan' / 'execute-script.py'
    cmd = [
        sys.executable,
        str(executor),
        _CI_WAIT_NOTATION,
        '--plan-id',
        plan_id,
        'ci',
        'wait',
        '--pr-number',
        str(pr_number),
        '--timeout',
        str(timeout_seconds),
    ]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        # The wait primitive's own --timeout enforces the inner ceiling.
        # Give the host platform a small buffer beyond it so the inner
        # ceiling is the binding one.
        timeout=timeout_seconds + 30,
        cwd=worktree_path,
    )
    stdout = completed.stdout or ''
    # The executor wraps every script call in TOON output even on error.
    # An empty stdout means the executor itself crashed; surface that as
    # a synthetic timeout-like envelope so the dispatcher can react.
    if not stdout.strip():
        return {
            'status': 'error',
            'error': (
                f"ci wait subprocess produced no output "
                f"(exit_code={completed.returncode}): "
                f"{completed.stderr.strip() or 'no stderr'}"
            ),
        }
    try:
        return parse_toon(stdout)
    except Exception as exc:  # pragma: no cover — defensive only
        return {
            'status': 'error',
            'error': f"ci wait output not parseable as TOON: {exc}",
            'raw_stdout': stdout,
        }


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------


def _resolve_plan_base_dir() -> Path:
    """Resolve the on-disk plan base directory.

    Honours the ``PLAN_BASE_DIR`` env override (used by tests). Otherwise
    walks up from the current working directory to find a ``.plan``
    directory — the same resolution pattern other marketplace scripts use
    when ``manage-files`` is not in play.
    """
    override = os.environ.get('PLAN_BASE_DIR')
    if override:
        return Path(override)
    # Default for in-tree calls: the executor lives at
    # ``<repo>/.plan/execute-script.py`` and is the canonical anchor.
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        executor = candidate / '.plan' / 'execute-script.py'
        if executor.is_file():
            return candidate / '.plan'
    # Fall back to ``<cwd>/.plan`` even when the executor is missing —
    # tests with a synthetic plan tree set PLAN_BASE_DIR directly.
    return cwd / '.plan'


def _cache_path(plan_id: str) -> Path:
    """Return the absolute path of the per-plan precondition cache file."""
    return _resolve_plan_base_dir() / 'plans' / plan_id / _CACHE_RELATIVE_PATH


def _read_cache(plan_id: str) -> dict | None:
    """Read the cache file, returning ``None`` when absent or unparseable."""
    path = _cache_path(plan_id)
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding='utf-8')
    except OSError:
        return None
    if not content.strip():
        return None
    try:
        return parse_toon(content)
    except Exception:
        # A corrupted cache file is treated as a miss — the resolver will
        # re-poll and overwrite the file on success.
        return None


def _write_cache(plan_id: str, head_sha: str, ci_final_status: str) -> None:
    """Persist the cache entry for a successful CI completion."""
    path = _cache_path(plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'head_sha': head_sha,
        'ci_final_status': ci_final_status,
    }
    path.write_text(serialize_toon(payload), encoding='utf-8')


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def resolve(
    plan_id: str,
    worktree_path: str,
    pr_number: int,
    *,
    timeout_seconds: int = DEFAULT_CI_WAIT_TIMEOUT_SECONDS,
    ci_wait_runner=None,
    git_head_resolver=None,
) -> dict:
    """Resolve the ``ci-complete`` precondition for the current HEAD.

    Args:
        plan_id: Plan identifier — used to locate the cache file.
        worktree_path: Absolute path to the active git worktree (or the
            main checkout for non-worktree plans). Used to resolve the
            current HEAD SHA and to set the ``ci wait`` subprocess cwd.
        pr_number: PR number to wait on. Resolved by the dispatcher from
            the ``create-pr`` step's outcome record. The dispatcher MUST
            pass a real PR number — there is no "no PR" branch here
            (the dispatcher handles that condition before calling).
        timeout_seconds: ``ci wait --timeout`` ceiling. Defaults to
            :data:`DEFAULT_CI_WAIT_TIMEOUT_SECONDS` (600s = 10 min).
        ci_wait_runner: Optional callable used as a test seam in place of
            :func:`_run_ci_wait`. Signature:
            ``(plan_id, pr_number, timeout_seconds, worktree_path) -> dict``.
        git_head_resolver: Optional callable used as a test seam in place
            of :func:`_run_git_rev_parse_head`. Signature:
            ``(worktree_path) -> str``.

    Returns:
        Dict matching the return contract documented in the module
        docstring.
    """
    head_fn = git_head_resolver or _run_git_rev_parse_head
    wait_fn = ci_wait_runner or _run_ci_wait

    head_sha = head_fn(worktree_path)

    # Cache hit?
    cached = _read_cache(plan_id)
    if (
        cached is not None
        and cached.get('head_sha') == head_sha
        and cached.get('ci_final_status') == 'success'
    ):
        return {
            'status': 'satisfied',
            'head_sha': head_sha,
            'ci_final_status': 'success',
        }

    # Cache miss (or stale) → run the bounded wait.
    wait_result = wait_fn(plan_id, pr_number, timeout_seconds, worktree_path)

    # Interpret the wait envelope.
    final_status = wait_result.get('final_status')
    envelope_status = wait_result.get('status')

    if envelope_status == 'success' and final_status == 'success':
        _write_cache(plan_id, head_sha, 'success')
        return {
            'status': 'wait_succeeded',
            'head_sha': head_sha,
            'ci_final_status': 'success',
        }

    if envelope_status == 'success' and final_status == 'failure':
        # CI ran to completion and failed. Do not cache.
        return {
            'status': 'wait_failed',
            'head_sha': head_sha,
            'ci_final_status': 'failure',
        }

    # Timeout or any other non-success envelope.
    return {
        'status': 'wait_failed',
        'head_sha': head_sha,
        'ci_final_status': 'timeout',
    }


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def cmd_resolve(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`resolve` — emits TOON, returns exit 0."""
    try:
        result = resolve(
            plan_id=args.plan_id,
            worktree_path=args.worktree_path,
            pr_number=args.pr_number,
            timeout_seconds=args.timeout,
        )
    except RuntimeError as exc:
        payload = {
            'status': 'error',
            'error': str(exc),
        }
        print(serialize_toon(payload))
        return 1
    print(serialize_toon(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with a single ``resolve`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Resolve the ci-complete precondition for the current HEAD. '
            'Consulted inline by the phase-6-finalize dispatcher before '
            'dispatching any step that declares requires: [ci-complete] '
            'in its frontmatter.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    resolve_parser = sub.add_parser(
        'resolve',
        help='Resolve the precondition for the current HEAD',
        allow_abbrev=False,
    )
    resolve_parser.add_argument(
        '--plan-id',
        required=True,
        dest='plan_id',
        help='Plan identifier (locates the cache file)',
    )
    resolve_parser.add_argument(
        '--worktree-path',
        required=True,
        dest='worktree_path',
        help='Absolute path to the active git worktree root',
    )
    resolve_parser.add_argument(
        '--pr-number',
        required=True,
        dest='pr_number',
        type=int,
        help='PR number to wait on (resolved by the dispatcher)',
    )
    resolve_parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_WAIT_TIMEOUT_SECONDS,
        help=(
            f'ci wait --timeout ceiling in seconds '
            f'(default: {DEFAULT_CI_WAIT_TIMEOUT_SECONDS})'
        ),
    )
    resolve_parser.set_defaults(func=cmd_resolve)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


# JSON helper export for use by callers that prefer dict-level integration
# over TOON parsing of the CLI output (e.g., other Python scripts within
# the same dispatcher process).
__all__ = [
    'DEFAULT_CI_WAIT_TIMEOUT_SECONDS',
    'resolve',
]


def _json_dump(result: dict) -> str:  # pragma: no cover — diagnostic only
    """Diagnostic helper for debugging cache contents."""
    return json.dumps(result, indent=2, sort_keys=True)
