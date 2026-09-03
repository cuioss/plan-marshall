#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Join an epic's parsed claim model against the real ``test/`` tree.

Stage 2 of the epic-surface derivation. Stage 1
(``plan-marshall:script-shared``'s :mod:`epic_spec_parser`, the marketplace's
single reader of the ``## Expected Surface`` grammar) turns prose specs into a
typed claim model; this module maps every test module in the tree to the plan(s)
claiming it, and groups the test-module line-budget findings by owning plan.

The partition reports each verdict in :data:`VERDICT_ORDER` as a SEPARATE
population:

- ``claimed`` — exactly one SLICE plan whose work is still outstanding covers
  the module.
- ``contested`` — two or more such plans cover it. This is the residual
  genuinely-contested set: small enough to enumerate and act on.
- ``swept`` — no slice plan covers it, but one or more SWEEP plans do. The
  crossing is reported and no owner is manufactured.
- ``not_derivable`` — no plan's resolved entries cover it, but at least one
  spec names it in a span the parser could not resolve, or names it in a
  LEAD-shaped entry. This is coverage the derivation cannot see.
- ``unclaimed`` — no plan covers it and no spec names it.

A **sweep plan** is one whose spec DECLARES ITSELF to cross the whole partition
by construction, rather than claiming a slice of it. Such a plan pairs with
every other plan by design, so counting it as a competing owner would mark the
whole tree contested and destroy the partition's signal. A slice that shares a
module with any number of sweeps therefore OWNS that module, and the sweeps
crossing it are recorded beside the verdict as a separate fact
(:attr:`ModuleVerdict.sweeps`) rather than as competing ownership.

⛔ Sweep-ness is detected from the spec's own self-declaration by
:data:`_SWEEP_RE`, never from a hard-coded plan-id list — such a list here would
be the same defect the derivation exists to close, one level down.

⛔ A sweep plan is a property of the PLAN; a root span is a property of an
ENTRY. The two are independent and neither implies the other.

⛔ ``unclaimed``, ``swept`` and ``not_derivable`` are never merged. Merging them
would report a parser limitation or a deliberate crossing as a partition defect,
manufacturing a disagreement the corpus does not contain.

⛔ A LEAD-shaped entry contributes NO claim here. Stage 1 states each entry's
shape and demotes nothing, because its other consumer needs the surface whole;
this stage does the demotion, which is the projection half of that shared
reader's contract. A lead names a path without claiming it, so honouring it as
ownership is what collapses the attribution into one contested bucket.

Exclusions subtract from the claiming plan's own set only: a plan that claims a
recursive glob and excludes a sub-directory does not claim the modules under
that sub-directory, while another plan's claim over them is unaffected.

⛔ A **root span** — an entry covering the whole population root, such as bare
``test/`` or ``test/**`` — discriminates nothing: it names every module, so
honouring it as a claim would mark the entire tree ``contested`` and destroy the
partition's signal. Several specs carry such a span as passing prose rather than
as an ownership claim. Root spans are therefore excluded from claim matching and
reported in :attr:`Partition.root_claims`, so the fact is STATED rather than
silently dropped.

⛔ A spec whose class is ``derived`` owns nothing: it declares its surface the
union of OTHER plans' surfaces, so its entries restate their claims instead of
competing with them. Its coverage is reported as ``not_derivable`` when no slice
claims the module, never as an ownership contest.

**Plan lifecycle state is the FOURTH derivation input, and the first that is not
the spec corpus.** A plan whose work is finished no longer competes for
ownership: its declared surface is a historical record, not a live claim. The
epic ledger beside the corpus carries an authoritative per-plan ``status``; its
vocabulary partitions into TERMINAL (:data:`TERMINAL_STATUSES`, the work is
finished) and ACTIVE (:data:`ACTIVE_STATUSES`, the work is outstanding), and a
module contested only between terminal and active plans resolves to the active
one, with the terminal claims recorded beside the verdict as
:attr:`ModuleVerdict.retired`.

⛔ The partition is taken over the ledger's OWN status vocabulary — never a
hard-coded plan-id list, and never the presence of a landing file. A status the
vocabulary does not cover raises :class:`UnknownPlanStatusError` rather than
defaulting into either bucket: silently bucketing an unrecognised status is how
this degenerates into the plan list the module forbids, one level down.

⛔ **Lifecycle narrows the competing set; it never picks a winner among live
plans.** A module contested between two or more ACTIVE plans stays contested —
that overlap is the one class this derivation deliberately refuses to
adjudicate. A module every one of whose claimants is terminal stays contested
too: narrowing it to nothing would manufacture an ownerless module out of one
that several plans really did claim. Both refusals are the same rule read in
opposite directions — the narrowing applies only when it leaves exactly one live
claimant standing.

⛔ A missing or unreadable ledger degrades to treating EVERY plan as active,
which is the behaviour that held before this input existed, and the degradation
is STATED on :attr:`PlanLifecycle.degradation` rather than absorbed. An absent
input reported as a clean one would attribute a terminal plan's claims on no
evidence.
"""

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path

from epic_spec_parser import (
    CLASS_DERIVED,
    KIND_DIRECTORY,
    KIND_RECURSIVE_GLOB,
    SHAPE_LEAD,
    SpecClaim,
)

#: The partition verdicts.
VERDICT_CLAIMED = 'claimed'
VERDICT_UNCLAIMED = 'unclaimed'
VERDICT_CONTESTED = 'contested'
VERDICT_SWEPT = 'swept'
VERDICT_NOT_DERIVABLE = 'not_derivable'

#: Every verdict carries a row in the tally even at zero, so an empty
#: population reads as measured rather than as absent.
VERDICT_ORDER = (
    VERDICT_CLAIMED,
    VERDICT_UNCLAIMED,
    VERDICT_CONTESTED,
    VERDICT_SWEPT,
    VERDICT_NOT_DERIVABLE,
)

#: Attribution bucket keys for modules with no single owning plan. They keep the
#: ownerless populations distinct inside the attribution, mirroring the
#: partition's refusal to merge them.
OWNER_UNCLAIMED = '<unclaimed>'
OWNER_CONTESTED = '<contested>'
OWNER_SWEPT = '<swept>'
OWNER_NOT_DERIVABLE = '<not-derivable>'

#: A spec's self-declaration that it crosses the whole partition by construction
#: rather than claiming a slice of it, as a keyword-marker regex over the spec's
#: OWN prose — the same style as the parser's ``_DERIVED_RE``. Four settled
#: phrasings of the ONE declaration, each a sentence a spec writes about itself:
#:
#: - its surface is the test tree ENTIRE;
#: - it PAIRS WITH NO OTHER plan over that tree;
#: - it CROSSES the epic's reduction SLICES;
#: - its sites DO NOT RESPECT the slice boundaries, or the epic's partition.
#:
#: ⛔ The alternation is deliberately wider than the narrowest set reproducing
#: today's sweep list, and that width is the point. A marker matching only the
#: specs that share ONE boilerplate sentence is the hard-coded plan list this
#: module's docstring forbids, wearing a regex: it happens to name today's
#: sweeps and stops matching the moment a plan declares its crossing in its own
#: words instead of copying that sentence — which is exactly how a self-declared
#: sweep was read as a competing slice owner and contested every slice it
#: crossed. The crossing and partition-disregard alternatives are what make this
#: a reading of what a spec SAYS rather than a fingerprint of who wrote it.
#:
#: ⛔ A REPRODUCTION IS NOT A DECLARATION, and the guard against reading one as
#: the other is applied UNIFORMLY to all four alternatives by
#: :func:`is_sweep_declaration`, never per-alternative. A spec ANALYSING the
#: corpus reproduces a sibling's declaration in order to discuss it, and every
#: one of these four phrasings is reproducible: reading any of them as the
#: analysing spec's OWN declaration sweeps that plan and hands its tests to a
#: neighbour. A guard fitted to one alternative leaves the other three carrying
#: the identical exposure while every control still passes green, which is why
#: the narrowing lives at the single point all four pass through rather than
#: inside the pattern. The FORMS a reproduction takes are enumerated at
#: :func:`_reproduction_spans`, and the same reasoning applies there: a guard
#: recognising one form is escaped by every other form the corpus uses.
#:
#: The crossing alternative additionally requires the plural ``slices`` — the
#: epic's reduction slices — and does not admit "crosses the whole partition".
#: That restriction is RETAINED beside the uniform guard, not replaced by it:
#: it narrows the alternative on its own terms, and a phrase can be reproduced
#: without quotation marks.
#:
#: ⛔ Corpus-independent by construction: it matches what a spec SAYS ABOUT
#: ITSELF, so a sweep added to the corpus is detected with no edit here, and no
#: plan identifier appears in the mechanism.
#: The four alternatives, published SEPARATELY rather than only as one joined
#: pattern. A control can then assert it carries a row for EVERY alternative, so
#: a fifth phrasing added here without its own matched declaration/quotation pair
#: fails that assertion instead of shipping unexercised beside three siblings
#: whose controls still pass green.
_SWEEP_ALTERNATIVES = (
    r'\bpairs with no other\b',
    r'\btree entire\b',
    r'\bcrosses\b[^.]{0,60}\bslices\b',
    r'\bdo(?:es)? not respect\b[^.]{0,60}\b(?:slice boundaries|partition)\b',
)

_SWEEP_RE = re.compile('|'.join(_SWEEP_ALTERNATIVES), re.IGNORECASE)

#: A QUOTATION span — text a spec sets off with quotation marks. Both straight
#: and typographic double quotes, and the typographic single pair.
#:
#: ⛔ The straight single quote is deliberately NOT admitted. The corpus writes
#: the possessive apostrophe with it, so admitting it would pair two unrelated
#: possessives and swallow whole sentences of genuine declaration between them —
#: silently converting a real sweep into an ordinary slice, the failure in the
#: other direction.
#:
#: ⛔ A quotation spans LINES but never a PARAGRAPH. Prose in this corpus is
#: hard-wrapped, so the dominant real reproduction has its opening and closing
#: mark on DIFFERENT lines: a line-bounded span sees none of them and every
#: hard-wrapped quotation escapes the guard entirely. The bound that survives is
#: the blank line — an unpaired mark then costs nothing beyond its own paragraph,
#: which is the containment the line bound was reaching for without the overfit
#: to prose that happens not to wrap.
#: The blank line that ends a paragraph, and with it the reach of any unpaired
#: mark inside one.
_PARAGRAPH_BREAK_RE = re.compile(r'\n[ \t]*\n')

_QUOTATION_RE = re.compile(
    r'"(?:[^"\n]|\n(?![ \t]*\n))*"'
    r'|“(?:[^”\n]|\n(?![ \t]*\n))*”'
    r'|‘(?:[^’\n]|\n(?![ \t]*\n))*’'
)

#: A BLOCKQUOTE span — the run of consecutive ``>``-prefixed lines that markdown
#: defines as quoted material.
#:
#: ⛔ LAZY CONTINUATION is deliberately out of scope: markdown lets a blockquote
#: run on into following lines that carry no ``>``, and this pattern stops at the
#: last prefixed line. Admitting it would need this module to decide which
#: unprefixed line starts a new block, and guessing wrong SUPPRESSES a real
#: declaration. Stopping short only ever leaves a marker uncontained, which makes
#: it fire — the conservative direction, and the one a reader can see.
_BLOCKQUOTE_RE = re.compile(r'^[ \t]{0,3}>.*(?:\n[ \t]{0,3}>.*)*', re.MULTILINE)

#: The backtick character, bound once so the fence rules below name what they
#: enforce rather than repeating a bare literal.
_BACKTICK = '`'

#: A fenced-code-block delimiter LINE. What separates a fence from an inline code
#: span is POSITION, not run length: CommonMark opens a fence only on a line whose
#: first content is the run, indented at most three spaces. A run of any length
#: sitting mid-line is an inline span, however long it is.
#:
#: ⛔ The distinction is load-bearing because the two differ in REACH. An inline
#: span may not contain a blank line, so it is bounded to its own paragraph; a
#: fence runs to its closing delimiter however many paragraphs later, and to the
#: END OF DOCUMENT when it has none. Deciding the two by run length instead —
#: three-or-more is a fence, wherever it sits — hands end-of-document reach to a
#: stray ``` typed in running prose, which then pairs with the next such run and
#: swallows every declaration between them. Group ``fence`` carries the WHOLE RUN
#: so its length survives to the close test; group ``info`` carries whatever
#: follows it on the line.
#:
#: This is the same rule, written the same way, as
#: ``epic_spec_parser._FENCE_RE`` / ``_fenced_mask`` — the shared reader that
#: masks fenced blocks out of the very specs this module scans. Two readers of
#: one corpus disagreeing about where a code block ends is the drift the
#: alignment removes. Only the backtick fence is recognised here: a ``~~~`` block
#: leaves its contents UNMASKED, so a marker inside one still fires — the
#: conservative direction, which over-reports a sweep rather than suppressing one.
_FENCE_LINE_RE = re.compile(r'^ {0,3}(?P<fence>`{3,})(?P<info>.*)$', re.MULTILINE)


def _backtick_run(text: str, index: int) -> int:
    """The length of the unbroken backtick run beginning at ``index``."""
    end = index
    while end < len(text) and text[end] == '`':
        end += 1
    return end - index


def _closing_backtick_run(text: str, start: int, run: int, limit: int) -> int | None:
    """Where the next backtick run of EXACTLY ``run`` begins, searching to ``limit``.

    Exactly, because an INLINE span is closed only by a run of its own length — a
    longer or shorter run is content, which is how a nested backtick survives
    inside a doubled span. A FENCED block closes on the weaker at-least-as-long
    rule and is resolved by :func:`_fenced_block_spans` instead, so this helper
    is the inline scan's alone.
    """
    index = start
    while index < limit:
        if text[index] != '`':
            index += 1
            continue
        length = _backtick_run(text, index)
        if length == run and index + length <= limit:
            return index
        index += length
    return None


def _fenced_block_spans(text: str) -> list[tuple[int, int]]:
    """The ``[start, end)`` span of every FENCED code block, delimiters included.

    Both decisions are taken against the CommonMark clauses, matching
    ``epic_spec_parser._fenced_mask`` rather than restating a looser rule:

    - a block OPENS only on a delimiter line whose info string carries no
      backtick, because a backtick fence's info string may not contain one. A
      sentence that begins with the fence marker and then quotes inline code
      wears the same shape, and reading it as an opener swallows the rest of the
      document;
    - it CLOSES only on a delimiter line built from a run AT LEAST AS LONG as the
      opener's and carrying no info string. A length-blind close ends a
      four-backtick block at the first three-backtick example inside it; an
      info-blind close ends a block at the next ````` ```text ````` heading.

    An unterminated fence runs to the end of the document — markdown's own
    reading, and the only place a stray delimiter reaches past its paragraph.
    """
    spans: list[tuple[int, int]] = []
    open_start: int | None = None
    open_length = 0
    for match in _FENCE_LINE_RE.finditer(text):
        run = match.group('fence')
        info = match.group('info')
        if open_start is None:
            if _BACKTICK in info:
                continue
            open_start, open_length = match.start(), len(run)
            continue
        if len(run) >= open_length and not info.strip():
            spans.append((open_start, match.end()))
            open_start, open_length = None, 0
    if open_start is not None:
        spans.append((open_start, len(text)))
    return spans


def _inline_code_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Every INLINE code span within ``text[start:end]``.

    Scanned rather than pattern-matched: a span is opened by a RUN of backticks
    and closed only by a run of the SAME length, which a single regex states as a
    backreference thicket while the scan reads as the rule itself.

    ⛔ Pairing is bounded by the BLANK LINE, because markdown forbids one inside
    an inline span. An unclosed run therefore delimits nothing beyond its own
    paragraph and is skipped, so a stray backtick costs exactly what a stray
    quotation mark costs — and two strays in different paragraphs cannot pair
    into one span that swallows a declaration standing between them.
    """
    spans: list[tuple[int, int]] = []
    index = start
    while index < end:
        if text[index] != _BACKTICK:
            index += 1
            continue
        run = _backtick_run(text, index)
        paragraph_break = _PARAGRAPH_BREAK_RE.search(text, index + run, end)
        limit = paragraph_break.start() if paragraph_break else end
        closing = _closing_backtick_run(text, index + run, run, limit)
        if closing is None:
            index += run
            continue
        spans.append((index, closing + run))
        index = closing + run
    return spans


def _code_spans(text: str) -> list[tuple[int, int]]:
    """The ``[start, end)`` span of every markdown code span, inline or fenced.

    The two forms are separated by POSITION and resolved in that order: fenced
    blocks are taken first from the delimiter LINES, and the inline scan then
    runs over the gaps BETWEEN them. Scanning inline first would let a run inside
    a fence pair with one outside it, and a length-based split would give
    end-of-document reach to a run that merely happens to be long.
    """
    fenced = _fenced_block_spans(text)
    spans = list(fenced)
    cursor = 0
    for start, end in fenced:
        spans.extend(_inline_code_spans(text, cursor, start))
        cursor = end
    spans.extend(_inline_code_spans(text, cursor, len(text)))
    return spans


def _reproduction_spans(text: str) -> list[tuple[int, int]]:
    """The ``[start, end)`` span of every region ``text`` REPRODUCES.

    ⛔ Three FORMS, because this corpus reproduces a sibling's sentence in three
    ways and a guard recognising only one of them is escaped by the other two —
    the same defect as a guard fitted to one sweep alternative, one level down:

    - a QUOTATION, in the marks :data:`_QUOTATION_RE` admits;
    - a markdown CODE SPAN, inline or fenced, which is this corpus's most common
      way of setting off a phrase it is discussing rather than asserting;
    - a BLOCKQUOTE, which markdown defines as quoted material outright.

    They are collected into ONE list because the containment test that consumes
    it asks a single question — is this occurrence inside text the spec
    reproduces — and answering it per form would restore the fitted guard.
    """
    spans = [(match.start(), match.end()) for match in _QUOTATION_RE.finditer(text)]
    spans.extend(_code_spans(text))
    spans.extend((match.start(), match.end()) for match in _BLOCKQUOTE_RE.finditer(text))
    return spans

#: The test-module line budget the campaign's findings are derived against.
DEFAULT_LINE_BUDGET = 400

#: The filename glob a test module is recognised by.
TEST_MODULE_GLOB = 'test_*.py'

#: The population root. An entry spanning exactly this discriminates nothing.
ROOT_PREFIX = 'test'

#: The epic ledger, and the keys the plan queue is read through. It sits BESIDE
#: the ``plans/`` spec corpus in the epic directory, and it is a genuinely
#: different input source: the corpus states what a plan SAYS it will touch,
#: the ledger states whether that plan is still doing it.
LEDGER_FILE = 'status.json'
LEDGER_QUEUE_KEY = 'plans'
LEDGER_ROW_ID_KEY = 'id'
LEDGER_ROW_STATUS_KEY = 'status'

#: The two buckets the ledger's status vocabulary partitions into.
LIFECYCLE_TERMINAL = 'terminal'
LIFECYCLE_ACTIVE = 'active'

#: The ledger's own per-plan status vocabulary, split by whether the plan's work
#: is FINISHED. A terminal plan's declared surface is a historical record; an
#: active plan's is a live claim. ``parked`` is ACTIVE by the same reading —
#: paused work is unfinished work, and a parked plan resumes onto the surface it
#: declared, so retiring its claim would hand that surface away while it waits.
TERMINAL_STATUSES = frozenset({'landed', 'shipped'})
ACTIVE_STATUSES = frozenset({'staged', 'running', 'parked'})

#: Every status the partition covers. A ledger value outside this set is not
#: bucketed by guess — see :class:`UnknownPlanStatusError`.
KNOWN_STATUSES = TERMINAL_STATUSES | ACTIVE_STATUSES

#: Why the lifecycle input could not be read. Each is STATED on the returned
#: :class:`PlanLifecycle` so a caller reporting all-plans-active can say whether
#: that is what the ledger said or what its absence forced.
DEGRADED_LEDGER_ABSENT = 'ledger_absent'
DEGRADED_LEDGER_UNREADABLE = 'ledger_unreadable'
DEGRADED_LEDGER_MALFORMED = 'ledger_malformed'


class UnknownPlanStatusError(Exception):
    """A ledger status value the terminal/active partition does not cover.

    Raised instead of defaulting the row into either bucket, so the run halts
    with the plan and the offending value named. Defaulting to ACTIVE would
    quietly keep a finished plan competing; defaulting to TERMINAL would quietly
    retire a live one — and neither guess is derivable from the vocabulary, which
    is the only authority this module reads the partition from.
    """

    def __init__(self, plan_id: str, status: str) -> None:
        super().__init__(f'{plan_id}: unknown plan status {status}')
        self.plan_id = plan_id
        self.status = status


@dataclass(frozen=True)
class LifecycleRow:
    """One ledger row: a plan, its recorded status, and the bucket it falls in."""

    plan_id: str
    status: str
    lifecycle: str


@dataclass(frozen=True)
class PlanLifecycle:
    """The ledger's per-plan lifecycle state, or a stated reason there is none.

    ⛔ Read :attr:`available` FIRST. When it is ``False`` no ledger was read at
    all, :attr:`rows` is empty, and :meth:`terminal_plans` is empty because
    nothing substantiates a single retirement — NOT because every plan is live.
    The two readings coincide in the partition's behaviour and differ entirely in
    what they claim, which is why :attr:`degradation` names the reason rather
    than leaving an empty set to be read as a measurement.
    """

    ledger_path: str
    available: bool
    degradation: str
    rows: tuple[LifecycleRow, ...] = ()

    def terminal_plans(self) -> frozenset[str]:
        """The plans whose work is finished, so their claims no longer compete."""
        return frozenset(row.plan_id for row in self.rows if row.lifecycle == LIFECYCLE_TERMINAL)

    def active_plans(self) -> frozenset[str]:
        """The plans whose work is outstanding, so their claims still compete."""
        return frozenset(row.plan_id for row in self.rows if row.lifecycle == LIFECYCLE_ACTIVE)


def lifecycle_of(status: str) -> str:
    """The bucket one status falls in, for a status already known to be covered.

    Total over :data:`KNOWN_STATUSES` and meaningless outside it — the
    unknown-status refusal belongs to the caller, which is the only party that
    knows WHICH plan carried the value and can therefore name it.
    """
    return LIFECYCLE_TERMINAL if status in TERMINAL_STATUSES else LIFECYCLE_ACTIVE


def read_plan_lifecycle(epic_dir: Path) -> PlanLifecycle:
    """Read the epic ledger's plan queue and partition it terminal/active.

    This is the derivation's SECOND input source and is read entirely apart from
    the spec corpus: it opens one file, consults no spec, and resolves no path.
    Keeping the two reads separate is what stops a ledger fact and a corpus fact
    from being mistaken for one another downstream.

    Raises:
        UnknownPlanStatusError: when a row carries a status outside
            :data:`KNOWN_STATUSES`. A structurally unusable ledger degrades with
            a stated reason instead — an unreadable input is a gap in the
            evidence, while an unrecognised status is a gap in this module's own
            model of the vocabulary, and only the latter is this module's to fix.
    """
    ledger_path = epic_dir / LEDGER_FILE
    if not ledger_path.is_file():
        return PlanLifecycle(str(ledger_path), False, DEGRADED_LEDGER_ABSENT)
    try:
        document = json.loads(ledger_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return PlanLifecycle(str(ledger_path), False, DEGRADED_LEDGER_UNREADABLE)
    if not isinstance(document, dict) or not isinstance(document.get(LEDGER_QUEUE_KEY), list):
        return PlanLifecycle(str(ledger_path), False, DEGRADED_LEDGER_MALFORMED)

    rows: list[LifecycleRow] = []
    for entry in document[LEDGER_QUEUE_KEY]:
        if not isinstance(entry, dict):
            return PlanLifecycle(str(ledger_path), False, DEGRADED_LEDGER_MALFORMED)
        plan_id = entry.get(LEDGER_ROW_ID_KEY)
        status = entry.get(LEDGER_ROW_STATUS_KEY)
        if not isinstance(plan_id, str) or not plan_id:
            return PlanLifecycle(str(ledger_path), False, DEGRADED_LEDGER_MALFORMED)
        if not isinstance(status, str) or status not in KNOWN_STATUSES:
            raise UnknownPlanStatusError(plan_id, repr(status))
        rows.append(LifecycleRow(plan_id, status, lifecycle_of(status)))
    return PlanLifecycle(str(ledger_path), True, '', tuple(rows))


@dataclass(frozen=True)
class ModuleVerdict:
    """One test module, its verdict, and the plans that verdict rests on.

    ``plans`` carries the SLICE plans the verdict rests on; ``sweeps`` carries
    the sweep plans that also cross the module. The two are separate fields
    because they are separate facts: a sweep crossing a slice's module is not a
    competing claim on it, and folding the two together is what produced a
    single undifferentiated contested bucket.

    ``retired`` carries the plans whose claim on this module lifecycle set aside
    — a third separate fact, for the same reason. It is populated only where the
    narrowing actually applied, so an empty tuple means "no claim was retired
    here", never "the ledger was not consulted"; that question is answered once,
    on :class:`PlanLifecycle`, rather than guessed from a per-module absence.
    """

    path: str
    verdict: str
    plans: tuple[str, ...]
    sweeps: tuple[str, ...] = ()
    retired: tuple[str, ...] = ()


@dataclass(frozen=True)
class RootClaim:
    """One span set aside because it covers the whole population root."""

    plan_id: str
    path: str


@dataclass(frozen=True)
class Partition:
    """Every test module in the tree, each with exactly one verdict."""

    modules: tuple[ModuleVerdict, ...]
    root_claims: tuple[RootClaim, ...] = ()

    def with_verdict(self, verdict: str) -> tuple[ModuleVerdict, ...]:
        """Every module carrying ``verdict``, in tree order."""
        return tuple(module for module in self.modules if module.verdict == verdict)

    def tally(self) -> dict[str, int]:
        """Population size per verdict, with every verdict present."""
        counts = dict.fromkeys(VERDICT_ORDER, 0)
        for module in self.modules:
            counts[module.verdict] += 1
        return counts

    def lifecycle_resolved(self) -> tuple[ModuleVerdict, ...]:
        """Every module an owner was found for by retiring a finished plan's claim.

        These are exactly the modules that would read ``contested`` without the
        lifecycle input, so the population is the input's own effect, measurable
        per instance rather than asserted as a shrunken total.
        """
        return tuple(
            module
            for module in self.modules
            if module.retired and module.verdict == VERDICT_CLAIMED
        )


@dataclass(frozen=True)
class BudgetFinding:
    """One test module over the line budget, as re-derived from the tree."""

    path: str
    line_count: int


@dataclass(frozen=True)
class AttributionBucket:
    """The over-budget modules attributed to one owner."""

    owner: str
    findings: tuple[BudgetFinding, ...]


@dataclass(frozen=True)
class Attribution:
    """Budget findings grouped by owning plan, each file appearing once."""

    budget: int
    buckets: tuple[AttributionBucket, ...]

    def total_findings(self) -> int:
        return sum(len(bucket.findings) for bucket in self.buckets)


def _segments(path: str) -> list[str]:
    return [segment for segment in path.strip('/').split('/') if segment]


def _match_segments(pattern: list[str], target: list[str]) -> bool:
    """Segment-wise glob match, so a ``*`` never spans a path separator."""
    if len(pattern) != len(target):
        return False
    return all(
        fnmatch.fnmatchcase(part, glob) for glob, part in zip(pattern, target, strict=True)
    )


def entry_matches(entry_path: str, kind: str, module: str) -> bool:
    """Whether one resolved claim entry covers ``module``.

    A recursive glob and a directory both cover everything beneath them; every
    other shape matches segment-wise, so ``a/test_*.py`` covers ``a/test_x.py``
    but not ``a/nested/test_x.py``.
    """
    if kind == KIND_RECURSIVE_GLOB:
        prefix = entry_path[:-2]
        return module.startswith(prefix) if prefix else True
    if kind == KIND_DIRECTORY:
        return module.startswith(entry_path)
    return _match_segments(_segments(entry_path), _segments(module))


def is_root_span(entry_path: str, kind: str) -> bool:
    """Whether an entry covers the whole population root, discriminating nothing.

    Only a directory or a recursive glob can span the root; a named file and a
    filename glob always name something narrower.
    """
    if kind == KIND_RECURSIVE_GLOB:
        prefix = entry_path[:-2]
    elif kind == KIND_DIRECTORY:
        prefix = entry_path
    else:
        return False
    stem = prefix.strip('/')
    return not stem or stem == ROOT_PREFIX


def is_sweep_declaration(spec_text: str) -> bool:
    """Whether a spec DECLARES ITSELF a whole-partition sweep.

    The marker is matched over the spec's own prose, so the decision rests on
    what the plan says about itself rather than on any list held here. Tested in
    isolation from the rest of the partition, because a marker that silently
    stopped matching would quietly restore the single-bucket collapse.

    ⛔ A marker occurrence lying WHOLLY inside a reproduction span — a quotation,
    a code span or a blockquote, per :func:`_reproduction_spans` — is a
    reproduction of someone else's declaration and is discarded. The test is
    applied here, to every match of every alternative, which is what makes the
    guard uniform: a narrowing written into one alternative's pattern leaves its
    siblings open. Containment must be TOTAL — a match merely OVERLAPPING a
    reproduction span still counts.

    ⛔ Every form's REACH is bounded by the blank line — a quotation's, a
    blockquote's and an inline code span's alike — so a stray or mismatched
    delimiter costs at most its own paragraph and cannot suppress a declaration
    standing outside it. The FENCED code block is the single exception: an
    unterminated fence runs to the end of the document, which is markdown's own
    reading of it and the one this corpus's shared reader
    (``epic_spec_parser._fenced_mask``) also takes. Departing from it here would
    put two readers of one corpus in disagreement over where a block ends.
    """
    spans = _reproduction_spans(spec_text)
    return any(
        not any(start <= match.start() and match.end() <= end for start, end in spans)
        for match in _SWEEP_RE.finditer(spec_text)
    )


def derive_sweep_plans(claims: list[SpecClaim], plans_dir: Path) -> frozenset[str]:
    """The plan ids whose specs declare themselves whole-partition sweeps.

    A spec that cannot be read contributes no sweep declaration: the partition
    then treats the plan as an ordinary slice, which is the conservative
    direction — it may report a contest that a readable spec would have resolved,
    and never invents an ownership it cannot substantiate.
    """
    sweeps = set()
    for claim in claims:
        try:
            text = (plans_dir / claim.spec).read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        if is_sweep_declaration(text):
            sweeps.add(claim.plan_id)
    return frozenset(sweeps)


def _discriminating(claim: SpecClaim) -> list:
    """The spec's claimed entries that discriminate at all — root spans removed."""
    return [entry for entry in claim.claimed if not is_root_span(entry.path, entry.kind)]


def _owning_entries(claim: SpecClaim) -> list:
    """The entries that carry OWNERSHIP.

    ⛔ A spec whose surface is DERIVED owns nothing: it declares itself the union
    of OTHER plans' surfaces, so its entries restate those plans' claims rather
    than competing with them. Counting them as ownership makes the deriving spec
    a co-owner of every module its constituents cover, which contests the whole
    corpus at once. Stage 1 already publishes this verdict, and the reader's
    OTHER consumer already refuses to compare a derived spec's paths at its
    disjointness gate — this is the same refusal, applied to attribution.
    """
    if claim.spec_class == CLASS_DERIVED:
        return []
    return [entry for entry in _discriminating(claim) if entry.shape != SHAPE_LEAD]


def _naming_entries(claim: SpecClaim) -> list:
    """The entries that NAME a module without owning it.

    Together with :func:`_owning_entries` this partitions the spec's
    discriminating entries: every one of them either owns or merely names, never
    both and never neither. A named-but-unowned module is coverage the
    derivation cannot attribute, which is ``not_derivable`` — never
    ``unclaimed``.
    """
    if claim.spec_class == CLASS_DERIVED:
        return _discriminating(claim)
    return [entry for entry in _discriminating(claim) if entry.shape == SHAPE_LEAD]


def _claims_module(claim: SpecClaim, module: str) -> bool:
    """Whether a spec claims ``module`` after leads, root spans and exclusions subtract."""
    covered = any(entry_matches(entry.path, entry.kind, module) for entry in _owning_entries(claim))
    if not covered:
        return False
    return not any(entry_matches(entry.path, entry.kind, module) for entry in claim.excluded)


def _leads_module(claim: SpecClaim, module: str) -> bool:
    """Whether a spec NAMES ``module`` without claiming it.

    Root spans are excluded for the same reason they are excluded from claim
    matching: a span over the whole root discriminates nothing, and honouring it
    would mark the entire tree ``not_derivable``.
    """
    return any(entry_matches(entry.path, entry.kind, module) for entry in _naming_entries(claim))


def _is_container_span(cleaned: str) -> bool:
    """Whether an unresolved span names a DIRECTORY rather than a file."""
    return cleaned.endswith('/') or cleaned.endswith('**')


def _raw_mentions_module(raw: str, module: str) -> bool:
    """Whether an UNRESOLVED span names ``module``.

    A file-shaped span names the module by its TRAILING segments, the filename
    included: ``test_x.py`` and ``a/test_x.py`` both name ``test/a/test_x.py``.

    A CONTAINER-shaped span — written with a trailing ``/`` or a trailing
    ``**`` — names a directory, so it names every module beneath that
    directory at any depth. Its segments are therefore matched against the
    module's ancestor directories rather than against the filename: the
    filename can never equal a directory name, so anchoring a container span on
    the trailing segment would make it name NOTHING.

    ⛔ A container span naming nothing is not a harmless miss. Every module it
    covers would fall through to ``unclaimed`` instead of ``not_derivable`` —
    the one merge :mod:`_epic_partition` exists to prevent, manufacturing
    partition defects out of the parser's own limits.

    The container match is deliberately unanchored at the front: an unresolved
    span is by definition one the parser could not anchor to the repo root, so
    the only honest reading is "some directory with these segments". Erring
    towards ``not_derivable`` reports coverage the derivation cannot see, which
    is the safe direction; erring the other way invents a defect.
    """
    cleaned = raw[2:] if raw.startswith('./') else raw
    cleaned = cleaned[4:] if cleaned.startswith('.../') else cleaned
    container = _is_container_span(cleaned)
    pattern = _segments(cleaned)
    if container and pattern and pattern[-1] == '**':
        pattern = pattern[:-1]
    target = _segments(module)
    if not pattern:
        return False
    if not container:
        if len(pattern) > len(target):
            return False
        return _match_segments(pattern, target[-len(pattern) :])
    parents = target[:-1]
    width = len(pattern)
    return any(
        _match_segments(pattern, parents[start : start + width])
        for start in range(len(parents) - width + 1)
    )


def _mentions_module(claim: SpecClaim, module: str) -> bool:
    """Whether a spec names ``module`` in coverage the derivation cannot see.

    Two independent sources of such coverage: a span the parser could not
    resolve, and an entry stage 1 resolved but marked lead-shaped.
    """
    if any(_raw_mentions_module(raw, module) for raw in claim.unresolved):
        return True
    return _leads_module(claim, module)


def iter_test_modules(test_root: Path, repo_root: Path) -> tuple[str, ...]:
    """Every test module under ``test_root``, as sorted repo-relative paths."""
    if not test_root.is_dir():
        return ()
    found = [
        path.relative_to(repo_root).as_posix()
        for path in test_root.rglob(TEST_MODULE_GLOB)
        if path.is_file()
    ]
    return tuple(sorted(found))


def derive_partition(
    claims: list[SpecClaim],
    modules: tuple[str, ...],
    sweeps: frozenset[str] = frozenset(),
    terminal_plans: frozenset[str] = frozenset(),
) -> Partition:
    """Assign every module exactly one verdict against the claim model.

    ``sweeps`` names the plans that declared themselves whole-partition sweeps
    (see :func:`derive_sweep_plans`). They are separated from the claiming set
    BEFORE the owner count is taken, which is what lets a single slice own a
    module that any number of sweeps also cross. Passing an empty set is the
    honest "no sweep declared" case, never a default that hides one.

    ``terminal_plans`` names the plans whose work is FINISHED, read from the epic
    ledger by :func:`read_plan_lifecycle`. It narrows a CONTEST and nothing else:

    - one owner — untouched, whatever its lifecycle. A sole terminal claimant is
      still the only plan that ever named the module, and there is no contest to
      resolve, so retiring it would replace an attribution with a blank.
    - two or more owners, exactly one of them live — the live plan owns it, and
      the finished plans land in :attr:`ModuleVerdict.retired`.
    - two or more owners, two or more of them live — CONTESTED among the live
      plans, with the finished ones retired beside the verdict. ⛔ Lifecycle
      never picks a winner here; that is the whole refusal.
    - two or more owners, NONE of them live — CONTESTED, unnarrowed and with
      nothing retired. Narrowing to an empty set would manufacture an ownerless
      module out of one that several plans really did claim.

    An empty ``terminal_plans`` reproduces the behaviour that held before the
    ledger was an input at all, which is exactly what the degraded read yields.
    """
    root_claims = tuple(
        RootClaim(plan_id=claim.plan_id, path=entry.path)
        for claim in claims
        for entry in claim.claimed
        if is_root_span(entry.path, entry.kind)
    )
    verdicts: list[ModuleVerdict] = []
    for module in modules:
        claiming = tuple(claim.plan_id for claim in claims if _claims_module(claim, module))
        owners = tuple(plan_id for plan_id in claiming if plan_id not in sweeps)
        crossing = tuple(plan_id for plan_id in claiming if plan_id in sweeps)
        if len(owners) == 1:
            verdicts.append(ModuleVerdict(module, VERDICT_CLAIMED, owners, crossing))
            continue
        if len(owners) > 1:
            live = tuple(plan_id for plan_id in owners if plan_id not in terminal_plans)
            retired = tuple(plan_id for plan_id in owners if plan_id in terminal_plans)
            if not live:
                verdicts.append(ModuleVerdict(module, VERDICT_CONTESTED, owners, crossing))
            elif len(live) == 1:
                verdicts.append(ModuleVerdict(module, VERDICT_CLAIMED, live, crossing, retired))
            else:
                verdicts.append(ModuleVerdict(module, VERDICT_CONTESTED, live, crossing, retired))
            continue
        if crossing:
            verdicts.append(ModuleVerdict(module, VERDICT_SWEPT, (), crossing))
            continue
        mentioned = tuple(claim.plan_id for claim in claims if _mentions_module(claim, module))
        if mentioned:
            verdicts.append(ModuleVerdict(module, VERDICT_NOT_DERIVABLE, mentioned))
        else:
            verdicts.append(ModuleVerdict(module, VERDICT_UNCLAIMED, ()))
    return Partition(modules=tuple(verdicts), root_claims=root_claims)


def derive_budget_findings(
    modules: tuple[str, ...],
    repo_root: Path,
    budget: int = DEFAULT_LINE_BUDGET,
) -> tuple[BudgetFinding, ...]:
    """Re-derive the over-budget modules from the CURRENT tree.

    The campaign's published baseline is never adopted as input — it is only
    ever a post-hoc comparison against what this returns.
    """
    findings = [
        BudgetFinding(path=module, line_count=count)
        for module, count in ((m, _line_count(repo_root / m)) for m in modules)
        if count > budget
    ]
    return tuple(findings)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding='utf-8').splitlines())


def owner_of(module: ModuleVerdict) -> str:
    """The attribution bucket key for one module's verdict.

    A ``claimed`` module is attributed to its owning slice REGARDLESS of how
    many sweeps also cross it — that is the whole point of separating the two
    populations, and it is what breaks the single-bucket collapse. The same
    holds for the plans lifecycle retired: ``plans[0]`` is the live owner
    :func:`derive_partition` left standing, and the retired claims are read from
    :attr:`ModuleVerdict.retired` rather than from the attribution bucket.
    """
    if module.verdict == VERDICT_CLAIMED:
        return module.plans[0]
    if module.verdict == VERDICT_CONTESTED:
        return OWNER_CONTESTED
    if module.verdict == VERDICT_SWEPT:
        return OWNER_SWEPT
    if module.verdict == VERDICT_NOT_DERIVABLE:
        return OWNER_NOT_DERIVABLE
    return OWNER_UNCLAIMED


def derive_attribution(
    partition: Partition,
    findings: tuple[BudgetFinding, ...],
    budget: int = DEFAULT_LINE_BUDGET,
) -> Attribution:
    """Group budget findings by owning plan; each file lands in exactly one bucket."""
    owners = {module.path: owner_of(module) for module in partition.modules}
    grouped: dict[str, list[BudgetFinding]] = {}
    for finding in findings:
        grouped.setdefault(owners.get(finding.path, OWNER_UNCLAIMED), []).append(finding)
    buckets = tuple(
        AttributionBucket(owner=owner, findings=tuple(grouped[owner])) for owner in sorted(grouped)
    )
    return Attribution(budget=budget, buckets=buckets)
