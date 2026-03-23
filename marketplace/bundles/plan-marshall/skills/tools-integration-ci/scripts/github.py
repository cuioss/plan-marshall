#!/usr/bin/env python3
"""GitHub operations via gh CLI.

Subcommands:
    pr create       Create a pull request
    pr view         View PR for current branch (number, URL, state)
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
import subprocess
import sys
import time
from datetime import UTC, datetime


def run_gh(args: list[str], capture_json: bool = False, timeout: int = 60) -> tuple[int, str, str]:
    """Run gh CLI command and return (returncode, stdout, stderr)."""
    cmd = ['gh'] + args
    if capture_json:
        cmd.extend(['--json'] if '--json' not in args else [])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, '', 'gh CLI not found. Install from https://cli.github.com/'
    except subprocess.TimeoutExpired:
        return 124, '', 'Command timed out'
    except Exception as e:
        return 1, '', str(e)


def check_auth() -> tuple[bool, str]:
    """Check if gh is authenticated. Returns (is_authenticated, error_message)."""
    returncode, _, stderr = run_gh(['auth', 'status'])
    if returncode != 0:
        return False, "Not authenticated. Run 'gh auth login' first."
    return True, ''


def output_error(operation: str, error: str, context: str = '') -> int:
    """Output error in TOON format to stderr."""
    print('status: error', file=sys.stderr)
    print(f'operation: {operation}', file=sys.stderr)
    print(f'error: {error}', file=sys.stderr)
    if context:
        print(f'context: {context}', file=sys.stderr)
    return 1


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


def cmd_pr_create(args: argparse.Namespace) -> int:
    """Handle 'pr create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_create', err)

    # Build command
    gh_args = ['pr', 'create', '--title', args.title, '--body', args.body]
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
    print('status: success')
    print('operation: pr_create')
    print(f'pr_number: {pr_number}')
    print(f'pr_url: {pr_url}')
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

    print('status: success')
    print('operation: pr_view')
    print(f'pr_number: {data.get("number", "unknown")}')
    print(f'pr_url: {data.get("url", "")}')
    print(f'state: {data.get("state", "unknown").lower()}')
    print(f'title: {data.get("title", "")}')
    print(f'head_branch: {data.get("headRefName", "")}')
    print(f'base_branch: {data.get("baseRefName", "")}')
    print(f'is_draft: {str(data.get("isDraft", False)).lower()}')
    print(f'mergeable: {data.get("mergeable", "unknown").lower() if data.get("mergeable") else "unknown"}')
    print(f'merge_state: {data.get("mergeStateStatus", "unknown").lower() if data.get("mergeStateStatus") else "unknown"}')
    print(f'review_decision: {data.get("reviewDecision", "none").lower() if data.get("reviewDecision") else "none"}')
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

    print('status: success')
    print('operation: pr_reply')
    print(f'pr_number: {args.pr_number}')
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

    print('status: success')
    print('operation: pr_resolve_thread')
    print(f'thread_id: {args.thread_id}')
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

    print('status: success')
    print('operation: pr_thread_reply')
    print(f'pr_number: {args.pr_number}')
    print(f'thread_id: {args.thread_id}')
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
    print('status: success')
    print('operation: pr_reviews')
    print(f'pr_number: {args.pr_number}')
    print(f'review_count: {len(reviews)}')
    print()
    print(f'reviews[{len(reviews)}]{{user,state,submitted_at}}:')
    for review in reviews:
        user = review.get('author', {}).get('login', 'unknown')
        state = review.get('state', 'UNKNOWN')
        submitted = review.get('submittedAt', '-')
        print(f'{user}\t{state}\t{submitted}')
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
    print('status: success')
    print('operation: pr_comments')
    print('provider: github')
    print(f'pr_number: {args.pr_number}')
    print(f'total: {len(comments)}')
    print(f'unresolved: {unresolved_count}')
    print()
    print(f'comments[{len(comments)}]{{id,author,body,path,line,resolved,created_at}}:')
    for c in comments:
        # Escape tabs and newlines in body for TOON format
        body = c['body'].replace('\t', ' ').replace('\n', ' ')[:100]
        print(f'{c["id"]}\t{c["author"]}\t{body}\t{c["path"]}\t{c["line"]}\t{c["resolved"]}\t{c["created_at"]}')
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

    print('status: success')
    print('operation: pr_merge')
    print(f'pr_number: {args.pr_number}')
    print(f'strategy: {args.strategy}')
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

    print('status: success')
    print('operation: pr_auto_merge')
    print(f'pr_number: {args.pr_number}')
    print('enabled: true')
    return 0


def cmd_pr_close(args: argparse.Namespace) -> int:
    """Handle 'pr close' subcommand - close a pull request."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_close', err)

    returncode, stdout, stderr = run_gh(['pr', 'close', str(args.pr_number)])
    if returncode != 0:
        return output_error('pr_close', f'Failed to close PR {args.pr_number}', stderr.strip())

    print('status: success')
    print('operation: pr_close')
    print(f'pr_number: {args.pr_number}')
    return 0


def cmd_pr_ready(args: argparse.Namespace) -> int:
    """Handle 'pr ready' subcommand - mark a draft PR as ready for review."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_ready', err)

    returncode, stdout, stderr = run_gh(['pr', 'ready', str(args.pr_number)])
    if returncode != 0:
        return output_error('pr_ready', f'Failed to mark PR {args.pr_number} as ready', stderr.strip())

    print('status: success')
    print('operation: pr_ready')
    print(f'pr_number: {args.pr_number}')
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

    print('status: success')
    print('operation: pr_edit')
    print(f'pr_number: {args.pr_number}')
    return 0


def format_checks_toon(checks: list[dict]) -> tuple[list[str], int]:
    """Format checks into TOON table rows and compute overall elapsed.

    Returns (toon_lines, elapsed_sec_total).
    """
    now = datetime.now(UTC)
    earliest_start = None
    rows: list[str] = []

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

        rows.append(f'{name}\t{state}\t{bucket}\t{elapsed_sec}\t{link}\t{workflow}')

    # Compute total elapsed from earliest start to now
    total_elapsed = 0
    if earliest_start:
        total_elapsed = int((now - earliest_start).total_seconds())

    lines: list[str] = []
    lines.append(f'checks[{len(checks)}]{{name,status,result,elapsed_sec,url,workflow}}:')
    lines.extend(rows)

    return lines, total_elapsed


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
    toon_lines, total_elapsed = format_checks_toon(checks)

    # Output TOON
    print('status: success')
    print('operation: ci_status')
    print(f'pr_number: {args.pr_number}')
    print(f'overall_status: {overall}')
    print(f'check_count: {len(checks)}')
    print(f'elapsed_sec: {total_elapsed}')
    print()
    for line in toon_lines:
        print(line)
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
            toon_lines, total_elapsed = format_checks_toon(last_checks) if last_checks else ([], 0)

            print('status: error', file=sys.stderr)
            print('operation: ci_wait', file=sys.stderr)
            print('error: Timeout waiting for CI', file=sys.stderr)
            print(f'pr_number: {args.pr_number}', file=sys.stderr)
            print(f'duration_sec: {int(elapsed)}', file=sys.stderr)
            print('last_status: pending', file=sys.stderr)
            if toon_lines:
                print(f'elapsed_sec: {total_elapsed}', file=sys.stderr)
                print(file=sys.stderr)
                for line in toon_lines:
                    print(line, file=sys.stderr)
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
            toon_lines, total_elapsed = format_checks_toon(checks)

            # Output TOON
            print('status: success')
            print('operation: ci_wait')
            print(f'pr_number: {args.pr_number}')
            print(f'final_status: {final_status}')
            print(f'duration_sec: {int(elapsed)}')
            print(f'polls: {polls}')
            print(f'elapsed_sec: {total_elapsed}')
            print()
            for line in toon_lines:
                print(line)
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

    print('status: success')
    print('operation: ci_rerun')
    print(f'run_id: {args.run_id}')
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

    print('status: success')
    print('operation: ci_logs')
    print(f'run_id: {args.run_id}')
    print(f'log_lines: {len(truncated)}')
    print(f'content: {content}')
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
    print('status: success')
    print('operation: issue_create')
    print(f'issue_number: {issue_number}')
    print(f'issue_url: {issue_url}')
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

    # Output TOON
    print('status: success')
    print('operation: issue_view')
    print(f'issue_number: {data.get("number", "unknown")}')
    print(f'issue_url: {data.get("url", "")}')
    print(f'title: {data.get("title", "")}')
    print(f'body: {data.get("body", "")}')
    print(f'author: {data.get("author", {}).get("login", "unknown")}')
    print(f'state: {data.get("state", "unknown").lower()}')
    print(f'created_at: {data.get("createdAt", "")}')
    print(f'updated_at: {data.get("updatedAt", "")}')

    # Labels
    labels = data.get('labels', [])
    if labels:
        print(f'\nlabels[{len(labels)}]:')
        for label in labels:
            print(f'- {label.get("name", "")}')

    # Assignees
    assignees = data.get('assignees', [])
    if assignees:
        print(f'\nassignees[{len(assignees)}]:')
        for assignee in assignees:
            print(f'- {assignee.get("login", "")}')

    # Milestone
    milestone = data.get('milestone')
    if milestone:
        print(f'\nmilestone: {milestone.get("title", "")}')

    return 0


def cmd_issue_close(args: argparse.Namespace) -> int:
    """Handle 'issue close' subcommand - close an issue."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('issue_close', err)

    returncode, stdout, stderr = run_gh(['issue', 'close', str(args.issue)])
    if returncode != 0:
        return output_error('issue_close', f'Failed to close issue {args.issue}', stderr.strip())

    print('status: success')
    print('operation: issue_close')
    print(f'issue_number: {args.issue}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='GitHub operations via gh CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # pr subcommand
    pr_parser = subparsers.add_parser('pr', help='Pull request operations')
    pr_subparsers = pr_parser.add_subparsers(dest='pr_command', required=True)

    # pr create
    pr_create_parser = pr_subparsers.add_parser('create', help='Create a pull request')
    pr_create_parser.add_argument('--title', required=True, help='PR title')
    pr_create_parser.add_argument('--body', required=True, help='PR description')
    pr_create_parser.add_argument('--base', help='Base branch (default: repo default)')
    pr_create_parser.add_argument('--draft', action='store_true', help='Create as draft PR')

    # pr view
    pr_subparsers.add_parser('view', help='View PR for current branch')

    # pr reply
    pr_reply_parser = pr_subparsers.add_parser('reply', help='Reply to a PR with a comment')
    pr_reply_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_reply_parser.add_argument('--body', required=True, help='Comment text')

    # pr resolve-thread
    pr_resolve_parser = pr_subparsers.add_parser('resolve-thread', help='Resolve a review thread')
    pr_resolve_parser.add_argument('--pr-number', type=int, help='PR number (accepted for API uniformity)')
    pr_resolve_parser.add_argument('--thread-id', required=True, help='Review thread ID')

    # pr thread-reply
    pr_thread_reply_parser = pr_subparsers.add_parser('thread-reply', help='Reply to a review thread')
    pr_thread_reply_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_thread_reply_parser.add_argument('--thread-id', required=True, help='Comment ID to reply to')
    pr_thread_reply_parser.add_argument('--body', required=True, help='Reply text')

    # pr reviews
    pr_reviews_parser = pr_subparsers.add_parser('reviews', help='Get PR reviews')
    pr_reviews_parser.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr comments
    pr_comments_parser = pr_subparsers.add_parser('comments', help='Get PR inline code comments')
    pr_comments_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_comments_parser.add_argument('--unresolved-only', action='store_true', help='Only show unresolved comments')

    # pr merge
    pr_merge_parser = pr_subparsers.add_parser('merge', help='Merge a pull request')
    pr_merge_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_merge_parser.add_argument('--strategy', default='merge', choices=['merge', 'squash', 'rebase'],
                                 help='Merge strategy (default: merge)')
    pr_merge_parser.add_argument('--delete-branch', action='store_true', help='Delete branch after merge')

    # pr auto-merge
    pr_auto_merge_parser = pr_subparsers.add_parser('auto-merge', help='Enable auto-merge on a PR')
    pr_auto_merge_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_auto_merge_parser.add_argument('--strategy', default='merge', choices=['merge', 'squash', 'rebase'],
                                      help='Merge strategy (default: merge)')

    # pr close
    pr_close_parser = pr_subparsers.add_parser('close', help='Close a pull request')
    pr_close_parser.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr ready
    pr_ready_parser = pr_subparsers.add_parser('ready', help='Mark draft PR as ready for review')
    pr_ready_parser.add_argument('--pr-number', required=True, type=int, help='PR number')

    # pr edit
    pr_edit_parser = pr_subparsers.add_parser('edit', help='Edit PR title and/or body')
    pr_edit_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    pr_edit_parser.add_argument('--title', help='New PR title')
    pr_edit_parser.add_argument('--body', help='New PR body')

    # ci subcommand
    ci_parser = subparsers.add_parser('ci', help='CI operations')
    ci_subparsers = ci_parser.add_subparsers(dest='ci_command', required=True)

    # ci status
    ci_status_parser = ci_subparsers.add_parser('status', help='Check CI status')
    ci_status_parser.add_argument('--pr-number', required=True, type=int, help='PR number')

    # ci wait
    ci_wait_parser = ci_subparsers.add_parser('wait', help='Wait for CI to complete')
    ci_wait_parser.add_argument('--pr-number', required=True, type=int, help='PR number')
    ci_wait_parser.add_argument('--timeout', type=int, default=300, help='Max wait time in seconds (default: 300)')
    ci_wait_parser.add_argument('--interval', type=int, default=30, help='Poll interval in seconds (default: 30)')

    # ci rerun
    ci_rerun_parser = ci_subparsers.add_parser('rerun', help='Rerun a workflow run')
    ci_rerun_parser.add_argument('--run-id', required=True, help='Workflow run ID')

    # ci logs
    ci_logs_parser = ci_subparsers.add_parser('logs', help='Get failed run logs')
    ci_logs_parser.add_argument('--run-id', required=True, help='Workflow run ID')

    # issue subcommand
    issue_parser = subparsers.add_parser('issue', help='Issue operations')
    issue_subparsers = issue_parser.add_subparsers(dest='issue_command', required=True)

    # issue create
    issue_create_parser = issue_subparsers.add_parser('create', help='Create an issue')
    issue_create_parser.add_argument('--title', required=True, help='Issue title')
    issue_create_parser.add_argument('--body', required=True, help='Issue description')
    issue_create_parser.add_argument('--labels', help='Comma-separated labels')

    # issue view
    issue_view_parser = issue_subparsers.add_parser('view', help='View issue details')
    issue_view_parser.add_argument('--issue', required=True, help='Issue number or URL')

    # issue close
    issue_close_parser = issue_subparsers.add_parser('close', help='Close an issue')
    issue_close_parser.add_argument('--issue', required=True, help='Issue number or URL')

    args = parser.parse_args()

    if args.command == 'pr':
        if args.pr_command == 'create':
            return cmd_pr_create(args)
        elif args.pr_command == 'view':
            return cmd_pr_view(args)
        elif args.pr_command == 'reply':
            return cmd_pr_reply(args)
        elif args.pr_command == 'resolve-thread':
            return cmd_pr_resolve_thread(args)
        elif args.pr_command == 'thread-reply':
            return cmd_pr_thread_reply(args)
        elif args.pr_command == 'reviews':
            return cmd_pr_reviews(args)
        elif args.pr_command == 'comments':
            return cmd_pr_comments(args)
        elif args.pr_command == 'merge':
            return cmd_pr_merge(args)
        elif args.pr_command == 'auto-merge':
            return cmd_pr_auto_merge(args)
        elif args.pr_command == 'close':
            return cmd_pr_close(args)
        elif args.pr_command == 'ready':
            return cmd_pr_ready(args)
        elif args.pr_command == 'edit':
            return cmd_pr_edit(args)
    elif args.command == 'ci':
        if args.ci_command == 'status':
            return cmd_ci_status(args)
        elif args.ci_command == 'wait':
            return cmd_ci_wait(args)
        elif args.ci_command == 'rerun':
            return cmd_ci_rerun(args)
        elif args.ci_command == 'logs':
            return cmd_ci_logs(args)
    elif args.command == 'issue':
        if args.issue_command == 'create':
            return cmd_issue_create(args)
        elif args.issue_command == 'view':
            return cmd_issue_view(args)
        elif args.issue_command == 'close':
            return cmd_issue_close(args)

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
