#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
GitLab MR workflow operations - two-verb provider contract: fetch_findings + post_responses.

The provider surface is exactly TWO pure, zero-LLM verbs — no triage judgment
lives here:

- ``fetch_findings`` fetches MR review comments, applies the keyword pre-filter
  from ``standards/comment-patterns.json`` to drop obvious noise, then files one
  ``pr-comment`` finding per surviving comment. The untrusted comment body is
  quarantined under ``raw_input.{body}`` — never embedded raw in the top-level
  ``detail`` — and promoted only by the batched ``manage-findings ingest`` pass.
- ``post_responses`` applies already-decided triage dispositions back to the MR
  — a discussion-note reply carrying the ``resolution_detail`` then a
  resolve-discussion — keyed by each finding's own ``hash_id``. It makes NO
  triage decision.

Both verbs FAIL LOUD when GitLab is not configured: a typed ``unconfigured``
status, never a silent no-op (lesson 2026-06-22-14-001). LLM consumers query the
ledger via ``manage-findings query --type pr-comment``.

Usage:
    gitlab_pr.py fetch-comments [--pr <number>] [--unresolved-only]
    gitlab_pr.py fetch_findings --pr-number <N> --plan-id <P>
    gitlab_pr.py post_responses --pr-number <N> --plan-id <P>
    gitlab_pr.py --help

Subcommands:
    fetch-comments    Fetch MR review comments (raw, no filtering or storage)
    fetch_findings    Producer-side: fetch + pre-filter + file one pr-comment finding per surviving comment
    post_responses    Apply triaged dispositions (note-reply + resolve-discussion) back to the MR, keyed by hash_id

Examples:
    # Fetch raw comments
    gitlab_pr.py fetch-comments --pr 123

    # Find stage (fetch, filter, file findings with quarantined raw_input)
    gitlab_pr.py fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN

    # Respond stage (apply already-decided dispositions back to the MR)
    gitlab_pr.py post_responses --pr-number 123 --plan-id EXAMPLE-PLAN
"""

import re
import sys
from typing import Any
from urllib.parse import quote

import gitlab_ops as _gitlab
from ci_base import extract_routing_args, register_subcommands, set_default_cwd
from triage_helpers import (
    ErrorCode,
    compile_patterns_from_config,
    create_workflow_cli,
    load_skill_config,
    make_error,
    safe_main,
)

# Register this script's top-level subcommand tokens so that extract_routing_args
# correctly identifies the subcommand boundary when gitlab_pr.py is the entry
# point (i.e., does not consume a subcommand-level --plan-id as a router flag).
register_subcommands({'fetch-comments', 'fetch_findings', 'post_responses'})

# Resolutions that are terminal triage dispositions — a pr-comment finding in one
# of these states has been decided by the triage pass and is eligible for a
# provider response. `pending` (still awaiting triage) is deliberately excluded.
_RESPONDABLE_RESOLUTIONS = frozenset({'fixed', 'suppressed', 'accepted', 'taken_into_account', 'rejected'})

# Matches the ``thread_id: <value>`` line written into every pr-comment finding's
# ``detail`` block by cmd_fetch_findings.
_THREAD_ID_DETAIL = re.compile(r'^thread_id:\s*(?P<id>.+?)\s*$', re.MULTILINE)

# ============================================================================
# PRE-FILTER CONFIGURATION (loaded from comment-patterns.json)
# ============================================================================
#
# comment-patterns.json is a PRE-FILTER for noise removal only. It used to
# carry the LLM decision authority (full keyword classification), but the
# producer-side migration moves the decision to the LLM consumer, which
# loads each surviving finding from the per-type store. The keyword data is
# kept here verbatim so we can still drop obvious automated/acknowledgment
# noise (e.g., "lgtm", "thanks!", bot signatures) before the finding store
# is populated. A surviving comment becomes a ``pr-comment`` finding.

PATTERNS: dict[str, Any] = load_skill_config(__file__, 'comment-patterns.json')

# Pre-compile only the ``ignore`` category — that's what the pre-filter uses.
# Other categories (``code_change``, ``explain``) are no longer consulted by
# this script; the LLM decides classification downstream from the finding
# detail.
_COMPILED_IGNORE: list[re.Pattern] = []
for _priority, _pattern_list in PATTERNS.get('ignore', {}).items():
    _COMPILED_IGNORE.extend(
        compile_patterns_from_config(
            _pattern_list,
            f'comment-patterns.json [ignore][{_priority}]',
        )
    )


# ============================================================================
# FETCH-COMMENTS SUBCOMMAND (raw fetch, no filtering or storage)
# ============================================================================


def get_current_pr_number() -> int | None:
    """Get MR number for current branch via GitLab's view_pr_data()."""
    result = _gitlab.view_pr_data()
    if result.get('status') != 'success':
        return None

    pr_number = result.get('pr_number')
    if pr_number is None or pr_number == 'unknown':
        return None
    try:
        return int(pr_number)
    except (ValueError, TypeError):
        return None


def fetch_comments(pr_number: int, unresolved_only: bool = False) -> dict[str, Any]:
    """Fetch review comments for a MR via GitLab's fetch_pr_comments_data()."""

    result = _gitlab.fetch_pr_comments_data(pr_number, unresolved_only)

    if result.get('status') != 'success':
        return make_error(result.get('error', 'Failed to fetch PR comments'), code=ErrorCode.FETCH_FAILURE)

    # Transform provider result into gitlab_pr.py's expected format
    return {
        'pr_number': pr_number,
        'provider': result.get('provider', 'unknown'),
        'comments': result.get('comments', []),
        'total_comments': result.get('total', 0),
        'unresolved_count': result.get('unresolved', 0),
        'status': 'success',
    }


def cmd_fetch_comments(args):
    """Handle fetch-comments subcommand."""
    # Determine PR number
    pr_number = args.pr
    if not pr_number:
        pr_number = get_current_pr_number()
        if not pr_number:
            return make_error('No PR found for current branch. Use --pr to specify.', code=ErrorCode.NOT_FOUND)

    result = fetch_comments(pr_number, getattr(args, 'unresolved_only', False))
    return result


# ============================================================================
# PRE-FILTER (Python-internal helper)
# ============================================================================


def _is_obvious_noise(body: str) -> bool:
    """Pre-filter: True if the comment body matches an ``ignore`` keyword.

    Used by ``comments-stage`` to drop obvious automated/acknowledgment noise
    (e.g., "lgtm", "thanks!", bot signatures) before each surviving comment is
    persisted as a ``pr-comment`` finding. This is intentionally permissive —
    the goal is only to skip the most obvious noise, not to make the final
    classification decision (that belongs to the LLM consumer).
    """
    if not body:
        return True
    body_lower = body.lower()
    return any(p.search(body_lower) for p in _COMPILED_IGNORE)


# ============================================================================
# FAIL-LOUD CONFIG GUARD (shared by fetch_findings + post_responses)
# ============================================================================


def _unconfigured_result(operation: str, detail: str) -> dict[str, Any]:
    """Build the typed ``unconfigured`` fail-loud signal (never a silent no-op).

    Returned when GitLab is not authenticated, so a caller can distinguish
    "provider not set up" from a genuine zero-findings success (lesson
    2026-06-22-14-001).
    """
    return {
        'status': 'unconfigured',
        'operation': operation,
        'provider': 'gitlab',
        'detail': detail,
    }


# ============================================================================
# FETCH_FINDINGS SUBCOMMAND (producer-side fetch + filter + file to ledger)
# ============================================================================


def cmd_fetch_findings(args):
    """Producer-side FIND verb: fetch + pre-filter + file one finding per surviving comment.

    Containment: the untrusted comment ``body`` is quarantined under
    ``raw_input.{body}`` — never embedded raw in the top-level ``detail``. The
    ``detail`` carries only trusted, producer-built structured metadata so the
    triage read surface stays clean-by-construction until the batched
    ``manage-findings ingest`` pass promotes the validated body.

    Fail-loud: returns a typed ``unconfigured`` status when GitLab is not
    authenticated. ``count_fetched`` vs ``count_stored`` mismatches are recorded
    as a ``qgate`` finding with title prefix ``(producer-mismatch)``.
    """
    from _findings_core import (
        add_finding,
        add_qgate_finding,
    )

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

    is_auth, auth_err = _gitlab.check_auth()
    if not is_auth:
        return _unconfigured_result('fetch_findings', auth_err)

    fetch_result = fetch_comments(pr_number, unresolved_only=False)
    if fetch_result.get('status') != 'success':
        return fetch_result

    raw_comments: list[dict] = fetch_result.get('comments') or []
    count_fetched = len(raw_comments)

    stored_hashes: list[str] = []
    skipped_noise = 0
    store_failures: list[str] = []

    for comment in raw_comments:
        body = comment.get('body') or ''
        if _is_obvious_noise(body):
            skipped_noise += 1
            continue

        kind = comment.get('kind') or 'inline'
        thread_id = comment.get('thread_id') or ''
        author = comment.get('author') or 'unknown'
        path = comment.get('path') or None
        line = comment.get('line') or None
        comment_id = comment.get('id') or 'unknown'

        location_suffix = f' @ {path}:{line}' if path and line else ''
        title = f'MR #{pr_number} {kind} comment by {author}{location_suffix} ({comment_id})'

        detail_lines = [
            f'pr_number: {pr_number}',
            f'kind: {kind}',
            f'author: {author}',
            f'thread_id: {thread_id}',
            f'comment_id: {comment_id}',
        ]
        if path:
            detail_lines.append(f'path: {path}')
        if line:
            detail_lines.append(f'line: {line}')
        detail = '\n'.join(detail_lines)

        line_arg: int | None = None
        if isinstance(line, int) and line > 0:
            line_arg = line

        add_result = add_finding(
            plan_id=plan_id,
            finding_type='pr-comment',
            title=title,
            detail=detail,
            file_path=path or None,
            line=line_arg,
            raw_input={'body': body},
        )
        if add_result.get('status') == 'success':
            stored_hashes.append(add_result.get('hash_id', ''))
        else:
            store_failures.append(comment_id)

    count_stored = len(stored_hashes)
    expected_stored = count_fetched - skipped_noise

    qgate_hash: str | None = None
    if count_stored != expected_stored:
        mismatch_detail = (
            f'count_fetched={count_fetched}, '
            f'count_skipped_noise={skipped_noise}, '
            f'count_stored={count_stored}, '
            f'expected_stored={expected_stored}, '
            f'failed_comment_ids={store_failures}'
        )
        qgate_result = add_qgate_finding(
            plan_id=plan_id,
            phase='5-execute',
            source='qgate',
            finding_type='pr-comment',
            title=f'(producer-mismatch) gitlab_pr fetch_findings MR #{pr_number}',
            detail=mismatch_detail,
        )
        qgate_hash = qgate_result.get('hash_id')

    return {
        'status': 'success',
        'operation': 'fetch_findings',
        'provider': 'gitlab',
        'pr_number': pr_number,
        'plan_id': plan_id,
        'count_fetched': count_fetched,
        'count_skipped_noise': skipped_noise,
        'count_stored': count_stored,
        'stored_hash_ids': stored_hashes,
        'producer_mismatch_hash_id': qgate_hash,
    }


# ============================================================================
# POST_RESPONSES SUBCOMMAND (apply triaged dispositions back to the MR)
# ============================================================================


def _thread_id_from_detail(detail: str | None) -> str:
    """Extract the ``thread_id`` value from a pr-comment finding's detail block."""
    match = _THREAD_ID_DETAIL.search(detail or '')
    return match.group('id') if match else ''


def cmd_post_responses(args):
    """RESPOND verb: apply already-decided triage dispositions back to the MR.

    Reads every ``pr-comment`` finding whose ``resolution`` is a terminal triage
    disposition (``_RESPONDABLE_RESOLUTIONS``) and that carries a ``thread_id``,
    and — keyed by each finding's own ``hash_id`` (relational, never positional,
    fixing lesson 2026-06-30-21-001) — posts the finding's ``resolution_detail``
    as a discussion-note reply then resolves the discussion. This verb makes NO
    triage decision.

    Fail-loud: returns a typed ``unconfigured`` status when GitLab is not
    authenticated. A finding without a ``resolution_detail`` or ``thread_id`` is
    skipped, never guessed at.
    """
    from _findings_core import query_findings

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

    is_auth, auth_err = _gitlab.check_auth()
    if not is_auth:
        return _unconfigured_result('post_responses', auth_err)

    project_path = _gitlab.get_project_path()
    if not project_path:
        return make_error('Could not determine GitLab project path', code=ErrorCode.NOT_FOUND)
    encoded_path = quote(project_path, safe='')

    findings = query_findings(plan_id, finding_type='pr-comment').get('findings') or []

    responded: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for finding in findings:
        hash_id = finding.get('hash_id', '')
        if finding.get('resolution') not in _RESPONDABLE_RESOLUTIONS:
            continue

        thread_id = _thread_id_from_detail(finding.get('detail'))
        reply_body = finding.get('resolution_detail') or ''
        if not thread_id or not reply_body:
            skipped.append({'hash_id': hash_id, 'reason': 'no thread_id or resolution_detail'})
            continue

        base = f'projects/{encoded_path}/merge_requests/{pr_number}/discussions/{thread_id}'
        rc, _out, err = _gitlab.run_glab(['api', '-X', 'POST', f'{base}/notes', '-f', f'body={reply_body}'])
        if rc != 0:
            failures.append({'hash_id': hash_id, 'thread_id': thread_id, 'error': f'note reply failed: {err.strip()}'})
            continue
        rc2, _out2, err2 = _gitlab.run_glab(['api', '-X', 'PUT', base, '-f', 'resolved=true'])
        if rc2 != 0:
            failures.append({'hash_id': hash_id, 'thread_id': thread_id, 'error': f'resolve failed: {err2.strip()}'})
            continue
        responded.append({'hash_id': hash_id, 'thread_id': thread_id})

    return {
        'status': 'success',
        'operation': 'post_responses',
        'provider': 'gitlab',
        'pr_number': pr_number,
        'plan_id': plan_id,
        'count_responded': len(responded),
        'count_skipped': len(skipped),
        'count_failed': len(failures),
        'responded': responded,
        'skipped': skipped,
        'failures': failures,
    }


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    # Consume top-level --plan-id / --project-dir before argparse runs,
    # matching the pattern used by ci.py. Two-state contract: --plan-id
    # auto-resolves via manage-status; --project-dir is the explicit
    # override; both together is a hard error. Resolved cwd is forwarded
    # to every glab subprocess via run_cli's process-global default.
    project_dir, remaining = extract_routing_args(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = create_workflow_cli(
        description='MR workflow operations',
        epilog="""
Examples:
  gitlab_pr.py fetch-comments --pr 123
  gitlab_pr.py fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN
  gitlab_pr.py post_responses --pr-number 123 --plan-id EXAMPLE-PLAN
""",
        subcommands=[
            {
                'name': 'fetch-comments',
                'help': 'Fetch MR review comments (raw)',
                'handler': cmd_fetch_comments,
                'args': [
                    {'flags': ['--pr'], 'type': int, 'help': "MR number (default: current branch's MR)"},
                    {'flags': ['--unresolved-only'], 'action': 'store_true', 'help': 'Only return unresolved comments'},
                ],
            },
            {
                'name': 'fetch_findings',
                'help': 'FIND: fetch + pre-filter + file one pr-comment finding per surviving comment (body quarantined under raw_input)',
                'handler': cmd_fetch_findings,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'MR number'},
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                ],
            },
            {
                'name': 'post_responses',
                'help': 'RESPOND: apply triaged dispositions (note-reply + resolve-discussion) back to the MR, keyed by hash_id',
                'handler': cmd_post_responses,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'MR number'},
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                ],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon

    return _output_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
