#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Data-not-code registry loader for the automatic-review bot pipeline.

Every reviewer bot the ``plan-marshall:automatic-review`` finalize step drives
ships one machine-readable record — a fenced-YAML data block embedded in its
``standards/{bot_kind}.md`` doc. This module parses those blocks ONCE at import
time and exposes stable accessors so the finding store, the re-review strategy
registry, the producer pre-filter, and the rate-limit detector DERIVE what they
need (the bot-kind set, the login->bot_kind map, each bot's re-review trigger
comment, its trigger semantics, its completion check-run name, its
skip-label-honoring flag, its ignore patterns, its refusal patterns, its
contentless-review markers, its actionable-content markers, its
participation-evidence publish shapes, its severity map, its rate-limit class,
and its rate-limit ETA patterns) instead of hard-coding three bots across
several code files.

The loader is deliberately generic — there is no per-bot branch anywhere in it.
Adding, removing, or re-configuring a bot is a pure data edit to a
``standards/{bot_kind}.md`` block; no code changes.

Data-block shape (one per ``standards/{bot_kind}.md``)::

    ```yaml
    bot_kind: coderabbit
    author_login: coderabbitai
    trigger_comment: "@coderabbitai review"
    trigger_semantics: requires_explicit_trigger   # or auto_on_push
    honors_skip_label: true
    rate_limit_class: awaitable_window
    participation_evidence:
      - review_body
      - inline
    participation_requires_update: false
    ignore_patterns:
      - "## Walkthrough"
      - "No actionable comments were generated"
    review_body_summary_patterns:     # a review_body OPENING with one of these is a status summary
      - "Actionable comments posted:"
    refusal_patterns:
      - "Review limit reached"
    refusal_size_patterns:            # subset of refusal_patterns whose CAUSE is diff-size
      - "your pull request is larger than the review limit of"
    refusal_size_cap_patterns:        # regexes extracting the CAP the size refusal states
      - "review limit of ([0-9][0-9,]*(?: [A-Za-z]+){0,2})"
    contentless_review_markers:
      - "## Review Guide"
      - "**Nothing to report**"
    actionable_content_markers:
      - "<details>"
    rate_limit_eta_patterns:
      - "wait ([0-9]+ minutes)"
    severity_map:
      potential_issue_critical: critical
      nitpick: low
    ```

Stdlib-only (no PyYAML): the block is a tightly-constrained subset — top-level
scalars, lists (``ignore_patterns``, ``review_body_summary_patterns``,
``refusal_patterns``, ``refusal_size_patterns``, ``refusal_size_cap_patterns``,
``contentless_review_markers``,
``actionable_content_markers``, ``participation_evidence``,
``rate_limit_eta_patterns``), and one nested map
(``severity_map``) — parsed by a small deterministic reader below. Load order is the sorted
``standards/*.md`` filename order, so ``bot_kinds()`` is stable across runs.
"""

import re
from pathlib import Path
from typing import Any

# The per-bot standards docs live one level up from this scripts/ dir. Anchoring
# on ``__file__`` keeps resolution correct in both the source tree and the
# plugin cache (the scripts/ <-> standards/ sibling layout is preserved by the
# build), with no dependence on the process cwd.
STANDARDS_DIR = Path(__file__).resolve().parent.parent / 'standards'

# The registry data block is a fenced ``yaml`` code block. A standards doc may
# carry other fenced blocks (bash examples, etc.); the registry block is the one
# whose body declares a top-level ``bot_kind:`` key.
_BOT_KIND_LINE = re.compile(r'(?m)^bot_kind:')


# ---------------------------------------------------------------------------
# Minimal constrained-YAML reader (stdlib-only)
# ---------------------------------------------------------------------------


def _strip_inline_comment(text: str) -> str:
    """Drop a trailing ``#`` comment that sits OUTSIDE any quoted span.

    A ``#`` begins a YAML comment only when it is at line start or preceded by
    whitespace and is not inside a single/double-quoted string. This preserves a
    ``#`` that is part of a quoted value (e.g. an HTML comment marker) while
    stripping the rationale comments the data blocks append after values.
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(text):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '#' and not in_single and not in_double and (i == 0 or text[i - 1] in ' \t'):
            return text[:i]
    return text


def _coerce(value: str) -> Any:
    """Coerce a scalar string to a bool where YAML would, else return the string."""
    if value == 'true':
        return True
    if value == 'false':
        return False
    return value


def _scalar(raw: str) -> Any:
    """Parse one scalar value: strip its inline comment, unquote, coerce booleans."""
    text = _strip_inline_comment(raw).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        text = text[1:-1]
    return _coerce(text)


def _parse_block(block: str) -> dict[str, Any]:
    """Parse a constrained registry data block into a plain dict.

    Handles exactly the shape the ``standards/{bot_kind}.md`` blocks use:
    indent-0 ``key: value`` scalars, an indent-0 ``key:`` opening either a
    ``- item`` list or a ``key: value`` nested map. Unknown/blank/comment lines
    are skipped. No anchors, flow collections, or multi-line scalars — those are
    not present in the data blocks and are intentionally unsupported.
    """
    data: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in block.splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.strip()
        if stripped.startswith('#'):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(' '))

        if indent == 0:
            key, sep, rest = stripped.partition(':')
            if not sep:
                continue
            key = key.strip()
            if not _strip_inline_comment(rest).strip():
                # A remainder that is empty once its trailing ``#`` comment is
                # removed opens a nested block (list or map); its kind is decided
                # by the first child line encountered below. Stripping the comment
                # first is load-bearing: the data blocks annotate block-opening
                # keys inline (``participation_evidence:  # the publish shapes``),
                # and testing the RAW remainder would read that comment as a
                # scalar value, silently discarding every child item. For a
                # fail-closed list such as ``participation_evidence`` the loss is
                # invisible — it degrades to the same empty list an absent field
                # yields. Comment-stripping still keeps a legitimately quoted
                # empty-string scalar (``key: ""``) a scalar, because its
                # remainder survives the strip as ``""``.
                data[key] = None
                current_key = key
            else:
                data[key] = _scalar(rest)
                current_key = None
            continue

        # Indented line: a child of the currently-open block key.
        if current_key is None:
            continue
        if stripped.startswith('- '):
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(_scalar(stripped[2:]))
        elif stripped == '-':
            continue
        else:
            child_key, sep, rest = stripped.partition(':')
            if not sep:
                continue
            if not isinstance(data.get(current_key), dict):
                data[current_key] = {}
            data[current_key][child_key.strip()] = _scalar(rest)

    # A block key that opened but gathered no children normalizes to an empty
    # list (harmless — the shipped blocks always carry children).
    for key, value in list(data.items()):
        if value is None:
            data[key] = []
    return data


def _extract_registry_block(md_text: str) -> str | None:
    """Return the body of the first fenced ``yaml`` block declaring ``bot_kind:``."""
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == '```yaml':
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != '```':
                body.append(lines[i])
                i += 1
            block_text = '\n'.join(body)
            if _BOT_KIND_LINE.search(block_text):
                return block_text
        i += 1
    return None


# ---------------------------------------------------------------------------
# The trigger-semantics vocabulary — ONE definition, read by every consumer
# ---------------------------------------------------------------------------
#
# Whether a bot re-reviews a new HEAD on its own, or must be ASKED. The set is
# CLOSED, and it is published as a tuple so a consumer or test derives the
# admissible population from here rather than restating it — a hand-copied pair
# keeps passing while the registry grows a third value it has never heard of.

#: The bot re-reviews automatically when the PR head moves; no trigger is needed.
TRIGGER_SEMANTICS_AUTO_ON_PUSH = 'auto_on_push'

#: The bot reviews only when explicitly asked (its ``trigger_comment`` is posted).
TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER = 'requires_explicit_trigger'

#: The closed admissible set. Consumers MUST derive from this tuple.
TRIGGER_SEMANTICS_VALUES = (
    TRIGGER_SEMANTICS_AUTO_ON_PUSH,
    TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class BotRegistry:
    """In-memory index of the per-bot registry records, loaded from standards docs.

    Construction parses every ``standards/*.md`` data block once; the accessors
    are pure reads over the cached index. A single module-level instance
    (:data:`REGISTRY`) backs the module-level convenience functions.
    """

    def __init__(self, standards_dir: Path = STANDARDS_DIR) -> None:
        self._standards_dir = standards_dir
        self._by_kind: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._standards_dir.is_dir():
            return
        for md_path in sorted(self._standards_dir.glob('*.md')):
            try:
                md_text = md_path.read_text(encoding='utf-8')
            except OSError:
                continue
            block = _extract_registry_block(md_text)
            if block is None:
                continue
            record = _parse_block(block)
            bot_kind = record.get('bot_kind')
            if isinstance(bot_kind, str) and bot_kind:
                self._by_kind[bot_kind] = record

    def bot_kinds(self) -> list[str]:
        """Return the registered bot-kind keys in deterministic sorted order."""
        return sorted(self._by_kind)

    def login_to_bot_kind(self) -> dict[str, str]:
        """Return the ``author_login`` -> ``bot_kind`` map across all records."""
        mapping: dict[str, str] = {}
        for bot_kind, record in self._by_kind.items():
            login = record.get('author_login')
            if isinstance(login, str) and login:
                mapping[login] = bot_kind
        return mapping

    def trigger_comment(self, bot_kind: str) -> str:
        """Return the re-review trigger comment for ``bot_kind`` (``''`` if unknown)."""
        value = self._by_kind.get(bot_kind, {}).get('trigger_comment', '')
        return value if isinstance(value, str) else ''

    def trigger_semantics(self, bot_kind: str) -> str:
        """Return whether ``bot_kind`` re-reviews on push or must be ASKED.

        The companion to :meth:`trigger_comment`, which says WHAT to post; this
        says WHETHER posting is required at all:

        - ``auto_on_push`` — the bot re-reviews when the PR head moves, so a
          trigger comment is redundant.
        - ``requires_explicit_trigger`` — the bot answers only when asked.

        ``requires_explicit_trigger`` is the FAIL-CLOSED default, returned for a
        bot whose record omits the field, declares it empty, declares a
        non-string, or declares a value outside :data:`TRIGGER_SEMANTICS_VALUES`.
        Closed in that direction because the two errors are not symmetric: wrongly
        believing a bot auto-reviews means the pipeline WAITS for a review nobody
        asked for and that will never arrive, which surfaces only as an
        unexplained timeout at the merge gate. Wrongly posting a trigger to a bot
        that would have reviewed anyway costs one redundant comment.

        The returned value is whitespace-stripped and validated against the closed
        set, matching the ``github_re_review._REGISTERED_TRIGGER_COMMENTS``
        convention of normalising every registry-sourced entry and dropping empties
        — so both sides of any comparison against this value are normalised the
        same way and a doc with a stray trailing space cannot silently miss.
        """
        value = self._by_kind.get(bot_kind, {}).get('trigger_semantics', '')
        normalized = value.strip() if isinstance(value, str) else ''
        if normalized not in TRIGGER_SEMANTICS_VALUES:
            return TRIGGER_SEMANTICS_REQUIRES_EXPLICIT_TRIGGER
        return normalized

    def completion_check_name(self, bot_kind: str) -> str:
        """Return the completion check-run name for ``bot_kind`` (``''`` if unknown/absent).

        Bots that publish an in-progress check-run (e.g. CodeRabbit) name it here
        so the ``automatic-review`` wait step can poll that check to completion
        instead of racing a fixed buffer. Bots with no completion check-run leave
        the field empty/absent and fall back to the ``review_bot_buffer_seconds``
        wait — the empty string is the fallback signal, so there is no per-bot
        branch here.
        """
        value = self._by_kind.get(bot_kind, {}).get('completion_check_name', '')
        return value if isinstance(value, str) else ''

    def honors_skip_label(self, bot_kind: str) -> bool:
        """Return whether ``bot_kind`` honors the shared skip-bot-review label."""
        return bool(self._by_kind.get(bot_kind, {}).get('honors_skip_label', False))

    def ignore_patterns(self, bot_kind: str) -> list[str]:
        """Return the per-bot whole-comment ignore patterns (``[]`` if unknown)."""
        value = self._by_kind.get(bot_kind, {}).get('ignore_patterns', [])
        return list(value) if isinstance(value, list) else []

    def refusal_patterns(self, bot_kind: str) -> list[str]:
        """Return the per-bot literal REFUSAL notice markers (``[]`` if unknown/absent).

        Each entry is an exact substring the bot emits when it DECLINES to review —
        a size-ceiling notice, a quota notice, a "posted in place of a review"
        banner. A body carrying one of these markers is that bot's refusal.

        This is deliberately a DEDICATED field, never a reuse of
        :meth:`ignore_patterns`. ``ignore_patterns`` lists the routine sections a
        bot emits on a *successful* review (CodeRabbit's ``## Walkthrough`` and
        ``✏️ Learnings added``, Sourcery's Reviewer's-Guide marker), so matching
        refusals against it would classify ordinary successful reviews as refusals.
        The two lists answer different questions and must stay distinct — see
        ``automatic-review/standards/bot-participation-contract.md`` § "Detecting a
        refusal".

        An empty list is the FAIL-CLOSED default for THIS arm: a bot with no declared
        refusal shape is never *claimed* to have refused on the strength of a pattern
        it never declared, because a refusal verdict is only ever asserted on
        positive evidence.

        It is not, however, the whole of that bot's recognition. Refusal recognition
        is a STACK of independent arms, none a superset of another, and this field
        feeds only the first of them — the other arms still cover what this one
        cannot: a notice-shaped body from an unregistered or renamed bot, and a
        rewording filed nowhere yet. See ``_github_pr.REFUSAL_LAYERS`` for the arms
        currently defined; that tuple is the single place they are named, so a bot
        declaring an empty list here inherits every arm added there with no edit to
        this record. A body no arm recognises at all is reported as an unrecognised
        refusal rather than silently filed as review feedback, so a bot resting
        wholly on the later arms is still never credited with a review it declined.
        """
        value = self._by_kind.get(bot_kind, {}).get('refusal_patterns', [])
        return list(value) if isinstance(value, list) else []

    def refusal_size_patterns(self, bot_kind: str) -> list[str]:
        """Return the refusal markers whose CAUSE is a diff-SIZE ceiling (``[]`` if absent).

        A **subset overlay** on :meth:`refusal_patterns`, not a separate detection
        list. ``refusal_patterns`` answers *"did the bot refuse?"*; this field answers
        *"which of those refusals was because the DIFF is too big?"* — the second,
        orthogonal **cause** axis. The awaitability axis (``rate_limit_class``) cannot
        carry it, because a bot can refuse for two different causes at the same
        awaitability: Sourcery's per-PR size ceiling (``your pull request is larger
        than the review limit of``) and its weekly quota (``reached your weekly rate
        limit of``) are BOTH ``hard_quota``, yet the first needs a smaller diff and the
        second needs backoff.

        A refusal matching an entry here is caused by size; any other detected refusal
        is a rate/budget **quota**. Every returned entry ALSO appears in
        ``refusal_patterns`` (detection stays that field's job); the subset invariant
        is ENFORCED here, not merely expected — an entry declared outside
        ``refusal_patterns`` is dropped, so a stray size marker can never mark a cause
        for a refusal the detection layer does not recognize. An empty list is the
        default — the bot declares no size-caused refusal, so every refusal it emits is
        classified ``quota``.
        """
        value = self._by_kind.get(bot_kind, {}).get('refusal_size_patterns', [])
        declared = list(value) if isinstance(value, list) else []
        # Derive the returned set from refusal_patterns rather than trusting the
        # registry block to stay in sync: filtering to the intersection keeps
        # refusal_size_patterns(bot) ⊆ refusal_patterns(bot) true at runtime, so a
        # size entry left outside the detection set cannot reclassify a quota refusal
        # as size. Declared order is preserved.
        refusal = set(self.refusal_patterns(bot_kind))
        return [marker for marker in declared if marker in refusal]

    def refusal_size_cap_patterns(self, bot_kind: str) -> list[str]:
        """Return the per-bot CAP-extraction regexes for a size refusal (``[]`` if absent).

        The exact counterpart of :meth:`rate_limit_eta_patterns`, one axis over: an
        awaitable refusal states WHEN it reopens, a structural one states HOW BIG the
        diff was allowed to be. Each entry is a regex applied to a body already
        recognized as a size-caused refusal, and its first capturing group is the cap
        the notice itself stated.

        The value is taken from the notice rather than declared as a number here on
        purpose. A declared figure is an assertion that goes stale silently the moment
        the provider changes its budget, and it cannot be reconciled against the diff
        that was actually refused; the notice's own figure is first-party evidence
        captured at the moment of refusal, which is what makes the recorded gap
        auditable rather than asserted. It is the same reason
        :meth:`refusal_patterns` keeps its size marker deliberately number-free — the
        marker must survive a changed budget, so the budget is read, never encoded.

        An empty list — or a notice that states no figure — yields ``''`` at the
        extraction seam, which the consumer reports as an UNKNOWN cap. It never
        reports a default, because a wrong cap is worse than an absent one: a reader
        auditing the gap against the real diff size would be reconciling against a
        number nobody observed.
        """
        value = self._by_kind.get(bot_kind, {}).get('refusal_size_cap_patterns', [])
        return list(value) if isinstance(value, list) else []

    def has_structural_size_cap(self, bot_kind: str) -> bool:
        """Whether ``bot_kind`` declares a diff-SIZE ceiling it refuses over.

        DERIVED from :meth:`refusal_size_patterns` rather than stored as its own
        flag, so the disclosure below can never disagree with the classification
        above — one declaration, two readers. A bot declaring a size marker is a bot
        that will refuse a diff over its ceiling; a bot declaring none refuses only
        for rate/budget quotas.

        This is the ADVANCE-disclosure predicate: it is answerable before any review
        is requested, because it reads the registry rather than an observed refusal.
        A structural ceiling is a property of the reviewer, not of the run, so a plan
        whose footprint will exceed it can know at outline time that this reviewer
        will not review it — as opposed to discovering it at the merge gate.
        """
        return bool(self.refusal_size_patterns(bot_kind))

    def contentless_review_markers(self, bot_kind: str) -> list[str]:
        """Return the literals a CONTENTLESS review body carries (``[]`` if unknown/absent).

        Every entry must be present for a body to qualify as contentless
        boilerplate — the producer's test is a CONJUNCTION over this whole list,
        not a disjunction. The list therefore describes one specific clean shape
        the bot emits when it reviewed and found nothing, not a set of
        alternatives; weakening it to a single representative marker silently
        broadens the suppression.

        An empty list is the FAIL-CLOSED default: the content-aware layer never
        fires for a bot that declares no clean shape, so a bot that has not opted
        in behaves exactly as it did before the layer existed. Consumed together
        with :meth:`actionable_content_markers`, whose entries veto the drop.
        """
        value = self._by_kind.get(bot_kind, {}).get('contentless_review_markers', [])
        return list(value) if isinstance(value, list) else []

    def review_body_summary_patterns(self, bot_kind: str) -> list[str]:
        """Return the literals marking a ``review_body`` as a STATUS SUMMARY (``[]`` if absent).

        A ``review_body`` is either the bot's consolidated findings or a status line
        about them (``"Actionable comments posted: N"``). The counting rule
        (``standards/bot-participation-contract.md`` § "The counting rule") excludes
        the latter from every finding count, and WHICH literal marks it is a per-bot
        fact — so it is registry data rather than a login literal baked into each
        counter.

        The body is a summary when it **BEGINS** with any entry, after leading
        whitespace and markdown emphasis are stripped — a status summary is a body
        that *opens* with its status line. A genuine review that merely mentions the
        phrase further down is not one, and stays counted.

        Do not read this as first-line-anchored. An earlier consumer tested whether
        any later line followed, which inverted the result on both realistic shapes:
        a real summary (status line, then a details block) was counted, while a
        one-line body carrying the phrase plus same-line substance was dropped. Line
        position does not carry *"is there review content"*; opening position does
        carry *"is this a status line"*.

        The accepted residual: a body that opens with the status line and continues
        with substance **on the same line** is classified a summary. Narrowing that
        needs a content predicate a literal match cannot supply — see
        :meth:`contentless_review_markers` / :meth:`actionable_content_markers`,
        which are that mechanism.

        An empty list is the fail-closed default, and "closed" here means
        **counted**: for a gate-escape count, dropping a substantive ``review_body``
        under-counts escapes and makes the gates look better than they are, so a bot
        that has not opted in keeps every ``review_body``.
        """
        value = self._by_kind.get(bot_kind, {}).get('review_body_summary_patterns', [])
        return list(value) if isinstance(value, list) else []

    def actionable_content_markers(self, bot_kind: str) -> list[str]:
        """Return the literals that DISQUALIFY a contentless drop (``[]`` if unknown/absent).

        ANY entry present in the body vetoes the contentless drop, whatever
        :meth:`contentless_review_markers` matched — these are the structural
        carriers of real findings (a ``<details>`` block, a severity badge), so
        their presence proves the review has content.

        An empty list means nothing vetoes. That is only ever reachable for a bot
        that also declares a non-empty ``contentless_review_markers``, because the
        drop short-circuits on the empty required list first.
        """
        value = self._by_kind.get(bot_kind, {}).get('actionable_content_markers', [])
        return list(value) if isinstance(value, list) else []

    def participation_evidence(self, bot_kind: str) -> list[str]:
        """Return the publish shapes that are EVIDENCE ``bot_kind`` participated.

        Each entry is a comment ``kind`` (``review_body`` / ``inline`` /
        ``issue_comment``) that this bot actually publishes when it reviews. A bot
        is recorded as a participant only when an observed comment's kind is in
        this list — participation is grounded in the bot's real publish shape
        rather than in the mere existence of some comment resolving to its login.

        The admissible vocabulary is CLOSED to publish shapes, and that closure is
        the structural guard behind the diff-derived-evidence rule: a publish shape
        is a review artifact the bot produced against the diff, whereas a
        body-derived signal — anything a reviewer could have produced by reading the
        PR description alone — has no publish shape at all and therefore no
        admissible evidence kind. It can never discharge a review obligation.

        An empty list resolves FAIL-CLOSED: a bot that declares no evidence shape
        can never be PROVEN to have participated, so it is reported as not-proven
        rather than silently credited.
        """
        value = self._by_kind.get(bot_kind, {}).get('participation_evidence', [])
        return list(value) if isinstance(value, list) else []

    def participation_requires_update(self, bot_kind: str) -> bool:
        """Return whether ``bot_kind``'s evidence additionally requires update movement.

        True for a bot that re-reviews by EDITING its single persistent comment in
        place rather than posting a new one (PR-Agent's Guide comment). For such a bot
        the mere continued existence of the comment proves only that it reviewed ONCE,
        at some earlier HEAD, so its credit has to clear the producer's CURRENCY TEST.

        That test reads ONE source — the plan-scoped currency ledger beside the
        findings store, which records per ``(bot_kind, comment_id)`` the
        merge-candidate SHA and the ``updated_at`` at the fetch that LAST credited the
        comment. The credit holds when the recorded SHA is the merge candidate, when
        the ledger holds no row for the comment and this fetch observes it at a
        resolvable merge candidate the comment does not demonstrably predate, or when
        its ``updated_at`` differs from the recorded value. An unresolvable
        merge-candidate SHA withholds the credit on every arm. See
        ``github_pr._reviewed_at_merge_candidate`` for the predicate this flag gates
        and ``standards/bot-participation-contract.md`` § "The currency rule".

        False (the default) for a bot whose every review appends a new comment. Such a
        bot is credited on the presence of a comment in a declared publish shape and no
        commit is compared, so the ledger holds no row for it at all.
        """
        return bool(self._by_kind.get(bot_kind, {}).get('participation_requires_update', False))

    def rate_limit_class(self, bot_kind: str) -> str:
        """Return the rate-limit class for ``bot_kind``, fail-closed to ``'unknown'``.

        Distinguishes a refusal the caller can usefully WAIT OUT from one it
        cannot, so an await decision is grounded in the bot's actual quota shape
        rather than assumed uniform across bots:

        - ``awaitable_window`` — a rolling window that reopens on its own, so
          awaiting the reset is productive.
        - ``hard_quota`` — a budget that does not reopen on a useful timescale
          (a per-PR size limit, a plan-level cap); awaiting it just burns budget.
        - ``unknown`` — no refusal has been observed for this bot, or the field
          is absent/malformed.

        ``unknown`` is the FAIL-CLOSED default (ADR-009): a bot whose record does
        not declare the field is never silently treated as awaitable, because
        awaiting a quota that never reopens is the expensive failure. A present
        but non-string value is treated the same as absent.
        """
        value = self._by_kind.get(bot_kind, {}).get('rate_limit_class', '')
        return value if isinstance(value, str) and value else 'unknown'

    def rate_limit_eta_patterns(self, bot_kind: str) -> list[str]:
        """Return the per-bot ETA-extraction regexes (``[]`` if unknown/absent).

        Each entry is a regex applied to a detected rate-limit notice body to
        pull out the reset time the notice itself states. A pattern that declares
        a capturing group yields that group as the ETA; otherwise the whole match
        is used. An empty list means the bot states no machine-readable ETA — the
        consumer then reports an absent ETA rather than inventing one.
        """
        value = self._by_kind.get(bot_kind, {}).get('rate_limit_eta_patterns', [])
        return list(value) if isinstance(value, list) else []

    def severity_map(self, bot_kind: str) -> dict[str, str]:
        """Return the per-bot marker->severity map (``{}`` if unknown)."""
        value = self._by_kind.get(bot_kind, {}).get('severity_map', {})
        return dict(value) if isinstance(value, dict) else {}


# Single process-wide instance parsed at import time. Consumers import either
# this object (``bot_registry.REGISTRY.bot_kinds()``) or the module-level
# functions below (``bot_registry.bot_kinds()``) — both read the same index.
REGISTRY = BotRegistry()


def bot_kinds() -> list[str]:
    """Registered bot-kind keys in deterministic sorted order."""
    return REGISTRY.bot_kinds()


def login_to_bot_kind() -> dict[str, str]:
    """The ``author_login`` -> ``bot_kind`` map across all registered bots."""
    return REGISTRY.login_to_bot_kind()


def trigger_comment(bot_kind: str) -> str:
    """The re-review trigger comment for ``bot_kind`` (``''`` if unknown)."""
    return REGISTRY.trigger_comment(bot_kind)


def completion_check_name(bot_kind: str) -> str:
    """The completion check-run name for ``bot_kind`` (``''`` if unknown/absent)."""
    return REGISTRY.completion_check_name(bot_kind)


def trigger_semantics(bot_kind: str) -> str:
    """Whether ``bot_kind`` re-reviews on push, fail-closed to ``requires_explicit_trigger``."""
    return REGISTRY.trigger_semantics(bot_kind)


def honors_skip_label(bot_kind: str) -> bool:
    """Whether ``bot_kind`` honors the shared skip-bot-review label."""
    return REGISTRY.honors_skip_label(bot_kind)


def ignore_patterns(bot_kind: str) -> list[str]:
    """The per-bot whole-comment ignore patterns for ``bot_kind`` (``[]`` if unknown)."""
    return REGISTRY.ignore_patterns(bot_kind)


def refusal_patterns(bot_kind: str) -> list[str]:
    """The per-bot literal refusal-notice markers for ``bot_kind`` (``[]`` if absent)."""
    return REGISTRY.refusal_patterns(bot_kind)


def refusal_size_patterns(bot_kind: str) -> list[str]:
    """The refusal markers whose cause is a diff-SIZE ceiling for ``bot_kind`` (``[]`` if absent)."""
    return REGISTRY.refusal_size_patterns(bot_kind)


def refusal_size_cap_patterns(bot_kind: str) -> list[str]:
    """The CAP-extraction regexes for ``bot_kind``'s size refusal (``[]`` if absent)."""
    return REGISTRY.refusal_size_cap_patterns(bot_kind)


def has_structural_size_cap(bot_kind: str) -> bool:
    """Whether ``bot_kind`` declares a diff-SIZE ceiling it refuses over."""
    return REGISTRY.has_structural_size_cap(bot_kind)


def contentless_review_markers(bot_kind: str) -> list[str]:
    """The literals a contentless ``bot_kind`` review carries (``[]`` = fail-closed)."""
    return REGISTRY.contentless_review_markers(bot_kind)


def actionable_content_markers(bot_kind: str) -> list[str]:
    """The literals that disqualify a contentless drop for ``bot_kind`` (``[]`` if absent)."""
    return REGISTRY.actionable_content_markers(bot_kind)


def review_body_summary_patterns(bot_kind: str) -> list[str]:
    """The literals marking a ``bot_kind`` review_body a STATUS SUMMARY (``[]`` = counted)."""
    return REGISTRY.review_body_summary_patterns(bot_kind)


def bot_kind_for_login(author_login: str | None) -> str:
    """Resolve an author login to its ``bot_kind`` (``''`` for a human or unknown).

    The normalised counterpart to the raw :func:`login_to_bot_kind` map, and the
    lookup a consumer should use: ``github_pr`` stores ``author`` VERBATIM, and real
    author logins carry two drifts a raw exact match silently loses — the ``[bot]``
    suffix some GraphQL logins carry, and non-canonical casing. Both resolve to no
    bot_kind under an exact match, which disables every per-bot rule keyed off the
    author for precisely the records that have no ``bot_kind`` to fall back on.

    Lives here because the registry owns the login map. ``github_re_review`` carries
    an equivalent (``bot_kind_for_author``, returning ``None`` rather than ``''``)
    over its own derived copy of the same map; consolidating the two is a
    worthwhile follow-up but is not required for either to be correct.
    """
    if not author_login:
        return ''
    normalized = author_login.lower()
    if normalized.endswith('[bot]'):
        normalized = normalized[: -len('[bot]')]
    # Both sides normalised — a registry doc declaring a mixed-case author_login
    # must resolve exactly as a lowercase one does.
    lowered = {login.lower(): kind for login, kind in login_to_bot_kind().items()}
    return lowered.get(normalized, '')


def participation_evidence(bot_kind: str) -> list[str]:
    """The publish shapes that are evidence ``bot_kind`` participated (``[]`` = fail-closed)."""
    return REGISTRY.participation_evidence(bot_kind)


def participation_requires_update(bot_kind: str) -> bool:
    """Whether ``bot_kind``'s participation evidence requires observed update movement."""
    return REGISTRY.participation_requires_update(bot_kind)


def rate_limit_class(bot_kind: str) -> str:
    """The rate-limit class for ``bot_kind``, fail-closed to ``'unknown'``."""
    return REGISTRY.rate_limit_class(bot_kind)


def rate_limit_eta_patterns(bot_kind: str) -> list[str]:
    """The per-bot ETA-extraction regexes for ``bot_kind`` (``[]`` if absent)."""
    return REGISTRY.rate_limit_eta_patterns(bot_kind)


def severity_map(bot_kind: str) -> dict[str, str]:
    """The per-bot marker->severity map for ``bot_kind`` (``{}`` if unknown)."""
    return REGISTRY.severity_map(bot_kind)
