#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared base module for CI provider scripts (GitHub, GitLab).

Provides unified CLI runner, auth checker, error output, parser builder,
command dispatch, polling framework, and CI check formatting.
Each provider imports from here and supplies provider-specific handler
functions and CLI details.

This module re-exports commonly used helpers from sibling skill scripts
(toon_parser, file_ops) so that CI provider scripts can import everything
they need from ``ci_base`` alone — reducing the PYTHONPATH entries required
for manual invocations from 4 directories to 2.
"""

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# sys.path auto-discovery for sibling skill script directories
# ---------------------------------------------------------------------------
# When invoked via the executor, PYTHONPATH already contains the required
# directories.  For manual invocations we add them here so that ``file_ops``
# and ``toon_parser`` are importable without the caller having to set up 4
# separate PYTHONPATH entries.


def _ensure_sibling_skill_paths() -> None:
    """Add sibling skill script directories to sys.path if not already present.

    Navigates from this file's location (``tools-integration-ci/scripts/``)
    up to the ``skills/`` directory and adds the script directories for
    ``tools-file-ops`` and ``ref-toon-format``.
    """
    scripts_dir = Path(__file__).resolve().parent  # .../tools-integration-ci/scripts
    skills_dir = scripts_dir.parent.parent  # .../skills

    sibling_dirs = [
        skills_dir / 'tools-file-ops' / 'scripts',
        skills_dir / 'ref-toon-format' / 'scripts',
        skills_dir / 'tools-input-validation' / 'scripts',
        skills_dir / 'manage-config' / 'scripts',
    ]
    for d in sibling_dirs:
        d_str = str(d)
        if d.is_dir() and d_str not in sys.path:
            sys.path.insert(0, d_str)


_ensure_sibling_skill_paths()

from file_ops import (  # noqa: E402, F401
    PlanNotFoundError,
    get_plan_dir,
    output_toon,
    require_plan_exists,
    safe_main,
)
from input_validation import (  # noqa: E402, F401
    add_plan_id_arg,
    parse_args_with_toon_errors,
)
from toon_parser import parse_toon, serialize_toon  # noqa: E402, F401

# Exit codes
EXIT_SUCCESS = 0

# ---------------------------------------------------------------------------
# Body store (path-allocate pattern for PR/issue/comment bodies)
# ---------------------------------------------------------------------------

# Valid body "kinds" — each identifies a distinct consumer surface.
BODY_KIND_PR_CREATE = 'pr-create'
BODY_KIND_PR_EDIT = 'pr-edit'
BODY_KIND_PR_REPLY = 'pr-reply'
BODY_KIND_PR_THREAD_REPLY = 'pr-thread-reply'
BODY_KIND_ISSUE_CREATE = 'issue-create'
BODY_KIND_ISSUE_COMMENT = 'issue-comment'

VALID_BODY_KINDS = frozenset(
    {
        BODY_KIND_PR_CREATE,
        BODY_KIND_PR_EDIT,
        BODY_KIND_PR_REPLY,
        BODY_KIND_PR_THREAD_REPLY,
        BODY_KIND_ISSUE_CREATE,
        BODY_KIND_ISSUE_COMMENT,
    }
)

_BODY_SLOT_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')


def _resolve_body_slot(slot: str | None) -> str:
    """Validate an optional slot identifier; default to 'default'."""
    if slot is None or slot == '':
        return 'default'
    if not _BODY_SLOT_RE.match(slot):
        raise ValueError(f"Invalid slot '{slot}': must match [a-z0-9][a-z0-9-]{{0,63}}")
    return slot


def normalize_issue_ref(issue: str) -> str:
    """Normalize a GitHub/GitLab issue reference to its bare number/IID.

    Accepts either a bare number (returned unchanged) or a full issue URL
    (e.g. ``https://github.com/o/r/issues/42`` or
    ``https://gitlab.com/o/r/-/issues/42``) and extracts the trailing
    identifier. The ``--issue`` argument advertises "Issue number or URL", but
    ``glab issue note`` does not accept a full URL and the return-dict
    ``issue_number`` field must carry a normalized number per the
    ``issue-operations.md`` contract; normalizing here honors both. Preserves a
    silent-fail contract: an unparseable value is returned unchanged rather than
    raising.
    """
    ref = str(issue)
    if '/issues/' in ref:
        try:
            ref = ref.split('/issues/')[1].split('/')[0].split('?')[0].split('#')[0]
        except (IndexError, ValueError):
            return str(issue)
    return ref


def get_body_path(plan_id: str, kind: str, slot: str | None = None) -> Path:
    """Return the script-owned scratch path for a body of the given kind.

    The layout is `<plan>/work/ci-bodies/{kind}-{slot}.md`. The file is NOT
    created here — callers use `prepare_body` to allocate and pre-create the
    parent directory, then write content with their native Write/Edit tools.
    """
    if kind not in VALID_BODY_KINDS:
        raise ValueError(f"Invalid body kind '{kind}'. Valid kinds: {sorted(VALID_BODY_KINDS)}")
    resolved_slot = _resolve_body_slot(slot)
    return get_plan_dir(plan_id) / 'work' / 'ci-bodies' / f'{kind}-{resolved_slot}.md'


def prepare_body(plan_id: str, kind: str, slot: str | None = None) -> dict[str, Any]:
    """Allocate a scratch path for a body of the given kind.

    Creates the parent directory and returns a structured result the
    caller can emit verbatim from a prepare-body subcommand.
    """
    try:
        resolved_slot = _resolve_body_slot(slot)
    except ValueError as e:
        return {'status': 'error', 'error': 'invalid_slot', 'message': str(e)}

    # Guard at script side: refuse to materialise a body path under a plan
    # directory that doesn't exist (and was never initialised by phase-1).
    # Without this guard the `path.parent.mkdir(parents=True, ...)` below
    # silently creates an orphan plan tree just to hold a scratch body file.
    try:
        require_plan_exists(plan_id)
    except PlanNotFoundError as exc:
        return {
            'status': 'error',
            'error': 'plan_not_found',
            'message': str(exc),
            'plan_id': plan_id,
            'plan_dir': str(exc.plan_dir),
        }

    path = get_body_path(plan_id, kind, resolved_slot)
    path.parent.mkdir(parents=True, exist_ok=True)

    return {
        'status': 'success',
        'plan_id': plan_id,
        'kind': kind,
        'slot': resolved_slot,
        'path': str(path),
        'exists': path.exists(),
        'note': 'Write the body content to this path, then call the matching consume subcommand (e.g. `pr create --plan-id ...`).',
    }


def read_and_consume_body(
    plan_id: str,
    kind: str,
    slot: str | None = None,
    *,
    required: bool = True,
) -> tuple[str | None, dict[str, Any] | None]:
    """Read a prepared body file for consumption.

    Returns ``(content, None)`` on success. On failure returns ``(None, error_dict)``.
    The scratch file is NOT deleted here — providers should call
    ``delete_consumed_body`` after the downstream CLI invocation succeeds
    (keeping the file around on failure so the caller can retry).

    Args:
        plan_id: Plan identifier (required).
        kind: One of the `BODY_KIND_*` constants.
        slot: Optional slot identifier (defaults to 'default').
        required: If True (default), a missing/empty file is an error. If
            False, returns ``('', None)`` so callers can treat the body as
            optional (e.g. pr edit where only the title changes).
    """
    if not plan_id:
        return None, {
            'status': 'error',
            'error': 'missing_plan_id',
            'message': '--plan-id is required to consume a prepared body.',
        }

    try:
        path = get_body_path(plan_id, kind, slot)
    except ValueError as e:
        return None, {'status': 'error', 'error': 'invalid_kind', 'message': str(e)}

    if not path.exists():
        if not required:
            return '', None
        return None, {
            'status': 'error',
            'error': 'body_not_prepared',
            'kind': kind,
            'path': str(path),
            'message': (
                f'No prepared body for kind={kind} plan_id={plan_id}. '
                f'Call the matching prepare-body subcommand first and write the '
                f'body content to the returned path.'
            ),
        }

    content = path.read_text(encoding='utf-8')
    if not content.strip() and required:
        return None, {
            'status': 'error',
            'error': 'body_empty',
            'kind': kind,
            'path': str(path),
            'message': f'Prepared body file is empty: {path}',
        }
    return content, None


def delete_consumed_body(plan_id: str, kind: str, slot: str | None = None) -> None:
    """Delete a previously-consumed scratch body. Silent on failure."""
    try:
        path = get_body_path(plan_id, kind, slot)
        if path.exists():
            path.unlink()
    except (OSError, ValueError):
        pass


def add_body_consumer_args(subparser: argparse.ArgumentParser) -> None:
    """Register the `--plan-id` + `--slot` arguments required by every consumer.

    Used on subcommands that now consume a prepared scratch body instead of a
    raw CLI argument (`pr create`, `pr edit`, `pr reply`, `pr thread-reply`,
    `issue create`, `issue comment`).
    """
    subparser.add_argument(
        '--plan-id',
        required=True,
        help='Plan identifier bound to the prepared body file',
    )
    subparser.add_argument(
        '--slot',
        default=None,
        help='Optional body slot identifier matching the prior prepare-body call (default: "default")',
    )


# Shared defaults for CI polling operations.
#
# `DEFAULT_CI_TIMEOUT` is resolved at module load via `_resolve_ci_timeout()`:
#   1. Read `plan.phase-6-finalize.checks_wait_timeout_seconds` from marshal.json
#      when the file is present and the key is set — the project-level override.
#      The timeout is a finalize wait-policy owned by phase-6-finalize.
#   2. Fall back to 600 seconds when marshal.json is absent OR the key is
#      unset. The 600s baseline replaces the prior hard-coded 300s default
#      after verify jobs were observed taking 318s+ on hot CI runners.
# The explicit `--timeout` CLI flag on each polling subparser ALWAYS wins —
# argparse-supplied values override the module-level default.
def _resolve_ci_timeout() -> int:
    """Resolve the default polling timeout from marshal.json with safe fallback.

    Returns:
        Integer seconds. 600 when marshal.json is absent OR the key is unset
        OR any read/parse error occurs (the resolver never raises — a missing
        or malformed config falls back to the conservative 600s baseline so
        the CLI remains usable outside a plan-marshall project).
    """
    try:
        # _config_core triggers get_base_dir() at import time, which raises
        # RuntimeError when no git root is resolvable from cwd. Catching
        # Exception broadly here is deliberate — the resolver MUST NOT raise
        # under any project state; falling back to 600s keeps the CLI usable.
        from _config_core import is_initialized, load_config
    except Exception:
        return 600
    try:
        if not is_initialized():
            return 600
        cfg = load_config()
        finalize_section = cfg.get('plan', {}).get('phase-6-finalize', {}) or {}
        value = finalize_section.get('checks_wait_timeout_seconds')
        if isinstance(value, int) and value > 0:
            return value
        return 600
    except Exception:
        return 600


DEFAULT_CI_TIMEOUT = _resolve_ci_timeout()  # seconds, see resolver above
DEFAULT_CI_INTERVAL = 30  # seconds
CI_LOG_TRUNCATE_LINES = 200


# ---------------------------------------------------------------------------
# CLI execution
# ---------------------------------------------------------------------------

# Process-global default working directory for all CLI subprocess invocations.
# Set via set_default_cwd() from the top-level router when --project-dir is
# supplied. When None, subprocesses inherit the Python process cwd. This exists
# so every gh/glab call in every provider can be redirected at a worktree path
# without threading the value through every handler signature — callers that
# need a per-call override can still pass `cwd=` explicitly to run_cli.
_DEFAULT_CWD: str | None = None


def extract_project_dir(argv: list[str]) -> tuple[str | None, list[str]]:
    """Strip an optional top-level ``--project-dir PATH`` flag from *argv*.

    Returns ``(project_dir_or_none, remaining_argv)``. Supports both the
    ``--project-dir PATH`` and ``--project-dir=PATH`` forms. Only the first
    occurrence is consumed; a second occurrence is left untouched so the
    downstream provider parser can reject it as unknown.

    Shared helper used by ``ci.py`` and all provider front-ends
    (``github_pr.py``, ``github_ops.py``, ``gitlab_pr.py``, ``gitlab_ops.py``,
    ``sonar.py``, ``sonar_rest.py``). Pre-parsing avoids forcing every
    downstream ``argparse`` layer to know about the router flag.

    See :func:`extract_routing_args` for the canonical entry point that
    consumes both ``--project-dir`` and ``--plan-id`` together and
    enforces the two-state contract (mutually exclusive flags).
    """
    project_dir: str | None = None
    out: list[str] = []
    consumed = False
    i = 0
    import sys as _sys

    while i < len(argv):
        token = argv[i]
        if not consumed and token == '--project-dir':
            if i + 1 >= len(argv):
                print(
                    'Error: --project-dir requires a PATH argument',
                    file=_sys.stderr,
                )
                _sys.exit(2)
            project_dir = argv[i + 1]
            consumed = True
            i += 2
            continue
        if not consumed and token.startswith('--project-dir='):
            project_dir = token.split('=', 1)[1]
            if not project_dir:
                print(
                    'Error: --project-dir requires a non-empty PATH',
                    file=_sys.stderr,
                )
                _sys.exit(2)
            consumed = True
            i += 1
            continue
        out.append(token)
        i += 1
    return project_dir, out


# ---------------------------------------------------------------------------
# Subcommand token registry (registration-driven boundary set)
# ---------------------------------------------------------------------------
# The token set that _split_at_subcommand uses to locate the subcommand
# boundary in argv is built lazily from build_parser() and extended by
# provider scripts that expose top-level subcommand tokens not registered in
# build_parser (e.g. 'fetch-comments', 'comments-stage' from github_pr.py /
# gitlab_pr.py). Callers must invoke register_subcommands() before calling
# extract_routing_args() for custom tokens to take effect.

_KNOWN_SUBCOMMANDS_CACHE: frozenset[str] | None = None


def get_known_subcommands() -> frozenset[str]:
    """Return the canonical set of known CI router subcommand tokens.

    Bootstraps lazily from ``build_parser()``'s top-level subparsers.choices
    on first call so the set is always derived from the registered argparse
    surface rather than a manually maintained literal.  Extra tokens added by
    provider scripts via :func:`register_subcommands` are merged in.

    Thread safety: not guaranteed — intended for single-threaded CLI use.
    """
    global _KNOWN_SUBCOMMANDS_CACHE
    if _KNOWN_SUBCOMMANDS_CACHE is None:
        # Bootstrap from the shared build_parser() defined later in this module.
        # No import cycle: build_parser is a plain function in the same module.
        parser, _, _, _, _ = build_parser('_subcommand_discovery')
        choices: set[str] = set()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                choices.update(action.choices.keys())
                break
        _KNOWN_SUBCOMMANDS_CACHE = frozenset(choices)
    return _KNOWN_SUBCOMMANDS_CACHE


def register_subcommands(tokens: frozenset[str] | set[str]) -> None:
    """Extend the known subcommand registry with additional tokens.

    Called by provider scripts that expose top-level subcommand tokens not
    registered in ``build_parser`` (for example ``'fetch-comments'`` and
    ``'comments-stage'`` from ``github_pr.py`` / ``gitlab_pr.py``).

    Safe to call multiple times; each call merges *tokens* into the existing
    registry.  Must be called **before** :func:`extract_routing_args` for the
    new tokens to influence subcommand-boundary detection.

    Example (at module level in a provider script)::

        from ci_base import register_subcommands
        register_subcommands({'fetch-comments', 'comments-stage'})
    """
    global _KNOWN_SUBCOMMANDS_CACHE
    current = get_known_subcommands()
    _KNOWN_SUBCOMMANDS_CACHE = current | frozenset(tokens)


def extract_routing_args(argv: list[str]) -> tuple[str | None, list[str]]:
    """Pre-parse ``--project-dir`` AND ``--plan-id`` and return the resolved cwd.

    Implements the two-state contract documented in
    ``script_shared/scripts/resolve_project_dir.py`` for the CI router
    and provider front-ends. Wraps :func:`extract_project_dir` and
    :func:`script_shared.resolve_project_dir.extract_plan_id` so that
    callers can swap a single ``extract_project_dir`` line for one
    ``extract_routing_args`` call and gain ``--plan-id`` support.

    Routing-vs-subcommand disambiguation: ``--plan-id`` at the **router
    level** (i.e., before the first token in the known subcommand registry;
    see :func:`get_known_subcommands`) is consumed for worktree resolution.
    ``--plan-id`` or ``--project-dir`` appearing AFTER a subcommand token is
    NOT consumed for routing — it passes through in ``remaining_argv`` so
    that body-consumer subcommands (e.g. ``pr prepare-body``, ``pr create``,
    ``issue create``) can declare and consume their own ``--plan-id``
    argument via their argparse subparser. The router returns
    ``resolved=None`` in this case (no router-level routing flag was found
    before the subcommand boundary).

    Returns:
        ``(resolved_project_dir, remaining_argv)``. ``resolved_project_dir``
        is ``None`` when neither flag was supplied (callers preserve the
        previous "inherit cwd" behaviour); otherwise it is an absolute
        path resolved via ``manage-status get-worktree-path`` for
        ``--plan-id`` or returned verbatim for ``--project-dir``.

    Side effects:
        Prints a structured TOON error and exits with code 2 when both
        flags are supplied or when ``--plan-id`` resolution fails.
        Mirrors the historical behaviour of :func:`extract_project_dir`
        which also calls ``sys.exit(2)`` on malformed input.
    """
    project_dir, after_project = extract_project_dir(argv)

    # Slice the argv at the first known subcommand token. Only the prefix
    # is searched for ``--plan-id`` (router-level); the suffix (subcommand
    # and its arguments) is the post-subcommand portion. ``--project-dir``
    # is already stripped from any position by ``extract_project_dir``
    # above. Subcommand-level ``--plan-id`` (declared by body-consumer
    # subparsers such as ``pr prepare-body``) survives in ``post`` and is
    # consumed by the subcommand parser downstream — no guard is needed
    # at the routing layer.
    pre, post = _split_at_subcommand(after_project)

    # Lazy import — keeps the dependency optional so older test fixtures
    # that monkeypatch ci_base in isolation do not need to satisfy the
    # full PYTHONPATH for resolve_project_dir.
    try:
        from resolve_project_dir import (
            MutuallyExclusiveArgsError,
            WorktreeResolutionError,
            emit_mutually_exclusive_error,
            emit_worktree_error,
            extract_plan_id,
            resolve_project_dir,
        )
    except ImportError:
        # Fall back to the legacy single-flag behaviour when the helper
        # is not on the import path (e.g., minimal smoke tests). Callers
        # that opt into ``--plan-id`` must ship the helper alongside.
        return project_dir, after_project

    plan_id, pre_remaining = extract_plan_id(pre)
    remaining = pre_remaining + post

    if plan_id is None and project_dir is None:
        return None, remaining

    try:
        resolved = resolve_project_dir(plan_id, project_dir, default=None)
    except MutuallyExclusiveArgsError:
        # Local fallback for output_error — defer to print() so we don't
        # introduce a cycle with the format_toon helper that may live in
        # a sibling module.
        from toon_parser import serialize_toon

        print(serialize_toon(emit_mutually_exclusive_error(plan_id, project_dir)))
        sys.exit(2)
    except WorktreeResolutionError as exc:
        from toon_parser import serialize_toon

        assert plan_id is not None  # only reachable when plan_id was supplied
        print(serialize_toon(emit_worktree_error(plan_id, exc)))
        sys.exit(2)

    return resolved, remaining


def _split_at_subcommand(argv: list[str]) -> tuple[list[str], list[str]]:
    """Return ``(pre_subcommand, post_subcommand_inclusive)``.

    Walks ``argv`` until the first token in the known subcommand registry
    (see :func:`get_known_subcommands`) is encountered. Returns the prefix
    (router-level args) and the inclusive suffix (subcommand + its own args).
    When no subcommand is found, the entire argv is returned as the prefix
    and the suffix is empty — matching the historical "no subcommand" behaviour.
    """
    tokens = get_known_subcommands()
    for index, token in enumerate(argv):
        if token in tokens:
            return argv[:index], argv[index:]
    return list(argv), []


def set_default_cwd(cwd: str | None) -> None:
    """Set the process-global default cwd used by run_cli.

    Passing ``None`` restores the default (inherit the current process cwd).
    Intended for the ci.py router to honour ``--project-dir`` without forcing
    every provider handler to plumb the value through its call chain.
    """
    global _DEFAULT_CWD
    _DEFAULT_CWD = cwd


def get_default_cwd() -> str | None:
    """Return the current process-global default cwd (None if unset)."""
    return _DEFAULT_CWD


def run_cli(
    cli_name: str,
    args: list[str],
    *,
    capture_json: bool = False,
    timeout: int = 60,
    not_found_msg: str = '',
    cwd: str | None = None,
) -> tuple[int, str, str]:
    """Run a CLI command and return (returncode, stdout, stderr).

    Args:
        cli_name: CLI executable name (e.g. 'gh', 'glab').
        args: Arguments to pass after the CLI name.
        capture_json: If True, append ``--json`` when not already present
                      (GitHub-specific convenience).
        timeout: Subprocess timeout in seconds.
        not_found_msg: Error message when the CLI binary is missing.
        cwd: Optional working directory for the subprocess. When None, falls
            back to the process-global default set via ``set_default_cwd()``.
            When that is also None, the subprocess inherits the current Python
            process cwd (standard subprocess behaviour).

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    cmd = [cli_name] + args
    if capture_json and '--json' not in args:
        cmd.append('--json')

    effective_cwd = cwd if cwd is not None else _DEFAULT_CWD

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=effective_cwd,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        msg = not_found_msg or f'{cli_name} CLI not found'
        return 127, '', msg
    except subprocess.TimeoutExpired:
        return 124, '', 'Command timed out'
    except Exception as e:
        return 1, '', str(e)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def check_auth_cli(
    cli_name: str,
    login_message: str,
    run_fn: Any,
) -> tuple[bool, str]:
    """Check whether *cli_name* is authenticated.

    Args:
        cli_name: Not used directly -- kept for symmetry with previous API.
        login_message: User-facing message on auth failure.
        run_fn: The provider's ``run_<cli>`` wrapper so the auth check goes
                through the same code path as all other calls.

    Returns:
        ``(True, '')`` on success, ``(False, login_message)`` on failure.
    """
    returncode, _, _ = run_fn(['auth', 'status'])
    if returncode != 0:
        return False, login_message
    return True, ''


# ---------------------------------------------------------------------------
# Error output (unified TOON via serialize_toon)
# ---------------------------------------------------------------------------


def make_error(operation: str, error: str, context: str = '') -> dict:
    """Build an error dict for CI operations.

    Returns a dict with status='error' that the caller can return directly.
    The dispatch/main layer handles serialization and output.
    """
    data: dict[str, str] = {'status': 'error', 'operation': operation, 'error': error}
    if context:
        data['context'] = context
    return data


# Keep output_error as a backwards-compatible alias used by ci.py router
def output_error(operation: str, error: str, context: str = '') -> int:
    """Output error in TOON format to stdout and return EXIT_SUCCESS.

    Legacy wrapper -- new code should use make_error() and return the dict.
    Three-tier model: Exit 0 for expected errors (status:error in TOON output).
    """
    data = make_error(operation, error, context)
    print(serialize_toon(data))
    return EXIT_SUCCESS


# ---------------------------------------------------------------------------
# Argument parser builder
# ---------------------------------------------------------------------------


def build_parser(
    description: str,
) -> tuple[
    argparse.ArgumentParser,
    argparse._SubParsersAction,
    argparse._SubParsersAction,
    argparse._SubParsersAction,
    argparse._SubParsersAction,
]:
    """Build the 4-tier argparse tree shared by all CI providers.

    Returns:
        ``(parser, pr_subparsers, checks_subparsers, issue_subparsers, branch_subparsers)``
        so that providers can customise individual sub-parsers if needed.
    """
    parser = argparse.ArgumentParser(description=description, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # -- pr -----------------------------------------------------------
    pr_parser = subparsers.add_parser('pr', help='Pull request operations', allow_abbrev=False)
    pr_sub = pr_parser.add_subparsers(dest='pr_command', required=True)

    # pr view — implicit current cwd HEAD by default; --head selects a different branch
    pr_view = pr_sub.add_parser('view', help='View PR for current branch', allow_abbrev=False)
    add_head_arg(pr_view)

    # pr list
    pr_list = pr_sub.add_parser('list', help='List pull requests', allow_abbrev=False)
    pr_list.add_argument('--head', help='Filter by head/source branch name')
    pr_list.add_argument(
        '--state',
        default='open',
        choices=['open', 'closed', 'all'],
        help='Filter by state (default: open)',
    )

    # pr reply — body supplied via prepare-body path-allocate pattern
    pr_reply = pr_sub.add_parser('reply', help='Reply to a PR with a comment', allow_abbrev=False)
    pr_reply.add_argument('--pr-number', required=True, type=int, help='PR number')
    add_body_consumer_args(pr_reply)

    # pr resolve-thread
    pr_resolve = pr_sub.add_parser('resolve-thread', help='Resolve a review thread', allow_abbrev=False)
    pr_resolve.add_argument('--thread-id', required=True, help='Review thread ID')

    # pr thread-reply — body supplied via prepare-body path-allocate pattern
    pr_treply = pr_sub.add_parser('thread-reply', help='Reply to a review thread', allow_abbrev=False)
    pr_treply.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_treply.add_argument('--thread-id', required=True, help='Thread/comment ID to reply to')
    add_body_consumer_args(pr_treply)

    # pr reviews
    pr_reviews = pr_sub.add_parser('reviews', help='Get PR reviews', allow_abbrev=False)
    pr_reviews.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr comments
    pr_comments = pr_sub.add_parser('comments', help='Get PR inline code comments', allow_abbrev=False)
    pr_comments.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_comments.add_argument('--unresolved-only', action='store_true', help='Only show unresolved comments')

    # pr wait-for-comments — poll until new bot comments arrive or timeout
    pr_wait_comments = pr_sub.add_parser(
        'wait-for-comments',
        help='Wait for new review comments to be posted (replaces blocking shell sleep)',
        allow_abbrev=False,
    )
    pr_wait_comments.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_wait_comments.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Max wait time in seconds (default: {DEFAULT_CI_TIMEOUT})',
    )
    pr_wait_comments.add_argument(
        '--interval',
        type=int,
        default=DEFAULT_CI_INTERVAL,
        help=f'Poll interval in seconds (default: {DEFAULT_CI_INTERVAL})',
    )

    # pr merge — accepts either --pr-number or --head (validated by handler)
    pr_merge = pr_sub.add_parser('merge', help='Merge a pull request', allow_abbrev=False)
    pr_merge.add_argument('--pr-number', type=int, help='PR number')
    add_head_arg(pr_merge)
    pr_merge.add_argument(
        '--strategy',
        default='merge',
        choices=['merge', 'squash', 'rebase'],
        help='Merge strategy (default: merge)',
    )
    pr_merge.add_argument('--delete-branch', action='store_true', help='Delete branch after merge')

    # pr auto-merge — accepts either --pr-number or --head (validated by handler)
    pr_auto = pr_sub.add_parser('auto-merge', help='Enable auto-merge on a PR', allow_abbrev=False)
    pr_auto.add_argument('--pr-number', type=int, help='PR number')
    add_head_arg(pr_auto)
    pr_auto.add_argument(
        '--strategy',
        default='merge',
        choices=['merge', 'squash', 'rebase'],
        help='Merge strategy (default: merge)',
    )

    # pr safe-merge — poll readiness, then merge; GitHub-only admin fallback on stuck state.
    # Accepts either --pr-number or --head (validated by handler). Registered once here and
    # consumed by both providers, mirroring how merge/auto-merge are shared.
    pr_safe = pr_sub.add_parser(
        'safe-merge',
        help='Poll PR readiness then merge, with a GitHub-only admin fallback on a stuck blocked state',
        allow_abbrev=False,
    )
    pr_safe.add_argument('--pr-number', type=int, help='PR number')
    add_head_arg(pr_safe)
    pr_safe.add_argument(
        '--strategy',
        default='merge',
        choices=['merge', 'squash', 'rebase'],
        help='Merge strategy (default: merge)',
    )
    pr_safe.add_argument('--delete-branch', action='store_true', help='Delete branch after merge')
    pr_safe.add_argument(
        '--admin-merge-on-stuck-state',
        dest='admin_merge_on_stuck_state',
        action='store_true',
        help='GitHub-only: when the PR stays mergeable_state=blocked past the poll timeout and every '
        'active ruleset requirement is provably met, fall back to "gh pr merge --admin"',
    )
    pr_safe.add_argument(
        '--poll-timeout',
        dest='poll_timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Max readiness-poll wait time in seconds (default: {DEFAULT_CI_TIMEOUT})',
    )
    pr_safe.add_argument(
        '--poll-interval',
        dest='poll_interval',
        type=int,
        default=DEFAULT_CI_INTERVAL,
        help=f'Readiness-poll interval in seconds (default: {DEFAULT_CI_INTERVAL})',
    )

    # pr update-branch — accepts either --pr-number or --head (validated by handler)
    pr_update_branch = pr_sub.add_parser(
        'update-branch', help='Update PR branch with base branch changes', allow_abbrev=False
    )
    pr_update_branch.add_argument('--pr-number', type=int, help='PR number')
    add_head_arg(pr_update_branch)

    # pr close
    pr_close = pr_sub.add_parser('close', help='Close a pull request', allow_abbrev=False)
    pr_close.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr ready
    pr_ready = pr_sub.add_parser('ready', help='Mark draft PR as ready for review', allow_abbrev=False)
    pr_ready.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr submit-review (GitHub safety net for recovering draft reviews)
    pr_submit = pr_sub.add_parser('submit-review', help='Submit a pending review', allow_abbrev=False)
    pr_submit.add_argument('--review-id', required=True, help='Pending PullRequestReview node id (PRR_*)')
    pr_submit.add_argument(
        '--event',
        default='COMMENT',
        choices=['COMMENT', 'APPROVE', 'REQUEST_CHANGES'],
        help='Review event (default: COMMENT)',
    )

    # pr edit — body optionally supplied via prepare-body path-allocate pattern
    pr_edit = pr_sub.add_parser('edit', help='Edit PR title and/or body', allow_abbrev=False)
    pr_edit.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_edit.add_argument('--title', help='New PR title')
    add_body_consumer_args(pr_edit)

    # -- checks -------------------------------------------------------
    checks_parser = subparsers.add_parser('checks', help='CI check operations', allow_abbrev=False)
    checks_sub = checks_parser.add_subparsers(dest='checks_command', required=True)

    # checks status — accepts either --pr-number or --head (validated by handler)
    ci_status = checks_sub.add_parser('status', help='Check CI status', allow_abbrev=False)
    ci_status.add_argument('--pr-number', type=int, help='PR number')
    add_head_arg(ci_status)
    add_error_style_arg(ci_status)

    # checks wait
    ci_wait = checks_sub.add_parser('wait', help='Wait for CI to complete', allow_abbrev=False)
    ci_wait.add_argument('--pr-number', required=True, type=int, help='PR number')
    add_error_style_arg(ci_wait)
    ci_wait.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Max wait time in seconds (default: {DEFAULT_CI_TIMEOUT})',
    )
    ci_wait.add_argument('--interval', type=int, default=30, help='Poll interval in seconds (default: 30)')

    # checks rerun
    ci_rerun = checks_sub.add_parser('rerun', help='Rerun a workflow/pipeline', allow_abbrev=False)
    ci_rerun.add_argument('--run-id', required=True, help='Run/pipeline ID')

    # checks logs
    ci_logs = checks_sub.add_parser('logs', help='Get failed run/job logs', allow_abbrev=False)
    ci_logs.add_argument('--run-id', required=True, help='Run/job ID')

    # checks wait-for-status-flip — poll until PR CI status flips from pending or timeout
    ci_wait_status_flip = checks_sub.add_parser(
        'wait-for-status-flip',
        help='Wait for PR CI status to flip from pending (replaces blocking shell sleep)',
        allow_abbrev=False,
    )
    ci_wait_status_flip.add_argument('--pr-number', required=True, type=int, help='PR number')
    ci_wait_status_flip.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Max wait time in seconds (default: {DEFAULT_CI_TIMEOUT})',
    )
    ci_wait_status_flip.add_argument(
        '--interval',
        type=int,
        default=DEFAULT_CI_INTERVAL,
        help=f'Poll interval in seconds (default: {DEFAULT_CI_INTERVAL})',
    )
    ci_wait_status_flip.add_argument(
        '--expected',
        choices=['success', 'failure', 'any'],
        default='any',
        help='Wait until status flips to this value; default any non-pending flip',
    )

    # -- issue --------------------------------------------------------
    issue_parser = subparsers.add_parser('issue', help='Issue operations', allow_abbrev=False)
    issue_sub = issue_parser.add_subparsers(dest='issue_command', required=True)

    # issue create — body supplied via prepare-body path-allocate pattern
    issue_create = issue_sub.add_parser('create', help='Create an issue', allow_abbrev=False)
    issue_create.add_argument('--title', required=True, help='Issue title')
    issue_create.add_argument('--labels', help='Comma-separated labels')
    add_body_consumer_args(issue_create)

    # issue prepare-body — allocate scratch path for the description
    issue_prepare = issue_sub.add_parser(
        'prepare-body',
        help='Allocate a scratch path for the issue description (path-allocate pattern)',
        allow_abbrev=False,
    )
    add_plan_id_arg(issue_prepare)
    issue_prepare.add_argument('--slot', default=None, help='Optional slot identifier (default: "default")')

    # issue comment — body supplied via prepare-comment path-allocate pattern
    issue_comment = issue_sub.add_parser(
        'comment',
        help='Post a comment on an existing issue',
        allow_abbrev=False,
    )
    issue_comment.add_argument('--issue', required=True, help='Issue number or URL')
    add_body_consumer_args(issue_comment)

    # issue prepare-comment — allocate scratch path for the comment body
    issue_prepare_comment = issue_sub.add_parser(
        'prepare-comment',
        help='Allocate a scratch path for an issue comment (path-allocate pattern)',
        allow_abbrev=False,
    )
    add_plan_id_arg(issue_prepare_comment)
    issue_prepare_comment.add_argument(
        '--slot', default=None, help='Optional slot identifier (default: "default")'
    )

    # pr prepare-body — allocate scratch path for PR create description
    pr_prepare_body = pr_sub.add_parser(
        'prepare-body',
        help='Allocate a scratch path for a PR body (create/edit) (path-allocate pattern)',
        allow_abbrev=False,
    )
    add_plan_id_arg(pr_prepare_body)
    pr_prepare_body.add_argument(
        '--for',
        dest='prepare_for',
        choices=['create', 'edit'],
        default='create',
        help='Which consumer this body is prepared for (default: create)',
    )
    pr_prepare_body.add_argument('--slot', default=None, help='Optional slot identifier (default: "default")')

    # pr prepare-comment — allocate scratch path for reply / thread-reply bodies
    pr_prepare_comment = pr_sub.add_parser(
        'prepare-comment',
        help='Allocate a scratch path for a PR comment (reply / thread-reply) (path-allocate pattern)',
        allow_abbrev=False,
    )
    add_plan_id_arg(pr_prepare_comment)
    pr_prepare_comment.add_argument(
        '--for',
        dest='prepare_for',
        choices=['reply', 'thread-reply'],
        default='reply',
        help='Which consumer this body is prepared for (default: reply)',
    )
    pr_prepare_comment.add_argument('--slot', default=None, help='Optional slot identifier (default: "default")')

    # issue view
    issue_view = issue_sub.add_parser('view', help='View issue details', allow_abbrev=False)
    issue_view.add_argument('--issue', required=True, help='Issue number or URL')

    # issue close
    issue_close = issue_sub.add_parser('close', help='Close an issue', allow_abbrev=False)
    issue_close.add_argument('--issue', required=True, help='Issue number or URL')

    # issue wait-for-close — poll until the issue transitions to closed or timeout
    issue_wait_close = issue_sub.add_parser(
        'wait-for-close',
        help='Wait for issue to close (replaces blocking shell sleep)',
        allow_abbrev=False,
    )
    issue_wait_close.add_argument('--issue-number', required=True, type=int, help='Issue number')
    issue_wait_close.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Max wait time in seconds (default: {DEFAULT_CI_TIMEOUT})',
    )
    issue_wait_close.add_argument(
        '--interval',
        type=int,
        default=DEFAULT_CI_INTERVAL,
        help=f'Poll interval in seconds (default: {DEFAULT_CI_INTERVAL})',
    )

    # issue wait-for-label — poll until a label appears/disappears on the issue or timeout
    issue_wait_label = issue_sub.add_parser(
        'wait-for-label',
        help='Wait for a label to be added or removed on an issue (replaces blocking shell sleep)',
        allow_abbrev=False,
    )
    issue_wait_label.add_argument('--issue-number', required=True, type=int, help='Issue number')
    issue_wait_label.add_argument('--label', required=True, help='Label name to watch')
    issue_wait_label.add_argument(
        '--mode',
        choices=['present', 'absent'],
        default='present',
        help='Wait for label to be present (default) or absent',
    )
    issue_wait_label.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Max wait time in seconds (default: {DEFAULT_CI_TIMEOUT})',
    )
    issue_wait_label.add_argument(
        '--interval',
        type=int,
        default=DEFAULT_CI_INTERVAL,
        help=f'Poll interval in seconds (default: {DEFAULT_CI_INTERVAL})',
    )

    # -- branch -------------------------------------------------------
    branch_parser = subparsers.add_parser('branch', help='Branch operations', allow_abbrev=False)
    branch_sub = branch_parser.add_subparsers(dest='branch_command', required=True)

    # branch delete — remote branch deletion via REST API.
    # The --remote-only flag is required and explicit: it signals that the caller has
    # already handled any local cleanup and the operation targets only the remote ref.
    # No local-branch mode is provided; local branches are managed via `git -C {path} branch`.
    branch_delete = branch_sub.add_parser(
        'delete',
        help='Delete a remote branch via REST API',
        allow_abbrev=False,
    )
    branch_delete.add_argument(
        '--remote-only',
        action='store_true',
        required=True,
        help='Required flag: confirms the operation targets only the remote branch',
    )
    branch_delete.add_argument(
        '--branch',
        required=True,
        help='Branch name to delete from the remote',
    )

    return parser, pr_sub, checks_sub, issue_sub, branch_sub


def add_pr_create_args(
    pr_subparsers: argparse._SubParsersAction,
) -> None:
    """Add 'pr create' sub-parser.

    The PR body is supplied via the path-allocate pattern: callers first run
    ``pr prepare-body --plan-id {id}`` to allocate a scratch path, write the
    body content to that path with their native Write/Edit tools, then invoke
    ``pr create --plan-id {id}``. No multi-line body content crosses the
    shell boundary.
    """
    pr_create = pr_subparsers.add_parser('create', help='Create a pull request', allow_abbrev=False)
    pr_create.add_argument('--title', required=True, help='PR title')
    add_body_consumer_args(pr_create)
    pr_create.add_argument('--base', help='Base/target branch (default: repo default)')
    pr_create.add_argument('--draft', action='store_true', help='Create as draft PR')
    pr_create.add_argument(
        '--head',
        help='Source branch (default: current cwd HEAD). Required when invoking from a different '
        'checkout than the worktree containing the source branch — e.g., when phase-6-finalize runs '
        'from the main checkout against a worktree-isolated plan branch.',
    )


def add_head_arg(subparser: argparse.ArgumentParser) -> None:
    """Register an optional ``--head BRANCH`` argument on a PR/CI subparser.

    Used by provider scripts on operations that identify a PR by branch when no
    explicit ``--pr-number`` is supplied: ``pr view``, ``pr merge``, ``pr auto-merge``,
    and ``checks status``. Provider handlers MUST treat ``--head`` as a branch-as-identifier
    substitute and validate that exactly one of ``--pr-number`` / ``--head`` is supplied.

    The flag is purely additive — operations behave as before when ``--head`` is omitted.
    Its purpose is to make branch-aware operations usable from a cwd whose HEAD is not
    the branch the caller wants to operate on (the worktree-isolation use case).
    """
    subparser.add_argument(
        '--head',
        help='Source branch — alternative to --pr-number for branch-identified lookups. '
        'Required when invoking from a different checkout than the worktree containing the branch.',
    )


def add_error_style_arg(subparser: argparse.ArgumentParser) -> None:
    """Register the ``--error-style`` selector on a checks subparser.

    Governs the failure-log filter heuristic applied by
    :func:`enrich_failing_checks_with_logs` when ``checks wait`` / ``checks
    status`` detect a failure: ``maven`` / ``gradle`` / ``npm`` route through
    the per-system build parsers, ``generic`` (the default) applies the
    context-window heuristic.
    """
    subparser.add_argument(
        '--error-style',
        dest='error_style',
        default='generic',
        choices=('maven', 'gradle', 'npm', 'generic'),
        help='Failure-log filter heuristic (default: generic)',
    )


def add_pr_resolve_thread_pr_number(
    pr_subparsers: argparse._SubParsersAction,
) -> None:
    """Add --pr-number to the resolve-thread sub-parser (GitLab requires it, GitHub accepts it for uniformity)."""
    # The resolve-thread parser was already created by build_parser.
    # We need to add --pr-number to it. Access it via choices.
    resolve_parser = pr_subparsers.choices.get('resolve-thread')
    if resolve_parser:
        resolve_parser.add_argument('--pr-number', required=True, type=int, help='PR number')


# ---------------------------------------------------------------------------
# Generic handler factories for simple operations
# ---------------------------------------------------------------------------


def make_simple_handler(
    operation: str,
    build_args_fn: Any,
    run_fn: Any,
    auth_fn: Any,
    *,
    result_extras: Any = None,
) -> Any:
    """Create a handler for simple CLI operations that follow the auth-build-run-output pattern.

    Args:
        operation: Operation name for TOON output (e.g. 'pr_close').
        build_args_fn: Callable(args) -> list[str] that builds CLI arguments.
        run_fn: The provider's run_<cli> wrapper.
        auth_fn: Callable() -> (bool, str) to check authentication.
        result_extras: Optional callable(args) -> dict of extra fields for output.

    Returns:
        A handler function suitable for the dispatch table.
    """

    def handler(args: argparse.Namespace) -> dict:
        is_auth, err = auth_fn()
        if not is_auth:
            return make_error(operation, err)

        cli_args = build_args_fn(args)
        returncode, stdout, stderr = run_fn(cli_args)
        if returncode != 0:
            return make_error(operation, 'Operation failed', stderr.strip())

        result = {'status': 'success', 'operation': operation}
        if result_extras:
            result.update(result_extras(args))

        return result

    return handler


def make_pr_number_handler(
    operation: str,
    cli_args_fn: Any,
    run_fn: Any,
    auth_fn: Any,
) -> Any:
    """Shortcut for handlers that only need --pr-number and produce a simple success output."""
    return make_simple_handler(
        operation,
        cli_args_fn,
        run_fn,
        auth_fn,
        result_extras=lambda args: {'pr_number': args.pr_number},
    )


# ---------------------------------------------------------------------------
# CI check formatting (shared between GitHub and GitLab)
# ---------------------------------------------------------------------------

MAX_ELAPSED_SECONDS = 24 * 3600


def _is_zero_time(iso: str | None) -> bool:
    """Return True when ``iso`` is a Go zero-value timestamp or otherwise unusable.

    The provider CLIs (``gh``, ``glab``) emit Go's zero-value time
    ``0001-01-01T00:00:00Z`` for never-started checks. Treating that string as
    a real timestamp produces ~63.9 billion-second elapsed values. A timestamp
    is considered "zero" when it is:

    - falsy (``None`` or empty string)
    - prefixed with ``0001-01-01`` (Go zero-value sentinel)
    - parses to a ``datetime`` with year ≤ 1971 (pre-Unix-epoch sentinels)

    Strings that fail to parse are treated as zero-time to be safe.
    """
    if not iso:
        return True
    if iso.startswith('0001-01-01'):
        return True
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return True
    return dt.year <= 1971


def compute_elapsed(started_at: str | None, completed_at: str | None, now: datetime) -> int | None:
    """Compute elapsed seconds from ISO timestamps.

    Returns ``None`` when:

    - ``started_at`` is a Go zero-value or otherwise unusable timestamp
      (see :func:`_is_zero_time`)
    - parsing fails for any provided timestamp
    - the computed elapsed value is negative (clamped to ``None`` rather than
      leaking a small negative integer when ``completed_at < started_at`` due
      to a sub-second precision artifact)

    Returns a non-negative ``int`` on success.
    """
    if _is_zero_time(started_at):
        return None
    try:
        start_dt = datetime.fromisoformat(started_at)  # type: ignore[arg-type]
        if completed_at and not _is_zero_time(completed_at):
            end_dt = datetime.fromisoformat(completed_at)
            elapsed = int((end_dt - start_dt).total_seconds())
        else:
            elapsed = int((now - start_dt).total_seconds())
    except (ValueError, TypeError):
        return None
    if elapsed < 0:
        return None
    return elapsed


def compute_total_elapsed(started_at_values: list[str | None], now: datetime) -> int:
    """Compute total elapsed from earliest non-zero-time start to now.

    Skips entries for which :func:`_is_zero_time` returns ``True`` so that
    Go zero-value sentinels (e.g. ``0001-01-01T00:00:00Z`` from never-started
    checks) do not poison the aggregate. Returns ``0`` when no usable
    timestamp is present.
    """
    earliest = None
    for val in started_at_values:
        if _is_zero_time(val):
            continue
        try:
            dt = datetime.fromisoformat(val)  # type: ignore[arg-type]
            if earliest is None or dt < earliest:
                earliest = dt
        except (ValueError, TypeError):
            continue
    return int((now - earliest).total_seconds()) if earliest else 0


def determine_overall_ci_status(
    checks: list[dict], pass_key: str, fail_key: str, pending_key: str, skip_key: str
) -> str:
    """Determine overall CI status from a list of check dicts.

    Args:
        checks: Raw check/job dicts from the provider.
        pass_key: Value indicating a passed check (e.g. 'pass' for GitHub, 'success' for GitLab).
        fail_key: Value indicating a failed check.
        pending_key: Value indicating a pending check.
        skip_key: Value indicating a skipped check.

    Returns:
        One of: 'success', 'failure', 'pending', 'none'.
    """
    if not checks:
        return 'none'

    statuses = [c.get('_resolved_status', '') for c in checks]
    if all(s in (pass_key, skip_key) for s in statuses):
        return 'success'
    if any(s == fail_key for s in statuses):
        return 'failure'
    return 'pending'


# ---------------------------------------------------------------------------
# Polling framework (shared between ci wait and await_until patterns)
# ---------------------------------------------------------------------------


def poll_until(
    check_fn: Any,
    is_complete_fn: Any,
    *,
    timeout: int = DEFAULT_CI_TIMEOUT,
    interval: int = DEFAULT_CI_INTERVAL,
) -> dict:
    """Generic polling loop that calls check_fn until is_complete_fn returns True.

    Args:
        check_fn: Callable() -> (ok: bool, data: dict). Called each poll iteration.
                  If ok is False, the error is propagated immediately.
        is_complete_fn: Callable(data: dict) -> bool. Returns True when polling should stop.
        timeout: Max wait time in seconds.
        interval: Sleep duration between polls in seconds.

    Returns:
        Dict with keys: 'timed_out' (bool), 'duration_sec' (int), 'polls' (int),
        'last_data' (dict from last successful check_fn call).
    """
    start_time = time.time()
    polls = 0
    last_data: dict = {}

    while True:
        polls += 1
        elapsed = time.time() - start_time

        if elapsed >= timeout:
            return {
                'timed_out': True,
                'duration_sec': int(elapsed),
                'polls': polls,
                'last_data': last_data,
            }

        ok, data = check_fn()
        if not ok:
            return {
                'timed_out': False,
                'duration_sec': int(time.time() - start_time),
                'polls': polls,
                'last_data': data,
                'error': data.get('error', 'Check failed'),
            }

        last_data = data
        if is_complete_fn(data):
            return {
                'timed_out': False,
                'duration_sec': int(time.time() - start_time),
                'polls': polls,
                'last_data': data,
            }

        time.sleep(interval)


# ---------------------------------------------------------------------------
# CI log truncation (shared between GitHub and GitLab)
# ---------------------------------------------------------------------------


def truncate_log_content(stdout: str, max_lines: int = CI_LOG_TRUNCATE_LINES) -> tuple[str, int]:
    """Truncate log output and escape for TOON.

    Returns (escaped_content, line_count).
    """
    lines = stdout.splitlines()
    truncated = lines[:max_lines]
    content = '\n'.join(truncated)
    return content.replace(chr(10), '\\n'), len(truncated)


# ---------------------------------------------------------------------------
# Failure-path log download + filter + store (shared between GitHub/GitLab)
# ---------------------------------------------------------------------------


def _load_persist():
    """Lazily load ``manage-ci-artifacts.persist`` from the sibling skill.

    The persistence layer lives in the ``manage-ci-artifacts`` skill with a
    hyphenated filename, so it is loaded via ``importlib`` rather than a plain
    import. Returns the ``persist`` callable, or ``None`` when the module
    cannot be located/loaded (callers degrade gracefully rather than raise).
    """
    import importlib.util

    scripts_dir = Path(__file__).resolve().parent  # .../tools-integration-ci/scripts
    skills_dir = scripts_dir.parent.parent  # .../skills
    module_path = skills_dir / 'manage-ci-artifacts' / 'scripts' / 'manage-ci-artifacts.py'
    if not module_path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location('manage_ci_artifacts', module_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:
        return None
    return getattr(module, 'persist', None)


def enrich_failing_checks_with_logs(
    *,
    failing_checks: list[dict],
    provider: str,
    raw_log_fetcher: Any,
    plan_id: str | None,
    error_style: str = 'generic',
) -> list[dict]:
    """Enrich each failing-check entry with its downloaded raw + filtered logs.

    Iterates ``failing_checks`` and, for every entry, derives a collision-free
    file slug from ``job_name`` (falling back to ``name``), downloads that
    check's raw log via ``raw_log_fetcher``, persists the raw log plus a
    filtered error-extraction variant under
    ``artifacts/ci-runs/{run_id}/{slug}.log`` and ``{slug}.filtered.log``
    through the ``manage-ci-artifacts`` storage layout, and appends the
    plan-dir-relative ``log_file`` / ``filtered_log_file`` paths back onto the
    entry. Two failing checks sharing one ``run_id`` get distinctly-slugged
    files and never collide.

    Args:
        failing_checks: The provider's ``failing_checks[]`` entries (each
            carrying at least ``name``/``job_name``/``run_id``). Mutated in
            place AND returned for convenience.
        provider: ``github`` or ``gitlab`` — recorded in the manifest.
        raw_log_fetcher: Callable ``(run_id: str, job_id: str) -> str | None``
            returning the raw failing-job log for a run, or ``None``/raising on
            failure. ``job_id`` is the entry's nested job id (non-empty for
            reusable-workflow callers) so the fetcher can target the called job;
            GitLab-style fetchers accept and ignore it.
        plan_id: Plan identifier locating the artifact tree. When ``None`` the
            hook is a no-op enrichment (every entry keeps empty path fields).
        error_style: One of ``maven|gradle|npm|generic`` (default ``generic``)
            governing the filter heuristic.

    Returns:
        The same list, with ``log_file`` / ``filtered_log_file`` set on each
        entry (empty strings on any entry whose ``run_id`` is missing or whose
        download/persist failed — per-entry graceful degradation, never raises).
    """
    persist = _load_persist() if plan_id else None
    filter_log, _slugify = _load_log_filter()

    for entry in failing_checks:
        entry.setdefault('log_file', '')
        entry.setdefault('filtered_log_file', '')
        entry.setdefault('error_style', error_style)

        run_id = entry.get('run_id') or ''
        if not plan_id or not run_id or persist is None or filter_log is None or _slugify is None:
            continue

        try:
            slug = _slugify(entry.get('job_name') or entry.get('name') or '')
            raw_log = raw_log_fetcher(run_id, entry.get('job_id') or '')
            if raw_log is None:
                continue
            filtered = filter_log(raw_log, error_style)
            job = {
                'name': entry.get('name', ''),
                'workflow_name': entry.get('workflow_name') or '',
                'job_name': entry.get('job_name') or '',
                'conclusion': entry.get('conclusion') or '',
                'started_at': entry.get('started_at') or '',
                'completed_at': entry.get('completed_at') or '',
                'run_url': entry.get('run_url') or '',
                'slug': slug,
                'raw_content': raw_log,
                'filtered_content': filtered,
            }
            result = persist(
                plan_id=plan_id,
                run_id=run_id,
                head_sha=entry.get('head_sha', '') or '',
                pr_number=entry.get('pr_number', '') or '',
                provider=provider,
                jobs=[job],
            )
            if result.get('status') != 'success':
                continue
            entry['log_file'] = _select_slug_path(result.get('log_paths'), slug, '.log')
            entry['filtered_log_file'] = _select_slug_path(
                result.get('filtered_log_paths'), slug, '.filtered.log'
            )
        except Exception:
            # Per-entry graceful degradation: a single failure must never
            # abort enrichment of the remaining entries or raise.
            continue

    return failing_checks


def _select_slug_path(paths: Any, slug: str, suffix: str) -> str:
    """Pick the path matching ``{slug}{suffix}`` from a persist result list."""
    if not paths:
        return ''
    target = f'{slug}{suffix}'
    for path in paths:
        if str(path).endswith(target):
            return str(path)
    return ''


def _load_log_filter():
    """Lazily import ``filter_log`` and ``slugify_check_name`` from this skill.

    Both live in the sibling ``_ci_log_filter`` module in this skill's scripts
    directory. Returns ``(filter_log, slugify_check_name)`` or ``(None, None)``
    when the module is unavailable (callers degrade gracefully).
    """
    try:
        from _ci_log_filter import (
            filter_log,
            slugify_check_name,
        )
    except ImportError:
        return None, None
    return filter_log, slugify_check_name


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

# Handler map type: maps (command, subcommand) -> handler function
HandlerMap = dict[tuple[str, str], Any]


def dispatch(args: argparse.Namespace, handlers: HandlerMap, parser: argparse.ArgumentParser) -> dict:
    """Route parsed args to the correct handler function.

    Args:
        args: Parsed argparse namespace.
        handlers: Dict mapping ``(command, subcommand)`` to handler callables.
        parser: Top-level parser (used for fallback help output).

    Returns:
        Result dict from the matched handler, or error dict if no match found.
    """
    command = args.command

    if command == 'pr':
        key = ('pr', args.pr_command)
    elif command == 'checks':
        key = ('checks', args.checks_command)
    elif command == 'issue':
        key = ('issue', args.issue_command)
    elif command == 'branch':
        key = ('branch', args.branch_command)
    else:
        parser.print_help()
        return make_error('dispatch', 'Unknown command')

    handler = handlers.get(key)
    if handler:
        result: dict = handler(args)
        return result

    parser.print_help()
    return make_error('dispatch', f'Unknown subcommand for {command}')
