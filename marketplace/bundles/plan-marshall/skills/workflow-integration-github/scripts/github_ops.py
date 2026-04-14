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
    pr submit-review   Submit a pending PR review (safety net)
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
    python3 github.py pr submit-review --review-id PRR_abc123 [--event COMMENT|APPROVE|REQUEST_CHANGES]
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
from typing import Any

from ci_base import (  # type: ignore[import-not-found]
    add_pr_create_args,
    build_parser,
    check_auth_cli,
    compute_elapsed,
    compute_total_elapsed,
    dispatch,
    make_error,
    make_pr_number_handler,
    make_simple_handler,
    poll_until,
    run_cli,
    truncate_log_content,
)
from toon_parser import serialize_toon  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# CLI wrappers
# ---------------------------------------------------------------------------


def run_gh(args: list[str], capture_json: bool = False, timeout: int = 60) -> tuple[int, str, str]:
    """Run gh CLI command and return (returncode, stdout, stderr)."""
    return run_cli(
        'gh',
        args,
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


def cmd_pr_create(args: argparse.Namespace) -> dict:
    """Handle 'pr create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_create', err)

    # Resolve body: --body-file takes precedence over --body
    body = args.body or ''
    if args.body_file:
        try:
            with open(args.body_file) as f:
                body = f.read()
        except OSError as e:
            return make_error('pr_create', f'Failed to read body file: {e}')

    # Build command
    gh_args = ['pr', 'create', '--title', args.title, '--body', body]
    if args.base:
        gh_args.extend(['--base', args.base])
    if args.draft:
        gh_args.append('--draft')

    # Execute
    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_create', 'Failed to create PR', stderr.strip())

    # Parse the URL from output (gh pr create outputs the URL)
    pr_url = stdout.strip()

    # Get PR number from URL
    pr_number = 'unknown'
    if '/pull/' in pr_url:
        try:
            pr_number = pr_url.split('/pull/')[1].split('/')[0].split('?')[0]
        except (IndexError, ValueError):
            pass

    return {
        'status': 'success',
        'operation': 'pr_create',
        'pr_number': pr_number,
        'pr_url': pr_url,
    }


def view_pr_data() -> dict:
    """Fetch PR data for current branch, returning structured dict.

    Returns dict with 'status' key ('success' or 'error').
    Importable by other scripts for direct data access without subprocess.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return {'status': 'error', 'operation': 'pr_view', 'error': err}

    returncode, stdout, stderr = run_gh(
        [
            'pr',
            'view',
            '--json',
            'number,url,state,title,headRefName,baseRefName,isDraft,mergeable,mergeStateStatus,reviewDecision',
        ]
    )
    if returncode != 0:
        return {
            'status': 'error',
            'operation': 'pr_view',
            'error': 'No PR found for current branch',
            'context': stderr.strip(),
        }

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            'status': 'error',
            'operation': 'pr_view',
            'error': 'Failed to parse gh output',
            'context': stdout[:100],
        }

    return {
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
    }


def cmd_pr_view(args: argparse.Namespace) -> dict:
    """Handle 'pr view' subcommand - get PR for current branch."""
    return view_pr_data()


def cmd_pr_list(args: argparse.Namespace) -> dict:
    """Handle 'pr list' subcommand - list pull requests with optional filters."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_list', err)

    gh_args = [
        'pr',
        'list',
        '--json',
        'number,url,title,state,headRefName,baseRefName',
        '--state',
        args.state,
    ]
    if args.head:
        gh_args.extend(['--head', args.head])

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_list', 'Failed to list PRs', stderr.strip())

    try:
        prs = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('pr_list', 'Failed to parse gh output', stdout[:100])

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
    return {
        'status': 'success',
        'operation': 'pr_list',
        'total': len(prs),
        'state_filter': args.state,
        'head_filter': args.head or '',
        'prs': pr_list,
    }


cmd_pr_reply = make_pr_number_handler(
    'pr_reply',
    lambda args: ['pr', 'comment', str(args.pr_number), '--body', args.body],
    run_gh,
    check_auth,
)


RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}
"""


THREAD_REPLY_MUTATION = """
mutation($threadId: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) {
    comment { id databaseId }
  }
}
"""


VIEWER_LOGIN_QUERY = """
query { viewer { login } }
"""


PENDING_REVIEWS_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviews(states: [PENDING], first: 20) {
        nodes { id author { login } }
      }
    }
  }
}
"""


def get_viewer_login() -> tuple[str | None, str]:
    """Return the authenticated viewer's login, or (None, error_message)."""
    returncode, data, err = run_graphql(VIEWER_LOGIN_QUERY, {})
    if returncode != 0 or data is None:
        return None, err or 'Failed to resolve viewer login'
    try:
        login = data['viewer']['login']
    except (KeyError, TypeError):
        return None, 'viewer.login missing from GraphQL response'
    if not login:
        return None, 'viewer.login empty'
    return login, ''


def cmd_pr_resolve_thread(args: argparse.Namespace) -> dict:
    """Handle 'pr resolve-thread' subcommand - resolve a review thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_resolve_thread', err)

    returncode, data, err = run_graphql(RESOLVE_THREAD_MUTATION, {'threadId': args.thread_id})
    if returncode != 0 or data is None:
        return make_error('pr_resolve_thread', f'Failed to resolve thread: {err}')

    return {
        'status': 'success',
        'operation': 'pr_resolve_thread',
        'thread_id': args.thread_id,
    }


def cmd_pr_thread_reply(args: argparse.Namespace) -> dict:
    """Handle 'pr thread-reply' subcommand - reply to a specific review thread.

    Uses addPullRequestReviewThreadReply which publishes replies immediately and
    takes a real review-thread node id (``PRRT_*``). No PR node-id lookup is
    needed — the thread already belongs to a PR. After a successful reply we
    verify that no PENDING review remains for the authenticated viewer; the
    presence of one indicates the reply silently landed in a draft review and
    callers need to recover it explicitly.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_thread_reply', err)

    returncode, data, err = run_graphql(
        THREAD_REPLY_MUTATION,
        {'threadId': args.thread_id, 'body': args.body},
    )
    if returncode != 0 or data is None:
        return make_error('pr_thread_reply', f'Failed to reply to thread: {err}')

    # Post-call regression check: a successful addPullRequestReviewThreadReply
    # must not leave a PENDING review owned by the current viewer. If it does,
    # the reply is queued into a draft review and is invisible to reviewers.
    viewer_login, viewer_err = get_viewer_login()
    if viewer_login is None:
        return make_error(
            'pr_thread_reply',
            f'Reply sent but viewer.login lookup failed: {viewer_err}',
        )

    owner, repo = get_repo_info()
    if not owner or not repo:
        return make_error(
            'pr_thread_reply',
            'Reply sent but could not determine repository owner/name for PENDING-review check',
        )

    rc2, pending_data, pending_err = run_graphql(
        PENDING_REVIEWS_QUERY,
        {'owner': owner, 'repo': repo, 'pr': args.pr_number},
    )
    if rc2 != 0 or pending_data is None:
        return make_error(
            'pr_thread_reply',
            f'Reply sent but PENDING-review check failed: {pending_err}',
        )

    try:
        pending_nodes = pending_data['repository']['pullRequest']['reviews']['nodes'] or []
    except (KeyError, TypeError):
        pending_nodes = []

    stuck = [
        n for n in pending_nodes
        if (n.get('author') or {}).get('login') == viewer_login
    ]
    if stuck:
        stuck_ids = ', '.join(n.get('id', '<unknown>') for n in stuck)
        return make_error(
            'pr_thread_reply',
            (
                f'Reply queued into PENDING review owned by {viewer_login}; '
                f"run 'ci pr submit-review --review-id <id>' to publish it. "
                f'Stuck review id(s): {stuck_ids}'
            ),
            stuck_ids,
        )

    return {
        'status': 'success',
        'operation': 'pr_thread_reply',
        'pr_number': args.pr_number,
        'thread_id': args.thread_id,
    }


SUBMIT_REVIEW_MUTATION = """
mutation($reviewId: ID!, $event: PullRequestReviewEvent!) {
  submitPullRequestReview(input: {pullRequestReviewId: $reviewId, event: $event}) {
    pullRequestReview { id state }
  }
}
"""


def cmd_pr_submit_review(args: argparse.Namespace) -> dict:
    """Handle 'pr submit-review' subcommand - publish a pending review."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_submit_review', err)

    returncode, data, err = run_graphql(
        SUBMIT_REVIEW_MUTATION,
        {'reviewId': args.review_id, 'event': args.event},
    )
    if returncode != 0 or data is None:
        return make_error('pr_submit_review', f'Failed to submit review: {err}')

    try:
        review = data['submitPullRequestReview']['pullRequestReview']
        review_id = review.get('id', args.review_id)
        state = review.get('state', 'unknown')
    except (KeyError, TypeError):
        return make_error('pr_submit_review', 'Malformed GraphQL response', str(data)[:200])

    return {
        'status': 'success',
        'operation': 'pr_submit_review',
        'review_id': review_id,
        'event': args.event,
        'state': state,
    }


def cmd_pr_reviews(args: argparse.Namespace) -> dict:
    """Handle 'pr reviews' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_reviews', err)

    # Get reviews
    returncode, stdout, stderr = run_gh(['pr', 'view', str(args.pr_number), '--json', 'reviews'])
    if returncode != 0:
        return make_error('pr_reviews', f'Failed to get reviews for PR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        reviews = data.get('reviews', [])
    except json.JSONDecodeError:
        return make_error('pr_reviews', 'Failed to parse gh output', stdout[:100])

    review_list = [
        {
            'user': r.get('author', {}).get('login', 'unknown'),
            'state': r.get('state', 'UNKNOWN'),
            'submitted_at': r.get('submittedAt', '-'),
        }
        for r in reviews
    ]
    return {
        'status': 'success',
        'operation': 'pr_reviews',
        'pr_number': args.pr_number,
        'review_count': len(reviews),
        'reviews': review_list,
    }


# GraphQL query for PR review threads (inline), review submission bodies, and issue-level comments
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
      reviews(first: 100) {
        nodes {
          id
          state
          body
          author { login }
          submittedAt
        }
      }
      comments(first: 100) {
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
"""


def fetch_pr_comments_data(pr_number: int, unresolved_only: bool = False) -> dict:
    """Fetch PR review comments, returning structured dict.

    Returns dict with 'status' key ('success' or 'error').
    Importable by other scripts for direct data access without subprocess.
    """
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return {'status': 'error', 'operation': 'pr_comments', 'error': err}

    # Get repo info
    owner, repo = get_repo_info()
    if not owner or not repo:
        return {'status': 'error', 'operation': 'pr_comments', 'error': 'Could not determine repository owner/name'}

    # Run GraphQL query
    returncode, data, err = run_graphql(REVIEW_THREADS_QUERY, {'owner': owner, 'repo': repo, 'pr': pr_number})
    if returncode != 0 or data is None:
        return {'status': 'error', 'operation': 'pr_comments', 'error': f'GraphQL query failed: {err}'}

    # Extract and normalize threads, reviews, and issue comments with null-safe traversal.
    # The entire parsing block is wrapped so any malformed node (non-dict, null nested field)
    # is caught and surfaced as a structured error rather than crashing the caller.
    comments: list[dict] = []
    try:
        pull_request = (data.get('repository') or {}).get('pullRequest') or {}
        threads = (pull_request.get('reviewThreads') or {}).get('nodes') or []
        reviews = (pull_request.get('reviews') or {}).get('nodes') or []
        issue_comments = (pull_request.get('comments') or {}).get('nodes') or []

        # 1. Inline review thread comments
        for thread in threads:
            if not isinstance(thread, dict):
                continue
            is_resolved = thread.get('isResolved', False)

            # Skip resolved threads if --unresolved-only
            if unresolved_only and is_resolved:
                continue

            path = thread.get('path') or ''
            line = thread.get('line') or 0
            thread_id = thread.get('id') or ''

            thread_comments = (thread.get('comments') or {}).get('nodes') or []
            for comment in thread_comments:
                if not isinstance(comment, dict):
                    continue
                comments.append(
                    {
                        'kind': 'inline',
                        'id': comment.get('id') or '',
                        'author': (comment.get('author') or {}).get('login', 'unknown'),
                        'body': comment.get('body') or '',
                        'path': path,
                        'line': line,
                        'resolved': is_resolved,
                        'created_at': comment.get('createdAt') or '',
                        'thread_id': thread_id,
                    }
                )

        # 2. Review submission bodies (APPROVED / COMMENTED / CHANGES_REQUESTED)
        for review in reviews:
            if not isinstance(review, dict):
                continue
            body = review.get('body') or ''
            if not body:
                continue
            comments.append(
                {
                    'kind': 'review_body',
                    'id': review.get('id') or '',
                    'author': (review.get('author') or {}).get('login', 'unknown'),
                    'body': body,
                    'path': '',
                    'line': 0,
                    'resolved': False,
                    'created_at': review.get('submittedAt') or '',
                    'thread_id': '',
                }
            )

        # 3. Issue-level PR comments
        for issue_comment in issue_comments:
            if not isinstance(issue_comment, dict):
                continue
            body = issue_comment.get('body') or ''
            if not body:
                continue
            comments.append(
                {
                    'kind': 'issue_comment',
                    'id': issue_comment.get('id') or '',
                    'author': (issue_comment.get('author') or {}).get('login', 'unknown'),
                    'body': body,
                    'path': '',
                    'line': 0,
                    'resolved': False,
                    'created_at': issue_comment.get('createdAt') or '',
                    'thread_id': '',
                }
            )
    except (TypeError, AttributeError) as e:
        return {'status': 'error', 'operation': 'pr_comments', 'error': f'Failed to parse response: {e}'}

    # Build result
    unresolved_count = sum(1 for c in comments if not c['resolved'])
    comment_list = [
        {
            'kind': c['kind'],
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
    return {
        'status': 'success',
        'operation': 'pr_comments',
        'provider': 'github',
        'pr_number': pr_number,
        'total': len(comments),
        'unresolved': unresolved_count,
        'comments': comment_list,
    }


def cmd_pr_comments(args: argparse.Namespace) -> dict:
    """Handle 'pr comments' subcommand - fetch inline code review comments."""
    return fetch_pr_comments_data(args.pr_number, args.unresolved_only)


def cmd_pr_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr merge' subcommand - merge a pull request."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_merge', err)

    gh_args = ['pr', 'merge', str(args.pr_number), f'--{args.strategy}']
    if args.delete_branch:
        gh_args.append('--delete-branch')

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_merge', f'Failed to merge PR {args.pr_number}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number,
        'strategy': args.strategy,
    }


def cmd_pr_auto_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr auto-merge' subcommand - enable auto-merge on a pull request."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_auto_merge', err)

    gh_args = ['pr', 'merge', str(args.pr_number), '--auto', f'--{args.strategy}']

    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_auto_merge', f'Failed to enable auto-merge for PR {args.pr_number}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'pr_auto_merge',
        'pr_number': args.pr_number,
        'enabled': True,
    }


cmd_pr_close = make_pr_number_handler(
    'pr_close',
    lambda args: ['pr', 'close', str(args.pr_number)],
    run_gh,
    check_auth,
)


cmd_pr_ready = make_pr_number_handler(
    'pr_ready',
    lambda args: ['pr', 'ready', str(args.pr_number)],
    run_gh,
    check_auth,
)


def cmd_pr_edit(args: argparse.Namespace) -> dict:
    """Handle 'pr edit' subcommand - edit PR title and/or body."""
    if not args.title and not args.body:
        return make_error('pr_edit', 'At least one of --title or --body must be provided')

    gh_args = ['pr', 'edit', str(args.pr_number)]
    if args.title:
        gh_args.extend(['--title', args.title])
    if args.body:
        gh_args.extend(['--body', args.body])

    result: dict = make_pr_number_handler('pr_edit', lambda a: gh_args, run_gh, check_auth)(args)
    return result


def format_checks_toon(checks: list[dict]) -> tuple[list[dict], int]:
    """Format checks into dicts and compute overall elapsed.

    Returns (check_dicts, elapsed_sec_total).
    """
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    check_dicts: list[dict] = []
    started_at_values: list[str | None] = []

    for check in checks:
        started_at = check.get('startedAt')
        started_at_values.append(started_at)

        check_dicts.append(
            {
                'name': check.get('name', 'unknown'),
                'status': check.get('state', 'unknown'),
                'result': check.get('bucket') or '-',
                'elapsed_sec': compute_elapsed(started_at, check.get('completedAt'), now),
                'url': check.get('link') or '-',
                'workflow': check.get('workflow') or '-',
            }
        )

    total_elapsed = compute_total_elapsed(started_at_values, now)
    return check_dicts, total_elapsed


def cmd_ci_status(args: argparse.Namespace) -> dict:
    """Handle 'ci status' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_status', err)

    # Get checks (bucket field contains pass/fail result)
    returncode, stdout, stderr = run_gh(
        ['pr', 'checks', str(args.pr_number), '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
    )
    if returncode != 0:
        return make_error('ci_status', f'Failed to get CI status for PR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        checks = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('ci_status', 'Failed to parse gh output', stdout[:100])

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

    return {
        'status': 'success',
        'operation': 'ci_status',
        'pr_number': args.pr_number,
        'overall_status': overall,
        'check_count': len(checks),
        'elapsed_sec': total_elapsed,
        'checks': check_dicts,
    }


def cmd_ci_wait(args: argparse.Namespace) -> dict:
    """Handle 'ci wait' subcommand."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_wait', err)

    def check_fn() -> tuple[bool, dict]:
        returncode, stdout, stderr = run_gh(
            ['pr', 'checks', str(args.pr_number), '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
        )
        if returncode != 0:
            return False, {'error': f'Failed to get CI status for PR {args.pr_number}', 'context': stderr.strip()}
        try:
            checks = json.loads(stdout)
        except json.JSONDecodeError:
            return False, {'error': 'Failed to parse gh output', 'context': stdout[:100]}
        return True, {'checks': checks}

    def is_complete_fn(data: dict) -> bool:
        checks = data.get('checks', [])
        return bool(checks) and all(c.get('bucket') != 'pending' for c in checks)

    result = poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error('ci_wait', result['error'], result['last_data'].get('context', ''))

    checks = result['last_data'].get('checks', [])
    check_dicts, total_elapsed = format_checks_toon(checks)

    if result['timed_out']:
        error_data: dict[str, Any] = {
            'status': 'error',
            'operation': 'ci_wait',
            'error': 'Timeout waiting for CI',
            'pr_number': args.pr_number,
            'duration_sec': result['duration_sec'],
            'last_status': 'pending',
        }
        if check_dicts:
            error_data['elapsed_sec'] = total_elapsed
            error_data['checks'] = check_dicts
        return error_data

    # Determine final status
    if all(c.get('bucket') in ('pass', 'skipped') for c in checks):
        final_status = 'success'
    elif any(c.get('bucket') == 'fail' for c in checks):
        final_status = 'failure'
    else:
        final_status = 'mixed'

    return {
        'status': 'success',
        'operation': 'ci_wait',
        'pr_number': args.pr_number,
        'final_status': final_status,
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'elapsed_sec': total_elapsed,
        'checks': check_dicts,
    }


cmd_ci_rerun = make_simple_handler(
    'ci_rerun',
    lambda args: ['run', 'rerun', str(args.run_id)],
    run_gh,
    check_auth,
    result_extras=lambda args: {'run_id': args.run_id},
)


def cmd_ci_logs(args: argparse.Namespace) -> dict:
    """Handle 'ci logs' subcommand - get failed run logs."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_logs', err)

    returncode, stdout, stderr = run_gh(['run', 'view', str(args.run_id), '--log-failed'], timeout=120)
    if returncode != 0:
        return make_error('ci_logs', f'Failed to get logs for run {args.run_id}', stderr.strip())

    content, line_count = truncate_log_content(stdout)

    return {
        'status': 'success',
        'operation': 'ci_logs',
        'run_id': args.run_id,
        'log_lines': line_count,
        'content': content,
    }


def cmd_issue_create(args: argparse.Namespace) -> dict:
    """Handle 'issue create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('issue_create', err)

    # Build command
    gh_args = ['issue', 'create', '--title', args.title, '--body', args.body]
    if args.labels:
        gh_args.extend(['--label', args.labels])

    # Execute
    returncode, stdout, stderr = run_gh(gh_args)
    if returncode != 0:
        return make_error('issue_create', 'Failed to create issue', stderr.strip())

    # Parse the URL from output
    issue_url = stdout.strip()

    # Get issue number from URL
    issue_number = 'unknown'
    if '/issues/' in issue_url:
        try:
            issue_number = issue_url.split('/issues/')[1].split('/')[0].split('?')[0]
        except (IndexError, ValueError):
            pass

    return {
        'status': 'success',
        'operation': 'issue_create',
        'issue_number': issue_number,
        'issue_url': issue_url,
    }


def cmd_issue_view(args: argparse.Namespace) -> dict:
    """Handle 'issue view' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('issue_view', err)

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
        return make_error('issue_view', f'Failed to view issue {args.issue}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('issue_view', 'Failed to parse gh output', stdout[:100])

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

    return result


cmd_issue_close = make_simple_handler(
    'issue_close',
    lambda args: ['issue', 'close', str(args.issue)],
    run_gh,
    check_auth,
    result_extras=lambda args: {'issue_number': args.issue},
)


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
        ('pr', 'submit-review'): cmd_pr_submit_review,
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

    result = dispatch(args, handlers, parser)
    print(serialize_toon(result, table_separator='\t'))
    return 0


if __name__ == '__main__':
    from file_ops import safe_main  # type: ignore[import-not-found]

    safe_main(main)()
