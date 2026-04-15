#!/usr/bin/env python3
"""GitLab operations via glab CLI.

Subcommands:
    pr create       Create a merge request (MR)
    pr view         View MR for current branch (number, URL, state)
    pr list         List merge requests with optional filters
    pr reviews      Get MR approvals
    pr comments     Get MR discussion comments (inline code comments)
    pr reply        Reply to a MR with a comment
    pr resolve-thread  Resolve a discussion thread
    pr thread-reply    Reply to a specific discussion thread
    pr merge        Merge a merge request
    pr auto-merge   Enable auto-merge when pipeline succeeds
    pr close        Close a merge request
    pr ready        Mark a draft MR as ready for review
    pr edit         Edit MR title and/or description
    ci status       Check pipeline status for a MR
    ci wait         Wait for pipeline to complete
    ci rerun        Retry a pipeline
    ci logs         Get job logs
    issue create    Create an issue
    issue view      View issue details
    issue close     Close an issue

Usage:
    python3 gitlab.py pr create --title "Title" --body "Body" [--base main] [--draft]
    python3 gitlab.py pr view
    python3 gitlab.py pr list [--head feature/branch] [--state open|closed|all]
    python3 gitlab.py pr reviews --pr-number 123
    python3 gitlab.py pr comments --pr-number 123 [--unresolved-only]
    python3 gitlab.py pr reply --pr-number 123 --body "Comment text"
    python3 gitlab.py pr resolve-thread --pr-number 123 --thread-id abc123
    python3 gitlab.py pr thread-reply --pr-number 123 --thread-id abc123 --body "Fixed"
    python3 gitlab.py pr merge --pr-number 123 [--strategy squash] [--delete-branch]
    python3 gitlab.py pr auto-merge --pr-number 123 [--strategy squash]
    python3 gitlab.py pr close --pr-number 123
    python3 gitlab.py pr ready --pr-number 123
    python3 gitlab.py pr edit --pr-number 123 [--title "New Title"] [--body "New Body"]
    python3 gitlab.py ci status --pr-number 123
    python3 gitlab.py ci wait --pr-number 123 [--timeout 300] [--interval 30]
    python3 gitlab.py ci rerun --run-id 12345
    python3 gitlab.py ci logs --run-id 12345
    python3 gitlab.py issue create --title "Title" --body "Body" [--labels "bug,priority::high"]
    python3 gitlab.py issue view --issue 123
    python3 gitlab.py issue close --issue 123

Note: Uses GitHub terminology (pr, issue) for API consistency.
      Internally maps to GitLab equivalents (mr, issue).

Output: TOON format
"""

import argparse
import json
import subprocess
from typing import Any
from urllib.parse import quote

from ci_base import (  # type: ignore[import-not-found]
    add_pr_create_args,
    add_pr_resolve_thread_pr_number,
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


def run_glab(args: list[str]) -> tuple[int, str, str]:
    """Run glab CLI command and return (returncode, stdout, stderr)."""
    return run_cli(
        'glab',
        args,
        not_found_msg='glab CLI not found. Install from https://gitlab.com/gitlab-org/cli',
    )


def check_auth() -> tuple[bool, str]:
    """Check if glab is authenticated. Returns (is_authenticated, error_message)."""
    return check_auth_cli('glab', "Not authenticated. Run 'glab auth login' first.", run_glab)


# ---------------------------------------------------------------------------
# Provider-specific helpers
# ---------------------------------------------------------------------------


def get_project_path() -> str | None:
    """Get project path (namespace/repo) from current repository.

    Returns project path like 'namespace/repo' or None if not found.
    """
    returncode, stdout, _ = run_glab(['repo', 'view', '--output', 'json'])
    if returncode != 0:
        return None
    try:
        data: dict[str, Any] = json.loads(stdout)
        path = data.get('full_path') or data.get('path_with_namespace')
        return str(path) if path else None
    except json.JSONDecodeError:
        return None


def run_api(endpoint: str) -> tuple[int, list | dict | None, str]:
    """Run GitLab API request via glab api.

    Returns (returncode, data, error).
    """
    returncode, stdout, stderr = run_glab(['api', endpoint])
    if returncode != 0:
        return returncode, None, stderr

    try:
        data = json.loads(stdout)
        return 0, data, ''
    except json.JSONDecodeError:
        return 1, None, f'Failed to parse API response: {stdout[:100]}'


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _resolve_mr_iid(args: argparse.Namespace, operation: str) -> tuple[str | None, dict | None]:
    """Resolve an MR IID from --pr-number or --head.

    For --pr-number: returns the value directly.
    For --head: looks up the open MR by source branch via ``glab mr list --source-branch``.

    Returns ``(iid, None)`` on success, or ``(None, error_dict)`` on validation failure
    or zero-match.
    """
    pr_number = getattr(args, 'pr_number', None)
    head = getattr(args, 'head', None)
    if pr_number and head:
        return None, make_error(operation, 'specify exactly one of --pr-number or --head, not both')
    if pr_number:
        return str(pr_number), None
    if not head:
        return None, make_error(operation, 'specify either --pr-number or --head')

    returncode, stdout, stderr = run_glab(['mr', 'list', '--source-branch', head, '--output', 'json'])
    if returncode != 0:
        return None, make_error(operation, f'Failed to look up MR for source branch {head}', stderr.strip())
    try:
        mrs = json.loads(stdout)
    except json.JSONDecodeError:
        return None, make_error(operation, 'Failed to parse glab mr list output', stdout[:100])
    if not mrs:
        return None, make_error(operation, f'no MR found for source branch {head}')
    iid = mrs[0].get('iid')
    if iid is None:
        return None, make_error(operation, f'glab mr list returned entry without iid for source branch {head}')
    return str(iid), None


def cmd_pr_create(args: argparse.Namespace) -> dict:
    """Handle 'pr create' subcommand (creates MR in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_create', err)

    # Build command - glab uses 'mr' for merge requests
    glab_args = ['mr', 'create', '--title', args.title, '--description', args.body]
    if args.base:
        glab_args.extend(['--target-branch', args.base])
    if args.draft:
        glab_args.append('--draft')
    if getattr(args, 'head', None):
        glab_args.extend(['--source-branch', args.head])

    # Execute
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_create', 'Failed to create MR', stderr.strip())

    # Parse the URL from output (glab mr create outputs the URL)
    mr_url = stdout.strip()

    # Get MR number (iid) from URL
    mr_number = 'unknown'
    if '/merge_requests/' in mr_url or '/-/merge_requests/' in mr_url:
        try:
            # Handle both URL formats
            parts = mr_url.split('/merge_requests/')
            if len(parts) > 1:
                mr_number = parts[1].split('/')[0].split('?')[0]
        except (IndexError, ValueError):
            pass

    # Output TOON (using 'pr' terminology for API consistency)
    return {
        'status': 'success',
        'operation': 'pr_create',
        'pr_number': mr_number,
        'pr_url': mr_url,
    }


def view_pr_data(head: str | None = None) -> dict:
    """Fetch MR data for current branch (or for the supplied ``head`` branch).

    Returns dict with 'status' key ('success' or 'error').
    Importable by other scripts for direct data access without subprocess.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return {'status': 'error', 'operation': 'pr_view', 'error': err}

    glab_args = ['mr', 'view', '--output', 'json']
    if head:
        glab_args = ['mr', 'view', head, '--output', 'json']
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return {
            'status': 'error',
            'operation': 'pr_view',
            'error': 'No MR found for current branch',
            'context': stderr.strip(),
        }

    try:
        data: dict[str, Any] = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            'status': 'error',
            'operation': 'pr_view',
            'error': 'Failed to parse glab output',
            'context': stdout[:100],
        }

    state = data.get('state', 'unknown')
    if state == 'opened':
        state = 'open'

    # Map merge_status to mergeable
    merge_status = data.get('merge_status', 'unknown')
    if merge_status == 'can_be_merged':
        mergeable = 'mergeable'
    elif merge_status in ('cannot_be_merged', 'cannot_be_merged_recheck'):
        mergeable = 'conflicting'
    else:
        mergeable = 'unknown'

    # Map approved state to review_decision
    approved = data.get('approved', None)
    if approved is True:
        review_decision = 'approved'
    elif approved is False:
        review_decision = 'review_required'
    else:
        review_decision = 'none'

    return {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': data.get('iid', 'unknown'),
        'pr_url': data.get('web_url', ''),
        'state': state,
        'title': data.get('title', ''),
        'head_branch': data.get('source_branch', ''),
        'base_branch': data.get('target_branch', ''),
        'is_draft': str(data.get('draft', False)).lower(),
        'mergeable': mergeable,
        'merge_state': merge_status,
        'review_decision': review_decision,
    }


def cmd_pr_view(args: argparse.Namespace) -> dict:
    """Handle 'pr view' subcommand - get MR for current branch (or --head branch)."""
    return view_pr_data(head=getattr(args, 'head', None))


def cmd_pr_list(args: argparse.Namespace) -> dict:
    """Handle 'pr list' subcommand - list merge requests with optional filters."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_list', err)

    # Map state for glab: open->opened, closed->closed, all->all
    state_map = {'open': 'opened', 'closed': 'closed', 'all': 'all'}
    glab_state = state_map.get(args.state, 'opened')

    glab_args = ['mr', 'list', '--output', 'json', '--state', glab_state]
    if args.head:
        glab_args.extend(['--source-branch', args.head])

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_list', 'Failed to list MRs', stderr.strip())

    try:
        mrs: list[dict[str, Any]] = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('pr_list', 'Failed to parse glab output', stdout[:100])

    pr_list = [
        {
            'number': mr.get('iid', 0),
            'url': mr.get('web_url', ''),
            'title': mr.get('title', ''),
            'state': 'open' if mr.get('state') == 'opened' else mr.get('state', 'unknown'),
            'head_branch': mr.get('source_branch', ''),
            'base_branch': mr.get('target_branch', ''),
        }
        for mr in mrs
    ]
    return {
        'status': 'success',
        'operation': 'pr_list',
        'total': len(mrs),
        'state_filter': args.state,
        'head_filter': args.head or '',
        'prs': pr_list,
    }


cmd_pr_reply = make_pr_number_handler(
    'pr_reply',
    lambda args: ['mr', 'note', str(args.pr_number), '--message', args.body],
    run_glab,
    check_auth,
)


def cmd_pr_resolve_thread(args: argparse.Namespace) -> dict:
    """Handle 'pr resolve-thread' subcommand - resolve a discussion thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_resolve_thread', err)

    project_path = get_project_path()
    if not project_path:
        return make_error('pr_resolve_thread', 'Could not determine project path')

    encoded_path = quote(project_path, safe='')
    endpoint = f'projects/{encoded_path}/merge_requests/{args.pr_number}/discussions/{args.thread_id}'

    returncode, stdout, stderr = run_glab(['api', '-X', 'PUT', endpoint, '-f', 'resolved=true'])
    if returncode != 0:
        return make_error('pr_resolve_thread', f'Failed to resolve thread: {stderr.strip()}')

    return {
        'status': 'success',
        'operation': 'pr_resolve_thread',
        'thread_id': args.thread_id,
    }


def cmd_pr_thread_reply(args: argparse.Namespace) -> dict:
    """Handle 'pr thread-reply' subcommand - reply to a discussion thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_thread_reply', err)

    project_path = get_project_path()
    if not project_path:
        return make_error('pr_thread_reply', 'Could not determine project path')

    encoded_path = quote(project_path, safe='')
    # GitLab's discussion notes endpoint publishes replies immediately —
    # there is no pending/draft state here, unlike GitHub's PR review flow.
    endpoint = f'projects/{encoded_path}/merge_requests/{args.pr_number}/discussions/{args.thread_id}/notes'

    returncode, stdout, stderr = run_glab(['api', '-X', 'POST', endpoint, '-f', f'body={args.body}'])
    if returncode != 0:
        return make_error('pr_thread_reply', f'Failed to reply to thread: {stderr.strip()}')

    return {
        'status': 'success',
        'operation': 'pr_thread_reply',
        'pr_number': args.pr_number,
        'thread_id': args.thread_id,
    }


def cmd_pr_submit_review(args: argparse.Namespace) -> dict:
    """Handle 'pr submit-review' subcommand.

    GitLab discussion replies are published immediately via the notes endpoint
    (see ``cmd_pr_thread_reply`` above), so there is no pending-review draft
    state on GitLab and no equivalent to GitHub's submitPullRequestReview.
    We deliberately return an explicit error rather than a silent success so
    that cross-provider callers notice the mismatch.
    """
    return make_error(
        'pr_submit_review',
        'Not supported on GitLab — discussion replies are immediate (no draft review state)',
    )


def cmd_pr_reviews(args: argparse.Namespace) -> dict:
    """Handle 'pr reviews' subcommand (gets MR approvals in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_reviews', err)

    # Get MR details including approvals
    returncode, stdout, stderr = run_glab(['mr', 'view', str(args.pr_number), '--output', 'json'])
    if returncode != 0:
        return make_error('pr_reviews', f'Failed to get MR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        # GitLab approvals are in 'approved_by' array
        approvals = data.get('approved_by', [])
    except json.JSONDecodeError:
        return make_error('pr_reviews', 'Failed to parse glab output', stdout[:100])

    # Build review list for TOON table
    reviews = []
    for approval in approvals:
        reviews.append(
            {
                'user': approval.get('username', 'unknown'),
                'state': 'APPROVED',
                'submitted_at': approval.get('approved_at', '-'),
            }
        )

    # Output TOON - map GitLab approvals to review format
    return {
        'status': 'success',
        'operation': 'pr_reviews',
        'pr_number': args.pr_number,
        'review_count': len(approvals),
        'reviews': reviews,
    }


def fetch_pr_comments_data(pr_number: int, unresolved_only: bool = False) -> dict:
    """Fetch MR discussion comments, returning structured dict.

    Returns dict with 'status' key ('success' or 'error').
    Importable by other scripts for direct data access without subprocess.
    """
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return {'status': 'error', 'operation': 'pr_comments', 'error': err}

    # Get project path
    project_path = get_project_path()
    if not project_path:
        return {'status': 'error', 'operation': 'pr_comments', 'error': 'Could not determine project path'}

    # URL-encode the project path for API
    encoded_path = quote(project_path, safe='')

    # Get MR discussions via API
    # https://docs.gitlab.com/api/discussions/#list-project-merge-request-discussion-items
    endpoint = f'projects/{encoded_path}/merge_requests/{pr_number}/discussions'
    returncode, discussions, err = run_api(endpoint)
    if returncode != 0:
        return {'status': 'error', 'operation': 'pr_comments', 'error': f'API request failed: {err}'}

    # Normalize comments
    comments: list[dict] = []
    for discussion in discussions or []:
        discussion_id = discussion.get('id', '')
        notes = discussion.get('notes', [])

        for note in notes:
            # Skip system notes (auto-generated)
            if note.get('system', False):
                continue

            # Get position info for diff notes
            position = note.get('position') or {}
            has_position = bool(position.get('new_path') or position.get('old_path'))
            path = position.get('new_path') or position.get('old_path', '')
            line = position.get('new_line') or position.get('old_line', 0)

            # Classify note kind: inline (diff-anchored) vs issue_comment (no position).
            # GitLab has no equivalent of GitHub's review_body kind.
            kind = 'inline' if has_position else 'issue_comment'

            # Get resolved status
            is_resolved = note.get('resolved', False)

            # Skip resolved if --unresolved-only
            if unresolved_only and is_resolved:
                continue

            comments.append(
                {
                    'id': str(note.get('id', '')),
                    'kind': kind,
                    'author': note.get('author', {}).get('username', 'unknown'),
                    'body': note.get('body', ''),
                    'path': path,
                    'line': line or 0,
                    'resolved': is_resolved,
                    'created_at': note.get('created_at', ''),
                    'thread_id': discussion_id,
                }
            )

    # Escape body text for TOON table rows
    toon_comments = []
    for c in comments:
        body = c['body'].replace('\t', ' ').replace('\n', ' ')
        toon_comments.append(
            {
                'id': c['id'],
                'kind': c['kind'],
                'thread_id': c['thread_id'],
                'author': c['author'],
                'body': body,
                'path': c['path'],
                'line': c['line'],
                'resolved': c['resolved'],
                'created_at': c['created_at'],
            }
        )

    # Build result
    unresolved_count = sum(1 for c in comments if not c['resolved'])
    return {
        'status': 'success',
        'operation': 'pr_comments',
        'provider': 'gitlab',
        'pr_number': pr_number,
        'total': len(comments),
        'unresolved': unresolved_count,
        'comments': toon_comments,
    }


def cmd_pr_comments(args: argparse.Namespace) -> dict:
    """Handle 'pr comments' subcommand - fetch MR discussion comments."""
    return fetch_pr_comments_data(args.pr_number, args.unresolved_only)


def format_checks_toon(jobs: list[dict]) -> tuple[list[dict], int]:
    """Format GitLab pipeline jobs into TOON-compatible dicts and compute overall elapsed.

    Returns (list_of_job_dicts, elapsed_sec_total).
    """
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    rows: list[dict] = []
    started_at_values: list[str | None] = []

    for job in jobs:
        job_status = job.get('status', 'unknown')

        # Map job status to state/result
        if job_status in ('running', 'pending', 'created'):
            state = 'in_progress'
            result = '-'
        else:
            state = 'completed'
            if job_status == 'success':
                result = 'success'
            elif job_status in ('failed', 'canceled'):
                result = 'failure'
            elif job_status == 'skipped':
                result = 'skipped'
            else:
                result = job_status

        started_at = job.get('started_at') or job.get('created_at')
        started_at_values.append(started_at)

        rows.append(
            {
                'name': job.get('name', 'unknown'),
                'status': state,
                'result': result,
                'elapsed_sec': compute_elapsed(started_at, job.get('finished_at'), now),
                'url': job.get('web_url') or '-',
                'stage': job.get('stage') or '-',
            }
        )

    total_elapsed = compute_total_elapsed(started_at_values, now)
    return rows, total_elapsed


def cmd_ci_status(args: argparse.Namespace) -> dict:
    """Handle 'ci status' subcommand (checks pipeline status in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_status', err)

    iid, err_dict = _resolve_mr_iid(args, 'ci_status')
    if err_dict:
        return err_dict
    assert iid is not None  # noqa: S101 — narrowing after err_dict guard

    # Get MR to find pipeline
    returncode, stdout, stderr = run_glab(['mr', 'view', iid, '--output', 'json'])
    if returncode != 0:
        return make_error('ci_status', f'Failed to get MR {iid}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        pipeline = data.get('pipeline', {})
        pipeline_status = pipeline.get('status', 'unknown')
        pipeline_id = pipeline.get('id', 'unknown')
    except json.JSONDecodeError:
        return make_error('ci_status', 'Failed to parse glab output', stdout[:100])

    # Get pipeline jobs if we have a pipeline
    jobs = []
    if pipeline_id and pipeline_id != 'unknown':
        returncode, stdout, stderr = run_glab(['ci', 'view', str(pipeline_id), '--output', 'json'])
        if returncode == 0:
            try:
                ci_data = json.loads(stdout)
                jobs = ci_data.get('jobs', [])
            except json.JSONDecodeError:
                pass

    # Map GitLab pipeline status to overall status
    status_map = {
        'success': 'success',
        'failed': 'failure',
        'canceled': 'failure',
        'skipped': 'success',
        'running': 'pending',
        'pending': 'pending',
        'created': 'pending',
    }
    overall = status_map.get(pipeline_status, 'unknown')

    # Format checks table
    checks, total_elapsed = format_checks_toon(jobs)

    # Output TOON
    return {
        'status': 'success',
        'operation': 'ci_status',
        'pr_number': args.pr_number if args.pr_number else iid,
        'overall_status': overall,
        'check_count': len(jobs),
        'elapsed_sec': total_elapsed,
        'checks': checks,
    }


def cmd_ci_wait(args: argparse.Namespace) -> dict:
    """Handle 'ci wait' subcommand (waits for pipeline in GitLab)."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_wait', err)

    completed_statuses = {'success', 'failed', 'canceled', 'skipped'}

    def check_fn() -> tuple[bool, dict]:
        returncode, stdout, stderr = run_glab(['mr', 'view', str(args.pr_number), '--output', 'json'])
        if returncode != 0:
            return False, {'error': f'Failed to get MR {args.pr_number}', 'context': stderr.strip()}
        try:
            data = json.loads(stdout)
            pipeline = data.get('pipeline', {})
            pipeline_status = pipeline.get('status', 'unknown')
            pipeline_id = pipeline.get('id', 'unknown')
        except json.JSONDecodeError:
            return False, {'error': 'Failed to parse glab output', 'context': stdout[:100]}

        # Fetch pipeline jobs for enriched output
        jobs: list[dict] = []
        if pipeline_id and pipeline_id != 'unknown':
            rc, out, _ = run_glab(['ci', 'view', str(pipeline_id), '--output', 'json'])
            if rc == 0:
                try:
                    ci_data = json.loads(out)
                    jobs = ci_data.get('jobs', [])
                except json.JSONDecodeError:
                    pass

        return True, {'pipeline_status': pipeline_status, 'jobs': jobs}

    def is_complete_fn(data: dict) -> bool:
        return data.get('pipeline_status', 'unknown') in completed_statuses

    result = poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error('ci_wait', result['error'], result['last_data'].get('context', ''))

    last_data = result['last_data']
    jobs = last_data.get('jobs', [])
    check_dicts, total_elapsed = format_checks_toon(jobs)

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

    pipeline_status = last_data.get('pipeline_status', 'unknown')
    final_status = 'success' if pipeline_status == 'success' else 'failure'

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
    lambda args: ['ci', 'retry', str(args.run_id)],
    run_glab,
    check_auth,
    result_extras=lambda args: {'run_id': args.run_id},
)


def cmd_ci_logs(args: argparse.Namespace) -> dict:
    """Handle 'ci logs' subcommand - get job logs."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_logs', err)

    # Use subprocess.run directly for longer timeout (120s)
    cmd = ['glab', 'ci', 'trace', str(args.run_id)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except FileNotFoundError:
        return make_error('ci_logs', 'glab CLI not found')
    except subprocess.TimeoutExpired:
        return make_error('ci_logs', 'Command timed out')
    except Exception as e:
        return make_error('ci_logs', str(e))

    if returncode != 0:
        return make_error('ci_logs', f'Failed to get logs for job {args.run_id}', stderr.strip())

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
    glab_args = ['issue', 'create', '--title', args.title, '--description', args.body]
    if args.labels:
        glab_args.extend(['--label', args.labels])

    # Execute
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('issue_create', 'Failed to create issue', stderr.strip())

    # Parse the URL from output
    issue_url = stdout.strip()

    # Get issue number (iid) from URL
    issue_number = 'unknown'
    if '/issues/' in issue_url or '/-/issues/' in issue_url:
        try:
            parts = issue_url.split('/issues/')
            if len(parts) > 1:
                issue_number = parts[1].split('/')[0].split('?')[0]
        except (IndexError, ValueError):
            pass

    # Output TOON
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

    # Get issue details
    returncode, stdout, stderr = run_glab(['issue', 'view', str(args.issue), '--output', 'json'])
    if returncode != 0:
        return make_error('issue_view', f'Failed to view issue {args.issue}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('issue_view', 'Failed to parse glab output', stdout[:100])

    # Map GitLab state to unified state
    state = data.get('state', 'unknown')
    if state == 'opened':
        state = 'open'

    # Build output dict
    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'issue_view',
        'issue_number': data.get('iid', 'unknown'),
        'issue_url': data.get('web_url', ''),
        'title': data.get('title', ''),
        'body': data.get('description', ''),  # GitLab uses 'description'
        'author': data.get('author', {}).get('username', 'unknown'),
        'state': state,
        'created_at': data.get('created_at', ''),
        'updated_at': data.get('updated_at', ''),
    }

    # Labels (GitLab: direct string array)
    labels = data.get('labels', [])
    if labels:
        result['labels'] = labels

    # Assignees
    assignees = data.get('assignees', [])
    if assignees:
        result['assignees'] = [a.get('username', '') for a in assignees]

    # Milestone
    milestone = data.get('milestone')
    if milestone:
        result['milestone'] = milestone.get('title', '')

    return result


def cmd_pr_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr merge' subcommand - merge a merge request."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_merge', err)

    iid, err_dict = _resolve_mr_iid(args, 'pr_merge')
    if err_dict:
        return err_dict
    assert iid is not None  # noqa: S101 — narrowing after err_dict guard

    glab_args = ['mr', 'merge', iid]
    if args.strategy == 'squash':
        glab_args.append('--squash')
    if args.delete_branch:
        glab_args.append('--remove-source-branch')

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_merge', f'Failed to merge MR {iid}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number if args.pr_number else iid,
        'strategy': args.strategy,
    }


def cmd_pr_auto_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr auto-merge' subcommand - auto-merge when pipeline succeeds."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_auto_merge', err)

    iid, err_dict = _resolve_mr_iid(args, 'pr_auto_merge')
    if err_dict:
        return err_dict
    assert iid is not None  # noqa: S101 — narrowing after err_dict guard

    glab_args = ['mr', 'merge', iid, '--when-pipeline-succeeds']
    if args.strategy == 'squash':
        glab_args.append('--squash')

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_auto_merge', f'Failed to enable auto-merge for MR {iid}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'pr_auto_merge',
        'pr_number': args.pr_number if args.pr_number else iid,
        'enabled': True,
    }


cmd_pr_close = make_pr_number_handler(
    'pr_close',
    lambda args: ['mr', 'close', str(args.pr_number)],
    run_glab,
    check_auth,
)


cmd_pr_ready = make_pr_number_handler(
    'pr_ready',
    lambda args: ['mr', 'update', str(args.pr_number), '--ready'],
    run_glab,
    check_auth,
)


def cmd_pr_edit(args: argparse.Namespace) -> dict:
    """Handle 'pr edit' subcommand - edit MR title and/or description."""
    if not args.title and not args.body:
        return make_error('pr_edit', 'At least one of --title or --body must be provided')

    glab_args = ['mr', 'update', str(args.pr_number)]
    if args.title:
        glab_args.extend(['--title', args.title])
    if args.body:
        glab_args.extend(['--description', args.body])

    result: dict = make_pr_number_handler('pr_edit', lambda a: glab_args, run_glab, check_auth)(args)
    return result


cmd_issue_close = make_simple_handler(
    'issue_close',
    lambda args: ['issue', 'close', str(args.issue)],
    run_glab,
    check_auth,
    result_extras=lambda args: {'issue_number': args.issue},
)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser, pr_sub, ci_sub, issue_sub = build_parser('GitLab operations via glab CLI')

    # GitLab-specific parser additions
    add_pr_create_args(pr_sub, body_required=True, body_file=False)

    # GitLab: --pr-number on resolve-thread is required
    add_pr_resolve_thread_pr_number(pr_sub)

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
