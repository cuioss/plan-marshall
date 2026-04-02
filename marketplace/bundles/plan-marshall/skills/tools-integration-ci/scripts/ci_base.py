#!/usr/bin/env python3
"""Shared base module for CI provider scripts (GitHub, GitLab).

Provides unified CLI runner, auth checker, error output, parser builder,
and command dispatch. Each provider imports from here and supplies
provider-specific handler functions and CLI details.

This module uses only stdlib imports -- no serialize_toon dependency.
"""

import argparse
import subprocess
import sys
from typing import Any

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1


# ---------------------------------------------------------------------------
# CLI execution
# ---------------------------------------------------------------------------

def run_cli(
    cli_name: str,
    args: list[str],
    *,
    capture_json: bool = False,
    timeout: int = 60,
    not_found_msg: str = '',
) -> tuple[int, str, str]:
    """Run a CLI command and return (returncode, stdout, stderr).

    Args:
        cli_name: CLI executable name (e.g. 'gh', 'glab').
        args: Arguments to pass after the CLI name.
        capture_json: If True, append ``--json`` when not already present
                      (GitHub-specific convenience).
        timeout: Subprocess timeout in seconds.
        not_found_msg: Error message when the CLI binary is missing.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    cmd = [cli_name] + args
    if capture_json and '--json' not in args:
        cmd.append('--json')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
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
# Error output (manual TOON to stderr -- no serialize_toon dependency)
# ---------------------------------------------------------------------------

def output_error(operation: str, error: str, context: str = '') -> int:
    """Output error in TOON format to stderr and return EXIT_ERROR."""
    print('status: error', file=sys.stderr)
    print(f'operation: {operation}', file=sys.stderr)
    print(f'error: {error}', file=sys.stderr)
    if context:
        print(f'context: {context}', file=sys.stderr)
    return EXIT_ERROR


# ---------------------------------------------------------------------------
# Argument parser builder
# ---------------------------------------------------------------------------

def build_parser(description: str) -> tuple[
    argparse.ArgumentParser,
    argparse._SubParsersAction,
    argparse._SubParsersAction,
    argparse._SubParsersAction,
]:
    """Build the 3-tier argparse tree shared by all CI providers.

    Returns:
        ``(parser, pr_subparsers, ci_subparsers, issue_subparsers)``
        so that providers can customise individual sub-parsers if needed.
    """
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers(dest='command', required=True)

    # -- pr -----------------------------------------------------------
    pr_parser = subparsers.add_parser('pr', help='Pull request operations')
    pr_sub = pr_parser.add_subparsers(dest='pr_command', required=True)

    # pr view
    pr_sub.add_parser('view', help='View PR for current branch')

    # pr list
    pr_list = pr_sub.add_parser('list', help='List pull requests')
    pr_list.add_argument('--head', help='Filter by head/source branch name')
    pr_list.add_argument(
        '--state', default='open', choices=['open', 'closed', 'all'],
        help='Filter by state (default: open)',
    )

    # pr reply
    pr_reply = pr_sub.add_parser('reply', help='Reply to a PR with a comment')
    pr_reply.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_reply.add_argument('--body', required=True, help='Comment text')

    # pr resolve-thread
    pr_resolve = pr_sub.add_parser('resolve-thread', help='Resolve a review thread')
    pr_resolve.add_argument('--thread-id', required=True, help='Review thread ID')

    # pr thread-reply
    pr_treply = pr_sub.add_parser('thread-reply', help='Reply to a review thread')
    pr_treply.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_treply.add_argument('--thread-id', required=True, help='Thread/comment ID to reply to')
    pr_treply.add_argument('--body', required=True, help='Reply text')

    # pr reviews
    pr_reviews = pr_sub.add_parser('reviews', help='Get PR reviews')
    pr_reviews.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr comments
    pr_comments = pr_sub.add_parser('comments', help='Get PR inline code comments')
    pr_comments.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_comments.add_argument('--unresolved-only', action='store_true', help='Only show unresolved comments')

    # pr merge
    pr_merge = pr_sub.add_parser('merge', help='Merge a pull request')
    pr_merge.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_merge.add_argument(
        '--strategy', default='merge', choices=['merge', 'squash', 'rebase'],
        help='Merge strategy (default: merge)',
    )
    pr_merge.add_argument('--delete-branch', action='store_true', help='Delete branch after merge')

    # pr auto-merge
    pr_auto = pr_sub.add_parser('auto-merge', help='Enable auto-merge on a PR')
    pr_auto.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_auto.add_argument(
        '--strategy', default='merge', choices=['merge', 'squash', 'rebase'],
        help='Merge strategy (default: merge)',
    )

    # pr close
    pr_close = pr_sub.add_parser('close', help='Close a pull request')
    pr_close.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr ready
    pr_ready = pr_sub.add_parser('ready', help='Mark draft PR as ready for review')
    pr_ready.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr edit
    pr_edit = pr_sub.add_parser('edit', help='Edit PR title and/or body')
    pr_edit.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_edit.add_argument('--title', help='New PR title')
    pr_edit.add_argument('--body', help='New PR body')

    # -- ci -----------------------------------------------------------
    ci_parser = subparsers.add_parser('ci', help='CI operations')
    ci_sub = ci_parser.add_subparsers(dest='ci_command', required=True)

    # ci status
    ci_status = ci_sub.add_parser('status', help='Check CI status')
    ci_status.add_argument('--pr-number', required=True, type=int, help='PR number')

    # ci wait
    ci_wait = ci_sub.add_parser('wait', help='Wait for CI to complete')
    ci_wait.add_argument('--pr-number', required=True, type=int, help='PR number')
    ci_wait.add_argument('--timeout', type=int, default=300, help='Max wait time in seconds (default: 300)')
    ci_wait.add_argument('--interval', type=int, default=30, help='Poll interval in seconds (default: 30)')

    # ci rerun
    ci_rerun = ci_sub.add_parser('rerun', help='Rerun a workflow/pipeline')
    ci_rerun.add_argument('--run-id', required=True, help='Run/pipeline ID')

    # ci logs
    ci_logs = ci_sub.add_parser('logs', help='Get failed run/job logs')
    ci_logs.add_argument('--run-id', required=True, help='Run/job ID')

    # -- issue --------------------------------------------------------
    issue_parser = subparsers.add_parser('issue', help='Issue operations')
    issue_sub = issue_parser.add_subparsers(dest='issue_command', required=True)

    # issue create
    issue_create = issue_sub.add_parser('create', help='Create an issue')
    issue_create.add_argument('--title', required=True, help='Issue title')
    issue_create.add_argument('--body', required=True, help='Issue description')
    issue_create.add_argument('--labels', help='Comma-separated labels')

    # issue view
    issue_view = issue_sub.add_parser('view', help='View issue details')
    issue_view.add_argument('--issue', required=True, help='Issue number or URL')

    # issue close
    issue_close = issue_sub.add_parser('close', help='Close an issue')
    issue_close.add_argument('--issue', required=True, help='Issue number or URL')

    return parser, pr_sub, ci_sub, issue_sub


def add_pr_create_args(
    pr_subparsers: argparse._SubParsersAction,
    *,
    body_required: bool = False,
    body_file: bool = False,
) -> None:
    """Add 'pr create' sub-parser with provider-specific variations.

    Args:
        pr_subparsers: The pr-level subparsers action.
        body_required: Whether ``--body`` is required (GitLab) or optional (GitHub).
        body_file: Whether to add ``--body-file`` argument (GitHub only).
    """
    pr_create = pr_subparsers.add_parser('create', help='Create a pull request')
    pr_create.add_argument('--title', required=True, help='PR title')
    if body_required:
        pr_create.add_argument('--body', required=True, help='PR description')
    else:
        pr_create.add_argument('--body', default='', help='PR description')
    if body_file:
        pr_create.add_argument('--body-file', help='Read PR body from file (takes precedence over --body)')
    pr_create.add_argument('--base', help='Base/target branch (default: repo default)')
    pr_create.add_argument('--draft', action='store_true', help='Create as draft PR')


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
    result_extras: dict | None = None,
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
    from toon_parser import serialize_toon  # type: ignore[import-not-found]

    def handler(args: argparse.Namespace) -> int:
        is_auth, err = auth_fn()
        if not is_auth:
            return output_error(operation, err)

        cli_args = build_args_fn(args)
        returncode, stdout, stderr = run_fn(cli_args)
        if returncode != 0:
            return output_error(operation, f'Operation failed', stderr.strip())

        result = {'status': 'success', 'operation': operation}
        if result_extras:
            result.update(result_extras(args))

        print(serialize_toon(result, table_separator='\t'))
        return 0

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
# Command dispatch
# ---------------------------------------------------------------------------

# Handler map type: maps (command, subcommand) -> handler function
HandlerMap = dict[tuple[str, str], Any]


def dispatch(args: argparse.Namespace, handlers: HandlerMap, parser: argparse.ArgumentParser) -> int:
    """Route parsed args to the correct handler function.

    Args:
        args: Parsed argparse namespace.
        handlers: Dict mapping ``(command, subcommand)`` to handler callables.
        parser: Top-level parser (used for fallback help output).

    Returns:
        Exit code from the matched handler, or 1 if no match found.
    """
    command = args.command

    if command == 'pr':
        key = ('pr', args.pr_command)
    elif command == 'ci':
        key = ('ci', args.ci_command)
    elif command == 'issue':
        key = ('issue', args.issue_command)
    else:
        parser.print_help()
        return 1

    handler = handlers.get(key)
    if handler:
        result: int = handler(args)
        return result

    parser.print_help()
    return EXIT_ERROR
