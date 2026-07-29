#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Doc-contract regression for the pre-submission-self-review clean verdicts.

``pre-submission-self-review.md`` used to report a single undifferentiated
clean verdict — ``"self-review clean: {N} candidates examined"`` — on two
structurally different outcomes:

* **Nothing to check.** No candidate was surfaced at all (the zero-generator
  fallback in Step 1, or a diff the surfacer found nothing in). No cognitive
  check ever ran.
* **No check matched.** Candidates WERE surfaced, every check was applied to
  them, and none fired.

Collapsing the two hides the review-coverage difference: an operator reading
"clean" on the nothing-to-check path concludes the change was reviewed and
passed, when in fact nothing was reviewed. The defect class this file guards is
the same one the workflow's own check 14 exists to catch — a verdict that cannot
distinguish two states is a guard that can never observe a difference.

These tests pin the split:

(a) The ``display_detail`` shape section declares exactly TWO distinct clean
    verdicts, each carrying its labelled name (``nothing-to-check`` /
    ``no-check-matched``).
(b) Neither clean verdict is a prefix of the other, so a consumer matching a
    whole verdict string cannot mistake one for the other.
(c) The zero-generator fallback path (Step 1) reports the nothing-to-check
    verdict, and never the no-check-matched one.
(d) The old single undifferentiated form is no longer the SOLE clean verdict.
(e) The inline-vs-dispatch return-shape invariant names both clean verdicts, so
    the two branches cannot drift into differing verdict vocabularies.

Every property assertion is paired with a mutation guard that runs the detector
against the known pre-fix prose; without them a regex typo would make the
corresponding assertion vacuously green.
"""

from __future__ import annotations

import re

from _dispatch_roster import section_lines
from conftest import MARKETPLACE_ROOT

_WORKFLOW_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'pre-submission-self-review.md'
)

_OUTPUT_HEADING = '### Dispatched-envelope output (returned from Steps 2–3 to Step 4)'
_GATE_HEADING = '### Step 1b: Candidate-count gate (inline vs dispatch) — B5'
_SURFACE_HEADING = '### Step 1: Deterministic surface (inline)'

#: Sub-headings and horizontal rules that terminate a ``### `` section.
_STOP_PREFIXES = ('### ', '## ', '# ', '---')

#: A verdict literal is a backticked, double-quoted string starting with the
#: ``self-review`` token. Captures the string body without its quotes.
_VERDICT_LITERAL = re.compile(r'`"(self-review[^"]*)"`')

#: The labelled verdict names the doc must carry, mapped to the marker phrase
#: that identifies which literal belongs to which label.
_NOTHING_TO_CHECK_LABEL = 'nothing-to-check'
_NO_CHECK_MATCHED_LABEL = 'no-check-matched'

#: The pre-fix, undifferentiated clean verdict, as a normalised shape. The
#: ``{N}`` placeholder is literal in the doc.
_OLD_CLEAN_FORM = 'self-review clean: {N} candidates examined'

#: The finding-bearing (non-clean) verdict, excluded from the clean-verdict set.
_FINDINGS_VERDICT_MARKER = 'found'

#: display_detail budget, per the agent-return-shape contract.
_DISPLAY_DETAIL_MAX = 80


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


def _clean_verdicts(text: str) -> list[str]:
    """Return the verdict literals that report a CLEAN outcome."""
    return [
        literal
        for literal in _verdict_literals(text)
        if _FINDINGS_VERDICT_MARKER not in literal
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

    assert section.strip(), (
        f'{_OUTPUT_HEADING!r} section is empty — every assertion below would be '
        f'vacuous'
    )


def test_surface_section_is_present_and_non_empty():
    section = _section(_SURFACE_HEADING)

    assert section.strip(), (
        f'{_SURFACE_HEADING!r} section is empty — the zero-generator fallback '
        f'assertion would be vacuous'
    )


# ---------------------------------------------------------------------------
# (a) two distinct clean verdicts, each labelled
# ---------------------------------------------------------------------------


def test_two_distinct_clean_verdicts_are_declared():
    clean = _clean_verdicts(_section(_OUTPUT_HEADING))

    assert len(clean) == 2, (
        f'The display_detail shape must declare exactly two distinct clean '
        f'verdicts (nothing-to-check and no-check-matched). Found {len(clean)}: '
        f'{clean}'
    )


def test_both_clean_verdicts_carry_their_label():
    section = _section(_OUTPUT_HEADING)

    for label in (_NOTHING_TO_CHECK_LABEL, _NO_CHECK_MATCHED_LABEL):
        assert label in section, (
            f'The display_detail shape must name the {label!r} verdict '
            f'explicitly, so a reader can tell which literal covers which state'
        )


def test_nothing_to_check_verdict_names_the_absent_candidate_set():
    section = _section(_OUTPUT_HEADING)
    clean = _clean_verdicts(section)
    nothing = [literal for literal in clean if '{N}' not in literal]

    assert len(nothing) == 1, (
        f'Exactly one clean verdict must be candidate-count-free (the '
        f'nothing-to-check verdict, reported when no candidate was surfaced at '
        f'all). Got: {nothing}'
    )


def test_no_check_matched_verdict_carries_the_candidate_count():
    section = _section(_OUTPUT_HEADING)
    clean = _clean_verdicts(section)
    counted = [literal for literal in clean if '{N}' in literal]

    assert len(counted) == 1, (
        f'Exactly one clean verdict must carry the {{N}} candidate count (the '
        f'no-check-matched verdict, reported when candidates WERE examined). '
        f'Got: {counted}'
    )


def test_every_verdict_fits_the_display_detail_budget():
    # The count placeholder is widened to its plausible maximum so the budget
    # is asserted against the rendered string, not the template.
    for literal in _verdict_literals(_section(_OUTPUT_HEADING)):
        rendered = literal.replace('{N}', '9999').replace('{K}', '9999')

        assert len(rendered) <= _DISPLAY_DETAIL_MAX, (
            f'Verdict {literal!r} renders to {len(rendered)} chars, over the '
            f'{_DISPLAY_DETAIL_MAX}-char display_detail budget'
        )
        assert rendered.isascii(), f'Verdict {literal!r} is not ASCII'
        assert not rendered.endswith('.'), (
            f'Verdict {literal!r} carries a trailing period, which the '
            f'agent-return-shape contract forbids'
        )


# ---------------------------------------------------------------------------
# (b) the two clean verdicts are not prefix-collisions
# ---------------------------------------------------------------------------


def test_clean_verdicts_are_not_prefix_collisions():
    clean = _clean_verdicts(_section(_OUTPUT_HEADING))
    assert clean, 'No clean verdicts parsed — the assertion would be vacuous'

    collisions = _prefix_collisions(clean)

    assert not collisions, (
        f'One clean verdict is a prefix of another, so a consumer matching a '
        f'whole verdict string can mistake one for the other: {collisions}'
    )


def test_no_verdict_at_all_is_a_prefix_of_another():
    literals = _verdict_literals(_section(_OUTPUT_HEADING))
    assert literals, 'No verdicts parsed — the assertion would be vacuous'

    collisions = _prefix_collisions(literals)

    assert not collisions, (
        f'Verdict prefix collision across the full verdict set: {collisions}'
    )


# ---------------------------------------------------------------------------
# (c) the zero-generator fallback uses the nothing-to-check verdict
# ---------------------------------------------------------------------------


def test_zero_generator_fallback_reports_the_nothing_to_check_verdict():
    surface = _section(_SURFACE_HEADING)
    nothing = [
        literal
        for literal in _clean_verdicts(_section(_OUTPUT_HEADING))
        if '{N}' not in literal
    ]
    assert len(nothing) == 1, 'Nothing-to-check verdict not resolvable'

    assert nothing[0] in surface, (
        f'The zero-generator fallback path must report the nothing-to-check '
        f'verdict {nothing[0]!r} — it surfaced no candidates, so no check ran'
    )


def test_zero_generator_fallback_does_not_report_the_examined_verdict():
    surface = _section(_SURFACE_HEADING)
    counted = [
        literal
        for literal in _clean_verdicts(_section(_OUTPUT_HEADING))
        if '{N}' in literal
    ]
    assert len(counted) == 1, 'No-check-matched verdict not resolvable'

    assert counted[0] not in surface, (
        f'The zero-generator fallback path must NOT claim candidates were '
        f'examined — it reported {counted[0]!r}, the no-check-matched verdict'
    )


def test_zero_generator_fallback_does_not_report_the_old_undifferentiated_form():
    surface = _section(_SURFACE_HEADING)

    assert f'"{_OLD_CLEAN_FORM}"' not in surface, (
        'The zero-generator fallback still reports the pre-fix undifferentiated '
        'clean verdict'
    )
    # The literal pre-fix zero-count rendering is the exact string the fallback
    # used to emit.
    assert '"self-review clean: 0 candidates examined"' not in surface


# ---------------------------------------------------------------------------
# (d) the old undifferentiated form is not the sole clean verdict
# ---------------------------------------------------------------------------


def test_old_undifferentiated_clean_form_is_not_the_sole_clean_verdict():
    clean = _clean_verdicts(_doc_text())

    assert clean != [_OLD_CLEAN_FORM], (
        f'The document still carries the pre-fix single undifferentiated clean '
        f'verdict {_OLD_CLEAN_FORM!r} as its only clean verdict'
    )
    assert len(clean) >= 2, (
        f'Fewer than two distinct clean verdicts survive document-wide: {clean}'
    )


def test_old_undifferentiated_form_does_not_survive_verbatim_as_a_verdict():
    # A verdict literal EQUAL to the old form would re-collapse the split even
    # while a second verdict exists elsewhere.
    clean = _clean_verdicts(_doc_text())

    assert _OLD_CLEAN_FORM not in clean, (
        f'The pre-fix verdict {_OLD_CLEAN_FORM!r} is still declared verbatim as '
        f'a verdict literal — the two states can still be reported identically'
    )


# ---------------------------------------------------------------------------
# (e) the inline / dispatch branches share one verdict vocabulary
# ---------------------------------------------------------------------------


def test_return_shape_invariant_names_both_clean_verdicts():
    gate = _section(_GATE_HEADING)
    clean = _clean_verdicts(_section(_OUTPUT_HEADING))
    assert len(clean) == 2, 'Clean verdicts not resolvable'

    missing = [literal for literal in clean if literal not in gate]

    assert not missing, (
        f'The inline-vs-dispatch return-shape invariant must name every clean '
        f'verdict so the two branches cannot drift into differing verdict '
        f'vocabularies. Missing from Step 1b: {missing}'
    )


# ---------------------------------------------------------------------------
# Mutation guards — each detector must fire on the known pre-fix prose
# ---------------------------------------------------------------------------


def test_verdict_parser_reads_the_pre_fix_single_clean_verdict():
    pre_fix = (
        '`display_detail` shape:\n'
        '- Empty `findings` → `"self-review clean: {N} candidates examined"` '
        'where `{N}` is the surfacer\'s `counts.total`.\n'
        '- Non-empty `findings` → `"self-review found {K} issues"`.\n'
    )

    literals = _verdict_literals(pre_fix)
    clean = _clean_verdicts(pre_fix)

    assert literals == [_OLD_CLEAN_FORM, 'self-review found {K} issues'], (
        f'Verdict parser failed to read the known pre-fix shape — assertions '
        f'(a), (b) and (d) would be vacuous. Got: {literals}'
    )
    assert clean == [_OLD_CLEAN_FORM], (
        f'Clean-verdict filter failed to separate the clean verdict from the '
        f'findings verdict. Got: {clean}'
    )


def test_sole_clean_verdict_detector_rejects_the_pre_fix_shape():
    pre_fix = (
        '- Empty `findings` → `"self-review clean: {N} candidates examined"`.\n'
        '- Non-empty `findings` → `"self-review found {K} issues"`.\n'
    )

    clean = _clean_verdicts(pre_fix)

    # This is exactly the state assertion (d) exists to fail on.
    assert clean == [_OLD_CLEAN_FORM]
    assert len(clean) < 2, (
        'The pre-fix shape must be detected as carrying fewer than two clean '
        'verdicts — otherwise assertion (d) could never fail'
    )


def test_prefix_collision_detector_fires_on_a_colliding_pair():
    colliding = [
        'self-review clean',
        'self-review clean: {N} candidates examined',
    ]

    collisions = _prefix_collisions(colliding)

    assert collisions == [(colliding[0], colliding[1])], (
        f'Prefix-collision detector failed to fire on a known colliding pair — '
        f'assertion (b) would be vacuous. Got: {collisions}'
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
    rendered = literals[0].replace('{N}', '9999')
    assert len(rendered) > _DISPLAY_DETAIL_MAX, (
        'Budget detector would not fire on an over-long verdict — the budget '
        'assertion would be vacuous'
    )
