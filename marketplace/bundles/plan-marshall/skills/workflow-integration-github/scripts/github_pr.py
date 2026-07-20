#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
GitHub PR workflow operations - two-verb findings contract (fetch_findings + post_responses) plus a bot_completion read verb.

The findings contract is exactly TWO pure, zero-LLM verbs — no triage judgment
lives here:

- ``fetch_findings`` fetches PR review comments, applies the keyword pre-filter
  from ``standards/comment-patterns.json`` to drop obvious noise, then files one
  ``pr-comment`` finding per surviving comment via ``manage-findings add``. The
  untrusted comment body is quarantined under ``raw_input.{body}`` (never
  embedded raw in the top-level ``detail``); the batched ``manage-findings
  ingest`` pass promotes it to top-level only after ``validate_struct``.
- ``post_responses`` applies already-decided triage dispositions back to the
  provider — a thread-reply carrying the ``resolution_detail`` then a
  resolve-thread — keyed by each finding's own ``hash_id`` (no positional
  pairing). It reads only findings the triage pass already resolved.

Beside the findings contract sits one auxiliary provider read:

- ``bot_completion`` reports a named bot's check-run completion state
  (``{status, in_progress, completed}``) for the PR HEAD, so the
  ``automatic-review`` wait step can await a slow bot's IN_PROGRESS check to
  completion instead of racing a fixed buffer. Pure read — files no finding.

All verbs FAIL LOUD when GitHub is not configured: a typed ``unconfigured``
status, never a silent ``done`` no-op. LLM consumers query the ledger via
``manage-findings query --type pr-comment``.

Usage:
    github_pr.py fetch-comments [--pr <number>] [--unresolved-only]
    github_pr.py fetch_findings --pr-number <N> --plan-id <P>
    github_pr.py post_responses --pr-number <N> --plan-id <P>
    github_pr.py bot_completion --pr-number <N> --bot-kind <kind>
    github_pr.py --help

Subcommands:
    fetch-comments    Fetch PR review comments (raw, no filtering or storage)
    fetch_findings    Producer-side: fetch + pre-filter + file one pr-comment finding per surviving comment
    post_responses    Apply triaged dispositions (thread-reply + resolve-thread) back to the PR, keyed by hash_id
    bot_completion    Read a named bot's check-run completion state ({status, in_progress, completed}) for the PR HEAD

Examples:
    # Fetch raw comments
    github_pr.py fetch-comments --pr 123

    # Find stage (fetch, filter, file findings with quarantined raw_input)
    github_pr.py fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN

    # Respond stage (apply already-decided dispositions back to the PR)
    github_pr.py post_responses --pr-number 123 --plan-id EXAMPLE-PLAN
"""

import json
import re
import sys
from typing import Any

import bot_registry
import github_ops as _github
from _github_pr import RESOLVE_THREAD_MUTATION, THREAD_REPLY_MUTATION, _is_rate_limit_notice
from ci_base import extract_routing_args, register_subcommands, set_default_cwd
from github_re_review import bot_kind_for_author, is_registered_trigger_comment
from triage_helpers import (
    ErrorCode,
    compile_patterns_from_config,
    create_workflow_cli,
    load_skill_config,
    make_error,
    safe_main,
)

# Register this script's top-level subcommand tokens so that extract_routing_args
# correctly identifies the subcommand boundary when github_pr.py is the entry
# point (i.e., does not consume a subcommand-level --plan-id as a router flag).
register_subcommands({'fetch-comments', 'fetch_findings', 'post_responses', 'bot_completion'})

# Resolutions that are terminal triage dispositions — a pr-comment finding in one
# of these states has been decided by the triage pass and is eligible for a
# provider response. `pending` (still awaiting triage) is deliberately excluded.
_RESPONDABLE_RESOLUTIONS = frozenset({'fixed', 'suppressed', 'accepted', 'taken_into_account', 'rejected'})

# ============================================================================
# PRE-FILTER CONFIGURATION (shared defaults + per-bot additions)
# ============================================================================
#
# The producer noise pre-filter is a two-layer, data-not-code composition:
#
#   1. SHARED / DEFAULT layer — the ``ignore`` category in comment-patterns.json.
#      These are bot-agnostic acknowledgment/automation regexes (lgtm, approved,
#      ``[bot]`` signatures, …) matched case-insensitively against the lowered
#      comment body. comment-patterns.json used to carry the LLM decision
#      authority (full keyword classification); the producer-side migration moved
#      that to the LLM consumer, so this file now holds only the shared noise
#      baseline. Its ``code_change`` / ``explain`` categories are retained as
#      historical documentation and are NOT consulted by this script.
#
#   2. PER-BOT layer — each enabled bot's ``ignore_patterns`` from the registry
#      (``automatic-review/standards/{bot_kind}.md``). These are literal
#      whole-comment markers (a walkthrough heading, a marketing footer, a no-op
#      review line, …) that only apply to that bot's own comments. They are
#      sourced from the registry at runtime, so adding/adjusting a bot's noise
#      drops is a pure standards-doc edit — no change here.
#
# A surviving comment (matched by neither layer) becomes a ``pr-comment`` finding.

PATTERNS: dict[str, Any] = load_skill_config(__file__, 'comment-patterns.json')

# Compile the SHARED ``ignore`` regexes — the bot-agnostic default layer. The
# per-bot layer is resolved separately at match time from the registry (literal
# substring markers, not regexes), so a bot-specific marker only ever drops that
# bot's comments.
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
    """Get PR number for current branch via GitHub's view_pr_data()."""
    result = _github.view_pr_data()
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
    """Fetch review comments for a PR via GitHub's fetch_pr_comments_data().

    The wrapper forwards the unified comments list from the provider verbatim,
    preserving every field on each entry — including the ``kind`` discriminator
    (``inline``, ``review_body``, or ``issue_comment``). No field filtering is
    applied, so downstream callers see the full provider-side schema unchanged.
    """

    result = _github.fetch_pr_comments_data(pr_number, unresolved_only)

    if result.get('status') != 'success':
        return make_error(result.get('error', 'Failed to fetch PR comments'), code=ErrorCode.FETCH_FAILURE)

    # Re-key the envelope for github_pr.py's expected format. The ``comments``
    # list is passed through by reference — every entry retains ``kind`` and all
    # other fields produced by ``github_ops.fetch_pr_comments_data``.
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


def _is_obvious_noise(body: str, bot_kind: str | None = None) -> bool:
    """Pre-filter: True if the comment body is shared or per-bot noise.

    Two layers (see PRE-FILTER CONFIGURATION above):

    1. SHARED — the bot-agnostic ``ignore`` regexes (lgtm, approved, ``[bot]``
       signatures, …) matched case-insensitively against the lowered body.
    2. PER-BOT — when ``bot_kind`` is a known reviewer bot, that bot's registry
       ``ignore_patterns`` (literal whole-comment markers) matched as
       case-sensitive substrings against the raw body. These markers are exact
       fragments the bot emits (a walkthrough heading, a marketing footer, a
       no-op review line), so only that bot's own comments are dropped.

    Two further pipeline-noise classes are folded in ahead of the two layers,
    both reusing existing data sources rather than new patterns:

    - REGISTERED TRIGGER — a comment whose whitespace-stripped body EQUALS a
      registered bot re-review trigger (``github_re_review.is_registered_trigger_comment``,
      derived from ``bot_registry``) is a pipeline-authored re-review request this
      workflow itself posted, not reviewer feedback. Checked for every comment
      (bot- or human-authored), since the pipeline may post under either account.
    - RATE-LIMIT / SERVICE NOTICE — a comment that is a rate-limit status notice
      (``_github_pr._is_rate_limit_notice``) posted in place of a review carries
      no actionable feedback. Bot-agnostic and author-ungated: the recognizer
      matches any notice by its structural signature (a limit-exceeded statement
      paired with a notice shape — callout / limit-heading / service tail), so a
      CodeRabbit, Sourcery, or unknown/renamed bot's notice is dropped with no
      code change naming the bot and no dependence on the author resolving to a
      known ``bot_kind``. Checked for every comment; the recognizer's two-part
      precision keeps a genuine comment that merely mentions a rate limit from
      matching.

    Used by ``fetch_findings`` to drop obvious automated/acknowledgment noise
    before each surviving comment is persisted as a ``pr-comment`` finding. This
    is intentionally permissive — the goal is only to skip the most obvious
    noise, not to make the final classification decision (that belongs to the LLM
    consumer). Human comments (``bot_kind is None``) are checked against the
    shared layer, the registered-trigger recognizer, and the author-ungated
    rate-limit / service-notice recognizer; the per-bot literal-marker layer
    stays reviewer-bot-scoped.
    """
    if not body:
        return True
    # Pipeline-authored re-review trigger comment (exact stripped-body match).
    if is_registered_trigger_comment(body):
        return True
    # Rate-limit / service notice posted in place of a review — bot-agnostic.
    # Ungated by author: the recognizer's two-part precision (a limit-exceeded
    # statement paired with a notice shape — callout / limit-heading / service
    # tail) is what drops a CodeRabbit, Sourcery, or unknown/renamed bot's
    # rate-limit notice by structural signature alone, with no per-bot hardcoding.
    # The same precision keeps a genuine comment that merely mentions a rate limit
    # in prose from being dropped, so the check is safe to apply to every comment.
    if _is_rate_limit_notice(body):
        return True
    body_lower = body.lower()
    if any(p.search(body_lower) for p in _COMPILED_IGNORE):
        return True
    if bot_kind:
        return any(marker in body for marker in bot_registry.ignore_patterns(bot_kind))
    return False


# ============================================================================
# FAIL-LOUD CONFIG GUARD (shared by fetch_findings + post_responses)
# ============================================================================


def _unconfigured_result(operation: str, detail: str) -> dict[str, Any]:
    """Build the typed ``unconfigured`` fail-loud signal (never a silent no-op).

    Both provider verbs return this shape — status ``unconfigured`` — when GitHub
    is not authenticated/reachable, so a caller can distinguish "provider not
    set up" from a genuine zero-findings success. A
    silent ``done``/``success`` on an unconfigured provider is the prohibited
    anti-pattern.
    """
    return {
        'status': 'unconfigured',
        'operation': operation,
        'provider': 'github',
        'detail': detail,
    }


# ============================================================================
# FETCH_FINDINGS SUBCOMMAND (producer-side fetch + filter + file to ledger)
# ============================================================================

# Matches the ``comment_id: <value>`` and ``thread_id: <value>`` lines written
# into every pr-comment finding's ``detail`` block by cmd_fetch_findings.
#
# The value class requires a leading non-whitespace character (``\S``) and matches
# only horizontal whitespace around it (``[ \t]``), never ``\s`` (which spans
# newlines). This is load-bearing for ``thread_id``: a thread_id-less finding is
# written as the literal line ``thread_id: `` (empty value, trailing space). A
# newline-spanning ``\s*(?P<id>.+?)`` would capture the *next* detail line (or the
# trailing space) as a spurious truthy id, so ``post_responses`` would try to
# resolve a non-existent thread instead of correctly skipping the finding. The
# ``\S``-anchored, line-bounded value class yields no match for an empty value, so
# ``_thread_id_from_detail`` returns ``''`` and the finding is skipped.
_COMMENT_ID_DETAIL = re.compile(r'^comment_id:[ \t]*(?P<id>\S[^\n]*?)[ \t]*$', re.MULTILINE)
_THREAD_ID_DETAIL = re.compile(r'^thread_id:[ \t]*(?P<id>\S[^\n]*?)[ \t]*$', re.MULTILINE)


def _existing_pr_comment_keys(query_findings, plan_id: str) -> set[tuple[str, str]]:
    """Return the set of ``(bot_kind, comment_id)`` keys already stored as pr-comment findings.

    Each pr-comment finding embeds its source ``comment_id`` on a
    ``comment_id: <value>`` line inside its ``detail`` block and carries the
    resolved ``bot_kind`` as a top-level field. Reconstructing the set of
    ``(bot_kind, comment_id)`` pairs from the persisted findings (across all
    resolution states) lets the producer skip any comment — thread-bearing or
    thread_id-less, from any bot kind — that was already staged in a prior
    finalize iteration, closing the cross-iteration phantom loop for all bots.

    Keying on ``(bot_kind, comment_id)`` rather than ``comment_id`` alone avoids
    a collision between two distinct bots that happen to reuse the same numeric
    comment id. A human-authored finding (``bot_kind`` unset) contributes
    ``('', comment_id)``.

    Args:
        query_findings: The ``_findings_core.query_findings`` callable.
        plan_id: Plan identifier whose findings store is queried.

    Returns:
        Set of ``(bot_kind, comment_id)`` tuples already present in the
        pr-comment store.
    """
    result = query_findings(plan_id, finding_type='pr-comment')
    keys: set[tuple[str, str]] = set()
    for finding in result.get('findings') or []:
        match = _COMMENT_ID_DETAIL.search(finding.get('detail') or '')
        if match:
            keys.add((finding.get('bot_kind') or '', match.group('id')))
    return keys


def cmd_fetch_findings(args):
    """Producer-side FIND verb: fetch + pre-filter + file one finding per surviving comment.

    Pre-filters applied in order (both contribute to ``count_skipped_noise``):
    1. Already-resolved threads — skipped silently; the thread owner addressed them.
    2. Obvious text noise — matched via ``_is_obvious_noise`` (lgtm, bot sigs, etc.).

    Containment: the untrusted comment ``body`` is quarantined under
    ``raw_input.{body}`` — never embedded raw in the top-level ``detail``. The
    ``detail`` carries only trusted, producer-built structured metadata
    (pr_number, kind, author, thread_id, comment_id, path, line) so the triage
    read surface stays clean-by-construction until the batched
    ``manage-findings ingest`` pass promotes the validated body.

    Fail-loud: returns a typed ``unconfigured`` status (not a silent success)
    when GitHub is not authenticated. ``count_fetched`` vs ``count_stored``
    mismatches are recorded as a ``qgate`` finding with title prefix
    ``(producer-mismatch)`` so the LLM sees them in ``manage-findings qgate list``.
    """
    from _findings_core import (
        add_finding,
        add_qgate_finding,
        query_findings,
    )

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

    # enabled-bots producer filter: --enabled-bots carries a comma-joined set of
    # enabled bot_kinds, split at read time. When the flag is omitted the value
    # is None and the filter is disabled (every comment is considered). When
    # supplied — even as an empty string, which yields an empty enabled set and
    # thus disables ALL bots — a comment whose derived bot_kind is non-empty and
    # NOT in the set files no finding. Human comments (bot_kind is None) are
    # never filtered; the gate is bot-scoped.
    enabled_bots_raw = getattr(args, 'enabled_bots', None)
    enabled_bots_set: set[str] | None = None
    if enabled_bots_raw is not None:
        enabled_bots_set = {b.strip() for b in enabled_bots_raw.split(',') if b.strip()}

    # Fail-loud config guard — an unconfigured provider must NOT report a silent
    # zero-findings success.
    is_auth, auth_err = _github.check_auth()
    if not is_auth:
        return _unconfigured_result('fetch_findings', auth_err)

    fetch_result = fetch_comments(pr_number, unresolved_only=False)
    if fetch_result.get('status') != 'success':
        return fetch_result

    raw_comments: list[dict] = fetch_result.get('comments') or []
    count_fetched = len(raw_comments)

    # Cross-iteration phantom-loop guard: a resolution from a prior finalize
    # iteration cannot always be matched back to the comment on the next fetch
    # (``review_body`` comments carry no ``thread_id``, and even thread-bearing
    # bot comments can re-surface when HEAD advances). Without a dedup the
    # resolved comment re-enters as a fresh pending finding every time HEAD
    # advances, producing an endless finalize loop. Build the set of
    # ``(bot_kind, comment_id)`` keys already recorded as ``pr-comment``
    # findings (regardless of resolution state) and skip any comment — from any
    # bot kind, thread-bearing or not — whose key is already present.
    existing_comment_keys = _existing_pr_comment_keys(query_findings, plan_id)

    # Stamp every finding with the PR HEAD SHA at ingestion time so re-review
    # matching can tell whether HEAD has advanced past the reviewed commit.
    # Fetched once for the whole batch (empty string on any failure path — the
    # field is then simply omitted from the record).
    reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)

    stored_hashes: list[str] = []
    skipped_noise = 0
    skipped_duplicate = 0
    skipped_disabled = 0
    store_failures: list[str] = []

    for comment in raw_comments:
        # Pre-filter 1: already-resolved threads — skip silently (not noise,
        # not a finding; the thread owner already addressed the comment).
        if comment.get('resolved'):
            skipped_noise += 1
            continue

        author = comment.get('author') or 'unknown'

        # Derive bot_kind from the comment author login (coderabbitai ->
        # coderabbit, gemini-code-assist -> gemini); a human author resolves to
        # None. Computed BEFORE the noise pre-filter (so per-bot ignore patterns
        # apply) AND before the dedup check (so the cross-iteration guard can key
        # on (bot_kind, comment_id)).
        bot_kind = bot_kind_for_author(author)

        # Pre-filter 2: obvious noise — the shared acknowledgment/automation
        # regexes plus, for a known reviewer bot, that bot's per-registry literal
        # ignore markers (walkthrough headings, marketing footers, no-op reviews).
        body = comment.get('body') or ''
        if _is_obvious_noise(body, bot_kind):
            skipped_noise += 1
            continue

        kind = comment.get('kind') or 'inline'
        thread_id = comment.get('thread_id') or ''
        path = comment.get('path') or None
        line = comment.get('line') or None
        comment_id = comment.get('id') or 'unknown'

        # Pre-filter 2b: enabled-bots producer filter. When --enabled-bots was
        # supplied, a comment whose bot_kind is non-empty and NOT in the enabled
        # set files no finding (its bot is disabled for this plan/flow). Human
        # comments (bot_kind is None) always pass — the gate is bot-scoped. A
        # disabled bot files nothing, so its re-review is transitively
        # suppressed (no findings -> no re-review trigger).
        if enabled_bots_set is not None and bot_kind and bot_kind not in enabled_bots_set:
            skipped_disabled += 1
            continue

        # Pre-filter 3: cross-iteration dedup keyed on (bot_kind, comment_id)
        # for ALL bot kinds, thread-bearing and thread_id-less alike. A comment
        # already staged in a prior iteration MUST NOT re-surface as a new
        # pending finding when HEAD advances. Dropping the earlier
        # ``not thread_id`` restriction closes the same phantom loop for
        # thread-bearing bot comments, and pairing the id with bot_kind avoids a
        # collision between two distinct bots reusing a numeric comment id.
        if (bot_kind or '', comment_id) in existing_comment_keys:
            skipped_duplicate += 1
            continue

        # Build a stable, deterministic title that disambiguates same-author
        # comments on the same file. Only trusted, producer-built structured
        # metadata goes in ``detail``; the untrusted comment body is quarantined
        # under ``raw_input.{body}`` so the top-level triage read surface never
        # sees un-validated free-text.
        location_suffix = f' @ {path}:{line}' if path and line else ''
        title = f'PR #{pr_number} {kind} comment by {author}{location_suffix} ({comment_id})'

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

        # ``line`` may be 0 from the GraphQL fallback for review-body /
        # issue-comment kinds — pass None in that case to keep the finding
        # record clean.
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
            author=author,
            kind=kind,
            reviewed_commit_sha=reviewed_commit_sha or None,
            bot_kind=bot_kind,
            raw_input={'body': body},
        )
        if add_result.get('status') == 'success':
            stored_hashes.append(add_result.get('hash_id', ''))
        else:
            store_failures.append(comment_id)

    count_stored = len(stored_hashes)
    # Duplicates skipped by the cross-iteration guard and comments skipped by the
    # enabled-bots filter are both legitimate non-stores, so they drop out of
    # expected_stored alongside the noise skips — otherwise every deduped or
    # disabled-bot comment would spuriously trip the producer-mismatch Q-Gate.
    expected_stored = count_fetched - skipped_noise - skipped_duplicate - skipped_disabled

    qgate_hash: str | None = None
    if count_stored != expected_stored:
        # Producer-side mismatch — surfaced as a Q-Gate finding so the LLM
        # picks it up in the standard query path. Phase ``5-execute`` is the
        # canonical phase for execution-time producer issues.
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
            title=f'(producer-mismatch) github_pr fetch_findings PR #{pr_number}',
            detail=mismatch_detail,
        )
        qgate_hash = qgate_result.get('hash_id')

    return {
        'status': 'success',
        'operation': 'fetch_findings',
        'provider': 'github',
        'pr_number': pr_number,
        'plan_id': plan_id,
        'count_fetched': count_fetched,
        'count_skipped_noise': skipped_noise,
        'count_skipped_duplicate': skipped_duplicate,
        'count_skipped_disabled': skipped_disabled,
        'count_stored': count_stored,
        'stored_hash_ids': stored_hashes,
        'producer_mismatch_hash_id': qgate_hash,
    }


# ============================================================================
# BOT_COMPLETION SUBCOMMAND (read a named bot's check-run completion state)
# ============================================================================

# Check states gh reports for an in-flight (not-yet-concluded) check-run. A check
# whose state is none of these — and whose bucket is not 'pending' — has reached a
# terminal conclusion (SUCCESS / FAILURE / …), so the bot's review pass is done.
_IN_PROGRESS_CHECK_STATES = frozenset({'IN_PROGRESS', 'QUEUED', 'PENDING', 'WAITING', 'REQUESTED'})


def cmd_bot_completion(args):
    """Read the named bot's most-recent check-run completion state for the PR HEAD.

    Pure provider read — no triage, no LLM. Given ``--pr-number`` and
    ``--bot-kind``, it resolves the bot's ``completion_check_name`` from the
    registry, then queries the PR's checks and reports whether that check is
    still running or has concluded — so the ``automatic-review`` wait step can
    await a slow bot instead of racing a fixed buffer.

    Returns ``{status, in_progress, completed}``:

    - ``completed: true`` — the named check exists AND has a terminal conclusion.
    - ``in_progress: true`` — the named check exists AND is still running/queued.
    - A bot whose registry ``completion_check_name`` is empty/absent (declares no
      completion check-run) yields status ``no_check_name`` with both flags
      ``false`` — the caller falls back to the ``review_bot_buffer_seconds`` wait.
    - A check name absent from the PR's checks (not posted yet, or no checks at
      all) yields status ``not_found`` with both flags ``false`` — the caller
      keeps polling within its bound.

    Fail-loud: returns a typed ``unconfigured`` status when GitHub is not
    authenticated.
    """
    pr_number: int = args.pr_number
    bot_kind: str = getattr(args, 'bot_kind', '') or ''
    check_name: str = bot_registry.completion_check_name(bot_kind)

    is_auth, auth_err = _github.check_auth()
    if not is_auth:
        return _unconfigured_result('bot_completion', auth_err)

    # A bot with no completion check-run has an empty registry marker. Report
    # neither flag so the caller does not spin polling a check that never appears
    # — it falls back to the review_bot_buffer_seconds wait instead.
    if not check_name:
        return {
            'status': 'no_check_name',
            'operation': 'bot_completion',
            'provider': 'github',
            'pr_number': pr_number,
            'bot_kind': bot_kind,
            'check_name': '',
            'in_progress': False,
            'completed': False,
        }

    _rc, stdout, _stderr = _github.run_gh(['pr', 'checks', str(pr_number), '--json', 'name,state,bucket'])

    # gh emits the JSON array whenever checks exist (regardless of the rollup
    # exit code it also sets for pending/failing checks), and empty output when
    # the PR has no checks at all. Parse whatever JSON is present; empty output
    # leaves the check list empty, so the named check resolves to ``not_found``.
    checks: list = []
    stdout_stripped = stdout.strip()
    if stdout_stripped:
        try:
            parsed = json.loads(stdout_stripped)
        except json.JSONDecodeError:
            return make_error(
                f'could not parse gh pr checks output: {stdout_stripped[:100]}',
                code=ErrorCode.FETCH_FAILURE,
            )
        if isinstance(parsed, list):
            checks = parsed

    matched = next(
        (c for c in checks if isinstance(c, dict) and c.get('name') == check_name),
        None,
    )
    if matched is None:
        return {
            'status': 'not_found',
            'operation': 'bot_completion',
            'provider': 'github',
            'pr_number': pr_number,
            'bot_kind': bot_kind,
            'check_name': check_name,
            'in_progress': False,
            'completed': False,
        }

    state = (matched.get('state') or '').upper()
    bucket = (matched.get('bucket') or '').lower()
    in_progress = bucket == 'pending' or state in _IN_PROGRESS_CHECK_STATES
    completed = not in_progress
    return {
        'status': state.lower() or bucket or 'unknown',
        'operation': 'bot_completion',
        'provider': 'github',
        'pr_number': pr_number,
        'bot_kind': bot_kind,
        'check_name': check_name,
        'in_progress': in_progress,
        'completed': completed,
    }


# ============================================================================
# POST_RESPONSES SUBCOMMAND (apply triaged dispositions back to the PR)
# ============================================================================


def _thread_id_from_detail(detail: str | None) -> str:
    """Extract the ``thread_id`` value from a pr-comment finding's detail block."""
    match = _THREAD_ID_DETAIL.search(detail or '')
    return match.group('id') if match else ''


def cmd_post_responses(args):
    """RESPOND verb: apply already-decided triage dispositions back to the PR.

    Reads every ``pr-comment`` finding whose ``resolution`` is a terminal triage
    disposition (``_RESPONDABLE_RESOLUTIONS``) and that carries a ``thread_id``,
    and — keyed by each finding's own ``hash_id`` (never positional pairing) —
    posts the finding's ``resolution_detail``
    as a thread-reply then resolves the thread. This verb makes NO triage
    decision; it only transmits decisions the triage pass already recorded.

    Fail-loud: returns a typed ``unconfigured`` status when GitHub is not
    authenticated. A finding without a ``resolution_detail`` or ``thread_id`` is
    skipped (recorded in ``skipped``), never guessed at.
    """
    from _findings_core import query_findings

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

    is_auth, auth_err = _github.check_auth()
    if not is_auth:
        return _unconfigured_result('post_responses', auth_err)

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

        # Reply carrying the recorded disposition, then resolve — keyed by this
        # finding's own thread_id (relational, not positional).
        rc, _data, err = _github.run_graphql(THREAD_REPLY_MUTATION, {'threadId': thread_id, 'body': reply_body})
        if rc != 0:
            failures.append({'hash_id': hash_id, 'thread_id': thread_id, 'error': f'thread-reply failed: {err}'})
            continue
        rc2, _data2, err2 = _github.run_graphql(RESOLVE_THREAD_MUTATION, {'threadId': thread_id})
        if rc2 != 0:
            failures.append({'hash_id': hash_id, 'thread_id': thread_id, 'error': f'resolve-thread failed: {err2}'})
            continue
        responded.append({'hash_id': hash_id, 'thread_id': thread_id})

    return {
        'status': 'success',
        'operation': 'post_responses',
        'provider': 'github',
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
    # to every gh subprocess via run_cli's process-global default.
    project_dir, remaining = extract_routing_args(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = create_workflow_cli(
        description='PR workflow operations',
        epilog="""
Examples:
  github_pr.py fetch-comments --pr 123
  github_pr.py fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN
  github_pr.py post_responses --pr-number 123 --plan-id EXAMPLE-PLAN
""",
        subcommands=[
            {
                'name': 'fetch-comments',
                'help': 'Fetch PR review comments (raw)',
                'handler': cmd_fetch_comments,
                'args': [
                    {'flags': ['--pr'], 'type': int, 'help': "PR number (default: current branch's PR)"},
                    {'flags': ['--unresolved-only'], 'action': 'store_true', 'help': 'Only return unresolved comments'},
                ],
            },
            {
                'name': 'fetch_findings',
                'help': 'FIND: fetch + pre-filter + file one pr-comment finding per surviving comment (body quarantined under raw_input)',
                'handler': cmd_fetch_findings,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'PR number'},
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                    {
                        'flags': ['--enabled-bots'],
                        'dest': 'enabled_bots',
                        'help': (
                            'Comma-joined enabled bot_kinds (e.g. "coderabbit,sourcery,gemini"). When '
                            'supplied, a comment whose derived bot_kind is non-empty and NOT in this set '
                            'files no finding — its bot is disabled for this plan/flow, so its re-review is '
                            'transitively suppressed. Human comments (bot_kind is None) always pass. Omit '
                            'the flag to disable the filter entirely (all comments considered).'
                        ),
                    },
                ],
            },
            {
                'name': 'post_responses',
                'help': 'RESPOND: apply triaged dispositions (thread-reply + resolve-thread) back to the PR, keyed by hash_id',
                'handler': cmd_post_responses,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'PR number'},
                    {'flags': ['--plan-id'], 'dest': 'plan_id', 'required': True, 'help': 'Plan ID for finding store'},
                ],
            },
            {
                'name': 'bot_completion',
                'help': "READ: report a bot's check-run completion state ({status, in_progress, completed}) for the PR HEAD",
                'handler': cmd_bot_completion,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'PR number'},
                    {
                        'flags': ['--bot-kind'],
                        'dest': 'bot_kind',
                        'required': True,
                        'help': (
                            'Reviewer bot_kind (e.g. coderabbit). Its registry completion_check_name is '
                            'resolved internally; a bot with an empty completion_check_name reports status '
                            'no_check_name so the caller falls back to the review_bot_buffer_seconds wait.'
                        ),
                    },
                ],
            },
        ],
    )
    args = parser.parse_args()
    from triage_helpers import print_toon as _output_toon

    return _output_toon(args.func(args))


if __name__ == '__main__':
    safe_main(main)()
