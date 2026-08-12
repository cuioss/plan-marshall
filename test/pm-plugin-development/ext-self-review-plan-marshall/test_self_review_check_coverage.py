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
inside the workflow doc's Step-3 checks region, so a counted entry with no
consuming check fails here rather than silently shipping.
"""

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

#: The Step-3 checks region boundaries. Coverage is asserted ONLY against the
#: region where the numbered cognitive checks live, so a candidate-list key that
#: appears in an Inputs table or an output-schema block elsewhere in the doc is
#: never mistaken for a consuming check.
_CHECKS_REGION_START = '### Step 3: Apply'
_CHECKS_REGION_END = '### Dispatched-envelope output'


def _checks_region(text: str) -> str:
    """Return the workflow doc's Step-3 cognitive-checks region."""
    start = text.index(_CHECKS_REGION_START)
    end = text.index(_CHECKS_REGION_END)
    return text[start:end]


def _counted_lists() -> list[CandidateList]:
    """The population: every registry entry summed into ``counts.total``."""
    return [spec for spec in CANDIDATE_LISTS if spec.in_total]


def _uncovered(candidate_lists: tuple[CandidateList, ...], checks_text: str) -> list[str]:
    """Return the counted keys with no backtick-quoted reference in ``checks_text``.

    The predicate is pure so a negative control can drive it with a synthetic
    registry, proving the invariant actually fails when a counted entry lacks a
    check rather than passing vacuously.
    """
    return [
        spec.key
        for spec in candidate_lists
        if spec.in_total and f'`{spec.key}`' not in checks_text
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
        checks = _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        uncovered = _uncovered(tuple(population), checks)
        assert uncovered == [], (
            'counted candidate list(s) with no consuming check in the workflow '
            f'doc Step-3 region: {uncovered} (population={len(population)})'
        )

    def test_coverage_predicate_detects_a_missing_check(self):
        # NEGATIVE CONTROL: the invariant MUST fail when a counted entry lacks a
        # consuming check. Drive the pure predicate with a synthetic registry
        # whose second in_total entry's key is absent from the checks text; a
        # non-counted (in_total=False) orphan is correctly ignored.
        synthetic = (
            CandidateList('covered_key', 'covered', True, 'structural'),
            CandidateList('orphan_key', 'orphan', True, 'structural'),
            CandidateList('anchor_key', 'anchor', False, 'prose_contract'),
        )
        checks_text = 'for each `covered_key` entry, adjudicate the thing.'
        assert _uncovered(synthetic, checks_text) == ['orphan_key']

    def test_both_new_checks_exist(self):
        # The two entries the plan targets each gained a consuming check.
        checks = _checks_region(_WORKFLOW_DOC.read_text(encoding='utf-8'))
        assert '`duplicate_claimable_keys`' in checks
        assert '`discard_without_report`' in checks

    def test_new_checks_do_not_change_total_magnitude(self):
        # Own the consequence rather than discovering it: adding the two checks
        # changes NO in_total flag, so counts.total (and the dispatch gate that
        # keys off it) keep their current magnitude by construction — the two
        # targeted entries were already counted and stay counted.
        assert next(s for s in CANDIDATE_LISTS if s.key == 'duplicate_claimable_keys').in_total
        assert next(s for s in CANDIDATE_LISTS if s.key == 'discard_without_report').in_total
