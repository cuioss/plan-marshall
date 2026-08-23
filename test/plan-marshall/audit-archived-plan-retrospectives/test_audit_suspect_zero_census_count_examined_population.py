#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The suspect-zero census — the class guard.

Scope: the zero streak and the population it is measured over — an unread count is
no count, a check that examined no plans is starved rather than disciplinary, and a
partial exclusion is still disciplinary.
"""


import re
from pathlib import Path

from _audit_fixtures import audit
from _audit_suspect_zero_census_fixtures import _EXAMINED_POPULATION_KEYS, _MEASURED_ZERO_BLOCK, _audit_source


class TestQuietStreaks:
    def test_streak_counts_consecutive_recorded_zeros(self):
        runs = [{"metrics": 0}, {"metrics": 0}, {"metrics": 3}]
        assert audit.quiet_streaks(runs)["metrics"] == 2

    def test_a_missing_record_breaks_the_streak(self):
        """An absent record is not a recorded zero.

        A check that stopped emitting must not accrue quiet runs toward its own
        retirement — which is also how an `unmeasured` run is kept out of the
        streak, since it publishes no genuine count.
        """
        runs = [{"metrics": 0}, {}, {"metrics": 0}]
        assert audit.quiet_streaks(runs)["metrics"] == 1

    def test_a_nonzero_first_run_yields_no_streak(self):
        assert audit.quiet_streaks([{"metrics": 1}, {"metrics": 0}])["metrics"] == 0


class TestNoCountAndExaminedPopulation:
    """The two ways a `disciplinary` verdict can be asserted without grounds."""

    def test_an_unread_count_is_no_count_not_disciplinary(self):
        """`None` means "no count was read" and must never render as a measured 0.

        `quality-chain` is such a block today: it emits
        `plan_genuine_signal_count` and `finding_genuine_signal_count` and no bare
        one, so `_GENUINE_COUNT_RE` records nothing for it. Defaulting that to 0
        and reporting `disciplinary` would have the census assert "a non-empty
        corpus was examined and nothing was genuine" on the strength of a default.
        """
        assert (
            audit._classify_zero(_MEASURED_ZERO_BLOCK, None, corpus_size=5)
            == audit._ZERO_NO_COUNT
        )

    def test_per_tier_genuine_counts_are_read_and_summed(self):
        """A multi-tier block states its total across per-tier lines, not one bare one.

        `quality-chain` publishes `plan_genuine_signal_count` and
        `finding_genuine_signal_count`. Reading only the bare spelling left it
        with no count on every run, so the census reported it a permanent suspect
        — including on runs where it FIRED, which is a constant rather than a
        detector.
        """
        block = (
            "check: quality-chain\nstatus: success\n"
            "plan_genuine_signal_count: 1\n"
            "finding_genuine_signal_count: 2\n"
        )
        assert audit._extract_per_check_genuine([block]) == {"quality-chain": 3}

    def test_a_bare_genuine_count_is_still_read(self):
        """The negative control — the widened read must not break the common shape."""
        assert audit._extract_per_check_genuine([_MEASURED_ZERO_BLOCK]) == {
            "dispatch-topology": 0
        }

    def test_a_firing_quality_chain_is_not_a_suspect(self, tmp_path: Path):
        """The consequence: a detector that produced positives is not suspect.

        D6's charter is to surface a detector that produced ZERO positives. One
        that fired must never appear in the suspect population, whatever spelling
        it used to state its count.
        """
        block = (
            "check: quality-chain\nstatus: success\n"
            "plan_genuine_signal_count: 1\n"
            "finding_genuine_signal_count: 1\n"
        )
        genuine = audit._extract_per_check_genuine([block])
        rows = audit.suspect_zero_census([block], genuine, {}, corpus_size=3)

        row = next(r for r in rows if r["check"] == "quality-chain")
        assert row["zero_class"] == audit._ZERO_NONE
        assert row["suspect"] == "false"

    def test_a_check_that_examined_no_plans_is_starved_not_disciplinary(self):
        """A delivery-cost check whose shipping partition excluded every plan.

        The corpus is non-empty, but this check saw nothing — so "a non-empty
        corpus was examined" is false of it. `_annotate_exclusions` stamps the
        count that makes the distinction available.
        """
        block = (
            "check: token-economics\nstatus: success\n"
            "plans_excluded_non_shipping: 5\n"
            "genuine_signal_count: 0\nrows[0]{a}:\n"
        )
        assert audit._classify_zero(block, 0, corpus_size=5) == audit._ZERO_STARVED

    def test_a_partially_excluded_check_is_still_disciplinary(self):
        """The discriminating half — exclusion alone does not mean starved."""
        block = (
            "check: token-economics\nstatus: success\n"
            "plans_excluded_non_shipping: 2\n"
            "genuine_signal_count: 0\nrows[3]{a}:\n"
        )
        assert audit._classify_zero(block, 0, corpus_size=5) == audit._ZERO_DISCIPLINARY

    def test_examined_population_defaults_to_the_whole_corpus(self):
        """A block with no exclusion line examined every plan."""
        assert audit._examined_population(_MEASURED_ZERO_BLOCK, 7) == 7

    def test_examined_population_never_goes_negative(self):
        block = "check: x\nplans_excluded_non_shipping: 9\n"
        assert audit._examined_population(block, 5) == 0


class TestGateExclusionKeyIsRead:
    """The gate-exclusion scalar `_classify_zero` reads is the one the emitter writes.

    `_UNATTRIBUTED_EXCLUDED_RE` hand-mirrors a scalar name that
    `emit_preference_pattern_block` owns — the same hand-mirror shape
    `_EXAMINED_POPULATION_KEYS` guards on the population axis, one key over. A
    rename on the emitting side leaves the reader matching nothing, and a reader
    that matches nothing does not fail loudly: it silently returns every gated
    zero to `disciplinary`, republishing the "the corpus was clean" reading the
    class exists to withhold. No other assertion in this suite would notice.

    Both tests drive the REAL emitter rather than a hand-built block. A
    synthesised fixture asserts only that the reader matches the string the test
    itself wrote, which is true however far the emitter has drifted from it.
    """

    @staticmethod
    def _emitted(excluded: int) -> str:
        return audit.emit_preference_pattern_block(
            {
                'threshold': 3,
                'candidate_count': 0,
                'unattributed_excluded_count': excluded,
                'plans_in_corpus': 4,
                'rows': [],
            }
        )

    def test_the_reader_matches_the_emitters_own_output(self):
        assert audit._UNATTRIBUTED_EXCLUDED_RE.search(self._emitted(2)) is not None

    def test_an_emitted_gated_zero_reaches_the_gated_class(self):
        """End-to-end: emitter → reader → verdict, with the pair that discriminates.

        A non-zero exclusion count is the gate speaking; a zero one is the gate
        silent, and the verdict must stay `disciplinary` for it — otherwise the
        first assertion would pass on a classifier that called every preference
        block `gated` regardless of the count.
        """
        assert audit._classify_zero(self._emitted(2), 0, corpus_size=4) == audit._ZERO_GATED
        assert (
            audit._classify_zero(self._emitted(0), 0, corpus_size=4)
            == audit._ZERO_DISCIPLINARY
        )


class TestPopulationKeyCoverage:
    """The key axis the whole-census guard does NOT quantify over.

    That guard loops over `CHECK_NAMES`, so a check cannot slip past it by being
    forgotten. But both it and `_examined_population` hard-code the KEY set, so a
    check can still slip past by publishing its population under a new name —
    which is the same enumeration shape, one axis over, and is exactly how
    `plans_in_series` and `plans_measured` went unread for five rounds.

    This narrows that axis: every key matching `f"plans_*:"` at the head of an
    f-string must be classified, either as a denominator `_examined_population`
    reads or as a deliberate non-denominator. A new key of that shape is a test
    failure rather than a silent gap.

    ⚠ It is a SHAPE-bounded guard, not a complete one. A population published
    under a different prefix, or assembled by concatenation rather than as an
    f-string literal, is invisible to the regex below and would slip through —
    verified by mutation. Today nothing does: every `plans_*` token in `audit.py`
    is classified. State the bound rather than claiming the axis is shut, because
    a guard believed stronger than it is is the defect this whole plan is about.
    """

    #: `plans_*` scalars that are NOT examined populations, each with its reason.
    #: Adding a key here is a claim; the docstring above says what the claim means.
    _NON_DENOMINATOR_KEYS = {
        # Zero means nothing was excluded — the population is FULL.
        "plans_excluded_non_shipping": "exclusion count",
        "plans_excluded_no_counters": "exclusion count",
        # `emit_table_block` emits `len(rows)` AFTER narrowing, so for the three
        # delivery-cost checks it routes (scope-estimate-accuracy,
        # task-count-efficiency, pr-merge-velocity) this IS the examined count,
        # not the corpus total. It is excluded anyway because those same blocks
        # carry the `plans_excluded_non_shipping` line `_examined_population`
        # reads at precedence 2, so the population is already established. A
        # FULL_CORPUS_CHECKS member that narrowed internally and emitted through
        # `emit_table_block` would be the gap — none does today.
        "plans_scanned": "narrowed row count; population established by the "
        "exclusion line these blocks also carry",
        # Numerators: how many plans landed in a result set. `plans_with_merge_events`
        # is the load-bearing case — `len(rows)`, how many plans HAD merge events.
        # Its check's substrate is the `[LOCK]` log, not the plan corpus, and an
        # absent log already reports `unmeasured`, so a readable log naming no merge
        # event is a genuine MEASURED zero and `disciplinary` is right for it.
        "plans_with_merge_events": "result count",
        "plans_without_ledger": "result count",
        "plans_without_ledger_ids": "result count",
    }

    def test_every_published_population_key_is_classified(self):
        published = set(
            re.findall(r'f"(plans_[a-z_]+):', _audit_source())
        )
        assert published, "no plans_* keys found — the sweep would pass vacuously"

        unclassified = published - set(_EXAMINED_POPULATION_KEYS) - set(
            self._NON_DENOMINATOR_KEYS
        )
        assert unclassified == set(), (
            f"unclassified population key(s): {sorted(unclassified)}. Either "
            "`_examined_population` must read it (and it joins "
            "`_EXAMINED_POPULATION_KEYS`), or it is not a denominator and joins "
            "`_NON_DENOMINATOR_KEYS` with its reason."
        )

    def test_every_denominator_key_is_read_by_the_production_reader(self):
        """A key this guard treats as a denominator the CODE must also read.

        The two lists disagreeing is what produced round 6's finding: the guard
        counted `plans_with_merge_events` as a population while
        `_examined_population` did not read it, and no fixture reached the state
        where that mattered.
        """
        for key in _EXAMINED_POPULATION_KEYS:
            block = f"check: x\nstatus: success\n{key}: 0\n"
            assert audit._examined_population(block, 7) == 0, key
