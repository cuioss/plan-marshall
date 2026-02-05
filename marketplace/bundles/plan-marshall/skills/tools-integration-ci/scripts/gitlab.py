#!/usr/bin/env python3
"""GitLab operations via glab CLI.

Subcommands:
    pr create       Create a merge request (MR)
    pr reviews      Get MR approvals
    pr comments     Get MR discussion comments (inline code comments)
    ci status       Check pipeline status for a MR
    ci wait         Wait for pipeline to complete
    issue create    Create an issue
    issue view      View issue details

Usage:
    python3 gitlab.py pr create --title "Title" --body "Body" [--base main] [--draft]
    python3 gitlab.py pr reviews --pr-number 123
    python3 gitlab.py pr comments --pr-number 123 [--unresolved-only]
    python3 gitlab.py ci status --pr-number 123
    python3 gitlab.py ci wait --pr-number 123 [--timeout 300] [--interval 30]
    python3 gitlab.py issue create --title "Title" --body "Body" [--labels "bug,priority::high"]
    python3 gitlab.py issue view --issue 123

Note: Uses GitHub terminology (pr, issue) for API consistency.
      Internally maps to GitLab equivalents (mr, issue).

Output: TOON format
"""

import argparse
import json
import subprocess
import sys
import time
from typing import Any


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
    print('status: success')
    print('operation: pr_create')
    print(f'pr_number: {mr_number}')
    print(f'pr_url: {mr_url}')
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

    # Output TOON - map GitLab approvals to review format
    print('status: success')
    print('operation: pr_reviews')
    print(f'pr_number: {args.pr_number}')
    print(f'review_count: {len(approvals)}')
    print()
    print(f'reviews[{len(approvals)}]{{user,state,submitted_at}}:')
    for approval in approvals:
        user = approval.get('username', 'unknown')
        # GitLab only has APPROVED state in approved_by list
        state = 'APPROVED'
        # approved_at may not be available in all GitLab versions
        submitted = approval.get('approved_at', '-')
        print(f'{user}\t{state}\t{submitted}')
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
    from urllib.parse import quote

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

    # Output TOON
    unresolved_count = sum(1 for c in comments if not c['resolved'])
    print('status: success')
    print('operation: pr_comments')
    print('provider: gitlab')
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

    # Output TOON
    print('status: success')
    print('operation: ci_status')
    print(f'pr_number: {args.pr_number}')
    print(f'overall_status: {overall}')
    print(f'check_count: {len(jobs)}')
    print()
    print(f'checks[{len(jobs)}]{{name,status,conclusion}}:')
    for job in jobs:
        name = job.get('name', 'unknown')
        job_status = job.get('status', 'unknown')
        # Map job status to state/conclusion
        if job_status in ('running', 'pending', 'created'):
            state = 'in_progress'
            conclusion = '-'
        else:
            state = 'completed'
            if job_status == 'success':
                conclusion = 'success'
            elif job_status in ('failed', 'canceled'):
                conclusion = 'failure'
            else:
                conclusion = job_status
        print(f'{name}\t{state}\t{conclusion}')
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

    while True:
        polls += 1
        elapsed = time.time() - start_time

        # Check timeout
        if elapsed >= timeout:
            print('status: error', file=sys.stderr)
            print('operation: ci_wait', file=sys.stderr)
            print('error: Timeout waiting for CI', file=sys.stderr)
            print(f'pr_number: {args.pr_number}', file=sys.stderr)
            print(f'duration_sec: {int(elapsed)}', file=sys.stderr)
            print('last_status: pending', file=sys.stderr)
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
        except json.JSONDecodeError:
            return output_error('ci_wait', 'Failed to parse glab output', stdout[:100])

        # Check if completed
        completed_statuses = {'success', 'failed', 'canceled', 'skipped'}
        if pipeline_status in completed_statuses:
            # Determine final status
            if pipeline_status == 'success':
                final_status = 'success'
            else:
                final_status = 'failure'

            # Output TOON
            print('status: success')
            print('operation: ci_wait')
            print(f'pr_number: {args.pr_number}')
            print(f'final_status: {final_status}')
            print(f'duration_sec: {int(elapsed)}')
            print(f'polls: {polls}')
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

    # Output TOON
    print('status: success')
    print('operation: issue_view')
    print(f'issue_number: {data.get("iid", "unknown")}')
    print(f'issue_url: {data.get("web_url", "")}')
    print(f'title: {data.get("title", "")}')
    print(f'body: {data.get("description", "")}')  # GitLab uses 'description'
    print(f'author: {data.get("author", {}).get("username", "unknown")}')
    print(f'state: {state}')
    print(f'created_at: {data.get("created_at", "")}')
    print(f'updated_at: {data.get("updated_at", "")}')

    # Labels (GitLab: direct string array)
    labels = data.get('labels', [])
    if labels:
        print(f'\nlabels[{len(labels)}]:')
        for label in labels:
            print(f'- {label}')

    # Assignees
    assignees = data.get('assignees', [])
    if assignees:
        print(f'\nassignees[{len(assignees)}]:')
        for assignee in assignees:
            print(f'- {assignee.get("username", "")}')

    # Milestone
    milestone = data.get('milestone')
    if milestone:
        print(f'\nmilestone: {milestone.get("title", "")}')

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

    # pr reviews
    pr_reviews_parser = pr_subparsers.add_parser('reviews', help='Get MR approvals')
    pr_reviews_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')

    # pr comments
    pr_comments_parser = pr_subparsers.add_parser('comments', help='Get MR discussion comments')
    pr_comments_parser.add_argument('--pr-number', required=True, type=int, help='MR number (iid)')
    pr_comments_parser.add_argument('--unresolved-only', action='store_true', help='Only show unresolved comments')

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

    args = parser.parse_args()

    if args.command == 'pr':
        if args.pr_command == 'create':
            return cmd_pr_create(args)
        elif args.pr_command == 'reviews':
            return cmd_pr_reviews(args)
        elif args.pr_command == 'comments':
            return cmd_pr_comments(args)
    elif args.command == 'ci':
        if args.ci_command == 'status':
            return cmd_ci_status(args)
        elif args.ci_command == 'wait':
            return cmd_ci_wait(args)
    elif args.command == 'issue':
        if args.issue_command == 'create':
            return cmd_issue_create(args)
        elif args.issue_command == 'view':
            return cmd_issue_view(args)

    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
