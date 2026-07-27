#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""GitHub bot_kind-keyed re-review strategy registry.

Closes the post-merge re-review gap: when a HEAD-advancing branch operation in
phase-6-finalize (branch-cleanup rebase/force-push, or a phase-5 loop-back fix
commit) leaves new commits unreviewed by automated bots, this registry requests
a fresh bot review for the new HEAD and polls until a review lands for it.

The registry is ``bot_kind``-keyed with a strict two-method contract — no
speculative extensibility:

    request_fresh_review(pr_number, push_time) -> trigger_time
    await_fresh_review(pr_number, head_sha, trigger_time) -> envelope

Data-not-code: there is ONE generic strategy, parameterized by the per-bot
trigger comment loaded from the registry (``bot_registry.trigger_comment``).
``request_fresh_review`` posts that bot's explicit trigger comment and returns
the comment-post time; the trigger comment is the only thing that varies between
bots, and it is data (each bot's ``trigger_comment`` in
``automatic-review/standards/{bot_kind}.md``), not a per-bot subclass. The
explicit comment is the reliable trigger for the new HEAD — a bot's incremental
auto-review on push can be debounced or skipped on a force-push and does not
auto-fire at all for some bots.

``await_fresh_review`` is identical for every bot and is satisfied by EITHER of
two completion signals, checked in that order of strength:

1. A **review** whose reviewed commit SHA matches ``head_sha`` AND whose
   ``submittedAt > trigger_time``. Preferred, and reported as
   ``matched_signal: review`` with ``head_sha_verified: true``.
2. An **issue comment** authored by the awaited ``bot_kind`` whose later of
   ``updated_at`` / ``created_at`` post-dates ``trigger_time``. Reported as
   ``matched_signal: issue_comment`` with ``head_sha_verified: false`` — a
   comment carries no reviewed-commit SHA, so it establishes that the bot
   responded, NOT that it reviewed the new HEAD.

BOTH discriminators additionally reject a **refusal notice** — a comment or a
review body a bot posts to say it could NOT review — using the same TWO-LAYER
rule the producer pre-filter applies: the awaited bot's registry
``ignore_patterns`` (case-sensitive substring containment) first, then the
structural ``_is_rate_limit_notice`` fallback for an unknown/unregistered bot or
a phrasing not yet captured as data. A refusal is the bot talking about itself,
never evidence that the new HEAD was reviewed. Accepted tradeoff: a genuine
review or comment whose body happens to contain an ``ignore_patterns`` substring
is skipped and surfaces as a timeout — deliberate, because a truthful
``matched: false`` / ``timed_out: true`` is recoverable, whereas a false
``head_sha_verified: true`` silently asserts review coverage that never happened.

The second signal exists because a bot that posts its review as one persistent
issue comment and submits no review object could otherwise only ever time out.
It is generic: no bot is named in code, and every bot's comment is equally valid
evidence that it responded. The envelope names which signal fired so the caller
is never misled about the strength of the evidence.

The bot-kind set, the login->bot_kind map, and each trigger comment are all
DERIVED from the registry (``bot_registry``), whose data source is the per-bot
standards docs. ``BOT_KINDS`` (imported from ``_findings_core``, itself derived
from the same registry) remains the argparse ``choices=`` surface, so a new bot
is added by dropping a ``standards/{bot_kind}.md`` doc — no code change here.

Usage:
    github_re_review.py re-review --pr-number N --bot-kind coderabbit \
        --head-sha SHA --push-time ISO8601 [--timeout SECONDS] --plan-id PLAN_ID

Output: TOON format
"""

import argparse
import sys
from datetime import UTC, datetime

import bot_registry
import github_ops as _github
from _findings_core import BOT_KINDS
from _github_pr import _is_rate_limit_notice
from ci_base import (
    DEFAULT_CI_INTERVAL,
    DEFAULT_CI_TIMEOUT,
    extract_routing_args,
    make_error,
    poll_until,
    register_subcommands,
    safe_main,
    serialize_toon,
    set_default_cwd,
)

register_subcommands({'re-review'})


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string (used as the post-comment time)."""
    return datetime.now(UTC).isoformat()


def _parse_iso(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp; return None on any malformed input.

    GitHub timestamps end in ``Z``; normalize to ``+00:00`` for fromisoformat.
    Timezone-naive datetimes are normalized to UTC so comparisons with
    timezone-aware GitHub API timestamps never raise a TypeError.
    """
    if not value:
        return None
    normalized = value.replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


# ---------------------------------------------------------------------------
# Strategy registry — one generic strategy parameterized by the trigger comment
# ---------------------------------------------------------------------------


class _ReReviewStrategy:
    """Generic re-review strategy parameterized by a bot's trigger comment.

    A single class serves every bot: ``request_fresh_review`` posts the
    ``trigger_comment`` this instance was built with (the bot's data-driven
    trigger from the registry) and returns the comment-post time;
    ``await_fresh_review`` is bot-independent. No per-bot subclass exists — the
    only thing that differs between bots is the trigger string, which is data.
    """

    def __init__(self, trigger_comment: str) -> None:
        self.trigger_comment = trigger_comment

    def request_fresh_review(self, pr_number: int | str, push_time: str) -> dict:
        """Post this bot's explicit trigger comment; return ``{status, trigger_time}``.

        The returned ``trigger_time`` is the comment-post time — the lower bound
        a fresh review's ``submittedAt`` must exceed for ``await_fresh_review``
        to match. ``push_time`` is unused (retained for routing uniformity): the
        trigger time is always the comment-post time, never the push time.
        """
        post_result = _github.post_pr_comment(pr_number, self.trigger_comment)
        if post_result.get('status') != 'success':
            return make_error('request_fresh_review', post_result.get('error', 'failed to post trigger comment'))
        return {'status': 'success', 'trigger_time': _now_iso()}

    def await_fresh_review(
        self,
        pr_number: int | str,
        head_sha: str,
        trigger_time: str,
        *,
        bot_kind: str | None = None,
        timeout: int = DEFAULT_CI_TIMEOUT,
        interval: int = DEFAULT_CI_INTERVAL,
    ) -> dict:
        """Poll until either completion signal for ``bot_kind`` is observed.

        Identical for every bot. The review match is checked first and wins when
        both are present. Returns a TOON envelope carrying ``matched``,
        ``matched_signal`` (``review`` | ``issue_comment`` | empty when
        unmatched), the matched record, and ``head_sha_verified`` — ``true``
        only on the review path.

        Args:
            pr_number: PR to poll.
            head_sha: Commit the fresh review must have reviewed (review path).
            trigger_time: ISO-8601 lower bound both signals must post-date.
            bot_kind: The awaited bot. Required for the comment path — without
                it there is no authorship to gate on, so only the review path
                can match (fail-closed, never "any comment counts").
            timeout: Poll budget in seconds.
            interval: Seconds between polls.
        """
        trigger_dt = _parse_iso(trigger_time)
        if trigger_dt is None:
            return make_error('await_fresh_review', f'Invalid trigger_time: {trigger_time!r}')

        def _check() -> tuple[bool, dict]:
            envelope = _github.fetch_pr_reviews_with_commits(pr_number)
            if envelope.get('status') != 'success':
                return False, {'error': envelope.get('error', 'fetch failed')}
            comments: list[dict] = []
            if bot_kind:
                comment_envelope = _github.fetch_pr_comments_data(int(pr_number))
                if comment_envelope.get('status') == 'success':
                    comments = comment_envelope.get('comments') or []
            return True, {**envelope, 'comments': comments}

        def _resolve(data: dict) -> tuple[str, dict | None]:
            """Return ``(matched_signal, record)`` for the strongest signal present."""
            review = self._match_review(data.get('reviews') or [], head_sha, trigger_dt, bot_kind)
            if review is not None:
                return 'review', review
            comment = self._match_bot_comment(data.get('comments') or [], bot_kind, trigger_dt)
            if comment is not None:
                return 'issue_comment', comment
            return '', None

        def _is_complete(data: dict) -> bool:
            return _resolve(data)[1] is not None

        poll_result = poll_until(_check, _is_complete, timeout=timeout, interval=interval)

        if poll_result.get('error'):
            return make_error('await_fresh_review', poll_result['error'])

        matched_signal, record = _resolve(poll_result.get('last_data') or {})
        return {
            'status': 'success',
            'operation': 'await_fresh_review',
            'pr_number': pr_number,
            'head_sha': head_sha,
            'trigger_time': trigger_time,
            'matched': record is not None,
            'matched_signal': matched_signal,
            'matched_review': record if matched_signal == 'review' else {},
            'matched_comment': record if matched_signal == 'issue_comment' else {},
            # An issue comment carries no reviewed-commit SHA, so it cannot prove
            # the new HEAD was reviewed. Only the review path verifies that.
            'head_sha_verified': matched_signal == 'review',
            'timed_out': poll_result.get('timed_out', False),
            'polls': poll_result.get('polls', 0),
            'duration_sec': poll_result.get('duration_sec', 0),
        }

    @staticmethod
    def _is_refusal(body: str, bot_kind: str | None) -> bool:
        """Return True when ``body`` is a refusal notice for the awaited ``bot_kind``.

        The single TWO-LAYER rule shared by both discriminator paths (and by the
        producer pre-filter): the awaited bot's registry ``ignore_patterns``
        (case-sensitive substring containment) first, then the structural
        ``_is_rate_limit_notice`` fallback for an unknown/unregistered bot or a
        phrasing not yet captured as data. When ``bot_kind`` is ``None`` the data
        layer cannot fire and only the structural test applies.

        Accepted tradeoff: a genuine review or comment whose body happens to
        contain an ``ignore_patterns`` substring is skipped and reported as a
        timeout. That is deliberate — a truthful ``matched: false`` /
        ``timed_out: true`` is recoverable, whereas a false ``head_sha_verified:
        true`` / "the bot responded" silently asserts review coverage that never
        happened.
        """
        if bot_kind and any(marker in body for marker in bot_registry.ignore_patterns(bot_kind)):
            return True
        return _is_rate_limit_notice(body)

    @staticmethod
    def _match_review(
        reviews: list[dict], head_sha: str, trigger_dt: datetime | None, bot_kind: str | None
    ) -> dict | None:
        """Return the first genuine review matching ``head_sha`` and post-dating ``trigger_dt``.

        A review matches when its reviewed commit SHA equals ``head_sha``, its
        ``submitted_at`` is strictly after ``trigger_dt``, AND its body is not a
        refusal notice (:meth:`_is_refusal`). A review with an unparseable
        ``submitted_at`` never matches (fail-closed). When ``trigger_dt`` is
        ``None`` (invalid or unparseable trigger time) the comparison is
        fail-closed — no review matches, preventing stale reviews from being
        incorrectly accepted. There is deliberately NO author gate on this path —
        the SHA match already establishes provenance.
        """
        if trigger_dt is None:
            return None
        for review in reviews:
            if review.get('commit_sha') != head_sha:
                continue
            submitted_dt = _parse_iso(review.get('submitted_at') or '')
            if submitted_dt is None:
                continue
            if submitted_dt <= trigger_dt:
                continue
            if _ReReviewStrategy._is_refusal(review.get('body') or '', bot_kind):
                continue
            return review
        return None

    @staticmethod
    def _match_bot_comment(comments: list[dict], bot_kind: str | None, trigger_dt: datetime | None) -> dict | None:
        """Return the first comment from ``bot_kind`` post-dating ``trigger_dt``.

        A comment matches when ALL of the following hold:

        - ``bot_kind`` is set and the comment's author resolves through
          :func:`bot_kind_for_author` to exactly that kind — a human author, or a
          different bot, never matches;
        - the LATER of its ``updated_at`` and ``created_at`` is strictly after
          ``trigger_dt``. Taking the later of the two is what makes an EDITED
          persistent comment count: such a bot updates one comment in place, so
          ``created_at`` stops advancing after the first review;
        - it is not a refusal notice (:meth:`_is_refusal`) — a "the bot could not
          review" comment is the bot talking about itself, not a completed review.

        Fail-closed on every missing input: no ``bot_kind``, no ``trigger_dt``,
        or an unparseable timestamp yields no match.
        """
        if not bot_kind or trigger_dt is None:
            return None
        for comment in comments:
            if bot_kind_for_author(comment.get('author')) != bot_kind:
                continue
            if _ReReviewStrategy._is_refusal(comment.get('body') or '', bot_kind):
                continue
            stamps = [
                dt
                for dt in (_parse_iso(comment.get('updated_at') or ''), _parse_iso(comment.get('created_at') or ''))
                if dt is not None
            ]
            if not stamps:
                continue
            if max(stamps) > trigger_dt:
                return comment
        return None


# One generic strategy instance per registered bot_kind, each parameterized by
# that bot's trigger comment loaded from the registry. Built from data — there is
# no per-bot class and no hard-coded bot list.
_STRATEGIES: dict[str, _ReReviewStrategy] = {
    bot_kind: _ReReviewStrategy(bot_registry.trigger_comment(bot_kind))
    for bot_kind in bot_registry.bot_kinds()
}

# Map a GitHub review-author login to its canonical ``bot_kind`` key, DERIVED
# from the registry (each bot's ``author_login`` in its standards doc). The login
# is the bot's account name (e.g. ``coderabbitai``, ``cuioss-review-bot``); the
# ``bot_kind`` is the registry key those accounts resolve to. This is the single
# source of truth for the login -> bot_kind correspondence — producers
# (``github_pr.py`` comments-stage) import ``bot_kind_for_author`` rather than
# inline-copying the mapping.
_AUTHOR_LOGIN_TO_BOT_KIND: dict[str, str] = bot_registry.login_to_bot_kind()


def resolve_strategy(bot_kind: str) -> _ReReviewStrategy | None:
    """Resolve a strategy by ``bot_kind``; None for an unknown key."""
    return _STRATEGIES.get(bot_kind)


def bot_kind_for_author(author_login: str | None) -> str | None:
    """Resolve a review-author login to its canonical ``bot_kind`` key.

    Returns the ``bot_kind`` (one of :data:`BOT_KINDS`) for a known reviewer-bot
    login, or ``None`` for a human author or any login not in the registry. The
    lookup is case-insensitive to tolerate login-casing drift; the bot-account
    suffix ``[bot]`` (present on some GraphQL author logins) is stripped before
    matching.
    """
    if not author_login:
        return None
    normalized = author_login.lower()
    if normalized.endswith('[bot]'):
        normalized = normalized[: -len('[bot]')]
    return _AUTHOR_LOGIN_TO_BOT_KIND.get(normalized)


# ---------------------------------------------------------------------------
# Registered trigger-comment recognizer (shared with the producer pre-filter)
# ---------------------------------------------------------------------------
#
# Every bot's re-review trigger comment — the exact string ``_ReReviewStrategy``
# posts to request a fresh review — is a registered value in the registry
# (``bot_registry.trigger_comment`` over ``bot_registry.bot_kinds``). The
# producer pre-filter (``github_pr.fetch_findings``) drops a surviving comment
# whose whitespace-stripped body EQUALS one of these registered triggers: such a
# comment is a pipeline-authored re-review request this workflow itself posted,
# never reviewer feedback. Recognition and posting therefore DERIVE from the same
# registry source — a trigger string added to a ``standards/{bot_kind}.md`` doc
# is both posted and recognised with no second code edit. Empty triggers (a bot
# that declares none) are excluded so a whitespace-only body never matches.
_REGISTERED_TRIGGER_COMMENTS: frozenset[str] = frozenset(
    trigger.strip()
    for trigger in (bot_registry.trigger_comment(bot_kind) for bot_kind in bot_registry.bot_kinds())
    if trigger.strip()
)


def is_registered_trigger_comment(body: str) -> bool:
    """Return True when ``body`` is exactly a registered bot re-review trigger.

    The comment body is whitespace-stripped and compared for EQUALITY (not
    substring containment) against :data:`_REGISTERED_TRIGGER_COMMENTS`. An exact
    match means the comment is a pipeline-authored re-review request this workflow
    posted — noise for the pre-merge finding pass, not reviewer feedback.
    Substring matching is deliberately avoided so a genuine review comment that
    merely quotes a trigger string is not misclassified.
    """
    return body.strip() in _REGISTERED_TRIGGER_COMMENTS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_re_review(args: argparse.Namespace) -> dict:
    """Resolve the strategy, request a fresh review, then await it for HEAD."""
    strategy = resolve_strategy(args.bot_kind)
    if strategy is None:
        return make_error('re_review', f'Unknown bot_kind: {args.bot_kind}. Must be one of {BOT_KINDS}')

    request_result = strategy.request_fresh_review(args.pr_number, args.push_time)
    if request_result.get('status') != 'success':
        return request_result

    trigger_time = request_result['trigger_time']
    await_result = strategy.await_fresh_review(
        args.pr_number,
        args.head_sha,
        trigger_time,
        bot_kind=args.bot_kind,
        timeout=args.timeout,
    )
    if await_result.get('status') != 'success':
        return await_result

    await_result['bot_kind'] = args.bot_kind
    return await_result


def main() -> int:
    project_dir, remaining = extract_routing_args(sys.argv[1:])
    sys.argv = [sys.argv[0], *remaining]
    if project_dir is not None:
        set_default_cwd(project_dir)

    parser = argparse.ArgumentParser(description='GitHub bot_kind-keyed re-review strategy registry', allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='command', required=True)

    re_review = subparsers.add_parser('re-review', help='Request and await a fresh bot review for the current HEAD', allow_abbrev=False)
    re_review.add_argument('--pr-number', type=int, required=True, help='PR number')
    re_review.add_argument('--bot-kind', choices=BOT_KINDS, required=True, help='Reviewer bot identity key')
    re_review.add_argument('--head-sha', required=True, help='Current HEAD SHA the fresh review must match')
    re_review.add_argument('--push-time', required=True, help='ISO-8601 push time (retained for routing uniformity; every registered bot posts an explicit trigger comment)')
    re_review.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_CI_TIMEOUT,
        help=f'Seconds to await the fresh review before timing out (default: {DEFAULT_CI_TIMEOUT})',
    )
    re_review.add_argument('--plan-id', help='Plan identifier (accepted for routing uniformity)')

    args = parser.parse_args()

    handlers = {'re-review': cmd_re_review}
    result = handlers[args.command](args)
    print(serialize_toon(result, table_separator='\t'))
    return 0


if __name__ == '__main__':
    safe_main(main)()
