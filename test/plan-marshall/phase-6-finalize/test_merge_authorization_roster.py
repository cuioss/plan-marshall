#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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

#: The ``--kind`` value of one grant invocation.
_KIND_ARG_RE = re.compile(r'--kind\s+([^\s\\]+)')

#: The ``--gap-class`` value of one grant or check invocation.
_GAP_CLASS_ARG_RE = re.compile(r'--gap-class\s+([^\s\\]+)')

#: The normative rule the barrier must state in as many words.
_INADMISSIBLE_EVIDENCE_MARKERS = ('decision', 'NEVER admissible')


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


#: Module-level derivation so the per-row tests can parametrize over it. Parsed
#: once at collection time from the authoritative document — no literal list.
_ROWS: list[tuple[str, str]] = parse_roster_rows(_read(_BRANCH_CLEANUP), _ROSTER_HEADING)
_ROSTER_KINDS: list[str] = [kind for kind, _ in _ROWS]
_ROW_IDS: list[str] = list(_ROSTER_KINDS)


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
            for token in _KIND_ARG_RE.findall(block):
                if not _is_form_placeholder(token):
                    kinds.add(token)
    return tuple(sorted(kinds))


def _undeclared_grant_kinds(declared: set[str]) -> list[str]:
    """The membership predicate: granted kinds absent from ``declared``.

    Factored out so the mutation guard drives the SAME predicate the closure
    assertion uses — a guard that re-implemented the check would prove nothing
    about the check that actually runs. Both sides are independent: the left is
    swept out of the documents, the right is parsed out of the roster.
    """
    return [kind for kind in _corpus_grant_kinds() if kind not in declared]


def test_roster_is_non_empty():
    """(a) The derivation resolves something — every later assertion depends on it.

    Asserted first and alone. ``ROSTER_ROW`` parses Markdown list items only, so
    a roster re-rendered as a table parses to zero rows and every parametrized
    test below would silently collect nothing.
    """
    assert _ROWS, (
        f'Parsing {_ROSTER_HEADING!r} in {_BRANCH_CLEANUP} yielded ZERO rows. Every '
        'assertion in this module would pass vacuously against an empty parse. The '
        'roster MUST be rendered as Markdown list rows (each leading with a '
        'backticked kind token) — a pipe-delimited table matches no row.'
    )


@pytest.mark.parametrize('kind,row_line', _ROWS, ids=_ROW_IDS)
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


@pytest.mark.parametrize('kind,row_line', _ROWS, ids=_ROW_IDS)
def test_every_head_bound_row_has_a_grant_site(kind, row_line):
    """(c) Every row's binding claim is cross-checked against real document content.

    No row escapes assertion by virtue of its binding mechanism:

    - ``bound_via: grant`` — the kind must appear in a real
      ``merge-authorization grant`` invocation **in the document the row's own
      ``site:`` names**, and that invocation must carry ``--kind {kind}``,
      ``--plan-id``, and a ``--gap-class`` equal to the row's own ``authorizes:``
      claim. ``add_plan_id_arg`` makes ``--plan-id`` required and
      ``manage-status`` is auto-routed, so a grant site missing it is
      simultaneously a worktree-isolation break and an argparse rejection. The
      ``--gap-class`` equality is what makes ``authorizes:`` falsifiable rather
      than decorative: it is the token routing actually compares, so a row whose
      claim disagrees with its site's real argument mis-predicts the reach of
      every ruling that site grants.
    - ``bound_via: head_dependent`` — asserted against its own declaration site
      instead: the step doc must declare ``head_dependent: true``.
    - ``bound_via: out_of_class`` — carries no HEAD binding by construction and
      is asserted by ``test_out_of_class_rows_are_annotated_rather_than_silently_absent``
      instead. The branch is explicit rather than a silent fall-through, so a
      row cannot dodge assertion by claiming an unrecognized mechanism.

    Checking against the row's OWN claimed site is what makes ``site:``
    falsifiable: a row that points at the wrong document fails here rather than
    passing because some other document happens to carry the invocation.
    """
    bound_via = _claim(row_line, 'bound_via')
    head_bound = _claim(row_line, 'head_bound')

    if bound_via == 'out_of_class':
        assert head_bound != 'yes', (
            f'{kind} is declared out_of_class but claims head_bound: yes — the two '
            'claims contradict each other.'
        )
        return

    assert head_bound == 'yes', (
        f'{kind} claims bound_via: {bound_via} but head_bound: {head_bound}. A row bound '
        'by a real mechanism must claim head_bound: yes.'
    )

    site = _site_doc_for(row_line)
    assert site.is_file(), f'{kind} names a site: document that does not exist: {site}'

    if bound_via == 'grant':
        matching = [block for block in _invocations(_read(site), _GRANT_VERB) if f'--kind {kind}' in block]
        assert matching, (
            f'{kind} claims bound_via: grant but no "{_GRANT_VERB}" invocation carrying '
            f'--kind {kind} exists in the document its site: claim names ({site.name}). '
            'Either the grant site is missing or the roster row points at the wrong '
            'document.'
        )
        without_plan_id = [block for block in matching if '--plan-id' not in block]
        assert not without_plan_id, (
            f'{kind} has a "{_GRANT_VERB}" invocation that omits --plan-id. '
            'add_plan_id_arg makes it REQUIRED, and manage-status is on the worktree '
            'auto-routing whitelist — so omitting it is both an argparse rejection '
            '(exit 2) and a silent write against the main checkout instead of the '
            'plan worktree.'
        )
        declared_class = _claim(row_line, 'authorizes')
        for block in matching:
            granted_classes = _GAP_CLASS_ARG_RE.findall(block)
            assert granted_classes == [declared_class], (
                f'{kind} declares authorizes: {declared_class} but its "{_GRANT_VERB}" '
                f'invocation in {site.name} passes --gap-class {granted_classes}. The '
                'roster claim and the real argument MUST agree: routing compares the '
                'persisted class against the class the check site reports, so a site '
                'passing a class the roster never declared is a ruling no reader of '
                'the roster can predict the reach of — and one omitting it entirely '
                'is an argparse rejection (--gap-class is required).'
            )
        return

    if bound_via == 'head_dependent':
        assert 'head_dependent: true' in _read(site), (
            f'{kind} claims bound_via: head_dependent, but the document its site: claim '
            f'names ({site.name}) does not declare "head_dependent: true". The '
            'declaration IS the binding for this row — without it the row asserts a '
            'binding that does not exist.'
        )
        return

    pytest.fail(
        f'{kind} declares an unrecognized bound_via: {bound_via!r}. Every row must be '
        'backed by grant, head_dependent, or out_of_class so no member escapes '
        'assertion by inventing a fourth mechanism.'
    )


@pytest.mark.parametrize('kind,row_line', _ROWS, ids=_ROW_IDS)
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
            f'{kind} binds via grant, so it belongs to the HEAD-bound class and must '
            'claim head_bound: yes.'
        )
        return

    assert _claim(row_line, 'head_bound') != 'n/a' or _claim(row_line, 'bound_via') == 'out_of_class', (
        f'{kind} claims head_bound: n/a without declaring bound_via: out_of_class — a '
        'member outside the HEAD-bound class must say which class it is in.'
    )
    assert len(_rationale(row_line).split()) >= 8, (
        f'{kind} sits outside the grant class but carries no rationale explaining WHY: '
        f'{row_line}'
    )


def test_barrier_checks_the_authorization_verb():
    """(e) The barrier consults the verb the roster claims, and states the D4 rule.

    Cross-checks the roster's central claim — that ``manage-status
    merge-authorization`` backs every ``bound_via: grant`` row and that the
    barrier is the single site at which those grants are checked — against the
    ACTUAL content of the barrier subsection and of the grant sites, rather than
    merely opening the documents. The roster cannot go green while the check site
    is absent, nor while its claimed verb disagrees with the verb the grant sites
    really call.
    """
    text = _read(_BRANCH_CLEANUP)
    roster = '\n'.join(section_lines(text, _ROSTER_HEADING))

    claimed = _VERB_CLAIM_RE.search(roster)
    assert claimed, (
        'The roster does not state which verb backs its bound_via: grant rows. That '
        'sentence is what ties the declared population to a checkable call site.'
    )
    assert claimed.group(1).endswith(_VERB), (
        f'The roster claims its grant rows are backed by {claimed.group(1)!r}, but the '
        f'grant and check sites call {_VERB!r}.'
    )

    granted_kinds = _corpus_grant_kinds()
    assert granted_kinds, (
        f'No "{_GRANT_VERB}" invocation with a concrete --kind was found anywhere under '
        f'{_BUNDLE_ROOT}. The roster claims the verb backs its grant rows; with no real '
        'invocation that claim is prose and the closure check below is vacuous.'
    )

    section = '\n'.join(section_lines(text, _CHECK_HEADING, stop_prefixes=_SUBSECTION_STOPS))
    checks = [block for block in _invocations(section, _CHECK_VERB) if '--head' in block]
    assert checks, (
        f'The barrier subsection {_CHECK_HEADING!r} carries no "{_CHECK_VERB}" invocation '
        'passing --head. The roster claims the barrier is the single check site for every '
        'granted authorization; without the invocation that claim is prose.'
    )
    assert all('--plan-id' in block for block in checks), (
        f'A "{_CHECK_VERB}" invocation in the barrier omits --plan-id — an argparse '
        'rejection at the exact gate this mechanism hardens.'
    )
    assert not any('--kind' in block for block in checks), (
        f'A "{_CHECK_VERB}" invocation in the barrier passes --kind. The check is '
        'deliberately kind-agnostic so one valid authorization can never mask a lapsed '
        'sibling — which is also what makes it cover every kind the grant sites emit '
        f'({list(granted_kinds)}) without enumerating them.'
    )

    for marker in _INADMISSIBLE_EVIDENCE_MARKERS:
        assert marker in section, (
            f'The barrier subsection does not state the D4 rule containing {marker!r}: '
            'the ONLY admissible evidence is a check verdict at the CURRENT HEAD, and a '
            'decision-log entry is NEVER admissible authorization evidence. Without the '
            'rule stated, a later reader can reintroduce log-recall as evidence — which '
            'is how plan-marshall#1067 merged five unreviewed commits.'
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
            kinds = [k for k in _KIND_ARG_RE.findall(block) if not _is_form_placeholder(k)]
            if kinds and not _GAP_CLASS_ARG_RE.search(block):
                unlabelled.append(f'{doc.relative_to(_BUNDLE_ROOT)}: --kind {kinds[0]}')

    assert not unlabelled, (
        f'These "{_GRANT_VERB}" invocations carry a concrete --kind but no --gap-class: '
        f'{unlabelled}. --gap-class is REQUIRED by the parser, so each of these is an '
        'argparse rejection at a merge gate; and a ruling with no declared class is one '
        'no check site can scope, which is the fail-open direction.'
    )


def test_barrier_routes_on_admissibility_not_on_head_validity():
    """(h) The barrier admits only rulings granted over ITS OWN gap.

    HEAD-binding alone is not sufficient, and the roster itself proves it: read
    the rows in execution order and three of the four grant kinds are granted at
    sites that run BEFORE this barrier, at the SAME HEAD, over a DIFFERENT gap.
    ``pre-merge-consent`` is granted on every interactive "Yes, merge" immediately
    above the barrier with no rebase in between, so a barrier routing on
    ``any_authorized`` would find a valid record on essentially every merge and
    skip its own disposition universally — a routine merge confirmation
    authorizing past a participation gap the operator was never shown.

    The inadmissible set is asserted NON-EMPTY first. Without that precondition
    the whole test would pass vacuously on a roster where every row happened to
    declare the barrier's own class, which is exactly the state that makes the
    distinction unnecessary — and the state a careless roster edit could produce.
    """
    text = _read(_BRANCH_CLEANUP)
    section = '\n'.join(section_lines(text, _CHECK_HEADING, stop_prefixes=_SUBSECTION_STOPS))

    assert _BARRIER_ADMISSIBLE, (
        f'No roster row declares authorizes: {_BARRIER_GAP_CLASS}, so NOTHING could ever '
        'satisfy this barrier and the operator would be locked out rather than re-asked. '
        'The escape hatch must be BOUND, not removed.'
    )
    assert _BARRIER_INADMISSIBLE, (
        'Every grant row declares the barrier\'s own gap class, so this test cannot '
        'distinguish admissibility-routing from HEAD-only routing and would pass '
        'vacuously. The cross-kind hazard is real precisely because rows like '
        'pre-merge-consent authorize a DIFFERENT gap at the same HEAD.'
    )

    checks = _invocations(section, _CHECK_VERB)
    for block in checks:
        classes = _GAP_CLASS_ARG_RE.findall(block)
        assert classes == [_BARRIER_GAP_CLASS], (
            f'The barrier\'s "{_CHECK_VERB}" invocation passes --gap-class {classes}, not '
            f'[{_BARRIER_GAP_CLASS!r}]. --gap-class is what scopes the admissibility '
            'verdict to the gap THIS barrier reports; omitting it is an argparse '
            'rejection and passing another gate\'s class answers the wrong question.'
        )

    assert 'any_admissible' in section, (
        'The barrier subsection never mentions any_admissible. Routing on any_authorized '
        'alone is the cross-kind fail-open: it is true whenever ANY ruling is bound to '
        f'this tree, including the {_BARRIER_INADMISSIBLE} granted over other gaps at '
        'this very HEAD.'
    )
    for kind in _BARRIER_INADMISSIBLE:
        assert kind in section, (
            f'The barrier subsection does not name {kind} as a ruling that does NOT '
            'authorize past it. Naming the inadmissible siblings is what stops a later '
            'reader from re-deriving "a valid authorization exists, therefore proceed".'
        )

    for marker in ('**`any_admissible: true`**', '**`any_admissible: false`**'):
        assert marker in section, (
            f'The barrier subsection carries no {marker} routing branch. Both dispositions '
            'must be keyed to the admissibility verdict, not to HEAD-validity.'
        )
    for stale in ('- **`any_authorized: true`**', '- **`any_authorized: false`**'):
        assert stale not in section, (
            f'The barrier subsection still carries the {stale} routing branch. That is the '
            'HEAD-only route this test exists to forbid: it resolves true on every '
            f'interactive merge via {_BARRIER_INADMISSIBLE}.'
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


@pytest.mark.parametrize('omitted', sorted(_corpus_grant_kinds()))
def test_each_row_is_independently_load_bearing(omitted):
    """(g) Mutation guard: dropping any ONE row is detected on its own.

    Removing a single kind from the DECLARED population must make the membership
    predicate report exactly that kind — no more, no fewer. This proves the check
    is sensitive to each row independently, so a roster that silently lost one
    while satisfying the others could never read as green.

    The parametrization is driven by the corpus sweep, not by the roster's own
    key list, and the predicate compares the two independent populations. A guard
    whose expected value and actual value both derive from the roster would be
    pure set arithmetic — true by construction, and unable to fail even if the
    roster and the documents disagreed completely.
    """
    declared = set(_ROSTER_KINDS)
    assert omitted in declared, (
        f'Mutation guard precondition failed: {omitted} is granted in the documents but '
        'is not declared in the roster, so removing it proves nothing. Fix the roster '
        'first — test_every_granted_kind_is_declared_in_the_roster reports the same gap.'
    )

    reported = _undeclared_grant_kinds(declared - {omitted})

    assert reported == [omitted], (
        f'The membership predicate did not isolate {omitted} when it alone was removed '
        'from the declared population. A predicate that cannot detect each member '
        'independently can pass while silently missing one. '
        f'Reported undeclared: {reported}'
    )
