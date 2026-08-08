#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub issue command handlers.

Holds the ``cmd_issue_*`` handler bodies plus the issue-only prepare-body
handlers. Every network primitive and monkeypatch-sensitive helper (``run_gh``,
``check_auth``, ``poll_until``, ``_fetch_issue_state_and_labels``) lives in the
entry module ``github_ops`` and is reached via ATTRIBUTE access on the imported
``github_ops`` module at call time — never ``from github_ops import <name>``,
which would defeat a test's ``monkeypatch.setattr(github_ops, '<name>', ...)``.
"""

import argparse
import json

import github_ops
from ci_base import (
    BODY_KIND_ISSUE_COMMENT,
    BODY_KIND_ISSUE_CREATE,
    delete_consumed_body,
    make_error,
    make_simple_handler,
    normalize_issue_ref,
    prepare_body,
    read_and_consume_body,
)


def cmd_issue_create(args: argparse.Namespace) -> dict:
    """Handle 'issue create' subcommand."""
    # Check auth
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('issue_create', err)

    # Consume the prepared issue body
    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_ISSUE_CREATE, getattr(args, 'slot', None))
    if err_dict:
        return make_error('issue_create', err_dict.get('message', 'body not prepared'))

    # Build command
    gh_args = ['issue', 'create', '--title', args.title, '--body', body]
    if args.labels:
        gh_args.extend(['--label', args.labels])

    # Execute
    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('issue_create', 'Failed to create issue', stderr.strip())

    delete_consumed_body(args.plan_id, BODY_KIND_ISSUE_CREATE, getattr(args, 'slot', None))

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


def cmd_issue_comment(args: argparse.Namespace) -> dict:
    """Handle 'issue comment' subcommand - post a comment on an existing issue."""
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('issue_comment', err)

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_ISSUE_COMMENT, getattr(args, 'slot', None))
    if err_dict or body is None:
        return make_error('issue_comment', (err_dict or {}).get('message', 'body not prepared'))

    issue_id = normalize_issue_ref(args.issue)
    gh_args = ['issue', 'comment', issue_id, '--body', body]
    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('issue_comment', f'Failed to comment on issue {issue_id}', stderr.strip())

    delete_consumed_body(args.plan_id, BODY_KIND_ISSUE_COMMENT, getattr(args, 'slot', None))
    return {
        'status': 'success',
        'operation': 'issue_comment',
        'issue_number': issue_id,
        'output': stdout.strip(),
    }


def cmd_issue_view(args: argparse.Namespace) -> dict:
    """Handle 'issue view' subcommand."""
    # Check auth
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('issue_view', err)

    # Get issue details - request all relevant fields
    issue_id = normalize_issue_ref(args.issue)
    gh_args = [
        'issue',
        'view',
        issue_id,
        '--json',
        'number,url,title,body,author,state,createdAt,updatedAt,labels,assignees,milestone',
    ]

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('issue_view', f'Failed to view issue {issue_id}', stderr.strip())

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
        'author': (data.get('author') or {}).get('login', 'unknown'),
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
    lambda args: ['issue', 'close', normalize_issue_ref(args.issue)],
    github_ops.run_gh,
    github_ops.check_auth,
    result_extras=lambda args: {'issue_number': normalize_issue_ref(args.issue)},
)


def cmd_issue_wait_for_close(args: argparse.Namespace) -> dict:
    """Handle 'issue wait-for-close' — poll until the issue transitions to closed or timeout.

    Replaces blocking shell ``sleep`` patterns in workflows that wait for an
    issue to be closed by another actor. Snapshots the current state, then
    polls on the standard CI interval and exits as soon as the state is no
    longer ``open`` (i.e. the issue has transitioned to ``closed``).
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('issue_wait_for_close', err)

    ok, initial = github_ops._fetch_issue_state_and_labels(args.issue_number)
    if not ok:
        return make_error(
            'issue_wait_for_close',
            initial.get('error', f'Initial state fetch failed for issue {args.issue_number}'),
            initial.get('context', ''),
        )
    baseline_state = initial['state']

    def check_fn() -> tuple[bool, dict]:
        inner_ok, data = github_ops._fetch_issue_state_and_labels(args.issue_number)
        if not inner_ok:
            return False, data
        return True, {'state': data['state']}

    def is_complete_fn(data: dict) -> bool:
        return data.get('state') != 'open'

    result = github_ops.poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error(
            'issue_wait_for_close',
            result['error'],
            result.get('last_data', {}).get('context', ''),
        )

    final_state = result['last_data'].get('state', baseline_state)
    return {
        'status': 'success',
        'operation': 'issue_wait_for_close',
        'issue_number': args.issue_number,
        'timed_out': result['timed_out'],
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'baseline_state': baseline_state,
        'final_state': final_state,
    }


def cmd_issue_wait_for_label(args: argparse.Namespace) -> dict:
    """Handle 'issue wait-for-label' — poll until the requested label transitions state.

    Snapshots whether ``args.label`` is present on the issue, then polls on the
    standard CI interval and exits as soon as presence flips and matches the
    requested ``--mode`` (``present`` means wait for the label to appear,
    ``absent`` means wait for it to disappear).
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('issue_wait_for_label', err)

    ok, initial = github_ops._fetch_issue_state_and_labels(args.issue_number)
    if not ok:
        return make_error(
            'issue_wait_for_label',
            initial.get('error', f'Initial label fetch failed for issue {args.issue_number}'),
            initial.get('context', ''),
        )
    baseline_present = args.label in initial['labels']

    def check_fn() -> tuple[bool, dict]:
        inner_ok, data = github_ops._fetch_issue_state_and_labels(args.issue_number)
        if not inner_ok:
            return False, data
        return True, {'labels': data['labels']}

    def is_complete_fn(data: dict) -> bool:
        present_now = args.label in data.get('labels', [])
        if present_now == baseline_present:
            return False
        if args.mode == 'present':
            return present_now is True
        return present_now is False

    result = github_ops.poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error(
            'issue_wait_for_label',
            result['error'],
            result.get('last_data', {}).get('context', ''),
        )

    final_present = args.label in result['last_data'].get('labels', [])
    return {
        'status': 'success',
        'operation': 'issue_wait_for_label',
        'issue_number': args.issue_number,
        'label': args.label,
        'mode': args.mode,
        'timed_out': result['timed_out'],
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'baseline_present': baseline_present,
        'final_present': final_present,
    }


def _cmd_issue_prepare_body(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for an issue description."""
    return prepare_body(args.plan_id, BODY_KIND_ISSUE_CREATE, getattr(args, 'slot', None))


def _cmd_issue_prepare_comment(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for an issue comment."""
    return prepare_body(args.plan_id, BODY_KIND_ISSUE_COMMENT, getattr(args, 'slot', None))
