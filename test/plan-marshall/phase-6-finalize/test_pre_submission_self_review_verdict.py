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


def test_output_section_is_present_and_non_empty():
    section = _section(_OUTPUT_HEADING)

    assert section.strip(), f'{_OUTPUT_HEADING!r} section is empty — every assertion below would be vacuous'


def test_surface_section_is_present_and_non_empty():
    section = _section(_SURFACE_HEADING)

    assert section.strip(), (
        f'{_SURFACE_HEADING!r} section is empty — the zero-generator fallback assertion would be vacuous'
    )


# ---------------------------------------------------------------------------
# (a) one distinct non-finding verdict per declared label
# ---------------------------------------------------------------------------


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


def test_every_non_finding_verdict_carries_its_label():
    section = _section(_OUTPUT_HEADING)

    for label in _NON_FINDING_VERDICT_MARKERS:
        assert label in section, (
            f'The display_detail shape must name the {label!r} verdict '
            f'explicitly, so a reader can tell which literal covers which state'
        )


# ---------------------------------------------------------------------------
# (b) the non-finding verdicts PARTITION over the declared labels
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# (c) the non-finding verdicts are not prefix-collisions
# ---------------------------------------------------------------------------


def test_non_finding_verdicts_are_not_prefix_collisions():
    non_finding = _non_finding_verdicts(_section(_OUTPUT_HEADING))
    assert non_finding, 'No non-finding verdicts parsed — assertion would be vacuous'

    collisions = _prefix_collisions(non_finding)

    assert not collisions, (
        f'One non-finding verdict is a prefix of another, so a consumer '
        f'matching a whole verdict string can mistake one for the other: '
        f'{collisions}'
    )


def test_no_verdict_at_all_is_a_prefix_of_another():
    literals = _verdict_literals(_section(_OUTPUT_HEADING))
    assert literals, 'No verdicts parsed — the assertion would be vacuous'

    collisions = _prefix_collisions(literals)

    assert not collisions, f'Verdict prefix collision across the full verdict set: {collisions}'


# ---------------------------------------------------------------------------
# (d) the zero-generator fallback uses the not-run verdict, and only it
# ---------------------------------------------------------------------------


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


def test_zero_generator_fallback_does_not_report_the_old_undifferentiated_form():
    surface = _section(_SURFACE_HEADING)

    assert f'"{_OLD_CLEAN_FORM}"' not in surface, (
        'The zero-generator fallback still reports the pre-fix undifferentiated clean verdict'
    )
    # The literal pre-fix zero-count rendering is the exact string the fallback
    # used to emit.
    assert '"self-review clean: 0 candidates examined"' not in surface


# ---------------------------------------------------------------------------
# (e) the old undifferentiated form is not the sole non-finding verdict
# ---------------------------------------------------------------------------


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


def test_old_undifferentiated_form_does_not_survive_verbatim_as_a_verdict():
    # A verdict literal EQUAL to the old form would re-collapse the split even
    # while a second verdict exists elsewhere.
    non_finding = _non_finding_verdicts(_doc_text())

    assert _OLD_CLEAN_FORM not in non_finding, (
        f'The pre-fix verdict {_OLD_CLEAN_FORM!r} is still declared verbatim as '
        f'a verdict literal — the two states can still be reported identically'
    )


# ---------------------------------------------------------------------------
# (f) the inline / dispatch branches share one verdict vocabulary
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# (g) `clean:` is reserved for a verdict produced after a surfacer RAN
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# (h) author and verifier: whichever arrangement was implemented is asserted,
#     and an unrecorded author-equals-verifier state fails
# ---------------------------------------------------------------------------
#
# The step used to close on its author's own reading of its own findings list:
# one party produced the verdict and the same party's branch selection accepted
# it. Two arrangements could answer that, and this suite must not pin either as
# a string — it asserts whichever one the document implements, and fails the one
# state that is never acceptable: author and verifier are the same party AND the
# document does not say so.
#
# The ARRANGEMENT is derived from the document, not listed here:
#   * independence — a Role table declaring an author and a verifier that run in
#     DIFFERENT contexts, a second dispatch that spawns the verifier, and a
#     closing branch that requires its acceptance;
#   * the honest alternative — the same-party limitation stated in BOTH the
#     workflow doc and the surfacer skill, and carried on the recorded verdict.
# Exactly one must hold. Neither is the unrecorded collapse; both at once is a
# document that says two contradictory things about its own shape.

_SURFACER_SKILL_DOC = (
    MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'ext-self-review-plan-marshall' / 'SKILL.md'
)

_INDEPENDENCE_HEADING = '## Author and verifier are different parties'
_VERIFIER_STEP_HEADING = '### Step 3b: Independent verification (dispatch)'
_BRANCH_A_SECTION_HEADING = '### Step 4: Mark Step Complete (inline)'

#: The two judging roles the independence arrangement must declare, as the Role
#: table spells them. Derived comparison: the assertion below reads each row's
#: "where it runs" cell out of the table, so the CONTEXTS are never pinned here —
#: only the fact that these two roles must both be declared and must differ.
_AUTHOR_ROLE = 'author'
_VERIFIER_ROLE = 'verifier'

#: The first header cell that identifies the Role table, by the same
#: first-header-cell discipline the prompt-fields guard uses for its own table.
_ROLE_TABLE_HEADER = 'role'

#: The phrase the HONEST-ALTERNATIVE arrangement would state. It is the marker
#: for "the limitation is recorded", never for "the limitation exists" — the
#: whole point of the disjunction below is that an existing-but-unstated
#: limitation matches nothing and therefore fails.
_SAME_PARTY_MARKER = 'author and verifier are the same party'

#: A dispatch spawn, as the workflow document writes one.
_TASK_SPAWN = re.compile(r'^\s*Task:\s+plan-marshall:', re.MULTILINE)

#: The acceptance token the closing branch must require. Read as a token of the
#: verifier's own return contract rather than as a sentence, so rewording the
#: precondition's prose does not break the assertion while dropping the
#: requirement would.
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


# ---------------------------------------------------------------------------
# (i) the STOP QUESTION — no path records `done` on an unanswered one
# ---------------------------------------------------------------------------
#
# (h) established that a second party exists and accepts the verdict. (i) pins
# the decision (h) made possible: *may this round record done?* is put TO that
# party, and the author records the answer. Branch A used to be selected by the
# author's own reading of the findings list it had just produced, which is the
# state both deliverables exist to leave behind.
#
# The branch set is DERIVED from the document — every `**Branch X — …**` label
# Step 4 declares — rather than pinned as {A, B, C} here. A branch added later
# is swept without editing this file, which is what keeps "no path records done
# without an answered stop question" a claim about the document rather than
# about the three branches someone remembered.

#: The affirmative stop answer, as the closing branch must require it.
_STOP_ANSWER_YES = 'may_close: yes'

#: The pre-fix selector — the author's own reading of the list it just produced.
#: A done-recording branch labelled with this is selected by its author.
_AUTHOR_PREDICATE = 'findings list is empty'

#: A Step 4 branch label, as the document writes one.
_BRANCH_LABEL = re.compile(r'^\*\*Branch ([A-Z]) — (.+?)\*\*', re.MULTILINE)

#: The outcome a branch records, read off the `--outcome` flag of the
#: `mark-step-done` call(s) inside that branch's own text.
_RECORDED_OUTCOME = re.compile(r'--outcome\s+([a-z_]+)')

#: The one path that reaches `done` without a stop answer, and the reason it is
#: not a hole: it ran no surfacer, so there is no round for a stop question to be
#: about. Matched on the label the document gives it, not on a sentence.
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


#: A branch's own "Precondition — ..." paragraph(s) — the line(s) a closing
#: decision's actual gate is written on, distinct from the label above it and
#: from the rest of the branch's unrelated prose.
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


# ---------------------------------------------------------------------------
# Mutation guards for (h) — each detector must fire on the shape it targets
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Mutation guards — each detector must fire on the known pre-fix prose
# ---------------------------------------------------------------------------


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


def test_budget_detector_fires_on_an_over_long_verdict():
    over_long = '`"self-review clean: {N} ' + ('x' * _DISPLAY_DETAIL_MAX) + '"`'

    literals = _verdict_literals(over_long)

    assert len(literals) == 1, 'Verdict parser failed on the synthetic over-long form'
    rendered = _render(literals[0])
    assert len(rendered) > _DISPLAY_DETAIL_MAX, (
        'Budget detector would not fire on an over-long verdict — the budget assertion would be vacuous'
    )
