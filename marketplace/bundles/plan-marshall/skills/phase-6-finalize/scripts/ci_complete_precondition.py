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
    ci_final_status: success | failure | timeout | no_checks | null
    failing_checks: [str, ...]      # present on wait_failed (may be empty)
    wait_outcome: completed | deadline_exceeded   # present on wait_failed
    mode: strict | consume-failures               # present on wait_failed

Outcome semantics:

* ``satisfied`` — the cache for the current HEAD already records a
  ``success`` outcome from a prior call in the same dispatcher pass. No CI
  poll is issued. ``ci_final_status`` is ``success``.
* ``wait_succeeded`` — the cache was missing (or stale relative to HEAD); a
  fresh ``ci wait`` returned ``final_status: success``. The cache is
  populated with the live HEAD SHA. ``ci_final_status`` is ``success``.
* ``wait_failed`` — the cache was missing (or stale); a fresh ``ci wait``
  returned ``final_status: failure`` (with ``failing_checks`` enumerating
  the failing checks), ``final_status: none`` (no checks reported — a
  distinct ``ci_final_status: no_checks`` so the dispatcher can
  distinguish "CI never ran" from a real failure), OR ``status: timeout``
  (``ci_final_status: timeout`` with ``failing_checks`` carrying the
  still-running checks at the deadline). No cache entry is written
  (re-entry will re-poll). The ``failing_checks`` and ``wait_outcome``
  fields are forwarded from the underlying ``ci wait`` envelope so
  downstream consumers (see lesson-2026-05-18-16-001 deliverables 5 and 6)
  can route the precondition decision into the correct triage producer
  string without re-fetching the CI run.

The script is invoked via the marketplace executor notation
``plan-marshall:phase-6-finalize:ci_complete_precondition`` from the
markdown dispatcher in ``phase-6-finalize/SKILL.md`` Step 3 ("Precondition
resolution" block). The dispatcher bears responsibility for mapping
``wait_failed`` to the consumer step's outcome record (``failed`` with
``display_detail "ci_failure (precondition)"``); this script never calls
``mark-step-done`` directly because the precondition is not itself a
finalize step.

Cache lifecycle:

* Storage: ``.plan/local/plans/{plan_id}/work/ci-precondition-cache.toon``.
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

The script is registered through ``generate_executor.py`` and consumed via
the executor proxy: ``python3 .plan/execute-script.py
plan-marshall:phase-6-finalize:ci_complete_precondition resolve ...``.
The executor injects ``PYTHONPATH`` for ``toon_parser`` and
``marketplace_paths``, so no in-script ``sys.path`` manipulation is
required (the previous underscore-prefixed sibling-traversal pattern broke
when the script was invoked from outside the source tree, e.g., from
``target/claude/`` or a relocated checkout — see lesson 2026-05-18-11-001).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from file_ops import get_plan_dir  # type: ignore[import-not-found]
from marketplace_paths import git_main_checkout_root  # type: ignore[import-not-found]
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

#: The run-configuration notation routed through the executor proxy. Used to
#: source — and adaptively update — the ``ci wait --timeout`` ceiling so the
#: precondition's tolerance tracks observed CI durations like build-command
#: timeouts do.
_RUN_CONFIG_NOTATION: str = 'plan-marshall:manage-run-config:run_config'

#: The run-configuration command key under which the CI-wait timeout is
#: persisted. ``manage-run-config`` namespaces command timeouts by an
#: arbitrary string key; ``ci:wait`` mirrors the ``checks wait`` primitive.
_CI_WAIT_TIMEOUT_KEY: str = 'ci:wait'


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
    repo_root = git_main_checkout_root()
    if repo_root is None:
        raise RuntimeError(
            'ci_complete_precondition: unable to resolve the git main '
            'checkout root via marketplace_paths.git_main_checkout_root() — '
            'is this script running outside a git repository?'
        )
    executor = repo_root / '.plan' / 'execute-script.py'
    cmd = [
        sys.executable,
        str(executor),
        _CI_WAIT_NOTATION,
        '--plan-id',
        plan_id,
        'checks',
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


def _run_run_config_timeout_get(default_seconds: int) -> int:
    """Read the persisted ``ci:wait`` timeout via the run-config helper.

    Invokes ``run_config timeout get --command ci:wait --default {n}`` through
    the executor proxy and returns the parsed ``timeout_seconds`` integer. Any
    failure (executor crash, unparseable output, missing field) degrades
    gracefully to ``default_seconds`` — sourcing the timeout from
    run-configuration.json is an optimisation, never a hard dependency.
    """
    repo_root = git_main_checkout_root()
    if repo_root is None:
        return default_seconds
    executor = repo_root / '.plan' / 'execute-script.py'
    cmd = [
        sys.executable,
        str(executor),
        _RUN_CONFIG_NOTATION,
        'timeout',
        'get',
        '--command',
        _CI_WAIT_TIMEOUT_KEY,
        '--default',
        str(default_seconds),
    ]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return default_seconds
    stdout = completed.stdout or ''
    if not stdout.strip():
        return default_seconds
    try:
        parsed = parse_toon(stdout)
    except Exception:  # pragma: no cover — defensive only
        return default_seconds
    value = parsed.get('timeout_seconds')
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default_seconds


def _run_run_config_timeout_set(duration_seconds: int) -> None:
    """Persist an observed CI-wait duration via the run-config helper.

    Invokes ``run_config timeout set --command ci:wait --duration {n}`` through
    the executor proxy so the timeout adapts to observed CI durations the same
    way build-command timeouts do. Failures are swallowed — recording the
    observed duration is best-effort telemetry, not a hard dependency of the
    precondition resolution.
    """
    repo_root = git_main_checkout_root()
    if repo_root is None:
        return
    executor = repo_root / '.plan' / 'execute-script.py'
    cmd = [
        sys.executable,
        str(executor),
        _RUN_CONFIG_NOTATION,
        'timeout',
        'set',
        '--command',
        _CI_WAIT_TIMEOUT_KEY,
        '--duration',
        str(duration_seconds),
    ]
    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return


# ---------------------------------------------------------------------------
# Cache I/O
# ---------------------------------------------------------------------------


def _cache_path(plan_id: str) -> Path:
    """Return the absolute path of the per-plan precondition cache file.

    Resolves the plan directory via the canonical ``file_ops.get_plan_dir``
    helper, which anchors plan-scoped state at
    ``<repo>/.plan/local/plans/{plan_id}/`` under normal operation and
    honours ``PLAN_BASE_DIR`` for tests. Local resolution of the plan-base
    directory was previously inlined here as ``_resolve_plan_base_dir`` and
    produced a ghost ``.plan/plans/...`` tree relative to the agent cwd
    whenever the env var was unset — see the fix-ghost-plan-dir lesson.
    """
    return get_plan_dir(plan_id) / _CACHE_RELATIVE_PATH


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
    timeout_seconds: int | None = None,
    ci_wait_runner=None,
    git_head_resolver=None,
    timeout_get_runner=None,
    timeout_set_runner=None,
    mode: str = 'strict',
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
        timeout_seconds: ``ci wait --timeout`` ceiling. When ``None``
            (the default), the ceiling is sourced from
            run-configuration.json under the command key ``ci:wait`` via
            the run-config ``timeout get`` helper, falling back to
            :data:`DEFAULT_CI_WAIT_TIMEOUT_SECONDS` (600s = 10 min) when
            no persisted value exists. An explicit integer overrides the
            run-config lookup entirely.
        ci_wait_runner: Optional callable used as a test seam in place of
            :func:`_run_ci_wait`. Signature:
            ``(plan_id, pr_number, timeout_seconds, worktree_path) -> dict``.
        git_head_resolver: Optional callable used as a test seam in place
            of :func:`_run_git_rev_parse_head`. Signature:
            ``(worktree_path) -> str``.
        timeout_get_runner: Optional callable used as a test seam in place
            of :func:`_run_run_config_timeout_get`. Signature:
            ``(default_seconds) -> int``.
        timeout_set_runner: Optional callable used as a test seam in place
            of :func:`_run_run_config_timeout_set`. Signature:
            ``(duration_seconds) -> None``.

    Returns:
        Dict matching the return contract documented in the module
        docstring.
    """
    head_fn = git_head_resolver or _run_git_rev_parse_head
    wait_fn = ci_wait_runner or _run_ci_wait
    timeout_get_fn = timeout_get_runner or _run_run_config_timeout_get
    timeout_set_fn = timeout_set_runner or _run_run_config_timeout_set

    if mode not in ('strict', 'consume-failures'):
        raise RuntimeError(
            f"ci_complete_precondition.resolve: invalid mode {mode!r} — "
            "must be 'strict' or 'consume-failures'"
        )

    # Source the wait ceiling from run-configuration.json when the caller
    # did not pass an explicit value. The run-config lookup degrades to
    # DEFAULT_CI_WAIT_TIMEOUT_SECONDS so the precondition never hard-fails
    # on a missing/corrupt run-configuration.json.
    if timeout_seconds is None:
        timeout_seconds = timeout_get_fn(DEFAULT_CI_WAIT_TIMEOUT_SECONDS)

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

    # Interpret the wait envelope. The ``failing_checks`` and
    # ``wait_outcome`` fields are forwarded verbatim from ``ci wait`` so
    # downstream consumers can classify the failure without re-fetching.
    final_status = wait_result.get('final_status')
    envelope_status = wait_result.get('status')
    failing_checks = wait_result.get('failing_checks') or []
    wait_outcome = wait_result.get('wait_outcome') or 'completed'

    if envelope_status == 'success' and final_status == 'success':
        _write_cache(plan_id, head_sha, 'success')
        # Record the observed CI duration so the ci:wait timeout adapts to
        # real run lengths the way build-command timeouts do. The wait
        # envelope carries ``duration_sec`` (see ci checks wait contract);
        # a missing/non-int value simply skips the adaptive update.
        observed = wait_result.get('duration_sec')
        try:
            observed_int = int(observed)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            observed_int = None
        if observed_int is not None and observed_int > 0:
            timeout_set_fn(observed_int)
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
            'failing_checks': failing_checks,
            'wait_outcome': wait_outcome,
            'mode': mode,
        }

    if envelope_status == 'success' and final_status == 'none':
        # CI never produced any checks. Distinct from real failure so the
        # dispatcher can surface "no CI configured" vs "CI ran red".
        return {
            'status': 'wait_failed',
            'head_sha': head_sha,
            'ci_final_status': 'no_checks',
            'failing_checks': [],
            'wait_outcome': wait_outcome,
            'mode': mode,
        }

    # Timeout or any other non-success envelope. ``ci wait`` carries
    # ``wait_outcome: deadline_exceeded`` and ``failing_checks`` enumerating
    # the still-running checks at the deadline.
    return {
        'status': 'wait_failed',
        'head_sha': head_sha,
        'ci_final_status': 'timeout',
        'failing_checks': failing_checks,
        'wait_outcome': wait_outcome or 'deadline_exceeded',
        'mode': mode,
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
            mode=args.mode,
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
        default=None,
        help=(
            'ci wait --timeout ceiling in seconds. When omitted, the '
            'ceiling is sourced from run-configuration.json under the '
            f'command key {_CI_WAIT_TIMEOUT_KEY!r}, falling back to '
            f'{DEFAULT_CI_WAIT_TIMEOUT_SECONDS}s when no value is '
            'persisted.'
        ),
    )
    resolve_parser.add_argument(
        '--mode',
        choices=('strict', 'consume-failures'),
        default='strict',
        dest='mode',
        help=(
            "Precondition mode. 'strict' (default) is used by "
            "automated-review / sonar-roundtrip — wait_failed short-"
            "circuits the consumer step. 'consume-failures' is used by "
            "ci-verify — wait_failed threads the envelope through to "
            "the consumer body without short-circuiting. See "
            "phase-6-finalize/standards/ci-verify.md."
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
