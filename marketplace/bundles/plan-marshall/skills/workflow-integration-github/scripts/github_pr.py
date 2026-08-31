#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
GitHub PR workflow operations - two-verb findings contract (fetch_findings + post_responses) plus a bot_completion read verb.

The findings contract is exactly TWO pure, zero-LLM verbs — no triage judgment
lives here:

- ``fetch_findings`` fetches PR review comments, applies the keyword pre-filter
  from ``standards/comment-patterns.json`` to drop obvious noise, excludes the
  batched response body ``post_responses`` itself posts (recognized start-anchored
  on ``_SELF_RESPONSE_HEADING``, counted in ``count_skipped_self_response``), then
  files one ``pr-comment`` finding per surviving comment via ``manage-findings
  add``. The untrusted comment body is quarantined under ``raw_input.{body}``
  (never embedded raw in the top-level ``detail``); the batched ``manage-findings
  ingest`` pass promotes it to top-level only after ``validate_struct``. Because
  the self-response filter cannot be complete (a thread-bearing disposition whose
  resolve fails leaves an unresolved reply carrying no transmission shape), a
  bounded guard reports exhaustion as a ``(self-response-loop)`` Q-Gate finding
  rather than looping silently. The bound counts the CURRENT cycle's consecutive
  self-responses (``_current_cycle_self_response_count``), not the PR's lifetime
  total, so a PR that merely completed several converged triage rounds is never
  reported as looping.
- ``post_responses`` applies already-decided triage dispositions back to the
  provider, keyed by each finding's own ``hash_id`` (no positional pairing), via
  a three-way disposition that never loses a decision: a finding with no
  ``resolution_detail`` is ``skipped`` (nothing to transmit); a thread-bearing
  finding gets the thread-reply-then-resolve path; and a thread-less finding
  whose disposition has a body is transmitted in ONE batched PR-level comment
  anchored on each source ``comment_id``. Anything that had something to say but
  could not be delivered lands in ``untransmitted`` and drives ``status:
  partial``. It reads only findings the triage pass already resolved.

Beside the findings contract sits one auxiliary provider read:

- ``bot_completion`` reports a named bot's check-run completion state
  (``{status, in_progress, completed}``) for the PR HEAD, so the
  ``automatic-review`` wait step can await a slow bot's IN_PROGRESS check to
  completion instead of racing a fixed buffer. Pure read — files no finding.
- ``pull_request_runs`` reports whether ANY ``pull_request``-event workflow run
  exists for the PR's head branch — the PR-WIDE observable behind the
  ``not_triggered`` participation state, where nothing ever ran on account of the
  PR so no bot could have published. An existing run that concluded ``skipped``
  keeps ``not_triggered`` false (the workflow WAS triggered); only the absence of
  any such run makes it true. Pure read — files no finding, and never reads
  ``mergeable_state``.

All verbs FAIL LOUD when GitHub is not configured: a typed ``unconfigured``
status, never a silent ``done`` no-op. LLM consumers query the ledger via
``manage-findings query --type pr-comment``.

Usage:
    github_pr.py fetch-comments [--pr <number>] [--unresolved-only]
    github_pr.py fetch_findings --pr-number <N> --plan-id <P> [--required-bots [<csv>]] [--optional-bots [<csv>]]
    github_pr.py post_responses --pr-number <N> --plan-id <P>
    github_pr.py bot_completion --pr-number <N> --bot-kind <kind>
    github_pr.py pull_request_runs --pr-number <N>
    github_pr.py --help

``fetch_findings``'s two classification list flags take an OPTIONAL value: each
may be supplied bare (the flag with no value at all), which reads as the empty
list — identical to omitting it. A caller interpolating an empty variable
therefore produces the empty-list reading rather than an argparse rejection.
Neither list admits or drops anything, so an empty list never changes what is
ingested; it only leaves every observed bot unclassified.

Subcommands:
    fetch-comments    Fetch PR review comments (raw, no filtering or storage)
    fetch_findings    Producer-side: fetch + pre-filter + file one pr-comment finding per surviving comment
    post_responses    Apply triaged dispositions (thread-reply + resolve-thread) back to the PR, keyed by hash_id
    bot_completion    Read a named bot's check-run completion state ({status, in_progress, completed}) for the PR HEAD
    pull_request_runs Read whether any pull_request-event workflow run exists for the PR (the not_triggered observable)

Examples:
    # Fetch raw comments
    github_pr.py fetch-comments --pr 123

    # Find stage (fetch, filter, file findings with quarantined raw_input)
    github_pr.py fetch_findings --pr-number 123 --plan-id EXAMPLE-PLAN

    # Respond stage (apply already-decided dispositions back to the PR)
    github_pr.py post_responses --pr-number 123 --plan-id EXAMPLE-PLAN
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import bot_registry
import github_ops as _github
from _github_pr import (
    REFUSAL_CAUSE_SIZE,
    REFUSAL_LAYER_ENUMERATIVE,
    REFUSAL_LAYER_REGISTRY,
    REFUSAL_LAYER_STRUCTURAL,
    RESOLVE_THREAD_MUTATION,
    THREAD_REPLY_MUTATION,
    _is_refusal_notice,
    _is_unrecognised_refusal,
    measure_diff_size,
    refusal_cause,
    refusal_layers,
    refusal_size_cap,
)
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
register_subcommands(
    {'fetch-comments', 'fetch_findings', 'post_responses', 'bot_completion', 'pull_request_runs'}
)

# Resolutions that are terminal triage dispositions — a pr-comment finding in one
# of these states has been decided by the triage pass and is eligible for a
# provider response. `pending` (still awaiting triage) is deliberately excluded.
_RESPONDABLE_RESOLUTIONS = frozenset({'fixed', 'suppressed', 'accepted', 'taken_into_account', 'rejected'})

# ============================================================================
# PRE-FILTER CONFIGURATION (shared defaults + per-bot additions)
# ============================================================================
#
# The producer noise pre-filter is a three-layer, data-not-code composition:
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
#   3. CONTENTLESS BOILERPLATE layer — each bot's ``contentless_review_markers``
#      and ``actionable_content_markers`` from the same registry. Unlike layer 2
#      this one is CONDITIONAL on the whole body: it drops a comment only when
#      EVERY ``contentless_review_markers`` entry is present AND no
#      ``actionable_content_markers`` entry is. It exists for a bot whose single
#      review comment carries both its findings and its clean-result assertions,
#      so no unconditional whole-body marker can express "this review found
#      nothing" without also dropping the reviews that found something. Empty
#      ``contentless_review_markers`` is the fail-closed default and the state
#      every bot that has not opted in is in.
#
# A surviving comment (matched by none of the three layers) becomes a
# ``pr-comment`` finding.

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


def _is_contentless_boilerplate(body: str, bot_kind: str | None) -> bool:
    """True if ``body`` is ``bot_kind``'s review boilerplate carrying no content.

    The predicate is a CONJUNCTION over the bot's registry
    ``contentless_review_markers`` vetoed by ANY ``actionable_content_markers``
    entry: every required marker must be present in the body, and no
    disqualifying marker may be. Both lists are literal substrings, stripped
    before matching so an incidentally-indented registry value still matches the
    raw body (the project's normalize-both-sides-of-a-registry-comparison rule).

    An empty ``contentless_review_markers`` short-circuits to ``False`` — the
    fail-closed default, and the state every bot that has not declared a clean
    shape is in. The conjunction is what keeps the drop safe: a body that
    deviates from the declared clean shape in ANY way (a missing marker, a
    changed marker, one actionable marker present) is left in place, so the
    predicate can only ever fail open.
    """
    kind = bot_kind or ''
    required = [m.strip() for m in bot_registry.contentless_review_markers(kind) if m.strip()]
    if not required:
        return False
    if not all(marker in body for marker in required):
        return False
    disqualifying = [m.strip() for m in bot_registry.actionable_content_markers(kind) if m.strip()]
    return not any(marker in body for marker in disqualifying)


def _is_obvious_noise(body: str, bot_kind: str | None = None) -> bool:
    """Pre-filter: True if the comment body is shared or per-bot noise.

    Three layers (see PRE-FILTER CONFIGURATION above):

    1. SHARED — the bot-agnostic ``ignore`` regexes (lgtm, approved, ``[bot]``
       signatures, …) matched case-insensitively against the lowered body.
    2. PER-BOT — when ``bot_kind`` is a known reviewer bot, that bot's registry
       ``ignore_patterns`` (literal whole-comment markers) matched as
       case-sensitive substrings against the raw body. These markers are exact
       fragments the bot emits on a *successful* review (a walkthrough heading, a
       marketing footer, a no-op review line), so only that bot's own comments are
       dropped.
    3. CONTENTLESS BOILERPLATE — ``_is_contentless_boilerplate``: that same bot's
       registry ``contentless_review_markers`` (ALL required) vetoed by any
       ``actionable_content_markers`` entry. Layer 2 cannot express this case: for
       a bot whose one comment carries both its findings and its clean-result
       assertions, an unconditional whole-body marker would drop the reviews that
       found something too.

    A layer-3 drop is counted in ``count_skipped_noise`` and given NO counter of
    its own, because it is routine successful-review boilerplate — the same class
    ``ignore_patterns`` already serves, differing only in being conditional on the
    whole body. That is unlike a REFUSAL (positive evidence the bot declined; its
    own ``count_skipped_refusal``) and unlike a SELF-RESPONSE (pipeline-authored
    re-ingestion; its own ``count_skipped_self_response``), both of which answer
    questions the noise count must not absorb.

    One further pipeline-noise class is folded in ahead of the three layers,
    reusing an existing data source rather than new patterns:

    - REGISTERED TRIGGER — a comment whose whitespace-stripped body EQUALS a
      registered bot re-review trigger (``github_re_review.is_registered_trigger_comment``,
      derived from ``bot_registry``) is a pipeline-authored re-review request this
      workflow itself posted, not reviewer feedback. Checked for every comment
      (bot- or human-authored), since the pipeline may post under either account.

    **A REFUSAL IS NOT NOISE AND NO ARM OF THE REFUSAL-RECOGNITION STACK IS
    CONSULTED HERE.** None of the arms named in ``_github_pr.REFUSAL_LAYERS`` runs
    inside this predicate — not the registry ``refusal_patterns`` arm, not the
    structural ``_github_pr._is_rate_limit_notice`` arm, and not the enumerative
    ``_github_pr._is_unrecognised_refusal`` arm. A refusal is positive evidence that
    a bot DECLINED to review, so it is classified by ``cmd_fetch_findings`` — the
    arms answerable before this filter run ahead of it via
    ``_github_pr._is_refusal_notice``, and the enumerative arm runs immediately
    AFTER it — and surfaced in ``refused_bots[]`` / ``unrecognised_refusal[]``. The
    completeness / quorum layer must SEE the refusal, not infer absence from
    silence. Folding ``refusal_patterns`` into this drop set collapsed exactly the
    distinction the two-field split was created for, and let a PR whose every
    required reviewer refused report a clean, complete review. ``ignore_patterns``
    and the contentless-marker pair belong here; no refusal-recognition arm does.

    The enumerative arm's position is the reason it is not folded in above rather
    than an accident of ordering: it must see a body this predicate has ALREADY
    declined, because a bot's own declared clean-review text would otherwise satisfy
    it.

    Used by ``fetch_findings`` to drop obvious automated/acknowledgment noise
    before each surviving comment is persisted as a ``pr-comment`` finding. This
    is intentionally permissive — the goal is only to skip the most obvious
    noise, not to make the final classification decision (that belongs to the LLM
    consumer). Human comments (``bot_kind is None``) are checked against the
    shared layer and the registered-trigger recognizer; the per-bot
    literal-marker layers stay reviewer-bot-scoped.
    """
    if not body:
        return True
    # Pipeline-authored re-review trigger comment (exact stripped-body match).
    if is_registered_trigger_comment(body):
        return True
    body_lower = body.lower()
    if any(p.search(body_lower) for p in _COMPILED_IGNORE):
        return True
    if bot_kind:
        if any(marker in body for marker in bot_registry.ignore_patterns(bot_kind)):
            return True
        return _is_contentless_boilerplate(body, bot_kind)
    return False


# The exact heading ``_build_batched_response_body`` emits as the literal first
# line of the batched PR-level comment ``post_responses`` posts for thread-less
# dispositions. The emitter and the ``_is_self_authored_response`` recognizer BOTH
# read this one constant, so the transmission shape and the shape that recognizes
# it cannot drift apart — a renamed heading would otherwise silently reopen the
# re-ingestion loop while every test still passed.
_SELF_RESPONSE_HEADING = '## Triage dispositions'

# How many CONSECUTIVE self-authored responses — responses belonging to the
# CURRENT, still-unconverged respond → re-fetch cycle — a single fetch may observe
# before the producer reports the loop as exhausted. Mirrors
# ``phase-6-finalize.max_iterations`` (3): three unbroken turns of respond →
# re-fetch without the comment set converging is not a slow convergence, it is a
# cycle. The guard is load-bearing beyond the filter because the filter cannot be
# complete — a thread-bearing disposition whose ``resolve_thread`` failed leaves
# an unresolved reply whose body is arbitrary ``resolution_detail`` text carrying
# no transmission shape at all, so only a bound can terminate it.
#
# The comparand is ``_current_cycle_self_response_count`` — the TRAILING run of
# self-responses — NOT the cumulative ``count_skipped_self_response`` over the
# PR's whole history. ``cmd_fetch_findings`` fetches with
# ``unresolved_only=False``, so the cumulative count spans every triage cycle the
# PR ever completed; comparing it against this bound made any PR that legitimately
# converged three times report a loop that was not running.
_SELF_RESPONSE_LOOP_BOUND = 3


def _is_self_authored_response(body: str) -> bool:
    """Pre-filter: True if ``body`` is the batched response ``post_responses`` posted.

    START-ANCHORED, never a substring search. ``post_responses`` transmits
    thread-less dispositions as a NEW PR-level comment authored by the repo-owner
    account (``bot_kind`` None, ``kind`` ``issue_comment``), which every other
    pre-filter stage misses: it is unresolved, it is not a refusal, no ``ignore``
    regex matches it, and the ``(bot_kind, comment_id)`` dedup cannot fire because
    each turn posts a comment with a NEW id. Without this stage the barrier
    re-ingests our own reply as a fresh unaddressed finding on every pass.

    The start anchor is the false-positive boundary and is load-bearing: a human
    comment that QUOTES the heading — as a blockquote (``> ## Triage
    dispositions``) or inside prose — is real reviewer feedback and MUST still be
    filed. Only leading whitespace is stripped before the prefix test, so a
    blockquote marker or any preceding prose leaves the body unmatched.

    This is deliberately NOT added to ``comment-patterns.json``: that file is the
    shared *acknowledgment-noise* layer, and a self-authored response is not noise
    — it is our own output. Folding a structural transmission-shape recognizer into
    the noise set would repeat exactly the mistake ``_is_obvious_noise``'s
    docstring warns against for refusals. It gets its own counter
    (``count_skipped_self_response``) for the same reason, following the
    established ``count_skipped_refusal`` precedent.
    """
    return body.lstrip().startswith(_SELF_RESPONSE_HEADING)


def _current_cycle_self_response_count(comments: list[dict]) -> int:
    """Count the self-responses belonging to the CURRENT, still-unconverged cycle.

    The bounded guard needs the number of unbroken respond → re-fetch turns in the
    cycle running RIGHT NOW, not the number of self-responses the PR accumulated
    over its lifetime. ``cmd_fetch_findings`` fetches with ``unresolved_only=False``,
    so a raw count spans every cycle the PR ever completed: a PR that legitimately
    converged three times carries three self-responses and would report a loop that
    is not running, filing a spurious ``(self-response-loop)`` Q-Gate finding long
    after every finding was resolved.

    The discriminator is CONSECUTIVENESS in time. A non-converging cycle posts
    self-response after self-response with nothing else in between — nobody else is
    speaking, which is precisely what "not converging" means. A converged cycle is
    always followed by fresh reviewer activity before the next cycle starts, so its
    self-responses sit BEHIND that activity. Counting only the trailing run
    therefore keeps the termination guarantee for a genuine loop while historical
    converged cycles stop counting as evidence of an active one.

    Two comment classes are transparent to the run — neither counts nor breaks it:

    - A **registered re-review trigger** (``is_registered_trigger_comment``) is
      pipeline-authored, exactly like the self-responses themselves. Letting it
      break the run would let the pipeline reset its own guard forever by
      interleaving trigger → response → trigger → response, masking the very loop
      class this bound exists to terminate.

    Everything else — any reviewer bot comment, any human comment — breaks the run:
    somebody other than this pipeline spoke, so the next self-response opens a new
    cycle rather than continuing the old one.

    Ordering is established here and is load-bearing: ``fetch_pr_comments_data``
    emits comments GROUPED BY KIND (inline threads, then review bodies, then issue
    comments), NOT chronologically. Self-responses are posted as ``issue_comment``
    and therefore always land in the last group, so scanning the provider list
    as-received would read every historical self-response as one contiguous tail
    and reproduce the exact false positive this function removes. Sorting by
    ``created_at`` first is what makes the trailing run mean "most recent in time".
    A comment whose ``created_at`` the provider omitted sorts as oldest and so
    cannot inflate the run; the stable sort preserves provider order among ties.

    Args:
        comments: The raw provider comment records for the PR.

    Returns:
        The number of consecutive most-recent self-authored responses.
    """
    ordered = sorted(comments, key=lambda c: str(c.get('created_at') or ''))
    count = 0
    for comment in reversed(ordered):
        body = str(comment.get('body') or '')
        if _is_self_authored_response(body):
            count += 1
            continue
        if is_registered_trigger_comment(body):
            continue
        break
    return count


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

# Matches the ``comment_id: <value>``, ``thread_id: <value>`` and ``kind: <value>``
# lines written into every pr-comment finding's ``detail`` block by
# cmd_fetch_findings.
#
# The value class requires a leading non-whitespace character (``\S``) and matches
# only horizontal whitespace around it (``[ \t]``), never ``\s`` (which spans
# newlines). This is load-bearing for ``thread_id``: a thread_id-less finding is
# written as the literal line ``thread_id: `` (empty value, trailing space). A
# newline-spanning ``\s*(?P<id>.+?)`` would capture the *next* detail line (or the
# trailing space) as a spurious truthy id, so ``post_responses`` would try to
# resolve a non-existent thread instead of correctly reporting the finding as
# undeliverable. The ``\S``-anchored, line-bounded value class yields no match for
# an empty value, so ``_detail_field`` returns ``''``.
_COMMENT_ID_DETAIL = re.compile(r'^comment_id:[ \t]*(?P<id>\S[^\n]*?)[ \t]*$', re.MULTILINE)
_THREAD_ID_DETAIL = re.compile(r'^thread_id:[ \t]*(?P<id>\S[^\n]*?)[ \t]*$', re.MULTILINE)
_KIND_DETAIL = re.compile(r'^kind:[ \t]*(?P<id>\S[^\n]*?)[ \t]*$', re.MULTILINE)
# The EDIT TERM — the third term of the cross-iteration filing dedup identity, stamped
# into every finding this producer stores so the key can be reconstructed from the store.
# A finding written before this term existed carries no such line and extracts ``''``,
# which is what makes a pre-upgrade row recognisable rather than merely different.
_EDIT_TERM_DETAIL = re.compile(r'^edit_term:[ \t]*(?P<id>\S[^\n]*?)[ \t]*$', re.MULTILINE)
# The originating PR, stamped by ``cmd_fetch_findings`` as the first ``detail``
# line. ``post_responses`` filters on it so a plan whose findings store spans
# several PRs transmits each disposition only to the PR it came from.
#
# Unlike the three patterns above this one is anchored to the START OF THE WHOLE
# detail string (``\A``, no ``re.MULTILINE``) and accepts a digits-only id. Both
# narrowings are deliberate: the producer writes ``pr_number`` as the FIRST detail
# line and always as an integer, so a per-line ``search`` would additionally honour
# a ``pr_number:`` line appearing anywhere later in the block — including inside
# text a future producer change might append — and a ``\S``-class value would admit
# a non-numeric id. ``cmd_post_responses`` routes on this extraction to decide
# ``belongs_to_pr_<n>`` vs ``pr_number_unrecorded``, so anything that does not match
# the producer's own shape must resolve as unrecorded rather than widen the
# routing predicate's trust surface.
_PR_NUMBER_DETAIL = re.compile(r'\Apr_number:[ \t]*(?P<id>[0-9]+)[ \t]*(?:\n|\Z)')

# The comment kinds that are GENUINELY threadless — GitHub gives them no
# resolvable review thread, so the only way to transmit their disposition is the
# batched PR-level comment. This is the ONLY admission predicate for the batch:
# ``post_responses`` routes on thread-BEARING-ness (the comment's kind), never on
# whether a ``thread_id`` happened to be extractable. An ``inline`` finding whose
# ``thread_id`` is missing is undeliverable, NOT threadless, and is reported in
# ``untransmitted`` rather than silently downgraded into the batch.
#
# The set is deliberately CLOSED rather than derived as ``PR_COMMENT_KINDS -
# {'inline'}``: a kind added to the vocabulary later must be classified by hand,
# because auto-inheriting the threadless side is exactly the silent-batching
# failure this predicate exists to prevent. An unrecognised or unrecorded kind
# therefore takes the thread-bearing path and surfaces as untransmitted.
_THREADLESS_KINDS = frozenset({'review_body', 'issue_comment'})

# How much of an unrecognised refusal's body travels on its record. The excerpt is
# not decoration — it is the REMEDY: the phrasing an operator copies into the bot's
# ``refusal_patterns`` so the next fetch reclassifies the same body through the
# registry arm. It is bounded because the record rides a TOON envelope, and a
# refusal notice states its point early, so the opening characters carry the
# phrasing worth filing.
_UNRECOGNISED_REFUSAL_EXCERPT_CHARS = 400


def _detail_field(detail: str | None, pattern: re.Pattern) -> str:
    """Extract a labelled value (``comment_id`` / ``thread_id``) from a pr-comment finding's detail block."""
    match = pattern.search(detail or '')
    return match.group('id') if match else ''


def _comment_edit_term(comment: dict) -> str:
    """Return the EDIT TERM of ``comment`` — the third term of the dedup identity.

    ``updated_at`` when the provider supplied one: a bot that edits its one persistent
    comment in place moves that value, so an edited comment presents as new information
    while an unchanged re-fetch still dedupes.

    A body digest when it did not. The fallback is required rather than cosmetic: with
    no third term at all an edited comment carrying no ``updated_at`` would collapse
    back onto the two-term key and be dropped as a duplicate — the exact defect the
    widening closes. The digest moves when the body moves, which is the same question
    ``updated_at`` answers, read from the content instead of from the metadata.
    """
    updated_at = str(comment.get('updated_at') or '')
    if updated_at:
        return updated_at
    digest = hashlib.sha256(str(comment.get('body') or '').encode('utf-8')).hexdigest()
    return f'sha256:{digest}'


def _read_pr_comment_findings(query_findings, plan_id: str) -> dict[str, Any]:
    """Return the plan's ``pr-comment`` query payload, or the store's own REFUSAL.

    ``manage-findings`` answers a plan whose directory is not under the root it
    resolved with ``error: findings_store_unresolved`` and NO ``findings`` key. A
    caller reading ``result.get('findings') or []`` therefore received an EMPTY LIST
    for a store nobody reached, and every verdict computed downstream from it — "no
    comment was ever filed here", "there is nothing to respond to" — was derived from
    a substrate that was never opened. Recognising the refusal first is what carries
    the store's own named error code out of this producer instead of a clean zero.

    ⛔ A store that RESOLVED and legitimately holds no ``pr-comment`` finding is
    untouched by this: it still returns the ordinary success payload with an empty
    ``findings`` list. Only an UNREACHED store refuses.

    Args:
        query_findings: The ``_findings_core.query_findings`` callable.
        plan_id: Plan identifier whose findings store is queried.

    Returns:
        The successful query payload — whose ``findings`` key the caller may then
        read — or the refusal dict (``status: error`` plus the store's provenance)
        for the caller to return verbatim.
    """
    from _findings_store_state import as_unresolved_store_error

    result = query_findings(plan_id, finding_type='pr-comment')
    refusal = as_unresolved_store_error(result)
    return refusal if refusal is not None else result


def _existing_pr_comment_keys(
    findings: list[dict],
) -> tuple[set[tuple[str, str, str]], set[tuple[str, str]]]:
    """Return the dedup keys already stored as pr-comment findings, in BOTH shapes.

    Each pr-comment finding embeds its source ``comment_id`` on a
    ``comment_id: <value>`` line inside its ``detail`` block, its ``edit_term`` on an
    ``edit_term: <value>`` line, and carries the resolved ``bot_kind`` as a top-level
    field. Reconstructing those keys from the persisted findings (across all resolution
    states) lets the producer skip any comment — thread-bearing or thread_id-less, from
    any bot kind — that was already staged in a prior finalize iteration, closing the
    cross-iteration phantom loop for all bots.

    The identity is ``(bot_kind, comment_id, edit_term)``. Keying on ``bot_kind``
    alongside the id avoids a collision between two distinct bots that happen to reuse
    the same numeric comment id; a human-authored finding (``bot_kind`` unset)
    contributes ``('', comment_id, edit_term)``. The EDIT TERM is what lets an
    in-place-edited review present as new information: without it, a bot that edits its
    one persistent comment to carry a real finding was credited as participating while
    the dedup dropped the comment, so the reviewer read present-and-clean and its actual
    feedback never became a finding.

    A PURE projection over an already-read finding list. The read itself lives in
    :func:`_read_pr_comment_findings`, so the caller settles the unreached-store
    refusal ONCE, before any key is reconstructed — this function can no longer turn
    a store it never reached into an empty key set, which would present a PR's entire
    comment history as unfiled and re-file all of it.

    Args:
        findings: The plan's stored ``pr-comment`` finding records.

    Returns:
        ``(keys, legacy_keys)`` — the three-term identities, and the two-term
        ``(bot_kind, comment_id)`` identities of findings stored BEFORE the edit term
        existed. A pre-upgrade row carries no ``edit_term`` line, so it can match no
        three-term key; it is deduped on the two-term key against ANY edit term
        instead. Without that, the upgrade would re-file a PR's entire comment history
        once, on the first fetch after it landed.
    """
    keys: set[tuple[str, str, str]] = set()
    legacy_keys: set[tuple[str, str]] = set()
    for finding in findings:
        detail = finding.get('detail')
        comment_id = _detail_field(detail, _COMMENT_ID_DETAIL)
        if not comment_id:
            continue
        bot_kind = finding.get('bot_kind') or ''
        edit_term = _detail_field(detail, _EDIT_TERM_DETAIL)
        if edit_term:
            keys.add((bot_kind, comment_id, edit_term))
        else:
            legacy_keys.add((bot_kind, comment_id))
    return keys, legacy_keys


# The plan-scoped CURRENCY LEDGER: per ``participation_requires_update`` comment the
# plan has credited, the ``(bot_kind, comment_id)`` key with the merge-candidate SHA
# AND the comment's ``updated_at`` at the fetch that last credited it. It is the SOLE
# source the currency test reads, so a comment stored as a finding and a comment
# dropped as noise (PR-Agent's contentless Guide) are treated identically — the
# ledger records the credit regardless of whether the comment produced a finding.
#
# Recording BOTH the SHA and the ``updated_at`` is load-bearing. Anchoring on the SHA
# alone leaves the edit-movement arm a permanent "was ever edited" flag: once a
# comment is edited at some commit, ``updated_at != created_at`` stays true forever,
# so every later HEAD advance would keep crediting it even though the bot never
# reviewed those commits. Comparing ``updated_at`` against the value recorded at the
# LAST credit instead ("edited since we last credited it") closes that hole: an edit
# at commit N credits N, but not N+1, N+2 unless a FURTHER edit lands.
#
# It sits BESIDE the findings store (the same ``artifacts/`` root) rather than
# inside ``artifacts/findings/``, and that placement is load-bearing: these are
# observation records, not findings. Filing them as findings — in any resolution
# state — would put routine clean-review boilerplate back in front of operator
# triage, into the pending-findings gate, and into the review-retrospective
# aggregation, which is the whole class of defect the contentless drop removes.
_CURRENCY_LEDGER_ARTIFACT = 'pr-participation-currency-ledger.jsonl'

#: The filename the ledger was written under before it was named for what it holds. It is
#: READ and never written, and that read is DATA MIGRATION rather than a deprecation
#: shim: the rows under this name are real credits, so a reader that stopped opening the
#: file would hand every comment recorded there back to the first-observation arm and
#: credit — at any resolvable HEAD — precisely the reviews the ledger was keeping honest.
#: It therefore does not expire with the rename.
_LEGACY_CURRENCY_LEDGER_ARTIFACT = 'pr-noise-dropped-comments.jsonl'


def _currency_ledger_path(plan_id: str) -> Path:
    """Resolve the plan-scoped path the currency ledger is WRITTEN to."""
    from jsonl_store import get_artifact_path

    return get_artifact_path(plan_id, _CURRENCY_LEDGER_ARTIFACT)


def _legacy_currency_ledger_path(plan_id: str) -> Path:
    """Resolve the plan-scoped path the currency ledger was written to before the rename.

    Read-only. See :data:`_LEGACY_CURRENCY_LEDGER_ARTIFACT` for why the read survives.
    """
    from jsonl_store import get_artifact_path

    return get_artifact_path(plan_id, _LEGACY_CURRENCY_LEDGER_ARTIFACT)


class _InvalidLegacyRecord:
    """A currency-ledger row present in the file but carrying no usable reviewed SHA."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover — diagnostic only
        return '<invalid legacy currency record>'


#: The STATED sentinel for a ledger row that exists but cannot anchor a credit — a row
#: written before the artifact carried a ``reviewed_commit_sha``, or one whose SHA is
#: empty. It is a THIRD state, distinct from both *no record* (``None``) and *a usable
#: record* (a ``(sha, updated_at)`` pair), and it is what makes the distinction legible.
#:
#: ⛔ Dropping such a row instead is the NON-FIX: an absent key takes the
#: first-observation arm, so a dropped row credits the bot at any resolvable advanced
#: HEAD — precisely the false credit the currency test exists to deny. The row must
#: survive the read and be REFUSED by the predicate, not vanish from it.
INVALID_LEGACY_RECORD = _InvalidLegacyRecord()

#: A ledger value: a usable ``(reviewed_commit_sha, updated_at)`` pair, or the sentinel.
#:
#: Consumers ask ``isinstance(record, _InvalidLegacyRecord)`` — a MEANING guard over the
#: stated identity above (ADR-015), never a truthiness test on the tuple's first element,
#: which is exactly the inline check that let a ``('', '')`` row fall through to the edit
#: arm and credit essentially any real comment.
CurrencyRecord = tuple[str, str] | _InvalidLegacyRecord


def _recorded_currency_records(plan_id: str) -> dict[tuple[str, str], CurrencyRecord]:
    """Return ``(bot_kind, comment_id) -> (reviewed_commit_sha, updated_at)`` for earlier credits.

    The currency ledger the currency test reads. Each entry is the ``(sha,
    updated_at)`` at which a ``participation_requires_update`` comment was LAST
    credited — the SHA to compare against the merge candidate, and the ``updated_at``
    to compare against the comment's current value so a fresh in-place edit
    (``updated_at`` moved past the recorded one) re-credits it while an old edit does
    not. Only prior fetches contribute — the current fetch's credits are appended
    after the participation loop has read this map, so a comment observed for the
    first time still takes the first-observation arm on the run that observed it.
    Last row wins per key, so a re-credit at a new HEAD supersedes the old record.

    A missing ledger reads as the empty map (no fetch has run for this plan yet).

    BOTH filenames are read — the pre-rename one first, then the current one — because a
    plan whose ledger was written before the rename holds its credits under the old name
    and nothing ever rewrites them. The current file is read SECOND so that, key by key,
    it supersedes the older anchor under the same last-row-wins rule that governs repeat
    credits within one file; a key the current file does not carry still resolves from the
    older one. ⛔ Reading the old file only when the new one is ABSENT is the shape to
    avoid, and it is not equivalent: the writer appends only CHANGED records, so the first
    post-rename credit creates a current file holding that one key, and a per-file
    fallback would from then on drop every unchanged key back to the first-observation arm
    — crediting at any resolvable HEAD exactly the reviews the ledger was anchoring.

    A row whose ``reviewed_commit_sha`` is missing or empty maps to
    :data:`INVALID_LEGACY_RECORD` — the third state — rather than to a
    ``('', updated_at)`` pair that would fall through to the edit arm (true for
    essentially any real comment), and rather than being dropped, which would hand the
    comment to the first-observation arm and credit it at any resolvable advanced HEAD.
    """
    from jsonl_store import read_jsonl

    records: dict[tuple[str, str], CurrencyRecord] = {}
    for path in (_legacy_currency_ledger_path(plan_id), _currency_ledger_path(plan_id)):
        for record in read_jsonl(path):
            key = (str(record.get('bot_kind') or ''), str(record.get('comment_id') or ''))
            sha = str(record.get('reviewed_commit_sha') or '')
            if not sha:
                records[key] = INVALID_LEGACY_RECORD
                continue
            records[key] = (sha, str(record.get('updated_at') or ''))
    return records


def _record_currency_records(
    plan_id: str, records: dict[tuple[str, str], tuple[str, str]]
) -> None:
    """Append currency records whose ``(sha, updated_at)`` changed since the last fetch.

    Callers pass only records that DIFFER from the current ledger value (a new key,
    or a re-credit at a new SHA / after a fresh edit), so the file accretes one row
    per distinct credit rather than one row per fetch. Sorted so the file order is
    deterministic.

    Only the CURRENT filename is ever written. The pre-rename file is read by
    :func:`_recorded_currency_records` and left untouched, so a plan's older credits keep
    resolving without this writer having to rewrite a file it did not create.
    """
    from jsonl_store import append_jsonl

    path = _currency_ledger_path(plan_id)
    for (bot_kind, comment_id), (sha, updated_at) in sorted(records.items()):
        append_jsonl(
            path,
            {
                'bot_kind': bot_kind,
                'comment_id': comment_id,
                'reviewed_commit_sha': sha,
                'updated_at': updated_at,
            },
        )


#: The ONE timestamp shape the ordering below is valid over: fixed-width ISO-8601 UTC
#: with a literal trailing ``Z``, as the GitHub API emits for both comment timestamps
#: and commit timestamps. Two strings of this shape sort lexicographically in the same
#: order as the instants they name, which is what makes a bare ``<`` a correct ordering
#: test. A string in ANY other shape — a numeric UTC offset (``+02:00``), a
#: fractional-second form, a bare date, an epoch integer — does NOT sort against this
#: one, so mixing shapes turns ``<`` into a silently wrong ordering CLAIM rather than
#: into a comparison error something would notice. The regex is therefore the
#: comparability guard, not a validation nicety.
_ISO_UTC_TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')


def _comment_predates_commit(comment: dict, merge_candidate_committed_at: str) -> bool:
    """True when ``comment`` demonstrably existed BEFORE the merge-candidate commit.

    The comment's own latest timestamp is the LATER of ``updated_at`` / ``created_at``
    — the moment it last said anything. When that moment precedes the commit's own
    timestamp, the comment cannot be an observation of that commit, however empty the
    currency ledger is.

    Returns False whenever the question cannot be decided: an unreadable commit
    timestamp, an absent comment timestamp, or timestamps that do not compare. An
    unknown ordering is NOT a claim that the comment predates the commit, and the
    caller must not read it as one — the withholding here rests on positive evidence
    of the ordering, never on its absence.

    "Do not compare" is a GUARDED condition, not an assumed one: every timestamp that
    reaches the ``<`` must match :data:`_ISO_UTC_TIMESTAMP`, and any that does not
    sends the whole question to False. Without that guard the ordering is a bare
    lexicographic string compare, and a format mismatch — one side offset-stamped, one
    side ``Z``-stamped — yields a confident but silently wrong ordering claim instead
    of the undecided answer promised above. The comment's OWN two timestamps are
    guarded for the same reason before ``max`` picks between them: a lexicographic max
    over two differently-shaped strings does not select the later moment.
    """
    commit_at = str(merge_candidate_committed_at or '')
    if not _ISO_UTC_TIMESTAMP.match(commit_at):
        return False
    stamps = [
        stamp
        for stamp in (
            str(comment.get('updated_at') or ''),
            str(comment.get('created_at') or ''),
        )
        if stamp
    ]
    if not stamps:
        return False
    if not all(_ISO_UTC_TIMESTAMP.match(stamp) for stamp in stamps):
        return False
    return max(stamps) < commit_at


def _reviewed_at_merge_candidate(
    comment: dict,
    currency_records: dict[tuple[str, str], CurrencyRecord],
    bot_kind: str,
    merge_candidate_sha: str,
    merge_candidate_committed_at: str = '',
) -> bool:
    """Return True when ``comment`` proves a review of the MERGE CANDIDATE commit.

    The currency qualifier for a bot that re-reviews by EDITING one persistent
    comment in place instead of posting a new one. Such a comment's continued
    existence proves only that the bot reviewed at SOME commit, so crediting it on
    presence alone would silently score a review of an earlier commit as a review
    of the tree being merged after a loop-back or a force-push. The credit is
    therefore anchored to the merge candidate's SHA, and the verdict is a PURE
    COMPARISON that consumes no observation state — so it is identical however many
    times it is evaluated **while the merge candidate remains resolvable**. That
    qualification is the honest reach of the claim, not a hedge: the SHA is read per
    fetch from a fallible provider call, so a resolved-then-unresolved sequence moves
    the verdict from a credit to the undecidable outcome without any observation state
    having been consumed. Idempotence holds over repeated evaluation, never over a
    changed ability to read the head. That fixes both original defects at once: the dead-anchor
    false positive AND the observer effect (the old first-presence arm was *consumed*
    on the first fetch, flipping the same unedited comment to stale on the second
    look at the same HEAD).

    ``currency_records`` maps every ``(bot_kind, comment_id)`` the plan has credited
    to the ``(reviewed_commit_sha, updated_at)`` at that LAST credit — the currency
    ledger. The credit holds when ANY of:

    - **SHA currency** — the recorded review is against the merge candidate. This is
      the idempotent arm: re-running at the same HEAD reads the same recorded SHA
      and returns the same answer, and it replaces the old observation-history term
      so no participation path reads ``observed_keys`` as a currency signal.
    - **First observation** — the comment is not yet in the ledger, so this fetch is
      observing it at the merge candidate; the caller records it. This arm is guarded
      on a resolvable (non-empty) ``merge_candidate_sha``: a failed head-SHA read
      cannot anchor the credit, so it FAILS CLOSED rather than crediting an
      observation it could not tie to a commit. Failing closed here is also what
      keeps the verdict idempotent when the head-SHA read fails — a later fetch that
      likewise cannot read the SHA reaches the same (blocking) answer, not a flip.
      It is guarded a second way when ``merge_candidate_committed_at`` is readable:
      a comment whose own timestamps PREDATE the merge-candidate commit cannot be an
      observation of it, whatever the ledger does or does not remember — the comment
      demonstrably existed before the code did. When the commit timestamp cannot be
      read the arm keeps its SHA-only behaviour, because an unreadable timestamp is
      not an ordering claim; that unresolved read is disclosed by the caller rather
      than turned into a new blocking state here.
    - **Fresh edit** — the bot edited the comment in place SINCE it was last credited
      (``updated_at`` differs from the recorded ``updated_at``), publishing a fresh
      review at the current tree. Comparing against the recorded ``updated_at`` — not
      against ``created_at`` — is what keeps this arm from becoming a permanent "was
      ever edited" flag: an edit at commit N credits N, but not N+1, N+2 unless a
      FURTHER edit lands. An absent ``updated_at`` degrades to "no movement" — the
      fail-closed direction, since crediting an unverified review is the expensive
      error. This arm is ALSO guarded on a resolvable ``merge_candidate_sha``, so an
      unreadable head fails closed on EVERY arm rather than on some of them: an edit
      proves a fresh review of *something*, and without a readable head there is no
      commit to say it was a review OF.
    - **Invalid legacy record** — a row that exists but carries no usable reviewed
      SHA (:data:`INVALID_LEGACY_RECORD`) yields False outright. It is neither a
      first observation nor a usable anchor, and reading it as either is how a
      pre-upgrade row credited a bot at any advanced HEAD. The third state is
      recognised by identity, not by testing the anchor for truthiness.

    A comment last credited against an EARLIER commit, with no fresh edit, yields
    False: stale evidence, which is neither absence nor participation.
    """
    comment_id = str(comment.get('id') or 'unknown')
    record = currency_records.get((bot_kind, comment_id))
    if isinstance(record, _InvalidLegacyRecord):
        # The third state: a row that EXISTS but anchors nothing. Refused outright —
        # falling through to the first-observation arm is what credited a pre-upgrade
        # row at any resolvable advanced HEAD.
        return False
    if record is None:
        # First observation — credit only when the merge candidate is resolvable AND
        # the comment does not predate the commit it would be credited against.
        if not merge_candidate_sha:
            return False
        return not _comment_predates_commit(comment, merge_candidate_committed_at)
    recorded_sha, recorded_updated_at = record
    if merge_candidate_sha and recorded_sha == merge_candidate_sha:
        return True
    if not merge_candidate_sha:
        return False
    updated_at = str(comment.get('updated_at') or '')
    return bool(updated_at) and updated_at != recorded_updated_at


def cmd_fetch_findings(args):
    """Producer-side FIND verb: fetch + pre-filter + file one finding per surviving comment.

    Pre-filters applied in order:
    1. Already-resolved threads — skipped silently (``count_skipped_noise``); the
       thread owner addressed them.
    2. REFUSALS — a comment recognized by ``_github_pr._is_refusal_notice`` as the
       bot DECLINING to review. Counted in ``count_skipped_refusal``, NEVER in
       ``count_skipped_noise``, and the refusing bot is named in ``refused_bots``.
       It files no ``pr-comment`` finding: a refusal is a signal ABOUT the review,
       not feedback about the code, so the operator is never asked to triage it.
    3. SELF-AUTHORED RESPONSE — the batched disposition comment ``post_responses``
       itself posted, recognized start-anchored by ``_is_self_authored_response``.
       Counted in ``count_skipped_self_response``, NEVER in ``count_skipped_noise``
       (it is our own output, not noise), and files no finding — re-ingesting it is
       the non-terminating barrier loop this stage exists to close.
    4. Obvious text noise — matched via ``_is_obvious_noise`` (lgtm, bot sigs, etc.),
       counted in ``count_skipped_noise``.
    5. UNRECOGNISED REFUSAL — a comment the enumerative arm
       (``_github_pr._is_unrecognised_refusal``) reads as a refusal no earlier arm
       matched. Counted in ``count_skipped_refusal`` alongside stage 2 (so
       ``expected_stored`` stays balanced and the ``(producer-mismatch)`` Q-Gate
       cannot fire on this branch), reported in ``unrecognised_refusal``, and files
       no finding. It runs HERE — after the noise filter, not beside stage 2 —
       because a bot's own declared clean-review text must already have been dropped
       before a short anchor-less body can be read as a refusal.
    6. Cross-iteration duplicate — a ``(bot_kind, comment_id, edit_term)`` key already
       present in the store, counted in ``count_skipped_duplicate``. The EDIT TERM is
       the comment's ``updated_at``, or a body digest when the provider supplied none,
       so an in-place-edited review presents as NEW INFORMATION and is filed while an
       unchanged re-fetch still dedupes. A finding stored before the term existed
       carries none, and dedupes on the two-term key against any edit term.

    ``self_response_loop_detected``: true when a single fetch observed
    ``count_self_response_current_cycle >= _SELF_RESPONSE_LOOP_BOUND``. Every turn
    of the respond → re-fetch cycle leaves one permanent response comment on the
    PR, so the PR's own comment list IS the iteration counter — no new state store
    and no new config key. The counter is the CURRENT cycle's trailing run of
    self-responses (``_current_cycle_self_response_count``), NOT the cumulative
    ``count_skipped_self_response``: this fetch is ``unresolved_only=False``, so the
    cumulative figure spans every cycle the PR ever completed and would report a
    loop on any PR that merely converged three normal times. Both counts are
    reported — the cumulative one is the honest total of what the filter dropped,
    the current-cycle one is the loop predicate. On detection the producer files a
    ``(self-response-loop)`` Q-Gate finding through ``add_qgate_finding_checked``,
    so exhaustion is a REPORTED coverage gap requiring an operator decision rather
    than a silent pass; a rejected persist surfaces as
    ``self_response_loop_persist_failed``. The enclosing ``status`` stays
    ``success`` — the fetch itself succeeded.

    Containment: the untrusted comment ``body`` is quarantined under
    ``raw_input.{body}`` — never embedded raw in the top-level ``detail``. The
    ``detail`` carries only trusted, producer-built structured metadata
    (pr_number, kind, author, thread_id, comment_id, path, line) so the triage
    read surface stays clean-by-construction until the batched
    ``manage-findings ingest`` pass promotes the validated body.

    Fail-loud on an UNREACHED findings store too: the cross-iteration dedup reads
    the plan's stored ``pr-comment`` findings, and a plan directory absent from the
    resolved root makes that read a refusal carrying no ``findings`` key. It is
    returned verbatim (``error: findings_store_unresolved``) rather than read as an
    empty key set, which would present the PR's whole comment history as unfiled. A
    resolved store that has simply filed nothing yet is unaffected and still fetches.

    Fail-loud: returns a typed ``unconfigured`` status (not a silent success)
    when GitHub is not authenticated. ``count_fetched`` vs ``count_stored``
    mismatches are recorded as a ``qgate`` finding with title prefix
    ``(producer-mismatch)`` so the LLM sees them in ``manage-findings qgate list``.
    When that mismatch finding is itself REJECTED by the persist primitive (status
    outside ``QGATE_PERSIST_OK``), the result carries ``qgate_persist_failed: true``
    plus the rejected finding's content and the primitive's message, so no caller
    can read a clean ``fetch_findings`` result while the mismatch finding was lost.
    The enclosing ``status`` stays ``success`` — it reports the fetch, which did
    succeed.

    ``participated_bots``: the EVIDENCE-TYPED participation set — one
    ``{bot_kind, evidence_kind}`` record per bot proven to have reviewed this diff,
    computed BEFORE any noise / duplicate / resolved filtering (so a bot whose
    comments were entirely noise-filtered or entirely already-resolved is still
    credited). A bot qualifies only when an observed comment's ``kind`` is one of
    the publish shapes its registry record declares in ``participation_evidence``
    — the mere presence of some comment resolving to its login is NOT evidence.
    For a bot whose record sets ``participation_requires_update`` (it re-reviews by
    editing one persistent comment in place) the record additionally requires the
    comment to prove a review of the MERGE CANDIDATE commit
    (``_reviewed_at_merge_candidate``), so a comment reviewed against an earlier
    commit cannot credit it with reviewing the tree being merged. The credit is an
    SHA comparison against the current PR HEAD, read from the plan-scoped currency
    ledger — the ``(reviewed_commit_sha, updated_at)`` at which each such comment was
    last credited. The ledger is blind to the STORAGE axis: a comment stored as a
    finding and one dropped as noise record alike. It is NOT blind to the currency
    verdict — a row is written or refreshed only for a comment that PASSED the currency
    test on this fetch, and a comment that FAILED leaves its row exactly as it stood
    (unchanged if it had one, absent if it had none). Staging a failing comment would
    stamp the current HEAD onto stale evidence, so the next fetch would read
    ``recorded_sha == merge_candidate_sha`` and credit the comment this fetch had just
    rejected. Because it is a pure comparison that consumes no observation
    state, the verdict is idempotent **while the merge candidate remains resolvable**:
    re-running the fetch at the same HEAD returns the same answer, closing the observer
    effect the old first-presence arm had. The qualification names the one sequence that
    refutes the unconditional claim — a fetch at the SAME HEAD whose head-SHA read fails
    yields the undecidable outcome instead of the credit, so the answer changed without
    any observation state being consumed. And
    because a fresh edit is measured against the recorded ``updated_at`` rather than
    against ``created_at``, an edit at one commit credits that commit only, not every
    later HEAD.

    ``stale_participation_bots``: where that currency-test failure now GOES, instead
    of being discarded. Same ``{bot_kind, evidence_kind}`` record shape as
    ``participated_bots``, carrying one entry per bot whose observed comment kind
    ALREADY matched a declared publish shape but which failed the
    ``participation_requires_update`` currency test. The proven set is subtracted
    before emitting, so a bot with one stale and one fresh comment appears only in
    ``participated_bots``. The completeness layer consumes it as
    ``--stale-participation-bots`` and classifies the bot ``participated_stale``
    rather than ``absent`` — two states whose remedies are opposite, since a stale
    publish is re-triggered while a true absence is escalated.

    ``merge_candidate_sha_resolved`` / ``undecidable_participation_bots``: the THIRD
    outcome, for when the merge candidate itself could not be read.
    ``fetch_pr_head_sha`` returns '' on ANY failure path, so the flag reports only
    whether the read produced a SHA — never a verdict an operator can act on. A
    currency-subject bot whose comment matched a declared publish shape on such a fetch
    is reported in ``undecidable_participation_bots`` (same ``{bot_kind, evidence_kind}``
    shape, proven set subtracted) and in NEITHER other set: not credited, because
    nothing anchors the credit; and not stale, because stale prescribes re-triggering a
    review, which cannot fix a failed head read. Disjointness from
    ``stale_participation_bots`` is structural — the head read is per-fetch, so a fetch
    either resolved the candidate or did not.

    ⚠ ``undecidable_participation_bots`` is PRODUCER-SIDE DISCLOSURE with no consumer
    yet: ``review_completeness``'s taxonomy has no member for this state, so nothing
    routes on it today. Widening the classifier is a separate plan, for which this field
    is the prerequisite. The gap is stated rather than left to surface as an unreachable
    branch.

    A bot declaring no evidence shape resolves FAIL-CLOSED — it can never be proven
    a participant. This proves PARTICIPATION only, never review QUALITY: the
    consumer must not read a satisfied participation set as a reviewed diff.

    ``refused_bots``: the sorted list of bot_kinds observed publishing a REFUSAL —
    a rate-limit / quota / size-ceiling notice posted in place of a review,
    recognized through ``_github_pr._is_refusal_notice``, which consults the arms of
    the refusal-recognition stack answerable before the noise filter (see
    ``_github_pr.REFUSAL_LAYERS`` for the arms currently defined). A refusal no arm
    at that position matched is picked up by the enumerative arm immediately after
    the noise filter and reported in ``unrecognised_refusal`` instead — see that
    field. This is the producer-side refusal channel the completeness / quorum layer
    consumes as ``--refused-bots``, so it can classify the bot into a refusal member
    instead of inferring absence from silence. That classification maps the bot's
    declared ``rate_limit_class`` BY DEFAULT, and TWO per-refusal observations
    displace that default — a diff-size ceiling resolves ``refused_structural``, and a
    refusal no recognition arm could read resolves ``refused_unknown`` whatever the
    bot's declared class says, because nothing about an unreadable notice is known.
    Both outrank the class because the class is declared per BOT while each of them is
    observed per REFUSAL. The mapping and its overrides are
    ``review_completeness``'s to state; it is deliberately not restated as a fixed
    correspondence here, so an override added there needs no edit in this docstring.
    A refusing comment
    is excluded from ``participated_bots`` — a refusal is positive evidence the bot
    did NOT review — and files no finding, so it never reaches operator triage. A
    refusal from an unregistered login is still dropped from the store but cannot
    be attributed, so it contributes to ``count_skipped_refusal`` without naming a
    bot here.

    ``unrecognised_refusal``: one record per comment the ENUMERATIVE arm recognised
    — a refusal that reached no arm consulted ahead of it. Distinct
    from ``refused_bots`` and never folded into it: those name a refusal the stack
    could READ, this one names a refusal it could only detect. Each record carries
    ``{bot_kind, layer, excerpt}`` plus the mechanism that closes the gap —
    ``registry_file``, ``registry_field`` and ``remedy``. ``layer`` is the third
    member of the shared vocabulary (``_github_pr.REFUSAL_LAYER_ENUMERATIVE``), so a
    reader of this record and a reader of a re-review refusal record are reading one
    vocabulary. The record is a REACHABLE remedy rather than a description of one:
    the excerpt is the phrasing to add, ``registry_file`` is the file to add it to,
    ``registry_field`` is the field, and the outcome is recorded because the next
    fetch reclassifies that same body through the registry arm instead. The bot is
    also denied participation credit when EVERY one of its publish-shape comments was
    an unrecognised refusal (see ``participated_bots``); a bot with any genuine review
    keeps its credit and the record stays a diagnostic.

    ``refusal_pattern_drift``: one ``{bot_kind, layer}`` record per bot whose
    recognition arms DISAGREED on a refusal — ``layer`` names the arm that fired
    ALONE, read from the shared ``_github_pr.REFUSAL_LAYERS`` vocabulary. Derived
    from the ``_github_pr.refusal_layers`` provenance seam at the filing pre-filter
    only, and scoped to comments arriving in one of the bot's declared
    ``participation_evidence`` publish shapes.

    A ``structural_fallback`` value is the actionable one: the notice was caught by
    SHAPE alone while the bot's own declared ``refusal_patterns`` missed it, so that
    registry record has gone stale against the bot's current wording and the next
    rewording may clear the structural shape too — at which point the refusal is
    filed as review feedback and the bot is credited with a review it declined.
    Emitting it is what makes that decay observable BEFORE it fails, since the
    ``_is_refusal_notice`` boolean returns ``True`` whether one arm fired or both.

    Deduped on ``(bot_kind, layer)`` — drift is a property of the bot's declared
    wording, not of each comment carrying it. Diagnostic ONLY: it changes no
    verdict, denies no participation credit, and gates nothing; a bot appearing here
    was still correctly recorded as having refused.

    ``refused_causes``: one ``{bot_kind, cause}`` record per refusing bot, ``cause``
    in ``{size, quota}`` — the orthogonal CAUSE axis (``_github_pr.refusal_cause``),
    distinct from ``rate_limit_class``'s awaitability. It names the remedy a refusal
    calls for: ``size`` (the diff is over a per-PR ceiling → a smaller diff) vs
    ``quota`` (a rate/budget limit → backoff). ``size`` is sticky per bot — a bot that
    posted both a size ceiling and a quota notice on this PR records ``size``. Forwarded
    to ``review_completeness check --refused-causes``.

    ``refused_size_caps``: one ``{bot_kind, cap}`` record per bot whose SIZE refusal
    stated the ceiling it refused over (``_github_pr.refusal_size_cap``). Sparse by
    design — a bot that refused for quota states no diff ceiling, and a size notice
    that states no figure yields no record — so an absent entry is an UNKNOWN cap the
    consumer reports as unknown rather than defaulting to one nobody observed. It is
    what makes a recorded coverage gap auditable against the diff that was actually
    refused. Forwarded to ``review_completeness check --refusal-size-caps``.

    ``measured_diff_size``: how big the refused diff actually was, as
    ``"{n} changed lines"`` — the OTHER half of an auditable gap, since a cap without
    the size that hit it is a claim the reader must take on trust. Measured ONLY when a
    size refusal was seen, so the extra provider round-trip is paid on the rare branch
    that needs it and never on the common path. ``''`` when no size refusal occurred or
    the read failed — UNKNOWN, never ``0``, which would read as an empty diff being
    refused for being too big. Its unit rides inside the value and is deliberately not
    the reviewer's unit (see ``_github_pr.measure_diff_size``), so the two figures are an
    order-of-magnitude comparison rather than an equality check. Forwarded to
    ``review_completeness check --measured-diff-size``.

    ``unclassified_bots``: the sorted list of bot_kinds that participated but
    appear in NEITHER ``--required-bots`` nor ``--optional-bots``. Per the
    warn-but-ingest rule these comments are **still ingested** — the two lists
    carry classification, not admission — and the bot is named here so the caller
    can surface the configuration gap. Dropping them would let a configuration
    omission silently destroy real review signal.
    """
    from _findings_core import (
        add_finding,
        add_qgate_finding_checked,
        query_findings,
    )

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

    # Participation classification: --required-bots / --optional-bots each carry a
    # comma-joined set of bot_kinds, split at read time. Their union is the set of
    # CLASSIFIED bots. Neither list admits or drops anything — a comment whose
    # derived bot_kind is outside the union is still ingested and its bot is
    # reported in ``unclassified_bots`` (the warn-but-ingest rule). Human comments
    # (bot_kind is None) are never classified; the notion is bot-scoped.
    classified_bots: set[str] = set()
    for _raw in (getattr(args, 'required_bots', None), getattr(args, 'optional_bots', None)):
        if _raw:
            classified_bots.update(b.strip() for b in _raw.split(',') if b.strip())

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
    # ``(bot_kind, comment_id, edit_term)`` keys already recorded as ``pr-comment``
    # findings (regardless of resolution state) and skip any comment — from any
    # bot kind, thread-bearing or not — whose key is already present. The
    # ``legacy_comment_keys`` companion carries the two-term identities of findings
    # stored before the edit term existed; see ``_existing_pr_comment_keys``.
    #
    # The READ is settled first, because an unreached store and a store holding no
    # pr-comment finding yet are the same empty key set to the dedup — and the first
    # of the two would present a PR's whole comment history as unfiled and re-file
    # every comment. The refusal is returned verbatim rather than reduced to a count.
    findings_payload = _read_pr_comment_findings(query_findings, plan_id)
    if findings_payload.get('status') == 'error':
        return findings_payload
    existing_comment_keys, legacy_comment_keys = _existing_pr_comment_keys(
        findings_payload.get('findings') or []
    )

    # The MERGE CANDIDATE SHA — the current PR HEAD — is fetched up front (before the
    # participation loop, not only for the ingestion stamp below) because the currency
    # test now compares each comment's reviewed SHA against it. Empty string on any
    # failure path, and the currency test then FAILS CLOSED on every arm — SHA currency,
    # first observation, and edit movement alike — rather than crediting a review it
    # cannot tie to a commit. The affected bots are disclosed as
    # ``undecidable_participation_bots`` and the read itself as
    # ``merge_candidate_sha_resolved``.
    reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)

    # The merge candidate's OWN timestamp, read alongside its SHA. It guards the
    # first-observation arm: a comment whose timestamps predate the commit cannot be an
    # observation OF it. Empty string on any failure path, which the arm reads as
    # "ordering unknown" and therefore as no reason to withhold — an unreadable
    # timestamp introduces no new blocking.
    merge_candidate_committed_at = _github.fetch_pr_head_committed_at(pr_number)

    # The currency test (``_reviewed_at_merge_candidate``) reads the currency ledger
    # recorded by earlier fetches (see ``_CURRENCY_LEDGER_ARTIFACT``): per
    # ``participation_requires_update`` comment the plan has credited, the
    # ``(reviewed_commit_sha, updated_at)`` at that last credit. It is the SOLE currency
    # source, so a comment stored as a finding and a comment dropped as noise are
    # treated identically. ``existing_comment_keys`` (read above) stays the input to the
    # cross-iteration dedup (pre-filter 6), which asks a different question — dedup asks
    # "was this already STAGED as a finding?", currency asks "which commit did this
    # comment review, and has it been re-edited since?".
    currency_records = _recorded_currency_records(plan_id)

    # Participation signal for the completeness guard, derived BEFORE any noise /
    # duplicate / resolved filtering so a bot whose comments were all
    # noise-filtered (count_stored 0) or all already-resolved is still credited.
    #
    # Participation is EVIDENCE-TYPED, not presence-typed: the mere existence of
    # some comment resolving to a bot's login proves nothing about whether that
    # bot reviewed this diff. A bot is recorded as a participant only when an
    # observed comment's ``kind`` is one of the publish shapes that bot's registry
    # record declares in ``participation_evidence``, and — for a bot that
    # re-reviews by editing one persistent comment in place
    # (``participation_requires_update``) — only when that comment proves a review
    # of the MERGE CANDIDATE commit (``_reviewed_at_merge_candidate``), since a
    # comment reviewed against an EARLIER commit proves only that the bot reviewed
    # an earlier HEAD.
    #
    # A bot declaring no evidence shape resolves fail-closed: it can never be
    # proven a participant. There is no bot-name literal here — the evidence
    # shapes and the update requirement are registry data.
    participated: dict[str, str] = {}
    stale_participation: dict[str, str] = {}
    # The THIRD outcome: a currency-subject bot whose comment matched a declared publish
    # shape while the merge candidate itself could not be read. It is neither credited
    # (nothing anchors the credit) nor stale (stale's remedy is "re-trigger the review",
    # which cannot fix a failed head read), so it is carried in its own disjoint set.
    undecidable_participation: dict[str, str] = {}
    # Currency records staged for the ``participation_requires_update`` comments credited
    # this fetch — written to the ledger after the loop so the NEXT fetch measures a fresh
    # edit against THIS credit rather than against ``created_at``.
    currency_updates: dict[tuple[str, str], tuple[str, str]] = {}
    for _comment in raw_comments:
        _bot_kind = bot_kind_for_author(_comment.get('author') or 'unknown')
        if not _bot_kind:
            continue
        _requires_update = bot_registry.participation_requires_update(_bot_kind)
        # An already-credited bot is skipped only when its credit needed no currency
        # test. For a CURRENCY-SUBJECT bot every declared-publish-shape comment is
        # evaluated, credited or not: such a bot declares several publish shapes, and
        # short-circuiting at its first credit left every LATER comment unevaluated and
        # so unrecorded in the currency ledger. On the next fetch that unrecorded
        # comment had no ledger row, took the first-observation arm, and credited the
        # bot at whatever HEAD was resolvable — bypassing the very currency test the
        # first comment had just failed. Evaluating every one of them is what closes it.
        if _bot_kind in participated and not _requires_update:
            continue
        # A refusal is positive evidence the bot did NOT review, so it can never
        # be its own participation evidence — even though a refusal is published in
        # one of the bot's declared publish shapes. Without this exclusion a bot
        # that posted nothing but "review limit reached" would be credited as a
        # proven participant and satisfy the quorum on zero review coverage.
        if _is_refusal_notice(str(_comment.get('body') or ''), _bot_kind):
            continue
        _kind = _comment.get('kind') or 'inline'
        if _kind not in bot_registry.participation_evidence(_bot_kind):
            continue
        if _requires_update and not _reviewed_at_merge_candidate(
            _comment,
            currency_records,
            _bot_kind,
            reviewed_commit_sha,
            merge_candidate_committed_at,
        ):
            # The comment's kind ALREADY matched a declared publish shape — only the
            # currency test failed. Discarding it here is what collapsed a stale
            # review into ``absent``, and the two have OPPOSITE remedies: ``absent``
            # means the bot never engaged (escalate the non-participation), while a
            # stale publish means it engaged against an EARLIER commit (re-trigger a
            # re-review). Record the observation so the classifier can tell them
            # apart instead of inferring absence from a failed currency test.
            #
            # NOTHING is staged on this branch. A failing comment leaves its ledger row
            # exactly as it stood — unchanged if it had one, absent if it had none.
            # Staging here would stamp the current HEAD onto stale evidence, and the very
            # next fetch would read ``recorded_sha == merge_candidate_sha`` and credit the
            # comment this fetch just rejected.
            #
            # WHY the credit was withheld decides WHERE the observation goes. An
            # unreadable merge candidate is not evidence about the review at all — the
            # bot may well have reviewed this very commit — so reporting it as stale
            # would prescribe a re-review trigger for a failure a re-review cannot fix.
            # It is disclosed as UNDECIDABLE instead, in its own disjoint set.
            if not reviewed_commit_sha:
                undecidable_participation.setdefault(_bot_kind, _kind)
                continue
            stale_participation.setdefault(_bot_kind, _kind)
            continue
        # Credited. For a ``participation_requires_update`` bot, stage THIS comment's
        # currency record so the next fetch anchors on this credit's SHA and updated_at.
        # One row per PASSING (bot_kind, comment_id) — every evidence comment that passed,
        # not merely the one that happened to credit the bot first.
        #
        # ``reviewed_commit_sha`` is required non-empty to stage: a row whose SHA is the
        # empty string can never again equal a merge candidate, so writing one POISONS
        # the key — the comment is thereafter neither first-observed nor SHA-current and
        # only an edit could ever revive it. Under the fail-closed arms above an
        # unreadable head credits nothing anyway, so this guard is what keeps the ledger
        # free of rows that could not have been written by a real credit.
        if _requires_update and reviewed_commit_sha:
            currency_updates[(_bot_kind, str(_comment.get('id') or 'unknown'))] = (
                reviewed_commit_sha,
                str(_comment.get('updated_at') or ''),
            )
        # The FIRST passing comment's kind is the credited record's ``evidence_kind`` and
        # is never overwritten by a later pass, so the emitted record stays deterministic
        # however many of the bot's comments pass.
        participated.setdefault(_bot_kind, _kind)

    # Persist the currency ledger for the NEXT fetch: for each
    # ``participation_requires_update`` comment credited above, record (merge-candidate
    # SHA, updated_at) — but only when it DIFFERS from the current ledger, so the file
    # accretes one row per distinct credit rather than one per fetch. Written AFTER the
    # loop has read ``currency_records``, so a comment observed for the first time takes
    # the first-observation arm on the run that observed it; on a LATER fetch the
    # recorded SHA is what the currency test compares against the merge candidate, and
    # the recorded updated_at is what a fresh edit must move past. The PR HEAD SHA
    # (``reviewed_commit_sha``) was fetched up front, before the participation loop, so
    # it also serves as the ingestion stamp on every finding below.
    #
    # This is the SECOND read path of ``_recorded_currency_records`` and it is migrated
    # to the third state alongside the predicate: an :data:`INVALID_LEGACY_RECORD` value
    # is never equal to a staged ``(sha, updated_at)`` pair, so a pre-upgrade row is
    # SUPERSEDED by the first real credit rather than suppressing the append.
    _record_currency_records(
        plan_id,
        {k: v for k, v in currency_updates.items() if currency_records.get(k) != v},
    )

    stored_hashes: list[str] = []
    skipped_noise = 0
    skipped_duplicate = 0
    skipped_refusal = 0
    skipped_self_response = 0
    refused_set: set[str] = set()
    # Per refusing bot, the CAUSE of its refusal (size vs quota) — the orthogonal
    # axis to rate_limit_class's awaitability. ``size`` is sticky: a bot that emitted
    # both a size ceiling and a quota notice on this PR records ``size``, the more
    # actionable remedy (a smaller diff).
    refused_causes: dict[str, str] = {}
    # Per SIZE-refusing bot, the diff-size CAP its own notice stated. Populated only
    # from a ``size`` refusal — a quota notice names no diff ceiling — and left absent
    # when the notice states no figure, so an unknown cap stays unknown rather than
    # defaulting to one nobody observed.
    refused_size_caps: dict[str, str] = {}
    # One record per comment the ENUMERATIVE arm recognised — a refusal no earlier
    # arm could read. Kept as its own list rather than folded into ``refused_set``:
    # those two answer different questions, and collapsing them would lose exactly
    # the distinction between a refusal the stack READ and one it could only detect.
    unrecognised_refusal: list[dict[str, str]] = []
    # One record per bot whose notice the STRUCTURAL arm read while the bot's own
    # declared ``refusal_patterns`` did not — the one direction in which a
    # single-arm catch means the registry record has gone stale. The mirror
    # direction is not recorded: a registry-only match is what the registry arm is
    # load-bearing FOR (a size notice is invisible to the structural arm by
    # construction), so recording it would report the design as decay. Deduped on
    # ``(bot_kind, layer)`` because drift is a property of the BOT's declared
    # wording, not of each comment carrying it: a bot that posts the same drifted
    # notice five times has one stale record to fix, and five identical rows would
    # read as five problems.
    refusal_pattern_drift: list[dict[str, str]] = []
    _drift_seen: set[tuple[str, str]] = set()
    unclassified_set: set[str] = set()
    store_failures: list[str] = []

    for comment in raw_comments:
        # Pre-filter 1: already-resolved threads — skip silently (not noise,
        # not a finding; the thread owner already addressed the comment).
        if comment.get('resolved'):
            skipped_noise += 1
            continue

        author = comment.get('author') or 'unknown'

        # Derive bot_kind from the comment author login (coderabbitai ->
        # coderabbit, cuioss-review-bot -> pr-agent); a human author resolves to
        # None. Computed BEFORE the noise pre-filter (so per-bot ignore patterns
        # apply) AND before the dedup check (so the cross-iteration guard can key
        # on (bot_kind, comment_id)).
        bot_kind = bot_kind_for_author(author)

        body = comment.get('body') or ''

        # Pre-filter 2: REFUSAL — the bot declined to review. This is a BRANCH, not
        # a drop-as-noise: the comment files no finding (a refusal is a signal
        # about the review, not feedback about the code, so it must never reach
        # operator triage), but the refusing bot is SURFACED in ``refused_bots`` so
        # the completeness / quorum layer classifies it into a refusal member —
        # by the bot's declared rate_limit_class by DEFAULT, displaced by the
        # per-refusal overrides review_completeness applies — rather than inferring
        # absence from silence. Checked BEFORE
        # the noise filter so a refusal can never be swallowed by a shared ignore
        # regex on its way past. An unregistered login's refusal is still
        # recognized structurally and skipped, but cannot be attributed to a bot.
        # This stage consults only the arms answerable at this position; the
        # enumerative arm runs after the noise filter (pre-filter 5).
        if _is_refusal_notice(body, bot_kind):
            skipped_refusal += 1
            if bot_kind:
                refused_set.add(bot_kind)
                # Classify the refusal's CAUSE (size vs quota) so the quorum layer can
                # name the remedy — a smaller diff vs backoff. ``size`` is sticky: once
                # a size ceiling is seen for this bot it wins over a later quota notice.
                cause = refusal_cause(body, bot_kind)
                if cause == REFUSAL_CAUSE_SIZE or bot_kind not in refused_causes:
                    refused_causes[bot_kind] = cause
                # A size refusal states the CAP it refused over; capture it from the
                # notice so the recorded coverage gap is auditable against the diff
                # that was actually refused. Kept on the same stickiness as the cause
                # (a size notice wins) and only ever SET from a size refusal — a quota
                # notice states no diff ceiling, so reading one from it would invent a
                # figure. An empty capture stays empty: unknown, never a default.
                if cause == REFUSAL_CAUSE_SIZE:
                    cap = refusal_size_cap(body, bot_kind)
                    if cap:
                        refused_size_caps[bot_kind] = cap
                # DRIFT: the STRUCTURAL arm read this notice while the bot's own
                # declared ``refusal_patterns`` did NOT. The refusal was still
                # caught, so nothing about the verdict changes; what changes is that
                # the catch is now known to rest on the shape-based last resort
                # ALONE: the registry record has gone stale against the bot's current
                # wording, and the next rewording may clear the structural shape too
                # and be filed as review feedback. That is invisible to the boolean,
                # which returns True either way — which is why the provenance seam
                # exists.
                #
                # The predicate is DIRECTIONAL — deliberately not "exactly one arm
                # fired". The mirror case, registry matched while the structural arm
                # did not, is the DESIGNED state for a whole class of refusals and
                # never decay: Sourcery's size notice ("your pull request is larger
                # than the review limit of …") is a COMPARISON, not an
                # "exceeded / reached / hit" statement, so it is invisible to the
                # structural arm BY CONSTRUCTION and its registry-only match is the
                # registry doing precisely the job it is load-bearing for. Reading
                # that as drift reported the architecture working as designed, which
                # is why the arm is named rather than counted.
                #
                # Scoped to a declared participation_evidence publish shape so the
                # signal is about an artifact the bot actually publishes when it
                # reviews; a body arriving in some other shape is not evidence its
                # review wording drifted.
                _drift_kind = comment.get('kind') or 'inline'
                if _drift_kind in bot_registry.participation_evidence(bot_kind):
                    _layers = refusal_layers(body, bot_kind)
                    if REFUSAL_LAYER_STRUCTURAL in _layers and REFUSAL_LAYER_REGISTRY not in _layers:
                        # The layer is named, never read positionally: the predicate
                        # above admits exactly one arm, so the recorded value cannot
                        # depend on the order ``refusal_layers`` happens to append in.
                        _key = (bot_kind, REFUSAL_LAYER_STRUCTURAL)
                        if _key not in _drift_seen:
                            _drift_seen.add(_key)
                            refusal_pattern_drift.append(
                                {'bot_kind': bot_kind, 'layer': REFUSAL_LAYER_STRUCTURAL}
                            )
            continue

        # Pre-filter 3: SELF-AUTHORED RESPONSE — the batched disposition comment
        # this workflow's own ``post_responses`` posted. Placed AFTER the refusal
        # branch (a refusal must never be swallowed by an earlier stage) and
        # BEFORE the noise filter, with its OWN counter rather than folding into
        # ``skipped_noise``: our own output is not acknowledgment noise. Without
        # this stage the reply is filed as a fresh pending finding, the pre-merge
        # barrier blocks on it, triage responds again, and the cycle never ends.
        if _is_self_authored_response(body):
            skipped_self_response += 1
            continue

        # Pre-filter 4: obvious noise — the shared acknowledgment/automation
        # regexes plus, for a known reviewer bot, that bot's per-registry literal
        # ignore markers (walkthrough headings, marketing footers, no-op reviews).
        if _is_obvious_noise(body, bot_kind):
            skipped_noise += 1
            continue

        # Pre-filter 5: UNRECOGNISED REFUSAL — the enumerative arm. A refusal that
        # reached NEITHER arm consulted at pre-filter 2 still files no finding and
        # still denies participation credit; what it cannot do is name what the bot
        # said, because no arm could read it. Placed HERE, immediately after the
        # noise filter, and that position is the whole design: a bot's own declared
        # clean-review text is short and anchor-less, so running this arm before the
        # noise filter would read every clean review as a refusal.
        #
        # Counted into ``skipped_refusal`` — the same counter pre-filter 2 uses — so
        # ``expected_stored`` stays balanced and this branch cannot trip the
        # ``(producer-mismatch)`` Q-Gate. The record is emitted unconditionally: the
        # predicate itself requires a REGISTERED bot (an unresolvable bot_kind takes
        # its own non-firing branch), so ``bot_kind`` is necessarily truthy here and
        # a guard on it would be one that can never be false.
        if _is_unrecognised_refusal(body, bot_kind):
            skipped_refusal += 1
            unrecognised_refusal.append(
                {
                    'bot_kind': bot_kind,
                    'layer': REFUSAL_LAYER_ENUMERATIVE,
                    # The withheld text, so the decision is auditable rather than a
                    # bare count — and so the phrasing to file is in the record.
                    'excerpt': body.strip()[:_UNRECOGNISED_REFUSAL_EXCERPT_CHARS],
                    # The mechanism that closes the gap, carried rather than described.
                    'registry_file': f'automatic-review/standards/{bot_kind}.md',
                    'registry_field': 'refusal_patterns',
                    'remedy': (
                        f'Add the excerpt phrasing to refusal_patterns in '
                        f'automatic-review/standards/{bot_kind}.md; the next fetch then '
                        f'recognises this body through the registry arm instead of here.'
                    ),
                }
            )
            continue

        kind = comment.get('kind') or 'inline'
        thread_id = comment.get('thread_id') or ''
        path = comment.get('path') or None
        line = comment.get('line') or None
        comment_id = comment.get('id') or 'unknown'

        # Participation classification (warn-but-ingest, NOT a filter). A comment
        # whose bot_kind falls outside required ∪ optional is still stored — the
        # bot is merely recorded as unclassified so the caller can surface the
        # configuration gap. This is deliberately NOT a `continue`: dropping the
        # comment would make a configuration omission silently destroy real review
        # signal, precisely when the operator had not yet considered that bot.
        if bot_kind and bot_kind not in classified_bots:
            unclassified_set.add(bot_kind)

        # Pre-filter 6: cross-iteration dedup keyed on
        # (bot_kind, comment_id, edit_term) for ALL bot kinds, thread-bearing and
        # thread_id-less alike. A comment already staged in a prior iteration MUST NOT
        # re-surface as a new pending finding when HEAD advances. Dropping the earlier
        # ``not thread_id`` restriction closes the same phantom loop for
        # thread-bearing bot comments, and pairing the id with bot_kind avoids a
        # collision between two distinct bots reusing a numeric comment id.
        #
        # THE EDIT TERM is the third term, and it is what makes the identity answer
        # "is this the same INFORMATION?" rather than merely "is this the same COMMENT?".
        # A bot that re-reviews by editing its one persistent comment in place keeps the
        # same ``comment_id`` forever: under the two-term key, an edit that replaced a
        # clean Guide with a real finding was dropped as a duplicate while the currency
        # test credited the bot as participating — so the reviewer read present and
        # clean, and its actual feedback never became a finding. Widening the key by the
        # edit term files the edited review and still dedupes an unchanged re-fetch,
        # because an unchanged comment carries an unchanged term.
        #
        # A PRE-UPGRADE row carries no edit term at all, so it can match no three-term
        # key. It dedupes on the two-term key against ANY edit term instead — otherwise
        # the first fetch after this widening landed would re-file a PR's entire comment
        # history once, which is a worse outcome than the defect being fixed.
        edit_term = _comment_edit_term(comment)
        if (bot_kind or '', comment_id) in legacy_comment_keys:
            skipped_duplicate += 1
            continue
        if (bot_kind or '', comment_id, edit_term) in existing_comment_keys:
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
            # The third dedup term, stamped so ``_existing_pr_comment_keys`` can
            # reconstruct the full identity from the store. Without it the widened key
            # would be write-only: every stored finding would read back as a
            # pre-upgrade row and the dedup would silently fall back to two terms.
            f'edit_term: {edit_term}',
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

    # Deny participation credit to a bot whose EVERY publish-shape comment was an
    # unrecognised refusal. Computed HERE, at assembly, from ``raw_comments`` — the
    # participation loop above is deliberately left unmodified.
    #
    # The all-quantifier is the whole point, and it mirrors the proven-set
    # subtraction already applied to ``stale_participation_bots`` below: a bot that
    # ALSO published a genuine review really did review this diff, so it keeps its
    # credit and the unrecognised refusal stays a diagnostic. Only a bot whose every
    # piece of admissible evidence was a refusal nobody could read loses the credit
    # — which is the defect being fixed, where such a bot reported as one that
    # reviewed and found nothing.
    #
    # The comment set is restricted to the bot's DECLARED publish shapes, so the
    # quantifier ranges over exactly the comments that could have granted the credit
    # in the first place. A bot with no such comment is not swept up: the empty set
    # would make ``all()`` vacuously true, so a non-empty evidence set is required.
    #
    # NOISE IS EXCLUDED FIRST, and that is a position precondition rather than a
    # refinement. ``_is_unrecognised_refusal`` is the enumerative arm, whose contract
    # places it AFTER the noise filter — its own defence-in-depth branch reproduces
    # only ``bot_registry.ignore_patterns``, one of the four arms ``_is_obvious_noise``
    # applies. Sweeping ``raw_comments`` unfiltered therefore ran the arm at a position
    # it does not hold at: a short, anchor-less noise comment from a registered bot
    # reads as an unrecognised refusal, and a bot whose every publish-shape comment was
    # such noise would lose its participation credit. That contradicts
    # ``automatic-review/SKILL.md`` item 1 — a bot that posted only noise is still
    # credited, because the evidence is computed before noise filtering. Excluding
    # noise here restores the arm to its documented position: the evidence set becomes
    # empty for a noise-only bot, the non-empty guard above declines to sweep it, and
    # the credit stands.
    unrecognised_only_bots: set[str] = set()
    for _credited_bot in participated:
        _shapes = bot_registry.participation_evidence(_credited_bot)
        _evidence_comments = [
            _c
            for _c in raw_comments
            if bot_kind_for_author(_c.get('author') or 'unknown') == _credited_bot
            and (_c.get('kind') or 'inline') in _shapes
            and not _is_obvious_noise(str(_c.get('body') or ''), _credited_bot)
        ]
        if _evidence_comments and all(
            _is_unrecognised_refusal(str(_c.get('body') or ''), _credited_bot)
            for _c in _evidence_comments
        ):
            unrecognised_only_bots.add(_credited_bot)

    count_stored = len(stored_hashes)
    # Duplicates skipped by the cross-iteration guard, refusals surfaced through
    # ``refused_bots``, and self-authored responses are all legitimate non-stores,
    # so they drop out of expected_stored alongside the noise skips — otherwise
    # every deduped comment, every surfaced refusal, and every correctly-excluded
    # self response would spuriously trip the producer-mismatch Q-Gate. An
    # unclassified bot's comments are NOT subtracted: under the warn-but-ingest
    # rule they are stored like any other, so they belong in expected_stored.
    expected_stored = (
        count_fetched - skipped_noise - skipped_duplicate - skipped_refusal - skipped_self_response
    )

    # Measure the diff ONLY when a size refusal was actually seen. A recorded cap
    # without the size that hit it is a claim the reader must take on trust, so the
    # measurement is what turns the gap from asserted into auditable — but it is a
    # provider round-trip, so it is gated on the rare branch that needs it rather
    # than paid on every fetch. An unmeasurable diff stays '' (UNKNOWN), never 0.
    #
    # Gated on the CAUSE, never on ``refused_size_caps``. Those two come apart exactly
    # where the measurement matters most: a size refusal whose notice states no figure
    # extracts no cap, so gating on the cap would leave the operator with NEITHER
    # number in the one case the feature exists to prevent — an unquantified gap.
    saw_size_refusal = any(cause == REFUSAL_CAUSE_SIZE for cause in refused_causes.values())
    measured_diff_size = measure_diff_size(args.pr_number) if saw_size_refusal else ''

    qgate_hash: str | None = None
    qgate_persist_failure: dict[str, str] | None = None
    if count_stored != expected_stored:
        # Producer-side mismatch — surfaced as a Q-Gate finding so the LLM
        # picks it up in the standard query path. Phase ``5-execute`` is the
        # canonical phase for execution-time producer issues.
        mismatch_detail = (
            f'count_fetched={count_fetched}, '
            f'count_skipped_noise={skipped_noise}, '
            f'count_skipped_duplicate={skipped_duplicate}, '
            f'count_skipped_refusal={skipped_refusal}, '
            f'count_skipped_self_response={skipped_self_response}, '
            f'count_stored={count_stored}, '
            f'expected_stored={expected_stored}, '
            f'failed_comment_ids={store_failures}'
        )
        mismatch_title = f'(producer-mismatch) github_pr fetch_findings PR #{pr_number}'
        # The mismatch finding's whole purpose is to report that findings were
        # lost — a rejected persist would lose it in turn, so
        # ``add_qgate_finding_checked`` surfaces the rejection on the returned
        # tuple instead of leaving it inferable only from ``hash_id``. The
        # enclosing status stays ``success``: the fetch itself succeeded, and
        # the persist failure travels as its own field.
        qgate_hash, qgate_persist_failure = add_qgate_finding_checked(
            plan_id=plan_id,
            phase='5-execute',
            source='qgate',
            finding_type='pr-comment',
            title=mismatch_title,
            detail=mismatch_detail,
        )

    # Termination guarantee — state-free. Every turn of the respond → re-fetch
    # cycle leaves one permanent self-response comment on the PR, so the PR's own
    # comment list is the iteration counter: no new state store, no new config
    # key. At the bound the exhaustion is REPORTED as a Q-Gate finding requiring
    # an operator decision, never passed silently — the same checked-persist
    # contract the ``(producer-mismatch)`` finding above uses, so a rejected
    # persist cannot lose the report.
    #
    # The counter is the CURRENT cycle's trailing run, not the cumulative
    # ``skipped_self_response`` over the PR's whole history: this fetch is
    # ``unresolved_only=False``, so the cumulative figure includes every
    # already-converged cycle and would report a loop on any PR that simply
    # completed three normal triage rounds. ``skipped_self_response`` remains the
    # honest total of what the filter dropped (it must, for ``expected_stored``);
    # only the loop predicate reads the narrower signal.
    current_cycle_self_response = _current_cycle_self_response_count(raw_comments)
    self_response_loop_detected = current_cycle_self_response >= _SELF_RESPONSE_LOOP_BOUND
    loop_hash: str | None = None
    loop_persist_failure: dict[str, str] | None = None
    if self_response_loop_detected:
        loop_hash, loop_persist_failure = add_qgate_finding_checked(
            plan_id=plan_id,
            phase='5-execute',
            source='qgate',
            finding_type='pr-comment',
            title=f'(self-response-loop) github_pr fetch_findings PR #{pr_number}',
            detail=(
                f'count_self_response_current_cycle={current_cycle_self_response} reached '
                f'_SELF_RESPONSE_LOOP_BOUND={_SELF_RESPONSE_LOOP_BOUND} on PR #{pr_number} '
                f'(count_skipped_self_response={skipped_self_response} over the PR\'s full history). '
                'The respond -> re-fetch cycle is not converging: every pass leaves another '
                'self-authored response comment on the PR, with no reviewer activity in between. '
                'Operator decision required.'
            ),
        )

    result: dict[str, Any] = {
        'status': 'success',
        'operation': 'fetch_findings',
        'provider': 'github',
        'pr_number': pr_number,
        'plan_id': plan_id,
        'count_fetched': count_fetched,
        'count_skipped_noise': skipped_noise,
        'count_skipped_duplicate': skipped_duplicate,
        'count_skipped_refusal': skipped_refusal,
        'count_skipped_self_response': skipped_self_response,
        'count_self_response_current_cycle': current_cycle_self_response,
        'self_response_loop_detected': self_response_loop_detected,
        'self_response_loop_hash_id': loop_hash,
        'count_stored': count_stored,
        # Bots whose every publish-shape comment was an unrecognised refusal are
        # subtracted here — the same shape as the stale-participation subtraction
        # below. A bot with any genuine review keeps its credit.
        'participated_bots': [
            {'bot_kind': bot, 'evidence_kind': participated[bot]}
            for bot in sorted(participated)
            if bot not in unrecognised_only_bots
        ],
        # The proven set is SUBTRACTED before emitting: a bot with one stale comment
        # and one fresh one is a participant, not a stale publisher. Without the
        # subtraction the same bot would appear in both sets and the classifier's
        # branch order would be doing work the producer should have settled.
        'stale_participation_bots': [
            {'bot_kind': bot, 'evidence_kind': stale_participation[bot]}
            for bot in sorted(stale_participation)
            if bot not in participated
        ],
        # Whether the merge candidate could be READ at all. It reports the read, and
        # nothing else: ``fetch_pr_head_sha`` returns '' on every failure path, so a
        # false here is "the head is unresolvable", never a verdict about any bot that
        # an operator could act on. The bots it affects travel in their own set below
        # rather than being folded into either existing one — which is what keeps the
        # unreadable case legible instead of actionable-looking.
        'merge_candidate_sha_resolved': bool(reviewed_commit_sha),
        # The THIRD, DISJOINT outcome — same record shape as the two sets above, and
        # subtracted against the proven set for the same reason. Disjointness from
        # ``stale_participation_bots`` is structural rather than enforced here: the head
        # read is per-FETCH, so a fetch either resolved the merge candidate (nothing can
        # be undecidable) or did not (nothing can be stale).
        #
        # ⚠ PRODUCER-SIDE DISCLOSURE ONLY: ``review_completeness``'s taxonomy has no
        # member for this state yet, so no consumer routes on it. Widening the
        # classifier is a plan of its own; this field is the prerequisite it needs, and
        # the gap is REPORTED here rather than left to be discovered as an unreachable
        # branch.
        'undecidable_participation_bots': [
            {'bot_kind': bot, 'evidence_kind': undecidable_participation[bot]}
            for bot in sorted(undecidable_participation)
            if bot not in participated
        ],
        'refused_bots': sorted(refused_set),
        # The ENUMERATIVE arm's records — reported ALONGSIDE refused_bots, never
        # folded into it. A recognised refusal produces an empty list here, and an
        # unrecognised one names no bot in refused_bots; the two states are what the
        # split exists to keep apart. Each record carries the mechanism that closes
        # the gap (registry_file / registry_field / remedy), so the remedy ships
        # with the finding rather than as prose elsewhere.
        'unrecognised_refusal': unrecognised_refusal,
        # One record per bot whose notice the STRUCTURAL arm read while the bot's own
        # declared refusal_patterns did NOT — {bot_kind, layer}, where ``layer`` is
        # therefore always ``structural_fallback``. That is the actionable direction
        # and the only one recorded: the bot's declared refusal_patterns no longer
        # match its own wording, so the catch now rests on shape alone. A
        # registry-only match is NOT recorded — it is the registry arm doing the job
        # it is load-bearing for, not decay. Diagnostic only — it changes no verdict
        # and gates nothing.
        'refusal_pattern_drift': refusal_pattern_drift,
        # The orthogonal CAUSE axis for each refusing bot — {bot_kind, cause} with
        # cause in {size, quota}. Distinct from rate_limit_class's awaitability: it
        # names the remedy (a smaller diff vs backoff). Forwarded to
        # ``review_completeness check --refused-causes``.
        'refused_causes': [
            {'bot_kind': bot, 'cause': refused_causes[bot]} for bot in sorted(refused_causes)
        ],
        # The CAP each SIZE-refusing bot's own notice stated — {bot_kind, cap}, sparse.
        # A bot is absent here when it refused for quota, or when its size notice
        # stated no figure; an absent entry is an UNKNOWN cap the consumer reports as
        # such, never a zero and never a default. Forwarded to
        # ``review_completeness check --refusal-size-caps``, which reports it alongside
        # the cause so a recorded gap can be reconciled against the real diff size.
        'refused_size_caps': [
            {'bot_kind': bot, 'cap': refused_size_caps[bot]} for bot in sorted(refused_size_caps)
        ],
        # The OTHER half of an auditable gap: how big the refused diff actually was.
        # Measured only when a size refusal was seen (see above) — one cheap metadata
        # call on a path that fires rarely, and none at all on the common path — and
        # left '' when the read fails or no size refusal occurred. Its unit rides
        # inside the value because it is NOT the reviewer's unit; see
        # ``_github_pr.measure_diff_size``.
        'measured_diff_size': measured_diff_size,
        'unclassified_bots': sorted(unclassified_set),
        'stored_hash_ids': stored_hashes,
        'producer_mismatch_hash_id': qgate_hash,
    }
    if qgate_persist_failure is not None:
        result['qgate_persist_failed'] = True
        result['qgate_persist_failure'] = qgate_persist_failure
    if loop_persist_failure is not None:
        result['self_response_loop_persist_failed'] = True
        result['self_response_loop_persist_failure'] = loop_persist_failure
    return result


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
# PULL_REQUEST_RUNS SUBCOMMAND (the PR-wide not_triggered observable)
# ============================================================================


def cmd_pull_request_runs(args):
    """Report whether any ``pull_request``-event workflow run exists for the PR.

    Pure provider read — files no finding, triages nothing. The PR-WIDE observable
    behind the ``not_triggered`` participation state: when no ``pull_request`` run
    exists, nothing ever ran on account of this PR, so no bot could have published
    and a required bot's silence says nothing about that bot. The remedy is to
    trigger the review, which is the opposite of the remedy for ``absent`` (a bot
    that was asked and did not answer).

    Two states that MUST NOT be collapsed:

    - A ``pull_request`` run that EXISTS and concluded ``skipped`` — the workflow
      was triggered and declined to do work. The bot WAS asked, so this is
      ``not_triggered: false``.
    - NO ``pull_request`` run at all — nothing was ever triggered. This is the
      only ``not_triggered: true`` case.

    ``mergeable_state`` is never read, returned, or branched on: it is an
    asynchronously-computed mergeability signal, and a participation state keyed on
    it would depend on when the question happened to be asked.

    The body is the shared ``github_ops.pull_request_runs_result`` — the same one
    the ``ci checks pull-request-runs`` abstraction verb calls — so the two entry
    points cannot drift into different answers. It is reached by attribute access
    at call time (``_github.<name>``) rather than defined here and imported back,
    which would close an import cycle since this module imports ``github_ops``.
    Its typed ``unconfigured`` fail-loud guard is inherited unchanged.
    """
    return _github.pull_request_runs_result(args.pr_number)


# ============================================================================
# POST_RESPONSES SUBCOMMAND (apply triaged dispositions back to the PR)
# ============================================================================


def _build_batched_response_body(entries: list[tuple[str, str]]) -> str:
    """Render the single batched PR comment carrying every thread-less disposition.

    Args:
        entries: ``(comment_id, reply_body)`` pairs in finding order. A pair whose
            ``comment_id`` is empty is still rendered — the disposition must be
            transmitted even when its source anchor is unrecoverable.

    Returns:
        One markdown body with a heading and one anchored section per entry.

    The heading is ``_SELF_RESPONSE_HEADING`` — the SAME constant
    ``_is_self_authored_response`` recognizes on the fetch side, so this emitted
    shape and the shape that excludes it on re-fetch cannot drift apart.
    """
    parts = [_SELF_RESPONSE_HEADING, '']
    for comment_id, reply_body in entries:
        anchor = f'comment_id: `{comment_id}`' if comment_id else 'comment_id: _(unrecorded)_'
        parts.append(f'### In reply to {anchor}')
        parts.append('')
        parts.append(reply_body)
        parts.append('')
    return '\n'.join(parts).rstrip() + '\n'


def cmd_post_responses(args):
    """RESPOND verb: apply already-decided triage dispositions back to the PR.

    Reads every ``pr-comment`` finding whose ``resolution`` is a terminal triage
    disposition (``_RESPONDABLE_RESOLUTIONS``) **and whose recorded ``pr_number``
    is the PR being responded to** — keyed by each finding's own ``hash_id``
    (never positional pairing) — and transmits it through a three-way
    disposition. This verb makes NO triage decision; it only transmits decisions
    the triage pass already recorded.

    The findings store is plan-scoped, not PR-scoped, so the ``pr_number`` gate
    is what keeps a multi-PR plan's dispositions from cross-delivering. A row
    owned by another PR, or one whose ``pr_number`` was never recorded, is
    reported in ``skipped`` (reason ``belongs_to_pr_<n>`` /
    ``pr_number_unrecorded``) — visibly deferred, never silently dropped and
    never misdelivered.

    The routing predicate is the finding's **kind** — its thread-BEARING-ness,
    recorded in the detail block by ``cmd_fetch_findings`` — never the mere
    presence of an extractable ``thread_id``:

    1. **No ``resolution_detail``** — recorded in ``skipped`` with reason
       ``no_resolution_detail``. There is genuinely nothing to transmit.
    2. **Genuinely threadless kind** (``review_body`` / ``issue_comment``, see
       ``_THREADLESS_KINDS``) — collected across the whole loop and transmitted
       as ONE batched PR-level comment, each section anchored on its source
       ``comment_id``. Recorded in ``responded`` with ``transmit_mode:
       batched_issue_comment`` and ``resolved_on_provider: false`` — an issue
       comment has no resolvable thread, and reporting ``true`` would be a false
       signal. Batching is deliberate: ``review_body`` findings from every bot
       are thread-less, so a per-finding comment would spam the PR.
    3. **Thread-bearing kind** (``inline``, and any unrecognised or unrecorded
       kind) — thread-reply carrying the disposition, then resolve-thread.
       Recorded in ``responded`` with ``transmit_mode: thread_reply`` and
       ``resolved_on_provider: true``.

    A thread-bearing finding whose ``thread_id`` is empty or whose thread reply
    fails is **undeliverable, not threadless**: it lands in ``untransmitted``
    with a reason naming the missing or unusable thread and the run reports
    ``status: partial``. It is NEVER re-routed into the batch — a silent
    downgrade would report a disposition as delivered while the reviewer's own
    thread stays unanswered and unresolved.

    Every disposition that had something to say but could not be delivered — a
    missing thread on a thread-bearing finding, a failed thread-reply, a failed
    resolve-thread, or a failed batched post — lands in ``untransmitted`` and
    drives ``count_untransmitted`` and a top-level ``status`` of ``partial``.
    Nothing is folded into a generic skip and nothing is masked by an
    unconditional ``success``.

    **Idempotent across rounds, keyed on (finding, disposition).** The findings
    store is plan-scoped and persists between passes, and terminality
    (``_RESPONDABLE_RESOLUTIONS``) is the SELECTION criterion — a terminal finding
    re-qualifies on every pass. So after a reply is transmitted its finding is
    stamped with the ``responded`` marker (``mark_finding_responded``) in the same
    unit of work as the send, and a later pass skips any finding already carrying
    it (recorded in ``skipped`` with reason ``already responded``). Consequently
    ``count_responded`` reports only the dispositions transmitted THIS round, never
    a standing re-count of every terminal finding. A disposition that genuinely
    CHANGED between rounds is re-transmitted: ``manage-findings resolve`` clears the
    marker whenever it changes a finding's resolution or reply body, so the guard
    is a per-``(finding, disposition)`` key, not a blanket suppression.

    Fail-loud: returns a typed ``unconfigured`` status when GitHub is not
    authenticated, and the store's own ``findings_store_unresolved`` refusal when
    the plan directory is absent from the resolved root — never an empty finding
    list, which would report a clean "nothing to transmit" for a store that was
    never opened. A resolved store holding no ``pr-comment`` finding still returns
    the ordinary success with zero counts.
    """
    from _findings_core import mark_finding_responded, query_findings

    pr_number: int = args.pr_number
    plan_id: str = args.plan_id

    is_auth, auth_err = _github.check_auth()
    if not is_auth:
        return _unconfigured_result('post_responses', auth_err)

    # An UNREACHED store is returned as the store's own refusal, never reduced to an
    # empty finding list: an empty list here reports "every disposition transmitted,
    # nothing untransmitted" for a store that was never opened. A store that resolved
    # and simply holds no pr-comment finding still yields the genuine empty list below.
    findings_payload = _read_pr_comment_findings(query_findings, plan_id)
    if findings_payload.get('status') == 'error':
        return findings_payload
    findings = findings_payload.get('findings') or []

    responded: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    untransmitted: list[dict[str, str]] = []
    # Thread-less dispositions accumulate here and go out in ONE batched comment
    # after the loop: (hash_id, comment_id, reply_body).
    batch: list[tuple[str, str, str]] = []

    for finding in findings:
        hash_id = finding.get('hash_id', '')
        if finding.get('resolution') not in _RESPONDABLE_RESOLUTIONS:
            continue

        # Transmit only what belongs to THIS PR. The findings store is
        # plan-scoped, not PR-scoped, so a plan that gathered findings across
        # several PRs (a review-debt sweep, a multi-PR triage) holds rows owned
        # by PRs other than the one being responded to. Without this gate every
        # threadless row lands in the batched comment on whichever PR happens to
        # be passed, misdelivering other PRs' dispositions while the return still
        # reports count_untransmitted: 0 — a confidently green report for a
        # partly-misdelivered action.
        #
        # Thread-bearing rows are filtered too, even though a thread_id is a
        # global GraphQL node id that would reach its own PR regardless: the
        # caller loops once per PR, so an unfiltered pass would re-reply to and
        # re-resolve every other PR's threads on every iteration.
        finding_pr = _detail_field(finding.get('detail'), _PR_NUMBER_DETAIL)
        if finding_pr != str(pr_number):
            # Fail closed on an unattributable row rather than defaulting it to
            # the current PR: an unrecorded pr_number is precisely the case that
            # cannot be shown to belong here. It is recorded in `skipped`, so it
            # is visibly deferred rather than silently dropped or misdelivered.
            reason = 'pr_number_unrecorded' if not finding_pr else f'belongs_to_pr_{finding_pr}'
            skipped.append({'hash_id': hash_id, 'reason': reason})
            continue

        # Idempotency across rounds: a finding carrying the `responded` marker had
        # its reply transmitted on a prior pass, so skip it rather than re-post the
        # same disposition. Terminality (`_RESPONDABLE_RESOLUTIONS`) is the
        # SELECTION criterion here, never an exclusion — a terminal finding stays
        # eligible on every pass — so this explicit per-finding marker is what makes
        # the pass idempotent. `resolve_finding` CLEARS the marker when the
        # disposition changes, so a genuinely re-decided disposition re-qualifies
        # below: the guard is keyed on (finding, disposition), not a blanket
        # suppression. The marker is set in the same unit of work that sends the
        # reply (below), so a crash between send and mark leaves the finding
        # eligible for a safe retry rather than silently dropped.
        if finding.get('responded'):
            skipped.append({'hash_id': hash_id, 'reason': 'already responded'})
            continue

        reply_body = finding.get('resolution_detail') or ''
        if not reply_body:
            skipped.append({'hash_id': hash_id, 'reason': 'no_resolution_detail'})
            continue

        detail = finding.get('detail')
        kind = _detail_field(detail, _KIND_DETAIL)

        # Disposition 2 — genuinely threadless kind: the ONLY path into the
        # batch. Admission is decided by the kind alone, so a thread-bearing
        # finding can never reach the batch by losing its thread_id.
        if kind in _THREADLESS_KINDS:
            batch.append((hash_id, _detail_field(detail, _COMMENT_ID_DETAIL), reply_body))
            continue

        # Disposition 3 — thread-bearing kind (inline, or an unrecognised kind
        # that must not be assumed threadless). Its disposition belongs in the
        # reviewer's own thread; without a usable thread it is undeliverable and
        # is reported as such, never downgraded into the batch.
        thread_id = _detail_field(detail, _THREAD_ID_DETAIL)
        if not thread_id:
            untransmitted.append(
                {
                    'hash_id': hash_id,
                    'reason': (
                        f'thread-bearing finding (kind: {kind or "unrecorded"}) has no thread_id — '
                        'its in-thread reply is undeliverable and is not batched'
                    ),
                }
            )
            continue

        # Reply carrying the recorded disposition, then resolve — keyed by this
        # finding's own thread_id (relational, not positional).
        rc, _data, err = _github.run_graphql(THREAD_REPLY_MUTATION, {'threadId': thread_id, 'body': reply_body})
        if rc != 0:
            untransmitted.append({'hash_id': hash_id, 'reason': f'thread-reply failed: {err}'})
            continue
        rc2, _data2, err2 = _github.run_graphql(RESOLVE_THREAD_MUTATION, {'threadId': thread_id})
        if rc2 != 0:
            untransmitted.append({'hash_id': hash_id, 'reason': f'resolve-thread failed: {err2}'})
            continue
        responded.append(
            {
                'hash_id': hash_id,
                'thread_id': thread_id,
                'transmit_mode': 'thread_reply',
                'resolved_on_provider': True,
            }
        )
        # Stamp the idempotency marker in the SAME unit of work that transmitted
        # the reply, so a subsequent pass over this unchanged disposition skips it.
        mark_finding_responded(plan_id, hash_id)

    if batch:
        body = _build_batched_response_body([(comment_id, text) for _hash, comment_id, text in batch])
        post_result = _github.post_pr_comment(pr_number, body)
        if post_result.get('status') == 'success':
            for hash_id, comment_id, _text in batch:
                responded.append(
                    {
                        'hash_id': hash_id,
                        'comment_id': comment_id,
                        'transmit_mode': 'batched_issue_comment',
                        'resolved_on_provider': False,
                    }
                )
                # The batched post IS the send for these dispositions; stamp each
                # marker now that it succeeded, so a later pass skips them.
                mark_finding_responded(plan_id, hash_id)
        else:
            # The single post carries the WHOLE batch — one failure means every
            # disposition in it is untransmitted.
            reason = f'batched-comment post failed: {post_result.get("detail") or post_result.get("message") or ""}'
            for hash_id, _comment_id, _text in batch:
                untransmitted.append({'hash_id': hash_id, 'reason': reason})

    return {
        'status': 'partial' if untransmitted else 'success',
        'operation': 'post_responses',
        'provider': 'github',
        'pr_number': pr_number,
        'plan_id': plan_id,
        'count_responded': len(responded),
        'count_skipped': len(skipped),
        'count_untransmitted': len(untransmitted),
        'responded': responded,
        'skipped': skipped,
        'untransmitted': untransmitted,
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
                        'flags': ['--required-bots'],
                        'dest': 'required_bots',
                        'nargs': '?',
                        'const': '',
                        'default': '',
                        'help': (
                            'Comma-joined bot_kinds whose participation is REQUIRED (e.g. '
                            '"coderabbit,pr-agent"). A required bot\'s silence is a failure and gates the '
                            'review-completeness quorum. This list classifies, it does NOT admit: a comment '
                            'from a bot outside both lists is still ingested and its bot is reported in '
                            'unclassified_bots. May be supplied bare (no value), which reads as the empty '
                            'list — identical to omitting it.'
                        ),
                    },
                    {
                        'flags': ['--optional-bots'],
                        'dest': 'optional_bots',
                        'nargs': '?',
                        'const': '',
                        'default': '',
                        'help': (
                            'Comma-joined bot_kinds whose participation is OPTIONAL (e.g. "sourcery"). An '
                            "optional bot's silence is not a failure and never gates mark-done. Like "
                            '--required-bots this classifies rather than admits; see '
                            'automatic-review/standards/bot-participation-contract.md. May be supplied bare '
                            '(no value), which reads as the empty list — identical to omitting it.'
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
                'name': 'pull_request_runs',
                'help': (
                    'READ: report whether any pull_request-event workflow run exists for the PR '
                    '(the PR-wide not_triggered observable)'
                ),
                'handler': cmd_pull_request_runs,
                'args': [
                    {'flags': ['--pr-number'], 'dest': 'pr_number', 'type': int, 'required': True, 'help': 'PR number'},
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
