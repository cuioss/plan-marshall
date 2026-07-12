#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
    pr update-branch  Update PR branch with base branch changes
    pr close        Close a pull request
    pr ready        Mark a draft PR as ready for review
    pr edit         Edit PR title and/or body
    ci status       Check CI status for a PR
    ci wait         Wait for CI to complete
    ci rerun        Rerun a workflow run
    ci logs         Get failed run logs
    issue create    Create an issue
    issue comment   Post a comment on an existing issue
    issue view      View issue details
    issue close     Close an issue

Usage (bodies supplied via path-allocate pattern: prepare-body → write file → consume):
    python3 github.py pr prepare-body --plan-id EXAMPLE-PLAN [--for create|edit] [--slot name]
    python3 github.py pr prepare-comment --plan-id EXAMPLE-PLAN [--for reply|thread-reply] [--slot name]
    python3 github.py issue prepare-body --plan-id EXAMPLE-PLAN [--slot name]
    python3 github.py issue prepare-comment --plan-id EXAMPLE-PLAN [--slot name]
    python3 github.py pr create --title "Title" --plan-id EXAMPLE-PLAN [--base main] [--draft]
    python3 github.py pr view
    python3 github.py pr list [--head feature/branch] [--state open|closed|all]
    python3 github.py pr reviews --pr-number 123
    python3 github.py pr comments --pr-number 123 [--unresolved-only]
    python3 github.py pr reply --pr-number 123 --plan-id EXAMPLE-PLAN
    python3 github.py pr resolve-thread --thread-id PRRT_abc123
    python3 github.py pr thread-reply --pr-number 123 --thread-id PRRT_abc123 --plan-id EXAMPLE-PLAN
    python3 github.py pr submit-review --review-id PRR_abc123 [--event COMMENT|APPROVE|REQUEST_CHANGES]
    python3 github.py pr merge --pr-number 123 [--strategy squash] [--delete-branch]
    python3 github.py pr auto-merge --pr-number 123 [--strategy squash]
    python3 github.py pr update-branch --pr-number 123
    python3 github.py pr close --pr-number 123
    python3 github.py pr ready --pr-number 123
    python3 github.py pr edit --pr-number 123 --plan-id EXAMPLE-PLAN [--title "New Title"]
    python3 github.py ci status --pr-number 123
    python3 github.py ci wait --pr-number 123 [--timeout 300] [--interval 30]
    python3 github.py ci rerun --run-id 12345
    python3 github.py ci logs --run-id 12345
    python3 github.py issue create --title "Title" --plan-id EXAMPLE-PLAN [--labels "bug,priority:high"]
    python3 github.py issue comment --issue 123 --plan-id EXAMPLE-PLAN [--slot name]
    python3 github.py issue view --issue 123
    python3 github.py issue close --issue 123

Output: TOON format

Module layout: this entry file defines the gh/GraphQL primitives and the
monkeypatch-sensitive data helpers (``run_gh``, ``run_graphql``, ``check_auth``,
``get_repo_info``, ``view_pr_data``, ``fetch_pr_comments_data``,
``format_checks_toon``, ``_fetch_pr_overall_ci_status``,
``_fetch_issue_state_and_labels``, ``_fetch_failed_run_log``,
``_safe_merge_stuck_state_gate``/``_safe_merge_behind_by_zero``), plus the
shared ``_resolve_pr_identifier`` and the ``main`` dispatch. The ``cmd_*``
handler bodies live in the co-located ``_github_pr`` / ``_github_ci`` /
``_github_issue`` submodules and are imported back at the bottom of this file
for the dispatch table. Those submodules reach every primitive above via
``github_ops.<name>`` attribute access at call time, so a test's
``monkeypatch.setattr(github_ops, '<name>', ...)`` is seen by the handlers
unchanged.
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any
from urllib.parse import quote

from _github_checks import (  # noqa: F401 — re-exported for callers and tests
    _BUCKET_TO_CONCLUSION,
    _CONCLUSION_FAILING,
    _CONCLUSION_NON_FAILING,
    _CONCLUSION_WAIT,
    _build_failing_check_entry,
    _classify_check_buckets,
    _derive_overall_status,
    _extract_job_id_from_link,
    _extract_run_id_from_link,
    _extract_segment_from_link,
    _normalize_conclusion,
)
from ci_base import (
    MAX_ELAPSED_SECONDS,
    MERGE_QUEUE_ELIGIBLE_CONFIGURED,
    MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
    MERGE_QUEUE_INELIGIBLE,
    MERGE_QUEUE_UNSUPPORTED,
    add_pr_create_args,
    build_parser,
    check_auth_cli,
    compute_elapsed,
    compute_total_elapsed,
    dispatch,
    extract_routing_args,
    make_error,
    parse_args_with_toon_errors,
    poll_until,  # noqa: F401 — re-exported as a patchable primitive for submodule handlers
    run_cli,
    safe_main,
    serialize_toon,
    set_default_cwd,
)

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
# Shared PR-identifier resolution
# ---------------------------------------------------------------------------


def _resolve_pr_identifier(args: argparse.Namespace, operation: str) -> tuple[str | None, dict | None]:
    """Resolve a PR identifier from --pr-number or --head.

    Returns ``(identifier, None)`` on success where ``identifier`` is the gh-acceptable
    positional (PR number or branch name), or ``(None, error_dict)`` on validation failure.

    gh accepts either a PR number or a branch name as the positional for ``pr view``,
    ``pr merge``, ``pr checks``, etc., so the abstraction simply substitutes the branch
    when ``--head`` is supplied.
    """
    pr_number = getattr(args, 'pr_number', None)
    head = getattr(args, 'head', None)
    if pr_number and head:
        return None, make_error(operation, 'specify exactly one of --pr-number or --head, not both')
    if pr_number:
        return str(pr_number), None
    if head:
        return head, None
    return None, make_error(operation, 'specify either --pr-number or --head')


def view_pr_data(head: str | None = None) -> dict:
    """Fetch PR data for current branch (or the supplied ``head`` branch).

    Returns dict with 'status' key ('success' or 'error').
    Importable by other scripts for direct data access without subprocess.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return {'status': 'error', 'operation': 'pr_view', 'error': err}

    pr_view_args = ['pr', 'view']
    if head:
        pr_view_args.append(head)
    pr_view_args.extend(
        [
            '--json',
            'number,url,state,title,headRefName,baseRefName,isDraft,mergeable,mergeStateStatus,reviewDecision',
        ]
    )
    returncode, stdout, stderr = run_gh(pr_view_args)
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


# ---------------------------------------------------------------------------
# Safe-merge stuck-state gate (GitHub-only ruleset verification)
# ---------------------------------------------------------------------------


def _safe_merge_stuck_state_gate(identifier: str) -> tuple[bool, str | None]:
    """Verify every active ruleset requirement is provably met for a stuck PR.

    Issues a richer ``gh pr view`` query than :func:`view_pr_data` to confirm
    the PR is admin-mergeable for the right reason — i.e. the ``blocked`` state
    is GitHub's post-force-push staleness, not a genuinely-unmet requirement.

    Returns ``(True, None)`` when every requirement is provably met, or
    ``(False, reason)`` naming the first unmet requirement otherwise. The gate
    fails closed: any query/parse failure returns ``(False, reason)``.
    """
    returncode, stdout, stderr = run_gh(
        [
            'pr',
            'view',
            identifier,
            '--json',
            'statusCheckRollup,reviewDecision,mergeable,mergeStateStatus,headRefOid',
        ]
    )
    if returncode != 0:
        return False, f'stuck-state gate query failed: {stderr.strip()}'

    # Fail closed on any structural anomaly in the gate-query payload: an admin
    # merge is authorized only when every requirement is *provably* met, so a
    # malformed or unexpectedly-shaped response must refuse, never raise an
    # untyped exception that could bypass the gate.
    try:
        data = json.loads(stdout)
        if not isinstance(data, dict):
            return False, 'stuck-state gate query returned non-dictionary JSON'

        # Required approving reviews satisfied. A null/empty ``reviewDecision``
        # means the ruleset does not require review approval (the requirement is
        # vacuously met); an explicit non-approved value (REVIEW_REQUIRED /
        # CHANGES_REQUESTED) is a real unmet requirement that refuses the gate.
        review_decision = (data.get('reviewDecision') or '').lower()
        if review_decision and review_decision != 'approved':
            return False, f'review decision is {review_decision!r}, not approved'

        # Required status checks all SUCCESS on the head SHA. ``statusCheckRollup``
        # is the per-head-SHA rollup, so a non-SUCCESS conclusion here is a real
        # unmet requirement, not staleness.
        rollup = data.get('statusCheckRollup') or []
        if not isinstance(rollup, list):
            return False, 'statusCheckRollup is not a list'
        for check in rollup:
            if not isinstance(check, dict):
                return False, 'statusCheckRollup contains a non-dictionary check entry'
            conclusion = (check.get('conclusion') or check.get('state') or '').upper()
            # gh reports completed checks via ``conclusion`` (SUCCESS / NEUTRAL /
            # SKIPPED are non-failing) and in-progress checks via empty conclusion.
            if conclusion and conclusion not in ('SUCCESS', 'NEUTRAL', 'SKIPPED'):
                name = check.get('name') or check.get('context') or 'unknown'
                return False, f'required check {name!r} concluded {conclusion}'
            if not conclusion:
                name = check.get('name') or check.get('context') or 'unknown'
                return False, f'required check {name!r} has not concluded'

        # Branch not behind base — the head must already contain the base tip,
        # otherwise the ``blocked`` state reflects a real out-of-date branch.
        head_oid = data.get('headRefOid')
    except (TypeError, ValueError, AttributeError) as exc:
        return False, f'stuck-state gate query response could not be parsed: {exc}'

    if not head_oid:
        return False, 'could not resolve head SHA for behind-by check'
    behind_ok, behind_reason = _safe_merge_behind_by_zero(identifier, head_oid)
    if not behind_ok:
        return False, behind_reason

    return True, None


def _safe_merge_behind_by_zero(identifier: str, head_oid: str) -> tuple[bool, str | None]:
    """Confirm the PR head is not behind its base branch (``behind_by == 0``).

    Resolves the base branch via ``gh pr view`` then queries the REST compare
    endpoint (``GET /repos/{owner}/{repo}/compare/{base}...{head_oid}``) whose
    ``behind_by`` field is the authoritative behind-count. Fails closed.
    """
    pr_view = view_pr_data(head=identifier)
    if pr_view.get('status') != 'success':
        return False, f'could not resolve base branch for behind-by check: {pr_view.get("error", "pr_view failed")}'
    base_branch = pr_view.get('base_branch') or ''
    if not base_branch:
        return False, 'pr_view returned empty base branch for behind-by check'

    owner, repo = get_repo_info()
    if not owner or not repo:
        return False, 'could not resolve repository owner/name for behind-by check'

    base_encoded = quote(base_branch, safe='')
    endpoint = f'repos/{owner}/{repo}/compare/{base_encoded}...{head_oid}'
    returncode, stdout, stderr = run_gh(['api', endpoint])
    if returncode != 0:
        return False, f'behind-by compare query failed: {stderr.strip()}'
    try:
        compare_data = json.loads(stdout)
        if not isinstance(compare_data, dict):
            return False, 'behind-by compare query returned non-dictionary JSON'
        behind_by = compare_data.get('behind_by')
    except (TypeError, ValueError, AttributeError) as exc:
        return False, f'behind-by compare query response could not be parsed: {exc}'

    if behind_by is None:
        return False, 'compare response missing behind_by'
    if behind_by != 0:
        return False, f'branch is behind base by {behind_by} commit(s)'
    return True, None


# ---------------------------------------------------------------------------
# CI check-table formatting (depends on the patchable compute_total_elapsed)
# ---------------------------------------------------------------------------


def format_checks_toon(
    checks: list[dict],
    *,
    duration_ceiling: int | None = None,
) -> tuple[list[dict], int]:
    """Format checks into dicts and compute overall elapsed.

    Per-check rows omit the ``elapsed_sec`` key entirely when
    :func:`compute_elapsed` returns ``None`` (Go zero-value timestamp or
    parse failure) — TOON callers treat absent keys as null-equivalent.

    The aggregate ``elapsed_sec`` is clamped via warn-and-substitute when it
    falls outside ``0 ≤ x ≤ 24*3600``: a stderr warning is emitted and the
    return value is replaced with ``duration_ceiling`` (caller-supplied for
    ``ci_wait``) or ``0`` (default for ``ci_status``).

    Returns ``(check_dicts, elapsed_sec_total)``.
    """
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    check_dicts: list[dict] = []
    started_at_values: list[str | None] = []

    for check in checks:
        started_at = check.get('startedAt')
        started_at_values.append(started_at)

        elapsed = compute_elapsed(started_at, check.get('completedAt'), now)
        row: dict = {
            'name': check.get('name', 'unknown'),
            'status': check.get('state', 'unknown'),
            'result': check.get('bucket') or '-',
            'url': check.get('link') or '-',
            'workflow': check.get('workflow') or '-',
        }
        if elapsed is not None:
            row['elapsed_sec'] = elapsed
        check_dicts.append(row)

    total_elapsed = compute_total_elapsed(started_at_values, now)

    # Defense-in-depth: clamp aggregate to a sane window. The per-check filter
    # above should already prevent zero-time leakage, but a runaway value here
    # would mask a regression — substitute the caller's ceiling and warn.
    if total_elapsed < 0 or total_elapsed > MAX_ELAPSED_SECONDS:
        print(
            'format_checks_toon: aggregate elapsed_sec out of range, clamping',
            file=sys.stderr,
        )
        total_elapsed = duration_ceiling if duration_ceiling is not None else 0

    return check_dicts, total_elapsed


# ---------------------------------------------------------------------------
# CI / issue polling primitives (monkeypatch-sensitive fetchers)
# ---------------------------------------------------------------------------


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


def _fetch_failed_run_log(run_id: str, job_id: str = '') -> str | None:
    """Download the raw failed-job log for a run via ``gh run view --log-failed``.

    When ``job_id`` is non-empty (reusable-workflow caller — the failing check
    is a nested called job, not the caller run), the download targets that job
    via ``gh run view {run_id} --log-failed --job {job_id}`` so the nested job's
    failure log is retrievable; the caller-run form returns empty for such
    checks. When ``job_id`` is empty the run-only form is used.

    Reuses the same CLI invocation as :func:`cmd_ci_logs` but returns the full,
    untruncated stdout (the filter/persist layer applies its own extraction).
    Returns ``None`` on any non-zero exit so the enrich hook degrades that entry
    gracefully without aborting siblings.
    """
    gh_args = ['run', 'view', str(run_id), '--log-failed']
    if job_id:
        gh_args.extend(['--job', str(job_id)])
    returncode, stdout, _stderr = run_gh(gh_args, timeout=120)
    if returncode != 0:
        return None
    return stdout


def _fetch_pr_overall_ci_status(pr_number: int) -> tuple[bool, Any]:
    """Fetch the overall CI status for a PR's head commit.

    Returns ``(True, status)`` on success where status is one of
    ``pending|success|failure|none``. On failure returns
    ``(False, {'error': ..., 'context': ...})`` so callers can propagate the
    error dict through ``poll_until`` in the same shape used by ``cmd_ci_wait``.
    """
    returncode, stdout, stderr = run_gh(
        ['pr', 'checks', str(pr_number), '--json', 'name,state,bucket,link,startedAt,completedAt,workflow']
    )
    if returncode != 0:
        return False, {
            'error': f'Failed to get CI status for PR {pr_number}',
            'context': stderr.strip(),
        }
    try:
        checks = json.loads(stdout)
    except json.JSONDecodeError:
        return False, {'error': 'Failed to parse gh output', 'context': stdout[:100]}

    overall, _failing_rows, _wait_rows = _derive_overall_status(checks)

    return True, overall


def _fetch_issue_state_and_labels(issue_number: int) -> tuple[bool, Any]:
    """Fetch issue state and labels for polling handlers.

    Returns ``(True, {'state': 'open'|'closed', 'labels': [str, ...]})`` on
    success, or ``(False, {'error': ..., 'context': ...})`` so callers can
    propagate the error dict through ``poll_until``.
    """
    returncode, stdout, stderr = run_gh(['issue', 'view', str(issue_number), '--json', 'state,labels'])
    if returncode != 0:
        return False, {
            'error': f'Failed to view issue {issue_number}',
            'context': stderr.strip(),
        }
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return False, {'error': 'Failed to parse gh output', 'context': stdout[:100]}

    state = str(data.get('state', 'unknown')).lower()
    labels = [label.get('name', '') for label in data.get('labels', []) if label.get('name')]
    return True, {'state': state, 'labels': labels}


# ---------------------------------------------------------------------------
# Repo-level merge-queue probe / enable (GitHub merge queue via rulesets)
# ---------------------------------------------------------------------------
#
# GitHub's merge queue is configured through a repository ruleset carrying a
# rule of ``type == "merge_queue"`` on the target branch. The probe reads the
# evaluated rule set for the default branch via
# ``GET /repos/{owner}/{repo}/rules/branches/{branch}`` (a single flat call that
# returns every rule applying to the branch) and maps the result to the shared
# eligibility vocabulary. The enable path creates a merge-queue ruleset via
# ``POST /repos/{owner}/{repo}/rulesets`` and is idempotent — an already
# configured repository is left unchanged.

# Actionable remedy surfaced on an auth-scope failure (D4) — never a stack trace.
_MERGE_QUEUE_AUTH_SCOPE_HINT = (
    "the gh token lacks the scope to read/write repository rulesets. Run "
    "'gh auth refresh -s repo,admin:org' (or grant the fine-grained "
    "'Administration' repository write permission), then retry."
)


def _is_auth_scope_error(stderr: str) -> bool:
    """Return True when *stderr* names an auth/permission-scope failure.

    GitHub surfaces scope failures as HTTP 401/403 with a ``must have admin``
    or ``Resource not accessible`` message. Matching on these markers keeps the
    actionable-error path from misfiring on unrelated failures.
    """
    lowered = stderr.lower()
    return (
        'http 403' in lowered
        or 'http 401' in lowered
        or 'must have admin' in lowered
        or 'resource not accessible' in lowered
        or 'requires authentication' in lowered
    )


def _resolve_default_branch(owner: str, repo: str) -> tuple[str | None, str]:
    """Resolve the repository default branch. Returns ``(branch, error)``."""
    returncode, stdout, stderr = run_gh(['api', f'repos/{owner}/{repo}'])
    if returncode != 0:
        return None, stderr.strip()
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None, 'could not parse repository metadata'
    if not isinstance(data, dict):
        return None, 'repository metadata response was not an object'
    branch = data.get('default_branch')
    if not branch:
        return None, 'repository metadata missing default_branch'
    return str(branch), ''


def _probe_merge_queue_state(owner: str, repo: str, branch: str) -> tuple[str, str, str | None]:
    """Probe the merge-queue configuration state for ``branch``.

    Returns ``(discriminator, detail, error)`` where ``discriminator`` is one of
    the ``MERGE_QUEUE_*`` constants. ``error`` is a non-None actionable error
    string (the caller converts it to a ``make_error`` result) on every failure
    that is NOT a confirmed feature-availability verdict — an auth-scope failure,
    a non-404 ``gh api`` error, or an unparseable / malformed rules response.
    Only two verdicts carry ``error=None``: a confirmed HTTP 404 on the rules
    endpoint (mapped to ``ineligible`` — the genuine "this repo does not offer
    the feature" signal) and the two eligible outcomes. A transient HTTP 500 /
    timeout / malformed response therefore surfaces as a real, retryable
    ``unsupported`` error rather than being folded into a permanent ``ineligible``
    refusal.
    """
    endpoint = f'repos/{owner}/{repo}/rules/branches/{branch}'
    returncode, stdout, stderr = run_gh(['api', endpoint])
    if returncode != 0:
        if _is_auth_scope_error(stderr):
            return MERGE_QUEUE_INELIGIBLE, stderr.strip(), _MERGE_QUEUE_AUTH_SCOPE_HINT
        if 'http 404' in stderr.lower():
            return MERGE_QUEUE_INELIGIBLE, 'branch rules endpoint not found', None
        detail = stderr.strip() or 'branch rules probe failed'
        return MERGE_QUEUE_UNSUPPORTED, detail, detail
    try:
        rules = json.loads(stdout)
    except json.JSONDecodeError:
        detail = 'could not parse branch rules response'
        return MERGE_QUEUE_UNSUPPORTED, detail, detail
    if not isinstance(rules, list):
        detail = 'branch rules response was not a list'
        return MERGE_QUEUE_UNSUPPORTED, detail, detail
    for rule in rules:
        if isinstance(rule, dict) and rule.get('type') == 'merge_queue':
            return MERGE_QUEUE_ELIGIBLE_CONFIGURED, 'merge_queue rule active on branch', None
    return MERGE_QUEUE_ELIGIBLE_UNCONFIGURED, 'no merge_queue rule on branch', None


def build_merge_queue_ruleset_payload(branch: str) -> dict:
    """Build the ``POST /rulesets`` request body enabling a merge queue on ``branch``.

    Pure function (no I/O) so the payload contract is unit-testable independent
    of the ``gh`` invocation. Creates an active branch ruleset scoped to the
    single target branch carrying one ``merge_queue`` rule with GitHub's
    documented default parameters.
    """
    return {
        'name': 'plan-marshall-merge-queue',
        'target': 'branch',
        'enforcement': 'active',
        'conditions': {
            'ref_name': {
                'include': [f'refs/heads/{branch}'],
                'exclude': [],
            }
        },
        'rules': [
            {
                'type': 'merge_queue',
                'parameters': {
                    'merge_method': 'MERGE',
                    'max_entries_to_build': 5,
                    'min_entries_to_merge': 1,
                    'max_entries_to_merge': 5,
                    'min_entries_to_merge_wait_minutes': 5,
                    'grouping_strategy': 'ALLGREEN',
                    'check_response_timeout_minutes': 60,
                },
            }
        ],
    }


def _resolve_repo_branch_and_probe(
    operation: str,
) -> tuple[dict | None, str, str, str, str, str]:
    """Resolve repo owner/name + default branch, then probe merge-queue state.

    Shared by ``cmd_repo_merge_queue_probe`` and ``cmd_repo_merge_queue_enable``,
    which differ only in what they do with the resolved discriminator. Returns
    ``(error, owner, repo, branch, discriminator, detail)``: on any failure
    ``error`` is a ready-to-return ``make_error`` dict (remaining fields empty);
    on success ``error`` is ``None``.
    """
    owner, repo = get_repo_info()
    if not owner or not repo:
        error = make_error(operation, 'Could not determine repository owner/name')
        return error, '', '', '', '', ''

    branch, branch_err = _resolve_default_branch(owner, repo)
    if branch is None:
        if _is_auth_scope_error(branch_err):
            error = make_error(operation, _MERGE_QUEUE_AUTH_SCOPE_HINT, branch_err)
        else:
            error = make_error(operation, 'Could not resolve default branch', branch_err)
        return error, '', '', '', '', ''

    discriminator, detail, scope_error = _probe_merge_queue_state(owner, repo, branch)
    if scope_error is not None:
        return make_error(operation, scope_error, detail), '', '', '', '', ''

    return None, owner, repo, branch, discriminator, detail


def cmd_repo_merge_queue_probe(args: argparse.Namespace) -> dict:
    """Handle 'repo merge-queue probe' — report merge-queue eligibility state.

    Returns a success TOON carrying ``eligibility`` (one of the shared
    discriminators) on every reachable path. An auth-scope failure returns the
    actionable error, never a stack trace.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('repo_merge_queue_probe', err)

    error, _owner, _repo, branch, discriminator, detail = _resolve_repo_branch_and_probe(
        'repo_merge_queue_probe'
    )
    if error is not None:
        return error

    return {
        'status': 'success',
        'operation': 'repo_merge_queue_probe',
        'provider': 'github',
        'branch': branch,
        'eligibility': discriminator,
        'detail': detail,
    }


def cmd_repo_merge_queue_enable(args: argparse.Namespace) -> dict:
    """Handle 'repo merge-queue enable' — configure the merge queue (idempotent).

    Probes first: an already-configured repository returns success without any
    mutation; an unconfigured-but-eligible repository gets a merge_queue ruleset
    created; an ineligible repository refuses with the actionable error.
    """
    is_auth, err = check_auth()
    if not is_auth:
        return make_error('repo_merge_queue_enable', err)

    error, owner, repo, branch, discriminator, detail = _resolve_repo_branch_and_probe(
        'repo_merge_queue_enable'
    )
    if error is not None:
        return error

    if discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED:
        # Idempotent no-op — the merge queue is already configured.
        return {
            'status': 'success',
            'operation': 'repo_merge_queue_enable',
            'provider': 'github',
            'branch': branch,
            'eligibility': discriminator,
            'changed': False,
            'detail': 'merge queue already configured; no change made',
        }

    if discriminator == MERGE_QUEUE_ELIGIBLE_UNCONFIGURED:
        payload = build_merge_queue_ruleset_payload(branch)
        # gh api reads a JSON request body from a file via --input; write the
        # payload to a transient file so the nested ruleset structure survives
        # intact (field flags cannot express the nested rules array).
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        )
        try:
            json.dump(payload, tmp)
            tmp.close()
            returncode, _stdout, stderr = run_gh(
                ['api', '-X', 'POST', f'repos/{owner}/{repo}/rulesets', '--input', tmp.name]
            )
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        if returncode != 0:
            if _is_auth_scope_error(stderr):
                return make_error('repo_merge_queue_enable', _MERGE_QUEUE_AUTH_SCOPE_HINT, stderr.strip())
            return make_error('repo_merge_queue_enable', 'Failed to create merge-queue ruleset', stderr.strip())
        return {
            'status': 'success',
            'operation': 'repo_merge_queue_enable',
            'provider': 'github',
            'branch': branch,
            'eligibility': MERGE_QUEUE_ELIGIBLE_CONFIGURED,
            'changed': True,
            'detail': 'merge_queue ruleset created',
        }

    # ineligible / unsupported → refuse with the actionable message.
    return make_error(
        'repo_merge_queue_enable',
        'Merge queue is not available for this repository — GitHub reports the '
        'feature ineligible (an org policy may disallow rulesets, or the token '
        'lacks Administration access). ' + _MERGE_QUEUE_AUTH_SCOPE_HINT,
        detail,
    )


# ---------------------------------------------------------------------------
# Command handlers (bodies live in the co-located domain submodules)
#
# These imports sit at the bottom of the file, after every primitive above is
# defined: each submodule does ``import github_ops`` and only ACCESSES the
# primitives at call time, so importing them here (once this module is
# partially initialized with all primitives present) is load-order safe. The
# names are brought back so the dispatch table and external callers/tests can
# resolve ``github_ops.cmd_*`` / ``github_ops.post_pr_comment`` etc.
#
# When this file is executed directly (``python github_ops.py``) it is loaded
# under the name ``__main__``. The domain submodules below do ``import
# github_ops`` and resolve every primitive via attribute access; alias this
# live module under its real name FIRST so that import returns THIS partially
# initialized module (whose primitives are all defined by now) instead of
# triggering a second, circular load of the file.
# ---------------------------------------------------------------------------

sys.modules.setdefault('github_ops', sys.modules[__name__])

from _github_ci import (  # noqa: E402 — bottom import: primitives must be defined first
    cmd_ci_logs,
    cmd_ci_rerun,
    cmd_ci_status,
    cmd_ci_wait,
    cmd_ci_wait_for_status_flip,
    fetch_pr_head_sha,
)
from _github_issue import (  # noqa: E402 — bottom import: primitives must be defined first
    _cmd_issue_prepare_body,
    _cmd_issue_prepare_comment,
    cmd_issue_close,
    cmd_issue_comment,
    cmd_issue_create,
    cmd_issue_view,
    cmd_issue_wait_for_close,
    cmd_issue_wait_for_label,
)
from _github_pr import (  # noqa: E402 — bottom import: primitives must be defined first
    _cmd_pr_prepare_body,
    _cmd_pr_prepare_comment,
    cmd_branch_delete,
    cmd_pr_auto_merge,
    cmd_pr_close,
    cmd_pr_comments,
    cmd_pr_create,
    cmd_pr_edit,
    cmd_pr_list,
    cmd_pr_merge,
    cmd_pr_merge_queue,
    cmd_pr_ready,
    cmd_pr_reply,
    cmd_pr_resolve_thread,
    cmd_pr_reviews,
    cmd_pr_safe_merge,
    cmd_pr_submit_review,
    cmd_pr_thread_reply,
    cmd_pr_update_branch,
    cmd_pr_view,
    cmd_pr_wait_for_comments,
    cmd_repo_label_ensure,
    fetch_pr_reviews_with_commits,
    post_pr_comment,
)

# fetch_pr_head_sha / fetch_pr_reviews_with_commits / post_pr_comment are
# re-exported for the sibling ``github_pr`` / ``github_re_review`` scripts,
# which import this module and call them as ``github_ops.<name>``.
_ = (fetch_pr_head_sha, fetch_pr_reviews_with_commits, post_pr_comment)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    # Consume top-level --plan-id / --project-dir before argparse runs so the
    # downstream provider parser never sees the router flags. Two-state
    # contract: --plan-id auto-resolves via manage-status; --project-dir is
    # the explicit override; both together is a hard error. Any resolved cwd
    # is installed as the process-global default for run_cli's gh invocations.
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

    parser, pr_sub, checks_sub, issue_sub, branch_sub = build_parser('GitHub operations via gh CLI')

    # GitHub-specific parser additions
    add_pr_create_args(pr_sub)

    # GitHub: --pr-number on resolve-thread is optional (accepted for API uniformity)
    resolve_parser = pr_sub.choices.get('resolve-thread')
    if resolve_parser:
        resolve_parser.add_argument('--pr-number', type=int, help='PR number (accepted for API uniformity)')

    args = parse_args_with_toon_errors(parser)
    # Surface the router plan_id on args so the checks handlers can pass it to
    # enrich_failing_checks_with_logs without re-parsing argv.
    args.router_plan_id = router_plan_id

    handlers = {
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
        ('pr', 'wait-for-comments'): cmd_pr_wait_for_comments,
        ('pr', 'merge'): cmd_pr_merge,
        ('pr', 'auto-merge'): cmd_pr_auto_merge,
        ('pr', 'safe-merge'): cmd_pr_safe_merge,
        ('pr', 'merge-queue'): cmd_pr_merge_queue,
        ('pr', 'update-branch'): cmd_pr_update_branch,
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
