#!/usr/bin/env python3
"""
GitLab MR workflow operations - producer-side fetch + pre-filter + per-finding store.

Producer-side flow: ``comments-stage`` fetches MR review comments, applies the
keyword pre-filter from ``standards/comment-patterns.json`` to drop obvious
noise, then writes one ``pr-comment`` finding per surviving comment via
``manage-findings add`` (direct ``add_finding`` import). LLM consumers query
via ``manage-findings query --type pr-comment`` — the script-side triage
batch surface that previously accepted inline JSON has been retired.

Usage:
    gitlab_pr.py fetch-comments [--pr <number>] [--unresolved-only]
    gitlab_pr.py comments-stage --pr-number <N> --plan-id <P>
    gitlab_pr.py --help

Subcommands:
    fetch-comments    Fetch MR review comments (raw, no filtering or storage)
    comments-stage    Producer-side: fetch + pre-filter + store one finding per surviving comment

Examples:
    # Fetch raw comments
    gitlab_pr.py fetch-comments --pr 123

    # Producer-side stage (fetch, filter, store findings)
    gitlab_pr.py comments-stage --pr-number 123 --plan-id my-plan
"""

import re
import sys
from typing import Any

import gitlab_ops as _gitlab  # type: ignore[import-not-found]
from ci_base import extract_project_dir, set_default_cwd  # type: ignore[import-not-found]
from triage_helpers import (  # type: ignore[import-not-found]
    ErrorCode,
    compile_patterns_from_config,
    create_workflow_cli,
    load_skill_config,
    make_error,
    safe_main,
)

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
# COMMENTS-STAGE SUBCOMMAND (producer-side fetch + filter + store)
# ============================================================================


def cmd_comments_stage(args):
    """Producer-side: fetch + pre-filter + write one finding per surviving comment.

    Always-on storage: every surviving (non-noise) comment becomes a
    ``pr-comment`` finding via ``add_finding``. ``count_fetched`` vs
    ``count_stored`` mismatches are recorded as a ``qgate`` finding with title
    prefix ``(producer-mismatch)`` so the LLM sees them in
    ``manage-findings qgate query``.
    """
    from _findings_core import (  # type: ignore[import-not-found]
        add_finding,
        add_qgate_finding,
    )

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

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
        detail_lines.append('')
        detail_lines.append('--- body ---')
        detail_lines.append(body)
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
            title=f'(producer-mismatch) gitlab_pr comments-stage MR #{pr_number}',
            detail=mismatch_detail,
        )
        qgate_hash = qgate_result.get('hash_id')

    return {
        'status': 'success',
        'pr_number': pr_number,
        'plan_id': plan_id,
        'count_fetched': count_fetched,
        'count_skipped_noise': skipped_noise,
        'count_stored': count_stored,
        'stored_hash_ids': stored_hashes,
        'producer_mismatch_hash_id': qgate_hash,
    }


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    # Consume top-level --project-dir before argparse runs, matching the
    # pattern used by ci.py. Forwards cwd to every glab subprocess via
    # run_cli's process-global default.
    project_dir, remaining = extract_project_dir(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = create_workflow_cli(
        description='MR workflow operations',
        epilog="""
Examples:
  gitlab_pr.py fetch-comments --pr 123
  gitlab_pr.py comments-stage --pr-number 123 --plan-id my-plan
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
                'name': 'comments-stage',
                'help': 'Producer-side: fetch + pre-filter + store one pr-comment finding per surviving comment',
                'handler': cmd_comments_stage,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'MR number'},
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                ],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon  # type: ignore[import-not-found]

    return _output_toon(args.func(args))


if __name__ == '__main__':
    sys.exit(safe_main(main))
