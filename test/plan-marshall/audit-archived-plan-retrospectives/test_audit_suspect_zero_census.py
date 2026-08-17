#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The suspect-zero census — the class guard.

A detector that has never produced a positive is indistinguishable, from its
output alone, from one that CANNOT produce one. The census makes every zero
SUSPECT rather than silently clean, and classifies what KIND of zero it is:

* ``structural`` — the check declared it could not measure. Not evidence.
* ``starved`` — the corpus supplied no plans. Not evidence either, for a
  different reason, and with a different remedy.
* ``disciplinary`` — a non-empty corpus was examined and nothing was genuine.
  Evidence about the corpus; never proof the check is able to fire.

The distinction is the deliverable. A census that lumped the three together
would report the same thing for a check whose predicate cannot fire and a check
that is doing its job over a clean corpus.
"""

from pathlib import Path

from _audit_fixtures import audit, minimal_corpus

_UNMEASURED_BLOCK = (
    "check: merge-window-accounting\nstatus: unmeasured\nunmeasured_reason: no substrate\n"
)
_MEASURED_ZERO_BLOCK = (
    "check: dispatch-topology\nstatus: success\ngenuine_signal_count: 0\nrows[3]{a}:\n"
)
_FIRED_BLOCK = (
    "check: dispatch-topology\nstatus: success\ngenuine_signal_count: 2\nrows[3]{a}:\n"
)


class TestZeroClassification:
    def test_unmeasured_status_is_a_structural_zero(self):
        assert (
            audit._classify_zero(_UNMEASURED_BLOCK, 0, corpus_size=5)
            == audit._ZERO_STRUCTURAL
        )

    def test_empty_corpus_is_a_starved_zero(self):
        assert (
            audit._classify_zero(_MEASURED_ZERO_BLOCK, 0, corpus_size=0)
            == audit._ZERO_STARVED
        )

    def test_measured_zero_over_a_real_corpus_is_disciplinary(self):
        assert (
            audit._classify_zero(_MEASURED_ZERO_BLOCK, 0, corpus_size=5)
            == audit._ZERO_DISCIPLINARY
        )

    def test_a_check_that_fired_is_not_a_suspect(self):
        assert audit._classify_zero(_FIRED_BLOCK, 2, corpus_size=5) == audit._ZERO_NONE

    def test_structural_outranks_starved(self):
        """An unmeasured check is structural even on an empty corpus.

        The check's own declaration is stronger evidence than the corpus size:
        it would not have measured whatever the corpus held.
        """
        assert (
            audit._classify_zero(_UNMEASURED_BLOCK, 0, corpus_size=0)
            == audit._ZERO_STRUCTURAL
        )

    def test_structural_outranks_no_count(self):
        """An unmeasured block withholds its count BY DESIGN.

        The withholding is how an unmeasured check stays out of the
        retire-on-quiet streak, so the absent count is a consequence of the
        declaration rather than an independent fact. Reporting `no_count` here
        would surface the symptom and discard the reason the block already gave —
        and `merge-window-accounting` is exactly this shape on a real sweep.
        """
        assert (
            audit._classify_zero(_UNMEASURED_BLOCK, None, corpus_size=5)
            == audit._ZERO_STRUCTURAL
        )


class TestCensusRows:
    def test_every_registered_check_gets_a_row(self):
        rows = audit.suspect_zero_census([], {}, {}, corpus_size=3)
        assert [r["check"] for r in rows] == list(audit.CHECK_NAMES)

    def test_a_check_that_emitted_no_block_is_itself_reported(self):
        """A detector that silently stopped emitting is the completest failure."""
        rows = audit.suspect_zero_census([], {}, {}, corpus_size=3)
        assert all(r["zero_class"] == "no_block" for r in rows)
        assert all(r["suspect"] == "true" for r in rows)

    def test_a_deliberately_starved_detector_is_surfaced_as_suspect(self):
        """The plan's acceptance: starve a detector, and the census must say so.

        `merge-window-accounting` has no `[LOCK]` substrate here, so it reports
        `unmeasured` and its zero is classified `structural` — not silently clean,
        and not conflated with a check that looked and found nothing.
        """
        rows = audit.suspect_zero_census(
            [_UNMEASURED_BLOCK, _MEASURED_ZERO_BLOCK],
            {"merge-window-accounting": 0, "dispatch-topology": 0},
            {},
            corpus_size=5,
        )
        by_check = {r["check"]: r for r in rows}

        starved = by_check["merge-window-accounting"]
        assert starved["suspect"] == "true"
        assert starved["zero_class"] == audit._ZERO_STRUCTURAL
        assert "NOT evidence" in starved["reading"]

        # The discriminating half: a check over the SAME corpus that did measure
        # is classified differently. Without this the test would pass on a census
        # that called everything structural.
        clean = by_check["dispatch-topology"]
        assert clean["zero_class"] == audit._ZERO_DISCIPLINARY
        assert clean["suspect"] == "true"

    def test_quiet_streak_is_carried_per_check(self):
        rows = audit.suspect_zero_census(
            [_MEASURED_ZERO_BLOCK], {"dispatch-topology": 0}, {"dispatch-topology": 7}, 5
        )
        row = next(r for r in rows if r["check"] == "dispatch-topology")
        assert row["quiet_run_count"] == 7


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


class TestCensusEndToEnd:
    """Joins the real emitter to the real classification.

    Building the block by hand and asserting on it is the shape the plan calls
    out for D3 — a suite that synthesises its own marker cannot see the emitter
    drift away from it. These assertions run a real sweep.
    """

    def test_a_starved_detector_is_structural_on_a_real_sweep(self, tmp_path: Path):
        """`merge-window-accounting` has no `[LOCK]` substrate in this corpus."""
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        row = next(
            ln
            for ln in output.splitlines()
            if ln.strip().startswith("merge-window-accounting,")
        )
        assert audit._ZERO_STRUCTURAL in row
        assert ",true," in row

    def test_a_measuring_check_over_the_same_sweep_is_classified_differently(
        self, tmp_path: Path
    ):
        """The discriminator — without it this would pass on an all-structural census."""
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        row = next(
            ln
            for ln in output.splitlines()
            if ln.strip().startswith("dispatch-topology,")
        )
        assert audit._ZERO_STRUCTURAL not in row

    def test_no_registered_check_is_classified_no_count_on_a_real_sweep(
        self, tmp_path: Path
    ):
        """Every emitted block states a genuine total the census can read.

        `no_count` is a defensive class for a block that publishes none. A check
        landing there on a normal sweep means the census is reporting a permanent
        suspect about a detector it simply cannot read — which is a constant, not
        a detector, and `quality-chain` was exactly that until its per-tier counts
        were made readable.
        """
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        census = output.split("check: suspect-zero-census", 1)[1]
        offenders = [
            ln.strip()
            for ln in census.splitlines()
            if f",{audit._ZERO_NO_COUNT}," in ln
        ]
        assert offenders == []

    def test_a_check_narrowing_its_own_population_to_zero_is_starved(
        self, tmp_path: Path
    ):
        """Pins the call ORDER `_examined_population` silently depends on.

        The population is read off the emitted block, so the census must run after
        the blocks are built and annotated. Move it earlier and every
        population-narrowing check regresses to `disciplinary` — a starved zero
        reported as evidence — with a green suite otherwise. This test fails on
        that reordering because it drives the real `run_checks`.
        """
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        census = output.split("check: suspect-zero-census", 1)[1]
        # `exploration-share` narrows on its own axis (plans with no counters) and
        # the minimal corpus supplies none, so its examined population is zero.
        row = next(
            ln for ln in census.splitlines() if ln.strip().startswith("exploration-share,")
        )
        assert audit._ZERO_DISCIPLINARY not in row


class TestCensusBlock:
    def test_block_carries_class_counts_and_the_reading_note(self):
        rows = audit.suspect_zero_census(
            [_UNMEASURED_BLOCK, _FIRED_BLOCK],
            {"merge-window-accounting": 0, "dispatch-topology": 2},
            {},
            corpus_size=5,
        )
        block = audit.emit_suspect_zero_census_block(rows, corpus_size=5)

        assert "check: suspect-zero-census" in block
        assert "structural_count: 1" in block
        assert "census_note:" in block
        assert "a zero is not a clean verdict" in block
        assert f"checks_registered: {len(audit.CHECK_NAMES)}" in block

    def test_full_sweep_emits_the_census(self, tmp_path: Path):
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        assert "check: suspect-zero-census" in output
        # It reports; it never proposes or blocks. The retirement reading lives in
        # its own block and the two are emitted together, so a quiet check is
        # never presented with only one of the two readings available.
        assert "check: retire-on-quiet" in output

    def test_census_and_retire_on_quiet_agree_on_the_streak(self, tmp_path: Path):
        """Both blocks read one derivation, so they cannot disagree about it."""
        runs = [{"metrics": 0}, {"metrics": 0}]
        streaks = audit.quiet_streaks(runs)
        rows = audit.suspect_zero_census(
            [_MEASURED_ZERO_BLOCK.replace("dispatch-topology", "metrics")],
            {"metrics": 0},
            streaks,
            corpus_size=4,
        )
        row = next(r for r in rows if r["check"] == "metrics")
        assert row["quiet_run_count"] == streaks["metrics"] == 2
