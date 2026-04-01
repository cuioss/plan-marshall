#!/usr/bin/env python3
"""GitHub operations via gh CLI.

Subcommands:
    pr create       Create a pull request
    pr view         View PR for current branch (number, URL, state)
    pr list         List pull requests with optional filters
    pr reviews      Get PR reviews
    pr comments     Get PR review comments (inline code comments)
    pr reply        Reply to a PR with a comment
    pr resolve-thread  Resolve a review thread
    pr thread-reply    Reply to a specific review thread
    pr merge        Merge a pull request
    pr auto-merge   Enable auto-merge on a pull request
    pr close        Close a pull request
    pr ready        Mark a draft PR as ready for review
    pr edit         Edit PR title and/or body
    ci status       Check CI status for a PR
    ci wait         Wait for CI to complete
    ci rerun        Rerun a workflow run
    ci logs         Get failed run logs
    issue create    Create an issue
    issue view      View issue details
    issue close     Close an issue

Usage:
    python3 github.py pr create --title "Title" --body "Body" [--base main] [--draft]
    python3 github.py pr view
    python3 github.py pr list [--head feature/branch] [--state open|closed|all]
    python3 github.py pr reviews --pr-number 123
    python3 github.py pr comments --pr-number 123 [--unresolved-only]
    python3 github.py pr reply --pr-number 123 --body "Comment text"
    python3 github.py pr resolve-thread --thread-id PRRT_abc123
    python3 github.py pr thread-reply --pr-number 123 --thread-id PRRT_abc123 --body "Fixed"
    python3 github.py pr merge --pr-number 123 [--strategy squash] [--delete-branch]
    python3 github.py pr auto-merge --pr-number 123 [--strategy squash]
    python3 github.py pr close --pr-number 123
    python3 github.py pr ready --pr-number 123
    python3 github.py pr edit --pr-number 123 [--title "New Title"] [--body "New Body"]
    python3 github.py ci status --pr-number 123
    python3 github.py ci wait --pr-number 123 [--timeout 300] [--interval 30]
    python3 github.py ci rerun --run-id 12345
    python3 github.py ci logs --run-id 12345
    python3 github.py issue create --title "Title" --body "Body" [--labels "bug,priority:high"]
    python3 github.py issue view --issue 123
    python3 github.py issue close --issue 123

Output: TOON format
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from typing import Any

from ci_base import (  # type: ignore[import-not-found]
    add_pr_create_args,
    build_parser,
    check_auth_cli,
    dispatch,
    output_error,
    run_cli,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# CLI wrappers
# ---------------------------------------------------------------------------

def run_gh(args: list[str], capture_json: bool = False, timeout: int = 60) -> tuple[int, str, str]:
    """Run gh CLI command and return (returncode, stdout, stderr)."""
    return run_cli(
        'gh', args,
        capture_json=capture_json,
        timeout=timeout,
        not_found_msg='gh CLI not found. Install from https://cli.github.com/',
    )


def check_auth() -> tuple[bool, str]:
    """Check if gh is authenticated. Returns (is_authenticated, error_message)."""
    return check_auth_cli('gh', "Not authenticated. Run 'gh auth login' first.", run_gh)


# ---------------------------------------------------------------------------
# Provider-specific helpers
# ---------------------------------------------------------------------------

def get_repo_info() -> tuple[str | None, str | None]:
    """Get owner and repo name from git remote URL.

    Returns (owner, repo) tuple, or (None, None) if not found.
    """
    returncode, stdout, _ = run_gh(['repo', 'view', '--json', 'owner,name'])
    if returncode != 0:
        return None, None
    try:
        data = json.loads(stdout)
        return data.get('owner', {}).get('login'), data.get('name')
    except json.JSONDecodeError:
        return None, None


def run_graphql(query: str, variables: dict) -> tuple[int, dict | None, str]:
    """Run GraphQL query via gh api graphql.

    Returns (returncode, data, error).
    """
    # Build command args
    args = ['api', 'graphql', '-f', f'query={query}']
    for key, value in variables.items():
        if isinstance(value, int):
            args.extend(['-F', f'{key}={value}'])
        else:
            args.extend(['-f', f'{key}={value}'])

    returncode, stdout, stderr = run_gh(args)
    if returncode != 0:
        return returncode, None, stderr

    try:
        data = json.loads(stdout)
        if 'errors' in data:
            return 1, None, str(data['errors'])
        return 0, data.get('data'), ''
    except json.JSONDecodeError:
        return 1, None, f'Failed to parse GraphQL response: {stdout[:100]}'


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_pr_create(args: argparse.Namespace) -> int:
    """Handle 'pr create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_create', err)

    # Resolve body: --body-file takes precedence over --body
    body = args.body or ''
    if args.body_file:
        try:
            with open(args.body_file) as f:
                body = f.read()
        except OSError as e:
            return output_error('pr_create', f'Failed to read body file: {e}')

    # Build command
    gh_args = ['pr', 'create', '--title', args.title, '--body', body]
    if args.base:
        gh_args.extend(['--base', args.base])
    if args.draft:
        gh_args.append('--draft')

    # Execute
    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('pr_create', 'Failed to create PR', stderr.strip())

    # Parse the URL from output (gh pr create outputs the URL)
    pr_url = stdout.strip()

    # Get PR number from URL
    pr_number = 'unknown'
    if '/pull/' in pr_url:
        try:
            pr_number = pr_url.split('/pull/')[1].split('/')[0].split('?')[0]
        except (IndexError, ValueError):
            pass

    # Output TOON
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_create',
        'pr_number': pr_number,
        'pr_url': pr_url,
    }, table_separator='\t'))
    return 0


def cmd_pr_view(args: argparse.Namespace) -> int:
    """Handle 'pr view' subcommand - get PR for current branch."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_view', err)

    returncode, stdout, stderr = run_gh(
        ['pr', 'view', '--json',
         'number,url,state,title,headRefName,baseRefName,isDraft,mergeable,mergeStateStatus,reviewDecision']
    )
    if returncode != 0:
        return output_error('pr_view', 'No PR found for current branch', stderr.strip())

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error('pr_view', 'Failed to parse gh output', stdout[:100])

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': data.get('number', 'unknown'),
        'pr_url': data.get('url', ''),
        'state': data.get('state', 'unknown').lower(),
        'title': data.get('title', ''),
        'head_branch': data.get('headRefName', ''),
        'base_branch': data.get('baseRefName', ''),
        'is_draft': str(data.get('isDraft', False)).lower(),
        'mergeable': data.get('mergeable', 'unknown').lower() if data.get('mergeable') else 'unknown',
        'merge_state': data.get('mergeStateStatus', 'unknown').lower() if data.get('mergeStateStatus') else 'unknown',
        'review_decision': data.get('reviewDecision', 'none').lower() if data.get('reviewDecision') else 'none',
    }, table_separator='\t'))
    return 0


def cmd_pr_list(args: argparse.Namespace) -> int:
    """Handle 'pr list' subcommand - list pull requests with optional filters."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_list', err)

    gh_args = [
        'pr', 'list',
        '--json', 'number,url,title,state,headRefName,baseRefName',
        '--state', args.state,
    ]
    if args.head:
        gh_args.extend(['--head', args.head])

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('pr_list', 'Failed to list PRs', stderr.strip())

    try:
        prs = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error('pr_list', 'Failed to parse gh output', stdout[:100])

    pr_list = [
        {
            'number': pr.get('number', 0),
            'url': pr.get('url', ''),
            'title': pr.get('title', ''),
            'state': pr.get('state', 'unknown').lower(),
            'head_branch': pr.get('headRefName', ''),
            'base_branch': pr.get('baseRefName', ''),
        }
        for pr in prs
    ]
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_list',
        'total': len(prs),
        'state_filter': args.state,
        'head_filter': args.head or '',
        'prs': pr_list,
    }, table_separator='\t'))
    return 0


def cmd_pr_reply(args: argparse.Namespace) -> int:
    """Handle 'pr reply' subcommand - post a comment on a PR."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_reply', err)

    returncode, stdout, stderr = run_gh(
        ['pr', 'comment', str(args.pr_number), '--body', args.body]
    )
    if returncode != 0:
        return output_error('pr_reply', f'Failed to comment on PR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_reply',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}
"""


THREAD_REPLY_MUTATION = """
mutation($prId: ID!, $body: String!, $inReplyTo: ID!) {
  addPullRequestReviewComment(input: {pullRequestId: $prId, body: $body, inReplyTo: $inReplyTo}) {
    comment { id }
  }
}
"""


def cmd_pr_resolve_thread(args: argparse.Namespace) -> int:
    """Handle 'pr resolve-thread' subcommand - resolve a review thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_resolve_thread', err)

    returncode, data, err = run_graphql(RESOLVE_THREAD_MUTATION, {'threadId': args.thread_id})
    if returncode != 0 or data is None:
        return output_error('pr_resolve_thread', f'Failed to resolve thread: {err}')

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_resolve_thread',
        'thread_id': args.thread_id,
    }, table_separator='\t'))
    return 0


def cmd_pr_thread_reply(args: argparse.Namespace) -> int:
    """Handle 'pr thread-reply' subcommand - reply to a specific review thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_thread_reply', err)

    # Get PR node ID (GraphQL requires it)
    returncode, stdout, stderr = run_gh(['pr', 'view', str(args.pr_number), '--json', 'id'])
    if returncode != 0:
        return output_error('pr_thread_reply', f'Failed to get PR {args.pr_number}', stderr.strip())

    try:
        pr_data = json.loads(stdout)
        pr_id = pr_data.get('id', '')
    except json.JSONDecodeError:
        return output_error('pr_thread_reply', 'Failed to parse PR data', stdout[:100])

    if not pr_id:
        return output_error('pr_thread_reply', 'Could not determine PR node ID')

    returncode, data, err = run_graphql(
        THREAD_REPLY_MUTATION,
        {'prId': pr_id, 'body': args.body, 'inReplyTo': args.thread_id},
    )
    if returncode != 0 or data is None:
        return output_error('pr_thread_reply', f'Failed to reply to thread: {err}')

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_thread_reply',
        'pr_number': args.pr_number,
        'thread_id': args.thread_id,
    }, table_separator='\t'))
    return 0


def cmd_pr_reviews(args: argparse.Namespace) -> int:
    """Handle 'pr reviews' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_reviews', err)

    # Get reviews
    returncode, stdout, stderr = run_gh(['pr', 'view', str(args.pr_number), '--json', 'reviews'])
    if returncode != 0:
        return output_error('pr_reviews', f'Failed to get reviews for PR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        reviews = data.get('reviews', [])
    except json.JSONDecodeError:
        return output_error('pr_reviews', 'Failed to parse gh output', stdout[:100])

    # Output TOON
    review_list = [
        {
            'user': r.get('author', {}).get('login', 'unknown'),
            'state': r.get('state', 'UNKNOWN'),
            'submitted_at': r.get('submittedAt', '-'),
        }
        for r in reviews
    ]
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_reviews',
        'pr_number': args.pr_number,
        'review_count': len(reviews),
        'reviews': review_list,
    }, table_separator='\t'))
    return 0


# GraphQL query for PR review threads (inline code comments)
REVIEW_THREADS_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 10) {
            nodes {
              id
              body
              author { login }
              createdAt
            }
          }
        }
      }
    }
  }
}
"""


def cmd_pr_comments(args: argparse.Namespace) -> int:
    """Handle 'pr comments' subcommand - fetch inline code review comments."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_comments', err)

    # Get repo info
    owner, repo = get_repo_info()
    if not owner or not repo:
        return output_error('pr_comments', 'Could not determine repository owner/name')

    # Run GraphQL query
    returncode, data, err = run_graphql(REVIEW_THREADS_QUERY, {'owner': owner, 'repo': repo, 'pr': args.pr_number})
    if returncode != 0 or data is None:
        return output_error('pr_comments', f'GraphQL query failed: {err}')

    # Extract threads
    try:
        threads = data['repository']['pullRequest']['reviewThreads']['nodes']
    except (KeyError, TypeError) as e:
        return output_error('pr_comments', f'Failed to parse response: {e}')

    # Normalize comments
    comments: list[dict] = []
    for thread in threads:
        is_resolved = thread.get('isResolved', False)

        # Skip resolved threads if --unresolved-only
        if args.unresolved_only and is_resolved:
            continue

        path = thread.get('path', '')
        line = thread.get('line', 0)
        thread_id = thread.get('id', '')

        # Process each comment in the thread
        thread_comments = thread.get('comments', {}).get('nodes', [])
        for comment in thread_comments:
            comments.append(
                {
                    'id': comment.get('id', ''),
                    'author': comment.get('author', {}).get('login', 'unknown'),
                    'body': comment.get('body', ''),
                    'path': path,
                    'line': line,
                    'resolved': is_resolved,
                    'created_at': comment.get('createdAt', ''),
                    'thread_id': thread_id,
                }
            )

    # Output TOON
    unresolved_count = sum(1 for c in comments if not c['resolved'])
    comment_list = [
        {
            'id': c['id'],
            'thread_id': c['thread_id'],
            'author': c['author'],
            'body': c['body'].replace('\t', ' ').replace('\n', ' '),
            'path': c['path'],
            'line': c['line'],
            'resolved': c['resolved'],
            'created_at': c['created_at'],
        }
        for c in comments
    ]
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_comments',
        'provider': 'github',
        'pr_number': args.pr_number,
        'total': len(comments),
        'unresolved': unresolved_count,
        'comments': comment_list,
    }, table_separator='\t'))
    return 0


def cmd_pr_merge(args: argparse.Namespace) -> int:
    """Handle 'pr merge' subcommand - merge a pull request."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_merge', err)

    gh_args = ['pr', 'merge', str(args.pr_number), f'--{args.strategy}']
    if args.delete_branch:
        gh_args.append('--delete-branch')

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('pr_merge', f'Failed to merge PR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number,
        'strategy': args.strategy,
    }, table_separator='\t'))
    return 0


def cmd_pr_auto_merge(args: argparse.Namespace) -> int:
    """Handle 'pr auto-merge' subcommand - enable auto-merge on a pull request."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_auto_merge', err)

    gh_args = ['pr', 'merge', str(args.pr_number), '--auto', f'--{args.strategy}']

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('pr_auto_merge', f'Failed to enable auto-merge for PR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_auto_merge',
        'pr_number': args.pr_number,
        'enabled': True,
    }, table_separator='\t'))
    return 0


def cmd_pr_close(args: argparse.Namespace) -> int:
    """Handle 'pr close' subcommand - close a pull request."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_close', err)

    returncode, stdout, stderr = run_gh(['pr', 'close', str(args.pr_number)])
    if returncode != 0:
        return output_error('pr_close', f'Failed to close PR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_close',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def cmd_pr_ready(args: argparse.Namespace) -> int:
    """Handle 'pr ready' subcommand - mark a draft PR as ready for review."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_ready', err)

    returncode, stdout, stderr = run_gh(['pr', 'ready', str(args.pr_number)])
    if returncode != 0:
        return output_error('pr_ready', f'Failed to mark PR {args.pr_number} as ready', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_ready',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def cmd_pr_edit(args: argparse.Namespace) -> int:
    """Handle 'pr edit' subcommand - edit PR title and/or body."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_edit', err)

    if not args.title and not args.body:
        return output_error('pr_edit', 'At least one of --title or --body must be provided')

    gh_args = ['pr', 'edit', str(args.pr_number)]
    if args.title:
        gh_args.extend(['--title', args.title])
    if args.body:
        gh_args.extend(['--body', args.body])

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('pr_edit', f'Failed to edit PR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_edit',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def format_checks_toon(checks: list[dict]) -> tuple[list[dict], int]:
    """Format checks into dicts and compute overall elapsed.

    Returns (check_dicts, elapsed_sec_total).
    """
    now = datetime.now(UTC)
    earliest_start = None
    check_dicts: list[dict] = []

    for check in checks:
        name = check.get('name', 'unknown')
        state = check.get('state', 'unknown')
        bucket = check.get('bucket') or '-'
        link = check.get('link') or '-'
        workflow = check.get('workflow') or '-'

        # Compute elapsed_sec for this check
        started_at = check.get('startedAt')
        completed_at = check.get('completedAt')
        elapsed_sec = 0

        if started_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                if earliest_start is None or start_dt < earliest_start:
                    earliest_start = start_dt
                if completed_at:
                    end_dt = datetime.fromisoformat(completed_at)
                    elapsed_sec = int((end_dt - start_dt).total_seconds())
                else:
                    elapsed_sec = int((now - start_dt).total_seconds())
            except (ValueError, TypeError):
                elapsed_sec = 0

        check_dicts.append({
            'name': name,
            'status': state,
            'result': bucket,
            'elapsed_sec': elapsed_sec,
            'url': link,
            'workflow': workflow,
        })

    # Compute total elapsed from earliest start to now
    total_elapsed = 0
    if earliest_start:
        total_elapsed = int((now - earliest_start).total_seconds())

    return check_dicts, total_elapsed


def cmd_ci_status(args: argparse.Namespace) -> int:
    """Handle 'ci status' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_status', err)

    # Get checks (bucket field contains pass/fail result)
    returncode, stdout, stderr = run_gh(
        ['pr', 'checks', str(args.pr_number), '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
    )
    if returncode != 0:
        return output_error('ci_status', f'Failed to get CI status for PR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        checks = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error('ci_status', 'Failed to parse gh output', stdout[:100])

    # Determine overall status (bucket: pass, fail, pending, skipped)
    if not checks:
        overall = 'none'
    elif all(c.get('bucket') == 'pass' for c in checks):
        overall = 'success'
    elif any(c.get('bucket') == 'fail' for c in checks):
        overall = 'failure'
    elif all(c.get('bucket') in ('pass', 'skipped') for c in checks):
        overall = 'success'
    else:
        overall = 'pending'

    # Format checks table
    check_dicts, total_elapsed = format_checks_toon(checks)

    # Output TOON
    print(serialize_toon({
        'status': 'success',
        'operation': 'ci_status',
        'pr_number': args.pr_number,
        'overall_status': overall,
        'check_count': len(checks),
        'elapsed_sec': total_elapsed,
        'checks': check_dicts,
    }, table_separator='\t'))
    return 0


def cmd_ci_wait(args: argparse.Namespace) -> int:
    """Handle 'ci wait' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_wait', err)

    start_time = time.time()
    polls = 0
    timeout = args.timeout
    interval = args.interval
    last_checks: list[dict] = []

    while True:
        polls += 1
        elapsed = time.time() - start_time

        # Check timeout
        if elapsed >= timeout:
            # Format checks table for timeout output
            check_dicts, total_elapsed = format_checks_toon(last_checks) if last_checks else ([], 0)

            error_data: dict[str, Any] = {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'pr_number': args.pr_number,
                'duration_sec': int(elapsed),
                'last_status': 'pending',
            }
            if check_dicts:
                error_data['elapsed_sec'] = total_elapsed
                error_data['checks'] = check_dicts
            print(serialize_toon(error_data, table_separator='\t'), file=sys.stderr)
            return 1

        # Get checks (bucket field contains pass/fail result)
        returncode, stdout, stderr = run_gh(
            ['pr', 'checks', str(args.pr_number), '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
        )
        if returncode != 0:
            return output_error('ci_wait', f'Failed to get CI status for PR {args.pr_number}', stderr.strip())

        # Parse and check status
        try:
            checks = json.loads(stdout)
        except json.JSONDecodeError:
            return output_error('ci_wait', 'Failed to parse gh output', stdout[:100])

        last_checks = checks

        # Check if all completed (bucket != pending means completed)
        if checks and all(c.get('bucket') != 'pending' for c in checks):
            # Determine final status (bucket: pass, fail, skipped)
            if all(c.get('bucket') in ('pass', 'skipped') for c in checks):
                final_status = 'success'
            elif any(c.get('bucket') == 'fail' for c in checks):
                final_status = 'failure'
            else:
                final_status = 'mixed'

            # Format checks table
            check_dicts, total_elapsed = format_checks_toon(checks)

            # Output TOON
            print(serialize_toon({
                'status': 'success',
                'operation': 'ci_wait',
                'pr_number': args.pr_number,
                'final_status': final_status,
                'duration_sec': int(elapsed),
                'polls': polls,
                'elapsed_sec': total_elapsed,
                'checks': check_dicts,
            }, table_separator='\t'))
            return 0

        # Wait before next poll
        time.sleep(interval)


def cmd_ci_rerun(args: argparse.Namespace) -> int:
    """Handle 'ci rerun' subcommand - rerun a workflow run."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_rerun', err)

    returncode, stdout, stderr = run_gh(['run', 'rerun', str(args.run_id)])
    if returncode != 0:
        return output_error('ci_rerun', f'Failed to rerun workflow {args.run_id}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'ci_rerun',
        'run_id': args.run_id,
    }, table_separator='\t'))
    return 0


def cmd_ci_logs(args: argparse.Namespace) -> int:
    """Handle 'ci logs' subcommand - get failed run logs."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_logs', err)

    returncode, stdout, stderr = run_gh(
        ['run', 'view', str(args.run_id), '--log-failed'], timeout=120
    )
    if returncode != 0:
        return output_error('ci_logs', f'Failed to get logs for run {args.run_id}', stderr.strip())

    # Truncate to first 200 lines
    lines = stdout.splitlines()
    truncated = lines[:200]
    content = '\n'.join(truncated)

    print(serialize_toon({
        'status': 'success',
        'operation': 'ci_logs',
        'run_id': args.run_id,
        'log_lines': len(truncated),
        'content': content.replace(chr(10), '\\n'),
    }, table_separator='\t'))
    return 0


def cmd_issue_create(args: argparse.Namespace) -> int:
    """Handle 'issue create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('issue_create', err)

    # Build command
    gh_args = ['issue', 'create', '--title', args.title, '--body', args.body]
    if args.labels:
        gh_args.extend(['--label', args.labels])

    # Execute
    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('issue_create', 'Failed to create issue', stderr.strip())

    # Parse the URL from output
    issue_url = stdout.strip()

    # Get issue number from URL
    issue_number = 'unknown'
    if '/issues/' in issue_url:
        try:
            issue_number = issue_url.split('/issues/')[1].split('/')[0].split('?')[0]
        except (IndexError, ValueError):
            pass

    # Output TOON
    print(serialize_toon({
        'status': 'success',
        'operation': 'issue_create',
        'issue_number': issue_number,
        'issue_url': issue_url,
    }, table_separator='\t'))
    return 0


def cmd_issue_view(args: argparse.Namespace) -> int:
    """Handle 'issue view' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('issue_view', err)

    # Get issue details - request all relevant fields
    gh_args = [
        'issue',
        'view',
        str(args.issue),
        '--json',
        'number,url,title,body,author,state,createdAt,updatedAt,labels,assignees,milestone',
    ]

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return output_error('issue_view', f'Failed to view issue {args.issue}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error('issue_view', 'Failed to parse gh output', stdout[:100])

    # Build output dict conditionally
    result = {
        'status': 'success',
        'operation': 'issue_view',
        'issue_number': data.get('number', 'unknown'),
        'issue_url': data.get('url', ''),
        'title': data.get('title', ''),
        'body': data.get('body', ''),
        'author': data.get('author', {}).get('login', 'unknown'),
        'state': data.get('state', 'unknown').lower(),
        'created_at': data.get('createdAt', ''),
        'updated_at': data.get('updatedAt', ''),
    }

    # Labels
    labels = data.get('labels', [])
    if labels:
        result['labels'] = [label.get('name', '') for label in labels]

    # Assignees
    assignees = data.get('assignees', [])
    if assignees:
        result['assignees'] = [assignee.get('login', '') for assignee in assignees]

    # Milestone
    milestone = data.get('milestone')
    if milestone:
        result['milestone'] = milestone.get('title', '')

    print(serialize_toon(result, table_separator='\t'))
    return 0


def cmd_issue_close(args: argparse.Namespace) -> int:
    """Handle 'issue close' subcommand - close an issue."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('issue_close', err)

    returncode, stdout, stderr = run_gh(['issue', 'close', str(args.issue)])
    if returncode != 0:
        return output_error('issue_close', f'Failed to close issue {args.issue}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'issue_close',
        'issue_number': args.issue,
    }, table_separator='\t'))
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser, pr_sub, ci_sub, issue_sub = build_parser('GitHub operations via gh CLI')

    # GitHub-specific parser additions
    add_pr_create_args(pr_sub, body_required=False, body_file=True)

    # GitHub: --pr-number on resolve-thread is optional (accepted for API uniformity)
    resolve_parser = pr_sub.choices.get('resolve-thread')
    if resolve_parser:
        resolve_parser.add_argument('--pr-number', type=int, help='PR number (accepted for API uniformity)')

    args = parser.parse_args()

    handlers = {
        ('pr', 'create'): cmd_pr_create,
        ('pr', 'view'): cmd_pr_view,
        ('pr', 'list'): cmd_pr_list,
        ('pr', 'reply'): cmd_pr_reply,
        ('pr', 'resolve-thread'): cmd_pr_resolve_thread,
        ('pr', 'thread-reply'): cmd_pr_thread_reply,
        ('pr', 'reviews'): cmd_pr_reviews,
        ('pr', 'comments'): cmd_pr_comments,
        ('pr', 'merge'): cmd_pr_merge,
        ('pr', 'auto-merge'): cmd_pr_auto_merge,
        ('pr', 'close'): cmd_pr_close,
        ('pr', 'ready'): cmd_pr_ready,
        ('pr', 'edit'): cmd_pr_edit,
        ('ci', 'status'): cmd_ci_status,
        ('ci', 'wait'): cmd_ci_wait,
        ('ci', 'rerun'): cmd_ci_rerun,
        ('ci', 'logs'): cmd_ci_logs,
        ('issue', 'create'): cmd_issue_create,
        ('issue', 'view'): cmd_issue_view,
        ('issue', 'close'): cmd_issue_close,
    }

    return dispatch(args, handlers, parser)


if __name__ == '__main__':
    sys.exit(main())
