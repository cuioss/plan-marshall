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

**Refusal recognition lives here, and it is a STACK of independent arms rather
than a fixed pair.** This module is the shared home every refusal consumer reads
from, so the arms and the vocabulary that NAMES them
(:data:`REFUSAL_LAYERS`) are defined once here:

- the registry arm — the acting bot's own declared ``refusal_patterns``;
- the structural arm — :func:`_is_rate_limit_notice`, matching a notice by shape
  alone, which is what covers an unregistered or renamed bot;
- the enumerative arm — :func:`_is_unrecognised_refusal`, which recognises that a
  body neither of the others matched is nonetheless not review feedback.

No arm is a superset of another and the list is open: a further arm is added by
extending :data:`REFUSAL_LAYERS` and this paragraph, never by renumbering a count
stated somewhere else.

**The enumerative arm sits at a DIFFERENT pipeline position from the other two,
and that is why it is not folded into the shared** :func:`_is_refusal_notice`
**boolean.** The registry and structural arms are consulted BEFORE the per-bot
``ignore_patterns`` noise filter; the enumerative arm must run AFTER it, because
a bot's own declared clean-review text is short and anchor-less and would
otherwise be read as a refusal. Folding it into the shared boolean would move it
in front of that filter at every one of the boolean's call sites.

**Error direction on a missing input.** The enumerative arm TIGHTENS a predicate,
so the failure it can introduce — withholding a genuine short review — blocks a
merge, while the failure it removes is silent. Every fallible input therefore has
its own named NON-firing branch, and the absent-threshold branch in particular is
non-firing by construction: with no measured threshold the arm never fires and
every consumer behaves exactly as it did before the arm existed.
"""

import argparse
import json
import re
from datetime import UTC, datetime
from urllib.parse import quote

import bot_registry
import github_ops
from ci_base import (
    AUTO_MERGE_ROUTING_NOTE,
    BODY_KIND_PR_CREATE,
    BODY_KIND_PR_EDIT,
    BODY_KIND_PR_REPLY,
    BODY_KIND_PR_THREAD_REPLY,
    LANDING_STATES,
    MERGE_QUEUE_ELIGIBLE_CONFIGURED,
    delete_consumed_body,
    derive_landing_state,
    make_error,
    make_pr_number_handler,
    prepare_body,
    read_and_consume_body,
)

# ---------------------------------------------------------------------------
# Bot-agnostic rate-limit / service-notice detection (any reviewer bot)
# ---------------------------------------------------------------------------
#
# When a reviewer bot is rate-limited (or otherwise cannot review) it posts a
# short status notice IN PLACE OF a review — CodeRabbit's ``Review limit
# reached`` notice, a Sourcery size-limit note, or an arbitrary unknown/renamed
# bot's equivalent. Such a notice carries no actionable feedback, so it files no
# finding — but it is NOT noise: it is positive evidence the bot DECLINED, and
# every consumer must branch on it (see :func:`_is_refusal_notice`). Recognition is
# author-agnostic so it does not hardcode a single bot's comment shape.
#
# The recognizer is two-part for precision, applied uniformly to any bot: it
# requires BOTH (a) a LIMIT-EXCEEDED STATEMENT — an explicit "<limit>
# exceeded/reached/hit" or "exceeded the limit for the number of ..." body
# sentence — AND (b) a NOTICE SHAPE — a status-notice presentation (a GitHub
# alert callout, a markdown heading whose leading text IS the limit phrase, or a
# "review will resume / try again / posted in place of a review" service tail).
# Requiring both signals conjunctively is load-bearing
# for precision: a genuine review comment that merely mentions "rate limit" in
# prose — without a limit-EXCEEDED statement AND without a notice shape — is
# never misclassified as a refusal. The verbs are notice-voiced ("exceeded",
# "reached") rather than review-voiced ("exceeds", "may exceed"), so a review
# discussing a rate limit stays a finding.
#
# The comment body is newline-flattened to a single line by
# ``fetch_pr_comments_data`` before this detector runs, so the markers are
# searched unanchored (no ``^`` / ``re.MULTILINE``) — the callout prefix, the
# heading marker, and the limit phrase all land on the same flattened line.
_RATE_LIMIT_PHRASE = (
    r'(?:rate[\s-]?limit(?:ed|s)?'
    r'|(?:weekly|daily|monthly|hourly|usage|review|request|api)(?:[\s-]\w+){0,2}[\s-]limits?)'
)

# (a) LIMIT-EXCEEDED STATEMENT — the notice's "you hit a limit" sentence.
_RATE_LIMIT_EXCEEDED_MARKERS: tuple[re.Pattern[str], ...] = (
    # A real observed notice phrasing: the limit statement spelled out as a
    # sentence rather than as "<limit> exceeded", which the next marker catches.
    re.compile(r'exceeded the limit for the number of', re.IGNORECASE),
    # "<limit> [has been|is|was] exceeded/reached/hit" — the limit phrase bound
    # tightly to a notice-voiced past-tense verb. "exceeds" / "may exceed"
    # (review voice) deliberately does NOT match.
    re.compile(
        rf'\b{_RATE_LIMIT_PHRASE}\s+(?:has\s+been\s+|is\s+|was\s+)?(?:exceeded|reached|hit)\b',
        re.IGNORECASE,
    ),
    # "reached/hit your <limit>" — the bot addressing the account's quota.
    re.compile(
        rf'\b(?:exceeded|reached|hit)\s+(?:your|the|its|our|my)\s+(?:\w+\s+){{0,3}}?{_RATE_LIMIT_PHRASE}\b',
        re.IGNORECASE,
    ),
)

# (b) NOTICE SHAPE — the "posted in place of a review" presentation.
_RATE_LIMIT_NOTICE_SHAPE_MARKERS: tuple[re.Pattern[str], ...] = (
    # GitHub alert callout (``> [!WARNING]`` etc.) — status-notice presentation.
    re.compile(r'>\s*\[!(?:WARNING|CAUTION|IMPORTANT|NOTE|TIP)\]', re.IGNORECASE),
    # Markdown heading whose leading text IS the rate/usage-limit phrase (only a
    # short emoji/symbol prefix allowed before it), e.g. ``## Rate limit
    # exceeded`` / ``### Weekly review limit reached``. A heading about something
    # else does not match, even after newline-flattening.
    re.compile(rf'#{{1,6}}\s+\W{{0,4}}{_RATE_LIMIT_PHRASE}\b', re.IGNORECASE),
    # Service-notice tail: the review is deferred/skipped and will resume.
    re.compile(
        r'\b(?:will\s+resume|resets?\s+(?:at|in|on)|try\s+again\s+(?:in|later|after)'
        r'|in\s+place\s+of\s+a\s+review|posted\s+in\s+place'
        r'|unable\s+to\s+(?:complete|review|generate)|paused\s+(?:the\s+)?review)\b',
        re.IGNORECASE,
    ),
)


def _is_rate_limit_notice(body: str) -> bool:
    """Return True when a comment ``body`` is a bot-agnostic rate-limit / service notice.

    Detects a rate-limit / service notice a reviewer bot posts in place of a
    review, independent of author. Requires BOTH a LIMIT-EXCEEDED statement
    (:data:`_RATE_LIMIT_EXCEEDED_MARKERS`) AND a NOTICE-SHAPE signal
    (:data:`_RATE_LIMIT_NOTICE_SHAPE_MARKERS`), so a notice is recognized by its
    structural signature with no author-specific literal.

    **This is the STRUCTURAL arm of the refusal-recognition stack, not its primary
    surface.** It covers an unknown / unregistered bot, and a phrasing not yet
    captured in the data layer whose PRESENTATION is still notice-shaped. A
    *registered* bot's OBSERVED refusal text belongs in that bot's
    ``automatic-review/standards/{bot_kind}.md`` ``refusal_patterns`` — a data
    record, not a regex.

    ``refusal_patterns`` is deliberately a DEDICATED field, never a reuse of
    ``ignore_patterns``: ``ignore_patterns`` lists the routine sections a bot emits
    on a *successful* review (walkthrough headings, learning notices), so matching
    refusals against it would classify ordinary successful reviews as refusals. The
    two lists answer different questions. See
    ``automatic-review/standards/bot-participation-contract.md``.

    Every refusal-recognition site (``_is_refusal_notice``, which
    ``github_pr.cmd_fetch_findings`` and :func:`_detect_rate_limited_bots` both read,
    plus ``github_re_review._match_bot_comment`` and
    ``github_re_review._match_review``) is expected to consult this structural arm
    ALONGSIDE the registry data arm and the other arms of the stack — see
    :data:`REFUSAL_LAYERS` for the arms currently defined. No arm is a superset of
    another, and a refusal recognized here but absent from the registry is a signal
    that the bot's ``refusal_patterns`` need the observed phrasing added. A refusal
    that reaches NONE of the arms consulted before the noise filter is picked up
    later by the enumerative arm (:func:`_is_unrecognised_refusal`), which runs at a
    different pipeline position — see this module's docstring.

    Precision is load-bearing: a genuine review comment that merely mentions a
    rate limit in prose (no limit-exceeded statement, no notice shape) is not
    matched.
    """
    if not body:
        return False
    has_exceeded = any(marker.search(body) for marker in _RATE_LIMIT_EXCEEDED_MARKERS)
    has_shape = any(marker.search(body) for marker in _RATE_LIMIT_NOTICE_SHAPE_MARKERS)
    return has_exceeded and has_shape


def _is_refusal_notice(body: str, bot_kind: str | None = None) -> bool:
    """Return True when ``body`` is a REFUSAL to review — by registry data or by shape.

    The recognition seam every refusal consumer reads BEFORE the per-bot
    ``ignore_patterns`` noise filter. It consults the arms of the stack that are
    answerable at that position — no arm being a superset of another is why more
    than one is consulted at all:

    - **Registry data layer** — the bot's own ``refusal_patterns`` from
      ``automatic-review/standards/{bot_kind}.md``. Load-bearing rather than
      redundant: Sourcery's observed refusal ("your pull request is larger than the
      review limit of …") is invisible to the structural layer, because "larger
      than the review limit of" is a comparison, not an "exceeded / reached / hit"
      statement.
    - **Structural last-resort layer** — :func:`_is_rate_limit_notice`, recognizing
      a notice by shape alone, which is what covers an unregistered or renamed bot
      and a notice-shaped phrasing not yet filed in the registry.

    **This boolean's contract is exactly "did an arm answerable BEFORE the noise
    filter recognise this body?" — not "is this body a refusal?".** A refusal no arm
    here matched is recognised later by the enumerative arm
    (:func:`_is_unrecognised_refusal`), which cannot run at this position; see this
    module's docstring for why. A caller that needs the whole stack must consult
    both seams, and a ``False`` from this function is therefore never on its own
    evidence that the bot reviewed.

    ``refusal_patterns`` is deliberately NOT ``ignore_patterns``: the latter lists
    the routine sections of a *successful* review, so reading it here would report
    every reviewing bot as refusing.

    **A refusal is positive evidence of NON-participation, never noise.** Callers
    MUST branch on it — surfacing the refusing bot so the completeness / quorum
    layer sees a refusal member — rather than drop it. That member is derived by
    ``automatic-review/scripts/review_completeness.py``, which maps the bot's
    declared ``rate_limit_class`` by DEFAULT and applies two per-refusal overrides on
    top of it (a diff-size ceiling, and a refusal no recognition arm matched); the
    mapping is that module's to state, and is deliberately not restated as a fixed
    correspondence here. Dropping the refusal is precisely what let a PR whose every
    required reviewer refused report a clean, complete review with substantively
    zero review coverage.

    **DERIVED from :func:`refusal_layers`, never a parallel implementation.** That
    function is the provenance seam reporting WHICH arms fired; this boolean is its
    "did any of them?" projection. Deriving rather than duplicating is what stops
    the two drifting into disagreement about what counts as a refusal — a drift
    that would be invisible precisely because each reads correctly on its own.
    """
    return bool(refusal_layers(body, bot_kind))


# ---------------------------------------------------------------------------
# The refusal-recognition layer vocabulary — ONE definition, read by every
# consumer that reports WHICH arm recognised a refusal
# ---------------------------------------------------------------------------
#
# ``github_re_review._refusal_record`` reports the arm that fired so a reader can
# tell a registry-declared refusal from one recognised by shape alone, and
# ``github_pr.cmd_fetch_findings`` reports the same vocabulary on the record it
# emits for a refusal no earlier arm matched. Both read these names from here, so
# the two records are directly comparable and there is exactly one place a new arm
# is named.
#
# The two pre-existing spellings are preserved BYTE-IDENTICALLY from when they were
# inline literals in ``github_re_review``: every stored envelope and every existing
# assertion comparing against them keeps its meaning.

#: The acting bot's own declared ``refusal_patterns`` matched the body.
REFUSAL_LAYER_REGISTRY = 'registry_refusal_patterns'

#: :func:`_is_rate_limit_notice` matched the body by its notice SHAPE alone.
REFUSAL_LAYER_STRUCTURAL = 'structural_fallback'

#: :func:`_is_unrecognised_refusal` matched — no earlier arm recognised the body,
#: but it is not review feedback either. Carries strictly LESS information than the
#: other two: it says the stack failed to read the notice, not what the notice said.
REFUSAL_LAYER_ENUMERATIVE = 'enumerative_unrecognised'

#: The arms currently defined, in the order they are consulted. Consumers that
#: iterate or validate layer values MUST derive their population from this tuple
#: rather than restating the members, so adding an arm cannot leave a consumer
#: silently iterating a stale, shorter set.
REFUSAL_LAYERS = (
    REFUSAL_LAYER_REGISTRY,
    REFUSAL_LAYER_STRUCTURAL,
    REFUSAL_LAYER_ENUMERATIVE,
)


def refusal_layers(body: str, bot_kind: str | None = None) -> list[str]:
    """Return EVERY pre-noise-filter arm that recognises ``body``, in consult order.

    The provenance seam beside :func:`_is_refusal_notice`. The boolean answers
    *whether* an arm recognised the body and necessarily collapses the arms
    together; this reports WHICH ones did, so a caller can tell a registry-declared
    refusal from one recognised by shape alone — and, crucially, can see when the
    two DISAGREE.

    **Disagreement is the observable this seam exists to expose.** A body the
    structural arm recognises while the acting bot's own ``refusal_patterns`` do
    NOT is a bot whose declared wording has DRIFTED: the notice is still being
    caught, but only by the shape-based last resort, so the registry record is
    stale and the next rewording may fall through both arms and be filed as review
    feedback. That is invisible to the boolean, which returns the same ``True``
    whether one arm fired or both.

    Scope matches the boolean's EXACTLY — only the arms answerable BEFORE the
    per-bot ``ignore_patterns`` noise filter. The enumerative arm
    (:func:`_is_unrecognised_refusal`) runs at a different pipeline position and is
    deliberately absent here; see this module's docstring for why it cannot be
    folded in. Its name is still part of :data:`REFUSAL_LAYERS`, so a consumer
    validating a layer value against that vocabulary stays correct.

    Returns ``[]`` when no arm here recognises the body — the same information the
    boolean's ``False`` carries, and never a claim that the body is review
    feedback.
    """
    if not body:
        return []
    layers: list[str] = []
    if bot_kind and any(marker in body for marker in bot_registry.refusal_patterns(bot_kind)):
        layers.append(REFUSAL_LAYER_REGISTRY)
    if _is_rate_limit_notice(body):
        layers.append(REFUSAL_LAYER_STRUCTURAL)
    return layers


# ---------------------------------------------------------------------------
# The enumerative arm — recognising a refusal no earlier arm matched
# ---------------------------------------------------------------------------

#: Upper bound (in characters, exclusive) on the flattened body length below which
#: an anchor-less comment from a registered bot is read as an unrecognised refusal.
#:
#: ``None`` means NO THRESHOLD WAS DERIVED, and it is the shipped value. The bound
#: is defined to be the shortest GENUINE review comment actually observed in the
#: finding corpus; the measurement that would derive it enumerated a corpus of 1
#: plan holding 0 ``pr-comment`` findings, so no genuine review comment was
#: observed and no bound is derivable from evidence.
#:
#: A guessed value is deliberately NOT substituted. This arm errs in the blocking
#: direction — a genuine short review it mistakes for a refusal withholds real
#: feedback and blocks a merge — so an unmeasured bound would trade a silent
#: failure for a loud one on no evidence. With ``None`` the arm never fires and
#: every consumer behaves exactly as it did before the arm existed, which is the
#: non-firing branch by construction rather than by falling through an ``else``.
#:
#: Populate it from a real measurement over a non-empty corpus, never by estimate.
UNRECOGNISED_REFUSAL_MAX_CHARS: int | None = None

#: Markers whose presence proves a body carries a CODE REFERENCE, and therefore
#: that it is review feedback rather than a status notice. Any one of them vetoes
#: the enumerative arm.
_CODE_ANCHOR_MARKERS: tuple[re.Pattern[str], ...] = (
    # Fenced code block (``` or ~~~), the carrier of a suggested patch.
    re.compile(r'```|~~~'),
    # Inline code span — a single backtick pair around at least one character.
    re.compile(r'`[^`]+`'),
    # Diff hunk header, e.g. ``@@ -12,7 +12,9 @@``.
    re.compile(r'@@[^@]*@@'),
    # ``path/to/file.ext:123`` — a file:line anchor pointing into the diff.
    re.compile(r'\b[\w./-]+\.[A-Za-z0-9]{1,10}:\d+\b'),
    # A ``<details>`` disclosure block — the structural carrier of a finding.
    re.compile(r'<details', re.IGNORECASE),
)


def _has_code_anchor(body: str) -> bool:
    """Return True when ``body`` carries any code-reference anchor.

    A body pointing at code is review feedback, whatever its length. This is the
    veto that keeps a short-but-genuine review out of the enumerative arm.
    """
    return any(marker.search(body) for marker in _CODE_ANCHOR_MARKERS)


def _is_unrecognised_refusal(body: str, bot_kind: str | None = None) -> bool:
    """Return True when ``body`` is a refusal NO earlier recognition arm matched.

    The enumerative arm of the refusal-recognition stack, and the one that closes
    the gap where a reworded refusal is filed as ordinary review feedback while its
    author is credited as a participant. It is called by BOTH refusal consumers —
    ``github_pr.cmd_fetch_findings``'s pre-filter chain and
    ``github_re_review._ReReviewStrategy._refusal_record`` — from this one
    definition; there is no second implementation.

    It fires only when EVERY one of the following holds:

    - ``bot_kind`` resolves to a REGISTERED bot. A human's short comment is never
      an unrecognised refusal.
    - :func:`_is_refusal_notice` already declined, i.e. neither the registry arm nor
      the structural arm recognised the body. This arm never overrides an arm that
      DID read the notice.
    - the body carries no marker from that bot's own ``ignore_patterns`` — its
      declared clean-review text is never a refusal.
    - the body carries no code-reference anchor at all (:func:`_has_code_anchor`).
    - the flattened body is shorter than
      :data:`UNRECOGNISED_REFUSAL_MAX_CHARS`.

    **Position in the pipeline is load-bearing.** This arm MUST be consulted AFTER
    the acting bot's ``ignore_patterns`` noise filter has run. A bot's own declared
    clean-review text (CodeRabbit's ``No actionable comments were generated``) is
    short, anchor-less, and authored by a registered bot — it satisfies every
    condition above, and only the noise filter having already removed it keeps this
    arm from reading it as a refusal.

    **Every fallible input has its own named NON-firing branch**, rather than one
    ``else`` covering all of them. A predicate assembled from fallible reads has
    more outcomes than it has truth values, and folding the missing-input outcome
    into the ``False`` branch would assert "this is not a refusal" on evidence
    nobody gathered. The absent-threshold branch is the one that matters most: with
    no measured bound the arm returns ``False`` for every input, so it is inert and
    both consumers behave exactly as they did before it existed.
    """
    # Non-firing branch 1 — no derived threshold. Deliberately FIRST: with no
    # measured bound there is no admissible way to fire, whatever the other inputs
    # say, and this is the branch that keeps the tightening off an unmeasured
    # corpus.
    threshold = UNRECOGNISED_REFUSAL_MAX_CHARS
    if threshold is None:
        return False

    # Non-firing branch 2 — no body to classify.
    if not body:
        return False

    # Non-firing branch 3 — unresolvable or unregistered author. Normalised on both
    # sides, matching how every other registry-sourced membership test compares.
    if not bot_kind:
        return False
    normalized = bot_kind.strip().lower()
    if normalized not in {kind.strip().lower() for kind in bot_registry.bot_kinds()}:
        return False

    # Non-firing branch 4 — an earlier arm already recognised this body. This arm
    # reports only what the others could not read.
    if _is_refusal_notice(body, bot_kind):
        return False

    # Non-firing branch 5 — the acting bot's OWN declared clean-review text. The
    # call-site ordering (this arm runs after the noise filter) already keeps such
    # a body away from here, but asserting it locally makes the guarantee a
    # property of the PREDICATE rather than of every caller's stage order — so a
    # future consumer that calls this arm too early still cannot read a bot's
    # clean review as a refusal. Defence in depth, not a replacement for the
    # ordering: see this module's docstring for why the ordering is what the
    # design rests on.
    if any(marker in body for marker in bot_registry.ignore_patterns(bot_kind)):
        return False

    # Non-firing branch 6 — the body points at code, so it is review feedback.
    if _has_code_anchor(body):
        return False

    # Non-firing branch 7 — the body is long enough to be a genuine review.
    return len(body.strip()) < threshold


# The orthogonal CAUSE axis for a detected refusal — distinct from ``rate_limit_class``
# (the awaitability axis). A refusal is caused by a diff-SIZE ceiling (remedy: a
# smaller diff) or by a rate/budget QUOTA (remedy: backoff / retry).
REFUSAL_CAUSE_SIZE = 'size'
REFUSAL_CAUSE_QUOTA = 'quota'


def refusal_cause(body: str, bot_kind: str | None = None) -> str:
    """Classify a detected refusal's CAUSE — ``'size'`` or ``'quota'``.

    The orthogonal companion to ``rate_limit_class`` (awaitability): whether the bot
    declined because the DIFF is too big (``size``) or because a rate/budget limit was
    hit (``quota``). The two axes are independent — a size refusal and a quota refusal
    can share the same ``hard_quota`` awaitability (both of Sourcery's do) — which is
    why the cause cannot be read off ``rate_limit_class`` and needs its own registry
    overlay, ``refusal_size_patterns``.

    ``size`` iff ``body`` matches one of the bot's declared ``refusal_size_patterns``;
    every other refusal is ``quota``, the rate/budget default. This assumes ``body`` is
    ALREADY a refusal — the caller gates on :func:`_is_refusal_notice` — so it does not
    re-detect. A structurally-detected refusal from an unregistered bot declares no
    size pattern and so classifies ``quota``, which is correct: the rate-limit shape the
    structural recogniser matches ("exceeded / reached / hit your limit") is a quota
    shape, while a size ceiling ("larger than the review limit of") is invisible to it
    and reaches recognition only through a declared pattern.
    """
    if bot_kind and any(marker in body for marker in bot_registry.refusal_size_patterns(bot_kind)):
        return REFUSAL_CAUSE_SIZE
    return REFUSAL_CAUSE_QUOTA


def refusal_size_cap(body: str, bot_kind: str | None = None) -> str:
    """Return the diff-size CAP ``body`` states, or ``''`` when it states none.

    The structural counterpart of :func:`_extract_rate_limit_eta`, and deliberately
    its mirror image: an awaitable refusal states WHEN its window reopens, a
    structural one states HOW BIG the diff was allowed to be. Both figures are read
    off the notice through per-bot registry regexes rather than encoded here, so no
    bot-name literal and no budget figure appears in this path.

    The cap is what makes a recorded coverage gap AUDITABLE — it can be reconciled
    against the diff that was actually refused — rather than merely asserted. That is
    why it is extracted from the bot's own notice at the moment of refusal instead of
    being declared as a constant: a declared figure goes stale silently when the
    provider changes its budget, and nothing would detect the drift.

    Returns ``''`` for a bot that declares no cap pattern, for a notice that states
    no figure, and for a body that is not a size refusal at all. The caller reports
    an empty cap as UNKNOWN and never substitutes a default — a cap nobody observed
    would make the gap look audited when it was not. A malformed registry pattern is
    skipped rather than raised, matching the ETA extractor: a bad registry edit must
    not break the producer's return path.
    """
    if not body or not bot_kind:
        return ''
    for pattern in bot_registry.refusal_size_cap_patterns(bot_kind):
        try:
            match = re.search(pattern, body, re.IGNORECASE)
        except re.error:
            continue
        if match is None:
            continue
        # A pattern that declares a group means "the cap is THAT group"; one that
        # declares none means "the cap is the whole match". Honour the declaration
        # rather than silently substituting one for the other.
        #
        # ``match.groups()`` is TRUTHY for a one-tuple holding ``None`` — a pattern whose
        # first group sits in a branch that did not participate (``limit of (?:[0-9]+)|(x)``)
        # matches, reports groups, and yields ``None``. Taking ``.strip()`` on that raised
        # an AttributeError out of the producer's whole return path, which is exactly the
        # failure the docstring above promises cannot happen: the ``re.error`` guard covers
        # a pattern that will not COMPILE, not one that compiles and captures nothing.
        #
        # A declared group that captured nothing yields NO figure and moves to the next
        # pattern — never a fallback to ``group(0)``. That fallback is the wrong kind of
        # graceful: on ``review limit of ([0-9]*)`` against a notice stating no number it
        # returns the prose ``"review limit of"``, which is comma-free, survives the CLI,
        # and renders as ``cap: review limit of`` beside a real measurement — making the
        # gap look audited against a figure nobody observed, the precise thing the
        # unknown-cap discipline forbids. Unknown is the honest answer.
        if match.groups():
            captured = (match.group(1) or '').strip()
            if not captured:
                continue
        else:
            captured = match.group(0).strip()
            if not captured:
                continue
        # Commas are stripped because the cap crosses a COMMA-SEPARATED CLI boundary
        # (``--refusal-size-caps "bot:cap"``), where a thousands separator would split
        # one record into two malformed ones. Removing it also leaves a figure that
        # compares directly against a measured diff size, which is the whole point of
        # recording it.
        return captured.replace(',', '')
    return ''


def measure_diff_size(pr_number: int) -> str:
    """Return this PR's measured diff size as ``"{n} changed lines"``, or ``''``.

    The second half of an auditable coverage gap. A recorded cap says what the
    reviewer's ceiling was; without the size of the diff that hit it, a reader can
    only take the refusal's word for it. Recording both makes the gap checkable:
    the operator accepting it can see how far over the line the PR actually was.

    **The unit is stated in the value, and it is deliberately NOT the reviewer's
    unit.** A provider's ceiling is expressed in whatever it counts — Sourcery's is
    diff CHARACTERS — and counting those exactly means downloading the whole patch,
    which is most expensive precisely on the oversized PRs where this fires. Changed
    lines come from the PR's existing metadata for one cheap call. So the two figures
    are an ORDER-OF-MAGNITUDE comparison, not an equality check, and carrying the unit
    inside the string is what stops a reader treating "150000 diff characters" against
    "1240 changed lines" as an exact reconciliation.

    Returns ``''`` when the read fails, is unparseable, or reports no numbers —
    UNKNOWN, never a zero. A zero would read as "an empty diff was refused for being
    too big", which is a claim this function has no evidence for.
    """
    returncode, stdout, _stderr = github_ops.run_gh(
        ['pr', 'view', str(pr_number), '--json', 'additions,deletions']
    )
    if returncode != 0 or not stdout.strip():
        return ''
    try:
        payload = json.loads(stdout)
    except (ValueError, TypeError):
        return ''
    if not isinstance(payload, dict):
        return ''
    additions = payload.get('additions')
    deletions = payload.get('deletions')
    if not isinstance(additions, int) or not isinstance(deletions, int):
        return ''
    return f'{additions + deletions} changed lines'


def _extract_rate_limit_eta(body: str, bot_kind: str) -> str:
    """Return the reset ETA ``bot_kind`` stated in ``body``, or ``''`` when none.

    The ETA phrasings are registry data — each bot's ``rate_limit_eta_patterns``
    in its ``automatic-review/standards/{bot_kind}.md`` block — so no bot-name
    literal and no per-bot branch appears here. The first pattern that yields a
    figure wins; its first capturing group is the ETA when the pattern declares
    one, otherwise the whole match is used. A bot that declares no ETA patterns
    (or whose notice states no ETA) yields ``''`` — the caller treats an absent
    ETA as "unknown when the window reopens", never as "reopens now".

    A malformed pattern in the data layer is skipped rather than raised: a bad
    registry edit must not break the poll return path.

    A declared group that captured NOTHING is resolved exactly as
    :func:`refusal_size_cap` resolves it, and for the same reason.
    ``match.groups()`` is TRUTHY for a one-tuple holding ``None`` — a pattern whose
    first group sits in a branch that did not participate
    (``wait (?:[0-9]+ minutes)|(x)``) matches, reports groups, and yields ``None``;
    calling ``.strip()`` on that raised an AttributeError out of the poll's whole
    return path. That is precisely the failure the ``re.error`` guard does NOT
    cover: the guard catches a pattern that will not COMPILE, not one that compiles
    and captures nothing. Such a pattern yields NO figure and moves to the next
    pattern — there is deliberately no fallback from an empty group to ``group(0)``,
    which would hand back the surrounding prose as though it were an observed ETA.
    """
    for pattern in bot_registry.rate_limit_eta_patterns(bot_kind):
        try:
            match = re.search(pattern, body, re.IGNORECASE)
        except re.error:
            continue
        if match is None:
            continue
        captured = (match.group(1) or '').strip() if match.groups() else match.group(0).strip()
        if not captured:
            continue
        return captured
    return ''


def _detect_rate_limited_bots(comments: list[dict]) -> list[dict]:
    """Return one record per registered bot whose newest comment is a rate-limit notice.

    Generalizes the former single-bot discriminator to every registered
    ``bot_kind``: for each bot in the registry, select the comments that bot
    authored (resolving each comment's author through
    :func:`github_re_review.bot_kind_for_author`, which owns the ``[bot]``-suffix
    stripping and case-insensitive matching), pick that bot's newest comment by
    ``created_at``, and classify its body through the refusal-recognition arms that
    are answerable at this position. No bot-name literal appears in this path — the
    bot set, each bot's login, its refusal markers, its rate-limit class, and its ETA
    phrasings are all registry data.

    Classification goes through the shared :func:`_is_refusal_notice` seam, so this
    detector and the ``fetch_findings`` producer's pre-noise-filter stage recognize a
    refusal identically, from one place. See that function for why no single arm
    suffices on its own, and this module's docstring for the arms the stack
    currently defines — including the enumerative arm, which sits after the noise
    filter and so is deliberately outside this seam.

    Each detected bot yields ``{bot_kind, rate_limit_class, eta, cause, cap}``:

    - ``rate_limit_class`` distinguishes a window the caller can usefully await
      from a quota it cannot; it is registry data and fails closed to ``unknown``
      for a bot that declares none.
    - ``eta`` is the reset time the notice itself stated, or ``''`` when the
      notice stated none.
    - ``cause`` is the orthogonal SIZE-vs-QUOTA axis (:func:`refusal_cause`). A
      refusal caused by a per-PR diff ceiling is answered by a smaller diff, one
      caused by a rate/budget quota by backoff. The axes are INDEPENDENT — a size
      refusal and a quota refusal can share one ``rate_limit_class``, as both of
      Sourcery's do — so a consumer cannot derive the cause from the class, and
      carrying it explicitly is what stops the recovery path offering a wait for a
      ceiling that waiting does not move.
    - ``cap`` is the ceiling the size notice itself stated
      (:func:`refusal_size_cap`), or ``''`` when it stated none. An empty cap is
      reported as UNKNOWN and never defaulted: a figure nobody observed would make
      the recorded coverage gap look audited when it was not.

    Both fields are emitted for EVERY detected refusal rather than only a size one,
    so every consumer reads ONE record shape whatever the cause; on a quota refusal
    ``cause`` is ``quota`` and ``cap`` is ``''``.

    Bots that are NOT rate-limited are simply absent from the list, so an empty
    list means "no registered bot is rate-limited" — the same signal the removed
    scalar carried, without collapsing a three-bot pipeline into one boolean.
    Detection is best-effort: any absent or malformed field degrades to "not
    rate-limited" for that bot and never raises into the poll return path.
    """
    # Deferred import: ``github_re_review`` imports ``_is_rate_limit_notice``
    # from this module at import time, so a module-level import here would close
    # a cycle. Resolving the login map through ``bot_kind_for_author`` (rather
    # than re-deriving it locally) keeps the single source of truth for the
    # login -> bot_kind correspondence.
    import github_re_review

    detected: list[dict] = []
    for bot_kind in bot_registry.bot_kinds():
        bot_comments = [
            c
            for c in comments
            if isinstance(c, dict) and github_re_review.bot_kind_for_author(c.get('author')) == bot_kind
        ]
        if not bot_comments:
            continue
        newest = max(bot_comments, key=lambda c: str(c.get('created_at') or ''))
        body = str(newest.get('body') or '')
        if not _is_refusal_notice(body, bot_kind):
            continue
        detected.append(
            {
                'bot_kind': bot_kind,
                'rate_limit_class': bot_registry.rate_limit_class(bot_kind),
                'eta': _extract_rate_limit_eta(body, bot_kind),
                'cause': refusal_cause(body, bot_kind),
                'cap': refusal_size_cap(body, bot_kind),
            }
        )
    return detected


def _detect_movement_bots(comments: list[dict], wait_start: datetime) -> list[dict]:
    """Return one record per registered bot that EDITED a comment after ``wait_start``.

    The movement arm of the wait-for-comments completion predicate. A bot that
    re-reviews by editing its single persistent comment in place produces no
    growth in the unresolved count, so the count arm is structurally blind to it;
    this arm keys on timestamp movement instead. Only bots whose registry record
    declares ``participation_requires_update: true`` are considered — for a bot
    that appends a new comment per review, the count arm already is the movement
    signal, and consulting this arm for it would double-count.

    A bot matches when ALL of the following hold for one of its comments — the
    FULL identity, never the author key alone:

    - the comment's author resolves through ``github_re_review.bot_kind_for_author``
      to exactly that ``bot_kind``;
    - its body is not a refusal notice (:func:`_is_refusal_notice`) — a bot
      editing its comment to say it could NOT review is the bot talking about
      itself, not a re-review. Mirrors ``github_re_review._match_bot_comment``;
    - the LATER of its ``updated_at`` and ``created_at`` is strictly after
      ``wait_start``. Taking the later of the two is what makes an EDITED
      persistent comment count: ``created_at`` stops advancing after the first
      review.

    **A match proves a re-review ARRIVED, not that the diff was reviewed well.**
    The returned records report arrival only and must never be rendered as
    evidence of review quality.

    Fail-closed per ADR-009 on every divergent input: a non-``dict`` element in
    the externally-fetched ``comments`` list is filtered rather than matched, and
    a timestamp that fails to parse yields ``None`` from ``_parse_iso`` and is
    dropped from the comparison — it is a NON-match, never a match-anything
    wildcard. A comment with no parseable timestamp at all therefore never
    matches. ``_parse_iso`` normalizes a timezone-naive stamp to UTC, so it never
    raises against the aware ``wait_start``.

    No bot-name literal appears here: the bot set, each login, and the arm
    selection are all registry data.
    """
    # Deferred import for the same reason :func:`_detect_rate_limited_bots` uses
    # one: ``github_re_review`` imports from this module at import time, so a
    # module-level import here would close the cycle.
    import github_re_review

    matched: list[dict] = []
    for bot_kind in bot_registry.bot_kinds():
        if not bot_registry.participation_requires_update(bot_kind):
            continue
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if github_re_review.bot_kind_for_author(comment.get('author')) != bot_kind:
                continue
            if _is_refusal_notice(str(comment.get('body') or ''), bot_kind):
                continue
            stamps = [
                dt
                for dt in (
                    github_re_review._parse_iso(str(comment.get('updated_at') or '')),
                    github_re_review._parse_iso(str(comment.get('created_at') or '')),
                )
                if dt is not None
            ]
            if not stamps:
                continue
            if max(stamps) > wait_start:
                matched.append({'bot_kind': bot_kind})
                break
    return matched


def _detector_answerability() -> tuple[bool, str]:
    """Return ``(detector_answerable, unanswerable_reason)`` from the REGISTRY alone.

    Distinguishes a timeout whose observable could never have moved from one
    where the bots were simply silent — today both return an identical bare
    ``timed_out: true`` (ADR-014: a working-but-empty substrate must be
    distinguishable from an inert one).

    The await is unanswerable in exactly two registry states, and
    ``unanswerable_reason`` names which one fired:

    - no bot kinds are registered at all, so no arm has a subject; or
    - every registered bot declares an empty ``participation_evidence``, the
      fail-closed never-provable state.

    The signal is independent of the OBSERVED comment set: an await that starts
    with zero comments, or whose bots stay silent, is ``detector_answerable:
    true`` — a genuine timeout, not an unanswerable one.
    """
    bot_kinds = bot_registry.bot_kinds()
    if not bot_kinds:
        return False, 'no bot kinds are registered'
    if all(not bot_registry.participation_evidence(bot_kind) for bot_kind in bot_kinds):
        return False, 'every registered bot declares an empty participation_evidence'
    return True, ''


def cmd_pr_create(args: argparse.Namespace) -> dict:
    """Handle 'pr create' subcommand.

    The PR body comes from ONE source: the plan-bound body store, keyed by
    ``--plan-id`` [+ ``--slot``] — a prepared scratch file consumed here and
    deleted on success.

    A genuinely plan-less caller passes ``--plan-id NO_PLAN``, which resolves to
    the shared plan-less directory, so the SAME store serves it. That is why
    there is no longer a second body source to choose between, and no
    mutual-exclusion contract to validate.
    """
    # Check auth
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_create', err)

    # ``plan_id`` is read defensively via getattr so a direct-Namespace caller
    # that bypasses the argparse parser (where it is required=True) falls
    # through to the structured error instead of raising AttributeError.
    plan_id = getattr(args, 'plan_id', None)
    if not plan_id:
        return make_error(
            'pr_create',
            '--plan-id is required; it keys the prepared body store. Genuinely '
            'plan-less callers pass --plan-id NO_PLAN.',
        )

    body, err_dict = read_and_consume_body(plan_id, BODY_KIND_PR_CREATE, getattr(args, 'slot', None))
    if err_dict or body is None:
        return make_error('pr_create', (err_dict or {}).get('message', 'body not prepared'))

    # Build command
    gh_args = ['pr', 'create', '--title', args.title, '--body', body]
    if args.base:
        gh_args.extend(['--base', args.base])
    if args.draft:
        gh_args.append('--draft')
    if getattr(args, 'head', None):
        gh_args.extend(['--head', args.head])
    # Optional --label passthrough (repeatable). create-pr applies
    # `--label skip-bot-review` when the required_bots/optional_bots union is
    # empty AND the operator actually answered that way. Under the two-list model
    # the producer classifies rather than admits (warn-but-ingest), so the label
    # is the only suppression signal on that path — and the bots honor it
    # asymmetrically, so it is best-effort.
    for label in getattr(args, 'label', None) or []:
        gh_args.extend(['--label', label])

    # Execute
    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_create', 'Failed to create PR', stderr.strip())

    # Delete the consumed scratch body — success only, so a failed create leaves
    # the prepared body in place for the caller to retry.
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
    """Handle 'pr view' — read PR state by number, by branch, or for the current cwd HEAD.

    ``gh pr view`` takes a number, a URL, or a branch name in the SAME positional
    slot, so ``--pr-number`` and ``--head`` are a selector CHOICE rather than two
    code paths: whichever is supplied becomes that one positional. Supplying
    neither is the historical default (the PR for the current cwd HEAD); supplying
    both is a structured error, never a silent precedence rule.

    ``--pr-number`` is the selector a landing poll MUST use. Under a required
    platform merge queue the platform auto-deletes the head branch as the queue
    merges, so a ``--head``-keyed poll stops resolving at exactly the moment the
    terminal ``state: merged`` it waits for becomes observable. The PR number is
    stable across that deletion.

    The payload carries ``merge_commit_sha`` — the landing commit of a merged PR, or
    ``None`` when there is none (an open PR, or a provider reporting no merge commit).
    ``None`` is the EXPLICIT absent form and is never an empty string, because a
    consumer reading the SHA cannot distinguish ``''`` from a resolved value without
    re-deriving the PR's state. A read failure is not an absent SHA either: it surfaces
    as ``status: error`` from this verb, so absent-because-open and
    could-not-read stay distinguishable at the boundary. See
    ``github_ops.view_pr_data`` for the field's construction.
    """
    pr_number = getattr(args, 'pr_number', None)
    head = getattr(args, 'head', None)
    if pr_number and head:
        return make_error('pr_view', 'specify exactly one of --pr-number or --head, not both')
    return github_ops.view_pr_data(head=str(pr_number) if pr_number else head)


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


#: Upper bound on the PR listing for landing-state correlation. A single head
#: branch has at most a handful of PRs, so hitting this ceiling means the listing
#: may be truncated — which the handler treats as an unreadable (fail-closed)
#: result rather than a complete correlation.
_PR_LIST_LIMIT = 100


def _resolve_landing_branch(explicit: str | None) -> tuple[str | None, dict | None]:
    """Resolve the branch a landing-state query is about.

    Returns ``(branch, None)`` on success or ``(None, error_dict)`` on failure.
    An explicit ``--branch`` wins; otherwise the checked-out branch of the routed
    working tree is read via ``git rev-parse --abbrev-ref HEAD``. A detached HEAD
    (``rev-parse`` yields ``HEAD``) is an error, not a silent classification — a
    landing state must be about a NAMED branch.
    """
    if explicit and explicit.strip():
        return explicit.strip(), None
    rc, out, err = github_ops.run_git(['rev-parse', '--abbrev-ref', 'HEAD'])
    if rc != 0:
        return None, make_error('pr_landing_state', 'Could not resolve the current branch', err.strip())
    branch = out.strip()
    if not branch or branch == 'HEAD':
        return None, make_error(
            'pr_landing_state',
            'Refusing to classify a detached HEAD — pass --branch to name the branch explicitly',
            branch,
        )
    return branch, None


def _branch_tip_sha(branch: str) -> tuple[str | None, dict | None]:
    """Resolve ``branch``'s current tip SHA, or ``(None, error_dict)``.

    The tip SHA is what makes PR correlation revision-accurate: ``gh pr list
    --head`` returns EVERY PR ever opened from the branch NAME, including one that
    merged an earlier tip and left the name to be reused. Only a PR whose head is
    the branch's current tip speaks to the revision being classified, so a failure
    to resolve the tip is fatal — the verdict cannot be trusted without it.
    """
    rc, out, err = github_ops.run_git(['rev-parse', branch])
    if rc != 0:
        return None, make_error('pr_landing_state', f'Could not resolve the tip SHA of branch {branch!r}', err.strip())
    sha = out.strip()
    if not sha:
        return None, make_error('pr_landing_state', f'git rev-parse returned an empty tip SHA for branch {branch!r}')
    return sha, None


def _branch_pushed_state(branch: str) -> tuple[bool | None, dict | None]:
    """Return ``(pushed, None)`` or ``(None, error_dict)`` for ``branch``.

    ``git branch -r --contains <branch>`` lists the remote-tracking branches that
    contain the ref's tip; ``rc == 0`` with non-empty output proves the commit is
    on a remote, ``rc == 0`` with empty output proves it is not. A NON-zero exit
    is neither proof — it is an UNREADABLE result, returned as ``(None, error)``
    so the caller can fail closed rather than silently reading a git failure as
    ``unpushed``, which would clear the archive gate on evidence nobody read.
    """
    rc, out, err = github_ops.run_git(['branch', '-r', '--contains', branch])
    if rc != 0:
        return None, make_error(
            'pr_landing_state',
            f'Could not determine whether branch {branch!r} is on a remote',
            err.strip(),
        )
    return bool(out.strip()), None


def cmd_pr_landing_state(args: argparse.Namespace) -> dict:
    """Handle 'pr landing-state' — classify a branch's done-ness at the PR, not the commit.

    Automates the deterministic correlation a foreign task's done-ness requires —
    resolve the branch and its tip SHA, list the branch's PRs, keep only those
    whose head IS that tip, test remote containment, correlate — and returns
    exactly one member of :data:`ci_base.LANDING_STATES` (``merged`` / ``pr_open``
    / ``pushed_no_pr`` / ``unpushed``). The pure correlation is
    :func:`ci_base.derive_landing_state`; this handler only gathers its inputs.

    **Fails closed on unreadable evidence.** A merged/open verdict rests on the PR
    listing and a pushed/unpushed verdict on git containment; whenever the
    evidence a verdict depends on cannot be read — auth failure, a truncated
    listing, a malformed/absent PR state, an unresolvable tip, or a git
    containment failure that the verdict rests on — the handler returns
    ``status: error`` rather than a state that could clear the archive gate. Only
    a **tip-matching** PR counts, so a stale PR that merged an earlier tip on a
    reused branch name cannot report ``merged`` for new, unlanded commits.

    Routed through the CI router's ``--project-dir``, every git/gh subprocess runs
    in the named working tree, so the verb answers "did THIS repository's change
    land?" for a foreign checkout as readily as for the host one. It is the
    backing signal the pre-archive gate reads: a foreign deliverable resolving to
    ``pushed_no_pr`` is a change committed and pushed to a branch that no PR
    carries anywhere — the failure this plan closes.
    """
    branch, err_dict = _resolve_landing_branch(getattr(args, 'branch', None))
    if err_dict is not None:
        return err_dict
    assert branch is not None  # noqa: S101 — narrowed by the err_dict guard

    # PR state is authoritative, but answering it needs auth; a merged/open
    # verdict must not be silently downgraded to pushed_no_pr because gh was
    # unauthenticated, so an auth failure is a hard error here.
    is_auth, auth_err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_landing_state', auth_err)

    tip_sha, err_dict = _branch_tip_sha(branch)
    if err_dict is not None:
        return err_dict
    assert tip_sha is not None  # noqa: S101 — narrowed by the err_dict guard

    rc, stdout, stderr = github_ops.run_gh(
        [
            'pr', 'list', '--head', branch, '--state', 'all',
            '--limit', str(_PR_LIST_LIMIT),
            '--json', 'number,state,url,headRefName,headRefOid',
        ]
    )
    if rc != 0:
        return make_error('pr_landing_state', f'Failed to list PRs for branch {branch!r}', stderr.strip())
    try:
        prs = json.loads(stdout)
    except json.JSONDecodeError:
        return make_error('pr_landing_state', 'Failed to parse gh output', stdout[:100])
    if not isinstance(prs, list):
        return make_error('pr_landing_state', 'gh pr list returned a non-list payload', str(prs)[:100])
    # Fail closed on a truncated listing: an unread PR could carry the merged/open
    # state, so a result at the ceiling is not a complete correlation.
    if len(prs) >= _PR_LIST_LIMIT:
        return make_error(
            'pr_landing_state',
            f'gh pr list returned {len(prs)} PRs at the --limit {_PR_LIST_LIMIT} ceiling for branch '
            f'{branch!r}; the listing may be truncated and cannot be reliably correlated',
        )

    # Validate every entry, then keep only PRs whose head IS the current tip.
    tip_pr_states: list[str] = []
    for pr in prs:
        if not isinstance(pr, dict):
            return make_error('pr_landing_state', 'gh pr list returned a non-object PR entry', str(pr)[:100])
        state = pr.get('state')
        if not isinstance(state, str) or not state.strip():
            return make_error('pr_landing_state', 'gh pr list returned a PR entry with no usable state', str(pr)[:100])
        if str(pr.get('headRefOid') or '') == tip_sha:
            tip_pr_states.append(state)

    # Push state informs only the no-PR verdicts (pushed_no_pr vs unpushed). It is
    # gathered unconditionally, but its unreadability is fatal only when the
    # verdict actually rests on it — a tip-matching merged/open PR needs no git.
    pushed_state, pushed_err = _branch_pushed_state(branch)
    pushed_known = pushed_state is not None
    landing_state = derive_landing_state(tip_pr_states, bool(pushed_state))
    if landing_state in ('pushed_no_pr', 'unpushed') and not pushed_known:
        # pushed_err is set whenever pushed_state is None (the two-state contract
        # of _branch_pushed_state), so the verdict rests on push evidence we could
        # not read.
        assert pushed_err is not None  # noqa: S101 — narrowed by the contract above
        return pushed_err

    return {
        'status': 'success',
        'operation': 'pr_landing_state',
        'provider': 'github',
        'branch': branch,
        'tip_sha': tip_sha,
        'pushed': pushed_state if pushed_known else None,
        'pr_count': len(tip_pr_states),
        'landing_state': landing_state,
        # The verb's OWN declared population, so a consumer/test asserts against
        # this rather than a hand-copied list that could drift from the code.
        'landing_states': list(LANDING_STATES),
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
    """Handle 'pr wait-for-comments' — poll until a bot re-review lands or timeout.

    Replaces the blocking shell ``sleep`` previously used by workflow-pr-doctor's
    Automated Review Lifecycle Step 2. Snapshots the unresolved-comment count and
    the wait-start time once, then polls on the standard CI interval and exits as
    soon as EITHER arm of the completion predicate fires, or the timeout is
    reached. Reuses the same ``poll_until`` helper that powers ``ci wait``:

    - **count-growth arm** — the unresolved count grows past the baseline. This is
      the only arm consulted for a bot that appends a NEW comment per review
      (``participation_requires_update: false``).
    - **movement arm** — a bot whose registry record declares
      ``participation_requires_update: true`` edited its persistent comment after
      the wait started (:func:`_detect_movement_bots`). Such a bot re-reviews in
      place, so the count never grows and the count arm alone can only ever run to
      the full timeout.

    A timeout is reported with :func:`_detector_answerability`, so an await whose
    observable could never have moved is distinguishable from one where the bots
    were simply silent.
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
    # Aware UTC, so every comparison against a ``_parse_iso`` result (which
    # normalizes a naive stamp to UTC) is aware-vs-aware and never raises.
    wait_start = datetime.now(UTC)

    def check_fn() -> tuple[bool, dict]:
        snapshot = github_ops.fetch_pr_comments_data(args.pr_number, unresolved_only=True)
        if snapshot.get('status') != 'success':
            return False, {
                'error': f'Unresolved-comment fetch failed for PR {args.pr_number}',
                'context': str(snapshot.get('error', '')),
            }
        # ``comments`` rides along on the SAME fetch the count comes from — no
        # second request. ``unresolved_only`` filters resolved review THREADS
        # only, so ``issue_comment`` records are always present.
        return True, {
            'unresolved': int(snapshot.get('unresolved') or 0),
            'comments': snapshot.get('comments') or [],
        }

    def is_complete_fn(data: dict) -> bool:
        if int(data.get('unresolved', 0)) > baseline:
            return True
        return bool(_detect_movement_bots(data.get('comments') or [], wait_start))

    result = github_ops.poll_until(check_fn, is_complete_fn, timeout=args.timeout, interval=args.interval)

    if 'error' in result:
        return make_error(
            'pr_wait_for_comments',
            result['error'],
            result.get('last_data', {}).get('context', ''),
        )

    final_count = int(result['last_data'].get('unresolved', baseline))
    # Recomputed from the snapshot the predicate itself settled on, so the report
    # names the bot whose edit actually ended the wait. Empty when the count arm
    # fired alone, or on a timeout.
    movement_matched_bots = _detect_movement_bots(result['last_data'].get('comments') or [], wait_start)
    detector_answerable, unanswerable_reason = _detector_answerability()

    # Per-bot rate-limit discriminator: after the poll settles, inspect each
    # REGISTERED bot's newest comment for a rate-limit status notice. Best-effort
    # — a failed fetch leaves the default empty list and never alters poll
    # behaviour. An empty list means no registered bot is rate-limited.
    rate_limited_bots: list[dict] = []
    post = github_ops.fetch_pr_comments_data(args.pr_number)
    if post.get('status') == 'success':
        rate_limited_bots = _detect_rate_limited_bots(post.get('comments') or [])

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
        'rate_limited_bots': rate_limited_bots,
        # Which bot's in-place edit ended the wait — arrival only, never a claim
        # about how well the diff was reviewed.
        'movement_matched_bots': movement_matched_bots,
        'detector_answerable': detector_answerable,
        'unanswerable_reason': unanswerable_reason,
    }


# ---------------------------------------------------------------------------
# Merge-shaped verb guards: base-branch queue preflight + post-merge corroboration
# ---------------------------------------------------------------------------
#
# Every merge-shaped verb in this module (``pr merge``, ``pr auto-merge``,
# ``pr safe-merge``, ``pr merge-queue``) carries two obligations, and neither is
# satisfiable from the ``gh`` exit code alone:
#
# 1. **Refuse an unsafe base.** On a base branch with a REQUIRED platform merge
#    queue, an immediate merge closes the PR unmerged instead of merging it (the
#    close-unmerged signature); conversely ``gh pr merge --auto`` silently degrades from
#    "enqueue into the queue" to "enable plain auto-merge" when the base has NO
#    queue configured. Both dispositions are properties of the PR's OWN base
#    branch, so every such verb probes that branch first and fails closed on any
#    resolution failure.
# 2. **Prove its own success claim.** A zero exit from ``gh`` means the command
#    was accepted, never that the merge landed. The accepted-not-landed signature is exactly a
#    verb that reported ``merged: true`` — and deleted the head branch — for a
#    merge that never happened. The claim is therefore established from a
#    post-merge RE-READ of provider state, BEFORE any follow-up call (notably
#    the branch-delete) can influence it.
#
# Both guards assert the MEANING of a value, never the mere presence of a key: a
# narrow ``'mergedAt' in payload`` style check passes on a wrongly-shaped record
# and reintroduces the defect it was meant to close.


def _resolve_base_queue_state(identifier: str, operation: str) -> tuple[str, str, str, dict | None]:
    """Resolve the PR's own base branch and probe that branch's merge-queue state.

    Returns ``(base_branch, discriminator, detail, None)`` on success, where
    ``discriminator`` is one of the ``MERGE_QUEUE_*`` constants, or
    ``('', '', '', error_dict)`` when the state could not be established.

    Probing the PR's OWN base branch — not the repository default branch — is
    load-bearing: a PR may target a non-default base whose merge-queue
    configuration differs, and every merge-shaped decision below is a property of
    the branch the PR will actually land on.

    Fails closed on every resolution failure (PR-view failure, empty base branch,
    unresolvable repo, auth-scope failure, malformed rules response): an unknown
    queue state is never silently read as "no queue".
    """
    preflight_view = github_ops.view_pr_data(head=identifier)
    if preflight_view.get('status') != 'success':
        return (
            '',
            '',
            '',
            make_error(
                operation,
                f'Could not resolve base branch for the merge-queue preflight of PR {identifier}',
                preflight_view.get('error', 'pr_view failed'),
            ),
        )

    base_branch = preflight_view.get('base_branch') or ''
    if not base_branch:
        return (
            '',
            '',
            '',
            make_error(
                operation,
                f'PR {identifier} view returned an empty base branch; refusing the merge-queue preflight',
            ),
        )

    owner, repo = github_ops.get_repo_info()
    if not owner or not repo:
        return (
            '',
            '',
            '',
            make_error(operation, 'Could not determine repository owner/name for the merge-queue preflight'),
        )

    discriminator, detail, mq_error, _merge_method = github_ops._probe_merge_queue_state(owner, repo, base_branch)
    if mq_error is not None:
        # Auth-scope failure, non-404 gh api error, or malformed rules response.
        return '', '', '', make_error(operation, mq_error, detail)
    return base_branch, discriminator, detail, None


def _refuse_on_required_merge_queue(identifier: str, operation: str) -> dict | None:
    """Return an error dict when an IMMEDIATE merge of ``identifier`` would be unsafe.

    Returns ``None`` when the merge may proceed. The refusal names BOTH remedies
    so the caller is never left with a bare error: route the PR through the queue,
    or reconcile the plan's ``use_merge_queue`` step param.
    """
    base_branch, discriminator, detail, err_dict = _resolve_base_queue_state(identifier, operation)
    if err_dict is not None:
        return err_dict
    if discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED:
        return make_error(
            operation,
            f'PR {identifier} targets base branch {base_branch!r}, which has a required platform '
            f'merge queue — an immediate merge would close the PR unmerged. Route the PR '
            f'through the merge queue via "ci pr merge-queue", or reconcile the plan\'s '
            f'use_merge_queue step param via /marshall-steward.',
            detail,
        )
    # MERGE_QUEUE_ELIGIBLE_UNCONFIGURED / MERGE_QUEUE_INELIGIBLE /
    # MERGE_QUEUE_UNSUPPORTED all permit the immediate merge.
    return None


# The PR state that means "this PR was merged". Compared case-insensitively
# against the provider's own spelling rather than probed for presence.
_MERGED_STATE = 'MERGED'

# Merge strategies that replay the PR's head commits onto the base verbatim, so
# base-branch ancestry of the head SHA is a valid POSITIVE proof the merge
# landed. A SQUASH merge rewrites the branch into one new commit, so the head
# SHA never becomes an ancestor of the base — ancestry proves nothing there and
# is deliberately not consulted, which is why the strategy selects the evidence.
_ANCESTRY_CORROBORABLE_STRATEGIES = frozenset({'merge', 'rebase'})

# ``GET /compare/{base}...{head}`` statuses that mean the BASE already contains
# the head commit: ``identical`` (same commit) and ``behind`` (head is behind
# base, i.e. fully contained). ``ahead`` / ``diverged`` mean it does not.
_BASE_CONTAINS_HEAD_COMPARE_STATES = frozenset({'identical', 'behind'})


def _parse_merged_at(raw: str) -> datetime | None:
    """Parse a provider ``mergedAt`` stamp into a TIMEZONE-AWARE datetime.

    Returns ``None`` when ``raw`` is empty or unparseable — an absent or
    malformed timestamp is a NON-corroboration, never a wildcard that satisfies
    the check.

    The result is always aware: GitHub stamps are ``Z``-suffixed UTC, and a
    timezone-naive value (a provider or fixture that omits the offset) is
    normalized to UTC rather than returned naive. A naive datetime would raise
    ``TypeError`` the moment any caller compared it against an aware ``now()``,
    turning a corroboration check into a crash.
    """
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _head_is_ancestor_of_base(head_sha: str, base_branch: str) -> tuple[bool, str]:
    """Return ``(base_contains_head, detail)`` from the REST compare endpoint.

    The secondary corroboration arm for the non-squash strategies: after a
    ``merge`` or ``rebase``, the PR's head commit is reachable from the base
    branch, so ``GET /compare/{base}...{head_sha}`` reporting ``identical`` or
    ``behind`` is positive evidence the commits landed.

    Fails closed — every failure (missing inputs, unresolvable repo, non-zero
    exit, unparseable payload, unexpected shape) returns ``False`` with a detail
    naming the failure, never a permissive default.
    """
    if not head_sha or not base_branch:
        return False, 'ancestry check unavailable: PR re-read returned no head SHA or no base branch'

    owner, repo = github_ops.get_repo_info()
    if not owner or not repo:
        return False, 'ancestry check unavailable: could not resolve repository owner/name'

    endpoint = f'repos/{owner}/{repo}/compare/{quote(base_branch, safe="")}...{quote(head_sha, safe="")}'
    returncode, stdout, stderr = github_ops.run_gh(['api', endpoint])
    if returncode != 0:
        return False, f'ancestry check failed: {stderr.strip()}'
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return False, f'ancestry check returned unparseable JSON: {stdout[:100]}'
    if not isinstance(payload, dict):
        return False, 'ancestry check returned a non-dictionary compare payload'

    compare_status = str(payload.get('status') or '').lower()
    if compare_status in _BASE_CONTAINS_HEAD_COMPARE_STATES:
        return True, f'base {base_branch} contains head {head_sha} (compare status={compare_status})'
    return False, (
        f'base {base_branch} does not contain head {head_sha} '
        f'(compare status={compare_status or "unknown"})'
    )


def _corroborate_merge(identifier: str, strategy: str) -> tuple[bool, str]:
    """Return ``(merged, detail)`` established from a post-merge RE-READ of PR state.

    This is the single seam every merge-shaped verb uses to prove its own success
    claim, and it is deliberately NOT a presence check: it asserts that ``state``
    equals :data:`_MERGED_STATE` and that ``mergedAt`` parses to a real
    timezone-aware instant. A record carrying a ``mergedAt`` key whose value is
    ``null``, an empty string, or an unparseable stamp is a NON-corroboration.

    The evidence admitted is selected by ``strategy``:

    - every strategy is corroborated by ``state == MERGED`` AND a parseable
      ``mergedAt``;
    - ``merge`` / ``rebase`` (:data:`_ANCESTRY_CORROBORABLE_STRATEGIES`)
      ADDITIONALLY admit the ancestry arm (:func:`_head_is_ancestor_of_base`),
      because those strategies land the head commits on the base verbatim;
    - ``squash`` does NOT, because the squashed commit is a new object and the
      head SHA never becomes an ancestor of the base.

    Fails closed on every read/parse failure: an unobservable state is never a
    landed merge.
    """
    returncode, stdout, stderr = github_ops.run_gh(
        ['pr', 'view', identifier, '--json', 'state,mergedAt,baseRefName,headRefOid']
    )
    if returncode != 0:
        return False, f'post-merge PR re-read failed: {stderr.strip()}'
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return False, f'post-merge PR re-read returned unparseable JSON: {stdout[:100]}'
    if not isinstance(data, dict):
        return False, 'post-merge PR re-read returned a non-dictionary payload'

    state = str(data.get('state') or '').upper()
    raw_merged_at = str(data.get('mergedAt') or '')
    merged_at = _parse_merged_at(raw_merged_at)
    if state == _MERGED_STATE and merged_at is not None:
        return True, f'state={state}, merged_at={merged_at.isoformat()}'

    primary_detail = f'state={state or "unknown"}, merged_at={raw_merged_at or "null"}'
    if strategy not in _ANCESTRY_CORROBORABLE_STRATEGIES:
        return False, primary_detail

    contained, ancestry_detail = _head_is_ancestor_of_base(
        str(data.get('headRefOid') or ''),
        str(data.get('baseRefName') or ''),
    )
    return contained, f'{primary_detail}, {ancestry_detail}'


def cmd_pr_merge(args: argparse.Namespace) -> dict:
    """Handle 'pr merge' subcommand - merge a pull request.

    Refuses an unsafe base and proves its own success claim, per the two
    obligations documented above :func:`_resolve_base_queue_state`:

    - **Base-branch merge-queue preflight** — the same guard ``pr safe-merge``
      carries, via the shared :func:`_refuse_on_required_merge_queue`. Without it
      this verb merges straight into the close-unmerged signature: on a base branch with a
      required queue, ``gh pr merge`` closes the PR unmerged.
    - **Post-merge corroboration** — ``merged`` is set ONLY from
      :func:`_corroborate_merge`, a re-read of provider state whose admitted
      evidence is selected by ``--strategy``. It is established BEFORE the
      branch-delete follow-up is allowed to run, so a merge that did not happen
      can never take the head branch down with it. A non-corroborated
      merge returns ``status: error`` and deletes nothing.

    When ``--delete-branch`` is requested, the merge is performed WITHOUT the
    ``--delete-branch`` pass-through to ``gh pr merge``; instead, after a
    CORROBORATED merge, the PR's head branch is deleted remotely via the
    ``cmd_branch_delete`` handler (REST ``DELETE /git/refs/heads/{branch}``).
    Local git state is never touched by this handler — callers who want a
    local branch gone must invoke ``git -C {path} branch -D`` separately.

    ``merged: true`` is reported on EVERY successful merge, independently of
    ``--delete-branch``: the verdict belongs to the merge, not to the optional
    branch-delete follow-up.

    On branch-delete failure after a corroborated merge, a compound result is
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

    # ``pr safe-merge`` runs this preflight itself before polling, then delegates
    # here; re-running it would pay a second round trip AND risk a divergent
    # second verdict if the queue is configured between the two probes. The
    # delegate namespace sets the skip flag; no CLI surface exposes it.
    if not getattr(args, 'skip_merge_queue_preflight', False):
        preflight_err = _refuse_on_required_merge_queue(identifier, 'pr_merge')
        if preflight_err is not None:
            return preflight_err

    gh_args = ['pr', 'merge', identifier, f'--{args.strategy}']

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_merge', f'Failed to merge PR {identifier}', stderr.strip())

    # Establish the merge verdict from provider state BEFORE the branch-delete
    # follow-up below can influence it. A zero exit above only means gh accepted
    # the command.
    merged, corroboration = _corroborate_merge(identifier, args.strategy)
    if not merged:
        return make_error(
            'pr_merge',
            f'PR {identifier} merge command succeeded but post-merge state does NOT corroborate a '
            f'merge — refusing to report merged and skipping the branch delete. Verify the '
            f'PR state; if its base branch requires the platform merge queue, route the PR via '
            f'"ci pr merge-queue" instead of an immediate merge.',
            corroboration,
        )

    result: dict = {
        'status': 'success',
        'operation': 'pr_merge',
        'pr_number': args.pr_number if args.pr_number else identifier,
        'strategy': args.strategy,
        'merged': True,
        'merge_corroboration': corroboration,
    }

    # Branch-delete is an optional follow-up. The merge is already corroborated;
    # we never retry the merge on branch-delete failure.
    if args.delete_branch:
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
    """Handle 'pr auto-merge' subcommand - schedule the PR to merge without waiting.

    ``gh pr merge --auto`` is ONE command with TWO dispositions, decided entirely
    by the PR's base branch: on a base with no merge queue it enables plain
    auto-merge, and on a base with a configured queue it ENQUEUES the PR into
    that queue instead. The exit code is identical either way, so a boolean
    derived from it alone cannot tell the two apart: it reads "auto-merge
    enabled" for a PR the platform actually placed on a merge queue.

    This verb therefore probes the base branch's queue state
    (:func:`_resolve_base_queue_state`) BEFORE returning and reports which
    disposition actually occurred in ``disposition``:

    - ``enabled`` — plain auto-merge was scheduled (no queue on the base);
    - ``enqueued`` — the base has a configured queue, so the PR joined it.

    The probe runs before the ``gh`` call: refusing to report blind is only
    possible if the state is known, and the probe is read-only, so establishing
    it first costs nothing and keeps the failure path free of side effects.
    Fails closed — an unresolvable queue state is an error, never a guessed
    disposition.

    The envelope carries NO ``enabled`` key and no alias for one: a bare boolean
    would report a disposition this verb cannot know from the exit code.

    On the ``enqueued`` disposition the envelope also carries an ADVISORY
    ``routing_note`` (:data:`ci_base.AUTO_MERGE_ROUTING_NOTE`). This verb is the
    one sanctioned exception to the closed dispatch set branch-cleanup.md
    declares, so the note reports the divergence rather than refusing it: the
    call still succeeds, and the enqueue is still the safe outcome.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_auto_merge', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_auto_merge')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    base_branch, discriminator, detail, probe_err = _resolve_base_queue_state(identifier, 'pr_auto_merge')
    if probe_err is not None:
        return probe_err

    gh_args = ['pr', 'merge', identifier, '--auto', f'--{args.strategy}']

    returncode, stdout, stderr = github_ops.run_gh(gh_args)
    if returncode != 0:
        return make_error('pr_auto_merge', f'Failed to schedule auto-merge for PR {identifier}', stderr.strip())

    disposition = 'enqueued' if discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED else 'enabled'
    result: dict = {
        'status': 'success',
        'operation': 'pr_auto_merge',
        'pr_number': args.pr_number if args.pr_number else identifier,
        'base_branch': base_branch,
        'disposition': disposition,
        'disposition_detail': detail,
    }
    if discriminator == MERGE_QUEUE_ELIGIBLE_CONFIGURED:
        # Advisory only — this call SUCCEEDED and the enqueue is the safe
        # outcome. The note records that the documented routing would have
        # reached the queue through a different verb, so the divergence is
        # observable in the response rather than only in the routing table.
        # Turning it into a refusal would break the sanctioned
        # enqueue-via-auto-merge path this exception exists to preserve.
        result['routing_note'] = dict(AUTO_MERGE_ROUTING_NOTE)
    return result


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

    # Base-branch-scoped merge-queue preflight (guards the close-unmerged signature: an
    # immediate merge on a branch with a REQUIRED platform merge queue closes
    # the PR unmerged instead of merging it). Shared with ``cmd_pr_merge`` — see
    # :func:`_refuse_on_required_merge_queue`, which probes the PR's OWN base
    # branch and fails closed on any resolution failure.
    preflight_err = _refuse_on_required_merge_queue(identifier, 'pr_safe_merge')
    if preflight_err is not None:
        return preflight_err

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
        # Post-merge verification, POSITIVE. A guard that only rejects the single
        # known-bad ``state == closed`` admits every OTHER non-merged state — a PR
        # left ``open``, a state the provider newly introduces, or an unreadable
        # one — as a merge. The delegate establishes the verdict from a post-merge
        # re-read (:func:`_corroborate_merge`) and returns ``status: error`` on
        # anything short of it, so a delegated success carries a corroborated
        # ``merged is True``. Assert that exact value rather than its mere presence.
        if merge_result.get('merged') is not True:
            return make_error(
                'pr_safe_merge',
                f'PR {identifier} merge reported success but was NOT corroborated as merged. This '
                f'base branch likely requires the platform merge queue; route the PR via '
                f'"ci pr merge-queue" instead of an immediate merge.',
                str(merge_result.get('merge_corroboration') or 'no corroboration recorded'),
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

    # The admin fallback does NOT go through cmd_pr_merge, so it carries its own
    # corroboration — identically established, and BEFORE the branch-delete
    # follow-up below can influence it. An admin merge that did not land must
    # never take the head branch down with it.
    merged, corroboration = _corroborate_merge(identifier, args.strategy)
    if not merged:
        return make_error(
            'pr_safe_merge',
            f'Admin merge of PR {identifier} succeeded but post-merge state does NOT corroborate a '
            f'merge — refusing to report merged and skipping the branch delete.',
            corroboration,
        )

    result: dict = {
        'status': 'success',
        'operation': 'pr_safe_merge',
        'pr_number': (poll_result.get('last_data') or {}).get('pr_number') or (args.pr_number if args.pr_number else identifier),
        'strategy': args.strategy,
        'merge_path': 'admin_fallback',
        'polls': polls,
        'duration_sec': duration_sec,
        'merged': True,
        'merge_corroboration': corroboration,
    }

    # Reuse the same REST-delete follow-up as the normal merge path.
    if args.delete_branch:
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
    four are forwarded from the caller's own args.

    ``skip_merge_queue_preflight`` is set because safe-merge has ALREADY run the
    base-branch queue preflight before polling. Re-running it inside the delegate
    would pay a second round trip and, worse, could return a divergent verdict if
    the queue were configured during the readiness poll — refusing a merge that
    the caller's own preflight cleared. It is an internal delegation flag with no
    CLI surface; every other caller of ``cmd_pr_merge`` leaves it unset and gets
    the preflight.
    """
    return argparse.Namespace(
        pr_number=args.pr_number,
        head=args.head,
        strategy=args.strategy,
        delete_branch=args.delete_branch,
        skip_merge_queue_preflight=True,
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

    **``enqueued: true`` is corroborated, not assumed.** ``gh pr merge --auto``
    exits zero whether or not the base branch has a queue: with no queue it
    quietly enables PLAIN auto-merge, which is a different disposition entirely.
    An ``enqueued: true`` derived from that exit code would therefore claim a
    successful enqueue for a PR that never joined any queue, leaving the caller
    waiting for a queue merge that cannot arrive. This verb probes the PR's own
    base branch (:func:`_resolve_base_queue_state`) BEFORE the enqueue and sets
    ``enqueued: true`` only when that branch actually has a configured queue;
    otherwise it returns ``status: error`` naming BOTH remedies.

    The probe runs before the ``gh`` call rather than after: on an unconfigured
    base the call would have enabled plain auto-merge as a side effect, leaving
    the PR scheduled to merge outside the queue the caller asked for.

    Returns canonical TOON with ``operation: pr_merge_queue`` and a corroborated
    ``enqueued: true`` on success.
    """
    is_auth, err = github_ops.check_auth()
    if not is_auth:
        return make_error('pr_merge_queue', err)

    identifier, err_dict = github_ops._resolve_pr_identifier(args, 'pr_merge_queue')
    if err_dict:
        return err_dict
    assert identifier is not None  # noqa: S101 — narrowing after err_dict guard

    base_branch, discriminator, detail, probe_err = _resolve_base_queue_state(identifier, 'pr_merge_queue')
    if probe_err is not None:
        return probe_err
    if discriminator != MERGE_QUEUE_ELIGIBLE_CONFIGURED:
        return make_error(
            'pr_merge_queue',
            f'PR {identifier} targets base branch {base_branch!r}, which has NO platform merge queue '
            f'configured — enqueuing would silently enable plain auto-merge instead. Remedies: '
            f'(a) run "/marshall-steward -> Configuration -> Merge Queue" to provision the merge '
            f'queue on that branch, or (b) disable the plan\'s use_merge_queue step param to merge '
            f'immediately via "ci pr safe-merge".',
            detail,
        )

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
        'base_branch': base_branch,
        'enqueued': True,
        'enqueue_corroboration': detail,
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
    comment (e.g. ``/review``). Reuses the existing ``run_gh`` wrapper —
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
    ``{user, state, submitted_at, commit_sha, body}`` dicts. ``body`` is carried
    because a bot can submit a REVIEW object whose body is a refusal notice
    ("I could not review this") rather than feedback; the re-review wait must be
    able to classify that body and decline to count it as a completed review,
    which it cannot do from the SHA and timestamp alone.
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
            'body': r.get('body') or '',
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
