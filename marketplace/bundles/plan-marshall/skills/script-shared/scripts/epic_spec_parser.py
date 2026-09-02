#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parse an epic's staged plan specs and classify each ``## Expected Surface``.

The SINGLE reader of the ``## Expected Surface`` grammar in the marketplace.
It lives in ``plan-marshall:script-shared`` because both bundles consume it:
``plan-marshall:plan-orchestrator`` reads it for the Ordered Queue's
``Surface (expected)`` cell and for ``corpus cross-check``'s file-overlap
collision class, and ``pm-plugin-development:tools-epic-surface-partition``
reads it as stage 1 of the epic-surface derivation, turning prose specs into a
typed claim model the partition stage joins against the real ``test/`` tree.

⛔ There is exactly ONE reader of this grammar, and this is it. The orchestrator
previously carried a second, weaker parse of the same section — a repo-path
regex requiring a ``/`` and a trailing ``.ext``, which resolved named files only
and could see neither a directory, a recursive glob, an exclusion, nor an entry
written relative to a path named earlier in the same bullet. A spec declaring
any of those four shapes therefore rendered as having no expected surface and
passed the disjointness gate as if it collided with nothing. Adding a second
reader back is that defect.

The corpus is enumerated by GLOB (:data:`SPEC_GLOB`) and never by a hard-coded
plan list — a hard-coded list here would be the same defect the derivation
exists to close, one level down. A spec added to the corpus is picked up with no
edit to this module.

Each spec lands in exactly one of three classes, with the evidence for the
verdict recorded beside it:

- ``declarative`` — the Expected Surface resolves to at least one path entry.
- ``derived`` — the section declares its surface a function of other plans'.
- ``prose`` — a section is present but resolves to no path entry.

A spec whose class cannot be determined raises :class:`UnclassifiableSpecError`
naming the spec, rather than defaulting to a class.

Independently of that spec-level class, EACH resolved entry carries its own
shape — :data:`SHAPE_CLAIM` or :data:`SHAPE_LEAD` — decided from its own
bullet's label and text by the entry-shape marker rules. A spec routinely mixes the
two: the same ``declarative`` spec may claim one directory outright and merely
point at another pending outline-time verification, and reading the second as
an ownership claim is what collapses a downstream attribution into a single
contested bucket.

⛔ The shape is ADDITIVE. It is recorded on the entry and changes no
accumulator: ``claimed`` and ``excluded`` hold exactly the entries they would
hold without it. This is deliberate, because the two consumers of this reader
want different things from the same resolution — the orchestrator's queue cell
and its disjointness gate need the surface whole, while the epic-surface
partition demotes leads on its OWN side. Moving a lead out of ``claimed`` here
would shrink the disjointness gate's input and make a colliding plan read as
disjoint, so this module states the shape and demotes nothing.
"""

import re
from dataclasses import dataclass
from pathlib import Path

#: Filename glob the spec corpus is enumerated by.
SPEC_GLOB = 'PLAN-*.md'

#: The three classes a spec's Expected Surface lands in.
CLASS_DECLARATIVE = 'declarative'
CLASS_DERIVED = 'derived'
CLASS_PROSE = 'prose'

#: The four shapes a resolved entry takes.
KIND_RECURSIVE_GLOB = 'recursive_glob'
KIND_DIRECTORY = 'directory'
KIND_FILENAME_GLOB = 'filename_glob'
KIND_FILE = 'file'

#: The two SHAPES a resolved entry takes, decided per ENTRY and independently of
#: the spec's class. ``claim`` is an ownership claim over the path; ``lead`` is a
#: pointer the spec has not settled — a hypothesis to verify at outline time, or
#: a statement of where the test runner collects from. A lead names a path
#: without claiming it, so a consumer deciding ownership must not read one as a
#: claim.
SHAPE_CLAIM = 'claim'
SHAPE_LEAD = 'lead'

#: The ``PLAN-``-prefixed half of the plan-id grammar — ``PLAN-{DIGITS}`` and
#: ``PLAN-{SLUG}-{DIGITS}``. Published in its own right because the prefix is the
#: corpus's own marker for a plan: a token wearing it denotes a plan WHEREVER it
#: appears, a spec's running prose included, which is what makes it the half a
#: prose-reading rule can key on.
PLAN_ID_PREFIXED_SEGMENT = r'PLAN-(?:[A-Z0-9]{2,8}-)?\d+'

#: The bare half — ``{SLUG}-{DIGITS}``, the form a code-slug spec name opens
#: with. Unambiguous only in a FILENAME, where the anchored leading position is
#: itself the statement that the token is a plan id. In PROSE the identical shape
#: is worn by the external references the corpus routinely cites — ``CWE-1333``,
#: ``CVE-2021-1234``, ``RFC-8259`` — so a prose rule keyed on this half reads a
#: standards citation as a plan citation.
PLAN_ID_BARE_SEGMENT = r'[A-Z0-9]{2,8}-\d+'

#: The plan-id segment of a spec name, as an explicit alternation over the two
#: halves above — together the settled forms ``PLAN-{DIGITS}``,
#: ``PLAN-{SLUG}-{DIGITS}`` and ``{SLUG}-{DIGITS}``. Writing it as an alternation
#: rather than as one pattern with an OPTIONAL slug group is load-bearing: an
#: optional group would also accept a bare ``01-foo.md`` that is neither
#: ``PLAN-``-prefixed nor slug-prefixed. ``{SLUG}`` is a bounded
#: uppercase-alphanumeric token and its trailing digits are mandatory, so the
#: grammar is widened without drifting toward an always-matching pattern.
#:
#: Single-definition: ``_orchestrator_inbox._SOURCE_ID_RE`` composes its own
#: pointer pattern from THIS binding rather than carrying a second copy, so the
#: two cannot drift.
PLAN_ID_SEGMENT = rf'(?:{PLAN_ID_PREFIXED_SEGMENT}|{PLAN_ID_BARE_SEGMENT})'

# --- markdown line scanners -------------------------------------------------
#
# CommonMark bounds a TOP-LEVEL block construct's leading indentation to 0-3
# SPACES; a fourth column starts an indented code block instead. Every scanner
# for such a construct — the two addressed headings, the generic heading that
# terminates a section, and the code fence — therefore writes the bound over the
# literal space character and never over ``\s``, which would readmit both the
# fourth space and a tab.
#
# ``_BULLET_RE`` is the deliberate carve-out and is bounded by horizontal
# whitespace of ANY width, because a nested list item legitimately indents past
# the third column: inside an open list item, an indented line is that item's
# continuation content, not an indented code block. The fourth column only
# starts code where no list is open, and that is the state
# ``_indented_code_mask`` tracks — so the construct the 0-3 bound exists to
# protect against is caught by the mask rather than by the bullet pattern.

#: The two sections this module addresses, and the generic ATX heading that
#: TERMINATES a section body. Both addressed headings are matched
#: case-insensitively: a case variant is a spelling of the same heading, and
#: treating it as absent would halt a spec that declared its surface.
EXPECTED_SURFACE_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Expected Surface(?:[ \t]+#+)?[ \t]*$', re.IGNORECASE)
OUT_OF_SCOPE_HEADING_RE = re.compile(r'^ {0,3}##[ \t]+Out of Scope(?:[ \t]+#+)?[ \t]*$', re.IGNORECASE)
_HEADING_RE = re.compile(r'^ {0,3}#{1,6}(?:[ \t]|$)')
#: A fenced-code-block delimiter line. Group ``fence`` carries the WHOLE RUN —
#: both the character and its length — because CommonMark closes a block only on
#: a run of the same character that is AT LEAST AS LONG as the opener: a ``~~~``
#: line inside a backtick fence is body text, and so is a three-backtick line
#: inside a four-backtick block. Group ``info`` carries whatever follows the run,
#: because only the OPENING fence may carry an info string; a delimiter with one
#: is body text, never a close.
_FENCE_RE = re.compile(r'^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$')

#: The backtick fence character, bound once so :func:`_fenced_mask` can name the
#: info-string clause it enforces instead of repeating a bare literal.
_BACKTICK = '`'
#: All three CommonMark bullet-list markers. ``+`` is admitted alongside ``-``
#: and ``*`` because a spec written with it is an ordinary list whose entries
#: would otherwise contribute nothing, silently under-classing the spec as
#: ``prose``.
_BULLET_RE = re.compile(r'^[ \t]*[-+*][ \t]+')

#: The column at which an unlisted line becomes an indented code block.
_CODE_INDENT_COLUMNS = 4

#: A tab advances to the next multiple of this width, per CommonMark.
_TAB_STOP = 4

# --- within-line scanners ----------------------------------------------------

#: ``OBSERVED:`` / ``HYPOTHESIS:`` label prefixes, including the corpus's
#: qualified forms (``OBSERVED — **re-derive; ...**:``). Everything up to the
#: first colon is the label.
#:
#: Group ``label`` RETAINS which of the two matched. The prefix is still stripped
#: from the body, but discarding which label it was is what previously made a
#: lead indistinguishable from a claim: ``HYPOTHESIS`` is precisely the corpus's
#: marker for a path the spec has NOT settled, so the distinction has to survive
#: the strip for rule (a) below to fire on it.
_LABEL_PREFIX_RE = re.compile(r'^(?P<label>OBSERVED|HYPOTHESIS)\b[^:]*:[ \t]*')

# --- entry-shape markers ------------------------------------------------------
#
# Every rule resolves a matched entry to SHAPE_LEAD, every one is a
# keyword/label/grammar marker match over the bullet's OWN text in the same
# style as _DERIVED_RE, and none of them names a plan — rule (c) keys on the
# PUBLISHED PLAN_ID_PREFIXED_SEGMENT grammar, which is the shape ANY
# PLAN--prefixed identifier takes and never a particular one, and compares the
# one it matched against the CITING spec's own id rather than against any list.
# A spec added to the corpus is shaped by the same rules with no edit here. They
# are independent: each fires on its own, and each is testable without the
# others.
#
# Rules (a), (b) and (d) read the WHOLE bullet, because the text that settles
# them routinely sits in the trailing commentary. Rule (c) reads the CLAIM HEAD
# ALONE, and that narrowing is load-bearing rather than incidental: a possessive
# citation in the head says the named span IS the other plan's surface, while
# the same citation in the commentary annotates a claim the bullet makes in its
# own right — "`_analyze_test_conventions.py` — D3 ⛔ WS-03's surface" claims
# that file and merely notes whose tree it sits in. Reading rule (c) over the
# whole bullet would demote most of the corpus, since a spec routinely names its
# neighbours when it explains a claim.

#: Rule (a), the label half — the label that marks a bullet a LEAD. A
#: ``HYPOTHESIS:`` bullet names a candidate path for outline-time verification,
#: not a surface the plan claims.
_LEAD_LABEL = 'HYPOTHESIS'

#: Rule (a), the phrase half — the corpus's explicit deferral phrase. Carries the
#: same meaning as the label and appears in the bullet's commentary, so a lead
#: written without the label is still resolved as one.
_LEAD_PHRASE_RE = re.compile(r'\bverify-at-outline\b', re.IGNORECASE)

#: Rule (b) — a collection constraint. ``testpaths`` is the pytest key naming
#: where the runner COLLECTS from; a bullet citing it is stating a constraint the
#: plan's own test location must satisfy, not claiming that tree. Matched
#: case-sensitively on the settings key itself, which is what keeps the rule
#: corpus-independent.
_COLLECTION_CONSTRAINT_RE = re.compile(r'\btestpaths\b')

#: Rule (c) — a CROSS-PLAN REFERENCE. A bullet whose CLAIM cites ANOTHER plan's
#: surface possessively is quoting that plan's ownership rather than asserting
#: its own: ``slice `050`'s ten directories under `test/plan-marshall/``` names
#: the tree slice 050 owns, and ``run 2 → PLAN-040's sixteen entries under
#: `test/plan-marshall/``` names PLAN-040's. Honouring either as a claim makes
#: the CITING plan a co-owner of the CITED plan's whole slice, which contests
#: that slice in full — the single largest residual driver in the corpus.
#:
#: ⛔ ANOTHER plan's, and the pattern alone cannot say that. A possessive-shape
#: match says only "SOME plan's", so the cited identifier is compared against the
#: CITING spec's own plan id by :func:`_cites_another_plan`, and a match on its
#: own id is NOT a cross-plan reference. A spec writing ``PLAN-170's own tests
#: under `test/x/``` is asserting ownership in the most direct words the corpus
#: offers; demoting it drops the module from ``claimed`` to ``not_derivable`` —
#: the exact INVERSE of the co-ownership defect this rule was added to close.
#:
#: ⛔ Keyed on :data:`PLAN_ID_PREFIXED_SEGMENT`, deliberately NOT on the whole
#: :data:`PLAN_ID_SEGMENT`. The bare ``{SLUG}-{DIGITS}`` half is a plan id only
#: in a filename's anchored leading position; in prose it equally matches the
#: external references the corpus cites, so ``bounded by CWE-1333's total
#: budget`` read as a plan citation and demoted the claim beside it. The
#: ``PLAN-`` prefix is the corpus's own plan marker and no standards reference
#: wears it. The residual is stated rather than hidden: a possessive citation of
#: a BARE code-slug sibling in a claim head stays a claim, which is the
#: conservative direction — the rule never invents a demotion it cannot
#: substantiate.
#:
#: Keyed on published grammar plus the possessive marker, so no particular plan
#: is named and a citation of a plan added later is read the same way. The
#: ``slice N`` alternative covers the corpus's other citation form, where the
#: reference is by slice ordinal rather than by full identifier and the ordinal
#: may be backticked; its digits are equally unbound to any one plan, and a slice
#: ordinal is never a spec's own plan id, so it always reads as another's. Both
#: the straight and the typographic apostrophe are admitted, because a spec
#: written with either is making the same citation. The two citations above are
#: quoted from the corpus to show the SHAPE the rule reads; neither identifier
#: appears in the pattern, which carries the grammar and nothing drawn from any
#: one spec.
_CROSS_PLAN_REFERENCE_RE = re.compile(
    rf"(?P<cited>\b{PLAN_ID_PREFIXED_SEGMENT}|\bslice[ \t]+`?\d+`?)['’]s\b"
)

#: Rule (d) — a HEDGED CONDITIONAL CLAIM. A bullet that names a span and then
#: WITHDRAWS it in its own words is not claiming that span: ``the tests for this
#: plan's own production changes, under `test/plan-marshall/` … Only where a D2
#: seam requires its own test — this plan does not otherwise edit `test/**` ``
#: names a whole subtree while stating the plan touches almost none of it.
#: Reading the span as ownership contests every module beneath it.
#:
#: Two settled withdrawal phrasings, each an ordinary English hedge rather than
#: any one spec's boilerplate: a conditional restriction on the claim (``only
#: where``), and an explicit denial of further coverage (``does not
#: otherwise``). Either alone marks the bullet. The rule reads the whole bullet
#: because the denial half routinely sits after the em dash, in the same
#: commentary the claim's paths are deliberately not taken from.
_HEDGED_CLAIM_RE = re.compile(r'\bonly where\b|\bdoes not otherwise\b', re.IGNORECASE)

#: A ``` `span` ``` of backticked text — the corpus's path notation.
_BACKTICK_RE = re.compile(r'`([^`\n]+)`')

#: Decoration a bullet may open with before its real text: bold/italic markers,
#: the ⛔ and ⚠/⚠️ markers, and whitespace.
_LEADING_DECORATION = r'[\s*_⛔⚠️]*'

#: A bullet stating what the plan does NOT touch. Its paths are exclusions.
_NEGATIVE_CLAIM_RE = re.compile(rf'^{_LEADING_DECORATION}no\b', re.IGNORECASE)

#: The em-dash separator between a bullet's claim and its trailing commentary.
_TAIL_SPLIT_RE = re.compile(r'\s—\s')

#: The carve-out keyword. Spans after it in the same segment are exclusions.
_EXCLUDING_RE = re.compile(r'\bexcluding\b', re.IGNORECASE)

#: The corpus's self-declaration that a surface is a function of other plans'.
#: Matched case-SENSITIVELY on the uppercase emphasis the corpus uses, so the
#: ordinary lowercase ``re-derive`` prose several specs carry is not a match.
_DERIVED_RE = re.compile(r'\bDERIVED\b')

#: The plan identifier a spec filename opens with, over the settled forms named
#: once in :data:`PLAN_ID_SEGMENT`. Anchored at the start of the filename.
_PLAN_ID_RE = re.compile(rf'^({PLAN_ID_SEGMENT})')

#: Characters that cannot appear in a repository path. Their presence in a
#: backticked span is what separates a path from the corpus's many other
#: backticked tokens — symbol names, notations, flags, quoted output.
_NON_PATH_CHARS = frozenset(' \t()[]{}<>:;,=!?|"\'`$%&^~#@\\')


class UnclassifiableSpecError(Exception):
    """A spec whose Expected-Surface class cannot be determined.

    Raised instead of defaulting to a class, so the run halts with the spec
    named. Carries ``spec`` and ``reason`` for the caller's structured report.
    """

    def __init__(self, spec: str, reason: str) -> None:
        super().__init__(f'{spec}: {reason}')
        self.spec = spec
        self.reason = reason


@dataclass(frozen=True)
class PathEntry:
    """One path a spec names, resolved against the repository root.

    ``shape`` records whether the spec CLAIMS the path or merely LEADS to it,
    decided per entry by the entry-shape marker rules and never inherited from
    the spec's class. It is an ADDED fact: an entry keeps its membership of
    ``claimed`` / ``excluded`` whatever its shape, so a consumer that ignores
    ``shape`` reads exactly the surface it read before the field existed.
    """

    path: str
    kind: str
    shape: str = SHAPE_CLAIM


@dataclass(frozen=True)
class SpecClaim:
    """One spec's parsed surface, its class, and the evidence for that class."""

    plan_id: str
    spec: str
    spec_class: str
    evidence: str
    claimed: tuple[PathEntry, ...]
    excluded: tuple[PathEntry, ...]
    unresolved: tuple[str, ...]


def _fenced_mask(lines: list[str]) -> list[bool]:
    """Mark every line that sits inside a fenced code block (fences included).

    BOTH decisions — whether a line OPENS a block and whether it CLOSES one — are
    taken against the CommonMark clauses. A block opens only on a delimiter
    indented at most three spaces whose info string is admissible for its fence
    character, and closes only on a delimiter indented at most three spaces,
    built from the SAME character as the opener, AT LEAST AS LONG as the opener,
    and carrying no info string.

    ⛔ The opening run's LENGTH is retained, not just its character. A
    length-blind close ends a four-backtick block at the first three-backtick
    example inside it, after which a ``#`` comment on the next line reads as a
    heading and TRUNCATES the enclosing section — so a spec that declared its
    surface after that example resolves to ``prose`` and the gate reads a
    confident empty surface. That is the very failure this parser is the single
    reader in order to prevent, so the rule is load-bearing here and not a
    fidelity nicety. An unterminated fence runs to the end of the document.
    """
    mask = [False] * len(lines)
    open_char = ''
    open_length = 0
    for index, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if match is None:
            mask[index] = bool(open_char)
            continue
        run = match.group('fence')
        info = match.group('info')
        if open_char:
            mask[index] = True
            if run[0] == open_char and len(run) >= open_length and not info.strip():
                open_char, open_length = '', 0
            continue
        if run[0] == _BACKTICK and _BACKTICK in info:
            # Not an opening fence: a backtick fence's info string may not carry
            # a backtick, so this is an ordinary paragraph line — the shape a
            # sentence takes when it opens with the fence marker and then quotes
            # inline code. Masking it would swallow the rest of the document.
            continue
        mask[index] = True
        open_char, open_length = run[0], len(run)
    return mask


def _leading_columns(line: str) -> int:
    """The column the line's first non-whitespace character sits at."""
    column = 0
    for char in line:
        if char == ' ':
            column += 1
        elif char == '\t':
            column += _TAB_STOP - (column % _TAB_STOP)
        else:
            break
    return column


def _indented_code_mask(lines: list[str], fenced: list[bool]) -> list[bool]:
    """Mark every line that sits inside an INDENTED code block.

    A fourth column only opens a code block where no list item is open; inside
    an open item the same indentation is that item's continuation content. The
    scan therefore tracks list state: a bullet opens it, a non-blank line back
    at columns 0-3 that is not a bullet closes it, and a blank line leaves it
    unchanged (a blank line does not end a list).
    """
    mask = [False] * len(lines)
    list_open = False
    for index, line in enumerate(lines):
        if fenced[index] or not line.strip():
            continue
        indented = _leading_columns(line) >= _CODE_INDENT_COLUMNS
        if indented and not list_open:
            mask[index] = True
        elif _BULLET_RE.match(line):
            list_open = True
        elif not indented:
            list_open = False
    return mask


def _mask_union(first: list[bool], second: list[bool]) -> list[bool]:
    """The lines masked by either scan."""
    return [left or right for left, right in zip(first, second, strict=True)]


def _section_span(lines: list[str], heading_re: re.Pattern[str], masked: list[bool]) -> tuple[int, int]:
    """Return the ``[start, end)`` body span of one section, or ``(-1, -1)``.

    The body ends at the next heading of any level, so a subsection never leaks
    into the parent. Both heading scans skip masked (code-block) lines.
    """
    start = -1
    for index, line in enumerate(lines):
        if not masked[index] and heading_re.match(line):
            start = index + 1
            break
    if start < 0:
        return (-1, -1)
    for index in range(start, len(lines)):
        if not masked[index] and _HEADING_RE.match(lines[index]):
            return (start, index)
    return (start, len(lines))


def _iter_bullets(lines: list[str], masked: list[bool], start: int, end: int) -> list[str]:
    """Return each bullet in a section span as one joined logical line.

    A bullet runs until the next bullet, a blank line, or the section end, so a
    surface entry wrapped across source lines is parsed whole. Non-bullet
    paragraph text is section preamble and contributes no entry.
    """
    bullets: list[str] = []
    current: list[str] = []
    for index in range(start, end):
        if masked[index]:
            continue
        line = lines[index]
        if _BULLET_RE.match(line):
            if current:
                bullets.append(' '.join(current))
            current = [_BULLET_RE.sub('', line).strip()]
        elif not line.strip():
            if current:
                bullets.append(' '.join(current))
                current = []
        elif current:
            current.append(line.strip())
    if current:
        bullets.append(' '.join(current))
    return bullets


def _is_path_candidate(span: str, repo_root: Path) -> bool:
    """Whether a backticked span denotes a repository path.

    A multi-segment span is a path. A single-segment span is one only when it
    globs or actually exists at ``repo_root`` — which is what keeps
    ``monkeypatch.delitem`` and the corpus's other dotted symbol names out,
    while admitting ``pyproject.toml`` and ``test_*.py``.
    """
    if not span or span.startswith('-'):
        return False
    if any(char in _NON_PATH_CHARS for char in span):
        return False
    if '/' in span:
        return True
    return '*' in span or (repo_root / span).exists()


def _is_rooted(span: str, repo_root: Path) -> bool:
    """Whether a candidate's first segment is a real top-level entry.

    Derived from the tree rather than from a hand-listed set of roots, so a new
    top-level directory needs no edit here.
    """
    first = span.split('/', 1)[0]
    if not first or first == '...':
        return False
    return (repo_root / first).exists()


def _base_from(rooted: str) -> str:
    """The directory a bullet's relative entries resolve against.

    A recursive glob names the directory its entries live under; every other
    shape names a sibling, so the base is that entry's parent.
    """
    if rooted.endswith('**'):
        stem = rooted[:-2]
    else:
        trimmed = rooted.rstrip('/')
        stem = trimmed.rsplit('/', 1)[0] if '/' in trimmed else ''
    if stem and not stem.endswith('/'):
        stem += '/'
    return stem


def _entry_kind(path: str) -> str:
    """Classify a resolved path into one of the four entry shapes."""
    if path.endswith('**'):
        return KIND_RECURSIVE_GLOB
    if path.endswith('/'):
        return KIND_DIRECTORY
    if '*' in path:
        return KIND_FILENAME_GLOB
    return KIND_FILE


def _spans_with_exclusion(segment: str) -> list[tuple[str, bool]]:
    """Return each backticked span with whether it follows an ``excluding``."""
    match = _EXCLUDING_RE.search(segment)
    cut = match.end() if match else None
    return [
        (found.group(1), cut is not None and found.start() >= cut)
        for found in _BACKTICK_RE.finditer(segment)
    ]


def _bullet_segments(body: str) -> list[str]:
    """The parts of a bullet that carry surface entries.

    The head — everything before the first em dash — is the claim. The trailing
    commentary is dropped, because it cites paths as reasons rather than
    claiming them, EXCEPT when it carries the carve-out keyword: several specs
    write their exclusion after the dash.
    """
    parts = _TAIL_SPLIT_RE.split(body, maxsplit=1)
    head = parts[0]
    tail = parts[1] if len(parts) > 1 else ''
    if tail and _EXCLUDING_RE.search(tail):
        return [head, tail]
    return [head]


def _cites_another_plan(head: str, plan_id: str) -> bool:
    """Whether the claim head possessively cites a plan OTHER than the citing one.

    Rule (c)'s decision, and the whole of what separates it from a possessive
    SHAPE match. Every citation in the head is examined and its cited identifier
    compared against ``plan_id``; a head whose citations are all the spec's OWN
    identifier cites no other plan, so its entries keep their claim. A slice
    ordinal is never a plan id, so it never compares equal and always reads as
    another's.
    """
    return any(
        match.group('cited') != plan_id
        for match in _CROSS_PLAN_REFERENCE_RE.finditer(head)
    )


def _entry_shape(label: str, body: str, head: str, plan_id: str) -> str:
    """Resolve one bullet's entry shape from its own label and text.

    Four independent marker rules, each resolving the bullet's entries to
    :data:`SHAPE_LEAD` on its own:

    (a) a ``HYPOTHESIS`` label, or the ``verify-at-outline`` deferral phrase —
        a candidate path named for outline-time verification;
    (b) a ``testpaths`` collection constraint — a statement about where the test
        runner collects from, not a claim over that tree;
    (c) a possessive citation of ANOTHER plan's surface in the claim head — a
        reference to that plan's ownership, not an assertion of this one's;
    (d) a withdrawal of the bullet's own span — a conditional restriction on the
        claim, or an explicit denial of further coverage.

    Anything else is an ordinary claim.

    ``head`` is the claim segment alone and ``body`` the whole bullet: rule (c)
    reads the first and the other three read the second, for the reason given in
    the marker block above. ``plan_id`` is the CITING spec's own identifier, and
    rule (c) is the only rule that reads it — a possessive citation is a
    cross-plan reference only relative to who is doing the citing.

    The spec's class is deliberately not an input: shape is decided per entry,
    so one spec's bullets may resolve to different shapes.
    """
    if label == _LEAD_LABEL or _LEAD_PHRASE_RE.search(body):
        return SHAPE_LEAD
    if _COLLECTION_CONSTRAINT_RE.search(body):
        return SHAPE_LEAD
    if _cites_another_plan(head, plan_id):
        return SHAPE_LEAD
    if _HEDGED_CLAIM_RE.search(body):
        return SHAPE_LEAD
    return SHAPE_CLAIM


def _collect_bullet(
    bullet: str,
    repo_root: Path,
    plan_id: str,
    force_excluded: bool,
    claimed: list[PathEntry],
    excluded: list[PathEntry],
    unresolved: list[str],
) -> None:
    """Resolve one bullet's entries into the caller's three accumulators.

    Every entry the bullet yields carries the bullet's resolved shape. The shape
    steers no accumulator: it is recorded ON the entry, never used to route one
    away from ``claimed``, so the membership the other consumer of this reader
    compares is unchanged by it.

    ``plan_id`` is the citing spec's own identifier, forwarded for rule (c) so a
    spec naming ITSELF possessively is not read as citing a neighbour.
    """
    label_match = _LABEL_PREFIX_RE.match(bullet)
    label = label_match.group('label') if label_match else ''
    body = bullet[label_match.end():] if label_match else bullet
    negative = bool(_NEGATIVE_CLAIM_RE.match(body))
    segments = _bullet_segments(body)
    shape = _entry_shape(label, body, segments[0], plan_id)

    spans: list[tuple[str, bool]] = []
    for segment in segments:
        spans.extend(_spans_with_exclusion(segment))

    # The ``./`` prefix is normalised away HERE, before the base loop, because
    # ``_is_rooted`` reads the first segment and ``(repo_root / '.').exists()``
    # is always true: a ``./``-prefixed span would otherwise read as rooted and
    # poison ``base`` for the bullet's LATER relative entries, which would then
    # resolve to a path no test module ever carries. The candidate FILTER still
    # sees the raw span, so ``./x`` is still admitted by its slash.
    candidates = [
        (span[2:] if span.startswith('./') else span, after)
        for span, after in spans
        if _is_path_candidate(span, repo_root)
    ]
    base = ''
    for span, _ in candidates:
        if _is_rooted(span, repo_root):
            base = _base_from(span)
            break

    for span, after_excluding in candidates:
        if _is_rooted(span, repo_root):
            path = span
        else:
            relative = span[4:] if span.startswith('.../') else span
            if not base:
                unresolved.append(span)
                continue
            path = base + relative
        entry = PathEntry(path=path, kind=_entry_kind(path), shape=shape)
        is_exclusion = force_excluded or negative or after_excluding
        (excluded if is_exclusion else claimed).append(entry)


def _evidence_line(body: str, position: int) -> str:
    """The source line containing ``position``, as the recorded evidence."""
    line_start = body.rfind('\n', 0, position) + 1
    line_end = body.find('\n', position)
    if line_end < 0:
        line_end = len(body)
    return body[line_start:line_end].strip()


def plan_id_of(spec_name: str) -> str:
    """The plan identifier a spec filename opens with, or the bare filename.

    Resolves all three settled forms via :data:`PLAN_ID_SEGMENT`, so a
    code-slug spec (``PLAN-TRUTH-098-….md``) keys on ``PLAN-TRUTH-098`` rather
    than on its whole filename — which is what makes cross-plan grouping work
    for the code-slug half of the corpus.
    """
    match = _PLAN_ID_RE.match(spec_name)
    return match.group(1) if match else spec_name


def classify_spec(spec_path: Path, repo_root: Path) -> SpecClaim:
    """Parse one spec's surface and assign it exactly one class with evidence.

    Raises:
        UnclassifiableSpecError: when the spec cannot be read, or carries no
            ``## Expected Surface`` section — the two states in which no class
            can be determined.

    "Cannot be read" covers BOTH failure modes of a text read, and the decode one
    is not incidental: ``read_text`` raises :class:`UnicodeDecodeError` — a
    ``ValueError``, not an ``OSError`` — for a spec whose bytes are not valid
    UTF-8, so catching ``OSError`` alone let that case escape as an unhandled
    exception. Every caller treats this error as the readable/unreadable
    discriminator, so an escaping decode failure did not merely crash one verb: it
    made ``unreadable`` unreachable for the whole decode route, leaving the state
    reportable only for a spec that failed to open.
    """
    try:
        text = spec_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as error:
        raise UnclassifiableSpecError(spec_path.name, f'unreadable: {error}') from error

    lines = text.splitlines()
    fenced = _fenced_mask(lines)
    masked = _mask_union(fenced, _indented_code_mask(lines, fenced))
    start, end = _section_span(lines, EXPECTED_SURFACE_HEADING_RE, masked)
    if start < 0:
        raise UnclassifiableSpecError(spec_path.name, 'no "## Expected Surface" section')

    plan_id = plan_id_of(spec_path.name)
    claimed: list[PathEntry] = []
    excluded: list[PathEntry] = []
    unresolved: list[str] = []

    for bullet in _iter_bullets(lines, masked, start, end):
        _collect_bullet(bullet, repo_root, plan_id, False, claimed, excluded, unresolved)

    scope_start, scope_end = _section_span(lines, OUT_OF_SCOPE_HEADING_RE, masked)
    if scope_start >= 0:
        for bullet in _iter_bullets(lines, masked, scope_start, scope_end):
            _collect_bullet(bullet, repo_root, plan_id, True, claimed, excluded, unresolved)

    # The marker is searched over the SAME masked lines the two scans above
    # honour: a code sample carrying the token is a sample, not a declaration.
    # Masked lines are blanked rather than dropped so the recorded evidence
    # still resolves to the real source line.
    body = '\n'.join('' if masked[index] else lines[index] for index in range(start, end))
    derived = _DERIVED_RE.search(body)
    if derived is not None:
        spec_class = CLASS_DERIVED
        evidence = _evidence_line(body, derived.start())
    elif claimed:
        spec_class = CLASS_DECLARATIVE
        evidence = f'{len(claimed)} resolved path entries; first: {claimed[0].path}'
    else:
        spec_class = CLASS_PROSE
        evidence = 'Expected Surface present; no entry the parser resolves to a path'

    return SpecClaim(
        plan_id=plan_id,
        spec=spec_path.name,
        spec_class=spec_class,
        evidence=evidence,
        claimed=tuple(claimed),
        excluded=tuple(excluded),
        unresolved=tuple(unresolved),
    )


def classify_corpus(plans_dir: Path, repo_root: Path) -> list[SpecClaim]:
    """Classify every spec in an epic's ``plans/`` directory, in filename order."""
    return [classify_spec(spec, repo_root) for spec in sorted(plans_dir.glob(SPEC_GLOB))]
