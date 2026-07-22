#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    issue comment   Post a comment on an existing issue
    issue view      View issue details
    issue close     Close an issue
    branch delete   Delete a remote branch via REST API

Usage (bodies supplied via path-allocate pattern: prepare-body → write file → consume):
    python3 gitlab.py pr prepare-body --plan-id EXAMPLE-PLAN [--for create|edit] [--slot name]
    python3 gitlab.py pr prepare-comment --plan-id EXAMPLE-PLAN [--for reply|thread-reply] [--slot name]
    python3 gitlab.py issue prepare-body --plan-id EXAMPLE-PLAN [--slot name]
    python3 gitlab.py issue prepare-comment --plan-id EXAMPLE-PLAN [--slot name]
    python3 gitlab.py pr create --title "Title" --plan-id EXAMPLE-PLAN [--base main] [--draft]
    python3 gitlab.py pr view
    python3 gitlab.py pr list [--head feature/branch] [--state open|closed|all]
    python3 gitlab.py pr reviews --pr-number 123
    python3 gitlab.py pr comments --pr-number 123 [--unresolved-only]
    python3 gitlab.py pr reply --pr-number 123 --plan-id EXAMPLE-PLAN
    python3 gitlab.py pr resolve-thread --pr-number 123 --thread-id abc123
    python3 gitlab.py pr thread-reply --pr-number 123 --thread-id abc123 --plan-id EXAMPLE-PLAN
    python3 gitlab.py pr merge --pr-number 123 [--strategy squash] [--delete-branch]
    python3 gitlab.py pr auto-merge --pr-number 123 [--strategy squash]
    python3 gitlab.py pr close --pr-number 123
    python3 gitlab.py pr ready --pr-number 123
    python3 gitlab.py pr edit --pr-number 123 --plan-id EXAMPLE-PLAN [--title "New Title"]
    python3 gitlab.py ci status --pr-number 123
    python3 gitlab.py ci wait --pr-number 123 [--timeout 300] [--interval 30]
    python3 gitlab.py ci rerun --run-id 12345
    python3 gitlab.py ci logs --run-id 12345
    python3 gitlab.py issue create --title "Title" --plan-id EXAMPLE-PLAN [--labels "bug,priority::high"]
    python3 gitlab.py issue comment --issue 123 --plan-id EXAMPLE-PLAN [--slot name]
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
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ci_base import (
    BODY_KIND_ISSUE_COMMENT,
    BODY_KIND_ISSUE_CREATE,
    BODY_KIND_PR_CREATE,
    BODY_KIND_PR_EDIT,
    BODY_KIND_PR_REPLY,
    BODY_KIND_PR_THREAD_REPLY,
    MAX_ELAPSED_SECONDS,
    MERGE_QUEUE_ELIGIBLE_CONFIGURED,
    MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
    MERGE_QUEUE_INELIGIBLE,
    MERGE_QUEUE_UNSUPPORTED,
    HandlerMap,
    add_pr_create_args,
    add_pr_resolve_thread_pr_number,
    build_parser,
    check_auth_cli,
    compute_elapsed,
    compute_total_elapsed,
    delete_consumed_body,
    dispatch,
    enrich_failing_checks_with_logs,
    extract_routing_args,
    get_default_cwd,
    make_error,
    make_pr_number_handler,
    make_simple_handler,
    normalize_issue_ref,
    parse_args_with_toon_errors,
    poll_until,
    prepare_body,
    read_and_consume_body,
    record_wait_mechanism,
    run_cli,
    safe_main,
    serialize_toon,
    set_default_cwd,
    truncate_log_content,
)

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
    """Handle 'pr create' subcommand (creates MR in GitLab).

    The MR body comes from exactly ONE of two mutually-exclusive sources: the
    plan-bound body store (``--plan-id`` [+ ``--slot``]) or an explicit
    ``--body-file PATH`` (the plan-less / steward path). Supplying neither, or
    both, is rejected.
    """
    # Check auth
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_create', err)

    # Resolve the body from exactly one source before any network call. Both
    # ``plan_id`` and ``body_file`` are read defensively via getattr so a
    # direct-Namespace caller that bypasses the argparse parser and omits either
    # flag falls through to the "no body source" error instead of raising
    # AttributeError.
    plan_id = getattr(args, 'plan_id', None)
    body_file = getattr(args, 'body_file', None)
    if plan_id and body_file:
        return make_error(
            'pr_create',
            '--plan-id and --body-file are mutually exclusive; supply exactly one body source',
        )
    if not plan_id and not body_file:
        return make_error(
            'pr_create',
            'A MR body source is required: supply either --plan-id (plan-bound body '
            'store) or --body-file PATH (plan-less body file)',
        )

    consumed_from_store = False
    if body_file:
        # Plan-less path: read the body directly from the explicit file.
        try:
            body = Path(body_file).read_text(encoding='utf-8')
        except OSError as exc:
            return make_error('pr_create', f'Could not read --body-file {body_file}', str(exc))
        if not body.strip():
            return make_error('pr_create', f'--body-file is empty: {body_file}')
    else:
        # Plan-bound path: plan_id is non-None here — the mutual-exclusion guard
        # above returned early when both sources were falsy, and body_file is
        # falsy in this branch.
        assert plan_id is not None  # noqa: S101 — narrowing after the mutual-exclusion guard
        store_body, err_dict = read_and_consume_body(plan_id, BODY_KIND_PR_CREATE, getattr(args, 'slot', None))
        if err_dict or store_body is None:
            return make_error('pr_create', (err_dict or {}).get('message', 'body not prepared'))
        body = store_body
        consumed_from_store = True

    # Build command - glab uses 'mr' for merge requests
    glab_args = ['mr', 'create', '--title', args.title, '--description', body]
    if args.base:
        glab_args.extend(['--target-branch', args.base])
    if args.draft:
        glab_args.append('--draft')
    if getattr(args, 'head', None):
        glab_args.extend(['--source-branch', args.head])
    # Optional --label passthrough (repeatable), mirroring the GitHub provider's
    # cmd_pr_create. create-pr applies `--label skip-bot-review` when the
    # enabled_bots set is empty; without this forward the label would be silently
    # dropped on GitLab MRs.
    for label in getattr(args, 'label', None) or []:
        glab_args.extend(['--label', label])

    # Execute
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_create', 'Failed to create MR', stderr.strip())

    # Delete the consumed scratch body — only when it came from the plan store.
    if consumed_from_store:
        assert plan_id is not None  # noqa: S101 — consumed_from_store is set only on the plan-bound path
        delete_consumed_body(plan_id, BODY_KIND_PR_CREATE, getattr(args, 'slot', None))

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


def cmd_pr_reply(args: argparse.Namespace) -> dict:
    """Handle 'pr reply' — post a note using the prepared body."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_reply', err)

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_PR_REPLY, getattr(args, 'slot', None))
    if err_dict or body is None:
        return make_error('pr_reply', (err_dict or {}).get('message', 'body not prepared'))

    glab_args = ['mr', 'note', str(args.pr_number), '--message', body]
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_reply', 'Failed to post note', stderr.strip())

    delete_consumed_body(args.plan_id, BODY_KIND_PR_REPLY, getattr(args, 'slot', None))
    return {
        'status': 'success',
        'operation': 'pr_reply',
        'pr_number': args.pr_number,
        'output': stdout.strip(),
    }


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

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_PR_THREAD_REPLY, getattr(args, 'slot', None))
    if err_dict:
        return make_error('pr_thread_reply', err_dict.get('message', 'body not prepared'))

    encoded_path = quote(project_path, safe='')
    # GitLab's discussion notes endpoint publishes replies immediately —
    # there is no pending/draft state here, unlike GitHub's PR review flow.
    endpoint = f'projects/{encoded_path}/merge_requests/{args.pr_number}/discussions/{args.thread_id}/notes'

    returncode, stdout, stderr = run_glab(['api', '-X', 'POST', endpoint, '-f', f'body={body}'])
    if returncode != 0:
        return make_error('pr_thread_reply', f'Failed to reply to thread: {stderr.strip()}')

    delete_consumed_body(args.plan_id, BODY_KIND_PR_THREAD_REPLY, getattr(args, 'slot', None))

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


# ---------------------------------------------------------------------------
# Merge-train (GitLab platform equivalent of a GitHub merge queue)
# ---------------------------------------------------------------------------
#
# GitLab merge trains are a Premium/Ultimate-tier feature enabled per-project.
# The REST surface is:
#   * probe:  GET  /projects/:id                     → merge_trains_enabled bool
#   * enable: PUT  /projects/:id                      → merge_trains_enabled=true
#   * enqueue:POST /projects/:id/merge_trains/merge_requests/:iid
# Auth/permission failures return the actionable error, never a stack trace.

# Actionable remedy surfaced when a merge-train call fails on scope/permission.
_MERGE_TRAIN_AUTH_SCOPE_HINT = (
    'the glab token lacks the scope/permission to read or update project '
    'merge-train settings. Ensure the token has at least Maintainer access and '
    "the 'api' scope, then retry."
)

# Actionable remedy surfaced when the project/tier does not offer merge trains.
_MERGE_TRAIN_INELIGIBLE_HINT = (
    'GitLab merge trains require a Premium/Ultimate tier and must be enabled '
    'per-project (Settings → Merge requests → Merge trains). This project is '
    'not eligible or the feature is unavailable on the current tier.'
)


def _is_auth_scope_error(stderr: str) -> bool:
    """Return True when *stderr* names an auth/permission-scope failure (401/403)."""
    lowered = stderr.lower()
    return 'http 401' in lowered or 'http 403' in lowered


def _probe_merge_train_state() -> tuple[str, str, str | None]:
    """Probe the project merge-train configuration state.

    Returns ``(discriminator, detail, error)`` where ``discriminator`` is one of
    the shared ``MERGE_QUEUE_*`` constants. ``error`` is a non-None actionable
    string (the caller converts it to a ``make_error`` result) on every failure
    that is NOT a confirmed feature-availability verdict — an auth-scope failure,
    a generic non-auth ``run_api`` failure, or a malformed (non-object) project
    response. Only the genuine feature/tier-absence verdicts carry ``error=None``:
    an unresolvable project path and an absent ``merge_trains_enabled`` field
    (both mapped to ``ineligible``), plus the two eligible outcomes. A
    transient/API failure therefore surfaces as a real, retryable ``unsupported``
    error rather than being folded into a permanent ``ineligible`` refusal.
    """
    project_path = get_project_path()
    if not project_path:
        return MERGE_QUEUE_INELIGIBLE, 'could not determine project path', None
    project_id = quote(project_path, safe='')
    returncode, data, err = run_api(f'projects/{project_id}')
    if returncode != 0:
        if _is_auth_scope_error(err):
            return MERGE_QUEUE_INELIGIBLE, err.strip(), _MERGE_TRAIN_AUTH_SCOPE_HINT
        detail = err.strip() or 'project merge-train probe failed'
        return MERGE_QUEUE_UNSUPPORTED, detail, detail
    if not isinstance(data, dict):
        detail = 'project response was not an object'
        return MERGE_QUEUE_UNSUPPORTED, detail, detail
    if 'merge_trains_enabled' not in data:
        # Field absent → the tier/feature does not expose merge trains.
        return MERGE_QUEUE_INELIGIBLE, 'merge_trains_enabled not present on project', None
    if data.get('merge_trains_enabled') is True:
        return MERGE_QUEUE_ELIGIBLE_CONFIGURED, 'merge_trains_enabled=true', None
    return MERGE_QUEUE_ELIGIBLE_UNCONFIGURED, 'merge_trains_enabled=false', None


def cmd_pr_merge_queue(args: argparse.Namespace) -> dict:
    """Handle 'pr merge-queue' on GitLab — enqueue the MR onto the merge train.

    Performs a REAL merge-train enqueue via
    ``POST /projects/:id/merge_trains/merge_requests/:iid`` rather than silently
    falling back to an immediate merge (which would defeat the external-commit
    serialization the caller asked for). When the project/tier does not offer
    merge trains the handler returns the actionable ineligible error.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_merge_queue', err)

    iid, err_dict = _resolve_mr_iid(args, 'pr_merge_queue')
    if err_dict:
        return err_dict
    assert iid is not None  # noqa: S101 — narrowing after err_dict guard

    project_path = get_project_path()
    if not project_path:
        return make_error('pr_merge_queue', 'Could not determine project path')

    project_id = quote(project_path, safe='')
    endpoint = f'projects/{project_id}/merge_trains/merge_requests/{iid}'
    returncode, stdout, stderr = run_glab(['api', '-X', 'POST', endpoint])
    if returncode != 0:
        stderr_text = stderr.strip()
        if _is_auth_scope_error(stderr_text) or 'http 404' in stderr_text.lower():
            return make_error('pr_merge_queue', _MERGE_TRAIN_INELIGIBLE_HINT, stderr_text)
        return make_error('pr_merge_queue', f'Failed to enqueue MR {iid} onto the merge train', stderr_text)

    # Best-effort parse of the returned merge-train car for the position/id.
    car_id = ''
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            car_id = str(data.get('id', '') or '')
    except json.JSONDecodeError:
        pass

    return {
        'status': 'success',
        'operation': 'pr_merge_queue',
        'provider': 'gitlab',
        'pr_number': args.pr_number if args.pr_number else iid,
        'enqueued': True,
        'merge_train_car_id': car_id,
    }


def cmd_repo_merge_queue_probe(args: argparse.Namespace) -> dict:
    """Handle 'repo merge-queue probe' on GitLab — report merge-train state.

    Returns a success TOON carrying ``eligibility`` (one of the shared
    discriminators). An auth-scope failure returns the actionable error.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('repo_merge_queue_probe', err)

    discriminator, detail, scope_error = _probe_merge_train_state()
    if scope_error is not None:
        return make_error('repo_merge_queue_probe', scope_error, detail)

    return {
        'status': 'success',
        'operation': 'repo_merge_queue_probe',
        'provider': 'gitlab',
        'eligibility': discriminator,
        'detail': detail,
    }


def cmd_repo_merge_queue_enable(args: argparse.Namespace) -> dict:
    """Handle 'repo merge-queue enable' on GitLab — enable the per-project merge train.

    Probes first: an already-enabled project returns success without mutation;
    an unconfigured-but-eligible project gets ``merge_trains_enabled=true`` set
    via ``PUT /projects/:id``; an ineligible project refuses with the actionable
    error.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('repo_merge_queue_enable', err)

    discriminator, detail, scope_error = _probe_merge_train_state()
    if scope_error is not None:
        return make_error('repo_merge_queue_enable', scope_error, detail)

    if discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED:
        return {
            'status': 'success',
            'operation': 'repo_merge_queue_enable',
            'provider': 'gitlab',
            'eligibility': discriminator,
            'changed': False,
            'detail': 'merge trains already enabled; no change made',
        }

    if discriminator == MERGE_QUEUE_ELIGIBLE_UNCONFIGURED:
        project_path = get_project_path()
        if not project_path:
            return make_error('repo_merge_queue_enable', 'Could not determine project path')
        project_id = quote(project_path, safe='')
        returncode, _stdout, stderr = run_glab(
            ['api', '-X', 'PUT', f'projects/{project_id}', '-f', 'merge_trains_enabled=true']
        )
        if returncode != 0:
            stderr_text = stderr.strip()
            if _is_auth_scope_error(stderr_text):
                return make_error('repo_merge_queue_enable', _MERGE_TRAIN_AUTH_SCOPE_HINT, stderr_text)
            return make_error('repo_merge_queue_enable', 'Failed to enable merge trains', stderr_text)
        return {
            'status': 'success',
            'operation': 'repo_merge_queue_enable',
            'provider': 'gitlab',
            'eligibility': MERGE_QUEUE_ELIGIBLE_CONFIGURED,
            'changed': True,
            'detail': 'merge_trains_enabled set to true',
        }

    # ineligible / unsupported → refuse with the actionable message.
    return make_error('repo_merge_queue_enable', _MERGE_TRAIN_INELIGIBLE_HINT, detail)


def cmd_repo_label_ensure(args: argparse.Namespace) -> dict:
    """Handle 'repo label ensure' on GitLab — ensure a project label exists (idempotent).

    ``glab label create`` errors when the label already exists, so an
    "already exists" (HTTP 409) failure is treated as a no-op success —
    create-if-missing semantics matching the GitHub provider. Optional
    ``--color`` / ``--description`` are passed through; GitLab expects a
    ``#``-prefixed hex color, so a bare 6-hex ``--color`` is prefixed here.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('repo_label_ensure', err)

    glab_args = ['label', 'create', '--name', args.label]
    color = getattr(args, 'color', None)
    if color:
        glab_args.extend(['--color', color if color.startswith('#') else f'#{color}'])
    if getattr(args, 'description', None):
        glab_args.extend(['--description', args.description])

    returncode, _stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        stderr_text = stderr.strip()
        stderr_lower = stderr_text.lower()
        # Idempotent: a duplicate create (GitLab "already exists" / HTTP 409) is a
        # no-op success, mirroring GitHub's `gh label create --force` semantics.
        # Both substrings are matched against the lower-cased stderr so a
        # lower-case "http 409" response is not missed.
        if 'already exist' in stderr_lower or 'http 409' in stderr_lower:
            return {
                'status': 'success',
                'operation': 'repo_label_ensure',
                'provider': 'gitlab',
                'label': args.label,
                'ensured': True,
                'already_present': True,
            }
        return make_error('repo_label_ensure', f'Failed to ensure label {args.label!r}', stderr_text)

    return {
        'status': 'success',
        'operation': 'repo_label_ensure',
        'provider': 'gitlab',
        'label': args.label,
        'ensured': True,
        'already_present': False,
    }


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


# GitLab job ``status`` partitioning. The raw job-status vocabulary is
# lower-case ``success | skipped | manual | failed | canceled | created |
# pending | running | preparing | scheduled | waiting_for_resource``. The
# three partitions below carry the canonical status → outcome table.
_JOB_STATUS_NON_FAILING: frozenset[str] = frozenset({'success', 'skipped', 'manual'})
_JOB_STATUS_FAILING: frozenset[str] = frozenset({'failed', 'canceled'})
_JOB_STATUS_WAIT: frozenset[str] = frozenset(
    {'created', 'pending', 'running', 'preparing', 'scheduled', 'waiting_for_resource', ''}
)


def _normalize_job_status(job: dict) -> str:
    """Return the canonical lower-case status for a GitLab job row.

    Missing or null values are normalised to the empty string, which the
    partition table treats as a wait-state.
    """

    raw = job.get('status')
    if raw is None:
        return ''
    return str(raw).lower()


def _build_failing_check_entry(job: dict) -> dict:
    """Build the transport-rich ``failing_checks[]`` entry for a single job.

    Mirrors the GitHub provider entry shape so deliverables 6 and 7 see a
    provider-independent contract.
    """

    entry: dict[str, Any] = {
        'name': job.get('name', 'unknown'),
        'conclusion': _normalize_job_status(job) or 'pending',
        'workflow_name': job.get('stage') or '',
        'job_name': job.get('name', '') or '',
        'started_at': job.get('started_at') or job.get('created_at') or '',
        'completed_at': job.get('finished_at') or '',
        'run_id': str(job.get('pipeline_id') or job.get('pipeline', {}).get('id', '') if isinstance(job.get('pipeline'), dict) else (job.get('pipeline_id') or '')),
        'run_url': job.get('web_url') or '',
    }
    return entry


def _classify_check_buckets(
    jobs: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Partition GitLab job rows into ``(failing, wait, non_failing)``.

    Unknown future statuses default to the failing partition (defense in
    depth — an unknown status is never silently accepted as success).
    """

    failing: list[dict] = []
    wait: list[dict] = []
    non_failing: list[dict] = []
    for job in jobs:
        status = _normalize_job_status(job)
        if status in _JOB_STATUS_NON_FAILING:
            non_failing.append(job)
        elif status in _JOB_STATUS_WAIT:
            wait.append(job)
        else:
            failing.append(job)
    return failing, wait, non_failing


def _derive_overall_status(jobs: list[dict]) -> tuple[str, list[dict], list[dict]]:
    """Derive ``overall | final_status`` plus failing-jobs transport.

    Returns ``(status, failing_job_rows, wait_job_rows)`` where ``status``
    is one of ``pending | success | failure | none``. The ``mixed`` outcome
    is intentionally absent — every input resolves to one of the four
    canonical states.
    """

    if not jobs:
        return 'none', [], []
    failing, wait, _non_failing = _classify_check_buckets(jobs)
    if wait:
        return 'pending', [], wait
    if failing:
        return 'failure', failing, []
    return 'success', [], []


def _fetch_mr_head_sha(pr_number: int | str) -> str:
    """Resolve the head commit SHA for a MR via ``glab mr view``.

    Returns the SHA on success; on any failure path returns an empty string
    so callers can still emit the rest of the envelope without aborting.
    """

    returncode, stdout, _stderr = run_glab(['mr', 'view', str(pr_number), '--output', 'json'])
    if returncode != 0:
        return ''
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return ''
    return str(data.get('sha') or data.get('diff_refs', {}).get('head_sha') or '')


def format_checks_toon(
    jobs: list[dict],
    *,
    duration_ceiling: int | None = None,
) -> tuple[list[dict], int]:
    """Format GitLab pipeline jobs into TOON-compatible dicts and compute overall elapsed.

    Per-job rows omit the ``elapsed_sec`` key entirely when
    :func:`compute_elapsed` returns ``None`` (Go zero-value timestamp or
    parse failure) — TOON callers treat absent keys as null-equivalent.

    The aggregate ``elapsed_sec`` is clamped via warn-and-substitute when it
    falls outside ``0 ≤ x ≤ 24*3600``: a stderr warning is emitted and the
    return value is replaced with ``duration_ceiling`` (caller-supplied for
    ``ci_wait``) or ``0`` (default for ``ci_status``).

    Returns ``(list_of_job_dicts, elapsed_sec_total)``.
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

        elapsed = compute_elapsed(started_at, job.get('finished_at'), now)
        row: dict = {
            'name': job.get('name', 'unknown'),
            'status': state,
            'result': result,
            'url': job.get('web_url') or '-',
            'stage': job.get('stage') or '-',
        }
        if elapsed is not None:
            row['elapsed_sec'] = elapsed
        rows.append(row)

    total_elapsed = compute_total_elapsed(started_at_values, now)

    # Defense-in-depth: clamp aggregate to a sane window. The per-job filter
    # above should already prevent zero-time leakage, but a runaway value here
    # would mask a regression — substitute the caller's ceiling and warn.
    if total_elapsed < 0 or total_elapsed > MAX_ELAPSED_SECONDS:
        print(
            'format_checks_toon: aggregate elapsed_sec out of range, clamping',
            file=sys.stderr,
        )
        total_elapsed = duration_ceiling if duration_ceiling is not None else 0

    return rows, total_elapsed


def _capture_router_plan_id(argv: list[str]) -> str | None:
    """Re-extract the router-level ``--plan-id`` from the original argv.

    ``extract_routing_args`` consumes ``--plan-id`` for cwd resolution but does
    not surface the value, which the failure-path log-download hook needs to
    locate the plan-scoped artifact tree. The checks subcommands declare no
    subcommand-level ``--plan-id``, so the first occurrence is unambiguously the
    router-level flag. Returns ``None`` when no ``--plan-id`` was supplied (the
    hook degrades to a no-op enrichment in that case).
    """
    try:
        from resolve_project_dir import extract_plan_id
    except ImportError:
        return None
    plan_id, _ = extract_plan_id(list(argv))
    return plan_id


def _fetch_failed_job_trace(run_id: str, job_id: str = '') -> str | None:
    """Download the raw failing-job trace for a pipeline via ``glab ci trace``.

    Reuses the same CLI invocation as :func:`cmd_ci_logs` (honouring the
    router's process-global cwd) but returns the full, untruncated stdout (the
    filter/persist layer applies its own extraction). Returns ``None`` on any
    non-zero exit or subprocess error so the enrich hook degrades that entry
    gracefully without aborting siblings.

    ``job_id`` is accepted to match the shared ``raw_log_fetcher`` callback
    signature (the GitHub path uses it to target a nested reusable-workflow job)
    and is intentionally ignored here — ``glab ci trace`` resolves the failing
    job from the pipeline id directly.
    """
    try:
        result = subprocess.run(
            ['glab', 'ci', 'trace', str(run_id)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=get_default_cwd(),
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _enrich_failing_checks(
    entries: list[dict],
    *,
    plan_id: str | None,
    error_style: str,
    head_sha: str,
    pr_number: int | str,
) -> list[dict]:
    """Inject per-run keys and run the shared download+filter+store hook.

    Seeds each entry with ``head_sha`` / ``pr_number`` so the persisted manifest
    is keyed correctly, then delegates to
    :func:`ci_base.enrich_failing_checks_with_logs` (per-entry graceful degrade).
    """
    for entry in entries:
        entry.setdefault('head_sha', head_sha)
        entry.setdefault('pr_number', pr_number)
    return enrich_failing_checks_with_logs(
        failing_checks=entries,
        provider='gitlab',
        raw_log_fetcher=_fetch_failed_job_trace,
        plan_id=plan_id,
        error_style=error_style,
    )


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

    # Derive overall via the canonical job-status partition. ``mixed`` is no
    # longer possible — every input resolves to ``pending | success |
    # failure | none``.
    overall, failing_rows, _wait_rows = _derive_overall_status(jobs)
    # When the pipeline envelope itself reports a definitive state but jobs
    # are missing (rare API hiccup), fall back to the pipeline_status mapping
    # so callers still see a sensible overall instead of ``none``.
    if not jobs and pipeline_status and pipeline_status != 'unknown':
        pipeline_map = {
            'success': 'success',
            'failed': 'failure',
            'canceled': 'failure',
            'skipped': 'success',
            'running': 'pending',
            'pending': 'pending',
            'created': 'pending',
        }
        overall = pipeline_map.get(pipeline_status, overall)

    # Format checks table — ci_status has no caller-supplied duration ceiling,
    # so out-of-range aggregates are substituted with 0.
    checks, total_elapsed = format_checks_toon(jobs, duration_ceiling=0)

    # Output TOON
    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'ci_status',
        'pr_number': args.pr_number if args.pr_number else iid,
        'overall_status': overall,
        'check_count': len(jobs),
        'elapsed_sec': total_elapsed,
        'checks': checks,
    }

    # On failure, surface the per-job failing-checks table enriched with each
    # entry's downloaded raw + filtered trace paths. Success/pending paths are
    # unchanged.
    if overall == 'failure':
        failing_entries = [_build_failing_check_entry(c) for c in failing_rows]
        head_sha = _fetch_mr_head_sha(iid)
        result['failing_checks'] = _enrich_failing_checks(
            failing_entries,
            plan_id=getattr(args, 'router_plan_id', None),
            error_style=getattr(args, 'error_style', 'generic'),
            head_sha=head_sha,
            pr_number=args.pr_number if args.pr_number else iid,
        )

    return result


#: Run-configuration command key under which the observed ``ci wait`` durations
#: are recorded (the p50 seed source for the adaptive first sleep). Mirrors the
#: ``ci:wait`` key ``ci_complete_precondition`` uses for the timeout ceiling and
#: the GitHub provider's ``_CI_WAIT_DURATION_KEY``.
_CI_WAIT_DURATION_KEY = 'ci:wait'


def _monotonic() -> float:
    """Monotonic wall-clock seam. Isolated so tests can supply a deterministic
    clock and observe the recorded wait duration in constant time."""
    import time

    return time.monotonic()


def _sleep_seed(seconds: int) -> None:
    """Sleep the p50-seeded first wait exactly once.

    Isolated as a seam so tests neutralise the sleep and run in constant time.
    A non-positive value is a no-op.
    """
    if seconds > 0:
        import time

        time.sleep(seconds)


def _read_ci_wait_p50_seed() -> int | float | None:
    """Read the p50 (median) seed for the ``ci:wait`` duration window.

    Private seam over the run-configuration ci-duration API so ``cmd_ci_wait``
    can seed its first sleep from history. Returns ``None`` on an empty/absent
    window or any failure, so the caller simply skips the seed. Test-mockable.
    """
    try:
        import run_config

        return run_config._p50_of(run_config._read_ci_duration_window(_CI_WAIT_DURATION_KEY))
    except Exception:
        return None


def _record_ci_wait_duration(duration: int) -> None:
    """Record an observed successful ``ci:wait`` duration into the p50 window.

    Private seam over the run-configuration ci-duration record API; best-effort —
    a failure never aborts the wait result. Test-mockable.
    """
    try:
        import run_config

        run_config._record_ci_duration(_CI_WAIT_DURATION_KEY, duration)
    except Exception:
        pass


def _watch_pipeline(pipeline_id: str, timeout: int) -> tuple[int, str, str]:
    """Private subprocess seam over ``glab ci status --wait``.

    Blocks until the checked-out branch's pipeline reaches a terminal state — the
    purpose-built terminal-state watch verb, never a hand-rolled sleep loop.
    Test-mockable via monkeypatch. ``pipeline_id`` is accepted for symmetry /
    telemetry; ``glab ci status`` resolves the pipeline from the branch. Returns
    ``(returncode, stdout, stderr)``.
    """
    try:
        result = subprocess.run(
            ['glab', 'ci', 'status', '--wait'],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=get_default_cwd(),
        )
    except Exception:
        return 1, '', 'glab ci status --wait failed'
    return result.returncode, result.stdout, result.stderr


def _fetch_mr_jobs(pr_number: int | str) -> tuple[bool, dict]:
    """Fetch the MR's pipeline jobs via ``glab mr view`` + ``glab ci view``.

    Returns ``(True, {'jobs', 'pipeline_id', 'pipeline_status'})`` on success, or
    ``(False, {'error', 'context'})`` on a fetch / parse failure — the same shape
    the retained ``poll_until`` fallback consumes.
    """
    returncode, stdout, stderr = run_glab(['mr', 'view', str(pr_number), '--output', 'json'])
    if returncode != 0:
        return False, {'error': f'Failed to get MR {pr_number}', 'context': stderr.strip()}
    try:
        data = json.loads(stdout)
        pipeline = data.get('pipeline', {})
        pipeline_status = pipeline.get('status', 'unknown')
        pipeline_id = pipeline.get('id', 'unknown')
    except json.JSONDecodeError:
        return False, {'error': 'Failed to parse glab output', 'context': stdout[:100]}

    jobs: list[dict] = []
    if pipeline_id and pipeline_id != 'unknown':
        rc, out, _ = run_glab(['ci', 'view', str(pipeline_id), '--output', 'json'])
        if rc == 0:
            try:
                ci_data = json.loads(out)
                jobs = ci_data.get('jobs', [])
            except json.JSONDecodeError:
                pass
    return True, {'jobs': jobs, 'pipeline_id': pipeline_id, 'pipeline_status': pipeline_status}


def cmd_ci_wait(args: argparse.Namespace) -> dict:
    """Handle 'ci wait' — p50-seeded first sleep, then terminal-state watch tail.

    GitLab counterpart to the GitHub ``cmd_ci_wait`` rework. Replaces the
    fixed-interval ``poll_until`` re-fetch of the MR pipeline with a two-stage,
    detach-friendly wait:

    1. **p50-seeded first sleep** — sleep once for the historical p50 (median) of
       observed ``ci:wait`` durations (bounded by ``--timeout``, skipped on an
       empty window), so the known-busy window is not polled from second zero.
    2. **terminal-state watch tail** — delegate the tail to ``glab ci status
       --wait`` (the purpose-built watch verb, never a hand-rolled sleep loop),
       then re-snapshot the pipeline jobs once.

    On a natural (non-timeout) SUCCESS completion the observed wall-clock
    duration is recorded back into the p50 window, closing the adaptive loop. The
    external return contract is preserved verbatim: ``final_status``,
    ``duration_sec``, ``failing_checks``, ``wait_outcome``, ``run_id``,
    ``head_sha``, plus the ``deadline_exceeded`` timeout envelope.

    The retained ``poll_until`` fallback covers the edge where the pipeline has
    not yet materialised any watchable jobs (empty jobs, or no resolvable
    pipeline id) — preserving the pre-change "keep waiting until jobs appear,
    then time out" behaviour.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_wait', err)

    start = _monotonic()
    deadline = start + args.timeout
    # Which of the three internal paths actually resolved the wait. Starts at
    # ``seed_only`` — the post-seed snapshot being already terminal is the case
    # where neither the watch tail nor the poll fallback runs. The provider's own
    # path vocabulary maps onto the shared ``WAIT_MECHANISMS`` members, so one
    # log query covers both providers.
    mechanism = 'seed_only'

    # 1. p50-seeded first sleep (once, bounded by --timeout, skipped when empty).
    seed = _read_ci_wait_p50_seed()
    if seed is not None:
        _sleep_seed(min(int(seed), args.timeout))

    # 2. Snapshot the pipeline jobs after the seed sleep.
    ok, data = _fetch_mr_jobs(args.pr_number)
    if not ok:
        return make_error('ci_wait', data['error'], data.get('context', ''))
    jobs = data['jobs']
    pipeline_id = data.get('pipeline_id', '')

    # 3. Terminal-state tail. When the pipeline has watchable jobs still running,
    #    delegate the wait to ``glab ci status --wait`` (a single blocking call —
    #    NOT a hand-rolled sleep loop) and re-snapshot. Otherwise fall back to the
    #    sanctioned ``poll_until`` framework for the remaining budget.
    _f, wait_rows, _nf = _classify_check_buckets(jobs)
    if wait_rows and pipeline_id and pipeline_id != 'unknown':
        remaining = int(deadline - _monotonic())
        if remaining > 0:
            _watch_pipeline(str(pipeline_id), remaining)
            mechanism = 'watch_tail'
        ok, data = _fetch_mr_jobs(args.pr_number)
        if not ok:
            return make_error('ci_wait', data['error'], data.get('context', ''))
        jobs = data['jobs']
        pipeline_id = data.get('pipeline_id', pipeline_id)
    elif not jobs or wait_rows:
        # No watchable jobs yet (empty jobs, or no resolvable pipeline id).
        # Preserve the pre-change wait-for-jobs behaviour via poll_until.
        mechanism = 'poll_fallback'

        def _check_fn() -> tuple[bool, dict]:
            return _fetch_mr_jobs(args.pr_number)

        def _is_complete_fn(inner: dict) -> bool:
            rows = inner.get('jobs', [])
            if not rows:
                # Empty jobs → defer to the terminal pipeline_status (manual-only
                # or no-op pipelines report a terminal status with zero jobs).
                return inner.get('pipeline_status', 'unknown') in {'success', 'failed', 'canceled', 'skipped'}
            _fail, waiting, _nonfail = _classify_check_buckets(rows)
            return not waiting

        remaining = max(1, int(deadline - _monotonic()))
        poll_result = poll_until(_check_fn, _is_complete_fn, timeout=remaining, interval=args.interval)
        if 'error' in poll_result:
            return make_error('ci_wait', poll_result['error'], poll_result['last_data'].get('context', ''))
        last_data = poll_result['last_data']
        jobs = last_data.get('jobs', [])
        pipeline_id = last_data.get('pipeline_id', pipeline_id)

    duration_sec = max(0, int(_monotonic() - start))
    head_sha = _fetch_mr_head_sha(args.pr_number)
    # ci_wait tracks its own wall-clock duration — use it as the clamp ceiling
    # so an out-of-range aggregate is substituted with the actual wait time.
    check_dicts, total_elapsed = format_checks_toon(jobs, duration_ceiling=duration_sec)

    _run_id = str(pipeline_id) if pipeline_id and pipeline_id != 'unknown' else ''

    # A remaining wait partition after the tail is a timeout: enumerate every
    # still-waiting job as a ``failing_checks`` entry so deliverables 6 and 7 can
    # route the timeout into the ``ci-verify-timeout`` producer.
    _f2, wait_rows2, _nf2 = _classify_check_buckets(jobs)
    if wait_rows2:
        wait_entries = [_build_failing_check_entry(c) for c in wait_rows2]
        wait_entries = _enrich_failing_checks(
            wait_entries,
            plan_id=getattr(args, 'router_plan_id', None),
            error_style=getattr(args, 'error_style', 'generic'),
            head_sha=head_sha,
            pr_number=args.pr_number,
        )
        error_data: dict[str, Any] = {
            'status': 'error',
            'operation': 'ci_wait',
            'error': 'Timeout waiting for CI',
            'pr_number': args.pr_number,
            'duration_sec': duration_sec,
            'last_status': 'pending',
            'wait_outcome': 'deadline_exceeded',
            'failing_checks': wait_entries,
            'run_id': _run_id,
            'head_sha': head_sha,
            'mechanism': mechanism,
        }
        if check_dicts:
            error_data['elapsed_sec'] = total_elapsed
            error_data['checks'] = check_dicts
        record_wait_mechanism(
            plan_id=getattr(args, 'router_plan_id', None),
            consumer='ci-wait',
            wait_mechanism=mechanism,
            dispatch=getattr(args, 'dispatch', 'undeclared'),
            wait_target=f'pr#{args.pr_number}',
            outcome='deadline_exceeded',
        )
        return error_data

    # Natural completion — every job reached a terminal status. Partition and
    # derive the final status; the ``mixed`` outcome no longer exists.
    final_status, failing_rows, _wait_rows = _derive_overall_status(jobs)
    failing_checks_entries = [_build_failing_check_entry(c) for c in failing_rows]
    if final_status == 'failure':
        failing_checks_entries = _enrich_failing_checks(
            failing_checks_entries,
            plan_id=getattr(args, 'router_plan_id', None),
            error_style=getattr(args, 'error_style', 'generic'),
            head_sha=head_sha,
            pr_number=args.pr_number,
        )

    # Record the observed wall-clock duration into the p50 window only on a
    # natural SUCCESS completion — the window seeds the next wait's first sleep.
    if final_status == 'success' and duration_sec > 0:
        _record_ci_wait_duration(duration_sec)

    record_wait_mechanism(
        plan_id=getattr(args, 'router_plan_id', None),
        consumer='ci-wait',
        wait_mechanism=mechanism,
        dispatch=getattr(args, 'dispatch', 'undeclared'),
        wait_target=f'pr#{args.pr_number}',
        outcome=final_status,
    )
    return {
        'status': 'success',
        'operation': 'ci_wait',
        'pr_number': args.pr_number,
        'final_status': final_status,
        'duration_sec': duration_sec,
        'elapsed_sec': total_elapsed,
        'checks': check_dicts,
        'failing_checks': failing_checks_entries,
        'wait_outcome': 'completed',
        'run_id': _run_id,
        'head_sha': head_sha,
        'mechanism': mechanism,
    }


cmd_ci_rerun = make_simple_handler(
    'ci_rerun',
    lambda args: ['ci', 'retry', str(args.run_id)],
    run_glab,
    check_auth,
    result_extras=lambda args: {'run_id': args.run_id},
)


def _fetch_pr_overall_ci_status(pr_number: int) -> tuple[bool, Any]:
    """Fetch the overall pipeline status for an MR.

    Returns ``(True, status)`` on success where status is one of
    ``pending|success|failure|none``. On failure returns
    ``(False, {'error': ..., 'context': ...})`` so callers can propagate the
    error dict through ``poll_until`` in the same shape used by ``cmd_ci_wait``.
    Mirrors the GitHub helper: GitLab's raw pipeline statuses are normalised to
    the same four-valued vocabulary so the wait-for-status-flip handler shares
    a response shape across providers.
    """
    returncode, stdout, stderr = run_glab(['mr', 'view', str(pr_number), '--output', 'json'])
    if returncode != 0:
        return False, {
            'error': f'Failed to get MR {pr_number}',
            'context': stderr.strip(),
        }
    try:
        data = json.loads(stdout)
        pipeline = data.get('pipeline') or {}
        pipeline_status = pipeline.get('status')
    except json.JSONDecodeError:
        return False, {'error': 'Failed to parse glab output', 'context': stdout[:100]}

    if not pipeline or not pipeline_status:
        return True, 'none'

    # Map the pipeline-level status to the canonical four-valued vocabulary
    # via the same partition the per-job classifier uses. This keeps the
    # provider-independent envelope shape consistent across cmd_ci_status,
    # cmd_ci_wait, and _fetch_pr_overall_ci_status.
    synthetic_job = {'status': pipeline_status}
    failing, wait, non_failing = _classify_check_buckets([synthetic_job])
    if wait:
        overall = 'pending'
    elif failing:
        overall = 'failure'
    elif non_failing:
        overall = 'success'
    else:
        overall = 'pending'
    return True, overall


def cmd_ci_wait_for_status_flip(args: argparse.Namespace) -> dict:
    """Handle 'ci wait-for-status-flip' — poll until MR pipeline status flips from pending or timeout.

    GitLab counterpart to the GitHub handler. Preserves the CLI key
    ``pr_number`` (the flag remains ``--pr-number``) for cross-provider
    consistency, even though GitLab calls these merge requests.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_wait_for_status_flip', err)

    ok, initial = _fetch_pr_overall_ci_status(args.pr_number)
    if not ok:
        return make_error(
            'ci_wait_for_status_flip',
            initial.get('error', f'Initial CI status fetch failed for MR {args.pr_number}'),
            initial.get('context', ''),
        )
    baseline = initial

    def check_fn() -> tuple[bool, dict]:
        inner_ok, data = _fetch_pr_overall_ci_status(args.pr_number)
        if not inner_ok:
            return False, data
        return True, {'status': data}

    def is_complete_fn(data: dict) -> bool:
        fresh = data.get('status')
        if fresh == baseline or fresh == 'pending':
            return False
        if args.expected != 'any' and fresh != args.expected:
            return False
        return True

    result = poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error(
            'ci_wait_for_status_flip',
            result['error'],
            result.get('last_data', {}).get('context', ''),
        )

    final_status = result['last_data'].get('status', baseline)
    return {
        'status': 'success',
        'operation': 'ci_wait_for_status_flip',
        'pr_number': args.pr_number,
        'timed_out': result['timed_out'],
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'baseline_status': baseline,
        'final_status': final_status,
    }


def cmd_ci_logs(args: argparse.Namespace) -> dict:
    """Handle 'ci logs' subcommand - get job logs."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('ci_logs', err)

    # Use subprocess.run directly for longer timeout (120s). Honour the
    # router's process-global default cwd so ci logs are fetched against
    # the worktree configured via --project-dir, not the Python cwd.
    cmd = ['glab', 'ci', 'trace', str(args.run_id)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=get_default_cwd(),
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

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_ISSUE_CREATE, getattr(args, 'slot', None))
    if err_dict:
        return make_error('issue_create', err_dict.get('message', 'body not prepared'))

    # Build command
    glab_args = ['issue', 'create', '--title', args.title, '--description', body]
    if args.labels:
        glab_args.extend(['--label', args.labels])

    # Execute
    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('issue_create', 'Failed to create issue', stderr.strip())

    delete_consumed_body(args.plan_id, BODY_KIND_ISSUE_CREATE, getattr(args, 'slot', None))

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


def cmd_issue_comment(args: argparse.Namespace) -> dict:
    """Handle 'issue comment' subcommand - post a note on an existing issue."""
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('issue_comment', err)

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_ISSUE_COMMENT, getattr(args, 'slot', None))
    if err_dict or body is None:
        return make_error('issue_comment', (err_dict or {}).get('message', 'body not prepared'))

    issue_id = normalize_issue_ref(args.issue)
    glab_args = ['issue', 'note', issue_id, '--message', body]
    returncode, stdout, stderr = run_glab(glab_args)
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
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('issue_view', err)

    # Get issue details
    issue_id = normalize_issue_ref(args.issue)
    returncode, stdout, stderr = run_glab(['issue', 'view', issue_id, '--output', 'json'])
    if returncode != 0:
        return make_error('issue_view', f'Failed to view issue {issue_id}', stderr.strip())

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
    """Handle 'pr merge' subcommand - merge a merge request.

    When ``--delete-branch`` is requested, the merge is performed WITHOUT
    passing a branch-delete flag to ``glab mr merge``; instead, after a
    successful merge, the MR's source branch is deleted remotely via the
    ``cmd_branch_delete`` handler (REST
    ``DELETE /projects/{id}/repository/branches/{branch}``). Local git state is
    never touched by this handler — callers who want a local branch gone must
    invoke ``git -C {path} branch -D`` separately.

    On branch-delete failure after a successful merge, a compound result is
    returned with ``merged: true`` and ``branch_delete_error`` populated. The
    merge is NOT retried.
    """
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

    returncode, stdout, stderr = run_glab(glab_args)
    if returncode != 0:
        return make_error('pr_merge', f'Failed to merge MR {iid}', stderr.strip())

    result: dict = {
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number if args.pr_number else iid,
        'strategy': args.strategy,
    }

    # Branch-delete is an optional follow-up. The merge has already succeeded;
    # we never retry the merge on branch-delete failure.
    if args.delete_branch:
        result['merged'] = True

        # Resolve the MR source branch name via existing MR metadata.
        # ``glab mr view`` accepts either an MR IID or a branch name as the
        # positional, so ``iid`` (already resolved) is passed through directly.
        mr_view = view_pr_data(head=iid)
        if mr_view.get('status') != 'success':
            result['branch_delete_error'] = (
                f'Merge succeeded but could not resolve source branch for delete: '
                f'{mr_view.get("error", "pr_view failed")}'
            )
            return result

        source_branch = mr_view.get('head_branch') or ''
        if not source_branch:
            result['branch_delete_error'] = 'Merge succeeded but pr_view returned empty source_branch'
            return result

        # Invoke the branch_delete handler with a synthesized argparse.Namespace.
        delete_args = argparse.Namespace(branch=source_branch)
        delete_result = cmd_branch_delete(delete_args)
        if delete_result.get('status') != 'success':
            result['branch_delete_error'] = delete_result.get(
                'error', f'Failed to delete remote branch {source_branch}'
            )
            return result

        result['branch_deleted'] = source_branch
        result['already_gone'] = delete_result.get('already_gone', False)

    return result


def cmd_branch_delete(args: argparse.Namespace) -> dict:
    """Handle 'branch delete' subcommand - delete a remote branch via REST API.

    Uses the GitLab REST API endpoint ``DELETE /projects/{id}/repository/branches/{branch}``
    invoked through ``glab api``. The project is identified by its URL-encoded
    namespaced path (e.g. ``group%2Frepo``) which GitLab accepts as ``{id}``.
    The ``--remote-only`` flag is required and explicit: local branch management
    is out of scope and handled via ``git -C {path} branch``.

    HTTP semantics:
      - 204 No Content  → ``status: success`` (normal delete)
      - 404 Not Found   → ``status: success`` with ``already_gone: true``
        (branch does not exist remotely; deletion is idempotent).
      - 422 Unprocessable Entity → ``status: success`` with ``already_gone: true``
        (symmetric with the GitHub provider for consistent caller semantics).
      - Anything else   → ``status: error``
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('branch_delete', err)

    project_path = get_project_path()
    if not project_path:
        return make_error('branch_delete', 'Failed to resolve project path from current cwd')

    project_id = quote(project_path, safe='')
    branch_encoded = quote(args.branch, safe='')
    endpoint = f'projects/{project_id}/repository/branches/{branch_encoded}'
    returncode, _stdout, stderr = run_glab(['api', '-X', 'DELETE', endpoint])
    if returncode != 0:
        stderr_text = stderr.strip()
        # glab api surfaces the HTTP status in stderr as "HTTP 404" / "HTTP 422".
        # Treat those as success (already gone) — deletion is idempotent by design.
        if 'HTTP 404' in stderr_text or 'HTTP 422' in stderr_text:
            return {
                'status': 'success',
                'operation': 'branch_delete',
                'branch': args.branch,
                'remote_only': True,
                'already_gone': True,
            }
        return make_error(
            'branch_delete',
            f'Failed to delete remote branch {args.branch}',
            stderr_text,
        )

    return {
        'status': 'success',
        'operation': 'branch_delete',
        'branch': args.branch,
        'remote_only': True,
        'already_gone': False,
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


# GitLab ``merge_status`` values for which a merge will succeed. ``can_be_merged``
# is the ready state; ``cannot_be_merged`` / ``cannot_be_merged_recheck`` /
# ``unchecked`` / ``checking`` are NOT ready and keep the readiness poll running.
_SAFE_MERGE_READY_STATES = frozenset({'can_be_merged'})


def _safe_merge_delegate_ns(args: argparse.Namespace) -> argparse.Namespace:
    """Synthesize the argparse.Namespace cmd_pr_merge expects from safe-merge args.

    cmd_pr_merge reads ``pr_number``, ``head``, ``strategy``, and
    ``delete_branch`` and re-resolves the MR IID itself, so only those four
    fields are forwarded.
    """
    return argparse.Namespace(
        pr_number=args.pr_number,
        head=args.head,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
    )


def cmd_pr_safe_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr safe-merge' subcommand - poll readiness then merge (poll-only).

    GitLab implements **Layer 1 only**: poll the MR's ``merge_status`` until it
    reaches ``can_be_merged``, then delegate the actual merge (including the
    ``--delete-branch`` REST follow-up) to :func:`cmd_pr_merge`.

    There is no admin-merge equivalent on GitLab, so ``--admin-merge-on-stuck-state``
    is accepted for cross-provider API uniformity but has NO effect here. When
    readiness stays unready past the poll timeout, the handler returns a
    canonical error rather than force-merging — the GitHub-only Layer 2 admin
    fallback does not exist on GitLab.

    Returns canonical TOON with ``operation: pr_safe_merge``,
    ``merge_path: polled_clean``, ``polls``, and ``duration_sec``.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('pr_safe_merge', err)

    iid, err_dict = _resolve_mr_iid(args, 'pr_safe_merge')
    if err_dict:
        return err_dict
    assert iid is not None  # noqa: S101 — narrowing after err_dict guard

    # Layer 1 — poll readiness via the shared poll_until helper.
    def check_fn() -> tuple[bool, dict]:
        data = view_pr_data(head=iid)
        if data.get('status') != 'success':
            return False, {'error': data.get('error', 'pr_view failed')}
        return True, data

    def is_ready(data: dict) -> bool:
        return data.get('merge_state') in _SAFE_MERGE_READY_STATES

    poll_result = poll_until(
        check_fn,
        is_ready,
        timeout=args.poll_timeout,
        interval=args.poll_interval,
    )

    polls = poll_result.get('polls', 0)
    duration_sec = poll_result.get('duration_sec', 0)

    # A check_fn failure (MR not found / auth) is propagated immediately.
    if poll_result.get('error'):
        return make_error('pr_safe_merge', f'Readiness poll failed for MR {iid}', poll_result['error'])

    if not poll_result.get('timed_out'):
        # Readiness reached — delegate to the normal merge path.
        merge_result = cmd_pr_merge(_safe_merge_delegate_ns(args))
        if merge_result.get('status') != 'success':
            # Normalize the delegated failure to this verb's operation so the
            # safe-merge response contract holds for downstream consumers.
            return make_error(
                'pr_safe_merge',
                merge_result.get('error', f'Failed to merge MR {iid}'),
                merge_result.get('context', ''),
            )
        merge_result['operation'] = 'pr_safe_merge'
        merge_result['merge_path'] = 'polled_clean'
        merge_result['polls'] = polls
        merge_result['duration_sec'] = duration_sec
        # Prefer the integer MR IID resolved during polling over the branch
        # name cmd_pr_merge echoes back when --head was used.
        merge_result['pr_number'] = (poll_result.get('last_data') or {}).get('pr_number') or merge_result.get('pr_number')
        return merge_result

    # Timed out while not ready. GitLab has no admin fallback — the
    # --admin-merge-on-stuck-state knob is accepted for API uniformity but never
    # force-merges here.
    last_state = (poll_result.get('last_data') or {}).get('merge_state', 'unknown')
    return make_error(
        'pr_safe_merge',
        f'MR {iid} not mergeable after poll timeout (merge_status={last_state}); '
        'GitLab has no admin fallback for a stuck merge state',
    )


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
    """Handle 'pr edit' subcommand - edit MR title and/or description.

    Body is consumed from the prepared scratch file for ``BODY_KIND_PR_EDIT``;
    callers who want to update only the title can skip preparing a body.
    """
    body, err_dict = read_and_consume_body(
        args.plan_id,
        BODY_KIND_PR_EDIT,
        getattr(args, 'slot', None),
        required=False,
    )
    if err_dict:
        return make_error('pr_edit', err_dict.get('message', 'body not prepared'))

    if not args.title and not body:
        return make_error(
            'pr_edit',
            'At least one of --title or a prepared body must be provided',
        )

    glab_args = ['mr', 'update', str(args.pr_number)]
    if args.title:
        glab_args.extend(['--title', args.title])
    if body:
        glab_args.extend(['--description', body])

    result: dict = make_pr_number_handler('pr_edit', lambda a: glab_args, run_glab, check_auth)(args)
    if body and result.get('status') == 'success':
        delete_consumed_body(args.plan_id, BODY_KIND_PR_EDIT, getattr(args, 'slot', None))
    return result


def _cmd_pr_prepare_body(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for an MR body (create or edit)."""
    kind = BODY_KIND_PR_EDIT if getattr(args, 'prepare_for', 'create') == 'edit' else BODY_KIND_PR_CREATE
    return prepare_body(args.plan_id, kind, getattr(args, 'slot', None))


def _cmd_pr_prepare_comment(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for an MR comment (reply or thread-reply)."""
    kind = BODY_KIND_PR_THREAD_REPLY if getattr(args, 'prepare_for', 'reply') == 'thread-reply' else BODY_KIND_PR_REPLY
    return prepare_body(args.plan_id, kind, getattr(args, 'slot', None))


def _cmd_issue_prepare_body(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for an issue description."""
    return prepare_body(args.plan_id, BODY_KIND_ISSUE_CREATE, getattr(args, 'slot', None))


def _cmd_issue_prepare_comment(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for an issue comment."""
    return prepare_body(args.plan_id, BODY_KIND_ISSUE_COMMENT, getattr(args, 'slot', None))


cmd_issue_close = make_simple_handler(
    'issue_close',
    lambda args: ['issue', 'close', normalize_issue_ref(args.issue)],
    run_glab,
    check_auth,
    result_extras=lambda args: {'issue_number': normalize_issue_ref(args.issue)},
)


def _fetch_issue_state_and_labels(issue_number: int) -> tuple[bool, Any]:
    """Fetch issue state and labels for polling handlers.

    Normalises GitLab's ``opened`` state to ``open`` to match the GitHub
    handler shape. Labels are returned verbatim (GitLab exposes them as a
    direct string array).
    """
    returncode, stdout, stderr = run_glab(['issue', 'view', str(issue_number), '--output', 'json'])
    if returncode != 0:
        return False, {
            'error': f'Failed to view issue {issue_number}',
            'context': stderr.strip(),
        }
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return False, {'error': 'Failed to parse glab output', 'context': stdout[:100]}

    state = str(data.get('state', 'unknown')).lower()
    if state == 'opened':
        state = 'open'
    labels = list(data.get('labels') or [])
    return True, {'state': state, 'labels': labels}


def cmd_issue_wait_for_close(args: argparse.Namespace) -> dict:
    """Handle 'issue wait-for-close' — poll until the issue transitions to closed or timeout.

    GitLab counterpart to the GitHub handler. Normalises GitLab's ``opened``
    state to ``open`` so the baseline/final values are consistent across
    providers.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('issue_wait_for_close', err)

    ok, initial = _fetch_issue_state_and_labels(args.issue_number)
    if not ok:
        return make_error(
            'issue_wait_for_close',
            initial.get('error', f'Initial state fetch failed for issue {args.issue_number}'),
            initial.get('context', ''),
        )
    baseline_state = initial['state']

    def check_fn() -> tuple[bool, dict]:
        inner_ok, data = _fetch_issue_state_and_labels(args.issue_number)
        if not inner_ok:
            return False, data
        return True, {'state': data['state']}

    def is_complete_fn(data: dict) -> bool:
        return data.get('state') != 'open'

    result = poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

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

    GitLab counterpart to the GitHub handler. Same response shape and
    completion semantics as GitHub: wait for the label to appear (``present``
    mode) or disappear (``absent`` mode) relative to the baseline.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('issue_wait_for_label', err)

    ok, initial = _fetch_issue_state_and_labels(args.issue_number)
    if not ok:
        return make_error(
            'issue_wait_for_label',
            initial.get('error', f'Initial label fetch failed for issue {args.issue_number}'),
            initial.get('context', ''),
        )
    baseline_present = args.label in initial['labels']

    def check_fn() -> tuple[bool, dict]:
        inner_ok, data = _fetch_issue_state_and_labels(args.issue_number)
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

    result = poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    # Consume top-level --plan-id / --project-dir before argparse runs so
    # the downstream provider parser never sees the router flags. Two-state
    # contract: --plan-id auto-resolves via manage-status; --project-dir is
    # the explicit override; both together is a hard error. Resolved cwd
    # is installed as the process-global default for run_cli's glab calls.
    # Capture the router-level --plan-id (consumed by extract_routing_args for
    # cwd resolution but not returned) so the failure-path log-download hook can
    # locate the plan-scoped artifact tree. The checks subcommands declare no
    # subcommand-level --plan-id, so the first occurrence in the original argv
    # is unambiguously the router-level flag.
    router_plan_id = _capture_router_plan_id(sys.argv[1:])

    project_dir, remaining = extract_routing_args(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser, pr_sub, checks_sub, issue_sub, branch_sub = build_parser('GitLab operations via glab CLI')

    # GitLab-specific parser additions
    add_pr_create_args(pr_sub)

    # GitLab: --pr-number on resolve-thread is required
    add_pr_resolve_thread_pr_number(pr_sub)

    args = parse_args_with_toon_errors(parser)
    # Surface the router plan_id on args so the checks handlers can pass it to
    # enrich_failing_checks_with_logs without re-parsing argv.
    args.router_plan_id = router_plan_id

    handlers: HandlerMap = {
        ('pr', 'prepare-body'): _cmd_pr_prepare_body,
        ('pr', 'prepare-comment'): _cmd_pr_prepare_comment,
        ('issue', 'prepare-body'): _cmd_issue_prepare_body,
        ('issue', 'prepare-comment'): _cmd_issue_prepare_comment,
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
        ('pr', 'safe-merge'): cmd_pr_safe_merge,
        ('pr', 'merge-queue'): cmd_pr_merge_queue,
        ('pr', 'close'): cmd_pr_close,
        ('pr', 'ready'): cmd_pr_ready,
        ('pr', 'edit'): cmd_pr_edit,
        ('checks', 'status'): cmd_ci_status,
        ('checks', 'wait'): cmd_ci_wait,
        ('checks', 'wait-for-status-flip'): cmd_ci_wait_for_status_flip,
        ('checks', 'rerun'): cmd_ci_rerun,
        ('checks', 'logs'): cmd_ci_logs,
        ('issue', 'create'): cmd_issue_create,
        ('issue', 'comment'): cmd_issue_comment,
        ('issue', 'view'): cmd_issue_view,
        ('issue', 'close'): cmd_issue_close,
        ('issue', 'wait-for-close'): cmd_issue_wait_for_close,
        ('issue', 'wait-for-label'): cmd_issue_wait_for_label,
        ('branch', 'delete'): cmd_branch_delete,
        ('repo', 'merge-queue', 'probe'): cmd_repo_merge_queue_probe,
        ('repo', 'merge-queue', 'enable'): cmd_repo_merge_queue_enable,
        ('repo', 'label', 'ensure'): cmd_repo_label_ensure,
    }

    # branch_sub is registered by ci_base.build_parser; acknowledge the returned
    # handle so static analysis does not flag it as unused.
    _ = branch_sub

    result = dispatch(args, handlers, parser)
    print(serialize_toon(result, table_separator='\t'))
    return 0


if __name__ == '__main__':
    safe_main(main)()
