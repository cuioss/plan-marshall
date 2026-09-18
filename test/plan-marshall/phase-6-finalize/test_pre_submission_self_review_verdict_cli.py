#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Doc-contract regression for the pre-submission-self-review non-finding verdicts.

``pre-submission-self-review.md`` used to report a single undifferentiated
clean verdict — ``"self-review clean: {N} candidates examined"`` — across
structurally different outcomes. The document now declares one labelled verdict
per no-finding outcome:

* **not-run.** No domain surfacer resolved in the executor (the zero-generator
  fallback in Step 1). Nothing ran: no file was searched, no candidate was
  constructed, no check executed. This verdict is a statement about the
  EXECUTOR and makes no claim about the diff.
* **nothing-to-check.** A surfacer RAN and produced no candidate, so no check
  had anything to run against. A statement about what the surfacer did; how
  strong a statement about the diff depends on the scope it echoes.
* **no-check-matched.** Candidates WERE surfaced, every check was applied to
  them, and none fired.
* **zero-observation.** A full-surface round returned no findings while its
  ``delta_coverage.files_with_candidates`` was 0 over a non-zero
  ``files_in_scope`` — it drew no observation of its own from the files it
  searched.

**These four are the NON-FINDING verdicts, not the clean ones.** Only three of
them are ``clean:`` verdicts. ``ext-point-self-review-surfacing.md`` owns that
boundary and states it outright — the fallback's outcome is ``done``; its
verdict is not "clean" — so a population that called all four "clean" would put
an un-run analysis inside the clean set, reintroducing at the level of the
VOCABULARY exactly the collapse the literal split exists to prevent. The
population below is therefore named for what it actually filters: every verdict
that is not the finding-bearing one.

Collapsing any two hides a review-coverage difference. The sharpest is the
first pair: an operator reading "clean" on the not-run path concludes the
change was reviewed and passed, when in fact NO ANALYSIS WAS PERFORMED. The
defect class this file guards is the same one the workflow's own check 14
exists to catch — a verdict that cannot distinguish two states is a guard that
can never observe a difference.

These tests pin the split:

(a) The ``display_detail`` shape section declares one distinct non-finding
    verdict per declared label, each carrying its labelled name. The expected
    cardinality is DERIVED from the label set rather than written as a
    literal, so adding a label without adding its verdict fails here.
(b) The non-finding verdicts partition: every declared label claims exactly one
    literal, and every literal is claimed by exactly one label.
(c) No non-finding verdict is a prefix of another, so a consumer matching a
    whole verdict string cannot mistake one for another.
(d) The zero-generator fallback path (Step 1) reports the not-run verdict by
    its own label, and reports NO other non-finding verdict.
(e) The old single undifferentiated form is no longer the SOLE non-finding
    verdict.
(f) The inline-vs-dispatch return-shape invariant names every non-finding
    verdict, so the two branches cannot drift into differing vocabularies.
(g) ``clean:`` is reserved for a verdict produced after a surfacer RAN — the
    not-run verdict carries no ``clean:`` prefix, and every other one does.

Every property assertion is paired with a mutation guard that runs the detector
against the known pre-fix prose; without them a regex typo would make the
corresponding assertion vacuously green.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines
from conftest import MARKETPLACE_ROOT

_WORKFLOW_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'pre-submission-self-review.md'
)

_OUTPUT_HEADING = '### Dispatched-envelope output (returned from Steps 2–3 to Step 4)'
_GATE_HEADING = '### Step 1b: Candidate-count gate (inline vs dispatch) — B5'
_SURFACE_HEADING = '### Step 1: Deterministic surface (inline)'

#: Sub-headings and horizontal rules that terminate a ``### `` section.
_STOP_PREFIXES = ('### ', '## ', '# ', '---')

#: A verdict literal is a backticked, double-quoted string starting with the
#: ``self-review`` token. Captures the string body without its quotes.
_VERDICT_LITERAL = re.compile(r'`"(self-review[^"]*)"`')

#: The labelled non-finding verdicts the doc must carry, mapped to the marker
#: phrase that identifies which literal belongs to which label.
#:
#: The name is load-bearing. These are the verdicts a round with an empty
#: ``findings`` list may report — NOT a set of "clean" ones. The not-run member
#: is explicitly not clean (see the module docstring and assertion (g)), so
#: calling the population clean would restate the un-run-versus-un-observed
#: collapse as a naming convention.
#:
#: This mapping is the POPULATION every cardinality below is derived from. A
#: bare ``len(...) == 2`` went stale the moment a third verdict was declared —
#: and it would have gone stale SILENTLY in the other direction too, passing
#: while a declared label had no literal at all. Deriving the expected count
#: from this dict is what keeps the assertion honest as the set grows: adding a
#: label here without adding its verdict to the document fails (a), and adding
#: a verdict to the document without a label here fails (b).
_NON_FINDING_VERDICT_MARKERS = {
    'not-run': 'not run',
    'nothing-to-check': 'zero candidates surfaced',
    'no-check-matched': '{N} candidates examined',
    'zero-observation': 'no observation',
}

#: The label whose verdict the zero-generator fallback path reports. Resolved
#: by LABEL rather than by a ``len(...) == 1`` filter over some incidental
#: property: three of the four non-finding verdicts carry no ``{N}``, so the old
#: "the one without a count" filter no longer identifies anything.
_ZERO_GENERATOR_LABEL = 'not-run'

#: The prefix that marks a verdict as CLEAN — reserved for a verdict produced
#: after a surfacer actually ran. The not-run verdict must not carry it.
_CLEAN_PREFIX = 'self-review clean:'

#: The pre-fix, undifferentiated clean verdict, as a normalised shape. The
#: ``{N}`` placeholder is literal in the doc.
_OLD_CLEAN_FORM = 'self-review clean: {N} candidates examined'

#: The finding-bearing verdict's marker, excluded from the non-finding set.
_FINDINGS_VERDICT_MARKER = 'found'

#: display_detail budget, per the agent-return-shape contract.
_DISPLAY_DETAIL_MAX = 80

#: Every count placeholder that may appear inside a verdict literal, widened to
#: its plausible maximum before the budget is measured.
#:
#: This list is load-bearing rather than incidental: the budget assertion
#: measures ``len(rendered)``, so a placeholder MISSING from it is measured at
#: its template width (``{C}`` is 3 characters) instead of its rendered width
#: (``9999`` is 4). A verdict that only just fits would then pass here and
#: overflow in production — the assertion would be measuring the template, which
#: is the vacuity this module exists to prevent elsewhere. Any new placeholder
#: introduced into a verdict literal MUST be added here in the SAME change.
#:
#: ``{N}`` — surfaced candidate count (no-check-matched verdict).
#: ``{K}`` — finding count (findings verdict).
#: ``{C}`` — distinct defect_class count across those findings (findings verdict).
_COUNT_PLACEHOLDERS = ('{N}', '{K}', '{C}')


def _render(literal: str) -> str:
    """Substitute every count placeholder with its plausible maximum."""
    rendered = literal
    for placeholder in _COUNT_PLACEHOLDERS:
        rendered = rendered.replace(placeholder, '9999')
    return rendered


def _doc_text() -> str:
    text: str = _WORKFLOW_DOC.read_text(encoding='utf-8')
    return text


def _section(heading: str) -> str:
    return '\n'.join(section_lines(_doc_text(), heading, _STOP_PREFIXES))


def _verdict_literals(text: str) -> list[str]:
    """Return the distinct ``self-review`` verdict literals in ``text``, in order."""
    seen: list[str] = []
    for match in _VERDICT_LITERAL.finditer(text):
        literal = match.group(1)
        if literal not in seen:
            seen.append(literal)
    return seen


def _non_finding_verdicts(text: str) -> list[str]:
    """Return the verdict literals that report NO finding.

    This is the complement of the finding-bearing verdict, not a "clean" set:
    the not-run member reports that no analysis ran at all, which is a
    non-finding outcome without being a clean one.
    """
    return [literal for literal in _verdict_literals(text) if _FINDINGS_VERDICT_MARKER not in literal]


def _partition_non_finding_verdicts(non_finding: list[str]) -> dict[str, list[str]]:
    """Map each declared label to the non-finding literals carrying its marker.

    A well-formed document yields exactly one literal per label and leaves no
    literal unclaimed — that is the partition assertion (b) checks, and it is
    what replaced the pre-split ``len(...) == 2`` count.
    """
    return {
        label: [literal for literal in non_finding if marker in literal]
        for label, marker in _NON_FINDING_VERDICT_MARKERS.items()
    }


def _unclaimed_non_finding_verdicts(non_finding: list[str]) -> list[str]:
    """Return non-finding literals no declared label's marker matches."""
    return [
        literal
        for literal in non_finding
        if not any(marker in literal for marker in _NON_FINDING_VERDICT_MARKERS.values())
    ]


def _prefix_collisions(literals: list[str]) -> list[tuple[str, str]]:
    """Return every ordered pair where one literal is a prefix of another."""
    collisions: list[tuple[str, str]] = []
    for outer in literals:
        for inner in literals:
            if outer is inner:
                continue
            if inner.startswith(outer):
                collisions.append((outer, inner))
    return collisions


# ---------------------------------------------------------------------------
# Sanity: the sections the assertions read actually exist and are non-empty
# ---------------------------------------------------------------------------


_SURFACER_SKILL_DOC = (
    MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'ext-self-review-plan-marshall' / 'SKILL.md'
)

_INDEPENDENCE_HEADING = '## Author and verifier are different parties'

_VERIFIER_STEP_HEADING = '### Step 3b: Independent verification (dispatch)'

_BRANCH_A_SECTION_HEADING = '### Step 4: Mark Step Complete (inline)'

_AUTHOR_ROLE = 'author'

_VERIFIER_ROLE = 'verifier'

_ROLE_TABLE_HEADER = 'role'

_SAME_PARTY_MARKER = 'author and verifier are the same party'

_TASK_SPAWN = re.compile(r'^\s*Task:\s+plan-marshall:', re.MULTILINE)

_ACCEPTANCE_TOKEN = 'acceptance: accepted'


def _optional_section(text: str, heading: str) -> str:
    """Return a heading-bounded section, or the empty string when absent.

    ``section_lines`` raises on a missing heading, which is correct for a section
    the document MUST carry. Both arrangement branches below are optional by
    construction — exactly one is expected to be present — so a raise would make
    the disjunction unaskable.
    """
    if not any(line.strip() == heading for line in text.splitlines()):
        return ''
    return '\n'.join(section_lines(text, heading, _STOP_PREFIXES))


def _table_rows(text: str, header_literal: str) -> list[list[str]]:
    """Return the body rows of the table whose first header cell is ``header_literal``.

    Matched on the first header cell, emphasis-stripped and lowercased — the same
    discriminator the prompt-body-field guard uses, and for the same reason: a
    document carries several tables and "the one with these columns" would fold
    an unrelated one in.
    """
    lines = text.splitlines()
    rows: list[list[str]] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip().startswith('|') or index + 1 >= len(lines):
            index += 1
            continue
        header = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
        delimiter = [cell.strip() for cell in lines[index + 1].strip().strip('|').split('|')]
        if len(delimiter) != len(header) or not all(re.fullmatch(r':?-{2,}:?', cell) for cell in delimiter):
            index += 1
            continue
        row_index = index + 2
        if header[0].strip('*_ ').lower() == header_literal:
            while row_index < len(lines) and lines[row_index].strip().startswith('|'):
                rows.append([cell.strip() for cell in lines[row_index].strip().strip('|').split('|')])
                row_index += 1
        else:
            while row_index < len(lines) and lines[row_index].strip().startswith('|'):
                row_index += 1
        index = row_index
    return rows


def _declared_roles(section: str) -> dict[str, str]:
    """Map each declared role name to the context its row says it runs in.

    The role NAME is the first cell (emphasis and backticks stripped, lowercased);
    the context is the LAST cell. Reading the last cell rather than a fixed index
    keeps the parse correct if the table gains a column between them.
    """
    roles: dict[str, str] = {}
    for row in _table_rows(section, _ROLE_TABLE_HEADER):
        if len(row) < 2:
            continue
        name = row[0].strip('*_` ').lower()
        roles[name] = row[-1]
    return roles


def _independence_is_implemented(doc: str) -> bool:
    """Whether the workflow doc implements the role-separated arrangement."""
    declares_roles = bool(_optional_section(doc, _INDEPENDENCE_HEADING))
    dispatches_verifier = bool(_optional_section(doc, _VERIFIER_STEP_HEADING))
    return declares_roles and dispatches_verifier


def _limitation_is_recorded(doc: str, surfacer_doc: str) -> bool:
    """Whether the honest-alternative arrangement is recorded in BOTH docs.

    Both, because the deliverable's alternative branch names both surfaces: a
    limitation recorded in one document and not the other is half-recorded, and
    the half that omits it reads as though no limitation exists.
    """
    return _SAME_PARTY_MARKER in doc.lower() and _SAME_PARTY_MARKER in surfacer_doc.lower()


_STOP_ANSWER_YES = 'may_close: yes'

_AUTHOR_PREDICATE = 'findings list is empty'

_BRANCH_LABEL = re.compile(r'^\*\*Branch ([A-Z]) — (.+?)\*\*', re.MULTILINE)

_RECORDED_OUTCOME = re.compile(r'--outcome\s+([a-z_]+)')

_CARVE_OUT_MARKER = 'zero-generator fallback'


def _slice_branches(section: str) -> dict[str, str]:
    """Map each branch letter to the text between its label and the next label.

    Pure over ``section`` so the real document and the mutation guard's synthetic
    prose go through ONE slicing rather than two that can drift. The final branch
    runs to the end of the section — a walk that stopped at the last label would
    silently drop it, which is the branch most likely to be added later.
    """
    matches = list(_BRANCH_LABEL.finditer(section))
    bodies: dict[str, str] = {}
    for position, match in enumerate(matches):
        end = matches[position + 1].start() if position + 1 < len(matches) else len(section)
        bodies[match.group(1)] = section[match.start() : end]
    return bodies


def _branch_label(body: str) -> str:
    """The label line of a branch body — the line its selector is written on."""
    return body.split('\n', 1)[0]


_BRANCH_PRECONDITION = re.compile(r'^\*\*Precondition.*$', re.MULTILINE)


def _branch_precondition(body: str) -> str:
    """The branch's own Precondition paragraph(s), joined.

    A branch with none returns the empty string — callers combine this with
    the label rather than assuming every branch carries a Precondition line.
    """
    return '\n'.join(_BRANCH_PRECONDITION.findall(body))


def _branch_selector(body: str) -> str:
    """The text a branch's routing decision is actually keyed on.

    The label plus any Precondition paragraph(s) — never the whole body, whose
    unrelated prose could accidentally mention a token this file checks for and
    let a branch pass on the strength of a sentence that decides nothing.
    """
    return _branch_label(body) + '\n' + _branch_precondition(body)


def _branch_bodies() -> dict[str, str]:
    """The Step 4 branch bodies of the real workflow document."""
    return _slice_branches(_optional_section(_doc_text(), _BRANCH_A_SECTION_HEADING))


def _branches_recording(bodies: dict[str, str], outcome: str) -> dict[str, str]:
    """The branches whose own text records ``--outcome {outcome}``."""
    return {letter: body for letter, body in bodies.items() if outcome in _RECORDED_OUTCOME.findall(body)}


def _branches_recording_done() -> dict[str, str]:
    """The Step 4 branches whose own text records `--outcome done`."""
    return _branches_recording(_branch_bodies(), 'done')


def test_one_distinct_non_finding_verdict_per_declared_label():
    non_finding = _non_finding_verdicts(_section(_OUTPUT_HEADING))
    expected = len(_NON_FINDING_VERDICT_MARKERS)

    # The cardinality is DERIVED from the declared label population, never
    # written as a literal — a hard-coded count is what went stale when the
    # un-run/un-observed split turned two verdicts into four.
    assert len(non_finding) == expected, (
        f'The display_detail shape must declare exactly one distinct '
        f'non-finding verdict per declared label '
        f'({sorted(_NON_FINDING_VERDICT_MARKERS)}) — {expected} in total. '
        f'Found {len(non_finding)}: {non_finding}'
    )


def test_no_check_matched_verdict_carries_the_candidate_count():
    """The no-check-matched verdict is the one that reports how many it examined.

    Resolved through the label partition rather than by scanning every verdict
    for ``{N}``. The marker for this label IS the count-bearing literal, so a
    scan and the partition select the same string today — but the partition says
    WHICH verdict is meant, and fails loudly when the label claims zero or more
    than one, where a bare ``{N}`` scan silently re-targets the moment another
    verdict gains a count.

    Deliberately no ``'{N}' in claimed[0]`` assertion: the marker table keys this
    label on ``'{N} candidates examined'``, so ``claimed[0]`` contains ``{N}`` by
    construction and such an assert could not fail. That tautology shipped here
    once already and was caught by this step's own round-5 review.
    """
    section = _section(_OUTPUT_HEADING)
    non_finding = _non_finding_verdicts(section)
    assert non_finding, 'No non-finding verdicts parsed — assertion would be vacuous'

    claimed = _partition_non_finding_verdicts(non_finding)['no-check-matched']

    assert len(claimed) == 1, f'The no-check-matched label must claim exactly one verdict literal. Got: {claimed}'


def test_non_finding_verdicts_are_not_prefix_collisions():
    non_finding = _non_finding_verdicts(_section(_OUTPUT_HEADING))
    assert non_finding, 'No non-finding verdicts parsed — assertion would be vacuous'

    collisions = _prefix_collisions(non_finding)

    assert not collisions, (
        f'One non-finding verdict is a prefix of another, so a consumer '
        f'matching a whole verdict string can mistake one for the other: '
        f'{collisions}'
    )


def test_zero_generator_fallback_reports_no_other_non_finding_verdict():
    """The fallback must not borrow a verdict that claims something ran.

    Every other non-finding verdict is a statement about a round in which a
    surfacer actually ran. The fallback ran none, so reporting any of them
    there would restate an un-run analysis as an observation — including the
    nothing-to-check verdict, which is the near-miss this guards.
    """
    surface = _section(_SURFACE_HEADING)
    partition = _partition_non_finding_verdicts(_non_finding_verdicts(_section(_OUTPUT_HEADING)))

    others = {label: hits[0] for label, hits in partition.items() if label != _ZERO_GENERATOR_LABEL and len(hits) == 1}
    assert others, 'No sibling non-finding verdicts resolvable — assertion vacuous'

    leaked = {label: literal for label, literal in others.items() if literal in surface}

    assert not leaked, (
        f'The zero-generator fallback path performed no analysis, so it must '
        f'report no verdict that claims a surfacer ran. It reported: {leaked}'
    )


def test_old_undifferentiated_form_does_not_survive_verbatim_as_a_verdict():
    # A verdict literal EQUAL to the old form would re-collapse the split even
    # while a second verdict exists elsewhere.
    non_finding = _non_finding_verdicts(_doc_text())

    assert _OLD_CLEAN_FORM not in non_finding, (
        f'The pre-fix verdict {_OLD_CLEAN_FORM!r} is still declared verbatim as '
        f'a verdict literal — the two states can still be reported identically'
    )


def test_exactly_one_author_verifier_arrangement_is_documented():
    """The one state that is never acceptable is the unrecorded collapse.

    This is the assertion the deliverable's criterion names: it fails when author
    and verifier are the same party and nothing says so. It is written as a
    disjunction over the two admissible arrangements rather than as a pin on the
    one that was implemented, so the suite states the property instead of the
    outcome — and so re-deciding the architecture later changes which branch is
    taken, not whether the property is asserted.
    """
    doc = _doc_text()
    surfacer_doc = _SURFACER_SKILL_DOC.read_text(encoding='utf-8')

    independent = _independence_is_implemented(doc)
    recorded = _limitation_is_recorded(doc, surfacer_doc)

    assert independent or recorded, (
        'The self-review documents neither arrangement: no role-separated '
        f'verifier ({_INDEPENDENCE_HEADING!r} + {_VERIFIER_STEP_HEADING!r} are '
        f'not both present) and no recorded limitation (neither doc states '
        f'{_SAME_PARTY_MARKER!r}). Author and verifier are then the same party '
        'with nothing saying so, which is the exact state this deliverable '
        'exists to make impossible — a reader of the step record cannot tell '
        'that the verdict was accepted by its own author.'
    )
    assert not (independent and recorded), (
        'The self-review documents BOTH arrangements at once — it declares a '
        'separately-dispatched verifier AND states that author and verifier are '
        'the same party. A reader has no way to know which is true of the '
        'shipped step.'
    )


def test_the_closing_branch_requires_the_verifiers_acceptance():
    """The round closes on an acceptance the author could not grant itself.

    Without this, the verifier is a dispatch whose answer nothing consumes — a
    producer with no consumer, which is a defect class this very step checks for.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    closing = _optional_section(doc, _BRANCH_A_SECTION_HEADING)
    assert closing.strip(), (
        f'{_BRANCH_A_SECTION_HEADING!r} parsed empty, so the acceptance assertion below would be vacuous'
    )

    assert _ACCEPTANCE_TOKEN in closing, (
        f'The closing branch does not require {_ACCEPTANCE_TOKEN!r}, so the round '
        f'still closes on the reading its own author produced, and the verifier '
        f'answer is consumed by nothing.'
    )


def test_the_closing_branch_is_selected_by_the_stop_answer_not_by_the_author():
    """Branch A's SELECTOR is the verifier's answer, not the findings list.

    The label is the selector: a branch labelled *findings list is empty* is
    selected by the author's own reading of its own output, however much prose
    elsewhere describes a verifier. Reading the label is what keeps this an
    assertion about the decision rather than about the documentation around it.
    """
    closing = _branches_recording_done()
    assert closing, f'No branch records done; derived branches: {sorted(_branch_bodies())}'

    author_selected = [letter for letter, body in closing.items() if _AUTHOR_PREDICATE in _branch_label(body)]

    assert not author_selected, (
        f'Branch(es) {author_selected} record `done` and are labelled by the bare '
        f'{_AUTHOR_PREDICATE!r} predicate — the author reading the list it just '
        f'produced. The stop question exists so that decision belongs to the party '
        f'that did not write the verdict.'
    )


def test_the_two_verifier_questions_are_not_collapsed_into_one():
    """`acceptance` and `may_close` answer different questions and both are read.

    Collapsing them is the near-miss: a verdict can be accurately worded about a
    round that should still be followed by another, so reading question (1)'s
    answer as question (2)'s closes a review the verifier did not close. Both
    tokens must appear in the verifier section AND in the closing branch.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    verifier_section = _optional_section(doc, _VERIFIER_STEP_HEADING)
    closing = _optional_section(doc, _BRANCH_A_SECTION_HEADING)

    for token in (_ACCEPTANCE_TOKEN, _STOP_ANSWER_YES):
        assert token in verifier_section, (
            f'{_VERIFIER_STEP_HEADING!r} does not declare {token!r}, so the verifier '
            f'is not asked for it and the closing branch has nothing to read.'
        )
        assert token in closing, (
            f'{_BRANCH_A_SECTION_HEADING!r} does not require {token!r}. Both answers '
            f'gate the close: one judges the verdict wording, the other judges '
            f'whether another round is owed, and neither substitutes for the other.'
        )


def test_role_parser_fires_on_a_same_context_table_and_ignores_a_foreign_table():
    """The role comparison must catch two roles sharing one context.

    And it must not read an unrelated table: a doc carries several, so a parser
    keyed on "has these columns" rather than on the first header cell would fold
    a foreign one in and compare cells that are not roles at all.
    """
    collapsed = (
        f'{_INDEPENDENCE_HEADING}\n\n'
        '| Role | What it does | Where it runs |\n'
        '|------|--------------|---------------|\n'
        '| **Author** | writes the verdict | the inline dispatcher context |\n'
        '| **Verifier** | accepts it | the inline dispatcher context |\n'
    )
    roles = _declared_roles(_optional_section(collapsed, _INDEPENDENCE_HEADING))

    assert roles[_AUTHOR_ROLE] == roles[_VERIFIER_ROLE], (
        'The role parser did not read two roles sharing one context as equal, so '
        'the separation assertion could never fail on the collapse it targets.'
    )

    foreign = (
        f'{_INDEPENDENCE_HEADING}\n\n'
        '| Prompt-body field | Required | Description |\n'
        '|---|---|---|\n'
        '| `candidates` | Yes | the surfaced candidates |\n'
    )
    assert _declared_roles(_optional_section(foreign, _INDEPENDENCE_HEADING)) == {}, (
        'The role parser folded a foreign table in. Selection is keyed on the '
        'first header cell, or every table in the document becomes a role table.'
    )


def test_partition_detector_fires_on_an_unclaimed_and_on_a_doubly_claimed_literal():
    """Both halves of the partition assertion must be able to fail.

    Without this, a marker typo would leave every label matching nothing while
    ``ambiguous`` reported the failure only if some label matched twice — and a
    marker broad enough to match every literal would leave ``unclaimed`` empty
    forever. Each half is fired here against a synthetic set built to trip it.
    """
    # Half 1 — a literal no declared marker claims.
    unclaimed_set = ['self-review clean: a shape no marker names']
    assert _unclaimed_non_finding_verdicts(unclaimed_set) == unclaimed_set, (
        'The unclaimed-literal detector did not fire on a literal carrying no '
        'declared marker — the coverage half of the partition would be vacuous'
    )

    # Half 2 — one label claiming two literals, which is the collapse the
    # partition exists to reject.
    doubled = [
        'self-review clean: {N} candidates examined, no check matched',
        'self-review clean: {N} candidates examined, nothing fired',
    ]
    partition = _partition_non_finding_verdicts(doubled)
    assert len(partition['no-check-matched']) == 2, (
        'The label-claim detector did not fire on one label claiming two '
        'literals — the uniqueness half of the partition would be vacuous'
    )

    # Positive control: the well-formed shape trips neither half.
    well_formed = [
        'self-review not run: no surfacer implementor resolved',
        'self-review clean: surfacer ran, zero candidates surfaced',
        'self-review clean: {N} candidates examined, no check matched',
        'self-review clean: no observation drawn from the files searched',
    ]
    assert not _unclaimed_non_finding_verdicts(well_formed)
    assert all(len(hits) == 1 for hits in _partition_non_finding_verdicts(well_formed).values())


def test_budget_detector_fires_on_an_over_long_verdict():
    over_long = '`"self-review clean: {N} ' + ('x' * _DISPLAY_DETAIL_MAX) + '"`'

    literals = _verdict_literals(over_long)

    assert len(literals) == 1, 'Verdict parser failed on the synthetic over-long form'
    rendered = _render(literals[0])
    assert len(rendered) > _DISPLAY_DETAIL_MAX, (
        'Budget detector would not fire on an over-long verdict — the budget assertion would be vacuous'
    )
