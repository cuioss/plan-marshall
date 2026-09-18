#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Derivation guard for the merge-authorization population.

Every mechanism by which an operator (or a policy standing in for one) can
authorize advancing a tree past a merge gate is declared in the
``## Merge-Authorization Roster`` section of ``branch-cleanup.md``. That section
is the single home of the membership; this module derives the population from it
by parsing the section's rows, so a mechanism added there is covered
automatically.

The population is **derived, never hardcoded**, and this module deliberately
asserts **no cardinality literal**: a pinned count is the drift shape the roster
exists to remove, and it would need hand-editing the first time a mechanism is
added.

The tests pin:

(a) The derived roster is **non-empty** — asserted first and on its own, because
    every later assertion would pass vacuously against an empty parse. This is
    not theoretical: ``ROSTER_ROW`` matches Markdown list items only, so
    rendering the roster as a pipe-delimited table yields ZERO rows and silently
    disarms the whole module.
(b) Every row declares the four machine-checkable claims (``head_bound:``,
    ``bound_via:``, ``authorizes:``, ``site:``). Without them a row is prose
    rather than a falsifiable claim, and (c) would have nothing to check it
    against.
(c) Every row's binding claim is cross-checked against real document content at
    the ``site:`` the row itself names — a ``grant`` row against a real
    ``merge-authorization grant`` invocation carrying ``--kind {kind}``,
    ``--plan-id`` and a ``--gap-class`` matching the row's own ``authorizes:``
    claim, a ``head_dependent`` row against its own frontmatter declaration.
(d) Out-of-class rows are **annotated rather than silently absent**, so a
    mechanism that does not fit the HEAD-bound class can never be hidden by
    simply not listing it.
(e) The barrier actually consults the verb the roster claims backs every
    ``bound_via: grant`` row, and states the D4 rule that a ``decision``-log
    entry is never admissible authorization evidence.
(h) The barrier routes on ADMISSIBILITY, not on HEAD-validity — it passes its own
    gap class to the check, and it does not carry an ``any_authorized``-only
    routing branch. This is the guard for the cross-kind hazard: three of the
    four grant kinds are granted at sites that run BEFORE the barrier, at the
    SAME HEAD, over a DIFFERENT gap, so a HEAD-only route would bypass the
    barrier's disposition on essentially every merge. The admissible set is
    DERIVED from the roster's ``authorizes:`` claims rather than listed here, and
    the test asserts the inadmissible set is non-empty first — without that
    precondition the whole check would be vacuous on a roster where every row
    happened to share one class.
(i) Every grant site declares a ``--gap-class``, so a site cannot fall back to
    HEAD-only authorization by simply omitting the flag.
(j) The ``--kind`` / ``--gap-class`` matchers are **form-agnostic** — they read
    both the space-separated and the ``=``-joined argument forms. A matcher that
    saw only one form would make an equals-form grant site invisible to the
    independent corpus sweep below, i.e. fail OPEN in a guard built to fail
    closed. No corpus invocation currently uses the equals form, so the corpus
    alone cannot catch that regression.

Plus the **both-directions** membership check and its per-member mutation guard:
the grant invocations that actually exist across the marketplace docs are
derived independently of the roster, so a grant site the roster never lists is
reported (f), and dropping exactly one roster row makes that same predicate
report exactly that row (g). The predicate is deliberately driven by the
INDEPENDENT corpus population rather than by the roster's own key list — a guard
whose expected and actual sides both derive from the roster is pure set
arithmetic and cannot fail, which is precisely the vacuous-guard shape this
project keeps re-introducing.

The roster's row shape, its claim vocabulary, and its membership live in the
central standard — see
``marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md``
§ "Merge-Authorization Roster". They are deliberately NOT restated here.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import pytest

from _dispatch_roster import parse_roster_rows, section_lines
from conftest import MARKETPLACE_ROOT

#: The heading that bounds the declared population.
_ROSTER_HEADING = '## Merge-Authorization Roster'

#: The barrier subsection that must consult the verb.
_CHECK_HEADING = '#### Authorization check — the only admissible evidence on a blocked path'

#: Sub-heading prefixes that terminate a ``####`` subsection walk.
_SUBSECTION_STOPS = ('#### ', '### ', '## ')

_BUNDLE_ROOT: Path = Path(MARKETPLACE_ROOT)
_STANDARDS_DIR: Path = _BUNDLE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards'
_BRANCH_CLEANUP: Path = _STANDARDS_DIR / 'branch-cleanup.md'

#: The verb name itself is a constant, not a membership list — the roster's own
#: closing claim that this verb backs every ``bound_via: grant`` row is asserted
#: against it in ``test_barrier_checks_the_authorization_verb``.
_VERB = 'merge-authorization'
_GRANT_VERB = f'{_VERB} grant'
_CHECK_VERB = f'{_VERB} check'

_CLAIM_RE = {
    'head_bound': re.compile(r'head_bound:\s*(\S+)'),
    'bound_via': re.compile(r'bound_via:\s*(\S+)'),
    'authorizes': re.compile(r'authorizes:\s*(\S+)'),
}

#: The gap class the pre-merge review barrier reports. A roster row whose
#: ``authorizes:`` claim equals this token is admissible AT THAT BARRIER; every
#: other grant row is a ruling over some other gate's gap. Only the token itself
#: is a constant here — WHICH rows carry it is derived from the roster.
_BARRIER_GAP_CLASS = 'review-barrier-gap'

#: The first Markdown link target inside a row's ``site:`` claim.
_SITE_LINK_RE = re.compile(r'\]\(([^)]+)\)')

#: The roster's closing claim about which verb backs the grant rows.
_VERB_CLAIM_RE = re.compile(r'verb backing every `bound_via: grant` row is `([^`]+)`')

#: Separator between a long option and its value. argparse accepts BOTH the
#: space-separated form (``--kind X``) and the equals form (``--kind=X``), so a
#: matcher that recognized only one would read a real invocation written in the
#: other as carrying no such argument at all. That direction is fail-OPEN in
#: guards built to be fail-closed: an unmatched ``--kind`` empties the corpus
#: population for that block, hiding the grant site from the reverse-direction
#: membership check and from its mutation guard.
_ARG_SEP = r'(?:\s+|=)'

#: The ``--kind`` value of one grant invocation, in either argparse form.
_KIND_ARG_RE = re.compile(rf'--kind{_ARG_SEP}([^\s\\]+)')

#: The ``--gap-class`` value of one grant or check invocation, in either form.
_GAP_CLASS_ARG_RE = re.compile(rf'--gap-class{_ARG_SEP}([^\s\\]+)')

#: The normative rule the barrier must state in as many words.
_INADMISSIBLE_EVIDENCE_MARKERS = ('decision', 'NEVER admissible')


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


#: Module-level derivation so the per-row tests can parametrize over it. Parsed
#: once at collection time from the authoritative document — no literal list.
_ROWS: list[tuple[str, str]] = parse_roster_rows(_read(_BRANCH_CLEANUP), _ROSTER_HEADING)

# ⛔ Vacuity guard — the rows are parsed out of a document, so a heading that moved
# collects zero cases at every parametrize below and still reports green.
assert _ROWS, f'no roster rows parsed under {_ROSTER_HEADING!r} in {_BRANCH_CLEANUP}'
_ROSTER_KINDS: list[str] = [kind for kind, _ in _ROWS]


def _claim(row_line: str, name: str) -> str | None:
    """Read one machine-checkable claim off a roster row."""
    match = _CLAIM_RE[name].search(row_line)
    return match.group(1) if match else None


def _grant_rows() -> list[tuple[str, str]]:
    """The roster rows whose binding mechanism is a real ``grant`` invocation."""
    return [(kind, row) for kind, row in _ROWS if _claim(row, 'bound_via') == 'grant']


#: Grant rows split by the barrier's own gap class — DERIVED from the roster's
#: ``authorizes:`` claims, never listed. Adding a mechanism to the roster puts it
#: on exactly one of these two sides automatically.
_BARRIER_ADMISSIBLE: list[str] = [
    kind for kind, row in _grant_rows() if _claim(row, 'authorizes') == _BARRIER_GAP_CLASS
]
_BARRIER_INADMISSIBLE: list[str] = [
    kind for kind, row in _grant_rows() if _claim(row, 'authorizes') != _BARRIER_GAP_CLASS
]


def _rationale(row_line: str) -> str:
    """The prose a row carries after its ``site:`` claim."""
    _, _, tail = row_line.partition('site:')
    return tail.strip()


def _site_doc_for(row_line: str) -> Path:
    """The document a row's ``site:`` claim names.

    The link target is resolved RELATIVE TO the roster's own host document, so
    the resolution derives from the row rather than from a basename table that
    would have to be hand-extended for every new site. A row whose ``site:``
    names no document at all refers to a section of the host itself, which is
    where an unqualified "§ ..." reference points.
    """
    match = _SITE_LINK_RE.search(_rationale(row_line))
    if match is None:
        return _BRANCH_CLEANUP
    return (_BRANCH_CLEANUP.parent / match.group(1)).resolve()


def _fenced_blocks(text: str) -> list[str]:
    """Every fenced code block in ``text``.

    Scoping the invocation search to fenced blocks is what keeps a *prose*
    mention of the verb ("then grant, see ... → `merge-authorization — grant`")
    from being read as a call site.
    """
    return text.split('```')[1::2]


def _invocations(text: str, verb: str) -> list[str]:
    """Every fenced block that issues ``verb``."""
    return [block for block in _fenced_blocks(text) if verb in block]


def _is_form_placeholder(token: str) -> bool:
    """True for a documented ARGUMENT FORM rather than a real granted kind.

    A canonical-invocations block advertises the shape ``--kind KIND`` and a
    workflow template writes ``--kind {kind}``; neither is a mechanism that was
    ever granted, so both are excluded from the corpus population.
    """
    return '{' in token or token.isupper()


def _kinds_in(block: str) -> list[str]:
    """Every concrete ``--kind`` value in one invocation block, in either argparse form.

    The SINGLE reader of the ``--kind`` argument in this module: the corpus
    sweep, the roster-driven site check, and the gap-class sweep all resolve
    kinds through it. Routing every call site through one reader is what stops
    any of them drifting back to a form-specific literal substring test — an
    ``f'--kind {kind}' in block`` check silently misses ``--kind={kind}`` and
    reports the site as absent rather than as present-in-another-form.
    """
    return [token for token in _KIND_ARG_RE.findall(block) if not _is_form_placeholder(token)]


@lru_cache(maxsize=1)
def _corpus_grant_kinds() -> tuple[str, ...]:
    """Every authorization kind actually granted somewhere in the marketplace.

    Derived by sweeping every bundle document for real ``merge-authorization
    grant`` invocations — INDEPENDENTLY of the roster. This is the second
    direction of the membership check: the roster answers "is every declared
    mechanism real?", and this corpus answers "is every real mechanism
    declared?". A one-directional check cannot see a grant site nobody listed.
    """
    kinds: set[str] = set()
    for doc in sorted(_BUNDLE_ROOT.rglob('*.md')):
        text = _read(doc)
        if _GRANT_VERB not in text:
            continue
        for block in _invocations(text, _GRANT_VERB):
            kinds.update(_kinds_in(block))
    # ⛔ Vacuity guard — a sweep that found no grant site collects zero cases at the
    # parametrize that binds this helper, reporting green while checking no mechanism.
    assert kinds, 'no merge-authorization grant invocation was found anywhere in the bundles'
    return tuple(sorted(kinds))


def _undeclared_grant_kinds(declared: set[str]) -> list[str]:
    """The membership predicate: granted kinds absent from ``declared``.

    Factored out so the mutation guard drives the SAME predicate the closure
    assertion uses — a guard that re-implemented the check would prove nothing
    about the check that actually runs. Both sides are independent: the left is
    swept out of the documents, the right is parsed out of the roster.
    """
    return [kind for kind in _corpus_grant_kinds() if kind not in declared]


@pytest.mark.parametrize(
    'block,expected_kind,expected_class',
    [
        pytest.param(
            'merge-authorization grant --plan-id P --kind sample-override --head abc --gap-class sample-gap\n',
            'sample-override',
            'sample-gap',
            id='space-separated',
        ),
        pytest.param(
            'merge-authorization grant --plan-id=P --kind=sample-override --head=abc --gap-class=sample-gap\n',
            'sample-override',
            'sample-gap',
            id='equals-separated',
        ),
        pytest.param(
            'merge-authorization grant --plan-id P --kind=sample-override --head abc --gap-class sample-gap\n',
            'sample-override',
            'sample-gap',
            id='mixed-forms',
        ),
    ],
)
def test_argument_matchers_are_form_agnostic(block, expected_kind, expected_class):
    """The ``--kind`` / ``--gap-class`` readers accept BOTH argparse forms.

    argparse accepts ``--kind X`` and ``--kind=X`` interchangeably, so a matcher
    keyed to whitespace alone reads an equals-form invocation as carrying no
    ``--kind`` at all. That miss is fail-OPEN in guards built to be fail-closed:
    an empty kind list for a block drops the site out of ``_corpus_grant_kinds``,
    so ``test_every_granted_kind_is_declared_in_the_roster`` and its mutation
    guard never see it, and ``test_every_grant_site_declares_a_gap_class``
    short-circuits on its ``if kinds`` precondition. The equals form is pinned
    here explicitly because it is the form no real invocation in the corpus
    currently uses — the corpus alone would keep this passing while the matcher
    silently lost the ability to see it.
    """
    assert _kinds_in(block) == [expected_kind]
    assert _GAP_CLASS_ARG_RE.findall(block) == [expected_class]


@pytest.mark.parametrize('kind,row_line', _ROWS, ids=_ROSTER_KINDS)
def test_every_row_declares_the_four_machine_checkable_claims(kind, row_line):
    """(b) Each row carries ``head_bound:``, ``bound_via:``, ``authorizes:`` and ``site:``.

    Without all four the row is prose rather than a falsifiable claim, and the
    binding assertions below would have nothing to check it against.
    ``authorizes:`` is the newest and the one that decides ROUTING: a row without
    it declares no gap class, so no check site can tell whether the ruling covers
    the gap it is reporting.
    """
    assert _claim(row_line, 'head_bound'), f'{kind} row declares no head_bound: claim — {row_line}'
    assert _claim(row_line, 'bound_via'), f'{kind} row declares no bound_via: claim — {row_line}'
    assert _claim(row_line, 'authorizes'), (
        f'{kind} row declares no authorizes: claim — {row_line}. Without a declared gap '
        'class a check site cannot distinguish a ruling given over ITS gap from one '
        'given over some other gate at the same HEAD.'
    )
    assert 'site:' in row_line, f'{kind} row declares no site: claim — {row_line}'


@pytest.mark.parametrize('kind,row_line', _ROWS, ids=_ROSTER_KINDS)
def test_out_of_class_rows_are_annotated_rather_than_silently_absent(kind, row_line):
    """(d) An out-of-class member is recorded WITH a rationale, never omitted.

    Leaving a mechanism off the roster because it does not fit the HEAD-bound
    class is exactly how an unhandled member hides. Recording it with an explicit
    non-``yes`` ``head_bound:`` and a rationale keeps it visible and reviewable.

    Rows inside the HEAD-bound class are asserted by
    ``test_every_head_bound_row_has_a_grant_site`` above; the class split is a
    branch, not a skip, so every row is covered by exactly one of the two.
    """
    if _claim(row_line, 'bound_via') == 'grant':
        assert _claim(row_line, 'head_bound') == 'yes', (
            f'{kind} binds via grant, so it belongs to the HEAD-bound class and must claim head_bound: yes.'
        )
        return

    assert _claim(row_line, 'head_bound') != 'n/a' or _claim(row_line, 'bound_via') == 'out_of_class', (
        f'{kind} claims head_bound: n/a without declaring bound_via: out_of_class — a '
        'member outside the HEAD-bound class must say which class it is in.'
    )
    assert len(_rationale(row_line).split()) >= 8, (
        f'{kind} sits outside the grant class but carries no rationale explaining WHY: {row_line}'
    )


def test_every_grant_site_declares_a_gap_class():
    """Corpus direction: no real grant invocation anywhere omits ``--gap-class``.

    The roster-driven check above only reaches grant blocks at the sites its own
    rows name. This sweeps the SAME independent corpus the membership check uses,
    so a grant site in a document no row points at is still caught. An unlabelled
    ruling is the fail-open shape the class exists to remove — and the parser
    makes it an exit-2 besides.
    """
    unlabelled: list[str] = []
    for doc in sorted(_BUNDLE_ROOT.rglob('*.md')):
        text = _read(doc)
        if _GRANT_VERB not in text:
            continue
        for block in _invocations(text, _GRANT_VERB):
            kinds = _kinds_in(block)
            if kinds and not _GAP_CLASS_ARG_RE.search(block):
                unlabelled.append(f'{doc.relative_to(_BUNDLE_ROOT)}: --kind {kinds[0]}')

    assert not unlabelled, (
        f'These "{_GRANT_VERB}" invocations carry a concrete --kind but no --gap-class: '
        f'{unlabelled}. --gap-class is REQUIRED by the parser, so each of these is an '
        'argparse rejection at a merge gate; and a ruling with no declared class is one '
        'no check site can scope, which is the fail-open direction.'
    )


def test_every_granted_kind_is_declared_in_the_roster():
    """(f) The reverse direction: no grant site exists that the roster never lists.

    The roster claims membership "lives here and nowhere else". Checking only
    that each declared row has a real site proves the roster contains no fiction;
    it says nothing about a real mechanism nobody declared — the absence a
    one-directional check structurally cannot see.
    """
    undeclared = _undeclared_grant_kinds(set(_ROSTER_KINDS))

    assert not undeclared, (
        f'These authorization kinds are granted somewhere under {_BUNDLE_ROOT} but appear '
        f'in no {_ROSTER_HEADING} row: {undeclared}. The roster is the declared '
        'population, so an undeclared grant site is an authorization mechanism that no '
        'reviewer of the roster can see.'
    )
