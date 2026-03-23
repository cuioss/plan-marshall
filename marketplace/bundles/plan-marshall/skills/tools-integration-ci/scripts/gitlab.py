#!/usr/bin/env python3
"""GitLab operations via glab CLI.

Subcommands:
    pr create       Create a merge request (MR)
    pr view         View MR for current branch (number, URL, state)
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
import sys
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from toon_parser import serialize_toon  # type: ignore[import-not-found]


def run_glab(args: list[str]) -> tuple[int, str, str]:
    """Run glab CLI command and return (returncode, stdout, stderr)."""
    cmd = ['glab'] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, '', 'glab CLI not found. Install from https://gitlab.com/gitlab-org/cli'
    except subprocess.TimeoutExpired:
        return 124, '', 'Command timed out'
    except Exception as e:
        return 1, '', str(e)


def check_auth() -> tuple[bool, str]:
    """Check if glab is authenticated. Returns (is_authenticated, error_message)."""
    returncode, _, stderr = run_glab(['auth', 'status'])
    if returncode != 0:
        return False, "Not authenticated. Run 'glab auth login' first."
    return True, ''


def output_error(operation: str, error: str, context: str = '') -> int:
    """Output error in TOON format to stderr."""
    print('status: error', file=sys.stderr)
    print(f'operation: {operation}', file=sys.stderr)
    print(f'error: {error}', file=sys.stderr)
    if context:
        print(f'context: {context}', file=sys.stderr)
    return 1


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


def cmd_pr_create(args: argparse.Namespace) -> int:
    """Handle 'pr create' subcommand (creates MR in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_create', err)

    # Build command - glab uses 'mr' for merge requests
    glab_args = ['mr', 'create', '--title', args.title, '--description', args.body]
    if args.base:
        glab_args.extend(['--target-branch', args.base])
    if args.draft:
        glab_args.append('--draft')

    # Execute
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return output_error('pr_create', 'Failed to create MR', stderr.strip())

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
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_create',
        'pr_number': mr_number,
        'pr_url': mr_url,
    }, table_separator='\t'))
    return 0


def cmd_pr_view(args: argparse.Namespace) -> int:
    """Handle 'pr view' subcommand - get MR for current branch."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_view', err)

    returncode, stdout, stderr = run_glab(['mr', 'view', '--output', 'json'])
    if returncode != 0:
        return output_error('pr_view', 'No MR found for current branch', stderr.strip())

    try:
        data: dict[str, Any] = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error('pr_view', 'Failed to parse glab output', stdout[:100])

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

    print(serialize_toon({
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
    }, table_separator='\t'))
    return 0


def cmd_pr_reply(args: argparse.Namespace) -> int:
    """Handle 'pr reply' subcommand - post a comment on an MR."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_reply', err)

    returncode, stdout, stderr = run_glab(
        ['mr', 'note', str(args.pr_number), '--message', args.body]
    )
    if returncode != 0:
        return output_error('pr_reply', f'Failed to comment on MR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_reply',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def cmd_pr_resolve_thread(args: argparse.Namespace) -> int:
    """Handle 'pr resolve-thread' subcommand - resolve a discussion thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_resolve_thread', err)

    project_path = get_project_path()
    if not project_path:
        return output_error('pr_resolve_thread', 'Could not determine project path')

    encoded_path = quote(project_path, safe='')
    endpoint = f'projects/{encoded_path}/merge_requests/{args.pr_number}/discussions/{args.thread_id}'

    returncode, stdout, stderr = run_glab(['api', '-X', 'PUT', endpoint, '-f', 'resolved=true'])
    if returncode != 0:
        return output_error('pr_resolve_thread', f'Failed to resolve thread: {stderr.strip()}')

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_resolve_thread',
        'thread_id': args.thread_id,
    }, table_separator='\t'))
    return 0


def cmd_pr_thread_reply(args: argparse.Namespace) -> int:
    """Handle 'pr thread-reply' subcommand - reply to a discussion thread."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_thread_reply', err)

    project_path = get_project_path()
    if not project_path:
        return output_error('pr_thread_reply', 'Could not determine project path')

    encoded_path = quote(project_path, safe='')
    endpoint = f'projects/{encoded_path}/merge_requests/{args.pr_number}/discussions/{args.thread_id}/notes'

    returncode, stdout, stderr = run_glab(['api', '-X', 'POST', endpoint, '-f', f'body={args.body}'])
    if returncode != 0:
        return output_error('pr_thread_reply', f'Failed to reply to thread: {stderr.strip()}')

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_thread_reply',
        'pr_number': args.pr_number,
        'thread_id': args.thread_id,
    }, table_separator='\t'))
    return 0


def cmd_pr_reviews(args: argparse.Namespace) -> int:
    """Handle 'pr reviews' subcommand (gets MR approvals in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_reviews', err)

    # Get MR details including approvals
    returncode, stdout, stderr = run_glab(['mr', 'view', str(args.pr_number), '--output', 'json'])
    if returncode != 0:
        return output_error('pr_reviews', f'Failed to get MR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        # GitLab approvals are in 'approved_by' array
        approvals = data.get('approved_by', [])
    except json.JSONDecodeError:
        return output_error('pr_reviews', 'Failed to parse glab output', stdout[:100])

    # Build review list for TOON table
    reviews = []
    for approval in approvals:
        reviews.append({
            'user': approval.get('username', 'unknown'),
            'state': 'APPROVED',
            'submitted_at': approval.get('approved_at', '-'),
        })

    # Output TOON - map GitLab approvals to review format
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_reviews',
        'pr_number': args.pr_number,
        'review_count': len(approvals),
        'reviews': reviews,
    }, table_separator='\t'))
    return 0


def cmd_pr_comments(args: argparse.Namespace) -> int:
    """Handle 'pr comments' subcommand - fetch MR discussion comments."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_comments', err)

    # Get project path
    project_path = get_project_path()
    if not project_path:
        return output_error('pr_comments', 'Could not determine project path')

    # URL-encode the project path for API
    encoded_path = quote(project_path, safe='')

    # Get MR discussions via API
    # https://docs.gitlab.com/api/discussions/#list-project-merge-request-discussion-items
    endpoint = f'projects/{encoded_path}/merge_requests/{args.pr_number}/discussions'
    returncode, discussions, err = run_api(endpoint)
    if returncode != 0:
        return output_error('pr_comments', f'API request failed: {err}')

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
            path = position.get('new_path') or position.get('old_path', '')
            line = position.get('new_line') or position.get('old_line', 0)

            # Get resolved status
            is_resolved = note.get('resolved', False)

            # Skip resolved if --unresolved-only
            if args.unresolved_only and is_resolved:
                continue

            comments.append(
                {
                    'id': str(note.get('id', '')),
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
        body = c['body'].replace('\t', ' ').replace('\n', ' ')[:100]
        toon_comments.append({
            'id': c['id'],
            'author': c['author'],
            'body': body,
            'path': c['path'],
            'line': c['line'],
            'resolved': c['resolved'],
            'created_at': c['created_at'],
        })

    # Output TOON
    unresolved_count = sum(1 for c in comments if not c['resolved'])
    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_comments',
        'provider': 'gitlab',
        'pr_number': args.pr_number,
        'total': len(comments),
        'unresolved': unresolved_count,
        'comments': toon_comments,
    }, table_separator='\t'))
    return 0


def format_checks_toon(jobs: list[dict]) -> tuple[list[dict], int]:
    """Format GitLab pipeline jobs into TOON-compatible dicts and compute overall elapsed.

    Returns (list_of_job_dicts, elapsed_sec_total).
    """
    now = datetime.now(UTC)
    earliest_start = None
    rows: list[dict] = []

    for job in jobs:
        name = job.get('name', 'unknown')
        job_status = job.get('status', 'unknown')
        stage = job.get('stage') or '-'
        web_url = job.get('web_url') or '-'

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

        # Compute elapsed_sec for this job
        started_at = job.get('started_at') or job.get('created_at')
        finished_at = job.get('finished_at')
        elapsed_sec = 0

        if started_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                if earliest_start is None or start_dt < earliest_start:
                    earliest_start = start_dt
                if finished_at:
                    end_dt = datetime.fromisoformat(finished_at)
                    elapsed_sec = int((end_dt - start_dt).total_seconds())
                else:
                    elapsed_sec = int((now - start_dt).total_seconds())
            except (ValueError, TypeError):
                elapsed_sec = 0

        rows.append({
            'name': name,
            'status': state,
            'result': result,
            'elapsed_sec': elapsed_sec,
            'url': web_url,
            'stage': stage,
        })

    # Compute total elapsed from earliest start to now
    total_elapsed = 0
    if earliest_start:
        total_elapsed = int((now - earliest_start).total_seconds())

    return rows, total_elapsed


def cmd_ci_status(args: argparse.Namespace) -> int:
    """Handle 'ci status' subcommand (checks pipeline status in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_status', err)

    # Get MR to find pipeline
    returncode, stdout, stderr = run_glab(['mr', 'view', str(args.pr_number), '--output', 'json'])
    if returncode != 0:
        return output_error('ci_status', f'Failed to get MR {args.pr_number}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
        pipeline = data.get('pipeline', {})
        pipeline_status = pipeline.get('status', 'unknown')
        pipeline_id = pipeline.get('id', 'unknown')
    except json.JSONDecodeError:
        return output_error('ci_status', 'Failed to parse glab output', stdout[:100])

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
    print(serialize_toon({
        'status': 'success',
        'operation': 'ci_status',
        'pr_number': args.pr_number,
        'overall_status': overall,
        'check_count': len(jobs),
        'elapsed_sec': total_elapsed,
        'checks': checks,
    }, table_separator='\t'))
    return 0


def cmd_ci_wait(args: argparse.Namespace) -> int:
    """Handle 'ci wait' subcommand (waits for pipeline in GitLab)."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_wait', err)

    start_time = time.time()
    polls = 0
    timeout = args.timeout
    interval = args.interval
    last_jobs: list[dict] = []

    while True:
        polls += 1
        elapsed = time.time() - start_time

        # Check timeout
        if elapsed >= timeout:
            # Format checks table for timeout output
            toon_lines, total_elapsed = format_checks_toon(last_jobs) if last_jobs else ([], 0)

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

        # Get MR pipeline status
        returncode, stdout, stderr = run_glab(['mr', 'view', str(args.pr_number), '--output', 'json'])
        if returncode != 0:
            return output_error('ci_wait', f'Failed to get MR {args.pr_number}', stderr.strip())

        # Parse and check status
        try:
            data = json.loads(stdout)
            pipeline = data.get('pipeline', {})
            pipeline_status = pipeline.get('status', 'unknown')
            pipeline_id = pipeline.get('id', 'unknown')
        except json.JSONDecodeError:
            return output_error('ci_wait', 'Failed to parse glab output', stdout[:100])

        # Fetch pipeline jobs for enriched output
        if pipeline_id and pipeline_id != 'unknown':
            rc, out, _ = run_glab(['ci', 'view', str(pipeline_id), '--output', 'json'])
            if rc == 0:
                try:
                    ci_data = json.loads(out)
                    last_jobs = ci_data.get('jobs', [])
                except json.JSONDecodeError:
                    pass

        # Check if completed
        completed_statuses = {'success', 'failed', 'canceled', 'skipped'}
        if pipeline_status in completed_statuses:
            # Determine final status
            if pipeline_status == 'success':
                final_status = 'success'
            else:
                final_status = 'failure'

            # Format checks table
            checks, total_elapsed = format_checks_toon(last_jobs)

            # Output TOON
            print(serialize_toon({
                'status': 'success',
                'operation': 'ci_wait',
                'pr_number': args.pr_number,
                'final_status': final_status,
                'duration_sec': int(elapsed),
                'polls': polls,
                'elapsed_sec': total_elapsed,
                'checks': checks,
            }, table_separator='\t'))
            return 0

        # Wait before next poll
        time.sleep(interval)


def cmd_issue_create(args: argparse.Namespace) -> int:
    """Handle 'issue create' subcommand."""
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('issue_create', err)

    # Build command
    glab_args = ['issue', 'create', '--title', args.title, '--description', args.body]
    if args.labels:
        glab_args.extend(['--label', args.labels])

    # Execute
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return output_error('issue_create', 'Failed to create issue', stderr.strip())

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

    # Get issue details
    returncode, stdout, stderr = run_glab(['issue', 'view', str(args.issue), '--output', 'json'])
    if returncode != 0:
        return output_error('issue_view', f'Failed to view issue {args.issue}', stderr.strip())

    # Parse JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return output_error('issue_view', 'Failed to parse glab output', stdout[:100])

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

    # Output TOON
    print(serialize_toon(result, table_separator='\t'))
    return 0


def cmd_pr_merge(args: argparse.Namespace) -> int:
    """Handle 'pr merge' subcommand - merge a merge request."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_merge', err)

    glab_args = ['mr', 'merge', str(args.pr_number)]
    if args.strategy == 'squash':
        glab_args.append('--squash')
    if args.delete_branch:
        glab_args.append('--remove-source-branch')

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return output_error('pr_merge', f'Failed to merge MR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number,
        'strategy': args.strategy,
    }, table_separator='\t'))
    return 0


def cmd_pr_auto_merge(args: argparse.Namespace) -> int:
    """Handle 'pr auto-merge' subcommand - auto-merge when pipeline succeeds."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_auto_merge', err)

    glab_args = ['mr', 'merge', str(args.pr_number), '--when-pipeline-succeeds']
    if args.strategy == 'squash':
        glab_args.append('--squash')

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return output_error('pr_auto_merge', f'Failed to enable auto-merge for MR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_auto_merge',
        'pr_number': args.pr_number,
        'enabled': True,
    }, table_separator='\t'))
    return 0


def cmd_pr_close(args: argparse.Namespace) -> int:
    """Handle 'pr close' subcommand - close a merge request."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_close', err)

    returncode, stdout, stderr = run_glab(['mr', 'close', str(args.pr_number)])
    if returncode != 0:
        return output_error('pr_close', f'Failed to close MR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_close',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def cmd_pr_ready(args: argparse.Namespace) -> int:
    """Handle 'pr ready' subcommand - mark a draft MR as ready for review."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_ready', err)

    returncode, stdout, stderr = run_glab(['mr', 'update', str(args.pr_number), '--ready'])
    if returncode != 0:
        return output_error('pr_ready', f'Failed to mark MR {args.pr_number} as ready', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_ready',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def cmd_pr_edit(args: argparse.Namespace) -> int:
    """Handle 'pr edit' subcommand - edit MR title and/or description."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('pr_edit', err)

    if not args.title and not args.body:
        return output_error('pr_edit', 'At least one of --title or --body must be provided')

    glab_args = ['mr', 'update', str(args.pr_number)]
    if args.title:
        glab_args.extend(['--title', args.title])
    if args.body:
        glab_args.extend(['--description', args.body])

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return output_error('pr_edit', f'Failed to edit MR {args.pr_number}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'pr_edit',
        'pr_number': args.pr_number,
    }, table_separator='\t'))
    return 0


def cmd_ci_rerun(args: argparse.Namespace) -> int:
    """Handle 'ci rerun' subcommand - retry a pipeline."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_rerun', err)

    returncode, stdout, stderr = run_glab(['ci', 'retry', str(args.run_id)])
    if returncode != 0:
        return output_error('ci_rerun', f'Failed to retry pipeline {args.run_id}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'ci_rerun',
        'run_id': args.run_id,
    }, table_separator='\t'))
    return 0


def cmd_ci_logs(args: argparse.Namespace) -> int:
    """Handle 'ci logs' subcommand - get job logs."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('ci_logs', err)

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
        return output_error('ci_logs', 'glab CLI not found')
    except subprocess.TimeoutExpired:
        return output_error('ci_logs', 'Command timed out')
    except Exception as e:
        return output_error('ci_logs', str(e))

    if returncode != 0:
        return output_error('ci_logs', f'Failed to get logs for job {args.run_id}', stderr.strip())

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


def cmd_issue_close(args: argparse.Namespace) -> int:
    """Handle 'issue close' subcommand - close an issue."""
    is_auth, err = check_auth()
    if not is_auth:
        return output_error('issue_close', err)

    returncode, stdout, stderr = run_glab(['issue', 'close', str(args.issue)])
    if returncode != 0:
        return output_error('issue_close', f'Failed to close issue {args.issue}', stderr.strip())

    print(serialize_toon({
        'status': 'success',
        'operation': 'issue_close',
        'issue_number': args.issue,
    }, table_separator='\t'))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='GitLab operations via glab CLI')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # pr subcommand (maps to MR in GitLab)
    pr_parser = subparsers.add_parser('pr', help='Pull request (MR) operations')
    pr_subparsers = pr_parser.add_subparsers(dest='pr_command', required=True)

    # pr create
    pr_create_parser = pr_subparsers.add_parser('create', help='Create a merge request')
    pr_create_parser.add_argument('--title', required=True, help='MR title')
    pr_create_parser.add_argument('--body', required=True, help='MR description')
    pr_create_parser.add_argument('--base', help='Target branch (default: repo default)')
    pr_create_parser.add_argument('--draft', action='store_true', help='Create as draft MR')

    # pr view
    pr_subparsers.add_parser('view', help='View MR for current branch')

    # pr reply
    pr_reply_parser = pr_subparsers.add_parser('reply', help='Reply to a MR with a comment')
    pr_reply_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_reply_parser.add_argument('--body', required=True, help='Comment text')

    # pr resolve-thread
    pr_resolve_parser = pr_subparsers.add_parser('resolve-thread', help='Resolve a discussion thread')
    pr_resolve_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_resolve_parser.add_argument('--thread-id', required=True, help='Discussion ID')

    # pr thread-reply
    pr_thread_reply_parser = pr_subparsers.add_parser('thread-reply', help='Reply to a discussion thread')
    pr_thread_reply_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_thread_reply_parser.add_argument('--thread-id', required=True, help='Discussion ID')
    pr_thread_reply_parser.add_argument('--body', required=True, help='Reply text')

    # pr reviews
    pr_reviews_parser = pr_subparsers.add_parser('reviews', help='Get MR approvals')
    pr_reviews_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')

    # pr comments
    pr_comments_parser = pr_subparsers.add_parser('comments', help='Get MR discussion comments')
    pr_comments_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_comments_parser.add_argument('--unresolved-only', action='store_true', help='Only show unresolved comments')

    # pr merge
    pr_merge_parser = pr_subparsers.add_parser('merge', help='Merge a merge request')
    pr_merge_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_merge_parser.add_argument('--strategy', default='merge', choices=['merge', 'squash', 'rebase'],
                                 help='Merge strategy (default: merge)')
    pr_merge_parser.add_argument('--delete-branch', action='store_true', help='Delete branch after merge')

    # pr auto-merge
    pr_auto_merge_parser = pr_subparsers.add_parser('auto-merge', help='Enable auto-merge when pipeline succeeds')
    pr_auto_merge_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_auto_merge_parser.add_argument('--strategy', default='merge', choices=['merge', 'squash', 'rebase'],
                                      help='Merge strategy (default: merge)')

    # pr close
    pr_close_parser = pr_subparsers.add_parser('close', help='Close a merge request')
    pr_close_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')

    # pr ready
    pr_ready_parser = pr_subparsers.add_parser('ready', help='Mark draft MR as ready for review')
    pr_ready_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')

    # pr edit
    pr_edit_parser = pr_subparsers.add_parser('edit', help='Edit MR title and/or description')
    pr_edit_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_edit_parser.add_argument('--title', help='New MR title')
    pr_edit_parser.add_argument('--body', help='New MR description')

    # ci subcommand
    ci_parser = subparsers.add_parser('ci', help='CI/Pipeline operations')
    ci_subparsers = ci_parser.add_subparsers(dest='ci_command', required=True)

    # ci status
    ci_status_parser = ci_subparsers.add_parser('status', help='Check pipeline status')
    ci_status_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')

    # ci wait
    ci_wait_parser = ci_subparsers.add_parser('wait', help='Wait for pipeline to complete')
    ci_wait_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    ci_wait_parser.add_argument('--timeout', type=int, default=300, help='Max wait time in seconds (default: 300)')
    ci_wait_parser.add_argument('--interval', type=int, default=30, help='Poll interval in seconds (default: 30)')

    # ci rerun
    ci_rerun_parser = ci_subparsers.add_parser('rerun', help='Retry a pipeline')
    ci_rerun_parser.add_argument('--run-id', required=True, help='Pipeline ID')

    # ci logs
    ci_logs_parser = ci_subparsers.add_parser('logs', help='Get job logs')
    ci_logs_parser.add_argument('--run-id', required=True, help='Job ID')

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
    issue_view_parser.add_argument('--issue', required=True, help='Issue number (iid) or URL')

    # issue close
    issue_close_parser = issue_subparsers.add_parser('close', help='Close an issue')
    issue_close_parser.add_argument('--issue', required=True, help='Issue number (iid) or URL')

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
