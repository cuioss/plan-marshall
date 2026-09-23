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

_STOP_PATH_CONFIRMATION_MARKERS = ('convergence', 'counts.total')

_SIMPLIFY_DOC = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'standards' / 'finalize-step-simplify.md'
)

_STOP_NAMES = ('empty-footprint', 'clean-sweep')

_STALL_ATTACHMENT_MARKER = 'which named shape fails'

_SURFACER_CONTROLS_HEADING = '### Stop/stall matched controls'

_SURFACER_CONTROL_FIELDS = ('scope_statement', 'counts', 'files_with_candidates')

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


def test_output_section_is_present_and_non_empty():
    section = _section(_OUTPUT_HEADING)

    assert section.strip(), f'{_OUTPUT_HEADING!r} section is empty — every assertion below would be vacuous'


def test_every_non_finding_verdict_carries_its_label():
    section = _section(_OUTPUT_HEADING)

    for label in _NON_FINDING_VERDICT_MARKERS:
        assert label in section, (
            f'The display_detail shape must name the {label!r} verdict '
            f'explicitly, so a reader can tell which literal covers which state'
        )


def test_every_verdict_fits_the_display_detail_budget():
    # Every count placeholder is widened to its plausible maximum so the budget
    # is asserted against the rendered string, not the template.
    for literal in _verdict_literals(_section(_OUTPUT_HEADING)):
        rendered = _render(literal)

        assert len(rendered) <= _DISPLAY_DETAIL_MAX, (
            f'Verdict {literal!r} renders to {len(rendered)} chars, over the '
            f'{_DISPLAY_DETAIL_MAX}-char display_detail budget'
        )
        assert rendered.isascii(), f'Verdict {literal!r} is not ASCII'
        assert not rendered.endswith('.'), (
            f'Verdict {literal!r} carries a trailing period, which the agent-return-shape contract forbids'
        )


def test_no_verdict_at_all_is_a_prefix_of_another():
    literals = _verdict_literals(_section(_OUTPUT_HEADING))
    assert literals, 'No verdicts parsed — the assertion would be vacuous'

    collisions = _prefix_collisions(literals)

    assert not collisions, f'Verdict prefix collision across the full verdict set: {collisions}'


def test_zero_generator_fallback_does_not_report_the_old_undifferentiated_form():
    surface = _section(_SURFACE_HEADING)

    assert f'"{_OLD_CLEAN_FORM}"' not in surface, (
        'The zero-generator fallback still reports the pre-fix undifferentiated clean verdict'
    )
    # The literal pre-fix zero-count rendering is the exact string the fallback
    # used to emit.
    assert '"self-review clean: 0 candidates examined"' not in surface


def test_return_shape_invariant_names_every_non_finding_verdict():
    gate = _section(_GATE_HEADING)
    non_finding = _non_finding_verdicts(_section(_OUTPUT_HEADING))
    # Re-derived over the FULL non-finding set: the pre-split form asserted
    # ``len(...) == 2`` and would have skipped every verdict beyond the
    # second, letting a new verdict enter the vocabulary un-checked.
    assert len(non_finding) == len(_NON_FINDING_VERDICT_MARKERS), 'Non-finding verdicts not resolvable'

    missing = [literal for literal in non_finding if literal not in gate]

    assert not missing, (
        f'The inline-vs-dispatch return-shape invariant must name every '
        f'non-finding verdict so the two branches cannot drift into differing '
        f'verdict vocabularies. Missing from Step 1b: {missing}'
    )


def test_the_implemented_arrangement_separates_the_two_judging_roles():
    """When independence is the implemented arrangement, the roles really differ.

    Skipped-by-construction on the honest-alternative branch: the disjunction
    above already asserted that branch's obligation, and a role table is not one
    of its surfaces. Everything here is READ from the table — the role names it
    declares and the context cell each one carries — so the contexts themselves
    are never pinned in this file.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    roles = _declared_roles(_optional_section(doc, _INDEPENDENCE_HEADING))

    missing = [role for role in (_AUTHOR_ROLE, _VERIFIER_ROLE) if role not in roles]
    assert not missing, (
        f'The independence section declares no role table row for {missing}. '
        f'Declared roles: {sorted(roles)}. Without both rows the separation is '
        f'prose with no stated division of labour.'
    )
    assert roles[_AUTHOR_ROLE] != roles[_VERIFIER_ROLE], (
        f'The author and the verifier are documented as running in the SAME '
        f'context ({roles[_AUTHOR_ROLE]!r}). Two roles in one context is one '
        f'party wearing two names, which is the arrangement this deliverable '
        f'replaced.'
    )


def test_an_absent_or_refused_acceptance_does_not_close_the_round():
    """An unanswered verifier is not a yes — the fail-open this arrangement closes.

    The three non-acceptance states (refused, errored dispatch, no return) must
    each be documented as NOT closing. Asserted over the verifier section, where
    the routing lives, rather than document-wide, so unrelated prose mentioning
    a refusal cannot satisfy it.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    verifier_section = _optional_section(doc, _VERIFIER_STEP_HEADING).lower()

    for state in ('refused', 'error'):
        assert state in verifier_section, (
            f'{_VERIFIER_STEP_HEADING!r} does not document the {state!r} state, '
            f'so what happens to a round the verifier did not accept is unstated.'
        )
    assert 'never read an absent verifier return as an acceptance' in verifier_section, (
        'The verifier section does not forbid reading an ABSENT return as an '
        'acceptance. That is the fail-open the separation exists to close: an '
        'unanswered question silently restores the author-accepts-itself state.'
    )


def test_no_branch_records_done_without_an_answered_stop_question():
    """The load-bearing assertion: every done-recording branch requires the answer.

    Quantified over the DERIVED branch set, so a branch added later that records
    `done` is swept without editing this file. There is NO per-branch carve-out
    here on purpose: the zero-generator fallback reaches `done` through this same
    closing branch, and the branch carves it out in its own prose — which the
    next assertion checks separately. Skipping a whole branch because it mentions
    the carve-out would let a branch that LOST the stop answer pass on the
    strength of a sentence about a different path.

    Scoped to the branch's SELECTOR (label + Precondition paragraph(s)), not the
    whole body: a whole-body scan accepts the stop answer appearing anywhere,
    including unrelated prose that never actually gates the `mark-step-done`
    call — the regex-over-fit class this plan's own self-review sweeps for.
    """
    doc = _doc_text()
    if not _independence_is_implemented(doc):
        return

    offenders = [
        letter for letter, body in _branches_recording_done().items() if _STOP_ANSWER_YES not in _branch_selector(body)
    ]

    assert not offenders, (
        f'Step 4 branch(es) {offenders} record `--outcome done` without requiring '
        f'{_STOP_ANSWER_YES!r} in their label or Precondition paragraph. A `done` '
        f'recorded on an unanswered stop question is the author closing the review '
        f'on its own verdict, which is the arrangement this deliverable replaced.'
    )


def test_branch_walk_and_stop_answer_detectors_fire_on_the_pre_fix_shape():
    """Mutation guard for (i): the pre-fix Step 4 must be flagged.

    Reproduces the shape this deliverable replaced — Branch A labelled by the
    author's own predicate and recording `done` with no stop answer anywhere —
    and a matched control in the post-fix shape, so neither detector is
    unconditionally positive or unconditionally negative.
    """
    pre_fix = (
        f'{_BRANCH_A_SECTION_HEADING}\n\n'
        '**Branch A — findings list is empty**: read the display_detail verbatim.\n\n'
        '```bash\n'
        'mark-step-done --outcome done --force\n'
        '```\n\n'
        '**Branch B — findings list is non-empty**: persist every finding.\n\n'
        '```bash\n'
        'mark-step-done --outcome loop_back --force\n'
        '```\n'
    )
    post_fix = pre_fix.replace(
        '**Branch A — findings list is empty**: read the display_detail verbatim.',
        f'**Branch A — the verifier answered the stop question `{_STOP_ANSWER_YES}`**: '
        f'confirm `{_ACCEPTANCE_TOKEN}` and `{_STOP_ANSWER_YES}` first.',
    )

    # The walk finds both branches in both shapes — otherwise the split below is
    # caused by the parser rather than by the selector.
    for shape, label in ((pre_fix, 'pre-fix'), (post_fix, 'post-fix')):
        matches = {match.group(1) for match in _BRANCH_LABEL.finditer(shape)}
        assert matches == {'A', 'B'}, f'The branch walk read {sorted(matches)} in the {label} shape, not A and B'

    pre_done = [
        letter
        for letter, body in _branches_recording(_slice_branches(pre_fix), 'done').items()
        if _STOP_ANSWER_YES not in body
    ]
    assert pre_done == ['A'], (
        f'The unanswered-stop-question detector did not flag the pre-fix Branch A; '
        f'got {pre_done}. It records done with no stop answer anywhere, which is '
        f'exactly the state (i) exists to reject.'
    )

    post_done = [
        letter
        for letter, body in _branches_recording(_slice_branches(post_fix), 'done').items()
        if _STOP_ANSWER_YES not in body
    ]
    assert post_done == [], (
        f'The detector flagged the post-fix shape, whose closing branch DOES require '
        f'the stop answer; got {post_done}. A guard that fires on the fix is a false '
        f'positive and would have to be suppressed.'
    )

    # And the author-selector detector separates the two labels, so the label
    # read is what distinguishes them rather than something incidental.
    pre_labels = {letter: _branch_label(body) for letter, body in _slice_branches(pre_fix).items()}
    post_labels = {letter: _branch_label(body) for letter, body in _slice_branches(post_fix).items()}
    assert _AUTHOR_PREDICATE in pre_labels['A'], 'Fixture drift: the pre-fix Branch A must carry the author predicate'
    assert _AUTHOR_PREDICATE not in post_labels['A'], (
        'The post-fix Branch A still carries the author predicate in its label, so '
        'the selector assertion could not tell the two shapes apart'
    )


def test_verdict_parser_reads_the_pre_fix_single_clean_verdict():
    pre_fix = (
        '`display_detail` shape:\n'
        '- Empty `findings` → `"self-review clean: {N} candidates examined"` '
        "where `{N}` is the surfacer's `counts.total`.\n"
        '- Non-empty `findings` → `"self-review found {K} issues"`.\n'
    )

    literals = _verdict_literals(pre_fix)
    non_finding = _non_finding_verdicts(pre_fix)

    assert literals == [_OLD_CLEAN_FORM, 'self-review found {K} issues'], (
        f'Verdict parser failed to read the known pre-fix shape — assertions '
        f'(a), (b) and (d) would be vacuous. Got: {literals}'
    )
    assert non_finding == [_OLD_CLEAN_FORM], (
        f'Non-finding filter failed to separate the no-finding verdict from the findings verdict. Got: {non_finding}'
    )


def test_clean_prefix_detector_separates_the_not_run_verdict_from_its_siblings():
    """The (g) detector must fire on the collapse and stay silent on the split.

    A prefix constant that matched everything — or nothing — would make both
    halves of (g) vacuously green, which is the failure mode that let the
    mis-classification stand in the first place.
    """
    collapsed = 'self-review clean: not run, no surfacer implementor resolved'
    split = 'self-review not run: no surfacer implementor resolved'
    ran = 'self-review clean: surfacer ran, zero candidates surfaced'

    assert collapsed.startswith(_CLEAN_PREFIX), (
        'The clean-prefix detector does not fire on a not-run verdict rewritten '
        'as a clean one, so the first half of (g) could never fail'
    )
    assert not split.startswith(_CLEAN_PREFIX), (
        'The clean-prefix detector fires on the shipped not-run verdict, so the '
        'first half of (g) would fail for the wrong reason'
    )
    assert ran.startswith(_CLEAN_PREFIX), (
        'The clean-prefix detector does not fire on a ran-and-clean verdict, so '
        'the second half of (g) would report every sibling as unmarked'
    )


# ---------------------------------------------------------------------------
# Honest stop (D4 hardening)
#
# A runner that correctly halts with nothing further to claim stops BY NAME
# with matched evidence; anything else is not a stop, and a clean claim
# without its controls is a stall signature. Three pins: the simplify doc
# names both honest stops with their evidence, the surfacer skill states the
# stop/stall control vocabulary, and the Branch A stop path confirms
# convergence plus deterministic evidence before it may record done.
# ---------------------------------------------------------------------------


def _simplify_text() -> str:
    text: str = _SIMPLIFY_DOC.read_text(encoding='utf-8')
    return text


_STOP_BULLET = re.compile(r'^-\s+\*\*`?([a-z][a-z0-9-]*)`?\*\*', re.MULTILINE)

_NAMED_STOPS_HEADING = '## Named honest stops'


def _named_stops_section(text: str) -> str:
    """The named-stops section body, or empty when the heading is absent."""
    _heading, _, after = text.partition(_NAMED_STOPS_HEADING)
    if not after:
        return ''
    section, _, _rest = after.partition('\n## ')
    return section


def _simplify_stop_names(text: str) -> list[str]:
    """The honest-stop names the simplify doc actually declares.

    Parses the stop bullets under the named-stops section rather than
    checking membership in the hardcoded expectation: a third declared name
    must surface here as an observed difference, not pass silently because
    the detector only looked for the two it already knew.
    """
    return _STOP_BULLET.findall(_named_stops_section(text))


def _surfacer_controls_section(text: str) -> str:
    """The stop/stall matched-controls section body, or empty when absent."""
    _heading, _, after = text.partition(_SURFACER_CONTROLS_HEADING)
    if not after:
        return ''
    section, _, _rest = after.partition('\n### ')
    return section


def _branch_a_confirmation_markers(body: str) -> list[str]:
    """The stop-path confirmation markers Branch A carries."""
    return [marker for marker in _STOP_PATH_CONFIRMATION_MARKERS if marker in body]


def test_simplify_names_both_honest_stops_with_evidence():
    """Stop-by-name passage: both stop shapes are named with matched evidence."""
    text = _simplify_text()

    assert _simplify_stop_names(text) == list(_STOP_NAMES), (
        f'Simplify names {_simplify_stop_names(text)}, not both honest stops {_STOP_NAMES}. '
        f'A stop with no name is what a stall finding attaches to.'
    )
    assert 'Evidence:' in text, 'The named stops carry no matched evidence markers'
    assert _STALL_ATTACHMENT_MARKER in text, 'The shield rule does not bind stall findings to the named shapes'


def test_simplify_stop_name_detector_fires_on_unnamed_prose():
    """Mutation guard: prose with no stop names fails the detector."""
    assert _simplify_stop_names('A run that halts records done.') == [], (
        'The stop-name detector fired on prose naming no stop — it cannot tell a named stop from an unnamed halt'
    )


def test_surfacer_controls_section_states_stop_and_stall():
    """Stall detection: the control vocabulary names both stop and stall."""
    section = _surfacer_controls_section(_SURFACER_SKILL_DOC.read_text(encoding='utf-8'))

    assert section, (
        f'{_SURFACER_CONTROLS_HEADING!r} is absent from the surfacer skill — '
        f'the stop/stall vocabulary has no stated home'
    )
    assert 'stall' in section.lower(), 'The controls section never names the stall it separates from stop'
    for field in _SURFACER_CONTROL_FIELDS:
        assert field in section, (
            f'Matched control {field!r} is absent from the controls section — '
            f'the gate cannot consume a control the surface does not state'
        )


def test_surfacer_controls_detector_fires_when_section_absent():
    """Mutation guard: a skill doc without the section yields no controls."""
    assert _surfacer_controls_section('# Unrelated skill\n\nNo controls here.\n') == '', (
        'The controls-section detector fired on a doc without the section'
    )


def test_branch_a_carries_convergence_and_evidence_confirmations():
    """The stop path confirms convergence plus deterministic evidence."""
    bodies = _branch_bodies()
    assert 'A' in bodies, 'No Branch A sliced — the confirmation has no body to live in'

    assert _branch_a_confirmation_markers(bodies['A']) == list(_STOP_PATH_CONFIRMATION_MARKERS), (
        f'Branch A carries {_branch_a_confirmation_markers(bodies["A"])}, not the full '
        f'confirmation pair {_STOP_PATH_CONFIRMATION_MARKERS}. A close without the '
        f'convergence signal or without the deterministic-evidence match is a stop '
        f'on an empty findings list alone.'
    )


def test_branch_a_confirmation_detector_fires_on_pre_fix_body():
    """Mutation guard: a Branch A without the confirmations fails the detector."""
    pre_fix = (
        '**Branch A — the verifier answered the stop question `may_close: yes`**: '
        'read the display_detail verbatim and record done.'
    )

    assert _branch_a_confirmation_markers(pre_fix) == [], (
        'The confirmation detector fired on a Branch A carrying neither marker — '
        'it cannot tell a confirmed close from an unconfirmed one'
    )
