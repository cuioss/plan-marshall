#!/usr/bin/env python3
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
    scripts_dir = Path(__file__).resolve().parent          # .../tools-integration-ci/scripts
    skills_dir = scripts_dir.parent.parent                 # .../skills

    sibling_dirs = [
        skills_dir / 'tools-file-ops' / 'scripts',
        skills_dir / 'ref-toon-format' / 'scripts',
    ]
    for d in sibling_dirs:
        d_str = str(d)
        if d.is_dir() and d_str not in sys.path:
            sys.path.insert(0, d_str)

_ensure_sibling_skill_paths()

from file_ops import get_plan_dir, output_toon, safe_main  # type: ignore[import-not-found]  # noqa: E402, F401
from toon_parser import parse_toon, serialize_toon  # type: ignore[import-not-found]  # noqa: E402, F401

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

VALID_BODY_KINDS = frozenset(
    {
        BODY_KIND_PR_CREATE,
        BODY_KIND_PR_EDIT,
        BODY_KIND_PR_REPLY,
        BODY_KIND_PR_THREAD_REPLY,
        BODY_KIND_ISSUE_CREATE,
    }
)

_BODY_SLOT_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')


def _resolve_body_slot(slot: str | None) -> str:
    """Validate an optional slot identifier; default to 'default'."""
    if slot is None or slot == '':
        return 'default'
    if not _BODY_SLOT_RE.match(slot):
        raise ValueError(
            f"Invalid slot '{slot}': must match [a-z0-9][a-z0-9-]{{0,63}}"
        )
    return slot


def get_body_path(plan_id: str, kind: str, slot: str | None = None) -> Path:
    """Return the script-owned scratch path for a body of the given kind.

    The layout is `<plan>/work/ci-bodies/{kind}-{slot}.md`. The file is NOT
    created here — callers use `prepare_body` to allocate and pre-create the
    parent directory, then write content with their native Write/Edit tools.
    """
    if kind not in VALID_BODY_KINDS:
        raise ValueError(
            f"Invalid body kind '{kind}'. Valid kinds: {sorted(VALID_BODY_KINDS)}"
        )
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
    `issue create`).
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

# Shared defaults for CI polling operations
DEFAULT_CI_TIMEOUT = 300  # seconds
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
        ``(parser, pr_subparsers, ci_subparsers, issue_subparsers, branch_subparsers)``
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

    # pr update-branch — accepts either --pr-number or --head (validated by handler)
    pr_update_branch = pr_sub.add_parser('update-branch', help='Update PR branch with base branch changes', allow_abbrev=False)
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

    # -- ci -----------------------------------------------------------
    ci_parser = subparsers.add_parser('ci', help='CI operations', allow_abbrev=False)
    ci_sub = ci_parser.add_subparsers(dest='ci_command', required=True)

    # ci status — accepts either --pr-number or --head (validated by handler)
    ci_status = ci_sub.add_parser('status', help='Check CI status', allow_abbrev=False)
    ci_status.add_argument('--pr-number', type=int, help='PR number')
    add_head_arg(ci_status)

    # ci wait
    ci_wait = ci_sub.add_parser('wait', help='Wait for CI to complete', allow_abbrev=False)
    ci_wait.add_argument('--pr-number', required=True, type=int, help='PR number')
    ci_wait.add_argument('--timeout', type=int, default=300, help='Max wait time in seconds (default: 300)')
    ci_wait.add_argument('--interval', type=int, default=30, help='Poll interval in seconds (default: 30)')

    # ci rerun
    ci_rerun = ci_sub.add_parser('rerun', help='Rerun a workflow/pipeline', allow_abbrev=False)
    ci_rerun.add_argument('--run-id', required=True, help='Run/pipeline ID')

    # ci logs
    ci_logs = ci_sub.add_parser('logs', help='Get failed run/job logs', allow_abbrev=False)
    ci_logs.add_argument('--run-id', required=True, help='Run/job ID')

    # ci wait-for-status-flip — poll until PR CI status flips from pending or timeout
    ci_wait_status_flip = ci_sub.add_parser(
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
    issue_prepare.add_argument('--plan-id', required=True, help='Plan identifier binding the prepared body')
    issue_prepare.add_argument('--slot', default=None, help='Optional slot identifier (default: "default")')

    # pr prepare-body — allocate scratch path for PR create description
    pr_prepare_body = pr_sub.add_parser(
        'prepare-body',
        help='Allocate a scratch path for a PR body (create/edit) (path-allocate pattern)',
        allow_abbrev=False,
    )
    pr_prepare_body.add_argument('--plan-id', required=True, help='Plan identifier binding the prepared body')
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
    pr_prepare_comment.add_argument('--plan-id', required=True, help='Plan identifier binding the prepared body')
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
        help="Wait for label to be present (default) or absent",
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

    return parser, pr_sub, ci_sub, issue_sub, branch_sub


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
    and ``ci status``. Provider handlers MUST treat ``--head`` as a branch-as-identifier
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


def compute_elapsed(started_at: str | None, completed_at: str | None, now: datetime) -> int:
    """Compute elapsed seconds from ISO timestamps.

    Returns 0 on parse failure.
    """
    if not started_at:
        return 0
    try:
        start_dt = datetime.fromisoformat(started_at)
        if completed_at:
            end_dt = datetime.fromisoformat(completed_at)
            return int((end_dt - start_dt).total_seconds())
        return int((now - start_dt).total_seconds())
    except (ValueError, TypeError):
        return 0


def compute_total_elapsed(started_at_values: list[str | None], now: datetime) -> int:
    """Compute total elapsed from earliest start to now."""
    earliest = None
    for val in started_at_values:
        if not val:
            continue
        try:
            dt = datetime.fromisoformat(val)
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
    elif command == 'ci':
        key = ('ci', args.ci_command)
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
