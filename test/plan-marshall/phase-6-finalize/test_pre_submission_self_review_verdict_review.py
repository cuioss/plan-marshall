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

def test_surface_section_is_present_and_non_empty():
    section = _section(_SURFACE_HEADING)

    assert section.strip(), (
        f'{_SURFACE_HEADING!r} section is empty — the zero-generator fallback assertion would be vacuous'
    )


def test_non_finding_verdicts_partition_over_the_declared_labels():
    """Every label claims exactly one literal; every literal exactly one label.

    This replaced a ``len(nothing) == 1`` filter that identified the
    candidate-count-free verdict by the ABSENCE of ``{N}``. Three of the four
    non-finding verdicts now carry no ``{N}``, so that filter identifies
    nothing — and, worse, would have kept passing had it happened to match one.
    A partition over labelled names states the property directly instead of
    inferring it from an incidental field.
    """
    non_finding = _non_finding_verdicts(_section(_OUTPUT_HEADING))
    assert non_finding, 'No non-finding verdicts parsed — assertion would be vacuous'

    partition = _partition_non_finding_verdicts(non_finding)

    ambiguous = {label: hits for label, hits in partition.items() if len(hits) != 1}
    assert not ambiguous, (
        f'Each declared label must claim exactly one non-finding verdict '
        f'literal. These claimed a different number: {ambiguous}'
    )

    unclaimed = _unclaimed_non_finding_verdicts(non_finding)
    assert not unclaimed, (
        f'These non-finding verdicts are claimed by no declared label, so the '
        f'partition does not cover the set the document actually declares: '
        f'{unclaimed}. Add each to _NON_FINDING_VERDICT_MARKERS in the same '
        f'change.'
    )


def test_every_verdict_placeholder_is_covered_by_the_widening_list():
    """No verdict placeholder escapes the budget test's substitution.

    This is what keeps the budget assertion above from going vacuous. A
    placeholder absent from ``_COUNT_PLACEHOLDERS`` is measured at its TEMPLATE
    width rather than its rendered width, so a verdict that only just fits would
    pass the budget check and still overflow in production. Deriving the
    offenders from the live verdict set — rather than trusting the list to have
    been maintained — is what makes the coverage claim checkable instead of
    assumed.
    """
    placeholder_re = re.compile(r'\{[A-Za-z_][A-Za-z0-9_]*\}')

    literals = _verdict_literals(_section(_OUTPUT_HEADING))
    assert literals, 'No verdicts parsed — the assertion would be vacuous'

    uncovered = sorted(
        {found for literal in literals for found in placeholder_re.findall(literal) if found not in _COUNT_PLACEHOLDERS}
    )

    assert not uncovered, (
        f'These verdict placeholders are not widened before the budget is '
        f'measured, so the budget assertion measures the template instead of '
        f'the rendered string: {uncovered}. Add each to _COUNT_PLACEHOLDERS.'
    )


def test_zero_generator_fallback_reports_the_not_run_verdict():
    surface = _section(_SURFACE_HEADING)
    partition = _partition_non_finding_verdicts(_non_finding_verdicts(_section(_OUTPUT_HEADING)))

    claimed = partition[_ZERO_GENERATOR_LABEL]
    assert len(claimed) == 1, (
        f'The {_ZERO_GENERATOR_LABEL!r} verdict is not resolvable by its label — '
        f'the assertion below would be vacuous. Got: {claimed}'
    )

    assert claimed[0] in surface, (
        f'The zero-generator fallback path must report the '
        f'{_ZERO_GENERATOR_LABEL!r} verdict {claimed[0]!r} — no surfacer ran, '
        f'so no analysis was performed at all'
    )


def test_old_undifferentiated_clean_form_is_not_the_sole_non_finding_verdict():
    non_finding = _non_finding_verdicts(_doc_text())

    assert non_finding != [_OLD_CLEAN_FORM], (
        f'The document still carries the pre-fix single undifferentiated clean '
        f'verdict {_OLD_CLEAN_FORM!r} as its only non-finding verdict'
    )
    # Derived from the declared label population, not a literal floor: every
    # labelled verdict is declared in the output section, so all of them must
    # survive a document-wide read too.
    expected = len(_NON_FINDING_VERDICT_MARKERS)
    assert len(non_finding) >= expected, (
        f'Fewer than {expected} distinct non-finding verdicts survive '
        f'document-wide (one per declared label '
        f'{sorted(_NON_FINDING_VERDICT_MARKERS)}): {non_finding}'
    )


def test_only_the_ran_verdicts_are_clean_and_the_not_run_one_is_not():
    """The not-run verdict is non-finding WITHOUT being clean.

    ``ext-point-self-review-surfacing.md`` is the authority and states the
    boundary outright: the fallback's outcome is ``done``; its verdict is not
    "clean". Calling all four members of the population "clean" would place an
    un-run analysis inside the clean set — the same un-run-versus-un-observed
    collapse the literal split exists to prevent, reintroduced one level up in
    the vocabulary. Both halves are asserted: the not-run literal must NOT
    carry the clean prefix, and every other one MUST, so the property cannot be
    satisfied by a document that dropped the prefix everywhere.
    """
    partition = _partition_non_finding_verdicts(_non_finding_verdicts(_section(_OUTPUT_HEADING)))

    not_run = partition[_ZERO_GENERATOR_LABEL]
    assert len(not_run) == 1, (
        f'The {_ZERO_GENERATOR_LABEL!r} verdict is not resolvable by its label, '
        f'so neither half below would be measuring it. Got: {not_run}'
    )
    assert not not_run[0].startswith(_CLEAN_PREFIX), (
        f'The not-run verdict {not_run[0]!r} carries the {_CLEAN_PREFIX!r} '
        f'prefix, so an un-run analysis reads as a clean review — which is what '
        f'ext-point-self-review-surfacing.md forbids outright'
    )

    ran = [literal for label, hits in partition.items() if label != _ZERO_GENERATOR_LABEL for literal in hits]
    assert len(ran) == len(_NON_FINDING_VERDICT_MARKERS) - 1, (
        f'The verdicts reported by a round that RAN are not all resolvable, so '
        f'the second half of this assertion would sweep a short set. Got: {ran}'
    )

    unmarked = [literal for literal in ran if not literal.startswith(_CLEAN_PREFIX)]
    assert not unmarked, (
        f'These verdicts are reported by a round in which a surfacer RAN, yet '
        f'do not carry the {_CLEAN_PREFIX!r} prefix, so the prefix no longer '
        f'discriminates a ran-and-clean verdict from the not-run one: {unmarked}'
    )


def test_the_verifier_is_a_second_dispatch_not_a_second_pass_in_the_author():
    """Independence rests on a SECOND dispatch, and the doc must carry one.

    A verifier described in prose but never spawned would be an arrangement the
    run cannot reach — the reachability question the settled harness evidence
    turns on. The count is derived from the document's own spawns rather than
    pinned: the author dispatch plus the verifier dispatch is two, and the
    assertion fails if the verifier section carries none of its own.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    verifier_section = _optional_section(doc, _VERIFIER_STEP_HEADING)

    assert _TASK_SPAWN.search(verifier_section), (
        f'{_VERIFIER_STEP_HEADING!r} describes a verifier but issues no '
        f'`Task: plan-marshall:` dispatch of its own, so the second party is '
        f'documented and unreachable.'
    )
    assert len(_TASK_SPAWN.findall(doc)) >= 2, (
        f'The document carries {len(_TASK_SPAWN.findall(doc))} dispatch(es). '
        f'Independence needs at least two — the author pass and the verifier — '
        f'because a leaf cannot spawn the second from inside the first.'
    )


def test_the_step_4_branch_set_is_derivable_and_non_trivial():
    """Vacuity guard for (i): the branch walk must find the real branches.

    Every assertion below quantifies over this derivation, so a parser that
    matched nothing would make each of them pass over an empty set — the exact
    shape that lets a contract guard certify nothing.
    """
    bodies = _branch_bodies()

    assert len(bodies) >= 2, (
        f'The Step 4 branch walk found {len(bodies)} branch(es) ({sorted(bodies)}). '
        f'The section declares several, so either the label shape changed or the '
        f'section resolved empty — and every (i) assertion would then sweep nothing.'
    )
    assert _branches_recording_done(), (
        f'No derived Step 4 branch records `--outcome done` ({sorted(bodies)}), so '
        f'the assertion that a closing branch requires a stop answer has no branch '
        f'to check.'
    )


def test_the_one_path_that_closes_without_a_stop_answer_is_named_where_it_closes():
    """The carve-out is stated in the branch that carries it, not left implicit.

    The zero-generator fallback reaches `done` having run no surfacer, so there is
    no round for a stop question to be about. That is a real exception, and the
    only honest form of it is one the closing branch NAMES — an unexplained
    silence is indistinguishable from a branch that simply forgot the gate.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    closing = _branches_recording_done()
    assert closing, 'No branch records done — the carve-out assertion would be vacuous'

    unnamed = [letter for letter, body in closing.items() if _CARVE_OUT_MARKER not in body.lower()]

    assert not unnamed, (
        f'Branch(es) {unnamed} record `done` but never name the '
        f'{_CARVE_OUT_MARKER!r} path, which reaches `done` without a stop answer. '
        f'A reader of the branch cannot then tell an intended exception from a '
        f'missing gate.'
    )


def test_arrangement_detectors_fire_on_the_pre_fix_and_alternative_shapes():
    """The disjunction must be able to fail, and each branch to be selected alone.

    Three synthetic documents, one per state. Without them a typo in either
    detector would make the disjunction unconditionally true — a guard that can
    never fail is exactly what let author-equals-verifier stand unremarked.
    """
    pre_fix = '## Execution\n\nStep 4 Branch A closes when the findings list is empty.\n'
    alternative = (
        '## Execution\n\nA limitation is recorded here: author and verifier are the same party in this harness.\n'
    )
    implemented = (
        f'{_INDEPENDENCE_HEADING}\n\n'
        '| Role | What it does | Where it runs |\n'
        '|------|--------------|---------------|\n'
        '| **Author** | writes the verdict | the dispatched envelope |\n'
        '| **Verifier** | accepts or refuses it | a separate dispatched envelope |\n'
        '\n'
        f'{_VERIFIER_STEP_HEADING}\n\n'
        '```text\n'
        'Task: plan-marshall:{target}\n'
        '```\n'
    )

    # Pre-fix: neither branch selected -> the disjunction FAILS.
    assert not _independence_is_implemented(pre_fix)
    assert not _limitation_is_recorded(pre_fix, pre_fix)

    # Honest alternative: the limitation branch alone.
    assert _limitation_is_recorded(alternative, alternative)
    assert not _independence_is_implemented(alternative)

    # Implemented: the independence branch alone, with both roles resolvable to
    # DIFFERENT contexts and a spawn inside the verifier section.
    assert _independence_is_implemented(implemented)
    assert not _limitation_is_recorded(implemented, implemented)
    roles = _declared_roles(_optional_section(implemented, _INDEPENDENCE_HEADING))
    assert set(roles) >= {_AUTHOR_ROLE, _VERIFIER_ROLE}, f'Role parser read {sorted(roles)}'
    assert roles[_AUTHOR_ROLE] != roles[_VERIFIER_ROLE]
    assert _TASK_SPAWN.search(_optional_section(implemented, _VERIFIER_STEP_HEADING))


def test_sole_non_finding_verdict_detector_rejects_the_pre_fix_shape():
    pre_fix = (
        '- Empty `findings` → `"self-review clean: {N} candidates examined"`.\n'
        '- Non-empty `findings` → `"self-review found {K} issues"`.\n'
    )

    non_finding = _non_finding_verdicts(pre_fix)

    # This is exactly the state
    # test_old_undifferentiated_clean_form_is_not_the_sole_non_finding_verdict
    # exists to fail on.
    assert non_finding == [_OLD_CLEAN_FORM]
    assert len(non_finding) < 2, (
        'The pre-fix shape must be detected as carrying fewer than two '
        'non-finding verdicts — otherwise '
        'test_old_undifferentiated_clean_form_is_not_the_sole_non_finding_verdict '
        'could never fail'
    )


def test_prefix_collision_detector_fires_on_a_colliding_pair():
    colliding = [
        'self-review clean',
        'self-review clean: {N} candidates examined',
    ]

    collisions = _prefix_collisions(colliding)

    assert collisions == [(colliding[0], colliding[1])], (
        f'Prefix-collision detector failed to fire on a known colliding pair — '
        f'assertion (c) would be vacuous. Got: {collisions}'
    )

    # Positive control: two verdicts that diverge before either ends collide not.
    disjoint = [
        'self-review: nothing to check - no candidates surfaced',
        'self-review clean: {N} candidates examined, no check matched',
    ]
    assert not _prefix_collisions(disjoint)
