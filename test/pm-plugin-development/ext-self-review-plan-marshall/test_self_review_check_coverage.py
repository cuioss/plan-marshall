#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Population-derived contract test: every counted candidate list has a check.

The self-review surfacer sums every ``CANDIDATE_LISTS`` entry whose ``in_total``
flag is set into ``counts.total`` — the number the terminal verdict reports as
``"{N} candidates examined"`` and the Step 1b dispatch gate keys off. A summed
entry that no cognitive check adjudicates inflates that examined-count without
being examined: volume-read-as-coverage, reproduced inside the very contract
built to detect it (the pre-fix ``duplicate_claimable_keys`` /
``discard_without_report`` gap).

This test ties registry membership to check coverage by an invariant. The
population is DERIVED from the registry (``in_total`` entries), never a
hand-copied list, and its size is published so a pass over an empty population —
the vacuous-confident-zero archetype this whole surface is about — is impossible.
For each counted entry it requires a backtick-quoted reference to the entry's key
inside the workflow doc's NUMBERED-CHECK block (not merely somewhere in the
Step-3 region): a key that appears only in the region's explanatory prose — the
preamble, the class-closure obligation, the present-state grounding precondition,
or a worked example — does NOT count as a consuming check, because none of those
adjudicates the candidate. A counted entry with no numbered check that references
it fails here rather than silently shipping.
"""

import re

from _self_review_patterns import CANDIDATE_LISTS, CandidateList

from conftest import MARKETPLACE_ROOT

_WORKFLOW_DOC = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'pre-submission-self-review.md'
)

#: The Step-3 checks region boundaries. Coverage is asserted ONLY inside the
#: region where the numbered cognitive checks live, so a candidate-list key that
#: appears in an Inputs table or an output-schema block elsewhere in the doc is
#: never mistaken for a consuming check.
_CHECKS_REGION_START = '### Step 3: Apply'
_CHECKS_REGION_END = '### Dispatched-envelope output'

#: A numbered cognitive-check entry opener — ``1. `` / ``17. `` at column zero.
#: The numbered checks are the LAST thing in the Step-3 region before the
#: dispatched-envelope output, after the preamble and every ``####`` subsection,
#: so the block from the first such line to the region end is exactly the
#: numbered checks. This is the discriminator that keeps a key mentioned only in
#: explanatory prose (which precedes the first numbered check) from reading as
#: covered.
_NUMBERED_CHECK_OPENER = re.compile(r'^\d+\.\s', re.MULTILINE)


def _checks_region(text: str) -> str:
    """Return the workflow doc's Step-3 cognitive-checks region."""
    start = text.index(_CHECKS_REGION_START)
    end = text.index(_CHECKS_REGION_END)
    return text[start:end]


def _numbered_check_block(region: str) -> str:
    """Return only the numbered-check entries of a Step-3 ``region``.

    The block runs from the first ``N.`` numbered-check opener to the end of the
    region, so the preamble and the ``####`` subsections that precede the checks
    — where a candidate-list key may legitimately appear in explanatory prose
    without any check adjudicating it — are excluded. An empty string is
    returned when the region carries no numbered check (which the caller asserts
    against, so it cannot pass vacuously).
    """
    match = _NUMBERED_CHECK_OPENER.search(region)
    if match is None:
        return ''
    return region[match.start() :]


def _counted_lists() -> list[CandidateList]:
    """The population: every registry entry summed into ``counts.total``."""
    return [spec for spec in CANDIDATE_LISTS if spec.in_total]


def _uncovered(candidate_lists: tuple[CandidateList, ...], check_block: str) -> list[str]:
    """Return the counted keys with no backtick-quoted reference in ``check_block``.

    ``check_block`` is the numbered-check text (see :func:`_numbered_check_block`),
    not the whole Step-3 region, so a key that appears only in the region's
    explanatory prose is correctly reported as uncovered. The predicate is pure
    so a negative control can drive it with synthetic input, proving the invariant
    actually fails when a counted entry lacks a check rather than passing vacuously.
    """
    return [
        spec.key
        for spec in candidate_lists
        if spec.in_total and f'`{spec.key}`' not in check_block
    ]


class TestCountedListCheckCoverage:
    def test_every_counted_candidate_list_has_a_consuming_check(self, capsys):
        population = _counted_lists()
        # Guard against a silently empty population. A set-guarding test that can
        # pass having enumerated nothing is exactly the vacuous-confident-zero
        # archetype this plan is about, so the population size is asserted > 0
        # and PUBLISHED before the coverage claim is made.
        assert len(population) > 0
        print(f'counted candidate lists (population size): {len(population)}')
        region = _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        block = _numbered_check_block(region)
        # The region MUST carry numbered checks, or the block is empty and every
        # key would (wrongly) read as uncovered — assert the block is real so the
        # coverage claim is drawn against actual check entries.
        assert block, 'Step-3 region carries no numbered check entry'
        uncovered = _uncovered(tuple(population), block)
        assert uncovered == [], (
            'counted candidate list(s) with no consuming numbered check in the '
            f'workflow doc Step-3 region: {uncovered} (population={len(population)})'
        )

    def test_coverage_predicate_detects_an_entirely_absent_key(self):
        # NEGATIVE CONTROL 1: the invariant MUST fail when a counted entry's key
        # is absent from the check block entirely. A non-counted (in_total=False)
        # orphan is correctly ignored.
        synthetic = (
            CandidateList('covered_key', 'covered', True, 'structural'),
            CandidateList('orphan_key', 'orphan', True, 'structural'),
            CandidateList('anchor_key', 'anchor', False, 'prose_contract'),
        )
        block = '1. **Real check** — for each `covered_key` entry, adjudicate it.'
        assert _uncovered(synthetic, block) == ['orphan_key']

    def test_coverage_predicate_rejects_a_key_present_only_in_non_check_prose(self):
        # NEGATIVE CONTROL 2 (the stronger one): a counted key that appears in the
        # Step-3 region's EXPLANATORY PROSE but in no numbered check must still be
        # reported as uncovered. Without the numbered-check narrowing this would
        # pass vacuously — a key mentioned in a preamble or worked example is not
        # a check that adjudicates the candidate.
        region = (
            '### Step 3: Apply seventeen checks\n'
            'Preamble prose references `prose_only_key` while explaining the mix.\n'
            '#### Present-state grounding precondition\n'
            'A worked example also names `prose_only_key` in passing.\n'
            '1. **Real check** — for each `covered_key` entry, adjudicate it.\n'
            '2. **Another check** — for each `other_covered_key` entry.\n'
            '### Dispatched-envelope output\n'
        )
        block = _numbered_check_block(_checks_region(region))
        synthetic = (
            CandidateList('prose_only_key', 'prose only', True, 'prose_contract'),
            CandidateList('covered_key', 'covered', True, 'structural'),
            CandidateList('other_covered_key', 'other', True, 'structural'),
        )
        assert _uncovered(synthetic, block) == ['prose_only_key']

    def test_both_new_checks_exist(self):
        # The two entries the plan targets each gained a consuming numbered check.
        block = _numbered_check_block(
            _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        )
        assert '`duplicate_claimable_keys`' in block
        assert '`discard_without_report`' in block

    def test_new_checks_do_not_change_total_magnitude(self):
        # Own the consequence rather than discovering it: adding the two checks
        # changes NO in_total flag, so counts.total (and the dispatch gate that
        # keys off it) keep their current magnitude by construction — the two
        # targeted entries were already counted and stay counted.
        assert next(s for s in CANDIDATE_LISTS if s.key == 'duplicate_claimable_keys').in_total
        assert next(s for s in CANDIDATE_LISTS if s.key == 'discard_without_report').in_total
