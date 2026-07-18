#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub pull-request command handlers.

Holds the ``cmd_pr_*`` / ``cmd_branch_delete`` handler bodies plus the PR-only
non-patched helpers (identifier resolution, viewer-login lookup, safe-merge
delegate/ready-state helpers) and the GraphQL mutation/query constants they use.

Every network primitive and monkeypatch-sensitive helper (``run_gh``,
``run_graphql``, ``check_auth``, ``get_repo_info``, ``view_pr_data``,
``fetch_pr_comments_data``, ``poll_until``, ``_safe_merge_stuck_state_gate``)
lives in the entry module ``github_ops`` and is reached here via ATTRIBUTE
access on the imported ``github_ops`` module at call time. That indirection is
what lets a test's ``monkeypatch.setattr(github_ops, '<name>', ...)`` reach
these handlers unchanged — never ``from github_ops import <name>``, which would
copy the binding and defeat the patch.
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote

import github_ops
from ci_base import (
    BODY_KIND_PR_CREATE,
    BODY_KIND_PR_EDIT,
    BODY_KIND_PR_REPLY,
    BODY_KIND_PR_THREAD_REPLY,
    MERGE_QUEUE_ELIGIBLE_CONFIGURED,
    delete_consumed_body,
    make_error,
    make_pr_number_handler,
    prepare_body,
    read_and_consume_body,
)

# ---------------------------------------------------------------------------
# CodeRabbit rate-limit status-notice detection (provider-scoped: GitHub/CodeRabbit)
# ---------------------------------------------------------------------------
#
# When CodeRabbit is rate-limited it posts a status-notice comment in place of a
# review. The notice carries a narrow, stable structure — a ``## Rate limit
# exceeded`` heading (typically inside a ``> [!WARNING]`` callout) plus the
# "exceeded the limit for the number of ..." body sentence. Detection is purely
# additive — it surfaces a ``rate_limited`` discriminator on the wait-for-comments
# return and never changes the poll behaviour or any existing field. Detection
# requires BOTH markers (``all``): the ``## Rate limit exceeded`` heading marker
# AND the specific body sentence must be present. Requiring both narrows detection
# to the notice's actual two-part structure, so an ordinary CodeRabbit review
# comment that merely mentions "rate limit exceeded" in prose — or that merely
# discusses "exceeded the limit for the number of ..." parameters/lines — is not
# misclassified as a status notice.
_CODERABBIT_BOT_LOGINS = frozenset({'coderabbitai', 'coderabbitai[bot]'})
_CODERABBIT_RATE_LIMIT_MARKERS: tuple[re.Pattern[str], ...] = (
    # The notice's own heading: ``## Rate limit exceeded``. Matched by its
    # markdown ``#`` heading markers rather than a bare phrase, so a prose
    # mention of "rate limit exceeded" in a genuine review body does not match.
    #
    # Deliberately NO ``^``/``re.MULTILINE`` line-start anchor:
    # ``fetch_pr_comments_data`` (in github_ops.py) flattens every comment body's
    # newlines to spaces BEFORE this detector runs, collapsing the notice to a
    # single line. A line-start anchor could therefore only ever match at offset
    # 0 — never at the ``## Rate limit exceeded`` heading, which sits mid-body
    # after the ``> [!WARNING]`` callout prefix — so the anchored form never
    # fired in production. The heading markers are searched unanchored instead.
    re.compile(r'#{1,6}\s+rate limit exceeded\b', re.IGNORECASE),
    re.compile(r'exceeded the limit for the number of', re.IGNORECASE),
)


def _is_coderabbit_rate_limit_notice(body: str) -> bool:
    """Return True when a single comment ``body`` is a CodeRabbit rate-limit notice.

    Matches the body against the narrow rate-limit marker set, requiring ALL
    markers (the ``## Rate limit exceeded`` heading marker AND the specific
    "exceeded the limit for the number of ..." body sentence). Requiring both
    narrows detection to the notice's actual two-part structure, so a genuine
    review comment that merely mentions one marker in prose is not misclassified.

    Exported for the ``github_pr.fetch_findings`` pre-filter to drop a
    CodeRabbit-authored rate-limit notice as noise, sharing the one marker set
    with the :func:`_detect_coderabbit_rate_limited` wait-return discriminator.
    """
    return all(marker.search(body) for marker in _CODERABBIT_RATE_LIMIT_MARKERS)


def _detect_coderabbit_rate_limited(comments: list[dict]) -> bool:
    """Return True when the newest CodeRabbit-bot comment is a rate-limit notice.

    Scans the CodeRabbit-bot-authored comments only, picks the newest by
    ``created_at``, and matches its body via :func:`_is_coderabbit_rate_limit_notice`
    (which requires ALL markers — the heading marker AND the body sentence — so a
    genuine review that merely mentions one of them in prose is not
    misclassified). Any absent / malformed field degrades to ``False`` —
    detection is best-effort and never raises into the poll return path.
    """
    bot_comments = [
        c
        for c in comments
        if isinstance(c, dict)
        and str(c.get('author') or '').lower() in _CODERABBIT_BOT_LOGINS
    ]
    if not bot_comments:
        return False
    newest = max(bot_comments, key=lambda c: str(c.get('created_at') or ''))
    body = str(newest.get('body') or '')
    return _is_coderabbit_rate_limit_notice(body)


def cmd_pr_create(args: argparse.Namespace) -> dict:
    """Handle 'pr create' subcommand.

    The PR body comes from exactly ONE of two mutually-exclusive sources:

    - ``--plan-id`` [+ ``--slot``]: the plan-bound body store (a prepared scratch
      file consumed here and deleted on success).
    - ``--body-file PATH``: an explicit file read directly (the plan-less /
      steward path — no plan directory exists to hold a scratch body).

    Supplying neither, or both, is rejected.
    """
    # Check auth
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_create', err)

    # Resolve the body from exactly one source. Validate the mutual-exclusion
    # contract before any network call. Both ``plan_id`` and ``body_file`` are
    # read defensively via getattr so a direct-Namespace caller that bypasses the
    # argparse parser and omits either flag falls through to the "no body source"
    # error instead of raising AttributeError.
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
            'A PR body source is required: supply either --plan-id (plan-bound body '
            'store) or --body-file PATH (plan-less body file)',
        )

    consumed_from_store = False
    if body_file:
        # Plan-less path: read the body directly from the explicit file. Fail
        # loud on a missing / unreadable / empty file.
        try:
            body = Path(body_file).read_text(encoding='utf-8')
        except OSError as exc:
            return make_error('pr_create', f'Could not read --body-file {body_file}', str(exc))
        if not body.strip():
            return make_error('pr_create', f'--body-file is empty: {body_file}')
    else:
        # Plan-bound path: consume the prepared scratch body from the body store.
        # plan_id is non-None here — the mutual-exclusion guard above returned
        # early when both sources were falsy, and body_file is falsy in this branch.
        assert plan_id is not None  # noqa: S101 — narrowing after the mutual-exclusion guard
        store_body, err_dict = read_and_consume_body(plan_id, BODY_KIND_PR_CREATE, getattr(args, 'slot', None))
        if err_dict or store_body is None:
            return make_error('pr_create', (err_dict or {}).get('message', 'body not prepared'))
        body = store_body
        consumed_from_store = True

    # Build command
    gh_args = ['pr', 'create', '--title', args.title, '--body', body]
    if args.base:
        gh_args.extend(['--base', args.base])
    if args.draft:
        gh_args.append('--draft')
    if getattr(args, 'head', None):
        gh_args.extend(['--head', args.head])
    # Optional --label passthrough (repeatable). create-pr applies
    # `--label skip-bot-review` when the enabled_bots set is empty; the label is
    # a best-effort suppression signal layered on top of the real gate (the
    # producer enabled_bots filter that files no findings for disabled bots).
    for label in getattr(args, 'label', None) or []:
        gh_args.extend(['--label', label])

    # Execute
    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_create', 'Failed to create PR', stderr.strip())

    # Delete the consumed scratch body — success only, and only when the body
    # came from the plan-bound store (the plan-less --body-file is caller-owned).
    if consumed_from_store:
        assert plan_id is not None  # noqa: S101 — consumed_from_store is set only on the plan-bound path
        delete_consumed_body(plan_id, BODY_KIND_PR_CREATE, getattr(args, 'slot', None))

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


def cmd_pr_view(args: argparse.Namespace) -> dict:
    """Handle 'pr view' subcommand - get PR for current branch (or --head branch)."""
    return github_ops.view_pr_data(head=getattr(args, 'head', None))


def cmd_pr_list(args: argparse.Namespace) -> dict:
    """Handle 'pr list' subcommand - list pull requests with optional filters."""
    is_auth, err = github_ops.check_auth()
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

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
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


def cmd_pr_reply(args: argparse.Namespace) -> dict:
    """Handle 'pr reply' — post a comment using the prepared body."""
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_reply', err)

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_PR_REPLY, getattr(args, 'slot', None))
    if err_dict or body is None:
        return make_error('pr_reply', (err_dict or {}).get('message', 'body not prepared'))

    gh_args = ['pr', 'comment', str(args.pr_number), '--body', body]
    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_reply', 'Failed to post comment', stderr.strip())

    delete_consumed_body(args.plan_id, BODY_KIND_PR_REPLY, getattr(args, 'slot', None))
    return {
        'status': 'success',
        'operation': 'pr_reply',
        'pr_number': args.pr_number,
        'output': stdout.strip(),
    }


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
    returncode, data, err = github_ops.run_graphql(VIEWER_LOGIN_QUERY, {})
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
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_resolve_thread', err)

    returncode, data, err = github_ops.run_graphql(RESOLVE_THREAD_MUTATION, {'threadId': args.thread_id})
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
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_thread_reply', err)

    body, err_dict = read_and_consume_body(args.plan_id, BODY_KIND_PR_THREAD_REPLY, getattr(args, 'slot', None))
    if err_dict:
        return make_error('pr_thread_reply', err_dict.get('message', 'body not prepared'))

    returncode, data, err = github_ops.run_graphql(
        THREAD_REPLY_MUTATION,
        {'threadId': args.thread_id, 'body': body},
    )
    if returncode != 0 or data is None:
        return make_error('pr_thread_reply', f'Failed to reply to thread: {err}')

    delete_consumed_body(args.plan_id, BODY_KIND_PR_THREAD_REPLY, getattr(args, 'slot', None))

    # Post-call regression check: a successful addPullRequestReviewThreadReply
    # must not leave a PENDING review owned by the current viewer. If it does,
    # the reply is queued into a draft review and is invisible to reviewers.
    viewer_login, viewer_err = get_viewer_login()
    if viewer_login is None:
        return make_error(
            'pr_thread_reply',
            f'Reply sent but viewer.login lookup failed: {viewer_err}',
        )

    owner, repo = github_ops.get_repo_info()
    if not owner or not repo:
        return make_error(
            'pr_thread_reply',
            'Reply sent but could not determine repository owner/name for PENDING-review check',
        )

    rc2, pending_data, pending_err = github_ops.run_graphql(
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

    stuck = [n for n in pending_nodes if (n.get('author') or {}).get('login') == viewer_login]
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
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_submit_review', err)

    returncode, data, err = github_ops.run_graphql(
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
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_reviews', err)

    # Get reviews
    returncode, stdout, stderr = github_ops.run_gh(['pr', 'view', str(args.pr_number), '--json', 'reviews'])
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
            'user': (r.get('author') or {}).get('login', 'unknown'),
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


def cmd_pr_comments(args: argparse.Namespace) -> dict:
    """Handle 'pr comments' subcommand - fetch inline code review comments."""
    return github_ops.fetch_pr_comments_data(args.pr_number, args.unresolved_only)


def cmd_pr_wait_for_comments(args: argparse.Namespace) -> dict:
    """Handle 'pr wait-for-comments' — poll until new unresolved comments arrive or timeout.

    Replaces the blocking shell ``sleep`` previously used by workflow-pr-doctor's
    Automated Review Lifecycle Step 2. Snapshots the unresolved-comment count
    once, then polls on the standard CI interval and exits as soon as the count
    grows (a new bot comment arrived) or the timeout is reached. Reuses the
    same ``poll_until`` helper that powers ``ci wait``.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_wait_for_comments', err)

    initial = github_ops.fetch_pr_comments_data(args.pr_number, unresolved_only=True)
    if initial.get('status') != 'success':
        return make_error(
            'pr_wait_for_comments',
            f'Initial unresolved-comment fetch failed for PR {args.pr_number}',
            str(initial.get('error', '')),
        )
    baseline = int(initial.get('unresolved') or 0)

    def check_fn() -> tuple[bool, dict]:
        snapshot = github_ops.fetch_pr_comments_data(args.pr_number, unresolved_only=True)
        if snapshot.get('status') != 'success':
            return False, {
                'error': f'Unresolved-comment fetch failed for PR {args.pr_number}',
                'context': str(snapshot.get('error', '')),
            }
        return True, {'unresolved': int(snapshot.get('unresolved') or 0)}

    def is_complete_fn(data: dict) -> bool:
        return int(data.get('unresolved', 0)) > baseline

    result = github_ops.poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error(
            'pr_wait_for_comments',
            result['error'],
            result.get('last_data', {}).get('context', ''),
        )

    final_count = int(result['last_data'].get('unresolved', baseline))

    # Additive rate-limit discriminator: after the poll settles, inspect the
    # newest CodeRabbit-bot comment for a rate-limit status notice. Best-effort —
    # a failed fetch leaves the default ``False`` and never alters poll behaviour.
    rate_limited = False
    post = github_ops.fetch_pr_comments_data(args.pr_number)
    if post.get('status') == 'success':
        rate_limited = _detect_coderabbit_rate_limited(post.get('comments') or [])

    return {
        'status': 'success',
        'operation': 'pr_wait_for_comments',
        'pr_number': args.pr_number,
        'timed_out': result['timed_out'],
        'duration_sec': result['duration_sec'],
        'polls': result['polls'],
        'baseline_count': baseline,
        'final_count': final_count,
        'new_count': max(final_count - baseline, 0),
        'rate_limited': rate_limited,
    }


def cmd_pr_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr merge' subcommand - merge a pull request.

    When ``--delete-branch`` is requested, the merge is performed WITHOUT the
    ``--delete-branch`` pass-through to ``gh pr merge``; instead, after a
    successful merge, the PR's head branch is deleted remotely via the
    ``cmd_branch_delete`` handler (REST ``DELETE /git/refs/heads/{branch}``).
    Local git state is never touched by this handler — callers who want a
    local branch gone must invoke ``git -C {path} branch -D`` separately.

    On branch-delete failure after a successful merge, a compound result is
    returned with ``merged: true`` and ``branch_delete_error`` populated. The
    merge is NOT retried.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_merge', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_merge')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    gh_args = ['pr', 'merge', identifier, f'--{args.strategy}']

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_merge', f'Failed to merge PR {identifier}', stderr.strip())

    result: dict = {
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number if args.pr_number else identifier,
        'strategy': args.strategy,
    }

    # Branch-delete is an optional follow-up. The merge has already succeeded;
    # we never retry the merge on branch-delete failure.
    if args.delete_branch:
        result['merged'] = True

        # Resolve the PR head branch name via existing PR metadata.
        # ``gh pr view`` accepts either a PR number or a branch name as the
        # positional, so ``identifier`` (already resolved) is passed through
        # directly.
        pr_view = github_ops.view_pr_data(head=identifier)
        if pr_view.get('status') != 'success':
            result['branch_delete_error'] = (
                f'Merge succeeded but could not resolve head branch for delete: '
                f'{pr_view.get("error", "pr_view failed")}'
            )
            return result

        head_branch = pr_view.get('head_branch') or ''
        if not head_branch:
            result['branch_delete_error'] = 'Merge succeeded but pr_view returned empty head_branch'
            return result

        # Invoke the branch_delete handler with a synthesized argparse.Namespace.
        delete_args = argparse.Namespace(branch=head_branch)
        delete_result = cmd_branch_delete(delete_args)
        if delete_result.get('status') != 'success':
            result['branch_delete_error'] = delete_result.get('error', f'Failed to delete remote branch {head_branch}')
            return result

        result['branch_deleted'] = head_branch
        result['already_gone'] = delete_result.get('already_gone', False)

    return result


def cmd_branch_delete(args: argparse.Namespace) -> dict:
    """Handle 'branch delete' subcommand - delete a remote branch via REST API.

    Uses the GitHub REST API endpoint ``DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}``
    invoked through ``gh api``. The ``--remote-only`` flag is required and explicit:
    local branch management is out of scope and handled via ``git -C {path} branch``.

    HTTP semantics:
      - 204 No Content  → ``status: success`` (normal delete)
      - 404 Not Found   → ``status: success`` with ``already_gone: true``
        (branch does not exist remotely; deletion is idempotent).
      - 422 Unprocessable Entity → ``status: success`` with ``already_gone: true``
        (GitHub returns 422 when the ref is already gone; same idempotent semantics).
      - Anything else   → ``status: error``
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('branch_delete', err)

    owner, repo = github_ops.get_repo_info()
    if not owner or not repo:
        return make_error('branch_delete', 'Failed to resolve repository owner/name from current cwd')

    branch = args.branch
    # URL-encode the branch segment so names like ``feature/x`` serialize as
    # ``feature%2Fx``. ``safe=''`` ensures ``/`` is encoded (mirrors the same
    # pattern used in gitlab_ops.py). Without this, branch names containing
    # ``/``, ``#``, ``?``, or other reserved characters would produce a
    # malformed REST path.
    branch_encoded = quote(branch, safe='')
    endpoint = f'repos/{owner}/{repo}/git/refs/heads/{branch_encoded}'
    returncode, _stdout, stderr = github_ops.run_gh(['api', '-X', 'DELETE', endpoint])
    if returncode != 0:
        stderr_text = stderr.strip()
        # gh api surfaces the HTTP status in stderr as "(HTTP 404)" / "(HTTP 422)".
        # Treat those as success (already gone) — deletion is idempotent by design.
        if 'HTTP 404' in stderr_text or 'HTTP 422' in stderr_text:
            return {
                'status': 'success',
                'operation': 'branch_delete',
                'branch': branch,
                'remote_only': True,
                'already_gone': True,
            }
        return make_error(
            'branch_delete',
            f'Failed to delete remote branch {branch}',
            stderr_text,
        )

    return {
        'status': 'success',
        'operation': 'branch_delete',
        'branch': branch,
        'remote_only': True,
        'already_gone': False,
    }


def cmd_pr_auto_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr auto-merge' subcommand - enable auto-merge on a pull request."""
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_auto_merge', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_auto_merge')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    gh_args = ['pr', 'merge', identifier, '--auto', f'--{args.strategy}']

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_auto_merge', f'Failed to enable auto-merge for PR {identifier}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'pr_auto_merge',
        'pr_number': args.pr_number if args.pr_number else identifier,
        'enabled': True,
    }


# Mergeable states for which a normal merge will succeed. ``clean`` is the
# fully-ready state; ``unstable`` (non-required checks failing) and
# ``has_hooks`` (merge will fire post-merge hooks) are also mergeable per the
# GitHub mergeStateStatus contract. ``blocked`` / ``behind`` / ``dirty`` /
# ``unknown`` are NOT mergeable and keep the readiness poll running.
_SAFE_MERGE_READY_STATES = frozenset({'clean', 'unstable', 'has_hooks'})


def cmd_pr_safe_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr safe-merge' subcommand - poll readiness then merge.

    Layer 1 (both providers): poll the PR's ``mergeStateStatus`` until it
    reaches a mergeable state, then delegate the actual merge (including the
    ``--delete-branch`` REST follow-up) to :func:`cmd_pr_merge`.

    Layer 2 (GitHub-only): when readiness stays ``blocked`` past the poll
    timeout AND ``--admin-merge-on-stuck-state`` is set AND every active
    ruleset requirement is provably met, fall back to ``gh pr merge --admin``.
    This targets GitHub's post-force-push ``mergeable_state: blocked``
    staleness, where the merge requirements are met but GitHub has not
    recomputed mergeability.

    Returns canonical TOON with ``operation: pr_safe_merge``, ``merge_path``
    (``polled_clean`` | ``admin_fallback``), ``polls``, and ``duration_sec``.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_safe_merge', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_safe_merge')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    # Base-branch-scoped merge-queue preflight (guards the #866 signature: an
    # immediate merge on a branch with a REQUIRED platform merge queue closes
    # the PR unmerged instead of merging it). Probe the PR's OWN base branch —
    # not the repository default branch — because a PR may target a non-default
    # base whose merge-queue configuration differs. Fail closed: any resolution
    # failure refuses the merge rather than polling or merging blind.
    preflight_view = github_ops.view_pr_data(head=identifier)
    if preflight_view.get('status') != 'success':
        return make_error(
            'pr_safe_merge',
            f'Could not resolve base branch for merge-queue preflight of PR {identifier}',
            preflight_view.get('error', 'pr_view failed'),
        )
    base_branch = preflight_view.get('base_branch') or ''
    if not base_branch:
        return make_error(
            'pr_safe_merge',
            f'PR {identifier} view returned an empty base branch; refusing the merge-queue preflight',
        )

    owner, repo = github_ops.get_repo_info()
    if not owner or not repo:
        return make_error(
            'pr_safe_merge',
            'Could not determine repository owner/name for the merge-queue preflight',
        )

    mq_discriminator, mq_detail, mq_error, _mq_method = github_ops._probe_merge_queue_state(
        owner, repo, base_branch
    )
    if mq_error is not None:
        # Auth-scope failure, non-404 gh api error, or malformed rules response.
        return make_error('pr_safe_merge', mq_error, mq_detail)
    if mq_discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED:
        # A merge queue is required on the PR's base branch — an immediate merge
        # would close the PR unmerged (#866). Refuse and name BOTH remedies.
        return make_error(
            'pr_safe_merge',
            f'PR {identifier} targets base branch {base_branch!r}, which has a required platform '
            f'merge queue — an immediate merge would close the PR unmerged (#866). Route the PR '
            f'through the merge queue via "ci pr merge-queue", or reconcile the plan\'s '
            f'use_merge_queue step param via /marshall-steward.',
            mq_detail,
        )
    # MERGE_QUEUE_ELIGIBLE_UNCONFIGURED / MERGE_QUEUE_INELIGIBLE /
    # MERGE_QUEUE_UNSUPPORTED all fall through to the existing behaviour.

    # Layer 1 — poll readiness via the shared poll_until helper.
    def check_fn() -> tuple[bool, dict]:
        data = github_ops.view_pr_data(head=identifier)
        if data.get('status') != 'success':
            return False, {'error': data.get('error', 'pr_view failed')}
        return True, data

    def is_ready(data: dict) -> bool:
        return data.get('merge_state') in _SAFE_MERGE_READY_STATES

    poll_result = github_ops.poll_until(
        check_fn,
        is_ready,
        timeout=args.poll_timeout,
        interval=args.poll_interval,
    )

    polls = poll_result.get('polls', 0)
    duration_sec = poll_result.get('duration_sec', 0)

    # A check_fn failure (PR not found / auth) is propagated immediately.
    if poll_result.get('error'):
        return make_error('pr_safe_merge', f'Readiness poll failed for PR {identifier}', poll_result['error'])

    last_state = (poll_result.get('last_data') or {}).get('merge_state', 'unknown')

    if not poll_result.get('timed_out'):
        # Readiness reached — delegate to the normal merge path.
        merge_result = cmd_pr_merge(_safe_merge_delegate_ns(args))
        if merge_result.get('status') != 'success':
            # Normalize the delegated failure to this verb's operation so the
            # safe-merge response contract holds for downstream consumers.
            return make_error(
                'pr_safe_merge',
                merge_result.get('error', f'Failed to merge PR {identifier}'),
                merge_result.get('context', ''),
            )
        # Post-merge verification: the merge CLI reported success, but on a
        # merge-queue-required base branch GitHub closes the PR unmerged rather
        # than merging it (the #866 signature). Re-fetch and require the PR to
        # be actually merged before trusting the reported success.
        post_merge_view = github_ops.view_pr_data(head=identifier)
        if post_merge_view.get('status') == 'success' and post_merge_view.get('state') == 'closed':
            return make_error(
                'pr_safe_merge',
                f'PR {identifier} was closed WITHOUT merging — the merge reported success but the '
                f'PR state is closed-unmerged (#866). This base branch likely requires the platform '
                f'merge queue; route the PR via "ci pr merge-queue" instead of an immediate merge.',
                'post_merge_state=closed',
            )
        merge_result['operation'] = 'pr_safe_merge'
        merge_result['merge_path'] = 'polled_clean'
        merge_result['polls'] = polls
        merge_result['duration_sec'] = duration_sec
        # Prefer the integer PR number resolved during polling over the branch
        # name cmd_pr_merge echoes back when --head was used.
        merge_result['pr_number'] = (poll_result.get('last_data') or {}).get('pr_number') or merge_result.get('pr_number')
        return merge_result

    # Timed out while not ready. Layer 2 admin fallback is GitHub-only and
    # gated by the knob plus a provably-met ruleset.
    if not args.admin_merge_on_stuck_state:
        return make_error(
            'pr_safe_merge',
            f'PR {identifier} not mergeable after poll timeout (merge_state={last_state}); '
            'admin fallback not enabled (--admin-merge-on-stuck-state)',
        )

    if last_state != 'blocked':
        return make_error(
            'pr_safe_merge',
            f'PR {identifier} not mergeable after poll timeout (merge_state={last_state}); '
            'admin fallback applies only to a stuck blocked state',
        )

    gate_ok, gate_reason = github_ops._safe_merge_stuck_state_gate(identifier)
    if not gate_ok:
        return make_error(
            'pr_safe_merge',
            f'PR {identifier} stuck blocked but ruleset requirements not provably met; '
            f'refusing admin fallback: {gate_reason}',
        )

    # Every requirement provably met — perform the admin merge.
    returncode, _stdout, stderr = github_ops.run_gh(['pr', 'merge', identifier, '--admin', f'--{args.strategy}'])
    if returncode != 0:
        return make_error('pr_safe_merge', f'Admin merge failed for PR {identifier}', stderr.strip())

    result: dict = {
        'status': 'success',
        'operation': 'pr_safe_merge',
        'pr_number': (poll_result.get('last_data') or {}).get('pr_number') or (args.pr_number if args.pr_number else identifier),
        'strategy': args.strategy,
        'merge_path': 'admin_fallback',
        'polls': polls,
        'duration_sec': duration_sec,
    }

    # Reuse the same REST-delete follow-up as the normal merge path.
    if args.delete_branch:
        result['merged'] = True
        pr_view = github_ops.view_pr_data(head=identifier)
        if pr_view.get('status') != 'success':
            result['branch_delete_error'] = (
                f'Merge succeeded but could not resolve head branch for delete: '
                f'{pr_view.get("error", "pr_view failed")}'
            )
            return result
        head_branch = pr_view.get('head_branch') or ''
        if not head_branch:
            result['branch_delete_error'] = 'Merge succeeded but pr_view returned empty head_branch'
            return result
        delete_result = cmd_branch_delete(argparse.Namespace(branch=head_branch))
        if delete_result.get('status') != 'success':
            result['branch_delete_error'] = delete_result.get('error', f'Failed to delete remote branch {head_branch}')
            return result
        result['branch_deleted'] = head_branch
        result['already_gone'] = delete_result.get('already_gone', False)

    return result


def _safe_merge_delegate_ns(args: argparse.Namespace) -> argparse.Namespace:
    """Synthesize the argparse.Namespace cmd_pr_merge expects from safe-merge args.

    cmd_pr_merge reads ``pr_number``, ``head``, ``strategy``, and
    ``delete_branch`` and re-resolves the PR identifier itself, so only those
    four fields are forwarded.
    """
    return argparse.Namespace(
        pr_number=args.pr_number,
        head=args.head,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
    )


def cmd_pr_merge_queue(args: argparse.Namespace) -> dict:
    """Handle 'pr merge-queue' subcommand — enqueue the PR into the GitHub merge queue.

    GitHub's merge queue is engaged by enabling auto-merge on a PR whose target
    branch has a merge queue configured in branch protection: ``gh pr merge
    --auto`` adds the PR to the queue, and the platform re-tests-and-merges it
    against the latest base. This serializes a truly-external commit (e.g. a
    dependabot merge to the base) that the session-scoped merge mutex cannot,
    closing the residual staleness gap the mutex leaves open. It composes with
    the widened mutex: the mutex guards the pre-enqueue rebase/force-push window;
    the merge queue serializes the merge itself at the platform.

    Returns canonical TOON with ``operation: pr_merge_queue`` and
    ``enqueued: true`` on success.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_merge_queue', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_merge_queue')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    # The enqueue command is exactly ``gh pr merge --auto``. Neither --strategy
    # nor --delete-branch is forwarded: the merge queue's own branch-protection
    # configuration dictates the merge method, and GitHub rejects
    # --delete-branch when a merge queue is enabled ("Cannot use --delete-branch
    # when merge queue enabled") — the platform auto-deletes the head branch
    # after the queue merge, so the flag is both rejected and redundant.
    gh_args = ['pr', 'merge', identifier, '--auto']
    returncode, _stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error(
            'pr_merge_queue',
            f'Failed to enqueue PR {identifier} into the merge queue',
            stderr.strip(),
        )

    return {
        'status': 'success',
        'operation': 'pr_merge_queue',
        'pr_number': args.pr_number if args.pr_number else identifier,
        'enqueued': True,
    }


# Stable fallback label color (GitHub's own default gray) applied when the
# caller omits --color. Without a stable default, `gh label create --force`
# passes no --color at all, and `gh`'s own provider default is not guaranteed
# to match a color a prior `ensure` call (or a manually-created label) already
# set — so a bare re-run of `ensure` is not a true no-op on color. Pinning a
# stable value here (rather than relying on `gh`'s default) keeps `ensure`
# idempotent on every field, not just presence.
_DEFAULT_LABEL_COLOR = 'ededed'


def cmd_repo_label_ensure(args: argparse.Namespace) -> dict:
    """Handle 'repo label ensure' — ensure a repository label exists (idempotent).

    Uses ``gh label create {name} --force``: ``--force`` makes the create
    UPDATE an existing label in place instead of erroring, so a re-run against an
    already-present label is a no-op success (create-if-missing semantics).
    ``--color`` always has a value — an explicitly supplied color is preserved,
    otherwise the stable ``_DEFAULT_LABEL_COLOR`` fallback is sent so a color-less
    re-run cannot reset an existing label's color to whatever `gh` defaults to.
    Optional ``--description`` is passed through when supplied.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('repo_label_ensure', err)

    color = getattr(args, 'color', None) or _DEFAULT_LABEL_COLOR
    gh_args = ['label', 'create', args.label, '--force', '--color', color]
    if getattr(args, 'description', None):
        gh_args.extend(['--description', args.description])

    returncode, _stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('repo_label_ensure', f'Failed to ensure label {args.label!r}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'repo_label_ensure',
        'provider': 'github',
        'label': args.label,
        'ensured': True,
    }


def cmd_pr_update_branch(args: argparse.Namespace) -> dict:
    """Handle 'pr update-branch' subcommand - update PR branch with base branch changes."""
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_update_branch', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_update_branch')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    gh_args = ['pr', 'update-branch', identifier]

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_update_branch', f'Failed to update branch for PR {identifier}', stderr.strip())

    return {
        'status': 'success',
        'operation': 'pr_update_branch',
        'pr_number': args.pr_number if args.pr_number else identifier,
    }


cmd_pr_close = make_pr_number_handler(
    'pr_close',
    lambda args: ['pr', 'close', str(args.pr_number)],
    github_ops.run_gh,
    github_ops.check_auth,
)


cmd_pr_ready = make_pr_number_handler(
    'pr_ready',
    lambda args: ['pr', 'ready', str(args.pr_number)],
    github_ops.run_gh,
    github_ops.check_auth,
)


def cmd_pr_edit(args: argparse.Namespace) -> dict:
    """Handle 'pr edit' subcommand - edit PR title and/or body.

    Body is consumed from the prepared scratch file for
    ``BODY_KIND_PR_EDIT``; callers who want to update only the title can skip
    preparing a body and the edit proceeds without touching the description.
    """
    # Body is optional on edit: the caller may just want to rename the PR.
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

    gh_args = ['pr', 'edit', str(args.pr_number)]
    if args.title:
        gh_args.extend(['--title', args.title])
    if body:
        gh_args.extend(['--body', body])

    result: dict = make_pr_number_handler('pr_edit', lambda a: gh_args, github_ops.run_gh, github_ops.check_auth)(args)
    if body and result.get('status') == 'success':
        delete_consumed_body(args.plan_id, BODY_KIND_PR_EDIT, getattr(args, 'slot', None))
    return result


def post_pr_comment(pr_number: int | str, body: str) -> dict:
    """Post a comment on a PR via ``gh pr comment``.

    Used by the re-review strategy registry to post a bot review-trigger
    comment (e.g. ``/gemini review``). Reuses the existing ``run_gh`` wrapper —
    no new HTTP path. Returns a structured envelope with ``status`` of
    ``success`` or ``error``.
    """

    returncode, stdout, stderr = github_ops.run_gh(['pr', 'comment', str(pr_number), '--body', body])
    if returncode != 0:
        return make_error('post_pr_comment', 'Failed to post comment', stderr.strip())
    return {
        'status': 'success',
        'operation': 'post_pr_comment',
        'pr_number': pr_number,
        'output': stdout.strip(),
    }


def fetch_pr_reviews_with_commits(pr_number: int | str) -> dict:
    """Fetch a PR's reviews with their reviewed commit SHA and submission time.

    ``gh pr view --json reviews`` does not expose each review's reviewed commit,
    so the re-review registry needs the raw ``commit.oid`` plus ``submittedAt``
    and the author login to match a fresh review against the current HEAD. Uses
    the ``gh api`` REST path (still via ``run_gh``) — the GraphQL
    ``PullRequestReview`` node exposes ``commit`` only on a recent schema, while
    the REST ``/reviews`` payload carries ``commit_id`` directly.

    Returns a structured envelope. On success ``reviews`` is a list of
    ``{user, state, submitted_at, commit_sha}`` dicts.
    """

    owner, repo = github_ops.get_repo_info()
    if not owner or not repo:
        return make_error('fetch_pr_reviews_with_commits', 'Could not determine repository owner/name')

    endpoint = f'repos/{owner}/{repo}/pulls/{pr_number}/reviews'
    returncode, stdout, stderr = github_ops.run_gh(['api', endpoint, '--paginate', '--slurp'])
    if returncode != 0:
        return make_error('fetch_pr_reviews_with_commits', f'Failed to fetch reviews for PR {pr_number}', stderr.strip())

    try:
        raw_pages = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('fetch_pr_reviews_with_commits', 'Failed to parse gh api output', stdout[:100])

    if not isinstance(raw_pages, list):
        return make_error('fetch_pr_reviews_with_commits', 'Unexpected reviews payload shape', str(raw_pages)[:100])

    # --slurp wraps all pages into an outer array; flatten pages into a single list.
    raw_reviews: list[dict] = []
    for page in raw_pages:
        if isinstance(page, list):
            raw_reviews.extend(r for r in page if isinstance(r, dict))
        elif isinstance(page, dict):
            raw_reviews.append(page)

    reviews = [
        {
            'user': (r.get('user') or {}).get('login', 'unknown'),
            'state': r.get('state', 'UNKNOWN'),
            'submitted_at': r.get('submitted_at') or '',
            'commit_sha': r.get('commit_id') or '',
        }
        for r in raw_reviews
    ]
    return {
        'status': 'success',
        'operation': 'fetch_pr_reviews_with_commits',
        'pr_number': pr_number,
        'review_count': len(reviews),
        'reviews': reviews,
    }


def _cmd_pr_prepare_body(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for a PR body (create or edit)."""
    kind = BODY_KIND_PR_EDIT if getattr(args, 'prepare_for', 'create') == 'edit' else BODY_KIND_PR_CREATE
    return prepare_body(args.plan_id, kind, getattr(args, 'slot', None))


def _cmd_pr_prepare_comment(args: argparse.Namespace) -> dict:
    """Allocate a scratch path for a PR comment (reply or thread-reply)."""
    kind = BODY_KIND_PR_THREAD_REPLY if getattr(args, 'prepare_for', 'reply') == 'thread-reply' else BODY_KIND_PR_REPLY
    return prepare_body(args.plan_id, kind, getattr(args, 'slot', None))
