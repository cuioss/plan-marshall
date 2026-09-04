#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Doc-contract regression for the pre-submission-self-review clean verdicts.

``pre-submission-self-review.md`` used to report a single undifferentiated
clean verdict — ``"self-review clean: {N} candidates examined"`` — across
structurally different outcomes. The document now declares one labelled clean
verdict per outcome:

* **not-run.** No domain surfacer resolved in the executor (the zero-generator
  fallback in Step 1). Nothing ran: no file was searched, no candidate was
  constructed, no check executed. This verdict is a statement about the
  EXECUTOR and makes no claim about the diff.
* **nothing-to-check.** A surfacer RAN over a real file set and produced no
  candidate, so no check had anything to run against. A weak statement about
  the diff, but a statement about the diff.
* **no-check-matched.** Candidates WERE surfaced, every check was applied to
  them, and none fired.
* **zero-observation.** A full-surface round returned no findings while its
  ``delta_coverage.files_with_candidates`` was 0 over a non-zero
  ``files_in_scope`` — it drew no observation of its own from the files it
  searched.

Collapsing any two hides a review-coverage difference. The sharpest is the
first pair: an operator reading "clean" on the not-run path concludes the
change was reviewed and passed, when in fact NO ANALYSIS WAS PERFORMED. The
defect class this file guards is the same one the workflow's own check 14
exists to catch — a verdict that cannot distinguish two states is a guard that
can never observe a difference.

These tests pin the split:

(a) The ``display_detail`` shape section declares one distinct clean verdict
    per declared label, each carrying its labelled name. The expected
    cardinality is DERIVED from the label set rather than written as a
    literal, so adding a label without adding its verdict fails here.
(b) The clean verdicts partition: every declared label claims exactly one
    literal, and every literal is claimed by exactly one label.
(c) No clean verdict is a prefix of another, so a consumer matching a whole
    verdict string cannot mistake one for another.
(d) The zero-generator fallback path (Step 1) reports the not-run verdict by
    its own label, and reports NO other clean verdict.
(e) The old single undifferentiated form is no longer the SOLE clean verdict.
(f) The inline-vs-dispatch return-shape invariant names every clean verdict,
    so the two branches cannot drift into differing verdict vocabularies.

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

#: The labelled clean verdicts the doc must carry, mapped to the marker phrase
#: that identifies which literal belongs to which label.
#:
#: This mapping is the POPULATION every cardinality below is derived from. A
#: bare ``len(clean) == 2`` went stale the moment a third clean verdict was
#: declared — and it would have gone stale SILENTLY in the other direction too,
#: passing while a declared label had no literal at all. Deriving the expected
#: count from this dict is what keeps the assertion honest as the set grows:
#: adding a label here without adding its verdict to the document fails (a),
#: and adding a verdict to the document without a label here fails (b).
_CLEAN_VERDICT_MARKERS = {
    'not-run': 'not run',
    'nothing-to-check': 'zero candidates surfaced',
    'no-check-matched': '{N} candidates examined',
    'zero-observation': 'no observation',
}

#: The label whose verdict the zero-generator fallback path reports. Resolved
#: by LABEL rather than by a ``len(...) == 1`` filter over some incidental
#: property: three of the four clean verdicts carry no ``{N}``, so the old
#: "the one without a count" filter no longer identifies anything.
_ZERO_GENERATOR_LABEL = 'not-run'

#: The pre-fix, undifferentiated clean verdict, as a normalised shape. The
#: ``{N}`` placeholder is literal in the doc.
_OLD_CLEAN_FORM = 'self-review clean: {N} candidates examined'

#: The finding-bearing (non-clean) verdict, excluded from the clean-verdict set.
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


def _clean_verdicts(text: str) -> list[str]:
    """Return the verdict literals that report a CLEAN outcome."""
    return [
        literal
        for literal in _verdict_literals(text)
        if _FINDINGS_VERDICT_MARKER not in literal
    ]


def _partition_clean_verdicts(clean: list[str]) -> dict[str, list[str]]:
    """Map each declared label to the clean literals carrying its marker.

    A well-formed document yields exactly one literal per label and leaves no
    literal unclaimed — that is the partition assertion (b) checks, and it is
    what replaced the pre-split ``len(clean) == 2`` count.
    """
    return {
        label: [literal for literal in clean if marker in literal]
        for label, marker in _CLEAN_VERDICT_MARKERS.items()
    }


def _unclaimed_clean_verdicts(clean: list[str]) -> list[str]:
    """Return clean literals no declared label's marker matches."""
    return [
        literal
        for literal in clean
        if not any(marker in literal for marker in _CLEAN_VERDICT_MARKERS.values())
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
# (a) one distinct clean verdict per declared label
# ---------------------------------------------------------------------------


def test_one_distinct_clean_verdict_per_declared_label():
    clean = _clean_verdicts(_section(_OUTPUT_HEADING))
    expected = len(_CLEAN_VERDICT_MARKERS)

    # The cardinality is DERIVED from the declared label population, never
    # written as a literal — a hard-coded count is what went stale when the
    # un-run/un-observed split turned two clean verdicts into four.
    assert len(clean) == expected, (
        f'The display_detail shape must declare exactly one distinct clean '
        f'verdict per declared label '
        f'({sorted(_CLEAN_VERDICT_MARKERS)}) — {expected} in total. '
        f'Found {len(clean)}: {clean}'
    )


def test_every_clean_verdict_carries_its_label():
    section = _section(_OUTPUT_HEADING)

    for label in _CLEAN_VERDICT_MARKERS:
        assert label in section, (
            f'The display_detail shape must name the {label!r} verdict '
            f'explicitly, so a reader can tell which literal covers which state'
        )


# ---------------------------------------------------------------------------
# (b) the clean verdicts PARTITION over the declared labels
# ---------------------------------------------------------------------------


def test_clean_verdicts_partition_over_the_declared_labels():
    """Every label claims exactly one literal; every literal exactly one label.

    This replaced a ``len(nothing) == 1`` filter that identified the
    candidate-count-free verdict by the ABSENCE of ``{N}``. Three of the four
    clean verdicts now carry no ``{N}``, so that filter identifies nothing —
    and, worse, would have kept passing had it happened to match one. A
    partition over labelled names states the property directly instead of
    inferring it from an incidental field.
    """
    clean = _clean_verdicts(_section(_OUTPUT_HEADING))
    assert clean, 'No clean verdicts parsed — the assertion would be vacuous'

    partition = _partition_clean_verdicts(clean)

    ambiguous = {label: hits for label, hits in partition.items() if len(hits) != 1}
    assert not ambiguous, (
        f'Each declared label must claim exactly one clean verdict literal. '
        f'These claimed a different number: {ambiguous}'
    )

    unclaimed = _unclaimed_clean_verdicts(clean)
    assert not unclaimed, (
        f'These clean verdicts are claimed by no declared label, so the '
        f'partition does not cover the set the document actually declares: '
        f'{unclaimed}. Add each to _CLEAN_VERDICT_MARKERS in the same change.'
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
            f'Verdict {literal!r} carries a trailing period, which the '
            f'agent-return-shape contract forbids'
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
        {
            found
            for literal in literals
            for found in placeholder_re.findall(literal)
            if found not in _COUNT_PLACEHOLDERS
        }
    )

    assert not uncovered, (
        f'These verdict placeholders are not widened before the budget is '
        f'measured, so the budget assertion measures the template instead of '
        f'the rendered string: {uncovered}. Add each to _COUNT_PLACEHOLDERS.'
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
# (d) the zero-generator fallback uses the not-run verdict, and only it
# ---------------------------------------------------------------------------


def test_zero_generator_fallback_reports_the_not_run_verdict():
    surface = _section(_SURFACE_HEADING)
    partition = _partition_clean_verdicts(_clean_verdicts(_section(_OUTPUT_HEADING)))

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


def test_zero_generator_fallback_reports_no_other_clean_verdict():
    """The fallback must not borrow a verdict that claims something ran.

    Every other clean verdict is a statement about a file set a surfacer
    actually searched. The fallback searched none, so reporting any of them
    there would restate an un-run analysis as an observation — including the
    nothing-to-check verdict, which is the near-miss this guards.
    """
    surface = _section(_SURFACE_HEADING)
    partition = _partition_clean_verdicts(_clean_verdicts(_section(_OUTPUT_HEADING)))

    others = {
        label: hits[0]
        for label, hits in partition.items()
        if label != _ZERO_GENERATOR_LABEL and len(hits) == 1
    }
    assert others, 'No sibling clean verdicts resolvable — assertion vacuous'

    leaked = {
        label: literal for label, literal in others.items() if literal in surface
    }

    assert not leaked, (
        f'The zero-generator fallback path performed no analysis, so it must '
        f'report no verdict that claims a file set was searched. It reported: '
        f'{leaked}'
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
    # Derived from the declared label population, not a literal floor: every
    # labelled verdict is declared in the output section, so all of them must
    # survive a document-wide read too.
    expected = len(_CLEAN_VERDICT_MARKERS)
    assert len(clean) >= expected, (
        f'Fewer than {expected} distinct clean verdicts survive document-wide '
        f'(one per declared label {sorted(_CLEAN_VERDICT_MARKERS)}): {clean}'
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
# (f) the inline / dispatch branches share one verdict vocabulary
# ---------------------------------------------------------------------------


def test_return_shape_invariant_names_every_clean_verdict():
    gate = _section(_GATE_HEADING)
    clean = _clean_verdicts(_section(_OUTPUT_HEADING))
    # Re-derived over the FULL clean set: the pre-split form asserted
    # ``len(clean) == 2`` and would have skipped every verdict beyond the
    # second, letting a new verdict enter the vocabulary un-checked.
    assert len(clean) == len(_CLEAN_VERDICT_MARKERS), 'Clean verdicts not resolvable'

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


def test_partition_detector_fires_on_an_unclaimed_and_on_a_doubly_claimed_literal():
    """Both halves of the partition assertion must be able to fail.

    Without this, a marker typo would leave every label matching nothing while
    ``ambiguous`` reported the failure only if some label matched twice — and a
    marker broad enough to match every literal would leave ``unclaimed`` empty
    forever. Each half is fired here against a synthetic set built to trip it.
    """
    # Half 1 — a literal no declared marker claims.
    unclaimed_set = ['self-review clean: a shape no marker names']
    assert _unclaimed_clean_verdicts(unclaimed_set) == unclaimed_set, (
        'The unclaimed-literal detector did not fire on a literal carrying no '
        'declared marker — the coverage half of the partition would be vacuous'
    )

    # Half 2 — one label claiming two literals, which is the collapse the
    # partition exists to reject.
    doubled = [
        'self-review clean: {N} candidates examined, no check matched',
        'self-review clean: {N} candidates examined, nothing fired',
    ]
    partition = _partition_clean_verdicts(doubled)
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
    assert not _unclaimed_clean_verdicts(well_formed)
    assert all(
        len(hits) == 1 for hits in _partition_clean_verdicts(well_formed).values()
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
    rendered = _render(literals[0])
    assert len(rendered) > _DISPLAY_DETAIL_MAX, (
        'Budget detector would not fire on an over-long verdict — the budget '
        'assertion would be vacuous'
    )
